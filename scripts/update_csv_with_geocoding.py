#!/usr/bin/env python3
"""
Script to update the CSV file with Province, District, Tehsil, and UC information
using the existing Google geocoding service.
"""

import os
import sys
import csv
import requests
import time
from pathlib import Path

# Standalone geocoding service (no Django dependencies)
class StandaloneGeocodingService:
    """Standalone geocoding service for CSV processing."""
    
    def __init__(self):
        self.google_api_key = os.environ.get('GOOGLE_GEOCODING_API_KEY') or os.environ.get('GOOGLE_FLOOD_HUB_API_KEY')
        
    def get_admin_boundaries(self, latitude: float, longitude: float) -> dict:
        """Get administrative boundaries for given coordinates."""
        if not self.google_api_key:
            print("Warning: Google API key not found")
            return self._empty_result()
            
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'latlng': f"{latitude},{longitude}",
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
                print(f"Geocoding failed for ({latitude}, {longitude}): {data.get('status')}")
                return self._empty_result()
                
        except Exception as e:
            print(f"Geocoding error for ({latitude}, {longitude}): {e}")
            return self._empty_result()
    
    def _parse_google_response(self, results) -> dict:
        """Parse Google Maps response to extract admin levels."""
        boundaries = self._empty_result()
        
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
                    boundaries['union_council'] = name
                    
        return boundaries
    
    def _empty_result(self) -> dict:
        """Return empty result structure."""
        return {
            'province': None,
            'district': None,
            'tehsil': None,
            'union_council': None
        }

def main():
    """Main function to process the CSV and add geocoding data."""
    
    # File paths
    csv_file_path = Path(__file__).parent.parent / 'docs' / 'Flood alerts 7 day monitoring(Flood alerts 7 day monitoring).csv'
    output_file_path = csv_file_path.parent / 'Flood_alerts_with_geocoding.csv'
    
    print(f"Reading CSV from: {csv_file_path}")
    print(f"Output will be saved to: {output_file_path}")
    
    # Initialize geocoding service
    geocoding_service = StandaloneGeocodingService()
    
    # Check if API key is available
    if not geocoding_service.google_api_key:
        print("ERROR: Google Geocoding API key not found in environment variables")
        print("Please set GOOGLE_GEOCODING_API_KEY or GOOGLE_FLOOD_HUB_API_KEY")
        return
    
    print("API key found, starting geocoding process...")
    
    # Read and process CSV
    processed_rows = []
    header_updated = False
    gauge_count = 0
    # max_gauges = 50  # Limit for testing - REMOVED TO PROCESS ALL
    
    with open(csv_file_path, 'r', encoding='utf-8-sig') as file:
        reader = csv.reader(file)
        
        for row_num, row in enumerate(reader):
            if row_num < 4:  # Skip header rows
                processed_rows.append(row)
                continue
                
            if row_num == 4:  # Header row with column names
                # Add new columns for administrative boundaries
                if len(row) >= 7:  # Make sure we have enough columns
                    # Insert new columns after longitude (column 7)
                    row.insert(8, 'Province')
                    row.insert(9, 'District') 
                    row.insert(10, 'Tehsil')
                    row.insert(11, 'UC')
                processed_rows.append(row)
                header_updated = True
                continue
            
            # Process data rows
            if len(row) >= 7 and row[1]:  # Make sure we have gauge data
                gauge_id = row[1]
                gauge_count += 1
                
                # Removed gauge limit - processing all gauges
                
                try:
                    # Extract latitude and longitude
                    latitude = float(row[5]) if row[5] else None
                    longitude = float(row[7]) if row[7] else None
                    
                    if latitude and longitude:
                        print(f"[{gauge_count}] Processing gauge {gauge_id} at ({latitude}, {longitude})")
                        
                        # Add delay to respect API rate limits
                        time.sleep(0.05)
                        
                        # Get administrative boundaries
                        boundaries = geocoding_service.get_admin_boundaries(latitude, longitude)
                        
                        # Insert the boundary data after longitude column
                        row.insert(8, boundaries.get('province', ''))
                        row.insert(9, boundaries.get('district', ''))
                        row.insert(10, boundaries.get('tehsil', ''))
                        row.insert(11, boundaries.get('union_council', ''))
                        
                        print(f"  -> {boundaries.get('province')}, {boundaries.get('district')}, {boundaries.get('tehsil')}, {boundaries.get('union_council')}")
                    else:
                        # No coordinates, add empty columns
                        row.insert(8, '')
                        row.insert(9, '')
                        row.insert(10, '')
                        row.insert(11, '')
                        print(f"[{gauge_count}] Gauge {gauge_id} has no coordinates")
                        
                except (ValueError, IndexError) as e:
                    print(f"Error processing gauge {gauge_id}: {e}")
                    # Add empty columns on error
                    row.insert(8, '')
                    row.insert(9, '')
                    row.insert(10, '')
                    row.insert(11, '')
            else:
                # Empty or invalid row, add empty columns if header was updated
                if header_updated and len(row) >= 7:
                    row.insert(8, '')
                    row.insert(9, '')
                    row.insert(10, '')
                    row.insert(11, '')
            
            processed_rows.append(row)
    
    # Write the updated CSV
    with open(output_file_path, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerows(processed_rows)
    
    print(f"\nProcessing complete! Updated CSV saved to: {output_file_path}")
    print(f"Added Province, District, Tehsil, and UC columns to {len(processed_rows) - 5} gauge records")

if __name__ == '__main__':
    main()