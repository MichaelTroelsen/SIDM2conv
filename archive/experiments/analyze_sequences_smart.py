#!/usr/bin/env python3
"""
Smart sequence analysis using Python - no runtime tracing needed.

Strategy:
1. We KNOW orderlists reference 39 sequences (0x00-0x26)
2. We KNOW orderlists are at $1AEE, $1B1A, $1B31
3. We can read orderlists to see which sequences are used WHEN
4. We can search for regions with proper sequence structure
5. We can use frequency analysis to find the most likely locations

This is pure static analysis - examining the file directly.
"""

def mem_to_file_offset(mem_addr):
    """Convert memory address to file offset."""
    return 0x7E + (mem_addr - 0x1000)

def file_to_mem_addr(file_offset):
    """Convert file offset to memory address."""
    return 0x1000 + (file_offset - 0x7E)

def read_orderlist(data, start_offset):
    """Read and decode orderlist."""
    entries = []
    i = start_offset
    current_transpose = 0xA0

    while i < len(data):
        byte = data[i]

        if byte == 0xFF or byte == 0xFE:
            break

        # Transpose marker
        if byte >= 0xA0:
            current_transpose = byte
            if i + 1 < len(data):
                seq_num = data[i+1]
                entries.append({'transpose': byte, 'sequence': seq_num, 'offset': i - start_offset})
                i += 2
            else:
                break
        else:
            # Sequence number
            entries.append({'transpose': current_transpose, 'sequence': byte, 'offset': i - start_offset})
            i += 1

    return entries

def analyze_sequence_region(data, start_offset, length):
    """Analyze a region to see if it contains sequence data."""
    score = 0
    entries_found = 0

    for i in range(0, min(length, len(data) - start_offset - 3), 3):
        offset = start_offset + i
        if offset + 2 >= len(data):
            break

        inst = data[offset]
        cmd = data[offset + 1]
        note = data[offset + 2]

        # Score this entry
        entry_score = 0

        # Instrument validation
        if inst <= 0x1F:  # Valid instrument number
            entry_score += 2
        elif inst >= 0x80:  # Persistence marker
            entry_score += 1
        elif inst in [0x7E, 0x7F]:  # Control markers
            entry_score += 1

        # Note validation
        if note <= 0x5F:  # Valid note
            entry_score += 2
        elif note in [0x7E, 0x7F, 0x80, 0xFF]:  # Control markers
            entry_score += 2
        elif note >= 0xA0:  # Transpose
            entry_score += 1

        # Command is harder to validate (any value possible)
        entry_score += 0.5

        score += entry_score
        if entry_score >= 3:
            entries_found += 1

    return score, entries_found

def find_pointer_table_by_analysis(data, num_sequences=39):
    """Find pointer table by looking for patterns."""
    candidates = []

    # A pointer table would be 39 * 2 = 78 bytes
    # Look for regions with increasing 16-bit values

    for offset in range(0x200, 0xB00, 2):
        if offset + num_sequences * 2 >= len(data):
            break

        # Try reading as pointer table
        pointers = []
        valid = True

        for i in range(num_sequences):
            ptr_offset = offset + i * 2
            if ptr_offset + 1 >= len(data):
                valid = False
                break

            lo = data[ptr_offset]
            hi = data[ptr_offset + 1]
            ptr = lo | (hi << 8)

            # Pointers should be in reasonable range
            if ptr < 0x1000 or ptr > 0x2000:
                valid = False
                break

            pointers.append(ptr)

        if not valid:
            continue

        # Check if mostly increasing
        increasing = sum(1 for i in range(len(pointers)-1) if pointers[i+1] >= pointers[i])
        increasing_ratio = increasing / (len(pointers) - 1) if len(pointers) > 1 else 0

        if increasing_ratio > 0.5:  # At least 50% increasing
            candidates.append({
                'offset': offset,
                'mem_addr': file_to_mem_addr(offset),
                'pointers': pointers,
                'increasing_ratio': increasing_ratio
            })

    return candidates

