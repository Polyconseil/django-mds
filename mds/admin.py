from django.contrib import admin
from . import models


@admin.register(models.Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ["id", "provider", "identification_number", "model", "status"]
    list_filter = ["provider", "model", "status"]


@admin.register(models.Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ["id", "creation_date", "deletion_date", "label"]
    list_filter = ["creation_date", "deletion_date"]
    ordering = ["-creation_date"]


@admin.register(models.Polygon)
class PolygonAdmin(admin.ModelAdmin):
    list_display = ["id", "creation_date", "deletion_date", "label"]
    list_filter = ["creation_date", "deletion_date"]
    ordering = ["-creation_date"]


@admin.register(models.Telemetry)
class TelemetryAdmin(admin.ModelAdmin):
    list_display = ["device", "timestamp", "provider", "status"]
    list_filter = ["provider", "status"]
    ordering = ["-timestamp"]
