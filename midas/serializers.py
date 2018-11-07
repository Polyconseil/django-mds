import json

# from django.contrib.gis.geos import Polygon
from django.contrib.gis.geos.geometry import GEOSGeometry
from rest_framework import fields
from rest_framework import serializers

from . import enums
from . import models


class GeometryField(serializers.Field):
    type_name = "GeometryField"

    def to_representation(self, value):
        if isinstance(value, dict) or value is None:
            return value
        return json.loads(value.geojson)

    def to_internal_value(self, value):
        if isinstance(value, GEOSGeometry) or value is None:
            return value
        if isinstance(value, dict):
            value = json.dumps(value)
        return GEOSGeometry(value)


class BaseModelSerializer(serializers.ModelSerializer):
    def __init__(self, instance=None, data=fields.empty, **kwargs):
        if data is not fields.empty:
            data = dict(data)
            data.update(getattr(kwargs.get("context", {}).get("view"), "kwargs", {}))
        super().__init__(instance, data, **kwargs)


class GSMProperties(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    operator = serializers.CharField(required=False, allow_null=True)
    signal = serializers.FloatField(
        required=False, allow_null=True, min_value=0, max_value=1
    )


class GPSProperties(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    accuracy = serializers.FloatField(required=False, allow_null=True, min_value=0)
    course = serializers.FloatField(
        required=False, allow_null=True, min_value=0, max_value=360
    )
    speed = serializers.FloatField(required=False, allow_null=True, min_value=0)


class VehicleProperties(serializers.Serializer):
    speed = serializers.FloatField(required=False, allow_null=True, min_value=0)
    acceleration = serializers.ListField(
        child=serializers.FloatField(required=False, allow_null=True, min_value=0),
        min_length=2,
        max_length=3,
    )
    odometer = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    driver_present = serializers.BooleanField(required=False, allow_null=True)


class EnergyProperties(serializers.Serializer):
    cruise_range = serializers.IntegerField(
        required=False, allow_null=True, min_value=0
    )
    autonomy = serializers.FloatField(
        required=False, allow_null=True, min_value=0, max_value=1
    )


class PointProperties(serializers.Serializer):
    gsm = GSMProperties()
    gps = GPSProperties()
    vehicle_state = VehicleProperties(required=False)
    energy = EnergyProperties(required=False)


class Point(serializers.Serializer):
    type = serializers.ChoiceField(choices=[("Feature", "Feature")], default="Feature")
    geometry = GeometryField(source="point")
    properties = PointProperties()


class Device(BaseModelSerializer):
    id = serializers.UUIDField()
    provider = serializers.UUIDField()
    identification_number = serializers.CharField()
    model = serializers.CharField()
    status = serializers.ChoiceField(enums.DEVICE_STATUS_CHOICES)
    position = Point(required=False, allow_null=True, source="*")

    class Meta:
        model = models.Device
        fields = (
            "id",
            "provider",
            "identification_number",
            "model",
            "status",
            "position",
        )


class DeviceRegister(Device):
    class Meta:
        model = models.Device
        fields = ("id", "provider", "identification_number", "model")


class DeviceTelemetry(Device):
    class Meta:
        model = models.Device
        fields = ("id", "provider", "status", "position")


class ServiceAreaSerializer(BaseModelSerializer):
    id = serializers.UUIDField(required=False)
    # TODO(lip) remove default
    provider = serializers.UUIDField(default="a19cdb1e-1342-413b-8e89-db802b2f83f6")
    # TODO(lip) use a FeatureCollection instead of these fields
    begin_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField(required=False)
    area = GeometryField(source="polygon")

    class Meta:
        model = models.Area
        fields = ("id", "provider", "begin_date", "end_date", "area")
