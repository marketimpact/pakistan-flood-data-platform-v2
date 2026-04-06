"""Base test case with common functionality."""

import os
from django.test import TestCase
from unittest.mock import Mock


class BaseTestCase(TestCase):
    """Base test case with common functionality for all tests."""

    def setUp(self):
        """Set up common test functionality."""
        # Set up API key for tests
        self.api_key = "test_api_key"
        os.environ["GOOGLE_FLOOD_HUB_API_KEY"] = self.api_key

        # Common test data
        self.test_gauge_id = "hybas_4121489010"
        self.test_latitude = 30.0
        self.test_longitude = 70.0

    def tearDown(self):
        """Clean up after tests."""
        # Clean up environment variables
        if "GOOGLE_FLOOD_HUB_API_KEY" in os.environ:
            del os.environ["GOOGLE_FLOOD_HUB_API_KEY"]

    def mock_api_response(self, status_code=200, json_data=None):
        """Create a mock API response object."""
        response = Mock()
        response.status_code = status_code

        if json_data is not None:
            response.json.return_value = json_data
        else:
            response.json.side_effect = ValueError("No JSON content")

        return response

    def mock_api_sequence(self, *responses):
        """Create a sequence of mock API responses."""
        return [self.mock_api_response(*resp) for resp in responses]

    def assert_gauge_created(self, gauge_id, **expected_fields):
        """Assert that a gauge was created with expected fields."""
        from core.models import Gauge

        gauge = Gauge.objects.get(gauge_id=gauge_id)

        for field, expected_value in expected_fields.items():
            actual_value = getattr(gauge, field)
            self.assertEqual(
                actual_value,
                expected_value,
                f"Gauge field '{field}' expected {expected_value}, got {actual_value}",
            )

        return gauge

    def assert_reading_created(self, gauge, **expected_fields):
        """Assert that a reading was created for a gauge."""
        from core.models import Reading

        reading = Reading.objects.filter(gauge=gauge).latest("timestamp")

        for field, expected_value in expected_fields.items():
            actual_value = getattr(reading, field)
            self.assertEqual(
                actual_value,
                expected_value,
                f"Reading field '{field}' expected {expected_value}, got {actual_value}",
            )

        return reading
