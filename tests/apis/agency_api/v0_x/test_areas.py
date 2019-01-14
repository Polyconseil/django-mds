import datetime
import pytest

from mds import factories
from mds.access_control.scopes import SCOPE_VEHICLE
from tests.auth_helper import auth_header


@pytest.mark.django_db
def test_areas_metadata(client, django_assert_num_queries):
    provider = factories.Provider(name="Test provider")
    response = client.options(
        "/mds/v0.x/service_areas/", **auth_header(SCOPE_VEHICLE, provider_id=provider.id)
    )
    assert response.status_code == 200
    assert response._headers["allow"][1] == "GET, HEAD, OPTIONS"


@pytest.mark.django_db
def test_areas_detail(client, django_assert_num_queries):
    provider = factories.Provider(name="Test provider")
    area = factories.Area(
        creation_date=datetime.datetime(2012, 1, 1, tzinfo=datetime.timezone.utc),
        providers=[provider],
    )
    other_provider = factories.Provider(name="Test other provider")

    response = client.get("/mds/v0.x/service_areas/%s/" % area.pk)
    assert response.status_code == 401

    response = client.get(
        "/mds/v0.x/service_areas/foo/bar/",
        **auth_header(SCOPE_VEHICLE, provider_id=provider.id),
    )
    assert response.status_code == 404

    response = client.get(
        "/mds/v0.x/service_areas/{}/".format(area.pk),
        **auth_header(SCOPE_VEHICLE, provider_id=other_provider.id),
    )
    assert response.status_code == 404

    with django_assert_num_queries(4):
        # 1 query on areas
        # 1 query on polygons
        # 2 savepoints
        response = client.get(
            "/mds/v0.x/service_areas/{}/".format(area.pk),
            **auth_header(SCOPE_VEHICLE, provider_id=provider.id),
        )
    assert response.status_code == 200
    assert response.data == {
        "service_area_id": str(area.pk),
        "service_area": {
            "coordinates": [
                [[[0.0, 0.0], [0.0, 50.0], [50.0, 50.0], [50.0, 0.0], [0.0, 0.0]]]
            ],
            "type": "MultiPolygon",
        },
    }


@pytest.mark.django_db
def test_areas_list(client, django_assert_num_queries):
    provider = factories.Provider(name="Test provider")
    factories.Area.create_batch(5, providers=[provider])

    response = client.get("/mds/v0.x/service_areas/")
    assert response.status_code == 401

    with django_assert_num_queries(4):
        # 1 query on areas
        # 1 query on polygons
        # 2 savepoints
        response = client.get(
            "/mds/v0.x/service_areas/", **auth_header(SCOPE_VEHICLE, provider_id=provider.id)
        )
    assert response.status_code == 200
    assert len(response.data) == 5
