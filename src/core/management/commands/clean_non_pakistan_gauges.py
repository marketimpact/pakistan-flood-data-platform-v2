"""
Management command to remove non-Pakistan gauges from the database.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from core.models import Gauge


class Command(BaseCommand):
    help = "Remove non-Pakistan gauges from the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting"
        )
        parser.add_argument(
            "--interactive",
            action="store_true",
            default=True,
            help="Ask for confirmation before deleting (default: True)"
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        interactive = options["interactive"]

        # Define Pakistani provinces
        PAKISTANI_PROVINCES = [
            'Punjab', 'Sindh', 'Balochistan', 'Khyber Pakhtunkhwa',
            'Gilgit-Baltistan', 'Azad Jammu and Kashmir', 
            'Islamabad Capital Territory'
        ]

        # Find non-Pakistan gauges
        non_pakistan_gauges = Gauge.objects.exclude(
            province__in=PAKISTANI_PROVINCES
        ).exclude(
            province__isnull=True
        ).exclude(
            province=""
        )

        total_non_pakistan = non_pakistan_gauges.count()
        
        if total_non_pakistan == 0:
            self.stdout.write(
                self.style.SUCCESS("No non-Pakistan gauges found!")
            )
            return

        # Show what we found
        self.stdout.write(f"\nFound {total_non_pakistan} non-Pakistan gauges:")
        
        province_breakdown = non_pakistan_gauges.values('province').annotate(
            count=Count('id')
        ).order_by('-count')
        
        for province_data in province_breakdown:
            province = province_data['province']
            count = province_data['count']
            self.stdout.write(f"  - {province}: {count} gauges")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\n[DRY RUN] Would delete {total_non_pakistan} non-Pakistan gauges"
                )
            )
            return

        # Confirm deletion
        if interactive:
            confirm = input(f"\nAre you sure you want to delete {total_non_pakistan} non-Pakistan gauges? (y/N): ")
            if confirm.lower() != 'y':
                self.stdout.write("Operation cancelled.")
                return

        try:
            with transaction.atomic():
                # Delete the gauges
                deleted_count = non_pakistan_gauges.delete()[0]
                
                # Get final counts
                total_remaining = Gauge.objects.count()
                pakistan_remaining = Gauge.objects.filter(
                    province__in=PAKISTANI_PROVINCES
                ).count()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n=== Cleanup Complete ===\n"
                        f"Deleted: {deleted_count} non-Pakistan gauges\n"
                        f"Remaining total gauges: {total_remaining}\n"
                        f"Remaining Pakistan gauges: {pakistan_remaining}"
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error during deletion: {e}")
            )