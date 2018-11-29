"""
WSGI configuration
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mds_server.settings")

application = get_wsgi_application()
