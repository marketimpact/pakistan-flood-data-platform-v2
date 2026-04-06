"""
Management command to ensure all Pakistan gauges are imported.
This runs during deployment to guarantee we have all 1,286 gauges.
"""
import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.management import call_command
from core.models import Gauge


class Command(BaseCommand):
    help = 'Ensure all 1,286 Pakistan gauges are imported'
    
    def handle(self, *args, **options):
        current_count = Gauge.objects.count()
        self.stdout.write(f"Current gauge count: {current_count}")
        
        # We expect at least 1,286 Pakistan gauges
        if current_count < 1286:
            self.stdout.write(
                self.style.WARNING(
                    f"Only {current_count} gauges found. Importing all Pakistan gauges..."
                )
            )
            
            # Try to import from the JSON file
            try:
                # Look for the JSON file in docs directory
                base_dir = Path(__file__).parent.parent.parent.parent.parent
                json_path = base_dir / 'docs' / 'pakistan_gauges.json'
                
                if json_path.exists():
                    call_command('import_pakistan_gauges', file=str(json_path))
                    new_count = Gauge.objects.count()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Successfully imported gauges. Total now: {new_count}"
                        )
                    )
                else:
                    # If JSON doesn't exist, fetch from Google Flood Hub
                    self.stdout.write("JSON file not found. Fetching from Google Flood Hub...")
                    call_command('fetch_google_flood_data')
                    new_count = Gauge.objects.count()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Fetched gauges from API. Total now: {new_count}"
                        )
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error importing gauges: {e}")
                )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"All gauges already present ({current_count} gauges)"
                )
            )