"""
Pulling data for registered providers

This is the opposite of provider pushing their data to the agency API.
"""
import datetime
import enum
import logging
import urllib.parse

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_duration

import requests
from retrying import retry

from mds import utils

from . import v0_3


MDS_CONTENT_TYPE = "application/vnd.mds.provider+json"


logger = logging.getLogger(__name__)


# polling_cursor configuration field translated to query parameter
class POLLING_CURSORS(enum.Enum):
    start_time = "start_time"  # from the MDS specification


class StatusChangesPoller(v0_3.StatusChangesPoller):
    """Override only what changed between 0.3 and 0.4."""

    def _poll_status_changes(self):
        # Start where we left, it's all based on providers sorting by start_time
        # (but we would miss telemetries older than start_time saved after we polled).
        # For those that support it, use the recorded time field or equivalent.
        polling_cursor = self.cursor or self.provider.api_configuration.get(
            "polling_cursor", POLLING_CURSORS.start_time.name
        )
        # We dropped other cursor types
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
        last_event_time_polled = (
            self.from_cursor or self.provider.last_event_time_polled
        )
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
            params["start_time"] = utils.to_mds_timestamp(last_event_time_polled)
            # Both bounds are mandatory now, use the lag as the event horizon
            # The provider will slice big results using pagination
            end_time = timezone.now()
            if polling_lag:
                # We tested the lag above, so end_time can't be older than start_time
                end_time -= polling_lag
            params["end_time"] = utils.to_mds_timestamp(end_time)

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
            body = self._get_body(next_url)
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
    def _get_body(self, url):
        authentication_type = self.provider.api_authentication.get("type")
        if authentication_type in (None, "", "none"):
            client = requests
        elif authentication_type == "oauth2":
            client = self.oauth2_store.get_client()
        else:
            raise NotImplementedError

        headers = {}

        # We only accept the version we expect from that provider
        # And it should reject it when it bumps to the new version
        headers["Accept"] = "%s;version=%s" % (MDS_CONTENT_TYPE, self.api_version)

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
        if received != self.api_version:
            logger.warning(
                "Provider %s didn't respond in version %s but %s",
                self.provider.name,
                self.api_version,
                received,
            )

        body = response.json()
        return body
