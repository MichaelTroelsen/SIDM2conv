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


def build_instrument_table_from_events(voices: Dict[int, List]) -> Tuple[List[List[int]], Dict]:
    """
    Build instrument table from runtime ADSR values.

    Args:
        voices: Dict mapping voice number to list of events

    Returns:
        (instrument_table, adsr_to_index) tuple
        - instrument_table: List of 8-byte instrument entries
        - adsr_to_index: Dict mapping (ad, sr) tuple to instrument index
    """
    # Collect unique ADSR combinations
    adsr_values = set()
    for voice_events in voices.values():
        for event in voice_events:
            adsr = event.get('adsr')
            if adsr is not None:
                ad = (adsr >> 8) & 0xFF  # High byte = AD
                sr = adsr & 0xFF          # Low byte = SR
                adsr_values.add((ad, sr))

    # Sort for deterministic output
    adsr_values = sorted(adsr_values)

    # Build instrument table (8 bytes per entry)
    instrument_table = []
    adsr_to_index = {}

    for idx, (ad, sr) in enumerate(adsr_values):
        # Format: [AD, SR, wave_count_speed, filter_setting, filter_ptr, pulse_ptr, pulse_prop, wave_ptr]
        instrument_entry = [
            ad,      # Byte 0: Attack/Decay
            sr,      # Byte 1: Sustain/Release
            0x00,    # Byte 2: Wave count speed (default)
            0x00,    # Byte 3: Filter setting (default)
            0x00,    # Byte 4: Filter table pointer (default)
            0x00,    # Byte 5: Pulse table pointer (will be updated later)
            0x00,    # Byte 6: Pulse property (default)
            0x00     # Byte 7: Wave table pointer (default)
        ]
        instrument_table.append(instrument_entry)
        adsr_to_index[(ad, sr)] = idx

    # Add default instrument if none found
    if not instrument_table:
        instrument_table.append([0x0F, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        adsr_to_index[(0x0F, 0x00)] = 0

    print(f"Built instrument table: {len(instrument_table)} instruments from {len(adsr_values)} unique ADSR combinations")
    return instrument_table, adsr_to_index


def build_pulse_table_from_events(voices: Dict[int, List]) -> Tuple[List[List[int]], Dict]:
    """
    Build pulse table from runtime pulse values.

    Args:
        voices: Dict mapping voice number to list of events

    Returns:
        (pulse_table, pulse_to_index) tuple
        - pulse_table: List of 4-byte pulse entries
        - pulse_to_index: Dict mapping pulse value to pulse table index
    """
    # Collect unique pulse values
    pulse_values = set()
    for voice_events in voices.values():
        for event in voice_events:
            pulse = event.get('pulse')
            if pulse is not None:
                pulse_values.add(pulse)

    # Sort for deterministic output
    pulse_values = sorted(pulse_values)

    # Build pulse table (4 bytes per entry)
    pulse_table = []
    pulse_to_index = {}

    for idx, pulse_val in enumerate(pulse_values):
        # Extract hi and lo bytes from 12-bit pulse value
        pulse_hi = (pulse_val >> 8) & 0x0F
        pulse_lo = pulse_val & 0xFF

        # Pack into nibbles as per format: hi nibble=lo byte, lo nibble=hi byte
        packed_value = (pulse_lo & 0xF0) | pulse_hi

        # Format: [initial_value, delta, duration, next]
        pulse_entry = [
            packed_value,  # Byte 0: Initial pulse value (packed)
            0x00,          # Byte 1: Add/subtract value (no modulation)
            0x00,          # Byte 2: Duration (loop to self)
            idx * 4        # Byte 3: Next entry (loop to self, Y-indexed)
        ]
        pulse_table.append(pulse_entry)
        pulse_to_index[pulse_val] = idx

    # Add default pulse entry if none found
    if not pulse_table:
        pulse_table.append([0x08, 0x00, 0x00, 0x00])  # Default pulse $0800
        pulse_to_index[0x800] = 0

    print(f"Built pulse table: {len(pulse_table)} entries from {len(pulse_values)} unique pulse values")
    return pulse_table, pulse_to_index


def build_filter_table() -> List[List[int]]:
    """
    Build minimal filter table (siddump doesn't capture filter values yet).

    Returns:
        filter_table: List of 4-byte filter entries
    """
    # Create minimal default filter table
    # Format: [filter_value, count, duration, next]
    filter_table = [
        [0xFF, 0x00, 0x00, 0x00],  # Entry 0: Keep current, no modulation
    ]

    print(f"Built filter table: {len(filter_table)} default entries")
    return filter_table


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


def convert_pattern_to_sequence(pattern: List[Dict], default_instrument: int = 0, use_waveform_gates: bool = True,
                               adsr_to_index: Optional[Dict] = None, pulse_to_index: Optional[Dict] = None) -> List[List[int]]:
    """
    Convert a pattern to SF2 sequence format with enhanced gate detection.

    SF2 uses a gate on/off system:
    - 0x7F in note column = end marker
    - 0x7E in note column = gate on (+++)
    - 0x80 in note column = gate off (---)
    - 0x80+ in instrument/command = no change (--)

    Args:
        pattern: List of events in pattern (from siddump with waveform data)
        default_instrument: Default instrument number
        use_waveform_gates: Use waveform register data for gate detection
        adsr_to_index: Dict mapping (ad, sr) to instrument index
        pulse_to_index: Dict mapping pulse value to pulse table index

    Returns:
        List of [instrument, command, note] entries
    """
    sequence = []

    # Special markers
    NO_CHANGE = 0x80  # -- (no change marker for instrument/command)
    GATE_ON = 0x7E    # +++ (gate on)
    GATE_OFF = 0x80   # --- (gate off)
    END_MARKER = 0x7F # End of sequence
    GATE_BIT = 0x01   # SID waveform register gate bit

    prev_gate_state = False
    prev_waveform = 0
    prev_instrument = default_instrument

    for i, event in enumerate(pattern):
        note_num = parse_note_string(event['note'])
        waveform = event.get('wave', 0) if use_waveform_gates else 0

        # Extract gate bit from waveform register
        current_gate = bool(waveform & GATE_BIT) if use_waveform_gates else True

        # Detect waveform changes (excluding gate bit)
        waveform_changed = (waveform & 0xFE) != (prev_waveform & 0xFE) if use_waveform_gates else False

        # Determine instrument from ADSR value if mappings provided
        instrument = default_instrument
        if adsr_to_index is not None and event.get('adsr') is not None:
            adsr = event['adsr']
            ad = (adsr >> 8) & 0xFF
            sr = adsr & 0xFF
            instrument = adsr_to_index.get((ad, sr), default_instrument)

        if note_num is not None:
            # Insert gate-off if we were in gate-on state and either:
            # - Gate bit changed to 0
            # - Waveform changed (requires gate reset)
            # - Instrument changed (requires gate reset)
            instrument_changed = (instrument != prev_instrument)
            if prev_gate_state and (not current_gate or waveform_changed or instrument_changed):
                sequence.append([NO_CHANGE, NO_CHANGE, GATE_OFF])
                prev_gate_state = False

            # Add note trigger with instrument and command
            sequence.append([instrument, 0x00, note_num])
            prev_instrument = instrument

            # Add gate on if gate bit is set or we're starting a new note
            if current_gate or not use_waveform_gates:
                sequence.append([NO_CHANGE, NO_CHANGE, GATE_ON])
                prev_gate_state = True

        # Detect gate-off from waveform register changes
        elif use_waveform_gates and prev_gate_state and not current_gate:
            sequence.append([NO_CHANGE, NO_CHANGE, GATE_OFF])
            prev_gate_state = False

        prev_waveform = waveform

    # Add end marker
    if sequence:
        sequence.append([0x00, 0x00, END_MARKER])

    return sequence


def extract_sequences_from_siddump(sid_file: str, seconds: int = 30, max_sequences: int = 39) -> Tuple[List, List, Dict]:
    """
    Extract sequences, orderlists, and tables from SID file using siddump.

    Args:
        sid_file: Path to SID file
        seconds: Seconds to capture
        max_sequences: Maximum number of sequences to extract

    Returns:
        (sequences, orderlists, tables) tuple
        sequences: List of sequences (each is list of [inst, cmd, note])
        orderlists: List of 3 orderlists (one per voice)
        tables: Dict with 'instruments', 'pulse', 'filter' keys
    """
    print(f"Running siddump on {sid_file}...")

    # Run siddump
    siddump_output = run_siddump(sid_file, seconds)
    if not siddump_output:
        print("Failed to get siddump output")
        return [], [], {}

    # Parse output
    voices = parse_siddump_output(siddump_output)

    print(f"Parsed {sum(len(v) for v in voices.values())} total events")
    for voice_num, events in voices.items():
        note_events = [e for e in events if e['note'] != "..."]
        print(f"  Voice {voice_num}: {len(events)} events ({len(note_events)} with notes)")

    # Build tables from runtime data
    print("\nBuilding tables from runtime data...")
    instrument_table, adsr_to_index = build_instrument_table_from_events(voices)
    pulse_table, pulse_to_index = build_pulse_table_from_events(voices)
    filter_table = build_filter_table()

    tables = {
        'instruments': instrument_table,
        'pulse': pulse_table,
        'filter': filter_table
    }

    # Detect patterns for each voice
    all_sequences = []
    orderlists = []
    global_seq_offset = 0  # Track global sequence index offset
    voice_sequence_counts = []  # Track how many sequences each voice contributed

    for voice_num in range(3):
        voice_events = voices[voice_num]
        patterns = detect_patterns(voice_events)

        print(f"Voice {voice_num}: detected {len(patterns)} patterns")

        # Convert patterns to sequences with runtime-built table mappings
        voice_sequences = []
        for pattern in patterns:
            seq = convert_pattern_to_sequence(pattern, adsr_to_index=adsr_to_index, pulse_to_index=pulse_to_index)
            if seq:
                voice_sequences.append(seq)

        voice_sequence_counts.append(len(voice_sequences))
        all_sequences.extend(voice_sequences)

    # Truncate sequences FIRST if too many
    total_sequences = len(all_sequences)
    if total_sequences > max_sequences:
        print(f"Warning: {total_sequences} sequences detected, truncating to {max_sequences}")
        all_sequences = all_sequences[:max_sequences]
    else:
        # Pad to max_sequences if too few
        while len(all_sequences) < max_sequences:
            all_sequences.append([[0x00, 0x00, 0x7F]])  # Empty sequence

    # Now create orderlists with correct truncation
    global_seq_offset = 0
    for voice_num in range(3):
        # Calculate how many sequences from this voice are in the final list
        voice_seq_count = voice_sequence_counts[voice_num]
        sequences_remaining = max(0, len(all_sequences) - global_seq_offset)
        available_sequences = min(voice_seq_count, sequences_remaining)

        # Create orderlist for sequences that actually exist
        orderlist = []
        for i in range(available_sequences):
            orderlist.append(0xA0)  # Default transpose
            orderlist.append(global_seq_offset + i)  # Use global index!
        orderlist.append(0x7F)  # End marker

        orderlists.append(orderlist)
        global_seq_offset += available_sequences  # Only advance by what we actually used!

    print(f"Extracted {len(all_sequences)} sequences total")
    print(f"Runtime-built tables: {len(instrument_table)} instruments, {len(pulse_table)} pulse entries, {len(filter_table)} filter entries")

    return all_sequences, orderlists, tables


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
