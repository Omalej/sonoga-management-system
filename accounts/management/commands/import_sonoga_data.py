from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from factory.models import FactoryProduct, Recipe, RecipeLine
from hotel.models import Room, RoomType
from hr.models import Employee
from inventory.models import Item
from organization.models import BusinessUnit, Department, Position


TRUE_VALUES = {"1", "true", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "no", "n", "off"}


def text(row, key, default=""):
    value = row.get(key, default)
    return (value or default).strip()


def required(row, key, row_number):
    value = text(row, key)
    if not value:
        raise ValueError(f"row {row_number}: '{key}' is required")
    return value


def boolean(row, key, default=False):
    raw = text(row, key)
    if not raw:
        return default
    value = raw.lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    raise ValueError(f"'{key}' must be true/false, yes/no, or 1/0")


def decimal_value(row, key, default="0"):
    raw = text(row, key, default)
    try:
        return Decimal(raw or default)
    except InvalidOperation as exc:
        raise ValueError(f"'{key}' must be a valid number") from exc


def integer(row, key, default=0):
    raw = text(row, key, str(default))
    try:
        return int(raw or default)
    except ValueError as exc:
        raise ValueError(f"'{key}' must be an integer") from exc


def date_value(row, key, row_number):
    raw = required(row, key, row_number)
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"row {row_number}: '{key}' must use YYYY-MM-DD") from exc


