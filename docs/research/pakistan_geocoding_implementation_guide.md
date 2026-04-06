# Pakistan Geocoding Implementation Guide

## Quick Start Implementation Plan

This guide provides a practical, step-by-step approach to implementing reverse geocoding for Pakistan administrative boundaries in the Django flood data platform.

## Phase 1: Simple API-Based Solution (Week 1)

### Step 1: Install Required Packages
```bash
pip install googlemaps geopy django-environ
```

### Step 2: Add to Django Settings
```python
# settings/base.py
import environ

env = environ.Env()

# Geocoding configuration
GEOCODING_BACKEND = env('GEOCODING_BACKEND', default='nominatim')  # 'google' or 'nominatim'
GOOGLE_MAPS_API_KEY = env('GOOGLE_MAPS_API_KEY', default='')
GEOCODING_CACHE_TIMEOUT = 86400 * 7  # 7 days
```

### Step 3: Create Geocoding Service
```python
# core/services/geocoding.py
from django.conf import settings
from django.core.cache import cache
import googlemaps
from geopy.geocoders import Nominatim
import logging

logger = logging.getLogger(__name__)

class GeocodingService:
    """Service for reverse geocoding coordinates to Pakistani admin boundaries."""
    
    def __init__(self):
        self.backend = settings.GEOCODING_BACKEND
        if self.backend == 'google' and settings.GOOGLE_MAPS_API_KEY:
            self.client = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
        else:
            self.client = Nominatim(user_agent="pakistan_flood_platform")
    
    def reverse_geocode(self, latitude, longitude):
        """
        Get administrative boundaries for given coordinates.
        
        Returns:
            dict: {
                'province': str,
                'district': str,
                'tehsil': str,
                'union_council': str,
                'raw_address': str,
                'source': str
            }
        """
        # Check cache first
        cache_key = f'geocode_{latitude:.6f}_{longitude:.6f}'
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            if self.backend == 'google':
                result = self._google_reverse_geocode(latitude, longitude)
            else:
                result = self._nominatim_reverse_geocode(latitude, longitude)
            
            # Cache the result
            cache.set(cache_key, result, settings.GEOCODING_CACHE_TIMEOUT)
            return result
            
        except Exception as e:
            logger.error(f"Geocoding error for {latitude}, {longitude}: {str(e)}")
            return self._empty_result()
    
    def _google_reverse_geocode(self, latitude, longitude):
        """Reverse geocode using Google Maps API."""
        results = self.client.reverse_geocode((latitude, longitude))
        
        if not results:
            return self._empty_result()
        
        components = results[0]['address_components']
        formatted_address = results[0]['formatted_address']
        
        # Extract administrative levels
        admin_areas = {}
        for component in components:
            types = component['types']
            if 'administrative_area_level_1' in types:
                admin_areas['province'] = component['long_name']
            elif 'administrative_area_level_2' in types:
                admin_areas['district'] = component['long_name']
            elif 'administrative_area_level_3' in types:
                admin_areas['tehsil'] = component['long_name']
            elif 'sublocality_level_1' in types:
                # Sometimes UC data is in sublocality
                admin_areas['union_council'] = component['long_name']
        
        return {
            'province': admin_areas.get('province', ''),
            'district': admin_areas.get('district', ''),
            'tehsil': admin_areas.get('tehsil', ''),
            'union_council': admin_areas.get('union_council', ''),
            'raw_address': formatted_address,
            'source': 'google'
        }
    
    def _nominatim_reverse_geocode(self, latitude, longitude):
        """Reverse geocode using Nominatim (OpenStreetMap)."""
        location = self.client.reverse(f"{latitude}, {longitude}", language='en')
        
        if not location:
            return self._empty_result()
        
        address = location.raw.get('address', {})
        
        # Map OSM admin levels to Pakistan structure
        # OSM typically uses: state, state_district, county, municipality, suburb
        return {
            'province': address.get('state', ''),
            'district': address.get('state_district', ''),
            'tehsil': address.get('county', address.get('municipality', '')),
            'union_council': address.get('suburb', address.get('neighbourhood', '')),
            'raw_address': location.address,
            'source': 'nominatim'
        }
    
    def _empty_result(self):
        """Return empty result structure."""
        return {
            'province': '',
            'district': '',
            'tehsil': '',
            'union_council': '',
            'raw_address': '',
            'source': 'none'
        }
```

