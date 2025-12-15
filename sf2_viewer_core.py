#!/usr/bin/env python3
"""
SF2 Viewer Core - Parse and extract data from SF2 files
Provides complete parsing of SF2 format with support for all block types and tables
"""

import struct
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class BlockType(Enum):
    """SF2 Block Type IDs"""
    DESCRIPTOR = 0x01
    DRIVER_COMMON = 0x02
    DRIVER_TABLES = 0x03
    INSTRUMENT_DESC = 0x04
    MUSIC_DATA = 0x05
    COLOR_RULES = 0x06
    INSERT_DELETE_RULES = 0x07
    ACTION_RULES = 0x08
    INSTRUMENT_DATA_DESC = 0x09
    END = 0xFF


class TableDataLayout(Enum):
    """How table data is organized in memory"""
    ROW_MAJOR = 0x00      # Row by row: col0row0, col1row0, col0row1, col1row1...
    COLUMN_MAJOR = 0x01   # Column by column: row0col0, row0col1, row1col0...


class Driver11TableDimensions:
    """Implicit table dimensions and layouts for Driver 11 (per SID Factory II specification).

    Table dimensions and layouts are defined by the driver, not stored in the SF2 file descriptor.
    The descriptor stores these, but they should match the driver's spec.
    """

    # Map table type to (row_count, column_count)
    DIMENSIONS = {
        0x81: (32, 6),      # Instruments: 32 instruments × 6 bytes each
        0x01: (128, 2),     # Wave: 128 rows × 2 bytes each
        0x02: (64, 4),      # Pulse: 64 rows × 4 bytes each
        0x03: (64, 4),      # Filter: 64 rows × 4 bytes each
        0x20: (32, 2),      # Arpeggio: 32 arpeggios × 2 bytes each
        0x40: (32, 3),      # Commands: 32 commands × 3 bytes each
    }

    # Map table type to data layout (0=row-major, 1=column-major)
    LAYOUTS = {
        0x81: 1,  # Instruments: column-major
        0x01: 1,  # Wave: column-major
        0x02: 1,  # Pulse: column-major
        0x03: 1,  # Filter: column-major
        0x20: 1,  # Arpeggio: column-major
        0x40: 1,  # Commands: column-major
    }

    @staticmethod
    def get_dimensions(table_type: int) -> Tuple[int, int]:
        """Get correct dimensions for a table type.

        Args:
            table_type: SF2 table type byte

        Returns:
            Tuple of (row_count, column_count), or (0, 0) if unknown
        """
        return Driver11TableDimensions.DIMENSIONS.get(table_type, (0, 0))

    @staticmethod
    def get_layout(table_type: int) -> int:
        """Get correct data layout for a table type.

        Args:
            table_type: SF2 table type byte

        Returns:
            0 for row-major, 1 for column-major
        """
        return Driver11TableDimensions.LAYOUTS.get(table_type, 0)


@dataclass
class TableDescriptor:
    """Describes a music table (instruments, waves, etc.)"""
    type: int
    id: int
    name: str
    data_layout: TableDataLayout
    address: int
    column_count: int
    row_count: int
    properties: int


