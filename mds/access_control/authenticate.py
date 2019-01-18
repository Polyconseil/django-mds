from typing import Set, Optional, List, Dict

import jwt
from django.apps import apps
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import ugettext as _
from rest_framework import exceptions

from .auth_means import BaseAuthMean
from .jwt_decode import jwt_multi_decode
from .scopes import SCOPE_ADMIN


class RemoteUser:
    """
    Inspired by django.contrib.auth.models.AnonymousUser
    """

    _id: str
    _scopes: Set[str] = set()
    _provider_id: Optional[str] = None
    """If provided, restrict access to data owned by given provider"""

    def __init__(self, sub, scopes, provider_id):
        self._id = sub
        self._scopes = scopes
        self._provider_id = provider_id

    def __str__(self):
        return "RemoteUser {}".format(self._id)

    @property
    def is_anonymous(self):
        return False

    @property
    def is_authenticated(self):
        return True

    @property
    def is_staff(self):
        return SCOPE_ADMIN in self._scopes

    @property
    def scopes(self):
        return self._scopes

    @property
    def provider_id(self):
        return self._provider_id


def authenticate(auth_means: List[BaseAuthMean], encoded_jwt: str) -> RemoteUser:
    # Step 1: check and decode token
    try:
        payload, introspect_url = jwt_multi_decode(auth_means, encoded_jwt)
    except jwt.ExpiredSignature:
        msg = _("Signature has expired.")
        raise exceptions.AuthenticationFailed(msg)
    except jwt.DecodeError:
        msg = _("Error decoding signature.")
        raise exceptions.AuthenticationFailed(msg)
    except jwt.InvalidTokenError:
        raise exceptions.AuthenticationFailed()

    # Step 2: optionally check token validity
    if payload.get("jti") in get_revocation_list():
        raise exceptions.AuthenticationFailed(_("Expired or revoked token"))

    # Step 3: build user
    user = build_user(payload)

    return user


def build_user(payload: Dict) -> RemoteUser:
    """
    Returns a user from the JWT payload

    Fields looked-for in the payload:
        * sub (required): identifier for the owner of the token. Could be a human user,
          a provider's server, ...
        * jti (required): identifier for the JWT (make it possible to blacklist
          the token)
        * scope (required): space-delimited permissions
        * provider_id (optional, required for provider): asked for by
          https://github.com/CityOfLosAngeles/mobility-data-specification/tree/dev/agency#authorization
    """
    required_fields = {"sub", "jti", "scope"}
    missing_fields = required_fields - payload.keys()

    if missing_fields:
        msg = _("Invalid payload, missing fields: %(fields)s")
        raise exceptions.AuthenticationFailed(
            msg % {"fields": ", ".join(missing_fields)}
        )

    # See https://tools.ietf.org/html/rfc6749#section-3.3
    scopes = set(payload["scope"].split(" "))

    return RemoteUser(payload["sub"], scopes, payload.get("app_owner", None))


def get_revocation_list() -> List[str]:
    """Get the list of revoked tokens.

    The code below could be replaced by an API call if the authentication
    server and the resource server are split.
    see (https://tools.ietf.org/id/draft-gpujol-oauth-atrl-00.html)
    """
    cache_key = "authent:revocation_list"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        apps.get_app_config("authent")
    except LookupError:
        raise NotImplementedError(
            "Calling this function requires mds.authent in INSTALLED_APPS."
        )

    # Keep the import here, there shouldn't be hard dependencies
    # with mds.authent as the authentication server could very well be split.
    from mds.authent import models

    token_ids = [
        str(t)
        for t in models.AccessToken.objects.filter(
            revoked_after__lt=timezone.now()
        ).values_list("jti", flat=True)
    ]
    cache.set(cache_key, token_ids, timeout=60)  # seconds
    return token_ids
