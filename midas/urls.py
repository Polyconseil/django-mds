"""
URL Configuration
"""
from django.conf.urls import url, include
from django.contrib import admin
from django.urls import path
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r'service_area', views.ServiceAreaViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
    path("admin/", admin.site.urls),
]
