from django.conf import settings

from cryptography import fernet


POLLER_TOKEN_CACHE = getattr(settings, "POLLER_TOKEN_CACHE", "default")
POLLER_TOKEN_ENCRYPTION_KEY = getattr(
    settings,
    "POLLER_TOKEN_ENCRYPTION_KEY",
    fernet.Fernet.generate_key(),  # The default is reset on each restart
)
