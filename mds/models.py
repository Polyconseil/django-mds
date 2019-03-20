"""
Database description
"""
import datetime
import json
import uuid

from django import forms, utils
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres import fields as pg_fields
from django.db import models
from django.db.models import OuterRef, Subquery, Prefetch
from django.utils import timezone

from rest_framework.utils import encoders

from . import enums


class UnboundedCharField(models.TextField):
    """Unlimited text, on a single line.

    Shows an ``<input type="text">`` in HTML but is stored as a TEXT
    column in Postgres (like ``TextField``).

    Like the standard :class:`~django.db.models.fields.CharField` widget,
    a ``select`` widget is automatically used if the field defines ``choices``.
    """

    def formfield(self, **kwargs):
        kwargs["widget"] = None if self.choices else forms.TextInput
        return super().formfield(**kwargs)


def agency_api_authentication_default():
    """Default value for the ``agency_api_authentication`` field.

    Other keys are specific to each type:
    - token: "header" and "token"
    - oauth2: "client_id" and "client_secret"
    """
    return {"type": "none"}


def agency_api_configuration_default():
    """Default value for the ``agency_api_configuration`` field."""
    return {}


def provider_api_authentication_default():
    """Default value for the API authentication field of a provider.

    Other keys are specific to each type:
    - token: "header" and "token"
    - oauth2: "client_id" and "client_secret"
    """
    return {"type": "none"}


def provider_api_configuration_default():
    """Default value for the API configuration field of a provider.

    Some provider implementations can be picky, configure these special cases here.
    """
    return {"trailing_slash": False}  # Some providers endpoint won't reply without it


def short_uuid4(uid):
    """When seeing a glimpse of the UID is enough."""
    return str(uid)[:8]  # Basically splitting on the first dash


