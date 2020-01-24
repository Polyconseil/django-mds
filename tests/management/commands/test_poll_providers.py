import datetime
import io
import urllib.parse

import pytest

from django.core.management import call_command
from django.utils import timezone

from mds import enums
from mds import factories
from mds import models
from mds import utils
from mds.provider_mapping import (
    PROVIDER_REASON_TO_AGENCY_EVENT,
    PROVIDER_EVENT_TYPE_REASON_TO_EVENT_TYPE,
)


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
        json=make_response(
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
        json=make_response(
            provider,
            expected_device2,
            expected_event2,
            event_type_reason="maintenance_pick_up",
        ),
    )
    call_command("poll_providers", "--raise-on-error", stdout=stdout, stderr=stderr)

    assert_command_success(stdout, stderr)

    event1 = device1.event_records.get()
    assert_event_equal(event1, expected_event1)

    # The second device was created on the fly
    device2 = models.Device.objects.get(pk=expected_device2.pk)
    assert device2.saved_at is not None
    # With a fake register event and the actual event
    event2_register, event2_regular = device2.event_records.order_by("timestamp")

    assert event2_register.event_type == enums.EVENT_TYPE.register.name
    assert event2_register.properties == {"created_on_register": True}
    assert_event_equal(event2_regular, expected_event2)
    assert_device_equal(device2, expected_device2)


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
            json=make_response(
                provider1,
                device1,
                expected_event1,
                event_type_reason="rebalance_drop_off",
            ),
        )
        requests_mock.get(
            urllib.parse.urljoin(provider2.base_api_url, "/status_changes"),
            json=make_response(
                provider2, device2, expected_event2, event_type_reason="maintenance"
            ),
        )
        call_command("poll_providers", "--raise-on-error", stdout=stdout, stderr=stderr)

    assert_command_success(stdout, stderr)

    event1_register, event1_regular = device1.event_records.order_by("timestamp")
    assert event1_register.event_type == enums.EVENT_TYPE.register.name
    assert event1_register.properties == {"created_on_register": True}
    assert_event_equal(event1_regular, expected_event1)

    event2_register, event2_regular = device2.event_records.order_by("timestamp")
    assert event2_register.event_type == enums.EVENT_TYPE.register.name
    assert event2_register.properties == {"created_on_register": True}
    assert_event_equal(event2_regular, expected_event2)


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
        json=make_response(
            provider, device, expected_event, event_type_reason="service_end"
        ),
    )
    call_command("poll_providers", "--raise-on-error", stdout=stdout, stderr=stderr)

    assert_command_success(stdout, stderr)

    assert device.event_records.count() == 2
    event = device.event_records.latest("timestamp")
    assert_event_equal(event, expected_event)


