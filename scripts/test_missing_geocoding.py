#!/usr/bin/env python3
"""
Test geocoding for coordinates that returned no data
"""

import os
import requests
import time

def test_geocoding(lat, lng, gauge_id):
    """Test Google geocoding for specific coordinates."""
    
    api_key = os.environ.get('GOOGLE_GEOCODING_API_KEY', 'AIzaSyCu8yng-tY0vS-KtPVUcs4vKtOVmsNEEUc')
    
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    
    # Try different approaches
    approaches = [
        {
            'name': 'Standard reverse geocoding',
            'params': {
                'latlng': f"{lat},{lng}",
                'key': api_key,
                'language': 'en'
            }
        },
        {
            'name': 'With result_type filter',
            'params': {
                'latlng': f"{lat},{lng}",
                'key': api_key,
                'language': 'en',
                'result_type': 'administrative_area_level_1|administrative_area_level_2|administrative_area_level_3|administrative_area_level_4'
            }
        },
        {
            'name': 'Without any filters',
            'params': {
                'latlng': f"{lat},{lng}",
                'key': api_key
            }
        }
    ]
    
    print(f"\nTesting gauge {gauge_id} at ({lat}, {lng}):")
    print("=" * 60)
    
    for approach in approaches:
        print(f"\n{approach['name']}:")
        
        try:
            response = requests.get(url, params=approach['params'], timeout=10)
            response.raise_for_status()
            data = response.json()
            
            print(f"Status: {data.get('status')}")
            
            if data['status'] == 'OK' and data['results']:
                print(f"Found {len(data['results'])} results")
                
                # Extract administrative info
                admin_info = {'province': None, 'district': None, 'tehsil': None, 'uc': None}
                
                for i, result in enumerate(data['results'][:3]):  # Show first 3 results
                    print(f"\nResult {i+1}:")
                    print(f"  Formatted address: {result.get('formatted_address', 'N/A')}")
                    print(f"  Types: {result.get('types', [])}")
                    
                    for component in result.get('address_components', []):
                        types = component.get('types', [])
                        name = component.get('long_name')
                        
                        if 'administrative_area_level_1' in types:
                            admin_info['province'] = name
                            print(f"  Province: {name}")
                        elif 'administrative_area_level_2' in types:
                            admin_info['district'] = name
                            print(f"  District: {name}")
                        elif 'administrative_area_level_3' in types:
                            admin_info['tehsil'] = name
                            print(f"  Tehsil: {name}")
                        elif 'administrative_area_level_4' in types:
                            admin_info['uc'] = name
                            print(f"  UC: {name}")
                        elif 'locality' in types:
                            print(f"  Locality: {name}")
                
                print(f"\nExtracted admin boundaries: {admin_info}")
                
            elif data['status'] == 'ZERO_RESULTS':
                print("No results found for this location")
            else:
                print(f"Error: {data.get('error_message', 'Unknown error')}")
                
        except Exception as e:
            print(f"Request failed: {e}")
        
        time.sleep(0.5)  # Rate limiting

# Test problematic coordinates
test_cases = [
    (29.6396, 66.1021, 'hybas_2120844580'),  # First gauge with no data
    (36.4771, 73.8438, 'hybas_4120567310'),  # One that returned ZERO_RESULTS
    (29.5729, 65.7312, 'hybas_2120845610'),  # One that worked for comparison
]

print("Testing geocoding for problematic coordinates...")
for lat, lng, gauge_id in test_cases:
    test_geocoding(lat, lng, gauge_id)