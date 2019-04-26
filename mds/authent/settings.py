import datetime

from django.conf import settings


AUTHENT_RSA_PRIVATE_KEY = getattr(settings, "AUTHENT_RSA_PRIVATE_KEY", "")
AUTHENT_SECRET_KEY = getattr(settings, "AUTHENT_SECRET_KEY", "")
assert not all([AUTHENT_SECRET_KEY, AUTHENT_RSA_PRIVATE_KEY]), (
    "You must define either settings.AUTHENT_RSA_PRIVATE_KEY "
    "or settings.AUTHENT_SECRET_KEY and not both."
)
AUTHENT_LONG_LIVED_TOKEN_DURATION = getattr(
    settings, "AUTHENT_LONG_LIVED_TOKEN_DURATION", datetime.timedelta(days=365)
)
