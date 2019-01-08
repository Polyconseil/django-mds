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
    ],
)

EVENT_SOURCE = enum.Enum(
    "Event source",
    [
        # push provider -> agency API
        ("push", pgettext_lazy("Event source", "push")),
        # pull agency <- provider API
        ("pull", pgettext_lazy("Event source", "pull")),
    ],
)
