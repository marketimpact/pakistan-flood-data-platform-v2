import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
from datetime import datetime
from core.models import Gauge


class Command(BaseCommand):
    help = "Runs daily data collection for all Pakistan flood gauges"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force update even if recent reading exists",
        )

    def handle(self, *args, **options):
        start_time = timezone.now()
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{"="*60}\n'
                f'DAILY FLOOD DATA COLLECTION - {start_time.strftime("%Y-%m-%d %H:%M:%S")}\n'
                f'{"="*60}\n'
            )
        )

        # Check if we have all gauges in the database
        current_gauge_count = Gauge.objects.count()

        # Always fetch data for all gauges in the database
        self.stdout.write(
            self.style.SUCCESS(
                f"\nDatabase has {current_gauge_count} gauges.\n"
                f"Fetching data for all gauges from Google Flood Hub...\n"
            )
        )

        # Fetch all gauges (no limit)
        try:
            call_command("fetch_google_flood_data")  # No limit - fetch all
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully fetched data for all gauges.\n"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Error fetching gauge data: {str(e)}\n"
                )
            )

        # Now update daily readings for all gauges
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{"="*60}\n' f"UPDATING DAILY READINGS\n" f'{"="*60}\n'
            )
        )

        force_flag = ["--force"] if options["force"] else []

        try:
            call_command("update_daily_readings", *force_flag)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error updating daily readings: {str(e)}")
            )
            return

        # Summary
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()

        self.stdout.write(
            self.style.SUCCESS(
                f'\n{"="*60}\n'
                f"DAILY COLLECTION COMPLETE\n"
                f'{"="*60}\n'
                f'Start time: {start_time.strftime("%Y-%m-%d %H:%M:%S")}\n'
                f'End time: {end_time.strftime("%Y-%m-%d %H:%M:%S")}\n'
                f"Duration: {duration:.2f} seconds\n"
                f"Total gauges: {Gauge.objects.count()}\n"
                f"Quality verified gauges: {Gauge.objects.filter(quality_verified=True).count()}\n"
                f'{"="*60}\n'
            )
        )
