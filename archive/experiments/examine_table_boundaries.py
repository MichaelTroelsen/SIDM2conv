#!/usr/bin/env python3
"""
Examine known table boundaries in Stinsens file to find sequence location.

Known from STINSEN_CONVERSION_STATUS.md:
- Tempo table ends: 0x0A9A
- Voice 0 orderlist: 0x0AEE
- Voice 1 orderlist: 0x0B1A
- Voice 2 orderlist: 0x0B31

All other tables (Pulse, Wave, Filter, Instruments, Arp, Commands) already extracted.
"""

def find_table_end(data, start, wrap_marker=0x7F):
    """Find end of a table by searching for wrap marker."""
    for i in range(start, len(data)):
        if data[i] == wrap_marker:
            return i
    return -1

def analyze_gap(data, start, end, name):
    """Analyze a gap between known structures."""
    print(f"\n=== {name} ===")
    print(f"Range: 0x{start:04X} - 0x{end:04X} ({end-start} bytes)")

    # Show hex dump
    print("\nHex dump:")
    for i in range(start, min(end, start + 64), 16):
        hex_vals = ' '.join(f'{data[j]:02X}' for j in range(i, min(i+16, end)))
        print(f"  0x{i:04X}: {hex_vals}")

    if end - start > 64:
        print(f"  ... ({end - start - 64} more bytes)")

        # Show last 64 bytes
        print("\nLast 64 bytes:")
        for i in range(max(start, end - 64), end, 16):
            hex_vals = ' '.join(f'{data[j]:02X}' for j in range(i, min(i+16, end)))
            print(f"  0x{i:04X}: {hex_vals}")

def main():
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print(f"Reading: {sid_file}")
    with open(sid_file, 'rb') as f:
        data = f.read()

    print(f"File size: {len(data)} bytes")

    # Known boundaries
    tempo_end = 0x0A9A
    orderlist_v0 = 0x0AEE
    orderlist_v1 = 0x0B1A
    orderlist_v2 = 0x0B31

    # Search backwards from tempo table for sequence data
    # Sequences should have recognizable patterns:
    # - Instrument bytes: 0x00-0x1F (0-31)
    # - Command bytes: often 0x80+ (no change) or 0x00-0x0F
    # - Note bytes: 0x00-0x5F or gate markers (7E, 80)

    print("\n=== Known Structure ===")
    print(f"Tempo table ends: 0x{tempo_end:04X}")
    print(f"Voice 0 orderlist: 0x{orderlist_v0:04X}")
    print(f"Voice 1 orderlist: 0x{orderlist_v1:04X}")
    print(f"Voice 2 orderlist: 0x{orderlist_v2:04X}")

    # Analyze gap between tempo and orderlist
    analyze_gap(data, tempo_end, orderlist_v0, "Gap between Tempo and Orderlist")

    # Look at what's before tempo table
    # Try to find where music data starts
    # Common pattern: tables are in reverse order (sequences first, then tempo)

    print("\n\n=== Searching backwards from Tempo table ===")

    # Check various regions before tempo
    regions_to_check = [
        (tempo_end - 512, tempo_end, "512 bytes before tempo"),
        (tempo_end - 1024, tempo_end - 512, "1024-512 bytes before tempo"),
        (0x0800, 0x0900, "0x0800-0x0900 region"),
    ]

    for start, end, name in regions_to_check:
        if start < 0:
            continue

        # Sample this region
        print(f"\n{name} (0x{start:04X} - 0x{end:04X}):")

        # Count potential sequence entries
        # Look for patterns where:
        # - byte 0 (instrument): 0x00-0x1F or 0x80+ (no change)
        # - byte 2 (note): reasonable note value or gate marker

        valid_entries = 0
        for i in range(start, min(end, len(data)), 3):
            if i + 2 >= len(data):
                break

            inst = data[i]
            cmd = data[i+1]
            note = data[i+2]

            # Valid instrument: 0-31 or 0x80+ (no change marker)
            inst_valid = (inst <= 0x1F) or (inst >= 0x80)

            # Valid note: 0-95 or gate markers (7E, 80, FF, FE)
            note_valid = (note <= 0x5F) or note in [0x7E, 0x80, 0xFF, 0xFE]

            if inst_valid and note_valid:
                valid_entries += 1

        total_entries = (min(end, len(data)) - start) // 3
        if total_entries > 0:
            percent = (valid_entries / total_entries) * 100
            print(f"  Valid entries: {valid_entries}/{total_entries} ({percent:.1f}%)")

            if percent > 70:
                print(f"  ** HIGH CONFIDENCE - likely sequence data **")

                # Show first few entries
                print(f"\n  First entries:")
                for i in range(start, min(start + 30, end), 3):
                    inst = data[i]
                    cmd = data[i+1]
                    note = data[i+2]
                    note_str = {0x7E: "GATE", 0x80: "---", 0xFF: "END", 0xFE: "LOOP"}.get(note, f"{note:02X}")
                    print(f"    0x{i:04X}: [{inst:02X}] [{cmd:02X}] [{note_str}]")

if __name__ == '__main__':
    main()
