"""Comprehensive tests for management commands."""

import os
from io import StringIO
from unittest.mock import patch, Mock, MagicMock
import pytest
from django.core.management import call_command
from django.test import TestCase, override_settings
from core.models import Gauge, Reading
from core.tests.factories import GaugeFactory, ReadingFactory
from django.utils import timezone
from datetime import timedelta


class FetchGoogleFloodDataCommandTests(TestCase):
    """Comprehensive tests for fetch_google_flood_data command."""

    def setUp(self):
        """Set up test environment."""
        self.api_key = "test_api_key_12345"
        os.environ["GOOGLE_FLOOD_HUB_API_KEY"] = self.api_key

    def tearDown(self):
        """Clean up environment."""
        if "GOOGLE_FLOOD_HUB_API_KEY" in os.environ:
            del os.environ["GOOGLE_FLOOD_HUB_API_KEY"]

    @patch("requests.get")
    def test_successful_gauge_fetch_with_quality_verified(self, mock_get):
        """Test successful gauge data fetching for quality verified gauge."""
        # Mock API responses
        gauge_response = Mock()
        gauge_response.status_code = 200
        gauge_response.json.return_value = {
            "siteName": "Chitral River Station",
            "location": {"latitude": 35.8462, "longitude": 71.7839},
            "qualityVerified": True,
            "hasModel": True,
            "river": "Chitral River",
        }

        threshold_response = Mock()
        threshold_response.status_code = 200
        threshold_response.json.return_value = {
            "thresholds": {
                "warningLevel": 10.0,
                "dangerLevel": 15.0,
                "extremeDangerLevel": 20.0,
            }
        }

        # Configure mock to return different responses for different calls
        mock_get.side_effect = [gauge_response, threshold_response]

        # Run command
        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Verify gauge was created
        self.assertEqual(Gauge.objects.count(), 1)
        gauge = Gauge.objects.first()
        self.assertEqual(gauge.name, "Chitral River Station")
        self.assertEqual(gauge.latitude, 35.8462)
        self.assertEqual(gauge.longitude, 71.7839)
        self.assertTrue(gauge.quality_verified)
        self.assertTrue(gauge.has_model)

        # Verify reading was created with 80% of warning level
        self.assertEqual(Reading.objects.count(), 1)
        reading = Reading.objects.first()
        self.assertEqual(reading.water_level, 8.0)  # 80% of 10.0
        self.assertEqual(reading.flow_rate, 8.0)
        self.assertEqual(reading.gauge, gauge)

        # Verify API calls were made correctly
        self.assertEqual(mock_get.call_count, 2)

        # Check output
        output = out.getvalue()
        self.assertIn("Created: Chitral River Station", output)
        self.assertIn("✓ VERIFIED", output)

    @patch("requests.get")
    def test_successful_gauge_fetch_without_quality_verification(self, mock_get):
        """Test successful gauge data fetching for non-quality verified gauge."""
        gauge_response = Mock()
        gauge_response.status_code = 200
        gauge_response.json.return_value = {
            "siteName": "Test River Station",
            "location": {"latitude": 30.0, "longitude": 70.0},
            "qualityVerified": False,
            "hasModel": False,
            "river": "Test River",
        }

        threshold_response = Mock()
        threshold_response.status_code = 404  # No threshold data

        mock_get.side_effect = [gauge_response, threshold_response]

        # Run command
        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Verify gauge was created
        gauge = Gauge.objects.first()
        self.assertFalse(gauge.quality_verified)
        self.assertFalse(gauge.has_model)

        # Verify output shows unverified status
        output = out.getvalue()
        self.assertIn("⚠ UNVERIFIED", output)

    @patch("requests.get")
    def test_quality_only_filter_excludes_unverified(self, mock_get):
        """Test --quality-only flag filters out unverified gauges."""
        # Mock unverified gauge response
        gauge_response = Mock()
        gauge_response.status_code = 200
        gauge_response.json.return_value = {
            "qualityVerified": False,
            "location": {"latitude": 30.0, "longitude": 70.0},
        }

        mock_get.return_value = gauge_response

        # Run with quality-only flag
        out = StringIO()
        call_command(
            "fetch_google_flood_data", "--limit=1", "--quality-only", stdout=out
        )

        # No gauges should be created
        self.assertEqual(Gauge.objects.count(), 0)

        # Verify API was still called to check quality
        mock_get.assert_called()

    @patch("requests.get")
    def test_api_404_error_handling(self, mock_get):
        """Test handling of 404 errors from API."""
        mock_get.return_value.status_code = 404

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # No gauges should be created
        self.assertEqual(Gauge.objects.count(), 0)

        # Verify error message
        output = out.getvalue()
        self.assertIn("not found (404)", output)

    @patch("requests.get")
    def test_network_error_handling(self, mock_get):
        """Test handling of network errors."""
        mock_get.side_effect = Exception("Network timeout")

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # No gauges should be created
        self.assertEqual(Gauge.objects.count(), 0)

        # Verify error message
        output = out.getvalue()
        self.assertIn("Network error", output)

    def test_missing_api_key_error(self):
        """Test behavior when API key is missing."""
        del os.environ["GOOGLE_FLOOD_HUB_API_KEY"]

        out = StringIO()
        call_command("fetch_google_flood_data", stdout=out)

        output = out.getvalue()
        self.assertIn("GOOGLE_FLOOD_HUB_API_KEY not found", output)

    @patch("requests.get")
    def test_limit_parameter_validation(self, mock_get):
        """Test limit parameter validation."""
        mock_get.return_value.status_code = 404

        # Test valid limits
        for limit in [1, 10, 50, 100]:
            out = StringIO()
            call_command("fetch_google_flood_data", f"--limit={limit}", stdout=out)
            self.assertIn(f"up to {limit} gauges", out.getvalue())

        # Test invalid limit (should be handled gracefully)
        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=0", stdout=out)
        # Should not crash


