#!/usr/bin/env python3
"""
Fix the CSV headers - move Province, District, Tehsil, UC from data row to header row
"""

import csv
from pathlib import Path

def fix_headers():
    """Fix the header row in the CSV file."""
    
    # File paths
    input_file = Path(__file__).parent.parent / 'docs' / 'Flood_alerts_with_geocoding.csv'
    output_file = Path(__file__).parent.parent / 'docs' / 'Flood_alerts_with_geocoding_fixed.csv'
    
    print(f"Reading from: {input_file}")
    print(f"Writing to: {output_file}")
    
    rows = []
    
    # Read the CSV file
    with open(input_file, 'r', encoding='utf-8-sig') as file:
        reader = csv.reader(file)
        for row in reader:
            rows.append(row)
    
    # Fix row 4 (index 3) - the header row
    # Currently has the geographic headers in the wrong place
    if len(rows) > 4:
        header_row = rows[3]
        
        # Find where to insert the headers (after Longitude column - position 7)
        # Insert the column headers
        if len(header_row) > 7:
            # Remove any existing entries at positions 8-11 if they exist
            # Insert proper headers
            header_row[8:12] = ['Province', 'District', 'Tehsil', 'UC']
    
    # Fix row 5 (index 4) - first data row
    # Currently has "Province", "District", "Tehsil", "UC" as data
    if len(rows) > 4:
        first_data_row = rows[4]
        if len(first_data_row) > 11 and first_data_row[8] == 'Province':
            # This row has the headers as data, need to replace with empty values
            # since this gauge doesn't have geocoding data
            first_data_row[8:12] = ['', '', '', '']
    
    # Write the corrected CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerows(rows)
    
    print("Headers fixed successfully!")
    
    # Rename files to replace original
    import shutil
    backup_file = input_file.with_suffix('.csv.backup')
    shutil.move(input_file, backup_file)
    shutil.move(output_file, input_file)
    print(f"Original file backed up to: {backup_file}")
    print(f"Fixed file saved as: {input_file}")

if __name__ == '__main__':
    fix_headers()