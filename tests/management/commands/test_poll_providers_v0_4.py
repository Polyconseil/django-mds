import datetime
import io
import urllib.parse

import pytest

from django.core.management import call_command
from django.utils import timezone

from mds import enums
from mds import factories
from mds import models
from mds.utils import from_mds_timestamp

from . import utils

# Note: testing with the default "POLLER_CREATE_REGISTER_EVENTS = False"


@pytest.mark.django_db
def test_poll_provider_batch(client, requests_mock):
    """A single provider with two pages of status changes."""
    provider = factories.Provider(
        base_api_url="http://provider",
        api_configuration__api_version=enums.MDS_VERSIONS.v0_4.name,
    )
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

    # As we're starting before the threshold, we'll poll the archives endpoint
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
            version="0.4.0",
        ),
    )
    requests_mock.get(
        next_page,
        json=utils.make_response(
            provider,
            expected_device2,
            expected_event2,
            event_type_reason="maintenance_pick_up",
            version="0.4.0",
        ),
    )
    call_command("poll_providers", "--raise-on-error", stdout=stdout, stderr=stderr)

    utils.assert_command_success(stdout, stderr)

    event1 = device1.event_records.get()
    utils.assert_event_equal(event1, expected_event1)

    # The second device was created on the fly
    device2 = models.Device.objects.get(pk=expected_device2.pk)
    assert device2.saved_at is not None
    event2 = device2.event_records.get()

    utils.assert_event_equal(event2, expected_event2)
    utils.assert_device_equal(device2, expected_device2)


@pytest.mark.django_db
def test_several_providers(client, django_assert_num_queries, requests_mock):
    """Two providers this time."""
    provider1 = factories.Provider(
        base_api_url="http://provider1",
        api_configuration__api_version=enums.MDS_VERSIONS.v0_4.name,
    )
    device1 = factories.Device.build(provider=provider1)
    expected_event1 = factories.EventRecord.build(
        event_type=enums.EVENT_TYPE.provider_drop_off.name
    )
    provider2 = factories.Provider(
        base_api_url="http://provider2",
        api_configuration__api_version=enums.MDS_VERSIONS.v0_4.name,
    )
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
                version="0.4.0",
            ),
        )
        requests_mock.get(
            urllib.parse.urljoin(provider2.base_api_url, "/status_changes"),
            json=utils.make_response(
                provider2,
                device2,
                expected_event2,
                event_type_reason="maintenance",
                version="0.4.0",
            ),
        )
        call_command("poll_providers", "--raise-on-error", stdout=stdout, stderr=stderr)

    utils.assert_command_success(stdout, stderr)

    event1 = device1.event_records.get()
    utils.assert_event_equal(event1, expected_event1)

    event2 = device2.event_records.get()
    utils.assert_event_equal(event2, expected_event2)


@pytest.mark.django_db
def test_follow_up(client, requests_mock):
    """Catching up new telemetries from the last one we got."""
    event = factories.EventRecord(
        device__provider__base_api_url="http://provider",
        device__provider__api_configuration__api_version=enums.MDS_VERSIONS.v0_4.name,
    )
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
        urllib.parse.urljoin(provider.base_api_url, "/events"), status_code=400,
    )
    requests_mock.get(
        urllib.parse.urljoin(
            provider.base_api_url,
            "/events?%s"
            % urllib.parse.urlencode(
                {"start_time": round(event.timestamp.timestamp() * 1000)}
            ),
        ),
        json=utils.make_response(
            provider,
            device,
            expected_event,
            event_type_reason="service_end",
            version="0.4.0",
        ),
    )
    call_command("poll_providers", "--raise-on-error", stdout=stdout, stderr=stderr)

    utils.assert_command_success(stdout, stderr)

    # The existing one and the new one
    assert device.event_records.count() == 2
    event = device.event_records.latest("timestamp")
    utils.assert_event_equal(event, expected_event)


