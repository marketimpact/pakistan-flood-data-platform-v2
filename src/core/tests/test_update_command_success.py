"""Success scenario tests for update_daily_readings command."""

from io import StringIO
from unittest.mock import patch
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta

from core.models import Gauge, Reading
from core.tests.base import BaseTestCase
from core.tests.factories import GaugeFactory, ReadingFactory
from core.tests.helpers import mock_api_response
from core.tests.fixtures.api_responses import SAMPLE_THRESHOLD_RESPONSE


class TestUpdateCommandSuccess(BaseTestCase):
    """Test successful data update scenarios for update_daily_readings command."""

    @patch("requests.get")
    def test_successful_real_api_data_update(self, mock_get):
        """Test successful update with real API flood status data."""
        # Create a gauge
        gauge = GaugeFactory(
            gauge_id="hybas_4121489010",
            name="Chitral River Station",
            quality_verified=True,
        )

        # Mock successful flood status response
        flood_status_response = {
            "gaugeId": "hybas_4121489010",
            "currentValue": 12.5,
            "severity": "MODERATE",
            "timestamp": "2025-07-16T12:00:00Z",
            "trend": "RISING",
        }

        mock_get.return_value = mock_api_response(200, flood_status_response)

        # Run command
        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Verify reading was created with real API data
        self.assertEqual(Reading.objects.count(), 1)
        reading = Reading.objects.first()
        self.assertEqual(reading.gauge, gauge)
        self.assertEqual(reading.water_level, 12.5)
        self.assertEqual(reading.flow_rate, 12.5)
        self.assertIsNotNone(reading.timestamp)

        # Verify output shows successful update
        output = out.getvalue()
        self.assertIn("✓ Updated Chitral River Station: 12.50 m³/s", output)
        self.assertIn("Updated: 1 gauges", output)
        self.assertIn("Daily update complete", output)

    @patch("requests.get")
    def test_threshold_based_fallback_values(self, mock_get):
        """Test fallback to threshold-based values when no current data available."""
        # Create gauge
        gauge = GaugeFactory(
            gauge_id="hybas_4121489010", name="Test Gauge", quality_verified=True
        )

        # Mock API responses: no flood status, but threshold data available
        mock_get.side_effect = [
            mock_api_response(404),  # No flood status
            mock_api_response(200, SAMPLE_THRESHOLD_RESPONSE),  # Threshold data
        ]

        # Run command
        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Verify reading was created
        self.assertEqual(Reading.objects.count(), 1)
        reading = Reading.objects.first()
        self.assertEqual(reading.gauge, gauge)

        # Value should be 70-90% of warning level (10.0)
        # So between 7.0 and 9.0
        self.assertGreaterEqual(reading.water_level, 7.0)
        self.assertLessEqual(reading.water_level, 9.0)
        self.assertEqual(reading.water_level, reading.flow_rate)

        # Verify output shows update
        output = out.getvalue()
        self.assertIn("✓ Updated Test Gauge", output)
        self.assertIn("Updated: 1 gauges", output)

    @patch("requests.get")
    def test_absolute_fallback_values(self, mock_get):
        """Test absolute fallback values when no API data is available."""
        # Create gauge
        gauge = GaugeFactory(
            gauge_id="hybas_4121489010", name="Fallback Gauge", quality_verified=False
        )

        # Mock API responses: no flood status, no threshold data
        mock_get.side_effect = [
            mock_api_response(404),  # No flood status
            mock_api_response(404),  # No threshold data
        ]

        # Run command
        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Verify reading was created with fallback value
        self.assertEqual(Reading.objects.count(), 1)
        reading = Reading.objects.first()
        self.assertEqual(reading.gauge, gauge)

        # Value should be between 1.0 and 5.0 (absolute fallback)
        self.assertGreaterEqual(reading.water_level, 1.0)
        self.assertLessEqual(reading.water_level, 5.0)
        self.assertEqual(reading.water_level, reading.flow_rate)

        # Verify output shows update with warning indicator
        output = out.getvalue()
        self.assertIn("⚠ Updated Fallback Gauge", output)
        self.assertIn("Updated: 1 gauges", output)

    @patch("requests.get")
    def test_quality_indicator_display(self, mock_get):
        """Test proper display of quality indicators for different gauge types."""
        # Create verified and unverified gauges
        verified_gauge = GaugeFactory(name="Verified Gauge", quality_verified=True)
        unverified_gauge = GaugeFactory(name="Unverified Gauge", quality_verified=False)

        # Mock responses for both gauges
        mock_get.return_value = mock_api_response(
            200, {"currentValue": 8.5, "severity": "NORMAL"}
        )

        # Run command
        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Verify both readings were created
        self.assertEqual(Reading.objects.count(), 2)

        # Verify output shows correct quality indicators
        output = out.getvalue()
        self.assertIn("✓ Updated Verified Gauge", output)  # Checkmark for verified
        self.assertIn("⚠ Updated Unverified Gauge", output)  # Warning for unverified
        self.assertIn("Updated: 2 gauges", output)

    @patch("requests.get")
    def test_multiple_gauge_updates(self, mock_get):
        """Test updating multiple gauges in a single command run."""
        # Create multiple gauges
        gauge1 = GaugeFactory(name="Gauge 1", quality_verified=True)
        gauge2 = GaugeFactory(name="Gauge 2", quality_verified=False)
        gauge3 = GaugeFactory(name="Gauge 3", quality_verified=True)

        # Mock different responses for each gauge
        mock_get.side_effect = [
            # Gauge 1: Real flood status
            mock_api_response(200, {"currentValue": 15.0}),
            # Gauge 2: No flood status, use threshold
            mock_api_response(404),
            mock_api_response(200, SAMPLE_THRESHOLD_RESPONSE),
            # Gauge 3: No flood status, no threshold (fallback)
            mock_api_response(404),
            mock_api_response(404),
        ]

        # Run command
        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Verify all readings were created
        self.assertEqual(Reading.objects.count(), 3)

        # Verify specific values
        reading1 = Reading.objects.get(gauge=gauge1)
        self.assertEqual(reading1.water_level, 15.0)

        reading2 = Reading.objects.get(gauge=gauge2)
        self.assertGreaterEqual(reading2.water_level, 7.0)
        self.assertLessEqual(reading2.water_level, 9.0)

        reading3 = Reading.objects.get(gauge=gauge3)
        self.assertGreaterEqual(reading3.water_level, 1.0)
        self.assertLessEqual(reading3.water_level, 5.0)

        # Verify output shows all updates
        output = out.getvalue()
        self.assertIn("✓ Updated Gauge 1: 15.00 m³/s", output)
        self.assertIn("⚠ Updated Gauge 2", output)
        self.assertIn("✓ Updated Gauge 3", output)
        self.assertIn("Updated: 3 gauges", output)

    @patch("requests.get")
    def test_force_flag_updates_recent_readings(self, mock_get):
        """Test --force flag successfully updates gauges with recent readings."""
        # Create gauge with recent reading
        gauge = GaugeFactory(name="Recent Gauge", quality_verified=True)

        # Create recent reading (12 hours ago)
        ReadingFactory(
            gauge=gauge, timestamp=timezone.now() - timedelta(hours=12), water_level=5.0
        )

        # Mock new API response
        mock_get.return_value = mock_api_response(
            200, {"currentValue": 10.0, "severity": "MODERATE"}
        )

        # Run command with force flag
        out = StringIO()
        call_command("update_daily_readings", "--force", stdout=out)

        # Verify new reading was created (should have 2 readings now)
        self.assertEqual(Reading.objects.count(), 2)

        # Verify latest reading has new value
        latest_reading = Reading.objects.latest("timestamp")
        self.assertEqual(latest_reading.water_level, 10.0)

        # Verify output shows update (not skip)
        output = out.getvalue()
        self.assertIn("✓ Updated Recent Gauge: 10.00 m³/s", output)
        self.assertNotIn("Skipped", output)

    @patch("requests.get")
    def test_mixed_success_and_skip_scenario(self, mock_get):
        """Test command handling mix of successful updates and skipped gauges."""
        # Create gauges with different reading states
        gauge1 = GaugeFactory(name="Recent Gauge")  # Has recent reading
        gauge2 = GaugeFactory(name="Update Gauge")  # No recent reading

        # Create recent reading for gauge1
        ReadingFactory(gauge=gauge1, timestamp=timezone.now() - timedelta(hours=12))

        # Mock API response (only called for gauge2)
        mock_get.return_value = mock_api_response(
            200, {"currentValue": 7.5, "severity": "NORMAL"}
        )

        # Run command
        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Should have 2 readings total (1 existing + 1 new)
        self.assertEqual(Reading.objects.count(), 2)

        # Verify only gauge2 got a new reading
        new_reading = Reading.objects.get(gauge=gauge2)
        self.assertEqual(new_reading.water_level, 7.5)

        # Verify output shows mixed results
        output = out.getvalue()
        self.assertIn("Skipped Recent Gauge", output)
        self.assertIn("Updated Update Gauge", output)
        self.assertIn("Updated: 1 gauges", output)
        self.assertIn("Skipped: 1 gauges", output)

    @patch("requests.get")
    def test_timestamp_accuracy(self, mock_get):
        """Test that readings are created with accurate timestamps."""
        gauge = GaugeFactory()

        # Mock API response
        mock_get.return_value = mock_api_response(
            200, {"currentValue": 8.0, "severity": "NORMAL"}
        )

        # Record time before command
        before_time = timezone.now()

        # Run command
        call_command("update_daily_readings")

        # Record time after command
        after_time = timezone.now()

        # Verify reading timestamp is within reasonable range
        reading = Reading.objects.first()
        self.assertGreaterEqual(reading.timestamp, before_time)
        self.assertLessEqual(reading.timestamp, after_time)

    @patch("requests.get")
    def test_api_call_sequence(self, mock_get):
        """Test correct sequence of API calls for different scenarios."""
        gauge = GaugeFactory(gauge_id="test_gauge")

        # Mock sequence: flood status succeeds
        mock_get.return_value = mock_api_response(
            200, {"currentValue": 12.0, "severity": "MODERATE"}
        )

        # Run command
        call_command("update_daily_readings")

        # Verify API was called with correct URL
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertIn("floodStatus/test_gauge", call_args[0][0])

        # Verify headers were set correctly
        headers = call_args[1]["headers"]
        self.assertIn("X-goog-api-key", headers)
        self.assertEqual(headers["X-goog-api-key"], self.api_key)

        # Verify timeout was set
        self.assertEqual(call_args[1]["timeout"], 30)

    @patch("requests.get")
    def test_threshold_fallback_api_sequence(self, mock_get):
        """Test API call sequence when falling back to threshold data."""
        gauge = GaugeFactory(gauge_id="test_gauge")

        # Mock sequence: flood status fails, threshold succeeds
        mock_get.side_effect = [
            mock_api_response(404),  # No flood status
            mock_api_response(200, SAMPLE_THRESHOLD_RESPONSE),  # Threshold data
        ]

        # Run command
        call_command("update_daily_readings")

        # Verify both API calls were made
        self.assertEqual(mock_get.call_count, 2)

        # Verify first call was for flood status
        first_call = mock_get.call_args_list[0]
        self.assertIn("floodStatus/test_gauge", first_call[0][0])

        # Verify second call was for threshold
        second_call = mock_get.call_args_list[1]
        self.assertIn("gaugeModels/test_gauge", second_call[0][0])

    @patch("requests.get")
    def test_comprehensive_success_summary(self, mock_get):
        """Test comprehensive success summary with detailed statistics."""
        # Create various gauge scenarios
        GaugeFactory.create_batch(5)

        # Mock successful response for all
        mock_get.return_value = mock_api_response(
            200, {"currentValue": 9.0, "severity": "NORMAL"}
        )

        # Run command
        out = StringIO()
        call_command("update_daily_readings", stdout=out)

        # Verify all readings created
        self.assertEqual(Reading.objects.count(), 5)

        # Verify comprehensive summary
        output = out.getvalue()
        self.assertIn("Daily update complete", output)
        self.assertIn("Updated: 5 gauges", output)
        self.assertIn("Skipped: 0 gauges", output)
        self.assertIn("Errors: 0 gauges", output)
        self.assertIn("Total processed: 5/5", output)

        # Should not show force flag hint (no skipped gauges)
        self.assertNotIn("Use --force", output)
