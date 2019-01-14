from django.conf.urls import include
from django.contrib import admin
from django.urls import path

import mds.apis.agency_api.v0_x.urls
import mds.apis.prv_api.urls


urlpatterns = [
    path(
        "mds/v0.x/",
        include(
            (
                mds.apis.agency_api.v0_x.urls.get_url_patterns(prefix="mds/v0.x"),
                "agency",
            )
        ),
    ),
    path("prv/", include(mds.apis.prv_api.urls, namespace="private")),
    path("admin/", admin.site.urls),
]