class Provider(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = UnboundedCharField(default="")
    logo_b64 = UnboundedCharField(null=True, blank=True, default=None)
    device_category = UnboundedCharField(choices=enums.choices(enums.DEVICE_CATEGORY))

    # The following fields are for us pulling data from the provider
    base_api_url = UnboundedCharField(default="", verbose_name="Base Provider API URL")
    oauth2_url = UnboundedCharField(
        default="", verbose_name="OAuth2 URL (if different)"
    )
    api_authentication = pg_fields.JSONField(
        default=provider_api_authentication_default,
        verbose_name="Provider API Authentication",
    )
    api_configuration = pg_fields.JSONField(
        default=provider_api_configuration_default,
        verbose_name="Provider API Configuration",
    )
    # We may poll a provider, e.g. LADOT sandbox that replies for many providers
    # but has no device itself.
    # So we cannot just rely on checking the latest event record saved.
    last_start_time_polled = models.DateTimeField(blank=True, null=True)

    # The following fields are for the provider pushing data to us
    agency_api_authentication = pg_fields.JSONField(
        default=agency_api_authentication_default,
        verbose_name="Agency API Authentication",
    )
    agency_api_configuration = pg_fields.JSONField(
        default=agency_api_configuration_default,
        verbose_name="Agency API Configuration",
    )

    def __str__(self):
        return "{} ({})".format(self.name, short_uuid4(self.id))


class DeviceQueryset(models.QuerySet):
    def with_latest_event(self):
        return self.prefetch_related(
            Prefetch(
                "event_records",
                queryset=EventRecord.objects.filter(
                    id__in=Subquery(
                        EventRecord.objects.filter(device_id=OuterRef("device_id"))
                        .exclude(event_type="telemetry")
                        .order_by("-timestamp")
                        .values_list("id", flat=True)[:1]
                    )
                ),
                to_attr="_latest_event",
            )
        )


class Device(models.Model):
    """A device
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    provider = models.ForeignKey(
        Provider, related_name="devices", on_delete=models.CASCADE
    )
    registration_date = models.DateTimeField(default=timezone.now)
    identification_number = UnboundedCharField()

    category = UnboundedCharField(choices=enums.choices(enums.DEVICE_CATEGORY))
    model = UnboundedCharField(default="")
    propulsion = pg_fields.ArrayField(
        UnboundedCharField(choices=enums.choices(enums.DEVICE_PROPULSION))
    )
    year_manufactured = models.IntegerField(null=True)
    manufacturer = UnboundedCharField(default="")

    # denormalized fields, the source of truth for this data is in the EventRecord table.
    # /!\ These fields are for internal usage and may disappear anytime
    dn_battery_pct = models.FloatField(null=True)
    dn_gps_point = gis_models.PointField(null=True)
    dn_gps_timestamp = models.DateTimeField(null=True)
    dn_status = UnboundedCharField(
        null=True, choices=enums.choices(enums.DEVICE_STATUS), default=None
    )

    objects = DeviceQueryset.as_manager()

    def __str__(self):
        return "{} {} ({})".format(
            self.get_category_display(),
            self.identification_number,
            short_uuid4(self.id),
        )

    @property
    def latest_event(self):
        if hasattr(self, "_latest_event"):
            # don't do a query in this case, the telemetry was prefetched.
            return self._latest_event[0] if self._latest_event else None
        device = Device.objects.filter(pk=self.pk).with_latest_event().get()
        return device.latest_event

    @property
    def gps_point_as_geojson(self):
        """Represent the GPS point as GeoJSON"""
        if not self.dn_gps_point:
            return None
        return json.loads(self.dn_gps_point.geojson)


class EventRecord(models.Model):
    timestamp = models.DateTimeField(db_index=True)
    point = gis_models.PointField(null=True)
    saved_at = models.DateTimeField(default=utils.timezone.now)
    source = models.CharField(
        choices=enums.choices(enums.EVENT_SOURCE),
        default=enums.EVENT_SOURCE.push.name,
        max_length=16,
    )
    device = models.ForeignKey(
        Device, related_name="event_records", on_delete=models.CASCADE
    )
    event_type = UnboundedCharField(choices=enums.choices(enums.EVENT_TYPE))

    # JSON fields:
    # {
    #   "telemetry": see factories.EventRecord for an exhaustive example
    # }
    properties = pg_fields.JSONField(default=dict, encoder=encoders.JSONEncoder)

    class Meta:
        unique_together = [("device", "timestamp")]

    @property
    def point_as_geojson(self):
        """Represent the GPS point as GeoJSON"""
        if not self.point:
            return None
        return json.loads(self.point.geojson)

    @property
    def updated_status(self):
        return enums.EVENT_TYPE_TO_DEVICE_STATUS.get(
            self.event_type, enums.DEVICE_STATUS.unknown.name
        )


class Polygon(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    creation_date = models.DateTimeField(default=utils.timezone.now)
    deletion_date = models.DateTimeField(null=True, blank=True)
    label = UnboundedCharField(default="", blank=True, db_index=True)
    geom = gis_models.PolygonField()
    properties = pg_fields.JSONField(default=dict, encoder=encoders.JSONEncoder)

    def __str__(self):
        return "{} ({})".format(self.label, short_uuid4(self.id))


class Area(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    creation_date = models.DateTimeField(
        default=datetime.datetime(2012, 1, 1, tzinfo=datetime.timezone.utc)
    )
    deletion_date = models.DateTimeField(null=True, blank=True)
    label = UnboundedCharField(default="", blank=True, db_index=True)
    polygons = models.ManyToManyField(Polygon, blank=True, related_name="areas")
    providers = models.ManyToManyField(Provider, blank=True, related_name="areas")
    color = models.CharField(
        max_length=8, default="#FFFFFF", help_text="hexa representation"
    )
    area_type = UnboundedCharField(
        choices=enums.choices(enums.AREA_TYPE), default="unrestricted"
    )

    def __str__(self):
        return "{} ({})".format(self.label, short_uuid4(self.id))
