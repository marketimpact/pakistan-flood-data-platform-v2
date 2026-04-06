"""Integration tests for performance and load scenarios."""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from django.db import connection
from django.test.utils import override_settings
from unittest.mock import patch, Mock
from datetime import datetime, timedelta
import time
import threading
import multiprocessing
import psutil
import os

from core.models import Gauge, Reading, Prediction
from core.tests.factories import GaugeFactory, ReadingFactory, PredictionFactory

User = get_user_model()


class TestDatabasePerformance(TestCase):
    """Test database performance under various conditions."""

    def test_bulk_insert_performance(self):
        """Test performance of bulk data insertion."""
        gauge = GaugeFactory()

        # Test bulk_create performance
        start_time = time.time()

        readings = []
        for i in range(10000):
            readings.append(
                Reading(
                    gauge=gauge,
                    timestamp=timezone.now() - timedelta(hours=i),
                    water_level=5.0 + (i % 10) * 0.1,
                    flow_rate=100.0 + (i % 20),
                )
            )

        Reading.objects.bulk_create(readings, batch_size=1000)

        bulk_time = time.time() - start_time

        # Should complete in reasonable time
        self.assertLess(bulk_time, 5.0)  # Less than 5 seconds
        self.assertEqual(Reading.objects.count(), 10000)

    def test_query_performance_with_indexes(self):
        """Test query performance with proper indexes."""
        # Create test data
        gauges = []
        for i in range(10):
            gauge = GaugeFactory(gauge_id=f"PK{i:03d}")
            gauges.append(gauge)

        # Create many readings
        for gauge in gauges:
            ReadingFactory.create_batch(100, gauge=gauge)

        # Test query performance
        start_time = time.time()

        # Query with index (gauge_id)
        readings = Reading.objects.filter(gauge__gauge_id="PK005").count()

        query_time = time.time() - start_time

        # Should be fast with index
        self.assertLess(query_time, 0.1)  # Less than 100ms
        self.assertEqual(readings, 100)

    def test_aggregation_performance(self):
        """Test aggregation query performance."""
        from django.db.models import Avg, Max, Min, Count

        # Create test data
        gauge = GaugeFactory()
        ReadingFactory.create_batch(1000, gauge=gauge)

        # Test aggregation performance
        start_time = time.time()

        stats = Reading.objects.filter(gauge=gauge).aggregate(
            avg_level=Avg("water_level"),
            max_level=Max("water_level"),
            min_level=Min("water_level"),
            total_count=Count("id"),
        )

        agg_time = time.time() - start_time

        # Should be fast
        self.assertLess(agg_time, 0.5)  # Less than 500ms
        self.assertEqual(stats["total_count"], 1000)

    def test_pagination_performance(self):
        """Test pagination performance with large datasets."""
        gauge = GaugeFactory()

        # Create large dataset
        ReadingFactory.create_batch(5000, gauge=gauge)

        # Test pagination performance
        page_times = []

        for page in range(1, 11):  # Test first 10 pages
            start_time = time.time()

            offset = (page - 1) * 100
            readings = list(Reading.objects.all()[offset : offset + 100])

            page_time = time.time() - start_time
            page_times.append(page_time)

        # All pages should load quickly
        avg_page_time = sum(page_times) / len(page_times)
        self.assertLess(avg_page_time, 0.1)  # Less than 100ms average

    def test_database_connection_pooling(self):
        """Test database connection pooling efficiency."""
        import threading

        results = []

        def query_database():
            start = time.time()
            list(Gauge.objects.all()[:10])
            results.append(time.time() - start)

        # Create some data
        GaugeFactory.create_batch(100)

        # Run concurrent queries
        threads = []
        for i in range(20):
            thread = threading.Thread(target=query_database)
            threads.append(thread)

        start_time = time.time()

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        total_time = time.time() - start_time

        # Should handle concurrent queries efficiently
        self.assertLess(total_time, 2.0)  # Less than 2 seconds total
        self.assertEqual(len(results), 20)


