"""A few helpers around DRF."""
import datetime
import json

from django_filters import rest_framework as filters
from drf_yasg.inspectors import SwaggerAutoSchema
from drf_yasg.inspectors.base import FilterInspector, NotHandled
import drf_yasg.inspectors.base
import drf_yasg.openapi
import drf_yasg.utils
from rest_framework import pagination
from rest_framework import serializers
from rest_framework.response import Response


# Pagination ###################################################


class LimitOffsetPagination(pagination.LimitOffsetPagination):
    default_limit = 100


# Viewsets #####################################################


class MultiSerializerViewSetMixin:
    serializers_mapping = {}

    def _create(self, request, *args, **kwargs):
        """Patch of rest_framework.mixins.CreateModelMixin.create.

        This patch works with our Request/Response serializers.
        """
        request_serializer = self.get_serializer(
            data=request.data, context={"request_or_response": "request"}
        )
        request_serializer.is_valid(raise_exception=True)
        instance = request_serializer.save()
        response_serializer = self.get_serializer(
            instance=instance, context={"request_or_response": "response"}
        )
        return Response(response_serializer.data, status=201)

    def _update(self, request, *args, **kwargs):
        """Patch of rest_framework.mixins.UpdateModelMixin.create.

        This patch works with our Request/Response serializers.
        """
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        request_serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial,
            context={"request_or_response": "request"},
        )
        request_serializer.is_valid(raise_exception=True)
        request_serializer.save()

        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        response_serializer = self.get_serializer(
            instance=instance, context={"request_or_response": "response"}
        )
        return Response(response_serializer.data)

    def get_serializer(self, *args, **kwargs):
        context = kwargs.get("context", {})
        context.update(self.get_serializer_context())
        kwargs["context"] = context
        request_or_response = context.get("request_or_response", "response")
        action = self.action
        if action == "partial_update":
            action = "update"
        serializer = self.serializers_mapping.get(action, {}).get(request_or_response)
        if serializer:
            return serializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)


# Serializers ##################################################


class EmptyResponseSerializer(serializers.Serializer):
    pass


class BaseGeometrySerializer(serializers.Serializer):
    def to_representation(self, value):
        if isinstance(value, dict) or value is None:
            return value
        return json.loads(value.geojson)

    def to_internal_value(self, value):
        if not isinstance(value, dict):
            value = json.loads(value)
        return value


class PointSerializer(BaseGeometrySerializer):
    type = serializers.ChoiceField(["Point"])
    coordinates = serializers.ListField(
        child=serializers.FloatField(), min_length=2, max_length=3
    )  # could include altitude


class MultiPointSerializer(BaseGeometrySerializer):
    type = serializers.ChoiceField(["MultiPoint"])
    coordinates = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField())
    )


class PolygonSerializer(BaseGeometrySerializer):
    type = serializers.ChoiceField(["Polygon"])
    coordinates = serializers.ListField(
        child=serializers.ListField(
            child=serializers.ListField(child=serializers.FloatField())
        )
    )


class UnixTimestampMilliseconds(serializers.IntegerField):
    def to_representation(self, value: datetime.datetime):
        td = value - datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
        return int(td.total_seconds() * 1000 + td.microseconds / 1000)

    def to_internal_value(self, value: int):
        dt = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
        return dt + datetime.timedelta(microseconds=value * 1000)


# Schema #########################################################


def _call_view_method(
    view, method_name, fallback_attr=None, default=None, args=None, kwargs=None
):
    """Override of drf_yasg.inspectors.base.call_view_method to allow passing args."""
    if hasattr(view, method_name):
        try:
            view_method, is_callabale = drf_yasg.inspectors.base.is_callable_method(
                view, method_name
            )
            if is_callabale:
                args = args or []
                kwargs = kwargs or {}
                return view_method(*args, **kwargs)
        except Exception:  # noqa
            drf_yasg.inspectors.base.logger.warning(
                "view's %s raised exception during schema generation; use "
                "`getattr(self, 'swagger_fake_view', False)` to detect and short-circuit this",
                type(view).__name__,
                exc_info=True,
            )

    if fallback_attr and hasattr(view, fallback_attr):
        return getattr(view, fallback_attr)

    return default


