#!/usr/bin/env python3
"""Quick test to verify orderlist fix in siddump_extractor."""

from sidm2.siddump_extractor import extract_sequences_from_siddump

# Test with one of the problematic files
sid_file = "SIDSF2player/Aint_Somebody.sid"

print(f"Testing orderlist generation for: {sid_file}")
print("="*80)

sequences, orderlists = extract_sequences_from_siddump(sid_file, seconds=10, max_sequences=256)

print(f"\nTotal sequences extracted: {len(sequences)}")
print(f"Number of orderlists: {len(orderlists)}")

# Parse orderlists to show sequence indices
for track_idx, orderlist in enumerate(orderlists):
    print(f"\nTrack {track_idx} orderlist (raw bytes: {len(orderlist)} bytes):")
    print(f"  Raw: {orderlist[:min(20, len(orderlist))]}...")  # Show first 20 bytes

    # Parse as transpose/seq_idx pairs
    seq_indices = []
    i = 0
    while i < len(orderlist) - 1:
        transpose = orderlist[i]
        if transpose == 0x7F or transpose == 0xFF:
            break
        seq_idx = orderlist[i + 1]
        seq_indices.append(seq_idx)
        i += 2

    print(f"  Sequence indices: {seq_indices[:20]}...")  # Show first 20 indices
    print(f"  Min: {min(seq_indices) if seq_indices else 'N/A'}, Max: {max(seq_indices) if seq_indices else 'N/A'}")

print(f"\n{'='*80}")
print("Expected behavior:")
print("  - Track 0 should reference sequences starting from 0")
print("  - Track 1 should reference sequences starting from where Track 0 ended")
print("  - Track 2 should reference sequences starting from where Track 1 ended")
print("\nIf all tracks show sequences starting from 0, the bug is NOT fixed!")
