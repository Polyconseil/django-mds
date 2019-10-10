import datetime
import uuid

from django.urls import reverse

import pytest
import pytz

from mds import factories

from tests.auth_helpers import BASE_NUM_QUERIES


@pytest.mark.django_db
def test_compliances_metadata(client):
    response = client.options(reverse("agency:compliance-list"))
    assert response.status_code == 200
    assert len(response.data) == 5  # FIXME
    assert response._headers["allow"][1] == "GET, POST, HEAD, OPTIONS"


@pytest.mark.django_db
def test_compliance_list_basic(client, django_assert_num_queries):
    device = factories.Device()
    policy = factories.Policy(published=True)

    # One provider-specific policy
    # provider_policy = factories.ComplianceFactory()
    # And one general-purpose policy
    compliance = factories.ComplianceFactory(
        rule=uuid.UUID("81b1bc92-65b7-4434-8ada-2feeb0b7b223"),
        geography=uuid.UUID("e0e4a085-7a50-43e0-afa4-6792ca897c5a"),
        policy_id=policy.id,
        vehicle_id=device.id,
        start_date=datetime.datetime(2007, 12, 6, 16, 29, 43, 79043, tzinfo=pytz.UTC),
        end_date=datetime.datetime(2007, 12, 7, 16, 29, 43, 79043, tzinfo=pytz.UTC),
    )

    compliance_null = factories.ComplianceFactory(
        rule=uuid.UUID("89b5bbb5-ba98-4498-9649-787eb8ddbb8e"),
        geography=uuid.UUID("2cfbdd7f-8ba2-4b48-9826-951fe3249981"),
        policy_id=factories.Policy().id,
        vehicle_id=factories.Device().id,
        start_date=datetime.datetime(2009, 12, 6, 16, 29, 43, 79043, tzinfo=pytz.UTC),
        end_date=None,
    )

    # Test without auth
    n = BASE_NUM_QUERIES
    n += 1  # query on device
    n += 1  # query on policy  # query on Compliance
    n += 1  # query on second compliance
    # query Last compliance
    with django_assert_num_queries(n):  # No token check
        response = client.get(reverse("agency:compliance-list"))
    assert response.status_code == 200

    # Check why there is policy more
    assert str(compliance.policy.id) == response.data[0]["id"]

    response = client.get(
        reverse("agency:compliance-list"), {"provider_id": str(device.provider.id)}
    )

    assert response.status_code == 200
    assert str(compliance.policy_id) == response.data[0]["id"]
    # provider is OK

    response = client.get(
        reverse("agency:compliance-list"),
        {
            "provider_id": str(device.provider.id),
            "end_date": int(
                datetime.datetime(
                    2009, 12, 7, 16, 29, 43, 79043, tzinfo=pytz.UTC
                ).timestamp()
            ),
        },
    )

    # provider is OK but timestamp is to high
    assert response.status_code == 200
    assert response.data == []

    response = client.get(
        reverse("agency:compliance-list"),
        {
            "provider_id": str(device.provider.id),
            "end_date": int(
                datetime.datetime(
                    2007, 12, 7, 16, 29, 43, 79043, tzinfo=pytz.UTC
                ).timestamp()
            )
            - 60000,
        },
    )

    # provider is OK and timestamp is OK
    assert response.status_code == 200
    assert response.data[0]["id"] == str(compliance.policy_id)

    response = client.get(
        reverse("agency:compliance-list"), {"end_date": 1126023900}
    )  # to low

    assert response.status_code == 200 and response.data == []

    response = client.get(
        reverse("agency:compliance-list"), {"end_date": 1741556700}
    )  # to high but compliance_null is not finish

    assert response.status_code == 200
    assert response.data[0]["id"] == str(compliance_null.policy_id)

    response = client.get(
        reverse("agency:compliance-list"),
        {"provider_id": "89b5bbb5-ba98-4498-9649-787eb8ddbb8e"},
    )  # this provider don't exist

    assert response.status_code == 200 and response.data == []
