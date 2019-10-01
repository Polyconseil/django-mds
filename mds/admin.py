from uuid import UUID

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from . import models


def is_uuid(uuid_string, version=4):
    try:
        UUID(uuid_string, version=version)
    except ValueError:
        return False
    return True


@admin.register(models.Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "operator"]
    list_filter = ["operator"]
    ordering = ["name"]


@admin.register(models.Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ["id", "provider_name", "identification_number", "category"]
    list_filter = ["provider", "category"]
    search_fields = ["id", "identification_number"]
    list_select_related = ["provider"]

    def provider_name(self, obj):
        return obj.provider.name

    provider_name.short_description = "Provider"


@admin.register(models.EventRecord)
class EventRecordAdmin(admin.ModelAdmin):
    list_display = [
        "saved_at",
        "timestamp",
        "provider",
        "device_id",
        "event_type",
        "event_type_reason",
    ]
    list_filter = ["device__provider", "event_type", "event_type_reason"]
    list_select_related = ["device__provider"]
    search_fields = ["device__id", "device__identification_number"]

    def get_search_results(self, request, queryset, search_term):
        if not search_term:
            return super().get_search_results(request, queryset, search_term)
        custom_queryset = get_devices_queryset_search_results(self, search_term)
        return super().get_search_results(request, custom_queryset, search_term)

    def provider(self, obj):
        return obj.device.provider.name

    def device_id(self, obj):
        return obj.device.id


# to use when searching for devices in get_search_results
# as a relationship to self.model
def get_devices_queryset_search_results(self, search_term):
    custom_queryset = self.model.objects.select_related(*self.list_select_related)
    if is_uuid(search_term):
        return custom_queryset.filter(device_id=search_term)
    else:
        return custom_queryset.filter(device__identification_number=search_term)


@admin.register(models.Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ["id", "label"]
    ordering = ["label"]


@admin.register(models.Polygon)
class PolygonAdmin(admin.ModelAdmin):
    list_display = ["id", "label"]
    ordering = ["label"]


class PublishedFilter(admin.SimpleListFilter):
    title = _("published")
    parameter_name = "is_published"

    def lookups(self, request, model_admin):
        return [("0", _("No")), ("1", _("Yes"))]

    def queryset(self, request, queryset):
        if self.value() == "0":
            queryset = queryset.filter(published_date__isnull=True)
        elif self.value() == "1":
            queryset = queryset.filter(published_date__isnull=False)
        return queryset


@admin.register(models.Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ["name", "start_date", "end_date", "is_published"]
    list_filter = ["start_date", "end_date", PublishedFilter, "providers"]
    search_fields = ["id", "name", "description"]
    ordering = ["start_date"]

    def is_published(self, policy):
        return bool(policy.published_date)

    is_published.boolean = True


@admin.register(models.Compliance)
class ComplianceAdmin(admin.ModelAdmin):
    list_display = ["id", "policy_name", "start_date", "end_date", "lag"]
    list_filter = ["start_date", "end_date", "lag"]
    search_fields = ["id", "policy_id", "vehicle_id"]
    ordering = ["start_date"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("policy")

    def policy_name(self, compliance):
        return compliance.policy.name
