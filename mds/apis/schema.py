"""A few helpers around Swagger."""
from django_filters import rest_framework as filters
from drf_yasg.inspectors import SwaggerAutoSchema
from drf_yasg.inspectors.base import FilterInspector, NotHandled
import drf_yasg.inspectors.base
import drf_yasg.openapi
import drf_yasg.utils


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