@pytest.mark.django_db
def test_poll_provider_v0_4_archives(client, requests_mock):
    # Note: testing with the default "POLLER_CREATE_REGISTER_EVENTS = False"
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
        json=make_response(
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

    assert_command_success(stdout, stderr)
    # The last poller cursor is updated
    provider = models.Provider.objects.get(pk=provider.pk)
    assert provider.last_event_time_polled is not None
    # The device was created on the fly
    device = models.Device.objects.get(pk=expected_device.pk)
    assert device.saved_at is not None
    # The actual event
    event = device.event_records.get()
    assert event.event_type == enums.EVENT_TYPE.service_start.name
    assert_event_equal(event, expected_event)
    assert_device_equal(device, expected_device)


@pytest.mark.django_db
def test_poll_provider_v0_4_archives_resume(client, requests_mock):
    # Note: testing with the default "POLLER_CREATE_REGISTER_EVENTS = False"
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
        json=make_response(
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

    assert_command_success(stdout, stderr)
    # The last poller cursor is updated
    provider = models.Provider.objects.get(pk=provider.pk)
    assert provider.last_event_time_polled > last_event_time_polled
    # The device was created on the fly
    device = models.Device.objects.get(pk=expected_device.pk)
    assert device.saved_at is not None
    # The actual event
    event = device.event_records.get()
    assert event.event_type == enums.EVENT_TYPE.service_start.name
    assert_event_equal(event, expected_event)
    assert_device_equal(device, expected_device)


@pytest.mark.django_db
def test_poll_provider_v0_4_archives_no_result(client, requests_mock):
    # Note: testing with the default "POLLER_CREATE_REGISTER_EVENTS = False"
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

    assert_command_success(stdout, stderr)
    # The last poller cursor is updated
    provider = models.Provider.objects.get(pk=provider.pk)
    # No event but we won't ask this hour again
    assert provider.last_event_time_polled is not None


@pytest.mark.django_db
def test_poll_provider_v0_4_realtime(client, requests_mock):
    # Note: testing with the default "POLLER_CREATE_REGISTER_EVENTS = False"
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
        start_time = utils.from_mds_timestamp(int(request.qs["start_time"][0]))
        assert almost_equal(start_time, last_event_time_polled)
        # End time is after start time but valued "now()" when the poller was running
        end_time = utils.from_mds_timestamp(int(request.qs["end_time"][0]))
        assert end_time > start_time
        assert almost_equal(
            end_time, timezone.now(), precision=datetime.timedelta(seconds=1)
        )
        context.status_code = 200
        return make_response(
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

    assert_command_success(stdout, stderr)
    # The last poller cursor is updated
    provider = models.Provider.objects.get(pk=provider.pk)
    assert provider.last_event_time_polled != last_event_time_polled
    # The device was created on the fly
    device = models.Device.objects.get(pk=expected_device.pk)
    assert device.saved_at is not None
    # The actual event
    event = device.event_records.get()
    assert event.event_type == enums.EVENT_TYPE.service_start.name
    assert_event_equal(event, expected_event)
    assert_device_equal(device, expected_device)


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
        start_time = utils.from_mds_timestamp(int(request.qs["start_time"][0]))
        assert almost_equal(start_time, last_event_time_polled)
        # End time is after start time but before the lag threshold
        end_time = utils.from_mds_timestamp(int(request.qs["end_time"][0]))
        assert end_time > start_time
        assert almost_equal(end_time, timezone.now(), precision=lag_plus_one_second)
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
    assert_command_success(stdout, stderr)

    # No result, the polling cursor is not updated
    provider = models.Provider.objects.get(pk=provider.pk)
    assert provider.last_event_time_polled == last_event_time_polled


@pytest.mark.django_db
def test_poll_provider_v0_4_lag(client, requests_mock):
    # Note: testing with the default "POLLER_CREATE_REGISTER_EVENTS = False"
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

    assert_command_success(stdout, stderr)
    # The last poller cursor is NOT updated
    provider = models.Provider.objects.get(pk=provider.pk)
    assert provider.last_event_time_polled == last_event_time_polled
    # No device created
    assert models.Device.objects.count() == 0
    # No event created
    assert models.EventRecord.objects.count() == 0


#
# Utilities
#


def make_response(
    provider,
    device,
    event,
    event_type_reason,
    associated_trip=None,
    next_page=None,
    version="0.3.0",
):
    assert event.event_type in [
        event_type for event_type, *_ in dict(PROVIDER_REASON_TO_AGENCY_EVENT).values()
    ]
    telemetry = event.properties["telemetry"]

    response = factories.ProviderStatusChangesBody(
        version=version,
        data__status_changes=[
            factories.ProviderStatusChange(
                provider_id=str(provider.pk),
                provider_name=provider.name,
                device_id=str(device.pk),
                vehicle_id=device.identification_number,
                vehicle_type=device.category,
                event_type=PROVIDER_EVENT_TYPE_REASON_TO_EVENT_TYPE[event_type_reason],
                event_type_reason=event_type_reason,
                propulsion_type=device.propulsion,
                event_time=int(event.timestamp.timestamp() * 1000),  # In ms
                event_location__properties__timestamp=telemetry["timestamp"],
                event_location__geometry__coordinates=[
                    telemetry["gps"]["lng"],
                    telemetry["gps"]["lat"],
                ],
                associated_trip=associated_trip,
                recorded=int(event.timestamp.timestamp() * 1000),  # In ms
            )
        ],
        links__next=next_page,
    )
    assert response["data"]["status_changes"][0]["event_location"]["geometry"][
        "coordinates"
    ] == [telemetry["gps"]["lng"], telemetry["gps"]["lat"]]
    return response


def assert_command_success(stdout, stderr):
    assert not stderr.getvalue().strip(), """Command failed!
stdout:
%s
stderr:
%s
""" % (
        stdout.getvalue(),
        stderr.getvalue(),
    )


def assert_device_equal(device, expected_device):
    assert device.category == expected_device.category
    assert device.identification_number == expected_device.identification_number
    if device.model:
        assert device.model == expected_device.model
    assert device.propulsion == expected_device.propulsion


def assert_event_equal(event, expected_event):
    # These are not (yet?) in the provider API
    del expected_event.properties["telemetry"]["gps"]["accuracy"]
    del expected_event.properties["telemetry"]["gps"]["altitude"]
    del expected_event.properties["telemetry"]["gps"]["heading"]
    del expected_event.properties["telemetry"]["gps"]["speed"]
    assert abs(event.timestamp - expected_event.timestamp) < datetime.timedelta(
        seconds=0.001
    )
    assert event.point.json == expected_event.point.json
    assert event.properties == expected_event.properties


def almost_equal(
    datetime1: datetime.datetime,
    datetime2: datetime.datetime,
    precision: datetime.timedelta = datetime.timedelta(milliseconds=1),
) -> bool:
    """Compares two datetimes to be almost equal.

    The default precision matches the MDS specification timestamps in milliseconds
    (when Python datetime objects can be precise to the microsecond).
    """
    return abs(datetime1 - datetime2) < precision
