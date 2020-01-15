import re

from django.urls import include, path, re_path

from rest_framework import permissions
from rest_framework import routers
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# The 0.4 API is 95% compatible with the 0.3 one
from mds.apis.agency_api.v0_3 import geographies
from mds.apis.agency_api.v0_3 import policies
from mds.apis.agency_api.v0_3 import compliances

from . import vehicles


agency_router = routers.DefaultRouter()
agency_router.register(r"vehicles", vehicles.DeviceViewSet, basename="device")
agency_router.register(r"policies", policies.PolicyViewSet, basename="policy")
agency_router.register(
    r"compliance/snapshot", compliances.ComplianceViewSet, basename="compliance"
)

agency_router.register(
    r"geographies", geographies.GeographyViewSet, basename="geography"
)


def get_url_patterns(prefix):
    # the schema view needs the prefix to generate correct urls
    # => url_patterns cannot be hardcoded here
    prefix = re.split(r"[/]+$", prefix)[0]
    prefix = ("%s/" % prefix) if prefix else ""
    schema_view = get_schema_view(
        openapi.Info(
            title="LADOT agency API",
            default_version="v0.4",
            description="see "
            "https://github.com/openmobilityfoundation/mobility-data-specification",
        ),
        patterns=[path(prefix, include(agency_router.urls))],
        public=True,
        permission_classes=(permissions.AllowAny,),
    )

    return agency_router.urls + [
        re_path(
            r"^swagger(?P<format>\.json|\.yaml)$",
            schema_view.without_ui(cache_timeout=0),
            name="schema-json",
        ),
        re_path(
            r"^swagger/$",
            schema_view.with_ui("swagger", cache_timeout=0),
            name="schema-swagger-ui",
        ),
    ]
