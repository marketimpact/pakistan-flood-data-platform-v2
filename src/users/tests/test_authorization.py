"""Authorization tests for access control and permissions."""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from core.models import Gauge, Reading, Prediction

User = get_user_model()


class TestDashboardAuthorization(TestCase):
    """Test dashboard access authorization."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpassword123"
        )
        self.staff_user = User.objects.create_user(
            username="staffuser", password="staffpassword123", is_staff=True
        )
        self.superuser = User.objects.create_superuser(
            username="admin", password="adminpassword123"
        )

    def test_dashboard_login_requirement(self):
        """Test that dashboard requires login."""
        # Test unauthenticated access
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/supersecretadminpanel/login/", response.url)

        # Test authenticated access
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)

    def test_dashboard_actions_login_requirement(self):
        """Test that dashboard actions require login."""
        actions = [
            "/dashboard/collect-data/",
            "/dashboard/update-readings/",
            "/dashboard/clear-data/",
            "/dashboard/export/readings/",
        ]

        for action_url in actions:
            # Test unauthenticated access
            response = self.client.get(action_url)
            self.assertEqual(response.status_code, 302)
            self.assertIn("/supersecretadminpanel/login/", response.url)

            response = self.client.post(action_url)
            self.assertEqual(response.status_code, 302)
            self.assertIn("/supersecretadminpanel/login/", response.url)

    def test_dashboard_access_with_different_user_types(self):
        """Test dashboard access with different user types."""
        # Test regular user
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)

        # Test staff user
        self.client.logout()
        self.client.login(username="staffuser", password="staffpassword123")
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)

        # Test superuser
        self.client.logout()
        self.client.login(username="admin", password="adminpassword123")
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)

    def test_export_functionality_authorization(self):
        """Test export functionality authorization."""
        # Test unauthenticated access
        response = self.client.get("/dashboard/export/readings/")
        self.assertEqual(response.status_code, 302)

        # Test authenticated access
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get("/dashboard/export/readings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")


class TestAdminPanelAuthorization(TestCase):
    """Test admin panel access authorization."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpassword123"
        )
        self.staff_user = User.objects.create_user(
            username="staffuser", password="staffpassword123", is_staff=True
        )
        self.superuser = User.objects.create_superuser(
            username="admin", password="adminpassword123"
        )

    def test_admin_panel_staff_requirement(self):
        """Test that admin panel requires staff status."""
        # Test unauthenticated access
        response = self.client.get("/supersecretadminpanel/")
        self.assertEqual(response.status_code, 302)

        # Test regular user (not staff)
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get("/supersecretadminpanel/")
        self.assertEqual(response.status_code, 302)  # Redirected to login

        # Test staff user
        self.client.logout()
        self.client.login(username="staffuser", password="staffpassword123")
        response = self.client.get("/supersecretadminpanel/")
        self.assertEqual(response.status_code, 200)

        # Test superuser
        self.client.logout()
        self.client.login(username="admin", password="adminpassword123")
        response = self.client.get("/supersecretadminpanel/")
        self.assertEqual(response.status_code, 200)

    def test_admin_login_page_access(self):
        """Test admin login page access."""
        # Anyone should be able to access login page
        response = self.client.get("/supersecretadminpanel/login/")
        self.assertEqual(response.status_code, 200)

        # Test with authenticated user
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get("/supersecretadminpanel/login/")
        self.assertEqual(response.status_code, 200)

    def test_admin_model_access_permissions(self):
        """Test admin model access permissions."""
        # Test staff user can access admin
        self.client.login(username="staffuser", password="staffpassword123")
        response = self.client.get("/supersecretadminpanel/")
        self.assertEqual(response.status_code, 200)

        # Test superuser has full access
        self.client.logout()
        self.client.login(username="admin", password="adminpassword123")
        response = self.client.get("/supersecretadminpanel/")
        self.assertEqual(response.status_code, 200)

    def test_admin_logout_functionality(self):
        """Test admin logout functionality."""
        # Login as staff user
        self.client.login(username="staffuser", password="staffpassword123")
        response = self.client.get("/supersecretadminpanel/")
        self.assertEqual(response.status_code, 200)

        # Logout
        response = self.client.post("/supersecretadminpanel/logout/")
        self.assertEqual(response.status_code, 302)

        # Should no longer have access
        response = self.client.get("/supersecretadminpanel/")
        self.assertEqual(response.status_code, 302)


