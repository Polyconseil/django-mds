import json
import os.path
import warnings

import yaml
from django.shortcuts import render
from django_filters import rest_framework as filters
from rest_framework import exceptions
from rest_framework import pagination
from rest_framework import serializers as drf_serializers
from rest_framework import viewsets
from rest_framework.compat import coreapi, coreschema
from rest_framework.response import Response
from rest_framework.schemas import inspectors

from mds.access_control.permissions import require_scopes
from mds.access_control.scopes import SCOPE_VEHICLE
from . import models
from . import serializers
from . import enums


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
    to accommodate our :class:`MultiSerializerViewSet`
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


class LimitOffsetPagination(pagination.LimitOffsetPagination):
    default_limit = 500


class DeviceFilter(filters.FilterSet):
    id = filters.CharFilter(lookup_expr="icontains")
    category = filters.MultipleChoiceFilter(choices=enums.DEVICE_CATEGORY_CHOICES)
    provider = filters.UUIDFilter()
    status = filters.MultipleChoiceFilter(
        "telemetries__status", choices=enums.DEVICE_STATUS_CHOICES
    )
    registrationDateFrom = filters.IsoDateTimeFilter(
        "registration_date", lookup_expr="gte"
    )
    registrationDateTo = filters.IsoDateTimeFilter(
        "registration_date", lookup_expr="lte"
    )

    class Meta:
        model = models.Device
        fields = [
            "id",
            "category",
            "provider",
            "status",
            "registrationDateFrom",
            "registrationDateTo",
        ]


class DeviceViewSet(
    viewsets.ModelViewSet, UpdateOnlyModelMixin, MultiSerializerViewSet
):
    def get_queryset(self):
        queryset = models.Device.objects

        provider_id = getattr(self.request.user, "provider_id", None)
        if provider_id:
            queryset = queryset.filter(provider_id=provider_id)

        return queryset.with_latest_telemetry().select_related("provider")

    permission_classes = (require_scopes(SCOPE_VEHICLE),)
    lookup_field = "id"
    serializers_map = {
        "list": serializers.Device,
        "retrieve": serializers.Device,
        "create": serializers.DeviceRegister,
        "update": serializers.DeviceRegister,
        "patch": serializers.DeviceRegister,
    }
    serializer_class = serializers.Device
    schema = CustomViewSchema()
    pagination_class = LimitOffsetPagination
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = DeviceFilter


class AreaViewSet(viewsets.ModelViewSet):
    queryset = models.Area.objects.prefetch_related("polygons").all()
    lookup_field = "id"
    serializer_class = serializers.AreaSerializer
    pagination_class = LimitOffsetPagination


class ProviderViewSet(viewsets.ModelViewSet):
    queryset = models.Provider.objects.all()
    lookup_field = "id"
    serializer_class = serializers.ProviderSerializer


def swagger(request):
    oas_file_path = os.path.join(os.path.dirname(__file__), "oas.yml")
    spec = json.dumps(yaml.load(open(oas_file_path)))
    return render(request, template_name="swagger.html", context={"data": spec})
