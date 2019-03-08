import logging
import traceback
import urllib.parse

from django.contrib.gis import geos
from django.core import management
from django.db import transaction
from django.db.models.aggregates import Max

from oauthlib.oauth2 import BackendApplicationClient
import requests
from requests_oauthlib import OAuth2Session

from mds import enums
from mds import models
from mds import utils


NOT_PROVIDED = object()

logger = logging.getLogger(__name__)


class Command(management.BaseCommand):
    help = "Poll providers to fetch their latest data."

    def handle(self, *args, **options):
        for provider in models.Provider.objects.all():
            if not provider.base_api_url:
                self.stdout.write(
                    "Provider %s has no URL defined, skipping." % provider.name
                )
                continue

            self.stdout.write("Polling %s... " % provider.name, ending="")
            try:
                with transaction.atomic():
                    self.poll_status_changes(provider)
            except Exception:  # pylint: disable=broad-except
                logger.exception("Error in polling provider %s", provider.name)
                self.stderr.write("Polling failed!")
                self.stderr.write(traceback.format_exc())
                # Try the next provider anyway
                continue

            self.stdout.write("Success!")

    def poll_status_changes(self, provider):
        next_url = urllib.parse.urljoin(provider.base_api_url, "status_changes")
        if provider.api_configuration.get("trailing_slash"):
            next_url += "/"

        # Start where we left
        # (we wouldn't know if the provider recorded late telemetries after the last sync)
        max_timestamp = models.EventRecord.objects.filter(
            device__provider=provider
        ).aggregate(max_timestamp=Max("timestamp"))["max_timestamp"]
        if max_timestamp:
            next_url = "%s?%s" % (
                next_url,
                urllib.parse.urlencode(
                    {"start_time": utils.to_mds_timestamp(max_timestamp)}
                ),
            )

        # Pagination
        while next_url:
            data = self.get_data(provider, next_url)
            for status_change in data["data"]["status_changes"]:
                # The list of event types and even the naming don't match between
                # the provider and agency APIs, so translate one to the other
                event_type = enums.PROVIDER_EVENT_TYPE_REASON_TO_AGENCY_EVENT_TYPE[
                    status_change["event_type_reason"]
                ]
                device, created = models.Device.objects.get_or_create(
                    pk=status_change["device_id"],
                    defaults={
                        "provider": provider,
                        "identification_number": status_change["vehicle_id"],
                        "category": status_change["vehicle_type"],
                        "propulsion": status_change["propulsion_type"],
                        "dn_status": enums.EVENT_TYPE_TO_DEVICE_STATUS[event_type],
                    },
                )
                if created:
                    self.stdout.write(
                        "Device %s was created." % status_change["device_id"]
                    )

                event_location = status_change["event_location"]
                assert event_location["geometry"]["type"] == "Point"

                # Filtering on start_time *should* be implemented
                # So consider timestamps as unique per device
                device.event_records.get_or_create(
                    timestamp=utils.from_mds_timestamp(status_change["event_time"]),
                    defaults=dict(
                        source="pull",  # pulled by agency
                        point=geos.Point(event_location["geometry"]["coordinates"]),
                        event_type=event_type,
                        properties={
                            "trip_id": status_change.get("associated_trip"),
                            "telemetry": {
                                "timestamp": event_location["properties"]["timestamp"],
                                "gps": {
                                    "lng": event_location["geometry"]["coordinates"][0],
                                    "lat": event_location["geometry"]["coordinates"][1],
                                    # XXX altitude, etc.?
                                },
                                "battery_pct": status_change.get("battery_pct"),
                            },
                        },
                    ),
                )

            next_url = data["links"].get("next", NOT_PROVIDED)
            if next_url is NOT_PROVIDED:
                self.stdout.write(
                    "Warning: provider %s doesn't provide a next URL, cannot batch."
                    % provider.name
                )
                # We'll poll the next page on the next round
                # Hoping that they *do* implement "start_time"...
                next_url = None

    def get_data(self, provider, url):
        authentication_type = provider.api_authentication.get("type")
        if authentication_type in (None, "", "none"):
            client = requests
        elif authentication_type == "oauth2":
            client = authenticate_client_credentials(provider)
        else:
            raise NotImplementedError()

        response = client.get(url, timeout=30)
        response.raise_for_status()
        return response.json()


def authenticate_client_credentials(provider):
    """Authenticate using the Backend Application Flow from OAuth2."""
    client_id = provider.api_authentication["client_id"]

    # Skip the whole token refreshing with just BlueLA to consider
    token = _fetch_token(provider)
    client = OAuth2Session(client_id, token=token)
    return client


def _fetch_token(provider):
    """Fetch an access token from the provider"""
    client_id = provider.api_authentication["client_id"]
    client_secret = provider.api_authentication["client_secret"]
    client = BackendApplicationClient(client_id=client_id)
    session = OAuth2Session(client=client)
    token_url = provider.oauth2_url
    if not token_url:
        token_url = urllib.parse.urljoin(provider.base_api_url, "/oauth2/token")
        if provider.api_configuration.get("trailing_slash"):
            token_url += "/"
    token = session.fetch_token(
        token_url=token_url, client_id=client_id, client_secret=client_secret
    )
    return token
