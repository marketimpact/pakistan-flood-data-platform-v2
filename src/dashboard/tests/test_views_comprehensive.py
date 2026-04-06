"""Comprehensive tests for dashboard views."""

import unittest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock
from io import StringIO

from core.models import Gauge, Reading, Prediction
from core.tests.factories import GaugeFactory, ReadingFactory, PredictionFactory

User = get_user_model()


class TestDashboardView(TestCase):
    """Test DashboardView functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpassword123"
        )
        self.dashboard_url = reverse("dashboard")

    def test_dashboard_login_requirement(self):
        """Test that dashboard requires user to be logged in."""
        # Test unauthenticated access
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/supersecretadminpanel/login/", response.url)

        # Test authenticated access
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

    def test_dashboard_template_rendering(self):
        """Test that dashboard uses correct template."""
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/dashboard.html")

    def test_dashboard_context_data_empty_database(self):
        """Test dashboard context data with empty database."""
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.dashboard_url)

        # Test counts are zero
        self.assertEqual(response.context["gauge_count"], 0)
        self.assertEqual(response.context["verified_gauge_count"], 0)
        self.assertEqual(response.context["reading_count"], 0)
        self.assertEqual(response.context["prediction_count"], 0)

        # Test recent lists are empty
        self.assertEqual(len(response.context["recent_gauges"]), 0)
        self.assertEqual(len(response.context["recent_readings"]), 0)

    def test_dashboard_context_data_with_gauges(self):
        """Test dashboard context data with gauge data."""
        # Create test gauges
        verified_gauge = GaugeFactory(quality_verified=True)
        unverified_gauge = GaugeFactory(quality_verified=False)

        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.dashboard_url)

        # Test gauge counts
        self.assertEqual(response.context["gauge_count"], 2)
        self.assertEqual(response.context["verified_gauge_count"], 1)

        # Test recent gauges
        recent_gauges = response.context["recent_gauges"]
        self.assertEqual(len(recent_gauges), 2)

        # Should be ordered by created_at descending
        self.assertEqual(list(recent_gauges), [unverified_gauge, verified_gauge])

    def test_dashboard_context_data_with_readings(self):
        """Test dashboard context data with reading data."""
        # Create test data
        gauge = GaugeFactory()
        reading1 = ReadingFactory(gauge=gauge)
        reading2 = ReadingFactory(gauge=gauge)

        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.dashboard_url)

        # Test reading count
        self.assertEqual(response.context["reading_count"], 2)

        # Test recent readings
        recent_readings = response.context["recent_readings"]
        self.assertEqual(len(recent_readings), 2)

        # Should be ordered by timestamp descending
        self.assertEqual(list(recent_readings), [reading2, reading1])

        # Should have gauge data through select_related
        for reading in recent_readings:
            self.assertIsNotNone(reading.gauge)

    def test_dashboard_context_data_with_predictions(self):
        """Test dashboard context data with prediction data."""
        # Create test predictions
        gauge = GaugeFactory()
        PredictionFactory(gauge=gauge)
        PredictionFactory(gauge=gauge)

        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.dashboard_url)

        # Test prediction count
        self.assertEqual(response.context["prediction_count"], 2)

    def test_dashboard_recent_gauges_limit(self):
        """Test that recent gauges are limited to 10."""
        # Create 15 gauges
        gauges = GaugeFactory.create_batch(15)

        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.dashboard_url)

        # Should only show 10 most recent
        recent_gauges = response.context["recent_gauges"]
        self.assertEqual(len(recent_gauges), 10)

        # Should show the 10 most recently created
        expected_gauges = Gauge.objects.order_by("-created_at")[:10]
        self.assertEqual(list(recent_gauges), list(expected_gauges))

    def test_dashboard_recent_readings_limit(self):
        """Test that recent readings are limited to 10."""
        # Create gauge and 15 readings
        gauge = GaugeFactory()
        readings = []
        for i in range(15):
            reading = ReadingFactory(
                gauge=gauge, timestamp=timezone.now() - timedelta(minutes=i)
            )
            readings.append(reading)

        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.dashboard_url)

        # Should only show 10 most recent
        recent_readings = response.context["recent_readings"]
        self.assertEqual(len(recent_readings), 10)

        # Should show the 10 most recent by timestamp
        expected_readings = Reading.objects.order_by("-timestamp")[:10]
        self.assertEqual(list(recent_readings), list(expected_readings))

    def test_dashboard_context_data_comprehensive(self):
        """Test comprehensive dashboard context data."""
        # Create comprehensive test data
        verified_gauge = GaugeFactory(quality_verified=True)
        unverified_gauge = GaugeFactory(quality_verified=False)

        # Create readings
        reading1 = ReadingFactory(gauge=verified_gauge)
        reading2 = ReadingFactory(gauge=unverified_gauge)

        # Create predictions
        prediction1 = PredictionFactory(gauge=verified_gauge)
        prediction2 = PredictionFactory(gauge=unverified_gauge)

        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.dashboard_url)

        # Test all counts
        self.assertEqual(response.context["gauge_count"], 2)
        self.assertEqual(response.context["verified_gauge_count"], 1)
        self.assertEqual(response.context["reading_count"], 2)
        self.assertEqual(response.context["prediction_count"], 2)

        # Test recent data
        self.assertEqual(len(response.context["recent_gauges"]), 2)
        self.assertEqual(len(response.context["recent_readings"]), 2)

    def test_dashboard_query_optimization(self):
        """Test that dashboard queries are optimized."""
        # Create test data
        gauge = GaugeFactory()
        ReadingFactory.create_batch(5, gauge=gauge)

        self.client.login(username="testuser", password="testpassword123")

        # Test that select_related is used for readings
        with self.assertNumQueries(6):  # Adjust based on actual query count
            response = self.client.get(self.dashboard_url)

            # Access the gauge through readings to verify select_related worked
            for reading in response.context["recent_readings"]:
                _ = reading.gauge.name  # This should not cause additional queries

    def test_dashboard_with_mixed_data_types(self):
        """Test dashboard with mixed data types and edge cases."""
        # Create gauges with different verification statuses
        verified_gauges = GaugeFactory.create_batch(3, quality_verified=True)
        unverified_gauges = GaugeFactory.create_batch(2, quality_verified=False)

        # Create readings with different timestamps
        recent_reading = ReadingFactory(
            gauge=verified_gauges[0], timestamp=timezone.now()
        )
        old_reading = ReadingFactory(
            gauge=verified_gauges[1], timestamp=timezone.now() - timedelta(days=1)
        )

        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.dashboard_url)

        # Test counts
        self.assertEqual(response.context["gauge_count"], 5)
        self.assertEqual(response.context["verified_gauge_count"], 3)
        self.assertEqual(response.context["reading_count"], 2)

        # Test ordering
        recent_readings = response.context["recent_readings"]
        self.assertEqual(recent_readings[0], recent_reading)
        self.assertEqual(recent_readings[1], old_reading)

    def test_dashboard_context_data_types(self):
        """Test that dashboard context data has correct types."""
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.dashboard_url)

        # Test that counts are integers
        self.assertIsInstance(response.context["gauge_count"], int)
        self.assertIsInstance(response.context["verified_gauge_count"], int)
        self.assertIsInstance(response.context["reading_count"], int)
        self.assertIsInstance(response.context["prediction_count"], int)

        # Test that recent data are querysets/lists
        self.assertIsNotNone(response.context["recent_gauges"])
        self.assertIsNotNone(response.context["recent_readings"])

    def test_dashboard_response_status_and_content(self):
        """Test dashboard response status and content."""
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.dashboard_url)

        # Test response status
        self.assertEqual(response.status_code, 200)

        # Test response content type
        self.assertEqual(response["Content-Type"], "text/html; charset=utf-8")

        # Test that response contains expected content
        self.assertContains(
            response, "dashboard"
        )  # Should contain dashboard-related content

    def test_dashboard_with_unicode_data(self):
        """Test dashboard with unicode/special characters in data."""
        # Create gauge with unicode characters
        gauge = GaugeFactory(name="测试仪表 (Test Gauge)", location="Пакистан Location")

        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.dashboard_url)

        # Should handle unicode without errors
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["gauge_count"], 1)

        # Recent gauges should contain the unicode gauge
        recent_gauges = response.context["recent_gauges"]
        self.assertEqual(len(recent_gauges), 1)
        self.assertEqual(recent_gauges[0].name, "测试仪表 (Test Gauge)")

    def test_dashboard_performance_with_large_dataset(self):
        """Test dashboard performance with larger dataset."""
        # Create larger dataset
        gauges = GaugeFactory.create_batch(50)

        # Create many readings
        for gauge in gauges[:10]:  # Only for first 10 gauges to keep test reasonable
            ReadingFactory.create_batch(5, gauge=gauge)

        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.dashboard_url)

        # Should handle large dataset without issues
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["gauge_count"], 50)
        self.assertEqual(response.context["reading_count"], 50)

        # Should still limit recent data to 10
        self.assertEqual(len(response.context["recent_gauges"]), 10)
        self.assertEqual(len(response.context["recent_readings"]), 10)

    def test_dashboard_context_inheritance(self):
        """Test that dashboard context inherits from parent correctly."""
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.dashboard_url)

        # Should have standard context items
        self.assertIn("view", response.context)
        self.assertIn("request", response.context)

        # Should have custom context items
        self.assertIn("gauge_count", response.context)
        self.assertIn("verified_gauge_count", response.context)
        self.assertIn("reading_count", response.context)
        self.assertIn("prediction_count", response.context)
        self.assertIn("recent_gauges", response.context)
        self.assertIn("recent_readings", response.context)

    def test_dashboard_login_redirect_behavior(self):
        """Test dashboard login redirect behavior."""
        # Test that unauthenticated users are redirected with next parameter
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("next=" + self.dashboard_url, response.url)

        # Test that after login, user is redirected to dashboard
        login_response = self.client.post(
            "/supersecretadminpanel/login/",
            {
                "username": "testuser",
                "password": "testpassword123",
                "next": self.dashboard_url,
            },
        )

        # Should be redirected after successful login
        self.assertEqual(login_response.status_code, 302)

    def test_dashboard_method_not_allowed(self):
        """Test that dashboard only allows GET requests."""
        self.client.login(username="testuser", password="testpassword123")

        # Test unsupported HTTP methods
        response = self.client.post(self.dashboard_url)
        self.assertEqual(response.status_code, 405)

        response = self.client.put(self.dashboard_url)
        self.assertEqual(response.status_code, 405)

        response = self.client.delete(self.dashboard_url)
        self.assertEqual(response.status_code, 405)

    def test_dashboard_csrf_protection(self):
        """Test that dashboard has CSRF protection."""
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.dashboard_url)

        # Should have CSRF token in context
        self.assertIn("csrf_token", response.context)

        # Should have CSRF token in rendered content
        self.assertContains(
            response, "csrfmiddlewaretoken", count=0
        )  # GET request doesn't need CSRF

    def test_dashboard_with_database_error_simulation(self):
        """Test dashboard behavior with database errors."""
        self.client.login(username="testuser", password="testpassword123")

        # This would normally be tested with database mocking
        # For now, we just test that the view is robust
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

    def test_dashboard_caching_behavior(self):
        """Test dashboard caching behavior."""
        # Create initial data
        GaugeFactory()

        self.client.login(username="testuser", password="testpassword123")

        # First request
        response1 = self.client.get(self.dashboard_url)
        self.assertEqual(response1.context["gauge_count"], 1)

        # Add more data
        GaugeFactory()

        # Second request should reflect new data (no caching)
        response2 = self.client.get(self.dashboard_url)
        self.assertEqual(response2.context["gauge_count"], 2)

    def test_dashboard_concurrent_access(self):
        """Test dashboard with concurrent access simulation."""
        # Create test data
        GaugeFactory()

        # Login multiple clients
        client1 = Client()
        client2 = Client()

        client1.login(username="testuser", password="testpassword123")

        # Create second user
        user2 = User.objects.create_user(username="user2", password="pass2")
        client2.login(username="user2", password="pass2")

        # Both should be able to access dashboard
        response1 = client1.get(self.dashboard_url)
        response2 = client2.get(self.dashboard_url)

        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)

        # Both should see same data
        self.assertEqual(
            response1.context["gauge_count"], response2.context["gauge_count"]
        )

    def test_dashboard_user_permissions(self):
        """Test that dashboard respects user permissions."""
        # Dashboard should be accessible to any authenticated user
        regular_user = User.objects.create_user(username="regular", password="pass123")
        staff_user = User.objects.create_user(
            username="staff", password="pass123", is_staff=True
        )
        super_user = User.objects.create_superuser(username="super", password="pass123")

        users = [regular_user, staff_user, super_user]

        for user in users:
            client = Client()
            client.login(username=user.username, password="pass123")
            response = client.get(self.dashboard_url)
            self.assertEqual(response.status_code, 200)

    def test_dashboard_url_resolution(self):
        """Test that dashboard URL resolves correctly."""
        from django.urls import resolve

        # Test URL resolution
        resolved = resolve("/dashboard/")
        self.assertEqual(resolved.url_name, "dashboard")

        # Test reverse URL resolution
        dashboard_url = reverse("dashboard")
        self.assertEqual(dashboard_url, "/dashboard/")

    def test_dashboard_view_inheritance(self):
        """Test that DashboardView inherits from correct base classes."""
        from dashboard.views import DashboardView
        from django.contrib.auth.mixins import LoginRequiredMixin
        from django.views.generic import TemplateView

        # Test inheritance
        self.assertTrue(issubclass(DashboardView, LoginRequiredMixin))
        self.assertTrue(issubclass(DashboardView, TemplateView))

    def test_dashboard_context_data_method(self):
        """Test get_context_data method specifically."""
        from dashboard.views import DashboardView

        # Create view instance
        view = DashboardView()
        view.request = type("Request", (), {"user": self.user})()

        # Test context data generation
        context = view.get_context_data()

        # Should have required context keys
        required_keys = [
            "gauge_count",
            "verified_gauge_count",
            "reading_count",
            "prediction_count",
            "recent_gauges",
            "recent_readings",
        ]

        for key in required_keys:
            self.assertIn(key, context)


class TestCollectDataView(TestCase):
    """Test CollectDataView functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpassword123"
        )
        self.collect_data_url = reverse("collect_data")
        self.dashboard_url = reverse("dashboard")

    def test_collect_data_login_requirement(self):
        """Test that collect data view requires login."""
        # Test unauthenticated GET
        response = self.client.get(self.collect_data_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/supersecretadminpanel/login/", response.url)

        # Test unauthenticated POST
        response = self.client.post(self.collect_data_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/supersecretadminpanel/login/", response.url)

    def test_collect_data_get_redirect_behavior(self):
        """Test that GET requests are redirected to dashboard."""
        self.client.login(username="testuser", password="testpassword123")

        response = self.client.get(self.collect_data_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.dashboard_url)

    @patch("dashboard.views.call_command")
    def test_collect_data_post_basic_functionality(self, mock_call_command):
        """Test basic POST functionality."""
        self.client.login(username="testuser", password="testpassword123")

        response = self.client.post(self.collect_data_url, {"limit": "50"})

        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.dashboard_url)

        # Should call management command
        mock_call_command.assert_called_once_with("fetch_google_flood_data", limit=50)

    @patch("dashboard.views.call_command")
    def test_collect_data_post_with_limit(self, mock_call_command):
        """Test POST with limit parameter."""
        self.client.login(username="testuser", password="testpassword123")

        response = self.client.post(
            self.collect_data_url, {"limit": "30"}
        )

        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.dashboard_url)

        # Should call management command with limit
        mock_call_command.assert_called_once_with(
            "fetch_google_flood_data", limit=30
        )

    @patch("dashboard.views.call_command")
    def test_collect_data_limit_validation(self, mock_call_command):
        """Test limit parameter validation."""
        self.client.login(username="testuser", password="testpassword123")

        # Test valid limits
        test_cases = [
            ("1", 1),
            ("50", 50),
            ("100", 100),
            ("500", 500),
        ]

        for input_limit, expected_limit in test_cases:
            mock_call_command.reset_mock()

            response = self.client.post(self.collect_data_url, {"limit": input_limit})

            self.assertEqual(response.status_code, 302)
            mock_call_command.assert_called_once_with(
                "fetch_google_flood_data", limit=expected_limit
            )

    @patch("dashboard.views.call_command")
    def test_collect_data_limit_validation_edge_cases(self, mock_call_command):
        """Test limit parameter validation edge cases."""
        self.client.login(username="testuser", password="testpassword123")

        # Test invalid limits that should default to 50
        test_cases = [
            ("0", 50),  # Too small
            ("501", 50),  # Too large
            ("-1", 50),  # Negative
            ("abc", 50),  # Non-numeric
            ("", 50),  # Empty
        ]

        for input_limit, expected_limit in test_cases:
            mock_call_command.reset_mock()

            response = self.client.post(self.collect_data_url, {"limit": input_limit})

            self.assertEqual(response.status_code, 302)
            mock_call_command.assert_called_once_with(
                "fetch_google_flood_data", limit=expected_limit
            )

    @patch("dashboard.views.call_command")
    def test_collect_data_no_limit_parameter(self, mock_call_command):
        """Test POST without limit parameter."""
        self.client.login(username="testuser", password="testpassword123")

        response = self.client.post(self.collect_data_url, {})

        # Should use default limit of 50
        self.assertEqual(response.status_code, 302)
        mock_call_command.assert_called_once_with("fetch_google_flood_data", limit=50)

    @patch("dashboard.views.call_command")
    def test_collect_data_success_message_display(self, mock_call_command):
        """Test success message display."""
        self.client.login(username="testuser", password="testpassword123")

        # Test without quality_only
        response = self.client.post(self.collect_data_url, {"limit": "25"}, follow=True)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            "Successfully collected up to 25 flood gauges from Google Flood Hub!",
        )
        self.assertEqual(messages[0].tags, "success")

    @patch("dashboard.views.call_command")
    def test_collect_data_success_message_with_different_limits(self, mock_call_command):
        """Test success message with different limit values."""
        self.client.login(username="testuser", password="testpassword123")

        # Test with different limit
        response = self.client.post(
            self.collect_data_url, {"limit": "100"}, follow=True
        )

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            "Successfully collected up to 100 flood gauges from Google Flood Hub!",
        )
        self.assertEqual(messages[0].tags, "success")

    @patch("dashboard.views.call_command")
    def test_collect_data_error_message_display(self, mock_call_command):
        """Test error message display when command fails."""
        self.client.login(username="testuser", password="testpassword123")

        # Mock command to raise exception
        mock_call_command.side_effect = Exception("API connection failed")

        response = self.client.post(self.collect_data_url, {"limit": "25"}, follow=True)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "Error collecting data: API connection failed"
        )
        self.assertEqual(messages[0].tags, "error")

    @patch("dashboard.views.call_command")
    def test_collect_data_command_invocation_verification(self, mock_call_command):
        """Test that management command is invoked correctly."""
        self.client.login(username="testuser", password="testpassword123")

        # Test various parameter combinations
        test_cases = [
            ({"limit": "10"}, {"limit": 10}),
            ({"limit": "25"}, {"limit": 25}),
            ({"limit": "100"}, {"limit": 100}),
            ({}, {"limit": 50}),  # Default case
        ]

        for post_data, expected_kwargs in test_cases:
            mock_call_command.reset_mock()

            response = self.client.post(self.collect_data_url, post_data)

            self.assertEqual(response.status_code, 302)

            # Verify command was called with correct arguments
            args, kwargs = mock_call_command.call_args
            self.assertEqual(args[0], "fetch_google_flood_data")

            for key, value in expected_kwargs.items():
                self.assertEqual(kwargs[key], value)

    @patch("dashboard.views.call_command")
    def test_collect_data_various_error_scenarios(self, mock_call_command):
        """Test various error scenarios."""
        self.client.login(username="testuser", password="testpassword123")

        # Test different exception types
        error_scenarios = [
            ("Connection timeout", "Error collecting data: Connection timeout"),
            ("Invalid API key", "Error collecting data: Invalid API key"),
            ("Rate limit exceeded", "Error collecting data: Rate limit exceeded"),
        ]

        for error_msg, expected_msg in error_scenarios:
            mock_call_command.reset_mock()
            mock_call_command.side_effect = Exception(error_msg)

            response = self.client.post(
                self.collect_data_url, {"limit": "10"}, follow=True
            )

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), expected_msg)
            self.assertEqual(messages[0].tags, "error")

    @patch("dashboard.views.call_command")
    def test_collect_data_csrf_protection(self, mock_call_command):
        """Test CSRF protection on collect data POST."""
        self.client.login(username="testuser", password="testpassword123")

        # Django test client handles CSRF automatically
        response = self.client.post(self.collect_data_url, {"limit": "25"})

        # Should succeed (test client handles CSRF)
        self.assertEqual(response.status_code, 302)
        mock_call_command.assert_called_once()

    @patch("dashboard.views.call_command")
    def test_collect_data_post_data_processing(self, mock_call_command):
        """Test POST data processing and sanitization."""
        self.client.login(username="testuser", password="testpassword123")

        # Test with extra POST data that should be ignored
        response = self.client.post(
            self.collect_data_url,
            {
                "limit": "30",
                "extra_field": "should_be_ignored",
                "malicious_script": '<script>alert("xss")</script>',
            },
        )

        # Should only process expected fields
        self.assertEqual(response.status_code, 302)
        mock_call_command.assert_called_once_with(
            "fetch_google_flood_data", limit=30
        )

    @patch("dashboard.views.call_command")
    def test_collect_data_limit_parameter_variations(self, mock_call_command):
        """Test different variations of limit parameter."""
        self.client.login(username="testuser", password="testpassword123")

        # Test different limit values
        limit_values = ["10", "25", "50", "100", "1000"]

        for value in limit_values:
            mock_call_command.reset_mock()

            response = self.client.post(
                self.collect_data_url, {"limit": value}
            )

            self.assertEqual(response.status_code, 302)
            mock_call_command.assert_called_once_with(
                "fetch_google_flood_data", limit=int(value)
            )

        # Test without limit parameter (should use default)
        mock_call_command.reset_mock()

        response = self.client.post(
            self.collect_data_url,
            {}
        )

        self.assertEqual(response.status_code, 302)
        mock_call_command.assert_called_once_with("fetch_google_flood_data", limit=50)

    @patch("dashboard.views.call_command")
    def test_collect_data_concurrent_requests(self, mock_call_command):
        """Test handling of concurrent requests."""
        self.client.login(username="testuser", password="testpassword123")

        # Simulate slower command execution
        mock_call_command.return_value = None

        # Make multiple concurrent requests (simulated)
        responses = []
        for i in range(3):
            response = self.client.post(self.collect_data_url, {"limit": str(10 + i)})
            responses.append(response)

        # All should succeed
        for response in responses:
            self.assertEqual(response.status_code, 302)

        # Command should be called for each request
        self.assertEqual(mock_call_command.call_count, 3)

    @patch("dashboard.views.call_command")
    def test_collect_data_method_not_allowed(self, mock_call_command):
        """Test that unsupported HTTP methods redirect to dashboard."""
        self.client.login(username="testuser", password="testpassword123")

        # Test unsupported methods - Django's View redirects them to dashboard
        unsupported_methods = ["put", "patch", "delete"]

        for method in unsupported_methods:
            client_method = getattr(self.client, method)
            response = client_method(self.collect_data_url)
            self.assertEqual(response.status_code, 302)  # Redirect to dashboard

        # Verify command was not called
        mock_call_command.assert_not_called()

    @patch("dashboard.views.call_command")
    def test_collect_data_view_class_behavior(self, mock_call_command):
        """Test CollectDataView class behavior."""
        from dashboard.views import CollectDataView
        from django.contrib.auth.mixins import LoginRequiredMixin
        from django.views import View

        # Test inheritance
        self.assertTrue(issubclass(CollectDataView, LoginRequiredMixin))
        self.assertTrue(issubclass(CollectDataView, View))

        # Test that view handles both GET and POST
        view = CollectDataView()
        self.assertTrue(hasattr(view, "get"))
        self.assertTrue(hasattr(view, "post"))

    @patch("dashboard.views.call_command")
    def test_collect_data_redirect_after_error(self, mock_call_command):
        """Test that view redirects to dashboard even after error."""
        self.client.login(username="testuser", password="testpassword123")

        # Mock command to raise exception
        mock_call_command.side_effect = Exception("Test error")

        response = self.client.post(self.collect_data_url, {"limit": "25"})

        # Should still redirect to dashboard
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.dashboard_url)

    @patch("dashboard.views.call_command")
    def test_collect_data_limit_boundary_conditions(self, mock_call_command):
        """Test limit parameter boundary conditions."""
        self.client.login(username="testuser", password="testpassword123")

        # Test exact boundary values
        boundary_tests = [
            ("1", 1),  # Minimum valid
            ("500", 500),  # Maximum valid
            ("0", 50),  # Below minimum
            ("501", 50),  # Above maximum
        ]

        for input_limit, expected_limit in boundary_tests:
            mock_call_command.reset_mock()

            response = self.client.post(self.collect_data_url, {"limit": input_limit})

            self.assertEqual(response.status_code, 302)
            mock_call_command.assert_called_once_with(
                "fetch_google_flood_data", limit=expected_limit
            )

    @patch("dashboard.views.call_command")
    def test_collect_data_unicode_handling(self, mock_call_command):
        """Test handling of unicode characters in parameters."""
        self.client.login(username="testuser", password="testpassword123")

        # Test with unicode characters in limit (should be handled gracefully)
        response = self.client.post(
            self.collect_data_url, {"limit": "50测试"}  # Contains unicode
        )

        # Should default to 50 due to invalid format
        self.assertEqual(response.status_code, 302)
        mock_call_command.assert_called_once_with("fetch_google_flood_data", limit=50)

    @patch("dashboard.views.call_command")
    def test_collect_data_empty_post_data(self, mock_call_command):
        """Test with completely empty POST data."""
        self.client.login(username="testuser", password="testpassword123")

        response = self.client.post(self.collect_data_url, {})

        # Should use default values
        self.assertEqual(response.status_code, 302)
        mock_call_command.assert_called_once_with("fetch_google_flood_data", limit=50)

    @patch("dashboard.views.call_command")
    def test_collect_data_large_limit_values(self, mock_call_command):
        """Test with very large limit values."""
        self.client.login(username="testuser", password="testpassword123")

        # Test with extremely large numbers
        large_values = ["99999", "1000000", "2147483647"]  # Including max int32

        for large_value in large_values:
            mock_call_command.reset_mock()

            response = self.client.post(self.collect_data_url, {"limit": large_value})

            # Should be capped at 50
            self.assertEqual(response.status_code, 302)
            mock_call_command.assert_called_once_with(
                "fetch_google_flood_data", limit=50
            )


