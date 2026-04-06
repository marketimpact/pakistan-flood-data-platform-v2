# Production Fix Instructions

## The Issue
The production site only shows 71 gauges instead of 1,286 because:
1. The old code has a default 50 gauge limit
2. The database needs migration for admin boundaries
3. All 1,286 gauges need to be re-imported

## Fix Steps (Run on Render.com Shell)

### 1. SSH into the production server
```bash
render ssh flood-data-platform
```

### 2. Apply the migration
```bash
cd src
python manage.py migrate
```

### 3. Re-import all Pakistan gauges
```bash
# First, check current gauge count
python manage.py shell -c "from core.models import Gauge; print(f'Current gauges: {Gauge.objects.count()}')"

# Import all 1,286 gauges from the JSON file
python manage.py import_pakistan_gauges --file pakistan_gauges.json

# Verify the import
python manage.py shell -c "from core.models import Gauge; print(f'Total gauges now: {Gauge.objects.count()}')"
```

### 4. Test data collection without limits
```bash
# Fetch data for ALL gauges (this will take ~20 seconds)
python manage.py fetch_google_flood_data

# Check the results
python manage.py shell -c "from core.models import Reading; print(f'Total readings: {Reading.objects.count()}')"
```

### 5. (Optional) Geocode some gauges
```bash
# Test geocoding with 10 gauges
python manage.py geocode_gauges --limit 10

# If successful, you can geocode all (will cost ~$6)
# python manage.py geocode_gauges
```

## Verification
After these steps:
1. Visit https://flood-data-platform.onrender.com/dashboard/
2. Log in with admin/Admin2025!
3. You should see 1,286 total gauges
4. Click "Collect Data" with "ALL gauges (Recommended)" selected
5. It should fetch data for all 1,286 gauges

## Notes
- The deployment already has the new code with removed limits
- The cron job will automatically fetch all gauges daily at 2 AM UTC
- Geocoding is optional but adds Province/District/Tehsil info