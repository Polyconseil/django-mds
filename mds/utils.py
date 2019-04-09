import datetime
import json
import random
import types

from django.contrib.gis.geos.point import Point
from django.db import connection
from rest_framework.utils import encoders


def to_mds_timestamp(dt: datetime.datetime) -> int:
    """
    Convert a datetime object into an MDS-compliant timestamp.

    MDS wants the timestamp to be in milliseconds.
    """
    return round(dt.timestamp() * 1000)


def from_mds_timestamp(value: int) -> datetime:
    """Convert an MDS timestamp (in milliseconds) to a datetime object."""
    return datetime.datetime.fromtimestamp(value / 1000, tz=datetime.timezone.utc)


def get_random_point(polygon):
    """Return a random point in the given polygon."""
    (x_min, y_min), (x_max, _), (_, y_max) = polygon.envelope[0][:3]
    while True:
        point = Point(random.uniform(x_min, x_max), random.uniform(y_min, y_max))
        if polygon.contains(point):
            return point


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
