#!/usr/bin/env python3
"""
Siddump-based sequence extraction module.

Extracts actual played sequences from siddump runtime analysis.
More accurate than static pattern matching for complex music data.
"""

import subprocess
import re
import pickle
from typing import List, Tuple, Dict, Optional


# Note name to MIDI note number mapping
NOTE_MAP = {
    'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5,
    'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11
}


def run_siddump(sid_file: str, seconds: int = 30) -> Optional[str]:
    """
    Run siddump on a SID file and return the output.

    Args:
        sid_file: Path to SID file
        seconds: Number of seconds to capture

    Returns:
        Siddump output as string, or None on error
    """
    try:
        from pathlib import Path
        siddump_path = Path('tools') / 'siddump.exe'
        cmd = [str(siddump_path), sid_file, f'-t{seconds}']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            print(f"Siddump error: {result.stderr}")
            return None

        return result.stdout

    except subprocess.TimeoutExpired:
        print(f"Siddump timeout after 60 seconds")
        return None
    except Exception as e:
        print(f"Siddump execution error: {e}")
        return None


def parse_voice_column(column_text: str) -> Optional[Tuple]:
    """
    Parse a single voice column from siddump output.

    Two formats:
    1. "2E66  F-5 C1  13 .... 800" - Note format
    2. "0116 (+ 0116) 20 0F00 ..." - Delta format

    Returns:
        (freq, note_str, wave, adsr, pulse) or None
    """
    text = column_text.strip()

    if text.startswith("...."):
        return None

    parts = text.split()
    if len(parts) < 4:
        return None

    try:
        freq_str = parts[0]
        freq = int(freq_str, 16)

        # Check format type
        if parts[1].startswith("("):
            # Delta format: skip delta (2 parts), get waveform at index 3
            wave_idx = 3
            note_str = "..."
        else:
            # Note format: parts[1] = note, parts[3] = wave
            note_str = parts[1]
            wave_idx = 3

        wave = int(parts[wave_idx], 16)

        # Parse ADSR if present
        if len(parts) > wave_idx + 1:
            adsr_str = parts[wave_idx + 1]
            if adsr_str != "....":
                adsr = int(adsr_str, 16)
            else:
                adsr = None
        else:
            adsr = None

        # Parse pulse if present
        if len(parts) > wave_idx + 2:
            pulse_str = parts[wave_idx + 2]
            if pulse_str != "...":
                pulse = int(pulse_str, 16)
            else:
                pulse = None
        else:
            pulse = None

        return (freq, note_str, wave, adsr, pulse)

    except (ValueError, IndexError) as e:
        return None


def parse_siddump_output(siddump_text: str) -> Dict[int, List]:
    """
    Parse siddump output into voice events.

    Args:
        siddump_text: Raw siddump output

    Returns:
        Dict mapping voice number (0-2) to list of events
    """
    voices = {0: [], 1: [], 2: []}

    lines = siddump_text.split('\n')

    for line in lines:
        # Skip informational lines and empty lines
        if (not line.strip() or 'Load address' in line or
            'Init address' in line or 'Calling' in line or 'Middle C' in line or
            line.startswith('-----')):
            continue

        # Skip table header and separator lines
        if line.startswith('|') or line.startswith('+'):
            # Check if this is the header line (contains "Frame")
            if 'Frame' in line:
                continue
            # Check if this is a separator line (contains ---)
            if '---' in line:
                continue

        # Try to parse as table format
        if '|' in line:
            # This is a table row: | frame | voice1 | voice2 | voice3 | filter |
            parts = [p.strip() for p in line.split('|')]
            # Remove empty first and last elements
            parts = [p for p in parts if p]

            if len(parts) < 4:  # Need at least frame + 3 voices
                continue

            try:
                frame = int(parts[0])
            except ValueError:
                continue
        else:
            # Legacy format without pipes
            # Split by multiple spaces to get columns
            parts = re.split(r'\s{2,}', line.strip())

            if len(parts) < 4:  # Need at least frame + 3 voices
                continue

            try:
                frame = int(parts[0])
            except ValueError:
                continue

        # Parse each voice column
        for voice_num in range(3):
            if voice_num + 1 < len(parts):
                voice_data = parse_voice_column(parts[voice_num + 1])
                if voice_data:
                    freq, note_str, wave, adsr, pulse = voice_data
                    voices[voice_num].append({
                        'frame': frame,
                        'freq': freq,
                        'note': note_str,
                        'wave': wave,
                        'adsr': adsr,
                        'pulse': pulse
                    })

    return voices


def parse_note_string(note_str: str) -> Optional[int]:
    """
    Parse note string like "F-5" to SF2 note number.

    Args:
        note_str: Note string (e.g., "F-5", "C#4")

    Returns:
        MIDI note number (0-119) or None
    """
    if note_str == "..." or not note_str:
        return None

    # Format: "F-5" or "F#5"
    if len(note_str) == 3:
        note_name = note_str[0]
        sharp = note_str[1] == '#'
        octave = int(note_str[2])
    elif len(note_str) == 2:
        note_name = note_str[0]
        sharp = False
        octave = int(note_str[1])
    else:
        return None

    if note_name not in NOTE_MAP:
        return None

    note_num = octave * 12 + NOTE_MAP[note_name]
    if sharp:
        note_num += 1

    # Clamp to valid range
    return min(119, max(0, note_num))


