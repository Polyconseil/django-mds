import json
import types

from django.db import connection
from rest_framework.utils import encoders


def upsert_providers(providers: types.GeneratorType):
    """
    Using "upsert" to create providers.

    Conflicts are always ignored.
    """

    def serialize(provider):
        provider.clean()
        return {
            "id": provider.id,
            "name": provider.name,
            "device_category": provider.device_category,
        }

    query = """
        INSERT INTO mds_provider (
            id,
            name,
            device_category
        ) VALUES (
            %(id)s,
            %(name)s,
            %(device_category)s
        ) ON CONFLICT DO NOTHING
    """

    with connection.cursor() as cursor:
        cursor.executemany(query, (serialize(provider) for provider in providers))


def upsert_devices(devices: types.GeneratorType):
    """
    Using "upsert" to create devices.

    Conflicts are always ignored.
    """

    def serialize(device):
        device.clean()
        return {
            "id": device.id,
            "provider_id": device.provider_id,
            "registration_date": device.registration_date,
            "identification_number": device.identification_number,
            "category": device.category,
            "model": device.model,
            "propulsion": device.propulsion,
            "manufacturer": device.manufacturer,
            "dn_status": device.dn_status,
        }

    query = """
        INSERT INTO mds_device (
            id,
            provider_id,
            registration_date,
            identification_number,
            category,
            model,
            propulsion,
            manufacturer,
            dn_status
        ) VALUES (
            %(id)s,
            %(provider_id)s,
            %(registration_date)s,
            %(identification_number)s,
            %(category)s,
            %(model)s,
            %(propulsion)s,
            %(manufacturer)s,
            %(dn_status)s
        ) ON CONFLICT DO NOTHING
    """

    with connection.cursor() as cursor:
        cursor.executemany(query, (serialize(device) for device in devices))


def upsert_event_records(
    event_records: types.GeneratorType, source: str, on_conflict_update=False
):
    """
    Using "upsert" to create event or telemetry records.

    Records pushed by providers have precedence over the ones we pull from them.
    So we overwrite any existing record with the same timestamp for a given device.

    Lines will be created or updated with the save time of the transaction.

    Args:
        event_records: list of EventRecord
        source: "push" or "pull"
        on_conflict_update: ignore duplicates (default) or overwrite
    """

    def serialize(event_record):
        event_record.clean()
        return {
            "timestamp": event_record.timestamp,
            "device_id": str(event_record.device_id),
            "point": event_record.point.ewkt if event_record.point else None,
            "event_type": event_record.event_type,
            # The same encoder as in the model
            "properties": json.dumps(event_record.properties, cls=encoders.JSONEncoder),
            "source": source,
        }

    query = """
        INSERT INTO mds_eventrecord (
            device_id,
            timestamp,
            point,
            event_type,
            properties,
            source,
            saved_at
        ) VALUES (
            %(device_id)s,
            %(timestamp)s,
            %(point)s,
            %(event_type)s,
            %(properties)s,
            %(source)s,
            current_timestamp
        )
        """
    if on_conflict_update:
        query += """
            ON CONFLICT (device_id, timestamp) DO UPDATE SET
                point = EXCLUDED.point,
                event_type = EXCLUDED.event_type,
                properties = EXCLUDED.properties,
                source = EXCLUDED.source,
                saved_at = current_timestamp
            """
    else:
        query += """
            ON CONFLICT DO NOTHING
            """

    with connection.cursor() as cursor:
        cursor.executemany(query, (serialize(record) for record in event_records))
