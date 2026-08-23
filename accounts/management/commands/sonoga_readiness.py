from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection
from factory.models import FactoryProduct, Recipe
from hotel.models import Room, RoomType
from hr.models import Employee
from inventory.models import Item, Store
from organization.models import BusinessUnit, Department


class Command(BaseCommand):
    help = "Check whether the Sonoga HMS has the minimum infrastructure and optional operating data required for use."

    def add_arguments(self, parser):
        parser.add_argument(
            "--operational",
            action="store_true",
            help="Also require initial hotel/factory operating data, not only infrastructure configuration.",
        )

    def handle(self, *args, **options):
        problems = []
        warnings = []

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        self.stdout.write(self.style.SUCCESS("Database connection: OK"))

        expected_units = {"HOTEL", "WATER", "BREAD"}
        actual_units = set(BusinessUnit.objects.filter(is_active=True).values_list("code", flat=True))
        missing_units = expected_units - actual_units
        if missing_units:
            problems.append(f"Missing business units: {', '.join(sorted(missing_units))}")

        for code in sorted(expected_units & actual_units):
            unit = BusinessUnit.objects.get(code=code)
            if not Department.objects.filter(business_unit=unit, is_active=True).exists():
                problems.append(f"{code}: no active departments configured")
            if not Store.objects.filter(business_unit=unit, is_active=True).exists():
                problems.append(f"{code}: no active stores configured")

        integration_username = getattr(settings, "SONOGA_WORDPRESS_USER", "wordpress-sync")
        integration_user_exists = get_user_model().objects.filter(
            username=integration_username, is_active=True
        ).exists()
        if not integration_user_exists:
            problems.append(f"WordPress integration user '{integration_username}' is missing or inactive")

        if not settings.DEBUG:
            if len(settings.SECRET_KEY) < 40:
                problems.append("Production DJANGO_SECRET_KEY is too short")
            if not settings.ALLOWED_HOSTS:
                problems.append("Production ALLOWED_HOSTS is empty")
            if not settings.SONOGA_WORDPRESS_API_KEY:
                problems.append("SONOGA_WORDPRESS_API_KEY is not configured")
            if not getattr(settings, "SONOGA_WORDPRESS_REQUIRE_SIGNATURE", False):
                warnings.append("WordPress webhook signatures are disabled in production")
            if not settings.SESSION_COOKIE_SECURE:
                problems.append("SESSION_COOKIE_SECURE is disabled in production")
            if not settings.CSRF_COOKIE_SECURE:
                problems.append("CSRF_COOKIE_SECURE is disabled in production")

        if options["operational"]:
            hotel = BusinessUnit.objects.filter(code="HOTEL", is_active=True).first()
            water = BusinessUnit.objects.filter(code="WATER", is_active=True).first()
            bread = BusinessUnit.objects.filter(code="BREAD", is_active=True).first()

            if hotel:
                if not RoomType.objects.filter(business_unit=hotel, is_active=True).exists():
                    problems.append("HOTEL: no active room types configured")
                if not Room.objects.filter(business_unit=hotel).exists():
                    problems.append("HOTEL: no rooms configured")

            if water:
                if not FactoryProduct.objects.filter(business_unit=water, is_active=True).exists():
                    problems.append("WATER: no active products configured")
                if not Item.objects.filter(business_unit=water, is_active=True).exists():
                    problems.append("WATER: no inventory items configured")

            if bread:
                bread_products = FactoryProduct.objects.filter(business_unit=bread, is_active=True)
                if not bread_products.exists():
                    problems.append("BREAD: no active products configured")
                elif not Recipe.objects.filter(product__in=bread_products, is_active=True).exists():
                    problems.append("BREAD: no active production recipe configured")
                if not Item.objects.filter(business_unit=bread, is_active=True).exists():
                    problems.append("BREAD: no inventory items configured")

            if not Employee.objects.filter(status=Employee.Status.ACTIVE).exists():
                warnings.append("No active employee records have been configured yet")

        for warning in warnings:
            self.stdout.write(self.style.WARNING(f"- WARNING: {warning}"))

        if problems:
            for problem in problems:
                self.stdout.write(self.style.ERROR(f"- {problem}"))
            raise SystemExit(1)

        mode = "operational" if options["operational"] else "infrastructure"
        self.stdout.write(self.style.SUCCESS(f"Sonoga HMS {mode} readiness checks passed."))
