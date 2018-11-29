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
    timestamp = serializers.DateTimeField(help_text="Timestamp from GSM provider")
    operator = serializers.CharField(
        required=False, allow_null=True, help_text="GSM provider"
    )
    signal = serializers.FloatField(
        required=False,
        allow_null=True,
        min_value=0,
        max_value=1,
        help_text="Signal strength in percents",
    )


class GPSProperties(serializers.Serializer):
    timestamp = serializers.DateTimeField(help_text="Timestamp from GPS")
    accuracy = serializers.FloatField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text="Position accuracy in IS units (m)",
    )
    course = serializers.FloatField(
        required=False,
        allow_null=True,
        min_value=0,
        max_value=360,
        help_text="Vehicle course relative to geographical north in degrees",
    )
    speed = serializers.FloatField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text="Vehicle speed measured by onboard GPS in IS units (m/s)",
    )


class VehicleProperties(serializers.Serializer):
    speed = serializers.FloatField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text="The vehicle speed in IS units (m/s)",
    )
    acceleration = serializers.ListField(
        child=serializers.FloatField(required=False, allow_null=True, min_value=0),
        min_length=2,
        max_length=3,
        help_text="The vehicle acceleration on [x,y,z] axis in IS units (m/s²)",
    )
    odometer = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text="The total distance covered by the vehicle in IS units (m)",
    )
    driver_present = serializers.BooleanField(
        required=False, allow_null=True, help_text="Driver presence detection"
    )


class EnergyProperties(serializers.Serializer):
    cruise_range = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text="The vehicle range in IS units (m)",
    )
    autonomy = serializers.FloatField(
        required=False,
        allow_null=True,
        min_value=0,
        max_value=1,
        help_text="The vehicle autonomy in percents",
    )


class PointProperties(serializers.Serializer):
    gsm = GSMProperties(required=False, help_text="GSM data")
    gps = GPSProperties(required=False, help_text="GPS data")
    vehicle_state = VehicleProperties(required=False, help_text="CAN data")
    energy = EnergyProperties(required=False, help_text="Energy information")


class Point(serializers.Serializer):
    """A GPS point
    """

    type = serializers.ChoiceField(choices=[("Feature", "Feature")], default="Feature")
    geometry = GeometryField(source="point")
    properties = PointProperties(required=False)


class Device(BaseModelSerializer):
    """A device
    """

    id = serializers.UUIDField(help_text="Unique device identifier (UUID)")
    provider = serializers.UUIDField(
        help_text="A unique ID identifying the service provider (UUID)"
    )
    identification_number = serializers.CharField(
        help_text="VIN (Vehicle Identification Number"
    )
    model = serializers.CharField(help_text="Vehicle model")
    status = serializers.ChoiceField(
        enums.DEVICE_STATUS_CHOICES, help_text="Service status"
    )
    position = Point(
        required=False,
        allow_null=True,
        source="*",
        help_text="GPS position and telemetry",
    )

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

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        timestamp = instance.properties.get("gps", {}).get("timestamp")
        timestamp = timestamp or instance.properties.get("gsm", {}).get("timestamp")
        models.Telemetry.objects.create(
            device=instance,
            provider=instance.provider,
            status=instance.status,
            point=instance.point,
            properties=instance.properties,
            timestamp=timestamp,
        )
        return instance


class ServiceAreaSerializer(BaseModelSerializer):
    """A service area
    """

    id = serializers.UUIDField(
        required=False, help_text="Unique Area identifier (UUID)"
    )
    # TODO(lip) remove default
    provider = serializers.UUIDField(
        default="a19cdb1e-1342-413b-8e89-db802b2f83f6",
        help_text="A unique ID identifying the service provider (UUID)",
    )
    # TODO(lip) use a FeatureCollection instead of these fields
    begin_date = serializers.DateTimeField(help_text="Area availability date")
    end_date = serializers.DateTimeField(
        required=False, help_text="Area end of availability date"
    )
    area = GeometryField(source="polygon", help_text="GeoJSON Polygon of the area")

    class Meta:
        model = models.Area
        fields = ("id", "provider", "begin_date", "end_date", "area")
