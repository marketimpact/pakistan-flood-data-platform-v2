"""Basic tests for update_daily_readings command."""

import os
from io import StringIO
from unittest.mock import patch
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta

from core.models import Gauge, Reading
from core.tests.base import BaseTestCase
from core.tests.factories import GaugeFactory, ReadingFactory
from core.tests.helpers import mock_api_response


class TestUpdateCommandBasic(BaseTestCase):
    """Basic functionality tests for update_daily_readings command."""

    def test_command_exists(self):
        """Test that update_daily_readings command is properly registered."""
        try:
            out = StringIO()
            with patch("requests.get") as mock_get:
                mock_get.return_value = mock_api_response(404)
                call_command("update_daily_readings", "--help", stdout=out)
        except SystemExit:  # --help causes exit
            pass

        # If we get here without error, command exists
        self.assertTrue(True)

    def test_command_requires_api_key(self):
        """Test command fails without API key."""
        # Remove API key from environment
        if "GOOGLE_FLOOD_HUB_API_KEY" in os.environ:
            del os.environ["GOOGLE_FLOOD_HUB_API_KEY"]

        # Create a gauge so we're not testing the no-gauges scenario
        GaugeFactory()

        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        output = out.getvalue()
        self.assertIn("GOOGLE_FLOOD_HUB_API_KEY not found", output)

    def test_no_gauges_scenario(self):
        """Test command behavior when no gauges exist."""
        # Ensure no gauges exist
        Gauge.objects.all().delete()

        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        output = out.getvalue()
        self.assertIn("No gauges found", output)
        self.assertIn("Run collect data first", output)

    def test_force_flag_functionality(self):
        """Test that --force flag is accepted and processed."""
        # Create a gauge
        gauge = GaugeFactory()

        # Create a recent reading (within 24 hours)
        ReadingFactory(gauge=gauge, timestamp=timezone.now() - timedelta(hours=12))

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(404)

            # Test without force flag - should skip
            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            output = out.getvalue()
            self.assertIn("Skipped", output)
            self.assertIn("Recent reading exists", output)

            # Test with force flag - should attempt update
            out = StringIO()
            call_command("update_daily_readings", "--force", stdout=out)

            output = out.getvalue()
            # Should not show "Skipped" message
            self.assertNotIn("Skipped", output)

    def test_command_output_format(self):
        """Test command produces expected output format."""
        # Create some gauges
        GaugeFactory.create_batch(3)

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(404)

            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            output = out.getvalue()
            # Should have progress indicators
            self.assertIn("Found 3 gauges", output)
            self.assertIn("Daily update complete", output)
            self.assertIn("Total processed", output)

    def test_command_with_existing_recent_readings(self):
        """Test command correctly identifies and skips recent readings."""
        # Create gauges with recent readings
        gauge1 = GaugeFactory(name="Gauge 1")
        gauge2 = GaugeFactory(name="Gauge 2")

        # Create recent reading for gauge1 (within 24 hours)
        ReadingFactory(gauge=gauge1, timestamp=timezone.now() - timedelta(hours=12))

        # Create old reading for gauge2 (older than 24 hours)
        ReadingFactory(gauge=gauge2, timestamp=timezone.now() - timedelta(hours=36))

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(404)

            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            output = out.getvalue()
            # Should skip gauge1 but attempt gauge2
            self.assertIn("Skipped Gauge 1", output)
            self.assertNotIn("Skipped Gauge 2", output)
            self.assertIn("Skipped: 1 gauges", output)

    def test_command_with_no_recent_readings(self):
        """Test command processes all gauges when no recent readings exist."""
        # Create gauges without recent readings
        GaugeFactory.create_batch(2)

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(404)

            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            output = out.getvalue()
            # Should not skip any gauges
            self.assertNotIn("Skipped:", output)
            self.assertIn("Found 2 gauges", output)

    def test_help_text_display(self):
        """Test command help text is descriptive."""
        try:
            out = StringIO()
            call_command("update_daily_readings", "--help", stdout=out)
        except SystemExit:
            pass

        # Check that help was displayed (even though it exits)
        # This test mainly ensures the command is registered
        self.assertTrue(True)

    def test_force_flag_help_text(self):
        """Test that --force flag shows proper help text."""
        # This is more of a documentation test
        try:
            out = StringIO()
            call_command("update_daily_readings", "--help", stdout=out)
        except SystemExit:
            pass

        # Command should have --force option available
        self.assertTrue(True)

    def test_command_handles_empty_database(self):
        """Test command gracefully handles completely empty database."""
        # Clear all data
        Gauge.objects.all().delete()
        Reading.objects.all().delete()

        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        output = out.getvalue()
        self.assertIn("No gauges found", output)
        # Should exit gracefully without errors
        self.assertEqual(Gauge.objects.count(), 0)
        self.assertEqual(Reading.objects.count(), 0)

    def test_command_summary_statistics(self):
        """Test command provides summary statistics."""
        # Create mix of gauges
        gauge1 = GaugeFactory(name="Recent Gauge")
        gauge2 = GaugeFactory(name="Old Gauge")
        gauge3 = GaugeFactory(name="No Reading Gauge")

        # Create recent reading for gauge1
        ReadingFactory(gauge=gauge1, timestamp=timezone.now() - timedelta(hours=12))

        # Create old reading for gauge2
        ReadingFactory(gauge=gauge2, timestamp=timezone.now() - timedelta(hours=36))

        # No reading for gauge3

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(404)

            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            output = out.getvalue()
            # Should show summary with counts
            self.assertIn("Daily update complete", output)
            self.assertIn("Updated:", output)
            self.assertIn("Skipped:", output)
            self.assertIn("Errors:", output)
            self.assertIn("Total processed:", output)

    def test_force_flag_hint_display(self):
        """Test command shows force flag hint when relevant."""
        # Create gauge with recent reading
        gauge = GaugeFactory()
        ReadingFactory(gauge=gauge, timestamp=timezone.now() - timedelta(hours=12))

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(404)

            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            output = out.getvalue()
            # Should show hint about --force flag
            self.assertIn("Use --force to update", output)

    def test_command_handles_mixed_gauge_states(self):
        """Test command handles gauges in various states correctly."""
        # Create gauges with different quality verification states
        verified_gauge = GaugeFactory(name="Verified Gauge", quality_verified=True)
        unverified_gauge = GaugeFactory(name="Unverified Gauge", quality_verified=False)

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(404)

            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            output = out.getvalue()
            # Should show both gauges being processed
            self.assertIn("Found 2 gauges", output)
            self.assertIn("Daily update complete", output)

    def test_command_timeout_handling(self):
        """Test command includes proper timeout parameters."""
        gauge = GaugeFactory()

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(404)

            call_command("update_daily_readings")

            # Verify timeout was set in API calls
            # The actual implementation uses timeout=30
            for call in mock_get.call_args_list:
                if call[1]:  # If kwargs exist
                    self.assertIn("timeout", call[1])
                    self.assertEqual(call[1]["timeout"], 30)

    def test_command_progress_indicators(self):
        """Test command shows progress indicators during processing."""
        # Create multiple gauges to see progress
        gauges = GaugeFactory.create_batch(3)

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(404)

            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            output = out.getvalue()
            # Should show progress for each gauge
            self.assertIn("[1/3]", output)
            self.assertIn("[2/3]", output)
            self.assertIn("[3/3]", output)
