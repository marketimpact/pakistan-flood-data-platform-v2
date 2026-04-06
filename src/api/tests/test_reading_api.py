"""Comprehensive tests for Reading API endpoints."""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from decimal import Decimal

from core.models import Gauge, Reading
from core.tests.factories import GaugeFactory, ReadingFactory

User = get_user_model()


class TestReadingAPIBase(APITestCase):
    """Base class for Reading API tests."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpassword123", email="test@example.com"
        )
        self.client.force_authenticate(user=self.user)

        # Create test gauges
        self.gauge1 = GaugeFactory(
            gauge_id="PK001",
            name="Test Gauge 1",
            latitude=31.5204,
            longitude=74.3587,
            country_code="PK",
            status="active",
        )
        self.gauge2 = GaugeFactory(
            gauge_id="PK002",
            name="Test Gauge 2",
            latitude=33.6844,
            longitude=73.0479,
            country_code="PK",
            status="active",
        )

        # Create test readings
        self.reading1 = ReadingFactory(
            gauge=self.gauge1,
            timestamp=timezone.now() - timedelta(hours=1),
            water_level=5.0,
            flow_rate=100.0,
        )
        self.reading2 = ReadingFactory(
            gauge=self.gauge1,
            timestamp=timezone.now() - timedelta(hours=2),
            water_level=4.5,
            flow_rate=95.0,
        )
        self.reading3 = ReadingFactory(
            gauge=self.gauge2,
            timestamp=timezone.now() - timedelta(hours=1),
            water_level=8.0,
            flow_rate=150.0,
        )

        # API endpoints
        self.reading_list_url = reverse("reading-list")
        self.reading_detail_url = reverse(
            "reading-detail", kwargs={"pk": self.reading1.pk}
        )


class TestReadingListEndpoint(TestReadingAPIBase):
    """Test Reading list endpoint."""

    def test_reading_list_success(self):
        """Test successful reading list retrieval."""
        response = self.client.get(self.reading_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 3)

    def test_reading_list_data_structure(self):
        """Test reading list data structure."""
        response = self.client.get(self.reading_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reading_data = response.data[0]

        # Check required fields
        required_fields = ["id", "gauge", "timestamp", "water_level", "flow_rate"]
        for field in required_fields:
            self.assertIn(field, reading_data)

    def test_reading_list_field_types(self):
        """Test reading list field types."""
        response = self.client.get(self.reading_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reading_data = response.data[0]

        # Check field types
        self.assertIsInstance(reading_data["id"], str)  # UUID as string
        self.assertIsInstance(reading_data["gauge"], str)  # Gauge UUID as string
        self.assertIsInstance(reading_data["timestamp"], str)  # ISO datetime string
        self.assertIsInstance(reading_data["water_level"], (int, float))
        self.assertIsInstance(
            reading_data["flow_rate"], (int, float, type(None))
        )  # Can be null

    def test_reading_list_timestamp_format(self):
        """Test reading list timestamp format."""
        response = self.client.get(self.reading_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reading_data = response.data[0]

        # Check timestamp format (ISO 8601)
        timestamp = reading_data["timestamp"]
        self.assertRegex(timestamp, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    def test_reading_list_gauge_reference(self):
        """Test that gauge references are valid UUIDs."""
        response = self.client.get(self.reading_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for reading in response.data:
            gauge_id = reading["gauge"]

            # Should be valid UUID format
            import uuid

            try:
                uuid.UUID(gauge_id)
            except ValueError:
                self.fail(f"Invalid UUID format for gauge: {gauge_id}")

    def test_reading_list_ordering(self):
        """Test reading list ordering."""
        response = self.client.get(self.reading_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        readings = response.data

        # Check that readings are returned in consistent order
        self.assertEqual(len(readings), 3)

        # Readings should be ordered by timestamp (most recent first, typically)
        timestamps = [reading["timestamp"] for reading in readings]
        self.assertEqual(len(timestamps), len(set(timestamps)))  # No duplicates

    def test_reading_list_empty_response(self):
        """Test reading list with no readings."""
        # Delete all readings
        Reading.objects.all().delete()

        response = self.client.get(self.reading_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 0)

    def test_reading_list_content_type(self):
        """Test reading list content type."""
        response = self.client.get(self.reading_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get("Content-Type"), "application/json")

    def test_reading_list_with_accept_header(self):
        """Test reading list with different accept headers."""
        headers = ["application/json", "application/xml", "text/html", "*/*"]

        for header in headers:
            response = self.client.get(self.reading_list_url, HTTP_ACCEPT=header)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestReadingDetailEndpoint(TestReadingAPIBase):
    """Test Reading detail endpoint."""

    def test_reading_detail_success(self):
        """Test successful reading detail retrieval."""
        response = self.client.get(self.reading_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check response data
        self.assertEqual(response.data["id"], str(self.reading1.pk))
        self.assertEqual(response.data["gauge"], str(self.reading1.gauge.pk))
        self.assertEqual(
            float(response.data["water_level"]), float(self.reading1.water_level)
        )
        self.assertEqual(
            float(response.data["flow_rate"]), float(self.reading1.flow_rate)
        )

    def test_reading_detail_not_found(self):
        """Test reading detail with non-existent ID."""
        import uuid

        non_existent_id = uuid.uuid4()
        url = reverse("reading-detail", kwargs={"pk": non_existent_id})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("detail", response.data)
        self.assertIn("not found", response.data["detail"].lower())

    def test_reading_detail_invalid_id_format(self):
        """Test reading detail with invalid ID format."""
        url = reverse("reading-detail", kwargs={"pk": "invalid-uuid"})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reading_detail_data_structure(self):
        """Test reading detail data structure."""
        response = self.client.get(self.reading_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check required fields
        required_fields = ["id", "gauge", "timestamp", "water_level", "flow_rate"]
        for field in required_fields:
            self.assertIn(field, response.data)

    def test_reading_detail_field_types(self):
        """Test reading detail field types."""
        response = self.client.get(self.reading_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check field types
        self.assertIsInstance(response.data["id"], str)  # UUID as string
        self.assertIsInstance(response.data["gauge"], str)  # Gauge UUID as string
        self.assertIsInstance(response.data["timestamp"], str)  # ISO datetime string
        self.assertIsInstance(response.data["water_level"], (int, float))
        self.assertIsInstance(response.data["flow_rate"], (int, float, type(None)))

    def test_reading_detail_timestamp_precision(self):
        """Test reading detail timestamp precision."""
        response = self.client.get(self.reading_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check timestamp format and precision
        timestamp = response.data["timestamp"]
        self.assertRegex(timestamp, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    def test_reading_detail_content_type(self):
        """Test reading detail content type."""
        response = self.client.get(self.reading_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get("Content-Type"), "application/json")


class TestReadingAPIPagination(TestReadingAPIBase):
    """Test Reading API pagination."""

    def test_reading_list_pagination_structure(self):
        """Test pagination structure in reading list."""
        response = self.client.get(self.reading_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # API returns list directly (no pagination)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 3)

    def test_reading_list_pagination_with_many_items(self):
        """Test pagination with many reading items."""
        # Create many additional readings
        ReadingFactory.create_batch(25, gauge=self.gauge1)

        response = self.client.get(self.reading_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # API returns list directly (no pagination)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 28)  # 3 existing + 25 new

    def test_reading_list_pagination_page_size(self):
        """Test pagination page size parameter."""
        # Create additional readings
        ReadingFactory.create_batch(10, gauge=self.gauge1)

        response = self.client.get(self.reading_list_url, {"page_size": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # API returns list directly (no pagination)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 13)  # 3 existing + 10 new

    def test_reading_list_pagination_page_parameter(self):
        """Test pagination page parameter."""
        # Create additional readings
        ReadingFactory.create_batch(10, gauge=self.gauge1)

        # Test first page
        response = self.client.get(self.reading_list_url, {"page": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test invalid page
        response = self.client.get(self.reading_list_url, {"page": 999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reading_list_pagination_invalid_parameters(self):
        """Test pagination with invalid parameters."""
        invalid_params = [
            {"page": "invalid"},
            {"page": -1},
            {"page": 0},
            {"page_size": "invalid"},
            {"page_size": -1},
            {"page_size": 0},
        ]

        for params in invalid_params:
            response = self.client.get(self.reading_list_url, params)
            # Should either return 400 or ignore invalid params
            self.assertIn(
                response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
            )


class TestReadingAPIFiltering(TestReadingAPIBase):
    """Test Reading API filtering capabilities."""

    def test_reading_list_filter_by_gauge(self):
        """Test filtering readings by gauge."""
        response = self.client.get(
            self.reading_list_url, {"gauge": str(self.gauge1.pk)}
        )

        if response.status_code == status.HTTP_200_OK:
            for reading in response.data["results"]:
                self.assertEqual(reading["gauge"], str(self.gauge1.pk))

    def test_reading_list_filter_by_gauge_id(self):
        """Test filtering readings by gauge ID."""
        response = self.client.get(self.reading_list_url, {"gauge__gauge_id": "PK001"})

        if response.status_code == status.HTTP_200_OK:
            # If nested filtering is supported
            for reading in response.data["results"]:
                self.assertEqual(reading["gauge"], str(self.gauge1.pk))

    def test_reading_list_filter_by_timestamp_range(self):
        """Test filtering readings by timestamp range."""
        # Filter for readings from the last hour
        since = (timezone.now() - timedelta(hours=1)).isoformat()
        response = self.client.get(self.reading_list_url, {"timestamp__gte": since})

        if response.status_code == status.HTTP_200_OK:
            # Should return readings from the last hour
            for reading in response.data["results"]:
                reading_time = reading["timestamp"]
                self.assertGreaterEqual(reading_time, since)

    def test_reading_list_filter_by_water_level_range(self):
        """Test filtering readings by water level range."""
        response = self.client.get(
            self.reading_list_url, {"water_level__gte": 5.0, "water_level__lte": 10.0}
        )

        if response.status_code == status.HTTP_200_OK:
            for reading in response.data["results"]:
                water_level = float(reading["water_level"])
                self.assertGreaterEqual(water_level, 5.0)
                self.assertLessEqual(water_level, 10.0)

    def test_reading_list_ordering_by_timestamp(self):
        """Test ordering readings by timestamp."""
        response = self.client.get(self.reading_list_url, {"ordering": "timestamp"})

        if response.status_code == status.HTTP_200_OK:
            if len(response.data["results"]) > 1:
                timestamps = [
                    reading["timestamp"] for reading in response.data["results"]
                ]
                self.assertEqual(timestamps, sorted(timestamps))

    def test_reading_list_ordering_by_water_level(self):
        """Test ordering readings by water level."""
        response = self.client.get(self.reading_list_url, {"ordering": "water_level"})

        if response.status_code == status.HTTP_200_OK:
            if len(response.data["results"]) > 1:
                water_levels = [
                    float(reading["water_level"])
                    for reading in response.data["results"]
                ]
                self.assertEqual(water_levels, sorted(water_levels))

    def test_reading_list_reverse_ordering(self):
        """Test reverse ordering of readings."""
        response = self.client.get(self.reading_list_url, {"ordering": "-timestamp"})

        if response.status_code == status.HTTP_200_OK:
            if len(response.data["results"]) > 1:
                timestamps = [
                    reading["timestamp"] for reading in response.data["results"]
                ]
                self.assertEqual(timestamps, sorted(timestamps, reverse=True))

    def test_reading_list_invalid_filter_parameters(self):
        """Test invalid filter parameters."""
        invalid_params = [
            {"gauge": "invalid-uuid"},
            {"timestamp__gte": "invalid-date"},
            {"water_level__gte": "invalid-number"},
            {"ordering": "invalid_field"},
            {"invalid_param": "value"},
        ]

        for params in invalid_params:
            response = self.client.get(self.reading_list_url, params)
            # Should either return 400 or ignore invalid params
            self.assertIn(
                response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
            )

    def test_reading_list_multiple_filters(self):
        """Test multiple filters combined."""
        response = self.client.get(
            self.reading_list_url,
            {
                "gauge": str(self.gauge1.pk),
                "water_level__gte": 4.0,
                "ordering": "-timestamp",
            },
        )

        if response.status_code == status.HTTP_200_OK:
            for reading in response.data["results"]:
                self.assertEqual(reading["gauge"], str(self.gauge1.pk))
                self.assertGreaterEqual(float(reading["water_level"]), 4.0)


class TestReadingAPIReadOnly(TestReadingAPIBase):
    """Test read-only enforcement for Reading API."""

    def test_reading_list_post_not_allowed(self):
        """Test that POST is not allowed on reading list."""
        response = self.client.post(
            self.reading_list_url,
            {
                "gauge": str(self.gauge1.pk),
                "timestamp": timezone.now().isoformat(),
                "water_level": 10.0,
                "flow_rate": 200.0,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_reading_detail_put_not_allowed(self):
        """Test that PUT is not allowed on reading detail."""
        response = self.client.put(
            self.reading_detail_url,
            {
                "gauge": str(self.gauge1.pk),
                "timestamp": timezone.now().isoformat(),
                "water_level": 15.0,
                "flow_rate": 250.0,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_reading_detail_patch_not_allowed(self):
        """Test that PATCH is not allowed on reading detail."""
        response = self.client.patch(self.reading_detail_url, {"water_level": 20.0})

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_reading_detail_delete_not_allowed(self):
        """Test that DELETE is not allowed on reading detail."""
        response = self.client.delete(self.reading_detail_url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_reading_allowed_methods(self):
        """Test allowed methods for reading endpoints."""
        # Test OPTIONS to see allowed methods
        response = self.client.options(self.reading_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check Allow header if present
        if "Allow" in response.headers:
            allowed_methods = response.headers["Allow"].split(", ")
            self.assertIn("GET", allowed_methods)
            self.assertIn("HEAD", allowed_methods)
            self.assertIn("OPTIONS", allowed_methods)
            self.assertNotIn("POST", allowed_methods)
            self.assertNotIn("PUT", allowed_methods)
            self.assertNotIn("PATCH", allowed_methods)
            self.assertNotIn("DELETE", allowed_methods)

    def test_reading_head_requests_allowed(self):
        """Test that HEAD requests are allowed."""
        response = self.client.head(self.reading_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.head(self.reading_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_reading_options_requests_allowed(self):
        """Test that OPTIONS requests are allowed."""
        response = self.client.options(self.reading_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.options(self.reading_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestReadingAPIErrorHandling(TestReadingAPIBase):
    """Test error handling in Reading API."""

    def test_reading_list_server_error_handling(self):
        """Test server error handling for reading list."""
        # This would require mocking database errors
        # For now, just test that the endpoint is accessible
        response = self.client.get(self.reading_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_reading_detail_not_found_error(self):
        """Test 404 error handling for reading detail."""
        import uuid

        non_existent_id = uuid.uuid4()
        url = reverse("reading-detail", kwargs={"pk": non_existent_id})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("detail", response.data)

    def test_reading_api_malformed_requests(self):
        """Test API with malformed requests."""
        # Test with invalid content type
        response = self.client.post(
            self.reading_list_url, '{"invalid": "json"', content_type="application/json"
        )

        # Should return 405 for POST, not 400 for malformed JSON
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_reading_api_large_request_handling(self):
        """Test API with large request data."""
        # Create a large request body
        large_data = {"data": "x" * 10000}

        response = self.client.post(self.reading_list_url, large_data)

        # Should return 405 for POST
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_reading_api_invalid_http_methods(self):
        """Test API with invalid HTTP methods."""
        # These methods should not be allowed
        forbidden_methods = ["POST", "PUT", "PATCH", "DELETE"]

        for method in forbidden_methods:
            response = getattr(self.client, method.lower())(self.reading_list_url)
            self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class TestReadingAPIDataIntegrity(TestReadingAPIBase):
    """Test data integrity in Reading API."""

    def test_reading_data_integrity(self):
        """Test that reading data maintains integrity."""
        response = self.client.get(self.reading_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check data integrity
        reading_data = response.data

        # Water level should be reasonable
        water_level = float(reading_data["water_level"])
        self.assertGreaterEqual(water_level, 0.0)  # Should not be negative
        self.assertLessEqual(water_level, 1000.0)  # Should be reasonable upper bound

        # Flow rate should be reasonable (if present)
        if reading_data["flow_rate"] is not None:
            flow_rate = float(reading_data["flow_rate"])
            self.assertGreaterEqual(flow_rate, 0.0)  # Should not be negative
            self.assertLessEqual(
                flow_rate, 100000.0
            )  # Should be reasonable upper bound

    def test_reading_required_fields_present(self):
        """Test that all required fields are present."""
        response = self.client.get(self.reading_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for reading in response.data["results"]:
            # Check all required fields are present
            required_fields = ["id", "gauge", "timestamp", "water_level"]
            for field in required_fields:
                self.assertIn(field, reading)
                self.assertIsNotNone(reading[field])

            # flow_rate can be null but should be present
            self.assertIn("flow_rate", reading)

    def test_reading_gauge_references_valid(self):
        """Test that gauge references are valid."""
        response = self.client.get(self.reading_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Get all gauge IDs
        gauge_ids = set(str(gauge.pk) for gauge in Gauge.objects.all())

        for reading in response.data["results"]:
            gauge_id = reading["gauge"]
            self.assertIn(gauge_id, gauge_ids)

    def test_reading_timestamp_consistency(self):
        """Test timestamp consistency."""
        response = self.client.get(self.reading_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for reading in response.data["results"]:
            timestamp = reading["timestamp"]

            # Should be valid ISO format
            from datetime import datetime

            try:
                datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                self.fail(f"Invalid timestamp format: {timestamp}")

    def test_reading_uuid_format(self):
        """Test that reading UUIDs are properly formatted."""
        response = self.client.get(self.reading_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check UUID format
        import uuid

        reading_id = response.data["id"]
        gauge_id = response.data["gauge"]

        # Should be able to parse as UUIDs
        try:
            uuid.UUID(reading_id)
            uuid.UUID(gauge_id)
        except ValueError:
            self.fail(f"Invalid UUID format: {reading_id} or {gauge_id}")

    def test_reading_numerical_precision(self):
        """Test numerical precision in readings."""
        response = self.client.get(self.reading_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check numerical precision
        water_level = response.data["water_level"]

        # Should have reasonable precision
        water_level_str = str(water_level)
        if "." in water_level_str:
            decimals = len(water_level_str.split(".")[1])
            self.assertLessEqual(decimals, 4)  # Reasonable precision

        # Same for flow rate if present
        if response.data["flow_rate"] is not None:
            flow_rate = response.data["flow_rate"]
            flow_rate_str = str(flow_rate)
            if "." in flow_rate_str:
                decimals = len(flow_rate_str.split(".")[1])
                self.assertLessEqual(decimals, 4)  # Reasonable precision


class TestReadingAPIPerformance(TestReadingAPIBase):
    """Test performance aspects of Reading API."""

    def test_reading_list_response_time(self):
        """Test reading list response time."""
        import time

        start_time = time.time()
        response = self.client.get(self.reading_list_url)
        end_time = time.time()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Response should be reasonably fast (less than 1 second)
        response_time = end_time - start_time
        self.assertLess(response_time, 1.0)

    def test_reading_detail_response_time(self):
        """Test reading detail response time."""
        import time

        start_time = time.time()
        response = self.client.get(self.reading_detail_url)
        end_time = time.time()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Response should be reasonably fast (less than 1 second)
        response_time = end_time - start_time
        self.assertLess(response_time, 1.0)

    def test_reading_list_with_many_items(self):
        """Test reading list performance with many items."""
        # Create many readings
        ReadingFactory.create_batch(100, gauge=self.gauge1)

        import time

        start_time = time.time()
        response = self.client.get(self.reading_list_url)
        end_time = time.time()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 103)  # 3 existing + 100 new

        # Should still be reasonably fast
        response_time = end_time - start_time
        self.assertLess(response_time, 2.0)

    def test_reading_api_concurrent_requests(self):
        """Test reading API with concurrent requests."""
        import threading
        import time

        results = []

        def make_request():
            response = self.client.get(self.reading_list_url)
            results.append(response.status_code)

        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)

        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        end_time = time.time()

        # All requests should succeed
        self.assertEqual(len(results), 10)
        for result in results:
            self.assertEqual(result, status.HTTP_200_OK)

        # Should complete within reasonable time
        total_time = end_time - start_time
        self.assertLess(total_time, 5.0)

    def test_reading_api_memory_usage(self):
        """Test reading API memory usage with large datasets."""
        # Create many readings
        ReadingFactory.create_batch(50, gauge=self.gauge1)

        # Get memory usage before request
        import psutil
        import os

        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss

        # Make request
        response = self.client.get(self.reading_list_url)

        # Get memory usage after request
        memory_after = process.memory_info().rss

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Memory increase should be reasonable (less than 50MB)
        memory_increase = memory_after - memory_before
        self.assertLess(memory_increase, 50 * 1024 * 1024)  # 50MB


class TestReadingAPIRealWorldScenarios(TestReadingAPIBase):
    """Test real-world scenarios for Reading API."""

    def test_reading_api_with_recent_data(self):
        """Test reading API with recent data."""
        # Create readings with recent timestamps
        recent_readings = []
        for i in range(5):
            reading = ReadingFactory(
                gauge=self.gauge1,
                timestamp=timezone.now() - timedelta(minutes=i * 10),
                water_level=5.0 + i * 0.5,
            )
            recent_readings.append(reading)

        response = self.client.get(self.reading_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 5)

    def test_reading_api_with_historical_data(self):
        """Test reading API with historical data."""
        # Create readings with historical timestamps
        historical_readings = []
        for i in range(10):
            reading = ReadingFactory(
                gauge=self.gauge1,
                timestamp=timezone.now() - timedelta(days=i),
                water_level=3.0 + i * 0.2,
            )
            historical_readings.append(reading)

        response = self.client.get(self.reading_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 10)

    def test_reading_api_with_mixed_gauges(self):
        """Test reading API with readings from multiple gauges."""
        # Create additional gauges
        gauge3 = GaugeFactory(gauge_id="PK003")
        gauge4 = GaugeFactory(gauge_id="PK004")

        # Create readings for each gauge
        ReadingFactory.create_batch(5, gauge=gauge3)
        ReadingFactory.create_batch(5, gauge=gauge4)

        response = self.client.get(self.reading_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 10)

        # Check that readings from different gauges are included
        gauge_ids = set(reading["gauge"] for reading in response.data)
        self.assertGreaterEqual(len(gauge_ids), 2)

    def test_reading_api_with_varying_data_quality(self):
        """Test reading API with varying data quality."""
        # Create readings with different data quality scenarios
        ReadingFactory(gauge=self.gauge1, water_level=0.0, flow_rate=0.0)  # Zero values
        ReadingFactory(
            gauge=self.gauge1, water_level=999.99, flow_rate=None
        )  # High value, no flow
        ReadingFactory(
            gauge=self.gauge1, water_level=5.123456, flow_rate=100.789
        )  # High precision

        response = self.client.get(self.reading_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # All readings should be handled properly
        for reading in response.data["results"]:
            self.assertIsNotNone(reading["water_level"])
            self.assertGreaterEqual(float(reading["water_level"]), 0.0)

    def test_reading_api_time_zone_handling(self):
        """Test reading API with different time zones."""
        # Create readings with different timezone-aware timestamps
        from django.utils import timezone
        import pytz

        # UTC timestamp
        utc_reading = ReadingFactory(
            gauge=self.gauge1, timestamp=timezone.now(), water_level=5.0
        )

        response = self.client.get(self.reading_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that timestamps are handled consistently
        for reading in response.data["results"]:
            timestamp = reading["timestamp"]
            # Should contain timezone information
            self.assertTrue(
                timestamp.endswith("Z") or "+" in timestamp or "-" in timestamp[-6:]
            )

    def test_reading_api_edge_cases(self):
        """Test reading API with edge cases."""
        # Create readings with edge case values
        ReadingFactory(gauge=self.gauge1, water_level=0.001)  # Very small value
        ReadingFactory(gauge=self.gauge1, water_level=999.999)  # Very large value
        ReadingFactory(gauge=self.gauge1, flow_rate=None)  # Null flow rate

        response = self.client.get(self.reading_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # All readings should be serialized properly
        for reading in response.data["results"]:
            self.assertIsInstance(reading["water_level"], (int, float))
            # flow_rate can be null
            if reading["flow_rate"] is not None:
                self.assertIsInstance(reading["flow_rate"], (int, float))
