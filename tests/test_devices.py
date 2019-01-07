import uuid

import pytest
from django.contrib.gis.geos.point import Point
from django.utils import timezone

from mds import factories
from mds.access_control.scopes import SCOPE_VEHICLE
from .auth_helper import auth_header

from mds import admin  # noqa: F401


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

    with django_assert_num_queries(5):  # 2 actual queries + 2 savepoints + 1 count
        response = client.get("/vehicle/", **auth_header(SCOPE_VEHICLE))
    assert response.status_code == 200
    assert len(response.data["results"]) == 2

    assert expected_device in response.data["results"]
    assert expected_device2 in response.data["results"]


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

    with django_assert_num_queries(5):  # 2 actual queries + 2 savepoints + 1 count
        response = client.get("/vehicle/", **auth_header(SCOPE_VEHICLE))
    assert response.status_code == 200
    assert len(response.data["results"]) == 1
    for (key, resp_val) in response.data["results"][0].items():
        assert expected[key] == resp_val


@pytest.mark.django_db
def test_device_list_filter(client):
    today = timezone.now()
    yesterday = today - timezone.timedelta(days=1)
    tomorrow = today + timezone.timedelta(days=1)

    device = factories.Device(
        id="aaaa0000-61fd-4cce-8113-81af1de90942",
        category="scooter",
        registration_date=yesterday,
    )
    device2 = factories.Device(
        id="bbbb0000-61fd-4cce-8113-81af1de90942",
        category="scooter",
        registration_date=today,
    )
    device3 = factories.Device(
        id="aaaa1111-61fd-4cce-8113-81af1de90942",
        category="bike",
        registration_date=tomorrow,
    )

    factories.Telemetry(device=device, status="removed")
    factories.Telemetry(device=device2, status="removed")
    factories.Telemetry(device=device3, status="available")

    requests = {
        "/vehicle/?id=aaaa": 2,
        "/vehicle/?category=scooter": 2,
        "/vehicle/?status=removed": 2,
        "/vehicle/?status=available&id=aaaa": 1,
        f"/vehicle/?registrationDateTo={today.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}": 2,
    }
    for req, expected_results in requests.items():
        results = client.get(req, **auth_header(SCOPE_VEHICLE)).data["results"]
        assert len(results) == expected_results


@pytest.mark.django_db
def test_device_add(client):
    client.post(
        "/provider/",
        data={"id": "aaaa0000-61fd-4cce-8113-81af1de90942", "name": "Test provider"},
        content_type="application/json",
    )

    response = client.post(
        "/vehicle/",
        data={
            "id": "bbbb0000-61fd-4cce-8113-81af1de90942",
            "provider": "aaaa0000-61fd-4cce-8113-81af1de90942",
            "category": "scooter",
            "identification_number": "foo",
            "propulsion": "electric",
        },
        content_type="application/json",
        **auth_header(SCOPE_VEHICLE),
    )
    assert response.status_code == 201

    response = client.get("/vehicle/", **auth_header(SCOPE_VEHICLE))
    assert response.status_code == 200
    assert len(response.data["results"]) == 1

    expected_results = {
        "id": "bbbb0000-61fd-4cce-8113-81af1de90942",
        "provider": "Test provider",
        "identification_number": "foo",
        "model": "",
        "status": None,
        "position": None,
        "propulsion": "electric",
        "category": "scooter",
        "last_telemetry_date": None,
    }
    for (key, resp_val) in expected_results.items():
        assert response.data["results"][0][key] == resp_val


@pytest.mark.django_db
def test_device_update(client):
    provider = factories.Provider(
        id="aaaa0000-61fd-4cce-8113-81af1de90942", name="Test provider"
    )
    factories.Device(
        id=uuid.UUID("bbbb0000-61fd-4cce-8113-81af1de90942"),
        provider=provider,
        identification_number="1AAAAA",
        model="",
        category="car",
        propulsion="combustion",
        registration_date=timezone.now(),
    )

    # Full update with POST
    response = client.post(
        "/vehicle/bbbb0000-61fd-4cce-8113-81af1de90942/",
        data={
            "provider": "aaaa0000-61fd-4cce-8113-81af1de90942",
            "category": "scooter",
            "identification_number": "8DDDDD",
            "propulsion": "combustion",
        },
        content_type="application/json",
        **auth_header(SCOPE_VEHICLE),
    )
    assert response.status_code == 200

    response = client.get("/vehicle/", **auth_header(SCOPE_VEHICLE))
    assert len(response.data["results"]) == 1
    expected_results = {
        "id": "bbbb0000-61fd-4cce-8113-81af1de90942",
        "provider": "Test provider",
        "identification_number": "8DDDDD",
        "propulsion": "combustion",
        "category": "scooter",
    }
    for (key, resp_val) in expected_results.items():
        assert response.data["results"][0][key] == resp_val

    # Partial update with PATCH
    response = client.patch(
        "/vehicle/bbbb0000-61fd-4cce-8113-81af1de90942/",
        data={"identification_number": "2BE3"},
        content_type="application/json",
        **auth_header(SCOPE_VEHICLE),
    )
    assert response.status_code == 200

    response = client.get("/vehicle/", **auth_header(SCOPE_VEHICLE))
    assert len(response.data["results"]) == 1
    expected_results = {
        "id": "bbbb0000-61fd-4cce-8113-81af1de90942",
        "provider": "Test provider",
        "identification_number": "2BE3",
        "propulsion": "combustion",
        "category": "scooter",
    }
    for (key, resp_val) in expected_results.items():
        assert response.data["results"][0][key] == resp_val
