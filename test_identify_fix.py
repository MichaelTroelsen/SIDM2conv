#!/usr/bin/env python3
"""Test the fixed identify_sid_type function."""

import sys
import os
import struct
import subprocess

sys.path.insert(0, os.path.dirname(__file__))

from complete_pipeline_with_validation import identify_sid_type

# Test the 4 files that were showing 0% accuracy
test_files = [
    "SIDSF2player/Aint_Somebody.sid",
    "SIDSF2player/Expand_Side_1.sid",
    "SIDSF2player/Halloweed_4_tune_3.sid",
    "SIDSF2player/Cocktail_to_Go_tune_3.sid",
]

print("Testing fixed identify_sid_type() function:")
print("="*80)

for filepath in test_files:
    if os.path.exists(filepath):
        file_type = identify_sid_type(filepath)
        print(f"{filepath:45} -> {file_type}")
    else:
        print(f"{filepath:45} -> FILE NOT FOUND")

print("\n" + "="*80)
print("Expected: All should return 'LAXITY'")
print("This will enable LAXITY conversion instead of TEMPLATE conversion!")
