from django.contrib import admin
from django.urls import include, path

from accounts.views import SonogaPasswordChangeView
from core.views import health, home, readiness

from reports.views import (
    management_dashboard,
    general_manager_dashboard,
    management_csv,
)


urlpatterns = [

    # ============================================================
    # SYSTEM HEALTH
    # ============================================================

    path(
        "health/",
        health,
        name="health",
    ),

    path(
        "ready/",
        readiness,
        name="readiness",
    ),


    # ============================================================
    # ADMIN
    # ============================================================

    path(
        "admin/",
        admin.site.urls,
    ),


    # ============================================================
    # AUTHENTICATION
    # ============================================================

    path(
        "accounts/password_change/",
        SonogaPasswordChangeView.as_view(),
        name="password_change",
    ),

    path(
        "accounts/",
        include("django.contrib.auth.urls"),
    ),


    # ============================================================
    # EXECUTIVE DASHBOARDS
    # ============================================================

    # CEO / Group Management Dashboard
    path(
        "dashboard/",
        management_dashboard,
        name="management_dashboard",
    ),

    # General Manager Dashboard
    # Controls / monitors all active business units
    path(
        "general-manager/",
        general_manager_dashboard,
        name="general_manager_dashboard",
    ),


    # ============================================================
    # MANAGEMENT REPORTS
    # ============================================================

    path(
        "reports/",
        include("reports.urls"),
    ),

    # Management CSV export
    path(
        "reports/management.csv",
        management_csv,
        name="management_csv",
    ),


    # ============================================================
    # INVENTORY
    # ============================================================

    path(
        "inventory/",
        include("inventory.urls"),
    ),


    # ============================================================
    # PROCUREMENT
    # ============================================================

    path(
        "procurement/",
        include("procurement.urls"),
    ),


    # ============================================================
    # PAYROLL
    # ============================================================

    path(
        "payroll/",
        include("payroll.urls"),
    ),


    # ============================================================
    # SYSTEM CONTROL
    # ============================================================

    path(
        "control/",
        include("control.urls"),
    ),


    # ============================================================
    # SONOGA HOTELS
    # ============================================================

    path(
        "hotel/",
        include("hotel.urls"),
    ),


    # ============================================================
    # FACTORIES
    # Mabinas Water / Mabinas Bread / Crown Field
    # ============================================================

    path(
        "factory/",
        include("factory.urls"),
    ),


    # ============================================================
    # FINANCE
    # ============================================================

    path(
        "finance/",
        include("finance.urls"),
    ),


    # ============================================================
    # HUMAN RESOURCES
    # ============================================================

    path(
        "hr/",
        include("hr.urls"),
    ),


    # ============================================================
    # INTEGRATIONS / API
    # ============================================================

    path(
        "api/",
        include("integrations.urls"),
    ),


    # ============================================================
    # HOME
    # ============================================================

    path(
        "",
        home,
        name="home",
    ),
]
