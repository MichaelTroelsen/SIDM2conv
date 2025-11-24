"""
Data models for SID to SF2 conversion.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class PSIDHeader:
    """PSID/RSID file header structure"""
    magic: str
    version: int
    data_offset: int
    load_address: int
    init_address: int
    play_address: int
    songs: int
    start_song: int
    speed: int
    name: str
    author: str
    copyright: str
    # V2+ fields
    flags: int = 0
    start_page: int = 0
    page_length: int = 0
    second_sid_address: int = 0
    third_sid_address: int = 0


@dataclass
class SequenceEvent:
    """A single event in a sequence"""
    instrument: int
    command: int
    note: int


@dataclass
class ExtractedData:
    """Data extracted from SID file"""
    header: PSIDHeader
    c64_data: bytes
    load_address: int
    # Identified data regions
    sequences: List[List[SequenceEvent]]
    orderlists: List[List[Tuple[int, int]]]  # (transposition, sequence_index)
    instruments: List[bytes]
    wavetable: bytes
    pulsetable: bytes
    filtertable: bytes
    # New fields for improvements
    tempo: int = 6  # Default tempo (6 = ~7.5 rows per second at 50Hz)
    init_volume: int = 0x0F  # Initial master volume (0-15)
    multi_speed: int = 1  # Multi-speed: 1 = normal, 2 = 2x, 4 = 4x speed
    commands: List[bytes] = None
    pointer_tables: dict = None
    validation_errors: List[str] = None
    raw_sequences: List[bytes] = None
    siddump_data: dict = None  # Data from siddump extraction
    arp_table: List[Tuple[int, int, int, int]] = None  # Extracted arpeggio table
    hr_table: List[Tuple[int, int]] = None  # Extracted HR (Hard Restart) table
    init_table: List[int] = None  # Extracted Init table [tempo, volume, instr0, instr1, instr2]

    def __post_init__(self):
        if self.commands is None:
            self.commands = []
        if self.pointer_tables is None:
            self.pointer_tables = {}
        if self.validation_errors is None:
            self.validation_errors = []
        if self.raw_sequences is None:
            self.raw_sequences = []


@dataclass
class SF2DriverInfo:
    """Information about an SF2 driver"""
    driver_type: int = 0
    driver_size: int = 0
    driver_name: str = ""
    driver_version_major: int = 0
    driver_version_minor: int = 0

    # Music data pointers
    track_count: int = 3
    orderlist_ptrs_lo: int = 0
    orderlist_ptrs_hi: int = 0
    sequence_count: int = 0
    sequence_ptrs_lo: int = 0
    sequence_ptrs_hi: int = 0
    orderlist_size: int = 0
    orderlist_start: int = 0
    sequence_size: int = 0
    sequence_start: int = 0

    # Table addresses (for instruments, commands, etc.)
    table_addresses: dict = None

    def __post_init__(self):
        if self.table_addresses is None:
            self.table_addresses = {}


@dataclass
class LaxityCommand:
    """Mapping of Laxity command to SF2 command"""
    laxity_cmd: int
    sf2_cmd: int
    name: str
    parameters: int = 0


@dataclass
class InstrumentData:
    """Parsed instrument data"""
    index: int
    ad: int  # Attack/Decay
    sr: int  # Sustain/Release
    restart: int
    filter_setting: int
    filter_ptr: int
    pulse_ptr: int
    pulse_property: int
    wave_ptr: int
    ctrl: int = 0x41
    wave_for_sf2: int = 0x41
    name: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary format"""
        return {
            'index': self.index,
            'ad': self.ad,
            'sr': self.sr,
            'restart': self.restart,
            'filter_setting': self.filter_setting,
            'filter_ptr': self.filter_ptr,
            'pulse_ptr': self.pulse_ptr,
            'pulse_property': self.pulse_property,
            'wave_ptr': self.wave_ptr,
            'ctrl': self.ctrl,
            'wave_for_sf2': self.wave_for_sf2,
            'name': self.name,
        }
