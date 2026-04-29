#!/usr/bin/env python3
"""
Test the fixed player detection logic.
"""

import struct
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyscript.complete_pipeline_with_validation import identify_sid_type

# Test files
test_files = [
    'SIDSF2player/Stinsens_Last_Night_of_89.sid',                  # Laxity original
    'SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid',       # SF2-packed with Laxity code
    'SIDSF2player/test_broware_packed_only.sid',                  # SF2-packed with SF2 driver
    'SIDSF2player/Broware.sid',                                   # Laxity original
]

print("=" * 80)
print("PLAYER DETECTION TEST - After Fix")
print("=" * 80)
print()

for sid_file in test_files:
    sid_path = Path(sid_file)

    if not sid_path.exists():
        print(f"[SKIP] {sid_file}: FILE NOT FOUND")
        continue

    # Get headers
    with open(sid_path, 'rb') as f:
        data = f.read()

    load_addr = struct.unpack('>H', data[8:10])[0]
    init_addr = struct.unpack('>H', data[10:12])[0]
    play_addr = struct.unpack('>H', data[12:14])[0]

    # Test detection
    detected_type = identify_sid_type(sid_path)

    # Expected types
    expected = {
        'Stinsens_Last_Night_of_89.sid': 'LAXITY',                   # play=$1006 → LAXITY
        'SF2packed_Stinsens_Last_Night_of_89.sid': 'LAXITY',        # play=$1006 → LAXITY (has Laxity code)
        'test_broware_packed_only.sid': 'SF2_PACKED',               # play=$1003 → SF2_PACKED (SF2 driver)
        'Broware.sid': 'LAXITY',                                     # play=$A006 → LAXITY
    }

    expected_type = expected.get(sid_path.name, 'UNKNOWN')
    status = "[OK]" if detected_type == expected_type else "[FAIL]"

    print(f"{status} {sid_path.name}")
    print(f"   Headers: init=${init_addr:04X}, play=${play_addr:04X}")
    print(f"   Expected: {expected_type}")
    print(f"   Detected: {detected_type}")

    if detected_type != expected_type:
        print(f"   [WARNING] MISMATCH!")

    print()

print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)
