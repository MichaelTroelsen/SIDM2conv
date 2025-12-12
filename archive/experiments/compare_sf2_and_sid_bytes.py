#!/usr/bin/env python3
"""
Compare reference SF2 with SID file byte-by-byte to find where data is located.

This is TRUE reverse engineering - finding the exact mapping.
"""

def find_byte_pattern(haystack, needle, min_length=8):
    """Find where a byte pattern from needle appears in haystack."""
    matches = []
    needle_len = len(needle)

    for i in range(len(haystack) - min_length):
        # Check for matching sequences of at least min_length
        match_len = 0
        for j in range(min(needle_len, len(haystack) - i)):
            if haystack[i + j] == needle[j]:
                match_len += 1
            else:
                break

        if match_len >= min_length:
            matches.append({
                'haystack_offset': i,
                'needle_offset': 0,
                'length': match_len
            })

    return matches

def main():
    sf2_file = 'learnings/Laxity - Stinsen - Last Night Of 89.sf2'
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print("=" * 70)
    print("BYTE-LEVEL COMPARISON: SF2 vs SID")
    print("=" * 70)
    print()

    with open(sf2_file, 'rb') as f:
        sf2_data = f.read()

    with open(sid_file, 'rb') as f:
        sid_data = f.read()

    print(f"SF2 file: {len(sf2_data)} bytes")
    print(f"SID file: {len(sid_data)} bytes")
    print()

    # Skip SF2 header (first ~100 bytes) and look for music data
    print("=" * 70)
    print("SEARCHING FOR SF2 DATA PATTERNS IN SID")
    print("=" * 70)
    print()

    # Try different starting points in SF2
    sf2_starts = [
        (0x100, "After SF2 header"),
        (0x200, "Music data area"),
        (0x400, "Mid-file"),
    ]

    for sf2_start, desc in sf2_starts:
        if sf2_start >= len(sf2_data):
            continue

        print(f"Searching for {desc} (SF2 offset 0x{sf2_start:04X})...")

        # Extract a chunk from SF2
        chunk_size = min(100, len(sf2_data) - sf2_start)
        sf2_chunk = sf2_data[sf2_start:sf2_start + chunk_size]

        # Find in SID
        matches = find_byte_pattern(sid_data, sf2_chunk, min_length=20)

        if matches:
            print(f"  Found {len(matches)} matches!")
            for match in matches[:3]:  # Show first 3
                sid_offset = match['haystack_offset']
                match_len = match['length']
                print(f"    SID offset 0x{sid_offset:04X}: {match_len} bytes match")

                # Show the matching bytes
                print(f"      SF2: ", end='')
                for i in range(min(16, match_len)):
                    print(f"{sf2_chunk[i]:02X} ", end='')
                print()
                print(f"      SID: ", end='')
                for i in range(min(16, match_len)):
                    print(f"{sid_data[sid_offset + i]:02X} ", end='')
                print()
        else:
            print(f"  No matches found")

        print()

    # Try specific known SF2 structures
    print("=" * 70)
    print("SEARCHING FOR SPECIFIC SF2 STRUCTURES")
    print("=" * 70)
    print()

    # In the reference SF2, let's extract sequences starting around offset 0x100-0x200
    # and search for them in the SID

    print("Scanning SF2 for sequence-like patterns and matching in SID...")
    print()

    # Look for 3-byte patterns with end markers (0x7F, 0xFF)
    for sf2_offset in range(0x80, min(0x500, len(sf2_data)), 3):
        # Check if this looks like a sequence entry
        if sf2_offset + 2 >= len(sf2_data):
            break

        # Look for patterns ending in 0x7F or 0xFF (end markers)
        if sf2_data[sf2_offset + 2] in [0x7F, 0xFF]:
            # Extract surrounding context
            context_start = max(0, sf2_offset - 30)
            context_end = min(len(sf2_data), sf2_offset + 30)
            context = sf2_data[context_start:context_end]

            # Search for this pattern in SID
            matches = find_byte_pattern(sid_data, context, min_length=15)

            if matches:
                print(f"Found sequence pattern at SF2 offset 0x{sf2_offset:04X}:")
                print(f"  Pattern: ...", end='')
                for i in range(max(0, sf2_offset - context_start - 6), min(len(context), sf2_offset - context_start + 9)):
                    print(f"{context[i]:02X} ", end='')
                print("...")

                for match in matches[:1]:  # Show first match
                    sid_offset = match['haystack_offset']
                    print(f"  Found in SID at offset 0x{sid_offset:04X}")

                print()

                # Only show first few matches
                if sf2_offset > 0x200:
                    break

if __name__ == '__main__':
    main()