class CustomSwaggerAutoSchema(SwaggerAutoSchema):
    """Customer Schema generator that understands Request and Response serializers.

    By default DRF has no concept of Request serializer VS Response serializer.
    A view only defines one serializer which could be limiting.
    This Schema generator, in combination with MultiSerializerViewSetMixin bypasses
    this limitation.
    """

    def get_view_serializer(self, request_or_response):
        """Return the serializer as defined by the view's ``get_serializer()`` method.

        :return: the view's ``Serializer``
        :rtype: rest_framework.serializers.Serializer
        """
        return _call_view_method(
            self.view,
            "get_serializer",
            kwargs={"context": {"request_or_response": request_or_response}},
        )

    def get_request_serializer(self):
        """Return the request serializer (used for parsing the request payload) for this endpoint.

        :return: the request serializer, or one of :class:`.Schema`, :class:`.SchemaRef`, ``None``
        :rtype: rest_framework.serializers.Serializer
        """
        body_override = self._get_request_body_override()

        if body_override is None and self.method in self.implicit_body_methods:
            return self.get_view_serializer("request")

        if body_override is drf_yasg.utils.no_body:
            return None

        return body_override

    def get_default_response_serializer(self):
        """Return the default response serializer for this endpoint. This is derived from either the ``request_body``
        override or the request serializer (:meth:`.get_view_serializer`).

        :return: response serializer, :class:`.Schema`, :class:`.SchemaRef`, ``None``
        """
        body_override = self._get_request_body_override()
        if body_override and body_override is not drf_yasg.utils.no_body:
            return body_override

        return self.get_view_serializer("response")


class CustomFilterInspector(FilterInspector):
    def _convert_range_field_to_parameters(self, field_name, field):
        """ Generate two separate query parameters for range filters """
        if isinstance(field, filters.NumberFilter):
            type_ = drf_yasg.openapi.TYPE_NUMBER
        else:
            type_ = drf_yasg.openapi.TYPE_STRING
        common_params = dict(
            in_=drf_yasg.openapi.IN_QUERY, required=field.extra["required"], type=type_
        )
        return (
            drf_yasg.openapi.Parameter(
                name=f"{field_name}_{field.field_class.widget.suffixes[0]}",
                description=f'{field.extra.get("help_text", "range")} (lower bound)',
                **common_params,
            ),
            drf_yasg.openapi.Parameter(
                name=f"{field_name}_{field.field_class.widget.suffixes[1]}",
                description=f'{field.extra.get("help_text", "range")} (upper bound)',
                **common_params,
            ),
        )

    def _convert_field_to_parameters(self, field_name, field):
        extra_param = {}
        if isinstance(field, filters.RangeFilter):
            return self._convert_range_field_to_parameters(field_name, field)

        if isinstance(field, filters.MultipleChoiceFilter):
            type_ = drf_yasg.openapi.TYPE_ARRAY
            extra_param["items"] = drf_yasg.openapi.Items(
                type=drf_yasg.openapi.TYPE_STRING,
                enum=[c for c, _ in field.extra["choices"]],
            )
            extra_param["collection_format"] = "multi"
        else:
            if isinstance(field, filters.ChoiceFilter):
                type_ = subtype = drf_yasg.openapi.TYPE_STRING
                extra_param["enum"] = [c for c, _ in field.extra["choices"]]
            elif isinstance(field, filters.NumberFilter):
                type_ = subtype = drf_yasg.openapi.TYPE_NUMBER
            else:
                type_ = subtype = drf_yasg.openapi.TYPE_STRING
            if field.lookup_expr == "in":
                type_ = drf_yasg.openapi.TYPE_ARRAY
                extra_param["items"] = drf_yasg.openapi.Items(
                    type=subtype, enum=extra_param.pop("enum", None)
                )
        return (
            drf_yasg.openapi.Parameter(
                name=field_name,
                in_=drf_yasg.openapi.IN_QUERY,
                required=field.extra["required"],
                description=field.extra.get("help_text", ""),
                type=type_,
                **extra_param,
            ),
        )

    def get_filter_parameters(self, filter_backend):
        if not hasattr(filter_backend, "get_filterset_class"):
            return NotHandled

        queryset = self.view.get_queryset()
        filterset_class = filter_backend.get_filterset_class(self.view, queryset)

        parameters = []
        if filterset_class:
            for field_name, field in filterset_class.base_filters.items():
                parameters += self._convert_field_to_parameters(field_name, field)
        return parameters


# Filters #########################################################


class UUIDInFilter(filters.BaseInFilter, filters.UUIDFilter):
    pass


class ChoicesInFilter(filters.BaseInFilter, filters.ChoiceFilter):
    pass


class DateTimeRangeOverlapFilter(filters.IsoDateTimeFromToRangeFilter):
    # Handles datetime range overlap filter
    def filter(self, qs, value):
        if not value:
            return qs

        lookup = "%s__%s" % (self.field_name, "overlap")
        return self.get_method(qs)(**{lookup: (value.start, value.stop)})
