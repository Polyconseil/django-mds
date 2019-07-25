from rest_framework import decorators, pagination, response, serializers, viewsets

from mds import enums, models, utils
from mds.access_control.permissions import require_scopes
from mds.access_control.scopes import SCOPE_PRV_API
from mds.apis import utils as apis_utils


class DeviceStatusChangesSerializer(serializers.ModelSerializer):
    id = serializers.CharField()
    recorded = apis_utils.UnixTimestampMilliseconds(source="saved_at")
    first_recorded = apis_utils.UnixTimestampMilliseconds(source="first_saved_at")
    associated_trip = serializers.CharField(source="properties.trip_id")
    device_id = serializers.CharField(source="device.id")
    event_location = serializers.SerializerMethodField()
    event_time = apis_utils.UnixTimestampMilliseconds(source="timestamp")
    event_type = serializers.SerializerMethodField()
    event_type_reason = serializers.SerializerMethodField()
    propulsion_type = serializers.ListSerializer(
        source="device.propulsion",
        child=serializers.ChoiceField(choices=enums.choices(enums.DEVICE_PROPULSION)),
    )
    provider_id = serializers.CharField(source="device.provider.id")
    provider_name = serializers.CharField(source="device.provider.name")
    vehicle_id = serializers.CharField(source="device.identification_number")
    vehicle_type = serializers.CharField(source="device.category")

    class Meta:
        model = models.EventRecord
        fields = (
            "id",
            "recorded",
            "first_recorded",
            "associated_trip",
            "device_id",
            "event_location",
            "event_time",
            "event_type",
            "event_type_reason",
            "propulsion_type",
            "provider_name",
            "provider_id",
            "vehicle_id",
            "vehicle_type",
        )

    def create(self, data):
        raise NotImplementedError()

    def update(self, instance, data):
        raise NotImplementedError()

    def get_event_location(self, obj):
        telemetry = obj.properties.get("telemetry", {})
        return {
            "type": "Feature",
            "properties": {"timestamp": telemetry.get("timestamp")},
            "geometry": obj.point_as_geojson,
        }

    def get_event_type(self, obj):
        return enums.EVENT_TYPE_TO_DEVICE_STATUS[obj.event_type]

    def get_event_type_reason(self, obj):
        return enums.AGENCY_EVENT_TO_PROVIDER_REASON[obj.event_type]


class CustomPagination(pagination.PageNumberPagination):
    page_size = 5000
    page_size_query_param = "take"
    max_page_size = 10000

    def get_paginated_response(self, data):
        return response.Response(
            {
                "version": "0.3.0",
                "links": {
                    "next": self.get_next_link(),
                    "prev": self.get_previous_link(),
                },
                "data": {"status_changes": data},
            }
        )


class ProviderApiViewSet(viewsets.ViewSet):
    permission_classes = [require_scopes(SCOPE_PRV_API)]

    @decorators.action(detail=False, methods=["get"])
    def status_changes(self, request, *args, **kwargs):
        skip = request.query_params.get("skip")
        start_recorded = request.query_params.get("start_recorded")
        start_time = request.query_params.get("start_time")
        end_time = request.query_params.get("end_time")

        # Only forward events that were first retrieved though providers'
        # `status_changes' endpoint
        event_types = enums.PROVIDER_REASON_TO_AGENCY_EVENT.values()
        events = models.EventRecord.objects.select_related("device__provider").filter(
            event_type__in=event_types
        )

        # We support either recorded, time search or offset but not at the same time
        if skip:
            order_by = "id"
            events = events.filter(id__gt=int(skip))
        elif start_recorded:
            order_by = "saved_at"
            start_recorded = utils.from_mds_timestamp(int(start_recorded))
            events = events.filter(saved_at__gte=start_recorded)
        else:
            order_by = "timestamp"
            if start_time:
                start_time = utils.from_mds_timestamp(int(start_time))
                events = events.filter(timestamp__gte=start_time)
            if end_time:
                end_time = utils.from_mds_timestamp(int(end_time))
                events = events.filter(timestamp__lte=end_time)

        paginator = CustomPagination()
        page = paginator.paginate_queryset(events.order_by(order_by), request)
        data = DeviceStatusChangesSerializer(page, many=True).data
        return paginator.get_paginated_response(data)
