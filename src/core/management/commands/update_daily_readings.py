import os
import requests
import json
import random
from django.core.management.base import BaseCommand
from core.models import Gauge, Reading
from django.utils import timezone
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = "Updates daily readings for all existing gauges from Google Flood Hub API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force update even if recent reading exists",
        )

    def handle(self, *args, **options):
        self.stdout.write("Updating daily readings using forecast data...")

        # Get API key from environment
        api_key = os.environ.get("GOOGLE_FLOOD_HUB_API_KEY")
        if not api_key:
            self.stdout.write(
                self.style.ERROR("GOOGLE_FLOOD_HUB_API_KEY not found in environment")
            )
            return

        base_url = "https://floodforecasting.googleapis.com/v1"
        headers = {"X-goog-api-key": api_key, "Content-Type": "application/json"}

        # Get all gauges in the system
        gauges = Gauge.objects.all()
        total_gauges = gauges.count()

        if total_gauges == 0:
            self.stdout.write(
                self.style.WARNING("No gauges found. Run collect data first.")
            )
            return

        self.stdout.write(f"Found {total_gauges} gauges to update...")

        # Process in batches (API limit is 500 gauges per request)
        batch_size = 100
        updated_count = 0
        skipped_count = 0
        error_count = 0
        force_update = options["force"]

        # Get forecast data for last 24 hours
        end_time = timezone.now()
        start_time = end_time - timedelta(hours=24)

        for i in range(0, total_gauges, batch_size):
            batch_gauges = gauges[i:i + batch_size]
            gauge_ids = [g.gauge_id for g in batch_gauges]
            
            try:
                # Query forecast data for this batch
                params = [("gaugeIds", gid) for gid in gauge_ids]
                params.append(("issuedTimeStart", start_time.isoformat()))
                params.append(("issuedTimeEnd", end_time.isoformat()))
                
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
                    
                    for gauge in batch_gauges:
                        # Check if we already have a recent reading
                        if not force_update:
                            recent_reading = Reading.objects.filter(
                                gauge=gauge, timestamp__gte=start_time
                            ).first()
                            if recent_reading:
                                skipped_count += 1
                                continue
                        
                        # Process forecast data for this gauge
                        gauge_forecasts = forecasts.get(gauge.gauge_id, {}).get("forecasts", [])
                        
                        if gauge_forecasts:
                            # Get the most recent forecast
                            latest_forecast = gauge_forecasts[-1]
                            forecast_ranges = latest_forecast.get("forecastRanges", [])
                            
                            if forecast_ranges:
                                # Use the most recent forecast value
                                latest_range = forecast_ranges[-1]  # Last one is most recent forecast
                                value = latest_range.get("value")
                                
                                if value is not None:
                                    # Use the forecast start time as the reading timestamp
                                    forecast_time = datetime.fromisoformat(
                                        latest_range["forecastStartTime"].replace("Z", "+00:00")
                                    )
                                    Reading.objects.update_or_create(
                                        gauge=gauge,
                                        timestamp=forecast_time,
                                        defaults={
                                            "water_level": value,
                                            "flow_rate": value,
                                        }
                                    )
                                    updated_count += 1
                                    quality_indicator = "✓" if gauge.quality_verified else "⚠"
                                    self.stdout.write(
                                        f"  {quality_indicator} Updated {gauge.name}: {value:.2f} m³/s"
                                    )
                                else:
                                    error_count += 1
                            else:
                                error_count += 1
                        else:
                            # No forecast data available
                            error_count += 1
                            
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Failed to get forecasts: {response.status_code}"
                        )
                    )
                    error_count += len(batch_gauges)
                    
            except requests.exceptions.RequestException as e:
                error_count += len(batch_gauges)
                self.stdout.write(
                    self.style.WARNING(
                        f"Network error for batch: {str(e)}"
                    )
                )
            except Exception as e:
                error_count += len(batch_gauges)
                self.stdout.write(
                    self.style.ERROR(
                        f"Error processing batch: {str(e)}"
                    )
                )

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\nDaily update complete!\n"
                f"✓ Updated: {updated_count} gauges\n"
                f"⏭ Skipped: {skipped_count} gauges (recent data exists)\n"
                f"❌ Errors: {error_count} gauges\n"
                f"📊 Total processed: {updated_count + skipped_count + error_count}/{total_gauges}"
            )
        )

        if skipped_count > 0 and not force_update:
            self.stdout.write(
                self.style.WARNING("Use --force to update gauges with recent readings")
            )