### Step 4: Update Gauge Model
```python
# core/models.py - add these fields to Gauge model
province = models.CharField(
    max_length=100, blank=True,
    help_text="Province/State name"
)
district = models.CharField(
    max_length=100, blank=True,
    help_text="District name"
)
tehsil = models.CharField(
    max_length=100, blank=True,
    help_text="Tehsil/Taluka name"
)
union_council = models.CharField(
    max_length=100, blank=True,
    help_text="Union Council name"
)
admin_boundaries_updated = models.DateTimeField(
    null=True, blank=True,
    help_text="Last time administrative boundaries were geocoded"
)

def update_administrative_boundaries(self):
    """Update administrative boundary fields using geocoding service."""
    from core.services.geocoding import GeocodingService
    
    service = GeocodingService()
    result = service.reverse_geocode(self.latitude, self.longitude)
    
    self.province = result['province']
    self.district = result['district']
    self.tehsil = result['tehsil']
    self.union_council = result['union_council']
    self.admin_boundaries_updated = timezone.now()
    self.save(update_fields=[
        'province', 'district', 'tehsil', 'union_council',
        'admin_boundaries_updated'
    ])
```

### Step 5: Create Migration
```bash
python manage.py makemigrations -n add_admin_boundaries
python manage.py migrate
```

### Step 6: Management Command for Batch Geocoding
```python
# core/management/commands/geocode_gauges.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import Gauge
import time

class Command(BaseCommand):
    help = 'Geocode gauges to add administrative boundaries'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of gauges to process in each batch'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='Delay in seconds between geocoding requests'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-geocoding of all gauges'
        )
    
    def handle(self, *args, **options):
        batch_size = options['batch_size']
        delay = options['delay']
        force = options['force']
        
        # Get gauges that need geocoding
        if force:
            gauges = Gauge.objects.all()
        else:
            # Geocode gauges that haven't been geocoded or were geocoded > 30 days ago
            cutoff = timezone.now() - timedelta(days=30)
            gauges = Gauge.objects.filter(
                models.Q(admin_boundaries_updated__isnull=True) |
                models.Q(admin_boundaries_updated__lt=cutoff)
            )
        
        total = gauges.count()
        self.stdout.write(f"Found {total} gauges to geocode")
        
        # Process in batches
        processed = 0
        errors = 0
        
        for gauge in gauges:
            try:
                gauge.update_administrative_boundaries()
                processed += 1
                self.stdout.write(
                    f"Geocoded {gauge.name}: "
                    f"{gauge.province}, {gauge.district}"
                )
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f"Error geocoding {gauge.name}: {str(e)}")
                )
            
            # Rate limiting
            time.sleep(delay)
            
            # Progress update
            if processed % batch_size == 0:
                self.stdout.write(
                    f"Progress: {processed}/{total} "
                    f"({processed/total*100:.1f}%)"
                )
        
        # Final summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\nCompleted: {processed} geocoded, {errors} errors"
            )
        )
```

### Step 7: Add to Data Collection Pipeline
```python
# core/services/data_collection.py - modify the create_gauge method
def create_gauge(self, gauge_data: Dict[str, Any]) -> Optional[Gauge]:
    """Create a new gauge with geocoded admin boundaries."""
    try:
        gauge = Gauge.objects.create(
            gauge_id=gauge_data["gaugeId"],
            name=gauge_data["name"],
            latitude=gauge_data["latitude"],
            longitude=gauge_data["longitude"],
            # ... other fields ...
        )
        
        # Geocode administrative boundaries
        try:
            gauge.update_administrative_boundaries()
        except Exception as e:
            logger.warning(f"Failed to geocode gauge {gauge.gauge_id}: {str(e)}")
        
        return gauge
        
    except Exception as e:
        logger.error(f"Error creating gauge: {str(e)}")
        return None
```

## Phase 2: Enhanced Shapefile Solution (Week 2)

