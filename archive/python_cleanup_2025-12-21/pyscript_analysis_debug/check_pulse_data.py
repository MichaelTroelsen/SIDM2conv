#!/usr/bin/env python3
"""Check pulse table data in Aint_Somebody.sid"""

with open('SIDSF2player/Aint_Somebody.sid', 'rb') as f:
    data = f.read()

# Skip PSID header (0x7C bytes)
c64_data = data[0x7C:]
load_addr = 0x1000  # From info.txt

# Try searching around 0x1A00 area (typical Laxity pulse range)
# Offset 0x1A00 - 0x1000 = 0xA00
print('Searching for pulse data around offset 0xA00-0xC00:')
found_count = 0
for base_off in range(0xA00, 0xC00, 0x10):
    if base_off + 16 < len(c64_data):
        # Check if this looks like a pulse table
        has_data = False
        for i in range(4):
            off = base_off + i * 4
            if off + 3 < len(c64_data):
                vals = c64_data[off:off+4]
                if any(vals):
                    has_data = True
                    break
        if has_data:
            print(f'\nOffset 0x{base_off:04X} (addr ${load_addr + base_off:04X}):')
            for i in range(8):
                off = base_off + i * 4
                if off + 3 < len(c64_data):
                    vals = c64_data[off:off+4]
                    print(f'  Entry {i}: {list(vals)} (${vals[0]:02X} ${vals[1]:02X} ${vals[2]:02X} ${vals[3]:02X})')
            found_count += 1
            if found_count >= 5:  # Only show first 5 candidates
                break
