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


@pytest.mark.django_db
def test_poll_provider_batch(client):
    """A single provider with two pages of status changes."""
    provider = factories.Provider()
    # The first device received already exists
    device1 = factories.Device(provider=provider)
    expected_event1 = factories.EventRecord.build()
    # The second device received is unknown
    expected_device2 = factories.Device.build()
    expected_event2 = factories.EventRecord.build()
    stdout, stderr = io.StringIO(), io.StringIO()

    with requests_mock.Mocker() as m:
        url = urllib.parse.urljoin(provider.base_api_url, "/status-changes/")
        next_page = "%s?page=2" % url
        m.get(url, json=make_response(provider, device1, expected_event1, next_page))
        m.get(
            next_page, json=make_response(provider, expected_device2, expected_event2)
        )
        call_command("poll_providers", stdout=stdout, stderr=stderr)

    assert_command_success(stdout, stderr)

    event1 = device1.event_records.get()
    assert_event_equal(event1, expected_event1)

    # The second device was created on the fly
    assert "Device %s was created" % expected_device2.pk in stdout.getvalue()
    device2 = models.Device.objects.get(pk=expected_device2.pk)
    assert_device_equal(device2, expected_device2)

    event2 = device2.event_records.get()
    assert_event_equal(event2, expected_event2)


@pytest.mark.django_db
def test_several_providers(client, django_assert_num_queries):
    """Two providers this time."""
    provider1 = factories.Provider(base_api_url="http://provider1")
    device1 = factories.Device(provider=provider1)
    expected_event1 = factories.EventRecord.build()
    provider2 = factories.Provider(base_api_url="http://provider2")
    device2 = factories.Device(provider=provider2)
    expected_event2 = factories.EventRecord.build()
    stdout, stderr = io.StringIO(), io.StringIO()

    n = 1  # List of providers
    n += (
        2  # Savepoint/release for each provider
        + 1  # Max timestamp for each provider
        + 1  # Does each device exist?
        + 1  # Does each event record exist?
        + 3  # Savepoint/insert/release for each record
    ) * 2  # For each provider
    with django_assert_num_queries(n):
        with requests_mock.Mocker() as m:
            m.get(
                urllib.parse.urljoin(provider1.base_api_url, "/status-changes/"),
                json=make_response(provider1, device1, expected_event1),
            )
            m.get(
                urllib.parse.urljoin(provider2.base_api_url, "/status-changes/"),
                json=make_response(provider2, device2, expected_event2),
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
    expected_event = factories.EventRecord.build(timestamp=timezone.now())
    stdout, stderr = io.StringIO(), io.StringIO()

    with requests_mock.Mocker() as m:
        # Mocking must fail if the command does not make the expected query
        m.get(
            urllib.parse.urljoin(provider.base_api_url, "/status-changes/"),
            status_code=400,
        )
        m.get(
            urllib.parse.urljoin(
                provider.base_api_url,
                "/status-changes/?%s"
                % urllib.parse.urlencode(
                    {"start_time": int(event.timestamp.timestamp() * 1000)}
                ),
            ),
            json=make_response(provider, device, expected_event),
        )
        call_command("poll_providers", stdout=stdout, stderr=stderr)

    assert_command_success(stdout, stderr)

    assert device.event_records.count() == 2
    event = device.event_records.latest("timestamp")
    assert_event_equal(event, expected_event)


def make_response(provider, device, event, next_page=None):
    telemetry = event.properties["telemetry"]

    response = factories.ProviderStatusChangesBody(
        data__status_changes=[
            factories.ProviderStatusChange(
                provider_id=str(provider.pk),
                provider_name=provider.name,
                device_id=str(device.pk),
                vehicle_id=device.identification_number,
                vehicle_type=device.category,
                propulsion_type=device.propulsion,
                event_time=int(event.timestamp.timestamp() * 1000),  # In ms
                event_type=enums.EVENT_TYPE_TO_DEVICE_STATUS[event.event_type],
                event_type_reason=event.event_type,
                event_location__properties__timestamp=telemetry["timestamp"],
                event_location__geometry__coordinates=[
                    telemetry["gps"]["lng"],
                    telemetry["gps"]["lat"],
                ],
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
    assert event.event_type == expected_event.event_type
    assert event.properties == expected_event.properties
