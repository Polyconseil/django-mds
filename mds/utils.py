import datetime
import random

from django.contrib.gis.geos.point import Point


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
