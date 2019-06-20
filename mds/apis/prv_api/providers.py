import django_filters.rest_framework
from rest_framework import serializers
from rest_framework import viewsets
from mds import models
from mds.access_control.permissions import require_scopes
from mds.access_control.scopes import SCOPE_PRV_API


class ProviderColorsSerializer(serializers.Serializer):
    primary = serializers.CharField(required=False)
    secondary = serializers.CharField(required=False)


class ProviderSerializer(serializers.ModelSerializer):

    id = serializers.UUIDField(
        required=True, help_text="Unique provider identifier (UUID)"
    )
    name = serializers.CharField(help_text="Name of the Provider")
    logo_b64 = serializers.CharField(
        required=False, help_text="Logo of provider base64 encoded"
    )
    operator = serializers.BooleanField(
        required=False, help_text="This provider is a device operator"
    )
    colors = ProviderColorsSerializer(
        default=dict, help_text="colors for distinguishing providers on map"
    )
    device_categories = serializers.DictField(serializers.IntegerField())

    def create(self, validated_data):
        instance = self.Meta.model(**validated_data)
        instance.save()
        return instance

    class Meta:
        model = models.Provider
        fields = (
            "id",
            "name",
            "colors",
            "logo_b64",
            "base_api_url",
            "api_authentication",
            "api_configuration",
            "agency_api_authentication",
            "device_categories",
            "operator",
        )


class ProviderViewSet(viewsets.ModelViewSet):
    permission_classes = (require_scopes(SCOPE_PRV_API),)
    queryset = models.Provider.objects.with_device_categories()
    lookup_field = "id"
    serializer_class = ProviderSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filterset_fields = ("operator",)
