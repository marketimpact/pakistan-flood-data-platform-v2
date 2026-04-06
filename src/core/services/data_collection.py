import os
import requests
from django.conf import settings
from ..models import Gauge, Reading, Prediction


class DataCollectionService:
    """Service for collecting data from Google Flood Hub API."""
    
    def __init__(self):
        self.api_key = os.environ.get('GOOGLE_FLOOD_HUB_API_KEY', '')
        self.base_url = 'https://floodforecasting.googleapis.com/v1'
        self.headers = {
            'X-goog-api-key': self.api_key,
            'Content-Type': 'application/json'
        }
    
    def get_gauge_data(self, gauge_id):
        """Get gauge data from API."""
        url = f"{self.base_url}/gauges/{gauge_id}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return None
    
    def get_gauge_readings(self, gauge_id):
        """Get gauge readings from API."""
        # Stub implementation
        return []
    
    def update_gauge_readings(self, gauge_id):
        """Update readings for a gauge."""
        # Stub implementation
        pass


# Alias for backward compatibility
GoogleFloodHubService = DataCollectionService


def update_gauges_from_api(api_data):
    """
    Updates gauge data from API response.
    Creates new gauges from the provided API data.
    """
    for gauge_data in api_data:
        gauge, created = Gauge.objects.get_or_create(
            gauge_id=gauge_data["id"],
            defaults={
                "name": gauge_data["name"],
                "latitude": gauge_data["latitude"],
                "longitude": gauge_data["longitude"],
                "country_code": gauge_data["countryCode"],
                "status": gauge_data["status"].lower(),
            },
        )
        if not created:
            # Update existing gauge
            gauge.name = gauge_data["name"]
            gauge.latitude = gauge_data["latitude"]
            gauge.longitude = gauge_data["longitude"]
            gauge.country_code = gauge_data["countryCode"]
            gauge.status = gauge_data["status"].lower()
            gauge.save()
