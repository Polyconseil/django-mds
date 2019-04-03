"""
Pulling data for registered providers

This is the opposite of provider pushing their data to the agency API.
"""
import datetime
import json
import logging
import threading
import urllib.parse
import uuid

from django.contrib.gis import geos
from django.core import management
from django.db import connection
from django.db import transaction
from django.utils import timezone

from oauthlib.oauth2 import BackendApplicationClient
import requests
from requests_oauthlib import OAuth2Session
from retrying import retry
from semantic_version import Version

from mds import enums
from mds import models
from mds import utils


ACCEPTED_MDS_VERSIONS = ["0.2", "0.3"]

logger = logging.getLogger(__name__)


class OAuth2Store(threading.local):
    def __init__(self):
        super().__init__()
        self.token_cache = {}

    def get_client(self, provider):
        """Authenticate using the Backend Application Flow from OAuth2."""
        client_id = provider.api_authentication["client_id"]
        token = self._get_access_token(provider)
        client = OAuth2Session(client_id, token=token)
        return client

    def _get_access_token(self, provider):
        """Fetch and cache the token."""
        if provider not in self.token_cache:
            self.token_cache[provider] = self._fetch_access_token(provider)
        return self.token_cache[provider]

    @retry(stop_max_attempt_number=2)
    def _fetch_access_token(self, provider):
        """Fetch an access token from the provider"""
        client_id = provider.api_authentication["client_id"]
        client_secret = provider.api_authentication["client_secret"]
        client = BackendApplicationClient(client_id=client_id)
        session = OAuth2Session(client=client)

        # The URL to fetch the token maybe on another base URL
        token_url = provider.oauth2_url
        if not token_url:
            token_url = urllib.parse.urljoin(provider.base_api_url, "/oauth2/token")
            if provider.api_configuration.get("trailing_slash"):
                token_url += "/"

        # Provider-specific parameters to request the token
        kwargs = {}
        try:
            kwargs.update(provider.api_configuration["token_params"])
        except KeyError:
            pass

        token = session.fetch_token(
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            **kwargs
        )
        return token


oauth2_store = OAuth2Store()


