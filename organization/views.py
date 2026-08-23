from django.shortcuts import render
from .models import BusinessUnit, Department

def company_department_list(request):
    companies = BusinessUnit.objects.prefetch_related('departments').all()
    context = {
        'companies': companies,
    }
    return render(request, 'organization/company_list.html', context)
