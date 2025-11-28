"""
Laxity NewPlayer v21 to SF2 Sequence Translator

This module provides the core translation layer for converting Laxity sequence
data to SID Factory II format. It handles:
- Parsing Laxity super commands with parameters
- Converting note indices via frequency table to SF2 note numbers
- Expanding duration bytes into multiple SF2 rows
- Inserting explicit gate markers
- Mapping commands to SF2 command table references

Part of Phase 1: Sequence Parser Rewrite (ACCURACY_ROADMAP)
Target: 9% → 50% overall accuracy
"""

import math
import logging
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

from sidm2.models import SequenceEvent

logger = logging.getLogger(__name__)

# Laxity NewPlayer v21 constants
LAXITY_FREQ_TABLE_ADDR = 0x1835  # Frequency table (96 notes × 2 bytes) - starts at $1835, not $1833!
LAXITY_FREQ_TABLE_SIZE = 96

# PAL C64 SID clock frequency
PAL_CLOCK_FREQ = 985248  # Hz

# SF2 control bytes
SF2_GATE_ON = 0x7E   # +++ sustain
SF2_GATE_OFF = 0x80  # --- release
SF2_END = 0x7F       # End marker
SF2_NO_CHANGE = 0x80 # No instrument/command change


@dataclass
class LaxityEvent:
    """Structured representation of a Laxity sequence event."""
    instrument: Optional[int] = None  # $A0-$BF or None
    command: Optional[int] = None      # $C0-$FF or None
    command_param: Optional[int] = None  # Parameter byte after command
    note: int = 0                      # $00-$5F (freq table index) or control byte
    duration: int = 1                  # Number of frames (from $80-$9F)

    def __repr__(self):
        parts = []
        if self.instrument is not None:
            parts.append(f"I:{self.instrument:02X}")
        if self.command is not None:
            parts.append(f"C:{self.command:02X}")
            if self.command_param is not None:
                parts.append(f"P:{self.command_param:02X}")
        parts.append(f"N:{self.note:02X}")
        if self.duration > 1:
            parts.append(f"D:{self.duration}")
        return f"LaxityEvent({' '.join(parts)})"


class LaxityFrequencyTable:
    """Handles Laxity frequency table extraction and note conversion."""

    def __init__(self, c64_data: bytes, load_addr: int):
        """
        Extract frequency table from Laxity player.

        Args:
            c64_data: C64 program data
            load_addr: Memory load address
        """
        self.frequencies = self._extract_frequency_table(c64_data, load_addr)
        logger.debug(f"Extracted {len(self.frequencies)} frequency table entries")

    def _extract_frequency_table(self, c64_data: bytes, load_addr: int) -> List[int]:
        """Extract 96-entry frequency table from $1833."""
        if load_addr > LAXITY_FREQ_TABLE_ADDR:
            logger.warning(f"Load address ${load_addr:04X} > freq table address ${LAXITY_FREQ_TABLE_ADDR:04X}")
            return []

        offset = LAXITY_FREQ_TABLE_ADDR - load_addr
        if offset + (LAXITY_FREQ_TABLE_SIZE * 2) > len(c64_data):
            logger.warning(f"Frequency table extends beyond data (offset ${offset:04X})")
            return []

        frequencies = []
        for i in range(LAXITY_FREQ_TABLE_SIZE):
            lo = c64_data[offset + i * 2]
            hi = c64_data[offset + i * 2 + 1]
            freq = lo | (hi << 8)
            frequencies.append(freq)

        return frequencies

    def frequency_to_sf2_note(self, frequency: int) -> int:
        """
        Convert SID frequency value to SF2 note number.

        SID frequency formula: freq = (note_hz * clock_hz) / 16777216
        Reverse: note_hz = (freq * clock_hz) / 16777216
        MIDI note: 12 * log2(note_hz / 440) + 69

        Args:
            frequency: SID frequency register value (0-65535)

        Returns:
            SF2 note number (0x00-0x5D for C-0 to B-7)
        """
        if frequency == 0:
            return 0

        # Convert SID frequency to Hz
        freq_hz = (frequency * PAL_CLOCK_FREQ) / 16777216.0

        if freq_hz <= 0:
            return 0

        # Convert Hz to MIDI note number (A4 = 440 Hz = MIDI 69)
        note_float = 12.0 * math.log2(freq_hz / 440.0) + 69.0
        note = int(round(note_float))

        # Clamp to SF2 range (C-0 to B-7 = 0 to 93 = 0x00 to 0x5D)
        return max(0, min(93, note))

    def translate_laxity_note(self, lax_note: int) -> int:
        """
        Translate Laxity note index to SF2 note number.

        Args:
            lax_note: Laxity note value ($00-$5F or control byte)

        Returns:
            SF2 note number or control byte
        """
        # Control bytes pass through
        # NOTE: $00 is a valid note (C-0), NOT a rest! Rest is $7E (SF2_GATE_ON)
        if lax_note == SF2_GATE_ON:
            return SF2_GATE_ON  # Gate continue
        elif lax_note == SF2_END:
            return SF2_END  # End marker
        elif lax_note >= 0x80:
            # Duration or other control byte - should not appear as note
            logger.warning(f"Unexpected control byte as note: ${lax_note:02X}")
            return SF2_GATE_ON

        # Regular note - lookup in frequency table
        if lax_note >= len(self.frequencies):
            logger.warning(f"Note index ${lax_note:02X} exceeds table size {len(self.frequencies)}")
            return 0x5D  # Clamp to B-7

        frequency = self.frequencies[lax_note]
        sf2_note = self.frequency_to_sf2_note(frequency)

        return sf2_note


