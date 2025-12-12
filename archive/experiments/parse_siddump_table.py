#!/usr/bin/env python3
"""
Parse siddump TABLE format output into voice events.

Siddump outputs a formatted table with:
| Frame | Voice0 (Freq Note WF ADSR Pul) | Voice1 | Voice2 | Filter |
"""

import re
from collections import defaultdict

class VoiceEvent:
    """A musical event for one voice."""
    def __init__(self, frame, freq, note, wave, adsr, pulse):
        self.frame = frame
        self.freq = freq  # Hex value like 0x2E66
        self.note = note  # String like "F-5" or "..."
        self.wave = wave  # Waveform byte like 0x13
        self.adsr = adsr  # ADSR value like 0xA025
        self.pulse = pulse  # Pulse value like 0x800

    def __repr__(self):
        return f"Frame {self.frame}: Freq ${self.freq:04X}, Note {self.note}, Wave ${self.wave:02X}"


def parse_voice_column(column_text):
    """
    Parse a single voice column from siddump output.

    Two formats:
    1. "2E66  F-5 C1  13 .... 800" - Note format (Freq, Note, Abs, WF, ADSR, Pul)
    2. "0116 (+ 0116) 20 0F00 ..." - Delta format (Freq, Delta, WF, ADSR, Pul)

    Returns: (freq, note, wave, adsr, pulse) or None if no change ("....")
    """
    text = column_text.strip()

    # Check if this is a "no change" marker
    if text.startswith("...."):
        return None

    # Split on whitespace
    parts = text.split()
    if len(parts) < 3:
        return None

    try:
        # First element is always frequency (hex)
        freq_str = parts[0]
        freq = int(freq_str, 16) if freq_str != "...." else 0

        note_str = "..."
        wave_idx = 1  # Default: parts after freq

        # Check format type
        if parts[1].startswith("("):
            # Delta format: "0116 (+ 0116) 20 0F00 ..."
            # parts = ['0116', '(+', '0116)', '20', '0F00', '...']
            # Skip the delta (2 parts), get waveform at index 3
            wave_idx = 3
            note_str = "..."  # No note in delta format
        else:
            # Note format: "2E66  F-5 C1  13 .... 800"
            # parts[1] = note, parts[2] = abs, parts[3] = wave
            if parts[1] != "...":
                note_str = parts[1]
            wave_idx = 3  # Skip note and abs

        # Get wave, ADSR, pulse
        if wave_idx + 2 >= len(parts):
            return None

        wave_str = parts[wave_idx]
        adsr_str = parts[wave_idx + 1]
        pulse_str = parts[wave_idx + 2] if wave_idx + 2 < len(parts) else "..."

        wave = int(wave_str, 16) if wave_str != ".." else 0
        adsr = int(adsr_str, 16) if adsr_str != "...." else 0
        pulse = int(pulse_str, 16) if pulse_str not in ["...", "..."] else 0

        return (freq, note_str, wave, adsr, pulse)
    except (ValueError, IndexError) as e:
        return None


def parse_siddump_table(dump_file):
    """
    Parse siddump table format output file into voice events.

    Returns: dict {0: [events], 1: [events], 2: [events]}
    """
    voices = {0: [], 1: [], 2: []}

    # Track current state for each voice
    voice_state = {
        0: {'freq': 0, 'note': '...', 'wave': 0, 'adsr': 0, 'pulse': 0},
        1: {'freq': 0, 'note': '...', 'wave': 0, 'adsr': 0, 'pulse': 0},
        2: {'freq': 0, 'note': '...', 'wave': 0, 'adsr': 0, 'pulse': 0},
    }

    with open(dump_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # Skip header lines and separators
            if not line.startswith('|') or 'Frame' in line or '---' in line:
                continue

            # Parse table row
            # Format: | Frame | Voice0 | Voice1 | Voice2 | Filter |
            parts = line.split('|')
            if len(parts) < 6:
                continue

            try:
                frame_str = parts[1].strip()
                if not frame_str or not frame_str.isdigit():
                    continue
                frame = int(frame_str)

                # Parse each voice column
                for voice_num in range(3):
                    column_text = parts[2 + voice_num]
                    parsed = parse_voice_column(column_text)

                    if parsed:
                        freq, note, wave, adsr, pulse = parsed

                        # Update state
                        voice_state[voice_num]['freq'] = freq
                        voice_state[voice_num]['note'] = note
                        voice_state[voice_num]['wave'] = wave
                        if adsr != 0:  # Only update if not ....
                            voice_state[voice_num]['adsr'] = adsr
                        if pulse != 0:  # Only update if not ...
                            voice_state[voice_num]['pulse'] = pulse

                        # Create event
                        event = VoiceEvent(
                            frame,
                            voice_state[voice_num]['freq'],
                            voice_state[voice_num]['note'],
                            voice_state[voice_num]['wave'],
                            voice_state[voice_num]['adsr'],
                            voice_state[voice_num]['pulse']
                        )
                        voices[voice_num].append(event)

            except (ValueError, IndexError) as e:
                # Skip malformed lines
                continue

    return voices


def identify_note_patterns(voice_events, max_sequences=39):
    """
    Identify repeating note patterns in voice events.

    Returns:
    - sequences: List of unique note patterns
    - orderlist: List of sequence numbers for this voice
    """
    # Extract just the musical notes
    notes = []
    for event in voice_events:
        if event.note != '...':
            notes.append({
                'note': event.note,
                'wave': event.wave,
                'freq': event.freq
            })

    print(f"  Total note events: {len(notes)}")

    # For now, create a simple sequence structure
    # In a real implementation, we'd find repeating patterns

    # Group into chunks of 16 notes
    chunk_size = 16
    sequences = []
    orderlist = []

    for i in range(0, len(notes), chunk_size):
        chunk = notes[i:i + chunk_size]
        if len(sequences) < max_sequences:
            sequences.append(chunk)
            orderlist.append(len(sequences) - 1)
        else:
            # Ran out of sequences, reuse last one
            orderlist.append(len(sequences) - 1)

    return sequences, orderlist


def main():
    dump_file = 'stinsens_original.dump'

    print("=" * 70)
    print("PARSING SIDDUMP TABLE FORMAT")
    print("=" * 70)
    print()

    print("Step 1: Parse siddump table...")
    voices = parse_siddump_table(dump_file)

    for voice_num, events in voices.items():
        print(f"  Voice {voice_num}: {len(events)} events")
        if events:
            print(f"    First event: {events[0]}")
            print(f"    Last event:  {events[-1]}")

    print()

    print("Step 2: Identify note patterns...")
    all_sequences = []
    all_orderlists = []

    for voice_num in range(3):
        sequences, orderlist = identify_note_patterns(voices[voice_num])
        print(f"  Voice {voice_num}: {len(sequences)} sequences, orderlist length {len(orderlist)}")
        all_sequences.extend(sequences)
        all_orderlists.append(orderlist)

    print()
    print(f"Total sequences extracted: {len(all_sequences)}")

    # Show example sequence
    if all_sequences:
        print()
        print("Example - Sequence 0:")
        for i, note_entry in enumerate(all_sequences[0][:10]):
            print(f"  Entry {i}: {note_entry['note']} (Freq ${note_entry['freq']:04X}, Wave ${note_entry['wave']:02X})")

    print()
    print("=" * 70)
    print("SUCCESS!")
    print("=" * 70)


if __name__ == '__main__':
    main()
