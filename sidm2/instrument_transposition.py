"""
Laxity → SF2 Instrument Transposition

Converts Laxity NewPlayer v21 instrument format (row-major 8×8)
to SF2 Driver 11 instrument format (column-major 32×6).

Based on docs/guides/LAXITY_TO_SF2_GUIDE.md

Version: 1.0.0
Date: 2025-12-27
"""

import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class InstrumentTransposer:
    """
    Transpose Laxity row-major instrument format to SF2 column-major format.

    **Laxity Format** (8 instruments × 8 bytes, row-major):
    ```
    Offset  Instrument Data
    $1A6B:  AD SR WF PW FL FW AR SP  ← Instrument 0
    $1A73:  AD SR WF PW FL FW AR SP  ← Instrument 1
    ...
    $1AA3:  AD SR WF PW FL FW AR SP  ← Instrument 7

    Where:
      AD = Attack/Decay
      SR = Sustain/Release
      WF = Waveform index
      PW = Pulse width index
      FL = Filter index
      FW = Filter waveform (not used in SF2)
      AR = Arpeggio index (not used in SF2)
      SP = Speed/flags
    ```

    **SF2 Format** (32 instruments × 6 bytes, column-major):
    ```
    $0A03-$0A22:  AD AD AD ... (32 bytes) ← Column 0: All AD values
    $0A23-$0A42:  SR SR SR ... (32 bytes) ← Column 1: All SR values
    $0A43-$0A62:  FL FL FL ... (32 bytes) ← Column 2: All Flags
    $0A63-$0A82:  FI FI FI ... (32 bytes) ← Column 3: Filter indices
    $0A83-$0AA2:  PW PW PW ... (32 bytes) ← Column 4: Pulse indices
    $0AA3-$0AC2:  WF WF WF ... (32 bytes) ← Column 5: Wave indices
    ```

    **Note**: Laxity uses 8 parameters, SF2 uses 6. The extra Laxity parameters
    (filter waveform at byte 5, arpeggio at byte 6) are not mapped to SF2.
    """

    # SF2 Driver 11 instrument table constants
    SF2_NUM_INSTRUMENTS = 32
    SF2_BYTES_PER_INSTRUMENT = 6
    SF2_TABLE_SIZE = SF2_NUM_INSTRUMENTS * 8  # 256 bytes (8 columns for compatibility)

    # Laxity instrument byte offsets
    LAXITY_AD = 0
    LAXITY_SR = 1
    LAXITY_WAVEFORM = 2
    LAXITY_PULSE = 3
    LAXITY_FILTER = 4
    LAXITY_FILTER_WAVEFORM = 5  # Not used in SF2
    LAXITY_ARPEGGIO = 6         # Not used in SF2
    LAXITY_FLAGS = 7

    # SF2 column indices
    SF2_COL_AD = 0
    SF2_COL_SR = 1
    SF2_COL_FLAGS = 2
    SF2_COL_FILTER = 3
    SF2_COL_PULSE = 4
    SF2_COL_WAVE = 5

    def __init__(self):
        """Initialize instrument transposer"""
        pass

    def transpose(
        self,
        laxity_instruments: List[bytes],
        pad_to: int = SF2_NUM_INSTRUMENTS
    ) -> bytes:
        """
        Transpose Laxity row-major instruments to SF2 column-major format.

        Args:
            laxity_instruments: List of 8-byte Laxity instrument data (up to 32)
            pad_to: Number of instruments to pad to (default: 32)

        Returns:
            SF2 instrument table (256 bytes)

        Raises:
            ValueError: If laxity_instruments is invalid

        Example:
            >>> laxity_inst = [bytes([0x49, 0x80, 0x05, 0x03, 0x07, 0x01, 0x00, 0x40])]  # 1 instrument
            >>> transposer = InstrumentTransposer()
            >>> sf2_table = transposer.transpose(laxity_inst)
            >>> len(sf2_table)
            256
        """
        if not laxity_instruments:
            logger.warning("No Laxity instruments provided, using defaults")
            laxity_instruments = []

        if len(laxity_instruments) > pad_to:
            logger.warning(
                f"Truncating {len(laxity_instruments)} instruments to {pad_to}",
                extra={
                    'suggestion': f"SF2 supports up to {pad_to} instruments",
                    'check': "Ensure all important instruments are in first 32 slots",
                    'try': "Reduce number of instruments or increase pad_to limit"
                }
            )
            laxity_instruments = laxity_instruments[:pad_to]

        # Validate instrument data
        for i, inst in enumerate(laxity_instruments):
            if len(inst) < 8:
                raise ValueError(
                    f"Instrument {i} has {len(inst)} bytes, expected 8. "
                    f"Laxity instruments must be 8 bytes each."
                )

        # Create SF2 table buffer (256 bytes)
        sf2_table = bytearray(self.SF2_TABLE_SIZE)

        # Transpose Laxity instruments to SF2 column-major format
        num_laxity = len(laxity_instruments)

        for inst_idx in range(num_laxity):
            laxity_inst = laxity_instruments[inst_idx]

            # Extract Laxity parameters
            ad = laxity_inst[self.LAXITY_AD]
            sr = laxity_inst[self.LAXITY_SR]
            waveform = laxity_inst[self.LAXITY_WAVEFORM]
            pulse = laxity_inst[self.LAXITY_PULSE]
            filter_idx = laxity_inst[self.LAXITY_FILTER]
            flags = laxity_inst[self.LAXITY_FLAGS]

            # Map to SF2 columns (column-major storage)
            sf2_table[self.SF2_COL_AD * self.SF2_NUM_INSTRUMENTS + inst_idx] = ad
            sf2_table[self.SF2_COL_SR * self.SF2_NUM_INSTRUMENTS + inst_idx] = sr
            sf2_table[self.SF2_COL_FLAGS * self.SF2_NUM_INSTRUMENTS + inst_idx] = flags
            sf2_table[self.SF2_COL_FILTER * self.SF2_NUM_INSTRUMENTS + inst_idx] = filter_idx
            sf2_table[self.SF2_COL_PULSE * self.SF2_NUM_INSTRUMENTS + inst_idx] = pulse
            sf2_table[self.SF2_COL_WAVE * self.SF2_NUM_INSTRUMENTS + inst_idx] = waveform

        # Pad remaining instruments with defaults
        for inst_idx in range(num_laxity, pad_to):
            default_inst = self._get_default_instrument(inst_idx - num_laxity)

            sf2_table[self.SF2_COL_AD * self.SF2_NUM_INSTRUMENTS + inst_idx] = default_inst['ad']
            sf2_table[self.SF2_COL_SR * self.SF2_NUM_INSTRUMENTS + inst_idx] = default_inst['sr']
            sf2_table[self.SF2_COL_FLAGS * self.SF2_NUM_INSTRUMENTS + inst_idx] = default_inst['flags']
            sf2_table[self.SF2_COL_FILTER * self.SF2_NUM_INSTRUMENTS + inst_idx] = default_inst['filter']
            sf2_table[self.SF2_COL_PULSE * self.SF2_NUM_INSTRUMENTS + inst_idx] = default_inst['pulse']
            sf2_table[self.SF2_COL_WAVE * self.SF2_NUM_INSTRUMENTS + inst_idx] = default_inst['wave']

        return bytes(sf2_table)

    def _get_default_instrument(self, offset: int = 0) -> Dict[str, int]:
        """
        Get default instrument parameters for padding.

        Args:
            offset: Offset from first default (for variation)

        Returns:
            Dict with default instrument parameters

        Default instruments provide useful starting points:
        - Instrument 0: Triangle (basic tone)
        - Instrument 1: Sawtooth (bright)
        - Instrument 2: Pulse (hollow)
        - Instrument 3: Noise (percussion)
        - Remaining: Triangle variants
        """
        # Default patterns (cycle through 4 basic waveforms)
        defaults = [
            # Triangle (smooth)
            {'ad': 0x00, 'sr': 0xF0, 'flags': 0x00, 'filter': 0x00, 'pulse': 0x00, 'wave': 0x01},
            # Sawtooth (bright)
            {'ad': 0x00, 'sr': 0xF0, 'flags': 0x00, 'filter': 0x00, 'pulse': 0x00, 'wave': 0x02},
            # Pulse (hollow)
            {'ad': 0x00, 'sr': 0xF0, 'flags': 0x00, 'filter': 0x00, 'pulse': 0x00, 'wave': 0x00},
            # Noise (percussion)
            {'ad': 0x00, 'sr': 0xF0, 'flags': 0x00, 'filter': 0x00, 'pulse': 0x00, 'wave': 0x03},
        ]

        return defaults[offset % len(defaults)]

    def transpose_from_dict(
        self,
        laxity_instruments: List[Dict],
        pad_to: int = SF2_NUM_INSTRUMENTS
    ) -> bytes:
        """
        Transpose Laxity instruments from dict format to SF2 bytes.

        This is a convenience method for working with instrument dicts
        (as used by instrument_extraction.py).

        Args:
            laxity_instruments: List of instrument dicts
            pad_to: Number of instruments to pad to

        Returns:
            SF2 instrument table (256 bytes)

        Example:
            >>> inst_dict = {
            ...     'ad': 0x49, 'sr': 0x80, 'wave_ptr': 0x05,
            ...     'pulse_ptr': 0x03, 'filter_ptr': 0x07,
            ...     'restart': 0x40
            ... }
            >>> transposer = InstrumentTransposer()
            >>> sf2_table = transposer.transpose_from_dict([inst_dict])
        """
        # Convert dicts to bytes
        laxity_bytes = []

        for inst_dict in laxity_instruments:
            # Build 8-byte Laxity instrument
            inst_bytes = bytearray(8)
            inst_bytes[self.LAXITY_AD] = inst_dict.get('ad', 0x00)
            inst_bytes[self.LAXITY_SR] = inst_dict.get('sr', 0xF0)
            inst_bytes[self.LAXITY_WAVEFORM] = inst_dict.get('wave_ptr', 0x01)
            inst_bytes[self.LAXITY_PULSE] = inst_dict.get('pulse_ptr', 0x00)
            inst_bytes[self.LAXITY_FILTER] = inst_dict.get('filter_ptr', 0x00)
            inst_bytes[self.LAXITY_FILTER_WAVEFORM] = 0x00  # Not used
            inst_bytes[self.LAXITY_ARPEGGIO] = 0x00         # Not used
            inst_bytes[self.LAXITY_FLAGS] = inst_dict.get('restart', 0x00)  # Map restart → flags

            laxity_bytes.append(bytes(inst_bytes))

        return self.transpose(laxity_bytes, pad_to=pad_to)

    def get_instrument_from_table(
        self,
        sf2_table: bytes,
        inst_idx: int
    ) -> Dict[str, int]:
        """
        Extract a single instrument from SF2 table (for validation).

        Args:
            sf2_table: SF2 instrument table (256 bytes)
            inst_idx: Instrument index (0-31)

        Returns:
            Dict with instrument parameters

        Raises:
            ValueError: If inst_idx out of range or sf2_table invalid

        Example:
            >>> sf2_table = transposer.transpose([laxity_inst_0])
            >>> inst = transposer.get_instrument_from_table(sf2_table, 0)
            >>> inst['ad']
            0x49
        """
        if len(sf2_table) < self.SF2_TABLE_SIZE:
            raise ValueError(f"SF2 table too small: {len(sf2_table)} bytes, expected {self.SF2_TABLE_SIZE}")

        if inst_idx < 0 or inst_idx >= self.SF2_NUM_INSTRUMENTS:
            raise ValueError(f"Instrument index {inst_idx} out of range (0-{self.SF2_NUM_INSTRUMENTS-1})")

        # Extract from column-major storage
        return {
            'ad': sf2_table[self.SF2_COL_AD * self.SF2_NUM_INSTRUMENTS + inst_idx],
            'sr': sf2_table[self.SF2_COL_SR * self.SF2_NUM_INSTRUMENTS + inst_idx],
            'flags': sf2_table[self.SF2_COL_FLAGS * self.SF2_NUM_INSTRUMENTS + inst_idx],
            'filter': sf2_table[self.SF2_COL_FILTER * self.SF2_NUM_INSTRUMENTS + inst_idx],
            'pulse': sf2_table[self.SF2_COL_PULSE * self.SF2_NUM_INSTRUMENTS + inst_idx],
            'wave': sf2_table[self.SF2_COL_WAVE * self.SF2_NUM_INSTRUMENTS + inst_idx],
        }


