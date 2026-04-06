"""Comprehensive tests for API serializers."""

from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from rest_framework import serializers
from rest_framework.test import APITestCase

from core.models import Gauge, Reading, Prediction
from core.tests.factories import GaugeFactory, ReadingFactory, PredictionFactory
from api.serializers import GaugeSerializer, ReadingSerializer, PredictionSerializer


class TestGaugeSerializer(TestCase):
    """Test GaugeSerializer functionality."""

    def setUp(self):
        """Set up test data."""
        self.gauge = GaugeFactory(
            gauge_id="PK001",
            name="Test Gauge",
            latitude=31.5204,
            longitude=74.3587,
            country_code="PK",
            status="active",
        )

    def test_gauge_serializer_serialize(self):
        """Test gauge serialization."""
        serializer = GaugeSerializer(self.gauge)
        data = serializer.data

        # Check all required fields are present
        required_fields = [
            "id",
            "gauge_id",
            "name",
            "latitude",
            "longitude",
            "country_code",
            "status",
        ]
        for field in required_fields:
            self.assertIn(field, data)

        # Check field values
        self.assertEqual(data["gauge_id"], "PK001")
        self.assertEqual(data["name"], "Test Gauge")
        self.assertEqual(data["latitude"], 31.5204)
        self.assertEqual(data["longitude"], 74.3587)
        self.assertEqual(data["country_code"], "PK")
        self.assertEqual(data["status"], "active")

    def test_gauge_serializer_field_types(self):
        """Test gauge serializer field types."""
        serializer = GaugeSerializer(self.gauge)
        data = serializer.data

        # Check field types
        self.assertIsInstance(data["id"], str)  # UUID as string
        self.assertIsInstance(data["gauge_id"], str)
        self.assertIsInstance(data["name"], str)
        self.assertIsInstance(data["latitude"], float)
        self.assertIsInstance(data["longitude"], float)
        self.assertIsInstance(data["country_code"], str)
        self.assertIsInstance(data["status"], str)

    def test_gauge_serializer_uuid_format(self):
        """Test that UUID is serialized as string."""
        serializer = GaugeSerializer(self.gauge)
        data = serializer.data

        # UUID should be serialized as string
        self.assertIsInstance(data["id"], str)

        # Should be valid UUID format
        try:
            uuid.UUID(data["id"])
        except ValueError:
            self.fail(f"Invalid UUID format: {data['id']}")

    def test_gauge_serializer_multiple_instances(self):
        """Test serializing multiple gauge instances."""
        gauge2 = GaugeFactory(
            gauge_id="PK002",
            name="Test Gauge 2",
            latitude=33.6844,
            longitude=73.0479,
            country_code="PK",
            status="inactive",
        )

        gauges = [self.gauge, gauge2]
        serializer = GaugeSerializer(gauges, many=True)
        data = serializer.data

        self.assertEqual(len(data), 2)

        # Check first gauge
        self.assertEqual(data[0]["gauge_id"], "PK001")
        self.assertEqual(data[0]["status"], "active")

        # Check second gauge
        self.assertEqual(data[1]["gauge_id"], "PK002")
        self.assertEqual(data[1]["status"], "inactive")

    def test_gauge_serializer_with_special_characters(self):
        """Test gauge serializer with special characters."""
        gauge = GaugeFactory(
            gauge_id="PK-001",
            name="Test Gauge (Main)",
            latitude=31.5204,
            longitude=74.3587,
            country_code="PK",
            status="active",
        )

        serializer = GaugeSerializer(gauge)
        data = serializer.data

        self.assertEqual(data["gauge_id"], "PK-001")
        self.assertEqual(data["name"], "Test Gauge (Main)")

    def test_gauge_serializer_coordinate_precision(self):
        """Test coordinate precision in serialization."""
        gauge = GaugeFactory(
            gauge_id="PK001",
            name="Test Gauge",
            latitude=31.520412345,
            longitude=74.358734567,
            country_code="PK",
            status="active",
        )

        serializer = GaugeSerializer(gauge)
        data = serializer.data

        # Check that coordinates maintain precision
        self.assertIsInstance(data["latitude"], float)
        self.assertIsInstance(data["longitude"], float)
        self.assertEqual(data["latitude"], 31.520412345)
        self.assertEqual(data["longitude"], 74.358734567)

    def test_gauge_serializer_empty_queryset(self):
        """Test serializing empty queryset."""
        serializer = GaugeSerializer(Gauge.objects.none(), many=True)
        data = serializer.data

        self.assertEqual(len(data), 0)
        self.assertIsInstance(data, list)

    def test_gauge_serializer_meta_fields(self):
        """Test that serializer includes all meta fields."""
        serializer = GaugeSerializer()

        # Check Meta fields
        expected_fields = [
            "id",
            "gauge_id",
            "name",
            "latitude",
            "longitude",
            "country_code",
            "status",
        ]
        self.assertEqual(set(serializer.Meta.fields), set(expected_fields))
        self.assertEqual(serializer.Meta.model, Gauge)

    def test_gauge_serializer_read_only(self):
        """Test that gauge serializer is read-only by default."""
        serializer = GaugeSerializer()

        # Should not have validation methods for creation/update
        self.assertFalse(hasattr(serializer, "create"))
        self.assertFalse(hasattr(serializer, "update"))
        self.assertFalse(hasattr(serializer, "validate"))


