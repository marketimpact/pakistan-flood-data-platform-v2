# Pakistan Administrative Boundary Geocoding Options Research

## Executive Summary

This document analyzes various options for reverse geocoding coordinates to obtain Pakistan administrative boundaries (Province, District, Tehsil, Union Council) for the flood data platform. The research covers both API-based and offline solutions suitable for Django implementation.

## Pakistan Administrative Hierarchy

Pakistan has a four-tier administrative structure:
1. **Provinces/Territories** (4 provinces + 3 territories)
   - Punjab, Sindh, Khyber Pakhtunkhwa, Balochistan
   - Islamabad Capital Territory, Azad Jammu & Kashmir, Gilgit-Baltistan
2. **Divisions** (35+ divisions)
3. **Districts** (150+ districts)
4. **Tehsils/Talukas** (600+ tehsils)
5. **Union Councils** (6,000+ union councils)

## Option 1: Google Maps Geocoding API

### Overview
Google's Geocoding API provides reverse geocoding with administrative area support.

### Pros
- High accuracy and reliability
- Well-documented Python client library (`googlemaps`)
- Returns administrative levels including:
  - administrative_area_level_1 (Province)
  - administrative_area_level_2 (District)
  - administrative_area_level_3 (Tehsil - limited coverage)
  - locality (City/Town)
- Regular updates to geographic data

### Cons
- Requires API key and billing
- Rate limits: 50 requests/second
- Cost: $5 per 1,000 requests after free tier (200 USD/month credit)
- May not have complete Union Council data
- Network dependency

### Implementation Example
```python
import googlemaps

gmaps = googlemaps.Client(key='YOUR_API_KEY')
result = gmaps.reverse_geocode((30.3753, 69.3451))  # Coordinates in Pakistan

# Extract administrative areas
for component in result[0]['address_components']:
    if 'administrative_area_level_1' in component['types']:
        province = component['long_name']
    elif 'administrative_area_level_2' in component['types']:
        district = component['long_name']
```

### Django Integration
```python
# settings.py
GOOGLE_MAPS_API_KEY = env('GOOGLE_MAPS_API_KEY')

# services/geocoding.py
class GoogleMapsGeocoder:
    def __init__(self):
        self.client = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
    
    def get_admin_boundaries(self, lat, lng):
        results = self.client.reverse_geocode((lat, lng))
        # Parse and return administrative boundaries
```

## Option 2: OpenStreetMap with Nominatim

### Overview
Free, open-source geocoding service using OpenStreetMap data.

### Pros
- Completely free
- No API key required for limited use
- Good coverage of Pakistan
- Can self-host for unlimited queries
- Returns admin levels 4-10 (Province to Union Council)

### Cons
- Rate limit: 1 request/second (public server)
- Less reliable than commercial services
- May have incomplete or outdated data for some areas
- Slower response times

### Implementation Example
```python
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="pakistan_flood_platform")
location = geolocator.reverse("30.3753, 69.3451", language='en')

# Parse address dictionary
address = location.raw['address']
province = address.get('state', '')
district = address.get('state_district', '')
```

### Django Integration
```python
# services/geocoding.py
from django.core.cache import cache
from geopy.geocoders import Nominatim

class NominatimGeocoder:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="pakistan_flood_platform")
    
    def get_admin_boundaries(self, lat, lng):
        cache_key = f"nominatim_{lat}_{lng}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        location = self.geolocator.reverse(f"{lat}, {lng}", language='en')
        result = self._parse_address(location.raw['address'])
        cache.set(cache_key, result, 86400)  # Cache for 24 hours
        return result
```

## Option 3: Pakistan-Specific Shapefile/GeoJSON Solutions

### Overview
Use offline administrative boundary data with spatial libraries.

### Data Sources
1. **GADM (Global Administrative Areas)**
   - URL: https://gadm.org/download_country.html
   - Provides shapefiles for Pakistan with all admin levels
   - High quality, research-grade data

2. **Natural Earth Data**
   - URL: https://www.naturalearthdata.com/
   - Province-level boundaries only

3. **Pakistan Bureau of Statistics**
   - Official boundary data (when available)

4. **OpenStreetMap Extracts**
   - Geofabrik: https://download.geofabrik.de/asia/pakistan.html
   - Complete OSM data for Pakistan