class Command(BaseCommand):
    help = "Import or update Sonoga setup data from controlled CSV templates."

    ENTITY_CHOICES = [
        "room-types",
        "rooms",
        "employees",
        "inventory-items",
        "factory-products",
        "recipes",
        "recipe-lines",
    ]

    def add_arguments(self, parser):
        parser.add_argument("entity", choices=self.ENTITY_CHOICES)
        parser.add_argument("csv_file")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate the file and show results without committing database changes.",
        )

    def handle(self, *args, **options):
        path = Path(options["csv_file"]).expanduser().resolve()
        if not path.exists() or not path.is_file():
            raise CommandError(f"CSV file not found: {path}")

        handler = getattr(self, "import_" + options["entity"].replace("-", "_"))
        created = 0
        updated = 0
        errors = []

        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise CommandError("CSV file has no header row.")
            rows = list(reader)

        with transaction.atomic():
            for row_number, row in enumerate(rows, start=2):
                if not any((value or "").strip() for value in row.values()):
                    continue
                try:
                    was_created = handler(row, row_number)
                    created += int(was_created)
                    updated += int(not was_created)
                except Exception as exc:
                    errors.append(f"row {row_number}: {exc}")

            if errors:
                transaction.set_rollback(True)
            elif options["dry_run"]:
                transaction.set_rollback(True)

        if errors:
            preview = "\n".join(f"- {message}" for message in errors[:30])
            extra = "" if len(errors) <= 30 else f"\n... and {len(errors) - 30} more error(s)."
            raise CommandError(f"Import aborted; no changes committed.\n{preview}{extra}")

        mode = "DRY RUN" if options["dry_run"] else "COMMITTED"
        self.stdout.write(self.style.SUCCESS(
            f"{mode}: {options['entity']} processed successfully; created={created}, updated={updated}."
        ))

    def unit(self, row, row_number):
        code = required(row, "business_unit_code", row_number).upper()
        try:
            return BusinessUnit.objects.get(code=code)
        except BusinessUnit.DoesNotExist as exc:
            raise ValueError(f"business unit '{code}' does not exist; run bootstrap_sonoga first") from exc

    def import_room_types(self, row, row_number):
        unit = self.unit(row, row_number)
        code = required(row, "code", row_number).upper()
        defaults = {
            "name": required(row, "name", row_number),
            "description": text(row, "description"),
            "standard_capacity": integer(row, "standard_capacity", 1),
            "maximum_capacity": integer(row, "maximum_capacity", 2),
            "base_rate": decimal_value(row, "base_rate"),
            "extra_person_charge": decimal_value(row, "extra_person_charge"),
            "amenities": text(row, "amenities"),
            "is_active": boolean(row, "is_active", True),
        }
        obj, created = RoomType.objects.update_or_create(business_unit=unit, code=code, defaults=defaults)
        obj.full_clean()
        obj.save()
        return created

    def import_rooms(self, row, row_number):
        unit = self.unit(row, row_number)
        room_type_code = required(row, "room_type_code", row_number).upper()
        try:
            room_type = RoomType.objects.get(business_unit=unit, code=room_type_code)
        except RoomType.DoesNotExist as exc:
            raise ValueError(f"room type '{room_type_code}' does not exist in {unit.code}") from exc
        number = required(row, "number", row_number)
        defaults = {
            "room_type": room_type,
            "floor": text(row, "floor"),
            "occupancy_status": text(row, "occupancy_status", Room.Occupancy.VACANT).upper(),
            "housekeeping_status": text(row, "housekeeping_status", Room.Housekeeping.CLEAN).upper(),
            "maintenance_status": text(row, "maintenance_status", Room.Maintenance.CLEAR).upper(),
            "is_blocked": boolean(row, "is_blocked", False),
            "notes": text(row, "notes"),
        }
        obj, created = Room.objects.update_or_create(business_unit=unit, number=number, defaults=defaults)
        obj.full_clean()
        obj.save()
        return created

    def import_employees(self, row, row_number):
        unit = self.unit(row, row_number)
        department_code = required(row, "department_code", row_number).upper()
        try:
            department = Department.objects.get(business_unit=unit, code=department_code)
        except Department.DoesNotExist as exc:
            raise ValueError(f"department '{department_code}' does not exist in {unit.code}") from exc
        position_name = required(row, "position_name", row_number)
        try:
            position = Position.objects.get(department=department, name=position_name)
        except Position.DoesNotExist as exc:
            raise ValueError(f"position '{position_name}' does not exist in {unit.code}/{department_code}") from exc

        staff_number = required(row, "staff_number", row_number)
        defaults = {
            "first_name": required(row, "first_name", row_number),
            "middle_name": text(row, "middle_name"),
            "last_name": required(row, "last_name", row_number),
            "phone": required(row, "phone", row_number),
            "email": text(row, "email"),
            "address": text(row, "address"),
            "business_unit": unit,
            "department": department,
            "position": position,
            "employment_type": text(row, "employment_type", Employee.EmploymentType.PERMANENT).upper(),
            "employment_date": date_value(row, "employment_date", row_number),
            "status": text(row, "status", Employee.Status.ACTIVE).upper(),
            "basic_salary": decimal_value(row, "basic_salary"),
            "bank_name": text(row, "bank_name"),
            "account_name": text(row, "account_name"),
            "account_number": text(row, "account_number"),
        }
        obj, created = Employee.objects.update_or_create(staff_number=staff_number, defaults=defaults)
        obj.full_clean()
        obj.save()
        return created

    def import_inventory_items(self, row, row_number):
        unit = self.unit(row, row_number)
        code = required(row, "code", row_number).upper()
        defaults = {
            "name": required(row, "name", row_number),
            "category": required(row, "category", row_number).upper(),
            "unit": required(row, "unit", row_number).upper(),
            "standard_cost": decimal_value(row, "standard_cost"),
            "minimum_stock": decimal_value(row, "minimum_stock"),
            "reorder_level": decimal_value(row, "reorder_level"),
            "is_active": boolean(row, "is_active", True),
        }
        obj, created = Item.objects.update_or_create(business_unit=unit, code=code, defaults=defaults)
        obj.full_clean()
        obj.save()
        return created

    def import_factory_products(self, row, row_number):
        unit = self.unit(row, row_number)
        if unit.unit_type not in {BusinessUnit.UnitType.WATER, BusinessUnit.UnitType.BREAD}:
            raise ValueError("factory products can only belong to WATER or BREAD")
        item_code = required(row, "inventory_item_code", row_number).upper()
        try:
            item = Item.objects.get(business_unit=unit, code=item_code)
        except Item.DoesNotExist as exc:
            raise ValueError(f"inventory item '{item_code}' does not exist in {unit.code}") from exc
        code = required(row, "code", row_number).upper()
        shelf_life_raw = text(row, "shelf_life_days")
        defaults = {
            "name": required(row, "name", row_number),
            "product_family": FactoryProduct.ProductFamily.WATER if unit.unit_type == BusinessUnit.UnitType.WATER else FactoryProduct.ProductFamily.BREAD,
            "inventory_item": item,
            "selling_price": decimal_value(row, "selling_price"),
            "wholesale_price": decimal_value(row, "wholesale_price"),
            "standard_cost": decimal_value(row, "standard_cost"),
            "shelf_life_days": int(shelf_life_raw) if shelf_life_raw else None,
            "minimum_stock": decimal_value(row, "minimum_stock"),
            "is_active": boolean(row, "is_active", True),
        }
        obj, created = FactoryProduct.objects.update_or_create(business_unit=unit, code=code, defaults=defaults)
        obj.full_clean()
        obj.save()
        return created

    def import_recipes(self, row, row_number):
        unit = self.unit(row, row_number)
        if unit.unit_type != BusinessUnit.UnitType.BREAD:
            raise ValueError("recipes can only be imported for the BREAD business unit")
        product_code = required(row, "product_code", row_number).upper()
        try:
            product = FactoryProduct.objects.get(business_unit=unit, code=product_code)
        except FactoryProduct.DoesNotExist as exc:
            raise ValueError(f"bread product '{product_code}' does not exist") from exc
        name = required(row, "name", row_number)
        defaults = {
            "output_quantity": decimal_value(row, "output_quantity", "1"),
            "is_default": boolean(row, "is_default", False),
            "notes": text(row, "notes"),
            "is_active": boolean(row, "is_active", True),
        }
        obj, created = Recipe.objects.update_or_create(product=product, name=name, defaults=defaults)
        obj.full_clean()
        obj.save()
        return created

    def import_recipe_lines(self, row, row_number):
        unit = self.unit(row, row_number)
        product_code = required(row, "product_code", row_number).upper()
        recipe_name = required(row, "recipe_name", row_number)
        item_code = required(row, "item_code", row_number).upper()
        try:
            product = FactoryProduct.objects.get(business_unit=unit, code=product_code)
            recipe = Recipe.objects.get(product=product, name=recipe_name)
            item = Item.objects.get(business_unit=unit, code=item_code)
        except (FactoryProduct.DoesNotExist, Recipe.DoesNotExist, Item.DoesNotExist) as exc:
            raise ValueError("product, recipe, or inventory item reference does not exist") from exc
        defaults = {
            "quantity": decimal_value(row, "quantity"),
            "notes": text(row, "notes"),
        }
        obj, created = RecipeLine.objects.update_or_create(recipe=recipe, item=item, defaults=defaults)
        obj.full_clean()
        obj.save()
        return created
