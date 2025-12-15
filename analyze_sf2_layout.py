#!/usr/bin/env python3
"""Analyze the physical layout of the Broware SF2 file"""

from pathlib import Path
import struct

sf2_path = Path("output/SIDSF2player_Complete_Pipeline/Broware/New/Broware.sf2")

with open(sf2_path, 'rb') as f:
    sf2_data = f.read()

print("="*80)
print("SF2 FILE PHYSICAL LAYOUT")
print("="*80)

# Get load address
load_addr = struct.unpack('<H', sf2_data[0:2])[0]
c64_data = sf2_data[2:]

print(f"\nLoad address (first 2 bytes): ${load_addr:04X}")
print(f"File data size: {len(c64_data):,} bytes")
print(f"File will be loaded from ${load_addr:04X} to ${load_addr + len(c64_data):04X}")

# When this is loaded into a 64K address space starting at load_addr,
# what happens at other addresses?

# If load_addr is 0x0D7E and we have ~13K of data:
# We'll fill memory from 0x0D7E to 0x0D7E + 13000

# But the code expects data to also be at 0x1000
# For this to work, there must be data in the SF2 file that maps to 0x1000

# When the SF2 is loaded:
# - Memory starting at 0x0D7E gets the first (0x1000 - 0x0D7E) bytes of the SF2 data
# - Memory starting at 0x1000 gets bytes from offset (0x1000 - 0x0D7E) onwards

offset_to_1000 = 0x1000 - load_addr  # How many bytes into the SF2 file is code at $1000?

print(f"\nMemory mapping:")
print(f"  SF2 byte 0-1: Load address (${ load_addr:04X})")
print(f"  SF2 byte 2 onwards: C64 data")
print(f"  C64 data byte 0 maps to memory ${load_addr:04X}")
print(f"  C64 data byte {offset_to_1000} maps to memory $1000")

if offset_to_1000 < len(c64_data):
    print(f"\n  [YES] The SF2 file IS large enough to have data at $1000")
    print(f"  Code at $1000 comes from SF2 file offset 2 + {offset_to_1000} = {offset_to_1000 + 2}")
else:
    print(f"\n  [NO] The SF2 file is TOO SMALL to have data at $1000")
    print(f"  We need at least {offset_to_1000 + 2} bytes, but file has {len(sf2_data)} bytes")

# Show what's at key addresses
print(f"\nData at key file offsets:")
print(f"  SF2[0:2] (load addr): {struct.unpack('<H', sf2_data[0:2])[0]:04x}")
print(f"  SF2[2:18] (start of C64 data): {' '.join(f'{b:02x}' for b in sf2_data[2:18])}")

if offset_to_1000 + 2 < len(sf2_data):
    print(f"  SF2[{offset_to_1000+2}:{offset_to_1000+18}] (code at $1000): {' '.join(f'{b:02x}' for b in sf2_data[offset_to_1000+2:offset_to_1000+18])}")

print(f"\nKey insight:")
print(f"  The SF2 file is a PRG file that, when loaded by the C64,")
print(f"  places the ENTIRE data starting at ${load_addr:04X}.")
print(f"  This means data meant for different addresses is concatenated in the file.")
print(f"  - Bytes 0-{offset_to_1000-1} are for address ${load_addr:04X}")
print(f"  - Bytes {offset_to_1000} onward are for address $1000 and beyond")
