from rest_framework import mixins
from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from django.contrib.gis.geos import Point
from django.db.utils import IntegrityError

from mds import db_helpers
from mds import enums
from mds import models
from mds.access_control.permissions import require_scopes
from mds.access_control.scopes import SCOPE_AGENCY_API
from mds.apis import utils as apis_utils


class DeviceSerializer(serializers.Serializer):
    """Expose devices as described in the Agency spec."""

    device_id = serializers.UUIDField(
        source="id", help_text="Provided by Operator to uniquely identify a vehicle."
    )
    provider_id = serializers.UUIDField(help_text="Issued by City and tracked.")
    vehicle_id = serializers.CharField(
        source="identification_number",
        help_text="Vehicle Identification Number (vehicle_id) visible on vehicle.",
    )
    type = serializers.ChoiceField(
        source="category",
        choices=enums.choices(enums.DEVICE_CATEGORY),
        help_text="Vehicle type.",
    )
    propulsion = serializers.ListSerializer(
        child=serializers.ChoiceField(choices=enums.choices(enums.DEVICE_PROPULSION)),
        help_text="Array of Propulsion Type.",
    )
    year = serializers.IntegerField(
        source="year_manufactured", help_text="Year Manufactured."
    )
    mfgr = serializers.CharField(
        source="manufacturer", help_text="Vehicle Manufacturer."
    )
    model = serializers.CharField(help_text="Vehicle Model.")
    status = serializers.ChoiceField(
        source="dn_status",
        choices=enums.choices(enums.DEVICE_STATUS),
        help_text="Current vehicle status.",
    )
    prev_event = serializers.ChoiceField(
        source="latest_event.event_type",
        choices=enums.choices(enums.EVENT_TYPE),
        help_text="Last Vehicle Event.",
        allow_null=True,
    )
    updated = apis_utils.UnixTimestampMilliseconds(
        source="latest_event.saved_at",
        help_text="Date of last event update as Unix Timestamp (milliseconds).",
        allow_null=True,
    )


class DeviceRegisterSerializer(serializers.Serializer):
    """Receive a new device to create from a provider."""

    device_id = serializers.UUIDField(
        source="id", help_text="Provided by Operator to uniquely identify a vehicle."
    )
    vehicle_id = serializers.CharField(
        source="identification_number",
        help_text="Vehicle Identification Number (vehicle_id) visible on vehicle.",
    )
    type = serializers.ChoiceField(
        source="category",
        choices=enums.choices(enums.DEVICE_CATEGORY),
        help_text="Vehicle type.",
    )
    propulsion = serializers.ListSerializer(
        child=serializers.ChoiceField(choices=enums.choices(enums.DEVICE_PROPULSION)),
        help_text="Array of Propulsion Type.",
    )
    year = serializers.IntegerField(
        required=False, source="year_manufactured", help_text="Year Manufactured."
    )
    mfgr = serializers.CharField(
        required=False, source="manufacturer", help_text="Vehicle Manufacturer."
    )
    model = serializers.CharField(required=False, help_text="Vehicle Model.")

    def create(self, validated_data):
        provider_id = self.context["request"].user.provider_id
        try:
            return models.Device.objects.create(
                provider_id=provider_id, **validated_data
            )
        except IntegrityError:
            detail = f"A vehicle with id={validated_data['id']} is already registered"
            raise apis_utils.AlreadyRegisteredError({"already_registered": detail})


class GPSSerializer(serializers.Serializer):
    """GPS data inside the telemetry frame sent by the provider."""

    lat = serializers.FloatField()
    lng = serializers.FloatField()
    altitude = serializers.FloatField(required=False, help_text="in meters")
    heading = serializers.FloatField(
        required=False, min_value=0, help_text="degrees, starting at 0 at true North"
    )
    speed = serializers.FloatField(required=False, help_text="in meters/second")
    hdop = serializers.FloatField(
        required=False,
        min_value=1,
        source="accuracy",
        help_text="Horizontal GPS accuracy",
    )
    satellites = serializers.IntegerField(
        required=False, min_value=0, help_text="Number of GPS satellites"
    )

    def validate(self, value):
        attrs = super().validate(value)

        # Some providers may mistake latitude and longitude
        provider = self.context.get("provider")
        if provider and provider.agency_api_configuration.get("swap_lat_lng"):
            attrs["lat"], attrs["lng"] = attrs["lng"], attrs["lat"]

        # Now we can validate (this will not catch valid inversions)
        if attrs["lat"] < -90.0 or attrs["lat"] > 90.0:
            raise ValidationError(
                {"lat": "Latitude is outside [-90 90]: %s" % attrs["lat"]}
            )
        if attrs["lng"] < -180.0 or attrs["lng"] > 180.0:
            raise ValidationError(
                {"lng": "Longitude is outside [-180 180]: %s" % attrs["lng"]}
            )

        return attrs


def gps_to_gis_point(gps_data):
    if gps_data:
        # TODO(lip): maybe use altitude as z ?
        return Point(gps_data["lng"], gps_data["lat"], srid=4326)
    return None


class DeviceTelemetrySerializer(serializers.Serializer):
    """Telemetry frame from event and telemetry endpoints."""

    device_id = serializers.UUIDField()
    gps = GPSSerializer()
    timestamp = apis_utils.UnixTimestampMilliseconds(
        help_text="Unix timestamp in milliseconds"
    )
    charge = serializers.FloatField(
        required=False,
        source="battery_pct",
        min_value=0,
        max_value=1,
        help_text="Percent battery charge of vehicle, expressed between 0 and 1",
    )