### Step 1: Install Spatial Libraries
```bash
# Install GDAL/GEOS dependencies first (OS-specific)
# Ubuntu/Debian:
sudo apt-get install gdal-bin libgdal-dev libgeos-dev

# macOS:
brew install gdal geos

# Then install Python packages
pip install django-geojson geopandas shapely
```

### Step 2: Download Pakistan Boundary Data
```bash
# Create data directory
mkdir -p data/boundaries/pakistan

# Download GADM data (includes all admin levels)
# Visit: https://gadm.org/download_country.html
# Download PAK_adm.zip and extract to data/boundaries/pakistan/
```

### Step 3: Create Boundary Loader Script
```python
# scripts/load_pakistan_boundaries.py
import geopandas as gpd
import json
from pathlib import Path

def process_pakistan_boundaries():
    """Process Pakistan shapefile and create optimized GeoJSON."""
    
    # Paths
    data_dir = Path('data/boundaries/pakistan')
    
    # Load different admin levels
    levels = {
        'province': 'PAK_adm1.shp',
        'district': 'PAK_adm2.shp',
        'tehsil': 'PAK_adm3.shp',
    }
    
    processed_data = {}
    
    for level, filename in levels.items():
        filepath = data_dir / filename
        if filepath.exists():
            print(f"Processing {level} boundaries...")
            
            # Read shapefile
            gdf = gpd.read_file(filepath)
            
            # Simplify geometry for faster lookups (tolerance in degrees)
            gdf['geometry'] = gdf['geometry'].simplify(0.001)
            
            # Convert to WGS84 if needed
            if gdf.crs != 'EPSG:4326':
                gdf = gdf.to_crs('EPSG:4326')
            
            # Extract relevant columns
            if level == 'province':
                gdf = gdf[['NAME_1', 'geometry']].rename(columns={'NAME_1': 'name'})
            elif level == 'district':
                gdf = gdf[['NAME_1', 'NAME_2', 'geometry']].rename(
                    columns={'NAME_1': 'province', 'NAME_2': 'name'}
                )
            elif level == 'tehsil':
                gdf = gdf[['NAME_1', 'NAME_2', 'NAME_3', 'geometry']].rename(
                    columns={'NAME_1': 'province', 'NAME_2': 'district', 'NAME_3': 'name'}
                )
            
            # Save as GeoJSON
            output_file = data_dir / f'pakistan_{level}.geojson'
            gdf.to_file(output_file, driver='GeoJSON')
            print(f"Saved {level} boundaries to {output_file}")
            
            processed_data[level] = gdf
    
    return processed_data

if __name__ == '__main__':
    process_pakistan_boundaries()
```

### Step 4: Create Offline Geocoding Service
```python
# core/services/offline_geocoding.py
import json
from pathlib import Path
from shapely.geometry import Point
import geopandas as gpd
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class OfflineGeocodingService:
    """Offline geocoding using local boundary files."""
    
    def __init__(self):
        self.data_dir = Path(settings.BASE_DIR) / 'data' / 'boundaries' / 'pakistan'
        self.boundaries = {}
        self._load_boundaries()
    
    def _load_boundaries(self):
        """Load boundary GeoJSON files into memory."""
        levels = ['province', 'district', 'tehsil']
        
        for level in levels:
            filepath = self.data_dir / f'pakistan_{level}.geojson'
            if filepath.exists():
                try:
                    self.boundaries[level] = gpd.read_file(filepath)
                    logger.info(f"Loaded {level} boundaries")
                except Exception as e:
                    logger.error(f"Error loading {level} boundaries: {str(e)}")
    
    def reverse_geocode(self, latitude, longitude):
        """Find administrative boundaries for given coordinates."""
        cache_key = f'offline_geocode_{latitude:.6f}_{longitude:.6f}'
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        point = Point(longitude, latitude)
        result = {
            'province': '',
            'district': '',
            'tehsil': '',
            'union_council': '',
            'source': 'offline'
        }
        
        # Check each administrative level
        for level, gdf in self.boundaries.items():
            if gdf is not None and len(gdf) > 0:
                # Find which polygon contains the point
                mask = gdf.contains(point)
                matches = gdf[mask]
                
                if not matches.empty:
                    match = matches.iloc[0]
                    result[level] = match['name']
                    
                    # Also update parent levels from the data
                    if level == 'district' and 'province' in match:
                        result['province'] = match['province']
                    elif level == 'tehsil':
                        if 'province' in match:
                            result['province'] = match['province']
                        if 'district' in match:
                            result['district'] = match['district']
        
        # Cache for 30 days
        cache.set(cache_key, result, 86400 * 30)
        return result
```

