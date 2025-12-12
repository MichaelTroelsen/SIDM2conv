#!/usr/bin/env python3
"""
Dump all memory regions from the SID file to understand the layout.

This will help us find where sequence data is actually stored.
"""

def mem_to_file_offset(mem_addr):
    """Convert memory address to file offset."""
    return 0x7E + (mem_addr - 0x1000)

def file_to_mem_addr(file_offset):
    """Convert file offset to memory address."""
    return 0x1000 + (file_offset - 0x7E)

def dump_region(data, start_mem, end_mem, name):
    """Dump a memory region."""
    start_file = mem_to_file_offset(start_mem)
    end_file = mem_to_file_offset(end_mem)

    print(f"\n{name}")
    print(f"  Memory: ${start_mem:04X} - ${end_mem:04X} ({end_mem - start_mem + 1} bytes)")
    print(f"  File:   0x{start_file:04X} - 0x{end_file:04X}")

    # Show first 48 bytes
    print(f"  First 48 bytes:")
    for i in range(0, min(48, end_file - start_file + 1), 12):
        offset = start_file + i
        print(f"    ${start_mem + i:04X}: ", end='')
        for j in range(min(12, end_file - start_file + 1 - i)):
            if offset + j < len(data):
                print(f"{data[offset + j]:02X} ", end='')
        print()

def main():
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print("=" * 70)
    print("MEMORY REGION DUMP")
    print("=" * 70)

    with open(sid_file, 'rb') as f:
        data = f.read()

    print(f"File: {sid_file}")
    print(f"Size: {len(data)} bytes")
    print()

    # Dump regions from memory map
    regions = [
        (0x1914, 0x1933, "Wave table - Note offsets"),
        (0x1934, 0x1953, "Wave table - Waveforms"),
        (0x1A1E, 0x1A4D, "Filter table"),
        (0x1A3B, 0x1A7A, "Pulse table"),
        (0x1A6B, 0x1AAA, "Instrument table"),
        (0x1A8B, 0x1ACA, "Arpeggio table"),
        (0x1ADB, 0x1B9A, "Command table"),
    ]

    for start, end, name in regions:
        dump_region(data, start, end, name)

    # Dump the mystery pointers
    print("\n" + "=" * 70)
    print("MYSTERY POINTER LOCATIONS (from $1A1C-$1A21)")
    print("=" * 70)

    mystery_locs = [
        (0x1A70, 0x1A9A, "Voice 0 data at $1A70"),
        (0x1A9B, 0x1AB2, "Voice 1 data at $1A9B"),
        (0x1AB3, 0x1AD0, "Voice 2 data at $1AB3"),
    ]

    for start, end, name in mystery_locs:
        dump_region(data, start, end, name)

    # Look for gaps in memory map
    print("\n" + "=" * 70)
    print("POTENTIAL SEQUENCE DATA GAPS")
    print("=" * 70)

    gaps = [
        (0x19A6, 0x1913, "Gap after sequence pointers"),
        (0x1954, 0x1A1D, "Gap between wave and filter tables"),
    ]

    for start, end, name in gaps:
        if end > start:
            dump_region(data, start, end, name)

    print()

if __name__ == '__main__':
    main()
