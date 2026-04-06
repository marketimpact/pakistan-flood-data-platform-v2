from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import Gauge, Reading


class DashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_dashboard_accessible_for_unauthenticated_user(self):
        """
        Test that accessing the dashboard view is publicly accessible
        without authentication.
        """
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pakistan Flood Data Dashboard")


class ExportReadingsCSVViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="testuser", password="password123"
        )
        self.gauge = Gauge.objects.create(
            gauge_id="export_test",
            name="Export Test",
            latitude=1,
            longitude=1,
            country_code="PK",
        )
        Reading.objects.create(
            gauge=self.gauge, timestamp=timezone.now(), water_level=5.0
        )

    def test_export_accessible_for_unauthenticated_user(self):
        """
        Test that the export view is publicly accessible without authentication.
        """
        response = self.client.get(reverse("export_readings_csv"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_export_returns_csv_for_authenticated_user(self):
        """
        Test that the export view returns a CSV file for authenticated users.
        """
        self.client.login(username="testuser", password="password123")
        response = self.client.get(reverse("export_readings_csv"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn(
            'attachment; filename="readings_export.csv"',
            response["Content-Disposition"],
        )
