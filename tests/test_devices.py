import pytest
import uuid

from django.contrib.gis.geos.point import Point
from django.utils import timezone

from mds import admin  # noqa: F401
from mds import factories


def format_timezone(timezone):
    return timezone.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@pytest.mark.django_db
def test_device_list_basic(client, django_assert_num_queries):
    today = timezone.now()

    provider = factories.Provider(name="Test provider")
    provider2 = factories.Provider(name="Test another provider")

    device = factories.Device(
        id=uuid.UUID("aaaaaaa1-1342-413b-8e89-db802b2f83f6"),
        provider=provider,
        identification_number="1AAAAA",
        model="Testa_Model_S",
        category="car",
        propulsion="combustion",
        registration_date=today,
    )
    factories.Device(
        id=uuid.UUID("ccccccc3-1342-413b-8e89-db802b2f83f6"),
        provider=provider2,
        identification_number="3CCCCC",
        model="Testa_Model_X",
        category="scooter",
        propulsion="electric",
        registration_date=today,
    )

    # Add a telemetry on the first device
    telemetry_properties = {
        "vehicle_state": {
            "speed": 1.0,
            "acceleration": [1.0, 1.0, 1.0],
            "odometer": 5000,
            "driver_present": True,
        },
        "energy": {"cruise_range": 12000, "autonomy": 0.69},
    }
    factories.Telemetry(
        device=device,
        timestamp=today,
        status="available",
        point=Point(40.0, 15.0),
        properties=telemetry_properties,
    )

    expected_device = {
        "id": "aaaaaaa1-1342-413b-8e89-db802b2f83f6",
        "provider": "Test provider",
        "identification_number": "1AAAAA",
        "model": "Testa_Model_S",
        "status": "available",
        "category": "car",
        "propulsion": "combustion",
        "position": {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [40.0, 15.0]},
            "properties": telemetry_properties,
        },
        "last_telemetry_date": format_timezone(today),
        "registration_date": format_timezone(today),
    }
    expected_device2 = {
        "id": "ccccccc3-1342-413b-8e89-db802b2f83f6",
        "provider": "Test another provider",
        "identification_number": "3CCCCC",
        "model": "Testa_Model_X",
        "status": None,
        "category": "scooter",
        "propulsion": "electric",
        "last_telemetry_date": None,
        "position": None,
        "registration_date": format_timezone(today),
    }

    with django_assert_num_queries(4):  # 2 actual queries + 2 savepoints
        response = client.get("/vehicle/")
    assert response.status_code == 200
    assert len(response.data) == 2

    assert expected_device in response.data
    assert expected_device2 in response.data


@pytest.mark.django_db
def test_device_list_multiple_telemetries(client, django_assert_num_queries):
    today = timezone.now()
    yesterday = today - timezone.timedelta(days=1)
    tomorrow = today + timezone.timedelta(days=1)

    provider = factories.Provider(name="Test provider")
    device = factories.Device(
        id=uuid.UUID("ccccccc3-1342-413b-8e89-db802b2f83f6"),
        provider=provider,
        identification_number="3CCCCC",
        model="Testa_Model_X",
        category="scooter",
        propulsion="electric",
        registration_date=today,
    )
    factories.Telemetry(
        device=device,
        timestamp=today,
        status="available",
        point=Point(0.0, 15.0),
        properties={},
    )
    factories.Telemetry(
        device=device,
        timestamp=tomorrow,
        status="removed",
        point=Point(15.0, 15.0),
        properties={},
    )
    factories.Telemetry(
        device=device,
        timestamp=yesterday,
        status="unavailable",
        point=Point(30.0, 15.0),
        properties={},
    )

    expected = {
        "id": "ccccccc3-1342-413b-8e89-db802b2f83f6",
        "provider": "Test provider",
        "identification_number": "3CCCCC",
        "model": "Testa_Model_X",
        "status": "removed",
        "category": "scooter",
        "propulsion": "electric",
        "position": {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [15.0, 15.0]},
            "properties": {},
        },
        "last_telemetry_date": format_timezone(tomorrow),
        "registration_date": format_timezone(today),
    }

    with django_assert_num_queries(4):  # 2 actual queries + 2 savepoints
        response = client.get("/vehicle/")
    assert response.status_code == 200
    assert len(response.data) == 1
    for (key, resp_val) in response.data[0].items():
        assert expected[key] == resp_val


@pytest.mark.skip(reason="Fix devices update behavior")
@pytest.mark.django_db
def test_device(client):
    response = client.put(
        "/vehicle/13b8c961-61fd-4cce-8113-81af1de90942/",
        data={
            "provider": "27e84290-06b4-4c5d-88f2-60e6dcb09712",
            "identification_number": "foo",
            "model": "bar",
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    now = "2018-11-07T15:35:58.108099+02:00"
    utcnow = "2018-11-07T13:35:58.108099Z"
    response = client.post(
        "/vehicle/13b8c961-61fd-4cce-8113-81af1de90942/",
        data={
            "provider": "27e84290-06b4-4c5d-88f2-60e6dcb09712",
            "status": "available",
            "position": {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [2.293117046356201, 48.85829170715186],
                },
                "properties": {"gsm": {"timestamp": now}, "gps": {"timestamp": now}},
            },
        },
        content_type="application/json",
    )
    assert response.status_code == 200
    response = client.get("/vehicle/")
    assert response.status_code == 200
    assert response.data == [
        {
            "id": "13b8c961-61fd-4cce-8113-81af1de90942",
            "provider": "27e84290-06b4-4c5d-88f2-60e6dcb09712",
            "identification_number": "foo",
            "model": "bar",
            "status": "available",
            "position": {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [2.293117046356201, 48.85829170715186],
                },
                "properties": {
                    "gsm": {"timestamp": utcnow, "operator": None, "signal": None},
                    "gps": {
                        "timestamp": utcnow,
                        "accuracy": None,
                        "course": None,
                        "speed": None,
                    },
                },
            },
        }
    ]