class TestAPIPerformanceIntegration(TestCase):
    """Test API performance under load."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )

        # Create test data
        self.gauges = []
        for i in range(10):
            gauge = GaugeFactory(gauge_id=f"PK{i:03d}")
            self.gauges.append(gauge)
            ReadingFactory.create_batch(50, gauge=gauge)
            PredictionFactory.create_batch(10, gauge=gauge)

    def test_api_response_time(self):
        """Test API response times under normal load."""
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=self.user)

        endpoints = [
            "/api/gauges/",
            "/api/readings/",
            "/api/predictions/",
        ]

        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint)
            response_time = time.time() - start_time

            self.assertEqual(response.status_code, 200)
            self.assertLess(response_time, 1.0)  # Less than 1 second

    def test_api_concurrent_requests(self):
        """Test API performance with concurrent requests."""
        from rest_framework.test import APIClient
        import threading

        results = []

        def make_request(endpoint):
            client = APIClient()
            client.force_authenticate(user=self.user)

            start = time.time()
            response = client.get(endpoint)
            duration = time.time() - start

            results.append(
                {
                    "endpoint": endpoint,
                    "status": response.status_code,
                    "duration": duration,
                }
            )

        # Make concurrent requests
        threads = []
        endpoints = ["/api/gauges/", "/api/readings/", "/api/predictions/"]

        for _ in range(10):  # 10 requests per endpoint
            for endpoint in endpoints:
                thread = threading.Thread(target=make_request, args=(endpoint,))
                threads.append(thread)

        start_time = time.time()

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        total_time = time.time() - start_time

        # Check results
        self.assertEqual(len(results), 30)  # 10 requests * 3 endpoints

        # All should succeed
        for result in results:
            self.assertEqual(result["status"], 200)
            self.assertLess(result["duration"], 2.0)  # Each request < 2 seconds

        # Total time should be reasonable
        self.assertLess(total_time, 5.0)  # All complete in < 5 seconds

    def test_api_filtering_performance(self):
        """Test API filtering performance."""
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=self.user)

        # Test various filters
        filter_tests = [
            ("/api/readings/?gauge=" + str(self.gauges[0].pk), 50),
            ("/api/readings/?water_level__gte=5.0", None),
            ("/api/gauges/?country_code=PK", 10),
            ("/api/predictions/?gauge=" + str(self.gauges[0].pk), 10),
        ]

        for url, expected_count in filter_tests:
            start_time = time.time()
            response = client.get(url)
            response_time = time.time() - start_time

            self.assertEqual(response.status_code, 200)
            self.assertLess(response_time, 1.0)  # Less than 1 second

            if expected_count:
                self.assertEqual(response.data["count"], expected_count)


class TestExportPerformance(TestCase):
    """Test export functionality performance."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")

    def test_large_export_performance(self):
        """Test performance of exporting large datasets."""
        # Create large dataset
        gauge = GaugeFactory()

        # Create readings in batches
        for batch in range(10):
            ReadingFactory.create_batch(
                1000, gauge=gauge, timestamp=timezone.now() - timedelta(days=batch)
            )

        # Test export performance
        start_time = time.time()
        response = self.client.get("/dashboard/export/readings/")
        export_time = time.time() - start_time

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

        # Should complete in reasonable time
        self.assertLess(export_time, 10.0)  # Less than 10 seconds

        # Verify content
        content = response.content.decode("utf-8")
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 10001)  # Header + 10000 readings

    def test_export_memory_usage(self):
        """Test memory usage during large exports."""
        # Create dataset
        gauge = GaugeFactory()
        ReadingFactory.create_batch(5000, gauge=gauge)

        # Monitor memory
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Perform export
        response = self.client.get("/dashboard/export/readings/")

        # Check memory usage
        peak_memory = process.memory_info().rss
        memory_increase = peak_memory - initial_memory

        self.assertEqual(response.status_code, 200)

        # Memory increase should be reasonable (streaming)
        self.assertLess(memory_increase, 100 * 1024 * 1024)  # Less than 100MB

    def test_concurrent_exports(self):
        """Test handling of concurrent export requests."""
        import threading

        # Create dataset
        gauge = GaugeFactory()
        ReadingFactory.create_batch(1000, gauge=gauge)

        results = []

        def export_data():
            client = self.client_class()
            client.login(username="testuser", password="testpass123")

            start = time.time()
            response = client.get("/dashboard/export/readings/")
            duration = time.time() - start

            results.append(
                {
                    "status": response.status_code,
                    "duration": duration,
                    "size": len(response.content),
                }
            )

        # Run concurrent exports
        threads = []
        for i in range(5):
            thread = threading.Thread(target=export_data)
            threads.append(thread)

        start_time = time.time()

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        total_time = time.time() - start_time

        # All exports should succeed
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertEqual(result["status"], 200)
            self.assertGreater(result["size"], 0)

        # Should handle concurrent exports efficiently
        self.assertLess(total_time, 10.0)  # Less than 10 seconds


