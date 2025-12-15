#!/usr/bin/env python3
"""Detailed analysis of SF2Reader block detection"""

from pathlib import Path
from sidm2.sf2_reader import SF2Reader

sf2_path = Path("output/SIDSF2player_Complete_Pipeline/Broware/New/Broware.sf2")

print("="*80)
print("SF2READER BLOCK DETECTION")
print("="*80)

with open(sf2_path, 'rb') as f:
    sf2_data = f.read()

# Load address from file
load_addr = int.from_bytes(sf2_data[0:2], 'little')

print(f"\nFile structure:")
print(f"  Load address: ${load_addr:04X}")
print(f"  Magic ID: ${int.from_bytes(sf2_data[2:4], 'little'):04X}")
print(f"  File size: {len(sf2_data)} bytes")

# Create reader
reader = SF2Reader(sf2_data, load_addr)

print(f"\nBlocks found by SF2Reader:")
if reader.block_offsets:
    for block_type, (offset, size) in sorted(reader.block_offsets.items()):
        block_name = {
            0x01: "DESCRIPTOR",
            0x02: "DRIVER_COMMON",
            0x03: "DRIVER_TABLES",
            0x04: "INSTRUMENT_DESC",
            0x05: "MUSIC_DATA",
            0xFF: "END"
        }.get(block_type, "UNKNOWN")
        print(f"  Block 0x{block_type:02X} ({block_name:16s}): offset {offset:5d}, size {size:5d} bytes")

        # Show first 32 bytes of block
        block_data = sf2_data[offset:offset+min(32, size)]
        print(f"    First bytes: {' '.join(f'{b:02x}' for b in block_data)}")
else:
    print(f"  (no blocks found)")

# Try extracting data
print(f"\nExtraction attempts:")

sequences = reader.extract_sequences()
print(f"  Sequences: {len(sequences)} found")
if sequences:
    for i, seq in enumerate(sequences[:3]):
        print(f"    [{i}] {len(seq)} bytes: {' '.join(f'{b:02x}' for b in seq[:20])}...")

instruments = reader.extract_instruments()
print(f"  Instruments: {len(instruments)} found")
if instruments:
    for i, instr in enumerate(instruments[:3]):
        print(f"    [{i}] {len(instr)} bytes: {' '.join(f'{b:02x}' for b in instr)}")

print(f"\n" + "="*80)
