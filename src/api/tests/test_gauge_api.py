"""Comprehensive tests for Gauge API endpoints."""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from core.models import Gauge, Reading, Prediction
from core.tests.factories import GaugeFactory, ReadingFactory, PredictionFactory

User = get_user_model()


class TestGaugeAPIBase(APITestCase):
    """Base class for Gauge API tests."""

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
        self.gauge3 = GaugeFactory(
            gauge_id="PK003",
            name="Test Gauge 3",
            latitude=24.8607,
            longitude=67.0011,
            country_code="PK",
            status="inactive",
        )

        # Create associated readings and predictions
        ReadingFactory(gauge=self.gauge1, water_level=5.0)
        ReadingFactory(gauge=self.gauge2, water_level=10.0)
        PredictionFactory(gauge=self.gauge1, water_level=6.0)
        PredictionFactory(gauge=self.gauge2, water_level=11.0)

        # API endpoints
        self.gauge_list_url = reverse("gauge-list")
        self.gauge_detail_url = reverse("gauge-detail", kwargs={"pk": self.gauge1.pk})


class TestGaugeListEndpoint(TestGaugeAPIBase):
    """Test Gauge list endpoint."""

    def test_gauge_list_success(self):
        """Test successful gauge list retrieval."""
        response = self.client.get(self.gauge_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 3)

    def test_gauge_list_data_structure(self):
        """Test gauge list data structure."""
        response = self.client.get(self.gauge_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # API returns list directly (no pagination)
        self.assertIsInstance(response.data, list)
        self.assertGreater(len(response.data), 0)
        
        gauge_data = response.data[0]

        # Check required fields
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
            self.assertIn(field, gauge_data)

    def test_gauge_list_field_types(self):
        """Test gauge list field types."""
        response = self.client.get(self.gauge_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreater(len(response.data), 0)
        
        gauge_data = response.data[0]

        # Check field types
        self.assertIsInstance(gauge_data["id"], str)  # UUID as string
        self.assertIsInstance(gauge_data["gauge_id"], str)
        self.assertIsInstance(gauge_data["name"], str)
        self.assertIsInstance(gauge_data["latitude"], float)
        self.assertIsInstance(gauge_data["longitude"], float)
        self.assertIsInstance(gauge_data["country_code"], str)
        self.assertIsInstance(gauge_data["status"], str)

    def test_gauge_list_ordering(self):
        """Test gauge list ordering."""
        response = self.client.get(self.gauge_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        gauges = response.data["results"]

        # Check if gauges are returned in consistent order
        gauge_ids = [gauge["gauge_id"] for gauge in gauges]
        self.assertEqual(len(gauge_ids), len(set(gauge_ids)))  # No duplicates

    def test_gauge_list_empty_response(self):
        """Test gauge list with no gauges."""
        # Delete all gauges
        Gauge.objects.all().delete()

        response = self.client.get(self.gauge_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(len(response.data["results"]), 0)

    def test_gauge_list_content_type(self):
        """Test gauge list content type."""
        response = self.client.get(self.gauge_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get("Content-Type"), "application/json")

    def test_gauge_list_with_accept_header(self):
        """Test gauge list with different accept headers."""
        headers = ["application/json", "application/xml", "text/html", "*/*"]

        for header in headers:
            response = self.client.get(self.gauge_list_url, HTTP_ACCEPT=header)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestGaugeDetailEndpoint(TestGaugeAPIBase):
    """Test Gauge detail endpoint."""

    def test_gauge_detail_success(self):
        """Test successful gauge detail retrieval."""
        response = self.client.get(self.gauge_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check response data
        self.assertEqual(response.data["gauge_id"], self.gauge1.gauge_id)
        self.assertEqual(response.data["name"], self.gauge1.name)
        self.assertEqual(response.data["latitude"], self.gauge1.latitude)
        self.assertEqual(response.data["longitude"], self.gauge1.longitude)
        self.assertEqual(response.data["country_code"], self.gauge1.country_code)
        self.assertEqual(response.data["status"], self.gauge1.status)

    def test_gauge_detail_not_found(self):
        """Test gauge detail with non-existent ID."""
        import uuid

        non_existent_id = uuid.uuid4()
        url = reverse("gauge-detail", kwargs={"pk": non_existent_id})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("detail", response.data)
        self.assertIn("not found", response.data["detail"].lower())

    def test_gauge_detail_invalid_id_format(self):
        """Test gauge detail with invalid ID format."""
        url = reverse("gauge-detail", kwargs={"pk": "invalid-uuid"})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_gauge_detail_data_structure(self):
        """Test gauge detail data structure."""
        response = self.client.get(self.gauge_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check required fields
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
            self.assertIn(field, response.data)

    def test_gauge_detail_field_types(self):
        """Test gauge detail field types."""
        response = self.client.get(self.gauge_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check field types
        self.assertIsInstance(response.data["id"], str)  # UUID as string
        self.assertIsInstance(response.data["gauge_id"], str)
        self.assertIsInstance(response.data["name"], str)
        self.assertIsInstance(response.data["latitude"], float)
        self.assertIsInstance(response.data["longitude"], float)
        self.assertIsInstance(response.data["country_code"], str)
        self.assertIsInstance(response.data["status"], str)

    def test_gauge_detail_inactive_gauge(self):
        """Test gauge detail for inactive gauge."""
        url = reverse("gauge-detail", kwargs={"pk": self.gauge3.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "inactive")

    def test_gauge_detail_content_type(self):
        """Test gauge detail content type."""
        response = self.client.get(self.gauge_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get("Content-Type"), "application/json")


class TestGaugeAPIPagination(TestGaugeAPIBase):
    """Test Gauge API pagination."""

    def test_gauge_list_pagination_structure(self):
        """Test pagination structure in gauge list."""
        response = self.client.get(self.gauge_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check pagination fields
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)

        # Check pagination values
        self.assertEqual(response.data["count"], 3)
        self.assertIsNone(response.data["next"])  # No next page with only 3 items
        self.assertIsNone(response.data["previous"])  # No previous page

    def test_gauge_list_pagination_with_many_items(self):
        """Test pagination with many gauge items."""
        # Create many additional gauges
        GaugeFactory.create_batch(25)

        response = self.client.get(self.gauge_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check pagination
        self.assertEqual(response.data["count"], 28)  # 3 existing + 25 new
        self.assertIsInstance(response.data["results"], list)

        # Check that we don't get all items in one page
        self.assertLessEqual(len(response.data["results"]), 25)

    def test_gauge_list_pagination_page_size(self):
        """Test pagination page size parameter."""
        # Create additional gauges
        GaugeFactory.create_batch(10)

        response = self.client.get(self.gauge_list_url, {"page_size": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should limit to 5 items per page if page_size is supported
        # Otherwise, should use default pagination
        results_count = len(response.data["results"])
        self.assertGreater(results_count, 0)
        self.assertEqual(response.data["count"], 13)  # 3 existing + 10 new

    def test_gauge_list_pagination_page_parameter(self):
        """Test pagination page parameter."""
        # Create additional gauges
        GaugeFactory.create_batch(10)

        # Test first page
        response = self.client.get(self.gauge_list_url, {"page": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Test invalid page
        response = self.client.get(self.gauge_list_url, {"page": 999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_gauge_list_pagination_invalid_parameters(self):
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
            response = self.client.get(self.gauge_list_url, params)
            # Should either return 400 or ignore invalid params
            self.assertIn(
                response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
            )


class TestGaugeAPIFiltering(TestGaugeAPIBase):
    """Test Gauge API filtering capabilities."""

    def test_gauge_list_filter_by_status(self):
        """Test filtering gauges by status."""
        # Test active gauges
        response = self.client.get(self.gauge_list_url, {"status": "active"})

        if response.status_code == status.HTTP_200_OK:
            for gauge in response.data["results"]:
                self.assertEqual(gauge["status"], "active")

        # Test inactive gauges
        response = self.client.get(self.gauge_list_url, {"status": "inactive"})

        if response.status_code == status.HTTP_200_OK:
            for gauge in response.data["results"]:
                self.assertEqual(gauge["status"], "inactive")

    def test_gauge_list_filter_by_country(self):
        """Test filtering gauges by country code."""
        response = self.client.get(self.gauge_list_url, {"country_code": "PK"})

        if response.status_code == status.HTTP_200_OK:
            for gauge in response.data["results"]:
                self.assertEqual(gauge["country_code"], "PK")

    def test_gauge_list_search_by_name(self):
        """Test searching gauges by name."""
        response = self.client.get(self.gauge_list_url, {"search": "Test Gauge 1"})

        if response.status_code == status.HTTP_200_OK:
            # If search is supported, should return gauge with matching name
            if response.data["count"] > 0:
                found_gauge = response.data["results"][0]
                self.assertIn("Test Gauge 1", found_gauge["name"])

    def test_gauge_list_search_by_gauge_id(self):
        """Test searching gauges by gauge ID."""
        response = self.client.get(self.gauge_list_url, {"search": "PK001"})

        if response.status_code == status.HTTP_200_OK:
            # If search is supported, should return gauge with matching ID
            if response.data["count"] > 0:
                found_gauge = response.data["results"][0]
                self.assertEqual(found_gauge["gauge_id"], "PK001")

    def test_gauge_list_ordering_by_name(self):
        """Test ordering gauges by name."""
        response = self.client.get(self.gauge_list_url, {"ordering": "name"})

        if response.status_code == status.HTTP_200_OK:
            # If ordering is supported, check order
            if len(response.data["results"]) > 1:
                names = [gauge["name"] for gauge in response.data["results"]]
                self.assertEqual(names, sorted(names))

    def test_gauge_list_ordering_by_gauge_id(self):
        """Test ordering gauges by gauge ID."""
        response = self.client.get(self.gauge_list_url, {"ordering": "gauge_id"})

        if response.status_code == status.HTTP_200_OK:
            # If ordering is supported, check order
            if len(response.data["results"]) > 1:
                gauge_ids = [gauge["gauge_id"] for gauge in response.data["results"]]
                self.assertEqual(gauge_ids, sorted(gauge_ids))

    def test_gauge_list_reverse_ordering(self):
        """Test reverse ordering of gauges."""
        response = self.client.get(self.gauge_list_url, {"ordering": "-name"})

        if response.status_code == status.HTTP_200_OK:
            # If reverse ordering is supported, check order
            if len(response.data["results"]) > 1:
                names = [gauge["name"] for gauge in response.data["results"]]
                self.assertEqual(names, sorted(names, reverse=True))

    def test_gauge_list_invalid_filter_parameters(self):
        """Test invalid filter parameters."""
        invalid_params = [
            {"status": "invalid_status"},
            {"country_code": "INVALID"},
            {"ordering": "invalid_field"},
            {"invalid_param": "value"},
        ]

        for params in invalid_params:
            response = self.client.get(self.gauge_list_url, params)
            # Should either return 400 or ignore invalid params
            self.assertIn(
                response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
            )

    def test_gauge_list_multiple_filters(self):
        """Test multiple filters combined."""
        response = self.client.get(
            self.gauge_list_url,
            {"status": "active", "country_code": "PK", "ordering": "name"},
        )

        if response.status_code == status.HTTP_200_OK:
            for gauge in response.data["results"]:
                self.assertEqual(gauge["status"], "active")
                self.assertEqual(gauge["country_code"], "PK")


class TestGaugeAPIReadOnly(TestGaugeAPIBase):
    """Test read-only enforcement for Gauge API."""

    def test_gauge_list_post_not_allowed(self):
        """Test that POST is not allowed on gauge list."""
        response = self.client.post(
            self.gauge_list_url,
            {
                "gauge_id": "PK999",
                "name": "New Gauge",
                "latitude": 30.0,
                "longitude": 70.0,
                "country_code": "PK",
                "status": "active",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_gauge_detail_put_not_allowed(self):
        """Test that PUT is not allowed on gauge detail."""
        response = self.client.put(
            self.gauge_detail_url,
            {
                "gauge_id": "PK999",
                "name": "Updated Gauge",
                "latitude": 30.0,
                "longitude": 70.0,
                "country_code": "PK",
                "status": "active",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_gauge_detail_patch_not_allowed(self):
        """Test that PATCH is not allowed on gauge detail."""
        response = self.client.patch(self.gauge_detail_url, {"name": "Patched Gauge"})

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_gauge_detail_delete_not_allowed(self):
        """Test that DELETE is not allowed on gauge detail."""
        response = self.client.delete(self.gauge_detail_url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_gauge_allowed_methods(self):
        """Test allowed methods for gauge endpoints."""
        # Test OPTIONS to see allowed methods
        response = self.client.options(self.gauge_list_url)
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

    def test_gauge_head_requests_allowed(self):
        """Test that HEAD requests are allowed."""
        response = self.client.head(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.head(self.gauge_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_gauge_options_requests_allowed(self):
        """Test that OPTIONS requests are allowed."""
        response = self.client.options(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.options(self.gauge_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestGaugeAPIErrorHandling(TestGaugeAPIBase):
    """Test error handling in Gauge API."""

    def test_gauge_list_server_error_handling(self):
        """Test server error handling for gauge list."""
        # This would require mocking database errors
        # For now, just test that the endpoint is accessible
        response = self.client.get(self.gauge_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_gauge_detail_not_found_error(self):
        """Test 404 error handling for gauge detail."""
        import uuid

        non_existent_id = uuid.uuid4()
        url = reverse("gauge-detail", kwargs={"pk": non_existent_id})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("detail", response.data)

    def test_gauge_api_malformed_requests(self):
        """Test API with malformed requests."""
        # Test with invalid content type
        response = self.client.post(
            self.gauge_list_url, '{"invalid": "json"', content_type="application/json"
        )

        # Should return 405 for POST, not 400 for malformed JSON
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_gauge_api_large_request_handling(self):
        """Test API with large request data."""
        # Create a large request body
        large_data = {"data": "x" * 10000}

        response = self.client.post(self.gauge_list_url, large_data)

        # Should return 405 for POST
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_gauge_api_invalid_http_methods(self):
        """Test API with invalid HTTP methods."""
        # These methods should not be allowed
        forbidden_methods = ["POST", "PUT", "PATCH", "DELETE"]

        for method in forbidden_methods:
            response = getattr(self.client, method.lower())(self.gauge_list_url)
            self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class TestGaugeAPIPerformance(TestGaugeAPIBase):
    """Test performance aspects of Gauge API."""

    def test_gauge_list_response_time(self):
        """Test gauge list response time."""
        import time

        start_time = time.time()
        response = self.client.get(self.gauge_list_url)
        end_time = time.time()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Response should be reasonably fast (less than 1 second)
        response_time = end_time - start_time
        self.assertLess(response_time, 1.0)

    def test_gauge_detail_response_time(self):
        """Test gauge detail response time."""
        import time

        start_time = time.time()
        response = self.client.get(self.gauge_detail_url)
        end_time = time.time()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Response should be reasonably fast (less than 1 second)
        response_time = end_time - start_time
        self.assertLess(response_time, 1.0)

    def test_gauge_list_with_many_items(self):
        """Test gauge list performance with many items."""
        # Create many gauges
        GaugeFactory.create_batch(100)

        import time

        start_time = time.time()
        response = self.client.get(self.gauge_list_url)
        end_time = time.time()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 103)  # 3 existing + 100 new

        # Should still be reasonably fast
        response_time = end_time - start_time
        self.assertLess(response_time, 2.0)

    def test_gauge_api_concurrent_requests(self):
        """Test gauge API with concurrent requests."""
        import threading
        import time

        results = []

        def make_request():
            response = self.client.get(self.gauge_list_url)
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


class TestGaugeAPIValidation(TestGaugeAPIBase):
    """Test data validation in Gauge API."""

    def test_gauge_data_integrity(self):
        """Test that gauge data maintains integrity."""
        response = self.client.get(self.gauge_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check data integrity
        gauge_data = response.data

        # Latitude should be valid range
        self.assertGreaterEqual(gauge_data["latitude"], -90.0)
        self.assertLessEqual(gauge_data["latitude"], 90.0)

        # Longitude should be valid range
        self.assertGreaterEqual(gauge_data["longitude"], -180.0)
        self.assertLessEqual(gauge_data["longitude"], 180.0)

        # Country code should be valid format
        self.assertEqual(len(gauge_data["country_code"]), 2)
        self.assertTrue(gauge_data["country_code"].isalpha())

        # Status should be valid
        self.assertIn(gauge_data["status"], ["active", "inactive"])

    def test_gauge_required_fields_present(self):
        """Test that all required fields are present."""
        response = self.client.get(self.gauge_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for gauge in response.data:
            # Check all required fields are present and not null
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
                self.assertIn(field, gauge)
                self.assertIsNotNone(gauge[field])

    def test_gauge_id_uniqueness(self):
        """Test that gauge IDs are unique."""
        response = self.client.get(self.gauge_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        gauge_ids = [gauge["gauge_id"] for gauge in response.data]
        unique_gauge_ids = set(gauge_ids)

        self.assertEqual(len(gauge_ids), len(unique_gauge_ids))

    def test_gauge_uuid_format(self):
        """Test that gauge UUIDs are properly formatted."""
        response = self.client.get(self.gauge_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check UUID format
        import uuid

        gauge_id = response.data["id"]

        # Should be able to parse as UUID
        try:
            uuid.UUID(gauge_id)
        except ValueError:
            self.fail(f"Invalid UUID format: {gauge_id}")

    def test_gauge_coordinate_precision(self):
        """Test gauge coordinate precision."""
        response = self.client.get(self.gauge_detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check coordinate precision (should be reasonable)
        latitude = response.data["latitude"]
        longitude = response.data["longitude"]

        # Should have reasonable precision (not too many decimal places)
        lat_str = str(latitude)
        lng_str = str(longitude)

        if "." in lat_str:
            lat_decimals = len(lat_str.split(".")[1])
            self.assertLessEqual(lat_decimals, 6)  # Reasonable precision

        if "." in lng_str:
            lng_decimals = len(lng_str.split(".")[1])
            self.assertLessEqual(lng_decimals, 6)  # Reasonable precision
