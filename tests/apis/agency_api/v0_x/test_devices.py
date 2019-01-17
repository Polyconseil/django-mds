import datetime

import pytest

from mds import factories
from mds import models
from mds.access_control.scopes import SCOPE_VEHICLE
from tests.auth_helper import auth_header


@pytest.mark.django_db
def test_devices_metadata(client, django_assert_num_queries):
    provider = factories.Provider(name="Test provider")
    response = client.options(
        "/mds/v0.x/vehicles/", **auth_header(SCOPE_VEHICLE, provider_id=provider.id)
    )
    assert response.status_code == 200
    assert response._headers["allow"][1] == "GET, POST, HEAD, OPTIONS"


@pytest.mark.django_db
def test_device_list_basic(client, django_assert_num_queries):
    today = datetime.datetime(2012, 1, 1, tzinfo=datetime.timezone.utc)
    uuid1 = "aaaaaaa1-1342-413b-8e89-db802b2f83f6"
    uuid2 = "ccccccc3-1342-413b-8e89-db802b2f83f6"

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
    factories.EventRecord(device=device, saved_at=today, event_type="reserve")
    factories.EventRecord.create_batch(
        3, device=device, saved_at=today - datetime.timedelta(seconds=10)
    )

    expected_device = {
        "device_id": uuid1,
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
        "device_id": uuid2,
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
    response = client.get("/mds/v0.x/vehicles/")
    assert response.status_code == 401
    with django_assert_num_queries(4):
        # 1 query on devices
        # 1 last telemetry for each device
        # 2 savepoints
        response = client.get(
            "/mds/v0.x/vehicles/", **auth_header(SCOPE_VEHICLE, provider_id=provider.id)
        )
    assert response.status_code == 200
    assert len(response.data) == 2

    assert expected_device in response.data
    assert expected_device2 in response.data

    # test auth
    response = client.get("/mds/v0.x/vehicles/%s/" % device.id)
    assert response.status_code == 401
    with django_assert_num_queries(4):
        # 1 query on devices
        # 1 last telemetry for each device
        # 2 savepoints
        response = client.get(
            "/mds/v0.x/vehicles/%s/" % device.id,
            **auth_header(SCOPE_VEHICLE, provider_id=provider.id),
        )
    assert response.status_code == 200
    assert response.data == expected_device

    # cannot access other providers data
    response = client.get(
        "/mds/v0.x/vehicles/%s/" % other_device.id,
        **auth_header(SCOPE_VEHICLE, provider_id=provider.id),
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_device_add(client):
    provider = factories.Provider(id="aaaa0000-61fd-4cce-8113-81af1de90942")
    device_id = "bbbb0000-61fd-4cce-8113-81af1de90942"

    data = {
        "device_id": device_id,
        "vehicle_id": "foo",
        "type": "scooter",
        "propulsion": ["electric"],
        "year": 2012,
        "mfgr": "Toto inc",
        "model": "IDFX 3000",
    }

    assert models.Device.objects.count() == 0
    # test auth
    response = client.post("/mds/v0.x/vehicles/", data=data, content_type="application/json")
    assert response.status_code == 401
    response = client.post(
        "/mds/v0.x/vehicles/",
        data=data,
        content_type="application/json",
        **auth_header(SCOPE_VEHICLE, provider_id=provider.id),
    )
    assert response.status_code == 201
    assert response.data == {}
    assert models.Device.objects.count() == 1


@pytest.mark.django_db
def test_device_event(client):
    provider = factories.Provider(id="aaaa0000-61fd-4cce-8113-81af1de90942")
    device_id = "bbbb0000-61fd-4cce-8113-81af1de90942"
    device = factories.Device(id=device_id, provider=provider)

    data = {
        "event_type": "reserve",
        "telemetry": {
            "device_id": device_id,
            "timestamp": 1_325_376_000_000,
            "gps": {
                "lat": 0.0,
                "lng": 3.0,
                "altitude": 30.0,
                "heading": 245.2,
                "speed": 32.3,
                "accuracy": 2.0,
            },
            "charge": 0.54,
        },
        "trip_id": None,
    }

    # test auth
    assert device.event_records.all().count() == 0
    response = client.post(
        "/mds/v0.x/vehicles/%s/event/" % device_id,
        data=data,
        content_type="application/json",
    )
    assert response.status_code == 401
    response = client.post(
        "/mds/v0.x/vehicles/%s/event/" % device_id,
        data=data,
        content_type="application/json",
        **auth_header(SCOPE_VEHICLE, provider_id=provider.id),
    )
    assert response.status_code == 201
    assert response.data == {}
    assert device.event_records.all().count() == 1


@pytest.mark.django_db
def test_device_telemetry(client, django_assert_num_queries):
    provider = factories.Provider(id="aaaa0000-61fd-4cce-8113-81af1de90942")
    provider2 = factories.Provider(id="aaaa0000-61fd-4cce-8113-81af1de90943")
    device_id = "bbbb0000-61fd-4cce-8113-81af1de9094%s"
    factories.Device(id=device_id % 1, provider=provider)
    factories.Device(id=device_id % 2, provider=provider)

    factories.Device(id=device_id % 3, provider=provider2)

    data = {
        "data": [
            {
                "device_id": device_id % 1,
                "timestamp": 1_325_376_000_000,
                "gps": {
                    "lat": 0.0,
                    "lng": 3.0,
                    "altitude": 30.0,
                    "heading": 245.2,
                    "speed": 32.3,
                    "accuracy": 2.0,
                },
                "charge": 0.54,
            },
            {
                "device_id": device_id % 2,
                "timestamp": 1_325_376_001_000,
                "gps": {
                    "lat": 0.0,
                    "lng": 3.2,
                    "altitude": 30.1,
                    "heading": 245.2,
                    "speed": 32.4,
                    "accuracy": 2.0,
                },
                "charge": 0.58,
            },
        ]
    }
    other_device_data = {
        "device_id": device_id % 3,
        "timestamp": 1_325_376_003_000,
        "gps": {
            "lat": 0.0,
            "lng": 3.2,
            "altitude": 30.1,
            "heading": 245.2,
            "speed": 32.4,
            "accuracy": 2.0,
        },
        "charge": 0.58,
    }

    # test auth
    assert (
        models.EventRecord.objects.filter(
            device_id__in=[device_id % i for i in range(1, 4)]
        ).count()
        == 0
    )
    response = client.post(
        "/mds/v0.x/vehicles/telemetry/", data=data, content_type="application/json"
    )
    assert response.status_code == 401

    # make sure providers can only update their telemetries
    response = client.post(
        "/mds/v0.x/vehicles/telemetry/",
        data={"data": data["data"] + [other_device_data]},
        content_type="application/json",
        **auth_header(SCOPE_VEHICLE, provider_id=provider.id),
    )
    assert response.status_code == 400

    with django_assert_num_queries(4):
        # 1 select devices
        # 1 insert records
        # 2 savepoints
        response = client.post(
            "/mds/v0.x/vehicles/telemetry/",
            data=data,
            content_type="application/json",
            **auth_header(SCOPE_VEHICLE, provider_id=provider.id),
        )
    assert response.status_code == 201
    assert response.data == {}
    assert (
        models.EventRecord.objects.filter(
            event_type="telemetry",
            device_id__in=[device_id % i for i in range(1, 4)],
            source="push",
        ).count()
        == 2
    )
