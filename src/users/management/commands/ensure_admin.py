import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Ensures admin user exists with configured password"

    def handle(self, *args, **options):
        username = "admin"
        email = "admin@example.com"
        password = os.environ.get("ADMIN_PASS", "changeme123")

        try:
            # Try to get existing admin user
            user = User.objects.get(username=username)
            self.stdout.write(f"Admin user already exists. Resetting password...")
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Password reset for admin user"))
        except User.DoesNotExist:
            # Create new admin user
            user = User.objects.create_user(
                username=username, email=email, password=password
            )
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created admin user"))

        # Verify
        fresh_user = User.objects.get(username=username)
        if fresh_user.check_password(password):
            self.stdout.write(self.style.SUCCESS(f"✓ Password verification successful"))
            self.stdout.write(f"Username: {username}")
            self.stdout.write(f"Password: [Set via ADMIN_PASS environment variable]")
        else:
            self.stdout.write(self.style.ERROR(f"✗ Password verification failed!"))
