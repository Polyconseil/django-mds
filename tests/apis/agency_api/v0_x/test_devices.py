import datetime
import uuid

from django.urls import reverse

import pytest

from mds import enums
from mds import factories
from mds import models
from mds.access_control.scopes import SCOPE_AGENCY_API
from tests.auth_helpers import auth_header, BASE_NUM_QUERIES


@pytest.mark.django_db
def test_devices_metadata(client):
    provider = factories.Provider(name="Test provider")
    response = client.options(
        reverse("agency:device-list"),
        **auth_header(SCOPE_AGENCY_API, provider_id=provider.id),
    )
    assert response.status_code == 200
    assert response._headers["allow"][1] == "GET, POST, HEAD, OPTIONS"


@pytest.mark.django_db
def test_device_list_basic(client, django_assert_num_queries):
    today = datetime.datetime(2012, 1, 1, tzinfo=datetime.timezone.utc)
    uuid1 = uuid.UUID("aaaaaaa1-1342-413b-8e89-db802b2f83f6")
    uuid2 = uuid.UUID("ccccccc3-1342-413b-8e89-db802b2f83f6")

    provider = factories.Provider(name="Test provider")
    provider2 = factories.Provider(name="Test another provider")

    device = factories.Device(
        id=uuid1,
        provider=provider,
        identification_number="1AAAAA",
        model="Testa_Model_S",
        category="car",
        propulsion=["combustion"],
        registration_date=today,
        dn_status="available",
    )
    factories.Device(
        id=uuid2,
        provider=provider,
        identification_number="3CCCCC",
        model="Testa_Model_X",
        category="scooter",
        propulsion=["electric"],
        registration_date=today,
        dn_status="available",
    )
    other_device = factories.Device(provider=provider2)

    # Add some telemetries on the first device
    factories.EventRecord(
        device=device,
        saved_at=today - datetime.timedelta(seconds=10),
        timestamp=today - datetime.timedelta(seconds=10),
    )
    # Last event
    factories.EventRecord(
        device=device,
        saved_at=today,
        event_type=enums.EVENT_TYPE.reserve.name,
        timestamp=today,
    )
    # timestamp predates second record, but it was saved afterwards
    factories.EventRecord(
        device=device,
        saved_at=today + datetime.timedelta(seconds=10),
        event_type=enums.EVENT_TYPE.maintenance_drop_off.name,
        timestamp=today - datetime.timedelta(seconds=5),
    )

    expected_device = {
        "device_id": str(uuid1),
        "provider_id": str(provider.id),
        "vehicle_id": "1AAAAA",
        "model": "Testa_Model_S",
        "type": "car",
        "propulsion": ["combustion"],
        "mfgr": "",
        "year": None,
        "status": "available",
        "prev_event": "reserve",
        "updated": 1_325_376_000_000,
    }

    expected_device2 = {
        "device_id": str(uuid2),
        "provider_id": str(provider.id),
        "vehicle_id": "3CCCCC",
        "model": "Testa_Model_X",
        "type": "scooter",
        "propulsion": ["electric"],
        "mfgr": "",
        "year": None,
        "status": "available",
        "prev_event": None,
        "updated": None,
    }

    # test auth
    response = client.get(reverse("agency:device-list"))
    assert response.status_code == 401

    n = BASE_NUM_QUERIES
    n += 1  # query on devices
    n += 1  # query on last telemetry
    with django_assert_num_queries(n):
        response = client.get(
            reverse("agency:device-list"),
            **auth_header(SCOPE_AGENCY_API, provider_id=provider.id),
        )
    assert response.status_code == 200
    assert len(response.data) == 2

    assert expected_device in response.data
    assert expected_device2 in response.data

    # test auth
    response = client.get(reverse("agency:device-detail", args=[device.id]))
    assert response.status_code == 401

    n = BASE_NUM_QUERIES
    n += 1  # query on devices
    n += 1  # query on last telemetry
    with django_assert_num_queries(n):
        response = client.get(
            reverse("agency:device-detail", args=[device.id]),
            **auth_header(SCOPE_AGENCY_API, provider_id=provider.id),
        )
    assert response.status_code == 200
    assert response.data == expected_device

    # cannot access other providers data
    response = client.get(
        reverse("agency:device-detail", args=[other_device.id]),
        **auth_header(SCOPE_AGENCY_API, provider_id=provider.id),
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_device_register(client):
    provider = factories.Provider(id=uuid.UUID("aaaa0000-61fd-4cce-8113-81af1de90942"))
    device_id = uuid.UUID("bbbb0000-61fd-4cce-8113-81af1de90942")

    assert models.Device.objects.count() == 0

    data = {
        "device_id": str(device_id),
        "vehicle_id": "foo",
        "type": "scooter",
        "propulsion": ["electric"],
        "year": 2012,
        "mfgr": "Toto inc",
        "model": "IDFX 3000",
    }

    # Test auth
    response = client.post(
        reverse("agency:device-list"), data=data, content_type="application/json"
    )
    assert response.status_code == 401

    response = client.post(
        reverse("agency:device-list"),
        data=data,
        content_type="application/json",
        **auth_header(SCOPE_AGENCY_API, provider_id=provider.id),
    )
    assert response.status_code == 201
    assert response.data == {}

    device = models.Device.objects.get()  # Also tests unicity
    assert device.provider == provider


@pytest.mark.django_db
def test_device_event(client):
    provider = factories.Provider(id=uuid.UUID("aaaa0000-61fd-4cce-8113-81af1de90942"))
    device_id = uuid.UUID("bbbb0000-61fd-4cce-8113-81af1de90942")
    device = factories.Device(id=device_id, provider=provider)

    data = {
        "event_type": "service_end",
        "telemetry": {
            "device_id": str(device_id),
            "timestamp": 1_325_376_000_000,
            "gps": {
                "lat": 0.0,
                "lng": 3.0,
                "altitude": 30.0,
                "heading": 245.2,
                "speed": 32.3,
                "hdop": 2.0,
                "satellites": 6,
            },
            "charge": 0.54,
        },
        "timestamp": 1_325_376_000_000,
        "trip_id": None,
    }

    # test auth
    assert device.event_records.all().count() == 0
    response = client.post(
        reverse("agency:device-event", args=[device_id]),
        data=data,
        content_type="application/json",
    )
    assert response.status_code == 401

    # test nominal
    response = client.post(
        reverse("agency:device-event", args=[device_id]),
        data=data,
        content_type="application/json",
        **auth_header(SCOPE_AGENCY_API, provider_id=provider.id),
    )
    assert response.status_code == 201
    assert response.data == {"device_id": str(device_id), "status": "removed"}
    assert device.event_records.all().count() == 1


@pytest.mark.django_db
def test_device_event_inverted_coordinates(client):
    provider = factories.Provider(id=uuid.UUID("aaaa0000-61fd-4cce-8113-81af1de90942"))
    device_id = uuid.UUID("bbbb0000-61fd-4cce-8113-81af1de90942")
    device = factories.Device(id=device_id, provider=provider)

    data = {
        "event_type": "service_end",
        "telemetry": {
            "device_id": str(device_id),
            "timestamp": 1_325_376_000_000,
            "gps": {
                "lat": -118.279_678,  # Not within [-90 90]
                "lng": 34.07068,  # This is the latitude
                "altitude": 30.0,
                "heading": 245.2,
                "speed": 32.3,
                "hdop": 2.0,
                "satellites": 6,
            },
            "charge": 0.54,
        },
        "timestamp": 1_325_376_000_000,
        "trip_id": None,
    }

    # test auth
    assert device.event_records.all().count() == 0
    response = client.post(
        reverse("agency:device-event", args=[device_id]),
        data=data,
        content_type="application/json",
        **auth_header(SCOPE_AGENCY_API, provider_id=provider.id),
    )
    assert response.status_code == 400
    assert "Latitude is outside [-90 90]: -118.279678" in str(response.data)

    # Flag the provider
    provider.agency_api_configuration["swap_lat_lng"] = True
    provider.save()

    response = client.post(
        reverse("agency:device-event", args=[device_id]),
        data=data,
        content_type="application/json",
        **auth_header(SCOPE_AGENCY_API, provider_id=provider.id),
    )
    assert response.status_code == 201
    assert response.data == {"device_id": str(device_id), "status": "removed"}
    # Stored as (lng lat) as expected
    assert device.event_records.all()[0].point.wkt == "POINT (-118.279678 34.07068)"


@pytest.mark.django_db
def test_device_telemetry(client, django_assert_num_queries):
    provider = factories.Provider(id=uuid.UUID("aaaa0000-61fd-4cce-8113-81af1de90942"))
    provider2 = factories.Provider(id=uuid.UUID("aaaa0000-61fd-4cce-8113-81af1de90943"))
    device_id_pattern = "bbbb0000-61fd-4cce-8113-81af1de9094%s"
    factories.Device(id=uuid.UUID(device_id_pattern % 1), provider=provider)
    factories.Device(id=uuid.UUID(device_id_pattern % 2), provider=provider)

    factories.Device(id=uuid.UUID(device_id_pattern % 3), provider=provider2)

    data = {
        "data": [
            {
                "device_id": device_id_pattern % 1,
                "timestamp": 1_325_376_000_000,
                "gps": {
                    "lat": 0.0,
                    "lng": 3.0,
                    "altitude": 30.0,
                    "heading": 245.2,
                    "speed": 32.3,
                    "hdop": 2.0,
                    "satellites": 6,
                },
            },
            {
                "device_id": device_id_pattern % 2,
                "timestamp": 1_325_376_001_000,
                "gps": {
                    "lat": 0.0,
                    "lng": 3.2,
                    "altitude": 30.1,
                    "heading": 245.2,
                    "speed": 32.4,
                    "hdop": 2.0,
                    "satellites": 6,
                },
                "charge": 0.58,
            },
        ]
    }
    other_device_data = {
        "device_id": device_id_pattern % 3,
        "timestamp": 1_325_376_003_000,
        "gps": {
            "lat": 0.0,
            "lng": 3.2,
            "altitude": 30.1,
            "heading": 245.2,
            "speed": 32.4,
            "hdop": 2.0,
            "satellites": 6,
        },
        "charge": 0.58,
    }

    # test auth
    assert (
        models.EventRecord.objects.filter(
            device_id__in=[device_id_pattern % i for i in range(1, 4)]
        ).count()
        == 0
    )
    response = client.post(
        reverse("agency:device-telemetry"), data=data, content_type="application/json"
    )
    assert response.status_code == 401

    # make sure providers can only update their telemetries
    response = client.post(
        reverse("agency:device-telemetry"),
        data={"data": data["data"] + [other_device_data]},
        content_type="application/json",
        **auth_header(SCOPE_AGENCY_API, provider_id=provider.id),
    )
    assert response.status_code == 400

    n = BASE_NUM_QUERIES
    n += 1  # select devices
    n += 1  # insert records
    n += 1  # check provider configuration
    with django_assert_num_queries(n):
        response = client.post(
            reverse("agency:device-telemetry"),
            data=data,
            content_type="application/json",
            **auth_header(SCOPE_AGENCY_API, provider_id=provider.id),
        )
    assert response.status_code == 201
    assert response.data == {}
    assert (
        models.EventRecord.objects.filter(
            event_type="telemetry",
            device_id__in=[device_id_pattern % i for i in range(1, 4)],
            source=enums.EVENT_SOURCE.push.name,
        ).count()
        == 2
    )
