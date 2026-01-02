#!/usr/bin/env python3
"""Check SID file header information."""

import struct
import sys

sid_file = sys.argv[1] if len(sys.argv) > 1 else 'Laxity/Stinsens_Last_Night_of_89.sid'

with open(sid_file, 'rb') as f:
    data = f.read()

print(f'File: {sid_file}')
print(f'Size: {len(data):,} bytes')
print()

# Parse PSID header
magic = data[0:4]
version = struct.unpack('>H', data[4:6])[0]
data_offset = struct.unpack('>H', data[6:8])[0]
load_header = struct.unpack('>H', data[8:10])[0]
init_addr = struct.unpack('>H', data[10:12])[0]
play_addr = struct.unpack('>H', data[12:14])[0]
songs = struct.unpack('>H', data[14:16])[0]

print('PSID Header:')
print(f'  Magic: {magic}')
print(f'  Version: {version}')
print(f'  Data offset: 0x{data_offset:04X}')
print(f'  Load (header): 0x{load_header:04X}')

if load_header == 0:
    # Load address embedded in data
    embedded_load = struct.unpack('<H', data[data_offset:data_offset+2])[0]
    print(f'  Load (embedded): 0x{embedded_load:04X}')
else:
    print(f'  (no embedded load address)')

print(f'  Init: 0x{init_addr:04X}')
print(f'  Play: 0x{play_addr:04X}')
print(f'  Songs: {songs}')
