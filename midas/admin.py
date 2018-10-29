from django.contrib import admin
from . import models


@admin.register(models.Query)
class QueryAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "provider", "endpoint", "method"]
    list_filter = ["provider"]
    ordering = ["-timestamp"]


@admin.register(models.Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ["provider", "technical_id", "visible_id", "model", "status"]
    list_filter = ["provider", "model", "status"]


@admin.register(models.Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ["id", "polygons"]


@admin.register(models.Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["provider", "area", "begin_date", "end_date"]
    list_filter = ["provider"]
    ordering = ["-begin_date"]
