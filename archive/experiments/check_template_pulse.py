#!/usr/bin/env python3
import struct

# Read template SF2
with open("G5/examples/Driver 11 Test - Arpeggio.sf2", 'rb') as f:
    data = f.read()

load_addr = struct.unpack('<H', data[0:2])[0]
pulse_addr = 0x1B24  # Driver 11 pulse table location (after load addr)
file_offset = pulse_addr - load_addr + 2

print(f"Template load address: ${load_addr:04X}")
print(f"Pulse table file offset: ${file_offset:04X}")
print()

# Read pulse table column 0
print("Template pulse table column 0 (first 10):")
print(' '.join(f'{data[file_offset + i]:02X}' for i in range(10)))

