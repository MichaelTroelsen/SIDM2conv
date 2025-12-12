#!/usr/bin/env python3
"""
Analyze sequence table structure in SF2-packed file.

Based on documentation:
- Format: 3 bytes per entry [Instrument] [Command] [Note]
- Gate markers: 7E (gate on/off), 80 (gate off)
- Sequences are variable length, stacked contiguously
"""

def analyze_sequence_region(data, start, end):
    """Analyze potential sequence data."""
    print(f"\n=== Analyzing region 0x{start:04X} to 0x{end:04X} ({end-start} bytes) ===\n")

    # Parse as 3-byte entries
    sequences = []
    current_seq = []
    seq_start = start

    for i in range(start, end, 3):
        if i + 2 >= len(data):
            break

        instrument = data[i]
        command = data[i+1]
        note = data[i+2]

        entry = {
            'offset': i,
            'instrument': instrument,
            'command': command,
            'note': note
        }

        # Check for potential sequence boundary markers
        # Gate on/off: 7E, Gate off: 80, End markers: FF, FE
        if note in [0x7E, 0x80, 0xFF, 0xFE]:
            entry['marker'] = {
                0x7E: 'GATE_TOGGLE',
                0x80: 'GATE_OFF',
                0xFF: 'END/LOOP',
                0xFE: 'LOOP_MARKER'
            }.get(note, 'UNKNOWN')

        current_seq.append(entry)

        # If we hit a potential end marker, save this sequence
        if note == 0xFF or note == 0xFE:
            sequences.append({
                'start': seq_start,
                'length': len(current_seq),
                'entries': current_seq.copy()
            })
            current_seq = []
            seq_start = i + 3

    # Add any remaining entries
    if current_seq:
        sequences.append({
            'start': seq_start,
            'length': len(current_seq),
            'entries': current_seq
        })

    return sequences

def print_sequence_summary(sequences):
    """Print summary of found sequences."""
    print(f"Found {len(sequences)} potential sequences:\n")

    for idx, seq in enumerate(sequences):
        print(f"Sequence #{idx:02d}:")
        print(f"  Start offset: 0x{seq['start']:04X}")
        print(f"  Length: {seq['length']} entries ({seq['length']*3} bytes)")

        # Show first few entries
        print(f"  First entries:")
        for i, entry in enumerate(seq['entries'][:5]):
            marker = entry.get('marker', '')
            marker_str = f" [{marker}]" if marker else ""
            print(f"    0x{entry['offset']:04X}: {entry['instrument']:02X} {entry['command']:02X} {entry['note']:02X}{marker_str}")

        if seq['length'] > 5:
            print(f"    ... ({seq['length'] - 5} more entries)")
        print()

def find_gate_patterns(data, start, end):
    """Find all gate marker patterns (7E, 80)."""
    patterns = []

    for i in range(start, end):
        if data[i] == 0x7E or data[i] == 0x80:
            # Check context (3-byte entry alignment)
            offset_in_entry = (i - start) % 3

            patterns.append({
                'offset': i,
                'value': data[i],
                'marker': '7E (GATE_TOGGLE)' if data[i] == 0x7E else '80 (GATE_OFF)',
                'position': f'byte {offset_in_entry} of 3-byte entry'
            })

    return patterns

def main():
    sf2_packed = 'SID/Stinsens_Last_Night_of_89.sid'

    print(f"Reading: {sf2_packed}")
    with open(sf2_packed, 'rb') as f:
        data = f.read()

    print(f"File size: {len(data)} bytes")
    print(f"Load address: 0x{data[0x7C] | (data[0x7D] << 8):04X}")

    # Known boundaries
    tempo_end = 0x0A9A  # Tempo table ends here
    orderlist_start = 0x0AEE  # Voice 0 orderlist starts here

    print(f"\nKnown structure:")
    print(f"  Tempo table ends: 0x{tempo_end:04X}")
    print(f"  Orderlist starts: 0x{orderlist_start:04X}")
    print(f"  Gap between: {orderlist_start - tempo_end} bytes")

    # Search region: after PSID header (0x007E+2) until tempo table
    search_start = 0x0100  # Conservative start
    search_end = tempo_end

    # Find gate patterns
    print(f"\n=== Gate Pattern Search ===")
    gate_patterns = find_gate_patterns(data, search_start, search_end)
    print(f"Found {len(gate_patterns)} gate markers:\n")

    for p in gate_patterns[:10]:  # Show first 10
        print(f"  0x{p['offset']:04X}: {p['marker']} ({p['position']})")

    if len(gate_patterns) > 10:
        print(f"  ... ({len(gate_patterns) - 10} more)")

    # Analyze as sequence structure
    sequences = analyze_sequence_region(data, search_start, search_end)
    print_sequence_summary(sequences)

    # Check specific regions around gate markers
    if gate_patterns:
        first_gate = gate_patterns[0]['offset']
        last_gate = gate_patterns[-1]['offset']

        print(f"\n=== Sequence Region Analysis ===")
        print(f"First gate marker: 0x{first_gate:04X}")
        print(f"Last gate marker: 0x{last_gate:04X}")
        print(f"Potential sequence region: 0x{first_gate:04X} - 0x{last_gate:04X} ({last_gate - first_gate} bytes)")

        # Show hex dump around first gate marker
        print(f"\nHex dump around first gate marker (0x{first_gate:04X}):")
        dump_start = max(0, first_gate - 15)
        dump_end = min(len(data), first_gate + 48)

        for i in range(dump_start, dump_end, 16):
            hex_str = ' '.join(f'{data[j]:02X}' for j in range(i, min(i+16, dump_end)))
            print(f"  0x{i:04X}: {hex_str}")

if __name__ == '__main__':
    main()
