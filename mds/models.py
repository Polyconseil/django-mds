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
    """Default value for the authentication of the Agency API use by the provider.

    Other keys are specific to each type:
    - token: "header" and "token"
    - oauth2: "client_id" and "client_secret"
    """
    return {"type": "none"}


def api_authentication_default():
    """Default value for the API authentication field of a provider.

    Other keys are specific to each type:
    - token: "header" and "token"
    - oauth2: "client_id" and "client_secret"
    """
    return {"type": "none"}


def api_configuration_default():
    """Default value for the API configuration field of a provider.

    Some provider implementations can be picky, configure these special cases here.
    """
    return {"trailing_slash": False}  # Some providers endpoint won't reply without it


class Provider(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = UnboundedCharField(default=str)
    logo_b64 = UnboundedCharField(null=True, blank=True, default=None)
    device_category = UnboundedCharField(choices=enums.choices(enums.DEVICE_CATEGORY))
    base_api_url = UnboundedCharField(default="", verbose_name="Base API URL")
    oauth2_url = UnboundedCharField(
        default="", verbose_name="OAuth2 URL (if different)"
    )
    api_authentication = pg_fields.JSONField(
        default=api_authentication_default, verbose_name="API Authentication"
    )
    api_configuration = pg_fields.JSONField(
        default=api_configuration_default, verbose_name="API Configuration"
    )
    agency_api_authentication = pg_fields.JSONField(
        default=agency_api_authentication_default,
        verbose_name="API Agency Authentication",
    )


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
    model = UnboundedCharField(default=str)
    propulsion = pg_fields.ArrayField(
        UnboundedCharField(choices=enums.choices(enums.DEVICE_PROPULSION))
    )
    year_manufactured = models.IntegerField(null=True)
    manufacturer = UnboundedCharField(default=str)

    # denormalized fields, the source of truth for this data is in the EventRecord table.
    dn_battery_pct = models.FloatField(null=True)
    dn_gps_point = gis_models.PointField(null=True)
    dn_gps_timestamp = models.DateTimeField(null=True)
    dn_status = UnboundedCharField(
        choices=enums.choices(enums.DEVICE_STATUS), default="unavailable"
    )

    objects = DeviceQueryset.as_manager()

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
    label = UnboundedCharField(null=True, blank=True, db_index=True)
    geom = gis_models.PolygonField()
    properties = pg_fields.JSONField(default=dict, encoder=encoders.JSONEncoder)


class Area(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    creation_date = models.DateTimeField(
        default=datetime.datetime(2012, 1, 1, tzinfo=datetime.timezone.utc)
    )
    deletion_date = models.DateTimeField(null=True, blank=True)
    label = UnboundedCharField(null=True, blank=True, db_index=True)
    polygons = models.ManyToManyField(Polygon, blank=True, related_name="areas")
    providers = models.ManyToManyField(Provider, blank=True, related_name="areas")
    color = models.CharField(
        max_length=8, default="#FFFFFF", help_text="hexa representation"
    )
    area_type = UnboundedCharField(
        choices=enums.choices(enums.AREA_TYPE), default="unrestricted"
    )
