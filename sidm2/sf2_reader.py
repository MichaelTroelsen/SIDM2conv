"""SF2 Reader - Extract music data from SF2 format files

This module reads SF2 (SID Factory II) format data embedded in SID files.
SF2-exported SIDs contain the complete SF2 structure in C64 memory.
"""

import struct
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class SF2Reader:
    """Read and extract music data from SF2 format structures"""

    # SF2 file format constants
    SF2_FILE_ID = 0x1337

    # Block type IDs
    BLOCK_DESCRIPTOR = 0x01
    BLOCK_DRIVER_COMMON = 0x02
    BLOCK_DRIVER_TABLES = 0x03
    BLOCK_INSTRUMENT_DESC = 0x04
    BLOCK_MUSIC_DATA = 0x05
    BLOCK_END = 0xFF

    def __init__(self, sf2_data: bytes, load_address: int):
        """Initialize SF2 Reader

        Args:
            sf2_data: Raw SF2 structure data (C64 memory format with load address prefix)
            load_address: C64 load address
        """
        self.sf2_data = sf2_data
        self.load_address = load_address
        self.sequences = []
        self.orderlists = [[], [], []]  # 3 voices
        self.instruments = []
        self.wavetable = b''
        self.pulsetable = b''
        self.filtertable = b''

        # Parse the SF2 header to find data locations
        self._parse_header()

    def _parse_header(self) -> bool:
        """Parse SF2 header and find block locations"""
        # Initialize block_offsets first to prevent AttributeError on early returns
        self.block_offsets = {}

        if len(self.sf2_data) < 4:
            logger.warning("SF2 data too short for header")
            return False

        # Load address (2 bytes, little-endian)
        load_addr = struct.unpack('<H', self.sf2_data[0:2])[0]

        # File ID marker ($1337)
        file_id = struct.unpack('<H', self.sf2_data[2:4])[0]
        if file_id != self.SF2_FILE_ID:
            logger.warning(f"Invalid SF2 file ID: ${file_id:04X} (expected $1337)")
            return False

        logger.debug(f"Valid SF2 structure found at ${load_addr:04X}")

        # Parse blocks to find table locations
        offset = 4  # After load address and file ID

        while offset < len(self.sf2_data):
            if offset + 3 > len(self.sf2_data):
                break

            block_type = self.sf2_data[offset]
            block_size = struct.unpack('<H', self.sf2_data[offset+1:offset+3])[0]

            if block_type == self.BLOCK_END:
                break

            self.block_offsets[block_type] = (offset + 3, block_size)
            logger.debug(f"  Block ${block_type:02X}: offset {offset+3}, size {block_size}")

            offset += 3 + block_size

        return True

    def extract_sequences(self) -> List[bytes]:
        """Extract sequence data from SF2 structure

        Returns:
            List of sequence byte arrays
        """
        if self.BLOCK_MUSIC_DATA not in self.block_offsets:
            logger.warning("No music data block found")
            return []

        offset, size = self.block_offsets[self.BLOCK_MUSIC_DATA]
        music_data = self.sf2_data[offset:offset+size]

        # Music data contains sequences - extract them
        # Sequences are variable-length, terminated by 0x7F
        sequences = []
        seq_offset = 0

        while seq_offset < len(music_data):
            # Find next sequence end marker (0x7F)
            end_idx = music_data.find(b'\x7F', seq_offset)
            if end_idx == -1:
                break

            # Extract sequence including end marker
            seq_data = music_data[seq_offset:end_idx+1]
            if len(seq_data) > 1:  # Skip empty sequences
                sequences.append(seq_data)

            seq_offset = end_idx + 1

        logger.debug(f"Extracted {len(sequences)} sequences from music data")
        self.sequences = sequences
        return sequences

    def extract_orderlists(self) -> List[List[int]]:
        """Extract orderlist data for each voice

        Returns:
            List of 3 orderlists (one per voice)
        """
        # Orderlists are typically embedded in the music data block
        # or in a separate structure. For now, return empty lists
        # as orderlists are less critical than sequences.
        logger.debug("Orderlist extraction not yet implemented - using empty lists")
        return [[], [], []]

    def extract_instruments(self) -> List[bytes]:
        """Extract instrument definitions

        Returns:
            List of instrument byte arrays
        """
        if self.BLOCK_INSTRUMENT_DESC not in self.block_offsets:
            logger.warning("No instrument block found")
            return []

        offset, size = self.block_offsets[self.BLOCK_INSTRUMENT_DESC]
        instr_data = self.sf2_data[offset:offset+size]

        # Instruments are typically 6 bytes each (Driver 11 format)
        # ADSR1, ADSR2, WavePtr, PulsePtr, FilterPtr, Flags
        instruments = []
        instr_size = 6

        for i in range(0, len(instr_data), instr_size):
            if i + instr_size <= len(instr_data):
                instr = instr_data[i:i+instr_size]
                instruments.append(instr)

        logger.debug(f"Extracted {len(instruments)} instruments")
        self.instruments = instruments
        return instruments

    def extract_wave_table(self) -> bytes:
        """Extract wave table data

        Returns:
            Wave table bytes
        """
        if self.BLOCK_DRIVER_TABLES not in self.block_offsets:
            logger.warning("No driver tables block found")
            return b''

        offset, size = self.block_offsets[self.BLOCK_DRIVER_TABLES]
        table_data = self.sf2_data[offset:offset+size]

        # Driver tables contain wave, pulse, and filter tables
        # Wave table is typically first, ending with 0x7F
        wave_end = table_data.find(b'\x7F')
        if wave_end != -1:
            self.wavetable = table_data[:wave_end+1]
            logger.debug(f"Extracted wave table: {len(self.wavetable)} bytes")
            return self.wavetable

        logger.warning("No wave table end marker found")
        return b''

    def extract_pulse_table(self) -> bytes:
        """Extract pulse table data

        Returns:
            Pulse table bytes
        """
        if not self.wavetable:
            self.extract_wave_table()

        if self.BLOCK_DRIVER_TABLES not in self.block_offsets:
            return b''

        offset, size = self.block_offsets[self.BLOCK_DRIVER_TABLES]
        table_data = self.sf2_data[offset:offset+size]

        # Pulse table follows wave table
        wave_len = len(self.wavetable)
        pulse_start = wave_len

        # Pulse table also ends with 0x7F
        pulse_end = table_data.find(b'\x7F', pulse_start)
        if pulse_end != -1:
            self.pulsetable = table_data[pulse_start:pulse_end+1]
            logger.debug(f"Extracted pulse table: {len(self.pulsetable)} bytes")
            return self.pulsetable

        logger.warning("No pulse table end marker found")
        return b''

    def extract_filter_table(self) -> bytes:
        """Extract filter table data

        Returns:
            Filter table bytes
        """
        if not self.pulsetable:
            self.extract_pulse_table()

        if self.BLOCK_DRIVER_TABLES not in self.block_offsets:
            return b''

        offset, size = self.block_offsets[self.BLOCK_DRIVER_TABLES]
        table_data = self.sf2_data[offset:offset+size]

        # Filter table follows pulse table
        wave_len = len(self.wavetable)
        pulse_len = len(self.pulsetable)
        filter_start = wave_len + pulse_len

        # Filter table ends with 0x7F or end of block
        filter_end = table_data.find(b'\x7F', filter_start)
        if filter_end != -1:
            self.filtertable = table_data[filter_start:filter_end+1]
        else:
            # Take rest of table data
            self.filtertable = table_data[filter_start:]

        logger.debug(f"Extracted filter table: {len(self.filtertable)} bytes")
        return self.filtertable
