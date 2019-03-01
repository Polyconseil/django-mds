import json

from rest_framework import serializers
from rest_framework import viewsets

from mds import enums
from mds import models
from mds.access_control.permissions import require_scopes
from mds.access_control.scopes import SCOPE_AGENCY_API
from mds.apis import utils


class MultiPolygonField(serializers.Field):
    def to_representation(self, value):
        ret = {"type": "MultiPolygon", "coordinates": []}
        for polygon in value:
            ret["coordinates"].append(json.loads(polygon.geom.geojson)["coordinates"])
        return ret

    def to_internal_value(self, value):
        raise NotImplementedError()


class AreaSerializer(serializers.ModelSerializer):
    """A service area
    """

    service_area_id = serializers.UUIDField(
        source="id", help_text="Unique Area identifier (UUID)"
    )
    start_date = utils.UnixTimestampMilliseconds(
        source="creation_date",
        help_text="Date at which this service area became effective",
    )
    end_date = utils.UnixTimestampMilliseconds(
        source="deletion_date",
        required=False,
        help_text="If exists, Date at which this service area was replaced.",
    )
    area = MultiPolygonField(source="polygons.all")
    type = serializers.ChoiceField(
        source="area_type",
        choices=enums.choices(enums.AREA_TYPE),
        default="unrestricted",
    )

    class Meta:
        model = models.Area
        fields = ("service_area_id", "start_date", "end_date", "area", "type")


class AreaViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (require_scopes(SCOPE_AGENCY_API),)
    queryset = models.Area.objects.prefetch_related("polygons").all()
    lookup_field = "id"
    serializer_class = AreaSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        provider_id = getattr(self.request.user, "provider_id", None)
        if provider_id:
            queryset = queryset.filter(providers__id=provider_id)
        else:
            queryset = queryset.none()

        return queryset
