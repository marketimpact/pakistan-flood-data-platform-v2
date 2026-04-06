"""Integration tests for complete data flow scenarios."""

import unittest
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from django.db import transaction
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime, timedelta
import json
import uuid

from core.models import Gauge, Reading, Prediction
from core.services import GoogleFloodHubService
from core.tests.factories import GaugeFactory, ReadingFactory, PredictionFactory
from core.tests.fixtures.api_responses import (
    SAMPLE_GAUGE_RESPONSE,
    SAMPLE_THRESHOLD_RESPONSE,
)

User = get_user_model()


class TestDataCollectionIntegration(TransactionTestCase):
    """Test complete data collection workflow from API to database."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@example.com"
        )

    @patch("requests.get")
    def test_complete_data_collection_flow(self, mock_get):
        """Test complete flow from API fetch to database storage."""
        # Create an existing gauge to update
        gauge = GaugeFactory(gauge_id="PK001", country_code="PK", name="Old Gauge Name")
        
        # Mock API responses for individual gauge requests
        mock_responses = [
            # First call: gauge metadata
            Mock(
                status_code=200,
                json=Mock(
                    return_value={
                        "gaugeId": "PK001",
                        "name": "Test Gauge 1",
                        "location": {
                            "latitude": 31.5204,
                            "longitude": 74.3587
                        },
                        "qualityVerified": True,
                        "hasModel": True,
                    }
                ),
            ),
            # Second call: threshold data
            Mock(
                status_code=200,
                json=Mock(
                    return_value={
                        "thresholds": {
                            "warningLevel": 4.0,
                            "dangerLevel": 6.0,
                            "highestRecorded": 8.0,
                        }
                    }
                ),
            ),
        ]
        mock_get.side_effect = mock_responses

        # Run the fetch command
        call_command("fetch_google_flood_data")

        # Verify data was stored correctly
        self.assertEqual(Gauge.objects.count(), 1)
        gauge = Gauge.objects.first()
        self.assertEqual(gauge.gauge_id, "PK001")
        self.assertEqual(gauge.name, "Test Gauge 1")
        self.assertEqual(gauge.latitude, 31.5204)
        self.assertEqual(gauge.longitude, 74.3587)
        self.assertEqual(gauge.country_code, "PK")
        self.assertTrue(gauge.quality_verified)
        self.assertTrue(gauge.has_model)

        # Verify reading was created with a safe water level
        self.assertEqual(Reading.objects.count(), 1)
        reading = Reading.objects.first()
        self.assertEqual(reading.gauge, gauge)
        # Water level should be below warning level
        self.assertLess(float(reading.water_level), 4.0)

    @patch("requests.get")
    def test_incremental_data_updates(self, mock_get):
        """Test incremental updates without duplicating data."""
        # Create existing gauge and reading
        gauge = GaugeFactory(gauge_id="PK001", country_code="PK", name="Old Name")
        existing_reading = ReadingFactory(
            gauge=gauge, timestamp=timezone.now() - timedelta(hours=2), water_level=4.5
        )

        # Mock API response with updated data
        mock_responses = [
            # Gauge metadata
            Mock(
                status_code=200,
                json=Mock(
                    return_value={
                        "gaugeId": "PK001",
                        "name": "Updated Gauge Name",
                        "location": {
                            "latitude": gauge.latitude,
                            "longitude": gauge.longitude
                        },
                        "qualityVerified": True,
                        "hasModel": True,
                    }
                ),
            ),
            # Threshold data
            Mock(
                status_code=200,
                json=Mock(return_value={"thresholds": {"warningLevel": 5.0}}),
            ),
        ]
        mock_get.side_effect = mock_responses

        # Run the fetch command
        call_command("fetch_google_flood_data")

        # Verify gauge wasn't duplicated but was updated
        self.assertEqual(Gauge.objects.count(), 1)
        gauge.refresh_from_db()
        self.assertEqual(gauge.name, "Updated Gauge Name")

        # Verify new reading was added
        self.assertEqual(Reading.objects.count(), 2)
        new_reading = Reading.objects.exclude(pk=existing_reading.pk).first()
        # Should be a safe level below warning
        self.assertLess(float(new_reading.water_level), 5.0)

    @patch("core.services.data_collection.requests.get")
    def test_data_collection_with_api_errors(self, mock_get):
        """Test data collection handles API errors gracefully."""
        # Mock API error
        mock_get.side_effect = Exception("API connection error")

        # Run the fetch command - should not crash
        try:
            call_command("fetch_google_flood_data")
        except Exception:
            self.fail("Command should handle API errors gracefully")

        # Verify no partial data was stored
        self.assertEqual(Gauge.objects.count(), 0)
        self.assertEqual(Reading.objects.count(), 0)
        self.assertEqual(Prediction.objects.count(), 0)

    @patch("requests.get")
    def test_concurrent_data_collection(self, mock_get):
        """Test concurrent data collection doesn't create duplicates."""
        import threading

        # Create initial gauge
        gauge = GaugeFactory(gauge_id="PK001", country_code="PK", name="Test Gauge")

        # Mock API responses for individual gauge
        gauge_response = Mock(
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
        )
        threshold_response = Mock(
            status_code=200, json=Mock(return_value={"thresholds": {"warningLevel": 5.0}})
        )

        def setup_mock():
            mock_get.side_effect = [gauge_response, threshold_response]

        # Run multiple concurrent fetches
        threads = []
        for i in range(3):
            setup_mock()
            thread = threading.Thread(
                target=call_command, args=("fetch_google_flood_data",)
            )
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify no duplicates were created
        self.assertEqual(Gauge.objects.count(), 1)
        # Readings might vary based on timing
        self.assertGreaterEqual(Reading.objects.count(), 1)
        self.assertLessEqual(Reading.objects.count(), 3)


