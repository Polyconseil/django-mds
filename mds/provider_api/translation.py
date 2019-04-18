"""
Everything related to support older Provider API versions by translating them to the latest supported version.
"""
from semantic_version import Version


def translate_data(data, version):
    version = Version(version)

    if version >= Version("0.3.0") and version < Version("0.4.0"):
        return data

    if version >= Version("0.2.0"):
        # The only two noticeable changes from our point of view are:
        # - timestamps converted from floating-point seconds to milliseconds;
        # - "trip_ids" now is a single "trip_id"
        for status_change in data["status_changes"]:
            # We were already expecting milliseconds in the 0.2 implementation
            if "." in str(status_change["event_time"]):
                status_change["event_time"] = round(status_change["event_time"] * 1000)
            # Keep only the first (and probably only) trip ID
            associated_trip = status_change.pop("associated_trips", None)
            if associated_trip:
                status_change["associated_trip"] = associated_trip[0]
        return data

    raise NotImplementedError(version)
