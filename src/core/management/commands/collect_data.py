from django.core.management.base import BaseCommand
from core.services.data_collection import update_gauges_from_api

# A mock API response for the command to use
MOCK_GAUGE_DATA = [
    {
        "id": "cmd_gauge_001",
        "name": "Command Gauge 1",
        "latitude": 31.5204,
        "longitude": 74.3587,
        "countryCode": "PK",
        "status": "Active",
    }
]


class Command(BaseCommand):
    help = "Collects flood gauge data from external sources."

    def handle(self, *args, **options):
        self.stdout.write("Starting data collection...")

        # In a real scenario, a function here would fetch the data.
        # For now, we pass mock data to the service function.
        update_gauges_from_api(MOCK_GAUGE_DATA)

        self.stdout.write(self.style.SUCCESS("Successfully collected data."))
