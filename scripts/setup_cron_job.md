# Setting Up the Daily Data Collection Cron Job

Since the Render CLI doesn't support creating new services, you need to use the Render Dashboard. However, there are two approaches:

## Option 1: Blueprint Sync (Recommended - Automatic)

If your repository is connected to Render:

1. The cron job is already defined in `render.yaml`
2. Go to your Render Dashboard: https://dashboard.render.com
3. Navigate to your project/environment
4. Click "New +" → "Blueprint"
5. Select your repository: `ThomasMarketImpact/flood-data-platform`
6. Render will automatically detect the `render.yaml` and create:
   - The web service (already exists)
   - The cron job service (will be created)
   - The database (already exists)

## Option 2: Manual Creation

If Blueprint sync doesn't work:

1. Go to https://dashboard.render.com
2. Click "New +" → "Cron Job"
3. Configure as follows:

### Basic Settings
- **Name**: `daily-flood-data-collection`
- **Environment**: Python
- **Region**: Frankfurt (same as your web service)
- **Schedule**: `0 2 * * *` (2 AM UTC daily)

### Build & Deploy
- **GitHub Repository**: `https://github.com/ThomasMarketImpact/flood-data-platform`
- **Branch**: `master`
- **Build Command**: `./build.sh`
- **Command**: `./scripts/daily_collection.sh`

### Environment Variables
Copy these from your web service or add manually:

```
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=[use same as web service]
DATABASE_URL=[will auto-link to flood-data-db]
GOOGLE_FLOOD_HUB_API_KEY=AIzaSyB0d7jLuqXjDJW_BQxOyCrBVt97zse7S-M
```

4. Click "Create Cron Job"

## Verifying the Cron Job

Once created, you can verify it's working:

```bash
# List all services to get the cron job ID
render services list -o json | jq '.[] | select(.service.name == "daily-flood-data-collection")'

# Check cron job logs (replace with actual service ID)
render logs -r <cron-job-service-id> -o text

# Check last run status
render jobs list -o json
```

## Testing the Cron Job

To manually trigger a test run:

1. In Render Dashboard, go to the cron job service
2. Click "Trigger Run" button
3. Monitor logs to ensure it completes successfully

## What the Cron Job Does

Every day at 2 AM UTC (7 AM Pakistan time):

1. Collects 7 days of forecast data for all gauges
2. Updates both historical readings and future predictions
3. Fetches current flood status (severity and trends)
4. Processes data in batches to avoid API limits
5. Creates/updates readings with actual forecast values
6. Logs summary of updates and any errors

## Monitoring

To monitor daily runs:

```bash
# View recent logs
render logs -r <cron-job-id> -o text --limit 100

# Check for errors
render logs -r <cron-job-id> -o text --text "ERROR"
```

## Troubleshooting

If the cron job fails:

1. Check environment variables are set correctly
2. Verify database connection (DATABASE_URL)
3. Ensure Google API key is valid
4. Check logs for specific error messages

Common issues:
- Missing environment variables
- Database connection errors
- API rate limiting
- Memory/timeout issues (upgrade plan if needed)