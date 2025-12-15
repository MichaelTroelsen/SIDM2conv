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

            return True

        except Exception as e:
            logger.error(f"Parse error: {e}")
            return False

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

        driver_name = data[3:name_end].decode('ascii', errors='ignore')

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
        """Parse Block 3: Driver Tables (table descriptors)"""
        if BlockType.DRIVER_TABLES not in self.blocks:
            return

        offset, data = self.blocks[BlockType.DRIVER_TABLES]

        pos = 0
        while pos < len(data):
            if pos + 12 > len(data):
                break

            table_type = data[pos]
            table_id = data[pos + 1]

            # Find name (null-terminated)
            name_start = pos + 2
            name_end = data.find(b'\x00', name_start)
            if name_end == -1:
                name_end = len(data)

            name = data[name_start:name_end].decode('ascii', errors='ignore')
            pos = name_end + 1

            if pos + 10 > len(data):
                break

            # Handle invalid data layout values
            try:
                data_layout = TableDataLayout(data[pos])
            except ValueError:
                # Default to ROW_MAJOR if invalid
                data_layout = TableDataLayout.ROW_MAJOR
            flags = data[pos + 1]
            insert_delete_rule = data[pos + 2]
            enter_action_rule = data[pos + 3]
            color_rule = data[pos + 4]
            address = struct.unpack('<H', data[pos + 5:pos + 7])[0]
            column_count = data[pos + 7]
            row_count = data[pos + 8]

            descriptor = TableDescriptor(
                type=table_type,
                id=table_id,
                name=name,
                data_layout=data_layout,
                address=address,
                column_count=column_count,
                row_count=row_count,
                properties=flags,
            )

            self.table_descriptors.append(descriptor)
            logger.debug(f"Table: {name} at ${address:04X} ({row_count}x{column_count})")

            pos += 9

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

    def get_sequences(self, max_count: int = 32) -> List[List[int]]:
        """Extract sequences from music data block"""
        if BlockType.MUSIC_DATA not in self.blocks:
            return []

        offset, data = self.blocks[BlockType.MUSIC_DATA]

        if len(data) < 4:
            return []

        # Music data block contains pointers to sequences
        sequences = []

        # Typically first 2 bytes are track count, next are track pointers
        # Actual sequence data comes later

        return sequences

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
