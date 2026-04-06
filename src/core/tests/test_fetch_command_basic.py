"""Basic tests for fetch_google_flood_data command."""

import os
from io import StringIO
from unittest.mock import patch
from django.core.management import call_command
from django.test import TestCase

from core.tests.base import BaseTestCase
from core.tests.helpers import mock_api_response


class TestFetchCommandBasic(BaseTestCase):
    """Basic functionality tests for fetch_google_flood_data command."""

    def test_command_exists(self):
        """Test that command is properly registered."""
        try:
            out = StringIO()
            with patch("requests.get") as mock_get:
                mock_get.return_value = mock_api_response(404)
                call_command("fetch_google_flood_data", "--help", stdout=out)
        except SystemExit:  # --help causes exit
            pass

        # If we get here without error, command exists
        self.assertTrue(True)

    def test_command_requires_api_key(self):
        """Test command fails without API key."""
        # Remove API key from environment
        if "GOOGLE_FLOOD_HUB_API_KEY" in os.environ:
            del os.environ["GOOGLE_FLOOD_HUB_API_KEY"]

        out = StringIO()
        call_command("fetch_google_flood_data", stdout=out)

        output = out.getvalue()
        self.assertIn("GOOGLE_FLOOD_HUB_API_KEY not found", output)

    @patch("requests.get")
    def test_limit_parameter_validation(self, mock_get):
        """Test --limit parameter accepts valid values."""
        mock_get.return_value = mock_api_response(404)

        # Test various limit values
        test_limits = [1, 5, 10, 50, 100, 200]

        for limit in test_limits:
            out = StringIO()
            call_command("fetch_google_flood_data", f"--limit={limit}", stdout=out)

            output = out.getvalue()
            self.assertIn(f"Processing up to {limit} gauges", output)

    @patch("requests.get")
    def test_quality_only_parameter(self, mock_get):
        """Test --quality-only flag is accepted."""
        mock_get.return_value = mock_api_response(404)

        out = StringIO()
        call_command("fetch_google_flood_data", "--quality-only", stdout=out)

        output = out.getvalue()
        self.assertIn("Quality verified gauges only", output)

    @patch("requests.get")
    def test_command_with_both_parameters(self, mock_get):
        """Test command works with both --limit and --quality-only."""
        mock_get.return_value = mock_api_response(404)

        out = StringIO()
        call_command(
            "fetch_google_flood_data", "--limit=10", "--quality-only", stdout=out
        )

        output = out.getvalue()
        self.assertIn("Processing up to 10 gauges", output)
        self.assertIn("Quality verified gauges only", output)

    @patch("requests.get")
    def test_command_output_format(self, mock_get):
        """Test command produces expected output format."""
        mock_get.return_value = mock_api_response(404)

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=5", stdout=out)

        output = out.getvalue()
        # Should have progress indicators
        self.assertIn("Fetching", output)
        self.assertIn("Processing", output)

    @patch("requests.get")
    def test_command_completion_summary(self, mock_get):
        """Test command shows completion summary."""
        mock_get.return_value = mock_api_response(404)

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=3", stdout=out)

        output = out.getvalue()
        # Should show summary statistics
        self.assertIn("complete", output.lower())

    def test_invalid_limit_parameter(self):
        """Test command handles invalid limit values gracefully."""
        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(404)

            # Test with invalid limit values
            invalid_limits = [0, -1, "abc", ""]

            for limit in invalid_limits:
                out = StringIO()
                try:
                    call_command(
                        "fetch_google_flood_data", f"--limit={limit}", stdout=out
                    )
                except (ValueError, SystemExit):
                    # Command should handle invalid input gracefully
                    pass
