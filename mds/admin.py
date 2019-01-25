from django.contrib import admin
from . import models


@admin.register(models.Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    ordering = ["name"]


@admin.register(models.Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ["id", "provider", "identification_number", "model"]
    list_filter = ["provider", "model"]


@admin.register(models.EventRecord)
class EventRecordAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "device", "event_type"]
    list_filter = ["device__provider", "event_type"]
    ordering = ["-timestamp"]


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
