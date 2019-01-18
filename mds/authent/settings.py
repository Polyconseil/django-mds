import datetime

from django.conf import settings


AUTHENT_RSA_PRIVATE_KEY = getattr(settings, "AUTHENT_RSA_PRIVATE_KEY", "")
AUTHENT_SECRET_KEY = getattr(settings, "AUTHENT_SECRET_KEY", "")
assert len([x for x in (AUTHENT_SECRET_KEY, AUTHENT_RSA_PRIVATE_KEY) if x]) == 1, (
    "You must define either settings.AUTHENT_RSA_PRIVATE_KEY "
    "or settings.AUTHENT_SECRET_KEY and not both."
)
AUTHENT_LONG_LIVED_TOKEN_DURATION = getattr(
    settings, "AUTHENT_LONG_LIVED_TOKEN_DURATION", datetime.timedelta(days=365)
)
