#!/usr/bin/env python3
"""
Extract gauge IDs and details from the CSV file and create a JSON file for import.
"""

import csv
import json
import os
from pathlib import Path

def extract_gauge_data():
    """Extract gauge data from CSV and save as JSON."""
    
    # Paths
    csv_path = Path(__file__).parent.parent / "docs" / "Flood alerts 7 day monitoring(Flood alerts 7 day monitoring).csv"
    json_path = Path(__file__).parent.parent / "docs" / "pakistan_gauges.json"
    
    print(f"Reading CSV from: {csv_path}")
    print(f"Will save JSON to: {json_path}")
    
    gauges = []
    
    with open(csv_path, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile)
        
        # Skip header rows (first 4 rows are metadata)
        for i in range(4):
            next(reader, None)
        
        for row_num, row in enumerate(reader, start=5):
            if len(row) < 8:  # Skip incomplete rows
                continue
                
            # Extract gauge data from row
            # Format: [empty, gauge_id, empty, quality_verified, unit, latitude, empty, longitude, ...]
            try:
                gauge_id = row[1].strip()
                if not gauge_id:  # Skip empty gauge IDs
                    continue
                    
                quality_verified = row[3].strip().lower() == 'true'
                unit = row[4].strip()
                latitude = float(row[5].strip()) if row[5].strip() else None
                longitude = float(row[7].strip()) if row[7].strip() else None
                
                # Extract threshold levels
                warning_level = float(row[8].strip()) if row[8].strip() else None
                danger_level = float(row[9].strip()) if row[9].strip() else None
                extreme_danger_level = float(row[10].strip()) if row[10].strip() else None
                
                gauge_data = {
                    "gauge_id": gauge_id,
                    "quality_verified": quality_verified,
                    "unit": unit,
                    "latitude": latitude,
                    "longitude": longitude,
                    "warning_level": warning_level,
                    "danger_level": danger_level,
                    "extreme_danger_level": extreme_danger_level,
                    "country_code": "PK",
                    "source": "GOOGLE_FLOOD_HUB",
                    "status": "active"
                }
                
                gauges.append(gauge_data)
                
            except (ValueError, IndexError) as e:
                print(f"Error processing row {row_num}: {e}")
                continue
    
    print(f"Extracted {len(gauges)} gauges")
    
    # Save as JSON
    with open(json_path, 'w', encoding='utf-8') as jsonfile:
        json.dump(gauges, jsonfile, indent=2, ensure_ascii=False)
    
    print(f"Saved gauge data to {json_path}")
    
    # Show some statistics
    quality_verified_count = sum(1 for g in gauges if g['quality_verified'])
    print(f"\nStatistics:")
    print(f"Total gauges: {len(gauges)}")
    print(f"Quality verified: {quality_verified_count}")
    print(f"Not quality verified: {len(gauges) - quality_verified_count}")
    
    # Show sample of gauge IDs
    print(f"\nSample gauge IDs:")
    for i, gauge in enumerate(gauges[:10]):
        print(f"  {i+1}. {gauge['gauge_id']} (lat: {gauge['latitude']}, lon: {gauge['longitude']})")
    
    return gauges

if __name__ == "__main__":
    gauges = extract_gauge_data()