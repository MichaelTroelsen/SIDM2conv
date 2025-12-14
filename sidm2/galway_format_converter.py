"""
Martin Galway to SF2 Format Converter

Converts extracted Martin Galway music tables to SID Factory II format.
Handles format translation with fallback strategies.

Phase 3 implementation: Format conversion and validation
"""

import logging
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConversionMapping:
    """Mapping from Galway format to SF2 format"""
    galway_offset: int
    galway_size: int
    sf2_offset: int
    sf2_size: int
    conversion_func: Optional[callable] = None
    lossy: bool = False
    confidence: float = 1.0
    notes: str = ""


class GalwayFormatConverter:
    """
    Convert Martin Galway tables to SF2 format.

    Galway and SF2 use different table layouts and control bytes.
    This converter maps Galway structures to SF2 equivalents with
    fallback strategies for incompatible formats.
    """

    # Control byte mappings
    GALWAY_CONTROL_BYTES = {
        0x7F: 'end_marker',      # End of sequence
        0x7E: 'gate_marker',     # Gate on/sustain
        0x80: 'gate_off',        # Gate off
        0xFF: 'padding',         # Padding
    }

    SF2_CONTROL_BYTES = {
        0x7F: 'end_marker',      # End of sequence
        0x7E: 'gate_marker',     # Gate on
        0x00: 'rest',            # Rest/silence
        0xFF: 'padding',         # Padding
    }

    # Standard instrument entry structure (C64 audio chip)
    INSTRUMENT_FORMAT = {
        'attack_decay': (0, 1),      # Byte 0: AD register
        'sustain_release': (1, 1),   # Byte 1: SR register
        'waveform': (2, 1),          # Byte 2: Waveform (triangle, sawtooth, pulse)
        'pulse_width_high': (3, 1),  # Byte 3: Pulse width high
        'pulse_width_low': (4, 1),   # Byte 4: Pulse width low
        'filter_setting': (5, 1),    # Byte 5: Filter settings
        'filter_envelope': (6, 1),   # Byte 6: Filter envelope
        'reserved': (7, 1),          # Byte 7: Reserved
    }

    def __init__(self, sf2_driver: str = "driver11"):
        """
        Initialize format converter.

        Args:
            sf2_driver: Target SF2 driver ("driver11", "np20", "laxity")
        """
        self.sf2_driver = sf2_driver
        self.conversions: List[ConversionMapping] = []
        self.conversion_errors: List[str] = []

    def convert_instruments(self, galway_data: bytes, galway_offset: int,
                          num_instruments: int, entry_size: int) -> Tuple[bytes, float]:
        """
        Convert Galway instrument table to SF2 format.

        Args:
            galway_data: Raw Galway instrument data
            galway_offset: Offset in Galway address space
            num_instruments: Number of instruments
            entry_size: Bytes per instrument entry

        Returns:
            (converted_data, confidence)
        """
        logger.debug(f"Converting {num_instruments} instruments ({entry_size} bytes/entry)")

        try:
            if entry_size not in [4, 8, 12]:
                logger.warning(f"Unusual instrument entry size: {entry_size}")

            # SF2 instruments are always 8 bytes
            converted = bytearray()

            for i in range(num_instruments):
                start = i * entry_size
                end = min(start + entry_size, len(galway_data))
                entry = galway_data[start:end]

                if len(entry) == entry_size:
                    # Convert this entry
                    sf2_entry = self._convert_instrument_entry(entry, entry_size)
                    converted.extend(sf2_entry)
                else:
                    # Incomplete entry, pad with zeros
                    sf2_entry = self._get_default_instrument()
                    converted.extend(sf2_entry)

            confidence = 0.85  # Good confidence for instrument conversion
            return bytes(converted), confidence

        except Exception as e:
            logger.error(f"Instrument conversion error: {e}")
            self.conversion_errors.append(f"Instruments: {e}")
            # Return default instruments
            default_inst = bytes([0x0F, 0x00, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00])
            return default_inst * num_instruments, 0.5

    def convert_sequences(self, galway_data: bytes, galway_offset: int) -> Tuple[bytes, float]:
        """
        Convert Galway sequence data to SF2 format.

        Sequences are more compatible between formats since both use
        similar note/command structure.

        Args:
            galway_data: Raw Galway sequence data
            galway_offset: Offset in Galway address space

        Returns:
            (converted_data, confidence)
        """
        logger.debug(f"Converting sequences ({len(galway_data)} bytes)")

        try:
            # Sequences are mostly compatible, mainly need to map control bytes
            converted = bytearray()

            i = 0
            while i < len(galway_data):
                byte_val = galway_data[i]

                # Map control bytes
                if byte_val in self.GALWAY_CONTROL_BYTES:
                    control = self.GALWAY_CONTROL_BYTES[byte_val]

                    if control == 'end_marker':
                        converted.append(0x7F)  # Same in SF2
                    elif control == 'gate_marker':
                        converted.append(0x7E)  # Same mapping
                    elif control == 'gate_off':
                        # Galway: 0x80 = gate off
                        # SF2: use rest (0x00) or note-off sequence
                        converted.append(0x80)
                    elif control == 'padding':
                        converted.append(0xFF)  # Padding stays the same
                else:
                    # Regular note value
                    converted.append(byte_val)

                i += 1

            confidence = 0.90  # High confidence for sequence conversion
            return bytes(converted), confidence

        except Exception as e:
            logger.error(f"Sequence conversion error: {e}")
            self.conversion_errors.append(f"Sequences: {e}")
            return galway_data, 0.5  # Return original as fallback

    def convert_wave_table(self, galway_data: bytes, num_entries: int) -> Tuple[bytes, float]:
        """
        Convert Galway wave table to SF2 format.

        Wave tables are highly player-specific. Fallback strategy:
        - Try to identify waveform patterns
        - Use standard waveforms if not detectable

        Args:
            galway_data: Raw wave table data
            num_entries: Number of waveforms

        Returns:
            (converted_data, confidence)
        """
        logger.debug(f"Converting wave table ({num_entries} entries)")

        try:
            # Waveform IDs in C64:
            # 0x01 = Triangle
            # 0x02 = Sawtooth
            # 0x04 = Pulse
            # 0x08 = Noise
            # Combinations: 0x03 = Tri+Saw, 0x10 = Triangle+Gate, etc.

            converted = bytearray()

            # If we have raw waveform data, analyze it
            # Otherwise, generate standard wave table
            if len(galway_data) >= num_entries:
                # Assume 1 byte per entry
                for i in range(num_entries):
                    wave_val = galway_data[i]
                    # Normalize to standard waveform IDs
                    if wave_val in [0x01, 0x02, 0x04, 0x08, 0x10, 0x20]:
                        converted.append(wave_val)
                    else:
                        # Try to guess based on value
                        if wave_val < 50:
                            converted.append(0x01)  # Triangle
                        elif wave_val < 100:
                            converted.append(0x02)  # Sawtooth
                        elif wave_val < 150:
                            converted.append(0x04)  # Pulse
                        else:
                            converted.append(0x10)  # Triangle+Gate

                confidence = 0.60  # Lower confidence for wave conversion
            else:
                # Generate default wave table
                converted = bytes([0x10] * num_entries)  # Default: triangle+gate
                confidence = 0.40  # Very low confidence

            return bytes(converted), confidence

        except Exception as e:
            logger.error(f"Wave table conversion error: {e}")
            self.conversion_errors.append(f"Wave table: {e}")
            # Return default wave table
            return bytes([0x10] * num_entries), 0.3

    def convert_pulse_table(self, galway_data: bytes, num_entries: int) -> Tuple[bytes, float]:
        """
        Convert Galway pulse width table to SF2 format.

        Args:
            galway_data: Raw pulse table data
            num_entries: Number of pulse entries

        Returns:
            (converted_data, confidence)
        """
        logger.debug(f"Converting pulse table ({num_entries} entries)")

        try:
            # Pulse width: 12-bit value (0-4095)
            # Galway: Usually 2 bytes per entry (high, low)
            # SF2: Same format

            if len(galway_data) >= num_entries * 2:
                return galway_data[:num_entries * 2], 0.85  # Direct mapping

            elif len(galway_data) >= num_entries:
                # Single byte per entry, expand to 2 bytes
                converted = bytearray()
                for i in range(num_entries):
                    val = galway_data[i]
                    converted.append(val >> 4)  # High nibble
                    converted.append((val << 4) & 0xFF)  # Low nibble
                return bytes(converted), 0.70

            else:
                # Generate default pulse table
                converted = bytearray()
                for i in range(num_entries):
                    # Sweep from 0 to max pulse width
                    pulse = (i * 4095) // max(num_entries - 1, 1)
                    converted.append((pulse >> 8) & 0xFF)
                    converted.append(pulse & 0xFF)
                return bytes(converted), 0.50

        except Exception as e:
            logger.error(f"Pulse table conversion error: {e}")
            self.conversion_errors.append(f"Pulse table: {e}")
            # Generate default
            converted = bytearray()
            for i in range(num_entries):
                pulse = (i * 4095) // max(num_entries - 1, 1)
                converted.append((pulse >> 8) & 0xFF)
                converted.append(pulse & 0xFF)
            return bytes(converted), 0.30

    def convert_filter_table(self, galway_data: bytes, num_entries: int) -> Tuple[bytes, float]:
        """
        Convert Galway filter table to SF2 format.

        Filter tables are complex and highly player-specific.
        Fallback: use default filter settings.

        Args:
            galway_data: Raw filter table data
            num_entries: Number of filter entries

        Returns:
            (converted_data, confidence)
        """
        logger.debug(f"Converting filter table ({num_entries} entries)")

        try:
            # SID filter: 24 possible frequency settings
            # Filter types: 1=Low-pass, 2=Band-pass, 4=High-pass

            if len(galway_data) >= num_entries:
                # Assume 1 byte per entry (frequency)
                converted = bytearray()
                for i in range(num_entries):
                    freq = galway_data[i] if i < len(galway_data) else 0x00
                    # Normalize to 0-23 range
                    freq = (freq % 24) if freq > 0 else 0
                    converted.append(freq)
                return bytes(converted), 0.50

            else:
                # Generate default filter table
                return bytes([0x00] * num_entries), 0.30

        except Exception as e:
            logger.error(f"Filter table conversion error: {e}")
            self.conversion_errors.append(f"Filter table: {e}")
            return bytes([0x00] * num_entries), 0.20

    def _convert_instrument_entry(self, entry: bytes, entry_size: int) -> bytes:
        """
        Convert single instrument entry to SF2 format (8 bytes).

        Args:
            entry: Galway instrument entry
            entry_size: Size of entry in Galway format

        Returns:
            8-byte SF2 instrument entry
        """
        # SF2 instrument: 8 bytes
        result = bytearray(8)

        if entry_size >= 1:
            result[0] = entry[0]  # AD register (attack/decay)
        if entry_size >= 2:
            result[1] = entry[1]  # SR register (sustain/release)
        if entry_size >= 3:
            result[2] = entry[2]  # Waveform
        if entry_size >= 4:
            result[3] = entry[3]  # Pulse width or other

        # Rest filled with defaults
        if entry_size < 8:
            # Fill remaining with reasonable defaults
            result[4] = 0x00
            result[5] = 0x00
            result[6] = 0x00
            result[7] = 0x00

        return bytes(result)

    def _get_default_instrument(self) -> bytes:
        """Return default instrument (all zeros)."""
        return bytes(8)

    def get_conversion_report(self) -> Dict[str, Any]:
        """Get conversion report with statistics."""
        return {
            'sf2_driver': self.sf2_driver,
            'conversions_attempted': len(self.conversions),
            'errors': self.conversion_errors,
            'error_count': len(self.conversion_errors),
        }


# Module initialization
logger.debug("galway_format_converter module loaded")