class LaxitySequenceParser:
    """Parse raw Laxity sequence bytes into structured events."""

    def __init__(self, command_table: List[tuple] = None):
        """
        Initialize parser with optional command table.

        Args:
            command_table: List of (cmd_byte, param_byte) tuples indexed by command index.
                          When a $C0-$FF byte is encountered, it's used as an index into
                          this table to get the actual command data.
        """
        self.command_table = command_table or []

    def parse_sequence(self, raw_bytes: bytes) -> List[LaxityEvent]:
        """
        Parse Laxity sequence with super commands.

        Laxity sequence format:
        - Instrument: $A0-$BF
        - Commands with parameters:
          * $0x yy = Slide up
          * $2x yy = Slide down
          * $60 xy = Vibrato
          * $8x xx = Portamento
          * $9x yy = Set ADSR (persistent)
          * $ax yy = Set ADSR (local)
          * $c0 xx = Set wave pointer
          * $dx yy = Filter/pulse control
          * $e0 xx = Set speed
          * $f0 xx = Set volume
        - Duration: $80-$9F (1-32 frames)
        - Note: $00-$5F (frequency table index) or $7E/$7F
        - End: $7F

        Args:
            raw_bytes: Raw Laxity sequence data

        Returns:
            List of parsed LaxityEvent objects
        """
        events = []
        pos = 0

        current_instrument = None
        current_command = None
        current_command_param = None
        current_duration = 1

        while pos < len(raw_bytes):
            byte = raw_bytes[pos]

            # End marker
            if byte == SF2_END:
                events.append(LaxityEvent(note=SF2_END, duration=1))
                break

            # Instrument change ($A0-$BF)
            elif 0xA0 <= byte <= 0xBF:
                current_instrument = byte
                pos += 1

            # Duration ($80-$9F)
            elif 0x80 <= byte <= 0x9F:
                current_duration = (byte & 0x1F) + 1  # $80 = 1 frame, $9F = 32 frames
                pos += 1

            # Laxity command bytes ($C0-$FF)
            # These are command INDICES into the command table, not commands with inline params
            # The index is (byte & $3F) - actual command data comes from the command table
            elif self._is_laxity_command(byte):
                cmd_idx = byte & 0x3F  # Get command table index

                # Look up actual command in command table
                if self.command_table and cmd_idx < len(self.command_table):
                    cmd_data = self.command_table[cmd_idx]
                    current_command = cmd_data[0]  # Actual command byte from table
                    current_command_param = cmd_data[1]  # Parameter byte from table
                    logger.debug(f"Command index ${byte:02X} -> cmd ${current_command:02X} param ${current_command_param:02X}")
                else:
                    # No command table or index out of range - store the index byte
                    current_command = byte
                    current_command_param = None
                    logger.warning(f"Command index ${byte:02X} (idx={cmd_idx}) not in command table (len={len(self.command_table)})")

                pos += 1

            # Note ($00-$5F or $7E for gate-on)
            elif byte <= 0x5F or byte == SF2_GATE_ON:
                event = LaxityEvent(
                    instrument=current_instrument,
                    command=current_command,
                    command_param=current_command_param,
                    note=byte,
                    duration=current_duration
                )
                events.append(event)

                # Reset per-note state
                current_instrument = None
                current_command = None
                current_command_param = None
                current_duration = 1

                pos += 1

            else:
                # Unexpected byte - could be another command format or data error
                logger.warning(f"Unexpected byte ${byte:02X} at offset ${pos:04X}")
                pos += 1

        logger.debug(f"Parsed {len(events)} Laxity events from {len(raw_bytes)} bytes")
        return events

    def _is_laxity_command(self, byte: int) -> bool:
        """
        Check if byte is a Laxity command byte.

        According to Laxity player analysis (W11B5), the sequence parser uses:
            bmi W11D1  ; If >= $80: command/instrument

        This means only bytes >= $80 are commands/instruments.
        Bytes $00-$7F are notes (or control bytes like $7E gate, $7F end).

        Commands in Laxity are handled INSIDE the wave table, not in sequences!
        The $0x/$2x slide commands that were here were INCORRECT - those are
        actually valid note bytes (C-0 through D#2).
        """
        # Only bytes >= $80 can be commands in Laxity sequence format
        # $80-$9F = duration bytes (handled separately)
        # $A0-$BF = instrument select (instrument = byte & 0x1F)
        # $C0-$FF = actual command bytes
        return byte >= 0xC0