### Pros
- No API costs or rate limits
- Complete offline operation
- Full control over data quality
- Can include custom boundaries
- Fast queries with spatial indexes

### Cons
- Requires initial setup and data processing
- Need to handle updates manually
- Larger storage requirements
- More complex implementation

### Implementation with GeoDjango
```python
# models.py
from django.contrib.gis.db import models

class PakistanAdminBoundary(models.Model):
    LEVEL_CHOICES = [
        ('province', 'Province'),
        ('district', 'District'),
        ('tehsil', 'Tehsil'),
        ('uc', 'Union Council'),
    ]
    
    name = models.CharField(max_length=255)
    name_urdu = models.CharField(max_length=255, blank=True)
    admin_level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)
    geometry = models.MultiPolygonField(srid=4326)
    
    class Meta:
        indexes = [
            models.Index(fields=['admin_level']),
        ]

# services/geocoding.py
from django.contrib.gis.geos import Point
from core.models import PakistanAdminBoundary

class ShapefileGeocoder:
    def get_admin_boundaries(self, lat, lng):
        point = Point(lng, lat, srid=4326)
        
        # Find all boundaries containing this point
        boundaries = PakistanAdminBoundary.objects.filter(
            geometry__contains=point
        ).select_related('parent')
        
        result = {}
        for boundary in boundaries:
            result[boundary.admin_level] = {
                'name': boundary.name,
                'name_urdu': boundary.name_urdu,
            }
        
        return result
```

### Data Loading Script
```python
# management/commands/load_pakistan_boundaries.py
import os
from django.core.management.base import BaseCommand
from django.contrib.gis.utils import LayerMapping
from core.models import PakistanAdminBoundary

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Load from shapefile
        shapefile_path = 'data/pakistan_boundaries/pakistan_admbnda_adm2_undp_wfp_20220909.shp'
        
        mapping = {
            'name': 'ADM2_EN',
            'name_urdu': 'ADM2_UR',
            'admin_level': 'admin_level',
            'geometry': 'MULTIPOLYGON',
        }
        
        lm = LayerMapping(
            PakistanAdminBoundary, shapefile_path, mapping,
            transform=False, encoding='utf-8'
        )
        lm.save(strict=True, verbose=True)
```

## Option 4: MapMyIndia (Now Mappls) API

### Overview
India-based mapping service with good coverage of Pakistan.

### Pros
- Detailed coverage of South Asian region
- Supports Urdu place names
- REST API available
- Good for cross-border regions

### Cons
- Requires commercial license
- May have political boundary sensitivities
- Limited documentation for Pakistan-specific features

## Option 5: HERE Maps API

### Overview
Commercial geocoding service with global coverage.

### Pros
- High-quality global data
- Multiple response formats
- Batch geocoding available
- 250K free transactions/month

### Cons
- Commercial service with costs
- May not have deep admin levels for Pakistan

## Option 6: Hybrid Approach (Recommended)

### Strategy
Combine multiple sources for reliability and completeness:

1. **Primary**: Use offline shapefiles (GADM) for basic admin boundaries
2. **Enhancement**: Use Google Maps API for additional details and verification
3. **Fallback**: Use Nominatim for cases where offline data is incomplete
4. **Caching**: Store results in database to minimize API calls

### Implementation Architecture
```python
# services/geocoding.py
class HybridGeocoder:
    def __init__(self):
        self.shapefile_geocoder = ShapefileGeocoder()
        self.google_geocoder = GoogleMapsGeocoder()
        self.nominatim_geocoder = NominatimGeocoder()
    
    def get_admin_boundaries(self, lat, lng):
        # Check cache first
        cache_key = f"geocode_{lat}_{lng}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Try offline shapefiles first
        result = self.shapefile_geocoder.get_admin_boundaries(lat, lng)
        
        # If incomplete, enhance with API data
        if not result.get('tehsil') or not result.get('uc'):
            try:
                api_result = self.google_geocoder.get_admin_boundaries(lat, lng)
                result.update(api_result)
            except Exception as e:
                # Fallback to Nominatim
                nominatim_result = self.nominatim_geocoder.get_admin_boundaries(lat, lng)
                result.update(nominatim_result)
        
        # Store in cache
        cache.set(cache_key, result, 86400 * 7)  # Cache for 7 days
        
        return result
```

