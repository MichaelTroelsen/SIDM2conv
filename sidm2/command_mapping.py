"""
Laxity NewPlayer v21 → SF2 Driver 11 Command Mapping

This module provides comprehensive command decomposition for converting
Laxity super-commands (multi-parameter packed) into SF2 simple commands
(one command = one parameter).

Based on the Laxity→SF2 Rosetta Stone (docs/guides/LAXITY_TO_SF2_GUIDE.md).

Version: 1.0.0
Date: 2025-12-27
"""

import logging
from typing import List, Tuple, Optional, Dict
from enum import IntEnum

logger = logging.getLogger(__name__)


class LaxityCommand(IntEnum):
    """Laxity NewPlayer v21 command opcodes"""
    # Note Events (0x00-0x5F) - direct mapping
    NOTE_MIN = 0x00
    NOTE_MAX = 0x5F

    # Control Commands
    SET_INSTRUMENT = 0x60
    VIBRATO = 0x61
    PITCH_SLIDE_UP = 0x62
    PITCH_SLIDE_DOWN = 0x63
    PATTERN_JUMP = 0x64
    PATTERN_BREAK = 0x65
    SET_VOLUME = 0x66
    FINE_VOLUME = 0x67

    # Extended Commands
    ARPEGGIO = 0x70
    PORTAMENTO = 0x71
    TREMOLO = 0x72

    # Control Markers
    CUT_NOTE = 0x7E
    END_SEQUENCE = 0x7F


class SF2Command(IntEnum):
    """SF2 Driver 11 command types (T0-TF)"""
    SLIDE = 0x00          # T0: Pitch slide (up/down based on sign)
    VIBRATO_DEPTH = 0x01  # T1: Vibrato depth
    VIBRATO_SPEED = 0x02  # T2: Vibrato speed
    SLIDE_UP = 0x03       # T3: Pitch slide up
    SLIDE_DOWN = 0x04     # T4: Pitch slide down
    ARPEGGIO_NOTE1 = 0x05 # T5: Arpeggio note 1
    ARPEGGIO_NOTE2 = 0x06 # T6: Arpeggio note 2
    PORTAMENTO = 0x07     # T7: Portamento (slide to note)
    TREMOLO_DEPTH = 0x08  # T8: Tremolo depth
    TREMOLO_SPEED = 0x09  # T9: Tremolo speed
    FILTER_PROG = 0x0A    # Ta: Filter program
    WAVE_PROG = 0x0B      # Tb: Wave program
    PULSE_PROG = 0x0C     # Tc: Pulse program
    TEMPO = 0x0D          # Td: Tempo/speed
    VOLUME = 0x0E         # Te: Main volume
    ADSR = 0x0F           # Tf: ADSR envelope

    # Gate markers (SF2 control bytes)
    GATE_ON = 0x7E        # Start note
    GATE_OFF = 0x80       # Stop note


