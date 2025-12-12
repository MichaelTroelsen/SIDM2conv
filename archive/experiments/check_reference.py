#!/usr/bin/env python3
"""Check the reference SF2 file"""
import struct

# Check the reference file
filepath = "learnings/Stinsen - Last Night Of 89.sf2"
print(f"Checking REFERENCE: {filepath}")
print()

with open(filepath, 'rb') as f:
    ref_data = f.read()

load_addr = struct.unpack('<H', ref_data[0:2])[0]
print(f"Load: ${load_addr:04X}, Size: {len(ref_data):,}")
print()

# Wave table
wave_addr = 0x1924
wave_offset = wave_addr - load_addr + 2
print(f"Wave at ${wave_addr:04X}, offset ${wave_offset:04X}")
print("Col0:", ' '.join(f'{ref_data[wave_offset+i]:02X}' for i in range(20)))
print("Col1:", ' '.join(f'{ref_data[wave_offset+256+i]:02X}' for i in range(20)))

wave_nonzero = sum(1 for i in range(512) if ref_data[wave_offset+i] != 0)
print(f"Non-zero: {wave_nonzero}/512")
print()

# Pulse table
pulse_addr = 0x1B24
pulse_offset = pulse_addr - load_addr + 2
print(f"Pulse at ${pulse_addr:04X}, offset ${pulse_offset:04X}")
print("Col0:", ' '.join(f'{ref_data[pulse_offset+i]:02X}' for i in range(20)))
print("Col1:", ' '.join(f'{ref_data[pulse_offset+256+i]:02X}' for i in range(20)))
print("Col2:", ' '.join(f'{ref_data[pulse_offset+512+i]:02X}' for i in range(20)))

pulse_nonzero = sum(1 for i in range(1024) if ref_data[pulse_offset+i] != 0)
print(f"Non-zero: {pulse_nonzero}/1024")
