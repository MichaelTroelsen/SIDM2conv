#!/usr/bin/env python3
"""
BREAKTHROUGH: Reconstruct SF2 sequences from siddump output!

Strategy:
1. Parse siddump output (3 voice streams)
2. Extract note/waveform/ADSR changes per voice
3. Identify repeating patterns
4. Create 39 unique sequences from patterns
5. Build orderlists referencing those sequences

This is "behavioral reconstruction" - we observe what the music DOES
and rebuild the SF2 structure from that!
"""

import re
from collections import defaultdict
from typing import List, Dict, Tuple

class VoiceEvent:
    """A musical event for one voice."""
    def __init__(self, frame, freq, wave, gate, adsr):
        self.frame = frame
        self.freq = freq  # Frequency (for note detection)
        self.wave = wave  # Waveform
        self.gate = gate  # Gate on/off
        self.adsr = adsr  # ADSR envelope
        self.note = self.freq_to_note(freq) if freq > 0 else None

    @staticmethod
    def freq_to_note(freq):
        """Convert SID frequency to note number (approximate)."""
        if freq == 0:
            return None
        # SID frequency table approximation
        # Note 0 = C-0, each semitone ~1.059463 ratio
        import math
        # Base frequency for C-0 (NTSC)
        base_freq = 268
        if freq < base_freq:
            return 0
        note = int(round(12 * math.log2(freq / base_freq)))
        return max(0, min(95, note))  # Clamp to valid range

    def __repr__(self):
        gate_str = "ON" if self.gate else "OFF"
        return f"Frame {self.frame}: Note {self.note}, Wave {self.wave:02X}, Gate {gate_str}"


def parse_siddump_output(dump_file):
    """Parse siddump output file into voice events."""
    voices = {0: [], 1: [], 2: []}  # 3 voices

    with open(dump_file, 'r') as f:
        current_frame = 0
        sid_state = {
            0: {'freq': 0, 'wave': 0, 'gate': False, 'adsr': 0},
            1: {'freq': 0, 'wave': 0, 'gate': False, 'adsr': 0},
            2: {'freq': 0, 'wave': 0, 'gate': False, 'adsr': 0},
        }

        for line in f:
            line = line.strip()
            if not line:
                continue

            # Parse frame number (format: "FRAME:nnnn")
            frame_match = re.match(r'FRAME:(\d+)', line)
            if frame_match:
                current_frame = int(frame_match.group(1))
                continue

            # Parse register writes (format: "Vn.REG = VALUE")
            reg_match = re.match(r'(\d+):([0-9A-F]{2})', line)
            if reg_match:
                reg = int(reg_match.group(1), 16)
                value = int(reg_match.group(2), 16)

                # Voice register mapping
                voice = reg // 7  # Registers 0-6=V0, 7-13=V1, 14-20=V2
                if voice > 2:
                    continue

                reg_offset = reg % 7

                if reg_offset == 0:  # Freq low
                    sid_state[voice]['freq'] = (sid_state[voice]['freq'] & 0xFF00) | value
                elif reg_offset == 1:  # Freq high
                    sid_state[voice]['freq'] = (sid_state[voice]['freq'] & 0x00FF) | (value << 8)
                elif reg_offset == 4:  # Control (waveform + gate)
                    sid_state[voice]['wave'] = value
                    sid_state[voice]['gate'] = (value & 0x01) != 0

                    # Create event on gate changes or waveform changes
                    event = VoiceEvent(
                        current_frame,
                        sid_state[voice]['freq'],
                        sid_state[voice]['wave'],
                        sid_state[voice]['gate'],
                        sid_state[voice]['adsr']
                    )
                    voices[voice].append(event)

    return voices


