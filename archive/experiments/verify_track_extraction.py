#!/usr/bin/env python3
"""
Verify track/sequence extraction methodology.

Show exactly how we determine where tracks 1, 2, 3 start.
"""

def analyze_reference_sf2_tracks(sf2_file):
    """Analyze reference SF2 to understand track structure."""
    print(f"=== REFERENCE SF2 FILE: {sf2_file} ===\n")

    with open(sf2_file, 'rb') as f:
        data = f.read()

    load_addr = data[0] | (data[1] << 8)
    print(f"Load address: ${load_addr:04X}")
    print(f"File size: {len(data)} bytes\n")

    # According to SF2_FORMAT_SPEC.md:
    # Sequence Pointers section at memory $0903
    seq_mem_addr = 0x0903

    # This is BEFORE the load address, so we need to find it in the file differently
    # Let's search for actual sequence patterns in the reference file

    print("Searching for sequence patterns in reference file...\n")

    # Look for instrument markers (0xA0-0xBF range indicates instrument)
    # and command markers (0xC0+ indicates command)
    # Note values should be 0x00-0x5F or special markers (7E, 7F, 80)

    # Scan through file looking for valid 3-byte sequence patterns
    best_regions = []

    for start in range(0x0100, len(data) - 300, 16):
        valid_count = 0
        total_count = 0

        for i in range(0, min(300, len(data) - start), 3):
            offset = start + i
            if offset + 2 >= len(data):
                break

            inst = data[offset]
            cmd = data[offset+1]
            note = data[offset+2]

            # Check if this looks like valid sequence data
            # Instrument: 0x80 (no change) or 0xA0-0xBF (instrument)
            # Command: 0x80 (no change) or 0xC0+ (command)
            # Note: 0x00-0x5F (notes) or 0x7E/7F/80 (markers)

            inst_valid = (inst == 0x80 or (inst >= 0xA0 and inst <= 0xBF))
            cmd_valid = (cmd == 0x80 or cmd >= 0xC0 or cmd <= 0x0F)
            note_valid = (note <= 0x5F or note in [0x7E, 0x7F, 0x80])

            if inst_valid and note_valid:
                valid_count += 1

            total_count += 1

        if total_count > 0:
            percent = (valid_count / total_count) * 100
            if percent > 70:
                best_regions.append({
                    'start': start,
                    'percent': percent,
                    'valid': valid_count,
                    'total': total_count
                })

    # Show top 5 regions
    best_regions.sort(key=lambda x: x['percent'], reverse=True)

    print(f"Top regions with valid sequence patterns:\n")
    for i, region in enumerate(best_regions[:5]):
        print(f"  {i+1}. Offset 0x{region['start']:04X}: {region['percent']:.1f}% valid ({region['valid']}/{region['total']})")

        # Show first few entries from top region
        if i == 0:
            print(f"\n     First 20 entries:")
            for j in range(20):
                offset = region['start'] + (j * 3)
                if offset + 2 >= len(data):
                    break

                inst = data[offset]
                cmd = data[offset+1]
                note = data[offset+2]

                # Format for display
                inst_str = f"{inst:02X}"
                if inst == 0x80:
                    inst_str = "-- (80)"
                elif inst >= 0xA0 and inst <= 0xBF:
                    inst_str = f"I{inst-0xA0:02d}"

                cmd_str = f"{cmd:02X}"
                if cmd == 0x80:
                    cmd_str = "-- (80)"
                elif cmd >= 0xC0:
                    cmd_str = f"C{cmd-0xC0:02d}"

                note_str = f"{note:02X}"
                if note == 0x7E:
                    note_str = "+++ (7E)"
                elif note == 0x7F:
                    note_str = "END (7F)"
                elif note == 0x80:
                    note_str = "--- (80)"

                print(f"       +0x{j*3:04X}: [{inst_str:8s}] [{cmd_str:8s}] [{note_str}]")

            print()

    if best_regions:
        return best_regions[0]['start']
    else:
        return None