class Command(management.BaseCommand):
    help = "Poll providers to fetch their latest data."

    def handle(self, *args, **options):
        self.verbosity = options["verbosity"]
        self.token_cache = {}
        self.providers = set(models.Provider.objects.values_list("pk", flat=True))
        self.devices = set(models.Device.objects.values_list("pk", flat=True))

        for provider in models.Provider.objects.all():
            if not provider.base_api_url:
                self.stdout.write(
                    "Provider %s has no URL defined, skipping." % provider.name
                )
                continue

            self.stdout.write("Polling %s... " % provider.name, ending="")

            try:
                self.poll_status_changes(provider)
            except Exception:  # pylint: disable=broad-except
                logger.exception("Error in polling provider %s", provider.name)
                self.stdout.write("Polling failed!")
                # Try the next provider anyway
                continue

            self.stdout.write("Success!")

    def poll_status_changes(self, provider):
        next_url = urllib.parse.urljoin(provider.base_api_url, "status_changes")
        if provider.api_configuration.get("trailing_slash"):
            next_url += "/"

        params = {}

        # Start where we left, it's all based on providers sorting by start_time, obviously
        # (we wouldn't know if the provider recorded late telemetries earlier than this date)
        if provider.last_start_time_polled:
            params["start_time"] = utils.to_mds_timestamp(
                provider.last_start_time_polled
            )

        # Provider-specific params to optimise polling
        try:
            params.update(provider.api_configuration["status_changes_params"])
        except KeyError:
            pass

        if params:
            next_url = "%s?%s" % (next_url, urllib.parse.urlencode(params))

        # Pagination
        while next_url:
            body = self.get_body(provider, next_url)
            # Translate older versions of data
            translated_data = translate_data(body["data"], body["version"])
            status_changes = translated_data["status_changes"]
            if not status_changes:
                break

            # A transaction for each "page" of data
            with transaction.atomic():
                last_start_time_polled = self.process_status_changes(
                    status_changes, provider
                )
                provider.last_start_time_polled = last_start_time_polled
                provider.save()

            next_url = body.get("links", {}).get("next")

    @retry(stop_max_attempt_number=2)
    def get_body(self, provider, url):
        authentication_type = provider.api_authentication.get("type")
        if authentication_type in (None, "", "none"):
            client = requests
        elif authentication_type == "oauth2":
            client = oauth2_store.get_client(provider)
        else:
            raise NotImplementedError

        headers = {}
        accepted_content_types = ["application/json"]
        # Add versioning header (some providers may choke on this)
        for version in ACCEPTED_MDS_VERSIONS:
            accepted_content_types.append(
                "application/vnd.mds.provider+json;version=%s" % version
            )
        headers["Accept"] = ", ".join(accepted_content_types)

        if self.verbosity > 1:
            self.stdout.write("Polling provider on URL %s" % url)
        response = client.get(url, timeout=30, headers=headers)
        # When we get a 401 with oauth2, we should try renewing the access token,
        # but when we try every minute, we're just delaying that retrial
        response.raise_for_status()

        # Servers should send what version of the API was served
        # but we rather trust the versioning in the body
        content_type = response.headers.get(
            "Content-Type", "application/json; charset=UTF-8"
        )
        if content_type.startswith("application/json"):
            version = "unspecified"
        else:
            # Let it raise if malformed
            content_type, version = content_type.split(";")
            _, version = version.split("=")
        if self.verbosity > 1:
            self.stdout.write("Provider pretends to accept version %s" % version)

        body = response.json()
        return body

    def process_status_changes(self, status_changes, provider):
        if self.verbosity > 1:
            self.stdout.write("Processing...")

        # We already had the surprise of not receiving a integer timestamp but its string representation
        status_changes = self.validate_event_times(status_changes)
        if not status_changes:
            # Data so bad there is no or nothing but invalid event times
            logger.exception(
                "No valid event_time found in status_changes series: %s", status_changes
            )
            # How can we prevent from asking them again next time?
            if provider.last_start_time_polled:
                return provider.last_start_time_polled + datetime.timedelta(
                    milliseconds=1
                )
            # The provider really doesn't help!
            return timezone.now()

        # What is the latest event recorded in that series? (order is not asserted in the specs)
        last_event_time_polled = utils.from_mds_timestamp(
            max(status_change["event_time"] for status_change in status_changes)
        )

        status_changes = self.validate_status_changes(status_changes, provider)
        if not status_changes:
            # None were valid, we won't ask that series again
            # (provided status changes are ordered by event_time ascending)
            return last_event_time_polled

        self.create_missing_providers(status_changes)
        self.create_missing_devices(status_changes)
        self.create_event_records(status_changes)

        return last_event_time_polled

    def validate_event_times(self, status_changes):
        """I need this one done before validating the rest of the data."""
        validated_status_changes = []

        for status_change in status_changes:
            try:
                status_change["event_time"] = int(status_change["event_time"])
            except (KeyError, ValueError):
                logger.warning(
                    "status_change %s has no valid event_time", status_change
                )
                continue
            validated_status_changes.append(status_change)

        return validated_status_changes

    def validate_status_changes(self, status_changes, provider):
        """Some preliminary checks/addenda"""
        validated_status_changes = []

        for status_change in status_changes:
            status_change["provider_id"] = uuid.UUID(status_change["provider_id"])
            status_change["device_id"] = device_id = uuid.UUID(
                status_change["device_id"]
            )

            # The list of event types and even the naming don't match between
            # the provider and agency APIs, so translate one to the other
            try:
                event_type_reason = status_change["event_type_reason"]
            except KeyError:  # Spec violation!
                logger.warning("Device %s has no event_type_reason", device_id)
                # Ignore just that status change to avoid rejecting the whole batch
                continue
            try:
                agency_event_type = enums.PROVIDER_EVENT_TYPE_REASON_TO_AGENCY_EVENT_TYPE[
                    event_type_reason
                ]
            except KeyError:  # Spec violation!
                logger.warning(
                    'Device %s has unknown "%s" event_type_reason',
                    device_id,
                    event_type_reason,
                )
                # Ignore just that status change to avoid rejecting the whole batch
                continue
            status_change["agency_event_type"] = agency_event_type

            event_location = status_change["event_location"]
            if event_location:
                assert event_location["geometry"]["type"] == "Point"
                # Some providers may get the (lng, lat) order wrong
                if provider.api_configuration.get("swap_lng_lat"):
                    lat, lng = event_location["geometry"]["coordinates"][:2]
                    event_location["geometry"]["coordinates"][0] = lng
                    event_location["geometry"]["coordinates"][1] = lat
            else:  # Spec violation!
                logger.warning("Device %s has no event_location", device_id)
                # This time, accept a status change with no location

            validated_status_changes.append(status_change)

        return validated_status_changes

    def create_missing_providers(self, status_changes):
        """Make sure all providers mentioned exist"""

        for status_change in status_changes:
            provider_id = status_change["provider_id"]
            if provider_id not in self.providers:
                name = status_change["provider_name"]
                device_category = status_change["vehicle_type"]

                models.Provider.objects.create(
                    pk=provider_id, name=name, device_category=device_category
                )
                self.providers.add(provider_id)
                self.stdout.write("Provider %s was created." % name)

    def create_missing_devices(self, status_changes):
        """Make sure all devices mentioned exist"""

        with_missing_devices = [
            status_change
            for status_change in status_changes
            if status_change["device_id"] not in self.devices
        ]

        with connection.cursor() as cursor:
            cursor.executemany(
                """INSERT INTO mds_device (
                    id,
                    provider_id,
                    registration_date,
                    identification_number,
                    category,
                    model,
                    propulsion,
                    manufacturer
                ) VALUES (
                    %(id)s,
                    %(provider_id)s,
                    %(registration_date)s,
                    %(identification_number)s,
                    %(category)s,
                    %(model)s,
                    %(propulsion)s,
                    %(manufacturer)s
                ) ON CONFLICT DO NOTHING
                """,
                (
                    create_device(status_change)
                    for status_change in with_missing_devices
                ),
            )

        devices_added = [
            str(status_change["device_id"]) for status_change in with_missing_devices
        ]
        if devices_added:
            self.devices.update(devices_added)
            self.stdout.write("Devices created: %s" % ", ".join(devices_added))

    def create_event_records(self, status_changes):
        """Now record the... records"""

        # Timestamps are unique per device, ignore duplicates
        with connection.cursor() as cursor:
            # Using "upsert"
            cursor.executemany(
                """INSERT INTO mds_eventrecord (
                    device_id,
                    timestamp,
                    source,
                    point,
                    event_type,
                    properties,
                    saved_at
                ) VALUES (
                    %(device_id)s,
                    %(timestamp)s,
                    %(source)s,
                    %(point)s,
                    %(event_type)s,
                    %(properties)s,
                    %(saved_at)s
                ) ON CONFLICT DO NOTHING
                """,
                (
                    create_event_record(status_change)
                    for status_change in status_changes
                ),
            )


