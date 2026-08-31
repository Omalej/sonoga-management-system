from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from accounts.access import RECEPTIONIST


class Command(BaseCommand):
    help = "Create or repair the Sonoga Receptionist login user."

    def handle(self, *args, **options):
        User = get_user_model()

        username = "reception"
        email = "reception@sonogahotels.com"
        password = "Sonoga2026!"

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
            },
        )

        user.email = email
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False

        user.set_password(password)
        user.save()

        group, _ = Group.objects.get_or_create(name=RECEPTIONIST)
        user.groups.add(group)

        self.stdout.write(
            self.style.SUCCESS(
                "Receptionist account repaired successfully."
            )
        )
        self.stdout.write(f"Username: {username}")
        self.stdout.write(f"Password: {password}")
        self.stdout.write(f"Active: {user.is_active}")
        self.stdout.write(f"Receptionist group: {group.name}")
