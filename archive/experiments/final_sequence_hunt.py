#!/usr/bin/env python3
"""
FINAL ATTEMPT: Find sequences by comprehensive pattern matching.

Extract ALL sequences from reference SF2, then search for each one
in the SID file to find where they were relocated.
"""

def read_word_le(data, offset):
    """Read 16-bit little-endian word."""
    return data[offset] | (data[offset + 1] << 8)

def extract_sf2_block_5(sf2_data):
    """Extract Block 5 (Music Data) from SF2 which contains sequences."""
    # SF2 starts with load address (2 bytes)
    offset = 2

    # Parse blocks
    while offset < len(sf2_data):
        if offset + 3 > len(sf2_data):
            break

        block_id = sf2_data[offset]
        if block_id == 0xFF:
            break

        if block_id == 0:
            offset += 1
            continue

        size = read_word_le(sf2_data, offset + 1)

        if size == 0 or size > 10000:
            offset += 1
            continue

        # Check if this might be music data block
        # Music data typically has sequences (lots of 3-byte entries)
        block_data = sf2_data[offset + 3:offset + 3 + size]

        # Count potential 3-byte sequence entries
        seq_like = 0
        for i in range(0, min(300, len(block_data)), 3):
            if i + 2 < len(block_data):
                b1, b2, b3 = block_data[i], block_data[i+1], block_data[i+2]
                if (b1 <= 0x1F or b1 >= 0x80) and (b3 <= 0x60 or b3 in [0x7E, 0x7F, 0x80, 0xFF]):
                    seq_like += 1

        if seq_like > 50:  # Lots of sequence-like data
            print(f"Found music-like block at SF2 offset 0x{offset:04X}")
            print(f"  Size: {size} bytes")
            print(f"  Sequence-like entries: {seq_like}/100")
            return block_data

        offset += 3 + size

    return None

def find_pattern_in_sid(sid_data, pattern, min_match=10):
    """Find where a pattern from SF2 appears in SID."""
    matches = []

    for i in range(len(sid_data) - min_match):
        match_len = 0
        for j in range(min(len(pattern), len(sid_data) - i)):
            if sid_data[i + j] == pattern[j]:
                match_len += 1
            else:
                break

        if match_len >= min_match:
            matches.append({'offset': i, 'length': match_len})

    return matches

def main():
    sf2_file = 'learnings/Laxity - Stinsen - Last Night Of 89.sf2'
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print("=" * 70)
    print("FINAL SEQUENCE HUNT - PATTERN MATCHING")
    print("=" * 70)
    print()

    with open(sf2_file, 'rb') as f:
        sf2_data = f.read()

    with open(sid_file, 'rb') as f:
        sid_data = f.read()

    print("Step 1: Extract music data from SF2...")
    music_data = extract_sf2_block_5(sf2_data)

    if not music_data:
        print("Could not find music data block in SF2!")
        return

    print()
    print(f"Extracted {len(music_data)} bytes of music data")
    print()

    # Show first 100 bytes
    print("First 100 bytes:")
    for i in range(0, min(100, len(music_data)), 16):
        print(f"  +{i:04X}: ", end='')
        for j in range(16):
            if i + j < len(music_data):
                print(f"{music_data[i+j]:02X} ", end='')
        print()
    print()

    # Now search for chunks of this data in the SID
    print("Step 2: Search for this data in SID...")
    print()

    # Try different chunk sizes
    chunk_sizes = [100, 50, 30, 20]

    for chunk_size in chunk_sizes:
        print(f"Trying {chunk_size}-byte chunks...")

        for start in range(0, min(500, len(music_data)), chunk_size):
            chunk = music_data[start:start + chunk_size]

            matches = find_pattern_in_sid(sid_data, chunk, min_match=min(20, chunk_size // 2))

            if matches:
                print(f"  Found match for SF2 offset 0x{start:04X}!")
                for match in matches[:2]:  # Show first 2
                    print(f"    SID offset 0x{match['offset']:04X}, length {match['length']} bytes")

                # If we found a good match, this tells us where sequences are!
                if matches[0]['length'] >= chunk_size // 2:
                    print()
                    print(f"POTENTIAL SEQUENCE LOCATION: SID offset 0x{matches[0]['offset']:04X}")
                    print()
                    return

        print()

    print("No significant matches found!")

if __name__ == '__main__':
    main()
