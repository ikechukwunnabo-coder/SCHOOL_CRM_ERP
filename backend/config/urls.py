from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import health_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="api-docs"),
    path("api/v1/health/", health_check, name="health-check"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.institutions.urls")),
    path("api/v1/admissions/", include("apps.admissions.urls")),
    path("api/v1/", include("apps.students.urls")),
    path("api/v1/", include("apps.imports.urls")),
    path("api/v1/", include("apps.employees.urls")),
    path("api/v1/", include("apps.academics.urls")),
    path("api/v1/", include("apps.teaching.urls")),
    path("api/v1/", include("apps.attendance.urls")),
    path("api/v1/examinations/", include("apps.examinations.urls")),
    path("api/v1/transcripts/", include("apps.transcripts.urls")),
    path("api/v1/alumni/", include("apps.alumni.urls")),
    path("api/v1/finance/", include("apps.finance.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    path("api/v1/accounting/", include("apps.accounting.urls")),
]
