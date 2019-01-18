"""Swappable models are badly designed in oauth2_provider.

see https://github.com/jazzband/django-oauth-toolkit/issues/634

This custom conf together with the setting
MIGRATION_MODULES = {"oauth2_provider": None}
enables to override all the models without quirks.
"""
import os

from pkg_resources import get_distribution
from django.apps import AppConfig


class Config(AppConfig):
    name = "oauth2_provider"
    verbose_name = "Django OAuth Toolkit"
    path = os.path.join(
        get_distribution("django-oauth-toolkit").location, "oauth2_provider"
    )

    def get_models(self, *args, **kwargs):
        excluded_models = {"Application", "AccessToken", "Grant", "RefreshToken"}
        yield from (
            model
            for model in super().get_models()
            if model.__name__ not in excluded_models
        )
