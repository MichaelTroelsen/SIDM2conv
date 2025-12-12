#!/usr/bin/env python3
"""
Analyze orderlist to understand how it references tracks/sequences.

From STINSEN_CONVERSION_STATUS.md:
- Voice 0: 0E 0F 0F 0F 0F 11 01...
- Voice 1: 00 12 06 06 06 07...
- Voice 2: 0A 0A 0B 0C 0A 10...

These are either:
1. Sequence numbers (0x00-0xFF) pointing to separate sequences
2. Byte offsets into a continuous sequence table
3. Something else

Let's decode the actual orderlist format to find out.
"""

def read_orderlist_data(sid_file):
    """Read the extracted orderlist files."""
    print("=== ORDERLIST DATA ===\n")

    orderlists = []

    for voice in range(3):
        filename = f'output/orderlist_voice{voice}_driver11.bin'
        try:
            with open(filename, 'rb') as f:
                data = f.read()

            orderlists.append(data)
            print(f"Voice {voice} orderlist: {len(data)} bytes")

            # Decode orderlist entries
            print(f"  Entries: ", end='')
            entries = []
            i = 0
            while i < len(data):
                byte = data[i]

                # Check for end markers
                if byte == 0xFF:
                    print(f"FF (loop)", end=' ')
                    i += 2  # FF + loop target
                    break
                elif byte == 0xFE:
                    print(f"FE (end)", end='')
                    break

                # Check if this is a transpose marker (A0, A2, AC, etc.)
                if byte >= 0xA0:
                    # Transpose marker
                    if i + 1 < len(data):
                        seq_num = data[i + 1]
                        entries.append({'transpose': byte, 'sequence': seq_num})
                        print(f"[{byte:02X} {seq_num:02X}]", end=' ')
                        i += 2
                    else:
                        break
                else:
                    # Just a sequence number (reuse previous transpose)
                    entries.append({'transpose': None, 'sequence': byte})
                    print(f"{byte:02X}", end=' ')
                    i += 1

            print(f"\n  Decoded {len(entries)} sequence references\n")
            orderlists.append(entries)

        except FileNotFoundError:
            print(f"  File not found: {filename}\n")
            orderlists.append(None)

    return orderlists

def analyze_sequence_references(orderlists):
    """Analyze what sequences are referenced."""
    print("\n=== SEQUENCE REFERENCE ANALYSIS ===\n")

    all_sequences = set()

    for voice, orderlist in enumerate(orderlists):
        if orderlist and isinstance(orderlist, list):
            sequences = [entry['sequence'] for entry in orderlist if 'sequence' in entry]
            unique = sorted(set(sequences))

            print(f"Voice {voice} references {len(unique)} unique sequences:")
            print(f"  {', '.join(f'{s:02X}' for s in unique)}\n")

            all_sequences.update(unique)

    print(f"Total unique sequences referenced: {len(all_sequences)}")
    print(f"  Sequence numbers: {', '.join(f'{s:02X}' for s in sorted(all_sequences))}\n")

    return all_sequences

def look_for_track_boundaries(sid_file, sequence_numbers):
    """Try to find where tracks might be stored in SID file."""
    print("\n=== SEARCHING FOR TRACK BOUNDARIES ===\n")

    with open(sid_file, 'rb') as f:
        data = f.read()

    # If tracks are stored separately, we might find patterns like:
    # - Multiple 0x7F (END) markers separating tracks
    # - Distinct regions with different characteristics

    # Search for 0x7F markers (END)
    end_markers = []
    for i in range(0x0700, 0x0A9A):
        if data[i] == 0x7F:
            end_markers.append(i)

    print(f"Found {len(end_markers)} potential END markers (0x7F) between 0x0700-0x0A9A:\n")

    for i, pos in enumerate(end_markers[:20]):
        # Show context around each marker
        context_before = ' '.join(f'{data[j]:02X}' for j in range(max(0, pos-6), pos))
        context_after = ' '.join(f'{data[j]:02X}' for j in range(pos+1, min(len(data), pos+7)))

        print(f"  0x{pos:04X}: ... {context_before} [7F] {context_after} ...")

    if len(end_markers) > 20:
        print(f"  ... ({len(end_markers) - 20} more)")

    # Look for 3 major regions (for 3 tracks)
    # Try to find gaps between end markers that might indicate track boundaries
    if len(end_markers) >= 3:
        print(f"\n\nPotential track boundaries based on END marker clusters:\n")

        # Find significant gaps
        gaps = []
        for i in range(len(end_markers) - 1):
            gap = end_markers[i+1] - end_markers[i]
            if gap > 100:  # Significant gap
                gaps.append({
                    'after': end_markers[i],
                    'before': end_markers[i+1],
                    'gap': gap
                })

        for i, gap in enumerate(gaps[:5]):
            print(f"  Gap {i+1}: 0x{gap['after']:04X} -> 0x{gap['before']:04X} ({gap['gap']} bytes)")
            print(f"    Track {i+1} might be: 0x{gap['after']:04X} - 0x{gap['before']:04X}")

def main():
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print("=" * 70)
    print("ORDERLIST REFERENCE ANALYSIS")
    print("=" * 70 + "\n")

    # Read and decode orderlists
    orderlists = read_orderlist_data(sid_file)

    # Analyze what sequences are referenced
    sequence_numbers = analyze_sequence_references(orderlists)

    # Look for track boundaries
    look_for_track_boundaries(sid_file, sequence_numbers)

    print("\n\n=== KEY QUESTIONS ===\n")
    print("1. Are the orderlist values (0E, 0F, 11, etc.) sequence NUMBERS or byte OFFSETS?")
    print("2. If sequence numbers: Where is the index/pointer table that maps numbers to addresses?")
    print("3. If byte offsets: Why are they so small (< 0x20) when sequences are ~670 bytes?")
    print("4. Are there 3 separate track regions, or one continuous sequence table?")

if __name__ == '__main__':
    main()