def detect_patterns(voice_events: List[Dict]) -> List[List[Dict]]:
    """
    Detect repeating patterns in voice events.

    Args:
        voice_events: List of events for one voice

    Returns:
        List of patterns (each pattern is a list of events)
    """
    patterns = []
    current_pattern = []

    for event in voice_events:
        note_str = event['note']

        if note_str != "...":
            # Start of a new note event
            if current_pattern and len(current_pattern) >= 1:
                patterns.append(current_pattern)
            current_pattern = [event]
        else:
            # Continuation of current note
            if current_pattern:
                current_pattern.append(event)

    # Add final pattern
    if current_pattern:
        patterns.append(current_pattern)

    return patterns


def convert_pattern_to_sequence(pattern: List[Dict], default_instrument: int = 0) -> List[List[int]]:
    """
    Convert a pattern to SF2 sequence format.

    SF2 uses a gate on/off system:
    - 0x7F in note column = end marker
    - 0x7E in note column = gate on (+++)
    - 0x80 in note column = gate off (---)
    - 0x80+ in instrument/command = no change (--)

    Args:
        pattern: List of events in pattern
        default_instrument: Default instrument number

    Returns:
        List of [instrument, command, note] entries
    """
    sequence = []

    # Special markers
    NO_CHANGE = 0x80  # -- (no change marker for instrument/command)
    GATE_ON = 0x7E    # +++ (gate on)
    GATE_OFF = 0x80   # --- (gate off)
    END_MARKER = 0x7F # End of sequence

    for i, event in enumerate(pattern):
        note_num = parse_note_string(event['note'])
        if note_num is not None:
            # Add note trigger with instrument and command
            sequence.append([default_instrument, 0x00, note_num])

            # Add gate on (+++) to sustain the note
            # Use NO_CHANGE for instrument and command
            sequence.append([NO_CHANGE, NO_CHANGE, GATE_ON])

            # Check if this is the last note - if not, add gate off before next note
            is_last = (i == len(pattern) - 1)
            if not is_last:
                # Look ahead to see if next event has a note
                has_next_note = False
                for next_event in pattern[i+1:]:
                    if parse_note_string(next_event['note']) is not None:
                        has_next_note = True
                        break

                # Add gate off before next note
                if has_next_note:
                    sequence.append([NO_CHANGE, NO_CHANGE, GATE_OFF])

    # Add end marker
    if sequence:
        sequence.append([0x00, 0x00, END_MARKER])

    return sequence


def extract_sequences_from_siddump(sid_file: str, seconds: int = 30, max_sequences: int = 39) -> Tuple[List, List]:
    """
    Extract sequences and orderlists from SID file using siddump.

    Args:
        sid_file: Path to SID file
        seconds: Seconds to capture
        max_sequences: Maximum number of sequences to extract

    Returns:
        (sequences, orderlists) tuple
        sequences: List of sequences (each is list of [inst, cmd, note])
        orderlists: List of 3 orderlists (one per voice)
    """
    print(f"Running siddump on {sid_file}...")

    # Run siddump
    siddump_output = run_siddump(sid_file, seconds)
    if not siddump_output:
        print("Failed to get siddump output")
        return [], []

    # Parse output
    voices = parse_siddump_output(siddump_output)

    print(f"Parsed {sum(len(v) for v in voices.values())} total events")
    for voice_num, events in voices.items():
        note_events = [e for e in events if e['note'] != "..."]
        print(f"  Voice {voice_num}: {len(events)} events ({len(note_events)} with notes)")

    # Detect patterns for each voice
    all_sequences = []
    orderlists = []

    for voice_num in range(3):
        voice_events = voices[voice_num]
        patterns = detect_patterns(voice_events)

        print(f"Voice {voice_num}: detected {len(patterns)} patterns")

        # Convert patterns to sequences
        voice_sequences = []
        for pattern in patterns:
            seq = convert_pattern_to_sequence(pattern)
            if seq:
                voice_sequences.append(seq)

        # Create orderlist for this voice
        orderlist = []
        for seq_idx in range(len(voice_sequences)):
            orderlist.append(0xA0)  # Default transpose
            orderlist.append(seq_idx)
        orderlist.append(0x7F)  # End marker

        orderlists.append(orderlist)
        all_sequences.extend(voice_sequences)

    # Pad to max_sequences
    while len(all_sequences) < max_sequences:
        all_sequences.append([[0x00, 0x00, 0x7F]])  # Empty sequence

    # Truncate if too many
    all_sequences = all_sequences[:max_sequences]

    print(f"Extracted {len(all_sequences)} sequences total")

    return all_sequences, orderlists


def save_extracted_data(sequences: List, orderlists: List, output_file: str = "sf2_music_data_extracted.pkl"):
    """
    Save extracted sequences and orderlists to pickle file.

    Args:
        sequences: List of sequences
        orderlists: List of orderlists
        output_file: Output pickle file path
    """
    data = {
        'sequences': sequences,
        'orderlists': orderlists
    }

    with open(output_file, 'wb') as f:
        pickle.dump(data, f)

    print(f"Saved extracted data to {output_file}")


def load_extracted_data(input_file: str = "sf2_music_data_extracted.pkl") -> Tuple[List, List]:
    """
    Load extracted sequences and orderlists from pickle file.

    Args:
        input_file: Input pickle file path

    Returns:
        (sequences, orderlists) tuple
    """
    with open(input_file, 'rb') as f:
        data = pickle.load(f)

    return data['sequences'], data['orderlists']


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m sidm2.siddump_extractor <sid_file>")
        sys.exit(1)

    sid_file = sys.argv[1]

    # Extract sequences
    sequences, orderlists = extract_sequences_from_siddump(sid_file)

    # Save to pickle
    save_extracted_data(sequences, orderlists)

    print("\nExtraction complete!")
    print(f"Sequences: {len(sequences)}")
    print(f"Orderlists: {len(orderlists)}")
