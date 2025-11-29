#!/usr/bin/env python3
"""Parser for SID Factory II player SID files.

This parser extracts music data from SID files that use the SID Factory II
player (driver by Laxity). Unlike Laxity NewPlayer files, these SIDs were
created in SF2 and exported, so the data format is already SF2-compatible.

The key insight is that when SF2 exports to SID, it:
1. Relocates all addresses to pack the data tightly
2. Strips the SF2 header blocks
3. Keeps table data identical (just at different addresses)

We can find tables by pattern-matching their content.
"""

import struct
import logging
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass
from pathlib import Path

from .models import ExtractedData, PSIDHeader, SequenceEvent

logger = logging.getLogger(__name__)


@dataclass
class SF2TableLocation:
    """Location of a table in SID memory"""
    address: int
    size: int
    data: bytes


class SF2PlayerParser:
    """Parser for SID Factory II player SID files.

    This parser is designed for SID files that were created in SID Factory II
    and exported using the SF2 packer. The data is already in SF2 format,
    just relocated to different addresses.
    """

    # Driver signature patterns (first bytes of SF2 drivers)
    SF2_DRIVER_SIGNATURES = [
        bytes([0x4C]),  # JMP instruction (common driver start)
    ]

    # Table type markers from SF2 format
    TABLE_TYPE_GENERIC = 0x00
    TABLE_TYPE_INSTRUMENTS = 0x80
    TABLE_TYPE_COMMANDS = 0x81

    def __init__(self, sid_path: str, sf2_reference_path: Optional[str] = None):
        """Initialize parser.

        Args:
            sid_path: Path to SID file
            sf2_reference_path: Optional path to original SF2 for comparison
        """
        self.sid_path = Path(sid_path)
        self.sf2_reference_path = Path(sf2_reference_path) if sf2_reference_path else None

        # Parsed data
        self.psid_header: Optional[PSIDHeader] = None
        self.c64_data: bytes = b''
        self.load_address: int = 0
        self.init_address: int = 0
        self.play_address: int = 0

        # Extracted table locations
        self.table_locations: Dict[str, SF2TableLocation] = {}

    def parse_sid_header(self) -> PSIDHeader:
        """Parse PSID header from SID file."""
        with open(self.sid_path, 'rb') as f:
            data = f.read()

        magic = data[0:4].decode('ascii')
        version = struct.unpack('>H', data[4:6])[0]
        data_offset = struct.unpack('>H', data[6:8])[0]
        load_address = struct.unpack('>H', data[8:10])[0]
        init_address = struct.unpack('>H', data[10:12])[0]
        play_address = struct.unpack('>H', data[12:14])[0]
        songs = struct.unpack('>H', data[14:16])[0]
        start_song = struct.unpack('>H', data[16:18])[0]
        speed = struct.unpack('>I', data[18:22])[0]

        name = data[22:54].split(b'\x00')[0].decode('latin-1')
        author = data[54:86].split(b'\x00')[0].decode('latin-1')
        copyright = data[86:118].split(b'\x00')[0].decode('latin-1')

        # Get actual load address from data if header says 0
        if load_address == 0:
            load_address = data[data_offset] | (data[data_offset + 1] << 8)

        # Store C64 data (skip load address bytes if embedded)
        if struct.unpack('>H', data[8:10])[0] == 0:
            self.c64_data = data[data_offset + 2:]
        else:
            self.c64_data = data[data_offset:]

        self.load_address = load_address
        self.init_address = init_address
        self.play_address = play_address

        self.psid_header = PSIDHeader(
            magic=magic, version=version, data_offset=data_offset,
            load_address=load_address, init_address=init_address,
            play_address=play_address, songs=songs, start_song=start_song,
            speed=speed, name=name, author=author, copyright=copyright
        )

        return self.psid_header

    def get_byte(self, addr: int) -> int:
        """Get byte at C64 address."""
        offset = addr - self.load_address
        if 0 <= offset < len(self.c64_data):
            return self.c64_data[offset]
        return 0

    def get_word(self, addr: int) -> int:
        """Get word (little-endian) at C64 address."""
        return self.get_byte(addr) | (self.get_byte(addr + 1) << 8)

    def get_bytes(self, addr: int, count: int) -> bytes:
        """Get bytes at C64 address."""
        offset = addr - self.load_address
        if 0 <= offset < len(self.c64_data):
            return self.c64_data[offset:offset + count]
        return bytes(count)

    def find_pattern(self, pattern: bytes, start: int = 0) -> Optional[int]:
        """Find pattern in C64 data, return address."""
        idx = self.c64_data.find(pattern, start)
        if idx >= 0:
            return self.load_address + idx
        return None

    def find_table_by_reference(self, sf2_table_data: bytes, table_name: str) -> Optional[SF2TableLocation]:
        """Find a table in SID memory by matching data from SF2 reference.

        Args:
            sf2_table_data: Table data from SF2 file
            table_name: Name of table for logging

        Returns:
            SF2TableLocation if found, None otherwise
        """
        if len(sf2_table_data) < 8:
            return None

        # Search for first 16 bytes (or less if table is small)
        search_len = min(16, len(sf2_table_data))
        search_pattern = sf2_table_data[:search_len]

        addr = self.find_pattern(search_pattern)
        if addr:
            logger.debug(f"Found {table_name} table at ${addr:04X}")
            return SF2TableLocation(
                address=addr,
                size=len(sf2_table_data),
                data=self.get_bytes(addr, len(sf2_table_data))
            )

        return None

    def extract_with_sf2_reference(self) -> ExtractedData:
        """Extract data using SF2 reference file for table locations.

        This method uses the original SF2 file to find exact table data
        in the SID memory by pattern matching.
        """
        if not self.sf2_reference_path or not self.sf2_reference_path.exists():
            raise ValueError("SF2 reference file required for this method")

        # Parse SID header if not done
        if not self.psid_header:
            self.parse_sid_header()

        # Parse SF2 reference file
        with open(self.sf2_reference_path, 'rb') as f:
            sf2_data = f.read()

        sf2_load_addr = sf2_data[0] | (sf2_data[1] << 8)

        # Parse SF2 header blocks to get table info
        tables = self._parse_sf2_tables(sf2_data, sf2_load_addr)

        # Find each table in SID memory
        extracted_tables = {}
        for name, info in tables.items():
            table_data = sf2_data[info['offset']:info['offset'] + info['size']]
            location = self.find_table_by_reference(table_data, name)
            if location:
                extracted_tables[name] = location
                self.table_locations[name] = location

        # Build ExtractedData from found tables
        return self._build_extracted_data(extracted_tables)

    def _parse_sf2_tables(self, sf2_data: bytes, load_addr: int) -> Dict:
        """Parse SF2 header to get table information."""
        tables = {}

        # Find tables block
        offset = 4
        while offset < len(sf2_data) - 2:
            block_id = sf2_data[offset]
            if block_id == 0xFF:
                break

            block_size = sf2_data[offset + 1]
            block_data = sf2_data[offset + 2:offset + 2 + block_size]

            if block_id == 3:  # DRIVER_TABLES
                tables = self._parse_tables_block(block_data, sf2_data, load_addr)

            offset += 2 + block_size

        return tables

    def _parse_tables_block(self, block_data: bytes, sf2_data: bytes, load_addr: int) -> Dict:
        """Parse driver tables block."""
        tables = {}
        idx = 0

        while idx < len(block_data):
            table_type = block_data[idx]
            if table_type == 0xFF:
                break

            if idx + 3 > len(block_data):
                break

            table_id = block_data[idx + 1]

            # Read name (may contain PETSCII screen codes, so just get first char)
            name_start = idx + 3
            name_end = name_start
            while name_end < len(block_data) and block_data[name_end] != 0:
                name_end += 1
            raw_name = block_data[name_start:name_end]
            # First character is usually the meaningful letter
            first_char = chr(raw_name[0]) if raw_name else ''

            # Read table info
            pos = name_end + 1
            if pos + 12 <= len(block_data):
                addr = struct.unpack('<H', block_data[pos+5:pos+7])[0]
                columns = struct.unpack('<H', block_data[pos+7:pos+9])[0]
                rows = struct.unpack('<H', block_data[pos+9:pos+11])[0]

                file_offset = addr - load_addr + 2
                size = columns * rows

                # Determine name by type first, then by first character
                if table_type == self.TABLE_TYPE_INSTRUMENTS:  # 0x80
                    norm_name = 'Instruments'
                elif table_type == self.TABLE_TYPE_COMMANDS:  # 0x81
                    norm_name = 'Commands'
                elif first_char == 'H' and raw_name[:2] == b'HR':
                    norm_name = 'HR'
                else:
                    # Use first character to determine type
                    name_map = {
                        'W': 'Wave',
                        'P': 'Pulse',
                        'F': 'Filter',
                        'A': 'Arpeggio',
                        'T': 'Tempo',
                        'I': 'Init',  # Init table (different from Instruments which has type 0x80)
                    }
                    norm_name = name_map.get(first_char, f'Unknown_{table_id}')

                tables[norm_name] = {
                    'type': table_type,
                    'id': table_id,
                    'address': addr,
                    'columns': columns,
                    'rows': rows,
                    'offset': file_offset,
                    'size': size,
                }

                idx = pos + 12
            else:
                break

        return tables

    def _build_extracted_data(self, tables: Dict[str, SF2TableLocation]) -> ExtractedData:
        """Build ExtractedData from found tables."""
        # Get table data
        wave_data = tables.get('Wave', SF2TableLocation(0, 0, b'')).data
        pulse_data = tables.get('Pulse', SF2TableLocation(0, 0, b'')).data
        filter_data = tables.get('Filter', SF2TableLocation(0, 0, b'')).data
        instr_data = tables.get('Instruments', SF2TableLocation(0, 0, b'')).data

        # Parse instruments (6 bytes each, column-major for 32 instruments)
        instruments = []
        if instr_data:
            # Column-major: first 32 bytes are AD, next 32 are SR, etc.
            for i in range(min(32, len(instr_data) // 6)):
                instr = bytes([
                    instr_data[i] if i < len(instr_data) else 0,  # AD
                    instr_data[32 + i] if 32 + i < len(instr_data) else 0,  # SR
                    instr_data[64 + i] if 64 + i < len(instr_data) else 0,  # Wave ptr
                    instr_data[96 + i] if 96 + i < len(instr_data) else 0,  # Pulse ptr
                    instr_data[128 + i] if 128 + i < len(instr_data) else 0,  # Filter ptr
                    instr_data[160 + i] if 160 + i < len(instr_data) else 0,  # Flags
                ])
                instruments.append(instr)

        # For now, sequences and orderlists need more work to extract
        # They're stored in a packed format that needs the music data block
        sequences: List[List[SequenceEvent]] = []
        orderlists: List[List[Tuple[int, int]]] = []

        return ExtractedData(
            header=self.psid_header,
            c64_data=self.c64_data,
            load_address=self.load_address,
            sequences=sequences,
            orderlists=orderlists,
            instruments=instruments,
            wavetable=wave_data,
            pulsetable=pulse_data,
            filtertable=filter_data,
        )

    def extract(self) -> ExtractedData:
        """Extract music data from SF2 player SID.

        If SF2 reference is available, uses pattern matching.
        Otherwise, attempts heuristic extraction.
        """
        if self.sf2_reference_path and self.sf2_reference_path.exists():
            return self.extract_with_sf2_reference()
        else:
            return self.extract_heuristic()

    def extract_heuristic(self) -> ExtractedData:
        """Extract data using heuristics (without SF2 reference).

        This is more challenging as we need to find tables without
        knowing their exact content.
        """
        if not self.psid_header:
            self.parse_sid_header()

        logger.info("Extracting SF2 player data using heuristics...")

        # SF2 driver 11 has a characteristic structure
        # The init routine at init_address typically sets up playback
        # Play routine follows shortly after

        # Look for table patterns
        # Wave table: pairs of (waveform, note_offset), ends with 0x7F
        # Pulse table: groups of 4 bytes (value, delta, duration, next)
        # Filter table: groups of 4 bytes

        # For now, return empty data - heuristic extraction needs more work
        return ExtractedData(
            header=self.psid_header,
            c64_data=self.c64_data,
            load_address=self.load_address,
            sequences=[],
            orderlists=[],
            instruments=[],
            wavetable=b'',
            pulsetable=b'',
            filtertable=b'',
        )


def extract_sf2_player_sid(sid_path: str, sf2_path: Optional[str] = None) -> ExtractedData:
    """Convenience function to extract data from SF2 player SID.

    Args:
        sid_path: Path to SID file
        sf2_path: Optional path to original SF2 for reference

    Returns:
        ExtractedData with tables and music data
    """
    parser = SF2PlayerParser(sid_path, sf2_path)
    return parser.extract()
