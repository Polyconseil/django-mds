import datetime

import pytest
from django.utils import timezone

from mds import enums, factories, utils
from mds.access_control.scopes import SCOPE_PRV_API
from tests.auth_helpers import BASE_NUM_QUERIES, auth_header


@pytest.mark.django_db
def test_device_list_basic(client, django_assert_num_queries):
    now = timezone.now()

    uuid1 = "aaaaaaa1-1342-413b-8e89-db802b2f83f6"
    uuid2 = "ccccccc3-1342-413b-8e89-db802b2f83f6"

    provider = factories.Provider(name="Test provider")
    provider2 = factories.Provider(name="Test another provider")

    device1 = factories.Device(
        id=uuid1,
        provider=provider,
        identification_number="1AAAAA",
        model="Testa_Model_S",
        category="car",
        propulsion=["combustion"],
        registration_date=now,
        dn_status="available",
        dn_gps_point="Point(40 15.0)",
        dn_gps_timestamp=now,
        dn_battery_pct=0.5,
    )
    device2 = factories.Device(
        id=uuid2,
        provider=provider2,
        identification_number="3CCCCC",
        model="Testa_Model_X",
        category="scooter",
        propulsion=["electric"],
        registration_date=now,
        dn_status="unavailable",
        dn_gps_point=None,
        dn_gps_timestamp=None,
        dn_battery_pct=None,
    )

    # Add an event on the first device
    factories.EventRecord(
        device=device1,
        timestamp=now,
        event_type=enums.EVENT_TYPE.maintenance.name,
        properties={
            "trip_id": "b3da2d46-065f-4036-903c-49d796f09357",
            "telemetry": {
                "timestamp": 1_325_376_000_000,
                "gps": {"lat": 33.996_339, "lng": -118.48153},
            },
        },
    )
    # A telemetry should not be considered as an event
    factories.EventRecord(
        device=device1,
        timestamp=now - datetime.timedelta(seconds=1),
        event_type=enums.EVENT_TYPE.telemetry.name,
    )
    # This one is too old
    factories.EventRecord(device=device1, timestamp=now - datetime.timedelta(hours=1))

    # Add an event on the second device
    factories.EventRecord(
        device=device2,
        timestamp=now,
        event_type=enums.EVENT_TYPE.trip_start.name,
        properties={
            "trip_id": None,
            "telemetry": {
                "timestamp": 1_325_376_000_000,
                "gps": {"lat": 33.996_339, "lng": -118.48153},
            },
        },
    )

    expected_event_device1 = {
        "provider_id": str(provider.id),
        "provider_name": "Test provider",
        "device_id": uuid1,
        "vehicle_id": "1AAAAA",
        "propulsion_type": ["combustion"],
        "event_type_reason": "maintenance",
        "event_type": "unavailable",
        "vehicle_type": "car",
        "event_time": utils.to_mds_timestamp(now),
        "event_location": {
            "type": "Feature",
            "properties": {"timestamp": 1_325_376_000_000},
            "geometry": {"type": "Point", "coordinates": [-118.48153, 33.996_339]},
        },
        "associated_trip": "b3da2d46-065f-4036-903c-49d796f09357",
    }
    expected_event_device2 = {
        "provider_id": str(provider2.id),
        "provider_name": "Test another provider",
        "device_id": uuid2,
        "vehicle_id": "3CCCCC",
        "propulsion_type": ["electric"],
        "event_type_reason": "trip_start",
        "event_type": "trip",
        "vehicle_type": "scooter",
        "event_time": utils.to_mds_timestamp(now),
        "event_location": {
            "type": "Feature",
            "properties": {"timestamp": 1_325_376_000_000},
            "geometry": {"type": "Point", "coordinates": [-118.48153, 33.996_339]},
        },
        "associated_trip": None,
    }
    # test auth
    response = client.get("/prv/provider_api/status_changes/")
    assert response.status_code == 401

    start_time = utils.to_mds_timestamp(now - datetime.timedelta(minutes=30))
    n = BASE_NUM_QUERIES
    n += 1  # query on events
    n += 1  # count on events
    with django_assert_num_queries(n):
        response = client.get(
            "/prv/provider_api/status_changes/?start_time=%s" % start_time,
            **auth_header(SCOPE_PRV_API, provider_id=provider.id),
        )
    assert response.status_code == 200

    data = response.data["data"]["status_changes"]
    assert len(data) == 2

    assert expected_event_device1 in data
    assert expected_event_device2 in data

    # Test pagination: retrieve only given number of events
    response = client.get(
        "/prv/provider_api/status_changes/?start_time=%s&take=1" % start_time,
        **auth_header(SCOPE_PRV_API, provider_id=provider.id),
    )
    data = response.data["data"]["status_changes"]
    assert len(data) == 1
