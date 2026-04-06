#!/bin/bash
# Deployment setup script for Pakistan Flood Data Platform
# This script runs on deployment to ensure all gauges are imported

echo "==============================="
echo "Running deployment setup"
echo "Date: $(date)"
echo "==============================="

# Change to the source directory
cd /opt/render/project/src

# Check if gauges exist, if not, import them
gauge_count=$(python manage.py shell -c "from core.models import Gauge; print(Gauge.objects.count())" 2>/dev/null | tail -1)

echo "Current gauge count: $gauge_count"

if [ "$gauge_count" -lt 2000 ]; then
    echo "Gauge count is low, importing Pakistan gauges..."
    python manage.py update_pakistan_gauges --csv-file="../pakistan_flood_gauges_geocoded_20250719_082835.csv" --clear-existing
    
    # Get updated count
    new_count=$(python manage.py shell -c "from core.models import Gauge; print(Gauge.objects.count())" 2>/dev/null | tail -1)
    echo "Imported $new_count gauges"
else
    echo "Sufficient gauges already exist, skipping import"
fi

echo "==============================="
echo "Deployment setup completed"
echo "Date: $(date)"
echo "==============================="