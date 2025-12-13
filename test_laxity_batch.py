#!/usr/bin/env python3
"""
Test Laxity driver with multiple files
"""

import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.sid_to_sf2 import convert_sid_to_sf2

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

# Test files (known Laxity format)
test_files = [
    "SID/Stinsens_Last_Night_of_89.sid",
    "SID/Beast.sid",
    "SID/Dreams.sid",
]

output_dir = "output/test_laxity_batch"
os.makedirs(output_dir, exist_ok=True)

print("=" * 80)
print("LAXITY DRIVER BATCH CONVERSION TEST")
print("=" * 80)
print()

results = []

for sid_file in test_files:
    if not os.path.exists(sid_file):
        print(f"SKIP: {sid_file} (not found)")
        continue

    base_name = os.path.splitext(os.path.basename(sid_file))[0]
    output_file = os.path.join(output_dir, f"{base_name}_laxity.sf2")

    print(f"Converting: {base_name}")
    print(f"  Input:  {sid_file}")
    print(f"  Output: {output_file}")

    try:
        # Remove existing file
        if os.path.exists(output_file):
            os.remove(output_file)

        # Convert with Laxity driver
        convert_sid_to_sf2(sid_file, output_file, driver_type='laxity')

        # Check result
        if os.path.exists(output_file):
            size = os.path.getsize(output_file)
            print(f"  Result: SUCCESS ({size:,} bytes)")
            results.append({
                'file': base_name,
                'status': 'SUCCESS',
                'size': size
            })
        else:
            print(f"  Result: FAILED (no output file)")
            results.append({
                'file': base_name,
                'status': 'FAILED',
                'error': 'No output file'
            })

    except Exception as e:
        print(f"  Result: ERROR - {e}")
        results.append({
            'file': base_name,
            'status': 'ERROR',
            'error': str(e)
        })

    print()

# Summary
print("=" * 80)
print("CONVERSION SUMMARY")
print("=" * 80)
print()

success_count = sum(1 for r in results if r['status'] == 'SUCCESS')
total_count = len(results)

for result in results:
    status_symbol = "+" if result['status'] == 'SUCCESS' else "X"
    if result['status'] == 'SUCCESS':
        print(f"  {status_symbol} {result['file']:<30} {result['size']:>8,} bytes")
    else:
        error = result.get('error', 'Unknown error')
        print(f"  {status_symbol} {result['file']:<30} {error}")

print()
print(f"Success Rate: {success_count}/{total_count} ({100*success_count//total_count if total_count > 0 else 0}%)")
print("=" * 80)
