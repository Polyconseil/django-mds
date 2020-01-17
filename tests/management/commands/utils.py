"""
Utilities
"""
import datetime

from mds import factories
from mds.provider_mapping import (
    PROVIDER_REASON_TO_AGENCY_EVENT,
    PROVIDER_EVENT_TYPE_REASON_TO_EVENT_TYPE,
)


def make_response(
    provider,
    device,
    event,
    event_type_reason,
    associated_trip=None,
    next_page=None,
    version="0.3.0",
):
    assert event.event_type in [
        event_type for event_type, *_ in dict(PROVIDER_REASON_TO_AGENCY_EVENT).values()
    ]
    telemetry = event.properties["telemetry"]

    response = factories.ProviderStatusChangesBody(
        version=version,
        data__status_changes=[
            factories.ProviderStatusChange(
                provider_id=str(provider.pk),
                provider_name=provider.name,
                device_id=str(device.pk),
                vehicle_id=device.identification_number,
                vehicle_type=device.category,
                event_type=PROVIDER_EVENT_TYPE_REASON_TO_EVENT_TYPE[event_type_reason],
                event_type_reason=event_type_reason,
                propulsion_type=device.propulsion,
                event_time=int(event.timestamp.timestamp() * 1000),  # In ms
                event_location__properties__timestamp=telemetry["timestamp"],
                event_location__geometry__coordinates=[
                    telemetry["gps"]["lng"],
                    telemetry["gps"]["lat"],
                ],
                associated_trip=associated_trip,
                recorded=int(event.timestamp.timestamp() * 1000),  # In ms
            )
        ],
        links__next=next_page,
    )
    assert response["data"]["status_changes"][0]["event_location"]["geometry"][
        "coordinates"
    ] == [telemetry["gps"]["lng"], telemetry["gps"]["lat"]]
    return response


def assert_command_success(stdout, stderr):
    assert not stderr.getvalue().strip(), """Command failed!
stdout:
%s
stderr:
%s
""" % (
        stdout.getvalue(),
        stderr.getvalue(),
    )


def assert_device_equal(device, expected_device):
    assert device.category == expected_device.category
    assert device.identification_number == expected_device.identification_number
    if device.model:
        assert device.model == expected_device.model
    assert device.propulsion == expected_device.propulsion


def assert_event_equal(event, expected_event):
    # These are not (yet?) in the provider API
    del expected_event.properties["telemetry"]["gps"]["accuracy"]
    del expected_event.properties["telemetry"]["gps"]["altitude"]
    del expected_event.properties["telemetry"]["gps"]["heading"]
    del expected_event.properties["telemetry"]["gps"]["speed"]
    assert abs(event.timestamp - expected_event.timestamp) < datetime.timedelta(
        seconds=0.001
    )
    assert event.point.json == expected_event.point.json
    assert event.properties == expected_event.properties


def almost_equal(
    datetime1: datetime.datetime,
    datetime2: datetime.datetime,
    precision: datetime.timedelta = datetime.timedelta(milliseconds=1),
) -> bool:
    """Compares two datetimes to be almost equal.

    The default precision matches the MDS specification timestamps in milliseconds
    (when Python datetime objects can be precise to the microsecond).
    """
    return abs(datetime1 - datetime2) < precision
