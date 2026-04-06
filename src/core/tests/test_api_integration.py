"""Comprehensive tests for Google Flood Hub API integration."""

import pytest
from unittest.mock import patch, Mock
import requests
from django.test import TestCase
from io import StringIO
from django.core.management import call_command

from core.models import Gauge, Reading
from core.tests.base import BaseTestCase
from core.tests.helpers import (
    mock_api_response,
    mock_api_sequence,
    assert_api_called_with,
)
from core.tests.fixtures.api_responses import (
    SAMPLE_GAUGE_RESPONSE,
    SAMPLE_THRESHOLD_RESPONSE,
    SAMPLE_FLOOD_STATUS_RESPONSE,
    ERROR_RESPONSES,
    MALFORMED_RESPONSES,
)


class TestGoogleFloodHubAPIIntegration(BaseTestCase):
    """Test Google Flood Hub API integration including success scenarios and error handling."""

    @patch("requests.get")
    def test_successful_api_response_handling(self, mock_get):
        """Test handling of successful API responses."""
        # Mock successful gauge and threshold responses
        mock_get.side_effect = [
            mock_api_response(200, SAMPLE_GAUGE_RESPONSE),
            mock_api_response(200, SAMPLE_THRESHOLD_RESPONSE),
        ]

        # Run fetch command
        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Verify API was called correctly
        assert_api_called_with(mock_get, "floodforecasting.googleapis.com/v1/gauges/")
        assert_api_called_with(
            mock_get, "floodforecasting.googleapis.com/v1/gaugeModels/", call_index=1
        )

        # Verify gauge was created
        gauge = self.assert_gauge_created(
            "hybas_4121489010",
            name="Chitral River Station",
            latitude=35.8462,
            longitude=71.7839,
            quality_verified=True,
            has_model=True,
        )

        # Verify reading was created with safe threshold value
        reading = self.assert_reading_created(
            gauge, water_level=8.0  # 80% of warning level (10.0)
        )

    @patch("requests.get")
    def test_404_error_handling(self, mock_get):
        """Test handling of 404 Not Found errors."""
        mock_get.return_value = mock_api_response(404, ERROR_RESPONSES["not_found"])

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Verify no gauge was created
        self.assertEqual(Gauge.objects.count(), 0)

        # Verify appropriate error message
        output = out.getvalue()
        self.assertIn("not found (404)", output)

    @patch("requests.get")
    def test_500_server_error_handling(self, mock_get):
        """Test handling of 500 Internal Server errors."""
        mock_get.return_value = mock_api_response(500, ERROR_RESPONSES["server_error"])

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Verify no gauge was created
        self.assertEqual(Gauge.objects.count(), 0)

        # Verify error handling
        output = out.getvalue()
        self.assertIn("Error", output)

    @patch("requests.get")
    def test_rate_limiting_handling(self, mock_get):
        """Test handling of API rate limiting (429 errors)."""
        mock_get.return_value = mock_api_response(429, ERROR_RESPONSES["rate_limited"])

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Verify no gauge was created
        self.assertEqual(Gauge.objects.count(), 0)

        # Verify rate limit handling
        output = out.getvalue()
        self.assertIn("Error", output)

    @patch("requests.get")
    def test_network_timeout_handling(self, mock_get):
        """Test handling of network timeouts."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Verify no gauge was created
        self.assertEqual(Gauge.objects.count(), 0)

        # Verify timeout handling
        output = out.getvalue()
        self.assertIn("Network error", output)

    @patch("requests.get")
    def test_malformed_json_response_handling(self, mock_get):
        """Test handling of malformed JSON responses."""
        # Create response that fails JSON parsing
        response = Mock()
        response.status_code = 200
        response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = response

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Verify no gauge was created
        self.assertEqual(Gauge.objects.count(), 0)

        # Verify error handling
        output = out.getvalue()
        self.assertIn("Error", output)

    @patch("requests.get")
    def test_missing_required_fields_handling(self, mock_get):
        """Test handling of API responses with missing required fields."""
        # Test with missing location
        mock_get.return_value = mock_api_response(
            200, MALFORMED_RESPONSES["missing_location"]
        )

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Command should handle gracefully - exact behavior depends on implementation
        # Either skip the gauge or use defaults
        output = out.getvalue()
        self.assertIn("Error", output)

    @patch("requests.get")
    def test_invalid_data_types_handling(self, mock_get):
        """Test handling of API responses with invalid data types."""
        # Test with invalid coordinates
        mock_get.return_value = mock_api_response(
            200, MALFORMED_RESPONSES["invalid_coordinates"]
        )

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Should handle invalid data gracefully
        output = out.getvalue()
        self.assertIn("Error", output)

    @patch("requests.get")
    def test_multiple_api_calls_with_mixed_responses(self, mock_get):
        """Test handling multiple API calls with mixed success/failure responses."""
        # Mock sequence: success, 404, success, network error
        mock_get.side_effect = [
            # First gauge - success
            mock_api_response(200, SAMPLE_GAUGE_RESPONSE),
            mock_api_response(200, SAMPLE_THRESHOLD_RESPONSE),
            # Second gauge - not found
            mock_api_response(404, ERROR_RESPONSES["not_found"]),
            # Third gauge - success but no threshold
            mock_api_response(
                200,
                {
                    "gaugeId": "hybas_4120000002",
                    "siteName": "Test Gauge 2",
                    "location": {"latitude": 30.0, "longitude": 70.0},
                    "qualityVerified": False,
                    "hasModel": False,
                },
            ),
            mock_api_response(404),  # No threshold data
            # Fourth gauge - network error
            requests.exceptions.ConnectionError("Network error"),
        ]

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=4", stdout=out)

        # Should create 2 gauges (first and third)
        self.assertEqual(Gauge.objects.count(), 2)

        # Should create 1 reading (only first gauge has threshold)
        self.assertEqual(Reading.objects.count(), 1)

        # Verify output shows mixed results
        output = out.getvalue()
        self.assertIn("Created:", output)
        self.assertIn("not found (404)", output)
        self.assertIn("Error", output)

    @patch("requests.get")
    def test_api_headers_included(self, mock_get):
        """Test that required API headers are included in requests."""
        mock_get.return_value = mock_api_response(404)

        call_command("fetch_google_flood_data", "--limit=1")

        # Verify API key header was included
        call_args = mock_get.call_args
        headers = call_args[1].get("headers", {})
        self.assertIn("X-goog-api-key", headers)
        self.assertEqual(headers["X-goog-api-key"], self.api_key)
