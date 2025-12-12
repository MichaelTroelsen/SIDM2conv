#!/usr/bin/env python3
"""
Analyze the PACKED SID structure to understand how SF2 data is organized.

Based on packer logic: SID contains driver code + music data, stripped of metadata.
"""

def read_word_le(data, offset):
    """Read 16-bit little-endian word."""
    return data[offset] | (data[offset + 1] << 8)

def mem_to_file_offset(mem_addr, load_addr=0x1000):
    """Convert memory address to file offset."""
    return 0x7C + 2 + (mem_addr - load_addr)  # PSID header + load addr word

def main():
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print("=" * 70)
    print("ANALYZING PACKED SID STRUCTURE")
    print("=" * 70)
    print()

    with open(sid_file, 'rb') as f:
        sid_data = f.read()

    # PSID header analysis
    magic = sid_data[0:4]
    version = read_word_le(sid_data, 4)
    data_offset = read_word_le(sid_data, 6)
    load_addr = read_word_le(sid_data, 8)
    init_addr = read_word_le(sid_data, 10)
    play_addr = read_word_le(sid_data, 12)

    print("PSID HEADER:")
    print(f"  Magic: {magic}")
    print(f"  Version: {version}")
    print(f"  Data offset: 0x{data_offset:04X}")
    print(f"  Load address: ${load_addr:04X}")
    print(f"  Init address: ${init_addr:04X}")
    print(f"  Play address: ${play_addr:04X}")
    print()

    # Get actual load address
    if load_addr == 0:
        actual_load = read_word_le(sid_data, 0x7C)
        music_start = 0x7C + 2
    else:
        actual_load = load_addr
        music_start = 0x7C

    print(f"Actual load address: ${actual_load:04X}")
    print(f"Music data starts at file offset: 0x{music_start:04X}")
    print()

    # Analyze what's at known addresses
    print("=" * 70)
    print("KNOWN ADDRESSES FROM PREVIOUS ANALYSIS")
    print("=" * 70)
    print()

    # Orderlists we found
    orderlists = [
        (0x1A70, "Voice 0 orderlist"),
        (0x1A9B, "Voice 1 orderlist"),
        (0x1AB3, "Voice 2 orderlist"),
    ]

    for addr, desc in orderlists:
        offset = mem_to_file_offset(addr, actual_load)
        print(f"{desc} at ${addr:04X} (file 0x{offset:04X}):")
        if offset + 40 < len(sid_data):
            print("  ", end='')
            for i in range(40):
                print(f"{sid_data[offset + i]:02X} ", end='')
            print()
        print()

    # Now, the key question: WHERE ARE THE SEQUENCES?
    # The orderlists contain sequence NUMBERS (0x00-0x26)
    # There must be a way to map sequence number -> sequence address

    print("=" * 70)
    print("SEARCHING FOR SEQUENCE DATA")
    print("=" * 70)
    print()

    # In SF2 format, there's often a sequence pointer table
    # Let's search for a table of 39 16-bit pointers

    print("Searching for 39-entry pointer table (78 bytes)...")
    print()

    # Check areas around orderlists
    search_areas = [
        (0x1800, 0x1A70, "Before orderlists"),
        (0x1000, 0x1800, "Early in file"),
    ]

    for start_addr, end_addr, desc in search_areas:
        print(f"Checking {desc} (${start_addr:04X} - ${end_addr:04X})...")

        for addr in range(start_addr, end_addr - 78, 2):
            offset = mem_to_file_offset(addr, actual_load)
            if offset + 78 >= len(sid_data):
                continue

            # Try reading 39 pointers
            pointers = []
            valid = True

            for i in range(39):
                ptr_offset = offset + i * 2
                ptr = read_word_le(sid_data, ptr_offset)

                # Pointers should be in reasonable range
                if ptr < 0x1000 or ptr > 0x2000:
                    valid = False
                    break

                pointers.append(ptr)

            if valid and len(set(pointers)) > 30:  # At least 30 unique pointers
                print(f"  FOUND candidate at ${addr:04X} (file 0x{offset:04X})!")
                print(f"  First 10 pointers:")
                for i in range(10):
                    print(f"    Seq {i:02d} -> ${pointers[i]:04X}")
                print()

                # This could be it!
                return pointers, addr

    print("No obvious pointer table found.")
    print()

    # Alternative: Sequences might be stored sequentially
    # starting at a fixed location

    print("=" * 70)
    print("TRYING SEQUENTIAL SEQUENCE STORAGE")
    print("=" * 70)
    print()

    # Look for sequence-like data (3-byte entries) before orderlists
    for start_addr in [0x1000, 0x1100, 0x1200, 0x1400, 0x1600, 0x1800]:
        offset = mem_to_file_offset(start_addr, actual_load)
        print(f"Checking ${start_addr:04X} (file 0x{offset:04X})...")

        # Show first 60 bytes as 3-byte groups
        if offset + 60 < len(sid_data):
            count = 0
            for i in range(0, 60, 3):
                b1 = sid_data[offset + i]
                b2 = sid_data[offset + i + 1]
                b3 = sid_data[offset + i + 2]

                # Check if looks like sequence data
                inst_ok = b1 <= 0x1F or b1 >= 0x80
                note_ok = b3 <= 0x60 or b3 in [0x7E, 0x7F, 0x80, 0xFF]

                if inst_ok and note_ok:
                    count += 1

            print(f"  Valid-looking entries: {count}/20")

        print()

if __name__ == '__main__':
    main()