class TestSystemLoadPerformance(TransactionTestCase):
    """Test overall system performance under load."""

    @patch("requests.get")
    def test_system_under_continuous_load(self, mock_get):
        """Test system performance under continuous load."""
        # Create gauges first
        gauges = []
        for i in range(10):
            gauge = GaugeFactory(gauge_id=f"PK{i:03d}", country_code="PK", name=f"Gauge {i}")
            gauges.append(gauge)

        # Mock API responses for each gauge
        def get_mock_responses():
            responses = []
            for gauge in gauges:
                responses.extend([
                    Mock(
                        status_code=200,
                        json=Mock(
                            return_value={
                                "gaugeId": gauge.gauge_id,
                                "name": gauge.name,
                                "location": {
                                    "latitude": gauge.latitude,
                                    "longitude": gauge.longitude
                                },
                                "qualityVerified": True,
                                "hasModel": True,
                            }
                        ),
                    ),
                    Mock(status_code=200, json=Mock(return_value={"thresholds": {"warningLevel": 10.0}})),
                ])
            return responses

        # Simulate continuous data collection
        start_time = time.time()

        for cycle in range(5):
            mock_get.side_effect = get_mock_responses()
            call_command("fetch_google_flood_data")
            # Small delay between cycles
            time.sleep(0.5)

        total_time = time.time() - start_time

        # Should handle continuous load
        self.assertLess(total_time, 20.0)  # Less than 20 seconds for 5 cycles

        # Verify data integrity
        self.assertEqual(Gauge.objects.count(), 10)
        self.assertGreaterEqual(Reading.objects.count(), 10)  # At least one per gauge

    def test_memory_leak_detection(self):
        """Test for memory leaks during extended operation."""
        import gc

        # Force garbage collection
        gc.collect()

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Perform many operations
        for i in range(100):
            gauge = GaugeFactory(gauge_id=f"PK{i:03d}")
            ReadingFactory.create_batch(10, gauge=gauge)

            # Periodic cleanup
            if i % 10 == 0:
                gc.collect()

        # Final cleanup
        gc.collect()

        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory

        # Memory growth should be reasonable
        self.assertLess(memory_growth, 200 * 1024 * 1024)  # Less than 200MB growth

    def test_database_connection_stress(self):
        """Test database connections under stress."""
        import threading

        errors = []

        def stress_database():
            try:
                # Perform various database operations
                gauge = GaugeFactory()
                ReadingFactory.create_batch(10, gauge=gauge)

                # Query operations
                Reading.objects.filter(gauge=gauge).count()
                list(Reading.objects.filter(gauge=gauge)[:5])

                # Update operation
                gauge.status = "inactive"
                gauge.save()

            except Exception as e:
                errors.append(str(e))

        # Run many concurrent operations
        threads = []
        for i in range(50):
            thread = threading.Thread(target=stress_database)
            threads.append(thread)

        start_time = time.time()

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        total_time = time.time() - start_time

        # Should handle stress without errors
        self.assertEqual(len(errors), 0)
        self.assertLess(total_time, 30.0)  # Complete in less than 30 seconds

        # Verify data consistency
        gauge_count = Gauge.objects.count()
        self.assertEqual(gauge_count, 50)  # One per thread


