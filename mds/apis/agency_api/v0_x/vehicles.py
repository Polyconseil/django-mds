from rest_framework import mixins
from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from django.contrib.gis.geos import Point

from mds import enums
from mds import models
from mds.access_control.permissions import require_scopes
from mds.access_control.scopes import SCOPE_AGENCY_API
from mds.apis import utils


class DeviceSerializer(serializers.Serializer):
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
    updated = utils.UnixTimestampMilliseconds(
        source="latest_event.saved_at",
        help_text="Date of last event update as Unix Timestamp (milliseconds).",
        allow_null=True,
    )


class DeviceRegisterSerializer(serializers.Serializer):
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
        return models.Device.objects.create(provider_id=provider_id, **validated_data)


class GPSSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    altitude = serializers.FloatField(help_text="in meters")
    heading = serializers.FloatField(help_text="degrees, starting at 0 at true North")
    speed = serializers.FloatField(help_text="in meters/second")
    accuracy = serializers.FloatField(help_text="in meters")


def gps_to_gis_point(gps_data):
    if gps_data:
        # TODO(lip): maybe use altitude as z ?
        return Point(gps_data["lng"], gps_data["lat"], srid=4326)
    return None


class DeviceTelemetrySerializer(serializers.Serializer):
    device_id = serializers.UUIDField()
    gps = GPSSerializer()
    timestamp = utils.UnixTimestampMilliseconds(
        help_text="Unix timestamp in milliseconds"
    )


class DeviceEventSerializer(serializers.Serializer):
    event_type = serializers.ChoiceField(
        choices=enums.choices(enums.EVENT_TYPE), help_text="Vehicle event."
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
        return models.EventRecord.objects.create(
            timestamp=validated_data["telemetry"]["timestamp"],
            point=gps_to_gis_point(validated_data["telemetry"].get("gps", {})),
            device_id=device.id,
            event_type=validated_data["event_type"],
            properties={
                "telemetry": validated_data["telemetry"],
                "trip_id": validated_data.get("trip_id"),
            },
        )


# TODO: these are in the spec but I don't see what it adds.
# class DeviceEventResponseSerializer(serializers.Serializer):
#     device_id = serializers.UUIDField()
#     status = serializers.ChoiceField(choices=enums.DEVICE_STATUS_CHOICES)


class DeviceTelemetryInputSerializer(serializers.Serializer):
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

        to_create = [
            models.EventRecord(
                timestamp=telemetry["timestamp"],
                point=gps_to_gis_point(telemetry.get("gps", {})),
                device_id=telemetry["device_id"],
                event_type=enums.EVENT_TYPE.telemetry.name,
                properties={"telemetry": telemetry, "trip_id": None},
            )
            for telemetry in validated_data["data"]
        ]
        return models.EventRecord.objects.bulk_create(to_create)


class DeviceViewSet(
    utils.MultiSerializerViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):

    queryset = models.Device.objects.with_latest_event()
    permission_classes = (require_scopes(SCOPE_AGENCY_API),)
    lookup_field = "id"
    serializer_class = DeviceSerializer
    serializers_mapping = {
        "list": {"response": DeviceSerializer},
        "retrieve": {"response": DeviceSerializer},
        "create": {
            "request": DeviceRegisterSerializer,
            "response": utils.EmptyResponseSerializer,
        },
        "event": {
            "request": DeviceEventSerializer,
            "response": utils.EmptyResponseSerializer,
        },
        "telemetry": {
            "request": DeviceTelemetryInputSerializer,
            "response": utils.EmptyResponseSerializer,
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
        provider_id = request.user.provider_id
        device = models.Device.objects.filter(provider_id=provider_id, id=id).last()
        if not device:
            return Response(data={}, status=404)

        request_serializer = self.get_serializer(
            data=request.data,
            context={"device": device, "request_or_response": "request"},
        )
        request_serializer.is_valid(raise_exception=True)
        instance = request_serializer.save()
        response_serializer = self.get_serializer(
            instance=instance, context={"request_or_response": "response"}
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post", "options"])
    def telemetry(self, request):
        context = self.get_serializer_context()  # adds the request to the context
        context["request_or_response"] = "request"
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
