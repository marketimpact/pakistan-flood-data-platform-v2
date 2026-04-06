from django.test import TestCase
from ..models import Gauge
from ..services.data_collection import update_gauges_from_api


class DataCollectionServiceTests(TestCase):
    def test_update_gauges_from_api(self):
        """
        Test that the service function correctly creates a new Gauge
        from mock API data. This test is expected to fail initially.
        """
        mock_api_data = [
            {
                "id": "test_gauge_001",
                "name": "API Gauge 1",
                "latitude": 30.3753,
                "longitude": 69.3451,
                "countryCode": "PK",
                "status": "Active",
            }
        ]

        update_gauges_from_api(mock_api_data)

        self.assertEqual(Gauge.objects.count(), 1)
        new_gauge = Gauge.objects.first()
        self.assertEqual(new_gauge.gauge_id, "test_gauge_001")
        self.assertEqual(new_gauge.name, "API Gauge 1")
        self.assertEqual(new_gauge.country_code, "PK")