### Step 5: Create Hybrid Geocoding Service
```python
# core/services/hybrid_geocoding.py
from django.conf import settings
from .geocoding import GeocodingService
from .offline_geocoding import OfflineGeocodingService
import logging

logger = logging.getLogger(__name__)

class HybridGeocodingService:
    """
    Hybrid geocoding service that tries offline first, 
    then falls back to online services.
    """
    
    def __init__(self):
        self.offline_service = OfflineGeocodingService()
        self.online_service = GeocodingService()
    
    def reverse_geocode(self, latitude, longitude):
        """
        Get administrative boundaries using hybrid approach.
        
        1. Try offline boundaries first
        2. If incomplete, enhance with online service
        3. Merge results prioritizing offline data
        """
        # Start with offline data
        result = self.offline_service.reverse_geocode(latitude, longitude)
        
        # Check if we have all required levels
        has_all_levels = all([
            result.get('province'),
            result.get('district'),
            result.get('tehsil')
        ])
        
        # If missing data, try online service
        if not has_all_levels:
            try:
                online_result = self.online_service.reverse_geocode(latitude, longitude)
                
                # Merge results, preferring offline data
                for key in ['province', 'district', 'tehsil', 'union_council']:
                    if not result.get(key) and online_result.get(key):
                        result[key] = online_result[key]
                
                result['source'] = 'hybrid'
                
            except Exception as e:
                logger.warning(f"Online geocoding failed: {str(e)}")
        
        return result
```

## Usage Examples

### 1. In Django Shell
```python
# Test geocoding service
from core.services.geocoding import GeocodingService

service = GeocodingService()
result = service.reverse_geocode(30.3753, 69.3451)
print(result)
# Output: {'province': 'Balochistan', 'district': 'Quetta', ...}
```

### 2. In Views
```python
# dashboard/views.py
from core.services.hybrid_geocoding import HybridGeocodingService

def gauge_detail(request, gauge_id):
    gauge = get_object_or_404(Gauge, pk=gauge_id)
    
    # Update admin boundaries if not set
    if not gauge.province:
        gauge.update_administrative_boundaries()
    
    context = {
        'gauge': gauge,
        'location': {
            'coordinates': f"{gauge.latitude}, {gauge.longitude}",
            'province': gauge.province,
            'district': gauge.district,
            'tehsil': gauge.tehsil,
            'union_council': gauge.union_council or 'N/A'
        }
    }
    return render(request, 'dashboard/gauge_detail.html', context)
```

### 3. In Admin Interface
```python
# core/admin.py
from django.contrib import admin
from .models import Gauge

@admin.register(Gauge)
class GaugeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'gauge_id', 'province', 'district', 
        'status', 'admin_boundaries_updated'
    ]
    list_filter = ['province', 'district', 'status']
    search_fields = ['name', 'gauge_id', 'province', 'district']
    
    readonly_fields = [
        'province', 'district', 'tehsil', 'union_council',
        'admin_boundaries_updated'
    ]
    
    actions = ['update_admin_boundaries']
    
    def update_admin_boundaries(self, request, queryset):
        updated = 0
        for gauge in queryset:
            try:
                gauge.update_administrative_boundaries()
                updated += 1
            except Exception as e:
                self.message_user(
                    request, 
                    f"Error updating {gauge.name}: {str(e)}", 
                    level='ERROR'
                )
        
        self.message_user(
            request, 
            f"Successfully updated {updated} gauges"
        )
    
    update_admin_boundaries.short_description = "Update administrative boundaries"
```

