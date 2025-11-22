#!/usr/bin/env python3
"""
Deep analysis to find instrument data in Laxity SID files.

The goal is to find where AD/SR values and waveform settings are stored
so we can convert them to SF2 format.

SF2 Instrument format (6 bytes):
- AD (Attack/Decay)
- SR (Sustain/Release)
- Wave table index
- Pulse table index
- Filter table index
- HR table index

Laxity likely stores similar data but we need to find the exact format.
"""

import struct
import os

def load_sid(path):
    with open(path, 'rb') as f:
        data = f.read()

    magic = data[0:4].decode('ascii')
    version = struct.unpack('>H', data[4:6])[0]
    data_offset = struct.unpack('>H', data[6:8])[0]
    load_address = struct.unpack('>H', data[8:10])[0]
    init_address = struct.unpack('>H', data[10:12])[0]
    play_address = struct.unpack('>H', data[12:14])[0]

    c64_data = data[data_offset:]
    if load_address == 0:
        load_address = struct.unpack('<H', c64_data[0:2])[0]
        c64_data = c64_data[2:]

    return {
        'load_address': load_address,
        'init_address': init_address,
        'play_address': play_address,
        'c64_data': c64_data
    }

def find_instrument_table_candidates(data, load_addr):
    """
    Search for instrument table by looking for:
    1. Consecutive entries with valid AD/SR patterns
    2. Waveform references (typically 0x10, 0x20, 0x40, 0x80 for tri/saw/pulse/noise)
    """

    candidates = []

    # Look for patterns where multiple consecutive entries have
    # reasonable AD/SR values

    for addr in range(load_addr + 0x100, load_addr + len(data) - 128):
        offset = addr - load_addr

        # Try different instrument sizes: 6, 7, 8 bytes
        for instr_size in [6, 7, 8]:
            score = 0
            instruments = []

            for i in range(16):  # Check up to 16 instruments
                instr_off = offset + i * instr_size
                if instr_off + instr_size > len(data):
                    break

                instr = data[instr_off:instr_off + instr_size]

                # Score based on typical instrument characteristics
                # AD byte (byte 0): Common values 0x00-0x0F for attack, 0x00-0xF0 for decay
                ad = instr[0]
                sr = instr[1] if len(instr) > 1 else 0

                # Check for reasonable AD/SR values
                # Attack 0-15, Decay 0-15 -> AD byte 0x00-0xFF
                # Sustain 0-15, Release 0-15 -> SR byte 0x00-0xFF

                # Most instruments have non-zero AD or SR
                if ad != 0 or sr != 0:
                    # Check if values look reasonable (not all same, not ascending sequence)
                    if ad != sr or ad > 0x10:  # Different or clearly not just padding
                        score += 1

                instruments.append(instr)

            if score >= 4:  # At least 4 instrument-like entries
                candidates.append({
                    'addr': addr,
                    'size': instr_size,
                    'score': score,
                    'instruments': instruments[:score]
                })

    # Sort by score
    candidates.sort(key=lambda x: -x['score'])

    return candidates[:10]  # Return top 10 candidates

def analyze_init_routine(data, load_addr, init_addr):
    """
    Analyze the init routine to find instrument table references.

    Look for patterns like:
    - LDA table,X / STA $D405 (store AD)
    - LDA table,X / STA $D406 (store SR)
    """

    print(f"\nAnalyzing init routine at ${init_addr:04X}")

    init_offset = init_addr - load_addr
    if init_offset < 0 or init_offset >= len(data):
        print("  Init address outside data range")
        return

    # Dump first 64 bytes of init routine
    print("  First 64 bytes of init:")
    for i in range(0, 64, 16):
        if init_offset + i + 16 > len(data):
            break
        row = data[init_offset + i:init_offset + i + 16]
        hex_str = ' '.join(f'{b:02X}' for b in row)
        print(f"    ${init_addr + i:04X}: {hex_str}")

    # Search for SID register writes in the code
    # STA $D4xx is 8D xx D4 (absolute addressing)
    # STA $D4xx,X is 9D xx D4 (absolute,X)

    print("\n  SID register writes found:")
    for i in range(len(data) - 3):
        # Check for STA $D4xx (8D xx D4)
        if data[i] == 0x8D and data[i + 2] == 0xD4:
            reg = data[i + 1]
            addr = load_addr + i
            if addr >= init_addr and addr < init_addr + 256:
                print(f"    ${addr:04X}: STA $D4{reg:02X}")

        # Check for LDA absolute,X (BD xx xx) near init
        if data[i] == 0xBD:
            table_lo = data[i + 1]
            table_hi = data[i + 2]
            table_addr = table_lo | (table_hi << 8)
            addr = load_addr + i
            if addr >= init_addr - 256 and addr < init_addr + 512:
                if load_addr <= table_addr < load_addr + len(data):
                    print(f"    ${addr:04X}: LDA ${table_addr:04X},X (table reference)")

def find_wave_pulse_tables(data, load_addr):
    """
    Look for wave table and pulse table patterns.

    Wave tables often contain values like:
    - 0x11 (triangle)
    - 0x21 (saw)
    - 0x41 (pulse)
    - 0x81 (noise)
    - 0x7F (end marker or jump back)
    """

    print("\nSearching for wave table patterns...")

    for addr in range(load_addr + 0x100, load_addr + len(data) - 32):
        offset = addr - load_addr
        chunk = data[offset:offset + 16]

        # Count waveform-like values
        wave_count = 0
        for b in chunk:
            if b in [0x11, 0x21, 0x41, 0x81, 0x7F, 0x7E]:
                wave_count += 1

        if wave_count >= 4:
            hex_str = ' '.join(f'{b:02X}' for b in chunk)
            print(f"  Potential wave table at ${addr:04X}: {hex_str}")

def main():
    sid_dir = 'SID'

    for filename in os.listdir(sid_dir):
        if not filename.endswith('.sid'):
            continue

        filepath = os.path.join(sid_dir, filename)
        print("=" * 70)
        print(f"FILE: {filename}")
        print("=" * 70)

        sid = load_sid(filepath)
        data = sid['c64_data']
        load_addr = sid['load_address']

        print(f"Load: ${load_addr:04X}, Init: ${sid['init_address']:04X}, Play: ${sid['play_address']:04X}")
        print(f"Data size: {len(data)} bytes")

        # Analyze init routine
        analyze_init_routine(data, load_addr, sid['init_address'])

        # Find instrument table candidates
        print("\nInstrument table candidates:")
        candidates = find_instrument_table_candidates(data, load_addr)

        for cand in candidates[:3]:  # Show top 3
            addr = cand['addr']
            size = cand['size']
            score = cand['score']
            print(f"\n  At ${addr:04X} ({size}-byte format, score={score}):")

            for i, instr in enumerate(cand['instruments'][:8]):
                hex_str = ' '.join(f'{b:02X}' for b in instr)
                print(f"    Instr {i}: {hex_str}")

        # Look for wave tables
        find_wave_pulse_tables(data, load_addr)

        print()

if __name__ == '__main__':
    main()
