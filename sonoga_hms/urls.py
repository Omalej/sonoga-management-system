from django.contrib import admin
from django.urls import include, path
from accounts.views import SonogaPasswordChangeView
from core.views import health, home, readiness
from reports.views import management_dashboard

urlpatterns = [
    path("organization/", include("organization.urls")),

    path("health/", health, name="health"),
    path("ready/", readiness, name="readiness"),
    path("admin/", admin.site.urls),
    path("accounts/password_change/", SonogaPasswordChangeView.as_view(), name="password_change"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("dashboard/", management_dashboard, name="management_dashboard"),
    path("reports/", include("reports.urls")),
    path("inventory/", include("inventory.urls")),
    path("procurement/", include("procurement.urls")),
    path("payroll/", include("payroll.urls")),
    path("control/", include("control.urls")),
    path("hotel/", include("hotel.urls")),
    path("factory/", include("factory.urls")),
    path("finance/", include("finance.urls")),
    path("hr/", include("hr.urls")),
    path("api/", include("integrations.urls")),
    path("", home, name="home"),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
