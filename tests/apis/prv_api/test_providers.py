import pytest
import uuid

from mds import factories
from mds.access_control.scopes import SCOPE_PRV_API, SCOPE_AGENCY_API
from tests.auth_helpers import auth_header, BASE_NUM_QUERIES


@pytest.mark.django_db
def test_provider_basic(client, django_assert_num_queries):
    provider = factories.Provider(
        id=uuid.UUID("aaaaaaa0-1342-413b-8e89-db802b2f83f6"), name="Test provider"
    )
    factories.Device(provider=provider, category="car")
    factories.Device(
        provider=factories.Provider(
            id=uuid.UUID("bbbbbbb0-1342-413b-8e89-db802b2f83f6"), name="Test provider 2"
        ),
        category="scooter",
    )
    factories.Device(
        provider=factories.Provider(
            id=uuid.UUID("ccccccc0-1342-413b-8e89-db802b2f83f6"), name="Test provider 3"
        ),
        category="bicycle",
    )

    response = client.get("/prv/providers/")
    assert response.status_code == 401

    response = client.get(
        "/prv/providers/", **auth_header(SCOPE_AGENCY_API, provider_id=provider.id)
    )
    assert response.status_code == 403

    n = BASE_NUM_QUERIES
    n += 1  # query on providers
    with django_assert_num_queries(n):
        response = client.get("/prv/providers/", **auth_header(SCOPE_PRV_API))
    assert response.status_code == 200
    assert len(response.data) == 3
    assert {
        "id": "aaaaaaa0-1342-413b-8e89-db802b2f83f6",
        "name": "Test provider",
        "logo_b64": None,
        "device_category": "",
        "base_api_url": "http://provider",
        "api_configuration": {"trailing_slash": False},
        "api_authentication": {"type": "none"},
        "agency_api_authentication": {"type": "none"},
        "colors": {},
        "device_categories": {"bicycle": 0, "scooter": 0, "car": 1},
    } in response.data
    assert {
        "id": "bbbbbbb0-1342-413b-8e89-db802b2f83f6",
        "name": "Test provider 2",
        "device_category": "",
        "logo_b64": None,
        "base_api_url": "http://provider",
        "api_configuration": {"trailing_slash": False},
        "api_authentication": {"type": "none"},
        "agency_api_authentication": {"type": "none"},
        "colors": {},
        "device_categories": {"bicycle": 0, "scooter": 1, "car": 0},
    } in response.data
    assert {
        "id": "ccccccc0-1342-413b-8e89-db802b2f83f6",
        "name": "Test provider 3",
        "logo_b64": None,
        "device_category": "",
        "base_api_url": "http://provider",
        "api_configuration": {"trailing_slash": False},
        "api_authentication": {"type": "none"},
        "agency_api_authentication": {"type": "none"},
        "colors": {},
        "device_categories": {"bicycle": 1, "scooter": 0, "car": 0},
    } in response.data

    response = client.get(
        "/prv/providers/%s/" % "aaaaaaa0-1342-413b-8e89-db802b2f83f6",
        **auth_header(SCOPE_PRV_API)
    )
    assert response.status_code == 200
    assert response.data == {
        "id": "aaaaaaa0-1342-413b-8e89-db802b2f83f6",
        "name": "Test provider",
        "device_category": "",
        "logo_b64": None,
        "base_api_url": "http://provider",
        "api_configuration": {"trailing_slash": False},
        "api_authentication": {"type": "none"},
        "agency_api_authentication": {"type": "none"},
        "colors": {},
        "device_categories": {"bicycle": 0, "scooter": 0, "car": 1},
    }
