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
from sidm2.command_mapping import decompose_laxity_command

logger = logging.getLogger(__name__)

# Laxity NewPlayer v21 constants
# The frequency table is LOCATED BY SEARCH (locate_frequency_table below), never
# by this constant. It survives only as the last-resort fallback for data in which
# no table can be found at all -- and it is known to be WRONG BY TWO BYTES: the
# player itself reads `LDA $1833,Y` / `LDA $1834,Y` (four call sites in Angular;
# $1835/$1836 is the SECOND read, used at $14A4 to compute the semitone delta
# table[n+1]-table[n]). Entry 0 is $0116, not $0127. Measured over 303 corpus
# files, the constant addresses a strictly-ascending table on ZERO of them.
LAXITY_FREQ_TABLE_ADDR = 0x1835  # legacy fallback only -- see locate_frequency_table
LAXITY_FREQ_TABLE_SIZE = 96

# Search parameters. A frequency table is a strictly ascending run of 16-bit
# values in which each note repeats an octave higher 12 entries later.
FREQ_MIN_ENTRIES = 36      # three octaves; below this a run is not a scale
FREQ_OCTAVE_TOL = 0.004    # the tables are exact to about +-1 LSB
FREQ_OCTAVE_AGREE = 0.9    # fraction of octave pairs that must hold

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


def _word(data: bytes, off: int) -> int:
    """Little-endian 16-bit read."""
    return data[off] | (data[off + 1] << 8)


def _ascending_run(data: bytes, off: int, cap: int) -> int:
    """Length of the strictly ascending 16-bit run starting at off."""
    n = 1
    while n < cap and off + n * 2 + 1 < len(data):
        if _word(data, off + n * 2) <= _word(data, off + (n - 1) * 2):
            break
        n += 1
    return n


def _octave_score(table: List[int]) -> float:
    """Fraction of entries whose note twelve semitones up is twice its frequency.

    This is what separates a frequency table from any other ascending run of
    bytes: an equal-tempered scale doubles every octave. Without it a packed
    sequence of counters scores as a table -- the Stinsen and Broware images each
    contain a 38-entry ascending run that is not music.
    """
    pairs = [(table[i], table[i + 12]) for i in range(len(table) - 12) if table[i] > 0]
    if not pairs:
        return 0.0
    ok = sum(1 for a, b in pairs
             if abs(b - 2 * a) <= max(2, FREQ_OCTAVE_TOL * 2 * a))
    return ok / len(pairs)


def _semitone_score(table: List[int]) -> float:
    """Fraction of consecutive pairs separated by one equal-tempered semitone.

    This is what fixes the BASE, and the octave test alone cannot: an ascending
    run may begin one or two bytes before the table, and those stray leading
    words are still ascending. A semitone is a ratio of 2**(1/12) = 1.0595, so a
    stray $0001 in front of $0116 shows up as a ratio of 278 and the candidate
    that starts on it is refused.
    """
    pairs = [(table[i], table[i + 1]) for i in range(len(table) - 1) if table[i] > 0]
    if not pairs:
        return 0.0
    ok = sum(1 for a, b in pairs if 1.03 <= b / a <= 1.09)
    return ok / len(pairs)


def _find_interleaved(data: bytes) -> Optional[Tuple[int, int, str]]:
    """Longest strictly-ascending, octave-doubling run of little-endian words."""
    best = None
    limit = len(data) - FREQ_MIN_ENTRIES * 2
    for off in range(0, max(0, limit)):
        if _word(data, off) == 0:
            continue                      # a zero frequency is not a note
        n = _ascending_run(data, off, cap=LAXITY_FREQ_TABLE_SIZE + 8)
        if n < FREQ_MIN_ENTRIES:
            continue
        table = [_word(data, off + i * 2) for i in range(n)]
        semitone = _semitone_score(table)
        if (_octave_score(table) >= FREQ_OCTAVE_AGREE
                and semitone >= FREQ_OCTAVE_AGREE):
            # The SCALE decides the base, not the length: a run that starts one
            # word early is LONGER, so ranking by length alone walks backwards
            # off the table. Best semitone agreement first, then longest, then
            # the earliest offset.
            cand = (round(semitone, 4), n, -off)
            if best is None or cand > best:
                best = cand
    if best is None:
        return None
    _sem, n, negoff = best
    return (-negoff, n, 'interleaved')


def _find_split(data: bytes) -> Optional[Tuple[int, int, str]]:
    """96 non-decreasing high bytes followed by 96 low bytes."""
    size = LAXITY_FREQ_TABLE_SIZE
    best = None
    for off in range(0, max(0, len(data) - 2 * size)):
        hi = data[off:off + size]
        if hi[0] > 8 or hi[-1] < 0x60:
            continue                      # must span roughly eight octaves
        if any(hi[i] > hi[i + 1] for i in range(size - 1)):
            continue
        lo = off + size
        table = [data[lo + i] | (hi[i] << 8) for i in range(size)]
        if any(table[i] >= table[i + 1] for i in range(size - 1)):
            continue
        score = _octave_score(table)
        if (score >= FREQ_OCTAVE_AGREE
                and _semitone_score(table) >= FREQ_OCTAVE_AGREE
                and (best is None or score > best[1])):
            best = (off, score)
    if best is None:
        return None
    return (best[0], size, 'split')


