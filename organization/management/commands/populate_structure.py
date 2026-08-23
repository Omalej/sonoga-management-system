from django.core.management.base import BaseCommand
from organization.models import BusinessUnit, Department

class Command(BaseCommand):
    help = "Populates Crown Field Group companies and departments"

    def handle(self, *args, **options):
        self.stdout.write("Populating Crown Field Group organizational structure...")

        # Define companies
        companies_data = [
            ("HO", "Crown Field Group / Head Office", BusinessUnit.UnitType.HEAD_OFFICE),
            ("HOTEL", "Sonoga Hotels", BusinessUnit.UnitType.HOTEL),
            ("WATER", "Pure Water Factory", BusinessUnit.UnitType.WATER),
            ("BREAD", "Bread Factory", BusinessUnit.UnitType.BREAD),
            ("ENERGY", "Crown Field Energy", BusinessUnit.UnitType.ENERGY),
        ]

        units = {}
        for code, name, unit_type in companies_data:
            unit, created = BusinessUnit.objects.get_or_create(
                code=code,
                defaults={"name": name, "unit_type": unit_type, "is_active": True}
            )
            if not created:
                unit.name = name
                unit.unit_type = unit_type
                unit.save()
            units[code] = unit
            self.stdout.write(f"Company: {name} ({code})")

        # Define departments per company
        departments_structure = {
            "HO": [
                ("ADMIN", "Administration"),
                ("HR", "Human Resources (HR)"),
                ("FIN", "Finance & Accounting"),
                ("PROC", "Procurement"),
                ("AUDIT", "Internal Audit"),
                ("LEGAL", "Legal & Compliance"),
                ("IT", "Information Technology (IT)"),
                ("SALES", "Sales & Marketing"),
                ("CS", "Customer Service"),
                ("SEC", "Security"),
                ("FLEET", "Fleet & Transport"),
                ("HSE", "Health, Safety & Environment (HSE)"),
                ("STORES", "Stores & Inventory"),
                ("BD", "Business Development"),
                ("CORP", "Corporate Communications"),
            ],
            "HOTEL": [
                ("GM", "General Management"),
                ("FO", "Front Office / Reception"),
                ("RES", "Reservations"),
                ("HK", "Housekeeping"),
                ("REST", "Restaurant"),
                ("KIT", "Kitchen"),
                ("FNB", "Food & Beverage"),
                ("BAR", "Bar"),
                ("LAUNDRY", "Laundry"),
                ("MAINT", "Maintenance"),
                ("SEC", "Security"),
                ("SALES", "Sales & Marketing"),
                ("EVENTS", "Events & Banqueting"),
                ("PROC", "Procurement"),
                ("STORES", "Stores"),
                ("FIN", "Accounts / Finance"),
                ("HR", "Human Resources"),
                ("IT", "IT / ICT"),
            ],
            "WATER": [
                ("GM", "General Management"),
                ("WATER_TREAT", "Water Treatment"),
                ("PROD", "Production"),
                ("PACK", "Packaging"),
                ("QC", "Quality Control / Quality Assurance"),
                ("MAINT", "Maintenance"),
                ("ELEC_MECH", "Electrical / Mechanical"),
                ("RAW_STORES", "Raw Materials & Stores"),
                ("WH", "Warehouse"),
                ("SALES", "Sales"),
                ("MKT", "Marketing"),
                ("DIST", "Distribution"),
                ("LOG", "Logistics"),
                ("FLEET", "Fleet & Transport"),
                ("PROC", "Procurement"),
                ("FIN", "Accounts / Finance"),
                ("HR", "Human Resources"),
                ("SEC", "Security"),
                ("HSE", "Health, Safety & Environment"),
            ],
            "BREAD": [
                ("GM", "General Management"),
                ("PROD_BAKERY", "Production / Bakery"),
                ("DOUGH", "Dough Preparation"),
                ("BAKING", "Baking"),
                ("PACK", "Packaging"),
                ("QC", "Quality Control / Quality Assurance"),
                ("MAINT", "Maintenance"),
                ("ELEC_MECH", "Electrical / Mechanical"),
                ("RAW_STORES", "Raw Materials & Stores"),
                ("WH", "Warehouse"),
                ("SALES", "Sales"),
                ("MKT", "Marketing"),
                ("DIST", "Distribution"),
                ("LOG", "Logistics"),
                ("FLEET", "Fleet & Transport"),
                ("PROC", "Procurement"),
                ("FIN", "Accounts / Finance"),
                ("HR", "Human Resources"),
                ("SEC", "Security"),
                ("HSE", "Health, Safety & Environment"),
            ],
            "ENERGY": [
                ("GM", "General Management"),
                ("ENG", "Engineering"),
                ("PM", "Project Management"),
                ("INSTALL", "Installation"),
                ("OPS", "Operations"),
                ("MAINT_TECH", "Maintenance & Technical Support"),
                ("SOLAR", "Solar / Renewable Energy"),
                ("ELEC_SERV", "Electrical Services"),
                ("ENERGY_SOL", "Energy Solutions"),
                ("SALES", "Sales"),
                ("MKT", "Marketing"),
                ("BD", "Business Development"),
                ("PROC", "Procurement"),
                ("STORES", "Stores & Inventory"),
                ("LOG", "Logistics"),
                ("FLEET", "Fleet & Transport"),
                ("CUST_SUPP", "Customer Support"),
                ("FIN", "Finance & Accounting"),
                ("HR", "Human Resources"),
                ("HSE", "Health, Safety & Environment"),
                ("SEC", "Security"),
                ("QC", "Quality Assurance / Quality Control"),
            ]
        }

        for comp_code, dept_list in departments_structure.items():
            unit = units[comp_code]
            for dept_code, dept_name in dept_list:
                Department.objects.get_or_create(
                    business_unit=unit,
                    code=dept_code,
                    defaults={"name": dept_name, "is_active": True}
                )
            self.stdout.write(f"  -> Populated {len(dept_list)} departments for {unit.name}")

        self.stdout.write(self.style.SUCCESS("Crown Field Group organizational structure populated successfully!"))
