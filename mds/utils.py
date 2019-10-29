import datetime
import importlib
import random

from django.conf import settings
from django.contrib.gis.geos.point import Point

from functools import lru_cache


@lru_cache()
def get_object_from_settings(setting):
    """Return an object.

    ``setting`` should be a full Python path,
    e.g. ``mds.utils.telemetry_is_enabled``.
    """
    module_name, obj_name = setting.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, obj_name)


def telemetry_is_enabled():
    """
    This function is imported with `get_object_from_cache`
    from ENABLE_TELEMETRY_FUNCTION in the settings.
    It may easily be overriden to enable/disable the telemetries
    saving through a dynamic setting.
    """
    return True


is_telemetry_enabled = get_object_from_settings(settings.ENABLE_TELEMETRY_FUNCTION)


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
