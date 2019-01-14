from rest_framework import serializers
from rest_framework import viewsets

from mds import models
from mds.access_control.permissions import require_scopes
from mds.access_control.scopes import SCOPE_ADMIN
from mds.apis import utils


class PolygonSerializer(serializers.ModelSerializer):
    """A geographic polygon.
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
    geom = utils.GeometryField(help_text="GeoJSON Polygon")

    class Meta:
        model = models.Polygon
        fields = ("id", "label", "creation_date", "deletion_date", "geom", "properties")


class AreaSerializer(serializers.ModelSerializer):
    """A service area, composed of a group of Polygons.
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


class PolygonViewSet(viewsets.ModelViewSet):
    permission_classes = (require_scopes(SCOPE_ADMIN),)
    queryset = models.Polygon.objects.all()
    lookup_field = "id"
    serializer_class = PolygonSerializer


class AreaViewSet(viewsets.ModelViewSet):
    permission_classes = (require_scopes(SCOPE_ADMIN),)
    queryset = models.Area.objects.prefetch_related("polygons").all()
    lookup_field = "id"
    serializer_class = AreaSerializer
