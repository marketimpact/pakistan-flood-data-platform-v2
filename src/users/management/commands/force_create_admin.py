import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = "Force creates admin user, deleting existing one if present"

    def handle(self, *args, **options):
        username = os.environ.get("ADMIN_USER", "admin")
        email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
        password = os.environ.get("ADMIN_PASS", "Admin2025!")

        with transaction.atomic():
            # Delete existing admin user
            deleted_count = User.objects.filter(username=username).delete()[0]
            if deleted_count > 0:
                self.stdout.write(
                    self.style.WARNING(f'Deleted existing admin user "{username}"')
                )

            # Create new admin user
            user = User(username=username, email=email)
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()

            # Verify the password was set correctly
            if user.check_password(password):
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Admin user "{username}" created successfully with password "{password}"'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR("Warning: Password verification failed!")
                )

            # Double-check by fetching from database
            verify_user = User.objects.get(username=username)
            self.stdout.write(
                f"Verification - Password check: {verify_user.check_password(password)}"
            )
