from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel
from organization.models import BusinessUnit, Department, Position


class Employee(TimeStampedModel):
    class EmploymentType(models.TextChoices):
        PERMANENT = "PERMANENT", "Permanent"
        CONTRACT = "CONTRACT", "Contract"
        CASUAL = "CASUAL", "Casual"
        TEMPORARY = "TEMPORARY", "Temporary"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        ON_LEAVE = "ON_LEAVE", "On Leave"
        SUSPENDED = "SUSPENDED", "Suspended"
        RESIGNED = "RESIGNED", "Resigned"
        TERMINATED = "TERMINATED", "Terminated"
        RETIRED = "RETIRED", "Retired"

    staff_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee",
    )

    first_name = models.CharField(max_length=80)
    middle_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80)

    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    business_unit = models.ForeignKey(
        BusinessUnit,
        on_delete=models.PROTECT,
        related_name="employees",
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="employees",
    )

    position = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        related_name="employees",
    )

    supervisor = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subordinates",
    )

    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentType.choices,
        default=EmploymentType.PERMANENT,
    )

    employment_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    basic_salary = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    bank_name = models.CharField(max_length=120, blank=True)
    account_name = models.CharField(max_length=150, blank=True)
    account_number = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def save(self, *args, **kwargs):
        if not self.staff_number:
            year = timezone.now().year

            last_employee = (
                Employee.objects
                .filter(staff_number__startswith=f"SG-{year}-")
                .order_by("-id")
                .first()
            )

            if last_employee:
                last_number = int(
                    last_employee.staff_number.split("-")[-1]
                )
                next_number = last_number + 1
            else:
                next_number = 1

            self.staff_number = f"SG-{year}-{next_number:05d}"

        super().save(*args, **kwargs)

    def clean(self):
        errors = {}

        if (
            self.department_id
            and self.business_unit_id
            and self.department.business_unit_id != self.business_unit_id
        ):
            errors["department"] = (
                "Department must belong to the selected business unit."
            )

        if (
            self.position_id
            and self.department_id
            and self.position.department_id != self.department_id
        ):
            errors["position"] = (
                "Position must belong to the selected department."
            )

        if errors:
            raise ValidationError(errors)

    @property
    def full_name(self):
        return " ".join(
            p for p in [
                self.first_name,
                self.middle_name,
                self.last_name
            ]
            if p
        )

    def __str__(self):
        return f"{self.staff_number} - {self.full_name}"