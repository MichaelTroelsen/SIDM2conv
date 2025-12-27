"""
Base classes for multi-player support.

This module provides the abstraction layer for supporting different
SID player formats (Laxity, JCH, GoatTracker, etc.) without breaking
existing conversions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional, Any
import logging

from .models import ExtractedData, PSIDHeader
from .errors import ConfigurationError

logger = logging.getLogger(__name__)


@dataclass
class PlayerProfile:
    """
    Configuration profile for a specific SID player format.

    Each player has different memory layouts, table formats, and
    byte encodings. This profile captures those differences.
    """
    # Identity
    name: str
    version: str = ""
    aliases: List[str] = field(default_factory=list)

    # Memory layout
    typical_load_address: int = 0x1000
    player_code_size: int = 0x800

    # Search ranges for table finding (offsets from load address)
    search_start_offset: int = 0x800
    search_end_offset: int = 0xC00

    # Instrument table format
    instrument_size: int = 8  # bytes per instrument
    max_instruments: int = 32

    # Table address ranges (absolute addresses, will be adjusted by load address)
    wave_table_addr_min: int = 0x1900
    wave_table_addr_max: int = 0x1B00
    pulse_table_addr_min: int = 0x1A38
    pulse_table_addr_max: int = 0x1A50

    # Sequence format byte ranges
    instrument_byte_min: int = 0xA0
    instrument_byte_max: int = 0xAF
    command_byte_min: int = 0xC0
    command_byte_max: int = 0xCF
    duration_byte_min: int = 0x80
    duration_byte_max: int = 0x9F
    note_byte_max: int = 0x6F

    # Control bytes
    table_end: int = 0x7F
    table_loop: int = 0x7E
    sequence_end: int = 0xFF

    # Valid values for scoring/validation
    valid_waveforms: Set[int] = field(default_factory=lambda: {
        0x01, 0x10, 0x11, 0x20, 0x21, 0x40, 0x41, 0x80, 0x81,
        0x30, 0x31, 0x50, 0x51, 0x14, 0x15, 0x34, 0x35, 0x2E, 0xF0
    })

    common_ad_values: Set[int] = field(default_factory=lambda: {
        0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0F
    })

    common_sr_values: Set[int] = field(default_factory=lambda: {
        0xF8, 0xA8, 0x88, 0xDD, 0xF9, 0x9D, 0xCA, 0xCD, 0x7A, 0x9B
    })

    valid_filter_settings: Set[int] = field(default_factory=lambda: {
        0x00, 0xF1, 0xF0, 0x10, 0x20, 0x40, 0x80, 0x11, 0x21, 0x41, 0x01, 0x07
    })

    valid_restart_options: Set[int] = field(default_factory=lambda: {
        0x00, 0x10, 0x11, 0x12, 0x40, 0x80, 0x90
    })

    # Scoring thresholds
    instrument_score_threshold: int = 6
    min_valid_instruments: int = 4
    wave_table_min_entries: int = 4
    wave_table_min_score: int = 4

    # Detection patterns (code signatures)
    init_patterns: List[bytes] = field(default_factory=list)
    play_patterns: List[bytes] = field(default_factory=list)

    # Number of voices/tracks
    track_count: int = 3

    def matches_name(self, player_name: str) -> bool:
        """Check if a player name matches this profile."""
        player_lower = player_name.lower()
        if self.name.lower() in player_lower:
            return True
        for alias in self.aliases:
            if alias.lower() in player_lower:
                return True
        return False


class BasePlayerAnalyzer(ABC):
    """
    Abstract base class for player-specific analyzers.

    Each supported player format should implement this interface.
    """

    def __init__(self, c64_data: bytes, load_address: int, header: PSIDHeader):
        """
        Initialize analyzer with C64 memory data.

        Args:
            c64_data: Raw C64 memory data from SID file
            load_address: Base address where data is loaded
            header: Parsed PSID/RSID header
        """
        self.c64_data = c64_data
        self.load_address = load_address
        self.header = header
        self.profile = self.get_profile()

        # Create 64KB memory image
        self.memory = bytearray(65536)
        end_addr = min(load_address + len(c64_data), 65536)
        self.memory[load_address:end_addr] = c64_data[:end_addr - load_address]

    @classmethod
    @abstractmethod
    def get_profile(cls) -> PlayerProfile:
        """Return the player profile for this analyzer."""
        pass

    @abstractmethod
    def extract_music_data(self) -> ExtractedData:
        """
        Extract all music data from the SID file.

        Returns:
            ExtractedData object with sequences, instruments, tables, etc.
        """
        pass

    @abstractmethod
    def validate_extraction(self, data: ExtractedData) -> List[str]:
        """
        Validate extracted data and return list of warnings.

        Args:
            data: Extracted data to validate

        Returns:
            List of warning messages
        """
        pass

    def get_byte(self, addr: int) -> int:
        """Get byte from memory at absolute address."""
        if 0 <= addr < 65536:
            return self.memory[addr]
        return 0

    def get_word(self, addr: int) -> int:
        """Get 16-bit word (little-endian) from memory."""
        return self.get_byte(addr) | (self.get_byte(addr + 1) << 8)


class PlayerRegistry:
    """
    Registry of available player analyzers.

    Maps player names to their analyzer classes.
    """

    _analyzers: Dict[str, type] = {}
    _profiles: Dict[str, PlayerProfile] = {}
    _default_analyzer: Optional[type] = None

    @classmethod
    def register(cls, analyzer_class: type, is_default: bool = False):
        """
        Register a player analyzer.

        Args:
            analyzer_class: Class that extends BasePlayerAnalyzer
            is_default: If True, use this analyzer when player is unknown
        """
        profile = analyzer_class.get_profile()
        cls._analyzers[profile.name] = analyzer_class
        cls._profiles[profile.name] = profile

        # Also register aliases
        for alias in profile.aliases:
            cls._analyzers[alias] = analyzer_class
            cls._profiles[alias] = profile

        if is_default:
            cls._default_analyzer = analyzer_class

        logger.debug(f"Registered player analyzer: {profile.name}")

    @classmethod
    def get_analyzer(cls, player_name: str) -> Optional[type]:
        """
        Get analyzer class for a player name.

        Args:
            player_name: Name from player-id.exe or detection

        Returns:
            Analyzer class or None if not found
        """
        # Try exact match first
        if player_name in cls._analyzers:
            return cls._analyzers[player_name]

        # Try matching against profiles
        player_lower = player_name.lower()
        for name, analyzer_class in cls._analyzers.items():
            profile = cls._profiles.get(name)
            if profile and profile.matches_name(player_name):
                return analyzer_class

        return None

    @classmethod
    def get_default_analyzer(cls) -> Optional[type]:
        """Get the default analyzer for unknown players."""
        return cls._default_analyzer

    @classmethod
    def get_analyzer_for_sid(cls, c64_data: bytes, load_address: int,
                             header: PSIDHeader, player_hint: str = "") -> BasePlayerAnalyzer:
        """
        Create an appropriate analyzer for a SID file.

        Args:
            c64_data: Raw C64 memory data
            load_address: Base load address
            header: PSID header
            player_hint: Optional player name hint (from player-id.exe)

        Returns:
            Instantiated analyzer
        """
        analyzer_class = None

        # Try hint first
        if player_hint:
            analyzer_class = cls.get_analyzer(player_hint)

        # Fall back to default
        if not analyzer_class:
            analyzer_class = cls.get_default_analyzer()

        if not analyzer_class:
            raise ConfigurationError(
                setting='player_analyzer',
                value=player_hint or '<no player hint>',
                valid_options=cls.list_players(),
                example='Register a default analyzer with PlayerRegistry.register(LaxityAnalyzer, is_default=True)',
                docs_link='guides/TROUBLESHOOTING.md#player-analyzer-configuration'
            )

        return analyzer_class(c64_data, load_address, header)

    @classmethod
    def list_players(cls) -> List[str]:
        """List all registered player names."""
        return list(set(cls._profiles.keys()))

    @classmethod
    def get_profile(cls, player_name: str) -> Optional[PlayerProfile]:
        """Get profile for a player name."""
        return cls._profiles.get(player_name)


# Default Laxity profile that matches current behavior
def get_laxity_profile() -> PlayerProfile:
    """Create the default Laxity NewPlayer profile."""
    return PlayerProfile(
        name="Laxity",
        version="NewPlayer v21",
        aliases=["Laxity_NewPlayer_V21", "Laxity NewPlayer", "LaxityNP"],

        typical_load_address=0x1000,
        player_code_size=0x800,

        search_start_offset=0x800,
        search_end_offset=0xC00,

        instrument_size=8,
        max_instruments=32,

        wave_table_addr_min=0x1900,
        wave_table_addr_max=0x1B00,
        pulse_table_addr_min=0x1A38,
        pulse_table_addr_max=0x1A50,

        instrument_byte_min=0xA0,
        instrument_byte_max=0xAF,
        command_byte_min=0xC0,
        command_byte_max=0xCF,
        duration_byte_min=0x80,
        duration_byte_max=0x9F,
        note_byte_max=0x6F,

        table_end=0x7F,
        table_loop=0x7E,
        sequence_end=0xFF,

        init_patterns=[
            bytes([0xA9, 0x00, 0x8D]),  # LDA #$00, STA
        ],

        track_count=3,
    )