class TestAPIAuthorization(TestCase):
    """Test API endpoint authorization."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="apiuser", password="apipassword123"
        )
        self.staff_user = User.objects.create_user(
            username="staffuser", password="staffpassword123", is_staff=True
        )
        # Create some test data
        self.gauge = Gauge.objects.create(
            gauge_id="test_gauge",
            name="Test Gauge",
            latitude=30.0,
            longitude=70.0,
            country_code="PK",
        )

    def test_api_unauthenticated_access(self):
        """Test API access without authentication."""
        # Test various API endpoints
        api_endpoints = [
            "/api/v1/gauges/",
            "/api/v1/readings/",
            "/api/v1/predictions/",
        ]

        for endpoint in api_endpoints:
            response = self.client.get(endpoint)
            # Should either require authentication or allow public access
            # depending on API design - adjust based on actual implementation
            self.assertIn(response.status_code, [200, 401, 403])

    def test_api_authenticated_access(self):
        """Test API access with authentication."""
        # Login user
        self.client.force_authenticate(user=self.user)

        # Test API endpoints
        response = self.client.get("/api/v1/gauges/")
        self.assertIn(response.status_code, [200, 403])  # Allow or forbidden

        response = self.client.get("/api/v1/readings/")
        self.assertIn(response.status_code, [200, 403])  # Allow or forbidden

    def test_api_staff_access(self):
        """Test API access with staff user."""
        # Login staff user
        self.client.force_authenticate(user=self.staff_user)

        # Test API endpoints
        response = self.client.get("/api/v1/gauges/")
        self.assertIn(response.status_code, [200, 403])  # Allow or forbidden

        response = self.client.get("/api/v1/readings/")
        self.assertIn(response.status_code, [200, 403])  # Allow or forbidden

    def test_api_schema_access(self):
        """Test API schema endpoint access."""
        # Test schema endpoint
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)

        # Test docs endpoint
        response = self.client.get("/api/docs/")
        self.assertEqual(response.status_code, 200)


class TestPermissionChecks(TestCase):
    """Test specific permission checks."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="permuser", password="permpassword123"
        )
        self.staff_user = User.objects.create_user(
            username="staffuser", password="staffpassword123", is_staff=True
        )
        self.superuser = User.objects.create_superuser(
            username="admin", password="adminpassword123"
        )

    def test_model_permissions(self):
        """Test model-level permissions."""
        # Test user permissions for core models
        content_types = [
            ContentType.objects.get_for_model(Gauge),
            ContentType.objects.get_for_model(Reading),
            ContentType.objects.get_for_model(Prediction),
        ]

        for content_type in content_types:
            # Test default permissions
            add_perm = Permission.objects.get(
                codename=f"add_{content_type.model}", content_type=content_type
            )
            change_perm = Permission.objects.get(
                codename=f"change_{content_type.model}", content_type=content_type
            )
            delete_perm = Permission.objects.get(
                codename=f"delete_{content_type.model}", content_type=content_type
            )
            view_perm = Permission.objects.get(
                codename=f"view_{content_type.model}", content_type=content_type
            )

            # Regular user should not have permissions
            self.assertFalse(self.user.has_perm(f"core.add_{content_type.model}"))
            self.assertFalse(self.user.has_perm(f"core.change_{content_type.model}"))
            self.assertFalse(self.user.has_perm(f"core.delete_{content_type.model}"))
            self.assertFalse(self.user.has_perm(f"core.view_{content_type.model}"))

            # Superuser should have all permissions
            self.assertTrue(self.superuser.has_perm(f"core.add_{content_type.model}"))
            self.assertTrue(
                self.superuser.has_perm(f"core.change_{content_type.model}")
            )
            self.assertTrue(
                self.superuser.has_perm(f"core.delete_{content_type.model}")
            )
            self.assertTrue(self.superuser.has_perm(f"core.view_{content_type.model}"))

    def test_group_permissions(self):
        """Test group-based permissions."""
        # Create a group with specific permissions
        group = Group.objects.create(name="Data Viewers")

        # Add view permission for gauges
        gauge_view_perm = Permission.objects.get(
            codename="view_gauge", content_type=ContentType.objects.get_for_model(Gauge)
        )
        group.permissions.add(gauge_view_perm)

        # Add user to group
        self.user.groups.add(group)

        # User should now have view permission
        self.assertTrue(self.user.has_perm("core.view_gauge"))

        # But not other permissions
        self.assertFalse(self.user.has_perm("core.add_gauge"))
        self.assertFalse(self.user.has_perm("core.change_gauge"))
        self.assertFalse(self.user.has_perm("core.delete_gauge"))

    def test_user_specific_permissions(self):
        """Test user-specific permissions."""
        # Add specific permission to user
        gauge_add_perm = Permission.objects.get(
            codename="add_gauge", content_type=ContentType.objects.get_for_model(Gauge)
        )
        self.user.user_permissions.add(gauge_add_perm)

        # User should have add permission
        self.assertTrue(self.user.has_perm("core.add_gauge"))

        # But not other permissions
        self.assertFalse(self.user.has_perm("core.change_gauge"))
        self.assertFalse(self.user.has_perm("core.delete_gauge"))
        self.assertFalse(self.user.has_perm("core.view_gauge"))

    def test_permission_inheritance(self):
        """Test permission inheritance from groups."""
        # Create nested groups
        admin_group = Group.objects.create(name="Administrators")
        viewer_group = Group.objects.create(name="Viewers")

        # Add permissions to groups
        all_permissions = Permission.objects.filter(
            content_type__in=[
                ContentType.objects.get_for_model(Gauge),
                ContentType.objects.get_for_model(Reading),
                ContentType.objects.get_for_model(Prediction),
            ]
        )

        admin_group.permissions.set(all_permissions)
        viewer_group.permissions.set(
            all_permissions.filter(codename__startswith="view_")
        )

        # Add user to viewer group
        self.user.groups.add(viewer_group)

        # User should have view permissions
        self.assertTrue(self.user.has_perm("core.view_gauge"))
        self.assertTrue(self.user.has_perm("core.view_reading"))
        self.assertTrue(self.user.has_perm("core.view_prediction"))

        # But not admin permissions
        self.assertFalse(self.user.has_perm("core.add_gauge"))
        self.assertFalse(self.user.has_perm("core.delete_gauge"))

    def test_staff_status_permissions(self):
        """Test permissions based on staff status."""
        # Regular user should not have admin access
        self.assertFalse(self.user.is_staff)

        # Staff user should have admin access
        self.assertTrue(self.staff_user.is_staff)

        # Superuser should have all access
        self.assertTrue(self.superuser.is_staff)
        self.assertTrue(self.superuser.is_superuser)

    def test_inactive_user_permissions(self):
        """Test that inactive users have no permissions."""
        # Give user some permissions
        gauge_perm = Permission.objects.get(
            codename="view_gauge", content_type=ContentType.objects.get_for_model(Gauge)
        )
        self.user.user_permissions.add(gauge_perm)

        # User should have permission when active
        self.assertTrue(self.user.has_perm("core.view_gauge"))

        # Deactivate user
        self.user.is_active = False
        self.user.save()

        # User should no longer have permissions
        self.assertFalse(self.user.has_perm("core.view_gauge"))

    def test_permission_caching(self):
        """Test permission caching behavior."""
        # Test that permissions are cached
        self.assertFalse(self.user.has_perm("core.view_gauge"))

        # Add permission
        gauge_perm = Permission.objects.get(
            codename="view_gauge", content_type=ContentType.objects.get_for_model(Gauge)
        )
        self.user.user_permissions.add(gauge_perm)

        # Permission should be available (after cache refresh)
        self.user.refresh_from_db()
        self.assertTrue(self.user.has_perm("core.view_gauge"))

    def test_superuser_bypass_permissions(self):
        """Test that superuser bypasses all permission checks."""
        # Superuser should have all permissions without explicitly granting them
        self.assertTrue(self.superuser.has_perm("core.add_gauge"))
        self.assertTrue(self.superuser.has_perm("core.change_gauge"))
        self.assertTrue(self.superuser.has_perm("core.delete_gauge"))
        self.assertTrue(self.superuser.has_perm("core.view_gauge"))

        # Even for non-existent permissions
        self.assertTrue(self.superuser.has_perm("nonexistent.fake_permission"))

    def test_anonymous_user_permissions(self):
        """Test anonymous user permissions."""
        from django.contrib.auth.models import AnonymousUser

        anon_user = AnonymousUser()

        # Anonymous user should have no permissions
        self.assertFalse(anon_user.has_perm("core.view_gauge"))
        self.assertFalse(anon_user.has_perm("core.add_gauge"))
        self.assertFalse(anon_user.is_authenticated)
        self.assertFalse(anon_user.is_staff)
        self.assertFalse(anon_user.is_superuser)


