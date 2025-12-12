#!/usr/bin/env python3
"""
Verify SF2 sequence and orderlist data.
Checks all 3 tracks for proper formatting and data integrity.
"""

import struct
import sys

def read_sf2_data(filepath):
    """Read SF2 file and return (data, load_addr)"""
    with open(filepath, 'rb') as f:
        data = f.read()
    # SF2 files are PRG files: first 2 bytes are load address (little-endian)
    load_addr = struct.unpack('<H', data[0:2])[0]
    return data, load_addr

def get_offset(load_addr, mem_addr):
    """Convert memory address to file offset"""
    # PRG format: load address (2 bytes) + data
    return mem_addr - load_addr + 2

def parse_sf2_header(data):
    """Parse SF2 header blocks to extract music data info"""
    BLOCK_DESCRIPTOR = 1
    BLOCK_DRIVER_COMMON = 2
    BLOCK_DRIVER_TABLES = 3
    BLOCK_INSTRUMENT_DESC = 4
    BLOCK_MUSIC_DATA = 5
    BLOCK_END = 0xFF

    music_data_info = {}

    load_addr = struct.unpack('<H', data[0:2])[0]

    offset = 4  # Skip load address (2) and file ID (2)
    while offset < len(data) - 2:
        block_id = data[offset]
        if block_id == BLOCK_END:
            break

        block_size = data[offset + 1]
        block_data = data[offset + 2:offset + 2 + block_size]

        if block_id == BLOCK_MUSIC_DATA:
            # Parse music data block
            if len(block_data) >= 18:
                idx = 0
                music_data_info['track_count'] = block_data[idx]
                idx += 1
                music_data_info['orderlist_ptrs_lo'] = struct.unpack('<H', block_data[idx:idx+2])[0]
                idx += 2
                music_data_info['orderlist_ptrs_hi'] = struct.unpack('<H', block_data[idx:idx+2])[0]
                idx += 2
                music_data_info['sequence_count'] = block_data[idx]
                idx += 1
                music_data_info['sequence_ptrs_lo'] = struct.unpack('<H', block_data[idx:idx+2])[0]
                idx += 2
                music_data_info['sequence_ptrs_hi'] = struct.unpack('<H', block_data[idx:idx+2])[0]
                idx += 2
                music_data_info['orderlist_size'] = struct.unpack('<H', block_data[idx:idx+2])[0]
                idx += 2
                music_data_info['orderlist_start'] = struct.unpack('<H', block_data[idx:idx+2])[0]
                idx += 2
                music_data_info['sequence_size'] = struct.unpack('<H', block_data[idx:idx+2])[0]
                idx += 2
                music_data_info['sequence_start'] = struct.unpack('<H', block_data[idx:idx+2])[0]

        offset += 2 + block_size

    return music_data_info

def parse_sequence_pointers(data, load_addr, music_info):
    """Parse orderlist pointer table from SF2 header info"""
    if not music_info or 'orderlist_ptrs_lo' not in music_info:
        return []

    # Read the orderlist pointer table (lo bytes)
    ptrs_lo_addr = music_info['orderlist_ptrs_lo']
    ptrs_hi_addr = music_info['orderlist_ptrs_hi']

    pointers = []
    track_count = music_info.get('track_count', 3)

    for track in range(track_count):
        lo_offset = get_offset(load_addr, ptrs_lo_addr + track)
        hi_offset = get_offset(load_addr, ptrs_hi_addr + track)

        if lo_offset < len(data) and hi_offset < len(data):
            lo = data[lo_offset]
            hi = data[hi_offset]
            ptr = (hi << 8) | lo
            pointers.append(ptr)

    return pointers

def parse_orderlist(data, load_addr, ptr):
    """Parse orderlist starting at given pointer"""
    offset = get_offset(load_addr, ptr)

    orderlist = []
    pos = offset

    # Read until end marker (0xFE or 0xFF) or max 256 entries
    for _ in range(256):
        if pos + 1 >= len(data):
            break

        transpose = data[pos]
        seq_index = data[pos + 1]

        # Check for end markers
        if transpose == 0xFE or transpose == 0xFF:
            # End of orderlist
            break

        orderlist.append((transpose, seq_index))
        pos += 2

    return orderlist

def parse_sequence_data(data, load_addr, start_addr, max_events=100):
    """Parse sequence data starting at given address"""
    offset = get_offset(load_addr, start_addr)

    events = []
    pos = offset

    for _ in range(max_events):
        if pos + 2 >= len(data):
            break

        instrument = data[pos]
        command = data[pos + 1]
        note = data[pos + 2]

        # Check for end of sequence
        if note == 0x7F:
            events.append((instrument, command, note))
            break

        events.append((instrument, command, note))
        pos += 3

    return events

def format_transpose(value):
    """Convert transpose byte to description"""
    if value == 0xA0:
        return "No transpose"
    elif value < 0xA0:
        semitones = value - 0xA0
        return f"{semitones:+d} semitones"
    else:
        semitones = value - 0xA0
        return f"{semitones:+d} semitones"

def format_note(value):
    """Convert note byte to description"""
    if value == 0x7E:
        return "+++"
    elif value == 0x7F:
        return "END"
    elif value == 0x80:
        return "---"
    elif value <= 0x5D:
        notes = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']
        octave = value // 12
        note = value % 12
        return f"{notes[note]}{octave}"
    else:
        return f"${value:02X}"

