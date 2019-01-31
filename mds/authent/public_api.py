import datetime
from typing import List

from django.apps import apps
from django.core.cache import cache
from django.utils import timezone


from mds.authent import models, generators


def get_long_lived_token(application, duration):
    token_duration = datetime.timedelta(seconds=duration)

    token = generators.generate_jwt(application, token_duration, save=True)
    return token


def revoke_long_lived_token(token):
    stored_token = models.AccessToken.objects.filter(token=token).last()

    if stored_token:
        stored_token.revoked_after = timezone.now()
        stored_token.save()


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


def create_application(name, owner=None, user=None, grant=None, scopes=None):
    grant = grant or models.Application.GRANT_CLIENT_CREDENTIALS
    return models.Application.objects.create(
        name=name,
        redirect_uris="http://example.com",
        client_type=models.Application.CLIENT_CONFIDENTIAL,
        authorization_grant_type=grant,
        scopes=scopes,
        user=user,
        owner=owner,
    )


def revoke_application(owner_id):
    models.Application.objects.filter(owner=owner_id).update(scopes=[])


def delete_application(owner_id):
    models.Application.objects.filter(owner=owner_id).delete()
