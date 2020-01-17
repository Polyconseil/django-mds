"""
Pulling data for registered providers

This is the opposite of provider pushing their data to the agency API.
"""
import datetime
import enum
import logging
import urllib.parse
import uuid

from django.conf import settings
from django.contrib.gis import geos
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_duration

import requests
from retrying import retry

from mds import db_helpers
from mds import enums
from mds import models
from mds import utils
from mds.provider_mapping import PROVIDER_REASON_TO_AGENCY_EVENT
from .oauth2_store import OAuth2Store
from .translation import translate_v0_2_to_v0_4


MDS_CONTENT_TYPE = "application/vnd.mds.provider+json"


logger = logging.getLogger(__name__)


# polling_cursor configuration field translated to query parameter
class POLLING_CURSORS(enum.Enum):
    start_time = "start_time"  # from the MDS specification
    start_recorded = "start_recorded"  # vendor only, 0.3 only
    total_events = "skip"  # vendor only, 0.3 only


class StatusChangesPoller:
    """Poll the given provider to fetch its latest data.

    Polling is automatically resumed from what was last saved in the provider config,
    unless cursor parameters are given.

    The from and to cursor values depend on the cursor type:
    - integer timestamp in milliseconds for "start_recorded" and "start_time"
    - integer count of lines for "total_events" (think LIMIT in SQL)

    Args:
        provider: Provider, the provider to poll
        cursor: POLLING_CURSORS, cursor type
        from_cursor: timestamp or int, lower limit
        to_cursor: timestamp or int, upper limit
    """

    def __init__(self, provider, cursor=None, from_cursor=None, to_cursor=None):
        self.provider = provider
        self.cursor = cursor
        self.from_cursor = from_cursor
        self.to_cursor = to_cursor
        self.oauth2_store = OAuth2Store(provider)
        # While we poll a given provider, it may aggregate data from several providers
        # There's no difference yet between a service provider and a pure data provider
        # (these are sets of UUIDs, not str)
        self.provider_uids = set(models.Provider.objects.values_list("pk", flat=True))
        self.device_uids = set(models.Device.objects.values_list("pk", flat=True))

    def poll(self):
        if not self.provider.base_api_url:
            logger.debug("Provider %s has no URL, skipping.", self.provider.name)
            return

        # We request a specific version of the Provider API
        # TODO(hcauwelier) make it mandatory, see SMP-1673
        api_version_raw = self.provider.api_configuration.get(
            "api_version", enums.DEFAULT_PROVIDER_API_VERSION
        )
        # We store the enum key, which cannot be a numeric identifier
        # It doubles as a validity check
        api_version = enums.MDS_VERSIONS[api_version_raw].value

        logger.debug("Polling %s using version %s", self.provider.name, api_version)

        getattr(self, "_poll_status_changes_%s" % api_version_raw)(api_version)

    # TODO(hcauwelier) Should be deleted ASAP
    def _poll_status_changes_v0_2(self, api_version):
        # Start where we left, it's all based on providers sorting by start_time
        # (but we would miss telemetries older than start_time saved after we polled).
        # For those that support it, use the recorded time field or equivalent.
        polling_cursor = self.cursor or self.provider.api_configuration.get(
            "polling_cursor", POLLING_CURSORS.start_time.name
        )
        logger.info(
            f"Starting polling {self.provider} using the field: {polling_cursor}.\n"
            "Current state:\n"
            + (
                (
                    f"\tLast event_time: {str(self.provider.last_event_time_polled)},\n"
                    + f"\tLast recorded: {str(self.provider.last_recorded_polled)}\n"
                    + f"\tLast skip: {self.provider.last_skip_polled}."
                )
                if not self.cursor
                else f"\tCursor value: {self.from_cursor}."
            )
        )

        params = {}

        # Cursor param (raise if typo)
        param_name = POLLING_CURSORS[polling_cursor].value

        if polling_cursor == POLLING_CURSORS.total_events.name:
            # Resume from the last line fetched
            params[param_name] = self.from_cursor or self.provider.last_skip_polled
        elif polling_cursor == POLLING_CURSORS.start_recorded.name:
            # Resume from the last "recorded" value
            params[param_name] = utils.to_mds_timestamp(
                self.from_cursor or self.provider.last_recorded_polled
            )
        elif polling_cursor == POLLING_CURSORS.start_time.name:
            # Resume from the last "event_time" value
            last_event_time_polled = self.provider.last_event_time_polled
            if not last_event_time_polled:
                last_event_time_polled = timezone.now() - datetime.timedelta(
                    getattr(settings, "PROVIDER_POLLER_LIMIT", 90)
                )

            # But we now apply a "lag" before actually polling,
            # leaving time for the provider to collect data from its devices
            polling_lag = self.provider.api_configuration.get("provider_polling_lag")
            if polling_lag:
                polling_lag = parse_duration(polling_lag)
                if (timezone.now() - last_event_time_polled) < polling_lag:
                    logger.debug("Still under the polling lag, back to sleep.")
                    return

            params[param_name] = utils.to_mds_timestamp(
                self.from_cursor or last_event_time_polled
            )

        # Provider-specific params to optimise polling
        try:
            params.update(self.provider.api_configuration["status_changes_params"])
        except KeyError:
            pass

        next_url = urllib.parse.urljoin(self.provider.base_api_url, "status_changes")
        if self.provider.api_configuration.get("trailing_slash"):
            next_url += "/"

        if params:
            next_url = "%s?%s" % (next_url, urllib.parse.urlencode(params))

        skip_polled = (
            self.from_cursor
            if self.from_cursor and self.cursor == POLLING_CURSORS.total_events.name
            else None
        )

        # Pagination
        while next_url:
            body = self._get_body(next_url, api_version)
            # Translate older versions of data
            translated_data = translate_v0_2_to_v0_4(body["data"])
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

                if self.cursor:
                    if self.cursor == POLLING_CURSORS.total_events.name:
                        skip_polled += len(status_changes)
                        if skip_polled >= self.to_cursor:
                            break
                    elif self.cursor == POLLING_CURSORS.start_recorded.name:
                        if recorded_polled >= self.to_cursor:
                            break
                    elif self.cursor == POLLING_CURSORS.start_time.name:
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

    def _poll_status_changes_v0_3(self, api_version):
        # Start where we left, it's all based on providers sorting by start_time
        # (but we would miss telemetries older than start_time saved after we polled).
        # For those that support it, use the recorded time field or equivalent.
        polling_cursor = self.cursor or self.provider.api_configuration.get(
            "polling_cursor", POLLING_CURSORS.start_time.name
        )
        logger.info(
            f"Starting polling {self.provider} using the field: {polling_cursor}.\n"
            "Current state:\n"
            + (
                (
                    f"\tLast event_time: {str(self.provider.last_event_time_polled)},\n"
                    + f"\tLast recorded: {str(self.provider.last_recorded_polled)}\n"
                    + f"\tLast skip: {self.provider.last_skip_polled}."
                )
                if not self.cursor
                else f"\tCursor value: {self.from_cursor}."
            )
        )

        params = {}

        # Cursor param (raise if typo)
        param_name = POLLING_CURSORS[polling_cursor].value

        if polling_cursor == POLLING_CURSORS.total_events.name:
            # Resume from the last line fetched
            params[param_name] = self.from_cursor or self.provider.last_skip_polled
        elif polling_cursor == POLLING_CURSORS.start_recorded.name:
            # Resume from the last "recorded" value
            params[param_name] = utils.to_mds_timestamp(
                self.from_cursor or self.provider.last_recorded_polled
            )
        elif polling_cursor == POLLING_CURSORS.start_time.name:
            # Resume from the last "event_time" value
            last_event_time_polled = self.provider.last_event_time_polled
            if not last_event_time_polled:
                last_event_time_polled = timezone.now() - datetime.timedelta(
                    getattr(settings, "PROVIDER_POLLER_LIMIT", 90)
                )

            # But we now apply a "lag" before actually polling,
            # leaving time for the provider to collect data from its devices
            polling_lag = self.provider.api_configuration.get("provider_polling_lag")
            if polling_lag:
                polling_lag = parse_duration(polling_lag)
                if (timezone.now() - last_event_time_polled) < polling_lag:
                    logger.debug("Still under the polling lag, back to sleep.")
                    return

            params[param_name] = utils.to_mds_timestamp(
                self.from_cursor or last_event_time_polled
            )

        # Provider-specific params to optimise polling
        try:
            params.update(self.provider.api_configuration["status_changes_params"])
        except KeyError:
            pass

        next_url = urllib.parse.urljoin(self.provider.base_api_url, "status_changes")
        if self.provider.api_configuration.get("trailing_slash"):
            next_url += "/"

        if params:
            next_url = "%s?%s" % (next_url, urllib.parse.urlencode(params))

        skip_polled = (
            self.from_cursor
            if self.from_cursor and self.cursor == POLLING_CURSORS.total_events.name
            else None
        )

        # Pagination
        while next_url:
            body = self._get_body(next_url, api_version)
            # MDS 0.3 is backwards compatible with 0.4
            status_changes = body["data"]["status_changes"]
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

                if self.cursor:
                    if self.cursor == POLLING_CURSORS.total_events.name:
                        skip_polled += len(status_changes)
                        if skip_polled >= self.to_cursor:
                            break
                    elif self.cursor == POLLING_CURSORS.start_recorded.name:
                        if recorded_polled >= self.to_cursor:
                            break
                    elif self.cursor == POLLING_CURSORS.start_time.name:
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

    def _poll_status_changes_v0_4(self, api_version):
        # Start where we left, it's all based on providers sorting by start_time
        # (but we would miss telemetries older than start_time saved after we polled).
        # For those that support it, use the recorded time field or equivalent.
        polling_cursor = self.cursor or self.provider.api_configuration.get(
            "polling_cursor", POLLING_CURSORS.start_time.name
        )
        if polling_cursor != POLLING_CURSORS.start_time.name:
            raise ValueError('Only "start_time" cursor is supported in MDS 0.4+')
        logger.info(
            f"Starting polling {self.provider} using the field: {polling_cursor}.\n"
            "Current state:\n"
            + (
                (f"\tLast event_time: {str(self.provider.last_event_time_polled)}.")
                if not self.cursor
                else f"\tCursor value: {self.from_cursor}."
            )
        )

        params = {}

        # Resume from the last "event_time" value
        last_event_time_polled = self.provider.last_event_time_polled
        if not last_event_time_polled:
            last_event_time_polled = timezone.now() - datetime.timedelta(
                getattr(settings, "PROVIDER_POLLER_LIMIT", 90)
            )

        # But we now apply a "lag" before actually polling,
        # leaving time for the provider to collect data from its devices
        polling_lag = self.provider.api_configuration.get("provider_polling_lag")
        if polling_lag:
            polling_lag = parse_duration(polling_lag)
            if (timezone.now() - last_event_time_polled) < polling_lag:
                logger.info("Still under the polling lag, back to sleep.")
                return

        # The MDS 0.4 Provider API got two endpoints:
        # - /events for the real-time or so data (formerly /status_changes)
        #   but limited to two weeks of history
        # - /status_changes for all the data except the current hour
        # If we're catching up far in time, begin by polling /status_changes
        realtime_threshold = parse_duration(  # Default is 9 days
            self.provider.api_configuration.get("realtime_threshold", "P9D")
        )
        next_event_time = last_event_time_polled + datetime.timedelta(hours=1)
        if (timezone.now() - next_event_time) > realtime_threshold:
            # We have to query the archived status changes with another format
            logger.info("last_event_time_polled is too old, asking archives")
            # We're done with the events of the last hour, ask the next hour
            params["event_time"] = next_event_time.isoformat()[: len("YYYY-MM-DDTHH")]
        else:
            # Query the real-time endpoint as usual
            params["start_time"] = utils.to_mds_timestamp(
                self.from_cursor or last_event_time_polled
            )

        # Provider-specific params to optimise polling
        try:
            params.update(self.provider.api_configuration["status_changes_params"])
        except KeyError:
            pass

        endpoint = "events"  # The new name for the real-time events endpoint
        if "event_time" in params:
            # We asked the archived status changes instead
            endpoint = "status_changes"
        next_url = urllib.parse.urljoin(self.provider.base_api_url, endpoint)
        if self.provider.api_configuration.get("trailing_slash"):
            next_url += "/"

        if params:
            next_url = "%s?%s" % (next_url, urllib.parse.urlencode(params))

        # Pagination
        while next_url:
            body = self._get_body(next_url, api_version)
            # No translation needed as long as 0.4 is the latest version
            status_changes = body["data"]["status_changes"]
            next_url = body.get("links", {}).get("next")

            # A transaction for each "page" of data
            with transaction.atomic():
                if status_changes:
                    # We get the maximum values from the status changes
                    event_time_polled, _ = self._process_status_changes(status_changes)
                elif endpoint == "status_changes":
                    # This hour frame of archives didn't contain results
                    event_time_polled = next_event_time
                else:
                    # Try again from this point later
                    break

                if self.cursor:
                    if self.cursor == POLLING_CURSORS.start_time.name:
                        if event_time_polled >= self.to_cursor:
                            break
                else:
                    self.provider.last_event_time_polled = event_time_polled
                    self.provider.save(update_fields=["last_event_time_polled"])

                logger.info(
                    f"Polled page using cursor: {polling_cursor}. New state:\n"
                    + f"\tLast event_time: {str(event_time_polled)}."
                )

    @retry(stop_max_attempt_number=2)
    def _get_body(self, url, api_version):
        authentication_type = self.provider.api_authentication.get("type")
        if authentication_type in (None, "", "none"):
            client = requests
        elif authentication_type == "oauth2":
            client = self.oauth2_store.get_client()
        else:
            raise NotImplementedError

        headers = {}

        # TODO(hcauwelier) just fork the code for MDS 0.4
        if api_version == "0.4":
            # We only accept the version we expect from that provider
            # And it should reject it when it bumps to the new version
            headers["Accept"] = "%s;version=%s" % (MDS_CONTENT_TYPE, api_version)
        else:
            # TODO(hcauwelier) some server implementations are flawed
            # leave the standard content type for now
            headers["Accept"] = "application/json,%s;version=%s" % (
                MDS_CONTENT_TYPE,
                api_version,
            )

        logger.debug("Polling provider on URL %s with headers %s", url, headers)
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
            received = "unspecified"
        else:
            # Let it raise if malformed
            params = content_type.split(";")
            content_type = params.pop(0)
            assert content_type == MDS_CONTENT_TYPE
            params = dict(param.split("=") for param in params)
            received = params.get("version", "unspecified")
        if received != api_version:
            logger.warning(
                "Provider %s didn't respond in version %s but %s",
                self.provider.name,
                api_version,
                received,
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
                event = PROVIDER_REASON_TO_AGENCY_EVENT[event_type_reason]
                agency_event_type, agency_event_type_reason = (
                    event if len(event) == 2 else event + (None,)
                )
            except KeyError:  # Spec violation!
                logger.warning(
                    'Device %s has unknown "%s" event_type_reason',
                    device_id,
                    event_type_reason,
                )
                # Ignore just that status change to avoid rejecting the whole batch
                continue
            status_change["agency_event_type"] = agency_event_type
            status_change["agency_event_type_reason"] = agency_event_type_reason

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
            if getattr(settings, "POLLER_CREATE_REGISTER_EVENTS", False):
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

    publication_time = None
    if status_change.get("publication_time"):
        publication_time = utils.from_mds_timestamp(status_change["publication_time"])
    # "Aggregation" providers store a recorded field, and we want to keep the same value
    # until we get the publication_time everywhere
    # Vendor only, 0.3 only, will disappear
    recorded = None
    if status_change.get("recorded"):
        recorded = utils.from_mds_timestamp(status_change["recorded"])
    if publication_time and recorded:
        difference = abs(publication_time - recorded)
        if difference > datetime.timedelta(minutes=10):
            logger.warning("publication_time and recorded differ by %s", difference)

    return models.EventRecord(
        device_id=status_change["device_id"],
        timestamp=utils.from_mds_timestamp(status_change["event_time"]),
        point=point,
        event_type=status_change["agency_event_type"],
        event_type_reason=status_change["agency_event_type_reason"],
        properties=properties,
        publication_time=publication_time or recorded,
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
