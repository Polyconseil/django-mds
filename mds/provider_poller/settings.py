from django.conf import settings


# May be set to None in order to pull all provider history
PROVIDER_POLLER_LIMIT_DAYS = getattr(settings, "PROVIDER_POLLER_LIMIT", 90)
