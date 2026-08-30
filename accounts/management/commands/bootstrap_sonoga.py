from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from organization.models import BusinessUnit

from accounts.access import (
    CEO,
    GENERAL_MANAGER,
    GROUP_MANAGEMENT,
    HOTEL_MANAGER,
    RECEPTIONIST,
    HOUSEKEEPING,
    WATER_MANAGER,
    BREAD_MANAGER,
    PRODUCTION_SUPERVISOR,
    STOREKEEPER,
    SALES_OFFICER,
    HR_MANAGER,
    ACCOUNTANT,
    AUDITOR,
)


ALL_SONOGA_APPS = {
    "organization",
    "hr",
    "hotel",
    "inventory",
    "factory",
    "commercial",
    "procurement",
    "finance",
    "payroll",
    "control",
}


# Rules are intentionally app-scoped. This prevents operational managers from
# receiving global permissions simply because a codename starts with view_.
ROLE_RULES = {

    # ============================================================
    # CEO
    # ============================================================

    CEO: {
        "apps": {
            app: {"view", "add", "change", "delete"}
            for app in ALL_SONOGA_APPS
        },
        "exact": set(),
    },

    # ============================================================
    # GENERAL MANAGER
    # ============================================================

    GENERAL_MANAGER: {
        "apps": {
            app: {"view", "add", "change"}
            for app in ALL_SONOGA_APPS
        },
        "exact": set(),
    },

    # ============================================================
    # GROUP MANAGEMENT
    # ============================================================

    GROUP_MANAGEMENT: {
        "apps": {
            app: {"view"}
            for app in ALL_SONOGA_APPS
        },
        "exact": set(),
    },

    # ============================================================
    # AUDITOR
    # ============================================================

    AUDITOR: {
        "apps": {
            app: {"view"}
            for app in ALL_SONOGA_APPS
        },
        "exact": set(),
    },

    # ============================================================
    # HOTEL MANAGER
    # ============================================================

    HOTEL_MANAGER: {
        "apps": {
            "hotel": {"view", "add", "change"},
            "inventory": {"view"},
            "organization": {"view"},
            "hr": {"view"},
        },
        "exact": set(),
    },

    # ============================================================
    # RECEPTIONIST
    # ============================================================

    RECEPTIONIST: {
        "apps": {},
        "exact": {
            "hotel.view_guest",
            "hotel.add_guest",
            "hotel.change_guest",

            "hotel.view_reservation",
            "hotel.add_reservation",
            "hotel.change_reservation",

            "hotel.view_room",
            "hotel.view_roomtype",

            "hotel.view_stay",
            "hotel.add_stay",
            "hotel.change_stay",

            "hotel.view_folio",
            "hotel.view_foliocharge",
            "hotel.add_foliocharge",

            "hotel.view_payment",
            "hotel.add_payment",
        },
    },

    # ============================================================
    # HOUSEKEEPING
    # ============================================================

    HOUSEKEEPING: {
        "apps": {},
        "exact": {
            "hotel.view_room",
            "hotel.view_housekeepingtask",
            "hotel.change_housekeepingtask",
        },
    },

    # ============================================================
    # WATER FACTORY MANAGER
    # ============================================================

    WATER_MANAGER: {
        "apps": {
            "factory": {"view", "add", "change"},
            "commercial": {"view", "add", "change"},
            "inventory": {"view", "add", "change"},
            "procurement": {"view", "add", "change"},
            "organization": {"view"},
            "hr": {"view"},
            "finance": {"view"},
        },
        "exact": set(),
    },

    # ============================================================
    # BREAD FACTORY MANAGER
    # ============================================================

    BREAD_MANAGER: {
        "apps": {
            "factory": {"view", "add", "change"},
            "commercial": {"view", "add", "change"},
            "inventory": {"view", "add", "change"},
            "procurement": {"view", "add", "change"},
            "organization": {"view"},
            "hr": {"view"},
            "finance": {"view"},
        },
        "exact": set(),
    },

    # ============================================================
    # PRODUCTION SUPERVISOR
    # ============================================================

    PRODUCTION_SUPERVISOR: {
        "apps": {
            "factory": {"view", "add", "change"},
            "inventory": {"view"},
        },
        "exact": set(),
    },

    # ============================================================
    # STOREKEEPER
    # ============================================================

    STOREKEEPER: {
        "apps": {
            "inventory": {"view", "add", "change"},
            "procurement": {"view", "add", "change"},
        },
        "exact": {
            "procurement.add_goodsreceipt",
            "procurement.change_goodsreceipt",
        },
    },

    # ============================================================
    # SALES OFFICER
    # ============================================================

    SALES_OFFICER: {
        "apps": {},
        "exact": {
            "commercial.view_customer",
            "commercial.add_customer",
            "commercial.change_customer",

            "commercial.view_salesinvoice",
            "commercial.add_salesinvoice",
            "commercial.change_salesinvoice",

            "commercial.view_salesinvoiceline",
            "commercial.add_salesinvoiceline",
            "commercial.change_salesinvoiceline",

            "commercial.view_factorypayment",
            "commercial.add_factorypayment",

            "commercial.view_delivery",
            "commercial.add_delivery",
            "commercial.change_delivery",

            "commercial.view_distributionroute",
            "commercial.view_vehicle",

            "factory.view_factoryproduct",

            "inventory.view_store",
            "inventory.view_item",
        },
    },

    # ============================================================
    # HR MANAGER
    # ============================================================

    HR_MANAGER: {
        "apps": {
            "hr": {"view", "add", "change"},
            "organization": {"view"},
            "payroll": {"view", "add", "change"},
        },
        "exact": set(),
    },

    # ============================================================
    # ACCOUNTANT
    # ============================================================

    ACCOUNTANT: {
        "apps": {
            "finance": {"view", "add", "change"},
            "payroll": {"view", "add", "change"},
            "procurement": {"view"},
            "commercial": {"view"},
            "hotel": {"view"},
            "factory": {"view"},
            "organization": {"view"},
        },
        "exact": set(),
    },
}


