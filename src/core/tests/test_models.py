import uuid
from django.test import TestCase
from django.utils import timezone
from ..models import Gauge, Reading, Prediction


class GaugeModelTests(TestCase):
    def test_create_gauge(self):
        """
        Test that a Gauge model instance can be
        created successfully.
        This test is expected to fail initially.
        """
        gauge = Gauge.objects.create(
            gauge_id="12345",
            source="google_flood_hub",
            name="Test Gauge",
            location="Test Location",
            latitude=12.34,
            longitude=56.78,
            country_code="PK",
            status="active",
        )
        self.assertIsInstance(gauge.id, uuid.UUID)
        self.assertEqual(gauge.gauge_id, "12345")
        self.assertEqual(gauge.source, "google_flood_hub")
        self.assertEqual(gauge.country_code, "PK")
        self.assertTrue(gauge.created_at)
        self.assertTrue(gauge.updated_at)
        self.assertLessEqual(gauge.created_at, timezone.now())


class ReadingModelTests(TestCase):
    def setUp(self):
        """Set up a Gauge instance to be used by tests."""
        self.gauge = Gauge.objects.create(
            gauge_id="test_gauge_for_reading",
            name="Test Gauge",
            latitude=1.0,
            longitude=1.0,
            country_code="PK",
        )

    def test_create_reading(self):
        """
        Test that a Reading model instance can be
        created successfully.
        This test is expected to fail initially.
        """
        reading = Reading.objects.create(
            gauge=self.gauge, timestamp=timezone.now(), water_level=10.5, flow_rate=50.2
        )
        self.assertEqual(reading.gauge, self.gauge)
        self.assertIsInstance(reading.id, uuid.UUID)
        self.assertLessEqual(reading.water_level, 10.5)


class PredictionModelTests(TestCase):
    def setUp(self):
        """Set up a Gauge instance to be used by tests."""
        self.gauge = Gauge.objects.create(
            gauge_id="test_gauge_for_prediction",
            name="Test Gauge",
            latitude=1.0,
            longitude=1.0,
            country_code="PK",
        )

    def test_create_prediction(self):
        """
        Test that a Prediction model instance can be
        created successfully.
        This test is expected to fail initially.
        """
        prediction = Prediction.objects.create(
            gauge=self.gauge,
            prediction_for_timestamp=timezone.now() + timezone.timedelta(hours=1),
            water_level=12.0,
        )
        self.assertEqual(prediction.gauge, self.gauge)
        self.assertIsInstance(prediction.id, uuid.UUID)
        self.assertEqual(prediction.water_level, 12.0)
