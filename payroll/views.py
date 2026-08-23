from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .models import PayrollRun, Payslip
from hr.models import Employee
from accounts.access import role_required

@role_required('HR Manager', 'Finance Manager', 'Group Management')
def payroll_dashboard(request):
    current_month = timezone.now().month
    current_year = timezone.now().year
    runs = PayrollRun.objects.all().order_by('-year', '-month')
    return render(request, 'payroll/dashboard.html', {'runs': runs, 'current_month': current_month, 'current_year': current_year})

@role_required('HR Manager', 'Finance Manager', 'Group Management')
def generate_payroll(request):
    if request.method == 'POST':
        month = int(request.POST.get('month', timezone.now().month))
        year = int(request.POST.get('year', timezone.now().year))
        
        run, created = PayrollRun.objects.get_or_create(month=month, year=year)
        if run.is_finalized:
            messages.error(request, f"Payroll for {month}/{year} is already finalized.")
            return redirect('payroll:dashboard')
        
        active_employees = Employee.objects.filter(status='Active')
        count = 0
        for emp in active_employees:
            payslip, p_created = Payslip.objects.get_or_create(
                payroll_run=run,
                employee=emp,
                defaults={'basic_salary': emp.basic_salary}
            )
            if p_created:
                count += 1
        
        messages.success(request, f"Successfully generated {count} new payslips for {month}/{year}.")
        return redirect('payroll:dashboard')
    return redirect('payroll:dashboard')
