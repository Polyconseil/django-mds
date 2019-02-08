import datetime
from typing import List

from django.apps import apps
from django.core.cache import cache
from django.utils import timezone


from mds.authent import models, generators


class MDSAuthentException(Exception):
    pass


class NoApplicationForOwner(MDSAuthentException):
    pass


class UnknownToken(MDSAuthentException):
    pass


def get_long_lived_token(owner, duration):
    application = models.Application.objects.filter(owner=owner).last()
    if not application:
        raise NoApplicationForOwner()

    token_duration = datetime.timedelta(seconds=duration)
    token = generators.generate_jwt(application, token_duration, save=True)
    return token


def revoke_long_lived_token(token):
    token_qs = models.AccessToken.objects.filter(token=token)
    stored_token = token_qs.last()
    if not stored_token:
        raise UnknownToken()

    if not stored_token.revoked_after:
        _revoke_tokens(token_qs)
    return stored_token.revoked_after


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

    token_ids = [
        str(t)
        for t in models.AccessToken.objects.filter(
            revoked_after__lt=timezone.now()
        ).values_list("jti", flat=True)
    ]
    cache.set(cache_key, token_ids, timeout=60)  # seconds
    return token_ids


def create_application(name, owner=None, grant=None, scopes=None):
    grant = grant or models.Application.GRANT_CLIENT_CREDENTIALS
    app, created = models.Application.objects.get_or_create(
        name=name,
        client_type=models.Application.CLIENT_CONFIDENTIAL,
        authorization_grant_type=grant,
        scopes=scopes,
        owner=owner,
    )
    return {
        "name": name,
        "client_id": app.client_id,
        "client_secret": app.client_secret,
        "client_type": models.Application.CLIENT_CONFIDENTIAL,
        "grant_type": grant,
        "scopes": scopes,
        "created": created,
    }


def revoke_application(owner_id):
    app_qs = models.Application.objects.filter(owner=owner_id)
    updated = app_qs.update(scopes=[])
    if not updated:
        raise NoApplicationForOwner()
    _revoke_tokens(
        models.AccessToken.objects.filter(
            application_id__in=app_qs.values_list("id", flat=True)
        )
    )


def delete_application(owner_id):
    deleted, _ = models.Application.objects.filter(owner=owner_id).delete()
    if not deleted:
        raise NoApplicationForOwner()


def _revoke_tokens(token_qs):
    token_qs.update(revoked_after=timezone.now())
