#!/usr/bin/env python3
"""Test player detection for 0% accuracy files."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from scripts.sid_to_sf2 import detect_player_type

# Test the 0% accuracy files
test_files = [
    "SIDSF2player/Aint_Somebody.sid",
    "SIDSF2player/Expand_Side_1.sid",
    "SIDSF2player/Halloweed_4_tune_3.sid",
    "SIDSF2player/Cocktail_to_Go_tune_3.sid",
]

print("Testing player detection:")
print("="*80)

for filepath in test_files:
    if os.path.exists(filepath):
        player_type = detect_player_type(filepath)
        print(f"{filepath:45} -> {player_type}")
    else:
        print(f"{filepath:45} -> FILE NOT FOUND")

print("\n" + "="*80)
print("Expected: All should detect as 'SidFactory_II/Laxity' or similar")
print("If showing 'Unknown', player detection is failing!")
