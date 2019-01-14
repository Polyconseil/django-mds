import pytest
import uuid

from mds import factories


@pytest.mark.django_db
def test_provider_basic(client, django_assert_num_queries):
    factories.Provider(
        id=uuid.UUID("aaaaaaa0-1342-413b-8e89-db802b2f83f6"), name="Test provider"
    )
    factories.Provider(
        id=uuid.UUID("bbbbbbb0-1342-413b-8e89-db802b2f83f6"), name="Test provider 2"
    )
    factories.Provider(
        id=uuid.UUID("ccccccc0-1342-413b-8e89-db802b2f83f6"), name="Test provider 3"
    )

    response = client.get("/providers/")
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
