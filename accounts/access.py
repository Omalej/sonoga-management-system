from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


# ============================================================
# SONOGA GROUP ROLES
# ============================================================

CEO = "CEO"
GENERAL_MANAGER = "General Manager"

GROUP_MANAGEMENT = "Group Management"

# HOTEL
HOTEL_MANAGER = "Hotel Manager"
RECEPTIONIST = "Receptionist"
HOUSEKEEPING = "Housekeeping"

# FACTORIES / BUSINESS UNITS
WATER_MANAGER = "Water Factory Manager"
BREAD_MANAGER = "Bread Factory Manager"
PRODUCTION_SUPERVISOR = "Production Supervisor"

# OPERATIONS
STOREKEEPER = "Storekeeper"
SALES_OFFICER = "Sales Officer"

# CORPORATE
HR_MANAGER = "HR Manager"
ACCOUNTANT = "Accountant"
AUDITOR = "Auditor"


def role_names(user):
    if not user.is_authenticated:
        return set()

    return set(
        user.groups.values_list("name", flat=True)
    )


def has_any_role(user, *roles):
    if not user.is_authenticated:
        return False

    # Superusers can access everything.
    if user.is_superuser:
        return True

    return bool(
        role_names(user).intersection(roles)
    )


def employee_for(user):
    try:
        return user.employee
    except Exception:
        return None


def business_unit_for(user):
    employee = employee_for(user)

    return (
        employee.business_unit
        if employee
        else None
    )


def role_required(*roles):
    def decorator(view_func):

        @wraps(view_func)
        def wrapped(request, *args, **kwargs):

            if not request.user.is_authenticated:
                return redirect_to_login(
                    request.get_full_path()
                )

            if not has_any_role(
                request.user,
                *roles
            ):
                raise PermissionDenied

            return view_func(
                request,
                *args,
                **kwargs
            )

        return wrapped

    return decorator