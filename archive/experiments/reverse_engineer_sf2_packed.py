#!/usr/bin/env python3
"""
REVERSE ENGINEER SF2-PACKED FORMAT

The SID was GENERATED FROM an SF2 file using sf2pack.
Therefore, ALL SF2 data (39 sequences, orderlists, tables) MUST be in the SID.

Strategy:
1. Understand SF2 Driver 11 format structure
2. Find where packer placed each component
3. Extract sequences using correct addresses
"""

def mem_to_file_offset(mem_addr):
    """Convert memory address to file offset."""
    return 0x7E + (mem_addr - 0x1000)

def file_to_mem_addr(file_offset):
    """Convert file offset to memory address."""
    return 0x1000 + (file_offset - 0x7E)

def read_word_le(data, offset):
    """Read 16-bit little-endian word."""
    return data[offset] | (data[offset + 1] << 8)

def analyze_sf2_structure():
    """
    Analyze the SID file as an SF2-packed format.

    SF2 Driver 11 typical structure:
    - Sequences: Multiple 3-byte entries
    - Orderlists: Reference sequence numbers
    - Tables: Wave, Pulse, Filter, etc.
    """
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print("=" * 70)
    print("REVERSE ENGINEERING SF2-PACKED FORMAT")
    print("=" * 70)
    print()

    with open(sid_file, 'rb') as f:
        data = f.read()

    # Read PSID header
    print("PSID HEADER:")
    load_addr = read_word_le(data, 0x08)
    init_addr = read_word_le(data, 0x0A)
    play_addr = read_word_le(data, 0x0C)

    print(f"  Load address: ${load_addr:04X}")
    print(f"  Init address: ${init_addr:04X}")
    print(f"  Play address: ${play_addr:04X}")
    print()

    # SF2-packed detection
    if load_addr == 0x1000 and init_addr == 0x1000 and play_addr == 0x1003:
        print("[CONFIRMED] This is SF2-packed format!")
        print()
    else:
        print("[WARNING] Header doesn't match expected SF2-packed format")
        print()

    # Known addresses from previous investigation
    print("=" * 70)
    print("KNOWN DATA LOCATIONS (from previous analysis)")
    print("=" * 70)
    print()

    print("Orderlists (SHORT - only reference sequence numbers):")
    print(f"  Voice 0: $1A70 (file 0x{mem_to_file_offset(0x1A70):04X}) - 43 bytes")
    print(f"  Voice 1: $1A9B (file 0x{mem_to_file_offset(0x1A9B):04X}) - 24 bytes")
    print(f"  Voice 2: $1AB3 (file 0x{mem_to_file_offset(0x1AB3):04X}) - 30 bytes")
    print()

    print("Tables (successfully extracted):")
    print(f"  Wave table: $1914-$1954")
    print(f"  Filter table: $1A1E-$1A4E")
    print(f"  Pulse table: $1A3B-$1A7A")
    print(f"  Instrument table: $1A6B-$1AAA")
    print()

    # KEY INSIGHT: Find sequence pointer table
    print("=" * 70)
    print("FINDING SEQUENCE POINTER TABLE")
    print("=" * 70)
    print()

    print("In SF2 format, there should be a pointer table mapping")
    print("sequence numbers (0-38) to their memory addresses.")
    print()

    # The orderlists reference sequences 0-38
    # There MUST be a table that maps these numbers to addresses

    # Check around the orderlist area for a pointer table
    # Typically, sequence pointers come before orderlists

    print("Checking for pointer table before orderlists...")
    print()

    # Try different possible locations
    possible_ptr_locations = [
        (0x1800, "Start of music data area"),
        (0x1900, "Before wave table"),
        (0x1A00, "Between tables and orderlists"),
        (0x199F, "Sequence pointers from disassembly"),
    ]

    for addr, desc in possible_ptr_locations:
        offset = mem_to_file_offset(addr)
        print(f"Checking ${addr:04X} ({desc}):")
        print(f"  File offset: 0x{offset:04X}")

        # Read potential pointer table (39 entries × 2 bytes = 78 bytes)
        print(f"  First 10 potential pointers:")
        for i in range(10):
            ptr_offset = offset + i * 2
            if ptr_offset + 1 < len(data):
                ptr = read_word_le(data, ptr_offset)
                ptr_file = mem_to_file_offset(ptr) if 0x1000 <= ptr <= 0x2000 else 0
                print(f"    Seq {i:02d} -> ${ptr:04X} (file 0x{ptr_file:04X})")
        print()

    print("=" * 70)
    print("ALTERNATIVE: SEQUENCE DATA MAY BE INLINE")
    print("=" * 70)
    print()

    print("If sequences are stored contiguously (all 39 in sequence):")
    print("Previous finding: 35 sequences found at file offset 0x0800")
    print()
    print("Let me re-examine that location with correct parsing...")

    return data

def main():
    data = analyze_sf2_structure()

    print()
    print("=" * 70)
    print("NEXT STEP")
    print("=" * 70)
    print()
    print("Need to:")
    print("1. Find the sequence pointer table OR")
    print("2. Understand how orderlists map to sequence data OR")
    print("3. Check if sequences are at a fixed location")
    print()

if __name__ == '__main__':
    main()
