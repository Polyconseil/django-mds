import datetime

import pytest

from mds import factories
from mds.access_control.scopes import SCOPE_ADMIN
from tests.auth_helper import auth_header


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
    )

    # Add some telemetries on the first device
    factories.EventRecord(device=device, saved_at=today, event_type="reserve")
    factories.EventRecord.create_batch(
        3, device=device, saved_at=today - datetime.timedelta(seconds=10)
    )

    expected_device = {
        "id": uuid1,
        "provider": "Test provider",
        "identification_number": "1AAAAA",
        "model": "Testa_Model_S",
        "status": "available",
        "category": "car",
        "propulsion": ["combustion"],
        "position": {"type": "Point", "coordinates": [40, 15.0]},
        "last_telemetry_date": "2012-01-01T00:00:00Z",
        "registration_date": "2012-01-01T00:00:00Z",
    }
    expected_device2 = {
        "id": uuid2,
        "provider": "Test another provider",
        "identification_number": "3CCCCC",
        "model": "Testa_Model_X",
        "status": "unavailable",
        "category": "scooter",
        "propulsion": ["electric"],
        "last_telemetry_date": None,
        "position": None,
        "registration_date": "2012-01-01T00:00:00Z",
    }
    # test auth
    response = client.get("/prv/vehicles/")
    assert response.status_code == 401
    with django_assert_num_queries(4):
        # 1 query on devices
        # 2 savepoints
        response = client.get(
            "/prv/vehicles/", **auth_header(SCOPE_ADMIN, provider_id=provider.id)
        )
    assert response.status_code == 200
    assert len(response.data) == 2

    assert expected_device in response.data
    assert expected_device2 in response.data

    # test auth
    response = client.get("/prv/vehicles/%s/" % device.id)
    assert response.status_code == 401
    with django_assert_num_queries(3):
        # 1 query on devices
        # 2 savepoints
        response = client.get(
            "/prv/vehicles/%s/" % device.id,
            **auth_header(SCOPE_ADMIN, provider_id=provider.id),
        )
    assert response.status_code == 200
    assert response.data == expected_device
