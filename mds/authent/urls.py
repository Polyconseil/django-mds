from django.urls import path
import oauth2_provider.urls

from . import views


app_name = "authent"
urlpatterns = oauth2_provider.urls.urlpatterns + [
    path(
        "long_lived_token/", views.LongLivedTokenView.as_view(), name="long_lived_token"
    )
]
