from rest_framework import viewsets

from . import models
from . import serializers


class MultiSerializerViewSet(viewsets.ModelViewSet):
    serializers_map = {}

    def get_serializer_class(self):
        return (
            self.serializers_map.get(self.action, None)
            or super().get_serializer_class()
        )


class DeviceViewSet(MultiSerializerViewSet):
    queryset = models.Device.objects.all()
    lookup_field = "id"
    serializers_map = {
        "list": serializers.Device,
        "retrieve": serializers.Device,
        "create": serializers.DeviceRegister,
        "update": serializers.DeviceTelemetry,
    }


class AreaViewSet(viewsets.ModelViewSet):
    queryset = models.Area.objects.all()
    lookup_field = "id"
    serializer_class = serializers.ServiceAreaSerializer