class SF2SequenceBuilder:
    """Build SF2 sequences from Laxity events."""

    def __init__(self, freq_table: LaxityFrequencyTable, command_table: Dict[Tuple[int, int, int], int]):
        """
        Initialize SF2 sequence builder.

        Args:
            freq_table: Laxity frequency table for note translation
            command_table: Mapping of (type, param1, param2) -> SF2 command index
        """
        self.freq_table = freq_table
        self.command_table = command_table

    def translate_event(self, lax_event: LaxityEvent) -> List[SequenceEvent]:
        """
        Translate single Laxity event to SF2 events with duration expansion.

        Args:
            lax_event: Parsed Laxity event

        Returns:
            List of SF2 SequenceEvent objects (expanded for duration)
        """
        # Translate note
        sf2_note = self.freq_table.translate_laxity_note(lax_event.note)

        # Translate command to SF2 command index
        sf2_command = SF2_NO_CHANGE
        if lax_event.command is not None and lax_event.command_param is not None:
            sf2_command = self._translate_command(lax_event.command, lax_event.command_param)

        # Instrument
        sf2_instrument = lax_event.instrument if lax_event.instrument is not None else SF2_NO_CHANGE

        # Build SF2 events with duration expansion
        events = []

        # First event: note trigger with instrument/command
        events.append(SequenceEvent(
            instrument=sf2_instrument,
            command=sf2_command,
            note=sf2_note
        ))

        # Sustain events: duration - 1 frames
        for _ in range(lax_event.duration - 1):
            events.append(SequenceEvent(
                instrument=SF2_NO_CHANGE,
                command=SF2_NO_CHANGE,
                note=SF2_GATE_ON  # Gate on (sustain)
            ))

        return events

    def _translate_command(self, lax_cmd: int, lax_param: int) -> int:
        """
        Translate Laxity command to SF2 command index.

        Converts Laxity command byte + parameter to SF2 (type, param1, param2)
        and looks up index in command table.

        Args:
            lax_cmd: Laxity command byte
            lax_param: Laxity command parameter byte

        Returns:
            SF2 command index (0-63) or SF2_NO_CHANGE if not found
        """
        high_nibble = (lax_cmd >> 4) & 0x0F
        low_nibble = lax_cmd & 0x0F

        # Convert Laxity format to SF2 (type, param1, param2)
        sf2_tuple = None

        if high_nibble == 0x0:  # $0x yy = Slide up
            speed_hi = low_nibble
            speed_lo = lax_param
            sf2_tuple = (0, speed_hi, speed_lo)  # T0 = slide

        elif high_nibble == 0x2:  # $2x yy = Slide down
            speed_hi = low_nibble | 0x80  # Set sign bit for down
            speed_lo = lax_param
            sf2_tuple = (0, speed_hi, speed_lo)  # T0 = slide

        elif lax_cmd == 0x60:  # $60 xy = Vibrato
            freq = (lax_param >> 4) & 0x0F
            amp = lax_param & 0x0F
            sf2_tuple = (1, freq, amp)  # T1 = vibrato

        elif high_nibble == 0x8:  # $8x xx = Portamento
            speed_hi = low_nibble
            speed_lo = lax_param
            sf2_tuple = (2, speed_hi, speed_lo)  # T2 = portamento

        elif high_nibble == 0x9:  # $9x yy = Set ADSR (persistent)
            ad = low_nibble << 4  # D value in high nibble
            sr = lax_param
            sf2_tuple = (9, ad, sr)  # T9 = ADSR persist

        elif high_nibble == 0xA:  # $ax yy = Set ADSR (local)
            ad = low_nibble << 4  # D value in high nibble
            sr = lax_param
            sf2_tuple = (8, ad, sr)  # T8 = ADSR local

        elif lax_cmd == 0xC0:  # $c0 xx = Set wave pointer
            sf2_tuple = (0x0B, 0, lax_param)  # Tb = wave index

        elif high_nibble == 0xD:  # $dx yy = Filter/pulse control
            if low_nibble == 0:
                sf2_tuple = (0x0A, 0, lax_param)  # Ta = filter program
            elif low_nibble == 2:
                sf2_tuple = (0x0C, 0, lax_param)  # Tc = pulse program
            # Other dx commands not directly supported

        elif lax_cmd == 0xE0:  # $e0 xx = Set speed
            sf2_tuple = (0x0D, 0, lax_param)  # Td = tempo

        elif lax_cmd == 0xF0:  # $f0 xx = Set volume
            volume = lax_param & 0x0F
            sf2_tuple = (0x0E, 0, volume)  # Te = volume

        # Look up in command table
        if sf2_tuple and sf2_tuple in self.command_table:
            return self.command_table[sf2_tuple]
        else:
            # Command not in table - return no change
            logger.debug(f"Command not in table: Lax ${lax_cmd:02X} ${lax_param:02X} -> SF2 {sf2_tuple}")
            return SF2_NO_CHANGE

    def build_sequence(self, lax_events: List[LaxityEvent]) -> List[SequenceEvent]:
        """
        Build complete SF2 sequence from Laxity events.

        Args:
            lax_events: List of parsed Laxity events

        Returns:
            List of SF2 SequenceEvent objects with gate markers
        """
        if not lax_events:
            return [SequenceEvent(SF2_NO_CHANGE, SF2_NO_CHANGE, SF2_END)]

        sf2_events = []

        for lax_event in lax_events:
            # Translate event to SF2 format (with duration expansion)
            translated = self.translate_event(lax_event)
            sf2_events.extend(translated)

        # Insert gate-off markers between notes (will be improved in Day 2)
        sf2_events = self._insert_gate_markers(sf2_events)

        # Ensure sequence ends with $7F
        if not sf2_events or sf2_events[-1].note != SF2_END:
            sf2_events.append(SequenceEvent(SF2_NO_CHANGE, SF2_NO_CHANGE, SF2_END))

        return sf2_events

    def _insert_gate_markers(self, events: List[SequenceEvent]) -> List[SequenceEvent]:
        """
        Insert SF2 gate-off markers between notes.

        SF2 requires explicit gate-off ($80) for proper ADSR release.
        Insert gate-off before each new note to ensure clean note transitions.

        Args:
            events: List of SF2 events

        Returns:
            Events with gate-off markers inserted
        """
        if not events:
            return events

        result = []
        prev_was_note = False

        for event in events:
            # Check if this event is a new note (not a sustain or control byte)
            is_new_note = (event.note < SF2_GATE_ON and event.note != 0)

            # Insert gate-off before new notes (except the first note)
            if is_new_note and prev_was_note:
                result.append(SequenceEvent(
                    instrument=SF2_NO_CHANGE,
                    command=SF2_NO_CHANGE,
                    note=SF2_GATE_OFF  # 0x80 = gate off
                ))

            result.append(event)

            # Update state for next iteration
            prev_was_note = is_new_note

        return result


def extract_laxity_frequency_table(c64_data: bytes, load_addr: int) -> LaxityFrequencyTable:
    """
    Extract Laxity frequency table from C64 data.

    Args:
        c64_data: C64 program data
        load_addr: Memory load address

    Returns:
        LaxityFrequencyTable object
    """
    return LaxityFrequencyTable(c64_data, load_addr)