@pytest.mark.django_db
def test_poll_provider_archives(client, requests_mock):
    provider = factories.Provider(
        base_api_url="http://provider",
        api_configuration__api_version=enums.MDS_VERSIONS.v0_4.name,
    )
    # We're polling from zero, nothing already exists in the DB
    expected_device = factories.Device.build()
    expected_event = factories.EventRecord.build(
        event_type=enums.EVENT_TYPE.service_start.name,
    )
    stdout, stderr = io.StringIO(), io.StringIO()

    # As we're starting before the threshold, we'll poll the archives endpoint
    status_changes = urllib.parse.urljoin(provider.base_api_url, "/status_changes")
    requests_mock.get(
        status_changes,
        json=utils.make_response(
            provider,
            expected_device,
            expected_event,
            event_type_reason="service_start",
            version="0.4.0",
        ),
    )
    # Mocking must fail if we query the real time endpoint instead
    requests_mock.get(
        urllib.parse.urljoin(provider.base_api_url, "/events"), status_code=400,
    )
    call_command("poll_providers", "--raise-on-error", stdout=stdout, stderr=stderr)

    utils.assert_command_success(stdout, stderr)
    # The last poller cursor is updated
    provider = models.Provider.objects.get(pk=provider.pk)
    assert provider.last_event_time_polled is not None
    # The device was created on the fly
    device = models.Device.objects.get(pk=expected_device.pk)
    assert device.saved_at is not None
    # The actual event
    event = device.event_records.get()
    assert event.event_type == enums.EVENT_TYPE.service_start.name
    utils.assert_event_equal(event, expected_event)
    utils.assert_device_equal(device, expected_device)


@pytest.mark.django_db
def test_poll_provider_archives_resume(client, requests_mock):
    last_event_time_polled = datetime.datetime(
        2019, 10, 16, 14, 40, 35, tzinfo=timezone.utc
    )
    provider = factories.Provider(
        base_api_url="http://provider",
        api_configuration__api_version=enums.MDS_VERSIONS.v0_4.name,
        last_event_time_polled=last_event_time_polled,
    )
    # We're polling from zero, nothing already exists in the DB
    expected_device = factories.Device.build()
    expected_event = factories.EventRecord.build(
        event_type=enums.EVENT_TYPE.service_start.name,
    )
    stdout, stderr = io.StringIO(), io.StringIO()

    # As we're starting before the threshold, we'll poll the archives endpoint
    status_changes = urllib.parse.urljoin(provider.base_api_url, "/status_changes")
    requests_mock.get(
        status_changes,
        json=utils.make_response(
            provider,
            expected_device,
            expected_event,
            event_type_reason="service_start",
            version="0.4.0",
        ),
    )
    # Mocking must fail if we query the real time endpoint instead
    requests_mock.get(
        urllib.parse.urljoin(provider.base_api_url, "/events"), status_code=400,
    )
    call_command("poll_providers", "--raise-on-error", stdout=stdout, stderr=stderr)

    utils.assert_command_success(stdout, stderr)
    # The last poller cursor is updated
    provider = models.Provider.objects.get(pk=provider.pk)
    assert provider.last_event_time_polled > last_event_time_polled
    # The device was created on the fly
    device = models.Device.objects.get(pk=expected_device.pk)
    assert device.saved_at is not None
    # The actual event
    event = device.event_records.get()
    assert event.event_type == enums.EVENT_TYPE.service_start.name
    utils.assert_event_equal(event, expected_event)
    utils.assert_device_equal(device, expected_device)


@pytest.mark.django_db
def test_poll_provider_archives_no_result(client, requests_mock):
    provider = factories.Provider(
        base_api_url="http://provider",
        api_configuration__api_version=enums.MDS_VERSIONS.v0_4.name,
        last_event_time_polled=None,
    )
    stdout, stderr = io.StringIO(), io.StringIO()

    # As we're starting before the threshold, we'll poll the archives endpoint
    status_changes = urllib.parse.urljoin(provider.base_api_url, "/status_changes")
    requests_mock.get(
        status_changes,
        json={
            "version": "0.4.0",
            "data": {"status_changes": []},
        },  # No status changes in this hour
    )
    # Mocking must fail if we query the real time endpoint instead
    requests_mock.get(
        urllib.parse.urljoin(provider.base_api_url, "/events"), status_code=400,
    )
    call_command("poll_providers", "--raise-on-error", stdout=stdout, stderr=stderr)

    utils.assert_command_success(stdout, stderr)
    # The last poller cursor is updated
    provider = models.Provider.objects.get(pk=provider.pk)
    # No event but we won't ask this hour again
    assert provider.last_event_time_polled is not None


