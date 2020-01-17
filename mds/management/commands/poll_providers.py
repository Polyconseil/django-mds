"""
Pulling data for registered providers

This is the opposite of provider pushing their data to the agency API.
"""
import logging

from django.core import management

from mds import enums
from mds import models
from mds.provider_poller.poller import v0_2
from mds.provider_poller.poller import v0_3
from mds.provider_poller.poller import v0_4


logger = logging.getLogger(__name__)


version_match = {
    enums.MDS_VERSIONS.v0_2.name: v0_2,
    enums.MDS_VERSIONS.v0_3.name: v0_3,
    enums.MDS_VERSIONS.v0_4.name: v0_4,
}


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
            # We request a specific version of the Provider API
            # TODO(hcauwelier) make it mandatory, see SMP-1673
            api_version_raw = provider.api_configuration.get(
                "api_version", enums.DEFAULT_PROVIDER_API_VERSION
            )
            # We store the enum key, which cannot be a numeric identifier
            # It doubles as a validity check
            api_version = enums.MDS_VERSIONS[api_version_raw].value
            logger.debug(
                "Polling provider %s using version %s... ", provider.name, api_version
            )
            try:
                # Raise on version mismatch
                version_match[api_version_raw].StatusChangesPoller(
                    provider, api_version
                ).poll()
            except Exception:  # pylint: disable=broad-except
                # In dev, test... environments, we want explicit errors
                if options["raise_on_error"]:
                    raise
                # But in production, we just log and try the next one
                logger.exception("Error in polling provider %s", provider.name)
            else:
                logger.debug("Polling provider %s succeeded.", provider.name)
