"""Comprehensive tests for core models."""

import uuid
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import datetime, timedelta

from core.models import Gauge, Reading, Prediction
from core.tests.factories import GaugeFactory, ReadingFactory, PredictionFactory


class TestGaugeModel(TestCase):
    """Comprehensive tests for Gauge model."""

    def test_gauge_creation(self):
        """Test basic gauge creation with all fields."""
        gauge = Gauge.objects.create(
            gauge_id="test_gauge_001",
            name="Test Gauge",
            location="Test Location",
            latitude=30.0,
            longitude=70.0,
            country_code="PK",
            source=Gauge.Source.GOOGLE_FLOOD_HUB,
            status=Gauge.Status.ACTIVE,
            quality_verified=True,
            has_model=True,
        )

        self.assertEqual(gauge.gauge_id, "test_gauge_001")
        self.assertEqual(gauge.name, "Test Gauge")
        self.assertEqual(gauge.location, "Test Location")
        self.assertEqual(gauge.latitude, 30.0)
        self.assertEqual(gauge.longitude, 70.0)
        self.assertEqual(gauge.country_code, "PK")
        self.assertEqual(gauge.source, Gauge.Source.GOOGLE_FLOOD_HUB)
        self.assertEqual(gauge.status, Gauge.Status.ACTIVE)
        self.assertTrue(gauge.quality_verified)
        self.assertTrue(gauge.has_model)

    def test_gauge_id_field_validation(self):
        """Test gauge_id field properties and validation."""
        # Test max_length
        long_id = "a" * 101  # 101 characters
        gauge = Gauge(
            gauge_id=long_id,
            name="Test",
            latitude=30.0,
            longitude=70.0,
            country_code="PK",
        )

        with self.assertRaises(ValidationError):
            gauge.full_clean()

    def test_gauge_id_unique_constraint(self):
        """Test that gauge_id must be unique."""
        # Create first gauge
        Gauge.objects.create(
            gauge_id="unique_test",
            name="First Gauge",
            latitude=30.0,
            longitude=70.0,
            country_code="PK",
        )

        # Try to create second gauge with same gauge_id
        with self.assertRaises(IntegrityError):
            Gauge.objects.create(
                gauge_id="unique_test",
                name="Second Gauge",
                latitude=31.0,
                longitude=71.0,
                country_code="PK",
            )

    def test_gauge_id_db_index(self):
        """Test that gauge_id has database index."""
        # This test verifies the field is marked for indexing
        gauge_id_field = Gauge._meta.get_field("gauge_id")
        self.assertTrue(gauge_id_field.db_index)

    def test_coordinate_validation(self):
        """Test coordinate field validation."""
        # Test valid coordinates
        gauge = Gauge(
            gauge_id="coord_test",
            name="Test",
            latitude=34.0,
            longitude=71.0,
            country_code="PK",
        )
        gauge.full_clean()  # Should not raise

        # Test extreme but valid coordinates
        gauge = Gauge(
            gauge_id="coord_test_2",
            name="Test 2",
            latitude=-90.0,
            longitude=-180.0,
            country_code="PK",
        )
        gauge.full_clean()  # Should not raise

    def test_source_choices(self):
        """Test source field choices."""
        # Test valid choices
        gauge = Gauge(
            gauge_id="source_test",
            name="Test",
            latitude=30.0,
            longitude=70.0,
            country_code="PK",
            source=Gauge.Source.GOOGLE_FLOOD_HUB,
        )
        gauge.full_clean()

        gauge.source = Gauge.Source.MANUAL
        gauge.full_clean()

        # Test invalid choice
        gauge.source = "invalid_source"
        with self.assertRaises(ValidationError):
            gauge.full_clean()

    def test_status_choices(self):
        """Test status field choices."""
        gauge = GaugeFactory()

        # Test all valid status choices
        valid_statuses = [
            Gauge.Status.ACTIVE,
            Gauge.Status.INACTIVE,
            Gauge.Status.MAINTENANCE,
        ]

        for status in valid_statuses:
            gauge.status = status
            gauge.full_clean()  # Should not raise

        # Test invalid choice
        gauge.status = "invalid_status"
        with self.assertRaises(ValidationError):
            gauge.full_clean()

    def test_default_values(self):
        """Test model default values."""
        gauge = Gauge.objects.create(
            gauge_id="default_test",
            name="Default Test",
            latitude=30.0,
            longitude=70.0,
            country_code="PK",
        )

        # Test defaults
        self.assertEqual(gauge.source, Gauge.Source.GOOGLE_FLOOD_HUB)
        self.assertEqual(gauge.status, Gauge.Status.ACTIVE)
        self.assertFalse(gauge.quality_verified)
        self.assertFalse(gauge.has_model)
        self.assertEqual(gauge.location, "")

    def test_uuid_primary_key(self):
        """Test that primary key is UUID."""
        gauge = GaugeFactory()

        # Test that id is UUID
        self.assertIsInstance(gauge.id, uuid.UUID)

        # Test that id is unique
        gauge2 = GaugeFactory()
        self.assertNotEqual(gauge.id, gauge2.id)

    def test_string_representation(self):
        """Test __str__ method."""
        gauge = GaugeFactory(name="Test River Station", gauge_id="hybas_123456")

        expected = "Test River Station (hybas_123456)"
        self.assertEqual(str(gauge), expected)

    def test_meta_options(self):
        """Test model Meta options."""
        meta = Gauge._meta

        # Test ordering
        self.assertEqual(meta.ordering, ["name"])

        # Test verbose names
        self.assertEqual(meta.verbose_name, "Flood Gauge")
        self.assertEqual(meta.verbose_name_plural, "Flood Gauges")

    def test_cascade_deletion(self):
        """Test cascade deletion with related objects."""
        gauge = GaugeFactory()

        # Create related objects
        reading = ReadingFactory(gauge=gauge)
        prediction = PredictionFactory(gauge=gauge)

        # Verify they exist
        self.assertTrue(Reading.objects.filter(id=reading.id).exists())
        self.assertTrue(Prediction.objects.filter(id=prediction.id).exists())

        # Delete gauge
        gauge.delete()

        # Verify related objects are deleted
        self.assertFalse(Reading.objects.filter(id=reading.id).exists())
        self.assertFalse(Prediction.objects.filter(id=prediction.id).exists())

    def test_timestamp_auto_fields(self):
        """Test auto timestamp fields."""
        before_creation = timezone.now()

        gauge = GaugeFactory()

        after_creation = timezone.now()

        # Test created_at
        self.assertGreaterEqual(gauge.created_at, before_creation)
        self.assertLessEqual(gauge.created_at, after_creation)

        # Test updated_at initially equals created_at
        self.assertEqual(gauge.created_at, gauge.updated_at)

        # Test updated_at changes on save
        original_updated_at = gauge.updated_at
        gauge.name = "Updated Name"
        gauge.save()

        self.assertGreater(gauge.updated_at, original_updated_at)

    def test_field_help_text(self):
        """Test field help text."""
        gauge_id_field = Gauge._meta.get_field("gauge_id")
        quality_field = Gauge._meta.get_field("quality_verified")
        model_field = Gauge._meta.get_field("has_model")

        self.assertEqual(
            gauge_id_field.help_text,
            "The unique identifier for the gauge from its source.",
        )
        self.assertEqual(
            quality_field.help_text, "Google Flood Hub quality verification status"
        )
        self.assertEqual(
            model_field.help_text, "Has hydrological model for predictions"
        )

    def test_country_code_field(self):
        """Test country_code field validation."""
        gauge = GaugeFactory()

        # Test valid country codes
        valid_codes = ["PK", "US", "GB", "IN"]
        for code in valid_codes:
            gauge.country_code = code
            gauge.full_clean()  # Should not raise

        # Test max length (should be 2)
        gauge.country_code = "USA"  # Too long
        with self.assertRaises(ValidationError):
            gauge.full_clean()

    def test_location_field_blank(self):
        """Test that location field can be blank."""
        gauge = Gauge.objects.create(
            gauge_id="blank_location_test",
            name="Test",
            latitude=30.0,
            longitude=70.0,
            country_code="PK",
            location="",  # Blank location
        )

        gauge.full_clean()  # Should not raise
        self.assertEqual(gauge.location, "")

    def test_boolean_field_defaults(self):
        """Test boolean field default values."""
        gauge = GaugeFactory()

        # Test that boolean fields have proper defaults
        self.assertIsInstance(gauge.quality_verified, bool)
        self.assertIsInstance(gauge.has_model, bool)
        self.assertFalse(gauge.quality_verified)
        self.assertFalse(gauge.has_model)

    def test_queryset_ordering(self):
        """Test that queryset returns objects in correct order."""
        # Create gauges with different names
        gauge_c = GaugeFactory(name="C Gauge")
        gauge_a = GaugeFactory(name="A Gauge")
        gauge_b = GaugeFactory(name="B Gauge")

        # Get all gauges
        gauges = list(Gauge.objects.all())

        # Should be ordered by name
        self.assertEqual(gauges[0], gauge_a)
        self.assertEqual(gauges[1], gauge_b)
        self.assertEqual(gauges[2], gauge_c)


