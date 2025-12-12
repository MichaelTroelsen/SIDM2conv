#!/usr/bin/env python3
"""Check the actual pipeline-generated file"""
import struct

# Read the ACTUAL pipeline file
filepath = "output/SIDSF2player_Complete_Pipeline/Stinsens_Last_Night_of_89/New/Stinsens_Last_Night_of_89.sf2"
print(f"Checking: {filepath}")
print()

with open(filepath, 'rb') as f:
    sf2_data = f.read()

# Get load address
load_addr = struct.unpack('<H', sf2_data[0:2])[0]
print(f"Load Address: ${load_addr:04X}")
print(f"File Size: {len(sf2_data):,} bytes")
print()

# Wave table
wave_addr = 0x1924
wave_offset = wave_addr - load_addr + 2

print(f"Wave table at ${wave_addr:04X}, file offset ${wave_offset:04X}")
print("Column 0 (first 20):", ' '.join(f'{sf2_data[wave_offset+i]:02X}' for i in range(20)))
print("Column 1 (first 20):", ' '.join(f'{sf2_data[wave_offset+256+i]:02X}' for i in range(20)))
print()

# Count non-zero bytes
wave_col0_nonzero = sum(1 for i in range(256) if sf2_data[wave_offset+i] != 0)
wave_col1_nonzero = sum(1 for i in range(256) if sf2_data[wave_offset+256+i] != 0)
print(f"Wave Col0 non-zero: {wave_col0_nonzero}/256")
print(f"Wave Col1 non-zero: {wave_col1_nonzero}/256")
print()

# Pulse table
pulse_addr = 0x1B24
pulse_offset = pulse_addr - load_addr + 2

print(f"Pulse table at ${pulse_addr:04X}, file offset ${pulse_offset:04X}")
print("Column 0 (first 20):", ' '.join(f'{sf2_data[pulse_offset+i]:02X}' for i in range(20)))
print("Column 1 (first 20):", ' '.join(f'{sf2_data[pulse_offset+256+i]:02X}' for i in range(20)))
print("Column 2 (first 20):", ' '.join(f'{sf2_data[pulse_offset+512+i]:02X}' for i in range(20)))
print()

# Count non-zero bytes
pulse_col0_nonzero = sum(1 for i in range(256) if sf2_data[pulse_offset+i] != 0)
pulse_col1_nonzero = sum(1 for i in range(256) if sf2_data[pulse_offset+256+i] != 0)
pulse_col2_nonzero = sum(1 for i in range(256) if sf2_data[pulse_offset+512+i] != 0)
print(f"Pulse Col0 non-zero: {pulse_col0_nonzero}/256")
print(f"Pulse Col1 non-zero: {pulse_col1_nonzero}/256")
print(f"Pulse Col2 non-zero: {pulse_col2_nonzero}/256")

# Expected values
print()
print("Expected Wave Col0 (first 10): 21 21 41 7F 81 41 41 41 7F 81")
print("Expected Pulse Col0 (first 10): 88 00 81 00 00 0F 7F 88 7F 88")
