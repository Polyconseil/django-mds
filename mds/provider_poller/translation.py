"""
Everything related to support older Provider API versions
by translating them to the latest supported version.
"""


def translate_v0_2_to_v0_4(data):
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

    # Now up to date
    return data
