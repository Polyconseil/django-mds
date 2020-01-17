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

from . import v0_2


MDS_CONTENT_TYPE = "application/vnd.mds.provider+json"


logger = logging.getLogger(__name__)


# polling_cursor configuration field translated to query parameter
class POLLING_CURSORS(enum.Enum):
    start_time = "start_time"  # from the MDS specification
    start_recorded = "start_recorded"  # vendor only, 0.3 only
    total_events = "skip"  # vendor only, 0.3 only


class StatusChangesPoller(v0_2.StatusChangesPoller):
    """Override only what changed between 0.2 and 0.3."""

    def _poll_status_changes(self):
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
            body = self._get_body(next_url)
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

        # Some server implementations are flawed
        # leave the standard content type even in 0.3
        headers["Accept"] = "application/json,%s;version=%s" % (
            MDS_CONTENT_TYPE,
            self.api_version,
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
        if received != self.api_version:
            logger.warning(
                "Provider %s didn't respond in version %s but %s",
                self.provider.name,
                self.api_version,
                received,
            )

        body = response.json()
        return body
