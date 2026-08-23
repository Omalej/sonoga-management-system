from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class SonogaUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Sonoga Access", {"fields": ("must_change_password",)}),
    )
