#!/usr/bin/env python3
"""
Analyze the specific table addresses found in Laxity player.
"""

import struct

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

def dump_area(data, load_addr, start, length, label):
    """Dump a memory area"""
    offset = start - load_addr
    if offset < 0 or offset >= len(data):
        return

    print(f"\n{label} (${start:04X}-${start+length-1:04X}):")
    for i in range(0, length, 16):
        if offset + i >= len(data):
            break
        row = data[offset + i:offset + i + 16]
        addr = start + i
        hex_str = ' '.join(f'{b:02X}' for b in row)
        print(f"  ${addr:04X}: {hex_str}")

def main():
    data, load_addr = load_sid('SID/Angular.sid')

    print(f"Load address: ${load_addr:04X}")
    print(f"Data size: {len(data)} bytes")

    # From the analysis, these are the table references:
    # LDA $1006,X - configuration
    # LDA $191F,X - ?
    # LDA $1949,X - ?
    # LDA $1901,X - ?
    # LDA $1904,X - ?
    # LDA $1907,X - ?
    # LDA $190A,X - ?
    # LDA $1928,X - ?
    # LDA $192E,X - ?

    dump_area(data, load_addr, 0x1900, 128, "Player tables area $1900-$197F")
    dump_area(data, load_addr, 0x1980, 128, "Player tables area $1980-$19FF")

    # Looking at the data we saw earlier, $19E7 onwards has waveform data
    # Let's examine it more carefully

    print("\n" + "="*60)
    print("INTERPRETING TABLE DATA")
    print("="*60)

    # $1901-$1903 (3 bytes per voice)
    # $1904-$1906 (3 bytes per voice)
    # etc.

    # These are likely per-voice state tables (3 bytes each for 3 voices)

    # The waveform data starts around $19E7
    # Let's see if this is organized as instrument data

    print("\nWaveform data area ($19E7-$1A1F):")
    print("Looking for waveform patterns (11=tri, 21=saw, 41=pulse, 81=noise):")

    offset = 0x19E7 - load_addr
    for i in range(16):
        byte_offset = offset + i * 3
        if byte_offset + 3 > len(data):
            break

        # Try 3-byte grouping
        b1, b2, b3 = data[byte_offset:byte_offset + 3]
        print(f"  Entry {i}: {b1:02X} {b2:02X} {b3:02X}")

    # Let's also look at what's at the exact table addresses
    print("\nExact table addresses:")

    tables = [
        (0x1006, "Config?"),
        (0x1901, "Voice 1?"),
        (0x1904, "Voice 2?"),
        (0x1907, "Voice 3?"),
        (0x190A, "Unknown"),
        (0x191F, "Unknown"),
        (0x1928, "Unknown"),
        (0x192E, "Unknown"),
        (0x1949, "Unknown"),
    ]

    for addr, name in tables:
        offset = addr - load_addr
        if offset >= 0 and offset + 16 <= len(data):
            chunk = data[offset:offset + 16]
            hex_str = ' '.join(f'{b:02X}' for b in chunk)
            print(f"  ${addr:04X} ({name}): {hex_str}")

    # Now let's see if there's an instrument table
    # In Laxity player, instruments are typically 8 bytes
    # With format like: AD, SR, Waveform, PulseLo, PulseHi, ...

    print("\n" + "="*60)
    print("SEARCHING FOR 8-BYTE INSTRUMENT TABLE")
    print("="*60)

    # The original analysis showed instruments at around $19F7
    # Let's interpret that area

    print("\n8-byte instrument interpretation starting at $19F7:")
    offset = 0x19F7 - load_addr
    for i in range(8):
        instr_offset = offset + i * 8
        if instr_offset + 8 > len(data):
            break
        instr = data[instr_offset:instr_offset + 8]
        hex_str = ' '.join(f'{b:02X}' for b in instr)

        # Try to interpret
        # For Laxity: byte 0-1 might be AD/SR, byte 2 might be waveform table index
        print(f"  Instr {i}: {hex_str}")

    # Actually, looking at the wave table pattern data at $19E7, it seems like
    # the waveform DATA itself, not indices. Let me check if this is the wave table.

    print("\n" + "="*60)
    print("POTENTIAL WAVE TABLE INTERPRETATION")
    print("="*60)

    # Wave tables typically have format: [waveform, command] or similar
    # with 0x7F as end/loop marker

    print("\nWave table entries (2-byte format) starting at $19E7:")
    offset = 0x19E7 - load_addr
    entry = 0
    for i in range(0, 64, 2):
        if offset + i + 2 > len(data):
            break
        b1, b2 = data[offset + i:offset + i + 2]

        # Decode waveform type
        wave_type = ""
        if b1 & 0x80:
            wave_type = "noise"
        elif b1 & 0x40:
            wave_type = "pulse"
        elif b1 & 0x20:
            wave_type = "saw"
        elif b1 & 0x10:
            wave_type = "tri"
        elif b1 == 0x7F:
            wave_type = "END"
        elif b1 == 0x7E:
            wave_type = "LOOP"

        print(f"  [{entry:2d}] ${offset + i + load_addr:04X}: {b1:02X} {b2:02X}  {wave_type}")
        entry += 1

        if b1 == 0x7F:
            print("  ---")
            # Continue to find next wave entry

if __name__ == '__main__':
    main()
