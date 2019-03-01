import datetime
import pytest

from mds import factories
from mds.access_control.scopes import SCOPE_AGENCY_API
from tests.auth_helpers import auth_header, BASE_NUM_QUERIES


@pytest.mark.django_db
def test_areas_metadata(client):
    provider = factories.Provider(name="Test provider")
    response = client.options(
        "/mds/v0.x/service_areas/",
        **auth_header(SCOPE_AGENCY_API, provider_id=provider.id),
    )
    assert response.status_code == 200
    assert response._headers["allow"][1] == "GET, HEAD, OPTIONS"


@pytest.mark.django_db
def test_areas_detail(client, django_assert_num_queries):
    provider = factories.Provider(name="Test provider")
    area = factories.Area(
        creation_date=datetime.datetime(2016, 1, 1, tzinfo=datetime.timezone.utc),
        deletion_date=datetime.datetime(2017, 1, 1, tzinfo=datetime.timezone.utc),
        providers=[provider],
    )
    other_provider = factories.Provider(name="Test other provider")

    response = client.get("/mds/v0.x/service_areas/%s/" % area.pk)
    assert response.status_code == 401

    response = client.get(
        "/mds/v0.x/service_areas/foo/bar/",
        **auth_header(SCOPE_AGENCY_API, provider_id=provider.id),
    )
    assert response.status_code == 404

    response = client.get(
        "/mds/v0.x/service_areas/{}/".format(area.pk),
        **auth_header(SCOPE_AGENCY_API, provider_id=other_provider.id),
    )
    assert response.status_code == 404

    n = BASE_NUM_QUERIES
    n += 1  # query on areas
    n += 1  # query on polygons
    with django_assert_num_queries(n):
        response = client.get(
            "/mds/v0.x/service_areas/{}/".format(area.pk),
            **auth_header(SCOPE_AGENCY_API, provider_id=provider.id),
        )
    assert response.status_code == 200
    assert response.data == {
        "service_area_id": str(area.pk),
        "start_date": 1_451_606_400_000,
        "end_date": 1_483_228_800_000,
        "area": {
            "coordinates": [
                [[[0.0, 0.0], [0.0, 50.0], [50.0, 50.0], [50.0, 0.0], [0.0, 0.0]]]
            ],
            "type": "MultiPolygon",
        },
        "type": "unrestricted",
    }


@pytest.mark.django_db
def test_areas_list(client, django_assert_num_queries):
    provider = factories.Provider(name="Test provider")
    factories.Area.create_batch(5, providers=[provider])

    response = client.get("/mds/v0.x/service_areas/")
    assert response.status_code == 401

    n = BASE_NUM_QUERIES
    n += 1  # query on areas
    n += 1  # query on polygons
    with django_assert_num_queries(n):
        response = client.get(
            "/mds/v0.x/service_areas/",
            **auth_header(SCOPE_AGENCY_API, provider_id=provider.id),
        )
    assert response.status_code == 200
    assert len(response.data) == 5