class TestReadingModel(TestCase):
    """Comprehensive tests for Reading model."""

    def test_reading_creation(self):
        """Test basic reading creation."""
        gauge = GaugeFactory()
        timestamp = timezone.now()

        reading = Reading.objects.create(
            gauge=gauge, timestamp=timestamp, water_level=12.5, flow_rate=25.0
        )

        self.assertEqual(reading.gauge, gauge)
        self.assertEqual(reading.timestamp, timestamp)
        self.assertEqual(reading.water_level, 12.5)
        self.assertEqual(reading.flow_rate, 25.0)

    def test_gauge_relationship(self):
        """Test gauge foreign key relationship."""
        gauge = GaugeFactory()
        reading = ReadingFactory(gauge=gauge)

        # Test forward relationship
        self.assertEqual(reading.gauge, gauge)

        # Test reverse relationship
        self.assertIn(reading, gauge.readings.all())

    def test_reading_uuid_primary_key(self):
        """Test that reading uses UUID primary key."""
        reading = ReadingFactory()

        self.assertIsInstance(reading.id, uuid.UUID)

    def test_timestamp_validation(self):
        """Test timestamp field validation."""
        gauge = GaugeFactory()

        # Test valid timestamps
        valid_timestamps = [
            timezone.now(),
            timezone.now() - timedelta(days=1),
            timezone.now() + timedelta(days=1),
        ]

        for timestamp in valid_timestamps:
            reading = Reading(gauge=gauge, timestamp=timestamp, water_level=10.0)
            reading.full_clean()  # Should not raise

    def test_water_level_constraints(self):
        """Test water level field constraints."""
        gauge = GaugeFactory()

        # Test positive values
        reading = Reading(gauge=gauge, timestamp=timezone.now(), water_level=15.5)
        reading.full_clean()

        # Test zero value
        reading.water_level = 0.0
        reading.full_clean()

        # Test negative values (should be allowed for some cases)
        reading.water_level = -2.0
        reading.full_clean()

    def test_flow_rate_optional(self):
        """Test that flow_rate field is optional."""
        gauge = GaugeFactory()

        # Test with flow_rate
        reading = Reading.objects.create(
            gauge=gauge, timestamp=timezone.now(), water_level=10.0, flow_rate=20.0
        )
        self.assertEqual(reading.flow_rate, 20.0)

        # Test without flow_rate
        reading = Reading.objects.create(
            gauge=gauge, timestamp=timezone.now(), water_level=10.0
        )
        self.assertIsNone(reading.flow_rate)

    def test_reading_ordering(self):
        """Test reading ordering by timestamp (newest first)."""
        gauge = GaugeFactory()

        # Create readings with different timestamps
        old_reading = ReadingFactory(
            gauge=gauge, timestamp=timezone.now() - timedelta(hours=2)
        )
        new_reading = ReadingFactory(
            gauge=gauge, timestamp=timezone.now() - timedelta(hours=1)
        )
        newest_reading = ReadingFactory(gauge=gauge, timestamp=timezone.now())

        # Get all readings
        readings = list(Reading.objects.all())

        # Should be ordered by timestamp (newest first)
        self.assertEqual(readings[0], newest_reading)
        self.assertEqual(readings[1], new_reading)
        self.assertEqual(readings[2], old_reading)

    def test_related_name_access(self):
        """Test accessing readings through gauge's related name."""
        gauge = GaugeFactory()
        reading1 = ReadingFactory(gauge=gauge)
        reading2 = ReadingFactory(gauge=gauge)

        # Test related name access
        gauge_readings = gauge.readings.all()
        self.assertIn(reading1, gauge_readings)
        self.assertIn(reading2, gauge_readings)
        self.assertEqual(gauge_readings.count(), 2)

    def test_reading_string_representation(self):
        """Test __str__ method."""
        gauge = GaugeFactory(name="Test River Station")
        timestamp = timezone.now()
        reading = ReadingFactory(gauge=gauge, timestamp=timestamp)

        expected = f"Test River Station - {timestamp}"
        self.assertEqual(str(reading), expected)

    def test_reading_meta_options(self):
        """Test Reading model Meta options."""
        meta = Reading._meta

        # Test ordering
        self.assertEqual(meta.ordering, ["-timestamp"])

        # Test verbose names
        self.assertEqual(meta.verbose_name, "Reading")
        self.assertEqual(meta.verbose_name_plural, "Readings")

    def test_reading_auto_timestamps(self):
        """Test auto timestamp fields."""
        before_creation = timezone.now()

        reading = ReadingFactory()

        after_creation = timezone.now()

        # Test created_at
        self.assertGreaterEqual(reading.created_at, before_creation)
        self.assertLessEqual(reading.created_at, after_creation)

        # Test updated_at changes on save
        original_updated_at = reading.updated_at
        reading.water_level = 999.9
        reading.save()

        self.assertGreater(reading.updated_at, original_updated_at)

    def test_reading_field_help_text(self):
        """Test field help text."""
        water_level_field = Reading._meta.get_field("water_level")
        flow_rate_field = Reading._meta.get_field("flow_rate")

        self.assertEqual(water_level_field.help_text, "Water level in meters")
        self.assertEqual(flow_rate_field.help_text, "Flow rate in m³/s")


