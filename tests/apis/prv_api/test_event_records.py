import pytest

from django.utils.dateparse import parse_datetime

from mds import factories
from mds.access_control.scopes import SCOPE_PRV_API
from tests.auth_helpers import auth_header


@pytest.mark.django_db
def test_provider_basic(client, django_assert_num_queries):
    device = factories.Device()
    event_record = factories.EventRecord(device=device)
    factories.EventRecord.create_batch(10)

    response = client.get("/prv/event_records/")
    assert response.status_code == 401

    response = client.get("/prv/event_records/", **auth_header(SCOPE_PRV_API))
    assert response.status_code == 200
    assert len(response.data) == 11

    response = client.get(
        "/prv/event_records/", {"device": device.id}, **auth_header(SCOPE_PRV_API)
    )
    assert response.status_code == 200
    assert len(response.data) == 1
    assert parse_datetime(response.data[0]["timestamp"]) == event_record.timestamp
