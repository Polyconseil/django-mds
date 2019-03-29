import datetime
import uuid

import pytest

from mds import factories
from mds import models
from mds.access_control.scopes import SCOPE_PRV_API
from tests.auth_helpers import auth_header, BASE_NUM_QUERIES


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
        dn_gps_point="Point(40 15.0)",
        dn_gps_timestamp=today,
        dn_battery_pct=0.5,
    )
    factories.Device(
        id=uuid2,
        provider=provider2,
        identification_number="3CCCCC",
        model="Testa_Model_X",
        category="scooter",
        propulsion=["electric"],
        registration_date=today,
        dn_status="unavailable",
        dn_gps_point=None,
        dn_gps_timestamp=None,
        dn_battery_pct=None,
    )

    # Add some telemetries on the first device
    factories.EventRecord(device=device, saved_at=today, event_type="reserve")
    factories.EventRecord.create_batch(
        3, device=device, saved_at=today - datetime.timedelta(seconds=10)
    )

    expected_device = {
        "id": uuid1,
        "provider_id": str(provider.id),
        "provider_name": "Test provider",
        "identification_number": "1AAAAA",
        "model": "Testa_Model_S",
        "status": "available",
        "category": "car",
        "propulsion": ["combustion"],
        "position": {"type": "Point", "coordinates": [40, 15.0]},
        "last_telemetry_date": "2012-01-01T00:00:00Z",
        "registration_date": "2012-01-01T00:00:00Z",
        "battery": 0.5,
    }
    expected_device2 = {
        "id": uuid2,
        "provider_id": str(provider2.id),
        "provider_name": "Test another provider",
        "identification_number": "3CCCCC",
        "model": "Testa_Model_X",
        "status": "unavailable",
        "category": "scooter",
        "propulsion": ["electric"],
        "last_telemetry_date": None,
        "position": None,
        "registration_date": "2012-01-01T00:00:00Z",
        "battery": None,
    }
    # test auth
    response = client.get("/prv/vehicles/")
    assert response.status_code == 401

    n = BASE_NUM_QUERIES
    n += 1  # query on devices
    n += 1  # count on devices
    with django_assert_num_queries(n):
        response = client.get(
            "/prv/vehicles/", **auth_header(SCOPE_PRV_API, provider_id=provider.id)
        )
    assert response.status_code == 200
    data = response.data["results"]
    assert len(data) == 2

    assert expected_device in data
    assert expected_device2 in data

    # test auth
    response = client.get("/prv/vehicles/%s/" % device.id)
    assert response.status_code == 401

    n = BASE_NUM_QUERIES
    n += 1  # query on devices
    n += 1  # query to get areas of device
    expected_device["areas"] = []
    expected_device["provider_logo"] = None

    with django_assert_num_queries(n):
        response = client.get(
            "/prv/vehicles/%s/" % device.id,
            **auth_header(SCOPE_PRV_API, provider_id=provider.id),
        )
    assert response.status_code == 200
    assert response.data == expected_device


@pytest.mark.django_db
def test_device_list_filters(client, django_assert_num_queries):
    factories.Device.create_batch(3, category="car", dn_status="available")
    factories.Device.create_batch(3, category="scooter", dn_status="unavailable")
    factories.Device.create_batch(3, category="bicycle", dn_status="unavailable")

    response = client.get("/prv/vehicles/?category=car", **auth_header(SCOPE_PRV_API))
    assert response.status_code == 200
    assert len(response.data["results"]) == 3

    response = client.get(
        "/prv/vehicles/?category=car,scooter", **auth_header(SCOPE_PRV_API)
    )
    assert response.status_code == 200
    assert len(response.data["results"]) == 6

    response = client.get(
        "/prv/vehicles/?status=available", **auth_header(SCOPE_PRV_API)
    )
    assert response.status_code == 200
    assert len(response.data["results"]) == 3

    response = client.get(
        "/prv/vehicles/?status=available,unavailable", **auth_header(SCOPE_PRV_API)
    )
    assert response.status_code == 200
    assert len(response.data["results"]) == 9

    response = client.get(
        "/prv/vehicles/?status=available,unavailable&category=car",
        **auth_header(SCOPE_PRV_API),
    )
    assert response.status_code == 200
    assert len(response.data["results"]) == 3

    provider = str(models.Device.objects.filter(category="car").first().provider_id)
    response = client.get(
        "/prv/vehicles/?provider=%s,%s" % (provider, str(uuid.uuid4())),
        **auth_header(SCOPE_PRV_API),
    )
    assert response.status_code == 200
    assert (
        len(response.data["results"])
        == models.Device.objects.filter(provider_id=provider).count()
    )

    response = client.get(
        "/prv/vehicles/?category=car&status=available&provider=%s,%s"
        % (provider, str(uuid.uuid4())),
        **auth_header(SCOPE_PRV_API),
    )
    assert response.status_code == 200
    assert (
        len(response.data["results"])
        == models.Device.objects.filter(
            category="car", dn_status="available", provider_id=provider
        ).count()
    )

    response = client.get(
        "/prv/vehicles/?category=car&status=unavailable&provider=%s,%s"
        % (provider, str(uuid.uuid4())),
        **auth_header(SCOPE_PRV_API),
    )
    assert response.status_code == 200
    assert len(response.data["results"]) == 0
