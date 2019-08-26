import enum

from django.utils.translation import pgettext_lazy


def choices(enum):
    """Convert an Enum to a Django-style "choices" iterator.
    """
    return [(member.name, member.value) for member in enum]


DEVICE_STATUS = enum.Enum(
    "Device status",
    [
        ("available", pgettext_lazy("Device status", "Available")),
        ("reserved", pgettext_lazy("Device status", "Reserved")),
        ("unavailable", pgettext_lazy("Device status", "Unavailable")),
        ("removed", pgettext_lazy("Device status", "Removed")),
        ("trip", pgettext_lazy("Device status", "Trip")),
        ("elsewhere", pgettext_lazy("Device status", "Elsewhere")),
        ("inactive", pgettext_lazy("Device status", "Inactive")),
        ("unknown", pgettext_lazy("Device status", "Unknown")),
    ],
)

DEVICE_CATEGORY = enum.Enum(
    "Device category",
    [
        ("bicycle", pgettext_lazy("Device category", "Bicycle")),
        ("scooter", pgettext_lazy("Device category", "Scooter")),
        ("car", pgettext_lazy("Device category", "Car")),
    ],
)
DEVICE_PROPULSION = enum.Enum(
    "Device propulsion",
    [
        ("human", pgettext_lazy("Device propulsion", "Human")),
        ("electric_assist", pgettext_lazy("Device propulsion", "Electric Assist")),
        ("electric", pgettext_lazy("Device propulsion", "Electric")),
        ("combustion", pgettext_lazy("Device propulsion", "Combustion")),
    ],
)

EVENT_TYPE = enum.Enum(
    "Event type",
    [
        # The first events are the one listed in the MDS agency API, in order:
        # https://github.com/CityOfLosAngeles/mobility-data-specification/tree/dev/agency
        ("register", pgettext_lazy("Event type", "Register")),
        ("service_start", pgettext_lazy("Event type", "Service start")),
        ("service_end", pgettext_lazy("Event type", "Service end")),
        ("provider_drop_off", pgettext_lazy("Event type", "Provider drop off")),
        ("provider_pick_up", pgettext_lazy("Event type", "Provider pick up")),
        ("city_pick_up", pgettext_lazy("Event type", "City pick up")),
        ("reserve", pgettext_lazy("Event type", "Reserve")),
        ("cancel_reservation", pgettext_lazy("Event type", "Cancel reservation")),
        ("trip_start", pgettext_lazy("Event type", "Trip start")),
        ("trip_enter", pgettext_lazy("Event type", "Trip enter")),
        ("trip_leave", pgettext_lazy("Event type", "Trip leave")),
        ("trip_end", pgettext_lazy("Event type", "Trip end")),
        ("deregister", pgettext_lazy("Event type", "Deregister")),
        # this last event is in neither of the MDS spec
        ("telemetry", pgettext_lazy("Event type", "Received telemetry")),
        # This may be added in a revision of the agency API specs
        ("battery_charged", pgettext_lazy("Event type", "Battery charged")),
    ],
)


# To make sure we still support the old version of the Agency API
# when we receive events.
OLD_EVENT_TYPE = enum.Enum(
    "Event type",
    [
        ("rebalance_drop_off", pgettext_lazy("Event type", "Rebalance drop off")),
        ("maintenance_drop_off", pgettext_lazy("Event type", "Maintenance drop off")),
        ("low_battery", pgettext_lazy("Event type", "Low battery")),
        ("maintenance", pgettext_lazy("Event type", "Maintenance")),
        ("rebalance_pick_up", pgettext_lazy("Event type", "Rebalance pick up")),
        ("maintenance_pick_up", pgettext_lazy("Event type", "Maintenance pick up")),
    ],
)


