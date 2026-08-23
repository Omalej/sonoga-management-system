from django import forms
from .models import Employee

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'first_name', 'middle_name', 'last_name',
            'phone', 'email', 'address', 'state_of_origin', 'lga', 'passport',
            'business_unit', 'department', 'position', 'supervisor',
            'employment_type', 'employment_date', 'status',
            'basic_salary', 'bank_name', 'account_name', 'account_number'
        ]
        widgets = {
            'employment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
