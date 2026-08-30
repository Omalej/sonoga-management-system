from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = "Create or update the Sonoga Receptionist login user."

    def handle(self, *args, **options):
        User = get_user_model()

        username = "reception"
        email = "reception@sonogahotels.com"
        password = "ChangeMe123!"

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_active": True,
                "is_staff": False,
                "must_change_password": False,
            },
        )

        user.email = email
        user.is_active = True
        user.must_change_password = False
        user.set_password(password)
        user.save()

        group, _ = Group.objects.get_or_create(
            name="Receptionist"
        )

        user.groups.add(group)

        self.stdout.write(
            self.style.SUCCESS(
                "Receptionist account is ready."
            )
        )
        self.stdout.write(f"Username: {username}")
        self.stdout.write(f"Password: {password}")