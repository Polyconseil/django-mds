"""
URL Configuration
"""
from django.conf.urls import url, include
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r'service_area', views.ServiceAreaViewSet)


def ok_view(request):
    return HttpResponse("OK", status=200)


urlpatterns = [
    url(r'^', include(router.urls)),
    path("admin/", admin.site.urls),
    path("selftest/ping/", ok_view),
]
