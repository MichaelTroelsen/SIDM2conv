#!/usr/bin/env python3
"""
Analyze ALL potential sequence data regions in the SF2-packed SID file.

This script will:
1. Scan the entire SID file for regions that look like sequence data
2. Show the memory address and content of each candidate region
3. Allow the user to verify with RetroDebugger which is actually used

The user can then set breakpoints in RetroDebugger to see which memory
addresses the player actually reads from during playback.
"""

def mem_to_file_offset(mem_addr):
    """Convert memory address to file offset."""
    return 0x7E + (mem_addr - 0x1000)

def file_to_mem_addr(file_offset):
    """Convert file offset to memory address."""
    return 0x1000 + (file_offset - 0x7E)

def is_sequence_like(data, offset, min_entries=10):
    """Check if data at offset looks like sequence data."""
    valid_count = 0

    for i in range(min_entries):
        if offset + i*3 + 2 >= len(data):
            return False

        inst = data[offset + i*3]
        cmd = data[offset + i*3 + 1]
        note = data[offset + i*3 + 2]

        # Sequence entry validation
        inst_ok = inst <= 0x1F or inst >= 0x80 or inst in [0x7E, 0x7F]
        note_ok = note <= 0x60 or note in [0x7E, 0x7F, 0x80, 0xFF] or note >= 0xA0

        if inst_ok and note_ok:
            valid_count += 1

    return valid_count >= min_entries * 0.7  # 70% valid

def analyze_sid_file(sid_file):
    """Find all sequence-like regions in SID file."""
    print("=" * 70)
    print("SEQUENCE CANDIDATE ANALYSIS")
    print("=" * 70 + "\n")

    with open(sid_file, 'rb') as f:
        data = f.read()

    print(f"File: {sid_file}")
    print(f"Size: {len(data)} bytes\n")

    # Find all candidates
    candidates = []

    print("Scanning file for sequence-like patterns...\n")

    # Scan every 3 bytes (since sequences are 3-byte entries)
    for offset in range(0x100, len(data) - 100, 3):
        if is_sequence_like(data, offset, min_entries=15):
            mem_addr = file_to_mem_addr(offset)

            # Check if this is a new region (not part of previous candidate)
            if not candidates or offset - candidates[-1]['offset'] > 50:
                candidates.append({
                    'offset': offset,
                    'mem_addr': mem_addr
                })

    print(f"Found {len(candidates)} candidate regions:\n")

    # Analyze each candidate
    for i, cand in enumerate(candidates):
        offset = cand['offset']
        mem_addr = cand['mem_addr']

        print(f"=== CANDIDATE {i+1} ===")
        print(f"File offset: 0x{offset:04X}")
        print(f"Memory addr: ${mem_addr:04X}\n")

        # Show first 20 entries
        print("First 20 entries:")
        for j in range(20):
            if offset + j*3 + 2 >= len(data):
                break

            inst = data[offset + j*3]
            cmd = data[offset + j*3 + 1]
            note = data[offset + j*3 + 2]

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

            print(f"  +0x{j*3:04X}: [{inst:02X}] [{cmd:02X}] [{note_str}]")

        print("\n" + "-" * 70 + "\n")

    # Generate RetroDebugger instructions
    print("=" * 70)
    print("RETRODEBUGGER VERIFICATION INSTRUCTIONS")
    print("=" * 70 + "\n")

    print("1. Load the SID file in RetroDebugger:")
    print("   File -> Load SID -> SID/Stinsens_Last_Night_of_89.sid\n")

    print("2. Set read breakpoints at each candidate address:")
    for i, cand in enumerate(candidates):
        print(f"   Candidate {i+1}: ${cand['mem_addr']:04X}")

    print("\n3. Start playback and see which breakpoint hits first")
    print("4. The address that gets read during playback is where sequences start\n")

    print("5. Alternative: Use Memory View to examine each address:")
    for i, cand in enumerate(candidates):
        print(f"   Goto ${cand['mem_addr']:04X} - Candidate {i+1}")

    print("\n6. Look for the address that contains actual musical sequence data")
    print("   (instrument numbers, note values, command bytes)\n")

    return candidates

if __name__ == '__main__':
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'
    candidates = analyze_sid_file(sid_file)

    print("=" * 70)
    print(f"FOUND {len(candidates)} POTENTIAL SEQUENCE LOCATIONS")
    print("=" * 70)
    print("\nUse RetroDebugger to determine which is actually used by the player.\n")
