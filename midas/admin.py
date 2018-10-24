from django.contrib import admin
from . import models


@admin.register(models.Query)
class QueryAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "provider", "endpoint", "method"]
    list_filter = ["provider"]
    ordering = ["-timestamp"]
