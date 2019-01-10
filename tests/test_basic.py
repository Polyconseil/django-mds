import pytest

from mds import admin  # noqa: F401


@pytest.mark.django_db
def test_admin(admin_client):
    response = admin_client.get("/admin/")
    assert response.status_code == 200
