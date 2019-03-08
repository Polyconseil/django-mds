import datetime


def to_mds_timestamp(dt: datetime.datetime) -> int:
    """Convert a datetime object into an MDS-compliant timestamp.

    MDS wants the timestamp to be in milliseconds.
    """
    return round(dt.timestamp() * 1000)


def from_mds_timestamp(value: int) -> datetime:
    """Convert an MDS timestamp (in milliseconds) to a datetime object."""
    return datetime.datetime.fromtimestamp(value / 1000, tz=datetime.timezone.utc)
