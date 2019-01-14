import pytest
from django.core.management import call_command

from mds import models


@pytest.mark.django_db
def test_loaddata():
    # Load fixtures
    call_command("genfixture", "--records_count", "10")
    assert models.EventRecord.objects.count() == 10
    assert models.Area.objects.count() == 1