def permission_selected(permission, rule):
    app_label = permission.content_type.app_label
    codename = permission.codename

    qualified = f"{app_label}.{codename}"

    if qualified in rule.get("exact", set()):
        return True

    allowed_actions = rule.get("apps", {}).get(
        app_label,
        set(),
    )

    return any(
        codename.startswith(f"{action}_")
        for action in allowed_actions
    )


class Command(BaseCommand):

    help = (
        "Create Sonoga business units, role groups, "
        "scoped permissions, and the WordPress integration user."
    )

    def handle(self, *args, **options):

        # ========================================================
        # BUSINESS UNITS
        # ========================================================

        units = [
            (
                "HOTEL",
                "Sonoga Hotels & Suites",
                BusinessUnit.UnitType.HOTEL,
            ),
            (
                "WATER",
                "Mabinas Water",
                BusinessUnit.UnitType.WATER,
            ),
            (
                "BREAD",
                "Mabinas Bread",
                BusinessUnit.UnitType.BREAD,
            ),
        ]

        for code, name, unit_type in units:

            unit, created = BusinessUnit.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "unit_type": unit_type,
                },
            )

            if not created:

                changed = False

                if unit.name != name:
                    unit.name = name
                    changed = True

                if unit.unit_type != unit_type:
                    unit.unit_type = unit_type
                    changed = True

                if changed:
                    unit.save()

        # ========================================================
        # PERMISSIONS / ROLE GROUPS
        # ========================================================

        permissions = list(
            Permission.objects.select_related(
                "content_type"
            ).all()
        )

        for role, rule in ROLE_RULES.items():

            group, _ = Group.objects.get_or_create(
                name=role
            )

            selected = [
                perm
                for perm in permissions
                if permission_selected(
                    perm,
                    rule,
                )
            ]

            group.permissions.set(selected)

            self.stdout.write(
                f"{role}: {len(selected)} permissions"
            )

        # ========================================================
        # WORDPRESS INTEGRATION USER
        # ========================================================

        User = get_user_model()

        integration_username = getattr(
            settings,
            "SONOGA_WORDPRESS_USER",
            "wordpress-sync",
        )

        integration_user, created = User.objects.get_or_create(
            username=integration_username,
            defaults={
                "email": "wordpress-sync@sonoga.local",
                "is_active": True,
                "must_change_password": False,
                "is_staff": False,
            },
        )

        changed_fields = []

        if integration_user.is_staff:
            integration_user.is_staff = False
            changed_fields.append("is_staff")

        if integration_user.must_change_password:
            integration_user.must_change_password = False
            changed_fields.append(
                "must_change_password"
            )

        if (
            created
            or integration_user.has_usable_password()
        ):
            integration_user.set_unusable_password()
            changed_fields.append("password")

        if changed_fields:
            integration_user.save(
                update_fields=list(
                    dict.fromkeys(changed_fields)
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Sonoga bootstrap complete."
            )
        )
