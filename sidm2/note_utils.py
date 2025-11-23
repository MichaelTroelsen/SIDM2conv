"""
Note utilities for SID to SF2 conversion.

Provides Laxity note-to-name mapping and siddump note extraction.
"""

import re
from typing import List, Tuple, Optional, Dict

# Laxity note table - maps index (0x00-0x5D) to note name
# C-0 is index 0, C-1 is index 12, etc.
# Based on C64 frequency table: C D E F G A B across 8 octaves
NOTE_NAMES = [
    'C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-'
]


def laxity_note_to_name(note_index: int) -> str:
    """
    Convert a Laxity note index (0x00-0x5D) to a note name.

    Args:
        note_index: Laxity note index (0-93)

    Returns:
        Note name like 'C-0', 'G-5', 'B-7' or '---' for invalid
    """
    # Valid note range for SF2 is 0x00-0x5D (0-93)
    if note_index < 0 or note_index > 0x5D:
        return '---'

    octave = note_index // 12
    note = note_index % 12

    return f"{NOTE_NAMES[note]}{octave}"


def note_name_to_laxity(note_name: str) -> int:
    """
    Convert a note name to Laxity note index.

    Args:
        note_name: Note name like 'C-0', 'G-5', 'B-7'

    Returns:
        Laxity note index (0-93) or -1 for invalid
    """
    if len(note_name) < 3:
        return -1

    note_part = note_name[:2]
    octave_part = note_name[2:]

    try:
        note_idx = NOTE_NAMES.index(note_part)
        octave = int(octave_part)
        return octave * 12 + note_idx
    except (ValueError, IndexError):
        return -1


def extract_notes_from_siddump(dump_content: str) -> Dict[int, List[Tuple[str, str, str]]]:
    """
    Extract notes from siddump output.

    Args:
        dump_content: Raw siddump file content

    Returns:
        Dict mapping frame number to list of (ch1_note, ch2_note, ch3_note) tuples
        Note names like 'G-5', '---' for no note
    """
    notes_by_frame = {}

    for line in dump_content.split('\n'):
        # Look for frame lines: | 13 | data | data | data | filter |
        if not line.startswith('|'):
            continue

        if 'Frame' in line:  # Header line
            continue

        parts = line.split('|')
        if len(parts) < 5:
            continue

        # Parse frame number
        try:
            frame = int(parts[1].strip())
        except ValueError:
            continue

        # Parse each channel (parts 2, 3, 4)
        channel_notes = []
        for ch in range(3):
            if ch + 2 >= len(parts):
                channel_notes.append('---')
                continue

            ch_data = parts[ch + 2].strip()

            # Look for note patterns:
            # "3426  G-5 C3" - note with frequency
            # "(E-5 C0)" - parenthesized note
            # "....  ... .." - no change (dots)

            note = '---'

            # Match note with gate on (e.g., "G-5 C3")
            match = re.search(r'\s([A-G][#-]\d)\s+[0-9A-F]{2}\s', ch_data)
            if match:
                note = match.group(1)
            else:
                # Match parenthesized note (e.g., "(E-5 C0)")
                match = re.search(r'\(([A-G][#-]\d)\s+[0-9A-F]{2}\)', ch_data)
                if match:
                    note = match.group(1)

            channel_notes.append(note)

        notes_by_frame[frame] = tuple(channel_notes)

    return notes_by_frame


def extract_first_notes_from_siddump(dump_content: str, max_frames: int = 300) -> Dict[int, List[str]]:
    """
    Extract first occurrence of each unique note per channel from siddump.

    Returns:
        Dict with 'ch1', 'ch2', 'ch3' keys, each containing list of unique notes in order
    """
    all_notes = extract_notes_from_siddump(dump_content)

    result = {
        'ch1': [],
        'ch2': [],
        'ch3': []
    }

    seen = {'ch1': set(), 'ch2': set(), 'ch3': set()}

    for frame in sorted(all_notes.keys()):
        if frame > max_frames:
            break

        notes = all_notes[frame]
        for i, (ch_key, note) in enumerate(zip(['ch1', 'ch2', 'ch3'], notes)):
            if note != '---' and note not in seen[ch_key]:
                result[ch_key].append(note)
                seen[ch_key].add(note)

    return result


