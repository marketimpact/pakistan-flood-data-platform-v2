#!/usr/bin/env python3
"""
Fix missing geocoding data in the CSV by processing only entries without location data
"""

import csv
import os
import requests
import time
from pathlib import Path

class GeocodingFixer:
    def __init__(self):
        self.api_key = os.environ.get('GOOGLE_GEOCODING_API_KEY', 'AIzaSyCu8yng-tY0vS-KtPVUcs4vKtOVmsNEEUc')
        self.processed_count = 0
        self.fixed_count = 0
        self.failed_count = 0
        
    def geocode_location(self, lat, lng):
        """Geocode a single location with retry logic."""
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        
        # Try without filter first for better results
        params = {
            'latlng': f"{lat},{lng}",
            'key': self.api_key,
            'language': 'en'
        }
        
        for attempt in range(3):  # 3 attempts
            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if data['status'] == 'OK' and data['results']:
                    return self.parse_response(data['results'])
                elif data['status'] == 'ZERO_RESULTS':
                    # Try with administrative filter
                    params['result_type'] = 'administrative_area_level_1|administrative_area_level_2|administrative_area_level_3|administrative_area_level_4|locality'
                    response = requests.get(url, params=params, timeout=10)
                    data = response.json()
                    if data['status'] == 'OK' and data['results']:
                        return self.parse_response(data['results'])
                    return {'province': None, 'district': None, 'tehsil': None, 'uc': None}
                elif data['status'] == 'OVER_QUERY_LIMIT':
                    time.sleep(2)  # Wait longer on rate limit
                    continue
                else:
                    print(f"  API error: {data.get('status')}")
                    return {'province': None, 'district': None, 'tehsil': None, 'uc': None}
                    
            except Exception as e:
                print(f"  Request error (attempt {attempt+1}): {e}")
                time.sleep(1)
                
        return {'province': None, 'district': None, 'tehsil': None, 'uc': None}
    
    def parse_response(self, results):
        """Parse Google geocoding response."""
        boundaries = {
            'province': None,
            'district': None, 
            'tehsil': None,
            'uc': None
        }
        
        # Check all results for administrative info
        for result in results:
            for component in result.get('address_components', []):
                types = component.get('types', [])
                name = component.get('long_name')
                
                if 'administrative_area_level_1' in types and not boundaries['province']:
                    boundaries['province'] = name
                elif 'administrative_area_level_2' in types and not boundaries['district']:
                    boundaries['district'] = name
                elif 'administrative_area_level_3' in types and not boundaries['tehsil']:
                    boundaries['tehsil'] = name
                elif 'administrative_area_level_4' in types and not boundaries['uc']:
                    boundaries['uc'] = name
                elif 'locality' in types and not boundaries['uc']:
                    # Sometimes UC/locality info is here
                    if not boundaries['tehsil']:
                        boundaries['tehsil'] = name
                    
        return boundaries
    
    def process_csv(self):
        """Process the CSV and fix missing geocoding data."""
        csv_path = Path(__file__).parent.parent / 'docs' / 'Flood_alerts_with_geocoding.csv'
        output_path = Path(__file__).parent.parent / 'docs' / 'Flood_alerts_comprehensive.csv'
        
        print(f"Reading from: {csv_path}")
        print(f"Will save to: {output_path}")
        
        # Read CSV
        rows = []
        with open(csv_path, 'r', encoding='utf-8-sig') as file:
            reader = csv.reader(file)
            rows = list(reader)
        
        print(f"\nTotal rows: {len(rows)}")
        
        # Find rows with missing geocoding data
        missing_data_rows = []
        for i in range(4, len(rows)):  # Start after headers
            row = rows[i]
            if len(row) > 11:
                # Check if all geocoding fields are empty
                if not any([row[8], row[9], row[10], row[11]]):
                    if len(row) > 7 and row[5] and row[7]:  # Has lat/lng
                        missing_data_rows.append(i)
        
        print(f"Found {len(missing_data_rows)} rows with missing geocoding data")
        
        # Process missing entries
        for idx, row_num in enumerate(missing_data_rows):
            row = rows[row_num]
            try:
                gauge_id = row[1]
                lat = float(row[5]) if row[5] else None
                lng = float(row[7]) if row[7] else None
                
                if lat and lng:
                    print(f"\n[{idx+1}/{len(missing_data_rows)}] Processing {gauge_id} at ({lat}, {lng})")
                    
                    # Add small delay to respect rate limits
                    time.sleep(0.1)
                    
                    # Get geocoding data
                    result = self.geocode_location(lat, lng)
                    
                    # Update row
                    row[8] = result['province'] or ''
                    row[9] = result['district'] or ''
                    row[10] = result['tehsil'] or ''
                    row[11] = result['uc'] or ''
                    
                    if any([result['province'], result['district'], result['tehsil']]):
                        print(f"  ✓ Fixed: {result['province']}, {result['district']}, {result['tehsil']}, {result['uc']}")
                        self.fixed_count += 1
                    else:
                        print(f"  ✗ No data available")
                        self.failed_count += 1
                        
                    self.processed_count += 1
                    
            except Exception as e:
                print(f"  Error processing row {row_num}: {e}")
                self.failed_count += 1
        
        # Also check for entries that might have partial data
        print("\n\nChecking for entries with partial geocoding data...")
        partial_count = 0
        
        for i in range(4, len(rows)):
            row = rows[i]
            if len(row) > 11 and i not in missing_data_rows:
                # Check if has coordinates but missing some admin levels
                if row[5] and row[7]:  # Has coordinates
                    has_province = bool(row[8])
                    has_district = bool(row[9])
                    
                    # If has province but missing district/tehsil, try to enhance
                    if has_province and not has_district:
                        try:
                            lat = float(row[5])
                            lng = float(row[7])
                            gauge_id = row[1]
                            
                            print(f"\nEnhancing {gauge_id} (currently only has province: {row[8]})")
                            time.sleep(0.1)
                            
                            result = self.geocode_location(lat, lng)
                            
                            # Only update if we got better data
                            if result['district']:
                                row[9] = result['district'] or row[9]
                                row[10] = result['tehsil'] or row[10]
                                row[11] = result['uc'] or row[11]
                                print(f"  ✓ Enhanced: Added {result['district']}, {result['tehsil']}")
                                partial_count += 1
                                
                        except Exception as e:
                            print(f"  Error enhancing row: {e}")
        
        # Write comprehensive CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(rows)
        
        # Summary
        print("\n" + "="*60)
        print("GEOCODING COMPLETE!")
        print(f"Processed: {self.processed_count} missing entries")
        print(f"Fixed: {self.fixed_count}")
        print(f"Enhanced: {partial_count}")
        print(f"Failed (no data available): {self.failed_count}")
        print(f"\nComprehensive file saved to: {output_path}")
        
        # Final statistics
        total_with_data = 0
        total_complete = 0
        
        for i in range(4, len(rows)):
            row = rows[i]
            if len(row) > 11 and row[5] and row[7]:  # Has coordinates
                if any([row[8], row[9], row[10], row[11]]):
                    total_with_data += 1
                    if all([row[8], row[9], row[10]]):  # Has province, district, tehsil
                        total_complete += 1
        
        print(f"\nFinal statistics:")
        print(f"Total gauges with coordinates: {len(rows) - 4}")
        print(f"Gauges with some geocoding data: {total_with_data}")
        print(f"Gauges with complete admin hierarchy: {total_complete}")

if __name__ == '__main__':
    fixer = GeocodingFixer()
    fixer.process_csv()