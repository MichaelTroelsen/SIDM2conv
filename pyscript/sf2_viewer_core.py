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
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Add sidm2 to path for Laxity parser import
sys.path.insert(0, str(Path(__file__).parent.parent / 'sidm2'))
sys.path.insert(0, str(Path(__file__).parent / 'sidm2'))
try:
    from laxity_parser import LaxityParser, LaxityData
    LAXITY_PARSER_AVAILABLE = True
except ImportError:
    LAXITY_PARSER_AVAILABLE = False
    logger.warning("LaxityParser not available - Laxity files will use generic parser")


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
    note: int        # 0x00-0x6F (MIDI notes), 0x7E (gate on/sustain), 0x7F (end)
    instrument: int  # 0x80=no change, 0x90=tie note, 0xA0-0xBF=instrument index
    command: int     # 0x80=no change, 0xC0-0xFF=command (bits 0-5 = index)
    param1: int      # First parameter (varies by command)
    param2: int      # Second parameter (varies by command)
    duration: int    # How many ticks this entry lasts

    def note_name(self) -> str:
        """Convert note value to name (SID Factory II editor format)"""
        if self.note == 0x00:
            return "---"  # Gate off
        elif self.note == 0x7E:
            return "+++"  # Gate on (sustain)
        elif self.note == 0x7F:
            return "END"
        elif self.note > 0x7F:
            # Invalid note value (shouldn't happen in valid sequence data)
            return f"0x{self.note:02X}"
        else:
            # Valid note value (0x01-0x7D)
            notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            octave = self.note // 12
            note = self.note % 12
            return f"{notes[note]}-{octave}"

    def instrument_display(self) -> str:
        """Convert instrument byte to display string (SID Factory II editor format)"""
        if self.instrument == 0x80:
            return "--"  # No change
        elif self.instrument == 0x90:
            return "TIE"  # Tie note
        elif self.instrument >= 0xA0:
            instr_idx = self.instrument & 0x1F
            return f"{instr_idx:02X}"
        else:
            return "--"

    def command_display(self) -> str:
        """Convert command byte to display string (SID Factory II editor format)"""
        if self.command == 0x80:
            return "--"  # No change
        elif self.command >= 0xC0:
            cmd_idx = self.command & 0x3F
            return f"{cmd_idx:02X}"
        else:
            return "--"

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

    def param_display(self) -> str:
        """Display parameter value (param1) in hex"""
        if self.param1 == 0:
            return "--"
        return f"{self.param1:02x}"


