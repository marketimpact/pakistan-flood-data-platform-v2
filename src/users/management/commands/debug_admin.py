from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Debug admin user status and authentication"

    def handle(self, *args, **options):
        self.stdout.write("=== Admin User Debug Information ===")

        # Check if admin user exists
        try:
            admin = User.objects.get(username="admin")
            self.stdout.write(self.style.SUCCESS(f"✓ Admin user exists"))
            self.stdout.write(f"  - Email: {admin.email}")
            self.stdout.write(f"  - Is superuser: {admin.is_superuser}")
            self.stdout.write(f"  - Is staff: {admin.is_staff}")
            self.stdout.write(f"  - Is active: {admin.is_active}")
            self.stdout.write(f"  - Date joined: {admin.date_joined}")

            # Test password
            test_passwords = ["Admin2025!", "admin", "2025", "FloodDataPK"]
            self.stdout.write("\nTesting passwords:")
            for pwd in test_passwords:
                if admin.check_password(pwd):
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Password "{pwd}" is correct')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Password "{pwd}" is incorrect')
                    )

        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR("✗ Admin user does not exist"))

        # List all superusers
        self.stdout.write("\n=== All Superusers ===")
        superusers = User.objects.filter(is_superuser=True)
        if superusers.exists():
            for user in superusers:
                self.stdout.write(f"- {user.username} (email: {user.email})")
        else:
            self.stdout.write("No superusers found")
