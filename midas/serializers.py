import json

from django.contrib.gis.geos.geometry import GEOSGeometry
from rest_framework import serializers

from . import enums


class GeometryField(serializers.Field):
    type_name = "GeometryField"

    def to_representation(self, value):
        if isinstance(value, dict) or value is None:
            return value
        return value.geojson

    def to_internal_value(self, value):
        if not value or isinstance(value, GEOSGeometry):
            return value
        if isinstance(value, dict):
            value = json.dumps(value)
        return GEOSGeometry(value)


class DeviceSerializer(serializers.Serializer):
    unique_id = serializers.UUIDField()
    visible_id = serializers.CharField()
    model = serializers.CharField()
    status = serializers.ChoiceField(choices=enums.DEVICE_STATUS_CHOICES)
    position = GeometryField()  # expects Point
    battery = serializers.FloatField(min=0, max=1)
    timestamp = serializers.DateTimeField()


class TripSerializer(serializers.Serializer):
    unique_id = serializers.UUIDField()
    vehicle_id = serializers.UUIDField()
    route = GeometryField()  # expects Feature of Point with properties: {timestamp}


class ServiceAreaSerializer(serializers.Serializer):
    unique_id = serializers.UUIDField()
    begin_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField(required=False)
    area = GeometryField()  # expects Feature of MultiPolygon
