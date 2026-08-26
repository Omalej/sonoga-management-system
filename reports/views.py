import csv
import json
from datetime import date

from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from accounts.access import (
    AUDITOR,
    CEO,
    GENERAL_MANAGER,
    GROUP_MANAGEMENT,
    role_required,
)

from organization.models import BusinessUnit

from .services import group_summary


def _period(request):
    today = timezone.localdate()

    start = request.GET.get("start")
    end = request.GET.get("end")

    try:
        start_date = date.fromisoformat(start) if start else today
        end_date = date.fromisoformat(end) if end else today
    except (ValueError, TypeError):
        start_date = end_date = today

    if end_date < start_date:
        start_date, end_date = end_date, start_date

    return start_date, end_date


def _dashboard_context(request):
    start_date, end_date = _period(request)

    selected_unit = request.GET.get("unit", "").strip()

    context = group_summary(
        start_date=start_date,
        end_date=end_date,
    )

    business_units = BusinessUnit.objects.filter(
        is_active=True
    ).order_by("name")

    # ============================================================
    # FILTER BUSINESS UNIT
    # ============================================================

    if selected_unit:
        context["rows"] = [
            row
            for row in context["rows"]
            if row["business_unit"].code == selected_unit
        ]

        # Recalculate totals for selected business unit.
        context["totals"] = {
            "revenue": sum(
                (row["revenue"] for row in context["rows"]),
                0,
            ),
            "cash_received": sum(
                (row["cash_received"] for row in context["rows"]),
                0,
            ),
            "expenses": sum(
                (row["expenses"] for row in context["rows"]),
                0,
            ),
            "payroll": sum(
                (row["payroll"] for row in context["rows"]),
                0,
            ),
            "receivables": sum(
                (row["receivables"] for row in context["rows"]),
                0,
            ),
            "operating_result": sum(
                (row["operating_result"] for row in context["rows"]),
                0,
            ),
        }

    # ============================================================
    # BUSINESS UNITS
    # ============================================================

    context["business_units"] = business_units
    context["selected_unit"] = selected_unit

    # ============================================================
    # CHART DATA
    # ============================================================

    chart_labels = [
        row["business_unit"].name
        for row in context["rows"]
    ]

    chart_revenue = [
        float(row["revenue"])
        for row in context["rows"]
    ]

    chart_expenses = [
        float(row["expenses"])
        for row in context["rows"]
    ]

    chart_profit = [
        float(row["operating_result"])
        for row in context["rows"]
    ]

    context["chart_labels"] = json.dumps(chart_labels)
    context["chart_revenue"] = json.dumps(chart_revenue)
    context["chart_expenses"] = json.dumps(chart_expenses)
    context["chart_profit"] = json.dumps(chart_profit)

    # ============================================================
    # PERIODS
    # ============================================================

    today = timezone.localdate()

    context["periods"] = {
        "today": today,
        "month_start": today.replace(day=1),
    }

    return context


# ============================================================
# CEO / GROUP MANAGEMENT DASHBOARD
# ============================================================

@role_required(
    CEO,
    GROUP_MANAGEMENT,
    AUDITOR,
)
def management_dashboard(request):
    context = _dashboard_context(request)

    context["dashboard_title"] = (
        "CEO / Group Management Dashboard"
    )

    context["dashboard_role"] = "CEO"

    return render(
        request,
        "reports/management_dashboard.html",
        context,
    )


# ============================================================
# GENERAL MANAGER DASHBOARD
# ============================================================

@role_required(GENERAL_MANAGER)
def general_manager_dashboard(request):
    context = _dashboard_context(request)

    context["dashboard_title"] = (
        "General Manager Dashboard"
    )

    context["dashboard_role"] = "General Manager"

    return render(
        request,
        "reports/general_manager_dashboard.html",
        context,
    )


# ============================================================
# MANAGEMENT CSV
# ============================================================

@role_required(
    CEO,
    GROUP_MANAGEMENT,
    AUDITOR,
)
def management_csv(request):
    start_date, end_date = _period(request)

    report = group_summary(
        start_date=start_date,
        end_date=end_date,
    )

    response = HttpResponse(
        content_type="text/csv"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="sonoga-management-'
        f'{start_date}-{end_date}.csv"'
    )

    writer = csv.writer(response)

    writer.writerow([
        "Sonoga Group Management Report",
        f"{start_date} to {end_date}",
    ])

    writer.writerow([])

    writer.writerow([
        "Business Unit",
        "Revenue",
        "Cash Received",
        "Receivables",
        "Expenses",
        "Payroll",
        "Operating Result",
    ])

    for row in report["rows"]:
        writer.writerow([
            row["business_unit"].name,
            row["revenue"],
            row["cash_received"],
            row["receivables"],
            row["expenses"],
            row["payroll"],
            row["operating_result"],
        ])

    totals = report["totals"]

    writer.writerow([
        "SONOGA GROUP TOTAL",
        totals["revenue"],
        totals["cash_received"],
        totals["receivables"],
        totals["expenses"],
        totals["payroll"],
        totals["operating_result"],
    ])

    return response
