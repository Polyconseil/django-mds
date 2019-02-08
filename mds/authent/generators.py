from collections import namedtuple
import datetime
import uuid

from django.utils import timezone
import jwt

from . import models
from . import settings


AuthMean = namedtuple("AuthMean", ("key", "algorithm"))


def generate_jwt_with_payload(application, token_duration, user=None):
    payload = _generate_payload(application, token_duration, user=user)
    return _generate_jwt(payload), payload


def generate_jwt(application, token_duration, save=False):
    token, payload = generate_jwt_with_payload(application, token_duration)
    if save:
        models.AccessToken.objects.create(
            token=token,
            jti=payload["jti"],
            application=application,
            expires=datetime.datetime.fromtimestamp(
                payload["exp"], tz=timezone.now().tzinfo
            ),
        )
    return token


def _generate_jwt(payload):
    auth_mean = _get_auth_mean()
    # returns a string because it needs to be JSON serializable by oauthlib
    return jwt.encode(payload, auth_mean.key, algorithm=auth_mean.algorithm).decode(
        "utf-8"
    )


def _get_auth_mean():
    if settings.AUTHENT_RSA_PRIVATE_KEY:
        return AuthMean(settings.AUTHENT_RSA_PRIVATE_KEY, "RS256")
    return AuthMean(settings.AUTHENT_SECRET_KEY, "HS256")


def _generate_payload(application, token_duration, user):
    payload = {"jti": str(uuid.uuid4()), "scope": application.scopes_string}
    if user:
        payload["sub"] = "user:%s" % user.username
        payload["name"] = user.get_full_name() or user.username
    else:
        payload["sub"] = ("application:%s" % application.client_id,)
    if application.owner:
        payload["app_owner"] = str(application.owner)
    if token_duration:
        expiry = timezone.now() + token_duration
        payload["exp"] = int(expiry.timestamp())

    return payload
