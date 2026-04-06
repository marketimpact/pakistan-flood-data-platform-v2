#!/bin/bash
# Quick setup helper for Render cron job

echo "======================================"
echo "Render Cron Job Setup Helper"
echo "======================================"
echo ""
echo "The Render CLI cannot create new services, but here's what you need to do:"
echo ""
echo "1. Open your browser to: https://dashboard.render.com"
echo ""
echo "2. Look for 'Blueprints' section in your dashboard"
echo "   - If you see it, click 'New Blueprint Instance'"
echo "   - Select your repo: ThomasMarketImpact/flood-data-platform"
echo "   - This will auto-create the cron job from render.yaml"
echo ""
echo "3. If no Blueprints option, create manually:"
echo "   - Click 'New +' → 'Cron Job'"
echo "   - Use these settings:"
echo ""
echo "   Name: daily-flood-data-collection"
echo "   Schedule: 0 2 * * *"
echo "   Build Command: ./build.sh"
echo "   Start Command: python src/manage.py daily_data_collection"
echo ""
echo "4. After creation, verify with:"
echo "   render services list -o text"
echo ""
echo "Would you like to open the Render dashboard now? (y/n)"
read -r response

if [[ "$response" == "y" ]]; then
    echo "Opening Render dashboard..."
    open "https://dashboard.render.com"
fi

echo ""
echo "After creating the cron job, you can monitor it with:"
echo "render logs -r <cron-job-id> -o text --tail"