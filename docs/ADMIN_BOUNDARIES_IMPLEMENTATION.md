# Adding Administrative Boundaries to Flood Gauges

## Overview
This implementation adds Province, District, Tehsil, and Union Council (UC) information to each flood gauge using reverse geocoding of their coordinates.

## What's Been Implemented

### 1. Database Schema Updates
Added fields to the Gauge model:
- `province` - Province name (e.g., Punjab, Sindh)
- `district` - District name  
- `tehsil` - Tehsil/Taluka name
- `union_council` - Union Council name
- `warning_level` - Water level threshold for warnings
- `danger_level` - Water level threshold for danger
- `extreme_danger_level` - Water level threshold for extreme danger

### 2. Geocoding Service (`core/services/geocoding.py`)
- Uses Google Maps Geocoding API (you already have the API key)
- Caches results for 7 days to minimize API calls
- Maps Google's admin levels to Pakistan's structure:
  - administrative_area_level_1 → Province
  - administrative_area_level_2 → District
  - administrative_area_level_3 → Tehsil
  - administrative_area_level_4/locality → Union Council

### 3. Management Command (`geocode_gauges`)
Batch geocodes all gauges:
```bash
python manage.py geocode_gauges
python manage.py geocode_gauges --limit 10  # Test with 10 gauges
python manage.py geocode_gauges --update-existing  # Re-geocode all
```

### 4. Dashboard Updates
The dashboard now displays:
- Province name (bold)
- District > Tehsil hierarchy
- Coordinates as before

## Deployment Steps

1. **Apply the migration**:
   ```bash
   python manage.py migrate
   ```

2. **Test geocoding locally**:
   ```bash
   python scripts/test_geocoding.py
   ```

3. **Geocode existing gauges** (start small):
   ```bash
   # Test with 5 gauges first
   python manage.py geocode_gauges --limit 5
   
   # If successful, geocode all
   python manage.py geocode_gauges
   ```

## API Costs & Limits

### Google Maps Geocoding API
- **Free tier**: $200 credit/month (~40,000 requests)
- **Cost**: $5 per 1,000 requests after free tier
- **For 1,286 gauges**: ~$6.50 one-time cost
- **Rate limit**: 50 requests/second

### Alternative Free Options

1. **OpenStreetMap/Nominatim** (Free)
   - 1 request/second limit
   - Would take ~21 minutes for all gauges
   
2. **Offline Shapefiles** (Free, faster)
   - Download Pakistan admin boundaries
   - No API limits
   - Requires more setup

## Future Enhancements

### 1. Add Province Filter to Dashboard
```python
# In dashboard view
provinces = Gauge.objects.values_list('province', flat=True).distinct()
context['provinces'] = sorted(set(p for p in provinces if p))
```

### 2. Statistics by Province
```python
from django.db.models import Count, Avg

province_stats = Gauge.objects.values('province').annotate(
    gauge_count=Count('id'),
    avg_water_level=Avg('readings__water_level')
)
```

### 3. Offline Geocoding (Cost-free)
```python
# Use shapely and geopandas with Pakistan shapefiles
import geopandas as gpd
from shapely.geometry import Point

# Load Pakistan admin boundaries shapefile
pakistan_boundaries = gpd.read_file('pakistan_admin.shp')

# Find which polygon contains the gauge point
point = Point(longitude, latitude)
admin_area = pakistan_boundaries[pakistan_boundaries.contains(point)]
```

### 4. Export with Admin Data
Update the CSV export to include:
- Province
- District  
- Tehsil
- Union Council

## Sample Data Structure

After geocoding, gauge data will look like:
```json
{
  "gauge_id": "hybas_4120570410",
  "name": "Indus River - Sehwan",
  "latitude": 26.4225,
  "longitude": 67.8625,
  "province": "Sindh",
  "district": "Jamshoro",
  "tehsil": "Sehwan",
  "union_council": "Sehwan Sharif"
}
```

## Monitoring & Maintenance

1. **Check geocoding coverage**:
   ```python
   # Gauges with admin data
   Gauge.objects.exclude(province='').count()
   
   # Gauges missing admin data
   Gauge.objects.filter(province='').count()
   ```

2. **Re-geocode failed gauges**:
   ```bash
   # Only process gauges without province data
   python manage.py geocode_gauges
   ```

3. **Monitor API usage**:
   - Google Cloud Console → APIs & Services → Credentials
   - Check Geocoding API usage and costs

## Benefits for Flood Monitoring

1. **Better Targeting**: Identify flood-prone areas by administrative unit
2. **Provincial Coordination**: Filter and report by province for stakeholder meetings
3. **Disaster Response**: Quickly identify affected districts/tehsils
4. **Resource Allocation**: Plan interventions based on administrative boundaries
5. **Integration Ready**: Data structure supports integration with BISP/NSER systems