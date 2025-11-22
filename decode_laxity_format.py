#!/usr/bin/env python3
"""
Decode the exact Laxity instrument format by analyzing table structure.

Based on analysis, Laxity appears to store:
- Separate tables for AD, SR, waveform, pulse width
- Indexed by instrument number (0xA0-0xAF in sequences = instruments 0-15)
"""

import struct
import os

def load_sid(path):
    with open(path, 'rb') as f:
        data = f.read()
    data_offset = struct.unpack('>H', data[6:8])[0]
    load_address = struct.unpack('>H', data[8:10])[0]
    c64_data = data[data_offset:]
    if load_address == 0:
        load_address = struct.unpack('<H', c64_data[0:2])[0]
        c64_data = c64_data[2:]
    return c64_data, load_address

def get_byte(data, load_addr, addr):
    offset = addr - load_addr
    if 0 <= offset < len(data):
        return data[offset]
    return 0

def analyze_angular():
    """Deep analysis of Angular.sid to find exact table locations"""

    data, load_addr = load_sid('SID/Angular.sid')

    print("="*70)
    print("ANGULAR.SID DEEP ANALYSIS")
    print("="*70)

    # From the earlier analysis, we found table references at:
    # $1006,X - config
    # $191F,X - ?
    # $1949,X - ?
    # $1901,X - per-voice?
    # $1904,X - per-voice?
    # $1907,X - per-voice?
    # $1928,X - ?

    # Let's examine the area around $1980 which had instrument-like data
    print("\nExamining $1980-$19FF (instrument data area):")

    for row_addr in range(0x1980, 0x1A20, 16):
        offset = row_addr - load_addr
        if offset + 16 > len(data):
            break
        row = data[offset:offset + 16]
        hex_str = ' '.join(f'{b:02X}' for b in row)
        print(f"  ${row_addr:04X}: {hex_str}")

    # Now let's look at the actual reference at $1984
    # $1984: F8 98 28 41 20 21 FF FF FF
    # These could be:
    # - F8, 98, 28 = AD/SR values
    # - 41, 20, 21 = Waveforms (pulse, saw+gate?, saw)

    print("\nAnalyzing $1984-$1990 as potential instrument table:")
    addr = 0x1984
    for i in range(8):
        offset = addr - load_addr + i
        b = data[offset] if offset < len(data) else 0
        print(f"  [{i}] ${addr+i:04X}: {b:02X}")

    # Let's look at what the sequences actually use
    # From Angular, sequences use instruments 0xA0-0xAC (instruments 0-12)

    print("\nLooking for separate AD/SR tables:")

    # In many C64 music formats, tables are 16 or 32 bytes apart
    # Let's search for tables that have typical AD/SR patterns

    # AD values typically: 0x00-0x0F for short attack, higher for longer
    # SR values typically: higher values for sustained sounds

    # Check area around $1A00 which had waveform-like data
    print("\nExamining $1A00-$1A40 (possible AD/SR/waveform tables):")
    for row_addr in range(0x1A00, 0x1A40, 16):
        offset = row_addr - load_addr
        if offset + 16 > len(data):
            break
        row = data[offset:offset + 16]
        hex_str = ' '.join(f'{b:02X}' for b in row)
        print(f"  ${row_addr:04X}: {hex_str}")

    # Let's try to identify the tables by their content patterns
    print("\nSearching for AD table (values typically 0x00-0xFF, first byte often 0x0X):")

    for addr in range(0x1900, 0x1B00):
        offset = addr - load_addr
        if offset + 16 > len(data):
            break

        # Check if this looks like an AD table (16 consecutive bytes)
        # AD values: attack in high nibble (0-F), decay in low nibble (0-F)
        table = data[offset:offset + 16]

        # Heuristic: Most AD values have attack < 0x10 (quick attack)
        # But some have higher values for pads
        quick_attacks = sum(1 for b in table if (b & 0xF0) <= 0x20)

        if quick_attacks >= 8:
            hex_str = ' '.join(f'{b:02X}' for b in table)
            print(f"  ${addr:04X}: {hex_str}")

    print("\nSearching for SR table (sustained sounds have high nibble >= 0x80):")

    for addr in range(0x1900, 0x1B00):
        offset = addr - load_addr
        if offset + 16 > len(data):
            break

        table = data[offset:offset + 16]

        # Heuristic: SR values often have sustain >= 0x80 for leads
        sustained = sum(1 for b in table if (b & 0xF0) >= 0x80)

        if sustained >= 4 and sustained <= 12:
            hex_str = ' '.join(f'{b:02X}' for b in table)
            print(f"  ${addr:04X}: {hex_str}")

    print("\nSearching for waveform table (values 0x11, 0x21, 0x41, 0x81):")

    valid_waves = {0x11, 0x21, 0x41, 0x81, 0x10, 0x20, 0x40, 0x80}

    for addr in range(0x1900, 0x1B00):
        offset = addr - load_addr
        if offset + 16 > len(data):
            break

        table = data[offset:offset + 16]
        wave_count = sum(1 for b in table if b in valid_waves)

        if wave_count >= 6:
            hex_str = ' '.join(f'{b:02X}' for b in table)
            print(f"  ${addr:04X}: {hex_str}")

def extract_all_instruments():
    """Extract instruments from all SID files"""

    sid_dir = 'SID'

    all_results = {}

    for filename in sorted(os.listdir(sid_dir)):
        if not filename.endswith('.sid'):
            continue

        filepath = os.path.join(sid_dir, filename)
        data, load_addr = load_sid(filepath)

        print(f"\n{'='*70}")
        print(f"FILE: {filename}")
        print(f"{'='*70}")

        # Find waveform table (most distinctive)
        wave_addr = find_waveform_table(data, load_addr)

        if wave_addr:
            # Waveform table often has AD/SR tables nearby
            # Check 16-32 bytes before
            offset = wave_addr - load_addr

            print(f"\nWaveform table at ${wave_addr:04X}")

            # Dump surrounding area
            for check_addr in [wave_addr - 32, wave_addr - 16, wave_addr]:
                check_offset = check_addr - load_addr
                if check_offset >= 0 and check_offset + 16 <= len(data):
                    table = data[check_offset:check_offset + 16]
                    hex_str = ' '.join(f'{b:02X}' for b in table)
                    print(f"  ${check_addr:04X}: {hex_str}")

            all_results[filename] = {
                'wave_addr': wave_addr,
                'data': data,
                'load_addr': load_addr
            }

    return all_results

def find_waveform_table(data, load_addr):
    """Find the most likely waveform table"""

    valid_waves = {0x11, 0x21, 0x41, 0x81, 0x10, 0x20, 0x40, 0x80}

    best_addr = None
    best_score = 0

    for addr in range(load_addr + 0x900, load_addr + len(data) - 32):
        offset = addr - load_addr

        table = data[offset:offset + 16]
        score = sum(1 for b in table if b in valid_waves)

        # Bonus for having multiple different waveforms
        unique_waves = len(set(b for b in table if b in valid_waves))
        score += unique_waves * 2

        if score > best_score:
            best_score = score
            best_addr = addr

    return best_addr if best_score >= 10 else None

if __name__ == '__main__':
    analyze_angular()
    print("\n\n")
    extract_all_instruments()
