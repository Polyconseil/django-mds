import pytest

from mds import factories
from mds import models


@pytest.mark.django_db
def test_with_device_categories(admin_client):
    factories.Device.create_batch(10, provider=factories.Provider())
    provider = models.Provider.objects.with_device_categories().get()
    assert sum(provider.device_categories.values()) == {
        "bicycle": 3,
        "scooter": 3,
        "car": 4,
    }
