import pytest

from mds import admin  # noqa: F401


@pytest.mark.django_db
def test_admin(admin_client):
    response = admin_client.get("/admin/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_service_area(client):
    response = client.get("/service_area/foo/bar/")
    assert response.status_code == 404
    response = client.post(
        "/service_area/",
        data={
            "id": "13b8c961-61fd-4cce-8113-81af1de90942",
            "creation_date": "2012-01-01T00:00:00Z",
            "label": "test",
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    response = client.get("/service_area/")
    assert response.status_code == 200
    assert response.data == [
        {
            "id": "13b8c961-61fd-4cce-8113-81af1de90942",
            "label": "test",
            "creation_date": "2012-01-01T00:00:00Z",
            "deletion_date": None,
            "polygons": [],
        }
    ]
