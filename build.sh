#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

cd src
python manage.py collectstatic --no-input
python manage.py migrate

# Ensure admin user exists
echo "=== Creating Admin User ==="
python manage.py ensure_admin

# Show final status
echo "=== Admin User Status ==="
python manage.py debug_admin

# Ensure all Pakistan gauges are imported
echo "=== Ensuring All Pakistan Gauges ==="
python manage.py ensure_all_gauges

# Collect initial forecast data (last 7 days)
echo "=== Collecting Initial Forecast Data ==="
python manage.py collect_forecast_data --days=7 --batch-size=100 || echo "Warning: Forecast collection had some errors but continuing..."

echo "=== Build completed successfully ==="