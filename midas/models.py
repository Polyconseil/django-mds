"""
Database description
"""
from django import forms
from django.contrib.postgres import fields as pg_fields
from django.db import models


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


class Query(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    provider = UnboundedCharField()
    endpoint = UnboundedCharField(default="")
    method = UnboundedCharField(
        choices=[("POST", "POST"), ("PUT", "PUT"), ("DELETE", "DELETE")]
    )
    content = pg_fields.JSONField(default={})
