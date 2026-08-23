from .access import (
    ACCOUNTANT, AUDITOR, BREAD_MANAGER, GROUP_MANAGEMENT, HOTEL_MANAGER,
    HOUSEKEEPING, HR_MANAGER, PRODUCTION_SUPERVISOR, RECEPTIONIST,
    SALES_OFFICER, STOREKEEPER, WATER_MANAGER, business_unit_for, has_any_role,
)


def sonoga_navigation(request):
    user = request.user
    if not getattr(user, "is_authenticated", False):
        return {"sonoga_nav": {}}
    unit = business_unit_for(user)
    is_group = user.is_superuser or has_any_role(user, GROUP_MANAGEMENT, AUDITOR)
    hotel_frontdesk = user.is_superuser or has_any_role(user, GROUP_MANAGEMENT, HOTEL_MANAGER, RECEPTIONIST)
    housekeeping = user.is_superuser or has_any_role(user, GROUP_MANAGEMENT, HOTEL_MANAGER, HOUSEKEEPING)
    factory = user.is_superuser or has_any_role(user, GROUP_MANAGEMENT, WATER_MANAGER, BREAD_MANAGER, PRODUCTION_SUPERVISOR, STOREKEEPER, SALES_OFFICER)
    finance = user.is_superuser or has_any_role(user, GROUP_MANAGEMENT, ACCOUNTANT)
    hr = user.is_superuser or has_any_role(user, GROUP_MANAGEMENT, HR_MANAGER)
    inventory = user.is_superuser or has_any_role(user, GROUP_MANAGEMENT, HOTEL_MANAGER, WATER_MANAGER, BREAD_MANAGER, STOREKEEPER)
    procurement = user.is_superuser or has_any_role(user, GROUP_MANAGEMENT, ACCOUNTANT, HOTEL_MANAGER, WATER_MANAGER, BREAD_MANAGER, STOREKEEPER)
    payroll = user.is_superuser or has_any_role(user, GROUP_MANAGEMENT, HR_MANAGER, ACCOUNTANT)
    approvals = user.is_superuser or has_any_role(user, GROUP_MANAGEMENT, ACCOUNTANT, HR_MANAGER, HOTEL_MANAGER, WATER_MANAGER, BREAD_MANAGER)
    notifications = user.is_superuser or has_any_role(user, GROUP_MANAGEMENT, ACCOUNTANT, HR_MANAGER, HOTEL_MANAGER, WATER_MANAGER, BREAD_MANAGER, STOREKEEPER)
    return {
        "sonoga_nav": {
            "group": is_group,
            "hotel": hotel_frontdesk or housekeeping,
            "hotel_frontdesk": hotel_frontdesk,
            "housekeeping": housekeeping,
            "factory": factory,
            "finance": finance,
            "hr": hr,
            "inventory": inventory,
            "procurement": procurement,
            "payroll": payroll,
            "approvals": approvals,
            "notifications": notifications,
            "audit": user.is_superuser or has_any_role(user, GROUP_MANAGEMENT, AUDITOR),
            "admin": user.is_staff,
            "unit": unit,
        }
    }