def unpack_sequence(packed_data: bytes) -> List[Dict]:
    """Unpack a sequence from SID Factory II packed format (Laxity compatible).

    Packed format (from SID Factory II editor source and Laxity player disassembly):
    - Byte value 0xC0-0xFF: Command byte (bits 0-5 = command index)
    - Byte value 0xA0-0xBF: Instrument byte (bits 0-4 = instrument index)
    - Byte value 0x80-0x9F: Duration byte
      - Bits 0-3: duration (0-15 frames)
      - Bit 4: tie note flag (no gate retrigger)
    - Byte value 0x00-0x7E: Note value
      - 0x00: Gate off
      - 0x01-0x6F: Note values
      - 0x7E: Gate on (sustain)
    - Byte value 0x7F: End of sequence marker / Jump marker

    CRITICAL FIX: Use elif chains to avoid overlapping range checks!
    Laxity player checks: if >= 0xC0 -> cmd, elif >= 0xA0 -> instr, elif >= 0x80 -> dur, else -> note

    Returns list of event dicts with keys: 'note', 'instrument', 'command', 'duration', 'tie'
    """
    events = []
    i = 0
    current_instrument = 0x80  # 0x80 = no change
    current_command = 0x80     # 0x80 = no change
    current_duration = 0
    current_tie = False

    while i < len(packed_data):
        value = packed_data[i]
        i += 1

        # Skip Laxity SF2 padding bytes (0xE1 = invalid/filler in offset table)
        # These should not be interpreted as sequence data
        if value == 0xE1:
            continue

        # End marker or jump marker
        if value == 0x7F:
            break

        # CRITICAL: Use ELIF chains to avoid range overlap!
        # Check ranges from highest to lowest (matches Laxity player logic)

        # Command byte (0xC0-0xFF)
        if value >= 0xC0:
            current_command = value
            # Get next byte for the actual data
            if i < len(packed_data):
                value = packed_data[i]
                i += 1
            else:
                break  # No data after command, stop

        # Instrument byte (0xA0-0xBF)
        if value >= 0xA0 and value < 0xC0:  # Explicitly exclude command range
            current_instrument = value
            # Get next byte for the actual data
            if i < len(packed_data):
                value = packed_data[i]
                i += 1
            else:
                break  # No data after instrument, stop

        # Duration byte (0x80-0x9F)
        if value >= 0x80 and value < 0xA0:  # Explicitly exclude instrument range
            current_duration = value & 0x0F
            current_tie = bool(value & 0x10)
            # Get next byte for the actual note
            if i < len(packed_data):
                value = packed_data[i]
                i += 1
            else:
                break  # No data after duration, stop

        # Note byte (0x00-0x7F, but 0x7F is end marker so really 0x00-0x7E)
        note = value

        # Add event
        events.append({
            'note': note,
            'instrument': current_instrument,
            'command': current_command,
            'duration': current_duration,
            'tie': current_tie
        })

        # Reset instrument and command after using them
        # They should only appear on the step where they're set, then revert to "no change" (0x80)
        current_instrument = 0x80
        current_command = 0x80

        # Add sustain events for duration
        for _ in range(current_duration):
            sustain_note = 0x7E if note != 0x00 else 0x00
            events.append({
                'note': sustain_note,
                'instrument': 0x80,  # No change for sustain events
                'command': 0x80,     # No change for sustain events
                'duration': 0,
                'tie': False
            })

    return events


