import uuid
from unittest import mock

import jwt
import pytest

from django.urls import reverse

from mds.access_control.scopes import SCOPE_PRV_API
from mds.authent import generators
import mds.authent.models

from tests.auth_helpers import auth_header
from tests.authent.test_tokens import _create_application


@pytest.mark.django_db
def test_create_delete_application(client):
    url = reverse("private:create_app")

    # test auth
    response = client.post(url)
    assert response.status_code == 401

    response = client.post(url, **auth_header("unknown_scope"))
    assert response.status_code == 403

    assert mds.authent.models.Application.objects.count() == 0

    app_owner = str(uuid.uuid4())
    data = {
        "app_name": "Test App",
        "scopes": ["admin", "others"],
        "app_owner": app_owner,
    }

    response = client.post(
        url, data=data, content_type="application/json", **auth_header(SCOPE_PRV_API)
    )
    assert response.status_code == 200
    assert mds.authent.models.Application.objects.count() == 1

    data = {"app_owner": app_owner, "delete": True}
    response = client.delete(
        url, data=data, content_type="application/json", **auth_header(SCOPE_PRV_API)
    )
    assert response.status_code == 200
    assert mds.authent.models.Application.objects.count() == 0


@pytest.mark.django_db
@mock.patch(
    "mds.authent.generators._get_auth_mean",
    return_value=generators.AuthMean(key="my-secret", algorithm="HS256"),
)
def test_long_lived_token(mocked, client):
    app = _create_application("My application", owner=uuid.uuid4())
    response = client.post(
        reverse("mds_prv_api:long_lived_token"), **auth_header(SCOPE_PRV_API)
    )
    assert response.status_code == 400
    assert set(response.data.keys()) == {"app_owner", "token_duration"}

    data = {"app_owner": str(app.owner), "token_duration": 3600}
    response = client.post(
        reverse("mds_prv_api:long_lived_token"),
        data=data,
        content_type="application/json",
        **auth_header(SCOPE_PRV_API),
    )
    assert response.status_code == 200
    auth_mean = mocked.return_value
    data = response.data
    jwt_token = jwt.decode(
        data.pop("access_token"), auth_mean.key, algorithms=auth_mean.algorithm
    )
    assert data == {"expires_in": 3600, "token_type": "bearer"}
    assert mds.authent.models.AccessToken.objects.get(jti=jwt_token["jti"])
