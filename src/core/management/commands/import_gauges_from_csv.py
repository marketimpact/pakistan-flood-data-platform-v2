import csv
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Gauge


class Command(BaseCommand):
    help = "Import gauge data from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-path",
            type=str,
            default="docs/Flood alerts 7 day monitoring(Flood alerts 7 day monitoring).csv",
            help="Path to the CSV file containing gauge data",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]

        # Make path absolute if relative
        if not os.path.isabs(csv_path):
            csv_path = os.path.join(os.getcwd(), csv_path)

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_path}"))
            return

        self.stdout.write(f"Reading gauge data from: {csv_path}")

        created_count = 0
        updated_count = 0
        error_count = 0

        with open(csv_path, "r", encoding="utf-8-sig") as csvfile:
            # Skip header rows
            for _ in range(4):
                next(csvfile)

            reader = csv.DictReader(
                csvfile,
                fieldnames=[
                    "empty",
                    "gauge_id",
                    "empty2",
                    "quality_verified",
                    "gauge_value_unit",
                    "latitude",
                    "empty3",
                    "longitude",
                    "warning_level",
                    "danger_level",
                    "extreme_danger_level",
                    "forecast_start_date",
                    "forecast_end_date",
                    "latest_forecast_issue_time",
                    "forecast_trend_t",
                    "forecast_trend_t_1",
                    "forecast_trend_t_2",
                    "forecast_trend_t_3",
                    "forecast_trend_t_4",
                    "forecast_trend_t_5",
                    "forecast_trend_t_6",
                    "forecast_severity_t",
                    "forecast_severity_t_1",
                    "forecast_severity_t_2",
                    "forecast_severity_t_3",
                    "forecast_severity_t_4",
                    "forecast_severity_t_5",
                    "forecast_severity_t_6",
                    "empty4",
                ],
            )

            with transaction.atomic():
                for row in reader:
                    try:
                        gauge_id = row["gauge_id"].strip()
                        if not gauge_id or not gauge_id.startswith("hybas_"):
                            continue

                        latitude = float(row["latitude"].strip())
                        longitude = float(row["longitude"].strip())
                        quality_verified = (
                            row["quality_verified"].strip().lower() == "true"
                        )

                        # Extract warning levels if available
                        warning_level = None
                        danger_level = None
                        extreme_danger_level = None

                        try:
                            if row["warning_level"] and row["warning_level"].strip():
                                warning_level = float(row["warning_level"].strip())
                        except (ValueError, TypeError):
                            pass

                        try:
                            if row["danger_level"] and row["danger_level"].strip():
                                danger_level = float(row["danger_level"].strip())
                        except (ValueError, TypeError):
                            pass

                        try:
                            if (
                                row["extreme_danger_level"]
                                and row["extreme_danger_level"].strip()
                            ):
                                extreme_danger_level = float(
                                    row["extreme_danger_level"].strip()
                                )
                        except (ValueError, TypeError):
                            pass

                        # Create or update gauge
                        gauge, created = Gauge.objects.update_or_create(
                            gauge_id=gauge_id,
                            defaults={
                                "name": f"Pakistan Gauge {gauge_id}",
                                "latitude": latitude,
                                "longitude": longitude,
                                "country_code": "PK",
                                "location": f"Pakistan ({latitude:.4f}, {longitude:.4f})",
                                "quality_verified": quality_verified,
                                "has_model": True,  # Assuming gauges with forecast data have models
                                "source": Gauge.Source.GOOGLE_FLOOD_HUB,
                                "status": Gauge.Status.ACTIVE,
                            },
                        )

                        if created:
                            created_count += 1
                            self.stdout.write(f"Created gauge: {gauge_id}")
                        else:
                            updated_count += 1
                            self.stdout.write(f"Updated gauge: {gauge_id}")

                        # Store warning levels as metadata (would need to extend model)
                        # For now, just log them
                        if warning_level or danger_level or extreme_danger_level:
                            self.stdout.write(
                                f"  Warning levels - 2yr: {warning_level}, "
                                f"5yr: {danger_level}, 10yr: {extreme_danger_level}"
                            )

                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.WARNING(f"Error processing row: {str(e)}")
                        )
                        continue

        self.stdout.write(
            self.style.SUCCESS(
                f"\nImport complete!\n"
                f"Created: {created_count} gauges\n"
                f"Updated: {updated_count} gauges\n"
                f"Errors: {error_count}"
            )
        )

        # Show total gauge count
        total_count = Gauge.objects.filter(country_code="PK").count()
        self.stdout.write(f"\nTotal Pakistan gauges in database: {total_count}")