class TestCachingPerformance(TestCase):
    """Test caching impact on performance."""

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            }
        }
    )
    def test_cache_effectiveness(self):
        """Test cache effectiveness for repeated queries."""
        from django.core.cache import cache

        # Create test data
        gauges = GaugeFactory.create_batch(20)

        # First query (cache miss)
        start_time = time.time()
        gauge_list = list(Gauge.objects.all())
        first_query_time = time.time() - start_time

        # Cache the result
        cache.set("all_gauges", gauge_list, 60)

        # Second query (cache hit)
        start_time = time.time()
        cached_gauges = cache.get("all_gauges")
        cache_query_time = time.time() - start_time

        # Cache should be faster
        self.assertLess(cache_query_time, first_query_time)
        self.assertEqual(len(cached_gauges), 20)

    def test_cache_invalidation_performance(self):
        """Test performance of cache invalidation."""
        from django.core.cache import cache

        # Populate cache
        for i in range(100):
            cache.set(f"key_{i}", f"value_{i}", 300)

        # Test invalidation performance
        start_time = time.time()

        # Clear specific keys
        for i in range(50):
            cache.delete(f"key_{i}")

        invalidation_time = time.time() - start_time

        # Should be fast
        self.assertLess(invalidation_time, 1.0)  # Less than 1 second

        # Verify invalidation
        self.assertIsNone(cache.get("key_0"))
        self.assertIsNotNone(cache.get("key_50"))


class TestScalabilityLimits(TestCase):
    """Test system scalability limits."""

    def test_maximum_concurrent_users(self):
        """Test maximum concurrent users the system can handle."""
        import threading

        # Create users
        users = []
        for i in range(50):
            user = User.objects.create_user(username=f"user{i}", password="testpass123")
            users.append(user)

        # Create test data
        gauge = GaugeFactory()
        ReadingFactory.create_batch(100, gauge=gauge)

        results = []

        def simulate_user(username):
            try:
                client = self.client_class()
                login_success = client.login(username=username, password="testpass123")

                if login_success:
                    # Simulate user actions
                    response = client.get("/dashboard/")
                    results.append({"user": username, "status": response.status_code})
            except Exception as e:
                results.append({"user": username, "error": str(e)})

        # Simulate concurrent users
        threads = []
        start_time = time.time()

        for user in users:
            thread = threading.Thread(target=simulate_user, args=(user.username,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        total_time = time.time() - start_time

        # Check results
        successful_users = [r for r in results if "status" in r and r["status"] == 200]

        # System should handle at least 40 concurrent users
        self.assertGreaterEqual(len(successful_users), 40)
        self.assertLess(total_time, 30.0)  # Complete in 30 seconds

    def test_data_volume_limits(self):
        """Test system limits with large data volumes."""
        # Test gauge limit
        start_time = time.time()

        # Create many gauges
        gauges = []
        for i in range(100):
            gauge = Gauge.objects.create(
                gauge_id=f"PK{i:04d}",
                name=f"Gauge {i}",
                latitude=31.5 + (i % 10) * 0.1,
                longitude=74.3 + (i % 10) * 0.1,
                country_code="PK",
                status="active",
            )
            gauges.append(gauge)

        gauge_creation_time = time.time() - start_time

        # Should handle 100 gauges easily
        self.assertLess(gauge_creation_time, 5.0)
        self.assertEqual(Gauge.objects.count(), 100)

        # Test reading volume
        start_time = time.time()

        # Create many readings for one gauge
        readings = []
        base_time = timezone.now()

        for i in range(1000):
            readings.append(
                Reading(
                    gauge=gauges[0],
                    timestamp=base_time - timedelta(hours=i),
                    water_level=5.0 + (i % 100) * 0.01,
                    flow_rate=100.0 + (i % 50),
                )
            )

        Reading.objects.bulk_create(readings, batch_size=500)

        reading_creation_time = time.time() - start_time

        # Should handle 1000 readings per gauge
        self.assertLess(reading_creation_time, 5.0)
        self.assertEqual(Reading.objects.filter(gauge=gauges[0]).count(), 1000)
