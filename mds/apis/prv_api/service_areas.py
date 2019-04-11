import json
import random

from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from django.db import IntegrityError

from mds import models
from mds.access_control.permissions import require_scopes
from mds.access_control.scopes import SCOPE_PRV_API
from mds.apis import utils

from rest_framework import filters


class PolygonRequestSerializer(serializers.ModelSerializer):
    """What we expect for a geographic polygon.
    """

    label = serializers.CharField(help_text="Name of the polygon")
    geom = utils.PolygonSerializer(help_text="GeoJSON Polygon")
    areas = serializers.PrimaryKeyRelatedField(many=True, queryset=models.Area.objects)

    class Meta:
        fields = ("geom", "label", "areas")
        model = models.Polygon

    def create(self, validated_data):
        instance = self.Meta.model(
            label=validated_data["label"], geom=json.dumps(validated_data["geom"])
        )
        instance.save()
        return instance

    def update(self, instance, validated_data):
        if validated_data.get("label"):
            instance.label = validated_data["label"]
        if validated_data.get("geom"):
            instance.geom = json.dumps(validated_data["geom"])
        if validated_data.get("areas"):
            areas = validated_data.pop("areas", [])
            instance.areas.set(areas)
        instance.save()
        return instance


class PolygonResponseSerializer(serializers.Serializer):
    """A representation of a geographic polygon.
    """

    id = serializers.UUIDField(help_text="Unique Polygon identifier (UUID)")
    label = serializers.CharField(help_text="Name of the polygon")
    geom = utils.PolygonSerializer(help_text="GeoJSON Polygon")
    areas = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        fields = ("id", "label", "geom", "areas")


class PolygonsImportRequestSerializer(serializers.Serializer):

    polygons = PolygonRequestSerializer(many=True)

    class Meta:
        fields = "polygons"


class PolygonViewSet(utils.MultiSerializerViewSetMixin, viewsets.ModelViewSet):
    permission_classes = (require_scopes(SCOPE_PRV_API),)
    queryset = models.Polygon.objects.prefetch_related("areas").all()
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ("label",)
    ordering = "label"
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
        "import_polygons": {
            "request": PolygonsImportRequestSerializer,
            "response": utils.EmptyResponseSerializer,
        },
    }

    def create(self, *args, **kwargs):
        return super()._create(*args, **kwargs)

    def update(self, *args, **kwargs):
        return super()._update(*args, **kwargs)

    @action(methods=["post"], url_path="import", detail=False)
    def import_polygons(self, request, pk=None):
        polygons = request.data.get("polygons", None)

        if not isinstance(polygons, list):
            return Response(status=400)

        try:
            polygons_to_create = []
            for polygon in polygons:
                geom = polygon.get("geom", None)
                if geom and geom["type"] == "Polygon":

                    areas = []
                    for area_label in polygon.get("areas", []):
                        defaults = {"color": "#%06x" % random.randint(0, 0xFFFFFF)}
                        # Create new Area if doesn't exist (based on label)
                        area = models.Area.objects.get_or_create(
                            label=area_label, defaults=defaults
                        )[0]
                        areas.append(area)
                    poly = models.Polygon(
                        label=polygon.get("label", ""), geom=str(geom)
                    )
                    poly.areas.set([a.id for a in areas])
                    polygons_to_create.append(poly)
            models.Polygon.objects.bulk_create(polygons_to_create)
        except IntegrityError as ex:
            return Response(exception=ex, status=500)

        return Response({"message": "ok"})


class AreaRequestSerializer(serializers.ModelSerializer):
    """A service area, composed of a group of Polygons.
    """

    label = serializers.CharField(help_text="Name of the Area")
    polygons = serializers.PrimaryKeyRelatedField(
        many=True, queryset=models.Polygon.objects
    )
    color = serializers.CharField(required=False, help_text="Color of the Area")

    class Meta:
        fields = ("label", "polygons", "color")
        model = models.Area

    def create(self, validated_data):
        instance = self.Meta.model(
            label=validated_data["label"], color=validated_data["color"]
        )
        instance.save()
        polygons = validated_data.get("polygons", [])
        instance.polygons.set(polygons)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        if validated_data.get("label"):
            instance.label = validated_data["label"]
        if validated_data.get("color"):
            instance.color = validated_data["color"]
        if "polygons" in validated_data:
            polygons = validated_data.get("polygons", [])
            instance.polygons.set(polygons)
        instance.save()
        return instance


class AreaResponseSerializer(serializers.Serializer):
    """A service area, composed of a group of Polygons.
    """

    id = serializers.UUIDField(help_text="Unique Area identifier (UUID)")
    label = serializers.CharField(help_text="Name of the Area")
    polygons = PolygonResponseSerializer(many=True)
    color = serializers.CharField(help_text="Color of the Area")

    class Meta:
        fields = ("id", "label", "polygons", "color")


class AreaViewSet(utils.MultiSerializerViewSetMixin, viewsets.ModelViewSet):
    permission_classes = (require_scopes(SCOPE_PRV_API),)
    queryset = models.Area.objects.prefetch_related("polygons").all()
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ("label",)
    ordering = "label"
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
