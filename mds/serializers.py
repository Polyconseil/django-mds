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


class DeviceRegister(BaseModelSerializer):
    id = serializers.UUIDField(help_text="Unique device identifier (UUID)")
    model = serializers.CharField(required=False, help_text="Vehicle model")
    identification_number = serializers.CharField(
        help_text="VIN (Vehicle Identification Number)"
    )
    category = serializers.ChoiceField(
        enums.DEVICE_CATEGORY_CHOICES, help_text="Device type"
    )
    propulsion = serializers.ChoiceField(
        enums.DEVICE_PROPULSION_CHOICES, help_text="Propulsion type"
    )

    class Meta:
        model = models.Device
        fields = (
            "id",
            "provider",
            "model",
            "identification_number",
            "category",
            "propulsion",
        )


class Device(DeviceRegister):
    provider = serializers.CharField(
        source="provider.name", help_text="Name of the service provider of the device"
    )
    registration_date = serializers.DateTimeField(help_text="Device registration date")
    last_telemetry_date = serializers.DateTimeField(
        source="latest_telemetry.timestamp",
        help_text="Device registration date",
        allow_null=True,
    )
    position = Point(
        source="latest_telemetry", help_text="Latest GPS position and telemetry"
    )
    status = serializers.ChoiceField(
        enums.DEVICE_STATUS_CHOICES,
        source="latest_telemetry.status",
        help_text="Latest status",
        allow_null=True,
    )

    class Meta:
        model = models.Device
        fields = (
            "id",
            "provider",
            "model",
            "identification_number",
            "category",
            "propulsion",
            "status",
            "position",
            "registration_date",
            "last_telemetry_date",
        )


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


class PolygonSerializer(BaseModelSerializer):
    """A service area
    """

    id = serializers.UUIDField(
        required=False, help_text="Unique Polygon identifier (UUID)"
    )
    label = serializers.CharField(help_text="Name of the polygon")
    creation_date = serializers.DateTimeField(help_text="Polygon creation date")
    deletion_date = serializers.DateTimeField(
        required=False, help_text="Polygon deletion date"
    )
    properties = serializers.JSONField(help_text="Properties of the Polygon")
    geom = GeometryField(help_text="GeoJSON Polygon")

    class Meta:
        model = models.Polygon
        fields = ("id", "label", "creation_date", "deletion_date", "geom", "properties")


class AreaSerializer(BaseModelSerializer):
    """A service area
    """

    id = serializers.UUIDField(
        required=False, help_text="Unique Area identifier (UUID)"
    )
    label = serializers.CharField(help_text="Name of the Area")
    creation_date = serializers.DateTimeField(help_text="Area creation date")
    deletion_date = serializers.DateTimeField(
        required=False, help_text="Area deletion date"
    )
    polygons = PolygonSerializer(required=False, many=True)

    class Meta:
        model = models.Area
        fields = ("id", "label", "creation_date", "deletion_date", "polygons")


class ProviderSerializer(BaseModelSerializer):
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
