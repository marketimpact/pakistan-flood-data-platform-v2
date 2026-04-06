"""
Geocoding service to get administrative boundaries for gauge coordinates.
"""
import os
import logging
import requests
from typing import Dict, Optional, Tuple
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class PakistanGeocodingService:
    """Service to reverse geocode coordinates to Pakistan administrative boundaries."""
    
    def __init__(self):
        self.google_api_key = os.environ.get('GOOGLE_GEOCODING_API_KEY') or os.environ.get('GOOGLE_FLOOD_HUB_API_KEY')
        self.cache_timeout = 60 * 60 * 24 * 7  # 7 days
        
    def get_admin_boundaries(self, latitude: float, longitude: float) -> Dict[str, Optional[str]]:
        """
        Get administrative boundaries for given coordinates.
        
        Returns dict with keys: province, district, tehsil, union_council
        """
        # Check cache first
        cache_key = f"geocode_{latitude}_{longitude}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
            
        # Try Google Maps Geocoding API
        result = self._google_geocode(latitude, longitude)
        
        # Cache the result
        if result:
            cache.set(cache_key, result, self.cache_timeout)
            
        return result
    
    def _google_geocode(self, lat: float, lng: float) -> Dict[str, Optional[str]]:
        """Use Google Maps Geocoding API to get admin boundaries."""
        if not self.google_api_key:
            logger.warning("Google API key not found")
            return self._empty_result()
            
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'latlng': f"{lat},{lng}",
            'key': self.google_api_key,
            'language': 'en',
            'result_type': 'administrative_area_level_1|administrative_area_level_2|administrative_area_level_3|administrative_area_level_4'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                return self._parse_google_response(data['results'])
            else:
                logger.warning(f"Google geocoding failed: {data.get('status')}")
                return self._empty_result()
                
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return self._empty_result()
    
    def _parse_google_response(self, results) -> Dict[str, Optional[str]]:
        """Parse Google Maps response to extract admin levels."""
        boundaries = self._empty_result()
        
        # Google uses these mappings for Pakistan:
        # administrative_area_level_1 = Province
        # administrative_area_level_2 = District  
        # administrative_area_level_3 = Tehsil
        # locality or administrative_area_level_4 = Union Council (sometimes)
        
        for result in results:
            for component in result.get('address_components', []):
                types = component.get('types', [])
                name = component.get('long_name')
                
                if 'administrative_area_level_1' in types:
                    boundaries['province'] = name
                elif 'administrative_area_level_2' in types:
                    boundaries['district'] = name
                elif 'administrative_area_level_3' in types:
                    boundaries['tehsil'] = name
                elif 'administrative_area_level_4' in types:
                    boundaries['union_council'] = name
                elif 'locality' in types and not boundaries['union_council']:
                    # Sometimes UC info is in locality
                    boundaries['union_council'] = name
                    
        return boundaries
    
    def _empty_result(self) -> Dict[str, Optional[str]]:
        """Return empty result structure."""
        return {
            'province': None,
            'district': None,
            'tehsil': None,
            'union_council': None
        }
    
    def update_gauge_boundaries(self, gauge):
        """Update a gauge object with administrative boundaries."""
        if not gauge.latitude or not gauge.longitude:
            logger.warning(f"Gauge {gauge.gauge_id} has no coordinates")
            return False
            
        boundaries = self.get_admin_boundaries(gauge.latitude, gauge.longitude)
        
        # Update gauge if we got results
        if any(boundaries.values()):
            gauge.province = boundaries['province']
            gauge.district = boundaries['district'] 
            gauge.tehsil = boundaries['tehsil']
            gauge.union_council = boundaries['union_council']
            gauge.save()
            return True
            
        return False