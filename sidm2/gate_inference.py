"""Enhanced gate inference for SID to SF2 conversion.

This module provides waveform-based gate detection by analyzing actual
SID register writes from siddump output. This improves accuracy by inferring
SF2 gate markers (0x7E gate-on, 0x80 gate-off) from Laxity's implicit gate
control (waveform register bit 0).

Gate Detection Strategy:
1. Monitor waveform control register (SID $04, $0B, $12)
2. Detect gate bit changes (bit 0: 0=off, 1=on)
3. Correlate with frequency changes for note triggers
4. Insert SF2 gate markers at proper timing

Version: 1.5.0
Date: 2025-12-12
Author: SIDM2 Project

Usage:
    from sidm2.gate_inference import WaveformGateAnalyzer

    analyzer = WaveformGateAnalyzer(siddump_events)
    enhanced_sequence = analyzer.infer_gates(sequence_events)
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from .models import SequenceEvent

# SF2 gate control markers
SF2_GATE_ON = 0x7E    # +++ (sustain)
SF2_GATE_OFF = 0x80   # --- (release)
SF2_END = 0x7F        # End marker
SF2_NO_CHANGE = 0x80  # No change in instrument/command

# SID waveform control bits
GATE_BIT = 0x01       # Bit 0 = gate
TEST_BIT = 0x08       # Bit 3 = test (resets oscillator)
TRIANGLE = 0x10       # Bit 4 = triangle waveform
SAWTOOTH = 0x20       # Bit 5 = sawtooth waveform
PULSE = 0x40          # Bit 6 = pulse waveform
NOISE = 0x80          # Bit 7 = noise waveform


@dataclass
class WaveformEvent:
    """Represents a waveform control register write from siddump."""
    frame: int          # Frame number
    voice: int          # Voice number (0-2)
    waveform: int       # Waveform control byte
    frequency: int      # Frequency value (0-65535)
    note: Optional[str] # Note string from siddump (e.g., "C-3")

    @property
    def gate_on(self) -> bool:
        """Check if gate bit is set."""
        return bool(self.waveform & GATE_BIT)

    @property
    def test_on(self) -> bool:
        """Check if test bit is set (hard restart)."""
        return bool(self.waveform & TEST_BIT)

    @property
    def waveform_type(self) -> int:
        """Get waveform type (without gate bit)."""
        return self.waveform & 0xFE  # Mask out gate bit


class WaveformGateAnalyzer:
    """Analyzes siddump waveform data to infer gate markers."""

    def __init__(self, siddump_data: Optional[Dict] = None):
        """Initialize analyzer with optional siddump data.

        Args:
            siddump_data: Parsed siddump output (from siddump_extractor)
        """
        self.siddump_data = siddump_data or {}
        self.gate_history: Dict[int, List[Tuple[int, bool]]] = {
            0: [],  # Voice 0 gate history: [(frame, gate_on), ...]
            1: [],  # Voice 1
            2: []   # Voice 2
        }

        if siddump_data:
            self._build_gate_history()

    def _build_gate_history(self):
        """Build gate on/off history from siddump data."""
        for voice_num in range(3):
            if voice_num not in self.siddump_data:
                continue

            events = self.siddump_data[voice_num]
            prev_gate = False

            for event in events:
                waveform = event.get('wave', 0)
                frame = event.get('frame', 0)

                # Extract gate bit
                gate_on = bool(waveform & GATE_BIT)

                # Record gate changes
                if gate_on != prev_gate:
                    self.gate_history[voice_num].append((frame, gate_on))
                    prev_gate = gate_on

    def detect_gate_transitions(self, voice: int, start_frame: int, end_frame: int) -> List[Tuple[int, bool]]:
        """Detect gate transitions within a frame range.

        Args:
            voice: Voice number (0-2)
            start_frame: Start frame
            end_frame: End frame

        Returns:
            List of (frame, gate_on) tuples
        """
        transitions = []

        for frame, gate_on in self.gate_history.get(voice, []):
            if start_frame <= frame <= end_frame:
                transitions.append((frame, gate_on))

        return transitions

    def infer_gates_simple(self, events: List[SequenceEvent]) -> List[SequenceEvent]:
        """Enhanced version of simple gate inference.

        Improves upon sequence_translator._insert_gate_markers() by:
        1. Detecting note changes (not just presence)
        2. Handling sustained notes properly
        3. Avoiding redundant gate markers

        Args:
            events: List of sequence events

        Returns:
            Events with enhanced gate markers
        """
        if not events:
            return events

        result = []
        prev_note = None
        prev_was_note = False
        in_sustain = False

        for event in events:
            # Check if this is a note (0-95) or control byte
            is_note = (event.note < SF2_GATE_ON and event.note != 0)
            is_gate_marker = event.note in (SF2_GATE_ON, SF2_GATE_OFF)

            # Detect note changes
            note_changed = is_note and (event.note != prev_note)

            # Insert gate-off before new notes if we were sustaining
            if note_changed and in_sustain:
                result.append(SequenceEvent(
                    instrument=SF2_NO_CHANGE,
                    command=SF2_NO_CHANGE,
                    note=SF2_GATE_OFF
                ))
                in_sustain = False

            # Add the event
            result.append(event)

            # Update state
            if is_note:
                prev_note = event.note
                prev_was_note = True

                # Add gate-on after note trigger to sustain
                if not in_sustain:
                    result.append(SequenceEvent(
                        instrument=SF2_NO_CHANGE,
                        command=SF2_NO_CHANGE,
                        note=SF2_GATE_ON
                    ))
                    in_sustain = True

            elif is_gate_marker:
                if event.note == SF2_GATE_ON:
                    in_sustain = True
                elif event.note == SF2_GATE_OFF:
                    in_sustain = False

        return result

    def infer_gates_from_waveforms(
        self,
        events: List[SequenceEvent],
        voice: int = 0,
        frames_per_event: int = 1
    ) -> List[SequenceEvent]:
        """Infer gate markers from actual waveform data.

        Uses siddump waveform history to detect gate changes and insert
        proper SF2 gate markers at the exact frames where the SID gate
        bit changed.

        Args:
            events: List of sequence events
            voice: Voice number to analyze (0-2)
            frames_per_event: Frames per sequence event (tempo-dependent)

        Returns:
            Events with waveform-inferred gate markers
        """
        if not self.siddump_data or voice not in self.siddump_data:
            # Fall back to simple inference
            return self.infer_gates_simple(events)

        result = []
        current_frame = 0

        for event in events:
            # Calculate frame range for this event
            start_frame = current_frame
            end_frame = current_frame + frames_per_event

            # Detect gate transitions in this range
            transitions = self.detect_gate_transitions(voice, start_frame, end_frame)

            # Insert gate markers based on transitions
            for frame, gate_on in transitions:
                if gate_on:
                    result.append(SequenceEvent(
                        instrument=SF2_NO_CHANGE,
                        command=SF2_NO_CHANGE,
                        note=SF2_GATE_ON
                    ))
                else:
                    result.append(SequenceEvent(
                        instrument=SF2_NO_CHANGE,
                        command=SF2_NO_CHANGE,
                        note=SF2_GATE_OFF
                    ))

            # Add the original event
            result.append(event)

            # Advance frame counter
            current_frame = end_frame

        return result

    def analyze_gate_accuracy(
        self,
        original_events: List[SequenceEvent],
        inferred_events: List[SequenceEvent]
    ) -> Dict[str, float]:
        """Compare inferred gates against expected gates for accuracy.

        Args:
            original_events: Original sequence with known gates
            inferred_events: Sequence with inferred gates

        Returns:
            Dictionary with accuracy metrics
        """
        orig_gates = sum(1 for e in original_events if e.note in (SF2_GATE_ON, SF2_GATE_OFF))
        inf_gates = sum(1 for e in inferred_events if e.note in (SF2_GATE_ON, SF2_GATE_OFF))

        # Simple match count
        matches = 0
        for orig, inf in zip(original_events, inferred_events):
            if orig.note == inf.note:
                matches += 1

        total = max(len(original_events), len(inferred_events))

        return {
            'total_events': total,
            'original_gates': orig_gates,
            'inferred_gates': inf_gates,
            'matching_events': matches,
            'accuracy': (matches / total * 100) if total > 0 else 0.0,
            'gate_detection_rate': (inf_gates / orig_gates * 100) if orig_gates > 0 else 0.0
        }


def enhance_sequence_with_gates(
    events: List[SequenceEvent],
    siddump_data: Optional[Dict] = None,
    voice: int = 0
) -> List[SequenceEvent]:
    """Convenience function to enhance a sequence with inferred gates.

    Args:
        events: Sequence events
        siddump_data: Optional siddump data for waveform-based inference
        voice: Voice number

    Returns:
        Enhanced sequence with gate markers
    """
    analyzer = WaveformGateAnalyzer(siddump_data)

    if siddump_data:
        return analyzer.infer_gates_from_waveforms(events, voice)
    else:
        return analyzer.infer_gates_simple(events)
