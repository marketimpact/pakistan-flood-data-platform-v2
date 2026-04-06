"""Success scenario tests for fetch_google_flood_data command."""

from io import StringIO
from unittest.mock import patch, Mock
from django.core.management import call_command
from django.utils import timezone

from core.models import Gauge, Reading
from core.tests.base import BaseTestCase
from core.tests.factories import GaugeFactory
from core.tests.helpers import mock_api_response
from core.tests.fixtures.api_responses import (
    SAMPLE_GAUGE_RESPONSE,
    SAMPLE_THRESHOLD_RESPONSE,
    PAKISTANI_GAUGE_SAMPLES,
)


class TestFetchCommandSuccess(BaseTestCase):
    """Test successful data collection scenarios for fetch_google_flood_data."""

    @patch("requests.get")
    def test_create_new_gauge(self, mock_get):
        """Test creating a new gauge from API data."""
        # Setup mock responses
        gauge_data = {
            "gaugeId": "hybas_4121489010",
            "siteName": "Indus River at Tarbela",
            "location": {"latitude": 34.0885, "longitude": 72.6986},
            "qualityVerified": True,
            "hasModel": True,
            "river": "Indus River",
        }

        threshold_data = {
            "thresholds": {
                "warningLevel": 15.0,
                "dangerLevel": 20.0,
                "extremeDangerLevel": 25.0,
            }
        }

        mock_get.side_effect = [
            mock_api_response(200, gauge_data),
            mock_api_response(200, threshold_data),
        ]

        # Run command
        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Verify gauge created
        self.assertEqual(Gauge.objects.count(), 1)
        gauge = Gauge.objects.first()
        self.assertEqual(gauge.gauge_id, "hybas_4121489010")
        self.assertEqual(gauge.name, "Indus River at Tarbela")
        self.assertEqual(gauge.latitude, 34.0885)
        self.assertEqual(gauge.longitude, 72.6986)
        self.assertTrue(gauge.quality_verified)
        self.assertTrue(gauge.has_model)
        self.assertEqual(gauge.location, "Northern Pakistan (KPK/Kashmir)")

        # Verify reading created
        self.assertEqual(Reading.objects.count(), 1)
        reading = Reading.objects.first()
        self.assertEqual(reading.gauge, gauge)
        self.assertEqual(reading.water_level, 12.0)  # 80% of warning level
        self.assertEqual(reading.flow_rate, 12.0)

        # Verify output
        output = out.getvalue()
        self.assertIn("Created: Indus River at Tarbela [✓ VERIFIED]", output)
        self.assertIn("Created: 1 gauges", output)

    @patch("requests.get")
    def test_update_existing_gauge(self, mock_get):
        """Test updating an existing gauge with new data."""
        # Create existing gauge with old data
        existing_gauge = GaugeFactory(
            gauge_id="hybas_4121489010",
            name="Old Name",
            quality_verified=False,
            has_model=False,
        )

        # Mock updated data from API
        updated_gauge_data = {
            "gaugeId": "hybas_4121489010",
            "siteName": "Updated Name",
            "location": {"latitude": 34.0885, "longitude": 72.6986},
            "qualityVerified": True,
            "hasModel": True,
            "river": "Indus River",
        }

        mock_get.side_effect = [
            mock_api_response(200, updated_gauge_data),
            mock_api_response(404),  # No threshold data
        ]

        # Run command
        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Verify gauge was updated
        gauge = Gauge.objects.get(gauge_id="hybas_4121489010")
        self.assertEqual(gauge.name, "Updated Name")
        self.assertTrue(gauge.quality_verified)
        self.assertTrue(gauge.has_model)

        # Verify only one gauge exists (not duplicated)
        self.assertEqual(Gauge.objects.count(), 1)

        # Verify output
        output = out.getvalue()
        self.assertIn("Updated: Updated Name", output)

    @patch("requests.get")
    def test_quality_filter_functionality(self, mock_get):
        """Test --quality-only flag filters correctly."""
        # Mock responses for quality and non-quality gauges
        responses = []

        # Quality verified gauge
        responses.extend(
            [
                mock_api_response(
                    200,
                    {
                        "gaugeId": "quality_1",
                        "siteName": "Quality Gauge",
                        "qualityVerified": True,
                        "location": {"latitude": 30, "longitude": 70},
                    },
                ),
                mock_api_response(404),  # No threshold
            ]
        )

        # Non-quality gauge (should be skipped with --quality-only)
        responses.extend(
            [
                mock_api_response(
                    200,
                    {
                        "gaugeId": "non_quality_1",
                        "siteName": "Non-Quality Gauge",
                        "qualityVerified": False,
                        "location": {"latitude": 31, "longitude": 71},
                    },
                ),
                mock_api_response(404),
            ]
        )

        # Another quality gauge
        responses.extend(
            [
                mock_api_response(
                    200,
                    {
                        "gaugeId": "quality_2",
                        "siteName": "Quality Gauge 2",
                        "qualityVerified": True,
                        "location": {"latitude": 32, "longitude": 72},
                    },
                ),
                mock_api_response(404),
            ]
        )

        mock_get.side_effect = responses

        # Run with quality filter
        out = StringIO()
        call_command(
            "fetch_google_flood_data", "--limit=3", "--quality-only", stdout=out
        )

        # Only quality verified gauges should be created
        self.assertEqual(Gauge.objects.count(), 2)
        self.assertEqual(Gauge.objects.filter(quality_verified=True).count(), 2)
        self.assertFalse(Gauge.objects.filter(gauge_id="non_quality_1").exists())

        # Verify output doesn't show skipped gauge
        output = out.getvalue()
        self.assertNotIn("Non-Quality Gauge", output)

    @patch("requests.get")
    def test_threshold_data_handling(self, mock_get):
        """Test proper handling of threshold data to create readings."""
        # Mock gauge with comprehensive threshold data
        mock_get.side_effect = [
            mock_api_response(200, SAMPLE_GAUGE_RESPONSE),
            mock_api_response(200, SAMPLE_THRESHOLD_RESPONSE),
        ]

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Verify reading created with correct threshold-based value
        reading = Reading.objects.first()
        self.assertIsNotNone(reading)
        # Should be 80% of warning level (10.0 * 0.8 = 8.0)
        self.assertEqual(reading.water_level, 8.0)
        self.assertEqual(reading.flow_rate, 8.0)

    @patch("requests.get")
    def test_gauge_without_threshold_data(self, mock_get):
        """Test handling gauges without threshold data."""
        # Mock gauge with no threshold data available
        mock_get.side_effect = [
            mock_api_response(
                200,
                {
                    "gaugeId": "no_threshold_gauge",
                    "siteName": "Gauge Without Thresholds",
                    "location": {"latitude": 30, "longitude": 70},
                    "qualityVerified": True,
                    "hasModel": False,
                },
            ),
            mock_api_response(404),  # No threshold data
        ]

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=1", stdout=out)

        # Gauge should be created
        self.assertEqual(Gauge.objects.count(), 1)
        gauge = Gauge.objects.first()
        self.assertEqual(gauge.gauge_id, "no_threshold_gauge")

        # No reading should be created without threshold data
        self.assertEqual(Reading.objects.count(), 0)

    @patch("requests.get")
    def test_multiple_gauge_creation(self, mock_get):
        """Test creating multiple gauges in one command run."""
        # Mock responses for 3 different gauges
        responses = []

        for i, gauge_sample in enumerate(PAKISTANI_GAUGE_SAMPLES[:3]):
            responses.append(mock_api_response(200, gauge_sample))
            if gauge_sample.get("hasModel"):
                responses.append(mock_api_response(200, SAMPLE_THRESHOLD_RESPONSE))
            else:
                responses.append(mock_api_response(404))

        mock_get.side_effect = responses

        out = StringIO()
        call_command("fetch_google_flood_data", "--limit=3", stdout=out)

        # Should create all 3 gauges
        self.assertEqual(Gauge.objects.count(), 3)

        # Verify gauge details
        for gauge_sample in PAKISTANI_GAUGE_SAMPLES[:3]:
            gauge = Gauge.objects.get(gauge_id=gauge_sample["gaugeId"])
            self.assertEqual(gauge.name, gauge_sample["siteName"])
            self.assertEqual(gauge.quality_verified, gauge_sample["qualityVerified"])

        # Only gauges with models should have readings
        gauges_with_models = [
            g for g in PAKISTANI_GAUGE_SAMPLES[:3] if g.get("hasModel")
        ]
        self.assertEqual(Reading.objects.count(), len(gauges_with_models))

        # Verify output summary
        output = out.getvalue()
        self.assertIn("Created: 3 gauges", output)

    @patch("requests.get")
    def test_location_classification(self, mock_get):
        """Test correct classification of gauge locations based on coordinates."""
        test_cases = [
            # Northern Pakistan (lat >= 32)
            {"lat": 35.0, "lon": 72.0, "expected": "Northern Pakistan (KPK/Kashmir)"},
            # Central Pakistan (28 <= lat < 32)
            {"lat": 30.0, "lon": 70.0, "expected": "Central Pakistan (Punjab)"},
            # Southern Pakistan (lat < 28)
            {
                "lat": 25.0,
                "lon": 68.0,
                "expected": "Southern Pakistan (Sindh/Balochistan)",
            },
        ]

        for test_case in test_cases:
            Gauge.objects.all().delete()  # Clear between tests

            mock_get.side_effect = [
                mock_api_response(
                    200,
                    {
                        "gaugeId": f'test_{test_case["lat"]}',
                        "siteName": "Test Gauge",
                        "location": {
                            "latitude": test_case["lat"],
                            "longitude": test_case["lon"],
                        },
                        "qualityVerified": True,
                    },
                ),
                mock_api_response(404),
            ]

            call_command("fetch_google_flood_data", "--limit=1")

            gauge = Gauge.objects.first()
            self.assertEqual(gauge.location, test_case["expected"])
