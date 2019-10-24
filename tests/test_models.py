import datetime
import unittest.mock
import uuid

import pytest

from django.core.exceptions import ValidationError
from django.utils import timezone

from mds import factories
from mds import models


@pytest.mark.django_db
def test_with_device_categories():
    provider = factories.Provider()
    factories.Device.create_batch(3, category="bicycle", provider=provider)
    factories.Device.create_batch(2, category="scooter", provider=provider)
    factories.Device.create_batch(1, category="car", provider=provider)
    provider = models.Provider.objects.with_device_categories().get()
    assert provider.device_categories == {"bicycle": 3, "scooter": 2, "car": 1}


@pytest.mark.django_db
def test_policy_active():
    now = timezone.now()
    yesterday = timezone.now() - datetime.timedelta(1)
    tomorrow = timezone.now() + datetime.timedelta(1)

    unpublished_policy = factories.Policy(published_date=None)  # noqa: F841
    old_policy = factories.Policy(
        start_date=yesterday, end_date=yesterday, published_date=yesterday
    )
    obsolete_policy = factories.Policy(  # noqa: F841
        start_date=yesterday,
        end_date=tomorrow + datetime.timedelta(seconds=1),  # Not included
        published_date=yesterday,
        prev_policies=[old_policy],
    )

    # None of these policies should show up
    assert set(models.Policy.objects.active()) == set()

    ongoing_policy = factories.Policy(
        name="ongoing", start_date=now, published_date=now
    )
    bound_policy = factories.Policy(
        name="bound", start_date=now, end_date=tomorrow, published_date=now
    )
    assert set(models.Policy.objects.active(now)) == {ongoing_policy, bound_policy}
    assert set(models.Policy.objects.active(yesterday)) == set()
    assert set(models.Policy.objects.active(tomorrow)) == {ongoing_policy}


@pytest.mark.django_db
def test_policy_publish():
    policy = factories.Policy(published_date=None, rules=[])

    try:
        policy.publish()
    except ValidationError:
        pass
    else:
        assert False, "Policy not prevented from being published."

    policy = factories.Policy(published_date=None)  # Rebuild with a rule

    try:
        policy.publish()
    except ValidationError:
        pass
    else:
        assert False, "Policy not prevented from being published."

    # The ID from the Policy factory
    factories.Area(
        label="Venice Beach", id=uuid.UUID("e0e4a085-7a50-43e0-afa4-6792ca897c5a")
    )

    with unittest.mock.patch(
        "uuid.uuid4", lambda: uuid.UUID("fe363c54-011b-4840-a909-0fd4ef6d168e")
    ):
        policy.publish()

    assert policy.geographies == {
        "fe363c54-011b-4840-a909-0fd4ef6d168e": {
            "type": "Feature",
            "geometry": {
                "type": "GeometryCollection",
                "geometries": [
                    {
                        "type": "MultiPolygon",
                        "coordinates": [
                            [
                                [
                                    [0.0, 0.0],
                                    [0.0, 50.0],
                                    [50.0, 50.0],
                                    [50.0, 0.0],
                                    [0.0, 0.0],
                                ]
                            ]
                        ],
                    }
                ],
            },
            "id": uuid.UUID("fe363c54-011b-4840-a909-0fd4ef6d168e"),
            "properties": {
                "name": "Venice Beach",
                "label": "Venice Beach",
                "area": "e0e4a085-7a50-43e0-afa4-6792ca897c5a",
            },
        }
    }
