#!/usr/bin/env python
"""
Test script for geocoding functionality.
Tests with a few sample Pakistan coordinates.
"""
import os
import sys
import django

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from core.services.geocoding import PakistanGeocodingService

# Test coordinates from different regions of Pakistan
test_locations = [
    {"name": "Lahore", "lat": 31.5497, "lng": 74.3436},
    {"name": "Karachi", "lat": 24.8607, "lng": 67.0011},
    {"name": "Islamabad", "lat": 33.6844, "lng": 73.0479},
    {"name": "Quetta", "lat": 30.1798, "lng": 66.9750},
    {"name": "Peshawar", "lat": 34.0151, "lng": 71.5249},
]

def main():
    print("Testing Pakistan Geocoding Service")
    print("=" * 50)
    
    service = PakistanGeocodingService()
    
    for location in test_locations:
        print(f"\nTesting {location['name']} ({location['lat']}, {location['lng']})")
        
        result = service.get_admin_boundaries(location['lat'], location['lng'])
        
        print(f"  Province: {result['province'] or 'Not found'}")
        print(f"  District: {result['district'] or 'Not found'}")
        print(f"  Tehsil: {result['tehsil'] or 'Not found'}")
        print(f"  UC: {result['union_council'] or 'Not found'}")

if __name__ == "__main__":
    main()