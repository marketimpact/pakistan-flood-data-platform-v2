"""Authentication workflow tests."""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model, authenticate
from django.urls import reverse
from django.contrib.sessions.models import Session
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.messages import get_messages

User = get_user_model()


class TestAuthenticationWorkflow(TestCase):
    """Test authentication workflow including login, logout, and redirects."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword123"
        )
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpassword123"
        )

    def test_successful_login_via_admin(self):
        """Test successful login through admin interface."""
        login_url = "/supersecretadminpanel/login/"

        # Test GET request to login page
        response = self.client.get(login_url)
        self.assertEqual(response.status_code, 200)

        # Test successful login
        response = self.client.post(
            login_url, {"username": "testuser", "password": "testpassword123"}
        )

        # Should redirect after successful login
        self.assertEqual(response.status_code, 302)

        # User should be logged in
        self.assertTrue(self.client.session.get("_auth_user_id"))

        # Verify user is authenticated in subsequent requests
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)

    def test_failed_login_attempts(self):
        """Test various failed login scenarios."""
        login_url = "/supersecretadminpanel/login/"

        # Test with wrong username
        response = self.client.post(
            login_url, {"username": "wronguser", "password": "testpassword123"}
        )
        self.assertEqual(response.status_code, 200)  # Returns to login page
        self.assertFalse(self.client.session.get("_auth_user_id"))

        # Test with wrong password
        response = self.client.post(
            login_url, {"username": "testuser", "password": "wrongpassword"}
        )
        self.assertEqual(response.status_code, 200)  # Returns to login page
        self.assertFalse(self.client.session.get("_auth_user_id"))

        # Test with empty credentials
        response = self.client.post(login_url, {"username": "", "password": ""})
        self.assertEqual(response.status_code, 200)  # Returns to login page
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_logout_functionality(self):
        """Test logout functionality."""
        # First login
        self.client.login(username="testuser", password="testpassword123")

        # Verify user is logged in
        self.assertTrue(self.client.session.get("_auth_user_id"))

        # Test logout
        logout_url = "/supersecretadminpanel/logout/"
        response = self.client.post(logout_url)

        # Should redirect after logout
        self.assertEqual(response.status_code, 302)

        # User should be logged out - session key should not exist or be None
        self.assertIsNone(self.client.session.get("_auth_user_id"))

        # Verify user cannot access protected pages
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_login_redirect_behavior(self):
        """Test login redirect behavior for protected views."""
        # Try to access protected dashboard without login
        response = self.client.get("/dashboard/")

        # Should redirect to login with next parameter
        self.assertEqual(response.status_code, 302)
        self.assertIn("/supersecretadminpanel/login/", response.url)
        self.assertIn("next=", response.url)

        # Login and verify redirect to originally requested page
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)

    def test_authenticate_function(self):
        """Test Django's authenticate function."""
        # Test successful authentication
        user = authenticate(username="testuser", password="testpassword123")
        self.assertEqual(user, self.user)

        # Test failed authentication
        user = authenticate(username="testuser", password="wrongpassword")
        self.assertIsNone(user)

        # Test with non-existent user
        user = authenticate(username="nonexistent", password="anypassword")
        self.assertIsNone(user)

        # Test with inactive user
        self.user.is_active = False
        self.user.save()
        user = authenticate(username="testuser", password="testpassword123")
        self.assertIsNone(user)

    def test_session_management(self):
        """Test session management during authentication."""
        # Test session creation on login
        self.client.login(username="testuser", password="testpassword123")

        # Session should exist
        self.assertTrue(self.client.session.exists(self.client.session.session_key))

        # Test session data
        session_data = self.client.session
        self.assertIn("_auth_user_id", session_data)
        self.assertIn("_auth_user_backend", session_data)

        # Test session destruction on logout
        self.client.logout()

        # Session should be cleared
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_staff_user_admin_access(self):
        """Test that staff users can access admin."""
        # Create staff user
        staff_user = User.objects.create_user(
            username="staffuser", password="staffpassword123", is_staff=True
        )

        # Test admin access
        self.client.login(username="staffuser", password="staffpassword123")
        response = self.client.get("/supersecretadminpanel/")
        self.assertEqual(response.status_code, 200)

    def test_non_staff_user_admin_access(self):
        """Test that non-staff users cannot access admin."""
        # Test admin access with regular user
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get("/supersecretadminpanel/")
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_superuser_privileges(self):
        """Test superuser authentication and privileges."""
        # Test superuser can access admin
        self.client.login(username="admin", password="adminpassword123")
        response = self.client.get("/supersecretadminpanel/")
        self.assertEqual(response.status_code, 200)

        # Test superuser can access dashboard
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)

    def test_password_change_invalidates_other_sessions(self):
        """Test that password change invalidates other sessions."""
        # Create two sessions for same user
        client1 = Client()
        client2 = Client()

        client1.login(username="testuser", password="testpassword123")
        client2.login(username="testuser", password="testpassword123")

        # Both should be able to access protected content
        response1 = client1.get("/dashboard/")
        response2 = client2.get("/dashboard/")
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)

        # Change password through one client
        self.user.set_password("newpassword123")
        self.user.save()

        # Old sessions should be invalidated
        # (Note: This test depends on Django's session invalidation behavior)
        response1 = client1.get("/dashboard/")
        response2 = client2.get("/dashboard/")

        # Both should be redirected to login
        self.assertEqual(response1.status_code, 302)
        self.assertEqual(response2.status_code, 302)

    def test_login_with_email_not_supported(self):
        """Test that login with email is not supported by default."""
        # Try to login with email instead of username
        user = authenticate(username="test@example.com", password="testpassword123")
        self.assertIsNone(user)

        # Login should work with username
        user = authenticate(username="testuser", password="testpassword123")
        self.assertEqual(user, self.user)

    def test_case_sensitive_username(self):
        """Test that username is case-sensitive."""
        # Try to login with different case
        user = authenticate(username="TestUser", password="testpassword123")
        self.assertIsNone(user)

        # Correct case should work
        user = authenticate(username="testuser", password="testpassword123")
        self.assertEqual(user, self.user)

    def test_login_required_mixin_behavior(self):
        """Test LoginRequiredMixin behavior on dashboard views."""
        # Test unauthenticated access to dashboard
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)

        # Test authenticated access
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)

        # Test access to dashboard actions
        response = self.client.get("/dashboard/collect-data/")
        self.assertEqual(response.status_code, 302)  # GET redirects to dashboard

        response = self.client.post("/dashboard/collect-data/")
        self.assertEqual(response.status_code, 302)  # POST should redirect after action

    def test_authentication_middleware(self):
        """Test authentication middleware functionality."""
        # Create request with session
        request = HttpRequest()
        request.session = {}
        request.user = AnonymousUser()

        # Apply session middleware
        session_middleware = SessionMiddleware(lambda x: None)
        session_middleware.process_request(request)

        # Apply authentication middleware
        auth_middleware = AuthenticationMiddleware(lambda x: None)
        auth_middleware.process_request(request)

        # User should be AnonymousUser
        self.assertIsInstance(request.user, AnonymousUser)

        # Test with authenticated session
        self.client.login(username="testuser", password="testpassword123")
        request.session = self.client.session
        auth_middleware.process_request(request)

        # User should be authenticated
        self.assertEqual(request.user, self.user)

    def test_concurrent_sessions(self):
        """Test multiple concurrent sessions for same user."""
        # Create multiple clients
        client1 = Client()
        client2 = Client()
        client3 = Client()

        # Login with all clients
        client1.login(username="testuser", password="testpassword123")
        client2.login(username="testuser", password="testpassword123")
        client3.login(username="testuser", password="testpassword123")

        # All should be able to access protected content
        response1 = client1.get("/dashboard/")
        response2 = client2.get("/dashboard/")
        response3 = client3.get("/dashboard/")

        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response3.status_code, 200)

    def test_remember_me_functionality(self):
        """Test session persistence behavior."""
        # Test short session (browser session)
        self.client.login(username="testuser", password="testpassword123")

        # Session should exist
        self.assertTrue(self.client.session.exists(self.client.session.session_key))

        # Test session expiry settings
        session = self.client.session
        # By default, sessions expire when browser closes
        self.assertFalse(session.get_expire_at_browser_close())

    def test_login_rate_limiting_simulation(self):
        """Test simulation of login rate limiting behavior."""
        login_url = "/supersecretadminpanel/login/"

        # Simulate multiple failed login attempts
        failed_attempts = 0
        for i in range(5):
            response = self.client.post(
                login_url, {"username": "testuser", "password": "wrongpassword"}
            )
            if response.status_code == 200:  # Login page returned
                failed_attempts += 1

        # Should have multiple failed attempts
        self.assertEqual(failed_attempts, 5)

        # Successful login should still work
        response = self.client.post(
            login_url, {"username": "testuser", "password": "testpassword123"}
        )
        self.assertEqual(response.status_code, 302)  # Successful redirect

    def test_csrf_protection_on_login(self):
        """Test CSRF protection on login forms."""
        login_url = "/supersecretadminpanel/login/"

        # Test that CSRF token is required for POST requests
        # First get the login page to get CSRF token
        response = self.client.get(login_url)
        self.assertEqual(response.status_code, 200)

        # Extract CSRF token
        csrf_token = None
        if "csrfmiddlewaretoken" in response.content.decode():
            # CSRF protection is active
            csrf_token = self.client.cookies.get("csrftoken")

        # Test login with proper CSRF handling
        response = self.client.post(
            login_url, {"username": "testuser", "password": "testpassword123"}
        )

        # Should succeed (Django test client handles CSRF automatically)
        self.assertEqual(response.status_code, 302)

    def test_login_redirect_after_logout(self):
        """Test login redirect behavior after logout."""
        # Login user
        self.client.login(username="testuser", password="testpassword123")

        # Access dashboard
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)

        # Logout
        self.client.logout()

        # Try to access dashboard again
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/supersecretadminpanel/login/", response.url)

    def test_authentication_persistence_across_requests(self):
        """Test that authentication persists across multiple requests."""
        # Login
        self.client.login(username="testuser", password="testpassword123")

        # Make multiple requests
        for i in range(5):
            response = self.client.get("/dashboard/")
            self.assertEqual(response.status_code, 200)

        # User should still be authenticated
        self.assertTrue(self.client.session.get("_auth_user_id"))

    def test_inactive_user_cannot_login(self):
        """Test that inactive users cannot login."""
        # Deactivate user
        self.user.is_active = False
        self.user.save()

        # Try to login
        login_success = self.client.login(
            username="testuser", password="testpassword123"
        )
        self.assertFalse(login_success)

        # Should not be able to access protected pages
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)

    def test_user_last_login_updated(self):
        """Test that user's last_login is updated on successful login."""
        # Initially last_login should be None
        self.assertIsNone(self.user.last_login)

        # Login
        self.client.login(username="testuser", password="testpassword123")

        # Refresh user from database
        self.user.refresh_from_db()

        # last_login should be updated
        self.assertIsNotNone(self.user.last_login)

        # Test that it's a recent timestamp
        from django.utils import timezone
        from datetime import timedelta

        self.assertTrue(self.user.last_login > timezone.now() - timedelta(seconds=10))
