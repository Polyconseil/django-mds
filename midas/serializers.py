import json

from django.contrib.gis.geos import MultiPolygon
from django.contrib.gis.geos.geometry import GEOSGeometry
from rest_framework import serializers

from . import enums
from . import models


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
    battery = serializers.FloatField(min_value=0, max_value=1)
    timestamp = serializers.DateTimeField()


class TripSerializer(serializers.Serializer):
    unique_id = serializers.UUIDField()
    vehicle_id = serializers.UUIDField()
    route = GeometryField()  # expects Feature of Point with properties: {timestamp}


class ServiceAreaSerializer(serializers.Serializer):
    unique_id = serializers.UUIDField(source="id", read_only=True)
    begin_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField(required=False)
    # TODO are should be a Feature of MultiPolygon.
    # It is a single polygon for the moment
    area = GeometryField(source="area.polygons")

    def create(self, data):
        area = models.Area.objects.create(
            polygons=MultiPolygon([data['area']['polygons']]),
        )
        return models.Service.objects.create(
            area=area,
            provider="bluela",
            begin_date=data["begin_date"],
            end_date=data.get("end_date"),
        )
