#!/usr/bin/env python3
"""
Download the latest GTFS static dataset from PTV.
This script downloads the 242MB GTFS schedule dataset.
"""

import requests
import sys
import os
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# GTFS Schedule dataset URL
GTFS_URL = "https://data.ptv.vic.gov.au/downloads/gtfs.zip"

def download_gtfs(output_path: str = "../data/gtfs.zip"):
    """Download GTFS dataset with progress indication."""
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Downloading GTFS dataset from: {GTFS_URL}")
    print(f"Output: {output_file.absolute()}")
    
    try:
        response = requests.get(GTFS_URL, stream=True, timeout=300)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192
        downloaded = 0
        
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\rProgress: {progress:.1f}% ({downloaded / 1024 / 1024:.1f} MB)", end='')
        
        print(f"\n✓ Download complete: {output_file}")
        print(f"  File size: {downloaded / 1024 / 1024:.1f} MB")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Download failed: {e}", file=sys.stderr)
        if output_file.exists():
            output_file.unlink()
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}", file=sys.stderr)
        if output_file.exists():
            output_file.unlink()
        return False

if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "../data/gtfs.zip"
    success = download_gtfs(output)
    sys.exit(0 if success else 1)
