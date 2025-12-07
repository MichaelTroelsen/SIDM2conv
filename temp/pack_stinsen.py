#!/usr/bin/env python3
"""Pack Stinsen SF2 file to verify Wave table packing fix."""

from pathlib import Path
from sidm2.sf2_packer import pack_sf2_to_sid

# Input and output paths
sf2_path = Path("learnings/Stinsen - Last Night Of 89.sf2")
sid_path = Path("SIDSF2player/SF2packed_new_Stiensens_last_night_of_89.sid")

# Pack the SF2 file
print(f"Packing: {sf2_path}")
print(f"Output: {sid_path}")

success = pack_sf2_to_sid(
    sf2_path=sf2_path,
    sid_path=sid_path,
    name="Stinsen Last Night 89",
    author="Stinsen",
    copyright_str="Repacked for Wave table test"
)

if success:
    print(f"\nSuccess! Created: {sid_path}")
    print(f"File size: {sid_path.stat().st_size:,} bytes")
else:
    print("\nPacking failed!")