def analyze_sid_file_for_tracks(sid_file):
    """Analyze SID file to find track locations."""
    print(f"\n=== SID FILE: {sid_file} ===\n")

    with open(sid_file, 'rb') as f:
        data = f.read()

    load_addr = data[0x7C] | (data[0x7D] << 8)
    print(f"Load address: ${load_addr:04X}")
    print(f"File size: {len(data)} bytes\n")

    # Known: Tempo table ends at 0x0A9A
    tempo_end = 0x0A9A
    print(f"Tempo table ends at: 0x{tempo_end:04X}\n")

    # Search backwards from tempo for sequence-like data
    print("Searching for sequence/track patterns...\n")

    best_regions = []

    # Scan from 0x0700 to tempo_end
    for start in range(0x0700, tempo_end - 100, 16):
        valid_count = 0
        total_count = 0

        for i in range(0, min(200, tempo_end - start), 3):
            offset = start + i
            if offset + 2 >= len(data):
                break

            inst = data[offset]
            cmd = data[offset+1]
            note = data[offset+2]

            # For SID file, sequences may have different encoding
            # Just check for reasonable values
            inst_valid = inst <= 0x1F or inst >= 0x80
            note_valid = note <= 0x5F or note in [0x7E, 0x7F, 0x80, 0xFF, 0xFE]

            if inst_valid and note_valid:
                valid_count += 1

            total_count += 1

        if total_count > 0:
            percent = (valid_count / total_count) * 100
            if percent > 60:
                best_regions.append({
                    'start': start,
                    'percent': percent,
                    'valid': valid_count,
                    'total': total_count
                })

    # Show top regions
    best_regions.sort(key=lambda x: x['percent'], reverse=True)

    print(f"Top regions with sequence-like patterns:\n")
    for i, region in enumerate(best_regions[:10]):
        print(f"  {i+1}. Offset 0x{region['start']:04X}: {region['percent']:.1f}% valid ({region['valid']}/{region['total']})")

    print()

    # Show first few entries from top region
    if best_regions:
        top = best_regions[0]
        print(f"First 20 entries from top region (0x{top['start']:04X}):\n")

        for j in range(20):
            offset = top['start'] + (j * 3)
            if offset + 2 >= len(data):
                break

            inst = data[offset]
            cmd = data[offset+1]
            note = data[offset+2]

            note_str = f"{note:02X}"
            if note == 0x7E:
                note_str = "7E (+++)"
            elif note == 0x7F:
                note_str = "7F (END)"
            elif note == 0x80:
                note_str = "80 (---)"
            elif note == 0xFF:
                note_str = "FF"

            print(f"  +0x{j*3:04X}: [{inst:02X}] [{cmd:02X}] [{note_str}]")

        print()
        return top['start']

    return None

def compare_extractions(ref_start, sid_start):
    """Compare what we'd extract from each file."""
    print(f"\n=== COMPARISON ===\n")

    if ref_start and sid_start:
        print(f"Reference SF2 best sequence start: 0x{ref_start:04X}")
        print(f"SID file best sequence start: 0x{sid_start:04X}")
        print(f"Difference: {abs(ref_start - sid_start)} bytes\n")
    else:
        print("Could not determine start addresses for comparison\n")

def main():
    ref_file = 'learnings/Laxity - Stinsen - Last Night Of 89.sf2'
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print("=" * 70)
    print("TRACK EXTRACTION VERIFICATION")
    print("=" * 70 + "\n")

    ref_start = analyze_reference_sf2_tracks(ref_file)
    sid_start = analyze_sid_file_for_tracks(sid_file)

    compare_extractions(ref_start, sid_start)

    # Now show the actual extraction I used
    print("\n=== MY EXTRACTION METHODOLOGY ===\n")
    print("I used:")
    print(f"  Start: 0x07FC")
    print(f"  End: 0x0A9A (tempo table start)")
    print(f"  Size: {0x0A9A - 0x07FC} bytes\n")

    print("This was based on:")
    print("  1. Finding high-confidence sequence patterns at 0x0800 (80% valid)")
    print("  2. Starting slightly before (0x07FC) to catch any header")
    print("  3. Ending at tempo table boundary (0x0A9A)\n")

    print("Question to investigate:")
    print("  - Are tracks stored separately (Track 1, Track 2, Track 3)?")
    print("  - Or as one continuous sequence table with all voices mixed?")
    print("  - Do orderlists reference byte offsets or sequence numbers?")

if __name__ == '__main__':
    main()
