# Daily Data Collection Setup Guide

## Overview
The flood data platform is configured to automatically collect data from all 2,391 Pakistan flood gauges daily.

## What Has Been Set Up

### 1. Daily Collection Command
- **Command**: `python manage.py daily_data_collection`
- **Purpose**: Fetches all Pakistan gauges and updates daily readings
- **Features**:
  - Checks if all 2,391 gauges are in the database
  - Fetches any missing gauges automatically
  - Updates readings for all gauges
  - Skips gauges with recent readings (within 24 hours)
  - Use `--force` flag to update even with recent readings

### 2. Cron Job Configuration
The `render.yaml` file has been updated with a cron job that runs daily at 2 AM UTC (7 AM Pakistan time).

## Manual Setup Required on Render

Since you're using an existing Render deployment, you need to manually add the cron job:

1. **Go to Render Dashboard**
   - Visit https://dashboard.render.com
   - Navigate to your project

2. **Create New Cron Job**
   - Click "New +" → "Cron Job"
   - Configure as follows:
     - **Name**: `daily-flood-data-collection`
     - **Environment**: Python
     - **Build Command**: `./build.sh`
     - **Command**: `python src/manage.py daily_data_collection`
     - **Schedule**: `0 2 * * *` (2 AM UTC daily)
     - **Region**: Same as your web service (Frankfurt)

3. **Environment Variables**
   Copy these from your web service:
   - `DJANGO_SETTINGS_MODULE`: `config.settings.production`
   - `DJANGO_SECRET_KEY`: (copy from web service)
   - `DATABASE_URL`: (link to same database)
   - `GOOGLE_FLOOD_HUB_API_KEY`: (copy from web service)

4. **Deploy**
   - Click "Create Cron Job"
   - The job will run automatically at the scheduled time

## Testing the Daily Collection

### Run Manually from Dashboard
You can trigger the daily collection manually:
1. Go to the dashboard at https://flood-data-platform.onrender.com/dashboard/
2. Click "📈 Update Daily Readings" button

### Run via Command Line (SSH)
```bash
cd /opt/render/project/src/src
python manage.py daily_data_collection
```

### Force Update All Gauges
To update all gauges regardless of recent readings:
```bash
python manage.py daily_data_collection --force
```

## What Happens During Daily Collection

1. **Gauge Check** (First Phase)
   - Checks current gauge count in database
   - If less than 2,391, fetches missing gauges from Google Flood Hub API
   - Updates gauge metadata

2. **Reading Updates** (Second Phase)
   - Iterates through all gauges
   - For each gauge:
     - Checks if recent reading exists (< 24 hours old)
     - If no recent reading, fetches current data from API
     - Stores water level and flow rate measurements

3. **Summary Report**
   - Shows number of gauges updated
   - Lists skipped gauges (recent data exists)
   - Reports any errors encountered
   - Total processing statistics

## Monitoring

### Check Cron Job Logs
```bash
render logs -r <cron-job-id> -o text
```

### Check Database Status
- Visit dashboard to see:
  - Total gauge count
  - Recent readings
  - Quality verified gauges
  - Latest update timestamps

## Troubleshooting

### If Cron Job Doesn't Run
1. Check environment variables are set correctly
2. Verify schedule syntax (cron format)
3. Check Render logs for errors

### If Data Collection Fails
1. Verify Google Flood Hub API key is valid
2. Check database connectivity
3. Look for rate limiting from API
4. Review error logs

### Common Issues
- **"Recent reading exists"**: Normal behavior, prevents duplicate data
- **API errors**: Usually temporary, will retry next run
- **Missing gauges**: The system will automatically fetch them

## Data Retention

- The system stores all historical readings
- No automatic data deletion
- Consider implementing data archival for long-term storage

## Next Steps

1. Monitor the first few automated runs
2. Verify data quality and completeness
3. Set up alerts for failed runs (optional)
4. Consider implementing data visualization features