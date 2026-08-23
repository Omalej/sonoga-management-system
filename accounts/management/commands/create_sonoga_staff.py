from datetime import date
from decimal import Decimal
from getpass import getpass
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from hr.models import Employee
from organization.models import BusinessUnit, Department, Position


class Command(BaseCommand):
    help = "Create a Sonoga staff user, employee record, and role assignment in one transaction."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument("--first-name", required=True)
        parser.add_argument("--last-name", required=True)
        parser.add_argument("--phone", required=True)
        parser.add_argument("--staff-number", required=True)
        parser.add_argument("--unit", required=True, choices=["HOTEL", "WATER", "BREAD"])
        parser.add_argument("--department", required=True, help="Department code, e.g. FO, PROD, ACC")
        parser.add_argument("--position", required=True, help="Exact position name")
        parser.add_argument("--role", required=True, help="Existing Sonoga role group name")
        parser.add_argument("--employment-date", default=date.today().isoformat())
        parser.add_argument("--basic-salary", default="0")
        parser.add_argument("--password", default=None, help="Temporary password. Omit to enter it securely.")

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        if User.objects.filter(username=options["username"]).exists():
            raise CommandError("Username already exists.")
        if Employee.objects.filter(staff_number=options["staff_number"]).exists():
            raise CommandError("Staff number already exists.")

        try:
            unit = BusinessUnit.objects.get(code=options["unit"], is_active=True)
            department = Department.objects.get(business_unit=unit, code=options["department"], is_active=True)
            position = Position.objects.get(business_unit=unit, department=department, name=options["position"], is_active=True)
            role = Group.objects.get(name=options["role"])
        except (BusinessUnit.DoesNotExist, Department.DoesNotExist, Position.DoesNotExist, Group.DoesNotExist) as exc:
            raise CommandError(str(exc)) from exc

        password = options["password"] or getpass("Temporary password: ")
        if len(password) < 10:
            raise CommandError("Temporary password must contain at least 10 characters.")

        user = User.objects.create_user(
            username=options["username"],
            email=options["email"],
            first_name=options["first_name"],
            last_name=options["last_name"],
            password=password,
            must_change_password=True,
            is_active=True,
        )
        user.groups.add(role)

        employee = Employee(
            staff_number=options["staff_number"],
            user=user,
            first_name=options["first_name"],
            last_name=options["last_name"],
            phone=options["phone"],
            email=options["email"],
            business_unit=unit,
            department=department,
            position=position,
            employment_date=options["employment_date"],
            basic_salary=Decimal(options["basic_salary"]),
            status=Employee.Status.ACTIVE,
        )
        employee.full_clean()
        employee.save()
        self.stdout.write(self.style.SUCCESS(
            f"Created {employee.full_name} ({employee.staff_number}) as {role.name}. Password change required on first login."
        ))
