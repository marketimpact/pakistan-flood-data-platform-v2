"""
Django management command to import Pakistan gauges from JSON file.
"""

import json
import os
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Gauge


class Command(BaseCommand):
    help = 'Import Pakistan gauges from JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default='pakistan_gauges.json',
            help='JSON file containing gauge data (default: pakistan_gauges.json)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing gauges before importing'
        )

    def handle(self, *args, **options):
        json_file = options['file']
        dry_run = options['dry_run']
        clear_existing = options['clear_existing']
        
        # Find the JSON file
        if not os.path.isabs(json_file):
            # Look for it in the docs directory
            base_dir = Path(__file__).parent.parent.parent.parent.parent
            json_path = base_dir / 'docs' / json_file
        else:
            json_path = Path(json_file)
        
        if not json_path.exists():
            raise CommandError(f'JSON file not found: {json_path}')
        
        self.stdout.write(f'Loading gauges from: {json_path}')
        
        # Load JSON data
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                gauge_data = json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f'Invalid JSON file: {e}')
        
        if not isinstance(gauge_data, list):
            raise CommandError('JSON file must contain a list of gauge objects')
        
        self.stdout.write(f'Found {len(gauge_data)} gauges in JSON file')
        
        if dry_run:
            self.stdout.write('DRY RUN - No changes will be made')
        
        # Clear existing gauges if requested
        if clear_existing:
            if dry_run:
                existing_count = Gauge.objects.count()
                self.stdout.write(f'Would delete {existing_count} existing gauges')
            else:
                deleted_count = Gauge.objects.all().delete()[0]
                self.stdout.write(f'Deleted {deleted_count} existing gauges')
        
        # Import gauges
        imported_count = 0
        updated_count = 0
        error_count = 0
        
        with transaction.atomic():
            for i, gauge_info in enumerate(gauge_data, 1):
                try:
                    # Validate required fields
                    if not gauge_info.get('gauge_id'):
                        self.stdout.write(f'Skipping gauge {i}: Missing gauge_id')
                        error_count += 1
                        continue
                    
                    if not dry_run:
                        # Create or update gauge
                        gauge, created = Gauge.objects.update_or_create(
                            gauge_id=gauge_info['gauge_id'],
                            defaults={
                                'name': gauge_info.get('name', f"Gauge {gauge_info['gauge_id']}"),
                                'latitude': gauge_info.get('latitude'),
                                'longitude': gauge_info.get('longitude'),
                                'country_code': gauge_info.get('country_code', 'PK'),
                                'source': gauge_info.get('source', 'GOOGLE_FLOOD_HUB'),
                                'status': gauge_info.get('status', 'active'),
                                'quality_verified': gauge_info.get('quality_verified', False),
                                'has_model': gauge_info.get('has_model', True),
                                'warning_level': gauge_info.get('warning_level'),
                                'danger_level': gauge_info.get('danger_level'),
                                'extreme_danger_level': gauge_info.get('extreme_danger_level'),
                                'location': gauge_info.get('location', 'Pakistan'),
                            }
                        )
                        
                        if created:
                            imported_count += 1
                        else:
                            updated_count += 1
                    else:
                        # Dry run - just check if gauge exists
                        exists = Gauge.objects.filter(gauge_id=gauge_info['gauge_id']).exists()
                        if exists:
                            updated_count += 1
                        else:
                            imported_count += 1
                    
                    if i % 100 == 0:
                        self.stdout.write(f'Processed {i}/{len(gauge_data)} gauges...')
                
                except Exception as e:
                    self.stdout.write(f'Error processing gauge {i} ({gauge_info.get("gauge_id", "unknown")}): {e}')
                    error_count += 1
                    continue
        
        # Summary
        self.stdout.write('')
        self.stdout.write('Import Summary:')
        self.stdout.write(f'  New gauges: {imported_count}')
        self.stdout.write(f'  Updated gauges: {updated_count}')
        self.stdout.write(f'  Errors: {error_count}')
        self.stdout.write(f'  Total processed: {imported_count + updated_count + error_count}')
        
        if not dry_run:
            total_gauges = Gauge.objects.count()
            self.stdout.write(f'  Total gauges in database: {total_gauges}')
            
            # Show some statistics
            quality_verified = Gauge.objects.filter(quality_verified=True).count()
            self.stdout.write(f'  Quality verified: {quality_verified}')
            self.stdout.write(f'  Not quality verified: {total_gauges - quality_verified}')
        
        if dry_run:
            self.stdout.write('')
            self.stdout.write('This was a dry run. Use --dry-run=False to actually import the data.')
        else:
            self.stdout.write('')
            self.stdout.write('Import completed successfully!')