from rest_framework import viewsets

from . import models
from . import serializers


class ServiceAreaViewSet(viewsets.ModelViewSet):
    queryset = models.Service.objects.all()
    serializer_class = serializers.ServiceAreaSerializer
