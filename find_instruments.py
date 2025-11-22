#!/usr/bin/env python3
"""Find instrument table location in SF2 files"""

import struct

def find_instruments_in_file(filepath, name):
    with open(filepath, 'rb') as f:
        data = f.read()

    load_addr = struct.unpack('<H', data[0:2])[0]
    print(f"\n{name}")
    print(f"Load address: ${load_addr:04X}, File size: {len(data)}")

    # Look at the "Instruments" section shown in screenshot
    # It shows addresses like "00: 00 c5 80 00 00"
    # This suggests 5-byte or 6-byte instrument format

    # In SF2, instruments are typically in the driver area
    # Let's look for common instrument patterns

    # From the screenshot, instrument 00 shows "00 c5 80 00 00"
    # Let's find where this pattern might be

    # Search for areas with waveform bytes (10, 11, 20, 21, 40, 41, 80, 81)
    valid_waves = {0x10, 0x11, 0x20, 0x21, 0x40, 0x41, 0x80, 0x81}

    print("\nSearching for instrument tables (6-byte format):")

    for addr in range(load_addr + 0x100, load_addr + 0x1000):
        offset = addr - load_addr + 2
        if offset + 96 > len(data):
            break

        # Check for 16 consecutive valid instruments (6-byte each)
        count = 0
        for i in range(16):
            instr_off = offset + i * 6
            if instr_off + 6 > len(data):
                break

            # 6-byte instrument: AD, SR, Wave, PulseL, PulseH, ???
            instr = data[instr_off:instr_off + 6]

            # Check wave byte (typically byte 2)
            wave = instr[2] if len(instr) > 2 else 0

            if wave in valid_waves or wave == 0:
                count += 1
            else:
                break

        if count >= 8:
            print(f"\n  Found at ${addr:04X} (offset {offset}), {count} instruments:")
            for i in range(min(count, 8)):
                instr = data[offset + i * 6:offset + (i + 1) * 6]
                hex_str = ' '.join(f'{b:02X}' for b in instr)
                print(f"    Instr {i}: {hex_str}")

    # Also try 8-byte format
    print("\nSearching for instrument tables (8-byte format):")

    for addr in range(load_addr + 0x100, load_addr + 0x1000):
        offset = addr - load_addr + 2
        if offset + 128 > len(data):
            break

        count = 0
        for i in range(16):
            instr_off = offset + i * 8
            if instr_off + 8 > len(data):
                break

            instr = data[instr_off:instr_off + 8]
            wave = instr[2] if len(instr) > 2 else 0

            if wave in valid_waves or wave == 0:
                count += 1
            else:
                break

        if count >= 8:
            print(f"\n  Found at ${addr:04X} (offset {offset}), {count} instruments:")
            for i in range(min(count, 8)):
                instr = data[offset + i * 8:offset + (i + 1) * 8]
                hex_str = ' '.join(f'{b:02X}' for b in instr)
                print(f"    Instr {i}: {hex_str}")


# Check template
find_instruments_in_file(
    r'C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master\SIDFactoryII\music\Driver 11 Test - Arpeggio.sf2',
    "=== TEMPLATE ==="
)

# Check our output
find_instruments_in_file(
    r'C:\Users\mit\claude\c64server\SIDM2\SF2\Angular.sf2',
    "=== OUR OUTPUT ==="
)