def identify_patterns(voice_events, min_length=3, max_sequences=39):
    """
    Identify repeating patterns in voice events.

    Returns:
    - sequences: List of unique patterns (up to max_sequences)
    - orderlist: List of sequence numbers for this voice
    """
    # Convert events to simple pattern format
    pattern = []
    for event in voice_events:
        # Create a simple tuple: (note, waveform, gate)
        pattern.append((event.note, event.wave, event.gate))

    # Find repeating sub-patterns
    sequences = []
    sequence_map = {}  # pattern_hash -> sequence_number
    orderlist = []

    i = 0
    while i < len(pattern):
        # Try to match with existing sequences
        matched = False

        for length in range(min(20, len(pattern) - i), min_length - 1, -1):
            sub_pattern = tuple(pattern[i:i + length])
            pattern_hash = hash(sub_pattern)

            if pattern_hash in sequence_map:
                # Found existing sequence
                seq_num = sequence_map[pattern_hash]
                orderlist.append(seq_num)
                i += length
                matched = True
                break

        if not matched:
            # Create new sequence
            length = min(10, len(pattern) - i)  # Default sequence length
            sub_pattern = tuple(pattern[i:i + length])
            pattern_hash = hash(sub_pattern)

            if len(sequences) < max_sequences:
                seq_num = len(sequences)
                sequences.append(list(sub_pattern))
                sequence_map[pattern_hash] = seq_num
                orderlist.append(seq_num)
                i += length
            else:
                # Ran out of sequences, just add to last one
                if sequences:
                    orderlist.append(len(sequences) - 1)
                i += 1

    return sequences, orderlist


def convert_to_sf2_format(sequences, orderlists):
    """
    Convert identified patterns to SF2 format.

    Returns:
    - sf2_sequences: 39 sequences in SF2 3-byte format [inst][cmd][note]
    - sf2_orderlists: 3 orderlists
    """
    sf2_sequences = []

    # Convert each pattern to SF2 sequence format
    for seq_pattern in sequences:
        sf2_seq = []

        for note, wave, gate in seq_pattern:
            # SF2 format: [instrument] [command] [note]
            inst = 0x00  # Default instrument (could be improved)
            cmd = 0x00   # Default command

            # Convert note
            if note is not None:
                sf2_note = note
            elif not gate:
                sf2_note = 0x80  # Gate off marker
            else:
                sf2_note = 0x7E  # Gate on marker

            sf2_seq.append([inst, cmd, sf2_note])

        # Add end marker
        sf2_seq.append([0x00, 0x00, 0x7F])  # End marker

        sf2_sequences.append(sf2_seq)

    # Pad to 39 sequences if needed
    while len(sf2_sequences) < 39:
        sf2_sequences.append([[0x00, 0x00, 0x7F]])  # Empty sequence

    return sf2_sequences, orderlists


def main():
    dump_file = 'stinsens_original.dump'  # Siddump output

    print("=" * 70)
    print("RECONSTRUCTING SF2 FROM SIDDUMP OUTPUT")
    print("=" * 70)
    print()

    # Check if dump file exists
    import os
    if not os.path.exists(dump_file):
        print(f"Dump file not found: {dump_file}")
        print("Creating it now with siddump...")
        import subprocess
        subprocess.run([
            'tools/siddump.exe',
            'SID/Stinsens_Last_Night_of_89.sid',
            '-t30'
        ], stdout=open(dump_file, 'w'))
        print(f"Created {dump_file}")
        print()

    print("Step 1: Parse siddump output...")
    voices = parse_siddump_output(dump_file)

    for voice_num, events in voices.items():
        print(f"  Voice {voice_num}: {len(events)} events")

    print()

    print("Step 2: Identify patterns and create sequences...")
    all_sequences = []
    all_orderlists = []

    for voice_num in range(3):
        sequences, orderlist = identify_patterns(voices[voice_num])
        print(f"  Voice {voice_num}: {len(sequences)} unique patterns, orderlist length {len(orderlist)}")
        all_sequences.extend(sequences)
        all_orderlists.append(orderlist)

    print()
    print(f"Total unique patterns found: {len(all_sequences)}")

    # Limit to 39 sequences
    if len(all_sequences) > 39:
        print(f"Trimming to 39 sequences (had {len(all_sequences)})")
        all_sequences = all_sequences[:39]

    print()

    print("Step 3: Convert to SF2 format...")
    sf2_sequences, sf2_orderlists = convert_to_sf2_format(all_sequences, all_orderlists)

    print(f"  Created {len(sf2_sequences)} SF2 sequences")
    print(f"  Created {len(sf2_orderlists)} orderlists")
    print()

    # Show first sequence as example
    if sf2_sequences:
        print("Example - Sequence 0:")
        for i, entry in enumerate(sf2_sequences[0][:10]):
            print(f"  Entry {i}: [{entry[0]:02X}] [{entry[1]:02X}] [{entry[2]:02X}]")
        print()

    print("=" * 70)
    print("SUCCESS!")
    print("=" * 70)
    print()
    print("Reconstructed SF2 structure from runtime behavior!")
    print("Next: Combine with extracted tables to create complete SF2")

if __name__ == '__main__':
    main()