def locate_frequency_table(data: bytes) -> Optional[Tuple[int, int, str]]:
    """Locate the Laxity frequency table by search: offset, size AND layout.

    Returns None when no candidate satisfies both tests, which is the honest
    answer for data that carries no table -- 50 of 303 corpus files.

    AND THOSE 50 ARE NOT NP21 FILES. Measured with detect_player_type over
    exactly the set this function declines:

        SidFactory/Laxity      27      Soundmonitor           20
        256bytes/Laxity         1      SidFactory_II/Laxity    1
        Unknown                 1

    Not one is Laxity_NewPlayer_V21 or Vibrants/Laxity. A 60-file control drawn
    from the files it DOES locate reads Vibrants/Laxity 25, SidFactory_II/Laxity
    21, Rob_Hubbard 8, Laxity_NewPlayer_V21 3, JCH_NewPlayer 3. So the search
    finds a table on the files the Laxity path owns, and the misses are other
    players sitting in SID/Laxity -- SF2-exported songs (which route to Driver
    11, not this one) and Sound Monitor rips. The two Laxity-family stragglers,
    one 256bytes/Laxity and one SidFactory_II/Laxity, are the only residue worth
    chasing.
    """
    return _find_interleaved(data) or _find_split(data)


def read_frequency_table(data: bytes, loc: Tuple[int, int, str]) -> List[int]:
    """Read the table a locate_frequency_table() result describes."""
    off, size, layout = loc
    if layout == 'split':
        return [data[off + size + i] | (data[off + i] << 8) for i in range(size)]
    return [_word(data, off + i * 2) for i in range(size)]


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
        """
        Locate and read the Laxity frequency table.

        The table is found BY SEARCH -- address and size together -- because the
        players relocate and because two different layouts are in use:

          interleaved   96 little-endian words, lo,hi,lo,hi (Angular, $1833)
          split         96 high bytes followed by 96 low bytes (Stinsen, $16A1)

        Both start on the same note: entry 0 is $0116. The historical $0835
        constant is retained only as a fallback for data in which no table can be
        located; it points two bytes past the base, i.e. one semitone sharp.
        """
        loc = locate_frequency_table(c64_data)
        if loc is not None:
            offset, size, layout = loc
            self.table_offset = offset
            self.table_size = size
            self.table_layout = layout
            logger.debug(
                f"Frequency table located by search: offset=${offset:04X} "
                f"(${load_addr + offset:04X}), {size} entries, {layout}")
            return read_frequency_table(c64_data, loc)

        # Nothing found. Fall back to the constant so that data which carries no
        # locatable table behaves as it always has, and say so at WARNING -- a
        # silent fallback is how a wrong address survives measurement.
        offset = LAXITY_FREQ_TABLE_ADDR - 0x1000
        self.table_offset = offset
        self.table_size = LAXITY_FREQ_TABLE_SIZE
        self.table_layout = 'fallback-constant'
        logger.warning(
            f"No frequency table located; falling back to the ${offset:04X} "
            f"constant, which is known to be two bytes past the base")

        if offset < 0 or offset + (LAXITY_FREQ_TABLE_SIZE * 2) > len(c64_data):
            logger.warning(f"Frequency table at offset ${offset:04X} extends beyond data (len={len(c64_data)})")
            self.table_size = 0
            return []

        return [c64_data[offset + i * 2] | (c64_data[offset + i * 2 + 1] << 8)
                for i in range(LAXITY_FREQ_TABLE_SIZE)]

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

        # Clamp to SF2 range (C-0 to B-7 = 0 to 93 = 0x00 to 0x5D).
        #
        # THE TOP OF THE CLAMP CAN NEVER STOP FIRING, and that is a property of
        # the format, not a defect to chase. A located Laxity table is 96 notes
        # starting on $0116 = MIDI 12, so it ends at MIDI 107 -- fourteen
        # semitones above SF2's B-7. Measured over the 236 tables located in
        # SID/Laxity: 3,266 entries sit above MIDI 93, ZERO below 0, and 231 of
        # the 236 files have EXACTLY 14 such entries. A song that plays a note
        # in its top 14 table slots clamps, correctly.
        #
        # What DID change when the table stopped being read at the $0835
        # constant (see locate_frequency_table): corpus clamp firings fell from
        # 16,406 to 7,838 here and from 2,976 to 1,055 on the index path, and
        # Short_but_Urgent went from ONE distinct pitch -- the value 93, i.e.
        # the clamp itself -- to fifty.
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
                # LOW NIBBLE plus one -- established from the player's own 6502 in
                # drivers/laxity/laxity_player_disassembly.asm, not from another
                # module here (all three in-repo readings disagreed, and all three
                # were wrong). The reader masks `and #$0F`, stores to $FD,X, copies
                # that to $EE,X, and the per-frame path is `dec ... / bpl`: the row
                # advances only when the counter goes NEGATIVE, so a stored n lasts
                # n+1 frames. $80..$8F is therefore 1..16 frames.
                #
                # BIT 4 IS NOT PART OF THE COUNT. `$1F` folded it in, making one
                # duration byte in seven (232 of 1,708 over SID/Laxity/) up to 16
                # frames too long. The player instead uses bit 4 to bump a SEPARATE
                # gate/continue flag ($100,X) that a note byte of $00/$7E also bumps
                # -- so it is not purely a tie, and it is not a duration input.
                # See docs/players/LAXITY.md.
                current_duration = (byte & 0x0F) + 1   # $80 = 1 frame, $8F = 16
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

        Uses B2 command decomposition for super-commands (vibrato, arpeggio, tremolo).

        Args:
            lax_event: Parsed Laxity event

        Returns:
            List of SF2 SequenceEvent objects (expanded for duration and command decomposition)
        """
        # Translate note
        sf2_note = self.freq_table.translate_laxity_note(lax_event.note)

        # Instrument
        sf2_instrument = lax_event.instrument if lax_event.instrument is not None else SF2_NO_CHANGE

        # Decompose Laxity command using B2 (returns list of SF2 commands)
        sf2_commands = []
        if lax_event.command is not None and lax_event.command_param is not None:
            # Use B2 command decomposition (Track B2)
            decomposed = decompose_laxity_command(lax_event.command, lax_event.command_param)

            # Convert B2 output format to command table indices
            for cmd_byte, param in decomposed:
                # Extract command type from B2 format (0xA0 + type → type)
                if 0xA0 <= cmd_byte <= 0xBF:
                    cmd_type = cmd_byte - 0xA0
                    # Convert to command table tuple (type, param, 0)
                    sf2_tuple = (cmd_type, param if param is not None else 0, 0)

                    # Look up in command table to get index
                    if sf2_tuple in self.command_table:
                        sf2_commands.append(self.command_table[sf2_tuple])
                    else:
                        logger.debug(f"B2 command not in table: {sf2_tuple}")
                elif 0x00 <= cmd_byte <= 0x5F:
                    # Note event from B2 (direct mapping)
                    continue
                elif cmd_byte in (0x7E, 0x80, 0x7F):
                    # Control markers (gate on/off, end)
                    continue
                else:
                    logger.warning(f"Unknown B2 command byte: ${cmd_byte:02X}")

        # Build SF2 events with duration expansion
        events = []

        # Handle multiple commands from decomposition (super-commands)
        if not sf2_commands:
            # No commands - just note with instrument
            events.append(SequenceEvent(
                instrument=sf2_instrument,
                command=SF2_NO_CHANGE,
                note=sf2_note
            ))
        elif len(sf2_commands) == 1:
            # Single command - standard case
            events.append(SequenceEvent(
                instrument=sf2_instrument,
                command=sf2_commands[0],
                note=sf2_note
            ))
        else:
            # Multiple commands from super-command decomposition (e.g., Vibrato → 2 commands)
            # First event: note + instrument + first command
            events.append(SequenceEvent(
                instrument=sf2_instrument,
                command=sf2_commands[0],
                note=sf2_note
            ))
            # Additional events for remaining commands (same note, no instrument change)
            for cmd_idx in sf2_commands[1:]:
                events.append(SequenceEvent(
                    instrument=SF2_NO_CHANGE,
                    command=cmd_idx,
                    note=SF2_GATE_ON  # Sustain while applying additional commands
                ))

        # Sustain events: duration - 1 frames (or duration - len(sf2_commands) if multiple commands)
        sustain_frames = max(0, lax_event.duration - len(events))
        for _ in range(sustain_frames):
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

        # Insert gate markers with enhanced inference (v1.5.0)
        sf2_events = self._insert_gate_markers_enhanced(sf2_events)

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

    def _insert_gate_markers_enhanced(self, events: List[SequenceEvent]) -> List[SequenceEvent]:
        """
        Enhanced gate marker insertion with improved detection.

        Improvements over simple version:
        1. Detects actual note changes (not just presence)
        2. Adds gate-on after note triggers
        3. Inserts gate-off before note changes
        4. Avoids redundant markers

        This provides better ADSR envelope control and note separation.

        Args:
            events: List of SF2 events

        Returns:
            Events with enhanced gate markers
        """
        from .gate_inference import WaveformGateAnalyzer

        # Use enhanced simple inference (no siddump data needed for static extraction)
        analyzer = WaveformGateAnalyzer()
        return analyzer.infer_gates_simple(events)


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
