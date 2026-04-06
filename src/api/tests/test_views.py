from rest_framework.test import APIClient
from rest_framework import status
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import Gauge, Reading, Prediction


class GaugeViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated_access_to_gauges_list(self):
        """
        Test that unauthenticated users receive a 401 Unauthorized error.
        This test is expected to fail with a 404 initially.
        """
        response = self.client.get("/api/v1/gauges/")
        # DRF may return 403 instead of 401 when using SessionAuthentication
        # Both indicate the request was rejected for authentication reasons
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_authenticated_access_to_gauges_list(self):
        """
        Test that an authenticated user can successfully retrieve a list of gauges.
        """
        # Create a user
        User = get_user_model()
        user = User.objects.create_user(username="testuser", password="password123")

        # Create a gauge to be listed
        Gauge.objects.create(
            gauge_id="auth_test_001",
            name="Authenticated Test Gauge",
            latitude=26.0,
            longitude=66.0,
            country_code="PK",
        )

        # Authenticate the client
        self.client.force_authenticate(user=user)

        # Make the request
        response = self.client.get("/api/v1/gauges/")

        # Assert success
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["gauge_id"], "auth_test_001")


class ReadingViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("test", "pass")
        self.gauge = Gauge.objects.create(
            gauge_id="reading_view_test",
            name="Test",
            latitude=1,
            longitude=1,
            country_code="PK",
        )
        Reading.objects.create(
            gauge=self.gauge, timestamp=timezone.now(), water_level=1
        )

    def test_authenticated_access_readings(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/v1/readings/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class PredictionViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("test", "pass")
        self.gauge = Gauge.objects.create(
            gauge_id="prediction_view_test",
            name="Test",
            latitude=1,
            longitude=1,
            country_code="PK",
        )
        Prediction.objects.create(
            gauge=self.gauge, prediction_for_timestamp=timezone.now(), water_level=2
        )

    def test_authenticated_access_predictions(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/v1/predictions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
