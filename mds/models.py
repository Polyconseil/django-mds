"""
Database description
"""
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


class ProviderModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    provider = models.UUIDField()

    class Meta:
        abstract = True


class Provider(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = UnboundedCharField(default=str)
    logo_b64 = UnboundedCharField(null=True, blank=True, default=None)


class DeviceQueryset(models.QuerySet):
    def with_latest_event(self):
        return self.prefetch_related(
            Prefetch(
                "event_records",
                queryset=EventRecord.objects.filter(
                    id__in=Subquery(
                        EventRecord.objects.filter(device_id=OuterRef("device_id"))
                        .exclude(event_type="telemetry")
                        .order_by("-saved_at")
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

    category = UnboundedCharField(choices=enums.DEVICE_CATEGORY_CHOICES)
    model = UnboundedCharField(default=str)
    propulsion = pg_fields.ArrayField(
        UnboundedCharField(choices=enums.DEVICE_PROPULSION_CHOICES)
    )
    year_manufactured = models.IntegerField(null=True)
    manufacturer = UnboundedCharField(default=str)

    # denormalized fields, the source of truth for this data is in the Record table.
    dn_gps_point = gis_models.PointField(null=True)
    dn_gps_timestamp = models.DateTimeField(null=True)
    dn_status = UnboundedCharField(
        choices=enums.DEVICE_STATUS_CHOICES, default="unavailable"
    )

    objects = DeviceQueryset.as_manager()

    @property
    def latest_event(self):
        if hasattr(self, "_latest_event"):
            # don't do a query in this case, the telemetry was prefetched.
            return self._latest_event[0] if self._latest_event else None
        device = Device.objects.filter(pk=self.pk).with_latest_event()
        return device.latest_event

    @property
    def gps_point_as_geojson(self):
        """Represent the gpos point as geojson"""
        return json.loads(self.dn_gps_point.geojson)


class EventRecord(models.Model):
    saved_at = models.DateTimeField(db_index=True, default=utils.timezone.now)
    source = models.CharField(
        choices=enums.EVENT_INGESTION_SOURCES, default="push", max_length=16
    )
    device = models.ForeignKey(
        Device, related_name="event_records", on_delete=models.CASCADE
    )
    event_type = UnboundedCharField(choices=enums.EVENT_TYPE_CHOICES)

    # JSON fields:
    # {
    #   "telemetry": see serializers.PointProperties for the fields
    # }
    properties = pg_fields.JSONField(default=dict, encoder=encoders.JSONEncoder)


class Polygon(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    creation_date = models.DateTimeField(default=utils.timezone.now)
    deletion_date = models.DateTimeField(null=True)
    label = UnboundedCharField(null=True)
    geom = gis_models.PolygonField()
    properties = pg_fields.JSONField(default=dict, encoder=encoders.JSONEncoder)


class Area(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    creation_date = models.DateTimeField(default=utils.timezone.now)
    deletion_date = models.DateTimeField(null=True)
    label = UnboundedCharField(null=True)
    polygons = models.ManyToManyField(Polygon, blank=True, related_name="areas")
    providers = models.ManyToManyField(Provider, blank=True, related_name="areas")
    color = models.CharField(
        max_length=8, default="#FFFFFF", help_text="hexa representation"
    )
