"""
Pulling data for registered providers

This is the opposite of provider pushing their data to the agency API.
"""
import logging

from django.core import management

from mds import models
from mds.provider_poller import poller


logger = logging.getLogger(__name__)


class Command(management.BaseCommand):
    help = "Poll providers to fetch their latest data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--raise-on-error",
            action="store_true",
            help=("Raise exceptions instead of ignoring them."),
        )

    def handle(self, *args, **options):
        for provider in models.Provider.objects.all():
            logger.info("Polling provider %s... ", provider.name)
            try:
                poller.StatusChangesPoller(provider).poll()
            except Exception:  # pylint: disable=broad-except
                # In dev, test... environments, we want explicit errors
                if options["raise_on_error"]:
                    raise
                # But in production, we just log and try the next one
                logger.exception("Error in polling provider %s", provider.name)
            else:
                logger.info("Polling provider %s succeeded.", provider.name)
