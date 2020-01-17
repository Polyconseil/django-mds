import datetime
import io
import urllib.parse

import pytest

from django.core.management import call_command
from django.utils import timezone

from mds import enums
from mds import factories
from mds import models

from . import utils


@pytest.mark.django_db
def test_poll_provider_batch(client, settings, requests_mock):
    """A single provider with two pages of status changes."""
    settings.POLLER_CREATE_REGISTER_EVENTS = True
    provider = factories.Provider(base_api_url="http://provider")
    # The first device received already exists
    device1 = factories.Device(provider=provider)
    expected_event1 = factories.EventRecord.build(
        event_type=enums.EVENT_TYPE.service_start.name,
        properties__trip_id="e7a9d3aa-68ea-4666-8adf-7bad40e49805",
    )
    # The second device received is unknown
    expected_device2 = factories.Device.build()
    expected_event2 = factories.EventRecord.build(
        event_type=enums.EVENT_TYPE.trip_end.name
    )
    stdout, stderr = io.StringIO(), io.StringIO()

    url = urllib.parse.urljoin(provider.base_api_url, "/status_changes")
    next_page = "%s?page=2" % url
    requests_mock.get(
        url,
        json=utils.make_response(
            provider,
            device1,
            expected_event1,
            event_type_reason="service_start",
            associated_trip="e7a9d3aa-68ea-4666-8adf-7bad40e49805",
            next_page=next_page,
        ),
    )
    requests_mock.get(
        next_page,
        json=utils.make_response(
            provider,
            expected_device2,
            expected_event2,
            event_type_reason="maintenance_pick_up",
        ),
    )
    call_command("poll_providers", "--raise-on-error", stdout=stdout, stderr=stderr)

    utils.assert_command_success(stdout, stderr)

    event1 = device1.event_records.get()
    utils.assert_event_equal(event1, expected_event1)

    # The second device was created on the fly
    device2 = models.Device.objects.get(pk=expected_device2.pk)
    assert device2.saved_at is not None
    # With a fake register event and the actual event
    event2_register, event2_regular = device2.event_records.order_by("timestamp")

    assert event2_register.event_type == enums.EVENT_TYPE.register.name
    assert event2_register.properties == {"created_on_register": True}
    utils.assert_event_equal(event2_regular, expected_event2)
    utils.assert_device_equal(device2, expected_device2)


@pytest.mark.django_db
def test_several_providers(client, django_assert_num_queries, settings, requests_mock):
    """Two providers this time."""
    settings.POLLER_CREATE_REGISTER_EVENTS = True
    provider1 = factories.Provider(base_api_url="http://provider1")
    device1 = factories.Device.build(provider=provider1)
    expected_event1 = factories.EventRecord.build(
        event_type=enums.EVENT_TYPE.provider_drop_off.name
    )
    provider2 = factories.Provider(base_api_url="http://provider2")
    device2 = factories.Device.build(provider=provider2)
    expected_event2 = factories.EventRecord.build(
        event_type=enums.EVENT_TYPE.trip_start.name
    )
    stdout, stderr = io.StringIO(), io.StringIO()

    n = 1  # List of providers
    n += 2  # List of provider IDs (for each provider)
    n += 2  # List of device IDs (for each provider)
    n += (
        2  # Savepoint/release for each provider
        + 1  # Insert missing devices
        + 1  # Insert fake register event
        + 1  # Insert missing event records
        + 1  # Update last start time polled
    ) * 2  # For each provider
    with django_assert_num_queries(n):
        requests_mock.get(
            urllib.parse.urljoin(provider1.base_api_url, "/status_changes"),
            json=utils.make_response(
                provider1,
                device1,
                expected_event1,
                event_type_reason="rebalance_drop_off",
            ),
        )
        requests_mock.get(
            urllib.parse.urljoin(provider2.base_api_url, "/status_changes"),
            json=utils.make_response(
                provider2, device2, expected_event2, event_type_reason="maintenance"
            ),
        )
        call_command("poll_providers", "--raise-on-error", stdout=stdout, stderr=stderr)

    utils.assert_command_success(stdout, stderr)

    event1_register, event1_regular = device1.event_records.order_by("timestamp")
    assert event1_register.event_type == enums.EVENT_TYPE.register.name
    assert event1_register.properties == {"created_on_register": True}
    utils.assert_event_equal(event1_regular, expected_event1)

    event2_register, event2_regular = device2.event_records.order_by("timestamp")
    assert event2_register.event_type == enums.EVENT_TYPE.register.name
    assert event2_register.properties == {"created_on_register": True}
    utils.assert_event_equal(event2_regular, expected_event2)


@pytest.mark.django_db
def test_follow_up(client, settings, requests_mock):
    """Catching up new telemetries from the last one we got."""
    settings.POLLER_CREATE_REGISTER_EVENTS = True
    event = factories.EventRecord(device__provider__base_api_url="http://provider")
    device = event.device
    provider = device.provider
    provider.last_event_time_polled = event.timestamp
    provider.save()
    expected_event = factories.EventRecord.build(
        event_type=enums.EVENT_TYPE.service_end.name, timestamp=timezone.now()
    )
    stdout, stderr = io.StringIO(), io.StringIO()

    # Mocking must fail if the command does not make the expected query
    requests_mock.get(
        urllib.parse.urljoin(provider.base_api_url, "/status_changes"), status_code=400,
    )
    requests_mock.get(
        urllib.parse.urljoin(
            provider.base_api_url,
            "/status_changes?%s"
            % urllib.parse.urlencode(
                {"start_time": round(event.timestamp.timestamp() * 1000)}
            ),
        ),
        json=utils.make_response(
            provider, device, expected_event, event_type_reason="service_end"
        ),
    )
    call_command("poll_providers", "--raise-on-error", stdout=stdout, stderr=stderr)

    utils.assert_command_success(stdout, stderr)

    assert device.event_records.count() == 2
    event = device.event_records.latest("timestamp")
    utils.assert_event_equal(event, expected_event)


@pytest.mark.django_db
def test_poll_provider_lag(client, requests_mock):
    # Note: testing with the default "POLLER_CREATE_REGISTER_EVENTS = False"
    # Below the lag threshold
    last_event_time_polled = timezone.now() - datetime.timedelta(minutes=30)
    provider = factories.Provider(
        base_api_url="http://provider",
        api_configuration__provider_polling_lag="PT1H",  # One hour
        last_event_time_polled=last_event_time_polled,
    )
    stdout, stderr = io.StringIO(), io.StringIO()

    # No endpoint should be called
    requests_mock.get(
        urllib.parse.urljoin(provider.base_api_url, "/events"), status_code=400,
    )
    requests_mock.get(
        urllib.parse.urljoin(provider.base_api_url, "/status_changes"), status_code=400,
    )
    call_command("poll_providers", "--raise-on-error", stdout=stdout, stderr=stderr)

    utils.assert_command_success(stdout, stderr)
    # The last poller cursor is NOT updated
    provider = models.Provider.objects.get(pk=provider.pk)
    assert provider.last_event_time_polled == last_event_time_polled
    # No device created
    assert models.Device.objects.count() == 0
    # No event created
    assert models.EventRecord.objects.count() == 0