class CommandDecomposer:
    """
    Decomposes Laxity super-commands into SF2 simple commands.

    Laxity super-commands pack multiple parameters into one byte.
    SF2 simple commands use separate commands for each parameter.

    Example:
        Laxity: $61 $35 (vibrato, depth=3, speed=5)
        SF2:    T1 $03 (depth), T2 $05 (speed)
    """

    def __init__(self):
        """Initialize command decomposer with mapping table"""
        self.decomposition_map = self._build_decomposition_map()

    def _build_decomposition_map(self) -> Dict[int, callable]:
        """
        Build mapping table from Laxity commands to decomposition functions.

        Returns:
            Dict mapping Laxity command byte → decomposition function
        """
        return {
            LaxityCommand.SET_INSTRUMENT: self._decompose_set_instrument,
            LaxityCommand.VIBRATO: self._decompose_vibrato,
            LaxityCommand.PITCH_SLIDE_UP: self._decompose_pitch_slide_up,
            LaxityCommand.PITCH_SLIDE_DOWN: self._decompose_pitch_slide_down,
            LaxityCommand.PATTERN_JUMP: self._decompose_pattern_jump,
            LaxityCommand.PATTERN_BREAK: self._decompose_pattern_break,
            LaxityCommand.SET_VOLUME: self._decompose_set_volume,
            LaxityCommand.FINE_VOLUME: self._decompose_fine_volume,
            LaxityCommand.ARPEGGIO: self._decompose_arpeggio,
            LaxityCommand.PORTAMENTO: self._decompose_portamento,
            LaxityCommand.TREMOLO: self._decompose_tremolo,
            LaxityCommand.CUT_NOTE: self._decompose_cut_note,
            LaxityCommand.END_SEQUENCE: self._decompose_end_sequence,
        }

    def decompose(self, laxity_cmd: int, param: int = 0) -> List[Tuple[int, Optional[int]]]:
        """
        Decompose a Laxity command into SF2 command(s).

        Args:
            laxity_cmd: Laxity command byte (0x00-0xFF)
            param: Command parameter byte (if applicable)

        Returns:
            List of (sf2_command, sf2_param) tuples
            sf2_param may be None for commands without parameters

        Example:
            >>> decomposer = CommandDecomposer()
            >>> decomposer.decompose(0x61, 0x35)  # Vibrato depth=3, speed=5
            [(0xA1, 3), (0xA2, 5)]  # T1 depth, T2 speed
        """
        # Note events (0x00-0x5F) map directly
        if LaxityCommand.NOTE_MIN <= laxity_cmd <= LaxityCommand.NOTE_MAX:
            return [(laxity_cmd, None)]

        # Look up decomposition function
        decompose_func = self.decomposition_map.get(laxity_cmd)

        if decompose_func:
            return decompose_func(param)
        else:
            # Unknown command - pass through
            logger.warning(
                f"Unknown Laxity command: ${laxity_cmd:02X} (param: ${param:02X})",
                extra={
                    'suggestion': "Check if this is a valid Laxity NewPlayer v21 command",
                    'check': [
                        "Command byte is in valid range (0x00-0xFF)",
                        "Command is documented in Laxity format specification"
                    ],
                    'try': [
                        "Use a known Laxity command (see LaxityCommand enum)",
                        "Check the Rosetta Stone (docs/guides/LAXITY_TO_SF2_GUIDE.md)"
                    ],
                    'see': "docs/guides/LAXITY_TO_SF2_GUIDE.md"
                }
            )
            return [(laxity_cmd, param)]

    # =========================================================================
    # Decomposition Functions (one per Laxity command type)
    # =========================================================================

    def _decompose_set_instrument(self, param: int) -> List[Tuple[int, int]]:
        """
        Set Instrument: $60 xx → $A1 xx

        Direct mapping (no decomposition needed).
        SF2 uses $A1 for instrument changes.
        """
        return [(0xA1, param)]

    def _decompose_vibrato(self, param: int) -> List[Tuple[int, int]]:
        """
        Vibrato: $61 xy → T1 XX, T2 YY

        Decomposes packed parameter:
        - High nibble (x) = depth
        - Low nibble (y) = speed

        Example: $61 $35 → T1 $03 (depth), T2 $05 (speed)
        """
        depth = (param >> 4) & 0x0F  # Extract high nibble
        speed = param & 0x0F         # Extract low nibble

        return [
            (0xA0 + SF2Command.VIBRATO_DEPTH, depth),  # T1
            (0xA0 + SF2Command.VIBRATO_SPEED, speed),  # T2
        ]

    def _decompose_pitch_slide_up(self, param: int) -> List[Tuple[int, int]]:
        """
        Pitch Slide Up: $62 xx → T3 XX

        Direct mapping to SF2 T3 (pitch slide up).
        """
        return [(0xA0 + SF2Command.SLIDE_UP, param)]  # T3

    def _decompose_pitch_slide_down(self, param: int) -> List[Tuple[int, int]]:
        """
        Pitch Slide Down: $63 xx → T4 XX

        Direct mapping to SF2 T4 (pitch slide down).
        """
        return [(0xA0 + SF2Command.SLIDE_DOWN, param)]  # T4

    def _decompose_pattern_jump(self, param: int) -> List[Tuple[int, int]]:
        """
        Pattern Jump: $64 xx → (no SF2 equivalent)

        Laxity pattern control - not directly supported in SF2.
        This affects orderlist sequencing, not note playback.
        """
        logger.debug(f"Pattern Jump (${param:02X}) - no SF2 equivalent")
        return []  # No output

    def _decompose_pattern_break(self, param: int) -> List[Tuple[int, int]]:
        """
        Pattern Break: $65 → (no SF2 equivalent)

        Laxity pattern control - not directly supported in SF2.
        """
        logger.debug("Pattern Break - no SF2 equivalent")
        return []  # No output

    def _decompose_set_volume(self, param: int) -> List[Tuple[int, int]]:
        """
        Set Volume: $66 xx → Te XX

        Global volume control.
        SF2 uses Te (0xAE) for main volume.
        """
        volume = param & 0x0F  # 4-bit volume (0-15)
        return [(0xA0 + SF2Command.VOLUME, volume)]  # Te

    def _decompose_fine_volume(self, param: int) -> List[Tuple[int, int]]:
        """
        Fine Volume: $67 xy → (channel-specific volume)

        Laxity supports per-channel volume.
        SF2 has limited support - map to global volume for now.

        TODO: Enhanced support for channel volume in future version
        """
        volume = param & 0x0F  # Use low nibble
        logger.debug(f"Fine Volume (${param:02X}) - mapped to global volume")
        return [(0xA0 + SF2Command.VOLUME, volume)]  # Te

    def _decompose_arpeggio(self, param: int) -> List[Tuple[int, int]]:
        """
        Arpeggio: $70 xy → T5 XX, T6 YY

        Decomposes packed parameter:
        - High nibble (x) = note 1 offset
        - Low nibble (y) = note 2 offset

        Example: $70 $47 → T5 $04 (note1), T6 $07 (note2)
        Creates C major chord: C (0) + E (+4) + G (+7)
        """
        note1 = (param >> 4) & 0x0F  # Extract high nibble
        note2 = param & 0x0F         # Extract low nibble

        return [
            (0xA0 + SF2Command.ARPEGGIO_NOTE1, note1),  # T5
            (0xA0 + SF2Command.ARPEGGIO_NOTE2, note2),  # T6
        ]

    def _decompose_portamento(self, param: int) -> List[Tuple[int, int]]:
        """
        Portamento: $71 xx → T7 XX

        Slide to target note at specified speed.
        Direct mapping to SF2 T7.
        """
        return [(0xA0 + SF2Command.PORTAMENTO, param)]  # T7

    def _decompose_tremolo(self, param: int) -> List[Tuple[int, int]]:
        """
        Tremolo: $72 xy → T8 XX, T9 YY

        Volume modulation (amplitude vibrato).
        Decomposes packed parameter:
        - High nibble (x) = depth
        - Low nibble (y) = speed

        Example: $72 $24 → T8 $02 (depth), T9 $04 (speed)
        """
        depth = (param >> 4) & 0x0F  # Extract high nibble
        speed = param & 0x0F         # Extract low nibble

        return [
            (0xA0 + SF2Command.TREMOLO_DEPTH, depth),  # T8
            (0xA0 + SF2Command.TREMOLO_SPEED, speed),  # T9
        ]

    def _decompose_cut_note(self, param: int) -> List[Tuple[int, Optional[int]]]:
        """
        Cut Note: $7E → $80 (gate off)

        Explicitly stop the current note.
        Maps to SF2 gate off marker.
        """
        return [(SF2Command.GATE_OFF, None)]  # $80

    def _decompose_end_sequence(self, param: int) -> List[Tuple[int, Optional[int]]]:
        """
        End Sequence: $7F → $7F

        Sequence terminator - direct mapping.
        """
        return [(0x7F, None)]


