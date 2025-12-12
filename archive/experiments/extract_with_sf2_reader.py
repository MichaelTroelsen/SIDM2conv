#!/usr/bin/env python3
"""
Use SF2PackedReader to properly extract sequences from the SID file.

This uses the existing module designed specifically for SF2-packed format.
"""

from sidm2.sf2_packed_reader import SF2PackedReader

def main():
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print("=" * 70)
    print("EXTRACTING SEQUENCES USING SF2PACKEDREADER")
    print("=" * 70)
    print()

    try:
        reader = SF2PackedReader(sid_file)

        print(f"File: {sid_file}")
        print(f"Load address: ${reader.load_address:04X}")
        print()

        # Parse header blocks
        reader.parse_header_blocks()

        print("=" * 70)
        print("HEADER BLOCKS FOUND")
        print("=" * 70)
        print()

        for block_id, block_data in reader.header_blocks.items():
            print(f"Block {block_id}: {len(block_data)} bytes")

        print()

        # Extract tables
        print("=" * 70)
        print("TABLES")
        print("=" * 70)
        print()

        for table_id, table_def in reader.tables.items():
            name = reader.table_names.get(table_id, f"Table{table_id}")
            print(f"{name}: {table_def}")

        print()

        # Try to extract sequences
        print("=" * 70)
        print("EXTRACTING SEQUENCES")
        print("=" * 70)
        print()

        # In SF2 format, sequences are in Block 5 (Music Data)
        if reader.BLOCK_MUSIC_DATA in reader.header_blocks:
            music_data = reader.header_blocks[reader.BLOCK_MUSIC_DATA]
            print(f"Music data block: {len(music_data)} bytes")
            print()

            # Parse music data structure
            # First part should be orderlists, then sequences
            # Let's examine the structure

            print("First 100 bytes of music data:")
            for i in range(0, min(100, len(music_data)), 16):
                print(f"  +{i:04X}: ", end='')
                for j in range(16):
                    if i + j < len(music_data):
                        print(f"{music_data[i+j]:02X} ", end='')
                print()

        else:
            print("No music data block found!")

        print()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
