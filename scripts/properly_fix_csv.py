#!/usr/bin/env python3
"""
Properly fix the CSV by reprocessing from the original
"""

import csv
from pathlib import Path

def fix_csv_properly():
    """Fix the CSV by properly inserting geocoding columns."""
    
    # File paths
    original_file = Path(__file__).parent.parent / 'docs' / 'Flood alerts 7 day monitoring(Flood alerts 7 day monitoring).csv'
    backup_file = Path(__file__).parent.parent / 'docs' / 'Flood_alerts_with_geocoding.csv.backup'
    output_file = Path(__file__).parent.parent / 'docs' / 'Flood_alerts_with_geocoding.csv'
    
    print(f"Reading original from: {original_file}")
    print(f"Reading geocoded backup from: {backup_file}")
    print(f"Writing fixed file to: {output_file}")
    
    # Read original structure
    original_rows = []
    with open(original_file, 'r', encoding='utf-8-sig') as file:
        reader = csv.reader(file)
        for row in reader:
            original_rows.append(row)
    
    # Read geocoded data
    geocoded_rows = []
    with open(backup_file, 'r', encoding='utf-8-sig') as file:
        reader = csv.reader(file)
        for row in reader:
            geocoded_rows.append(row)
    
    # Process and fix
    fixed_rows = []
    
    # Copy first 3 rows as-is
    for i in range(3):
        fixed_rows.append(original_rows[i])
    
    # Fix header row (row 4, index 3)
    header_row = original_rows[3].copy()
    # Insert geocoding headers after Longitude (column 7)
    header_row.insert(8, 'Province')
    header_row.insert(9, 'District')
    header_row.insert(10, 'Tehsil')
    header_row.insert(11, 'UC')
    fixed_rows.append(header_row)
    
    # Process data rows
    for i in range(4, len(original_rows)):
        if i < len(geocoded_rows):
            # Get geocoded data from backup
            geocoded_row = geocoded_rows[i]
            original_row = original_rows[i].copy()
            
            # Extract geocoding data (should be at positions 8-11 in geocoded file)
            if len(geocoded_row) > 11:
                province = geocoded_row[8] if geocoded_row[8] != 'Province' else ''
                district = geocoded_row[9] if geocoded_row[9] != 'District' else ''
                tehsil = geocoded_row[10] if geocoded_row[10] != 'Tehsil' else ''
                uc = geocoded_row[11] if geocoded_row[11] != 'UC' else ''
                
                # Insert into original row structure
                original_row.insert(8, province)
                original_row.insert(9, district)
                original_row.insert(10, tehsil)
                original_row.insert(11, uc)
            else:
                # No geocoding data, insert empty values
                original_row.insert(8, '')
                original_row.insert(9, '')
                original_row.insert(10, '')
                original_row.insert(11, '')
                
            fixed_rows.append(original_row)
        else:
            # No geocoded data for this row
            fixed_rows.append(original_rows[i])
    
    # Write the properly fixed CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerows(fixed_rows)
    
    print("CSV properly fixed!")
    
    # Verify the fix
    print("\nVerifying first few rows:")
    with open(output_file, 'r', encoding='utf-8-sig') as file:
        reader = csv.reader(file)
        for i, row in enumerate(reader):
            if i < 6:
                if i == 3:  # Header row
                    print(f"Row {i+1} (headers): ...{row[6]}, {row[7]}, {row[8]}, {row[9]}, {row[10]}, {row[11]}, {row[12]}...")
                elif i >= 4:  # Data rows
                    print(f"Row {i+1} (data): ...{row[6]}, {row[7]}, {row[8]}, {row[9]}, {row[10]}, {row[11]}, {row[12]}...")
            else:
                break

if __name__ == '__main__':
    fix_csv_properly()