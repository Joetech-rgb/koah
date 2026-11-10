from __future__ import annotations
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    path("", include("dashboard.urls")),
    path("admin/", admin.site.urls),
    path("api/brain/", include("brain.urls")),
    path("api/agent/", include("agent.urls")),
    path("api/crm/", include("crm.urls")),
    path("api/reporting/", include("reporting.urls")),
    path("api/outreach/", include("outreach.urls")),
    path("api/prospecting/", include("prospecting.urls")),
]
