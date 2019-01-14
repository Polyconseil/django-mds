import re
from django.urls import include, path, re_path
from rest_framework import permissions
from rest_framework import routers
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from . import service_areas
from . import vehicles


agency_router = routers.DefaultRouter()
agency_router.register(r"service_areas", service_areas.AreaViewSet)
agency_router.register(r"vehicles", vehicles.DeviceViewSet, basename="device")


def get_url_patterns(prefix):
    # the schema view needs the prefix to generate correct urls
    # => url_patterns cannot be hardcoded here
    prefix = re.split(r"[/]+$", prefix)[0]
    prefix = ("%s/" % prefix) if prefix else ""
    schema_view = get_schema_view(
        openapi.Info(
            title="LADOT agency API",
            default_version="v0.2",
            description="see https://github.com/CityOfLosAngeles/mobility-data-specification/tree/dev/agency",
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
