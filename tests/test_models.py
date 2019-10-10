import datetime

import pytest

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
