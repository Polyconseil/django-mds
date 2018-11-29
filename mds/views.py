import json
import yaml
import warnings

from django.shortcuts import render

from rest_framework import mixins
from rest_framework import serializers as drf_serializers
from rest_framework import viewsets
from rest_framework.compat import coreapi, coreschema
from rest_framework.response import Response
from rest_framework.schemas import inspectors
from rest_framework import exceptions

from . import models
from . import serializers


class MultiSerializerViewSet(viewsets.GenericViewSet):
    serializers_map = {}

    def get_serializer_class(self):
        return (
            self.serializers_map.get(self.action, None)
            or super().get_serializer_class()
        )


class CustomViewSchema(inspectors.AutoSchema):
    """
    Overrides `get_serializer_fields()`
    to accomodate our :class:`MultiSerializerViewSet`
    """

    def get_serializer_fields(self, path, method):
        view = self.view

        # set view action
        method = method.lower()
        if method == "options":
            view.action = "metadata"
        else:
            view.action = view.action_map.get(method)

        if method not in ("put", "patch", "post"):
            return []

        if not hasattr(view, "get_serializer"):
            return []

        try:
            serializer = view.get_serializer()
        except exceptions.APIException:
            serializer = None
            warnings.warn(
                "{}.get_serializer() raised an exception during "
                "schema generation. Serializer fields will not be "
                "generated for {} {}.".format(
                    view.__class__.__name__, method.upper(), path
                )
            )

        if isinstance(serializer, drf_serializers.ListSerializer):
            return [
                coreapi.Field(
                    name="data",
                    location="body",
                    required=True,
                    schema=coreschema.Array(),
                )
            ]

        if not isinstance(serializer, drf_serializers.Serializer):
            return []

        return [
            coreapi.Field(
                name=field.field_name,
                location="body",
                required=field.required and method != "patch",
                schema=inspectors.field_to_schema(field),
            )
            for field in serializer.fields.values()
            if not (field.read_only or isinstance(field, drf_serializers.HiddenField))
        ]


class UpdateOnlyModelMixin(object):
    """
    Update a model instance.
    """

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()


class DeviceViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    UpdateOnlyModelMixin,
    MultiSerializerViewSet,
):
    queryset = models.Device.objects.all()
    lookup_field = "id"
    serializers_map = {
        "list": serializers.Device,
        "retrieve": serializers.Device,
        "create": serializers.DeviceRegister,
        "update": serializers.DeviceTelemetry,
    }
    serializer_class = serializers.Device
    schema = CustomViewSchema()


class AreaViewSet(viewsets.ModelViewSet):
    queryset = models.Area.objects.all()
    lookup_field = "id"
    serializer_class = serializers.ServiceAreaSerializer


def swagger(request):
    spec = json.dumps(yaml.load(open("mds/oas.yml")))
    return render(request, template_name="swagger.html", context={"data": spec})
