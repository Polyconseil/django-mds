from django_filters import rest_framework as filters
from rest_framework import serializers, viewsets

from mds import enums, models
from mds.access_control.permissions import require_scopes
from mds.access_control.scopes import SCOPE_PRV_API
from mds.apis import utils


class DeviceFilter(filters.FilterSet):
    id = filters.CharFilter(lookup_expr="icontains")
    category = utils.ChoicesInFilter(choices=enums.choices(enums.DEVICE_CATEGORY))
    provider = utils.UUIDInFilter()
    status = utils.ChoicesInFilter(
        "dn_status", choices=enums.choices(enums.DEVICE_STATUS)
    )
    registrationDateFrom = filters.IsoDateTimeFilter(
        "registration_date", lookup_expr="gte"
    )
    registrationDateTo = filters.IsoDateTimeFilter(
        "registration_date", lookup_expr="lte"
    )

    class Meta:
        model = models.Device
        fields = [
            "id",
            "category",
            "provider",
            "status",
            "registrationDateFrom",
            "registrationDateTo",
        ]


class DeviceSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(help_text="Unique device identifier (UUID)")
    model = serializers.CharField(required=False, help_text="Vehicle model")
    identification_number = serializers.CharField(
        help_text="VIN (Vehicle Identification Number)"
    )
    category = serializers.ChoiceField(
        enums.choices(enums.DEVICE_CATEGORY), help_text="Device type"
    )
    propulsion = serializers.ListField(
        child=serializers.ChoiceField(enums.choices(enums.DEVICE_PROPULSION)),
        help_text="Propulsion type(s)",
    )
    provider_id = serializers.UUIDField(
        source="provider.id", help_text="ID of the service provider of the device"
    )
    provider_name = serializers.CharField(
        source="provider.name", help_text="Name of the service provider of the device"
    )
    registration_date = serializers.DateTimeField(help_text="Device registration date")
    last_telemetry_date = serializers.DateTimeField(
        source="dn_gps_timestamp", help_text="Latest GPS timestamp", allow_null=True
    )
    position = utils.PointSerializer(
        source="dn_gps_point", help_text="Latest GPS position"
    )
    status = serializers.ChoiceField(
        enums.choices(enums.DEVICE_STATUS),
        source="dn_status",
        help_text="Latest status",
        allow_null=True,
    )
    battery = serializers.FloatField(
        source="latest_event.properties.telemetry.battery_pct",
        help_text="Percentage between 0 and 1",
        allow_null=True,
    )

    class Meta:
        model = models.Device
        fields = (
            "id",
            "provider_id",
            "provider_name",
            "model",
            "identification_number",
            "category",
            "propulsion",
            "status",
            "position",
            "registration_date",
            "last_telemetry_date",
            "battery",
        )


class DeviceViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (require_scopes(SCOPE_PRV_API),)
    lookup_field = "id"
    serializer_class = DeviceSerializer
    pagination_class = utils.LimitOffsetPagination
    filter_backends = (filters.DjangoFilterBackend,)

    filterset_class = DeviceFilter
    queryset = (
        models.Device.objects.with_latest_event().select_related("provider").all()
    )
