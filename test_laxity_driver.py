#!/usr/bin/env python3
"""
Test Laxity driver integration
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.sid_to_sf2 import convert_sid_to_sf2

# Test with a Laxity SID file
input_sid = "SID/Stinsens_Last_Night_of_89.sid"
output_sf2 = "output/test_laxity/test_laxity.sf2"

# Ensure output directory exists
os.makedirs(os.path.dirname(output_sf2), exist_ok=True)

print("=" * 70)
print("TESTING LAXITY DRIVER INTEGRATION")
print("=" * 70)
print(f"Input:  {input_sid}")
print(f"Output: {output_sf2}")
print()

try:
    convert_sid_to_sf2(input_sid, output_sf2, driver_type='laxity')
    print()
    print("=" * 70)
    print("SUCCESS - Laxity driver conversion completed!")
    print("=" * 70)

    # Show file size
    if os.path.exists(output_sf2):
        size = os.path.getsize(output_sf2)
        print(f"Output file size: {size:,} bytes")

except Exception as e:
    print()
    print("=" * 70)
    print(f"ERROR: {e}")
    print("=" * 70)
    import traceback
    traceback.print_exc()
    sys.exit(1)
