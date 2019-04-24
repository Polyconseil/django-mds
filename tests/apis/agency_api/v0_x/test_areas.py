import pytest

from django.urls import reverse

from mds import factories
from mds.access_control.scopes import SCOPE_AGENCY_API
from tests.auth_helpers import auth_header, BASE_NUM_QUERIES


@pytest.mark.django_db
def test_areas_metadata(client):
    provider = factories.Provider(name="Test provider")
    response = client.options(
        reverse("agency:area-list"),
        **auth_header(SCOPE_AGENCY_API, provider_id=provider.id),
    )
    assert response.status_code == 200
    assert response._headers["allow"][1] == "GET, HEAD, OPTIONS"


@pytest.mark.django_db
def test_areas_detail(client, django_assert_num_queries):
    provider = factories.Provider(name="Test provider")
    area = factories.Area(providers=[provider])
    other_provider = factories.Provider(name="Test other provider")

    response = client.get(reverse("agency:area-detail", args=[area.pk]))
    assert response.status_code == 401

    response = client.get(
        reverse("agency:area-detail", args=["foobar"]),
        **auth_header(SCOPE_AGENCY_API, provider_id=provider.id),
    )
    assert response.status_code == 404  # Testing DRF?!

    response = client.get(
        reverse("agency:area-detail", args=[area.pk]),
        **auth_header(SCOPE_AGENCY_API, provider_id=other_provider.id),
    )
    assert response.status_code == 404

    n = BASE_NUM_QUERIES
    n += 1  # query on areas
    n += 1  # query on polygons
    with django_assert_num_queries(n):
        response = client.get(
            reverse("agency:area-detail", args=[area.pk]),
            **auth_header(SCOPE_AGENCY_API, provider_id=provider.id),
        )
    assert response.status_code == 200
    assert response.data == {
        "service_area_id": str(area.pk),
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

    response = client.get(reverse("agency:area-list"))
    assert response.status_code == 401

    n = BASE_NUM_QUERIES
    n += 1  # query on areas
    n += 1  # query on polygons
    with django_assert_num_queries(n):
        response = client.get(
            reverse("agency:area-list"),
            **auth_header(SCOPE_AGENCY_API, provider_id=provider.id),
        )
    assert response.status_code == 200
    assert len(response.data) == 5