# event_type_reason(s) listed in the provider API but not in the agency API
# https://github.com/CityOfLosAngeles/mobility-data-specification/tree/dev/provider
PROVIDER_EVENT_TYPE_REASON = enum.Enum(
    "Provider event type reason",
    [
        # available #
        ("service_start", pgettext_lazy("Event type", "Service start")),
        ("user_drop_off", pgettext_lazy("Event type", "User drop off")),
        ("rebalance_drop_off", pgettext_lazy("Event type", "Rebalance drop off")),
        ("maintenance_drop_off", pgettext_lazy("Event type", "Maintenance drop off")),
        ("agency_drop_off", pgettext_lazy("Event type", "Agency drop off")),
        # reserved #
        ("user_pick_up", pgettext_lazy("Event type", "User pick up")),
        # unavailable #
        ("maintenance", pgettext_lazy("Event type", "Maintenance")),
        ("low_battery", pgettext_lazy("Event type", "Low battery")),
        # removed #
        ("service_end", pgettext_lazy("Event type", "Service end")),
        ("rebalance_pick_up", pgettext_lazy("Event type", "Rebalance pick up")),
        ("maintenance_pick_up", pgettext_lazy("Event type", "Maintenance pick up")),
        ("agency_pick_up", pgettext_lazy("Event type", "Agency pick up")),
        # this last event is in neither of the MDS spec
        ("telemetry", pgettext_lazy("Event type", "Received telemetry")),
        # This may be added in a revision of the agency API specs
        ("battery_charged", pgettext_lazy("Event type", "Battery charged")),
    ],
)

# see: https://github.com/CityOfLosAngeles/mobility-data-specification/tree/dev/agency
EVENT_TYPE_REASON = enum.Enum(
    "Event type reason",
    [
        ("low_battery", pgettext_lazy("Event type reason", "Low battery")),
        ("maintenance", pgettext_lazy("Event type reason", "Maintenance")),
        ("compliance", pgettext_lazy("Event type reason", "Compliance")),
        ("off_hours", pgettext_lazy("Event type reason", "Off hours")),
        ("rebalance", pgettext_lazy("Event type reason", "Rebalance")),
        ("charge", pgettext_lazy("Event type reason", "Charge")),
        ("missing", pgettext_lazy("Event type reason", "Missing")),
        ("decommissioned", pgettext_lazy("Event type reason", "Decommissioned")),
    ],
)

EVENT_SOURCE = enum.Enum(
    "Event source",
    [
        ("agency_api", pgettext_lazy("Event source", "Agency API")),
        ("provider_api", pgettext_lazy("Event source", "Provider API")),
    ],
)

AREA_TYPE = enum.Enum(
    "Area type",
    [
        ("unrestricted", pgettext_lazy("Area type", "Unrestricted")),
        ("restricted", pgettext_lazy("Area type", "Restricted")),
        ("preferred_pick_up", pgettext_lazy("Area type", "Preferred pick up")),
        ("preferred_drop_off", pgettext_lazy("Area type", "Preferred drop off")),
    ],
)

EVENT_TYPE_TO_DEVICE_STATUS = {
    EVENT_TYPE.register.name: DEVICE_STATUS.removed.name,
    EVENT_TYPE.service_start.name: DEVICE_STATUS.available.name,
    EVENT_TYPE.service_end.name: DEVICE_STATUS.unavailable.name,
    EVENT_TYPE.provider_drop_off.name: DEVICE_STATUS.available.name,
    EVENT_TYPE.provider_pick_up.name: DEVICE_STATUS.removed.name,
    EVENT_TYPE.city_pick_up.name: DEVICE_STATUS.removed.name,
    EVENT_TYPE.reserve.name: DEVICE_STATUS.reserved.name,
    EVENT_TYPE.cancel_reservation.name: DEVICE_STATUS.available.name,
    EVENT_TYPE.trip_start.name: DEVICE_STATUS.trip.name,
    EVENT_TYPE.trip_enter.name: DEVICE_STATUS.trip.name,
    EVENT_TYPE.trip_leave.name: DEVICE_STATUS.elsewhere.name,
    EVENT_TYPE.trip_end.name: DEVICE_STATUS.available.name,
    EVENT_TYPE.deregister.name: DEVICE_STATUS.inactive.name,
    # Other events
    EVENT_TYPE.telemetry.name: DEVICE_STATUS.unknown.name,
    EVENT_TYPE.battery_charged.name: DEVICE_STATUS.available.name,
    # Old events
    OLD_EVENT_TYPE.rebalance_drop_off.name: DEVICE_STATUS.available.name,
    OLD_EVENT_TYPE.maintenance_drop_off.name: DEVICE_STATUS.available.name,
    OLD_EVENT_TYPE.low_battery.name: DEVICE_STATUS.unavailable.name,
    OLD_EVENT_TYPE.maintenance.name: DEVICE_STATUS.unavailable.name,
    OLD_EVENT_TYPE.rebalance_pick_up.name: DEVICE_STATUS.removed.name,
    OLD_EVENT_TYPE.maintenance_pick_up.name: DEVICE_STATUS.removed.name,
}
