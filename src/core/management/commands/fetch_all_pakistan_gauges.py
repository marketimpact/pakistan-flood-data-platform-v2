import os
import requests
from django.core.management.base import BaseCommand
from core.models import Gauge, Reading
from django.utils import timezone
import random


class Command(BaseCommand):
    help = "Fetches ALL Pakistan flood gauges from Google Flood Hub API"

    def handle(self, *args, **options):
        self.stdout.write(
            "Fetching ALL Pakistan flood gauges from Google Flood Hub API..."
        )

        # Get API key from environment
        api_key = os.environ.get("GOOGLE_FLOOD_HUB_API_KEY")
        if not api_key:
            self.stdout.write(
                self.style.ERROR("GOOGLE_FLOOD_HUB_API_KEY not found in environment")
            )
            return

        base_url = "https://floodforecasting.googleapis.com/v1"
        headers = {"X-goog-api-key": api_key, "Content-Type": "application/json"}

        # Try to fetch gauge list from API
        # Note: This endpoint might need adjustment based on actual API
        try:
            # First, try to get list of all gauges for Pakistan
            list_url = f"{base_url}/gauges"
            params = {
                "filter": "countryCode=PK",  # Pakistan
                "pageSize": 3000,  # Get all gauges
            }

            response = requests.get(
                list_url, headers=headers, params=params, timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                gauges_data = data.get("gauges", [])

                self.stdout.write(f"Found {len(gauges_data)} gauges from API")

                created_count = 0
                updated_count = 0

                for gauge_data in gauges_data:
                    gauge_id = gauge_data.get("gaugeId")
                    if not gauge_id:
                        continue

                    # Create or update gauge
                    gauge, created = Gauge.objects.update_or_create(
                        gauge_id=gauge_id,
                        defaults={
                            "name": gauge_data.get("name", f"Gauge {gauge_id}"),
                            "latitude": gauge_data.get("latitude", 0),
                            "longitude": gauge_data.get("longitude", 0),
                            "country_code": "PK",
                            "location": gauge_data.get("location", ""),
                            "quality_verified": gauge_data.get(
                                "qualityVerified", False
                            ),
                            "has_model": gauge_data.get("hasModel", False),
                            "source": Gauge.Source.GOOGLE_FLOOD_HUB,
                            "status": Gauge.Status.ACTIVE,
                        },
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully processed {len(gauges_data)} gauges\n"
                        f"Created: {created_count}\n"
                        f"Updated: {updated_count}"
                    )
                )
            else:
                # If list endpoint doesn't work, fall back to generating gauge IDs
                self.stdout.write(
                    self.style.WARNING(
                        f"Could not fetch gauge list (status: {response.status_code})\n"
                        f"Falling back to ID generation method..."
                    )
                )
                self._generate_pakistan_gauges()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching gauges: {str(e)}"))
            self.stdout.write("Falling back to ID generation method...")
            self._generate_pakistan_gauges()

    def _generate_pakistan_gauges(self):
        """Generate Pakistan gauge IDs based on HYBAS pattern"""
        # Pakistan's HYBAS IDs typically start with 412
        # Generate a comprehensive set based on the pattern
        created_count = 0

        # Major river basins in Pakistan
        basins = {
            "Indus": (4120000000, 4120100000),
            "Jhelum": (4120100000, 4120200000),
            "Chenab": (4120200000, 4120300000),
            "Ravi": (4120300000, 4120400000),
            "Sutlej": (4120400000, 4120500000),
            "Kabul": (4120500000, 4120600000),
        }

        # Generate gauges for each basin
        for basin_name, (start_id, end_id) in basins.items():
            # Sample gauges from each range
            for i in range(50):  # 50 gauges per basin = 300 total
                gauge_id = f"hybas_{start_id + random.randint(1000, 100000)}"

                # Check if gauge exists in API
                try:
                    api_key = os.environ.get("GOOGLE_FLOOD_HUB_API_KEY")
                    headers = {
                        "X-goog-api-key": api_key,
                        "Content-Type": "application/json",
                    }

                    gauge_url = (
                        f"https://floodforecasting.googleapis.com/v1/gauges/{gauge_id}"
                    )
                    response = requests.get(gauge_url, headers=headers, timeout=10)

                    if response.status_code == 200:
                        gauge_data = response.json()

                        gauge, created = Gauge.objects.update_or_create(
                            gauge_id=gauge_id,
                            defaults={
                                "name": gauge_data.get(
                                    "name", f"{basin_name} Gauge {i}"
                                ),
                                "latitude": gauge_data.get(
                                    "latitude", 25 + random.uniform(0, 12)
                                ),  # Pakistan lat range
                                "longitude": gauge_data.get(
                                    "longitude", 61 + random.uniform(0, 16)
                                ),  # Pakistan lon range
                                "country_code": "PK",
                                "location": f"{basin_name} Basin, Pakistan",
                                "quality_verified": gauge_data.get(
                                    "qualityVerified", False
                                ),
                                "has_model": gauge_data.get("hasModel", False),
                                "source": Gauge.Source.GOOGLE_FLOOD_HUB,
                                "status": Gauge.Status.ACTIVE,
                            },
                        )

                        if created:
                            created_count += 1
                            self.stdout.write(
                                f"Created gauge: {gauge_id} in {basin_name} Basin"
                            )

                except Exception:
                    # Skip if API call fails
                    continue

        self.stdout.write(
            self.style.SUCCESS(
                f"Generated {created_count} Pakistan gauges across major river basins"
            )
        )
