"""
Database description
"""
import uuid

from django import forms
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres import fields as pg_fields
from django.db import models

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


class UuidModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    class Meta:
        abstract = True


class Query(UuidModel):
    timestamp = models.DateTimeField(auto_now_add=True)
    provider = UnboundedCharField()
    endpoint = UnboundedCharField(default=str)
    method = UnboundedCharField(choices=enums.HTTP_METHOD_CHOICES)
    content = pg_fields.JSONField(default=dict)


class Device(UuidModel):
    provider = UnboundedCharField()
    technical_id = UnboundedCharField()
    visible_id = UnboundedCharField()
    model = UnboundedCharField(default=str)
    status = UnboundedCharField(choices=enums.DEVICE_STATUS_CHOICES)
    position = gis_models.PointField(null=True)
    position_timestamp = models.DateTimeField(null=True)
    details = pg_fields.JSONField(default=dict)


class Area(UuidModel):
    polygons = gis_models.MultiPolygonField()


class Service(UuidModel):
    area = models.ForeignKey(Area, on_delete=models.CASCADE)
    provider = UnboundedCharField()
    begin_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True)
    details = pg_fields.JSONField(default=dict)
