import base64
import datetime
import json
import uuid
from unittest import mock

from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

import jwt
import pytest

from mds.access_control.auth_means import SecretKeyJwtBaseAuthMean
from mds.authent import generators
from mds.authent import models
from tests.auth_helpers import gen_keys


def _create_application(name, owner=None, user=None, grant=None, scopes=None):
    scopes = scopes or ["toto", "titi"]
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


def _create_user(username, password):
    user = User.objects.create(username=username, email="%s@example.com" % username)
    user.set_password(password)
    user.save()
    return user


@pytest.mark.django_db
@mock.patch(
    "mds.authent.generators._get_auth_mean",
    return_value=generators.AuthMean(key="my-secret", algorithm="HS256"),
)
def test_generate_jwt_with_secret(mocked):
    app = _create_application("My application", owner=uuid.uuid4())
    token = generators.generate_jwt(app, datetime.timedelta(days=365))
    jwt.decode(token, "my-secret", algorithms="HS256")


RSA_PUBLIC_KEY, RSA_PRIVATE_KEY = gen_keys()


@pytest.mark.django_db
@mock.patch(
    "mds.authent.generators._get_auth_mean",
    return_value=generators.AuthMean(key=RSA_PRIVATE_KEY, algorithm="RS256"),
)
def test_generate_jwt_with_rsa(mocked):
    app = _create_application("My application", owner=uuid.uuid4())
    token = generators.generate_jwt(app, datetime.timedelta(days=365))
    jwt.decode(token, RSA_PUBLIC_KEY, algorithms="RS256")


@pytest.mark.django_db
def test_long_lived_token_view_auth(client):
    response = client.post(reverse("mds_prv_api:long_lived_token"))
    assert response.status_code == 401
    assert response["WWW-Authenticate"] == "Bearer"


@pytest.mark.django_db
@mock.patch(
    "mds.authent.generators._get_auth_mean",
    return_value=generators.AuthMean(key="my-secret", algorithm="HS256"),
)
def test_token_views_nominal_path(mocked, client):
    _create_application("My application", owner=uuid.uuid4())
    our_frontend = _create_application(
        "Frontend", grant=models.Application.GRANT_PASSWORD, scopes=["anyscope"]
    )
    _create_user("toto", "titi")

    # Get access token
    basic_auth_headers = {
        "HTTP_AUTHORIZATION": b"Basic %s"
        % base64.b64encode(
            ("%s:%s" % (our_frontend.client_id, our_frontend.client_secret)).encode()
        )
    }
    data = {"grant_type": "password", "username": "toto", "password": "titi"}
    response = client.post(reverse("authent:token"), data, **basic_auth_headers)
    assert response.status_code == 200
    data = json.loads(response.content)
    token = data["access_token"]
    refresh_token = data["refresh_token"]
    auth_mean = mocked.return_value
    token_payload = jwt.decode(token, auth_mean.key, algorithms=auth_mean.algorithm)
    assert list(
        models.AccessToken.objects.get(jti=token_payload["jti"]).scopes.keys()
    ) == ["anyscope"]

    # Get a new token with the refresh token for later
    data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    response = client.post(reverse("authent:token"), data, **basic_auth_headers)
    assert response.status_code == 200
    data = json.loads(response.content)
    token = data["access_token"]
    token_payload = jwt.decode(token, auth_mean.key, algorithms=auth_mean.algorithm)
    assert list(
        models.AccessToken.objects.get(jti=token_payload["jti"]).scopes.keys()
    ) == ["anyscope"]


@pytest.mark.django_db
@mock.patch(
    "mds.authent.generators._get_auth_mean",
    return_value=generators.AuthMean(key="my-secret", algorithm="HS256"),
)
@override_settings(AUTH_MEANS=[SecretKeyJwtBaseAuthMean("my-secret")])
def test_revocation_list(mocked, client):
    our_frontend = _create_application(
        "Frontend", grant=models.Application.GRANT_PASSWORD, scopes=["prv_api"]
    )
    _create_user("toto", "titi")

    # Get access token
    basic_auth_headers = {
        "HTTP_AUTHORIZATION": b"Basic %s"
        % base64.b64encode(
            ("%s:%s" % (our_frontend.client_id, our_frontend.client_secret)).encode()
        )
    }
    data = {"grant_type": "password", "username": "toto", "password": "titi"}
    response = client.post(reverse("authent:token"), data, **basic_auth_headers)
    assert response.status_code == 200
    data = json.loads(response.content)
    token = data["access_token"]

    bearer_headers = {"HTTP_AUTHORIZATION": b"Bearer %s" % token.encode("utf-8")}
    response = client.get("/prv/providers/", **bearer_headers)
    assert response.status_code == 200

    # revoke token
    models.AccessToken.objects.update(revoked_after=timezone.now())
    response = client.get("/prv/providers/", **bearer_headers)
    assert response.status_code == 401