### Django Model Extension
```python
# models.py
class Gauge(models.Model):
    # ... existing fields ...
    
    # Administrative boundaries
    province = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    tehsil = models.CharField(max_length=100, blank=True)
    union_council = models.CharField(max_length=100, blank=True)
    
    # Geocoding metadata
    geocoded_at = models.DateTimeField(null=True, blank=True)
    geocoding_source = models.CharField(max_length=50, blank=True)
    
    def update_admin_boundaries(self):
        """Update administrative boundaries using geocoding service."""
        geocoder = HybridGeocoder()
        boundaries = geocoder.get_admin_boundaries(self.latitude, self.longitude)
        
        self.province = boundaries.get('province', '')
        self.district = boundaries.get('district', '')
        self.tehsil = boundaries.get('tehsil', '')
        self.union_council = boundaries.get('uc', '')
        self.geocoded_at = timezone.now()
        self.geocoding_source = boundaries.get('source', 'hybrid')
        self.save()
```

## Python Libraries for Pakistan Geodata

### 1. GeoPandas
- Excellent for working with shapefiles
- Spatial operations and analysis
- Integration with matplotlib for visualization

### 2. Shapely
- Geometric operations
- Used by GeoDjango internally
- Good for point-in-polygon tests

### 3. Fiona
- Reading and writing spatial data files
- Better performance than GeoPandas for simple operations

### 4. PyProj
- Coordinate system transformations
- Important for Pakistan data (often in local projections)

### 5. Django-specific
- **GeoDjango**: Built-in spatial database functions
- **django-geojson**: Serialize Django models to GeoJSON
- **django-leaflet**: Interactive maps for admin interface

## Implementation Recommendations

### For Production Use

1. **Start with Shapefiles**
   - Download GADM Pakistan data
   - Process and load into PostGIS database
   - Create spatial indexes for performance

2. **Add API Enhancement**
   - Use Google Maps API for verification
   - Implement caching to reduce costs
   - Set up monitoring for API usage

3. **Database Schema**
   ```sql
   -- Add to existing gauge table
   ALTER TABLE core_gauge ADD COLUMN province VARCHAR(100);
   ALTER TABLE core_gauge ADD COLUMN district VARCHAR(100);
   ALTER TABLE core_gauge ADD COLUMN tehsil VARCHAR(100);
   ALTER TABLE core_gauge ADD COLUMN union_council VARCHAR(100);
   ALTER TABLE core_gauge ADD COLUMN admin_boundaries JSONB;
   
   -- Create indexes
   CREATE INDEX idx_gauge_province ON core_gauge(province);
   CREATE INDEX idx_gauge_district ON core_gauge(district);
   ```

4. **Management Command**
   ```python
   # management/commands/geocode_gauges.py
   class Command(BaseCommand):
       def handle(self, *args, **options):
           geocoder = HybridGeocoder()
           
           for gauge in Gauge.objects.filter(geocoded_at__isnull=True):
               gauge.update_admin_boundaries()
               time.sleep(1)  # Rate limiting
   ```

### Performance Considerations

1. **Caching Strategy**
   - Cache geocoding results for 7-30 days
   - Use Redis for distributed caching
   - Implement cache warming for known coordinates

2. **Batch Processing**
   - Process gauges in batches during off-peak hours
   - Use Celery for async processing

3. **Spatial Indexing**
   - Create GIST indexes on geometry columns
   - Use PostGIS for optimal performance

## Cost Analysis

| Service | Free Tier | Cost per 1000 | Monthly (10K requests) |
|---------|-----------|---------------|------------------------|
| Google Maps | $200 credit/month | $5 | Free with credit |
| HERE Maps | 250K/month | $1 | Free |
| Nominatim | Unlimited (self-hosted) | $0 | Server costs only |
| MapMyIndia | None | Contact sales | Variable |
| Shapefiles | Unlimited | $0 | One-time setup |

## Conclusion

For the Pakistan Flood Data Platform, I recommend the **Hybrid Approach**:

1. **Primary**: Use GADM shapefiles loaded into PostGIS for offline geocoding
2. **Enhancement**: Google Maps API for additional detail and verification
3. **Fallback**: Self-hosted Nominatim instance for unlimited queries
4. **Optimization**: Aggressive caching and batch processing

This approach provides:
- High reliability (offline capability)
- Cost efficiency (minimal API calls)
- Complete admin hierarchy coverage
- Scalability for future growth

The implementation can start simple with just shapefiles and gradually add API services as needed.