def detect_sequence_format(events: List[Dict]) -> str:
    """Detect if sequence is single-track or 3-track interleaved.

    Returns:
        'single' - Single continuous track
        'interleaved' - 3 tracks interleaved

    Detection heuristics:
    1. Very short sequences (<50 events) are likely single-track
    2. Check for repeating instrument patterns every 3 entries (suggests interleaving)
    3. Check if instruments/commands appear in groups of 3
    """
    if len(events) < 50:
        # Short sequences are typically single-track
        return 'single'

    # Count how many events have instruments/commands set
    inst_positions = [i for i, e in enumerate(events) if e['instrument'] != 0x80]
    cmd_positions = [i for i, e in enumerate(events) if e['command'] != 0x80]

    if not inst_positions and not cmd_positions:
        # No instruments or commands, can't determine - assume interleaved
        return 'interleaved'

    # Check if instruments appear in multiples of 3 positions
    # For interleaved format, instruments for each track would be at positions 0,3,6,... or 1,4,7,... or 2,5,8,...
    positions = inst_positions + cmd_positions

    # Count positions modulo 3
    mod_counts = {0: 0, 1: 0, 2: 0}
    for pos in positions:
        mod_counts[pos % 3] += 1

    # If >80% of positions are in one modulo group, it's likely single-track
    max_count = max(mod_counts.values())
    if max_count > len(positions) * 0.8:
        return 'single'

    # If positions are evenly distributed across all 3 modulo groups, it's interleaved
    min_count = min(mod_counts.values())
    if min_count > len(positions) * 0.2:
        return 'interleaved'

    # Default to interleaved for longer sequences
    return 'interleaved'


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
        self.orderlist_unpacked: List[List[Dict]] = []  # NEW: Unpacked orderlist entries for 3 tracks
        self.sequences: Dict[int, List[SequenceEntry]] = {}
        self.sequence_formats: Dict[int, str] = {}  # Maps sequence idx to 'single' or 'interleaved'
        self.memory = bytearray(65536)
        self.is_laxity_driver = False
        self.laxity_data: Optional[LaxityData] = None

        self.parse()

    def parse(self) -> bool:
        """Parse the SF2 file"""
        try:
            with open(self.file_path, 'rb') as f:
                self.data = f.read()

            if len(self.data) < 4:
                logger.error(
                    "File too small\n"
                    "  Suggestion: SF2 file is less than 4 bytes (minimum header size)\n"
                    "  Check: Verify file was fully downloaded or extracted\n"
                    "  Try: Re-download or re-generate SF2 file\n"
                    "  See: docs/guides/TROUBLESHOOTING.md#invalid-sf2-files"
                )
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
            logger.error(
                f"Parse error: {e}\n"
                f"  Suggestion: Failed to parse SF2 file structure\n"
                f"  Check: Verify file is valid SF2 format\n"
                f"  Try: Re-generate file or use SF2 Viewer debug mode\n"
                f"  See: docs/guides/TROUBLESHOOTING.md#sf2-parse-errors"
            )
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

    def _detect_laxity_driver(self) -> bool:
        """Detect if this is a Laxity driver SF2 file.

        Laxity driver files have these characteristics:
        - Load address: 0x0D7E
        - Magic ID: 0x1337
        - Relocated Laxity player code at $0E00
        - Sequence pointer table at offset $099F from load address

        Returns:
            True if this appears to be a Laxity driver file
        """
        # Check load address (0x0D7E is standard for Laxity driver)
        if self.load_address != 0x0D7E:
            return False

        # Check for relocated Laxity player code signature
        # Laxity player typically has specific patterns at $0E00
        player_code_offset = 0x0E00 - self.load_address
        if player_code_offset + 16 > len(self.data):
            return False

        # Check for Laxity-specific patterns in player code
        # Look for common 6502 patterns in the player
        player_bytes = self.data[player_code_offset:player_code_offset + 32]

        # Laxity player should have non-zero code
        if not any(player_bytes):
            return False

        logger.info(f"Detected Laxity driver SF2 (load address 0x{self.load_address:04X})")
        return True

    def _infer_table_name(self, table_type: int, table_id: int, raw_name: str,
                         row_count: int = 0, column_count: int = 0, address: int = 0) -> str:
        """Infer table name from type, ID, and dimensions if raw name is unavailable.

        Args:
            table_type: Table type byte
            table_id: Table ID byte
            raw_name: Raw name from descriptor
            row_count: Number of rows (optional, for dimension-based inference)
            column_count: Number of columns (optional, for dimension-based inference)
            address: Table address in memory (optional, for disambiguation)

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
                    if row_count == 256 and column_count == 3:
                        # Distinguish between Wave, Pulse, Filter using address
                        # If address provided, use it to disambiguate
                        if address > 0:
                            # Use address to determine type
                            if address >= 0x1EDB:  # Filter threshold (higher address)
                                return "Filter"
                            elif address >= 0x1BDB:  # Pulse threshold
                                return "Pulse"
                        # Default to Wave if no address or can't determine
                        return "Wave"
                    elif (row_count == 128 or row_count == 256) and column_count == 2:
                        return "Wave"
                    elif (row_count == 64 or row_count == 256) and column_count == 4:
                        return "Pulse"
                    elif row_count == 32 and column_count == 2:
                        # Use address to distinguish between Arpeggio and Init
                        # Init is typically at lower addresses
                        if address > 0 and address < 0x1900:
                            return "Init"
                        else:
                            return "Arpeggio"
                    elif row_count == 256 and column_count == 1:
                        # Distinguish between Arpeggio and Tempo using address
                        if address > 0 and address < 0x22DB:
                            return "Arpeggio"
                        else:
                            return "Tempo"
                    elif row_count == 128 and column_count == 1:
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
            # Pass dimensions and address for type 0x00 table identification
            final_name = self._infer_table_name(table_type, table_id, name_raw,
                                               row_count, column_count, address)

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
            # Music Data block structure (18 bytes for Laxity):
            # [0-1]    : Unknown (0xDB03)
            # [2-3]    : Unknown (0xDE23)
            # [4-5]    : Sequence Data Address (0x8023) - little-endian
            # [6-7]    : Sequence Index Address (0x23E1) - little-endian
            # [8-9]    : Default Sequence Length (0x2461 = 0x61 = 97) - little-endian
            # [10-11]  : Unknown (0x0100)
            # [12-13]  : Unknown (0x24E1) - might be related address
            # [14-15]  : Unknown (0x0100)
            # [16-17]  : Unknown (0x27E1)

            # Extract sequence addresses from block
            seq_data_addr = data[4] | (data[5] << 8) if len(data) >= 6 else 0x8023
            seq_idx_addr = data[6] | (data[7] << 8) if len(data) >= 8 else 0x23E1
            default_len = data[8] if len(data) >= 9 else 0x61
            default_tempo = data[9] if len(data) >= 10 else 0x18

            # For Laxity driver files, the OrderList has 3 columns stored separately:
            # Column 1 (sequences/offsets): file offset 0x1766 → C64 address
            # Column 2 (values): file offset 0x1866 (0x100 bytes later) → C64 address
            # Column 3 (values): file offset 0x1966 (0x100 bytes later) → C64 address
            # Each column is 256 bytes with up to 256 entries (one byte per entry per column)

            # SF2 file structure: bytes 0-3 are header, bytes 4+ start at load_address
            # Therefore: C64_addr = load_address + (file_offset - 4)

            col1_file_offset = 0x1766
            col1_addr = self.load_address + (col1_file_offset - 4)
            col2_addr = self.load_address + (0x1866 - 4)
            col3_addr = self.load_address + (0x1966 - 4)

            # Store col1 address as the primary orderlist_address for accessing the data
            # Caller should read all 3 columns to get complete OrderList entries
            orderlist_addr = col1_addr

            # Extract number of tracks from first byte
            num_tracks = data[0] if len(data) >= 1 else 0x03

            self.music_data_info = MusicDataInfo(
                num_tracks=num_tracks,
                orderlist_address=orderlist_addr,
                sequence_data_address=seq_data_addr,
                sequence_index_address=seq_idx_addr,
                default_sequence_length=default_len,
                default_tempo=default_tempo
            )

            # Store additional OrderList column addresses for GUI to use
            self.orderlist_col2_addr = col2_addr
            self.orderlist_col3_addr = col3_addr

            logger.info(f"Music Data: OrderList at 0x{col1_addr:04X}, SeqIdx=0x{seq_idx_addr:04X}, SeqData=0x{seq_data_addr:04X}, SeqLen={default_len}")

        except Exception as e:
            logger.error(
                f"Error parsing music data block: {e}\n"
                f"  Suggestion: Failed to parse SF2 music data structure\n"
                f"  Check: Verify music data block format is valid\n"
                f"  Try: Re-generate SF2 file or check conversion log\n"
                f"  See: docs/guides/TROUBLESHOOTING.md#music-data-parse-errors"
            )

    def _unpack_orderlist_track(self, track_addr: int, max_entries: int = 256) -> List[Dict]:
        """Unpack a single track's orderlist from packed format.

        Implements the SF2 editor unpacking algorithm:
        - Values >= 0x80: Transpose values (update state, don't create entry)
        - Values < 0x80: Sequence indices (create entry with current transpose)
        - 0xFE: End marker
        - 0xFF: Loop marker

        Args:
            track_addr: Memory address of packed orderlist data for this track
            max_entries: Maximum number of entries to read

        Returns:
            List of dicts with 'transpose' and 'sequence' keys
        """
        entries = []
        current_transpose = 0xA0  # Default: no transpose

        for i in range(max_entries):
            if track_addr + i >= len(self.memory):
                break

            value = self.memory[track_addr + i]

            # End markers
            if value == 0xFE or value == 0xFF:
                break

            # Transpose value (>= 0x80): Update state, don't create entry
            if value >= 0x80:
                current_transpose = value
            else:
                # Sequence index (< 0x80): Create entry with current transpose
                entries.append({
                    'transpose': current_transpose,
                    'sequence': value
                })

        return entries

    def _parse_orderlist(self):
        """Extract and unpack orderlist from memory.

        Reads packed orderlist data for all 3 tracks and unpacks using
        SF2 editor algorithm (transpose state machine).

        Creates:
        - self.orderlist: Raw packed bytes (legacy compatibility)
        - self.orderlist_unpacked: List of 3 track lists with unpacked entries
        """
        if not self.music_data_info:
            return

        # Legacy: Read raw bytes from first column (for backward compatibility)
        addr = self.music_data_info.orderlist_address
        self.orderlist = []

        for i in range(256):  # Max 256 entries
            if addr + i >= len(self.memory):
                break
            byte = self.memory[addr + i]
            self.orderlist.append(byte)
            if byte == 0x7F:  # End marker
                break

        # NEW: Unpack all 3 tracks using SF2 editor algorithm
        self.orderlist_unpacked = []

        # Get addresses for all 3 OrderList columns
        track_addrs = [
            self.music_data_info.orderlist_address,  # Track 1
            getattr(self, 'orderlist_col2_addr', self.music_data_info.orderlist_address + 0x100),  # Track 2
            getattr(self, 'orderlist_col3_addr', self.music_data_info.orderlist_address + 0x200),  # Track 3
        ]

        for track_num, track_addr in enumerate(track_addrs, 1):
            unpacked = self._unpack_orderlist_track(track_addr)
            self.orderlist_unpacked.append(unpacked)
            logger.info(f"OrderList Track {track_num}: {len(unpacked)} unpacked entries (from 0x{track_addr:04X})")

        logger.info(f"OrderList: {len(self.orderlist)} raw bytes, {len(self.orderlist_unpacked)} tracks unpacked")

    def _detect_laxity_offset_table_structure(self) -> Optional[int]:
        """Detect Laxity offset table structure in SF2 file.

        Laxity SF2 files contain a complex header structure with padding and index tables.
        The REAL sequence data starts at the first location where we find:
        - Valid packed sequence data (0xA0-0xFF or 0x01-0x7E bytes)
        - Followed by a 0x7F terminator within reasonable distance (50-2000 bytes)
        - The data before 0x7F contains valid packed format patterns

        Returns: File offset where real sequence data begins
        """
        # Look for real sequences by finding valid 0x7F terminators with packed data before them
        search_start = 0x1600
        search_end = min(len(self.data), 0x2000)

        # Find all potential sequence starts (positions with valid packed markers)
        candidates = []

        for offset in range(search_start, search_end - 50):
            byte = self.data[offset]

            # Look for bytes that could start a sequence:
            # 0xA0-0xBF (instrument), 0xC0-0xFF (command), or 0x01-0x7E (note)
            if not (0x01 <= byte <= 0x7E or 0xA0 <= byte <= 0xFF):
                continue

            # For each candidate, look for a 0x7F terminator within 50-2000 bytes
            for end_search in range(offset + 50, min(offset + 2000, search_end)):
                if self.data[end_search] == 0x7F:
                    # Verify this looks like real sequence data
                    # Should have multiple valid packed bytes between offset and 0x7F
                    valid_bytes = 0
                    for check in range(offset, end_search):
                        b = self.data[check]
                        if (0x01 <= b <= 0x7F or 0xA0 <= b <= 0xFF):
                            valid_bytes += 1

                    # Need substantial valid data (at least 20% of range should be valid)
                    if valid_bytes > (end_search - offset) * 0.2:
                        candidates.append((offset, end_search - offset))
                        break

        if candidates:
            # Return the earliest candidate (first real sequence)
            candidates.sort()
            first_offset = candidates[0][0]
            logger.info(f"Detected Laxity offset table structure")
            logger.info(f"First sequence at offset 0x{first_offset:04X}")
            logger.info(f"Found {len(candidates)} sequence candidates")
            return first_offset

        logger.debug("Laxity offset table detection failed: no valid sequence data found")
        return None

    def _parse_packed_sequences_laxity_sf2(self) -> bool:
        """Parse sequences from Laxity SF2 files using comprehensive scan.

        Scans entire file for all sequences marked with 0x7F terminators.
        This ensures all sequences are found, regardless of layout.
        """
        self.sequences = {}

        logger.info(f"Scanning file for all packed sequences (Laxity SF2)")

        # Scan entire file for sequences
        # Start after header blocks (around 0x1000)
        offset = 0x1000
        seq_candidates = []

        while offset < len(self.data) - 10:
            byte = self.data[offset]

            # Check if this could be a sequence start
            # Valid packed sequence start: 0xA0-0xBF (instrument), 0x01-0x7E (note), or 0xC0-0xFF (command)
            if not (0x01 <= byte <= 0x7E or 0xA0 <= byte <= 0xFF):
                offset += 1
                continue

            # Try to extract sequence from here
            seq_start = offset
            seq_bytes = bytearray()
            temp_offset = offset

            while temp_offset < len(self.data) and len(seq_bytes) < 2000:
                byte = self.data[temp_offset]
                seq_bytes.append(byte)
                temp_offset += 1

                if byte == 0x7F:  # End of sequence marker
                    break

            # Validate this looks like a real sequence
            if len(seq_bytes) >= 10 and seq_bytes[-1] == 0x7F:
                # Check if packed data looks valid
                valid_bytes = 0
                for b in seq_bytes[:-1]:  # Exclude 0x7F terminator
                    if 0x01 <= b <= 0x7F or 0xA0 <= b <= 0xFF:
                        valid_bytes += 1

                # At least 70% of bytes should be valid packed format
                if valid_bytes > len(seq_bytes) * 0.7:
                    seq_candidates.append({
                        'offset': seq_start,
                        'bytes': bytes(seq_bytes),
                        'length': len(seq_bytes)
                    })
                    offset = temp_offset  # Skip past this sequence
                    continue

            offset += 1

        # Now unpack all valid sequences
        logger.info(f"Found {len(seq_candidates)} sequence candidates")

        for idx, cand in enumerate(seq_candidates):
            if idx >= self.MAX_SEQUENCES:
                break

            # Unpack sequence
            events = unpack_sequence(cand['bytes'])
            entries = []

            for event in events:
                entry = SequenceEntry(
                    note=event['note'],
                    instrument=event['instrument'],
                    command=event['command'],
                    param1=0,
                    param2=0,
                    duration=event['duration']
                )
                entries.append(entry)

            if entries:
                self.sequences[idx] = entries

                # Detect sequence format (single-track or 3-track interleaved)
                seq_format = detect_sequence_format(events)
                self.sequence_formats[idx] = seq_format

                logger.info(f"Sequence {idx}: {cand['length']} packed bytes -> {len(entries)} entries (offset 0x{cand['offset']:04X}, format={seq_format})")

        logger.info(f"Parsed {len(self.sequences)} sequences from Laxity SF2 file")
        return len(self.sequences) > 0

    def _find_packed_sequences(self) -> Optional[int]:
        """Find packed sequence data in file (for Laxity driver files).

        Laxity files store sequences in packed format at a fixed location.
        This method searches for the start of sequence data by looking for
        patterns that indicate packed sequence format.

        Returns: File offset of first sequence if found, None otherwise
        """
        # Look for patterns that indicate packed sequence data
        # Start searching after the Music Data block (typically after 0x1000)
        search_start = 0x1600  # Typical location for Laxity sequence data
        search_end = min(len(self.data), 0x2000)

        for offset in range(search_start, search_end - 20):
            # Skip all-zero regions (padding/empty blocks)
            # Check for at least one non-zero byte in first 10 bytes
            has_non_zero = any(b != 0x00 for b in self.data[offset:offset+10])
            if not has_non_zero:
                continue

            # Skip pointer blocks (sequences of 0xE1 bytes, which are common in Laxity files)
            # These are typically metadata/pointers before actual sequence data
            test_offset = offset
            while test_offset < len(self.data) and self.data[test_offset] == 0xE1:
                test_offset += 1

            # If we skipped some bytes, use the position after them
            if test_offset > offset:
                offset = test_offset
                if offset >= search_end - 20:
                    continue

            # Valid packed sequence must start with meaningful data:
            # - 0xA0-0xBF (instrument command), or
            # - 0xC0-0xFF (effect command), or
            # - 0x01-0x7E (note value, not gate off)
            byte = self.data[offset]
            if not (0x01 <= byte <= 0x7E or 0xA0 <= byte <= 0xBF or 0xC0 <= byte <= 0xFF):
                continue

            # Look for end marker (0x7F) within reasonable distance
            for end_offset in range(offset + 4, min(offset + 256, search_end)):
                if self.data[end_offset] == 0x7F:
                    # Check if this looks like a valid sequence
                    seq_length = end_offset - offset + 1
                    if seq_length >= 5:  # Minimum valid sequence
                        # Verify it has packed sequence patterns
                        has_packed_patterns = False
                        for check_offset in range(offset, end_offset):
                            b = self.data[check_offset]
                            if 0xA0 <= b <= 0xBF or 0xC0 <= b <= 0xFF:
                                has_packed_patterns = True
                                break

                        if has_packed_patterns or seq_length > 30:  # Good candidate
                            logger.info(f"Found packed sequences at file offset 0x{offset:04X} (length {seq_length})")
                            return offset
                    break

        return None

    def _parse_packed_sequences(self):
        """Parse sequences from packed format data (Laxity driver files)."""
        seq_offset = self._find_packed_sequences()
        if seq_offset is None:
            return

        # Convert file offset to memory address
        seq_data_addr = self.load_address + (seq_offset - 4)

        self.sequences = {}
        seq_idx = 0
        offset = seq_offset

        # Parse sequences until we reach end of file or run out of sequences
        while offset < len(self.data) and seq_idx < self.MAX_SEQUENCES:
            # Extract one sequence (bytes until 0x7F end marker)
            seq_start = offset
            seq_bytes = bytearray()

            while offset < len(self.data):
                byte = self.data[offset]
                seq_bytes.append(byte)
                offset += 1

                if byte == 0x7F:  # End marker
                    break

            if not seq_bytes or seq_bytes[-1] != 0x7F:
                # Invalid sequence, stop parsing
                break

            # Skip padding (consecutive zeros)
            while offset < len(self.data) and self.data[offset] == 0x00:
                offset += 1

            # Unpack and convert to SequenceEntry format
            events = unpack_sequence(bytes(seq_bytes))

            # Convert unpacked events to SequenceEntry objects
            entries = []
            for event in events:
                entry = SequenceEntry(
                    note=event['note'],
                    instrument=event['instrument'],
                    command=event['command'],
                    param1=0,
                    param2=0,
                    duration=event['duration']
                )
                entries.append(entry)

            if entries:
                self.sequences[seq_idx] = entries

            seq_idx += 1

            # Stop if we've found a reasonable number of sequences or hit end
            if offset >= len(self.data) or (seq_idx > 1 and offset > seq_offset + 1000):
                break

        logger.info(f"Parsed {len(self.sequences)} packed sequences from offset 0x{seq_offset:04X}")

    def _parse_laxity_sequences(self):
        """Extract sequences using Laxity parser for Laxity driver SF2 files.

        This method uses the proven LaxityParser which achieves 99.93% accuracy
        by extracting sequences via pointer table at offset $099F.
        """
        if not LAXITY_PARSER_AVAILABLE:
            logger.warning("LaxityParser not available, skipping Laxity-specific parsing")
            return False

        try:
            # Use Laxity parser with C64 memory data
            # The load_address is already in self.load_address (0x0D7E)
            laxity_parser = LaxityParser(self.data[2:], self.load_address)
            self.laxity_data = laxity_parser.parse()

            if not self.laxity_data or not self.laxity_data.sequences:
                logger.warning("Laxity parser found no sequences")
                return False

            logger.info(f"Laxity parser extracted {len(self.laxity_data.sequences)} sequences")

            # Convert Laxity sequences to SequenceEntry format
            for seq_idx, seq_bytes in enumerate(self.laxity_data.sequences):
                entries = self._convert_laxity_sequence(seq_bytes)
                if entries:
                    self.sequences[seq_idx] = entries
                    logger.debug(f"Sequence {seq_idx}: {len(entries)} entries")

            logger.info(f"Converted {len(self.sequences)} Laxity sequences to SequenceEntry format")
            return True

        except Exception as e:
            logger.error(
                f"Error parsing Laxity sequences: {e}\n"
                f"  Suggestion: Failed to parse Laxity format sequences\n"
                f"  Check: Verify SF2 file was generated from Laxity SID\n"
                f"  Try: Use Laxity driver for conversion or re-generate file\n"
                f"  See: docs/guides/TROUBLESHOOTING.md#laxity-sequence-parse-errors"
            )
            import traceback
            traceback.print_exc()
            return False

    def _convert_laxity_sequence(self, seq_bytes: bytes) -> List[SequenceEntry]:
        """Convert a Laxity format sequence to SequenceEntry list.

        Laxity format (from laxity_parser.py documentation):
        - $00: Rest
        - $01-$5F: Note value
        - $7E: Gate continue (sustain)
        - $7F: End of sequence
        - $80-$8F: Rest with duration
        - $90-$9F: Duration with gate
        - $A0-$BF: Instrument
        - $C0-$FF: Command

        Args:
            seq_bytes: Raw sequence bytes in Laxity format

        Returns:
            List of SequenceEntry objects
        """
        entries = []
        i = 0
        current_instrument = 0x80  # No change
        current_command = 0x80     # No change

        while i < len(seq_bytes):
            byte = seq_bytes[i]
            i += 1

            # End marker
            if byte == 0x7F:
                break

            # Command byte (0xC0-0xFF)
            if byte >= 0xC0:
                current_command = byte
                continue

            # Instrument byte (0xA0-0xBF)
            if byte >= 0xA0:
                current_instrument = byte
                continue

            # Duration bytes (0x80-0x9F) or rest with duration (0x80-0x8F)
            # These are typically followed by a note
            if byte >= 0x80:
                # This is part of the note encoding, will be handled with the note
                continue

            # Note byte (0x00-0x7E)
            # Note: 0x7E is gate continue (sustain), not a rest
            note = byte

            # Create sequence entry
            entry = SequenceEntry(
                note=note,
                instrument=current_instrument,
                command=current_command,
                param1=0,
                param2=0,
                duration=0
            )
            entries.append(entry)

        logger.debug(f"Converted Laxity sequence: {len(entries)} entries")
        return entries

    def _parse_sequences(self):
        """Extract all sequences from memory"""
        if not self.music_data_info:
            return

        self.sequences = {}

        # First priority: Try Laxity driver SF2 parser (for Laxity NewPlayer in SF2 container)
        if self._detect_laxity_driver():
            self.is_laxity_driver = True

            # Try new Laxity SF2 parser (handles offset table structure)
            if self._parse_packed_sequences_laxity_sf2():
                logger.info(f"Successfully parsed {len(self.sequences)} sequences using Laxity SF2 parser")
                return

            # Fallback: Try original Laxity parser
            if self._parse_laxity_sequences():
                logger.info(f"Successfully parsed {len(self.sequences)} sequences using Laxity parser")
                return
            else:
                logger.warning("Laxity driver detected but parsing failed, trying fallback methods")
                self.sequences = {}  # Clear any partial results

        # Second priority: Try generic packed sequences (for other SF2 formats with packed sequences)
        if self._parse_packed_sequences_laxity_sf2():
            if self.sequences:
                logger.info(f"Successfully parsed {len(self.sequences)} sequences using Laxity SF2 offset table parser")
                return
            self.sequences = {}  # Clear if no sequences found

        if self._find_packed_sequences() is not None:
            self._parse_packed_sequences()
            if self.sequences:
                logger.info(f"Successfully parsed {len(self.sequences)} packed sequences")
                return

        # Fallback: Try traditional indexed sequence parsing
        logger.info("Trying traditional indexed sequence parsing")
        for seq_idx in range(self.MAX_SEQUENCES):
            seq_data = self._parse_sequence(seq_idx)
            if seq_data:
                self.sequences[seq_idx] = seq_data
            else:
                # Stop if we can't parse a sequence
                if seq_idx > 32:  # At least try first 32
                    break

        logger.info(f"Parsed {len(self.sequences)} sequences total")

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
                        instrument=0x80,
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
                    instrument=0x80,  # Traditional format doesn't have explicit instrument bytes
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
            lines.append("\n  Driver Addresses:")
            lines.append(f"    Init:   ${self.driver_common.init_address:04X}")
            lines.append(f"    Play:   ${self.driver_common.play_address:04X}")
            lines.append(f"    Stop:   ${self.driver_common.stop_address:04X}")

        if self.music_data_info:
            lines.append("\n  Music Data Addresses:")
            lines.append(f"    OrderList:        ${self.music_data_info.orderlist_address:04X}")
            lines.append(f"    Sequence Data:    ${self.music_data_info.sequence_data_address:04X}")
            lines.append(f"    Sequence Index:   ${self.music_data_info.sequence_index_address:04X}")

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