### 4. In Templates
```html
<!-- templates/dashboard/gauge_list.html -->
<table class="table">
    <thead>
        <tr>
            <th>Name</th>
            <th>Location</th>
            <th>Province</th>
            <th>District</th>
            <th>Status</th>
        </tr>
    </thead>
    <tbody>
        {% for gauge in gauges %}
        <tr>
            <td>{{ gauge.name }}</td>
            <td>{{ gauge.latitude|floatformat:4 }}, {{ gauge.longitude|floatformat:4 }}</td>
            <td>{{ gauge.province|default:"—" }}</td>
            <td>{{ gauge.district|default:"—" }}</td>
            <td>
                <span class="badge badge-{{ gauge.status|lower }}">
                    {{ gauge.get_status_display }}
                </span>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
```

## Testing

### Unit Tests
```python
# core/tests/test_geocoding.py
from django.test import TestCase
from unittest.mock import patch, Mock
from core.services.geocoding import GeocodingService

class GeocodingServiceTest(TestCase):
    def setUp(self):
        self.service = GeocodingService()
    
    @patch('googlemaps.Client.reverse_geocode')
    def test_google_reverse_geocode(self, mock_reverse):
        # Mock Google Maps response
        mock_reverse.return_value = [{
            'address_components': [
                {
                    'long_name': 'Sindh',
                    'types': ['administrative_area_level_1']
                },
                {
                    'long_name': 'Karachi',
                    'types': ['administrative_area_level_2']
                }
            ],
            'formatted_address': 'Karachi, Sindh, Pakistan'
        }]
        
        result = self.service.reverse_geocode(24.8607, 67.0011)
        
        self.assertEqual(result['province'], 'Sindh')
        self.assertEqual(result['district'], 'Karachi')
        self.assertEqual(result['source'], 'google')
    
    def test_caching(self):
        # First call
        result1 = self.service.reverse_geocode(24.8607, 67.0011)
        
        # Second call should hit cache
        with patch.object(self.service.client, 'reverse_geocode') as mock:
            result2 = self.service.reverse_geocode(24.8607, 67.0011)
            mock.assert_not_called()
        
        self.assertEqual(result1, result2)
```

## Deployment Considerations

### 1. Environment Variables
```bash
# .env file
GEOCODING_BACKEND=hybrid
GOOGLE_MAPS_API_KEY=your-api-key-here
```

### 2. Data Storage
- Store boundary files in a persistent volume
- Consider using S3 or similar for production
- Keep backups of processed boundary data

### 3. Performance Optimization
- Pre-load boundary data on application start
- Use spatial indexes in PostGIS for large datasets
- Implement request queuing for batch operations

### 4. Monitoring
- Track API usage and costs
- Monitor cache hit rates
- Alert on geocoding failures

## Common Issues and Solutions

### Issue 1: Rate Limiting
**Solution**: Implement exponential backoff and request queuing
```python
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
def geocode_with_retry(self, lat, lng):
    return self.service.reverse_geocode(lat, lng)
```

### Issue 2: Incomplete Admin Data
**Solution**: Use multiple sources and fuzzy matching
```python
from fuzzywuzzy import process

def match_district_name(self, input_name, known_districts):
    match, score = process.extractOne(input_name, known_districts)
    return match if score > 80 else input_name
```

### Issue 3: Coordinate Format Issues
**Solution**: Normalize coordinates before geocoding
```python
def normalize_coordinates(self, lat, lng):
    # Ensure coordinates are float and in valid range
    lat = float(lat)
    lng = float(lng)
    
    if not (-90 <= lat <= 90):
        raise ValueError(f"Invalid latitude: {lat}")
    if not (-180 <= lng <= 180):
        raise ValueError(f"Invalid longitude: {lng}")
    
    return round(lat, 6), round(lng, 6)
```

## Next Steps

1. **Immediate** (Day 1-2):
   - Implement basic Nominatim geocoding
   - Add admin boundary fields to Gauge model
   - Create management command

2. **Short-term** (Week 1):
   - Set up Google Maps API integration
   - Implement caching
   - Add to data collection pipeline

3. **Medium-term** (Week 2-3):
   - Download and process Pakistan shapefiles
   - Implement offline geocoding
   - Create hybrid service

4. **Long-term** (Month 1):
   - Optimize performance with spatial indexes
   - Add support for Urdu names
   - Implement fuzzy matching for boundary names