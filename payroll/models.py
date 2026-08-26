from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from core.models import TimeStampedModel
from organization.models import BusinessUnit
from hr.models import Employee


class PayrollRun(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        GENERATED = "GENERATED", "Generated"
        APPROVED = "APPROVED", "Approved"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    payroll_number = models.CharField(max_length=50, unique=True)
    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, related_name="payroll_runs")
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payroll_runs_created")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="payroll_runs_approved")
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-period_end", "business_unit__name"]
        constraints = [
            models.UniqueConstraint(fields=["business_unit", "period_start", "period_end"], name="uniq_payroll_period_per_unit")
        ]

    def clean(self):
        if self.period_end and self.period_start and self.period_end < self.period_start:
            raise ValidationError({"period_end": "Payroll period end cannot be before start."})

    @property
    def gross_total(self):
        return self.lines.aggregate(total=Sum("gross_pay"))["total"] or Decimal("0.00")

    @property
    def deductions_total(self):
        return self.lines.aggregate(total=Sum("deductions"))["total"] or Decimal("0.00")

    @property
    def net_total(self):
        return self.lines.aggregate(total=Sum("net_pay"))["total"] or Decimal("0.00")

    def __str__(self):
        return self.payroll_number


class PayrollLine(TimeStampedModel):
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name="lines")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="payroll_lines")
    basic_salary = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    allowances = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    overtime = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    bonuses = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gross_pay = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    payment_reference = models.CharField(max_length=100, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["payroll_run", "employee"], name="uniq_employee_per_payroll_run")]

    def clean(self):
        if self.payroll_run_id and self.employee_id and self.employee.business_unit_id != self.payroll_run.business_unit_id:
            raise ValidationError({"employee": "Employee must belong to the payroll business unit."})
        for field in ["basic_salary", "allowances", "overtime", "bonuses", "deductions"]:
            value = getattr(self, field)
            if value is not None and value < 0:
                raise ValidationError({field: "Amount cannot be negative."})

    def calculate(self):
        self.gross_pay = self.basic_salary + self.allowances + self.overtime + self.bonuses
        self.net_pay = max(self.gross_pay - self.deductions, Decimal("0.00"))

    def save(self, *args, **kwargs):
        self.calculate()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.payroll_run.payroll_number} - {self.employee.full_name}"