def format_instrument(value):
    """Convert instrument byte to description"""
    if value == 0x80:
        return "--"
    elif 0xA0 <= value <= 0xBF:
        return f"{value - 0xA0:02d}"
    else:
        return f"${value:02X}"

def format_command(value):
    """Convert command byte to description"""
    if value == 0x80:
        return "--"
    elif value >= 0xC0:
        return f"T{value - 0xC0:X}"
    else:
        return f"${value:02X}"

def verify_sequences(data, load_addr):
    """Verify all sequence and orderlist data"""
    print("=" * 80)
    print("SF2 MUSIC DATA HEADER")
    print("=" * 80)

    # Parse SF2 header blocks
    music_info = parse_sf2_header(data)

    if not music_info:
        print("ERROR: Could not parse SF2 music data header")
        return False

    print(f"Track count: {music_info.get('track_count', 'N/A')}")
    print(f"Sequence count: {music_info.get('sequence_count', 'N/A')}")
    print(f"Orderlist pointers Lo: ${music_info.get('orderlist_ptrs_lo', 0):04X}")
    print(f"Orderlist pointers Hi: ${music_info.get('orderlist_ptrs_hi', 0):04X}")
    print(f"Orderlist start: ${music_info.get('orderlist_start', 0):04X}")
    print(f"Orderlist size: {music_info.get('orderlist_size', 0)} bytes")
    print(f"Sequence pointers Lo: ${music_info.get('sequence_ptrs_lo', 0):04X}")
    print(f"Sequence pointers Hi: ${music_info.get('sequence_ptrs_hi', 0):04X}")
    print(f"Sequence start: ${music_info.get('sequence_start', 0):04X}")
    print(f"Sequence size: {music_info.get('sequence_size', 0)} bytes")

    print("\n" + "=" * 80)
    print("ORDERLIST POINTERS")
    print("=" * 80)

    pointers = parse_sequence_pointers(data, load_addr, music_info)
    print(f"Found {len(pointers)} track pointers:")
    for i, ptr in enumerate(pointers):
        print(f"  Track {i+1}: ${ptr:04X}")

    print("\n" + "=" * 80)
    print("ORDERLISTS")
    print("=" * 80)

    for track_num, ptr in enumerate(pointers, 1):
        print(f"\nTrack {track_num} orderlist at ${ptr:04X}:")
        orderlist = parse_orderlist(data, load_addr, ptr)
        print(f"  Entries: {len(orderlist)}")

        if orderlist:
            print("  First 5 entries:")
            for i, (transpose, seq_idx) in enumerate(orderlist[:5]):
                print(f"    [{i:2d}] Transpose: ${transpose:02X} ({format_transpose(transpose)}), Sequence: ${seq_idx:02X}")

    print("\n" + "=" * 80)
    print("SEQUENCE DATA SAMPLES")
    print("=" * 80)

    # Collect all unique sequence indices referenced
    all_seq_indices = set()
    for ptr in pointers:
        orderlist = parse_orderlist(data, load_addr, ptr)
        for _, seq_idx in orderlist:
            all_seq_indices.add(seq_idx)

    print(f"\nFound {len(all_seq_indices)} unique sequences referenced")

    return True

def verify_orderlist_integrity(data, load_addr):
    """Verify orderlist data integrity"""
    print("\n" + "=" * 80)
    print("ORDERLIST INTEGRITY CHECK")
    print("=" * 80)

    music_info = parse_sf2_header(data)
    if not music_info:
        print("ERROR: Could not parse SF2 music data header")
        return False

    pointers = parse_sequence_pointers(data, load_addr, music_info)

    all_pass = True
    for track_num, ptr in enumerate(pointers, 1):
        orderlist = parse_orderlist(data, load_addr, ptr)

        # Check 1: Orderlist should have entries
        if not orderlist:
            print(f"  Track {track_num}: FAIL - Empty orderlist")
            all_pass = False
            continue

        # Check 2: Transpose values should be reasonable (0x80-0xC0 range typically)
        invalid_transposes = [t for t, _ in orderlist if not (0x80 <= t <= 0xC0)]
        if invalid_transposes:
            print(f"  Track {track_num}: WARN - {len(invalid_transposes)} unusual transpose values")

        # Check 3: Sequence indices should be < 256 (always true for byte, but check for 0xFF)
        max_seq = max(s for _, s in orderlist)
        if max_seq == 0xFF:
            print(f"  Track {track_num}: WARN - Sequence index 0xFF (may be terminator)")

        print(f"  Track {track_num}: PASS - {len(orderlist)} entries, transpose range ${min(t for t,_ in orderlist):02X}-${max(t for t,_ in orderlist):02X}, sequences 0-{max_seq}")

    return all_pass

def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_sequences.py <sf2_file>")
        sys.exit(1)

    sf2_file = sys.argv[1]
    print(f"Verifying SF2 sequences: {sf2_file}\n")

    data, load_addr = read_sf2_data(sf2_file)
    print(f"Load address: ${load_addr:04X}")
    print(f"File size: {len(data)} bytes\n")

    # Verify sequence structure
    verify_sequences(data, load_addr)

    # Verify data integrity
    result = verify_orderlist_integrity(data, load_addr)

    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    print(f"  SEQUENCES: {'PASS' if result else 'FAIL'}")

if __name__ == '__main__':
    main()
