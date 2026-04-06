"""Error handling tests for fetch_google_flood_data command."""

from io import StringIO
from unittest.mock import patch, Mock
import requests
from django.core.management import call_command

from core.models import Gauge, Reading
from core.tests.base import BaseTestCase
from core.tests.helpers import mock_api_response
from core.tests.fixtures.api_responses import ERROR_RESPONSES, MALFORMED_RESPONSES


class TestFetchCommandErrors(BaseTestCase):
    """Test error handling scenarios for fetch_google_flood_data command."""

    @patch("requests.get")
    def test_handle_404_not_found(self, mock_get):
        """Test handling of 404 Not Found responses."""
        # Mock 404 response for gauge API
        mock_get.return_value = mock_api_response(404, ERROR_RESPONSES["not_found"])

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Should not create any gauges
        self.assertEqual(Gauge.objects.count(), 0)
        self.assertEqual(Reading.objects.count(), 0)

        # Should show appropriate error message
        output = out.getvalue()
        self.assertIn("not found (404)", output)

    @patch("requests.get")
    def test_handle_500_server_error(self, mock_get):
        """Test handling of 500 Internal Server Error responses."""
        # Mock 500 response
        mock_get.return_value = mock_api_response(500, ERROR_RESPONSES["server_error"])

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Should not create any gauges
        self.assertEqual(Gauge.objects.count(), 0)

        # Should show error message
        output = out.getvalue()
        self.assertIn("Error", output)
        self.assertIn("500", output)

    @patch("requests.get")
    def test_handle_429_rate_limit(self, mock_get):
        """Test handling of 429 Too Many Requests (rate limiting)."""
        # Mock 429 response with retry headers
        headers = {"Retry-After": "60"}
        mock_get.return_value = mock_api_response(
            429, ERROR_RESPONSES["rate_limited"], headers=headers
        )

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Should not create any gauges
        self.assertEqual(Gauge.objects.count(), 0)

        # Should show rate limit error
        output = out.getvalue()
        self.assertIn("Error", output)
        self.assertIn("429", output)

    @patch("requests.get")
    def test_handle_network_timeout(self, mock_get):
        """Test handling of network timeout errors."""
        # Mock timeout exception
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Should not create any gauges
        self.assertEqual(Gauge.objects.count(), 0)

        # Should show network error
        output = out.getvalue()
        self.assertIn("Network error", output)

    @patch("requests.get")
    def test_handle_connection_error(self, mock_get):
        """Test handling of connection errors."""
        # Mock connection error
        mock_get.side_effect = requests.exceptions.ConnectionError("Failed to connect")

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Should not create any gauges
        self.assertEqual(Gauge.objects.count(), 0)

        # Should show network error
        output = out.getvalue()
        self.assertIn("Network error", output)

    @patch("requests.get")
    def test_handle_malformed_json(self, mock_get):
        """Test handling of malformed JSON responses."""
        # Create response that fails JSON parsing
        response = Mock()
        response.status_code = 200
        response.json.side_effect = ValueError("Invalid JSON")
        response.text = "Not valid JSON{"
        response.ok = True
        mock_get.return_value = response

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Should not create any gauges
        self.assertEqual(Gauge.objects.count(), 0)

        # Should show parsing error
        output = out.getvalue()
        self.assertIn("Error", output)

    @patch("requests.get")
    def test_handle_missing_gauge_id(self, mock_get):
        """Test handling of response missing gaugeId field."""
        # Response without gaugeId
        mock_get.return_value = mock_api_response(
            200,
            {
                "siteName": "Test Gauge",
                "location": {"latitude": 30.0, "longitude": 70.0},
                "qualityVerified": True
                # Missing gaugeId
            },
        )

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Should not create gauge without ID
        self.assertEqual(Gauge.objects.count(), 0)

        # Should show error about missing field
        output = out.getvalue()
        self.assertIn("Error", output)

    @patch("requests.get")
    def test_handle_missing_location(self, mock_get):
        """Test handling of response missing location data."""
        # Use fixture with missing location
        mock_get.return_value = mock_api_response(
            200, MALFORMED_RESPONSES["missing_location"]
        )

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Should handle gracefully
        output = out.getvalue()
        self.assertIn("Error", output)

    @patch("requests.get")
    def test_handle_invalid_coordinates(self, mock_get):
        """Test handling of invalid coordinate data types."""
        # Use fixture with string coordinates instead of floats
        mock_get.return_value = mock_api_response(
            200, MALFORMED_RESPONSES["invalid_coordinates"]
        )

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Should handle invalid data gracefully
        output = out.getvalue()
        self.assertIn("Error", output)

    @patch("requests.get")
    def test_handle_partial_gauge_data(self, mock_get):
        """Test handling of gauge with minimal required fields only."""
        # Gauge with only required fields
        minimal_gauge = {
            "gaugeId": "minimal_gauge",
            "location": {"latitude": 30.0, "longitude": 70.0}
            # Missing: siteName, qualityVerified, hasModel, river
        }

        mock_get.side_effect = [
            mock_api_response(200, minimal_gauge),
            mock_api_response(404),  # No threshold data
        ]

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Should create gauge with defaults for missing fields
        self.assertEqual(Gauge.objects.count(), 1)
        gauge = Gauge.objects.first()
        self.assertEqual(gauge.gauge_id, "minimal_gauge")
        self.assertEqual(gauge.name, "Unnamed Gauge")  # Default name
        self.assertFalse(gauge.quality_verified)  # Default false
        self.assertFalse(gauge.has_model)  # Default false

    @patch("requests.get")
    def test_handle_threshold_api_error(self, mock_get):
        """Test handling when gauge API succeeds but threshold API fails."""
        # Mock successful gauge response, then threshold error
        mock_get.side_effect = [
            mock_api_response(
                200,
                {
                    "gaugeId": "test_gauge",
                    "siteName": "Test Gauge",
                    "location": {"latitude": 30.0, "longitude": 70.0},
                    "qualityVerified": True,
                    "hasModel": True,
                },
            ),
            mock_api_response(500, ERROR_RESPONSES["server_error"]),
        ]

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Should create gauge but no reading
        self.assertEqual(Gauge.objects.count(), 1)
        self.assertEqual(Reading.objects.count(), 0)

        # Should show partial success
        output = out.getvalue()
        self.assertIn("Created:", output)

    @patch("requests.get")
    def test_handle_invalid_threshold_data(self, mock_get):
        """Test handling of malformed threshold response data."""
        # Mock gauge success, then malformed threshold
        mock_get.side_effect = [
            mock_api_response(
                200,
                {
                    "gaugeId": "test_gauge",
                    "siteName": "Test Gauge",
                    "location": {"latitude": 30.0, "longitude": 70.0},
                    "qualityVerified": True,
                    "hasModel": True,
                },
            ),
            mock_api_response(
                200,
                {
                    "thresholds": {
                        "warningLevel": "not_a_number",  # Invalid type
                        "dangerLevel": 20.0,
                    }
                },
            ),
        ]

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Should create gauge but handle threshold error gracefully
        self.assertEqual(Gauge.objects.count(), 1)
        # Reading creation depends on error handling implementation

    @patch("requests.get")
    def test_handle_multiple_sequential_errors(self, mock_get):
        """Test handling of multiple sequential API errors."""
        # Mock a series of different errors
        mock_get.side_effect = [
            mock_api_response(404),  # First gauge not found
            mock_api_response(500),  # Second gauge server error
            requests.exceptions.Timeout(),  # Third gauge timeout
            mock_api_response(429),  # Fourth gauge rate limited
        ]

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=4", stdout=out)

        # Should not create any gauges
        self.assertEqual(Gauge.objects.count(), 0)

        # Should show multiple errors
        output = out.getvalue()
        self.assertIn("Error", output)
        self.assertIn("complete", output.lower())

    @patch("requests.get")
    def test_error_recovery_continues_processing(self, mock_get):
        """Test that processing continues after recoverable errors."""
        # Mock: error, success, error, success pattern
        mock_get.side_effect = [
            # First gauge - 404 error
            mock_api_response(404),
            # Second gauge - success
            mock_api_response(
                200,
                {
                    "gaugeId": "success_gauge_1",
                    "siteName": "Success Gauge 1",
                    "location": {"latitude": 31.0, "longitude": 71.0},
                    "qualityVerified": True,
                    "hasModel": False,
                },
            ),
            mock_api_response(404),  # No threshold
            # Third gauge - network error
            requests.exceptions.ConnectionError(),
            # Fourth gauge - success
            mock_api_response(
                200,
                {
                    "gaugeId": "success_gauge_2",
                    "siteName": "Success Gauge 2",
                    "location": {"latitude": 32.0, "longitude": 72.0},
                    "qualityVerified": True,
                    "hasModel": True,
                },
            ),
            mock_api_response(
                200, {"thresholds": {"warningLevel": 15.0, "dangerLevel": 20.0}}
            ),
        ]

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=4", stdout=out)

        # Should create 2 successful gauges
        self.assertEqual(Gauge.objects.count(), 2)
        self.assertTrue(Gauge.objects.filter(gauge_id="success_gauge_1").exists())
        self.assertTrue(Gauge.objects.filter(gauge_id="success_gauge_2").exists())

        # Should create 1 reading (only second success has model)
        self.assertEqual(Reading.objects.count(), 1)

        # Output should show mixed results
        output = out.getvalue()
        self.assertIn("Created: 2 gauges", output)
        self.assertIn("Error", output)

    @patch("requests.get")
    def test_handle_unexpected_api_response_format(self, mock_get):
        """Test handling of completely unexpected API response format."""
        # Mock response that's valid JSON but wrong structure
        mock_get.return_value = mock_api_response(
            200, {"unexpected": "format", "no": "expected fields", "data": [1, 2, 3]}
        )

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Should handle gracefully without crashing
        output = out.getvalue()
        self.assertIn("Error", output)

        # Should not create any gauges
        self.assertEqual(Gauge.objects.count(), 0)