def create_device(status_change):
    device_id = status_change["device_id"]
    identification_number = status_change["vehicle_id"]
    if not identification_number:  # Spec violation!
        identification_number = "test-%s" % str(device_id).split("-", 1)

    return {
        "id": device_id,
        # Don't assume the device received belongs to the provider requested
        # The LA sandbox contains data for several providers
        "provider_id": status_change["provider_id"],
        "registration_date": timezone.now(),
        "identification_number": identification_number,
        "category": status_change["vehicle_type"],
        "model": "",
        "propulsion": status_change["propulsion_type"],
        "manufacturer": "",
    }


def create_event_record(status_change):
    properties = {"trip_id": status_change.get("associated_trip")}

    event_location = status_change["event_location"]
    if event_location:
        # GeoJSON Point Feature
        try:
            longitude, latitude, altitude = event_location["geometry"]["coordinates"]
        except ValueError:
            longitude, latitude = event_location["geometry"]["coordinates"]
            altitude = None
        point = geos.Point(longitude, latitude, altitude, srid=4326)
        properties["telemetry"] = {
            "timestamp": event_location["properties"]["timestamp"],
            "gps": {"lng": longitude, "lat": latitude},
            # No coordinates, no battery charge saved
            "battery_pct": status_change.get("battery_pct"),
        }
        if altitude:
            properties["telemetry"]["gps"]["altitude"] = altitude
    else:  # Spec violation!
        point = None

    return {
        "device_id": status_change["device_id"],
        "timestamp": utils.from_mds_timestamp(status_change["event_time"]),
        "source": "pull",  # pulled by agency,
        "point": point.ewkt if point else None,
        "event_type": status_change["agency_event_type"],
        "properties": json.dumps(properties),
        "saved_at": timezone.now(),
    }


def translate_data(data, version):
    version = Version(version)

    if version >= Version("0.3.0") and version < Version("0.4.0"):
        return data

    if version >= Version("0.2.0"):
        # The only two noticeable changes from our point of view are:
        # - timestamps converted from floating-point seconds to milliseconds;
        # - "trip_ids" now is a single "trip_id"
        for status_change in data["status_changes"]:
            # We were already expecting milliseconds in the 0.2 implementation
            if "." in str(status_change["event_time"]):
                status_change["event_time"] = round(status_change["event_time"] * 1000)
            # Keep only the first (and probably only) trip ID
            associated_trip = status_change.pop("associated_trips", None)
            if associated_trip:
                status_change["associated_trip"] = associated_trip[0]
        return data

    raise NotImplementedError(version)
