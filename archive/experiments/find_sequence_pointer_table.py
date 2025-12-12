#!/usr/bin/env python3
"""
Find the sequence pointer table.

We need 39 pointers (for sequences 0x00-0x26).
Pointers are likely 2 bytes each (little-endian addresses).
Total size: 39 * 2 = 78 bytes.

The pointer table should be somewhere before the sequence data.
"""

def find_pointer_table(data, expected_count=39):
    """
    Search for a table of pointers.

    Characteristics:
    - expected_count consecutive 2-byte pointers
    - Pointers should be in increasing order (mostly)
    - Pointers should point to reasonable addresses (0x1000-0x2000 range?)
    """
    print(f"Searching for pointer table with {expected_count} entries...\n")

    candidates = []

    # Search range: likely between orderlist end and tempo table
    # Or before tempo table
    search_start = 0x0700
    search_end = 0x0B00

    for start in range(search_start, search_end - (expected_count * 2), 2):
        # Read expected_count pointers
        pointers = []
        valid = True

        for i in range(expected_count):
            offset = start + (i * 2)
            if offset + 1 >= len(data):
                valid = False
                break

            lo = data[offset]
            hi = data[offset + 1]
            ptr = lo | (hi << 8)

            pointers.append(ptr)

            # Basic validation: pointers should be reasonable
            if ptr < 0x1000 or ptr > 0x2000:
                valid = False
                break

        if not valid:
            continue

        # Check if pointers are mostly increasing
        increasing_count = 0
        for i in range(len(pointers) - 1):
            if pointers[i+1] >= pointers[i]:
                increasing_count += 1

        increasing_percent = (increasing_count / (len(pointers) - 1)) * 100 if len(pointers) > 1 else 0

        if increasing_percent > 70:  # Most pointers should be increasing
            candidates.append({
                'start': start,
                'pointers': pointers,
                'increasing_percent': increasing_percent
            })

    return candidates

def analyze_candidates(candidates, data):
    """Analyze pointer table candidates."""
    print(f"Found {len(candidates)} pointer table candidates:\n")

    for i, cand in enumerate(candidates[:5]):
        print(f"Candidate {i+1}: Offset 0x{cand['start']:04X}")
        print(f"  Increasing: {cand['increasing_percent']:.1f}%")
        print(f"  Pointer range: ${cand['pointers'][0]:04X} - ${cand['pointers'][-1]:04X}")

        # Show first 10 pointers
        print(f"  First 10 pointers:")
        for j in range(min(10, len(cand['pointers']))):
            ptr = cand['pointers'][j]
            file_offset = ptr - 0x1000 + 2  # Convert memory addr to file offset
            print(f"    Seq {j:02X}: ${ptr:04X} (file offset 0x{file_offset:04X})")

        # Check if pointed-to locations look like sequence data
        print(f"  Validating pointed-to data:")
        valid_count = 0
        for j in range(min(10, len(cand['pointers']))):
            ptr = cand['pointers'][j]
            file_offset = ptr - 0x1000 + 2

            if file_offset >= 0 and file_offset + 6 < len(data):
                # Check if this looks like sequence data (3-byte entries)
                inst = data[file_offset]
                cmd = data[file_offset+1]
                note = data[file_offset+2]

                inst_valid = inst <= 0x1F or inst >= 0x80
                note_valid = note <= 0x5F or note in [0x7E, 0x7F, 0x80]

                if inst_valid and note_valid:
                    valid_count += 1
                    status = "OK"
                else:
                    status = "BAD"

                print(f"    Seq {j:02X}: [{inst:02X}] [{cmd:02X}] [{note:02X}] - {status}")

        print(f"  Valid sequences: {valid_count}/10\n")

def main():
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print("=" * 70)
    print("SEQUENCE POINTER TABLE SEARCH")
    print("=" * 70 + "\n")

    with open(sid_file, 'rb') as f:
        data = f.read()

    load_addr = data[0x7C] | (data[0x7D] << 8)
    print(f"File: {sid_file}")
    print(f"Load address: ${load_addr:04X}")
    print(f"File size: {len(data)} bytes\n")

    # Search for pointer table
    candidates = find_pointer_table(data, expected_count=39)

    if candidates:
        analyze_candidates(candidates, data)
    else:
        print("No pointer table candidates found.\n")
        print("Trying with relaxed criteria...")

        # Try with fewer sequences
        for count in [30, 25, 20]:
            print(f"\nTrying with {count} sequences...")
            candidates = find_pointer_table(data, expected_count=count)
            if candidates:
                analyze_candidates(candidates, data)
                break

if __name__ == '__main__':
    main()
