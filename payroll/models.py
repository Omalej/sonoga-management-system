from django.db import models
from hr.models import Employee
from core.models import TimeStampedModel

class PayrollRun(TimeStampedModel):
    month = models.IntegerField(default=8, help_text="Month (1-12)")
    year = models.IntegerField(default=2026, help_text="Year (e.g. 2026)")
    is_finalized = models.BooleanField(default=False)

    def __str__(self):
        return f"Payroll - {self.month:02d}/{self.year}"

class Payslip(TimeStampedModel):
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name='payslips')
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='payslips')
    
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    pension_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def calculate_net(self):
        self.pension_deduction = round(float(self.basic_salary) * 0.08, 2)
        total_deductions = float(self.pension_deduction) + float(self.tax_deduction) + float(self.other_deductions)
        gross = float(self.basic_salary) + float(self.allowances)
        self.net_salary = round(gross - total_deductions, 2)
        return self.net_salary

    def save(self, *args, **kwargs):
        self.calculate_net()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payslip: {self.employee} - {self.payroll_run}"
