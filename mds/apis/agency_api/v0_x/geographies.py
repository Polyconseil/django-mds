from rest_framework import exceptions
from rest_framework import response
from rest_framework import viewsets

from mds import models


class GeographyViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = ()  # Public endpoint
    # Allow to access geographies from any published policy
    # Past or future, active or superseded by another policy
    queryset = models.Policy.objects.filter(published_date__isnull=False)

    def list(self, request, *args, **kwargs):
        # The spec excluded that use case
        raise exceptions.NotFound()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # We already dump the geographies as a dict of FeatureCollections
        # Just flatten the dict to a list
        features = instance.geographies.values()

        return response.Response(
            # Geographies already stored in the GeoJSON format
            {"type": "FeatureCollection", "features": features}
        )
