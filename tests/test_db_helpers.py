import pytest

from mds import db_helpers
from mds import factories
from mds import models


# Don't use factories not to prefill all fields


@pytest.mark.django_db
def test_upsert_provider():
    provider = factories.Provider.build()
    db_helpers.upsert_providers([provider])

    assert models.Provider.objects.get()


@pytest.mark.django_db
def test_upsert_device():
    provider = factories.Provider()  # Had issue when not creating it
    device = factories.Device.build(provider=provider)
    db_helpers.upsert_devices([device])

    assert models.Device.objects.get()


@pytest.mark.django_db
def test_upsert_event_record():
    device = factories.Device()  # Same
    event_record = factories.EventRecord.build(device=device)
    db_helpers.upsert_event_records([event_record], "push")

    assert models.EventRecord.objects.get()
