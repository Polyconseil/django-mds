"""
Pulling data for registered providers

This is the opposite of provider pushing their data to the agency API.
"""
import datetime
import enum
import logging
import urllib.parse
import uuid

from django.contrib.gis import geos
from django.db import transaction
from django.utils import timezone

import requests
from retrying import retry

from mds import db_helpers
from mds import enums
from mds import models
from mds import utils
from .oauth2_store import OAuth2Store
from .translation import translate_data
from .settings import PROVIDER_POLLER_LIMIT_DAYS


ACCEPTED_MDS_VERSIONS = ["0.2", "0.3"]
POLLING_CURSOR_TO_QUERY_PARAM = enum.Enum(
    "polling_cursor field to the query parameter",
    [
        ("start_recorded", "start_recorded"),
        ("start_time", "start_time"),
        ("total_events", "skip"),
    ],
)

logger = logging.getLogger(__name__)


def get_date_param(last_event):
    if last_event:
        return utils.to_mds_timestamp(last_event)
    elif PROVIDER_POLLER_LIMIT_DAYS:
        delta = timezone.now() - datetime.timedelta(PROVIDER_POLLER_LIMIT_DAYS)
        logger.debug(f"No last_event on provider, starting from: {str(delta)}")
        return utils.to_mds_timestamp(delta)


