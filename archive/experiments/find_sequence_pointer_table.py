#!/usr/bin/env python3
"""
Search for the sequence pointer table.

We need to find a table with 39 entries (78 bytes) that maps
sequence numbers 0-38 to their memory addresses.

Could be in two formats:
1. Interleaved: [lo0, hi0, lo1, hi1, ..., lo38, hi38] (78 bytes)
2. Split: [lo0, lo1, ..., lo38, hi0, hi1, ..., hi38] (78 bytes)
"""

def mem_to_file_offset(mem_addr):
    """Convert memory address to file offset."""
    return 0x7E + (mem_addr - 0x1000)

def file_to_mem_addr(file_offset):
    """Convert file offset to memory address."""
    return 0x1000 + (file_offset - 0x7E)

def try_interleaved_format(data, offset, count=39):
    """Try reading pointers in interleaved format."""
    pointers = []
    for i in range(count):
        ptr_offset = offset + i * 2
        if ptr_offset + 1 >= len(data):
            return None

        lo = data[ptr_offset]
        hi = data[ptr_offset + 1]
        ptr = lo | (hi << 8)
        pointers.append(ptr)

    return pointers

def try_split_format(data, offset, count=39):
    """Try reading pointers in split format."""
    if offset + count * 2 >= len(data):
        return None

    low_bytes = data[offset:offset + count]
    high_bytes = data[offset + count:offset + count * 2]

    pointers = []
    for i in range(count):
        ptr = low_bytes[i] | (high_bytes[i] << 8)
        pointers.append(ptr)

    return pointers

def score_pointer_table(pointers):
    """
    Score a potential pointer table.

    Good indicators:
    - Pointers in valid range ($1000-$2000)
    - Generally increasing (sequences stored sequentially)
    - No duplicates (each sequence unique)
    """
    if not pointers:
        return 0

    score = 0

    # Check valid range
    valid_count = sum(1 for p in pointers if 0x1000 <= p <= 0x2000)
    score += valid_count * 2

    # Check for mostly increasing
    increasing = sum(1 for i in range(len(pointers)-1) if pointers[i+1] >= pointers[i])
    score += increasing

    # Check for no duplicates
    if len(set(pointers)) == len(pointers):
        score += 20  # Bonus for all unique

    # Penalty for out of range
    out_of_range = sum(1 for p in pointers if p < 0x1000 or p > 0x2000)
    score -= out_of_range * 5

    return score

def search_for_pointer_table(data, num_sequences=39):
    """Search entire file for pointer table candidates."""
    candidates = []

    # Search every 2-byte aligned position
    for offset in range(0x200, len(data) - num_sequences * 2, 2):
        # Try both formats
        interleaved = try_interleaved_format(data, offset, num_sequences)
        split = try_split_format(data, offset, num_sequences)

        for fmt_name, pointers in [('interleaved', interleaved), ('split', split)]:
            if not pointers:
                continue

            score = score_pointer_table(pointers)

            # Only keep high-scoring candidates
            if score > 50:  # Threshold
                candidates.append({
                    'offset': offset,
                    'format': fmt_name,
                    'pointers': pointers,
                    'score': score
                })

    # Sort by score
    candidates.sort(key=lambda x: x['score'], reverse=True)

    return candidates

def main():
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print("=" * 70)
    print("SEARCHING FOR SEQUENCE POINTER TABLE")
    print("=" * 70)
    print()

    with open(sid_file, 'rb') as f:
        data = f.read()

    print(f"File: {sid_file}")
    print(f"Size: {len(data)} bytes")
    print(f"Looking for: 39 pointers (78 bytes)")
    print()

    print("Searching...")
    candidates = search_for_pointer_table(data, 39)

    print(f"Found {len(candidates)} candidates")
    print()

    if not candidates:
        print("No good candidates found!")
        print()
        print("Trying with lower threshold...")
        # Retry with lower threshold
        candidates = []
        for offset in range(0x200, len(data) - 39 * 2, 2):
            interleaved = try_interleaved_format(data, offset, 39)
            split = try_split_format(data, offset, 39)

            for fmt_name, pointers in [('interleaved', interleaved), ('split', split)]:
                if not pointers:
                    continue

                score = score_pointer_table(pointers)

                if score > 30:  # Lower threshold
                    candidates.append({
                        'offset': offset,
                        'format': fmt_name,
                        'pointers': pointers,
                        'score': score
                    })

        candidates.sort(key=lambda x: x['score'], reverse=True)
        print(f"Found {len(candidates)} candidates with lower threshold")
        print()

    # Show top 5 candidates
    for i, cand in enumerate(candidates[:5]):
        print(f"Candidate {i+1}:")
        print(f"  File offset: 0x{cand['offset']:04X}")
        print(f"  Memory addr: ${file_to_mem_addr(cand['offset']):04X}")
        print(f"  Format: {cand['format']}")
        print(f"  Score: {cand['score']}")
        print()

        # Show first 10 pointers
        print(f"  First 10 pointers:")
        for j in range(min(10, len(cand['pointers']))):
            ptr = cand['pointers'][j]
            file_off = mem_to_file_offset(ptr)
            print(f"    Seq {j:02d} -> ${ptr:04X} (file 0x{file_off:04X})")
        print()

        # Show range
        min_ptr = min(cand['pointers'])
        max_ptr = max(cand['pointers'])
        print(f"  Pointer range: ${min_ptr:04X} - ${max_ptr:04X}")
        print(f"  File range: 0x{mem_to_file_offset(min_ptr):04X} - 0x{mem_to_file_offset(max_ptr):04X}")
        print()

        # Check if this makes sense relative to orderlists
        orderlist_start = 0x1A70
        print(f"  Orderlists start at: ${orderlist_start:04X}")
        if max_ptr < orderlist_start:
            print(f"  [OK] All pointers BEFORE orderlists (sequences should come first)")
        else:
            print(f"  [PROBLEM] Some pointers AFTER orderlists")
        print()
        print("=" * 70)
        print()

if __name__ == '__main__':
    main()
