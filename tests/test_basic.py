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


@pytest.mark.django_db
def test_device(client):
    response = client.put(
        "/vehicle/13b8c961-61fd-4cce-8113-81af1de90942/",
        data={
            "provider": "27e84290-06b4-4c5d-88f2-60e6dcb09712",
            "identification_number": "foo",
            "model": "bar",
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    now = "2018-11-07T15:35:58.108099+02:00"
    utcnow = "2018-11-07T13:35:58.108099Z"
    response = client.post(
        "/vehicle/13b8c961-61fd-4cce-8113-81af1de90942/",
        data={
            "provider": "27e84290-06b4-4c5d-88f2-60e6dcb09712",
            "status": "available",
            "position": {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [2.293117046356201, 48.85829170715186],
                },
                "properties": {"gsm": {"timestamp": now}, "gps": {"timestamp": now}},
            },
        },
        content_type="application/json",
    )
    assert response.status_code == 200
    response = client.get("/vehicle/")
    assert response.status_code == 200
    assert response.data == [
        {
            "id": "13b8c961-61fd-4cce-8113-81af1de90942",
            "provider": "27e84290-06b4-4c5d-88f2-60e6dcb09712",
            "identification_number": "foo",
            "model": "bar",
            "status": "available",
            "position": {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [2.293117046356201, 48.85829170715186],
                },
                "properties": {
                    "gsm": {"timestamp": utcnow, "operator": None, "signal": None},
                    "gps": {
                        "timestamp": utcnow,
                        "accuracy": None,
                        "course": None,
                        "speed": None,
                    },
                },
            },
        }
    ]
