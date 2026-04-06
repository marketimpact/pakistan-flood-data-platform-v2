"""Tests for custom User model."""

import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

User = get_user_model()


class TestUserModel(TestCase):
    """Test custom User model functionality."""

    def test_user_creation(self):
        """Test basic user creation."""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword123"
        )

        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("testpassword123"))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_uuid_primary_key(self):
        """Test that User model uses UUID as primary key."""
        user = User.objects.create_user(username="uuiduser", password="testpassword123")

        # Test that id is UUID
        self.assertIsInstance(user.id, uuid.UUID)

        # Test that UUIDs are unique
        user2 = User.objects.create_user(
            username="uuiduser2", password="testpassword123"
        )
        self.assertNotEqual(user.id, user2.id)

    def test_uuid_not_editable(self):
        """Test that UUID field is not editable."""
        id_field = User._meta.get_field("id")
        self.assertFalse(id_field.editable)

    def test_password_hashing(self):
        """Test password hashing functionality."""
        user = User.objects.create_user(
            username="hashuser", password="plainpassword123"
        )

        # Password should be hashed, not stored in plain text
        self.assertNotEqual(user.password, "plainpassword123")

        # Should be able to check password
        self.assertTrue(user.check_password("plainpassword123"))
        self.assertFalse(user.check_password("wrongpassword"))

    def test_superuser_creation(self):
        """Test superuser creation."""
        superuser = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpassword123"
        )

        self.assertEqual(superuser.username, "admin")
        self.assertEqual(superuser.email, "admin@example.com")
        self.assertTrue(superuser.check_password("adminpassword123"))
        self.assertTrue(superuser.is_active)
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)

    def test_superuser_creation_without_is_staff(self):
        """Test that superuser creation requires is_staff=True."""
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                username="admin",
                email="admin@example.com",
                password="adminpassword123",
                is_staff=False,
            )

    def test_superuser_creation_without_is_superuser(self):
        """Test that superuser creation requires is_superuser=True."""
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                username="admin",
                email="admin@example.com",
                password="adminpassword123",
                is_superuser=False,
            )

    def test_string_representation(self):
        """Test __str__ method returns username."""
        user = User.objects.create_user(
            username="stringuser", password="testpassword123"
        )

        self.assertEqual(str(user), "stringuser")

    def test_username_uniqueness(self):
        """Test that username must be unique."""
        User.objects.create_user(username="unique", password="testpassword123")

        # Try to create another user with same username
        with self.assertRaises(IntegrityError):
            User.objects.create_user(username="unique", password="testpassword123")

    def test_email_field(self):
        """Test email field functionality."""
        user = User.objects.create_user(
            username="emailuser", email="test@example.com", password="testpassword123"
        )

        self.assertEqual(user.email, "test@example.com")

        # Test email is optional
        user2 = User.objects.create_user(username="noemail", password="testpassword123")
        self.assertEqual(user2.email, "")

    def test_user_permissions(self):
        """Test user permissions functionality."""
        user = User.objects.create_user(username="permuser", password="testpassword123")

        # User should start with no permissions
        self.assertEqual(user.user_permissions.count(), 0)
        self.assertFalse(user.has_perm("auth.add_user"))

        # Add permission
        content_type = ContentType.objects.get_for_model(User)
        permission = Permission.objects.get(
            codename="add_user", content_type=content_type
        )
        user.user_permissions.add(permission)

        # Need to refresh user from DB for permissions to take effect
        user = User.objects.get(pk=user.pk)
        
        # User should now have permission
        self.assertTrue(user.has_perm("auth.add_user"))

    def test_user_groups(self):
        """Test user groups functionality."""
        from django.contrib.auth.models import Group

        user = User.objects.create_user(
            username="groupuser", password="testpassword123"
        )

        # User should start with no groups
        self.assertEqual(user.groups.count(), 0)

        # Create and add group
        group = Group.objects.create(name="TestGroup")
        user.groups.add(group)

        # User should now be in group
        self.assertIn(group, user.groups.all())

    def test_staff_status(self):
        """Test staff status functionality."""
        user = User.objects.create_user(
            username="staffuser", password="testpassword123"
        )

        # User should not be staff by default
        self.assertFalse(user.is_staff)

        # Make user staff
        user.is_staff = True
        user.save()

        self.assertTrue(user.is_staff)

    def test_active_status(self):
        """Test active status functionality."""
        user = User.objects.create_user(
            username="activeuser", password="testpassword123"
        )

        # User should be active by default
        self.assertTrue(user.is_active)

        # Deactivate user
        user.is_active = False
        user.save()

        self.assertFalse(user.is_active)

    def test_date_joined(self):
        """Test date_joined field."""
        user = User.objects.create_user(username="dateuser", password="testpassword123")

        # date_joined should be set automatically
        self.assertIsNotNone(user.date_joined)

        # Should be a datetime object
        from datetime import datetime

        self.assertIsInstance(user.date_joined, datetime)

    def test_last_login(self):
        """Test last_login field."""
        user = User.objects.create_user(
            username="loginuser", password="testpassword123"
        )

        # last_login should be None initially
        self.assertIsNone(user.last_login)

        # After login, last_login should be set
        from django.contrib.auth import authenticate
        from django.utils import timezone

        user.last_login = timezone.now()
        user.save()

        self.assertIsNotNone(user.last_login)

    def test_first_name_last_name(self):
        """Test first_name and last_name fields."""
        user = User.objects.create_user(
            username="nameuser",
            password="testpassword123",
            first_name="John",
            last_name="Doe",
        )

        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "Doe")

        # Test get_full_name method
        self.assertEqual(user.get_full_name(), "John Doe")

        # Test get_short_name method
        self.assertEqual(user.get_short_name(), "John")

    def test_user_without_username(self):
        """Test that username is required."""
        with self.assertRaises(ValueError):
            User.objects.create_user(username="", password="testpassword123")

    def test_user_without_password(self):
        """Test user creation without password."""
        user = User.objects.create_user(username="nopassuser")

        # User should have unusable password
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.check_password(""))
        self.assertFalse(user.check_password("anypassword"))

    def test_user_model_inheritance(self):
        """Test that User model inherits from AbstractUser."""
        from django.contrib.auth.models import AbstractUser

        self.assertTrue(issubclass(User, AbstractUser))

        # Should have all AbstractUser fields
        expected_fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
            "password",
        ]

        user_fields = [field.name for field in User._meta.fields]
        for field in expected_fields:
            self.assertIn(field, user_fields)

    def test_user_manager(self):
        """Test user manager functionality."""
        # Test create_user
        user = User.objects.create_user(
            username="manageruser", password="testpassword123"
        )
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

        # Test create_superuser
        superuser = User.objects.create_superuser(
            username="managersuperuser", password="testpassword123"
        )
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)

    def test_user_meta_options(self):
        """Test User model meta options."""
        # Test that User model has proper meta options
        self.assertIsNotNone(User._meta)

        # Test verbose names (inherited from AbstractUser)
        self.assertEqual(User._meta.verbose_name, "user")
        self.assertEqual(User._meta.verbose_name_plural, "users")

    def test_user_authentication_backend_compatibility(self):
        """Test compatibility with Django's authentication backend."""
        user = User.objects.create_user(username="authuser", password="testpassword123")

        # Test that user can be authenticated
        from django.contrib.auth import authenticate

        authenticated_user = authenticate(
            username="authuser", password="testpassword123"
        )
        self.assertEqual(authenticated_user, user)

        # Test failed authentication
        failed_auth = authenticate(username="authuser", password="wrongpassword")
        self.assertIsNone(failed_auth)

    def test_user_session_compatibility(self):
        """Test user model works with Django sessions."""
        user = User.objects.create_user(
            username="sessionuser", password="testpassword123"
        )

        # Test that user can be serialized (important for sessions)
        from django.contrib.sessions.serializers import JSONSerializer

        serializer = JSONSerializer()

        # Convert UUID to string for JSON serialization
        try:
            serialized = serializer.dumps(str(user.pk))
            deserialized = serializer.loads(serialized)
            self.assertEqual(str(user.pk), str(deserialized))
        except Exception as e:
            self.fail(f"User serialization failed: {e}")

    def test_user_admin_display(self):
        """Test user display in admin interface."""
        user = User.objects.create_user(
            username="adminuser",
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
        )

        # Test string representation for admin
        self.assertEqual(str(user), "adminuser")

        # Test that all necessary fields are accessible
        self.assertEqual(user.username, "adminuser")
        self.assertEqual(user.email, "admin@example.com")
        self.assertEqual(user.get_full_name(), "Admin User")