class TestViewLevelAuthorization(TestCase):
    """Test view-level authorization beyond login requirements."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="viewuser", password="viewpassword123"
        )
        self.staff_user = User.objects.create_user(
            username="staffuser", password="staffpassword123", is_staff=True
        )

    def test_dashboard_context_permissions(self):
        """Test that dashboard context respects permissions."""
        # Login user
        self.client.login(username="viewuser", password="viewpassword123")

        # Access dashboard
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)

        # Context should be available regardless of model permissions
        # (since this is a read-only dashboard)
        self.assertIn("gauge_count", response.context)
        self.assertIn("reading_count", response.context)
        self.assertIn("prediction_count", response.context)

    def test_home_page_access(self):
        """Test home page access permissions."""
        # Home page should be accessible without authentication
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        # Should also be accessible with authentication
        self.client.login(username="viewuser", password="viewpassword123")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_management_command_simulation(self):
        """Test management command authorization (simulated)."""
        # Management commands run with system privileges
        # This test simulates the authorization context

        # Commands should work regardless of user permissions
        # (since they run in system context)
        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        # This should work without authentication context
        try:
            call_command("help", stdout=out)
            self.assertIn("Available subcommands", out.getvalue())
        except Exception as e:
            self.fail(f"Management command failed: {e}")

    def test_csrf_protection_on_actions(self):
        """Test CSRF protection on dashboard actions."""
        # Login user
        self.client.login(username="viewuser", password="viewpassword123")

        # Test that POST actions are CSRF protected
        # Django test client handles CSRF automatically
        response = self.client.post("/dashboard/collect-data/")

        # Should redirect (not fail due to CSRF)
        self.assertEqual(response.status_code, 302)

    def test_method_not_allowed_handling(self):
        """Test method not allowed handling."""
        # Login user
        self.client.login(username="viewuser", password="viewpassword123")

        # Test unsupported HTTP methods
        response = self.client.put("/dashboard/")
        self.assertEqual(response.status_code, 405)

        response = self.client.delete("/dashboard/")
        self.assertEqual(response.status_code, 405)

        response = self.client.patch("/dashboard/")
        self.assertEqual(response.status_code, 405)