class TestReadingSerializer(TestCase):
    """Test ReadingSerializer functionality."""

    def setUp(self):
        """Set up test data."""
        self.gauge = GaugeFactory(gauge_id="PK001", name="Test Gauge")
        self.reading = ReadingFactory(
            gauge=self.gauge, timestamp=timezone.now(), water_level=5.0, flow_rate=100.0
        )

    def test_reading_serializer_serialize(self):
        """Test reading serialization."""
        serializer = ReadingSerializer(self.reading)
        data = serializer.data

        # Check all required fields are present
        required_fields = ["id", "gauge", "timestamp", "water_level", "flow_rate"]
        for field in required_fields:
            self.assertIn(field, data)

        # Check field values
        self.assertEqual(data["gauge"], str(self.gauge.pk))
        self.assertEqual(float(data["water_level"]), 5.0)
        self.assertEqual(float(data["flow_rate"]), 100.0)

    def test_reading_serializer_field_types(self):
        """Test reading serializer field types."""
        serializer = ReadingSerializer(self.reading)
        data = serializer.data

        # Check field types
        self.assertIsInstance(data["id"], str)  # UUID as string
        self.assertIsInstance(data["gauge"], str)  # Gauge UUID as string
        self.assertIsInstance(data["timestamp"], str)  # ISO datetime string
        self.assertIsInstance(data["water_level"], (int, float))
        self.assertIsInstance(data["flow_rate"], (int, float, type(None)))

    def test_reading_serializer_timestamp_format(self):
        """Test timestamp serialization format."""
        serializer = ReadingSerializer(self.reading)
        data = serializer.data

        # Check timestamp format (ISO 8601)
        timestamp = data["timestamp"]
        self.assertIsInstance(timestamp, str)
        self.assertRegex(timestamp, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

        # Should be parseable as datetime
        from datetime import datetime

        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            self.fail(f"Invalid timestamp format: {timestamp}")

    def test_reading_serializer_null_flow_rate(self):
        """Test reading serialization with null flow rate."""
        reading = ReadingFactory(
            gauge=self.gauge, timestamp=timezone.now(), water_level=5.0, flow_rate=None
        )

        serializer = ReadingSerializer(reading)
        data = serializer.data

        self.assertEqual(data["flow_rate"], None)
        self.assertEqual(float(data["water_level"]), 5.0)

    def test_reading_serializer_decimal_precision(self):
        """Test decimal precision in serialization."""
        reading = ReadingFactory(
            gauge=self.gauge,
            timestamp=timezone.now(),
            water_level=Decimal("5.123456"),
            flow_rate=Decimal("100.789012"),
        )

        serializer = ReadingSerializer(reading)
        data = serializer.data

        # Check that decimal values are preserved
        self.assertIsInstance(data["water_level"], (int, float))
        self.assertIsInstance(data["flow_rate"], (int, float))

        # Check precision
        self.assertAlmostEqual(float(data["water_level"]), 5.123456, places=6)
        self.assertAlmostEqual(float(data["flow_rate"]), 100.789012, places=6)

    def test_reading_serializer_multiple_instances(self):
        """Test serializing multiple reading instances."""
        reading2 = ReadingFactory(
            gauge=self.gauge,
            timestamp=timezone.now() - timedelta(hours=1),
            water_level=4.5,
            flow_rate=95.0,
        )

        readings = [self.reading, reading2]
        serializer = ReadingSerializer(readings, many=True)
        data = serializer.data

        self.assertEqual(len(data), 2)

        # Check that both readings are serialized
        gauge_ids = [reading["gauge"] for reading in data]
        self.assertTrue(all(gauge_id == str(self.gauge.pk) for gauge_id in gauge_ids))

    def test_reading_serializer_extreme_values(self):
        """Test reading serializer with extreme values."""
        reading = ReadingFactory(
            gauge=self.gauge,
            timestamp=timezone.now(),
            water_level=0.001,  # Very small value
            flow_rate=999999.999,  # Very large value
        )

        serializer = ReadingSerializer(reading)
        data = serializer.data

        self.assertEqual(float(data["water_level"]), 0.001)
        self.assertEqual(float(data["flow_rate"]), 999999.999)

    def test_reading_serializer_uuid_references(self):
        """Test UUID references in serialization."""
        serializer = ReadingSerializer(self.reading)
        data = serializer.data

        # Check UUID formats
        reading_id = data["id"]
        gauge_id = data["gauge"]

        try:
            uuid.UUID(reading_id)
            uuid.UUID(gauge_id)
        except ValueError:
            self.fail(f"Invalid UUID format: {reading_id} or {gauge_id}")

    def test_reading_serializer_empty_queryset(self):
        """Test serializing empty queryset."""
        serializer = ReadingSerializer(Reading.objects.none(), many=True)
        data = serializer.data

        self.assertEqual(len(data), 0)
        self.assertIsInstance(data, list)

    def test_reading_serializer_meta_fields(self):
        """Test that serializer includes all meta fields."""
        serializer = ReadingSerializer()

        # Check Meta fields
        expected_fields = ["id", "gauge", "timestamp", "water_level", "flow_rate"]
        self.assertEqual(set(serializer.Meta.fields), set(expected_fields))
        self.assertEqual(serializer.Meta.model, Reading)

    def test_reading_serializer_timezone_handling(self):
        """Test timezone handling in serialization."""
        # Create reading with timezone-aware timestamp
        aware_timestamp = timezone.now()
        reading = ReadingFactory(
            gauge=self.gauge,
            timestamp=aware_timestamp,
            water_level=5.0,
            flow_rate=100.0,
        )

        serializer = ReadingSerializer(reading)
        data = serializer.data

        # Timestamp should be serialized with timezone info
        timestamp = data["timestamp"]
        self.assertTrue(
            timestamp.endswith("Z") or "+" in timestamp or "-" in timestamp[-6:]
        )


class TestPredictionSerializer(TestCase):
    """Test PredictionSerializer functionality."""

    def setUp(self):
        """Set up test data."""
        self.gauge = GaugeFactory(gauge_id="PK001", name="Test Gauge")
        self.prediction = PredictionFactory(
            gauge=self.gauge,
            prediction_for_timestamp=timezone.now() + timedelta(hours=1),
            water_level=6.0,
        )

    def test_prediction_serializer_serialize(self):
        """Test prediction serialization."""
        serializer = PredictionSerializer(self.prediction)
        data = serializer.data

        # Check all required fields are present
        required_fields = ["id", "gauge", "prediction_for_timestamp", "water_level"]
        for field in required_fields:
            self.assertIn(field, data)

        # Check field values
        self.assertEqual(data["gauge"], str(self.gauge.pk))
        self.assertEqual(float(data["water_level"]), 6.0)

    def test_prediction_serializer_field_types(self):
        """Test prediction serializer field types."""
        serializer = PredictionSerializer(self.prediction)
        data = serializer.data

        # Check field types
        self.assertIsInstance(data["id"], str)  # UUID as string
        self.assertIsInstance(data["gauge"], str)  # Gauge UUID as string
        self.assertIsInstance(
            data["prediction_for_timestamp"], str
        )  # ISO datetime string
        self.assertIsInstance(data["water_level"], (int, float))

    def test_prediction_serializer_timestamp_format(self):
        """Test prediction timestamp serialization format."""
        serializer = PredictionSerializer(self.prediction)
        data = serializer.data

        # Check timestamp format (ISO 8601)
        timestamp = data["prediction_for_timestamp"]
        self.assertIsInstance(timestamp, str)
        self.assertRegex(timestamp, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

        # Should be parseable as datetime
        from datetime import datetime

        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            self.fail(f"Invalid timestamp format: {timestamp}")

    def test_prediction_serializer_future_timestamp(self):
        """Test prediction serialization with future timestamp."""
        future_time = timezone.now() + timedelta(days=1)
        prediction = PredictionFactory(
            gauge=self.gauge, prediction_for_timestamp=future_time, water_level=7.5
        )

        serializer = PredictionSerializer(prediction)
        data = serializer.data

        self.assertEqual(float(data["water_level"]), 7.5)
        # Timestamp should be in future
        prediction_time = datetime.fromisoformat(
            data["prediction_for_timestamp"].replace("Z", "+00:00")
        )
        self.assertGreater(prediction_time, timezone.now().replace(tzinfo=None))

    def test_prediction_serializer_decimal_precision(self):
        """Test decimal precision in prediction serialization."""
        prediction = PredictionFactory(
            gauge=self.gauge,
            prediction_for_timestamp=timezone.now() + timedelta(hours=1),
            water_level=Decimal("6.123456"),
        )

        serializer = PredictionSerializer(prediction)
        data = serializer.data

        # Check that decimal values are preserved
        self.assertIsInstance(data["water_level"], (int, float))
        self.assertAlmostEqual(float(data["water_level"]), 6.123456, places=6)

    def test_prediction_serializer_multiple_instances(self):
        """Test serializing multiple prediction instances."""
        prediction2 = PredictionFactory(
            gauge=self.gauge,
            prediction_for_timestamp=timezone.now() + timedelta(hours=2),
            water_level=5.5,
        )

        predictions = [self.prediction, prediction2]
        serializer = PredictionSerializer(predictions, many=True)
        data = serializer.data

        self.assertEqual(len(data), 2)

        # Check that both predictions are serialized
        gauge_ids = [prediction["gauge"] for prediction in data]
        self.assertTrue(all(gauge_id == str(self.gauge.pk) for gauge_id in gauge_ids))

    def test_prediction_serializer_extreme_values(self):
        """Test prediction serializer with extreme values."""
        prediction = PredictionFactory(
            gauge=self.gauge,
            prediction_for_timestamp=timezone.now() + timedelta(hours=1),
            water_level=0.001,  # Very small value
        )

        serializer = PredictionSerializer(prediction)
        data = serializer.data

        self.assertEqual(float(data["water_level"]), 0.001)

    def test_prediction_serializer_uuid_references(self):
        """Test UUID references in prediction serialization."""
        serializer = PredictionSerializer(self.prediction)
        data = serializer.data

        # Check UUID formats
        prediction_id = data["id"]
        gauge_id = data["gauge"]

        try:
            uuid.UUID(prediction_id)
            uuid.UUID(gauge_id)
        except ValueError:
            self.fail(f"Invalid UUID format: {prediction_id} or {gauge_id}")

    def test_prediction_serializer_empty_queryset(self):
        """Test serializing empty queryset."""
        serializer = PredictionSerializer(Prediction.objects.none(), many=True)
        data = serializer.data

        self.assertEqual(len(data), 0)
        self.assertIsInstance(data, list)

    def test_prediction_serializer_meta_fields(self):
        """Test that serializer includes all meta fields."""
        serializer = PredictionSerializer()

        # Check Meta fields
        expected_fields = ["id", "gauge", "prediction_for_timestamp", "water_level"]
        self.assertEqual(set(serializer.Meta.fields), set(expected_fields))
        self.assertEqual(serializer.Meta.model, Prediction)

    def test_prediction_serializer_timezone_handling(self):
        """Test timezone handling in prediction serialization."""
        # Create prediction with timezone-aware timestamp
        aware_timestamp = timezone.now() + timedelta(hours=1)
        prediction = PredictionFactory(
            gauge=self.gauge, prediction_for_timestamp=aware_timestamp, water_level=6.0
        )

        serializer = PredictionSerializer(prediction)
        data = serializer.data

        # Timestamp should be serialized with timezone info
        timestamp = data["prediction_for_timestamp"]
        self.assertTrue(
            timestamp.endswith("Z") or "+" in timestamp or "-" in timestamp[-6:]
        )


class TestSerializerIntegration(TestCase):
    """Test serializer integration scenarios."""

    def setUp(self):
        """Set up test data."""
        self.gauge = GaugeFactory(gauge_id="PK001", name="Test Gauge")
        self.reading = ReadingFactory(
            gauge=self.gauge, timestamp=timezone.now(), water_level=5.0, flow_rate=100.0
        )
        self.prediction = PredictionFactory(
            gauge=self.gauge,
            prediction_for_timestamp=timezone.now() + timedelta(hours=1),
            water_level=6.0,
        )

    def test_serializer_consistency(self):
        """Test consistency between serializers."""
        # Serialize all objects
        gauge_data = GaugeSerializer(self.gauge).data
        reading_data = ReadingSerializer(self.reading).data
        prediction_data = PredictionSerializer(self.prediction).data

        # Check that gauge IDs are consistent
        self.assertEqual(gauge_data["id"], reading_data["gauge"])
        self.assertEqual(gauge_data["id"], prediction_data["gauge"])

    def test_serializer_with_related_objects(self):
        """Test serializers with related objects."""
        # Create multiple readings and predictions for the same gauge
        readings = ReadingFactory.create_batch(3, gauge=self.gauge)
        predictions = PredictionFactory.create_batch(3, gauge=self.gauge)

        # Serialize all objects
        gauge_data = GaugeSerializer(self.gauge).data
        reading_data = ReadingSerializer(readings, many=True).data
        prediction_data = PredictionSerializer(predictions, many=True).data

        # Check that all readings and predictions reference the same gauge
        for reading in reading_data:
            self.assertEqual(reading["gauge"], gauge_data["id"])

        for prediction in prediction_data:
            self.assertEqual(prediction["gauge"], gauge_data["id"])

    def test_serializer_performance_with_large_dataset(self):
        """Test serializer performance with large dataset."""
        # Create large dataset
        GaugeFactory.create_batch(10)
        ReadingFactory.create_batch(50)
        PredictionFactory.create_batch(50)

        import time

        # Test gauge serialization performance
        start_time = time.time()
        gauge_data = GaugeSerializer(Gauge.objects.all(), many=True).data
        gauge_time = time.time() - start_time

        # Test reading serialization performance
        start_time = time.time()
        reading_data = ReadingSerializer(Reading.objects.all(), many=True).data
        reading_time = time.time() - start_time

        # Test prediction serialization performance
        start_time = time.time()
        prediction_data = PredictionSerializer(Prediction.objects.all(), many=True).data
        prediction_time = time.time() - start_time

        # Performance should be reasonable (less than 1 second each)
        self.assertLess(gauge_time, 1.0)
        self.assertLess(reading_time, 1.0)
        self.assertLess(prediction_time, 1.0)

        # Data should be complete
        self.assertGreater(len(gauge_data), 0)
        self.assertGreater(len(reading_data), 0)
        self.assertGreater(len(prediction_data), 0)

    def test_serializer_error_handling(self):
        """Test serializer error handling."""
        # Test with None objects
        gauge_serializer = GaugeSerializer(None)
        self.assertIsNone(gauge_serializer.data)

        # Test with invalid objects (should not crash)
        try:
            reading_serializer = ReadingSerializer(self.gauge)  # Wrong model type
            # Should not crash, but data might be incomplete
            data = reading_serializer.data
        except Exception:
            # Some serializers might raise exceptions with wrong model types
            pass

    def test_serializer_unicode_handling(self):
        """Test serializer handling of unicode characters."""
        # Create objects with unicode characters
        gauge = GaugeFactory(
            gauge_id="PK001", name="Test Gauge — Special Characters: ñáéíóú"
        )

        serializer = GaugeSerializer(gauge)
        data = serializer.data

        # Unicode characters should be preserved
        self.assertEqual(data["name"], "Test Gauge — Special Characters: ñáéíóú")
        self.assertIsInstance(data["name"], str)

    def test_serializer_null_handling(self):
        """Test serializer handling of null values."""
        # Create reading with null flow_rate
        reading = ReadingFactory(
            gauge=self.gauge, timestamp=timezone.now(), water_level=5.0, flow_rate=None
        )

        serializer = ReadingSerializer(reading)
        data = serializer.data

        # Null values should be handled properly
        self.assertIsNone(data["flow_rate"])
        self.assertIsNotNone(data["water_level"])

    def test_serializer_validation_compatibility(self):
        """Test that serializers are compatible with DRF validation."""
        # Test that serializers have proper validation methods
        gauge_serializer = GaugeSerializer()
        reading_serializer = ReadingSerializer()
        prediction_serializer = PredictionSerializer()

        # Check that serializers have proper meta classes
        self.assertTrue(hasattr(gauge_serializer, "Meta"))
        self.assertTrue(hasattr(reading_serializer, "Meta"))
        self.assertTrue(hasattr(prediction_serializer, "Meta"))

        # Check that meta classes have required attributes
        self.assertTrue(hasattr(gauge_serializer.Meta, "model"))
        self.assertTrue(hasattr(gauge_serializer.Meta, "fields"))
        self.assertTrue(hasattr(reading_serializer.Meta, "model"))
        self.assertTrue(hasattr(reading_serializer.Meta, "fields"))
        self.assertTrue(hasattr(prediction_serializer.Meta, "model"))
        self.assertTrue(hasattr(prediction_serializer.Meta, "fields"))


# Keep the original basic tests as well for backward compatibility
class GaugeSerializerTests(TestCase):
    """Legacy test class for backward compatibility."""

    def test_serialize_gauge(self):
        """
        Test that a Gauge instance is correctly serialized.
        """
        gauge = Gauge.objects.create(
            gauge_id="serializer_test_001",
            name="Serializer Test Gauge",
            latitude=25.123,
            longitude=65.456,
            country_code="PK",
            status="active",
        )

        serializer = GaugeSerializer(instance=gauge)
        data = serializer.data

        self.assertEqual(
            set(data.keys()),
            {
                "id",
                "gauge_id",
                "name",
                "latitude",
                "longitude",
                "country_code",
                "status",
            },
        )
        self.assertEqual(data["gauge_id"], "serializer_test_001")
        self.assertEqual(data["name"], "Serializer Test Gauge")
        self.assertEqual(data["country_code"], "PK")


class ReadingSerializerTests(TestCase):
    """Legacy test class for backward compatibility."""

    def test_serialize_reading(self):
        gauge = Gauge.objects.create(
            gauge_id="reading_serializer_test",
            name="Test",
            latitude=1,
            longitude=1,
            country_code="PK",
        )
        reading = Reading.objects.create(
            gauge=gauge, timestamp=timezone.now(), water_level=1.23
        )
        serializer = ReadingSerializer(instance=reading)
        data = serializer.data
        self.assertEqual(
            set(data.keys()), {"id", "gauge", "timestamp", "water_level", "flow_rate"}
        )
        self.assertEqual(data["water_level"], 1.23)


class PredictionSerializerTests(TestCase):
    """Legacy test class for backward compatibility."""

    def test_serialize_prediction(self):
        gauge = Gauge.objects.create(
            gauge_id="prediction_serializer_test",
            name="Test",
            latitude=1,
            longitude=1,
            country_code="PK",
        )
        prediction = Prediction.objects.create(
            gauge=gauge, prediction_for_timestamp=timezone.now(), water_level=2.34
        )
        serializer = PredictionSerializer(instance=prediction)
        data = serializer.data
        self.assertEqual(
            set(data.keys()), {"id", "gauge", "prediction_for_timestamp", "water_level"}
        )
        self.assertEqual(data["water_level"], 2.34)
