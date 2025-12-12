#!/usr/bin/env python3
"""
Analyze SF2 file structure to understand the format.
"""

def analyze_sf2_blocks(sf2_data):
    """Analyze block structure of SF2 file."""
    print("Analyzing SF2 block structure...")
    print()

    offset = 0
    block_num = 0

    while offset < min(len(sf2_data), 2000):  # Analyze first 2KB
        if offset + 3 > len(sf2_data):
            break

        block_id = sf2_data[offset]

        # Show hex at this offset
        hex_view = ' '.join(f'{b:02X}' for b in sf2_data[offset:min(offset+16, len(sf2_data))])
        print(f"Offset 0x{offset:04X}: {hex_view}")

        if block_id == 0xFF:
            print(f"  -> Block {block_num}: END (0xFF)")
            break

        if block_id == 0:
            print(f"  -> Padding byte")
            offset += 1
            continue

        # Try to read size
        if offset + 2 < len(sf2_data):
            size_lo = sf2_data[offset + 1]
            size_hi = sf2_data[offset + 2]
            size = size_lo | (size_hi << 8)

            print(f"  -> Block {block_num}: ID={block_id}, Size={size} bytes")

            block_num += 1
            offset += 3 + size
        else:
            break

        if block_num > 20:  # Limit output
            print("  ... (limiting output)")
            break

        print()


def main():
    reference_file = 'learnings/Laxity - Stinsen - Last Night Of 89.sf2'

    print("=" * 70)
    print("SF2 STRUCTURE ANALYSIS")
    print("=" * 70)
    print()

    with open(reference_file, 'rb') as f:
        sf2_data = f.read()

    print(f"File size: {len(sf2_data)} bytes")
    print()

    analyze_sf2_blocks(sf2_data)


if __name__ == '__main__':
    main()
