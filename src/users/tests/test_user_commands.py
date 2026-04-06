"""Tests for user management commands."""

import os
from io import StringIO
from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.core.management.base import CommandError

User = get_user_model()


class TestCreateAdminCommand(TestCase):
    """Test create_admin command functionality."""

    def setUp(self):
        """Set up test data."""
        # Clear environment variables
        for env_var in ["ADMIN_USER", "ADMIN_EMAIL", "ADMIN_PASS"]:
            if env_var in os.environ:
                del os.environ[env_var]

    def tearDown(self):
        """Clean up after tests."""
        # Clear environment variables
        for env_var in ["ADMIN_USER", "ADMIN_EMAIL", "ADMIN_PASS"]:
            if env_var in os.environ:
                del os.environ[env_var]

    def test_create_admin_command_exists(self):
        """Test that create_admin command is properly registered."""
        try:
            out = StringIO()
            call_command("create_admin", "--help", stdout=out)
        except SystemExit:  # --help causes exit
            pass

        # If we get here without error, command exists
        self.assertTrue(True)

    def test_create_admin_missing_environment_variables(self):
        """Test command behavior when environment variables are missing."""
        out = StringIO()
        call_command("create_admin", stdout=out)

        output = out.getvalue()
        self.assertIn("Missing ADMIN_USER, ADMIN_EMAIL, or ADMIN_PASS", output)

    def test_create_admin_missing_username(self):
        """Test command behavior when ADMIN_USER is missing."""
        os.environ["ADMIN_EMAIL"] = "admin@example.com"
        os.environ["ADMIN_PASS"] = "testpassword123"

        out = StringIO()
        call_command("create_admin", stdout=out)

        output = out.getvalue()
        self.assertIn("Missing ADMIN_USER, ADMIN_EMAIL, or ADMIN_PASS", output)

    def test_create_admin_missing_email(self):
        """Test command behavior when ADMIN_EMAIL is missing."""
        os.environ["ADMIN_USER"] = "admin"
        os.environ["ADMIN_PASS"] = "testpassword123"

        out = StringIO()
        call_command("create_admin", stdout=out)

        output = out.getvalue()
        self.assertIn("Missing ADMIN_USER, ADMIN_EMAIL, or ADMIN_PASS", output)

    def test_create_admin_missing_password(self):
        """Test command behavior when ADMIN_PASS is missing."""
        os.environ["ADMIN_USER"] = "admin"
        os.environ["ADMIN_EMAIL"] = "admin@example.com"

        out = StringIO()
        call_command("create_admin", stdout=out)

        output = out.getvalue()
        self.assertIn("Missing ADMIN_USER, ADMIN_EMAIL, or ADMIN_PASS", output)

    def test_create_admin_successful_creation(self):
        """Test successful admin user creation."""
        os.environ["ADMIN_USER"] = "testadmin"
        os.environ["ADMIN_EMAIL"] = "testadmin@example.com"
        os.environ["ADMIN_PASS"] = "testpassword123"

        out = StringIO()
        call_command("create_admin", stdout=out)

        output = out.getvalue()
        self.assertIn('Admin user "testadmin" created successfully', output)

        # Verify user was created
        user = User.objects.get(username="testadmin")
        self.assertEqual(user.email, "testadmin@example.com")
        self.assertTrue(user.check_password("testpassword123"))
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_create_admin_idempotent_behavior(self):
        """Test that command is idempotent (doesn't create duplicate users)."""
        os.environ["ADMIN_USER"] = "testadmin"
        os.environ["ADMIN_EMAIL"] = "testadmin@example.com"
        os.environ["ADMIN_PASS"] = "testpassword123"

        # Run command first time
        out = StringIO()
        call_command("create_admin", stdout=out)

        output = out.getvalue()
        self.assertIn('Admin user "testadmin" created successfully', output)

        # Run command second time
        out = StringIO()
        call_command("create_admin", stdout=out)

        output = out.getvalue()
        self.assertIn('Admin user "testadmin" already exists. Skipping.', output)

        # Verify only one user exists
        self.assertEqual(User.objects.filter(username="testadmin").count(), 1)

    def test_create_admin_with_existing_regular_user(self):
        """Test command behavior when regular user with same username exists."""
        # Create regular user first
        User.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            password="existingpass123",
        )

        os.environ["ADMIN_USER"] = "existinguser"
        os.environ["ADMIN_EMAIL"] = "admin@example.com"
        os.environ["ADMIN_PASS"] = "adminpass123"

        out = StringIO()
        call_command("create_admin", stdout=out)

        output = out.getvalue()
        self.assertIn('Admin user "existinguser" already exists. Skipping.', output)

        # Verify user was not modified
        user = User.objects.get(username="existinguser")
        self.assertEqual(user.email, "existing@example.com")
        self.assertTrue(user.check_password("existingpass123"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_admin_with_empty_environment_variables(self):
        """Test command behavior with empty environment variables."""
        os.environ["ADMIN_USER"] = ""
        os.environ["ADMIN_EMAIL"] = "admin@example.com"
        os.environ["ADMIN_PASS"] = "testpassword123"

        out = StringIO()
        call_command("create_admin", stdout=out)

        output = out.getvalue()
        self.assertIn("Missing ADMIN_USER, ADMIN_EMAIL, or ADMIN_PASS", output)

    def test_create_admin_password_bypasses_validation(self):
        """Test that command bypasses password validation."""
        # Use a weak password that would normally fail validation
        os.environ["ADMIN_USER"] = "testadmin"
        os.environ["ADMIN_EMAIL"] = "testadmin@example.com"
        os.environ["ADMIN_PASS"] = "123"  # Weak password

        out = StringIO()
        call_command("create_admin", stdout=out)

        output = out.getvalue()
        self.assertIn('Admin user "testadmin" created successfully', output)

        # Verify user was created with weak password
        user = User.objects.get(username="testadmin")
        self.assertTrue(user.check_password("123"))

    def test_create_admin_with_special_characters(self):
        """Test command with special characters in credentials."""
        os.environ["ADMIN_USER"] = "admin@test"
        os.environ["ADMIN_EMAIL"] = "admin+test@example.com"
        os.environ["ADMIN_PASS"] = "p@ssw0rd!@#$%"

        out = StringIO()
        call_command("create_admin", stdout=out)

        output = out.getvalue()
        self.assertIn('Admin user "admin@test" created successfully', output)

        # Verify user was created
        user = User.objects.get(username="admin@test")
        self.assertEqual(user.email, "admin+test@example.com")
        self.assertTrue(user.check_password("p@ssw0rd!@#$%"))


class TestEnsureAdminCommand(TestCase):
    """Test ensure_admin command functionality."""

    def test_ensure_admin_command_exists(self):
        """Test that ensure_admin command is properly registered."""
        try:
            out = StringIO()
            call_command("ensure_admin", "--help", stdout=out)
        except SystemExit:  # --help causes exit
            pass

        # If we get here without error, command exists
        self.assertTrue(True)

    def test_ensure_admin_creates_new_user(self):
        """Test ensure_admin creates new admin user when none exists."""
        out = StringIO()
        call_command("ensure_admin", stdout=out)

        output = out.getvalue()
        self.assertIn("Created admin user", output)
        self.assertIn("Password verification successful", output)
        self.assertIn("Username: admin", output)
        self.assertIn("Password:", output)

        # Verify user was created
        user = User.objects.get(username="admin")
        self.assertEqual(user.email, "admin@example.com")
        # Password should be set from environment variable or default
        self.assertTrue(user.check_password(os.environ.get("ADMIN_PASS", "changeme123")))
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_ensure_admin_resets_existing_user_password(self):
        """Test ensure_admin resets password for existing admin user."""
        # Create existing admin user with different password
        existing_user = User.objects.create_user(
            username="admin", email="old@example.com", password="oldpassword123"
        )
        existing_user.is_staff = False
        existing_user.is_superuser = False
        existing_user.is_active = False
        existing_user.save()

        out = StringIO()
        call_command("ensure_admin", stdout=out)

        output = out.getvalue()
        self.assertIn("Admin user already exists. Resetting password", output)
        self.assertIn("Password reset for admin user", output)
        self.assertIn("Password verification successful", output)

        # Verify user was updated
        user = User.objects.get(username="admin")
        self.assertEqual(user.email, "old@example.com")  # Email should not change
        # Password should be set from environment variable or default
        self.assertTrue(user.check_password(os.environ.get("ADMIN_PASS", "changeme123")))
        self.assertFalse(user.check_password("oldpassword123"))
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_ensure_admin_idempotent_behavior(self):
        """Test that ensure_admin is idempotent."""
        # Run command first time
        out = StringIO()
        call_command("ensure_admin", stdout=out)

        output = out.getvalue()
        self.assertIn("Created admin user", output)

        # Run command second time
        out = StringIO()
        call_command("ensure_admin", stdout=out)

        output = out.getvalue()
        self.assertIn("Admin user already exists. Resetting password", output)

        # Verify only one user exists
        self.assertEqual(User.objects.filter(username="admin").count(), 1)

        # Verify user still has correct credentials
        user = User.objects.get(username="admin")
        # Password should be set from environment variable or default
        self.assertTrue(user.check_password(os.environ.get("ADMIN_PASS", "changeme123")))

    def test_ensure_admin_password_verification(self):
        """Test password verification in ensure_admin command."""
        out = StringIO()
        call_command("ensure_admin", stdout=out)

        output = out.getvalue()
        self.assertIn("Password verification successful", output)
        self.assertNotIn("Password verification failed", output)

        # Verify password actually works
        user = User.objects.get(username="admin")
        # Password should be set from environment variable or default
        self.assertTrue(user.check_password(os.environ.get("ADMIN_PASS", "changeme123")))

    def test_ensure_admin_updates_user_flags(self):
        """Test that ensure_admin properly sets user flags."""
        # Create regular user with admin username
        User.objects.create_user(
            username="admin", email="admin@example.com", password="oldpass123"
        )

        out = StringIO()
        call_command("ensure_admin", stdout=out)

        # Verify user flags were updated
        user = User.objects.get(username="admin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_ensure_admin_with_inactive_user(self):
        """Test ensure_admin with inactive existing user."""
        # Create inactive admin user
        existing_user = User.objects.create_user(
            username="admin", email="admin@example.com", password="oldpass123"
        )
        existing_user.is_active = False
        existing_user.save()

        out = StringIO()
        call_command("ensure_admin", stdout=out)

        # Verify user was activated
        user = User.objects.get(username="admin")
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_ensure_admin_preserves_email(self):
        """Test that ensure_admin preserves existing user's email."""
        # Create existing user with custom email
        User.objects.create_user(
            username="admin", email="custom@example.com", password="oldpass123"
        )

        out = StringIO()
        call_command("ensure_admin", stdout=out)

        # Verify email was preserved
        user = User.objects.get(username="admin")
        self.assertEqual(user.email, "custom@example.com")

    def test_ensure_admin_command_output_format(self):
        """Test ensure_admin command output format."""
        out = StringIO()
        call_command("ensure_admin", stdout=out)

        output = out.getvalue()
        # Check for required output elements
        self.assertIn("admin user", output.lower())
        self.assertIn("Username: admin", output)
        self.assertIn("Password:", output)
        self.assertIn("✓", output)  # Success checkmark

    def test_ensure_admin_multiple_runs_consistency(self):
        """Test that multiple runs of ensure_admin are consistent."""
        # Run command multiple times
        for i in range(3):
            out = StringIO()
            call_command("ensure_admin", stdout=out)

            output = out.getvalue()
            self.assertIn("Password verification successful", output)

            # Verify user still has correct credentials
            user = User.objects.get(username="admin")
            # Password should be set from environment variable or default
        self.assertTrue(user.check_password(os.environ.get("ADMIN_PASS", "changeme123")))
            self.assertTrue(user.is_staff)
            self.assertTrue(user.is_superuser)
            self.assertTrue(user.is_active)

        # Verify only one user exists
        self.assertEqual(User.objects.filter(username="admin").count(), 1)


class TestUserCommandsIntegration(TestCase):
    """Test integration between different user commands."""

    def test_create_admin_then_ensure_admin(self):
        """Test running create_admin followed by ensure_admin."""
        # First use create_admin
        os.environ["ADMIN_USER"] = "admin"
        os.environ["ADMIN_EMAIL"] = "admin@example.com"
        os.environ["ADMIN_PASS"] = "custompass123"

        out = StringIO()
        call_command("create_admin", stdout=out)

        output = out.getvalue()
        self.assertIn('Admin user "admin" created successfully', output)

        # Verify user was created with custom password
        user = User.objects.get(username="admin")
        self.assertTrue(user.check_password("custompass123"))

        # Clean up environment
        del os.environ["ADMIN_USER"]
        del os.environ["ADMIN_EMAIL"]
        del os.environ["ADMIN_PASS"]

        # Now use ensure_admin
        out = StringIO()
        call_command("ensure_admin", stdout=out)

        output = out.getvalue()
        self.assertIn("Admin user already exists. Resetting password", output)

        # Verify password was reset to configured value
        user = User.objects.get(username="admin")
        # Password should be set from environment variable or default
        self.assertTrue(user.check_password(os.environ.get("ADMIN_PASS", "changeme123")))
        self.assertFalse(user.check_password("custompass123"))

    def test_ensure_admin_then_create_admin(self):
        """Test running ensure_admin followed by create_admin."""
        # First use ensure_admin
        out = StringIO()
        call_command("ensure_admin", stdout=out)

        output = out.getvalue()
        self.assertIn("Created admin user", output)

        # Now use create_admin with same username
        os.environ["ADMIN_USER"] = "admin"
        os.environ["ADMIN_EMAIL"] = "admin@example.com"
        os.environ["ADMIN_PASS"] = "newpass123"

        out = StringIO()
        call_command("create_admin", stdout=out)

        output = out.getvalue()
        self.assertIn('Admin user "admin" already exists. Skipping.', output)

        # Verify password was not changed
        user = User.objects.get(username="admin")
        # Password should be set from environment variable or default
        self.assertTrue(user.check_password(os.environ.get("ADMIN_PASS", "changeme123")))
        self.assertFalse(user.check_password("newpass123"))

        # Clean up
        del os.environ["ADMIN_USER"]
        del os.environ["ADMIN_EMAIL"]
        del os.environ["ADMIN_PASS"]

    def test_command_help_text(self):
        """Test help text for user commands."""
        commands = ["create_admin", "ensure_admin"]

        for command in commands:
            try:
                out = StringIO()
                call_command(command, "--help", stdout=out)
            except SystemExit:  # --help causes exit
                pass

            # Command should be registered and have help text
            self.assertTrue(True)

    def test_commands_work_in_different_environments(self):
        """Test that commands work in different environment setups."""
        # Test with clean environment
        for env_var in ["ADMIN_USER", "ADMIN_EMAIL", "ADMIN_PASS"]:
            if env_var in os.environ:
                del os.environ[env_var]

        # ensure_admin should work without environment variables
        out = StringIO()
        call_command("ensure_admin", stdout=out)

        output = out.getvalue()
        self.assertIn("Created admin user", output)

        # create_admin should fail without environment variables
        out = StringIO()
        call_command("create_admin", stdout=out)

        output = out.getvalue()
        self.assertIn("Missing ADMIN_USER, ADMIN_EMAIL, or ADMIN_PASS", output)

    def test_user_creation_with_uuid_primary_key(self):
        """Test that commands work with UUID primary keys."""
        out = StringIO()
        call_command("ensure_admin", stdout=out)

        # Verify user was created with UUID primary key
        user = User.objects.get(username="admin")
        self.assertIsNotNone(user.id)

        # UUID should be a valid UUID
        import uuid

        self.assertIsInstance(user.id, uuid.UUID)

    def test_concurrent_command_execution_safety(self):
        """Test that commands are safe for concurrent execution."""
        # This test simulates concurrent execution by running ensure_admin multiple times
        # In a real scenario, you'd use threading or multiprocessing

        results = []
        for i in range(3):
            out = StringIO()
            call_command("ensure_admin", stdout=out)
            results.append(out.getvalue())

        # All executions should succeed
        for result in results:
            self.assertIn("Password verification successful", result)

        # Only one user should exist
        self.assertEqual(User.objects.filter(username="admin").count(), 1)
