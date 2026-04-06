import os
import requests
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Gauge, Reading, Prediction


class Command(BaseCommand):
    help = "Collects forecast data from Google Flood Hub API for all gauges"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Number of days of forecast data to retrieve (default: 7)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of gauges to process per batch (max 500)",
        )

    def handle(self, *args, **options):
        # Auto-import Pakistan gauges if count is low
        current_gauge_count = Gauge.objects.count()
        self.stdout.write(f"Current gauge count: {current_gauge_count}")
        
        if current_gauge_count < 2000:
            self.stdout.write("Gauge count is low, attempting to import Pakistan gauges...")
            try:
                from django.core.management import call_command
                call_command('update_pakistan_gauges', 
                            csv_file='../pakistan_flood_gauges_geocoded_20250719_082835.csv',
                            clear_existing=True,
                            verbosity=1)
                new_count = Gauge.objects.count()
                self.stdout.write(f"Updated gauge count: {new_count}")
                
                # Also clean non-Pakistan gauges
                try:
                    call_command('clean_non_pakistan_gauges', verbosity=0, interactive=False)
                    final_count = Gauge.objects.count()
                    self.stdout.write(f"Final count after cleanup: {final_count}")
                except Exception as cleanup_error:
                    self.stdout.write(f"Warning: Failed to clean non-Pakistan gauges: {cleanup_error}")
                    
            except Exception as e:
                self.stdout.write(f"Failed to import gauges: {e}")
        
        api_key = os.environ.get("GOOGLE_FLOOD_HUB_API_KEY")
        if not api_key:
            self.stdout.write(
                self.style.ERROR("GOOGLE_FLOOD_HUB_API_KEY not found in environment")
            )
            return

        base_url = "https://floodforecasting.googleapis.com/v1"
        headers = {"X-goog-api-key": api_key, "Content-Type": "application/json"}

        # Get all gauges
        gauges = Gauge.objects.filter(source=Gauge.Source.GOOGLE_FLOOD_HUB)
        total_gauges = gauges.count()
        
        if total_gauges == 0:
            self.stdout.write(self.style.WARNING("No gauges found"))
            return

        self.stdout.write(f"Processing {total_gauges} gauges...")

        # Calculate time range
        end_time = timezone.now()
        start_time = end_time - timedelta(days=options["days"])
        
        # Process in batches (API limit is 500 gauges per request)
        batch_size = min(options["batch_size"], 500)
        processed = 0
        total_forecasts = 0
        total_readings = 0
        errors = 0

        for i in range(0, total_gauges, batch_size):
            batch_gauges = gauges[i:i + batch_size]
            gauge_ids = [g.gauge_id for g in batch_gauges]
            
            # 1. Get forecast data
            # Build params as list of tuples for multiple values
            params = [("gaugeIds", gid) for gid in gauge_ids]
            if options["days"] <= 7:  # Only add time params for recent data
                params.append(("issuedTimeStart", start_time.isoformat()))
                params.append(("issuedTimeEnd", end_time.isoformat()))
            
            try:
                self.stdout.write(f"\nFetching forecasts for batch {i//batch_size + 1}...")
                response = requests.get(
                    f"{base_url}/gauges:queryGaugeForecasts",
                    params=params,
                    headers=headers,
                    timeout=30,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    forecasts = data.get("forecasts", {})
                    
                    for gauge_id, gauge_data in forecasts.items():
                        gauge = next((g for g in batch_gauges if g.gauge_id == gauge_id), None)
                        if not gauge:
                            continue
                        
                        forecast_list = gauge_data.get("forecasts", [])
                        for forecast in forecast_list:
                            issued_time = datetime.fromisoformat(
                                forecast["issuedTime"].replace("Z", "+00:00")
                            )
                            
                            # Process each forecast range
                            for range_data in forecast.get("forecastRanges", []):
                                start = datetime.fromisoformat(
                                    range_data["forecastStartTime"].replace("Z", "+00:00")
                                )
                                value = range_data.get("value")
                                
                                if value is not None:
                                    # Create prediction for future times
                                    if start > issued_time:
                                        Prediction.objects.update_or_create(
                                            gauge=gauge,
                                            prediction_for_timestamp=start,
                                            defaults={
                                                "water_level": value,
                                            }
                                        )
                                        total_forecasts += 1
                                    else:
                                        # Create reading for past/current times
                                        Reading.objects.update_or_create(
                                            gauge=gauge,
                                            timestamp=start,
                                            defaults={
                                                "water_level": value,
                                                "flow_rate": value,  # Assuming same unit
                                            }
                                        )
                                        total_readings += 1
                    
                    self.stdout.write(
                        f"  Processed {len(forecasts)} gauges with forecast data"
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  Failed to get forecasts: {response.status_code}"
                        )
                    )
                    errors += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  Error fetching forecasts: {str(e)}")
                )
                errors += 1
            
            # 2. Get current flood status
            try:
                self.stdout.write(f"  Fetching flood status...")
                params = [("gaugeIds", gid) for gid in gauge_ids]
                response = requests.get(
                    f"{base_url}/floodStatus:queryLatestFloodStatusByGaugeIds",
                    params=params,
                    headers=headers,
                    timeout=30,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    statuses = data.get("floodStatuses", [])
                    
                    for status in statuses:
                        gauge_id = status.get("gaugeId")
                        gauge = next((g for g in batch_gauges if g.gauge_id == gauge_id), None)
                        if gauge:
                            # Update gauge with latest status
                            severity = status.get("severity", "UNKNOWN")
                            if severity != "UNKNOWN":
                                self.stdout.write(
                                    f"    {gauge.name}: {severity} - {status.get('forecastTrend', 'NO_CHANGE')}"
                                )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  No flood status available: {response.status_code}"
                        )
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"  Error fetching flood status: {str(e)}")
                )
            
            processed += len(batch_gauges)
            self.stdout.write(f"Progress: {processed}/{total_gauges} gauges")

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\nCollection complete!"
                f"\n✓ Processed: {processed} gauges"
                f"\n✓ Readings created: {total_readings}"
                f"\n✓ Predictions created: {total_forecasts}"
                f"\n✗ Errors: {errors}"
            )
        )