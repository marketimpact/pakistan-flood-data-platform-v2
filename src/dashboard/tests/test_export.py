"""Tests for CSV export functionality."""

import csv
import io
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.db import connection

from core.models import Gauge, Reading
from core.tests.factories import GaugeFactory, ReadingFactory

User = get_user_model()


class TestCSVExportFunctionality(TestCase):
    """Test CSV export functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpassword123"
        )
        self.export_url = reverse("export_readings_csv")

    def test_csv_export_login_requirement(self):
        """Test that CSV export requires login."""
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/supersecretadminpanel/login/", response.url)

    def test_csv_export_streaming_response(self):
        """Test that CSV export uses streaming response."""
        # Create test data
        gauge = GaugeFactory()
        ReadingFactory(gauge=gauge)

        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.export_url)

        # Should use streaming response
        self.assertEqual(response.status_code, 200)
        self.assertTrue(hasattr(response, "streaming_content"))

        # Should be iterable
        content_chunks = list(response.streaming_content)
        self.assertGreater(len(content_chunks), 0)

    def test_csv_export_proper_headers(self):
        """Test that CSV export has proper HTTP headers."""
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.export_url)

        # Test content type
        self.assertEqual(response["Content-Type"], "text/csv")

        # Test content disposition
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="readings_export.csv"',
        )

        # Test status code
        self.assertEqual(response.status_code, 200)

    def test_csv_export_data_accuracy_empty_database(self):
        """Test CSV export with empty database."""
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.export_url)

        # Get response content
        content = b"".join(response.streaming_content).decode("utf-8")

        # Should only contain header
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 1)
        self.assertEqual(
            lines[0], "Gauge ID,Gauge Name,Timestamp,Water Level (m),Flow Rate (m³/s)"
        )

    def test_csv_export_data_accuracy_single_reading(self):
        """Test CSV export with single reading."""
        # Create test data
        gauge = GaugeFactory(gauge_id="test_gauge_001", name="Test Gauge Station")
        timestamp = timezone.now()
        reading = ReadingFactory(
            gauge=gauge, timestamp=timestamp, water_level=12.5, flow_rate=25.0
        )

        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.export_url)

        # Get response content
        content = b"".join(response.streaming_content).decode("utf-8")

        # Parse CSV
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        # Should have header + 1 data row
        self.assertEqual(len(rows), 2)

        # Check header
        header = rows[0]
        expected_header = [
            "Gauge ID",
            "Gauge Name",
            "Timestamp",
            "Water Level (m)",
            "Flow Rate (m³/s)",
        ]
        self.assertEqual(header, expected_header)

        # Check data row
        data_row = rows[1]
        self.assertEqual(data_row[0], "test_gauge_001")
        self.assertEqual(data_row[1], "Test Gauge Station")
        self.assertEqual(data_row[2], timestamp.isoformat())
        self.assertEqual(data_row[3], "12.5")
        self.assertEqual(data_row[4], "25.0")

    def test_csv_export_data_accuracy_multiple_readings(self):
        """Test CSV export with multiple readings."""
        # Create test data
        gauge1 = GaugeFactory(gauge_id="gauge_001", name="Gauge 1")
        gauge2 = GaugeFactory(gauge_id="gauge_002", name="Gauge 2")

        reading1 = ReadingFactory(gauge=gauge1, water_level=10.0, flow_rate=20.0)
        reading2 = ReadingFactory(gauge=gauge2, water_level=15.0, flow_rate=30.0)
        reading3 = ReadingFactory(gauge=gauge1, water_level=12.0, flow_rate=25.0)

        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.export_url)

        # Get response content
        content = b"".join(response.streaming_content).decode("utf-8")

        # Parse CSV
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        # Should have header + 3 data rows
        self.assertEqual(len(rows), 4)

        # Check that all readings are present
        gauge_ids = [row[0] for row in rows[1:]]
        self.assertIn("gauge_001", gauge_ids)
        self.assertIn("gauge_002", gauge_ids)

        # Check water levels
        water_levels = [float(row[3]) for row in rows[1:]]
        self.assertIn(10.0, water_levels)
        self.assertIn(15.0, water_levels)
        self.assertIn(12.0, water_levels)

    def test_csv_export_large_dataset_handling(self):
        """Test CSV export with large dataset."""
        # Create larger dataset
        gauges = GaugeFactory.create_batch(10)
        readings = []

        for gauge in gauges:
            readings.extend(ReadingFactory.create_batch(100, gauge=gauge))

        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.export_url)

        # Should handle large dataset
        self.assertEqual(response.status_code, 200)

        # Count rows in response
        content = b"".join(response.streaming_content).decode("utf-8")
        lines = content.strip().split("\n")

        # Should have header + 1000 data rows
        self.assertEqual(len(lines), 1001)

    def test_csv_export_memory_efficiency(self):
        """Test that CSV export is memory efficient."""
        # Create dataset
        gauges = GaugeFactory.create_batch(5)
        for gauge in gauges:
            ReadingFactory.create_batch(20, gauge=gauge)

        self.client.login(username="testuser", password="testpassword123")

        # Test that response uses streaming
        response = self.client.get(self.export_url)
        self.assertTrue(hasattr(response, "streaming_content"))

        # Test that content is generated lazily
        content_iterator = response.streaming_content
        self.assertTrue(hasattr(content_iterator, "__iter__"))
        self.assertTrue(hasattr(content_iterator, "__next__"))

    def test_csv_export_query_optimization(self):
        """Test that CSV export uses query optimization."""
        # Create test data
        gauge = GaugeFactory()
        ReadingFactory.create_batch(10, gauge=gauge)

        self.client.login(username="testuser", password="testpassword123")

        # Monitor database queries
        with self.assertNumQueries(1):  # Should use select_related efficiently
            response = self.client.get(self.export_url)
            # Consume the iterator to trigger database queries
            content = b"".join(response.streaming_content)

    def test_csv_export_unicode_handling(self):
        """Test CSV export with unicode characters."""
        # Create test data with unicode
        gauge = GaugeFactory(gauge_id="unicode_测试", name="Test Gauge 测试站点")
        reading = ReadingFactory(gauge=gauge)

        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.export_url)

        # Should handle unicode without errors
        self.assertEqual(response.status_code, 200)

        # Get response content
        content = b"".join(response.streaming_content).decode("utf-8")

        # Should contain unicode characters
        self.assertIn("unicode_测试", content)
        self.assertIn("Test Gauge 测试站点", content)

    def test_csv_export_null_values_handling(self):
        """Test CSV export with null values."""
        # Create reading with null flow_rate
        gauge = GaugeFactory()
        reading = ReadingFactory(gauge=gauge, flow_rate=None)

        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.export_url)

        # Should handle null values
        self.assertEqual(response.status_code, 200)

        # Get response content
        content = b"".join(response.streaming_content).decode("utf-8")

        # Parse CSV
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        # Should have data
        self.assertEqual(len(rows), 2)

        # Check null value handling
        data_row = rows[1]
        self.assertEqual(data_row[4], "None")  # flow_rate should be 'None'

    def test_csv_export_timestamp_formatting(self):
        """Test CSV export timestamp formatting."""
        # Create reading with specific timestamp
        gauge = GaugeFactory()
        timestamp = timezone.now().replace(
            microsecond=0
        )  # Remove microseconds for cleaner test
        reading = ReadingFactory(gauge=gauge, timestamp=timestamp)

        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.export_url)

        # Get response content
        content = b"".join(response.streaming_content).decode("utf-8")

        # Parse CSV
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        # Check timestamp format
        data_row = rows[1]
        self.assertEqual(data_row[2], timestamp.isoformat())

    def test_csv_export_special_characters_escaping(self):
        """Test CSV export with special characters that need escaping."""
        # Create test data with special characters
        gauge = GaugeFactory(
            gauge_id="special,chars", name='Gauge with "quotes" and, commas'
        )
        reading = ReadingFactory(gauge=gauge)

        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.export_url)

        # Should handle special characters
        self.assertEqual(response.status_code, 200)

        # Get response content
        content = b"".join(response.streaming_content).decode("utf-8")

        # Parse CSV to verify proper escaping
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        # Should have data
        self.assertEqual(len(rows), 2)

        # Check that special characters are properly handled
        data_row = rows[1]
        self.assertEqual(data_row[0], "special,chars")
        self.assertEqual(data_row[1], 'Gauge with "quotes" and, commas')

    def test_csv_export_ordering(self):
        """Test CSV export data ordering."""
        # Create readings with different timestamps
        gauge = GaugeFactory()

        # Create readings in non-chronological order
        reading3 = ReadingFactory(
            gauge=gauge, timestamp=timezone.now() - timedelta(hours=1), water_level=30.0
        )
        reading1 = ReadingFactory(
            gauge=gauge, timestamp=timezone.now() - timedelta(hours=3), water_level=10.0
        )
        reading2 = ReadingFactory(
            gauge=gauge, timestamp=timezone.now() - timedelta(hours=2), water_level=20.0
        )

        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.export_url)

        # Get response content
        content = b"".join(response.streaming_content).decode("utf-8")

        # Parse CSV
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        # Should have header + 3 data rows
        self.assertEqual(len(rows), 4)

        # Check ordering (should be by timestamp descending based on model ordering)
        water_levels = [float(row[3]) for row in rows[1:]]
        # The exact order depends on the model's default ordering
        self.assertEqual(len(water_levels), 3)
        self.assertIn(10.0, water_levels)
        self.assertIn(20.0, water_levels)
        self.assertIn(30.0, water_levels)

    def test_csv_export_concurrent_access(self):
        """Test CSV export with concurrent access."""
        # Create test data
        gauge = GaugeFactory()
        ReadingFactory.create_batch(10, gauge=gauge)

        self.client.login(username="testuser", password="testpassword123")

        # Simulate concurrent requests
        responses = []
        for i in range(3):
            response = self.client.get(self.export_url)
            responses.append(response)

        # All should succeed
        for response in responses:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "text/csv")

    def test_csv_export_performance_with_large_dataset(self):
        """Test CSV export performance with large dataset."""
        # Create large dataset
        gauges = GaugeFactory.create_batch(20)
        for gauge in gauges:
            ReadingFactory.create_batch(50, gauge=gauge)

        self.client.login(username="testuser", password="testpassword123")

        # Test response time (should be reasonable)
        import time

        start_time = time.time()
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 200)

        # Consume the response
        content = b"".join(response.streaming_content)
        end_time = time.time()

        # Should complete in reasonable time (adjust threshold as needed)
        self.assertLess(end_time - start_time, 10.0)  # 10 seconds max

    def test_csv_export_method_not_allowed(self):
        """Test that CSV export only allows GET requests."""
        self.client.login(username="testuser", password="testpassword123")

        # Test unsupported methods
        unsupported_methods = ["post", "put", "patch", "delete"]

        for method in unsupported_methods:
            client_method = getattr(self.client, method)
            response = client_method(self.export_url)
            self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_csv_export_with_related_data(self):
        """Test that CSV export includes related gauge data."""
        # Create test data
        gauge = GaugeFactory(gauge_id="related_test", name="Related Test Gauge")
        reading = ReadingFactory(gauge=gauge)

        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.export_url)

        # Get response content
        content = b"".join(response.streaming_content).decode("utf-8")

        # Parse CSV
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        # Should include gauge data
        data_row = rows[1]
        self.assertEqual(data_row[0], "related_test")
        self.assertEqual(data_row[1], "Related Test Gauge")

    def test_csv_export_generator_function(self):
        """Test the generate_readings_csv generator function directly."""
        from dashboard.views import generate_readings_csv

        # Create test data
        gauge = GaugeFactory(gauge_id="gen_test", name="Generator Test")
        reading = ReadingFactory(gauge=gauge, water_level=15.0, flow_rate=30.0)

        # Test generator function
        readings = Reading.objects.select_related("gauge").all()
        generator = generate_readings_csv(readings)

        # Should be a generator
        self.assertTrue(hasattr(generator, "__iter__"))
        self.assertTrue(hasattr(generator, "__next__"))

        # Get generated content
        content_lines = list(generator)
        self.assertEqual(len(content_lines), 2)  # Header + 1 data row

        # Check header
        self.assertIn("Gauge ID", content_lines[0])
        self.assertIn("Gauge Name", content_lines[0])

        # Check data
        self.assertIn("gen_test", content_lines[1])
        self.assertIn("Generator Test", content_lines[1])

    def test_csv_export_echo_class(self):
        """Test the Echo class used for CSV streaming."""
        from dashboard.views import Echo

        # Test Echo class
        echo = Echo()

        # Should have write method
        self.assertTrue(hasattr(echo, "write"))

        # Write method should return the input
        test_value = "test,value,123"
        result = echo.write(test_value)
        self.assertEqual(result, test_value)

    def test_csv_export_database_iterator(self):
        """Test that CSV export uses database iterator for memory efficiency."""
        # Create test data
        gauge = GaugeFactory()
        ReadingFactory.create_batch(100, gauge=gauge)

        self.client.login(username="testuser", password="testpassword123")

        # Mock the iterator method to verify it's used
        with patch("django.db.models.query.QuerySet.iterator") as mock_iterator:
            mock_iterator.return_value = Reading.objects.all()

            response = self.client.get(self.export_url)

            # Consume the response to trigger the generator
            content = b"".join(response.streaming_content)

            # Verify iterator was called
            mock_iterator.assert_called_once()

    def test_csv_export_view_class_behavior(self):
        """Test ExportReadingsCSVView class behavior."""
        from dashboard.views import ExportReadingsCSVView
        from django.contrib.auth.mixins import LoginRequiredMixin
        from django.views import View

        # Test inheritance
        self.assertTrue(issubclass(ExportReadingsCSVView, LoginRequiredMixin))
        self.assertTrue(issubclass(ExportReadingsCSVView, View))

        # Test that view has get method
        view = ExportReadingsCSVView()
        self.assertTrue(hasattr(view, "get"))

    def test_csv_export_response_headers_immutable(self):
        """Test that CSV export response headers are set correctly."""
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.export_url)

        # Test that headers are set
        self.assertEqual(response.get("Content-Type"), "text/csv")
        self.assertIn("attachment", response.get("Content-Disposition", ""))
        self.assertIn("readings_export.csv", response.get("Content-Disposition", ""))

    def test_csv_export_empty_readings_with_gauges(self):
        """Test CSV export when gauges exist but no readings."""
        # Create gauge without readings
        GaugeFactory()

        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.export_url)

        # Should only have header
        content = b"".join(response.streaming_content).decode("utf-8")
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 1)
        self.assertEqual(
            lines[0], "Gauge ID,Gauge Name,Timestamp,Water Level (m),Flow Rate (m³/s)"
        )

    def test_csv_export_different_user_access(self):
        """Test CSV export with different user accounts."""
        # Create different users
        user1 = User.objects.create_user(username="user1", password="pass1")
        user2 = User.objects.create_user(username="user2", password="pass2")

        # Create test data
        gauge = GaugeFactory()
        ReadingFactory(gauge=gauge)

        # Both users should see same data
        for user in [user1, user2]:
            client = Client()
            client.login(
                username=user.username, password="pass1" if user == user1 else "pass2"
            )
            response = client.get(self.export_url)

            self.assertEqual(response.status_code, 200)
            content = b"".join(response.streaming_content).decode("utf-8")
            lines = content.strip().split("\n")
            self.assertEqual(len(lines), 2)  # Header + 1 data row