class UpdateDailyReadingsCommandTests(TestCase):
    """Comprehensive tests for update_daily_readings command."""

    def setUp(self):
        """Set up test environment."""
        self.api_key = "test_api_key_12345"
        os.environ["GOOGLE_FLOOD_HUB_API_KEY"] = self.api_key

        # Create test gauges
        self.gauge1 = GaugeFactory(
            gauge_id="test_gauge_001", name="Test Gauge 1", quality_verified=True
        )
        self.gauge2 = GaugeFactory(
            gauge_id="test_gauge_002", name="Test Gauge 2", quality_verified=False
        )

    def tearDown(self):
        """Clean up environment."""
        if "GOOGLE_FLOOD_HUB_API_KEY" in os.environ:
            del os.environ["GOOGLE_FLOOD_HUB_API_KEY"]

    @patch("requests.get")
    def test_successful_daily_update_with_api_data(self, mock_get):
        """Test successful daily update with real API data."""
        # Mock successful API response
        status_response = Mock()
        status_response.status_code = 200
        status_response.json.return_value = {"currentValue": 7.5, "severity": "NORMAL"}

        mock_get.return_value = status_response

        # Run command
        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Verify readings were created
        self.assertEqual(Reading.objects.count(), 2)

        # Check that both gauges got readings
        for gauge in [self.gauge1, self.gauge2]:
            reading = Reading.objects.filter(gauge=gauge).first()
            self.assertIsNotNone(reading)
            self.assertEqual(reading.water_level, 7.5)
            self.assertEqual(reading.flow_rate, 7.5)

        # Verify output
        output = out.getvalue()
        self.assertIn("Updated: Test Gauge 1", output)
        self.assertIn("Updated: Test Gauge 2", output)
        self.assertIn("✓ Updated: 2 gauges", output)

    @patch("requests.get")
    def test_fallback_to_safe_generated_values(self, mock_get):
        """Test fallback to safe generated values when API fails."""
        # Mock API failure for status, success for thresholds
        status_response = Mock()
        status_response.status_code = 404

        threshold_response = Mock()
        threshold_response.status_code = 200
        threshold_response.json.return_value = {
            "thresholds": {"warningLevel": 10.0, "dangerLevel": 15.0}
        }

        mock_get.side_effect = [status_response, threshold_response] * 2

        # Run command
        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Verify readings were created with safe values
        self.assertEqual(Reading.objects.count(), 2)

        for reading in Reading.objects.all():
            # Should be between 70-90% of warning level (7.0-9.0)
            self.assertGreaterEqual(reading.water_level, 7.0)
            self.assertLessEqual(reading.water_level, 9.0)

    @patch("requests.get")
    def test_skip_recent_readings_without_force(self, mock_get):
        """Test that recent readings are skipped without --force flag."""
        # Create recent reading for gauge1
        recent_reading = ReadingFactory(
            gauge=self.gauge1, timestamp=timezone.now() - timedelta(hours=2)
        )

        # Mock API response
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"currentValue": 8.0}

        # Run command
        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Should only create reading for gauge2 (no recent reading)
        self.assertEqual(Reading.objects.count(), 2)  # 1 existing + 1 new

        # Verify output
        output = out.getvalue()
        self.assertIn("Skipped Test Gauge 1", output)
        self.assertIn("Updated: Test Gauge 2", output)
        self.assertIn("⏭ Skipped: 1 gauges", output)

    @patch("requests.get")
    def test_force_update_ignores_recent_readings(self, mock_get):
        """Test that --force flag ignores recent readings."""
        # Create recent reading
        ReadingFactory(gauge=self.gauge1, timestamp=timezone.now() - timedelta(hours=2))

        # Mock API response
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"currentValue": 8.0}

        # Run command with force flag
        out = StringIO()
        call_command("update_daily_readings", "--force", stdout=out)

        # Should create readings for both gauges
        self.assertEqual(Reading.objects.count(), 3)  # 1 existing + 2 new

        # Verify output
        output = out.getvalue()
        self.assertIn("Updated: Test Gauge 1", output)
        self.assertIn("Updated: Test Gauge 2", output)
        self.assertIn("✓ Updated: 2 gauges", output)

    def test_no_gauges_scenario(self):
        """Test behavior when no gauges exist."""
        # Delete all gauges
        Gauge.objects.all().delete()

        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        output = out.getvalue()
        self.assertIn("No gauges found", output)

    def test_missing_api_key_error(self):
        """Test behavior when API key is missing."""
        del os.environ["GOOGLE_FLOOD_HUB_API_KEY"]

        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        output = out.getvalue()
        self.assertIn("GOOGLE_FLOOD_HUB_API_KEY not found", output)

    @patch("requests.get")
    def test_quality_indicator_in_output(self, mock_get):
        """Test that quality indicators are shown in output."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"currentValue": 5.0}

        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        output = out.getvalue()
        # Quality verified gauge should show ✓
        self.assertIn("✓ Updated Test Gauge 1", output)
        # Non-quality verified gauge should show ⚠
        self.assertIn("⚠ Updated Test Gauge 2", output)