@dataclass
class DriverCommonAddresses:
    """Critical driver routine addresses"""
    init_address: int
    stop_address: int
    play_address: int
    sid_channel_offset: int
    driver_state: int
    tick_counter: int
    orderlist_index: int
    sequence_index: int
    sequence_in_use: int
    current_sequence: int
    current_transpose: int
    event_duration: int
    next_instrument: int
    next_command: int
    next_note: int
    next_note_tied: int
    tempo_counter: int
    trigger_sync: int
    note_trigger_value: int

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary for display"""
        return {
            'Init': self.init_address,
            'Stop': self.stop_address,
            'Play': self.play_address,
            'SID Channel Offset': self.sid_channel_offset,
            'Driver State': self.driver_state,
            'Tick Counter': self.tick_counter,
            'OrderList Index': self.orderlist_index,
            'Sequence Index': self.sequence_index,
            'Sequence in Use': self.sequence_in_use,
            'Current Sequence': self.current_sequence,
            'Current Transpose': self.current_transpose,
            'Event Duration': self.event_duration,
            'Next Instrument': self.next_instrument,
            'Next Command': self.next_command,
            'Next Note': self.next_note,
            'Next Note Tied': self.next_note_tied,
            'Tempo Counter': self.tempo_counter,
            'Trigger Sync': self.trigger_sync,
            'Note Trigger Value': self.note_trigger_value,
        }


@dataclass
class SequenceEntry:
    """Single entry in a music sequence"""
    note: int        # 0x00-0x6F (MIDI notes), 0x7E (note off), 0x7F (end)
    command: int     # 0x00-0x0F (no command to 15 standard commands)
    param1: int      # First parameter (varies by command)
    param2: int      # Second parameter (varies by command)
    duration: int    # How many ticks this entry lasts

    def note_name(self) -> str:
        """Convert note value to name"""
        if self.note == 0x7E:
            return "---"
        elif self.note == 0x7F:
            return "END"
        else:
            notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            octave = self.note // 12
            note = self.note % 12
            return f"{notes[note]}-{octave}"

    def command_name(self) -> str:
        """Convert command byte to name"""
        commands = {
            0x00: "---",
            0x01: "Inst",
            0x02: "Vol",
            0x03: "Arp",
            0x04: "Port",
            0x05: "Vib",
            0x06: "Trem",
            0x07: "Duty",
            0x08: "Filt",
            0x09: "Res",
            0x0A: "HRst",
            0x0B: "Skip",
            0x0C: "Dly",
            0x0D: "Gate",
            0x0E: "Res",
            0x0F: "End"
        }
        return commands.get(self.command, f"Cmd{self.command:02X}")


@dataclass
class MusicDataInfo:
    """Information extracted from Music Data block"""
    num_tracks: int
    orderlist_address: int
    sequence_data_address: int
    sequence_index_address: int
    default_sequence_length: int
    default_tempo: int


class SF2Parser:
    """Parse and extract data from SF2 files"""

    # Constants
    SF2_MAGIC = 0x1337
    MAX_INSTRUMENTS = 32
    MAX_SEQUENCES = 128

    def __init__(self, file_path: str):
        """Initialize parser with file path"""
        self.file_path = file_path
        self.data = b''
        self.load_address = 0
        self.magic_id = 0
        self.blocks: Dict[BlockType, Tuple[int, bytes]] = {}
        self.driver_info = {}
        self.driver_common: Optional[DriverCommonAddresses] = None
        self.table_descriptors: List[TableDescriptor] = []
        self.music_data_info: Optional[MusicDataInfo] = None
        self.orderlist: List[int] = []
        self.sequences: Dict[int, List[SequenceEntry]] = {}
        self.memory = bytearray(65536)

        self.parse()

    def parse(self) -> bool:
        """Parse the SF2 file"""
        try:
            with open(self.file_path, 'rb') as f:
                self.data = f.read()

            if len(self.data) < 4:
                logger.error("File too small")
                return False

            # Read PRG header
            self.load_address = struct.unpack('<H', self.data[0:2])[0]
            self.magic_id = struct.unpack('<H', self.data[2:4])[0]

            if self.magic_id != self.SF2_MAGIC:
                logger.warning(f"Invalid magic ID: 0x{self.magic_id:04X} (expected 0x{self.SF2_MAGIC:04X})")
                return False

            # Load data into memory
            c64_data = self.data[2:]
            self.memory[self.load_address:self.load_address + len(c64_data)] = c64_data

            # Parse header blocks
            offset = 4
            while offset < len(self.data):
                if offset + 2 > len(self.data):
                    break

                block_id = self.data[offset]
                block_size = self.data[offset + 1]

                if block_id == BlockType.END.value:
                    break

                if offset + 2 + block_size > len(self.data):
                    break

                block_data = self.data[offset + 2:offset + 2 + block_size]
                block_type = BlockType(block_id) if block_id in [e.value for e in BlockType] else None

                if block_type:
                    self.blocks[block_type] = (offset, block_data)
                    logger.debug(f"Found block {block_type.name} at offset {offset}, size {block_size}")

                offset += 2 + block_size

            # Parse critical blocks
            self._parse_descriptor_block()
            self._parse_driver_common_block()
            self._parse_driver_tables_block()
            self._parse_music_data_block()
            self._parse_orderlist()
            self._parse_sequences()

            return True

        except Exception as e:
            logger.error(f"Parse error: {e}")
            return False

    def _clean_string(self, s: str) -> str:
        """Clean non-printable characters from string.

        Replaces control characters (0x00-0x1F, 0x7F-0x9F) with their hex representation
        and keeps printable ASCII/Latin-1 characters (0x20-0x7E, 0xA0-0xFF).

        Args:
            s: Raw string with possible non-printable characters

        Returns:
            Cleaned string with non-printable characters replaced with [0xNN] notation
        """
        result = []
        for char in s:
            code = ord(char)
            # Keep printable ASCII (0x20-0x7E) and extended Latin-1 (0xA0-0xFF)
            if (0x20 <= code <= 0x7E) or (0xA0 <= code <= 0xFF):
                result.append(char)
            # Replace control characters with hex notation
            elif code == 0x00:  # Skip null terminator
                break
            else:
                # Replace with [0xNN] notation for visibility
                result.append(f"[0x{code:02X}]")
        return ''.join(result).strip()

    def _infer_table_name(self, table_type: int, table_id: int, raw_name: str,
                         row_count: int = 0, column_count: int = 0) -> str:
        """Infer table name from type, ID, and dimensions if raw name is unavailable.

        Args:
            table_type: Table type byte
            table_id: Table ID byte
            raw_name: Raw name from descriptor
            row_count: Number of rows (optional, for dimension-based inference)
            column_count: Number of columns (optional, for dimension-based inference)

        Returns:
            Best guess for table name
        """
        # If raw name is just control characters or very short, try to infer
        # Remove hex notation [0xNN] patterns
        import re
        cleaned = re.sub(r'\[0x[0-9A-Fa-f]{2}\]', '', raw_name)
        printable_chars = ''.join(c for c in cleaned if 0x20 <= ord(c) <= 0x7E)

        if not printable_chars or len(printable_chars) <= 1:
            # Check for specific table type patterns
            if table_type == 0x81:
                return "Instruments"
            elif table_type == 0x80:
                return "Commands"
            elif table_type == 0x40:
                return "Commands"
            elif table_type == 0x01:
                return "Wave"
            elif table_type == 0x02:
                return "Pulse"
            elif table_type == 0x03:
                return "Filter"
            elif table_type == 0x20:
                return "Arpeggio"
            elif table_type == 0x00:
                # For generic tables (type 0x00), try to infer from dimensions
                if row_count > 0 and column_count > 0:
                    # Common table dimension patterns
                    if (row_count == 128 or row_count == 256) and (column_count == 2 or column_count == 3):
                        return "Wave"
                    elif (row_count == 64 or row_count == 256) and column_count == 4:
                        return "Pulse"
                    elif (row_count == 64 or row_count == 256) and column_count == 4:
                        return "Filter"
                    elif row_count == 32 and column_count == 2:
                        return "Arpeggio"
                    elif (row_count == 256 or row_count == 128) and column_count == 1:
                        return "Tempo"
                    elif row_count == 16 and column_count == 2:
                        return "HR"
                    elif row_count == 32 and column_count == 1:
                        return "Init"

                # Fallback for type 0x00
                if table_id == 0:
                    return "Sequence Data"
                else:
                    return f"Table[0x{table_type:02X}] ({row_count}x{column_count})"

            # Generic fallback
            return f"Table[0x{table_type:02X}]"

        # Otherwise use the cleaned name
        return raw_name

    def _parse_descriptor_block(self):
        """Parse Block 1: Descriptor (driver info)"""
        if BlockType.DESCRIPTOR not in self.blocks:
            return

        offset, data = self.blocks[BlockType.DESCRIPTOR]

        if len(data) < 3:
            return

        driver_type = data[0]
        driver_size = struct.unpack('<H', data[1:3])[0]

        # Extract driver name (null-terminated string)
        name_end = data.find(b'\x00', 3)
        if name_end == -1:
            name_end = len(data)

        # Use latin-1 to preserve all bytes, then clean non-printable characters
        driver_name_raw = data[3:name_end].decode('latin-1')
        driver_name = self._clean_string(driver_name_raw)

        self.driver_info = {
            'type': driver_type,
            'size': driver_size,
            'name': driver_name,
            'size_hex': f"0x{driver_size:04X}",
        }

        logger.info(f"Driver: {driver_name} (size: ${driver_size:04X})")

    def _parse_driver_common_block(self):
        """Parse Block 2: Driver Common (addresses)"""
        if BlockType.DRIVER_COMMON not in self.blocks:
            return

        offset, data = self.blocks[BlockType.DRIVER_COMMON]

        if len(data) < 40:
            logger.warning("Driver Common block too small")
            return

        def read_addr(pos):
            return struct.unpack('<H', data[pos:pos+2])[0]

        self.driver_common = DriverCommonAddresses(
            init_address=read_addr(0x00),
            stop_address=read_addr(0x02),
            play_address=read_addr(0x04),
            sid_channel_offset=read_addr(0x06),
            driver_state=read_addr(0x08),
            tick_counter=read_addr(0x0A),
            orderlist_index=read_addr(0x0C),
            sequence_index=read_addr(0x0E),
            sequence_in_use=read_addr(0x10),
            current_sequence=read_addr(0x12),
            current_transpose=read_addr(0x14),
            event_duration=read_addr(0x16),
            next_instrument=read_addr(0x18),
            next_command=read_addr(0x1A),
            next_note=read_addr(0x1C),
            next_note_tied=read_addr(0x1E),
            tempo_counter=read_addr(0x20),
            trigger_sync=read_addr(0x22),
            note_trigger_value=data[0x24],
        )

    def _parse_driver_tables_block(self):
        """Parse Block 3: Driver Tables (table descriptors)

        Per SF2 specification, each table descriptor has:
        - Type (1 byte) at offset 0x00
        - ID (1 byte) at offset 0x01
        - Name Length (1 byte) at offset 0x02 (includes null terminator)
        - Name (variable length) at offset 0x03
        - Data Layout, Flags, Rules (5 bytes)
        - Address (2 bytes little-endian)
        - Column Count (2 bytes little-endian)
        - Row Count (2 bytes little-endian)
        - Visible Rows (1 byte)
        Total fixed portion: 12 bytes after name

        This implementation correctly reads the name length field to determine
        variable-length name portion, then reads all remaining fields at the
        correct offsets.
        """
        if BlockType.DRIVER_TABLES not in self.blocks:
            return

        offset, data = self.blocks[BlockType.DRIVER_TABLES]

        pos = 0
        while pos < len(data):
            # Need at least 4 bytes: type, id, text_field_size, and at least null terminator for name
            if pos + 4 > len(data):
                break

            table_type = data[pos + 0]
            table_id = data[pos + 1]
            text_field_size = data[pos + 2]  # NOT the name length - just text field size

            # Check for end marker
            if table_type == 0xFF:
                break

            # Name starts at pos + 3 and continues until we find a null terminator
            name_start = pos + 3

            # Find the null terminator
            null_pos = name_start
            while null_pos < len(data) and data[null_pos] != 0:
                null_pos += 1

            if null_pos >= len(data):
                # Corrupt data - no null terminator found
                break

            # Extract name (bytes from name_start to null_pos, excluding the null)
            name_bytes = data[name_start:null_pos]
            try:
                # Use ASCII decoding per SF2 specification
                name_raw = name_bytes.decode('ascii')
            except UnicodeDecodeError:
                # Fall back to latin-1 if ASCII fails, then clean
                name_raw = name_bytes.decode('latin-1')
                name_raw = self._clean_string(name_raw)

            # Position of remaining fields (right after the null terminator)
            field_start = null_pos + 1

            # Verify we have enough data for remaining 12 fixed bytes
            if field_start + 12 > len(data):
                break

            # Read DataLayout (1B) @ field_start + 0
            layout_value = data[field_start + 0]
            try:
                data_layout = TableDataLayout(layout_value)
            except ValueError:
                # Default to ROW_MAJOR if invalid
                data_layout = TableDataLayout.ROW_MAJOR

            # Read flags, rule IDs (1B each) @ field_start + 1-4
            flags = data[field_start + 1]
            insert_delete_rule = data[field_start + 2]
            enter_action_rule = data[field_start + 3]
            color_rule = data[field_start + 4]

            # Address is 2 bytes little-endian @ field_start + 5
            address = struct.unpack('<H', data[field_start + 5:field_start + 7])[0]

            # ColumnCount is 2 bytes little-endian @ field_start + 7
            # RowCount is 2 bytes little-endian @ field_start + 9
            stored_column_count = struct.unpack('<H', data[field_start + 7:field_start + 9])[0]
            stored_row_count = struct.unpack('<H', data[field_start + 9:field_start + 11])[0]

            # VisibleRowCount is 1 byte @ field_start + 11
            visible_rows = data[field_start + 11] if field_start + 11 < len(data) else 0

            # Use the stored dimensions from the file (they ARE correct for this file)
            # User's test file has 19 instruments (0x13), stored values should be trusted
            row_count = stored_row_count
            column_count = stored_column_count

            # Try to infer better name if raw name is unclear
            # Pass dimensions for type 0x00 table identification
            final_name = self._infer_table_name(table_type, table_id, name_raw,
                                               row_count, column_count)

            descriptor = TableDescriptor(
                type=table_type,
                id=table_id,
                name=final_name,
                data_layout=data_layout,
                address=address,
                column_count=column_count,
                row_count=row_count,
                properties=flags,
            )

            self.table_descriptors.append(descriptor)
            logger.debug(
                f"Table: {final_name} (type=0x{table_type:02X}, id={table_id}) "
                f"@ ${address:04X} dims={row_count}x{column_count} layout={'CM' if data_layout == TableDataLayout.COLUMN_MAJOR else 'RM'}"
            )

            # Move to next descriptor (3 header + name_length + 12 fixed fields)
            pos = field_start + 12

    def get_table_data(self, descriptor: TableDescriptor) -> List[List[int]]:
        """Extract table data from memory"""
        table_data = []

        for row in range(descriptor.row_count):
            row_data = []
            for col in range(descriptor.column_count):
                if descriptor.data_layout == TableDataLayout.ROW_MAJOR:
                    addr = descriptor.address + row * descriptor.column_count + col
                else:  # COLUMN_MAJOR
                    addr = descriptor.address + col * descriptor.row_count + row

                if addr < len(self.memory):
                    row_data.append(self.memory[addr])
                else:
                    row_data.append(0)

            table_data.append(row_data)

        return table_data

    def _parse_music_data_block(self):
        """Parse Block 5: Music Data (sequence/orderlist organization)"""
        if BlockType.MUSIC_DATA not in self.blocks:
            return

        offset, data = self.blocks[BlockType.MUSIC_DATA]

        if len(data) < 10:
            logger.warning("Music Data block too small")
            return

        try:
            num_tracks = struct.unpack('<H', data[0:2])[0]
            orderlist_addr = struct.unpack('<H', data[2:4])[0]
            seq_data_addr = struct.unpack('<H', data[4:6])[0]
            seq_idx_addr = struct.unpack('<H', data[6:8])[0]
            default_len = data[8]
            default_tempo = data[9]

            self.music_data_info = MusicDataInfo(
                num_tracks=num_tracks,
                orderlist_address=orderlist_addr,
                sequence_data_address=seq_data_addr,
                sequence_index_address=seq_idx_addr,
                default_sequence_length=default_len,
                default_tempo=default_tempo
            )

            logger.info(f"Music Data: {num_tracks} tracks, OrderList=${orderlist_addr:04X}, Seq Data=${seq_data_addr:04X}")

        except Exception as e:
            logger.error(f"Error parsing music data block: {e}")

    def _parse_orderlist(self):
        """Extract orderlist from memory"""
        if not self.music_data_info:
            return

        addr = self.music_data_info.orderlist_address
        self.orderlist = []

        # Read orderlist until we find 0x7F (end marker)
        for i in range(256):  # Max 256 entries
            if addr + i >= len(self.memory):
                break

            byte = self.memory[addr + i]
            self.orderlist.append(byte)

            if byte == 0x7F:  # End marker
                break

        logger.info(f"OrderList: {len(self.orderlist)} entries (up to first 0x7F)")

    def _parse_sequences(self):
        """Extract all sequences from memory"""
        if not self.music_data_info:
            return

        self.sequences = {}

        # Try to parse up to 128 sequences
        for seq_idx in range(self.MAX_SEQUENCES):
            seq_data = self._parse_sequence(seq_idx)
            if seq_data:
                self.sequences[seq_idx] = seq_data
            else:
                # Stop if we can't parse a sequence
                if seq_idx > 32:  # At least try first 32
                    break

        logger.info(f"Parsed {len(self.sequences)} sequences")

    def _parse_sequence(self, sequence_index: int) -> Optional[List[SequenceEntry]]:
        """Parse a single sequence from memory"""
        if not self.music_data_info:
            return None

        try:
            # Get sequence address from sequence index table
            idx_table_addr = self.music_data_info.sequence_index_address
            seq_addr_offset = idx_table_addr + (sequence_index * 2)

            if seq_addr_offset + 2 > len(self.memory):
                return None

            # Read address from index table (little-endian)
            seq_addr = self.memory[seq_addr_offset] | (self.memory[seq_addr_offset + 1] << 8)

            if seq_addr == 0 or seq_addr >= 0x10000:
                return None

            # Parse sequence entries
            entries = []
            pos = seq_addr

            for step in range(256):  # Max 256 steps per sequence
                if pos >= len(self.memory):
                    break

                note = self.memory[pos]

                # End marker
                if note == 0x7F:
                    entries.append(SequenceEntry(
                        note=0x7F,
                        command=0,
                        param1=0,
                        param2=0,
                        duration=0
                    ))
                    break

                # Parse command and parameters
                command = self.memory[pos + 1] if pos + 1 < len(self.memory) else 0
                duration = self.memory[pos + 3] if pos + 3 < len(self.memory) else 0

                # Parameter count depends on command
                if command in [0x03, 0x04, 0x05, 0x06, 0x07, 0x08]:
                    # Two-parameter commands
                    param1 = self.memory[pos + 2] if pos + 2 < len(self.memory) else 0
                    param2 = self.memory[pos + 3] if pos + 3 < len(self.memory) else 0
                    duration = self.memory[pos + 4] if pos + 4 < len(self.memory) else 0
                    pos += 5
                elif command in [0x01, 0x02, 0x0B, 0x0C, 0x0D, 0x09]:
                    # Single-parameter commands
                    param1 = self.memory[pos + 2] if pos + 2 < len(self.memory) else 0
                    param2 = 0
                    pos += 4
                else:
                    # No parameters
                    param1 = 0
                    param2 = 0
                    pos += 3

                entries.append(SequenceEntry(
                    note=note,
                    command=command,
                    param1=param1,
                    param2=param2,
                    duration=duration
                ))

                if len(entries) > 256:  # Safety limit
                    break

            return entries if entries else None

        except Exception as e:
            logger.debug(f"Error parsing sequence {sequence_index}: {e}")
            return None

    def get_sequences(self, max_count: int = 32) -> List[List[int]]:
        """Extract sequences from music data block (legacy method)"""
        return []

    def get_memory_map(self) -> str:
        """Generate a visual memory map"""
        lines = []
        lines.append("Memory Map:")
        lines.append(f"  Load Address: ${self.load_address:04X}")
        lines.append(f"  File Size: {len(self.data):,} bytes")

        if self.table_descriptors:
            lines.append("\n  Tables:")
            for desc in self.table_descriptors:
                lines.append(f"    {desc.name:20s}: ${desc.address:04X} ({desc.row_count}x{desc.column_count})")

        if self.driver_common:
            lines.append("\n  Critical Addresses:")
            lines.append(f"    Init:   ${self.driver_common.init_address:04X}")
            lines.append(f"    Play:   ${self.driver_common.play_address:04X}")
            lines.append(f"    Stop:   ${self.driver_common.stop_address:04X}")

        return '\n'.join(lines)

    def get_validation_summary(self) -> Dict[str, str]:
        """Generate validation summary"""
        magic_check = " [OK]" if self.magic_id == self.SF2_MAGIC else " [FAIL]"
        summary = {
            'Magic ID': f"0x{self.magic_id:04X}" + magic_check,
            'Load Address': f"${self.load_address:04X}",
            'File Size': f"{len(self.data):,} bytes",
            'Driver Name': self.driver_info.get('name', 'Unknown'),
            'Driver Size': self.driver_info.get('size_hex', 'Unknown'),
            'Tables Found': str(len(self.table_descriptors)),
            'Header Blocks': str(len(self.blocks)),
        }

        if self.driver_common:
            summary['Init Address'] = f"${self.driver_common.init_address:04X}"
            summary['Play Address'] = f"${self.driver_common.play_address:04X}"

        return summary
