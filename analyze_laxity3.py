#!/usr/bin/env python3
"""
Precise analysis of Laxity player format based on init routine references.
Focus on $199F and surrounding data structures.
"""

import struct

def load_sid(path):
    with open(path, 'rb') as f:
        data = f.read()
    version = struct.unpack('>H', data[4:6])[0]
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

def get_word(data, load_addr, addr):
    return get_byte(data, load_addr, addr) | (get_byte(data, load_addr, addr + 1) << 8)

def hex_dump(data, load_addr, start, length, label=""):
    """Hex dump a region"""
    print(f"\n{label} (${start:04X} - ${start+length-1:04X}):")
    offset = start - load_addr
    for i in range(0, length, 16):
        addr = start + i
        if offset + i >= len(data):
            break
        line = data[offset + i:offset + i + 16]
        hex_str = ' '.join(f'{b:02X}' for b in line)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in line)
        print(f"  ${addr:04X}: {hex_str:<48} {ascii_str}")

def analyze_angular():
    """Precise analysis for Angular.sid based on init routine"""
    c64_data, load_addr = load_sid('SID/Angular.sid')

    print("=" * 70)
    print("LAXITY PLAYER FORMAT - PRECISE ANALYSIS")
    print("=" * 70)
    print(f"Load: ${load_addr:04X}, End: ${load_addr + len(c64_data) - 1:04X}")

    # The init routine loads from $199F,Y - this is the music data pointer
    # Let's examine the structure starting at $199F

    print("\n" + "=" * 70)
    print("EXAMINING $199F - MUSIC DATA HEADER")
    print("=" * 70)

    # $199F appears to be a table/index that the init routine reads
    # Looking at the hex dump: 01 24 33 00 00 00 00 00...
    # This could be: song number, then parameters

    hex_dump(c64_data, load_addr, 0x1990, 32, "Header region")

    # The key discovery from analyze_laxity2.py:
    # $19A0: 1A 00 1B 0E 1B 01 07 F2 1A 00 1B 0E 1B FF
    # These look like small sequence indices! Let's interpret them

    print("\n" + "=" * 70)
    print("POTENTIAL ORDERLIST DATA")
    print("=" * 70)

    # Let's find all sequences of small values ending in FF
    # Starting around $19A0

    # Based on the patterns, it seems like orderlists might be at:
    # - Around $1AEF-$1B00 area
    # Looking at: 01 01 01 01 01 01 08 08 08 08 08 08 FF
    # and: 02 02 02 02 02 02 09 09 09 09 09 09 FF
    # and: 05 06 03 04 03 07 0A 0A 0B 0C 0B 0D FF

    print("\nSearching for clean orderlists (small seq indices, FF terminator):")

    orderlists_found = []

    for addr in range(0x1900, 0x1C00):
        offset = addr - load_addr
        if offset < 0 or offset >= len(c64_data) - 32:
            continue

        # Read sequence until we hit FF
        seq = []
        for i in range(32):
            b = c64_data[offset + i]
            seq.append(b)
            if b == 0xFF:
                break

        if len(seq) < 4 or seq[-1] != 0xFF:
            continue

        # Check if all values before FF are small (sequence indices)
        # Typical sequence indices are 0x00-0x1F
        values = seq[:-1]  # Exclude FF

        # All values should be small
        if all(v <= 0x20 for v in values):
            # Not all zeros
            if any(v > 0 for v in values):
                hex_str = ' '.join(f'{b:02X}' for b in seq)
                print(f"  ${addr:04X}: {hex_str}")
                orderlists_found.append((addr, seq))

    print("\n" + "=" * 70)
    print("SEQUENCE POINTER TABLES")
    print("=" * 70)

    # Laxity typically uses pointer tables for sequences
    # Let's find where sequence pointers are stored
    # They would point to addresses in range $1B00-$1E00

    # Look for a table of 3 pointers (lo bytes) followed by 3 hi bytes
    # For 3 voices

    print("\nSearching for 3-pointer voice tables:")

    for lo_addr in range(0x1990, 0x1C00):
        offset = lo_addr - load_addr
        if offset < 0 or offset >= len(c64_data) - 8:
            continue

        # Try different hi byte offsets
        for hi_offset in [3]:  # Laxity often uses 3-byte separation
            hi_addr = lo_addr + hi_offset

            # Read 3 pointers
            ptrs = []
            valid = True
            for i in range(3):
                lo = get_byte(c64_data, load_addr, lo_addr + i)
                hi = get_byte(c64_data, load_addr, hi_addr + i)
                ptr = lo | (hi << 8)

                # Pointer should be in data range
                if not (0x1900 <= ptr <= 0x1F00):
                    valid = False
                    break
                ptrs.append(ptr)

            if valid and len(set(ptrs)) >= 2:  # Not all same
                # Print this potential table
                print(f"\n  lo=${lo_addr:04X}, hi=${hi_addr:04X}")
                for i, ptr in enumerate(ptrs):
                    # Show data at pointer
                    ptr_data = [get_byte(c64_data, load_addr, ptr + j) for j in range(16)]
                    hex_str = ' '.join(f'{b:02X}' for b in ptr_data)
                    print(f"    Voice {i+1} -> ${ptr:04X}: {hex_str}")

    print("\n" + "=" * 70)
    print("ANALYZING ACTUAL SEQUENCE DATA ($1B38+)")
    print("=" * 70)

    # The cleaner music data appears to start around $1B38
    # Let's examine what looks like actual sequence data

    hex_dump(c64_data, load_addr, 0x1B38, 64, "Data at $1B38")
    hex_dump(c64_data, load_addr, 0x1B78, 64, "Data at $1B78")
    hex_dump(c64_data, load_addr, 0x1BB8, 64, "Data at $1BB8")

    # Now let's find sequence start addresses by looking for
    # data patterns followed by 0x7F terminators

    print("\n" + "=" * 70)
    print("FINDING SEQUENCE BOUNDARIES (by 7F markers)")
    print("=" * 70)

    # Find all 0x7F positions
    markers = []
    for i, b in enumerate(c64_data):
        if b == 0x7F:
            addr = load_addr + i
            if 0x1B00 <= addr <= 0x1F00:
                markers.append(addr)

    print(f"Found {len(markers)} sequence end markers (0x7F) in music data area:")

    # List all markers
    for m in markers:
        # Show data before the marker
        start = m - 16
        data = [get_byte(c64_data, load_addr, start + j) for j in range(17)]
        hex_str = ' '.join(f'{b:02X}' for b in data)
        print(f"  ${m:04X}: ...{hex_str}")

    print("\n" + "=" * 70)
    print("INFERRING SEQUENCE START ADDRESSES")
    print("=" * 70)

    # Sequences end with 7F. Work backwards from each 7F to find starts.
    # A new sequence starts after the previous 7F.

    if markers:
        # Assume first sequence starts at $1B38 based on pattern
        prev_end = 0x1B38 - 1

        sequences = []
        for end in markers:
            start = prev_end + 1
            length = end - start + 1
            if length > 0 and length < 256:
                sequences.append((start, end, length))
            prev_end = end

        print(f"\nInferred {len(sequences)} sequences:")
        for i, (start, end, length) in enumerate(sequences[:20]):
            # Show sequence data
            seq_data = [get_byte(c64_data, load_addr, start + j) for j in range(min(length, 24))]
            hex_str = ' '.join(f'{b:02X}' for b in seq_data)
            if length > 24:
                hex_str += ' ...'
            print(f"  Seq {i}: ${start:04X}-${end:04X} ({length} bytes): {hex_str}")

    print("\n" + "=" * 70)
    print("INSTRUMENT TABLE SEARCH")
    print("=" * 70)

    # Laxity instruments are typically 8-byte structures:
    # AD/SR, waveform, pulse width, etc.

    # Look for consecutive valid instrument-like structures
    print("\nSearching for 8-byte instrument tables:")

    for addr in range(0x1900, 0x1B00):
        offset = addr - load_addr
        if offset < 0 or offset >= len(c64_data) - 64:
            continue

        # Check for 8 consecutive potential instruments
        instr_count = 0
        for i in range(8):
            instr = c64_data[offset + i*8:offset + (i+1)*8]

            # Basic sanity check:
            # - AD should be non-zero
            # - SR should be non-zero
            # - Waveform should have some typical bits set (10, 20, 40, 80)
            ad = instr[0] if len(instr) > 0 else 0
            sr = instr[1] if len(instr) > 1 else 0
            wave = instr[2] if len(instr) > 2 else 0

            if ad > 0 and sr > 0 and (wave & 0xF1):  # Has waveform bits
                instr_count += 1
            else:
                break

        if instr_count >= 4:
            print(f"\n  Table at ${addr:04X} ({instr_count} instruments):")
            for i in range(instr_count):
                instr = c64_data[offset + i*8:offset + (i+1)*8]
                hex_str = ' '.join(f'{b:02X}' for b in instr)
                print(f"    Instr {i}: {hex_str}")

if __name__ == '__main__':
    analyze_angular()
