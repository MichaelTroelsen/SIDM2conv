#!/usr/bin/env python3
"""Extract SF2 sequences from MIDI note events.

This module converts MIDI note events (from Python emulator or SIDtool)
into SF2 sequence format for SID Factory II conversion.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class SF2SequenceEvent:
    """Represents a single event in an SF2 sequence."""
    frame: int
    command: int  # Command byte (note number, gate commands, etc.)
    param: Optional[int] = None  # Optional parameter for some commands


class MIDISequenceExtractor:
    """Extract SF2 sequences from MIDI note events."""

    # SF2 command bytes
    GATE_ON = 0x7E   # +++ gate on marker
    GATE_OFF = 0x80  # --- gate off marker
    END_MARKER = 0x7F  # End of sequence

    def __init__(self):
        """Initialize MIDI sequence extractor."""
        self.logger = logging.getLogger(__name__)

    def midi_note_to_sf2_note(self, midi_note: int) -> int:
        """Convert MIDI note number (0-127) to SF2 note index.

        SF2 uses a different note numbering than MIDI.
        For now, we'll use a direct mapping and adjust as needed.

        Args:
            midi_note: MIDI note number (0-127)

        Returns:
            SF2 note index
        """
        # Direct mapping for now - may need adjustment based on SF2 format
        # SF2 note range is typically 0-63 or similar
        # We'll need to transpose to match SF2's range

        # Assume middle C (MIDI 60) maps to SF2 note ~30
        sf2_note = midi_note - 30

        # Clamp to valid range
        if sf2_note < 0:
            sf2_note = 0
        elif sf2_note > 63:
            sf2_note = 63

        return sf2_note

    def extract_sequences_from_midi(self, midi_path: str) -> Tuple[List[SF2SequenceEvent],
                                                                     List[SF2SequenceEvent],
                                                                     List[SF2SequenceEvent]]:
        """Extract SF2 sequences from MIDI file (one per voice).

        Args:
            midi_path: Path to MIDI file

        Returns:
            Tuple of (voice1_seq, voice2_seq, voice3_seq)
        """
        try:
            import mido
        except ImportError:
            self.logger.error("mido library not found - cannot extract from MIDI")
            return ([], [], [])

        try:
            mid = mido.MidiFile(midi_path)
        except Exception as e:
            self.logger.error(f"Failed to load MIDI file {midi_path}: {e}")
            return ([], [], [])

        # Extract note events per track (voice)
        voice_sequences = [[], [], []]

        for track_idx, track in enumerate(mid.tracks):
            if track_idx >= 3:  # Only process first 3 tracks (SID voices)
                break

            current_time = 0
            sequence = []

            for msg in track:
                current_time += msg.time

                if msg.type == 'note_on' and msg.velocity > 0:
                    # Note ON event - add note number
                    sf2_note = self.midi_note_to_sf2_note(msg.note)

                    # Convert MIDI ticks to frames (assuming 25 ticks/beat, 1 tick/frame)
                    frame = current_time

                    sequence.append(SF2SequenceEvent(
                        frame=frame,
                        command=sf2_note
                    ))

                    # Add gate on marker
                    sequence.append(SF2SequenceEvent(
                        frame=frame,
                        command=self.GATE_ON
                    ))

                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    # Note OFF event - add gate off marker
                    frame = current_time

                    sequence.append(SF2SequenceEvent(
                        frame=frame,
                        command=self.GATE_OFF
                    ))

            # Add end marker
            if sequence:
                sequence.append(SF2SequenceEvent(
                    frame=sequence[-1].frame + 1,
                    command=self.END_MARKER
                ))

            voice_sequences[track_idx] = sequence

        self.logger.info(f"Extracted sequences: "
                        f"V1={len(voice_sequences[0])} events, "
                        f"V2={len(voice_sequences[1])} events, "
                        f"V3={len(voice_sequences[2])} events")

        return tuple(voice_sequences)

    def sequences_to_orderlist_format(self, sequences: Tuple[List[SF2SequenceEvent],
                                                              List[SF2SequenceEvent],
                                                              List[SF2SequenceEvent]]) -> dict:
        """Convert sequences to SF2 orderlist format.

        Args:
            sequences: Tuple of (voice1, voice2, voice3) sequences

        Returns:
            Dictionary with orderlist data suitable for SF2Writer
        """
        orderlist_data = {
            'voice1': [],
            'voice2': [],
            'voice3': []
        }

        voice_names = ['voice1', 'voice2', 'voice3']

        for voice_idx, sequence in enumerate(sequences):
            voice_name = voice_names[voice_idx]

            # Convert SF2SequenceEvent to simple list of command bytes
            # This matches the format expected by SF2Writer
            commands = [event.command for event in sequence]

            orderlist_data[voice_name] = commands

        return orderlist_data


def extract_sequences_from_midi_file(midi_path: str) -> dict:
    """Convenience function to extract sequences from MIDI file.

    Args:
        midi_path: Path to MIDI file

    Returns:
        Dictionary with orderlist data (voice1, voice2, voice3)
    """
    extractor = MIDISequenceExtractor()
    sequences = extractor.extract_sequences_from_midi(midi_path)
    return extractor.sequences_to_orderlist_format(sequences)
