#!/usr/bin/env python3
"""Test runtime table building on Broware."""

from sidm2.siddump_extractor import extract_sequences_from_siddump

sid_file = "SIDSF2player/Broware.sid"

print(f"Testing runtime table building on: {sid_file}")
print("="*80)

# Extract sequences with runtime table building
sequences, orderlists, tables = extract_sequences_from_siddump(sid_file, seconds=10, max_sequences=256)

print(f"\n{'-'*80}")
print(f"RUNTIME TABLE BUILDING RESULTS")
print(f"{'-'*80}")

print(f"\nSequences: {len(sequences)} extracted")
print(f"Orderlists: {len(orderlists)}")

print(f"\nInstrument Table: {len(tables['instruments'])} instruments")
for idx, inst in enumerate(tables['instruments'][:5]):  # Show first 5
    print(f"  Inst {idx}: AD=${inst[0]:02X} SR=${inst[1]:02X} pulse_ptr=${inst[5]:02X}")

print(f"\nPulse Table: {len(tables['pulse'])} entries")
for idx, pulse in enumerate(tables['pulse'][:5]):  # Show first 5
    print(f"  Pulse {idx}: value=${pulse[0]:02X} delta=${pulse[1]:02X} dur=${pulse[2]:02X} next=${pulse[3]:02X}")

print(f"\nFilter Table: {len(tables['filter'])} entries")
for idx, filt in enumerate(tables['filter']):
    print(f"  Filter {idx}: value=${filt[0]:02X} count=${filt[1]:02X} dur=${filt[2]:02X} next=${filt[3]:02X}")

print(f"\nOrderlists:")
for track_idx, orderlist in enumerate(orderlists):
    seq_indices = []
    i = 0
    while i < len(orderlist) - 1:
        transpose = orderlist[i]
        if transpose == 0x7F or transpose == 0xFF:
            break
        seq_idx = orderlist[i + 1]
        seq_indices.append(seq_idx)
        i += 2

    print(f"  Track {track_idx}: {len(seq_indices)} sequences, range [{min(seq_indices) if seq_indices else 'N/A'}..{max(seq_indices) if seq_indices else 'N/A'}]")

print(f"\n{'-'*80}")
print(f"Expected behavior:")
print(f"  - Instruments should contain unique ADSR combinations from runtime")
print(f"  - Pulse table should contain unique pulse values from runtime")
print(f"  - Orderlists should reference sequences across the full range")
print(f"  - NOT all orderlists pointing to sequence 0!")
print(f"{'-'*80}")
