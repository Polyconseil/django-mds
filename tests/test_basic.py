import pytest

from midas import admin  # noqa: F401
from midas import models


@pytest.mark.django_db
def test_models():
    models.Query.objects.create(provider="foo", method="PUT")
    assert models.Query.objects.count() == 1