# ============================================================================
# Public API
# ============================================================================

# Global decomposer instance (singleton pattern)
_decomposer = CommandDecomposer()


def decompose_laxity_command(cmd: int, param: int = 0) -> List[Tuple[int, Optional[int]]]:
    """
    Decompose a Laxity command into SF2 command(s).

    This is the primary public API for command decomposition.

    Args:
        cmd: Laxity command byte (0x00-0xFF)
        param: Command parameter byte (default: 0)

    Returns:
        List of (sf2_command, sf2_param) tuples
        sf2_param may be None for commands without parameters

    Example:
        >>> decompose_laxity_command(0x61, 0x35)  # Vibrato
        [(161, 3), (162, 5)]  # T1 depth=3, T2 speed=5

        >>> decompose_laxity_command(0x62, 0x10)  # Pitch slide up
        [(163, 16)]  # T3 speed=16

        >>> decompose_laxity_command(0x3C)  # Note C-4
        [(60, None)]  # Direct note mapping
    """
    return _decomposer.decompose(cmd, param)


def get_command_expansion_ratio(laxity_cmd: int, param: int = 0) -> float:
    """
    Calculate the expansion ratio for a Laxity command.

    Expansion ratio = SF2 bytes / Laxity bytes

    Args:
        laxity_cmd: Laxity command byte
        param: Command parameter byte

    Returns:
        Expansion ratio (e.g., 2.0 means SF2 is 2x larger)

    Example:
        >>> get_command_expansion_ratio(0x61, 0x35)  # Vibrato
        2.0  # Laxity: 2 bytes → SF2: 4 bytes
    """
    sf2_commands = decompose_laxity_command(laxity_cmd, param)

    # Count SF2 bytes
    sf2_bytes = sum(2 if param is not None else 1 for _, param in sf2_commands)

    # Count Laxity bytes (most commands are 2 bytes: cmd + param)
    if laxity_cmd in (LaxityCommand.CUT_NOTE, LaxityCommand.END_SEQUENCE):
        laxity_bytes = 1  # No parameter
    elif LaxityCommand.NOTE_MIN <= laxity_cmd <= LaxityCommand.NOTE_MAX:
        laxity_bytes = 1  # Just the note
    else:
        laxity_bytes = 2  # Command + parameter

    return sf2_bytes / laxity_bytes if laxity_bytes > 0 else 1.0
