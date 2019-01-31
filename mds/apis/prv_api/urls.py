from rest_framework import routers
from django.conf.urls import include
from django.urls import path

from . import providers
from . import service_areas
from . import vehicles
from . import authent


def get_prv_router():
    """Generates a fresh router.

    Enables to register new routes even after .urls has
    been called on the router.
    """
    prv_router = routers.DefaultRouter()
    prv_router.register(r"providers", providers.ProviderViewSet)
    prv_router.register(r"service_areas", service_areas.AreaViewSet)
    prv_router.register(r"polygons", service_areas.PolygonViewSet)
    prv_router.register(r"vehicles", vehicles.DeviceViewSet, basename="device")
    return prv_router


app_name = "mds_prv_api"

auth_urls = [
    path(
        "long_lived_token/",
        authent.LongLivedTokenView.as_view(),
        name="long_lived_token",
    ),
    path("create_application/", authent.AppCreationView.as_view(), name="create_app"),
    path("revoke_application/", authent.AppCreationView.as_view(), name="revoke_app"),
    path("delete_application/", authent.AppCreationView.as_view(), name="delete_app"),
]

urlpatterns = [path("authent/", include(auth_urls))]
urlpatterns += get_prv_router().urls
