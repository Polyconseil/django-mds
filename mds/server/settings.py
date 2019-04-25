"""
Django settings
"""
import itertools
import os

from corsheaders.defaults import default_headers
import getconf

from mds.access_control.auth_means import (
    SecretKeyJwtBaseAuthMean,
    PublicKeyJwtBaseAuthMean,
)

CONFIG = getconf.ConfigGetter("mds")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = CONFIG.getstr(
    "django.secret_key", "weak", doc="Secret key for signing data"
)
DEBUG = CONFIG.getbool("dev.debug", False)

ALLOWED_HOSTS = CONFIG.getlist(
    "django.allowed_hosts", [], doc="Comma-separated list of allowed hosts"
)

INSTALLED_APPS = [
    "mds.authent.apps.Config",
    "mds.authent.oauth2_provider_apps.Config",
    "mds.apps.Config",
    "corsheaders",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.postgres",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "drf_yasg",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "corsheaders.middleware.CorsMiddleware",
]
ROOT_URLCONF = "mds.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "mds.server.wsgi.application"
DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": CONFIG.getstr("db.name", "mds"),
        "USER": CONFIG.getstr("db.user", "postgres"),
        "PASSWORD": CONFIG.getstr("db.password"),
        "HOST": CONFIG.getstr("db.host", "127.0.0.1"),
        "PORT": CONFIG.getstr("db.port", "5432"),
        "ATOMIC_REQUESTS": True,
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"}
]
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True
STATIC_URL = "/static/"
LOCALE_PATH = (os.path.join(BASE_DIR, "locale"),)

CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = list(default_headers) + ["cache-control"]

REST_FRAMEWORK = {
    # "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "mds.access_control.stateless_jwt.StatelessJwtAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    )
}
SWAGGER_SETTINGS = {
    "DEFAULT_AUTO_SCHEMA_CLASS": "mds.apis.schema.CustomSwaggerAutoSchema",
    "SECURITY_DEFINITIONS": {
        "Bearer": {"type": "apiKey", "name": "Authorization", "in": "header"}
    },
}

# AUTH_USER_MODEL = None # TODO later

AUTH_MEANS = []
for i in itertools.count(start=1):
    section = "auth" + ("_" + str(i) if i > 1 else "")

    auth_mean = None
    if CONFIG.getstr(section + ".secret_key"):
        auth_mean = SecretKeyJwtBaseAuthMean(CONFIG.getstr(section + ".secret_key"))
    elif CONFIG.getstr(section + ".public_key"):
        # PEM public keys (-----BEGIN PUBLIC KEY-----)
        auth_mean = PublicKeyJwtBaseAuthMean(CONFIG.getstr(section + ".public_key"))
    else:
        break

    # Optional, recommended if handling long-lived access tokens
    # (not a good idea when using JWT)
    if "introspect_url" in section:
        auth_mean.introspect_url = CONFIG.getstr(section + ".introspect_url", None)

    AUTH_MEANS.append(auth_mean)
AUTHENT_SECRET_KEY = "my-secret"
AUTHENT_RSA_PRIVATE_KEY = ""
OAUTH2_PROVIDER = {
    "APPLICATION_MODEL": "authent.Application",
    "ACCESS_TOKEN_MODEL": "authent.AccessToken",
    "GRANT_MODEL": "authent.Grant",
    "REFRESH_TOKEN_MODEL": "authent.RefreshToken",
    "OAUTH2_SERVER_CLASS": "mds.authent.oauthlib_utils.Server",
    "OAUTH2_VALIDATOR_CLASS": "mds.authent.oauthlib_utils.OAuth2Validator",
    "SCOPES_BACKEND_CLASS": "mds.authent.oauthlib_utils.AppScopes",
}
MIGRATION_MODULES = {
    # see https://github.com/jazzband/django-oauth-toolkit/issues/634
    # swappable models are badly designed in oauth2_provider
    # ignore migrations and provide our own models.
    "oauth2_provider": None
}
