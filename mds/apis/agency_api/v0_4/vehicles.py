import logging

from rest_framework import serializers
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from mds import db_helpers
from mds import enums, models
from mds.utils import is_telemetry_enabled

from mds.apis.agency_api.v0_3 import vehicles as v0_3_vehicles
from .utils import to_mds_error_response


logger = logging.getLogger(__name__)


class DeviceTelemetryInputSerializer(serializers.Serializer):
    """Receive a new telemetry pushed by a provider."""

    data = v0_3_vehicles.DeviceTelemetrySerializer(many=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        provider_id = self.context["request"].user.provider_id
        unknown_ids = [
            str(id)
            for id in (
                set(t["device_id"] for t in attrs["data"])
                - set(
                    models.Device.objects.filter(
                        id__in=[t["device_id"] for t in attrs["data"]]
                    )
                    .filter(provider_id=provider_id)
                    .values_list("id", flat=True)
                )
            )
        ]
        if unknown_ids:
            raise ValidationError(
                # Reformatted for to_mds_error_response
                {
                    "data": [
                        {
                            "device_id": [
                                "Unknown device_ids: %s" % " ".join(unknown_ids)
                            ]
                        }
                    ]
                }
            )
        return attrs

    def create(self, validated_data):
        event_records = (
            models.EventRecord(
                timestamp=telemetry["timestamp"],
                point=v0_3_vehicles.gps_to_gis_point(telemetry.get("gps", {})),
                device_id=telemetry["device_id"],
                event_type=enums.EVENT_TYPE.telemetry.name,
                properties={"telemetry": telemetry, "trip_id": None},
                source=enums.EVENT_SOURCE.agency_api.name,
            )
            for telemetry in validated_data["data"]
        )
        db_helpers.upsert_event_records(
            event_records,
            enums.EVENT_SOURCE.agency_api.name,
            # Agency telemetries are canonical over what may have been polled already
            on_conflict_update=True,
        )

        # We don't have the created event records,
        # but we will return an empty response anyway (cf. DeviceViewSet)
        return []


class DeviceTelemetryResponseSerializer(serializers.Serializer):
    """Response format for the telemetry endpoint."""

    result = serializers.CharField()
    failures = v0_3_vehicles.DeviceTelemetrySerializer(many=True)


class DeviceViewSet(v0_3_vehicles.DeviceViewSet):
    serializers_mapping = dict(
        v0_3_vehicles.DeviceViewSet.serializers_mapping.items(),
        **{
            "telemetry": {
                "request": DeviceTelemetryInputSerializer,
                "response": DeviceTelemetryResponseSerializer,
            },
        }
    )

    @action(detail=False, methods=["post", "options"])
    def telemetry(self, request):
        """Endpoint to receive a telemetry from a provider."""
        context = self.get_serializer_context()  # adds the request to the context
        context["request_or_response"] = "request"
        provider_id = request.user.provider_id
        context["provider"] = models.Provider.objects.get(pk=provider_id)
        serializer = self.get_serializer(data=request.data, context=context)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            # Don't raise or DRF will use its error format
            return to_mds_error_response(exc)

        if is_telemetry_enabled():
            serializer.save()

        # The 0.4 spec is not clear about the return format
        response_serializer = self.get_serializer(
            {
                # Invalid data already rejected
                "result": "%(total)s/%(total)s"
                % {"total": len(serializer.validated_data)},
                # Writing not expected to fail
                "failures": [],
            },
            context={"request_or_response": "response"},
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
