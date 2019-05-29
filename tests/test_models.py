import pytest

from mds import factories
from mds import models


@pytest.mark.django_db
def test_with_device_categories(admin_client):
    provider = factories.Provider()
    factories.Device.create_batch(3, category="bicycle", provider=provider)
    factories.Device.create_batch(2, category="scooter", provider=provider)
    factories.Device.create_batch(1, category="car", provider=provider)
    provider = models.Provider.objects.with_device_categories().get()
    assert provider.device_categories == {"bicycle": 3, "scooter": 2, "car": 1}
