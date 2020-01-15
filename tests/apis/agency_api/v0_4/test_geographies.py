from django.urls import reverse

import pytest

from mds import factories


@pytest.mark.django_db
def test_geography_list(client):
    response = client.get(reverse("agency-0.4:geography-list"))
    assert response.status_code == 404


@pytest.mark.django_db
def test_geography_detail(client):
    policy = factories.Policy(published=True)
    response = client.get(reverse("agency-0.4:geography-detail", args=[policy.id]))
    assert response.status_code == 200
    # The whole structure is tested in test_models
    assert response.json()["type"] == "FeatureCollection"
    assert len(response.json()["features"]) == 1
