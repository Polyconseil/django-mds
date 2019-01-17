"""A few helpers around DRF."""
import datetime
import json

from django.contrib.gis.geos.geometry import GEOSGeometry
import drf_yasg.inspectors
import drf_yasg.inspectors.base
import drf_yasg.utils
from rest_framework import serializers
from rest_framework.response import Response


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


class GeometryField(serializers.Field):
    type_name = "GeometryField"

    def to_representation(self, value):
        if isinstance(value, dict) or value is None:
            return value
        return json.loads(value.geojson)

    def to_internal_value(self, value):
        if isinstance(value, GEOSGeometry) or value is None:
            return value
        if isinstance(value, dict):
            value = json.dumps(value)
        return GEOSGeometry(value)


class UnixTimestampMilliseconds(serializers.IntegerField):
    def to_representation(self, value: datetime.datetime):
        dt = value - datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
        return int(dt.total_seconds() * 1000)

    def to_internal_value(self, value):
        value = super().to_representation(value)
        dt = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
        return dt + datetime.timedelta(0, 0, 0, value)


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


class CustomSwaggerAutoSchema(drf_yasg.inspectors.SwaggerAutoSchema):
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
