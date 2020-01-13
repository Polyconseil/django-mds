import datetime

from django.conf import settings  # noqa

from appconf import AppConf


class AuthentConf(AppConf):
    AUTHENT_RSA_PRIVATE_KEY = ""
    AUTHENT_SECRET_KEY = ""
    AUTHENT_LONG_LIVED_TOKEN_DURATION = datetime.timedelta(days=365)

    class Meta:
        prefix = ""
