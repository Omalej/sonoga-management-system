from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render

from organization.models import BusinessUnit


def health(request):
    return JsonResponse({
        "ok": True,
        "service": "sonoga-hms",
    })


def readiness(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        unit_count = BusinessUnit.objects.filter(
            is_active=True
        ).count()

        return JsonResponse({
            "ok": True,
            "database": "ready",
            "active_business_units": unit_count,
        })

    except Exception:
        return JsonResponse({
            "ok": False,
            "database": "unavailable",
        }, status=503)


def home(request):
    """
    Main Sonoga portal launcher.

    This page is intentionally not login_required so the
    WordPress homepage can link directly to it.

    Individual portals remain protected by their own
    authentication and permission checks.
    """
    return render(request, "home.html")
