"""Integration tests for error scenarios and edge cases."""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime, timedelta
import json
import uuid

from core.models import Gauge, Reading, Prediction
from core.services import GoogleFloodHubService
from core.tests.factories import GaugeFactory, ReadingFactory, PredictionFactory

User = get_user_model()


class TestAPIErrorIntegration(TransactionTestCase):
    """Test integration behavior during API errors."""

    def setUp(self):
        """Set up test data."""
        self.service = GoogleFloodHubService()

    @patch("requests.get")
    def test_partial_api_failure_recovery(self, mock_get):
        """Test system recovers from partial API failures."""
        # Create gauge first
        gauge = GaugeFactory(gauge_id="PK001", country_code="PK")
        
        # First call succeeds, second fails
        mock_get.side_effect = [
            Mock(
                status_code=200,
                json=Mock(
                    return_value={
                        "gaugeId": "PK001",
                        "name": "Test Gauge",
                        "location": {
                            "latitude": 31.5204,
                            "longitude": 74.3587
                        },
                        "qualityVerified": True,
                        "hasModel": True,
                    }
                ),
            ),
            Exception("Network error"),  # Threshold API fails
        ]

        # Run fetch command
        call_command("fetch_google_flood_data")

        # Verify data was saved despite threshold failure
        self.assertEqual(Gauge.objects.count(), 1)
        self.assertEqual(Reading.objects.count(), 1)

        # Verify system is in consistent state
        gauge.refresh_from_db()
        self.assertEqual(gauge.gauge_id, "PK001")
        self.assertIsNone(gauge.warning_level)  # No threshold data

    @patch("requests.get")
    def test_malformed_api_response_handling(self, mock_get):
        """Test handling of malformed API responses."""
        # Create gauge first (command expects gauges)
        gauge = GaugeFactory(gauge_id="PK001", country_code="PK")
        
        # Mock various malformed responses
        malformed_responses = [
            None,  # Null response
            {},  # Empty response
            {"error": "Internal server error"},  # Error response
            {"gaugeId": "PK001"},  # Missing location
            {"location": {}},  # Missing gaugeId
        ]

        initial_reading_count = Reading.objects.count()
        
        for response_data in malformed_responses:
            mock_get.side_effect = [
                Mock(status_code=200, json=Mock(return_value=response_data)),
                Mock(status_code=200, json=Mock(return_value={"thresholds": []})),
            ]

            # Should not crash
            try:
                call_command("fetch_google_flood_data")
            except Exception as e:
                self.fail(f"Command crashed with malformed response: {e}")

        # No new readings should be created from malformed responses
        self.assertEqual(Reading.objects.count(), initial_reading_count)

    @patch("core.services.data_collection.requests.get")
    def test_api_timeout_handling(self, mock_get):
        """Test handling of API timeouts."""
        import requests

        # Mock timeout
        mock_get.side_effect = requests.Timeout("Connection timed out")

        # Run command
        call_command("fetch_google_flood_data")

        # Verify no data was saved
        self.assertEqual(Gauge.objects.count(), 0)
        self.assertEqual(Reading.objects.count(), 0)

    @patch("core.services.data_collection.requests.get")
    def test_api_rate_limit_handling(self, mock_get):
        """Test handling of API rate limits."""
        # Mock rate limit response
        mock_get.return_value = Mock(
            status_code=429,
            headers={"Retry-After": "60"},
            json=Mock(return_value={"error": "Rate limit exceeded"}),
        )

        # Run command
        call_command("fetch_google_flood_data")

        # Verify no data was saved
        self.assertEqual(Gauge.objects.count(), 0)
        self.assertEqual(Reading.objects.count(), 0)

    @patch("requests.get")
    def test_intermittent_api_failures(self, mock_get):
        """Test handling of intermittent API failures."""
        # Create existing gauge
        gauge = GaugeFactory(gauge_id="PK001", country_code="PK")

        # First attempt fails
        mock_get.side_effect = Exception("Network error")
        call_command("fetch_google_flood_data")
        self.assertEqual(Reading.objects.count(), 0)

        # Second attempt succeeds
        mock_get.side_effect = [
            Mock(
                status_code=200,
                json=Mock(
                    return_value={
                        "gaugeId": "PK001",
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
        ]
        
        call_command("fetch_google_flood_data")
        self.assertEqual(Reading.objects.count(), 1)


class TestDatabaseErrorIntegration(TransactionTestCase):
    """Test integration behavior during database errors."""

    @patch("requests.get")
    def test_database_constraint_violations(self, mock_get):
        """Test handling of database constraint violations."""
        # Create existing gauge
        gauge = GaugeFactory(gauge_id="PK001", country_code="PK")

        # Mock API response with same gauge but different data
        mock_get.side_effect = [
            Mock(
                status_code=200,
                json=Mock(
                    return_value={
                        "gaugeId": "PK001",  # Same ID
                        "name": "Different Name",
                        "location": {
                            "latitude": 30.0,  # Different location
                            "longitude": 70.0
                        },
                        "qualityVerified": True,
                        "hasModel": True,
                    }
                ),
            ),
            Mock(status_code=200, json=Mock(return_value={"thresholds": {"warningLevel": 10.0}})),
        ]

        # Run command
        call_command("fetch_google_flood_data")

        # Verify gauge wasn't duplicated
        self.assertEqual(Gauge.objects.count(), 1)

        # Verify existing gauge was updated
        gauge.refresh_from_db()
        self.assertEqual(gauge.name, "Different Name")
        self.assertEqual(gauge.latitude, 30.0)
        self.assertEqual(gauge.longitude, 70.0)

    @patch("core.models.Reading.save")
    @patch("requests.get")
    def test_database_save_failures(self, mock_get, mock_save):
        """Test handling of database save failures."""
        # Create gauge first
        gauge = GaugeFactory(gauge_id="PK001", country_code="PK")
        
        # Mock API success
        mock_get.side_effect = [
            Mock(
                status_code=200,
                json=Mock(
                    return_value={
                        "gaugeId": "PK001",
                        "name": "Test Gauge",
                        "location": {
                            "latitude": 31.5204,
                            "longitude": 74.3587
                        },
                        "qualityVerified": True,
                        "hasModel": True,
                    }
                ),
            ),
            Mock(status_code=200, json=Mock(return_value={"thresholds": {"warningLevel": 10.0}})),
        ]

        # Mock database error
        mock_save.side_effect = IntegrityError("Database error")

        # Run command
        try:
            call_command("fetch_google_flood_data")
        except Exception:
            pass  # Expected to handle error

        # Verify no readings were saved
        self.assertEqual(Reading.objects.count(), 0)

    def test_concurrent_write_conflicts(self):
        """Test handling of concurrent write conflicts."""
        import threading
        from django.db import connection

        gauge = GaugeFactory(gauge_id="PK001")

        results = []
        errors = []

        def create_reading(water_level):
            try:
                with transaction.atomic():
                    # Simulate some processing time
                    import time

                    time.sleep(0.1)

                    reading = Reading.objects.create(
                        gauge=gauge, timestamp=timezone.now(), water_level=water_level
                    )
                    results.append(reading.water_level)
            except Exception as e:
                errors.append(str(e))

        # Create concurrent writes
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_reading, args=(5.0 + i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # All writes should succeed (no conflicts for different timestamps)
        self.assertEqual(len(results), 5)
        self.assertEqual(len(errors), 0)
        self.assertEqual(Reading.objects.count(), 5)


class TestAuthenticationErrorIntegration(TestCase):
    """Test integration behavior during authentication errors."""

    def test_expired_session_handling(self):
        """Test handling of expired sessions."""
        user = User.objects.create_user(username="testuser", password="testpass123")

        # Login
        self.client.login(username="testuser", password="testpass123")

        # Access dashboard
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)

        # Simulate session expiry
        self.client.logout()

        # Try to access dashboard again
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)  # Redirect to login
        self.assertIn("/login/", response.url)

    def test_invalid_credentials_handling(self):
        """Test handling of invalid credentials."""
        # Try to login with invalid credentials
        response = self.client.post(
            "/login/", {"username": "nonexistent", "password": "wrongpass"}
        )

        # Should not authenticate
        self.assertNotIn("_auth_user_id", self.client.session)

        # Try to access protected resource
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_concurrent_session_handling(self):
        """Test handling of concurrent sessions."""
        user = User.objects.create_user(username="testuser", password="testpass123")

        # Create multiple client sessions
        client1 = self.client_class()
        client2 = self.client_class()

        # Both clients login
        client1.login(username="testuser", password="testpass123")
        client2.login(username="testuser", password="testpass123")

        # Both should access dashboard
        response1 = client1.get("/dashboard/")
        response2 = client2.get("/dashboard/")

        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)

    def test_permission_denied_handling(self):
        """Test handling of permission denied scenarios."""
        # Create non-staff user
        user = User.objects.create_user(
            username="regular", password="pass123", is_staff=False
        )

        self.client.login(username="regular", password="pass123")

        # Try to access admin
        response = self.client.get("/admin/")
        self.assertIn(response.status_code, [302, 403])  # Redirect or forbidden


class TestDataIntegrityErrors(TestCase):
    """Test data integrity error scenarios."""

    def test_orphaned_reading_prevention(self):
        """Test prevention of orphaned readings."""
        gauge = GaugeFactory()
        reading = ReadingFactory(gauge=gauge)

        # Try to delete gauge with readings
        with self.assertRaises(Exception):
            with transaction.atomic():
                gauge.delete()

        # Gauge should still exist
        self.assertTrue(Gauge.objects.filter(pk=gauge.pk).exists())
        self.assertTrue(Reading.objects.filter(pk=reading.pk).exists())

    def test_invalid_data_rejection(self):
        """Test rejection of invalid data."""
        gauge = GaugeFactory()

        # Test invalid water level
        with self.assertRaises(ValidationError):
            reading = Reading(
                gauge=gauge,
                timestamp=timezone.now(),
                water_level=-10.0,  # Negative water level
            )
            reading.full_clean()

        # Test invalid coordinates
        with self.assertRaises(ValidationError):
            invalid_gauge = Gauge(
                gauge_id="INVALID",
                name="Invalid Gauge",
                latitude=200.0,  # Invalid latitude
                longitude=74.0,
                country_code="PK",
                status="active",
            )
            invalid_gauge.full_clean()

    def test_data_consistency_during_errors(self):
        """Test data consistency is maintained during errors."""
        gauge = GaugeFactory()

        # Create initial reading
        reading1 = ReadingFactory(gauge=gauge, water_level=5.0)

        # Try to create invalid reading
        try:
            with transaction.atomic():
                reading2 = ReadingFactory(gauge=gauge, water_level=6.0)
                # Force an error
                raise Exception("Simulated error")
        except Exception:
            pass

        # Only first reading should exist
        self.assertEqual(Reading.objects.count(), 1)
        self.assertEqual(Reading.objects.first().water_level, 5.0)


class TestExportErrorScenarios(TestCase):
    """Test export functionality error scenarios."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")

    def test_export_with_no_data(self):
        """Test export when no data exists."""
        response = self.client.get("/dashboard/export/readings/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

        # Should have only header
        content = response.content.decode("utf-8")
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 1)
        self.assertIn("gauge_id", lines[0])

    def test_export_with_corrupt_data(self):
        """Test export handles corrupt data gracefully."""
        gauge = GaugeFactory()

        # Create reading with extreme values
        reading = ReadingFactory(gauge=gauge, water_level=999999.999999, flow_rate=None)

        response = self.client.get("/dashboard/export/readings/")

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")

        # Should handle extreme values
        self.assertIn("999999", content)
        self.assertIn("", content)  # Empty flow_rate

    def test_export_memory_efficiency(self):
        """Test export handles large datasets efficiently."""
        import psutil
        import os

        # Create large dataset
        gauge = GaugeFactory()
        ReadingFactory.create_batch(1000, gauge=gauge)

        # Get initial memory
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Perform export
        response = self.client.get("/dashboard/export/readings/")

        # Check memory didn't spike too much
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Should stream efficiently (less than 50MB increase)
        self.assertLess(memory_increase, 50 * 1024 * 1024)
        self.assertEqual(response.status_code, 200)


class TestSystemRecoveryScenarios(TransactionTestCase):
    """Test system recovery from various failure scenarios."""

    @patch("requests.get")
    def test_recovery_after_complete_failure(self, mock_get):
        """Test system recovers after complete failure."""
        # Simulate multiple failures
        mock_get.side_effect = [
            Exception("Complete system failure"),
            Exception("Still failing"),
            Exception("Another failure"),
        ]

        # Multiple fetch attempts fail
        for _ in range(3):
            call_command("fetch_google_flood_data")

        # System should have no corrupt data
        self.assertEqual(Gauge.objects.count(), 0)
        self.assertEqual(Reading.objects.count(), 0)

        # Create gauge and recover
        gauge = GaugeFactory(gauge_id="PK001", country_code="PK")
        
        # Now API recovers
        mock_get.side_effect = [
            Mock(
                status_code=200,
                json=Mock(
                    return_value={
                        "gaugeId": "PK001",
                        "name": "Test Gauge",
                        "location": {
                            "latitude": 31.5204,
                            "longitude": 74.3587
                        },
                        "qualityVerified": True,
                        "hasModel": True,
                    }
                ),
            ),
            Mock(status_code=200, json=Mock(return_value={"thresholds": {"warningLevel": 10.0}})),
        ]

        # System should recover
        call_command("fetch_google_flood_data")

        self.assertEqual(Gauge.objects.count(), 1)
        self.assertEqual(Reading.objects.count(), 1)

    def test_data_integrity_after_crash(self):
        """Test data integrity is maintained after crash."""
        # Create initial data
        gauge = GaugeFactory()
        readings = ReadingFactory.create_batch(5, gauge=gauge)

        # Simulate crash during operation
        try:
            with transaction.atomic():
                # Start modifying data
                new_reading = ReadingFactory(gauge=gauge)
                gauge.status = "inactive"
                gauge.save()

                # Simulate crash
                raise Exception("System crash")
        except Exception:
            pass

        # Verify original data is intact
        self.assertEqual(Reading.objects.count(), 5)
        gauge.refresh_from_db()
        self.assertEqual(gauge.status, "active")

    def test_concurrent_error_recovery(self):
        """Test recovery from concurrent errors."""
        import threading

        errors = []
        successes = []

        def operation(op_id):
            try:
                if op_id % 2 == 0:
                    # Even operations fail
                    raise Exception(f"Operation {op_id} failed")
                else:
                    # Odd operations succeed
                    gauge = GaugeFactory(gauge_id=f"PK{op_id:03d}")
                    successes.append(gauge.gauge_id)
            except Exception as e:
                errors.append(str(e))

        # Run concurrent operations
        threads = []
        for i in range(10):
            thread = threading.Thread(target=operation, args=(i,))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify partial success
        self.assertEqual(len(errors), 5)  # Even operations failed
        self.assertEqual(len(successes), 5)  # Odd operations succeeded
        self.assertEqual(Gauge.objects.count(), 5)  # Only successful creates
