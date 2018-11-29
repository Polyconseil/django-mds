"""
Database description
"""
import uuid

from django import forms
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres import fields as pg_fields
from django.db import models

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


class Device(ProviderModel):
    """A device
    """

    identification_number = UnboundedCharField()
    model = UnboundedCharField(default=str)
    status = UnboundedCharField(choices=enums.DEVICE_STATUS_CHOICES)
    point = gis_models.PointField(null=True)
    properties = pg_fields.JSONField(default=dict, encoder=encoders.JSONEncoder)


class Area(ProviderModel):
    begin_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True)
    polygon = gis_models.PolygonField()
    properties = pg_fields.JSONField(default=dict, encoder=encoders.JSONEncoder)


class Telemetry(models.Model):
    device = models.ForeignKey(
        Device, related_name="telemetries", on_delete=models.CASCADE
    )
    provider = models.UUIDField()
    timestamp = models.DateTimeField(db_index=True)
    status = UnboundedCharField(choices=enums.DEVICE_STATUS_CHOICES)
    point = gis_models.PointField(null=True)
    properties = pg_fields.JSONField(default=dict, encoder=encoders.JSONEncoder)

    class Meta:
        verbose_name_plural = "telemetries"
