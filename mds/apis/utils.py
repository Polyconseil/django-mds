"""A few helpers around DRF."""
import datetime
import json

from django_filters import rest_framework as filters
from rest_framework import pagination
from rest_framework import serializers
from rest_framework.response import Response

from rest_framework import status
from rest_framework.exceptions import APIException
from django.utils.translation import pgettext_lazy

import mds.utils


# Errors #######################################################


class AlreadyRegisteredError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = pgettext_lazy("API Error", "Already registered")
    default_code = "already_registered"


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
        return mds.utils.to_mds_timestamp(value)

    def to_internal_value(self, value: int):
        return mds.utils.from_mds_timestamp(value)


# Schema #########################################################
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
