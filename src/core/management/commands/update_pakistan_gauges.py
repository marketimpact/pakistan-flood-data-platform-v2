"""
Management command to update Pakistan flood gauges from comprehensive CSV file.
"""

import csv
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Gauge


class Command(BaseCommand):
    help = "Update Pakistan flood gauges from comprehensive CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="pakistan_flood_gauges_geocoded_20250719_082835.csv",
            help="Path to the CSV file containing gauge data"
        )
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Clear existing Pakistan gauges before importing"
        )
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Update existing gauges with new data"
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        clear_existing = options["clear_existing"]
        update_existing = options["update_existing"]

        # Find the CSV file
        if not os.path.isabs(csv_file):
            # Look for file in project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            csv_path = os.path.join(project_root, csv_file)
        else:
            csv_path = csv_file

        if not os.path.exists(csv_path):
            self.stdout.write(
                self.style.ERROR(f"CSV file not found: {csv_path}")
            )
            return

        self.stdout.write(f"Reading gauge data from: {csv_path}")

        try:
            with transaction.atomic():
                if clear_existing:
                    self.stdout.write("Clearing existing Pakistan gauges...")
                    deleted_count = Gauge.objects.filter(country_code="PK").delete()[0]
                    self.stdout.write(f"Deleted {deleted_count} existing gauges")

                gauges_created = 0
                gauges_updated = 0
                gauges_skipped = 0
                
                with open(csv_path, "r", encoding="utf-8") as file:
                    # Skip header lines (first 6 lines are metadata/headers)
                    for _ in range(6):
                        next(file)
                    
                    reader = csv.DictReader(file)
                    
                    for row_num, row in enumerate(reader, start=7):
                        try:
                            gauge_id = row["Gauge ID"].strip()
                            if not gauge_id:
                                continue

                            # Parse data from CSV
                            gauge_data = {
                                "gauge_id": gauge_id,
                                "name": row.get("Site Name", "").strip() or f"Gauge {gauge_id}",
                                "source": Gauge.Source.GOOGLE_FLOOD_HUB,
                                "latitude": float(row["Latitude"]),
                                "longitude": float(row["Longitude"]),
                                "country_code": "PK",
                                "quality_verified": row.get("Quality Verified", "").lower() == "true",
                                "has_model": row.get("Has Model", "").lower() == "true",
                                "province": row.get("Province", "").strip() or None,
                                "district": row.get("District", "").strip() or None,
                                "tehsil": row.get("Tehsil", "").strip() or None,
                                "location": row.get("Formatted Address", "").strip() or "",
                            }

                            # Parse warning levels (convert empty strings to None)
                            warning_level = row.get("Warning Level (2 year return period)", "").strip()
                            if warning_level and warning_level != "":
                                try:
                                    gauge_data["warning_level"] = float(warning_level)
                                except ValueError:
                                    gauge_data["warning_level"] = None
                            else:
                                gauge_data["warning_level"] = None

                            danger_level = row.get("Danger Level (5 year return period)", "").strip()
                            if danger_level and danger_level != "":
                                try:
                                    gauge_data["danger_level"] = float(danger_level)
                                except ValueError:
                                    gauge_data["danger_level"] = None
                            else:
                                gauge_data["danger_level"] = None

                            extreme_danger_level = row.get("Extreme Danger Level (10 year return period)", "").strip()
                            if extreme_danger_level and extreme_danger_level != "":
                                try:
                                    gauge_data["extreme_danger_level"] = float(extreme_danger_level)
                                except ValueError:
                                    gauge_data["extreme_danger_level"] = None
                            else:
                                gauge_data["extreme_danger_level"] = None

                            # Check if gauge already exists
                            try:
                                existing_gauge = Gauge.objects.get(gauge_id=gauge_id)
                                if update_existing:
                                    # Update existing gauge
                                    for field, value in gauge_data.items():
                                        setattr(existing_gauge, field, value)
                                    existing_gauge.save()
                                    gauges_updated += 1
                                    if gauges_updated % 100 == 0:
                                        self.stdout.write(f"Updated {gauges_updated} gauges...")
                                else:
                                    gauges_skipped += 1
                            except Gauge.DoesNotExist:
                                # Create new gauge
                                Gauge.objects.create(**gauge_data)
                                gauges_created += 1
                                if gauges_created % 100 == 0:
                                    self.stdout.write(f"Created {gauges_created} gauges...")

                        except Exception as e:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Error processing row {row_num}: {e}"
                                )
                            )
                            continue

                # Final statistics
                total_gauges = Gauge.objects.count()
                pakistan_gauges = Gauge.objects.filter(country_code="PK").count()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n=== Import Complete ===\n"
                        f"Gauges created: {gauges_created}\n"
                        f"Gauges updated: {gauges_updated}\n"
                        f"Gauges skipped: {gauges_skipped}\n"
                        f"Total Pakistan gauges: {pakistan_gauges}\n"
                        f"Total all gauges: {total_gauges}"
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error reading CSV file: {e}")
            )