def main():
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print("=" * 70)
    print("SMART SEQUENCE ANALYSIS")
    print("=" * 70)
    print()

    with open(sid_file, 'rb') as f:
        data = f.read()

    print(f"File: {sid_file}")
    print(f"Size: {len(data)} bytes")
    print()

    # Read orderlists
    print("=" * 70)
    print("STEP 1: READ ORDERLISTS")
    print("=" * 70)
    print()

    orderlist_offsets = {
        'Voice 0': 0x0AEE,
        'Voice 1': 0x0B1A,
        'Voice 2': 0x0B31
    }

    all_sequences_used = set()

    for voice, offset in orderlist_offsets.items():
        entries = read_orderlist(data, offset)
        sequences = [e['sequence'] for e in entries]
        all_sequences_used.update(sequences)

        print(f"{voice} orderlist at 0x{offset:04X} (${file_to_mem_addr(offset):04X}):")
        print(f"  Uses {len(set(sequences))} unique sequences: {sorted(set(sequences))}")
        print(f"  First 5 entries: {sequences[:5]}")
        print()

    print(f"Total unique sequences used: {len(all_sequences_used)}")
    print(f"Sequence numbers: {sorted(all_sequences_used)}")
    print()

    # Search for pointer table
    print("=" * 70)
    print("STEP 2: SEARCH FOR POINTER TABLE")
    print("=" * 70)
    print()

    pointer_candidates = find_pointer_table_by_analysis(data, len(all_sequences_used))

    if pointer_candidates:
        print(f"Found {len(pointer_candidates)} pointer table candidates:")
        print()

        for i, cand in enumerate(pointer_candidates[:3]):
            print(f"Candidate {i+1}:")
            print(f"  File offset: 0x{cand['offset']:04X}")
            print(f"  Memory addr: ${cand['mem_addr']:04X}")
            print(f"  Increasing ratio: {cand['increasing_ratio']:.1%}")
            print(f"  First 10 pointers:")

            for j, ptr in enumerate(cand['pointers'][:10]):
                file_off = mem_to_file_offset(ptr)
                print(f"    Seq {j:02X} -> ${ptr:04X} (file 0x{file_off:04X})")

            print()
    else:
        print("No pointer table candidates found with standard format.")
        print("Trying alternative search...")
        print()

    # Analyze potential sequence regions
    print("=" * 70)
    print("STEP 3: ANALYZE POTENTIAL SEQUENCE REGIONS")
    print("=" * 70)
    print()

    # Check regions between tables and orderlists
    regions_to_check = [
        (0x0800, 200, "After instrument/table area"),
        (0x0900, 200, "Typical sequence location"),
        (0x0A00, 200, "Before tempo table"),
        (0x0AEE - 300, 300, "Before orderlists"),
    ]

    best_regions = []

    for offset, length, description in regions_to_check:
        if offset + length > len(data):
            continue

        score, entries = analyze_sequence_region(data, offset, length)
        avg_score = score / (length / 3) if length > 0 else 0

        best_regions.append({
            'offset': offset,
            'length': length,
            'score': score,
            'avg_score': avg_score,
            'entries': entries,
            'description': description
        })

        mem_addr = file_to_mem_addr(offset)
        print(f"Region: {description}")
        print(f"  File offset: 0x{offset:04X}")
        print(f"  Memory addr: ${mem_addr:04X}")
        print(f"  Score: {score:.1f} ({avg_score:.2f} avg)")
        print(f"  Valid entries: {entries}/{length//3}")

        # Show first few bytes
        print(f"  First 12 bytes: ", end='')
        for i in range(min(12, len(data) - offset)):
            print(f"{data[offset + i]:02X} ", end='')
        print()
        print()

    # Find best region
    best = max(best_regions, key=lambda x: x['avg_score'])

    print("=" * 70)
    print("BEST CANDIDATE REGION")
    print("=" * 70)
    print()

    print(f"Location: {best['description']}")
    print(f"File offset: 0x{best['offset']:04X}")
    print(f"Memory addr: ${file_to_mem_addr(best['offset']):04X}")
    print(f"Score: {best['score']:.1f}")
    print()

    print("First 30 entries as 3-byte sequences:")
    for i in range(30):
        offset = best['offset'] + i * 3
        if offset + 2 >= len(data):
            break

        inst = data[offset]
        cmd = data[offset + 1]
        note = data[offset + 2]

        note_str = f"{note:02X}"
        if note == 0x7E:
            note_str = "7E (+++)"
        elif note == 0x7F:
            note_str = "7F (END)"
        elif note == 0x80:
            note_str = "80 (---)"
        elif note == 0xFF:
            note_str = "FF (LOOP)"
        elif note >= 0xA0:
            note_str = f"{note:02X} (TRAN)"

        print(f"  +{i*3:03d}: [{inst:02X}] [{cmd:02X}] [{note_str}]")

    print()
    print("=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    print()
    print("Check the best candidate region above.")
    print("If it looks like valid sequence data, that's where sequences start!")
    print()

if __name__ == '__main__':
    main()
