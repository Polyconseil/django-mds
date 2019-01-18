from django.utils.translation import ugettext_lazy as _


HTTP_METHOD_CHOICES = [("POST", "POST"), ("PUT", "PUT"), ("DELETE", "DELETE")]
DEVICE_STATUS_CHOICES = [
    ("available", _("Available")),
    ("reserved", _("Reserved")),
    ("unavailable", _("Unavailable")),
    ("removed", _("Removed")),
]
DEVICE_CATEGORY_CHOICES = [
    ("bike", _("Bike")),
    ("scooter", _("Scooter")),
    ("car", _("Car")),
]
DEVICE_PROPULSION_CHOICES = [
    ("electric", _("Electric")),
    ("combustion", _("Combustion")),
]

EVENT_TYPE_CHOICES = [
    ("service_start", _("Service start")),
    ("trip_end", _("Trip end")),
    ("rebalance_drop_off", _("Rebalance drop_off")),
    ("maintenance_drop_off", _("Maintenance drop off")),
    ("cancel_reservation", _("Cancel reservation")),
    ("reserve", _("Reserve")),
    ("trip_start", _("Trip start")),
    ("trip_enter", _("Trip enter")),
    ("trip_leave", _("Trip leave")),
    ("register", _("Register")),
    ("low_battery", _("Low battery")),
    ("maintenance", _("Maintenance")),
    ("service_end", _("Service end")),
    ("rebalance_pick_up", _("Rebalance pick up")),
    ("maintenance_pick_up", _("Maintenance pick up")),
    ("deregister", _("Deregister")),
    # this last event is not in the MDS spec
    ("telemetry", _("Received telemetry")),
]

EVENT_INGESTION_SOURCES = [
    ("push", "push"),  # pushed by the provider
    ("pull", "pull"),  # pulled by agency (e.g. from the provider's API
]