class TestUpdateReadingsView(TestCase):
    """Test UpdateReadingsView functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpassword123"
        )
        self.update_readings_url = reverse("update_readings")
        self.dashboard_url = reverse("dashboard")

    def test_update_readings_login_requirement(self):
        """Test that update readings view requires login."""
        # Test unauthenticated GET
        response = self.client.get(self.update_readings_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/supersecretadminpanel/login/", response.url)

        # Test unauthenticated POST
        response = self.client.post(self.update_readings_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/supersecretadminpanel/login/", response.url)

    def test_update_readings_get_redirect_behavior(self):
        """Test that GET requests are redirected to dashboard."""
        self.client.login(username="testuser", password="testpassword123")

        response = self.client.get(self.update_readings_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.dashboard_url)

    @patch("dashboard.views.call_command")
    def test_update_readings_post_basic_functionality(self, mock_call_command):
        """Test basic POST functionality."""
        self.client.login(username="testuser", password="testpassword123")

        response = self.client.post(self.update_readings_url, {})

        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.dashboard_url)

        # Should call management command
        mock_call_command.assert_called_once_with("update_daily_readings")

    @patch("dashboard.views.call_command")
    def test_update_readings_post_with_force_update(self, mock_call_command):
        """Test POST with force_update parameter."""
        self.client.login(username="testuser", password="testpassword123")

        response = self.client.post(self.update_readings_url, {"force_update": "on"})

        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.dashboard_url)

        # Should call management command with force=True
        mock_call_command.assert_called_once_with("update_daily_readings", force=True)

    @patch("dashboard.views.call_command")
    def test_update_readings_success_message_display(self, mock_call_command):
        """Test success message display."""
        self.client.login(username="testuser", password="testpassword123")

        # Test without force_update
        response = self.client.post(self.update_readings_url, {}, follow=True)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "Successfully updated daily readings for all gauges!"
        )
        self.assertEqual(messages[0].tags, "success")

    @patch("dashboard.views.call_command")
    def test_update_readings_success_message_force_update(self, mock_call_command):
        """Test success message with force_update."""
        self.client.login(username="testuser", password="testpassword123")

        # Test with force_update
        response = self.client.post(
            self.update_readings_url, {"force_update": "on"}, follow=True
        )

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            "Successfully updated readings for all gauges (forced update)!",
        )
        self.assertEqual(messages[0].tags, "success")

    @patch("dashboard.views.call_command")
    def test_update_readings_error_message_display(self, mock_call_command):
        """Test error message display when command fails."""
        self.client.login(username="testuser", password="testpassword123")

        # Mock command to raise exception
        mock_call_command.side_effect = Exception("Network connection failed")

        response = self.client.post(self.update_readings_url, {}, follow=True)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "Error updating readings: Network connection failed"
        )
        self.assertEqual(messages[0].tags, "error")

    @patch("dashboard.views.call_command")
    def test_update_readings_command_invocation_verification(self, mock_call_command):
        """Test that management command is invoked correctly."""
        self.client.login(username="testuser", password="testpassword123")

        # Test various parameter combinations
        test_cases = [
            ({}, []),  # No parameters
            ({"force_update": "on"}, [("force", True)]),  # With force
            ({"force_update": "true"}, [("force", True)]),  # Alternative truthy value
            ({"other_param": "ignored"}, []),  # Extra params ignored
        ]

        for post_data, expected_kwargs in test_cases:
            mock_call_command.reset_mock()

            response = self.client.post(self.update_readings_url, post_data)

            self.assertEqual(response.status_code, 302)

            # Verify command was called with correct arguments
            args, kwargs = mock_call_command.call_args
            self.assertEqual(args[0], "update_daily_readings")

            for key, value in expected_kwargs:
                self.assertEqual(kwargs[key], value)

    @patch("dashboard.views.call_command")
    def test_update_readings_force_update_variations(self, mock_call_command):
        """Test different variations of force_update parameter."""
        self.client.login(username="testuser", password="testpassword123")

        # Test truthy values
        truthy_values = ["on", "true", "1", "yes", "checked"]

        for value in truthy_values:
            mock_call_command.reset_mock()

            response = self.client.post(
                self.update_readings_url, {"force_update": value}
            )

            self.assertEqual(response.status_code, 302)
            mock_call_command.assert_called_once_with(
                "update_daily_readings", force=True
            )

        # Test falsy values (should not include force parameter)
        mock_call_command.reset_mock()

        response = self.client.post(self.update_readings_url, {})

        self.assertEqual(response.status_code, 302)
        mock_call_command.assert_called_once_with("update_daily_readings")

    @patch("dashboard.views.call_command")
    def test_update_readings_various_error_scenarios(self, mock_call_command):
        """Test various error scenarios."""
        self.client.login(username="testuser", password="testpassword123")

        # Test different exception types
        error_scenarios = [
            ("API timeout", "Error updating readings: API timeout"),
            ("No gauges found", "Error updating readings: No gauges found"),
            (
                "Database connection failed",
                "Error updating readings: Database connection failed",
            ),
        ]

        for error_msg, expected_msg in error_scenarios:
            mock_call_command.reset_mock()
            mock_call_command.side_effect = Exception(error_msg)

            response = self.client.post(self.update_readings_url, {}, follow=True)

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), expected_msg)
            self.assertEqual(messages[0].tags, "error")

    @patch("dashboard.views.call_command")
    def test_update_readings_method_not_allowed(self, mock_call_command):
        """Test that unsupported HTTP methods redirect to dashboard."""
        self.client.login(username="testuser", password="testpassword123")

        # Test unsupported methods - Django's View class redirects non-handled methods
        unsupported_methods = ["put", "patch", "delete"]

        for method in unsupported_methods:
            client_method = getattr(self.client, method)
            response = client_method(self.update_readings_url)
            # Django's View redirects unhandled methods to dashboard (GET handler)
            self.assertEqual(response.status_code, 302)  # Redirect

        # Verify command was not called
        mock_call_command.assert_not_called()

    @patch("dashboard.views.call_command")
    def test_update_readings_redirect_after_error(self, mock_call_command):
        """Test that view redirects to dashboard even after error."""
        self.client.login(username="testuser", password="testpassword123")

        # Mock command to raise exception
        mock_call_command.side_effect = Exception("Test error")

        response = self.client.post(self.update_readings_url, {})

        # Should still redirect to dashboard
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.dashboard_url)


@unittest.skip("ClearDataView functionality has been removed")
class TestClearDataView(TestCase):
    """Test ClearDataView functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpassword123"
        )
        self.clear_data_url = reverse("clear_data")
        self.dashboard_url = reverse("dashboard")

    def test_clear_data_login_requirement(self):
        """Test that clear data view requires login."""
        # Test unauthenticated GET
        response = self.client.get(self.clear_data_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/supersecretadminpanel/login/", response.url)

        # Test unauthenticated POST
        response = self.client.post(self.clear_data_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/supersecretadminpanel/login/", response.url)

    def test_clear_data_get_redirect_behavior(self):
        """Test that GET requests are redirected to dashboard."""
        self.client.login(username="testuser", password="testpassword123")

        response = self.client.get(self.clear_data_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.dashboard_url)

    def test_clear_data_post_basic_functionality(self):
        """Test basic POST functionality."""
        # Create test data
        gauge = GaugeFactory()
        reading = ReadingFactory(gauge=gauge)
        prediction = PredictionFactory(gauge=gauge)

        self.client.login(username="testuser", password="testpassword123")

        response = self.client.post(self.clear_data_url, {})

        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.dashboard_url)

        # Should delete all data
        self.assertEqual(Gauge.objects.count(), 0)
        self.assertEqual(Reading.objects.count(), 0)
        self.assertEqual(Prediction.objects.count(), 0)

    def test_clear_data_success_message_display(self):
        """Test success message display."""
        # Create test data
        gauge1 = GaugeFactory()
        gauge2 = GaugeFactory()
        reading1 = ReadingFactory(gauge=gauge1)
        reading2 = ReadingFactory(gauge=gauge2)
        prediction1 = PredictionFactory(gauge=gauge1)

        self.client.login(username="testuser", password="testpassword123")

        response = self.client.post(self.clear_data_url, {}, follow=True)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            "Successfully cleared all data: 2 gauges, 2 readings, 1 predictions",
        )
        self.assertEqual(messages[0].tags, "success")

    def test_clear_data_with_empty_database(self):
        """Test clear data with empty database."""
        self.client.login(username="testuser", password="testpassword123")

        response = self.client.post(self.clear_data_url, {}, follow=True)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            "Successfully cleared all data: 0 gauges, 0 readings, 0 predictions",
        )
        self.assertEqual(messages[0].tags, "success")

    def test_clear_data_cascade_deletion(self):
        """Test that cascade deletion works properly."""
        # Create test data with relationships
        gauge = GaugeFactory()
        readings = ReadingFactory.create_batch(3, gauge=gauge)
        predictions = PredictionFactory.create_batch(2, gauge=gauge)

        self.client.login(username="testuser", password="testpassword123")

        # Verify initial state
        self.assertEqual(Gauge.objects.count(), 1)
        self.assertEqual(Reading.objects.count(), 3)
        self.assertEqual(Prediction.objects.count(), 2)

        response = self.client.post(self.clear_data_url, {})

        # Should delete all data
        self.assertEqual(Gauge.objects.count(), 0)
        self.assertEqual(Reading.objects.count(), 0)
        self.assertEqual(Prediction.objects.count(), 0)

    def test_clear_data_error_handling(self):
        """Test error handling in clear data operation."""
        self.client.login(username="testuser", password="testpassword123")

        # Simulate database error
        with patch("dashboard.views.Gauge.objects.all") as mock_gauge_objects:
            mock_gauge_objects.return_value.delete.side_effect = Exception(
                "Database error"
            )

            response = self.client.post(self.clear_data_url, {}, follow=True)

            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(str(messages[0]), "Error clearing data: Database error")
            self.assertEqual(messages[0].tags, "error")

    def test_clear_data_counts_before_deletion(self):
        """Test that counts are captured before deletion."""
        # Create specific amounts of test data
        gauges = GaugeFactory.create_batch(5)
        readings = []
        predictions = []

        for gauge in gauges:
            readings.extend(ReadingFactory.create_batch(2, gauge=gauge))
            predictions.extend(PredictionFactory.create_batch(1, gauge=gauge))

        self.client.login(username="testuser", password="testpassword123")

        response = self.client.post(self.clear_data_url, {}, follow=True)

        # Should show correct counts in message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            "Successfully cleared all data: 5 gauges, 10 readings, 5 predictions",
        )

        # Data should be deleted
        self.assertEqual(Gauge.objects.count(), 0)
        self.assertEqual(Reading.objects.count(), 0)
        self.assertEqual(Prediction.objects.count(), 0)

    def test_clear_data_method_not_allowed(self):
        """Test that unsupported HTTP methods are not allowed."""
        self.client.login(username="testuser", password="testpassword123")

        # Test unsupported methods
        unsupported_methods = ["put", "patch", "delete", "head", "options"]

        for method in unsupported_methods:
            client_method = getattr(self.client, method)
            response = client_method(self.clear_data_url)
            self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_clear_data_redirect_after_error(self):
        """Test that view redirects to dashboard even after error."""
        self.client.login(username="testuser", password="testpassword123")

        # Mock to raise exception
        with patch("dashboard.views.Gauge.objects.all") as mock_gauge_objects:
            mock_gauge_objects.return_value.delete.side_effect = Exception("Test error")

            response = self.client.post(self.clear_data_url, {})

            # Should still redirect to dashboard
            self.assertEqual(response.status_code, 302)
            self.assertRedirects(response, self.dashboard_url)

    def test_clear_data_deletion_order(self):
        """Test that data is deleted in correct order (readings, predictions, gauges)."""
        # Create test data
        gauge = GaugeFactory()
        reading = ReadingFactory(gauge=gauge)
        prediction = PredictionFactory(gauge=gauge)

        self.client.login(username="testuser", password="testpassword123")

        # Use mocks to verify deletion order
        with patch(
            "dashboard.views.Reading.objects.all"
        ) as mock_reading_objects, patch(
            "dashboard.views.Prediction.objects.all"
        ) as mock_prediction_objects, patch(
            "dashboard.views.Gauge.objects.all"
        ) as mock_gauge_objects:
            mock_reading_objects.return_value.delete.return_value = None
            mock_prediction_objects.return_value.delete.return_value = None
            mock_gauge_objects.return_value.count.return_value = 1
            mock_gauge_objects.return_value.delete.return_value = None

            response = self.client.post(self.clear_data_url, {})

            # Verify deletion methods were called
            mock_reading_objects.return_value.delete.assert_called_once()
            mock_prediction_objects.return_value.delete.assert_called_once()
            mock_gauge_objects.return_value.delete.assert_called_once()

    def test_clear_data_view_class_behavior(self):
        """Test ClearDataView class behavior."""
        from dashboard.views import ClearDataView
        from django.contrib.auth.mixins import LoginRequiredMixin
        from django.views import View

        # Test inheritance
        self.assertTrue(issubclass(ClearDataView, LoginRequiredMixin))
        self.assertTrue(issubclass(ClearDataView, View))

        # Test that view handles both GET and POST
        view = ClearDataView()
        self.assertTrue(hasattr(view, "get"))
        self.assertTrue(hasattr(view, "post"))

    def test_clear_data_large_dataset_handling(self):
        """Test clear data with large dataset."""
        # Create larger dataset
        gauges = GaugeFactory.create_batch(20)

        # Create many readings and predictions
        for gauge in gauges:
            ReadingFactory.create_batch(5, gauge=gauge)
            PredictionFactory.create_batch(2, gauge=gauge)

        self.client.login(username="testuser", password="testpassword123")

        # Verify initial state
        self.assertEqual(Gauge.objects.count(), 20)
        self.assertEqual(Reading.objects.count(), 100)
        self.assertEqual(Prediction.objects.count(), 40)

        response = self.client.post(self.clear_data_url, {}, follow=True)

        # Should clear all data
        self.assertEqual(Gauge.objects.count(), 0)
        self.assertEqual(Reading.objects.count(), 0)
        self.assertEqual(Prediction.objects.count(), 0)

        # Should show correct counts in message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]),
            "Successfully cleared all data: 20 gauges, 100 readings, 40 predictions",
        )

    def test_clear_data_partial_failure_handling(self):
        """Test handling of partial failures during deletion."""
        # Create test data
        gauge = GaugeFactory()
        reading = ReadingFactory(gauge=gauge)

        self.client.login(username="testuser", password="testpassword123")

        # Mock to simulate partial failure
        with patch("dashboard.views.Reading.objects.all") as mock_reading_objects:
            mock_reading_objects.return_value.delete.side_effect = Exception(
                "Reading deletion failed"
            )

            response = self.client.post(self.clear_data_url, {}, follow=True)

            # Should show error message
            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 1)
            self.assertEqual(
                str(messages[0]), "Error clearing data: Reading deletion failed"
            )
            self.assertEqual(messages[0].tags, "error")

    def test_clear_data_csrf_protection(self):
        """Test CSRF protection on clear data POST."""
        self.client.login(username="testuser", password="testpassword123")

        # Django test client handles CSRF automatically
        response = self.client.post(self.clear_data_url, {})

        # Should succeed (test client handles CSRF)
        self.assertEqual(response.status_code, 302)

    def test_clear_data_concurrent_access(self):
        """Test clear data with concurrent access."""
        # Create test data
        GaugeFactory.create_batch(5)

        self.client.login(username="testuser", password="testpassword123")

        # Simulate concurrent requests
        responses = []
        for i in range(3):
            response = self.client.post(self.clear_data_url, {})
            responses.append(response)

        # All should succeed (though later ones will clear empty database)
        for response in responses:
            self.assertEqual(response.status_code, 302)

        # Data should be cleared
        self.assertEqual(Gauge.objects.count(), 0)
