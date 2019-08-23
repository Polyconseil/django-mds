import pytest
import uuid

from importlib import import_module
from django.test import TestCase
from django.apps import apps
from django.db import connection
from django.utils import timezone
from mds.models import EventRecord
from mds import enums, factories


data_migration = import_module("mds.migrations.0041_map_old_to_new_event_records")


mapping = [
    ("rebalance_drop_off", ("provider_drop_off", None)),  # 1
    ("maintenance_drop_off", ("provider_drop_off", "maintenance")),  # 2
    ("maintenance", ("service_end", "maintenance")),  # 3
    ("low_battery", ("service_end", "low_battery")),  # 4
    ("service_end", ("provider_pick_up", None)),  # 5
    ("rebalance_pick_up", ("provider_pick_up", "rebalance")),  # 6
    ("maintenance_pick_up", ("provider_pick_up", "maintenance")),  # 7
    ("agency_pick_up", ("city_pick_up", None)),  # 8
    ("service_start", ("service_start", None)),  # 9
    ("register", ("register", None)),  # 10
    ("deregister", ("deregister", None)),  # 11
    ("trip_end", ("trip_end", None)),  # 12
    ("trip_start", ("trip_start", None)),  # 13
    ("trip_enter", ("trip_enter", None)),  # 14
    ("trip_leave", ("trip_leave", None)),  # 15
    ("battery_charged", ("battery_charged", None)),  # 16
    ("telemetry", ("telemetry", None)),  # 17
    ("reserve", ("reserve", None)),  # 18
    ("cancel_reservation", ("cancel_reservation", None)),  # 19
]


class DataMigrationTests(TestCase):
    @pytest.mark.django_db
    def test_forward(self):
        now = timezone.now()
        uuid1 = uuid.UUID("aaaaaaa1-1342-413b-8e89-db802b2f83f6")
        provider = factories.Provider(name="Test provider")
        device = factories.Device(
            id=uuid1,
            provider=provider,
            identification_number="1AAAAA",
            model="Testa_Model_S",
            category="car",
            propulsion=["combustion"],
            registration_date=now,
            dn_status="available",
        )

        for i, obj in enumerate(mapping):
            event_type, _ = obj
            for _ in range(i + 1):
                now = timezone.now()
                factories.EventRecord(
                    device=device, saved_at=now, event_type=event_type, timestamp=now
                )

        assert EventRecord.objects.count() == len(mapping) * (len(mapping) + 1) / 2

        # Forward migration
        data_migration.fill_event_type_and_reason(apps, connection.schema_editor())

        for i, obj in enumerate(mapping):
            _, agency_event = obj
            count_event = (
                EventRecord.objects.filter(
                    event_type=agency_event[0], event_type_reason=agency_event[1]
                ).count()
                if agency_event[1]
                else EventRecord.objects.filter(
                    event_type=agency_event[0], event_type_reason__isnull=True
                ).count()
            )
            assert count_event == i + 1

    @pytest.mark.django_db
    def test_backward(self):
        now = timezone.now()
        uuid1 = uuid.UUID("aaaaaaa1-1342-413b-8e89-db802b2f83f6")
        provider = factories.Provider(name="Test provider")
        device = factories.Device(
            id=uuid1,
            provider=provider,
            identification_number="1AAAAA",
            model="Testa_Model_S",
            category="car",
            propulsion=["combustion"],
            registration_date=now,
            dn_status="available",
        )

        for i, obj in enumerate(mapping):
            _, event = obj
            event_type, event_type_reason = event
            for _ in range(i + 1):
                now = timezone.now()
                factories.EventRecord(
                    device=device,
                    saved_at=now,
                    event_type=event_type,
                    event_type_reason=event_type_reason,
                    timestamp=now,
                )

        assert EventRecord.objects.count() == len(mapping) * (len(mapping) + 1) / 2

        # Backward migration
        data_migration.reverse_fill_event_type_and_reason(
            apps, connection.schema_editor()
        )

        for i, obj in enumerate(mapping):
            event_type, _ = obj
            count_event = EventRecord.objects.filter(event_type=event_type).count()
            assert count_event == i + 1