@pytest.mark.django_db
def test_poll_provider_realtime(client, requests_mock):
    # This time we didn't poll long ago
    last_event_time_polled = timezone.now() - datetime.timedelta(3)
    provider = factories.Provider(
        base_api_url="http://provider",
        api_configuration__api_version=enums.MDS_VERSIONS.v0_4.name,
        last_event_time_polled=last_event_time_polled,
    )
    # We're polling from zero, nothing already exists in the DB
    expected_device = factories.Device.build()
    expected_event = factories.EventRecord.build(
        event_type=enums.EVENT_TYPE.service_start.name,
    )
    stdout, stderr = io.StringIO(), io.StringIO()

    def events_callback(request, context):
        """Check the query parameters"""
        # Start time is were the poller stopped last time
        start_time = from_mds_timestamp(int(request.qs["start_time"][0]))
        assert utils.almost_equal(start_time, last_event_time_polled)
        # End time is after start time but valued "now()" when the poller was running
        end_time = from_mds_timestamp(int(request.qs["end_time"][0]))
        assert end_time > start_time
        assert utils.almost_equal(
            end_time, timezone.now(), precision=datetime.timedelta(seconds=1)
        )
        context.status_code = 200
        return utils.make_response(
            provider,
            expected_device,
            expected_event,
            event_type_reason="service_start",
            version="0.4.0",
        )

    events = urllib.parse.urljoin(provider.base_api_url, "/events")
    requests_mock.get(events, json=events_callback)
    # Mocking must fail if we query the archives endpoint instead
    requests_mock.get(
        urllib.parse.urljoin(provider.base_api_url, "/status_changes"), status_code=400,
    )
    call_command("poll_providers", "--raise-on-error", stdout=stdout, stderr=stderr)

    utils.assert_command_success(stdout, stderr)
    # The last poller cursor is updated
    provider = models.Provider.objects.get(pk=provider.pk)
    assert provider.last_event_time_polled != last_event_time_polled
    # The device was created on the fly
    device = models.Device.objects.get(pk=expected_device.pk)
    assert device.saved_at is not None
    # The actual event
    event = device.event_records.get()
    assert event.event_type == enums.EVENT_TYPE.service_start.name
    utils.assert_event_equal(event, expected_event)
    utils.assert_device_equal(device, expected_device)


@pytest.mark.django_db
def test_poll_provider_v0_4_realtime_lag(client, requests_mock):
    """test the edge case of being just above the lag threshold"""
    lag_plus_one_second = datetime.timedelta(hours=1, seconds=1)
    last_event_time_polled = timezone.now() - lag_plus_one_second
    provider = factories.Provider(
        base_api_url="http://provider",
        api_configuration__api_version=enums.MDS_VERSIONS.v0_4.name,
        last_event_time_polled=last_event_time_polled,
        api_configuration__provider_polling_lag="PT1H",  # One hour
    )

    def events_callback(request, context):
        """Check the query parameters"""
        # Start time is were the poller stopped last time
        start_time = from_mds_timestamp(int(request.qs["start_time"][0]))
        assert utils.almost_equal(start_time, last_event_time_polled)
        # End time is after start time but before the lag threshold
        end_time = from_mds_timestamp(int(request.qs["end_time"][0]))
        assert end_time > start_time
        assert utils.almost_equal(
            end_time, timezone.now(), precision=lag_plus_one_second
        )
        context.status_code = 200
        return {
            "version": "0.4.0",
            "data": {"status_changes": []},
        }

    events = urllib.parse.urljoin(provider.base_api_url, "/events")
    requests_mock.get(events, json=events_callback)
    # Mocking must fail if we query the archives endpoint instead
    requests_mock.get(
        urllib.parse.urljoin(provider.base_api_url, "/status_changes"), status_code=400,
    )

    stdout, stderr = io.StringIO(), io.StringIO()
    call_command("poll_providers", "--raise-on-error", stdout=stdout, stderr=stderr)
    utils.assert_command_success(stdout, stderr)

    # No result, the polling cursor is not updated
    provider = models.Provider.objects.get(pk=provider.pk)
    assert provider.last_event_time_polled == last_event_time_polled


@pytest.mark.django_db
def test_poll_provider_lag(client, requests_mock):
    # Below the lag threshold
    last_event_time_polled = timezone.now() - datetime.timedelta(minutes=30)
    provider = factories.Provider(
        base_api_url="http://provider",
        api_configuration__api_version=enums.MDS_VERSIONS.v0_4.name,
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
