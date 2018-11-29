from django.utils.translation import ugettext_lazy as _


HTTP_METHOD_CHOICES = [("POST", "POST"), ("PUT", "PUT"), ("DELETE", "DELETE")]
DEVICE_STATUS_CHOICES = [
    ("available", _("Available")),
    ("reserved", _("Reserved")),
    ("unavailable", _("Unavailable")),
    ("removed", _("Removed")),
]
