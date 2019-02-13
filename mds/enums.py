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
        ("unknown", pgettext_lazy("Device status", "Unknown")),
    ],
)

DEVICE_CATEGORY = enum.Enum(
    "Device category",
    [
        ("bike", pgettext_lazy("Device category", "Bike")),
        ("scooter", pgettext_lazy("Device category", "Scooter")),
        ("car", pgettext_lazy("Device category", "Car")),
    ],
)
DEVICE_PROPULSION = enum.Enum(
    "Device propulsion",
    [
        ("electric", pgettext_lazy("Device propulsion", "Electric")),
        ("combustion", pgettext_lazy("Device propulsion", "Combustion")),
    ],
)

EVENT_TYPE = enum.Enum(
    "Event type",
    [
        ("service_start", pgettext_lazy("Event type", "Service start")),
        ("trip_end", pgettext_lazy("Event type", "Trip end")),
        ("rebalance_drop_off", pgettext_lazy("Event type", "Rebalance drop_off")),
        ("maintenance_drop_off", pgettext_lazy("Event type", "Maintenance drop off")),
        ("cancel_reservation", pgettext_lazy("Event type", "Cancel reservation")),
        ("reserve", pgettext_lazy("Event type", "Reserve")),
        ("trip_start", pgettext_lazy("Event type", "Trip start")),
        ("trip_enter", pgettext_lazy("Event type", "Trip enter")),
        ("trip_leave", pgettext_lazy("Event type", "Trip leave")),
        ("register", pgettext_lazy("Event type", "Register")),
        ("low_battery", pgettext_lazy("Event type", "Low battery")),
        ("maintenance", pgettext_lazy("Event type", "Maintenance")),
        ("service_end", pgettext_lazy("Event type", "Service end")),
        ("rebalance_pick_up", pgettext_lazy("Event type", "Rebalance pick up")),
        ("maintenance_pick_up", pgettext_lazy("Event type", "Maintenance pick up")),
        ("deregister", pgettext_lazy("Event type", "Deregister")),
        # this last event is not in the MDS spec
        ("telemetry", pgettext_lazy("Event type", "Received telemetry")),
        # Also added to fill a hole in the provider API
        ("battery_ok", pgettext_lazy("Event type", "Battery OK")),
    ],
)


EVENT_TYPE_TO_DEVICE_STATUS = {
    EVENT_TYPE.service_start.name: DEVICE_STATUS.available.name,
    EVENT_TYPE.trip_end.name: DEVICE_STATUS.available.name,
    EVENT_TYPE.rebalance_drop_off.name: DEVICE_STATUS.available.name,
    EVENT_TYPE.maintenance_drop_off.name: DEVICE_STATUS.available.name,
    EVENT_TYPE.cancel_reservation.name: DEVICE_STATUS.available.name,
    EVENT_TYPE.reserve.name: DEVICE_STATUS.reserved.name,
    EVENT_TYPE.trip_start.name: DEVICE_STATUS.reserved.name,
    EVENT_TYPE.trip_enter.name: DEVICE_STATUS.reserved.name,
    EVENT_TYPE.trip_leave.name: DEVICE_STATUS.reserved.name,
    EVENT_TYPE.register.name: DEVICE_STATUS.unknown.name,
    EVENT_TYPE.low_battery.name: DEVICE_STATUS.unavailable.name,
    EVENT_TYPE.maintenance.name: DEVICE_STATUS.unavailable.name,
    EVENT_TYPE.service_end.name: DEVICE_STATUS.unavailable.name,
    EVENT_TYPE.rebalance_pick_up.name: DEVICE_STATUS.reserved.name,
    EVENT_TYPE.maintenance_pick_up.name: DEVICE_STATUS.reserved.name,
    EVENT_TYPE.deregister.name: DEVICE_STATUS.unknown.name,
    EVENT_TYPE.telemetry.name: DEVICE_STATUS.unknown.name,
    EVENT_TYPE.battery_ok.name: DEVICE_STATUS.available.name,
}


# The two APIs don't match on names, hopefully temporary
PROVIDER_EVENT_TYPE_REASON_TO_AGENCY_EVENT_TYPE = {
    "service_start": EVENT_TYPE.service_start.name,
    "user_drop_off": EVENT_TYPE.trip_end.name,
    "rebalance_drop_off": EVENT_TYPE.rebalance_drop_off.name,
    "maintenance_drop_off": EVENT_TYPE.maintenance_drop_off.name,
    "user_pick_up": EVENT_TYPE.trip_start.name,
    "maintenance": EVENT_TYPE.maintenance.name,
    "low_battery": EVENT_TYPE.low_battery.name,
    "service_end": EVENT_TYPE.service_end.name,
    "rebalance_pick_up": EVENT_TYPE.rebalance_pick_up.name,
    "maintenance_pick_up": EVENT_TYPE.maintenance_pick_up.name,
    # XXX Added to fill a hole in the provider API
    "battery_ok": EVENT_TYPE.battery_ok.name,
}


EVENT_SOURCE = enum.Enum(
    "Event source",
    [
        # push provider -> agency API
        ("push", pgettext_lazy("Event source", "push")),
        # pull agency <- provider API
        ("pull", pgettext_lazy("Event source", "pull")),
    ],
)
