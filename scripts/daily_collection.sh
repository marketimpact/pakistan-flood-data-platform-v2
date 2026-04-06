#!/bin/bash
# Daily data collection script for Pakistan Flood Data Platform
# This script runs daily to collect flood gauge data from Google Flood Hub

echo "=============================="
echo "Starting daily data collection"
echo "Date: $(date)"
echo "=============================="

# Change to the source directory
cd /opt/render/project/src

# Run the forecast data collection command
# Collect 7 days of forecast data
python manage.py collect_forecast_data --days=7

# Also run the updated daily readings command for any gauges not covered by forecasts
python manage.py update_daily_readings

echo "=============================="
echo "Daily collection completed"
echo "Date: $(date)"
echo "=============================="