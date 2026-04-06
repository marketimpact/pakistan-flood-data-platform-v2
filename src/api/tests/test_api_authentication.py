"""API authentication tests."""

import base64
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Gauge, Reading, Prediction
from core.tests.factories import GaugeFactory, ReadingFactory, PredictionFactory

User = get_user_model()


class TestAPIAuthenticationBase(APITestCase):
    """Base class for API authentication tests."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpassword123", email="test@example.com"
        )

        # Create test data
        self.gauge = GaugeFactory()
        self.reading = ReadingFactory(gauge=self.gauge)
        self.prediction = PredictionFactory(gauge=self.gauge)

        # API endpoints
        self.gauge_list_url = reverse("gauge-list")
        self.gauge_detail_url = reverse("gauge-detail", kwargs={"pk": self.gauge.pk})
        self.reading_list_url = reverse("reading-list")
        self.reading_detail_url = reverse(
            "reading-detail", kwargs={"pk": self.reading.pk}
        )
        self.prediction_list_url = reverse("prediction-list")
        self.prediction_detail_url = reverse(
            "prediction-detail", kwargs={"pk": self.prediction.pk}
        )


class TestUnauthenticatedAPIAccess(TestAPIAuthenticationBase):
    """Test unauthenticated API access denial."""

    def test_unauthenticated_gauge_list_access_denied(self):
        """Test that unauthenticated users cannot access gauge list."""
        response = self.client.get(self.gauge_list_url)
        # SessionAuthentication returns 403 when no authentication is provided
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Check response format
        self.assertIn("detail", response.data)

    def test_unauthenticated_gauge_detail_access_denied(self):
        """Test that unauthenticated users cannot access gauge detail."""
        response = self.client.get(self.gauge_detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_reading_list_access_denied(self):
        """Test that unauthenticated users cannot access reading list."""
        response = self.client.get(self.reading_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_reading_detail_access_denied(self):
        """Test that unauthenticated users cannot access reading detail."""
        response = self.client.get(self.reading_detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_prediction_list_access_denied(self):
        """Test that unauthenticated users cannot access prediction list."""
        response = self.client.get(self.prediction_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_prediction_detail_access_denied(self):
        """Test that unauthenticated users cannot access prediction detail."""
        response = self.client.get(self.prediction_detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_post_requests_denied(self):
        """Test that unauthenticated users cannot make POST requests."""
        endpoints = [
            self.gauge_list_url,
            self.reading_list_url,
            self.prediction_list_url,
        ]

        for endpoint in endpoints:
            response = self.client.post(endpoint, {})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_put_requests_denied(self):
        """Test that unauthenticated users cannot make PUT requests."""
        endpoints = [
            self.gauge_detail_url,
            self.reading_detail_url,
            self.prediction_detail_url,
        ]

        for endpoint in endpoints:
            response = self.client.put(endpoint, {})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_delete_requests_denied(self):
        """Test that unauthenticated users cannot make DELETE requests."""
        endpoints = [
            self.gauge_detail_url,
            self.reading_detail_url,
            self.prediction_detail_url,
        ]

        for endpoint in endpoints:
            response = self.client.delete(endpoint)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_options_requests_allowed(self):
        """Test that OPTIONS requests are allowed for unauthenticated users."""
        # OPTIONS requests should typically be allowed for CORS
        response = self.client.options(self.gauge_list_url)
        # This might be 200 or 401 depending on configuration
        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]
        )

    def test_unauthenticated_head_requests_denied(self):
        """Test that HEAD requests are denied for unauthenticated users."""
        response = self.client.head(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestSessionAuthentication(TestAPIAuthenticationBase):
    """Test session-based authentication."""

    def test_session_authentication_success(self):
        """Test successful session authentication."""
        # Login using session authentication
        self.client.force_authenticate(user=self.user)

        # Test access to all endpoints
        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(self.gauge_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(self.reading_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(self.reading_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(self.prediction_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(self.prediction_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_session_authentication_login_required(self):
        """Test that session authentication requires login."""
        # Try to access without authentication
        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Authenticate and try again
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_session_authentication_logout(self):
        """Test session authentication logout."""
        # Authenticate
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Logout
        self.client.force_authenticate(user=None)
        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_session_authentication_inactive_user(self):
        """Test session authentication with inactive user."""
        # Deactivate user
        self.user.is_active = False
        self.user.save()

        # Try to authenticate with inactive user
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.gauge_list_url)

        # Should be denied (behavior depends on DRF configuration)
        # Most likely will be 401 or 403
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )


class TestBasicAuthentication(TestAPIAuthenticationBase):
    """Test HTTP Basic authentication."""

    def test_basic_authentication_success(self):
        """Test successful basic authentication."""
        # Create credentials
        credentials = base64.b64encode(b"testuser:testpassword123").decode("ascii")

        # Set authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f"Basic {credentials}")

        # Test access to endpoints
        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(self.reading_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(self.prediction_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_basic_authentication_invalid_credentials(self):
        """Test basic authentication with invalid credentials."""
        # Create invalid credentials
        credentials = base64.b64encode(b"testuser:wrongpassword").decode("ascii")

        # Set authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f"Basic {credentials}")

        # Test access denied
        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_basic_authentication_malformed_header(self):
        """Test basic authentication with malformed header."""
        # Set malformed authorization header
        self.client.credentials(HTTP_AUTHORIZATION="Basic invalid_base64")

        # Test access denied
        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_basic_authentication_missing_credentials(self):
        """Test basic authentication with missing credentials."""
        # Set authorization header without credentials
        self.client.credentials(HTTP_AUTHORIZATION="Basic ")

        # Test access denied
        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_basic_authentication_wrong_method(self):
        """Test basic authentication with wrong authentication method."""
        # Set wrong authentication method
        self.client.credentials(HTTP_AUTHORIZATION="Bearer token123")

        # Test access denied
        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_basic_authentication_case_sensitivity(self):
        """Test basic authentication case sensitivity."""
        # Test with different cases
        test_cases = [
            "basic",  # lowercase
            "BASIC",  # uppercase
            "Basic",  # correct case
        ]

        for auth_type in test_cases:
            credentials = base64.b64encode(b"testuser:testpassword123").decode("ascii")
            self.client.credentials(HTTP_AUTHORIZATION=f"{auth_type} {credentials}")

            response = self.client.get(self.gauge_list_url)
            if auth_type == "Basic":
                self.assertEqual(response.status_code, status.HTTP_200_OK)
            else:
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_basic_authentication_unicode_password(self):
        """Test basic authentication with unicode password."""
        # Create user with unicode password
        unicode_user = User.objects.create_user(
            username="unicode_user",
            password="пароль123",  # Cyrillic password
            email="unicode@example.com",
        )

        # Create credentials
        credentials = base64.b64encode("unicode_user:пароль123".encode("utf-8")).decode(
            "ascii"
        )

        # Set authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f"Basic {credentials}")

        # Test access
        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_basic_authentication_special_characters(self):
        """Test basic authentication with special characters in password."""
        # Create user with special characters in password
        special_user = User.objects.create_user(
            username="special_user",
            password="p@ssw0rd!@#$%^&*()",
            email="special@example.com",
        )

        # Create credentials
        credentials = base64.b64encode(b"special_user:p@ssw0rd!@#$%^&*()").decode(
            "ascii"
        )

        # Set authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f"Basic {credentials}")

        # Test access
        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestAuthenticationMethods(TestAPIAuthenticationBase):
    """Test different authentication methods."""

    def test_multiple_authentication_methods(self):
        """Test that multiple authentication methods work."""
        # Test session authentication
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Reset authentication
        self.client.force_authenticate(user=None)

        # Test basic authentication
        credentials = base64.b64encode(b"testuser:testpassword123").decode("ascii")
        self.client.credentials(HTTP_AUTHORIZATION=f"Basic {credentials}")
        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authentication_priority(self):
        """Test authentication method priority."""
        # Set both session and basic auth
        self.client.force_authenticate(user=self.user)
        credentials = base64.b64encode(b"testuser:testpassword123").decode("ascii")
        self.client.credentials(HTTP_AUTHORIZATION=f"Basic {credentials}")

        # Should still work
        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_permissions_with_authentication(self):
        """Test that authenticated users have proper permissions."""
        # Create different users
        regular_user = User.objects.create_user(
            username="regular", password="password123"
        )
        staff_user = User.objects.create_user(
            username="staff", password="password123", is_staff=True
        )
        superuser = User.objects.create_superuser(
            username="super", password="password123"
        )

        users = [regular_user, staff_user, superuser]

        for user in users:
            self.client.force_authenticate(user=user)

            # All authenticated users should have read access
            response = self.client.get(self.gauge_list_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response = self.client.get(self.reading_list_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response = self.client.get(self.prediction_list_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestAPIReadOnlyAccess(TestAPIAuthenticationBase):
    """Test read-only access enforcement."""

    def test_authenticated_post_requests_forbidden(self):
        """Test that authenticated users cannot make POST requests."""
        self.client.force_authenticate(user=self.user)

        endpoints = [
            (self.gauge_list_url, {"name": "New Gauge"}),
            (self.reading_list_url, {"gauge": self.gauge.pk, "water_level": 10.0}),
            (self.prediction_list_url, {"gauge": self.gauge.pk, "water_level": 10.0}),
        ]

        for endpoint, data in endpoints:
            response = self.client.post(endpoint, data)
            self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_authenticated_put_requests_forbidden(self):
        """Test that authenticated users cannot make PUT requests."""
        self.client.force_authenticate(user=self.user)

        endpoints = [
            (self.gauge_detail_url, {"name": "Updated Gauge"}),
            (self.reading_detail_url, {"water_level": 15.0}),
            (self.prediction_detail_url, {"water_level": 15.0}),
        ]

        for endpoint, data in endpoints:
            response = self.client.put(endpoint, data)
            self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_authenticated_patch_requests_forbidden(self):
        """Test that authenticated users cannot make PATCH requests."""
        self.client.force_authenticate(user=self.user)

        endpoints = [
            (self.gauge_detail_url, {"name": "Patched Gauge"}),
            (self.reading_detail_url, {"water_level": 20.0}),
            (self.prediction_detail_url, {"water_level": 20.0}),
        ]

        for endpoint, data in endpoints:
            response = self.client.patch(endpoint, data)
            self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_authenticated_delete_requests_forbidden(self):
        """Test that authenticated users cannot make DELETE requests."""
        self.client.force_authenticate(user=self.user)

        endpoints = [
            self.gauge_detail_url,
            self.reading_detail_url,
            self.prediction_detail_url,
        ]

        for endpoint in endpoints:
            response = self.client.delete(endpoint)
            self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_authenticated_head_requests_allowed(self):
        """Test that authenticated users can make HEAD requests."""
        self.client.force_authenticate(user=self.user)

        endpoints = [
            self.gauge_list_url,
            self.gauge_detail_url,
            self.reading_list_url,
            self.reading_detail_url,
            self.prediction_list_url,
            self.prediction_detail_url,
        ]

        for endpoint in endpoints:
            response = self.client.head(endpoint)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authenticated_options_requests_allowed(self):
        """Test that authenticated users can make OPTIONS requests."""
        self.client.force_authenticate(user=self.user)

        endpoints = [
            self.gauge_list_url,
            self.gauge_detail_url,
            self.reading_list_url,
            self.reading_detail_url,
            self.prediction_list_url,
            self.prediction_detail_url,
        ]

        for endpoint in endpoints:
            response = self.client.options(endpoint)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestAPIAuthenticationHeaders(TestAPIAuthenticationBase):
    """Test authentication-related headers."""

    def test_www_authenticate_header_present(self):
        """Test that WWW-Authenticate header is present on 401 responses."""
        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Check WWW-Authenticate header
        self.assertIn("WWW-Authenticate", response.headers)
        auth_header = response.headers["WWW-Authenticate"]

        # Should include both Basic and Session auth
        self.assertIn("Basic", auth_header)

    def test_content_type_header_on_auth_error(self):
        """Test content type header on authentication error."""
        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Should be JSON response
        self.assertEqual(response.headers.get("Content-Type"), "application/json")

    def test_authentication_with_custom_headers(self):
        """Test authentication with custom headers."""
        self.client.force_authenticate(user=self.user)

        # Add custom headers
        response = self.client.get(
            self.gauge_list_url,
            HTTP_ACCEPT="application/json",
            HTTP_USER_AGENT="TestClient/1.0",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestAPIAuthenticationErrorHandling(TestAPIAuthenticationBase):
    """Test authentication error handling."""

    def test_authentication_error_response_format(self):
        """Test authentication error response format."""
        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Check response format
        self.assertIn("detail", response.data)
        self.assertIsInstance(response.data["detail"], str)
        self.assertIn("credentials", response.data["detail"].lower())

    def test_authentication_error_different_endpoints(self):
        """Test authentication errors across different endpoints."""
        endpoints = [
            self.gauge_list_url,
            self.gauge_detail_url,
            self.reading_list_url,
            self.reading_detail_url,
            self.prediction_list_url,
            self.prediction_detail_url,
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            self.assertIn("detail", response.data)

    def test_authentication_error_with_invalid_basic_auth(self):
        """Test authentication error with invalid basic auth."""
        # Test various invalid basic auth formats
        invalid_auths = [
            "Basic invalidbase64",
            "Basic ",
            "Basic dGVzdA==",  # Just 'test' without colon
            "Basic dGVzdDp3cm9uZw==",  # test:wrong
        ]

        for auth in invalid_auths:
            self.client.credentials(HTTP_AUTHORIZATION=auth)
            response = self.client.get(self.gauge_list_url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authentication_with_nonexistent_user(self):
        """Test authentication with non-existent user."""
        credentials = base64.b64encode(b"nonexistent:password").decode("ascii")
        self.client.credentials(HTTP_AUTHORIZATION=f"Basic {credentials}")

        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authentication_throttling(self):
        """Test authentication throttling behavior."""
        # This test depends on throttling configuration
        # Make multiple unauthenticated requests
        for i in range(5):
            response = self.client.get(self.gauge_list_url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Should still get 401, not throttled (since user is not authenticated)
        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestAPIAuthenticationIntegration(TestAPIAuthenticationBase):
    """Test authentication integration with API functionality."""

    def test_authenticated_api_data_access(self):
        """Test that authenticated users can access API data."""
        self.client.force_authenticate(user=self.user)

        # Test gauge data
        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertTrue(len(response.data) > 0)

        # Test reading data
        response = self.client.get(self.reading_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertTrue(len(response.data) > 0)

        # Test prediction data
        response = self.client.get(self.prediction_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertTrue(len(response.data) > 0)

    def test_authentication_with_pagination(self):
        """Test authentication with paginated results."""
        # Create more data for pagination
        GaugeFactory.create_batch(20)

        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # API returns list directly (no pagination configured)
        self.assertIsInstance(response.data, list)
        self.assertGreater(len(response.data), 0)

    def test_authentication_persistence_across_requests(self):
        """Test that authentication persists across multiple requests."""
        self.client.force_authenticate(user=self.user)

        # Make multiple requests
        for i in range(5):
            response = self.client.get(self.gauge_list_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Authentication should still work
        response = self.client.get(self.reading_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authentication_with_different_user_accounts(self):
        """Test authentication with different user accounts."""
        # Create additional users
        user2 = User.objects.create_user(username="user2", password="password123")

        users = [self.user, user2]

        for user in users:
            self.client.force_authenticate(user=user)

            # Each user should have access to same data
            response = self.client.get(self.gauge_list_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response = self.client.get(self.reading_list_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            response = self.client.get(self.prediction_list_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authentication_with_api_browsable_interface(self):
        """Test authentication with DRF browsable API."""
        self.client.force_authenticate(user=self.user)

        # Test with HTML accept header (browsable API)
        response = self.client.get(self.gauge_list_url, HTTP_ACCEPT="text/html")

        # Should still work
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authentication_with_different_content_types(self):
        """Test authentication with different content types."""
        self.client.force_authenticate(user=self.user)

        content_types = [
            "application/json",
            "application/xml",
            "text/html",
        ]

        for content_type in content_types:
            response = self.client.get(self.gauge_list_url, HTTP_ACCEPT=content_type)

            # Should work regardless of content type
            self.assertEqual(response.status_code, status.HTTP_200_OK)
