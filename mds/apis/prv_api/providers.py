from rest_framework import serializers
from rest_framework import viewsets

from mds import models
from mds.access_control.permissions import require_scopes
from mds.access_control.scopes import SCOPE_ADMIN


class ProviderSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(
        required=False, help_text="Unique Area identifier (UUID)"
    )
    name = serializers.CharField(help_text="Name of the Provider")
    logo_b64 = serializers.CharField(
        required=False, help_text="Logo of provider base64 encoded"
    )

    class Meta:
        model = models.Provider
        fields = ("id", "name", "logo_b64")


class ProviderViewSet(viewsets.ModelViewSet):
    permission_classes = (require_scopes(SCOPE_ADMIN),)
    queryset = models.Provider.objects.all()
    lookup_field = "id"
    serializer_class = ProviderSerializer
