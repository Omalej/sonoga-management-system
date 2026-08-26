from django import forms

from .models import Employee


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee

        fields = [
            "user",
            "first_name",
            "middle_name",
            "last_name",
            "phone",
            "email",
            "address",
            "business_unit",
            "department",
            "position",
            "supervisor",
            "employment_type",
            "employment_date",
            "status",
            "basic_salary",
            "bank_name",
            "account_name",
            "account_number",
        ]

        widgets = {
            "employment_date": forms.DateInput(
                attrs={"type": "date"}
            ),
        }

    def clean(self):
        cleaned = super().clean()

        unit = cleaned.get("business_unit")
        department = cleaned.get("department")
        position = cleaned.get("position")

        if unit and department and department.business_unit_id != unit.id:
            self.add_error(
                "department",
                "Department must belong to the selected business unit."
            )

        if department and position and position.department_id != department.id:
            self.add_error(
                "position",
                "Position must belong to the selected department."
            )

        return cleaned