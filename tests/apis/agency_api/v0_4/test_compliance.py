import datetime
import uuid

from django.urls import reverse

import pytest
import pytz

from mds import factories
from mds import utils


@pytest.mark.django_db
def test_compliances_metadata(client):
    response = client.options(reverse("agency-0.4:compliance-list"))
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

    compliance_ongoing = factories.ComplianceFactory(
        rule=uuid.UUID("89b5bbb5-ba98-4498-9649-787eb8ddbb8e"),
        geography=uuid.UUID("2cfbdd7f-8ba2-4b48-9826-951fe3249981"),
        policy_id=factories.Policy().id,
        vehicle_id=factories.Device().id,
        start_date=datetime.datetime(2009, 12, 6, 16, 29, 43, 79043, tzinfo=pytz.UTC),
        end_date=None,
    )

    # Test without auth
    n = 2  # Savepoint and release
    n += 1  # query on policy
    n += 1  # query on related compliances
    n += 1  # query on device
    n += 1  # query on other device
    # query Last compliance
    with django_assert_num_queries(n):
        response = client.get(reverse("agency-0.4:compliance-list"))
    assert response.status_code == 200

    # Check why there is policy more (??? what does it mean?)
    assert response.data[0]["id"] == str(compliance.policy.id)

    # Now test with a provider ID

    response = client.get(
        reverse("agency-0.4:compliance-list"), {"provider_id": str(device.provider.id)}
    )

    # The provider can fetch a policy that applies to them
    # (to all providers in this case)
    assert response.status_code == 200
    assert response.data[0]["id"] == str(compliance.policy_id)

    response = client.get(
        reverse("agency-0.4:compliance-list"),
        {
            "provider_id": str(device.provider.id),
            "end_date": utils.to_mds_timestamp(
                datetime.datetime(2009, 12, 7, 16, 29, 43, 79043, tzinfo=pytz.UTC)
            ),
        },
    )

    # provider is OK but timestamp is too high
    assert response.status_code == 200
    assert response.data == []

    response = client.get(
        reverse("agency-0.4:compliance-list"),
        {
            "provider_id": str(device.provider.id),
            "end_date": utils.to_mds_timestamp(
                datetime.datetime(2007, 12, 7, 16, 29, 43, 79043, tzinfo=pytz.UTC)
            )
            - 60000,  # XXX ?!
        },
    )

    # provider is OK and timestamp is OK
    assert response.status_code == 200
    assert response.data[0]["id"] == str(compliance.policy_id)

    response = client.get(
        reverse("agency-0.4:compliance-list"),
        {
            "end_date": utils.to_mds_timestamp(
                datetime.datetime(
                    1970, 1, 14, 0, 47, 3, 900000, tzinfo=datetime.timezone.utc
                )
            )
        },
    )

    # too low
    assert response.status_code == 200 and response.data == []

    response = client.get(
        reverse("agency-0.4:compliance-list"),
        {
            "end_date": utils.to_mds_timestamp(
                datetime.datetime(
                    2070, 1, 21, 3, 45, 56, 700000, tzinfo=datetime.timezone.utc
                )
            )
        },
    )

    # too high but compliance_ongoing is not finished
    assert response.status_code == 200
    assert response.data[0]["id"] == str(compliance_ongoing.policy_id)

    response = client.get(
        reverse("agency-0.4:compliance-list"),
        {"provider_id": "89b5bbb5-ba98-4498-9649-787eb8ddbb8e"},
    )  # this provider don't exist

    assert response.status_code == 200 and response.data == []
