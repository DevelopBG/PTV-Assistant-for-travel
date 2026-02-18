#!/usr/bin/env python3
"""
Extract and merge all GTFS feeds from PTV GTFS ZIP.
"""

import zipfile
import csv
import shutil
from pathlib import Path
from collections import defaultdict

def extract_all_gtfs(gtfs_zip_path: str, output_dir: str):
    """Extract and merge all GTFS feeds."""
    
    gtfs_zip = Path(gtfs_zip_path)
    output = Path(output_dir)
    
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    
    temp_dir = output / "_temp"
    temp_dir.mkdir()
    
    print("Extracting All GTFS Feeds from PTV")
    print("=" * 80)
    
    with zipfile.ZipFile(gtfs_zip, 'r') as main_zip:
        transit_zips = [f for f in main_zip.namelist() if f.endswith('google_transit.zip')]
        
        # Collect all data
        all_data = defaultdict(lambda: {'headers': set(), 'rows': []})
        
        for i, transit_zip in enumerate(transit_zips, 1):
            route_type = transit_zip.split('/')[0]
            print(f"[{i}/{len(transit_zips)}] Route type {route_type}...", end=' ')
            
            main_zip.extract(transit_zip, temp_dir)
            transit_zip_path = temp_dir / transit_zip
            
            route_dir = temp_dir / f"route_{route_type}"
            route_dir.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(transit_zip_path, 'r') as tz:
                tz.extractall(route_dir)
            
            row_count = 0
            for txt_file in route_dir.glob('*.txt'):
                filename = txt_file.name
                
                with open(txt_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    row_count += len(rows)
                    
                    all_data[filename]['headers'].update(reader.fieldnames or [])
                    all_data[filename]['rows'].extend(rows)
            
            print(f"{row_count:,} rows")
        
        print()
        print("Merging & Writing...")
        print("=" * 80)
        
        for filename, data in sorted(all_data.items()):
            output_file = output / filename
            headers = sorted(data['headers'])
            
            if not data['rows']:
                continue
            
            # Remove duplicates - use ALL fields as key for safety
            seen = set()
            unique_rows = []
            
            for row in data['rows']:
                complete_row = {h: row.get(h, '') for h in headers}
                
                # Create tuple of all values as key
                key = tuple(complete_row[h] for h in headers)
                
                if key not in seen:
                    seen.add(key)
                    unique_rows.append(complete_row)
            
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(unique_rows)
            
            print(f"✓ {filename:25} {len(unique_rows):>10,} rows")
        
        shutil.rmtree(temp_dir)
        print()
        print(f"✅ Complete: {output}")

if __name__ == "__main__":
    extract_all_gtfs('data/gtfs.zip', 'data/gtfs')
