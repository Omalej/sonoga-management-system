from django.core.management.base import BaseCommand
from organization.models import BusinessUnit, Department, Position
from inventory.models import Store
from finance.models import ExpenseCategory

DEPARTMENTS = {
    "HOTEL": [
        ("ADM", "Administration"), ("FO", "Front Office"), ("HK", "Housekeeping"),
        ("REST", "Restaurant"), ("KIT", "Kitchen"), ("MNT", "Maintenance"),
        ("SEC", "Security"), ("ACC", "Accounts"),
    ],
    "WATER": [
        ("ADM", "Administration"), ("PROD", "Production"), ("PACK", "Packaging"),
        ("QC", "Quality Control"), ("WH", "Warehouse"), ("SALES", "Sales"),
        ("DIST", "Distribution"), ("MNT", "Maintenance"), ("ACC", "Accounts"),
    ],
    "BREAD": [
        ("ADM", "Administration"), ("PROD", "Production"), ("PACK", "Packaging"),
        ("QC", "Quality Control"), ("WH", "Warehouse"), ("SALES", "Sales"),
        ("DIST", "Distribution"), ("MNT", "Maintenance"), ("ACC", "Accounts"),
    ],
}

POSITIONS = {
    "HOTEL": {
        "ADM": ["General Manager"],
        "FO": ["Front Office Manager", "Receptionist"],
        "HK": ["Housekeeping Supervisor", "Room Attendant"],
        "REST": ["Restaurant Manager", "Cashier", "Waiter"],
        "KIT": ["Chef", "Kitchen Assistant"],
        "MNT": ["Maintenance Officer"],
        "SEC": ["Security Officer"],
        "ACC": ["Accountant"],
    },
    "WATER": {
        "ADM": ["Factory Manager"],
        "PROD": ["Production Manager", "Production Supervisor", "Machine Operator"],
        "PACK": ["Packaging Operator"],
        "QC": ["Quality Control Officer"],
        "WH": ["Storekeeper"],
        "SALES": ["Sales Officer"],
        "DIST": ["Driver", "Distribution Officer"],
        "MNT": ["Maintenance Officer"],
        "ACC": ["Accountant"],
    },
    "BREAD": {
        "ADM": ["Factory Manager"],
        "PROD": ["Production Manager", "Production Supervisor", "Baker", "Production Assistant"],
        "PACK": ["Packaging Operator"],
        "QC": ["Quality Control Officer"],
        "WH": ["Storekeeper"],
        "SALES": ["Sales Officer"],
        "DIST": ["Driver", "Distribution Officer"],
        "MNT": ["Maintenance Officer"],
        "ACC": ["Accountant"],
    },
}

STORES = {
    "HOTEL": [
        ("MAIN", "Hotel Main Store", Store.StoreType.GENERAL),
        ("KITCHEN", "Kitchen Store", Store.StoreType.KITCHEN),
        ("BAR", "Bar Store", Store.StoreType.BAR),
        ("HOUSEKEEPING", "Housekeeping Store", Store.StoreType.HOUSEKEEPING),
        ("MAINTENANCE", "Maintenance Store", Store.StoreType.MAINTENANCE),
    ],
    "WATER": [
        ("RAW", "Water Raw Material Store", Store.StoreType.RAW_MATERIAL),
        ("FG", "Water Finished Goods Store", Store.StoreType.FINISHED_GOODS),
    ],
    "BREAD": [
        ("RAW", "Bread Raw Material Store", Store.StoreType.RAW_MATERIAL),
        ("FG", "Bread Finished Goods Store", Store.StoreType.FINISHED_GOODS),
    ],
}

EXPENSE_CATEGORIES = [
    "Diesel & Fuel", "Electricity", "Food & Kitchen",
    "Repairs & Maintenance", "Cleaning", "Transportation", "Marketing",
    "Raw Materials", "Packaging", "Utilities", "Security", "Taxes & Levies",
    "Office & Administration", "Other",
]


class Command(BaseCommand):
    help = "Seed safe Sonoga defaults: departments, positions, stores, and expense categories."

    def handle(self, *args, **options):
        for unit_code, departments in DEPARTMENTS.items():
            unit = BusinessUnit.objects.get(code=unit_code)
            dep_lookup = {}
            for code, name in departments:
                dep, _ = Department.objects.get_or_create(
                    business_unit=unit,
                    code=code,
                    defaults={"name": name, "is_active": True},
                )
                dep_lookup[code] = dep
            for dep_code, names in POSITIONS[unit_code].items():
                department = dep_lookup[dep_code]
                for name in names:
                    Position.objects.get_or_create(
                        business_unit=unit,
                        department=department,
                        name=name,
                        defaults={"is_active": True},
                    )
            for code, name, store_type in STORES[unit_code]:
                Store.objects.get_or_create(
                    business_unit=unit,
                    code=code,
                    defaults={"name": name, "store_type": store_type, "is_active": True},
                )

        for name in EXPENSE_CATEGORIES:
            ExpenseCategory.objects.get_or_create(name=name, defaults={"is_active": True})

        self.stdout.write(self.style.SUCCESS("Sonoga default organizational data seeded."))
