from rest_framework import serializers
from rest_framework import viewsets

from mds import models
from mds.access_control.permissions import require_scopes
from mds.access_control.scopes import SCOPE_ADMIN
from mds.apis import utils


class PolygonRequestSerializer(serializers.ModelSerializer):
    """What we expect for a geographic polygon.
    """

    label = serializers.CharField(help_text="Name of the polygon")
    geom = utils.GeometryField(help_text="GeoJSON Polygon")

    class Meta:
        fields = ("geom", "label")
        model = models.Polygon


class PolygonResponseSerializer(serializers.Serializer):
    """A representation of a geographic polygon.
    """

    id = serializers.UUIDField(help_text="Unique Polygon identifier (UUID)")
    label = serializers.CharField(help_text="Name of the polygon")
    creation_date = serializers.DateTimeField(help_text="Polygon creation date")
    deletion_date = serializers.DateTimeField(
        required=False, help_text="Polygon deletion date"
    )
    geom = utils.GeometryField(help_text="GeoJSON Polygon")
    areas = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        fields = ("id", "label", "creation_date", "deletion_date", "geom", "areas")


class PolygonViewSet(utils.MultiSerializerViewSetMixin, viewsets.ModelViewSet):
    permission_classes = (require_scopes(SCOPE_ADMIN),)
    queryset = models.Polygon.objects.prefetch_related("areas").all()
    lookup_field = "id"
    serializer_class = PolygonResponseSerializer
    serializers_mapping = {
        "list": {"response": PolygonResponseSerializer},
        "retrieve": {"response": PolygonResponseSerializer},
        "create": {
            "request": PolygonRequestSerializer,
            "response": utils.EmptyResponseSerializer,
        },
        "update": {
            "request": PolygonRequestSerializer,
            "response": utils.EmptyResponseSerializer,
        },
    }

    def create(self, *args, **kwargs):
        return super()._create(*args, **kwargs)

    def update(self, *args, **kwargs):
        return super()._update(*args, **kwargs)


class AreaRequestSerializer(serializers.ModelSerializer):
    """A service area, composed of a group of Polygons.
    """

    label = serializers.CharField(help_text="Name of the Area")
    polygons = PolygonRequestSerializer(required=False, many=True)
    color = serializers.CharField(required=False, help_text="Color of the Area")

    class Meta:
        fields = ("label", "polygons", "color")
        model = models.Area


class AreaResponseSerializer(serializers.Serializer):
    """A service area, composed of a group of Polygons.
    """

    id = serializers.UUIDField(help_text="Unique Area identifier (UUID)")
    label = serializers.CharField(help_text="Name of the Area")
    creation_date = serializers.DateTimeField(help_text="Area creation date")
    deletion_date = serializers.DateTimeField(
        required=False, help_text="Area deletion date"
    )
    label = serializers.CharField(help_text="Name of the Area")
    polygons = PolygonResponseSerializer(many=True)
    color = serializers.CharField(help_text="Color of the Area")

    class Meta:
        fields = ("id", "label", "creation_date", "deletion_date", "polygons", "color")


class AreaViewSet(utils.MultiSerializerViewSetMixin, viewsets.ModelViewSet):
    permission_classes = (require_scopes(SCOPE_ADMIN),)
    queryset = models.Area.objects.prefetch_related("polygons").all()
    lookup_field = "id"
    serializer_class = AreaResponseSerializer
    serializers_mapping = {
        "list": {"response": AreaResponseSerializer},
        "retrieve": {"response": AreaResponseSerializer},
        "create": {
            "request": AreaRequestSerializer,
            "response": utils.EmptyResponseSerializer,
        },
        "update": {
            "request": AreaRequestSerializer,
            "response": utils.EmptyResponseSerializer,
        },
    }

    def create(self, *args, **kwargs):
        return super()._create(*args, **kwargs)

    def update(self, *args, **kwargs):
        return super()._update(*args, **kwargs)
