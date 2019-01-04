import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mds.server.settings")
os.environ["MDS_AUTH_SECRET_KEY"] = "secret_for_tests"


def pytest_configure():
    django.setup()