class DeviceEventSerializer(serializers.Serializer):
    """Receive a new event pushed by a provider."""

    event_type = serializers.ChoiceField(
        choices=enums.choices(enums.EVENT_TYPE), help_text="Vehicle event."
    )
    timestamp = apis_utils.UnixTimestampMilliseconds(
        help_text="Timestamp of the last event update"
    )
    telemetry = DeviceTelemetrySerializer(
        write_only=True, help_text="Single point of telemetry."
    )
    trip_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text=(
            "UUID provided by Operator to uniquely identify the trip. "
            "Required for trip_* events."
        ),
    )

    def create(self, validated_data):
        device = self.context["device"]
        event_record = models.EventRecord(
            timestamp=validated_data["timestamp"],
            point=gps_to_gis_point(validated_data["telemetry"].get("gps", {})),
            device_id=device.id,
            event_type=validated_data["event_type"],
            properties={
                "telemetry": validated_data["telemetry"],
                "trip_id": validated_data.get("trip_id"),
            },
        )
        db_helpers.upsert_event_records([event_record], "push", on_conflict_update=True)

        # We don't get the created event record but we need to return it
        return models.EventRecord.objects.get(
            device=device, timestamp=validated_data["timestamp"]
        )


class DeviceEventResponseSerializer(serializers.Serializer):
    """Response format for the event endpoint."""

    device_id = serializers.UUIDField()
    status = serializers.ChoiceField(
        source="updated_status", choices=enums.choices(enums.DEVICE_STATUS)
    )


class DeviceTelemetryInputSerializer(serializers.Serializer):
    """Receive a new telemetry pushed by a provider."""

    data = DeviceTelemetrySerializer(many=True)

    def create(self, validated_data):
        provider_id = self.context["request"].user.provider_id
        unknown_ids = [
            str(id)
            for id in (
                set(t["device_id"] for t in validated_data["data"])
                - set(
                    models.Device.objects.filter(
                        id__in=[t["device_id"] for t in validated_data["data"]]
                    )
                    .filter(provider_id=provider_id)
                    .values_list("id", flat=True)
                )
            )
        ]
        if unknown_ids:
            raise ValidationError(
                {"data.device_id": "Unknown ids: %s" % " ".join(unknown_ids)}
            )

        event_records = (
            models.EventRecord(
                timestamp=telemetry["timestamp"],
                point=gps_to_gis_point(telemetry.get("gps", {})),
                device_id=telemetry["device_id"],
                event_type=enums.EVENT_TYPE.telemetry.name,
                properties={"telemetry": telemetry, "trip_id": None},
            )
            for telemetry in validated_data["data"]
        )
        db_helpers.upsert_event_records(event_records, "push", on_conflict_update=True)

        # We don't have the created event records, but we'll return an empty response anyway
        return []


class DeviceViewSet(
    apis_utils.MultiSerializerViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):

    queryset = models.Device.objects.with_latest_events()
    permission_classes = (require_scopes(SCOPE_AGENCY_API),)
    lookup_field = "id"
    serializer_class = DeviceSerializer
    serializers_mapping = {
        "list": {"response": DeviceSerializer},
        "retrieve": {"response": DeviceSerializer},
        "create": {
            "request": DeviceRegisterSerializer,
            "response": apis_utils.EmptyResponseSerializer,
        },
        "event": {
            "request": DeviceEventSerializer,
            "response": DeviceEventResponseSerializer,
        },
        "telemetry": {
            "request": DeviceTelemetryInputSerializer,
            "response": apis_utils.EmptyResponseSerializer,
        },
    }

    def list(self, *args, **kwargs):
        return super().list(*args, **kwargs)

    def retrieve(self, *args, **kwargs):
        return super().retrieve(*args, **kwargs)

    def create(self, *args, **kwargs):
        return self._create(*args, **kwargs)

    @action(detail=True, methods=["post", "options"])
    def event(self, request, id):
        """Endpoint to receive an event from a provider."""
        provider_id = request.user.provider_id
        device = models.Device.objects.filter(provider_id=provider_id, id=id).last()
        if not device:
            return Response(data={}, status=404)

        provider = models.Provider.objects.get(pk=provider_id)
        request_serializer = self.get_serializer(
            data=request.data,
            context={
                "device": device,
                "request_or_response": "request",
                "provider": provider,
            },
        )
        request_serializer.is_valid(raise_exception=True)
        instance = request_serializer.save()
        response_serializer = self.get_serializer(
            instance=instance, context={"request_or_response": "response"}
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post", "options"])
    def telemetry(self, request):
        """Endpoint to receive a telemetry from a provider."""
        context = self.get_serializer_context()  # adds the request to the context
        context["request_or_response"] = "request"
        provider_id = request.user.provider_id
        context["provider"] = models.Provider.objects.get(pk=provider_id)
        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        response_serializer = self.get_serializer(
            instance=instance, context={"request_or_response": "response"}
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        queryset = super().get_queryset()
        provider_id = getattr(self.request.user, "provider_id", None)
        if provider_id:
            queryset = queryset.filter(provider_id=provider_id)
        else:
            queryset = queryset.none()

        return queryset
