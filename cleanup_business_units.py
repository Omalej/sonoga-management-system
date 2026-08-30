from django.db import transaction
from organization.models import BusinessUnit
from hr.models import Department, Position
from inventory.models import Store

mapping = {
    5: 1,  # Sonoga Hotels & Suites -> Sonoga Hotels and Suites
    6: 2,  # Sonoga Pure Water Factory -> Mabinas Water
    7: 3,  # Sonoga Bread Factory -> Mabinas Bread
}

print("\nCURRENT BUSINESS UNITS")
for x in BusinessUnit.objects.all().order_by("id"):
    print(x.id, "|", x.code, "|", x.name, "|", x.unit_type)

with transaction.atomic():

    for old_id, new_id in mapping.items():

        old = BusinessUnit.objects.get(id=old_id)
        new = BusinessUnit.objects.get(id=new_id)

        print(f"\nMOVING {old.id} | {old.name}")
        print(f"      INTO {new.id} | {new.name}")

        departments = Department.objects.filter(
            business_unit_id=old_id
        )
        print("Departments:", departments.count())
        departments.update(business_unit_id=new_id)

        positions = Position.objects.filter(
            business_unit_id=old_id
        )
        print("Positions:", positions.count())
        positions.update(business_unit_id=new_id)

        stores = Store.objects.filter(
            business_unit_id=old_id
        )
        print("Stores:", stores.count())
        stores.update(business_unit_id=new_id)

    print("\nDELETING DUPLICATE BUSINESS UNITS...")

    BusinessUnit.objects.filter(
        id__in=list(mapping.keys())
    ).delete()

print("\nCLEANUP COMPLETE")
