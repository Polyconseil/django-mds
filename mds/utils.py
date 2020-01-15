import datetime
from functools import lru_cache
import random

from django.conf import settings
from django.contrib.gis.geos.point import Point
from django.utils.module_loading import import_string


def telemetry_is_enabled():
    """Default implementation for the ENABLE_TELEMETRY_FUNCTION setting."""
    return True


def is_telemetry_enabled():
    # Cache using the setting value as a key,
    # to get a different value from a setting override (tests)
    @lru_cache()
    def get_function_from_settings(setting):
        return import_string(setting)

    return get_function_from_settings(settings.ENABLE_TELEMETRY_FUNCTION)()


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
