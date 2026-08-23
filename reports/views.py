import csv
from datetime import date, timedelta
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from accounts.access import AUDITOR, GROUP_MANAGEMENT, role_required
from .services import group_summary


def _period(request):
    today = timezone.localdate()
    start = request.GET.get("start")
    end = request.GET.get("end")
    try:
        start_date = date.fromisoformat(start) if start else today
        end_date = date.fromisoformat(end) if end else today
    except ValueError:
        start_date = end_date = today
    if end_date < start_date:
        start_date, end_date = end_date, start_date
    return start_date, end_date


@role_required(GROUP_MANAGEMENT, AUDITOR)
def management_dashboard(request):
    start_date, end_date = _period(request)
    context = group_summary(start_date=start_date, end_date=end_date)
    return render(request, "reports/management_dashboard.html", context)


@role_required(GROUP_MANAGEMENT, AUDITOR)
def management_csv(request):
    start_date, end_date = _period(request)
    report = group_summary(start_date=start_date, end_date=end_date)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="sonoga-management-{start_date}-{end_date}.csv"'
    writer = csv.writer(response)
    writer.writerow(["Sonoga Group Management Report", f"{start_date} to {end_date}"])
    writer.writerow([])
    writer.writerow(["Business Unit", "Revenue", "Cash Received", "Receivables", "Expenses", "Payroll", "Operating Result"])
    for row in report["rows"]:
        writer.writerow([
            row["business_unit"].name, row["revenue"], row["cash_received"], row["receivables"],
            row["expenses"], row["payroll"], row["operating_result"],
        ])
    t = report["totals"]
    writer.writerow(["SONOGA GROUP TOTAL", t["revenue"], t["cash_received"], t["receivables"], t["expenses"], t["payroll"], t["operating_result"]])
    return response
