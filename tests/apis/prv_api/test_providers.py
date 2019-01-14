import pytest
import uuid

from mds import factories
from mds.access_control.scopes import SCOPE_ADMIN, SCOPE_VEHICLE
from tests.auth_helper import auth_header


@pytest.mark.django_db
def test_provider_basic(client, django_assert_num_queries):
    provider = factories.Provider(
        id=uuid.UUID("aaaaaaa0-1342-413b-8e89-db802b2f83f6"), name="Test provider"
    )
    factories.Provider(
        id=uuid.UUID("bbbbbbb0-1342-413b-8e89-db802b2f83f6"), name="Test provider 2"
    )
    factories.Provider(
        id=uuid.UUID("ccccccc0-1342-413b-8e89-db802b2f83f6"), name="Test provider 3"
    )

    response = client.get("/prv/providers/")
    assert response.status_code == 401

    response = client.get(
        "/prv/providers/", **auth_header(SCOPE_VEHICLE, provider_id=provider.id)
    )
    assert response.status_code == 403

    with django_assert_num_queries(3):
        # 1 providers
        # 2 savepoints
        response = client.get("/prv/providers/", **auth_header(SCOPE_ADMIN))
    assert response.status_code == 200
    assert len(response.data) == 3

    assert {
        "id": "aaaaaaa0-1342-413b-8e89-db802b2f83f6",
        "name": "Test provider",
        "logo_b64": None,
    } in response.data
    assert {
        "id": "bbbbbbb0-1342-413b-8e89-db802b2f83f6",
        "name": "Test provider 2",
        "logo_b64": None,
    } in response.data
    assert {
        "id": "ccccccc0-1342-413b-8e89-db802b2f83f6",
        "name": "Test provider 3",
        "logo_b64": None,
    } in response.data

    response = client.get(
        "/prv/providers/%s/" % "aaaaaaa0-1342-413b-8e89-db802b2f83f6",
        **auth_header(SCOPE_ADMIN)
    )
    assert response.status_code == 200
    assert response.data == {
        "id": "aaaaaaa0-1342-413b-8e89-db802b2f83f6",
        "name": "Test provider",
        "logo_b64": None,
    }
