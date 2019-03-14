import datetime
import io
import urllib.parse

import pytest

from django.core.management import call_command
from django.utils import timezone

import requests_mock

from mds import enums
from mds import factories
from mds import models


# This is what the agency API is calling status, go figure
PROVIDER_EVENT_TYPES = {
    "service_start": "available",
    "user_drop_off": "available",
    "rebalance_drop_off": "available",
    "maintenance_drop_off": "available",
    "user_pick_up": "reserved",
    "maintenance": "unavailable",
    "low_battery": "unavailable",
    "service_end": "removed",
    "rebalance_pick_up": "removed",
    "maintenance_pick_up": "removed",
}


@pytest.mark.django_db
def test_poll_provider_batch(client):
    """A single provider with two pages of status changes."""
    provider = factories.Provider()
    # The first device received already exists
    device1 = factories.Device(provider=provider, dn_status="available")
    expected_event1 = factories.EventRecord.build(
        event_type=enums.EVENT_TYPE.service_start.name,
        properties__trip_id="e7a9d3aa-68ea-4666-8adf-7bad40e49805",
    )
    # The second device received is unknown
    expected_device2 = factories.Device.build(dn_status="removed")
    expected_event2 = factories.EventRecord.build(
        event_type=enums.EVENT_TYPE.trip_end.name
    )
    stdout, stderr = io.StringIO(), io.StringIO()

    with requests_mock.Mocker() as m:
        url = urllib.parse.urljoin(provider.base_api_url, "/status_changes")
        next_page = "%s?page=2" % url
        m.get(
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
        m.get(
            next_page,
            json=make_response(
                provider,
                expected_device2,
                expected_event2,
                event_type_reason="maintenance_pick_up",
            ),
        )
        call_command("poll_providers", stdout=stdout, stderr=stderr)

    assert_command_success(stdout, stderr)

    event1 = device1.event_records.get()
    assert_event_equal(event1, expected_event1)

    # The second device was created on the fly
    assert "Devices created: %s" % expected_device2.pk in stdout.getvalue()
    device2 = models.Device.objects.get(pk=expected_device2.pk)
    event2 = device2.event_records.get()

    assert_event_equal(event2, expected_event2)
    assert_device_equal(device2, expected_device2)


@pytest.mark.django_db
def test_several_providers(client, django_assert_num_queries):
    """Two providers this time."""
    provider1 = factories.Provider(base_api_url="http://provider1")
    device1 = factories.Device(provider=provider1)
    expected_event1 = factories.EventRecord.build(
        event_type=enums.EVENT_TYPE.rebalance_drop_off.name
    )
    provider2 = factories.Provider(base_api_url="http://provider2")
    device2 = factories.Device(provider=provider2)
    expected_event2 = factories.EventRecord.build(
        event_type=enums.EVENT_TYPE.trip_start.name
    )
    stdout, stderr = io.StringIO(), io.StringIO()

    n = 1  # List of provider IDs
    n += 1  # List of device IDs
    n += 1  # List of providers
    n += (
        2  # Savepoint/release for each provider
        + 1  # Insert missing devices
        + 1  # Insert missing event records
        + 1  # Update last start time polled
    ) * 2  # For each provider
    with django_assert_num_queries(n):
        with requests_mock.Mocker() as m:
            m.get(
                urllib.parse.urljoin(provider1.base_api_url, "/status_changes"),
                json=make_response(
                    provider1,
                    device1,
                    expected_event1,
                    event_type_reason="rebalance_drop_off",
                ),
            )
            m.get(
                urllib.parse.urljoin(provider2.base_api_url, "/status_changes"),
                json=make_response(
                    provider2, device2, expected_event2, event_type_reason="maintenance"
                ),
            )
            call_command("poll_providers", stdout=stdout, stderr=stderr)

    assert_command_success(stdout, stderr)

    event1 = device1.event_records.get()
    assert_event_equal(event1, expected_event1)
    event2 = device2.event_records.get()
    assert_event_equal(event2, expected_event2)


@pytest.mark.django_db
def test_follow_up(client):
    """Catching up new telemetries from the last one we got."""
    event = factories.EventRecord()
    device = event.device
    provider = device.provider
    provider.last_start_time_polled = event.timestamp
    provider.save()
    expected_event = factories.EventRecord.build(
        event_type=enums.EVENT_TYPE.service_end.name, timestamp=timezone.now()
    )
    stdout, stderr = io.StringIO(), io.StringIO()

    with requests_mock.Mocker() as m:
        # Mocking must fail if the command does not make the expected query
        m.get(
            urllib.parse.urljoin(provider.base_api_url, "/status_changes"),
            status_code=400,
        )
        m.get(
            urllib.parse.urljoin(
                provider.base_api_url,
                "/status_changes?%s"
                % urllib.parse.urlencode(
                    {"start_time": int(event.timestamp.timestamp() * 1000)}
                ),
            ),
            json=make_response(
                provider, device, expected_event, event_type_reason="service_end"
            ),
        )
        call_command("poll_providers", stdout=stdout, stderr=stderr)

    assert_command_success(stdout, stderr)

    assert device.event_records.count() == 2
    event = device.event_records.latest("timestamp")
    assert_event_equal(event, expected_event)


def make_response(
    provider, device, event, event_type_reason, associated_trip=None, next_page=None
):
    assert (
        event.event_type
        in dict(enums.PROVIDER_EVENT_TYPE_REASON_TO_AGENCY_EVENT_TYPE).values()
    )
    telemetry = event.properties["telemetry"]

    response = factories.ProviderStatusChangesBody(
        data__status_changes=[
            factories.ProviderStatusChange(
                provider_id=str(provider.pk),
                provider_name=provider.name,
                device_id=str(device.pk),
                vehicle_id=device.identification_number,
                vehicle_type=device.category,
                event_type=PROVIDER_EVENT_TYPES[event_type_reason],
                event_type_reason=event_type_reason,
                propulsion_type=device.propulsion,
                event_time=int(event.timestamp.timestamp() * 1000),  # In ms
                event_location__properties__timestamp=telemetry["timestamp"],
                event_location__geometry__coordinates=[
                    telemetry["gps"]["lng"],
                    telemetry["gps"]["lat"],
                ],
                associated_trip=associated_trip,
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
    assert device.dn_status == expected_device.dn_status


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
