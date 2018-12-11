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