class TestPredictionModel(TestCase):
    """Comprehensive tests for Prediction model."""

    def test_prediction_creation(self):
        """Test basic prediction creation."""
        gauge = GaugeFactory()
        prediction_time = timezone.now() + timedelta(hours=6)

        prediction = Prediction.objects.create(
            gauge=gauge, prediction_for_timestamp=prediction_time, water_level=15.0
        )

        self.assertEqual(prediction.gauge, gauge)
        self.assertEqual(prediction.prediction_for_timestamp, prediction_time)
        self.assertEqual(prediction.water_level, 15.0)

    def test_prediction_gauge_relationship(self):
        """Test gauge foreign key relationship."""
        gauge = GaugeFactory()
        prediction = PredictionFactory(gauge=gauge)

        # Test forward relationship
        self.assertEqual(prediction.gauge, gauge)

        # Test reverse relationship
        self.assertIn(prediction, gauge.predictions.all())

    def test_prediction_uuid_primary_key(self):
        """Test that prediction uses UUID primary key."""
        prediction = PredictionFactory()

        self.assertIsInstance(prediction.id, uuid.UUID)

    def test_future_timestamp_validation(self):
        """Test prediction timestamp validation."""
        gauge = GaugeFactory()

        # Test future timestamp (normal case)
        future_time = timezone.now() + timedelta(hours=24)
        prediction = Prediction(
            gauge=gauge, prediction_for_timestamp=future_time, water_level=10.0
        )
        prediction.full_clean()  # Should not raise

        # Test past timestamp (should still be allowed for testing)
        past_time = timezone.now() - timedelta(hours=1)
        prediction.prediction_for_timestamp = past_time
        prediction.full_clean()  # Should not raise

    def test_prediction_ordering(self):
        """Test prediction ordering by prediction_for_timestamp."""
        gauge = GaugeFactory()

        # Create predictions with different times
        later_prediction = PredictionFactory(
            gauge=gauge, prediction_for_timestamp=timezone.now() + timedelta(hours=12)
        )
        earlier_prediction = PredictionFactory(
            gauge=gauge, prediction_for_timestamp=timezone.now() + timedelta(hours=6)
        )
        middle_prediction = PredictionFactory(
            gauge=gauge, prediction_for_timestamp=timezone.now() + timedelta(hours=9)
        )

        # Get all predictions
        predictions = list(Prediction.objects.all())

        # Should be ordered by prediction_for_timestamp (earliest first)
        self.assertEqual(predictions[0], earlier_prediction)
        self.assertEqual(predictions[1], middle_prediction)
        self.assertEqual(predictions[2], later_prediction)

    def test_prediction_string_representation(self):
        """Test __str__ method."""
        gauge = GaugeFactory(name="Test River Station")
        prediction_time = timezone.now() + timedelta(hours=6)
        prediction = PredictionFactory(
            gauge=gauge, prediction_for_timestamp=prediction_time
        )

        expected = f"Test River Station - Prediction for {prediction_time}"
        self.assertEqual(str(prediction), expected)

    def test_prediction_meta_options(self):
        """Test Prediction model Meta options."""
        meta = Prediction._meta

        # Test ordering
        self.assertEqual(meta.ordering, ["prediction_for_timestamp"])

        # Test verbose names
        self.assertEqual(meta.verbose_name, "Prediction")
        self.assertEqual(meta.verbose_name_plural, "Predictions")

    def test_prediction_field_help_text(self):
        """Test field help text."""
        water_level_field = Prediction._meta.get_field("water_level")

        self.assertEqual(water_level_field.help_text, "Predicted water level in meters")

    def test_prediction_auto_timestamps(self):
        """Test auto timestamp fields."""
        before_creation = timezone.now()

        prediction = PredictionFactory()

        after_creation = timezone.now()

        # Test created_at
        self.assertGreaterEqual(prediction.created_at, before_creation)
        self.assertLessEqual(prediction.created_at, after_creation)

        # Test updated_at changes on save
        original_updated_at = prediction.updated_at
        prediction.water_level = 999.9
        prediction.save()

        self.assertGreater(prediction.updated_at, original_updated_at)

    def test_prediction_related_name_access(self):
        """Test accessing predictions through gauge's related name."""
        gauge = GaugeFactory()
        prediction1 = PredictionFactory(gauge=gauge)
        prediction2 = PredictionFactory(gauge=gauge)

        # Test related name access
        gauge_predictions = gauge.predictions.all()
        self.assertIn(prediction1, gauge_predictions)
        self.assertIn(prediction2, gauge_predictions)
        self.assertEqual(gauge_predictions.count(), 2)