def extract_notes_from_sequences(sequences: list, max_notes: int = 100) -> List[str]:
    """
    Extract note names from parsed sequence events.

    Args:
        sequences: List of List[SequenceEvent]
        max_notes: Maximum notes to extract per sequence

    Returns:
        List of note names
    """
    notes = []

    for seq in sequences:
        seq_notes = []
        for event in seq:
            note = event.note
            # Skip control bytes (0x7E, 0x7F) and duration bytes (0x80-0x9F)
            if 0 <= note <= 0x5D:
                note_name = laxity_note_to_name(note)
                seq_notes.append(note_name)

            if len(seq_notes) >= max_notes:
                break

        notes.extend(seq_notes)

    return notes


def compare_notes(dump_notes: List[str], seq_notes: List[str]) -> Dict:
    """
    Compare notes from siddump with notes from sequences.

    Note: This is a simplified comparison. Siddump shows actual playback notes
    (after wave table transposition), while sequence notes are raw indices.

    Args:
        dump_notes: List of note names from siddump
        seq_notes: List of note names from sequences

    Returns:
        Dict with comparison statistics
    """
    dump_set = set(dump_notes)
    seq_set = set(seq_notes)

    common = dump_set & seq_set
    only_in_dump = dump_set - seq_set
    only_in_seq = seq_set - dump_set

    return {
        'dump_total': len(dump_notes),
        'dump_unique': len(dump_set),
        'seq_total': len(seq_notes),
        'seq_unique': len(seq_set),
        'common': len(common),
        'only_dump': list(sorted(only_in_dump)),
        'only_seq': list(sorted(only_in_seq)),
        'overlap_pct': (len(common) / len(dump_set) * 100) if dump_set else 0
    }


def generate_note_comparison_report(
    dump_content: str,
    sequences: list,
    max_frames: int = 300
) -> str:
    """
    Generate a note comparison report between siddump and sequences.

    Args:
        dump_content: Raw siddump file content
        sequences: List of List[SequenceEvent]
        max_frames: Maximum frames to analyze from siddump

    Returns:
        Formatted report string
    """
    # Extract notes from siddump
    dump_notes_by_frame = extract_notes_from_siddump(dump_content)

    # Get unique notes per channel from siddump
    dump_notes = extract_first_notes_from_siddump(dump_content, max_frames)

    # Extract notes from sequences
    seq_notes = extract_notes_from_sequences(sequences)

    # Count total siddump notes (non-'---')
    total_dump_notes = 0
    all_dump_notes = []
    for frame in sorted(dump_notes_by_frame.keys()):
        if frame > max_frames:
            break
        for note in dump_notes_by_frame[frame]:
            if note != '---':
                total_dump_notes += 1
                all_dump_notes.append(note)

    # Compare
    comparison = compare_notes(all_dump_notes, seq_notes)

    # Build report
    lines = []
    lines.append("Note Comparison Analysis")
    lines.append("-" * 50)

    lines.append(f"Siddump notes (first {max_frames} frames):")
    lines.append(f"  Total note events:    {comparison['dump_total']}")
    lines.append(f"  Unique notes:         {comparison['dump_unique']}")

    # Show first few notes per channel
    for ch_key in ['ch1', 'ch2', 'ch3']:
        ch_notes = dump_notes.get(ch_key, [])[:8]
        if ch_notes:
            ch_num = ch_key[-1]
            notes_str = ' '.join(ch_notes)
            lines.append(f"  Channel {ch_num} first:      {notes_str}")

    lines.append("")
    lines.append("Sequence notes (extracted):")
    lines.append(f"  Total note events:    {comparison['seq_total']}")
    lines.append(f"  Unique notes:         {comparison['seq_unique']}")

    # Show first few sequence notes
    if seq_notes:
        first_seq = ' '.join(seq_notes[:8])
        lines.append(f"  First notes:          {first_seq}")

    lines.append("")
    lines.append("Comparison:")
    lines.append(f"  Notes in both:        {comparison['common']}")
    lines.append(f"  Note overlap:         {comparison['overlap_pct']:.1f}%")

    if comparison['only_dump']:
        only_dump_str = ' '.join(comparison['only_dump'][:10])
        if len(comparison['only_dump']) > 10:
            only_dump_str += ' ...'
        lines.append(f"  Only in siddump:      {only_dump_str}")

    if comparison['only_seq']:
        only_seq_str = ' '.join(comparison['only_seq'][:10])
        if len(comparison['only_seq']) > 10:
            only_seq_str += ' ...'
        lines.append(f"  Only in sequences:    {only_seq_str}")

    lines.append("")

    return '\n'.join(lines)