# ============================================================================
# Public API
# ============================================================================

# Global transposer instance (singleton pattern)
_transposer = InstrumentTransposer()


def transpose_instruments(
    laxity_instruments: List[bytes],
    pad_to: int = 32
) -> bytes:
    """
    Transpose Laxity row-major instruments to SF2 column-major format.

    This is the primary public API for instrument transposition.

    Args:
        laxity_instruments: List of 8-byte Laxity instrument data
        pad_to: Number of instruments to pad to (default: 32)

    Returns:
        SF2 instrument table (256 bytes)

    Example:
        >>> from sidm2.instrument_transposition import transpose_instruments
        >>> laxity_inst = bytes([0x49, 0x80, 0x05, 0x03, 0x07, 0x01, 0x00, 0x40])
        >>> sf2_table = transpose_instruments([laxity_inst])
        >>> len(sf2_table)
        256
    """
    return _transposer.transpose(laxity_instruments, pad_to=pad_to)


def transpose_instruments_from_dict(
    laxity_instruments: List[Dict],
    pad_to: int = 32
) -> bytes:
    """
    Transpose Laxity instruments from dict format to SF2 bytes.

    Args:
        laxity_instruments: List of instrument dicts
        pad_to: Number of instruments to pad to

    Returns:
        SF2 instrument table (256 bytes)

    Example:
        >>> inst = {'ad': 0x49, 'sr': 0x80, 'wave_ptr': 0x05}
        >>> sf2_table = transpose_instruments_from_dict([inst])
    """
    return _transposer.transpose_from_dict(laxity_instruments, pad_to=pad_to)


def get_instrument_from_sf2_table(
    sf2_table: bytes,
    inst_idx: int
) -> Dict[str, int]:
    """
    Extract a single instrument from SF2 table.

    Args:
        sf2_table: SF2 instrument table (256 bytes)
        inst_idx: Instrument index (0-31)

    Returns:
        Dict with instrument parameters

    Example:
        >>> inst = get_instrument_from_sf2_table(sf2_table, 0)
        >>> print(f"Attack/Decay: ${inst['ad']:02X}")
    """
    return _transposer.get_instrument_from_table(sf2_table, inst_idx)
