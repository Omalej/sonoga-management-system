from django.contrib import messages
from django.db.models import Count
from django.shortcuts import redirect, render
from accounts.access import GROUP_MANAGEMENT, HR_MANAGER, role_required
from organization.models import BusinessUnit
from .forms import EmployeeForm
from .models import Employee


@role_required(HR_MANAGER, GROUP_MANAGEMENT)
def hr_dashboard(request):
    units = BusinessUnit.objects.filter(is_active=True).annotate(employee_count=Count("employees"))
    return render(request, "hr/dashboard.html", {
        "units": units,
        "active_count": Employee.objects.filter(status=Employee.Status.ACTIVE).count(),
        "on_leave_count": Employee.objects.filter(status=Employee.Status.ON_LEAVE).count(),
        "recent": Employee.objects.select_related("business_unit", "department", "position").order_by("-created_at")[:15],
    })


@role_required(HR_MANAGER, GROUP_MANAGEMENT)
def employee_list(request):
    employees = Employee.objects.select_related("business_unit", "department", "position", "user").order_by("business_unit__name", "last_name", "first_name")
    return render(request, "hr/employee_list.html", {"employees": employees})


@role_required(HR_MANAGER, GROUP_MANAGEMENT)
def employee_create(request):
    form = EmployeeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        employee = form.save()
        messages.success(request, f"Employee {employee.full_name} created.")
        return redirect("hr:employees")
    return render(request, "layouts/form_page.html", {"form": form, "title": "Add Employee", "cancel_url": "/hr/employees/"})
