import pytest


@pytest.mark.django_db
def test_schema_get(client):
    response = client.get("/mds/v0.x/swagger.json")
    assert response.status_code == 200
    assert response.data["swagger"] == "2.0"
