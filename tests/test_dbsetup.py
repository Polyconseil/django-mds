import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_loaddata():
    # Load fixtures
    call_command('loaddata', 'ladot.yaml', verbosity=0)
