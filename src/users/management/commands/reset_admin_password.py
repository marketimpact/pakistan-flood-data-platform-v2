from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Resets the admin user password to Admin2025!"

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username="admin")
            user.set_password("Admin2025!")
            user.save()
            self.stdout.write(self.style.SUCCESS("Admin password reset successfully!"))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR("Admin user does not exist."))
