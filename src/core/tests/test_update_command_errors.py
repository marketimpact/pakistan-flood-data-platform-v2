"""Error handling tests for update_daily_readings command."""

from io import StringIO
from unittest.mock import patch, Mock
import requests
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta

from core.models import Gauge, Reading
from core.tests.base import BaseTestCase
from core.tests.factories import GaugeFactory, ReadingFactory
from core.tests.helpers import mock_api_response
from core.tests.fixtures.api_responses import ERROR_RESPONSES, SAMPLE_THRESHOLD_RESPONSE


class TestUpdateCommandErrors(BaseTestCase):
    """Test error handling scenarios for update_daily_readings command."""

    @patch("requests.get")
    def test_partial_api_failures_continue_processing(self, mock_get):
        """Test that partial API failures don't stop processing of other gauges."""
        # Create multiple gauges
        gauge1 = GaugeFactory(name="Success Gauge 1")
        gauge2 = GaugeFactory(name="Error Gauge")
        gauge3 = GaugeFactory(name="Success Gauge 2")

        # Mock sequence: success, error, success
        mock_get.side_effect = [
            mock_api_response(200, {"currentValue": 10.0}),  # Success
            mock_api_response(500, ERROR_RESPONSES["server_error"]),  # Error
            mock_api_response(200, {"currentValue": 12.0}),  # Success
        ]

        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Should create 2 readings (for successful gauges)
        self.assertEqual(Reading.objects.count(), 2)

        # Verify successful gauges got readings
        self.assertTrue(Reading.objects.filter(gauge=gauge1).exists())
        self.assertTrue(Reading.objects.filter(gauge=gauge3).exists())

        # Verify failed gauge has no new reading
        self.assertFalse(Reading.objects.filter(gauge=gauge2).exists())

        # Verify output shows mixed results
        output = out.getvalue()
        self.assertIn("Updated Success Gauge 1", output)
        self.assertIn("Updated Success Gauge 2", output)
        self.assertIn("Error updating Error Gauge", output)
        self.assertIn("Updated: 2 gauges", output)
        self.assertIn("Errors: 1 gauges", output)

    @patch("requests.get")
    def test_network_timeout_handling(self, mock_get):
        """Test handling of network timeouts during API calls."""
        gauge = GaugeFactory(name="Timeout Gauge")

        # Mock timeout exception
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Should not create any readings
        self.assertEqual(Reading.objects.count(), 0)

        # Should show network error
        output = out.getvalue()
        self.assertIn("Network error for Timeout Gauge", output)
        self.assertIn("Errors: 1 gauges", output)

    @patch("requests.get")
    def test_connection_error_handling(self, mock_get):
        """Test handling of connection errors during API calls."""
        gauge = GaugeFactory(name="Connection Error Gauge")

        # Mock connection error
        mock_get.side_effect = requests.exceptions.ConnectionError("Failed to connect")

        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Should not create any readings
        self.assertEqual(Reading.objects.count(), 0)

        # Should show network error
        output = out.getvalue()
        self.assertIn("Network error for Connection Error Gauge", output)
        self.assertIn("Errors: 1 gauges", output)

    @patch("requests.get")
    def test_complete_api_failure_with_fallback(self, mock_get):
        """Test complete API failure falls back to safe value generation."""
        gauge = GaugeFactory(name="Complete Failure Gauge")

        # Mock complete failure: both flood status and threshold fail
        mock_get.side_effect = [
            mock_api_response(404),  # No flood status
            mock_api_response(500, ERROR_RESPONSES["server_error"]),  # Threshold error
        ]

        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Should create reading with fallback value
        self.assertEqual(Reading.objects.count(), 1)
        reading = Reading.objects.first()

        # Should use absolute fallback range (1.0 - 5.0)
        self.assertGreaterEqual(reading.water_level, 1.0)
        self.assertLessEqual(reading.water_level, 5.0)

        # Should show successful update despite API failures
        output = out.getvalue()
        self.assertIn("Updated Complete Failure Gauge", output)
        self.assertIn("Updated: 1 gauges", output)
        self.assertIn(
            "Errors: 0 gauges", output
        )  # Not counted as error since fallback worked

    @patch("requests.get")
    def test_malformed_json_response_handling(self, mock_get):
        """Test handling of malformed JSON responses."""
        gauge = GaugeFactory(name="Malformed JSON Gauge")

        # Create response that fails JSON parsing
        response = Mock()
        response.status_code = 200
        response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = response

        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Should not create any readings
        self.assertEqual(Reading.objects.count(), 0)

        # Should show error
        output = out.getvalue()
        self.assertIn("Error updating Malformed JSON Gauge", output)
        self.assertIn("Errors: 1 gauges", output)

    @patch("requests.get")
    def test_safe_value_generation_ranges(self, mock_get):
        """Test that safe value generation stays within expected ranges."""
        gauge = GaugeFactory(name="Safe Value Gauge")

        # Mock threshold response with known values
        mock_get.side_effect = [
            mock_api_response(404),  # No flood status
            mock_api_response(
                200,
                {
                    "thresholds": {
                        "warningLevel": 20.0,
                        "dangerLevel": 30.0,
                        "extremeDangerLevel": 40.0,
                    }
                },
            ),
        ]

        # Run command multiple times to test range consistency
        for _ in range(10):
            Reading.objects.all().delete()  # Clear between tests

            call_command("update_daily_readings")

            reading = Reading.objects.first()

            # Should be 70-90% of warning level (20.0)
            # So between 14.0 and 18.0
            self.assertGreaterEqual(reading.water_level, 14.0)
            self.assertLessEqual(reading.water_level, 18.0)

            # Water level and flow rate should be identical
            self.assertEqual(reading.water_level, reading.flow_rate)

    @patch("requests.get")
    def test_absolute_fallback_range_verification(self, mock_get):
        """Test absolute fallback values are within safe range."""
        gauge = GaugeFactory(name="Absolute Fallback Gauge")

        # Mock complete API failure
        mock_get.side_effect = [
            mock_api_response(404),  # No flood status
            mock_api_response(404),  # No threshold data
        ]

        # Run command multiple times to test range consistency
        for _ in range(10):
            Reading.objects.all().delete()  # Clear between tests

            call_command("update_daily_readings")

            reading = Reading.objects.first()

            # Should be in absolute fallback range (1.0 - 5.0)
            self.assertGreaterEqual(reading.water_level, 1.0)
            self.assertLessEqual(reading.water_level, 5.0)

            # Water level and flow rate should be identical
            self.assertEqual(reading.water_level, reading.flow_rate)

    @patch("requests.get")
    def test_mixed_error_scenarios(self, mock_get):
        """Test mixed error scenarios in a single command run."""
        # Create various gauges for different error scenarios
        timeout_gauge = GaugeFactory(name="Timeout Gauge")
        server_error_gauge = GaugeFactory(name="Server Error Gauge")
        fallback_gauge = GaugeFactory(name="Fallback Gauge")
        success_gauge = GaugeFactory(name="Success Gauge")

        # Mock different error types
        mock_get.side_effect = [
            # Timeout gauge
            requests.exceptions.Timeout("Timeout"),
            # Server error gauge
            mock_api_response(500, ERROR_RESPONSES["server_error"]),
            # Fallback gauge - no flood status, no threshold
            mock_api_response(404),
            mock_api_response(404),
            # Success gauge
            mock_api_response(200, {"currentValue": 15.0}),
        ]

        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Should create readings for fallback and success gauges
        self.assertEqual(Reading.objects.count(), 2)

        # Verify fallback gauge got reading
        fallback_reading = Reading.objects.filter(gauge=fallback_gauge).first()
        self.assertIsNotNone(fallback_reading)
        self.assertGreaterEqual(fallback_reading.water_level, 1.0)
        self.assertLessEqual(fallback_reading.water_level, 5.0)

        # Verify success gauge got reading
        success_reading = Reading.objects.filter(gauge=success_gauge).first()
        self.assertIsNotNone(success_reading)
        self.assertEqual(success_reading.water_level, 15.0)

        # Verify output shows mixed results
        output = out.getvalue()
        self.assertIn("Network error for Timeout Gauge", output)
        self.assertIn("Error updating Server Error Gauge", output)
        self.assertIn("Updated Fallback Gauge", output)
        self.assertIn("Updated Success Gauge", output)
        self.assertIn("Updated: 2 gauges", output)
        self.assertIn("Errors: 2 gauges", output)

    @patch("requests.get")
    def test_api_rate_limiting_handling(self, mock_get):
        """Test handling of API rate limiting (429 errors)."""
        gauge = GaugeFactory(name="Rate Limited Gauge")

        # Mock 429 rate limit response
        mock_get.return_value = mock_api_response(429, ERROR_RESPONSES["rate_limited"])

        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Should not create any readings
        self.assertEqual(Reading.objects.count(), 0)

        # Should show error
        output = out.getvalue()
        self.assertIn("Error updating Rate Limited Gauge", output)
        self.assertIn("Errors: 1 gauges", output)

    @patch("requests.get")
    def test_threshold_api_partial_failure(self, mock_get):
        """Test partial threshold API failure still allows fallback."""
        gauge = GaugeFactory(name="Partial Threshold Gauge")

        # Mock: no flood status, threshold fails but fallback works
        mock_get.side_effect = [
            mock_api_response(404),  # No flood status
            requests.exceptions.Timeout("Threshold timeout"),  # Threshold fails
        ]

        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Should create reading with absolute fallback
        self.assertEqual(Reading.objects.count(), 1)
        reading = Reading.objects.first()

        # Should use absolute fallback range
        self.assertGreaterEqual(reading.water_level, 1.0)
        self.assertLessEqual(reading.water_level, 5.0)

        # Should show successful update (fallback worked)
        output = out.getvalue()
        self.assertIn("Updated Partial Threshold Gauge", output)
        self.assertIn("Updated: 1 gauges", output)

    @patch("requests.get")
    def test_database_error_handling(self, mock_get):
        """Test handling of database errors during reading creation."""
        gauge = GaugeFactory(name="DB Error Gauge")

        # Mock successful API response
        mock_get.return_value = mock_api_response(200, {"currentValue": 10.0})

        # Mock database error during reading creation
        with patch("core.models.Reading.objects.create") as mock_create:
            mock_create.side_effect = Exception("Database error")

            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            # Should not create any readings
            self.assertEqual(Reading.objects.count(), 0)

            # Should show error
            output = out.getvalue()
            self.assertIn("Error updating DB Error Gauge", output)
            self.assertIn("Errors: 1 gauges", output)

    @patch("requests.get")
    def test_invalid_threshold_data_handling(self, mock_get):
        """Test handling of invalid threshold data from API."""
        gauge = GaugeFactory(name="Invalid Threshold Gauge")

        # Mock: no flood status, invalid threshold data
        mock_get.side_effect = [
            mock_api_response(404),  # No flood status
            mock_api_response(
                200,
                {
                    "thresholds": {
                        "warningLevel": "not_a_number",  # Invalid data type
                        "dangerLevel": None,
                        "extremeDangerLevel": -5.0,  # Invalid negative value
                    }
                },
            ),
        ]

        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Should handle gracefully and fall back to absolute range
        self.assertEqual(Reading.objects.count(), 1)
        reading = Reading.objects.first()

        # Should use absolute fallback range
        self.assertGreaterEqual(reading.water_level, 1.0)
        self.assertLessEqual(reading.water_level, 5.0)

        # Should show successful update
        output = out.getvalue()
        self.assertIn("Updated Invalid Threshold Gauge", output)

    @patch("requests.get")
    def test_missing_threshold_fields(self, mock_get):
        """Test handling of threshold response missing required fields."""
        gauge = GaugeFactory(name="Missing Fields Gauge")

        # Mock: no flood status, threshold response missing warningLevel
        mock_get.side_effect = [
            mock_api_response(404),  # No flood status
            mock_api_response(
                200,
                {
                    "thresholds": {
                        "dangerLevel": 20.0,
                        "extremeDangerLevel": 30.0
                        # Missing warningLevel
                    }
                },
            ),
        ]

        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Should handle gracefully and fall back to absolute range
        self.assertEqual(Reading.objects.count(), 1)
        reading = Reading.objects.first()

        # Should use absolute fallback range
        self.assertGreaterEqual(reading.water_level, 1.0)
        self.assertLessEqual(reading.water_level, 5.0)

        # Should show successful update
        output = out.getvalue()
        self.assertIn("Updated Missing Fields Gauge", output)

    @patch("requests.get")
    def test_error_recovery_continues_processing(self, mock_get):
        """Test that command continues processing after errors."""
        # Create multiple gauges where some will fail
        error_gauge_1 = GaugeFactory(name="Error 1")
        success_gauge = GaugeFactory(name="Success")
        error_gauge_2 = GaugeFactory(name="Error 2")

        # Mock sequence with errors
        mock_get.side_effect = [
            requests.exceptions.Timeout("First error"),
            mock_api_response(200, {"currentValue": 10.0}),  # Success
            mock_api_response(500, ERROR_RESPONSES["server_error"]),  # Second error
        ]

        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Should create reading for successful gauge
        self.assertEqual(Reading.objects.count(), 1)
        self.assertTrue(Reading.objects.filter(gauge=success_gauge).exists())

        # Should show all results
        output = out.getvalue()
        self.assertIn("Network error for Error 1", output)
        self.assertIn("Updated Success", output)
        self.assertIn("Error updating Error 2", output)
        self.assertIn("Updated: 1 gauges", output)
        self.assertIn("Errors: 2 gauges", output)
        self.assertIn("Total processed: 3/3", output)

    @patch("requests.get")
    def test_comprehensive_error_summary(self, mock_get):
        """Test comprehensive error summary with various failure types."""
        # Create gauges for different scenarios
        GaugeFactory.create_batch(3)

        # Mock all failures
        mock_get.side_effect = [
            requests.exceptions.Timeout("Timeout"),
            mock_api_response(500, ERROR_RESPONSES["server_error"]),
            requests.exceptions.ConnectionError("Connection failed"),
        ]

        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Should not create any readings
        self.assertEqual(Reading.objects.count(), 0)

        # Should show comprehensive error summary
        output = out.getvalue()
        self.assertIn("Daily update complete", output)
        self.assertIn("Updated: 0 gauges", output)
        self.assertIn("Errors: 3 gauges", output)
        self.assertIn("Total processed: 3/3", output)

    @patch("requests.get")
    def test_force_flag_with_errors(self, mock_get):
        """Test force flag behavior when errors occur."""
        # Create gauge with recent reading
        gauge = GaugeFactory(name="Force Error Gauge")
        ReadingFactory(gauge=gauge, timestamp=timezone.now() - timedelta(hours=12))

        # Mock API error
        mock_get.side_effect = requests.exceptions.Timeout("Timeout error")

        out = StringIO()
        call_command("update_daily_readings", "--force", stdout=out)

        # Should not create new reading due to error
        self.assertEqual(Reading.objects.count(), 1)  # Only the original

        # Should show error (not skip)
        output = out.getvalue()
        self.assertNotIn("Skipped", output)
        self.assertIn("Network error for Force Error Gauge", output)
        self.assertIn("Errors: 1 gauges", output)
