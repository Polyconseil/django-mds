import datetime
import pytest

from mds import factories
from mds import models


@pytest.mark.django_db
def test_areas_detail(client, django_assert_num_queries):
    response = client.get("/service_area/foo/bar/")
    assert response.status_code == 404
    area = factories.Area(
        creation_date=datetime.datetime(2012, 1, 1, tzinfo=datetime.timezone.utc)
    )
    with django_assert_num_queries(4):
        # 1 query on areas
        # 1 query on polygons
        # 2 savepoints
        response = client.get("/service_area/{}/".format(area.pk))
    assert response.status_code == 200
    assert response.data == {
        "id": str(area.pk),
        "label": area.label,
        "creation_date": "2012-01-01T00:00:00Z",
        "deletion_date": None,
        "polygons": [],
    }


@pytest.mark.django_db
def test_areas_list(client, django_assert_num_queries):
    factories.Area.create_batch(5)
    with django_assert_num_queries(5):
        # 1 query on areas
        # 1 query on polygons
        # 1 count
        # 2 savepoints
        response = client.get("/service_area/")
    assert response.status_code == 200
    assert len(response.data["results"]) == 5


@pytest.mark.django_db
def test_areas_add(client, django_assert_num_queries):
    response = client.post(
        "/service_area/",
        data={"label": "myarea", "creation_date": "2012-01-01T00:00:00Z"},
        content_type="application/json",
    )
    assert response.status_code == 201
    created_area = models.Area.objects.get()
    assert created_area.label == "myarea"
    assert list(created_area.polygons.all()) == []
