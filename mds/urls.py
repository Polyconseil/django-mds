from django.conf.urls import include
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

import mds.apis.agency_api.v0_3.urls
import mds.authent.urls

urlpatterns = [
    # TODO(hcauwelier) Backwards compat, to remove with MDS 0.3
    path(
        "mds/v0.x/",
        include(
            (
                mds.apis.agency_api.v0_3.urls.get_url_patterns(prefix="mds/v0.x"),
                "agency",
            )
        ),
    ),
    # MDS 0.3
    path(
        "mds/v0.3/",
        include(
            (
                mds.apis.agency_api.v0_3.urls.get_url_patterns(prefix="mds/v0.3"),
                "agency-0.3",
            )
        ),
    ),
    path("admin/", admin.site.urls),
    path("authent/", include(mds.authent.urls, namespace="authent")),
    # oauth2_provider gives views to manage applications.
    # These views require a logged in user.
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="admin/login.html"),
    ),
]
