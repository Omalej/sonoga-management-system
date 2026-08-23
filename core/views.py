from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render
from accounts.access import (
    ACCOUNTANT, AUDITOR, BREAD_MANAGER, GROUP_MANAGEMENT, HOTEL_MANAGER, HOUSEKEEPING,
    HR_MANAGER, PRODUCTION_SUPERVISOR, RECEPTIONIST, SALES_OFFICER,
    STOREKEEPER, WATER_MANAGER, business_unit_for, has_any_role,
)
from organization.models import BusinessUnit


def health(request):
    return JsonResponse({"ok": True, "service": "sonoga-hms"})


def readiness(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        unit_count = BusinessUnit.objects.filter(is_active=True).count()
        return JsonResponse({"ok": True, "database": "ready", "active_business_units": unit_count})
    except Exception:
        return JsonResponse({"ok": False, "database": "unavailable"}, status=503)


@login_required
def home(request):
    user = request.user
    if user.is_superuser or has_any_role(user, GROUP_MANAGEMENT, AUDITOR):
        return redirect("management_dashboard")
    if has_any_role(user, ACCOUNTANT):
        return redirect("finance:dashboard")
    if has_any_role(user, HR_MANAGER):
        return redirect("hr:dashboard")
    if has_any_role(user, HOUSEKEEPING):
        return redirect("hotel:housekeeping")
    if has_any_role(user, HOTEL_MANAGER, RECEPTIONIST):
        return redirect("hotel:dashboard")
    if has_any_role(user, WATER_MANAGER, BREAD_MANAGER, PRODUCTION_SUPERVISOR, STOREKEEPER, SALES_OFFICER):
        unit = business_unit_for(user)
        if unit and unit.unit_type in {BusinessUnit.UnitType.WATER, BusinessUnit.UnitType.BREAD}:
            return redirect("factory:dashboard", code=unit.code)
        return redirect("factory:dashboard_default")
    return render(request, "home.html")
