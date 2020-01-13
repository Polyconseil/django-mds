from django.conf import settings  # noqa

from appconf import AppConf
from cryptography import fernet


class MdsConf(AppConf):
    POLLER_TOKEN_CACHE = "default"
    # The default is reset on each restart
    POLLER_TOKEN_ENCRYPTION_KEY = fernet.Fernet.generate_key()

    POLLER_CREATE_REGISTER_EVENTS = False

    # May be set to None in order to pull all provider history
    PROVIDER_POLLER_LIMIT_DAYS = 90

    class Meta:
        prefix = ""  # No magical prefix
