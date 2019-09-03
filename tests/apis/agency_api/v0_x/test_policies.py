import datetime

from django.urls import reverse
from django.utils import timezone

import pytest

from mds import factories
from mds import utils
from mds.access_control.scopes import SCOPE_AGENCY_API

from tests.auth_helpers import auth_header, BASE_NUM_QUERIES


@pytest.mark.django_db
def test_policies_metadata(client):
    response = client.options(reverse("agency:policy-list"))
    assert response.status_code == 200
    assert len(response.data) == 4  # FIXME
    assert response._headers["allow"][1] == "GET, HEAD, OPTIONS"


@pytest.mark.django_db
def test_policy_list_basic(client, django_assert_num_queries):
    provider = factories.Provider(name="Test provider")
    other_provider = factories.Provider(name="Other provider")

    # One provider-specific policy
    provider_policy = factories.Policy(providers=[provider])
    # And one general-purpose policy
    general_policy = factories.Policy()

    # Test without auth
    n = BASE_NUM_QUERIES
    n += 1  # query on policies
    n += 1  # query on related providers
    n += 1  # query on related previous policies
    with django_assert_num_queries(n - 1):  # No token check
        response = client.get(reverse("agency:policy-list"))
    assert response.status_code == 200
    assert [p["policy_id"] for p in response.data] == [str(general_policy.id)]

    # Test with provider auth
    with django_assert_num_queries(n):
        response = client.get(
            reverse("agency:policy-list"),
            **auth_header(SCOPE_AGENCY_API, provider_id=provider.id),
        )
    assert response.status_code == 200
    assert [p["policy_id"] for p in response.data] == [
        str(provider_policy.id),
        str(general_policy.id),
    ]
    # We made this mistake before, don't serve a UUID object
    assert response.data[0]["provider_ids"] == [str(provider.id)]

    # Test with other provider auth
    with django_assert_num_queries(n):
        response = client.get(
            reverse("agency:policy-list"),
            **auth_header(SCOPE_AGENCY_API, provider_id=other_provider.id),
        )
    assert response.status_code == 200
    assert [p["policy_id"] for p in response.data] == [str(general_policy.id)]


@pytest.mark.django_db
def test_policy_list_range(client):
    # Policy from last year
    past = factories.Policy(start_date=timezone.now() - datetime.timedelta(days=365))
    # Policy ongoing (half of the lifespan)
    ongoing = factories.Policy(start_date=timezone.now() - datetime.timedelta(days=15))
    # Policy for next year
    future = factories.Policy(start_date=timezone.now() + datetime.timedelta(days=365))

    # Ongoing and future policies by default
    response = client.get(reverse("agency:policy-list"))
    assert [p["policy_id"] for p in response.data] == [str(ongoing.id), str(future.id)]

    # Ongoing only
    response = client.get(
        reverse("agency:policy-list"),
        {
            "start_time": utils.to_mds_timestamp(timezone.now()),
            "end_time": utils.to_mds_timestamp(timezone.now()),
        },
    )
    assert [p["policy_id"] for p in response.data] == [str(ongoing.id)]

    # Future only
    response = client.get(
        reverse("agency:policy-list"),
        {
            "start_time": utils.to_mds_timestamp(
                timezone.now() + datetime.timedelta(days=30)
            )
        },
    )
    assert [p["policy_id"] for p in response.data] == [str(future.id)]

    # Past only
    response = client.get(
        reverse("agency:policy-list"),
        {
            "start_time": utils.to_mds_timestamp(
                timezone.now() - datetime.timedelta(days=365)
            ),
            "end_time": utils.to_mds_timestamp(
                timezone.now() - datetime.timedelta(days=30)
            ),
        },
    )
    assert [p["policy_id"] for p in response.data] == [str(past.id)]

    # All
    response = client.get(
        reverse("agency:policy-list"),
        {
            "start_time": utils.to_mds_timestamp(
                timezone.now() - datetime.timedelta(days=365)
            ),
            "end_time": utils.to_mds_timestamp(
                timezone.now() + datetime.timedelta(days=365)
            ),
        },
    )
    assert [p["policy_id"] for p in response.data] == [
        str(past.id),
        str(ongoing.id),
        str(future.id),
    ]
