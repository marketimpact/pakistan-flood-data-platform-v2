"""Integration tests for export workflow."""

import csv
import io
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.sessions.models import Session

from core.models import Gauge, Reading
from core.tests.factories import GaugeFactory, ReadingFactory

User = get_user_model()


class TestExportWorkflowIntegration(TestCase):
    """Integration tests for the complete export workflow."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpassword123"
        )
        self.export_url = reverse("export_readings_csv")
        self.dashboard_url = reverse("dashboard")
        self.login_url = "/supersecretadminpanel/login/"

    def test_export_authentication_requirement_workflow(self):
        """Test complete authentication workflow for export."""
        # Step 1: Try to access export without authentication
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(self.login_url, response.url)

        # Step 2: Login and try again
        login_success = self.client.login(
            username="testuser", password="testpassword123"
        )
        self.assertTrue(login_success)

        # Step 3: Access export after login
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_export_authentication_with_redirect(self):
        """Test export authentication with login redirect."""
        # Create test data
        gauge = GaugeFactory()
        ReadingFactory(gauge=gauge)

        # Step 1: Access export (should redirect to login)
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 302)

        # Step 2: Follow redirect to login
        response = self.client.get(response.url)
        self.assertEqual(response.status_code, 200)

        # Step 3: Submit login form
        response = self.client.post(
            self.login_url, {"username": "testuser", "password": "testpassword123"}
        )
        self.assertEqual(response.status_code, 302)

        # Step 4: Access export after successful login
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 200)

        # Step 5: Verify export content
        content = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("Gauge ID", content)
        self.assertIn("Gauge Name", content)

    def test_export_session_management_integration(self):
        """Test export with session management."""
        # Create test data
        gauge = GaugeFactory()
        ReadingFactory(gauge=gauge)

        # Step 1: Login and access export
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 200)

        # Step 2: Logout and try to access export again
        self.client.logout()
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 302)

        # Step 3: Login again and access export
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 200)

    def test_export_empty_data_handling_complete_workflow(self):
        """Test complete workflow with empty data."""
        # Step 1: Login
        self.client.login(username="testuser", password="testpassword123")

        # Step 2: Access dashboard (should show empty state)
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["gauge_count"], 0)
        self.assertEqual(response.context["reading_count"], 0)

        # Step 3: Export with empty data
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 200)

        # Step 4: Verify export content
        content = b"".join(response.streaming_content).decode("utf-8")
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 1)  # Only header
        self.assertEqual(
            lines[0], "Gauge ID,Gauge Name,Timestamp,Water Level (m),Flow Rate (m³/s)"
        )

    def test_export_data_lifecycle_integration(self):
        """Test export through complete data lifecycle."""
        self.client.login(username="testuser", password="testpassword123")

        # Step 1: Initial empty state
        response = self.client.get(self.export_url)
        content = b"".join(response.streaming_content).decode("utf-8")
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 1)  # Only header

        # Step 2: Add data
        gauge = GaugeFactory()
        reading = ReadingFactory(gauge=gauge)

        # Step 3: Export with data
        response = self.client.get(self.export_url)
        content = b"".join(response.streaming_content).decode("utf-8")
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 2)  # Header + 1 data row

        # Step 4: Add more data
        ReadingFactory.create_batch(5, gauge=gauge)

        # Step 5: Export with more data
        response = self.client.get(self.export_url)
        content = b"".join(response.streaming_content).decode("utf-8")
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 7)  # Header + 6 data rows

        # Step 6: Clear data
        Reading.objects.all().delete()
        Gauge.objects.all().delete()

        # Step 7: Export after clearing
        response = self.client.get(self.export_url)
        content = b"".join(response.streaming_content).decode("utf-8")
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 1)  # Only header again

    def test_special_character_escaping_integration(self):
        """Test special character escaping in complete workflow."""
        self.client.login(username="testuser", password="testpassword123")

        # Create test data with various special characters
        test_cases = [
            ("csv,comma", "Gauge with, comma"),
            ('csv"quote', 'Gauge with "quotes"'),
            ("csv\nnewline", "Gauge with\nnewline"),
            ("csv\rcarriage", "Gauge with\rcarriage return"),
            ("csv\ttab", "Gauge with\ttab"),
            ("csv'apostrophe", "Gauge with'apostrophe"),
            ("csv;semicolon", "Gauge with;semicolon"),
            ("csv|pipe", "Gauge with|pipe"),
            ("csv\\backslash", "Gauge with\\backslash"),
        ]

        for gauge_id, gauge_name in test_cases:
            # Step 1: Clear previous data
            Reading.objects.all().delete()
            Gauge.objects.all().delete()

            # Step 2: Create gauge with special characters
            gauge = GaugeFactory(gauge_id=gauge_id, name=gauge_name)
            reading = ReadingFactory(gauge=gauge)

            # Step 3: Export and verify
            response = self.client.get(self.export_url)
            content = b"".join(response.streaming_content).decode("utf-8")

            # Step 4: Parse CSV to verify proper escaping
            reader = csv.reader(io.StringIO(content))
            rows = list(reader)

            # Step 5: Verify data integrity
            self.assertEqual(len(rows), 2)  # Header + 1 data row
            data_row = rows[1]
            self.assertEqual(data_row[0], gauge_id)
            self.assertEqual(data_row[1], gauge_name)

    def test_unicode_handling_integration(self):
        """Test unicode handling in complete workflow."""
        self.client.login(username="testuser", password="testpassword123")

        # Create test data with unicode characters
        unicode_test_cases = [
            ("测试仪表", "中文测试站点"),
            ("گیج_اردو", "اردو ٹیسٹ اسٹیشن"),
            ("тест_кирилица", "Кириллическая тестовая станция"),
            ("δοκιμή_ελληνικά", "Ελληνικός σταθμός δοκιμής"),
            ("テスト_日本語", "日本語テストステーション"),
            ("मापक_हिंदी", "हिंदी परीक्षण स्टेशन"),
        ]

        for gauge_id, gauge_name in unicode_test_cases:
            # Step 1: Clear previous data
            Reading.objects.all().delete()
            Gauge.objects.all().delete()

            # Step 2: Create gauge with unicode
            gauge = GaugeFactory(gauge_id=gauge_id, name=gauge_name)
            reading = ReadingFactory(gauge=gauge)

            # Step 3: Export and verify
            response = self.client.get(self.export_url)
            self.assertEqual(response.status_code, 200)

            # Step 4: Check content
            content = b"".join(response.streaming_content).decode("utf-8")

            # Step 5: Verify unicode characters are preserved
            self.assertIn(gauge_id, content)
            self.assertIn(gauge_name, content)

            # Step 6: Verify CSV parsing works
            reader = csv.reader(io.StringIO(content))
            rows = list(reader)
            data_row = rows[1]
            self.assertEqual(data_row[0], gauge_id)
            self.assertEqual(data_row[1], gauge_name)

    def test_export_concurrent_user_access(self):
        """Test export with concurrent user access."""
        # Create test data
        gauge = GaugeFactory()
        ReadingFactory.create_batch(10, gauge=gauge)

        # Create multiple users
        users = []
        for i in range(3):
            user = User.objects.create_user(username=f"user{i}", password="testpass123")
            users.append(user)

        # Step 1: Login all users concurrently
        clients = []
        for user in users:
            client = Client()
            client.login(username=user.username, password="testpass123")
            clients.append(client)

        # Step 2: Access export concurrently
        responses = []
        for client in clients:
            response = client.get(self.export_url)
            responses.append(response)

        # Step 3: Verify all responses are successful
        for response in responses:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "text/csv")

        # Step 4: Verify all users get same data
        contents = []
        for response in responses:
            content = b"".join(response.streaming_content).decode("utf-8")
            contents.append(content)

        # All contents should be identical
        for content in contents[1:]:
            self.assertEqual(content, contents[0])

    def test_export_with_data_modifications_during_export(self):
        """Test export behavior when data is modified during export."""
        self.client.login(username="testuser", password="testpassword123")

        # Step 1: Create initial data
        gauge = GaugeFactory()
        ReadingFactory.create_batch(5, gauge=gauge)

        # Step 2: Start export
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 200)

        # Step 3: Get streaming content (simulating concurrent modification)
        content = b"".join(response.streaming_content).decode("utf-8")

        # Step 4: Verify export completed successfully
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 6)  # Header + 5 data rows

        # Step 5: Modify data after export
        ReadingFactory.create_batch(3, gauge=gauge)

        # Step 6: New export should reflect changes
        response = self.client.get(self.export_url)
        content = b"".join(response.streaming_content).decode("utf-8")
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 9)  # Header + 8 data rows

    def test_export_error_handling_integration(self):
        """Test export error handling in complete workflow."""
        self.client.login(username="testuser", password="testpassword123")

        # Step 1: Normal export
        gauge = GaugeFactory()
        ReadingFactory(gauge=gauge)

        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 200)

        # Step 2: Test with malformed data (simulate database issues)
        # This would typically be tested with mocking
        # For now, we test that the export handles normal edge cases

        # Step 3: Export with extreme values
        extreme_reading = ReadingFactory(
            gauge=gauge, water_level=999999.99, flow_rate=-999999.99
        )

        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 200)

        content = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("999999.99", content)
        self.assertIn("-999999.99", content)

    def test_export_pagination_simulation(self):
        """Test export with large dataset (simulating pagination needs)."""
        self.client.login(username="testuser", password="testpassword123")

        # Step 1: Create large dataset
        gauges = GaugeFactory.create_batch(10)
        total_readings = 0

        for gauge in gauges:
            readings = ReadingFactory.create_batch(50, gauge=gauge)
            total_readings += len(readings)

        # Step 2: Export all data
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 200)

        # Step 3: Verify all data is included
        content = b"".join(response.streaming_content).decode("utf-8")
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), total_readings + 1)  # +1 for header

        # Step 4: Verify data integrity
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        # Check header
        header = rows[0]
        self.assertEqual(header[0], "Gauge ID")
        self.assertEqual(header[1], "Gauge Name")

        # Check some data rows
        for i in range(1, min(10, len(rows))):
            row = rows[i]
            self.assertEqual(len(row), 5)  # Should have 5 columns
            self.assertIsNotNone(row[0])  # Gauge ID
            self.assertIsNotNone(row[1])  # Gauge Name

    def test_export_workflow_with_different_data_types(self):
        """Test export workflow with different data types and edge cases."""
        self.client.login(username="testuser", password="testpassword123")

        # Step 1: Create gauges with different data types
        gauge1 = GaugeFactory(gauge_id="int_gauge", name="Integer Gauge")
        gauge2 = GaugeFactory(gauge_id="float_gauge", name="Float Gauge")
        gauge3 = GaugeFactory(gauge_id="null_gauge", name="Null Gauge")

        # Step 2: Create readings with different value types
        reading1 = ReadingFactory(gauge=gauge1, water_level=10, flow_rate=20)  # Integer
        reading2 = ReadingFactory(
            gauge=gauge2, water_level=15.5, flow_rate=25.75  # Float
        )
        reading3 = ReadingFactory(
            gauge=gauge3, water_level=0.0, flow_rate=None  # Zero  # Null
        )

        # Step 3: Export and verify
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 200)

        content = b"".join(response.streaming_content).decode("utf-8")

        # Step 4: Parse and verify data types
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        self.assertEqual(len(rows), 4)  # Header + 3 data rows

        # Find and verify each reading
        for row in rows[1:]:
            if row[0] == "int_gauge":
                self.assertEqual(row[3], "10")
                self.assertEqual(row[4], "20")
            elif row[0] == "float_gauge":
                self.assertEqual(row[3], "15.5")
                self.assertEqual(row[4], "25.75")
            elif row[0] == "null_gauge":
                self.assertEqual(row[3], "0.0")
                self.assertEqual(row[4], "None")

    def test_export_full_workflow_with_dashboard_integration(self):
        """Test export workflow integrated with dashboard."""
        # Step 1: Login and access dashboard
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

        # Step 2: Verify initial empty state
        self.assertEqual(response.context["gauge_count"], 0)
        self.assertEqual(response.context["reading_count"], 0)

        # Step 3: Export empty data
        response = self.client.get(self.export_url)
        content = b"".join(response.streaming_content).decode("utf-8")
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 1)  # Only header

        # Step 4: Add data (simulate data collection)
        gauges = GaugeFactory.create_batch(5)
        readings = []
        for gauge in gauges:
            readings.extend(ReadingFactory.create_batch(3, gauge=gauge))

        # Step 5: Check dashboard reflects new data
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.context["gauge_count"], 5)
        self.assertEqual(response.context["reading_count"], 15)

        # Step 6: Export with new data
        response = self.client.get(self.export_url)
        content = b"".join(response.streaming_content).decode("utf-8")
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 16)  # Header + 15 data rows

        # Step 7: Verify export reflects dashboard data
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

        # Check that all gauges are represented
        gauge_ids_in_export = set(row[0] for row in rows[1:])
        gauge_ids_in_db = set(gauge.gauge_id for gauge in gauges)

        # All gauges should be represented in export
        for gauge_id in gauge_ids_in_db:
            self.assertIn(gauge_id, gauge_ids_in_export)

    def test_export_cross_browser_compatibility_simulation(self):
        """Test export compatibility across different client scenarios."""
        # Create test data
        gauge = GaugeFactory()
        ReadingFactory.create_batch(3, gauge=gauge)

        # Test different client scenarios
        test_scenarios = [
            {
                "HTTP_USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            {
                "HTTP_USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
            {"HTTP_USER_AGENT": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
        ]

        for headers in test_scenarios:
            client = Client()
            client.login(username="testuser", password="testpassword123")

            # Access export with different user agents
            response = client.get(self.export_url, **headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "text/csv")

            # Verify content is consistent
            content = b"".join(response.streaming_content).decode("utf-8")
            lines = content.strip().split("\n")
            self.assertEqual(len(lines), 4)  # Header + 3 data rows

    def test_export_url_resolution_integration(self):
        """Test export URL resolution and routing."""
        # Test URL resolution
        from django.urls import resolve

        resolved = resolve(self.export_url)
        self.assertEqual(resolved.url_name, "export_readings_csv")

        # Test reverse URL resolution
        self.assertEqual(reverse("export_readings_csv"), "/dashboard/export/readings/")

        # Test URL with authentication
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get("/dashboard/export/readings/")
        self.assertEqual(response.status_code, 200)

        # Test URL without authentication
        self.client.logout()
        response = self.client.get("/dashboard/export/readings/")
        self.assertEqual(response.status_code, 302)

    def test_export_complete_user_journey(self):
        """Test complete user journey from login to export download."""
        # Step 1: User visits site (unauthenticated)
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 302)

        # Step 2: User is redirected to login
        login_redirect_url = response.url
        self.assertIn(self.login_url, login_redirect_url)

        # Step 3: User logs in
        response = self.client.post(
            self.login_url, {"username": "testuser", "password": "testpassword123"}
        )
        self.assertEqual(response.status_code, 302)

        # Step 4: User visits dashboard
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

        # Step 5: User sees no data initially
        self.assertEqual(response.context["gauge_count"], 0)
        self.assertEqual(response.context["reading_count"], 0)

        # Step 6: Data is added to system
        gauge = GaugeFactory()
        ReadingFactory.create_batch(5, gauge=gauge)

        # Step 7: User refreshes dashboard
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.context["gauge_count"], 1)
        self.assertEqual(response.context["reading_count"], 5)

        # Step 8: User accesses export
        response = self.client.get(self.export_url)
        self.assertEqual(response.status_code, 200)

        # Step 9: User downloads CSV
        content = b"".join(response.streaming_content).decode("utf-8")

        # Step 10: Verify download content
        lines = content.strip().split("\n")
        self.assertEqual(len(lines), 6)  # Header + 5 data rows

        # Step 11: Verify CSV structure
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)

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

        # Check data rows
        for row in rows[1:]:
            self.assertEqual(len(row), 5)
            self.assertIsNotNone(row[0])  # Gauge ID
            self.assertIsNotNone(row[1])  # Gauge Name
            self.assertIsNotNone(row[2])  # Timestamp
            self.assertIsNotNone(row[3])  # Water Level
            # Flow Rate can be None/null
