"""
Pulling data for registered providers

This is the opposite of provider pushing their data to the agency API.
"""
from django.core import management

from mds import models
from mds.provider_poller import poller


class Command(management.BaseCommand):
    help = "Poll providers to fetch their latest data."

    def handle(self, *args, **options):
        for provider in models.Provider.objects.all():
            poller.StatusChangesPoller(provider).poll()
