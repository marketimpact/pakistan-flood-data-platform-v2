"""Skip logic tests for update_daily_readings command."""

from io import StringIO
from unittest.mock import patch
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta

from core.models import Gauge, Reading
from core.tests.base import BaseTestCase
from core.tests.factories import GaugeFactory, ReadingFactory
from core.tests.helpers import mock_api_response


class TestUpdateCommandSkip(BaseTestCase):
    """Test skip logic and behavior for update_daily_readings command."""

    def test_24_hour_threshold_checking(self):
        """Test that gauges with readings within 24 hours are skipped."""
        # Create gauge with reading exactly at 24 hour boundary
        gauge = GaugeFactory(name="Boundary Gauge")
        ReadingFactory(
            gauge=gauge,
            timestamp=timezone.now()
            - timedelta(hours=24, minutes=1),  # Just over 24 hours
        )

        # Create gauge with reading within 24 hours
        gauge2 = GaugeFactory(name="Recent Gauge")
        ReadingFactory(
            gauge=gauge2,
            timestamp=timezone.now()
            - timedelta(hours=23, minutes=59),  # Just under 24 hours
        )

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(200, {"currentValue": 10.0})

            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            output = out.getvalue()

            # Gauge with >24h reading should be updated
            self.assertIn("Updated Boundary Gauge", output)
            self.assertNotIn("Skipped Boundary Gauge", output)

            # Gauge with <24h reading should be skipped
            self.assertIn("Skipped Recent Gauge", output)
            self.assertNotIn("Updated Recent Gauge", output)

    def test_exact_24_hour_boundary(self):
        """Test exact 24-hour boundary behavior."""
        # Create gauge with reading exactly 24 hours ago
        gauge = GaugeFactory(name="Exact Boundary Gauge")
        ReadingFactory(gauge=gauge, timestamp=timezone.now() - timedelta(hours=24))

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(200, {"currentValue": 10.0})

            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            output = out.getvalue()

            # Reading exactly 24 hours ago should be eligible for update
            self.assertIn("Updated Exact Boundary Gauge", output)
            self.assertNotIn("Skipped Exact Boundary Gauge", output)

    def test_multiple_readings_uses_most_recent(self):
        """Test that skip logic uses the most recent reading for each gauge."""
        gauge = GaugeFactory(name="Multi Reading Gauge")

        # Create multiple readings, most recent is within 24 hours
        ReadingFactory(
            gauge=gauge, timestamp=timezone.now() - timedelta(hours=48)  # Old reading
        )
        ReadingFactory(
            gauge=gauge, timestamp=timezone.now() - timedelta(hours=36)  # Older reading
        )
        ReadingFactory(
            gauge=gauge,
            timestamp=timezone.now()
            - timedelta(hours=12),  # Recent reading (should cause skip)
        )

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(200, {"currentValue": 10.0})

            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            output = out.getvalue()

            # Should be skipped because most recent reading is within 24 hours
            self.assertIn("Skipped Multi Reading Gauge", output)
            self.assertNotIn("Updated Multi Reading Gauge", output)

    def test_force_flag_override_behavior(self):
        """Test that --force flag overrides skip logic."""
        # Create gauge with recent reading
        gauge = GaugeFactory(name="Force Test Gauge")
        ReadingFactory(gauge=gauge, timestamp=timezone.now() - timedelta(hours=12))

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(200, {"currentValue": 15.0})

            # First run without force - should skip
            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            output = out.getvalue()
            self.assertIn("Skipped Force Test Gauge", output)
            self.assertNotIn("Updated Force Test Gauge", output)

            # Second run with force - should update
            out = StringIO()
            call_command("update_daily_readings", "--force", stdout=out)

            output = out.getvalue()
            self.assertIn("Updated Force Test Gauge", output)
            self.assertNotIn("Skipped Force Test Gauge", output)

    def test_skip_count_reporting(self):
        """Test accurate skip count reporting in command summary."""
        # Create gauges with different reading states
        gauge1 = GaugeFactory(name="Skip 1")
        gauge2 = GaugeFactory(name="Skip 2")
        gauge3 = GaugeFactory(name="Skip 3")
        gauge4 = GaugeFactory(name="Update 1")
        gauge5 = GaugeFactory(name="Update 2")

        # Create recent readings for first 3 gauges
        for gauge in [gauge1, gauge2, gauge3]:
            ReadingFactory(gauge=gauge, timestamp=timezone.now() - timedelta(hours=12))

        # Create old readings for last 2 gauges
        for gauge in [gauge4, gauge5]:
            ReadingFactory(gauge=gauge, timestamp=timezone.now() - timedelta(hours=36))

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(200, {"currentValue": 10.0})

            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            output = out.getvalue()

            # Verify skip count is accurate
            self.assertIn("Skipped: 3 gauges", output)
            self.assertIn("Updated: 2 gauges", output)
            self.assertIn("Total processed: 5/5", output)

    def test_skip_reason_messaging(self):
        """Test that skip messages include proper reasoning."""
        gauge = GaugeFactory(name="Skip Reason Gauge")
        ReadingFactory(gauge=gauge, timestamp=timezone.now() - timedelta(hours=18))

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(200, {"currentValue": 10.0})

            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            output = out.getvalue()

            # Should explain why it was skipped
            self.assertIn("Skipped Skip Reason Gauge - Recent reading exists", output)

    def test_force_flag_hint_display(self):
        """Test that force flag hint is displayed when gauges are skipped."""
        # Create gauge with recent reading
        gauge = GaugeFactory(name="Hint Test Gauge")
        ReadingFactory(gauge=gauge, timestamp=timezone.now() - timedelta(hours=12))

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(200, {"currentValue": 10.0})

            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            output = out.getvalue()

            # Should show force flag hint
            self.assertIn("Use --force to update gauges with recent readings", output)

    def test_no_force_hint_when_no_skips(self):
        """Test that force flag hint is not shown when no gauges are skipped."""
        # Create gauge without recent reading
        gauge = GaugeFactory(name="No Skip Gauge")
        ReadingFactory(gauge=gauge, timestamp=timezone.now() - timedelta(hours=36))

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(200, {"currentValue": 10.0})

            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            output = out.getvalue()

            # Should not show force flag hint
            self.assertNotIn("Use --force", output)

    def test_skip_logic_with_force_flag(self):
        """Test that skip logic is completely bypassed with force flag."""
        # Create multiple gauges with recent readings
        gauges = []
        for i in range(3):
            gauge = GaugeFactory(name=f"Force Skip {i+1}")
            ReadingFactory(
                gauge=gauge,
                timestamp=timezone.now() - timedelta(hours=6),  # Very recent
            )
            gauges.append(gauge)

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(200, {"currentValue": 10.0})

            out = StringIO()
            call_command("update_daily_readings", "--force", stdout=out)

            output = out.getvalue()

            # All gauges should be updated, none skipped
            self.assertIn("Updated: 3 gauges", output)
            self.assertIn("Skipped: 0 gauges", output)
            self.assertNotIn("Skipped Force Skip", output)

    def test_mixed_skip_and_update_scenarios(self):
        """Test complex scenarios with mixed skip and update situations."""
        # Create various gauge scenarios
        skip_gauge_1 = GaugeFactory(name="Skip 1")
        skip_gauge_2 = GaugeFactory(name="Skip 2")
        update_gauge_1 = GaugeFactory(name="Update 1")
        update_gauge_2 = GaugeFactory(name="Update 2")
        no_reading_gauge = GaugeFactory(name="No Reading")

        # Recent readings (should skip)
        ReadingFactory(
            gauge=skip_gauge_1, timestamp=timezone.now() - timedelta(hours=6)
        )
        ReadingFactory(
            gauge=skip_gauge_2, timestamp=timezone.now() - timedelta(hours=18)
        )

        # Old readings (should update)
        ReadingFactory(
            gauge=update_gauge_1, timestamp=timezone.now() - timedelta(hours=30)
        )
        ReadingFactory(
            gauge=update_gauge_2, timestamp=timezone.now() - timedelta(hours=48)
        )

        # No reading at all (should update)
        # no_reading_gauge has no readings

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(200, {"currentValue": 10.0})

            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            output = out.getvalue()

            # Verify correct skip/update behavior
            self.assertIn("Skipped Skip 1", output)
            self.assertIn("Skipped Skip 2", output)
            self.assertIn("Updated Update 1", output)
            self.assertIn("Updated Update 2", output)
            self.assertIn("Updated No Reading", output)

            # Verify counts
            self.assertIn("Skipped: 2 gauges", output)
            self.assertIn("Updated: 3 gauges", output)
            self.assertIn("Total processed: 5/5", output)

    def test_progress_indicators_for_skipped_gauges(self):
        """Test that progress indicators are shown for skipped gauges."""
        # Create multiple gauges that will be skipped
        for i in range(3):
            gauge = GaugeFactory(name=f"Skip Progress {i+1}")
            ReadingFactory(gauge=gauge, timestamp=timezone.now() - timedelta(hours=12))

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(200, {"currentValue": 10.0})

            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            output = out.getvalue()

            # Should show progress indicators for skipped gauges
            self.assertIn("[1/3] Skipped Skip Progress 1", output)
            self.assertIn("[2/3] Skipped Skip Progress 2", output)
            self.assertIn("[3/3] Skipped Skip Progress 3", output)

    def test_skip_with_different_timezone_readings(self):
        """Test skip logic works correctly across different timezones."""
        # Create gauge with reading in a specific timezone context
        gauge = GaugeFactory(name="Timezone Test Gauge")

        # Create reading 23 hours ago (should be skipped)
        ReadingFactory(gauge=gauge, timestamp=timezone.now() - timedelta(hours=23))

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(200, {"currentValue": 10.0})

            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            output = out.getvalue()

            # Should be skipped regardless of timezone
            self.assertIn("Skipped Timezone Test Gauge", output)

    def test_skip_count_accuracy_with_errors(self):
        """Test skip count accuracy when some gauges have errors."""
        # Create mixed scenario: skips, updates, and errors
        skip_gauge = GaugeFactory(name="Skip Gauge")
        update_gauge = GaugeFactory(name="Update Gauge")
        error_gauge = GaugeFactory(name="Error Gauge", gauge_id="error_id")

        # Recent reading for skip gauge
        ReadingFactory(gauge=skip_gauge, timestamp=timezone.now() - timedelta(hours=12))

        # Old reading for update gauge
        ReadingFactory(
            gauge=update_gauge, timestamp=timezone.now() - timedelta(hours=36)
        )

        # No reading for error gauge (will cause API call)

        with patch("requests.get") as mock_get:
            # Mock: success for update_gauge, error for error_gauge
            mock_get.side_effect = [
                mock_api_response(200, {"currentValue": 10.0}),  # update_gauge
                mock_api_response(500, {"error": "Server error"}),  # error_gauge
            ]

            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            output = out.getvalue()

            # Verify accurate counting
            self.assertIn("Skipped: 1 gauges", output)
            self.assertIn("Updated: 1 gauges", output)
            self.assertIn("Errors: 1 gauges", output)
            self.assertIn("Total processed: 3/3", output)

    def test_skip_behavior_with_null_timestamps(self):
        """Test skip logic handles edge cases with timestamp data."""
        # Create gauge and ensure it has no recent readings
        gauge = GaugeFactory(name="Clean Gauge")

        # Ensure no readings exist
        Reading.objects.filter(gauge=gauge).delete()

        with patch("requests.get") as mock_get:
            mock_get.return_value = mock_api_response(200, {"currentValue": 10.0})

            out = StringIO()
            call_command("update_daily_readings", stdout=out)

            output = out.getvalue()

            # Should be updated (no recent readings)
            self.assertIn("Updated Clean Gauge", output)
            self.assertNotIn("Skipped Clean Gauge", output)
