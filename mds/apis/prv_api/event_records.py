import django_filters.rest_framework
from rest_framework import pagination, serializers, viewsets

from mds.access_control import scopes
from mds.access_control.permissions import require_scopes
import mds.models


class EventRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = mds.models.EventRecord
        fields = ["timestamp", "event_type"]


class EventRecordViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EventRecordSerializer
    queryset = mds.models.EventRecord.objects.order_by("-timestamp")
    pagination_class = pagination.LimitOffsetPagination
    permission_classes = [require_scopes(scopes.SCOPE_PRV_API)]
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filterset_fields = ("device",)
