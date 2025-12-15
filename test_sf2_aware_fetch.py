#!/usr/bin/env python3
"""Test the new SF2-aware fetch_driver_code() implementation"""

from pathlib import Path
from sidm2.sf2_packer import SF2Packer

sf2_path = Path("output/SIDSF2player_Complete_Pipeline/Broware/New/Broware.sf2")

print("="*80)
print("TESTING SF2-AWARE FETCH_DRIVER_CODE()")
print("="*80)

packer = SF2Packer(sf2_path)

print(f"\nLoading SF2 file: {sf2_path.name}")
print(f"  Load address: ${packer.load_address:04X}")
print(f"  File size: {len(packer.memory)} bytes")

# Check if SF2 format is detected
print(f"\nChecking for SF2 format:")
is_sf2 = packer._is_sf2_format()
if is_sf2:
    print(f"  [YES] SF2 format detected!")
    magic_id = packer._read_word(packer.load_address + 2)
    print(f"  Magic ID: 0x{magic_id:04X}")
else:
    print(f"  [NO] Not SF2 format")

# Now call fetch_driver_code()
print(f"\nCalling fetch_driver_code():")
packer.fetch_driver_code()

print(f"\nExtraction results:")
print(f"  Total sections extracted: {len(packer.data_sections)}")

for i, section in enumerate(packer.data_sections):
    section_type = "CODE" if section.is_code else "DATA"
    print(f"  [{i}] {section_type:4s} ${section.source_address:04X} ({len(section.data):5d} bytes)")

# Check first code section (most important)
if packer.data_sections and packer.data_sections[0].is_code:
    first_code = packer.data_sections[0]
    print(f"\nFirst code section analysis:")
    print(f"  Address: ${first_code.source_address:04X}")
    print(f"  Size: {len(first_code.data)} bytes")

    # Show first 32 bytes
    first_bytes = first_code.data[:32]
    print(f"  First 32 bytes: {' '.join(f'{b:02x}' for b in first_bytes)}")

    # Check if they look like valid 6502 code
    from sidm2.cpu6502 import INSTRUCTION_SIZES
    valid_opcodes = sum(1 for b in first_bytes if INSTRUCTION_SIZES[b] > 0)
    print(f"  Valid 6502 opcodes: {valid_opcodes}/{len(first_bytes)}")

print(f"\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