class StatusChangesPoller:
    """Poll all providers to fetch their latest telemetry data."""

    def __init__(self, provider, cursor=None, from_cursor=None, to_cursor=None):
        self.provider = provider
        self.overriden_cursor = cursor
        self.from_cursor = from_cursor
        self.to_cursor = to_cursor
        self.oauth2_store = OAuth2Store(provider)
        # While we poll a given provider, it may aggegrate data from several providers
        # (these are sets of UUIDs, not str)
        self.provider_uids = set(models.Provider.objects.values_list("pk", flat=True))
        self.device_uids = set(models.Device.objects.values_list("pk", flat=True))

    def poll(self):
        if not self.provider.base_api_url:
            logger.debug("Provider %s has no URL, skipping.", self.provider.name)
            return
        logger.debug(f"Polling {self.provider.name}")
        self._poll_status_changes()

    def _poll_status_changes(self):
        next_url = urllib.parse.urljoin(self.provider.base_api_url, "status_changes")
        if self.provider.api_configuration.get("trailing_slash"):
            next_url += "/"

        params = {}
        # Start where we left, it's all based on providers sorting by start_time
        # (but we would miss telemetries older than start_time saved after we polled).
        # For those that support it, use the recorded time field or equivalent.
        polling_cursor = self.overriden_cursor or self.provider.api_configuration.get(
            "polling_cursor", POLLING_CURSOR_TO_QUERY_PARAM.start_time.name
        )
        logger.info(
            f"Starting polling using the field: {polling_cursor}. Current state:\n"
            + (
                (
                    f"\tLast event_time: {str(self.provider.last_event_time_polled)},\n"
                    + f"\tLast recorded: {str(self.provider.last_recorded_polled)}\n"
                    + f"\tLast skip: {self.provider.last_skip_polled}."
                )
                if not self.overriden_cursor
                else f"\tCursor value: {self.from_cursor}."
            )
        )

        # skip
        if polling_cursor == POLLING_CURSOR_TO_QUERY_PARAM.total_events.name:
            params[POLLING_CURSOR_TO_QUERY_PARAM.total_events.value] = (
                self.from_cursor or self.provider.last_skip_polled
            )
        # start_recorded
        elif polling_cursor == POLLING_CURSOR_TO_QUERY_PARAM.start_recorded.name:
            params[POLLING_CURSOR_TO_QUERY_PARAM.start_recorded.value] = get_date_param(
                self.from_cursor or self.provider.last_recorded_polled
            )
        # start_time
        elif polling_cursor == POLLING_CURSOR_TO_QUERY_PARAM.start_time.name:
            params[POLLING_CURSOR_TO_QUERY_PARAM.start_time.value] = get_date_param(
                self.from_cursor or self.provider.last_event_time_polled
            )

        # Provider-specific params to optimise polling
        try:
            params.update(self.provider.api_configuration["status_changes_params"])
        except KeyError:
            pass

        if params:
            next_url = "%s?%s" % (next_url, urllib.parse.urlencode(params))

        skip_polled = (
            self.from_cursor
            if self.from_cursor
            and self.overriden_cursor == POLLING_CURSOR_TO_QUERY_PARAM.total_events.name
            else None
        )

        # Pagination
        while next_url:
            body = self._get_body(next_url)
            # Translate older versions of data
            translated_data = translate_data(body["data"], body["version"])
            status_changes = translated_data["status_changes"]
            if not status_changes:
                break

            next_url = body.get("links", {}).get("next")

            # A transaction for each "page" of data
            with transaction.atomic():
                # We get the maximum of the recorded and event_types
                # from the status changes
                event_time_polled, recorded_polled = self._process_status_changes(
                    status_changes
                )
                if self.overriden_cursor:
                    if (
                        polling_cursor
                        == POLLING_CURSOR_TO_QUERY_PARAM.total_events.name
                    ):
                        skip_polled += len(status_changes)
                        if skip_polled >= self.to_cursor:
                            break
                    elif (
                        polling_cursor
                        == POLLING_CURSOR_TO_QUERY_PARAM.start_recorded.name
                    ):
                        if recorded_polled >= self.to_cursor:
                            break
                    elif (
                        polling_cursor == POLLING_CURSOR_TO_QUERY_PARAM.start_time.name
                    ):
                        if event_time_polled >= self.to_cursor:
                            break
                else:
                    # We get the new skip from the number of status changes
                    skip_polled = (
                        self.provider.last_skip_polled + len(status_changes)
                        if self.provider.last_skip_polled
                        else len(status_changes)
                    )
                    self.provider.last_event_time_polled = event_time_polled
                    self.provider.last_recorded_polled = recorded_polled
                    self.provider.last_skip_polled = skip_polled
                    self.provider.save(
                        update_fields=[
                            "last_event_time_polled",
                            "last_recorded_polled",
                            "last_skip_polled",
                        ]
                    )

                logger.info(
                    f"Polled page using cursor: {polling_cursor}. New state:\n"
                    + f"\tLast event_time: {str(event_time_polled)},\n"
                    + f"\tLast recorded: {str(recorded_polled)}\n"
                    + f"\tLast skip: {skip_polled}."
                )

    @retry(stop_max_attempt_number=2)
    def _get_body(self, url):
        authentication_type = self.provider.api_authentication.get("type")
        if authentication_type in (None, "", "none"):
            client = requests
        elif authentication_type == "oauth2":
            client = self.oauth2_store.get_client()
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

        logger.debug("Polling provider on URL %s", url)
        response = client.get(url, timeout=30, headers=headers)
        # Token may be expired sooner than expected, retry in one minute
        if response.status_code in (401, 403):
            self.oauth2_store.flush_token()
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
        logger.debug(
            "Provider %s pretends to accept version %s", self.provider.name, version
        )

        body = response.json()
        return body

    def _process_status_changes(self, status_changes):
        logger.debug("Processing...")

        # accept timestamp as a string instead of an integer
        status_changes = self._validate_event_times(status_changes)
        if not status_changes:
            # Data so bad there is no or nothing but invalid event times
            logger.exception(
                "No valid event_time found in status_changes series: %s", status_changes
            )
            # How can we prevent from asking them again next time?
            if (
                self.provider.last_event_time_polled
                and self.provider.last_recorded_polled
            ):
                ms = datetime.timedelta(milliseconds=1)
                return (
                    self.provider.last_event_time_polled + ms,
                    self.provider.last_recorded_polled + ms,
                )

            # The provider really doesn't help!
            return timezone.now(), timezone.now()

        last_event_time_polled = utils.from_mds_timestamp(
            max(status_change["event_time"] for status_change in status_changes)
        )
        last_recorded_polled = utils.from_mds_timestamp(
            max(status_change.get("recorded") or 0 for status_change in status_changes)
        )

        status_changes = self._validate_status_changes(status_changes)
        if not status_changes:
            # None were valid, we won't ask that series again
            # (provided status changes are ordered by event_time ascending)
            return last_event_time_polled, last_recorded_polled

        self._create_missing_providers(status_changes)
        self._create_missing_devices(status_changes)
        self._create_event_records(status_changes)

        return last_event_time_polled, last_recorded_polled

    def _validate_event_times(self, status_changes):
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

    def _validate_status_changes(self, status_changes):
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
                agency_event_type = enums.PROVIDER_REASON_TO_AGENCY_EVENT[
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
                if self.provider.api_configuration.get("swap_lng_lat"):
                    lat, lng = event_location["geometry"]["coordinates"][:2]
                    event_location["geometry"]["coordinates"][0] = lng
                    event_location["geometry"]["coordinates"][1] = lat
            else:  # Spec violation!
                logger.warning("Device %s has no event_location", device_id)
                # This time, accept a status change with no location

            validated_status_changes.append(status_change)

        return validated_status_changes

    def _create_missing_providers(self, status_changes):
        """Make sure all providers mentioned exist"""

        with_missing_providers = [
            status_change
            for status_change in status_changes
            if status_change["provider_id"] not in self.provider_uids
        ]

        if with_missing_providers:
            db_helpers.upsert_providers(
                (
                    _create_provider(status_change)
                    for status_change in with_missing_providers
                )
            )

            providers_added = [
                status_change["provider_id"] for status_change in with_missing_providers
            ]
            self.provider_uids.update(providers_added)

            logger.info(
                "Providers created: %s", ", ".join(str(uid) for uid in providers_added)
            )

    def _create_missing_devices(self, status_changes):
        """Make sure all devices mentioned exist"""

        with_missing_devices = [
            status_change
            for status_change in status_changes
            if status_change["device_id"] not in self.device_uids
        ]

        if with_missing_devices:
            db_helpers.upsert_devices(
                (
                    _create_device(status_change)
                    for status_change in with_missing_devices
                )
            )
            # Create fake register events to simulate device registration
            db_helpers.upsert_event_records(
                (
                    _create_register_event_record(status_change)
                    for status_change in with_missing_devices
                ),
                source=enums.EVENT_SOURCE.provider_api.name,
            )

            devices_added = [
                status_change["device_id"] for status_change in with_missing_devices
            ]
            self.device_uids.update(devices_added)

            logger.info(
                "Devices created: %s", ", ".join(str(uid) for uid in devices_added)
            )

    def _create_event_records(self, status_changes):
        """Now record the... records"""
        db_helpers.upsert_event_records(
            (_create_event_record(status_change) for status_change in status_changes),
            enums.EVENT_SOURCE.provider_api.name,
            # Timestamps are unique per device, ignore duplicates
            # Events already pushed by the provider will always have precedence
            on_conflict_update=False,
        )


def _create_provider(status_change):
    provider_id = status_change["provider_id"]
    try:
        name = status_change["provider_name"]
    except KeyError:  # Spec violation!
        logger.warning("Provider %s has no name", provider_id)
        name = ""

    return models.Provider(id=provider_id, name=name)


def _create_device(status_change):
    device_id = status_change["device_id"]
    identification_number = status_change["vehicle_id"]
    if not identification_number:  # Spec violation!
        logger.warning("Device %s has no identification number", device_id)
        identification_number = "test-%s" % str(device_id).split("-", 1)

    return models.Device(
        id=device_id,
        # Don't assume the device received belongs to the provider requested
        # The LA sandbox contains data for several providers
        provider_id=status_change["provider_id"],
        identification_number=identification_number,
        category=status_change["vehicle_type"],
        propulsion=status_change["propulsion_type"],
    )


def _create_event_record(status_change):
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

    first_saved_at = None
    # "Aggregation" layers store a recorded field, and we want to keep the same value
    if "recorded" in status_change and status_change["recorded"]:
        first_saved_at = utils.from_mds_timestamp(status_change["recorded"])

    return models.EventRecord(
        device_id=status_change["device_id"],
        timestamp=utils.from_mds_timestamp(status_change["event_time"]),
        point=point,
        event_type=status_change["agency_event_type"],
        properties=properties,
        first_saved_at=first_saved_at,
    )


def _create_register_event_record(status_change):
    """
    As the goal of the poller is to catch up with the history of a provider,
    simulate the registration of a device with a fake register event.

    This fake event is flagged in its properties to tell it apart from real ones.

    Should the device be unregistered and registered again according to the specs,
    don't delete the fake events in the past.
    """
    return models.EventRecord(
        device_id=status_change["device_id"],
        # Another event for the same device with the same timestamp will be rejected
        timestamp=utils.from_mds_timestamp(status_change["event_time"])
        - datetime.timedelta(milliseconds=1),
        event_type=enums.EVENT_TYPE.register.name,
        properties={"created_on_register": True},
        source=enums.EVENT_SOURCE.provider_api.name,
    )
