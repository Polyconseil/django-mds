import os
import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mds.server.settings")


def pytest_configure():
    django.setup()
