#!/usr/bin/env python3
"""
Convert siddump-extracted sequences to SF2 format.

SF2 sequences are 3-byte entries: [instrument] [command] [note]
"""

from parse_siddump_table import parse_siddump_table, identify_note_patterns

# Note name to SF2 note number mapping
# SF2 uses C-0 = 0, C#0 = 1, ..., B-9 = 119
NOTE_MAP = {
    'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5,
    'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11
}

def parse_note_string(note_str):
    """
    Parse a note string like "F-5" or "A#4" to SF2 note number.

    Returns: note number (0-119) or None if invalid
    """
    if note_str == "..." or not note_str:
        return None

    try:
        # Format: "F-5" or "F#5"
        if len(note_str) == 3:
            # "F-5"
            note_name = note_str[0]
            octave = int(note_str[2])
        elif len(note_str) == 4:
            # "F#5"
            note_name = note_str[0:2]
            octave = int(note_str[3])
        else:
            return None

        if note_name not in NOTE_MAP:
            return None

        # SF2 note number = octave * 12 + note_offset
        note_num = octave * 12 + NOTE_MAP[note_name]
        return min(119, max(0, note_num))  # Clamp to valid range

    except (ValueError, IndexError):
        return None


def convert_sequence_to_sf2(sequence, default_instrument=0):
    """
    Convert a sequence of note events to SF2 3-byte format.

    Args:
        sequence: List of note dicts {'note': 'F-5', 'wave': 0x13, 'freq': 0x2E66}
        default_instrument: Instrument number to use (0-31)

    Returns: List of [inst, cmd, note] entries
    """
    sf2_sequence = []

    for note_entry in sequence:
        note_str = note_entry['note']
        note_num = parse_note_string(note_str)

        if note_num is not None:
            # Create SF2 entry
            inst = default_instrument  # Use default for now
            cmd = 0x00  # No command by default
            sf2_sequence.append([inst, cmd, note_num])

    # Add end marker
    sf2_sequence.append([0x00, 0x00, 0x7F])

    return sf2_sequence


def pad_sequences_to_39(sequences):
    """
    Pad sequence list to exactly 39 sequences.

    If less than 39, add empty sequences.
    If more than 39, truncate.
    """
    # Truncate if too many
    if len(sequences) > 39:
        sequences = sequences[:39]

    # Pad if too few
    while len(sequences) < 39:
        # Empty sequence = just end marker
        sequences.append([[0x00, 0x00, 0x7F]])

    return sequences


def main():
    dump_file = 'stinsens_original.dump'

    print("=" * 70)
    print("CONVERTING SIDDUMP SEQUENCES TO SF2 FORMAT")
    print("=" * 70)
    print()

    print("Step 1: Parse siddump table...")
    voices = parse_siddump_table(dump_file)

    print(f"  Voice 0: {len(voices[0])} events")
    print(f"  Voice 1: {len(voices[1])} events")
    print(f"  Voice 2: {len(voices[2])} events")
    print()

    print("Step 2: Extract note sequences from each voice...")
    all_sequences = []
    all_orderlists = []
    sequence_offset = 0  # Track global sequence numbering

    for voice_num in range(3):
        sequences, orderlist = identify_note_patterns(voices[voice_num])
        print(f"  Voice {voice_num}: {len(sequences)} sequences, orderlist length {len(orderlist)}")

        # Adjust orderlist to use global sequence numbers
        adjusted_orderlist = [seq_num + sequence_offset for seq_num in orderlist]
        all_orderlists.append(adjusted_orderlist)

        all_sequences.extend(sequences)
        sequence_offset += len(sequences)

    print(f"\nTotal sequences: {len(all_sequences)}")
    print(f"Orderlists: {[len(ol) for ol in all_orderlists]}")
    print()

    print("Step 3: Convert to SF2 3-byte format...")
    sf2_sequences = []

    for i, seq in enumerate(all_sequences):
        sf2_seq = convert_sequence_to_sf2(seq, default_instrument=0)
        sf2_sequences.append(sf2_seq)
        print(f"  Sequence {i}: {len(sf2_seq)} entries")

    print()

    print("Step 4: Pad to 39 sequences...")
    sf2_sequences = pad_sequences_to_39(sf2_sequences)
    print(f"  Final count: {len(sf2_sequences)} sequences")
    print()

    # Show example sequence
    print("Example - SF2 Sequence 0:")
    for i, entry in enumerate(sf2_sequences[0][:10]):
        print(f"  Entry {i}: [{entry[0]:02X}] [{entry[1]:02X}] [{entry[2]:02X}]")
    print()

    # Convert orderlists to SF2 format (with transpose markers)
    print("Step 5: Create SF2 orderlists...")
    sf2_orderlists = []

    for voice_num, orderlist in enumerate(all_orderlists):
        # SF2 orderlist format: [transpose_marker] [sequence_number] ...
        # Default transpose = 0xA0 (no transpose)
        sf2_orderlist = []
        for seq_num in orderlist:
            sf2_orderlist.append(0xA0)  # No transpose
            sf2_orderlist.append(seq_num)

        # Add end marker
        sf2_orderlist.append(0xA0)
        sf2_orderlist.append(0x7F)  # End marker

        sf2_orderlists.append(sf2_orderlist)
        print(f"  Voice {voice_num}: {len(sf2_orderlist)} bytes")

    print()

    # Show example orderlist
    print("Example - SF2 Orderlist 0 (first 20 bytes):")
    for i in range(0, min(20, len(sf2_orderlists[0]))):
        print(f"  [{i:02d}]: {sf2_orderlists[0][i]:02X}")
    print()

    # Save sequences and orderlists to a file for later use
    import pickle
    with open('sf2_music_data_extracted.pkl', 'wb') as f:
        pickle.dump({
            'sequences': sf2_sequences,
            'orderlists': sf2_orderlists
        }, f)

    print("Saved music data to: sf2_music_data_extracted.pkl")
    print()

    print("=" * 70)
    print("SUCCESS!")
    print("=" * 70)
    print()
    print(f"Summary:")
    print(f"  - 39 sequences created (19 from music + 20 empty)")
    print(f"  - 3 orderlists created (one per voice)")
    print(f"  - Voice 0 orderlist: {len(sf2_orderlists[0])} bytes")
    print(f"  - Voice 1 orderlist: {len(sf2_orderlists[1])} bytes")
    print(f"  - Voice 2 orderlist: {len(sf2_orderlists[2])} bytes")
    print()
    print("Next step: Combine these sequences with the 8 already-extracted tables")
    print("to create a complete SF2 file.")


if __name__ == '__main__':
    main()
