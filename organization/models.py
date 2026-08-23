from django.conf import settings
from django.db import models
from core.models import TimeStampedModel

class BusinessUnit(TimeStampedModel):
    class UnitType(models.TextChoices):
        HEAD_OFFICE = "HEAD_OFFICE", "Head Office"
        HOTEL = "HOTEL", "Sonoga Hotels"
        WATER = "WATER", "Pure Water Factory"
        BREAD = "BREAD", "Bread Factory"
        ENERGY = "ENERGY", "Crown Field Energy"
        OTHER = "OTHER", "Other"

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150, unique=True)
    unit_type = models.CharField(max_length=20, choices=UnitType.choices)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_business_units",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class Department(TimeStampedModel):
    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, related_name="departments")
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sub_departments",
    )
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    head = models.ForeignKey(
        "hr.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_departments",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["business_unit__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["business_unit", "code"], name="uniq_department_code_per_unit"),
            models.UniqueConstraint(fields=["business_unit", "name"], name="uniq_department_name_per_unit"),
        ]

    def __str__(self):
        parent_str = f" ({self.parent.name})" if self.parent else ""
        return f"{self.business_unit.code} - {self.name}{parent_str}"

class Position(TimeStampedModel):
    business_unit = models.ForeignKey(BusinessUnit, on_delete=models.PROTECT, related_name="positions", null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="positions")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    reports_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subordinate_positions",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["department__name", "name"]

    def __str__(self):
        return f"{self.name} ({self.department.name})"
