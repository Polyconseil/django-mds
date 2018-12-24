import pytest
import uuid

from mds import factories


@pytest.mark.django_db
def test_provider_basic(client, django_assert_num_queries):
    factories.Provider(
        id=uuid.UUID("aaaaaaa0-1342-413b-8e89-db802b2f83f6"), name="Test provider"
    )
    factories.Provider(
        id=uuid.UUID("bbbbbbb0-1342-413b-8e89-db802b2f83f6"), name="Test amateurvider"
    )
    factories.Provider(
        id=uuid.UUID("ccccccc0-1342-413b-8e89-db802b2f83f6"), name="Test proremplir"
    )

    response = client.get("/provider/")
    assert response.status_code == 200
    assert len(response.data) == 3

    assert {
        "id": "aaaaaaa0-1342-413b-8e89-db802b2f83f6",
        "name": "Test provider",
    } in response.data
    assert {
        "id": "bbbbbbb0-1342-413b-8e89-db802b2f83f6",
        "name": "Test amateurvider",
    } in response.data
    assert {
        "id": "ccccccc0-1342-413b-8e89-db802b2f83f6",
        "name": "Test proremplir",
    } in response.data