class TestDashboardIntegration(TestCase):
    """Test dashboard integration with data models."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", email="test@example.com"
        )
        self.client.login(username="testuser", password="testpass123")

        # Create test data
        self.gauge1 = GaugeFactory(gauge_id="PK001", name="Gauge 1")
        self.gauge2 = GaugeFactory(gauge_id="PK002", name="Gauge 2")

        # Create readings
        for i in range(5):
            ReadingFactory(
                gauge=self.gauge1,
                timestamp=timezone.now() - timedelta(hours=i),
                water_level=5.0 + i * 0.5,
            )
            ReadingFactory(
                gauge=self.gauge2,
                timestamp=timezone.now() - timedelta(hours=i),
                water_level=3.0 + i * 0.3,
            )

        # Create predictions
        for i in range(3):
            PredictionFactory(
                gauge=self.gauge1,
                prediction_for_timestamp=timezone.now() + timedelta(hours=i),
                water_level=6.0 + i * 0.2,
            )

    def test_dashboard_displays_all_data(self):
        """Test dashboard shows all relevant data."""
        response = self.client.get("/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gauge 1")
        self.assertContains(response, "Gauge 2")
        self.assertContains(response, "2")  # Total gauges
        self.assertContains(response, "10")  # Total readings
        self.assertContains(response, "3")  # Total predictions

    def test_dashboard_data_collection_trigger(self):
        """Test dashboard can trigger data collection."""
        with patch(
            "core.management.commands.fetch_google_flood_data.Command.handle"
        ) as mock_handle:
            response = self.client.post("/dashboard/collect-data/")

            self.assertEqual(response.status_code, 302)
            mock_handle.assert_called_once()

    def test_dashboard_export_integration(self):
        """Test dashboard export with actual data."""
        response = self.client.get("/dashboard/export/readings/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

        # Check CSV content
        content = response.content.decode("utf-8")
        lines = content.strip().split("\n")

        # Header + 10 readings
        self.assertEqual(len(lines), 11)

        # Verify header
        self.assertIn("gauge_id", lines[0])
        self.assertIn("water_level", lines[0])

        # Verify data
        self.assertIn("PK001", content)
        self.assertIn("PK002", content)

    def test_dashboard_update_readings_integration(self):
        """Test dashboard update readings integration."""
        with patch(
            "core.management.commands.update_daily_readings.Command.handle"
        ) as mock_handle:
            response = self.client.post("/dashboard/update-readings/")

            self.assertEqual(response.status_code, 302)
            mock_handle.assert_called_once()

    @unittest.skip("Clear data functionality has been removed")
    def test_dashboard_clear_data_integration(self):
        """Test dashboard clear data integration."""
        # Initial data exists
        self.assertEqual(Reading.objects.count(), 10)
        self.assertEqual(Prediction.objects.count(), 3)

        # Clear data
        response = self.client.post("/dashboard/clear-data/")

        self.assertEqual(response.status_code, 302)

        # Verify data was cleared
        self.assertEqual(Reading.objects.count(), 0)
        self.assertEqual(Prediction.objects.count(), 0)
        # Gauges should remain
        self.assertEqual(Gauge.objects.count(), 2)


class TestAPIIntegration(TestCase):
    """Test API integration with authentication and data access."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="apiuser", password="apipass123", email="api@example.com"
        )

        # Create test data
        self.gauge = GaugeFactory(gauge_id="PK001")
        self.readings = [
            ReadingFactory(
                gauge=self.gauge,
                timestamp=timezone.now() - timedelta(hours=i),
                water_level=5.0 + i * 0.1,
            )
            for i in range(10)
        ]
        self.predictions = [
            PredictionFactory(
                gauge=self.gauge,
                prediction_for_timestamp=timezone.now() + timedelta(hours=i),
                water_level=5.5 + i * 0.1,
            )
            for i in range(5)
        ]

    def test_api_authentication_flow(self):
        """Test complete API authentication flow."""
        from rest_framework.test import APIClient

        client = APIClient()

        # Unauthenticated request should fail
        response = client.get("/api/gauges/")
        self.assertEqual(response.status_code, 403)  # SessionAuth returns 403

        # Authenticate
        client.force_authenticate(user=self.user)

        # Authenticated request should succeed
        response = client.get("/api/gauges/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_api_data_retrieval_flow(self):
        """Test complete data retrieval through API."""
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=self.user)

        # Get gauges
        response = client.get("/api/gauges/")
        self.assertEqual(response.status_code, 200)
        gauge_data = response.data["results"][0]
        gauge_id = gauge_data["id"]

        # Get gauge detail
        response = client.get(f"/api/gauges/{gauge_id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["gauge_id"], "PK001")

        # Get readings
        response = client.get("/api/readings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 10)

        # Get predictions
        response = client.get("/api/predictions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 5)

    def test_api_filtering_integration(self):
        """Test API filtering integration."""
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=self.user)

        # Create another gauge with readings
        gauge2 = GaugeFactory(gauge_id="PK002")
        ReadingFactory(gauge=gauge2, water_level=10.0)

        # Filter readings by gauge
        response = client.get(f"/api/readings/?gauge={self.gauge.pk}")
        self.assertEqual(response.status_code, 200)

        # All readings should be from gauge1
        for reading in response.data["results"]:
            self.assertEqual(reading["gauge"], str(self.gauge.pk))

    def test_api_pagination_integration(self):
        """Test API pagination integration."""
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=self.user)

        # Create many readings
        ReadingFactory.create_batch(50, gauge=self.gauge)

        # Get first page
        response = client.get("/api/readings/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["next"])

        # Get next page
        page2_url = response.data["next"]
        response = client.get(page2_url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["previous"])


class TestCommandIntegration(TestCase):
    """Test management command integration scenarios."""

    def setUp(self):
        """Set up test data."""
        self.gauge = GaugeFactory(gauge_id="PK001")

    @patch("requests.get")
    def test_fetch_and_update_command_integration(self, mock_get):
        """Test fetch and update commands work together."""
        # Create gauge first (command expects existing gauges)
        gauge = GaugeFactory(gauge_id="PK001", country_code="PK")
        
        # Mock API responses for individual gauge request
        mock_get.side_effect = [
            # Gauge metadata
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
            # Threshold data
            Mock(status_code=200, json=Mock(return_value={"thresholds": {"warningLevel": 10.0}})),
        ]

        # Run fetch command
        call_command("fetch_google_flood_data")
        
        # Should create a reading with safe water level
        self.assertEqual(Reading.objects.count(), 1)
        reading = Reading.objects.first()
        self.assertLess(float(reading.water_level), 10.0)

    def test_command_error_recovery(self):
        """Test commands can recover from errors."""
        # Create a reading
        ReadingFactory(gauge=self.gauge)

        with patch("requests.get") as mock_get:
            # First call fails
            mock_get.side_effect = [
                Exception("Network error"),
                Exception("Network error"),
            ]

            # Run command - should handle error
            call_command("fetch_google_flood_data")

            # Data should be unchanged
            self.assertEqual(Reading.objects.count(), 1)

            # Second attempt succeeds
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

            # Run command again
            call_command("fetch_google_flood_data")

            # New data should be added
            self.assertEqual(Reading.objects.count(), 2)


class TestEndToEndWorkflow(TransactionTestCase):
    """Test complete end-to-end workflows."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
            is_staff=True,
        )

    @patch("requests.get")
    def test_complete_user_workflow(self, mock_get):
        """Test complete workflow from login to data export."""
        # 1. User logs in
        login_success = self.client.login(username="testuser", password="testpass123")
        self.assertTrue(login_success)

        # 2. User views dashboard (no data yet)
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<div class="number">0</div>')

        # 3. Create a gauge first (command expects existing gauges)
        gauge = GaugeFactory(gauge_id="PK001", country_code="PK", name="Test Gauge")
        
        # Mock API responses for fetch command
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

        response = self.client.post("/dashboard/collect-data/")
        self.assertEqual(response.status_code, 302)

        # 4. User views dashboard with data
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<div class="number">1</div>')  # 1 gauge
        self.assertContains(response, "Total Readings")
        
        # 5. User exports data
        response = self.client.get("/dashboard/export/readings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

        content = response.content.decode("utf-8")
        self.assertIn("PK001", content)

        # 6. User logs out
        response = self.client.post("/logout/")
        self.assertEqual(response.status_code, 302)

    @patch("requests.get")
    def test_automated_daily_update_workflow(self, mock_get):
        """Test automated daily update workflow."""
        # Initial data setup
        gauge = GaugeFactory(gauge_id="PK001", country_code="PK")
        old_reading = ReadingFactory(
            gauge=gauge, timestamp=timezone.now() - timedelta(days=2), water_level=4.0
        )

        # Mock API response with new data
        mock_get.side_effect = [
            # Gauge metadata
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
            # Threshold data
            Mock(status_code=200, json=Mock(return_value={"thresholds": {"warningLevel": 10.0}})),
        ]

        # Simulate cron job running fetch command
        call_command("fetch_google_flood_data")

        # Verify new data was added
        self.assertEqual(Reading.objects.count(), 2)
        new_reading = Reading.objects.exclude(pk=old_reading.pk).first()
        # Should be safe level below warning
        self.assertLess(float(new_reading.water_level), 10.0)

        # Verify gauge status was updated
        gauge.refresh_from_db()
        self.assertEqual(gauge.status, "active")

    def test_data_consistency_across_components(self):
        """Test data consistency across all components."""
        # Create data through factories
        gauge = GaugeFactory(gauge_id="PK001")
        readings = ReadingFactory.create_batch(5, gauge=gauge)
        predictions = PredictionFactory.create_batch(3, gauge=gauge)

        # Login
        self.client.login(username="testuser", password="testpass123")

        # Check dashboard shows correct counts
        response = self.client.get("/dashboard/")
        # Dashboard uses div.number for counts
        self.assertContains(response, '<div class="number">1</div>')  # 1 gauge
        self.assertContains(response, '<div class="number">5</div>')  # 5 readings
        self.assertContains(response, '<div class="number">3</div>')  # 3 predictions

        # Check API returns same data
        from rest_framework.test import APIClient

        api_client = APIClient()
        api_client.force_authenticate(user=self.user)

        response = api_client.get("/api/gauges/")
        self.assertEqual(response.data["count"], 1)

        response = api_client.get("/api/readings/")
        self.assertEqual(response.data["count"], 5)

        response = api_client.get("/api/predictions/")
        self.assertEqual(response.data["count"], 3)

        # Check export contains all readings
        response = self.client.get("/dashboard/export/readings/")
        content = response.content.decode("utf-8")
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 6)  # Header + 5 readings


class TestPerformanceIntegration(TestCase):
    """Test performance under various load conditions."""

    def test_large_dataset_handling(self):
        """Test system handles large datasets efficiently."""
        import time

        # Create large dataset
        gauge = GaugeFactory()

        start_time = time.time()

        # Create 1000 readings in batches
        for i in range(10):
            ReadingFactory.create_batch(
                100, gauge=gauge, timestamp=timezone.now() - timedelta(hours=i)
            )

        creation_time = time.time() - start_time
        self.assertLess(creation_time, 10.0)  # Should complete in < 10 seconds

        # Test dashboard performance
        user = User.objects.create_user(username="perfuser", password="pass123")
        self.client.login(username="perfuser", password="pass123")

        start_time = time.time()
        response = self.client.get("/dashboard/")
        dashboard_time = time.time() - start_time

        self.assertEqual(response.status_code, 200)
        self.assertLess(dashboard_time, 2.0)  # Should load in < 2 seconds

        # Test export performance
        start_time = time.time()
        response = self.client.get("/dashboard/export/readings/")
        export_time = time.time() - start_time

        self.assertEqual(response.status_code, 200)
        self.assertLess(export_time, 5.0)  # Should export in < 5 seconds

    def test_concurrent_user_access(self):
        """Test system handles concurrent users."""
        import threading

        # Create test data
        gauge = GaugeFactory()
        ReadingFactory.create_batch(50, gauge=gauge)

        # Create multiple users
        users = []
        for i in range(5):
            user = User.objects.create_user(username=f"user{i}", password="pass123")
            users.append(user)

        results = []

        def access_dashboard(username):
            client = self.client_class()
            client.login(username=username, password="pass123")
            response = client.get("/dashboard/")
            results.append(response.status_code)

        # Simulate concurrent access
        threads = []
        for user in users:
            thread = threading.Thread(target=access_dashboard, args=(user.username,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # All requests should succeed
        self.assertEqual(len(results), 5)
        for status_code in results:
            self.assertEqual(status_code, 200)
