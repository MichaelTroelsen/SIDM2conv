"""
SID to SF2 Converter Package

Converts Commodore 64 SID music files to SID Factory II format.
"""

__version__ = "0.6.0"
__build_date__ = "2025-11-25"

from .constants import *
from .exceptions import *
from .models import PSIDHeader, SequenceEvent, ExtractedData, SF2DriverInfo
from .sid_parser import SIDParser
from .table_extraction import (
    find_instrument_table,
    find_and_extract_wave_table,
    find_and_extract_pulse_table,
    find_and_extract_filter_table,
    extract_all_laxity_tables,
)
from .instrument_extraction import extract_laxity_instruments, extract_laxity_wave_table
from .sequence_extraction import analyze_sequence_commands, extract_command_parameters, get_command_names
from .laxity_analyzer import LaxityPlayerAnalyzer
from .sf2_writer import SF2Writer
from .siddump import extract_from_siddump
from .note_utils import (
    laxity_note_to_name,
    note_name_to_laxity,
    extract_notes_from_siddump,
    extract_first_notes_from_siddump,
    extract_notes_from_sequences,
    compare_notes,
    generate_note_comparison_report,
)
from .logging_config import setup_logging, get_logger
from .confidence import (
    ExtractionConfidence,
    ComponentScore,
    ConfidenceCalculator,
    calculate_extraction_confidence,
)
from .player_base import (
    PlayerProfile,
    BasePlayerAnalyzer,
    PlayerRegistry,
    get_laxity_profile,
)
from .players import LaxityPlayerAnalyzerV2, LAXITY_PROFILE

__all__ = [
    # Version info
    '__version__',
    '__build_date__',

    # Models
    'PSIDHeader',
    'SequenceEvent',
    'ExtractedData',
    'SF2DriverInfo',

    # Parsers
    'SIDParser',
    'LaxityPlayerAnalyzer',

    # Extraction functions
    'find_instrument_table',
    'find_and_extract_wave_table',
    'find_and_extract_pulse_table',
    'find_and_extract_filter_table',
    'extract_all_laxity_tables',
    'extract_laxity_instruments',
    'extract_laxity_wave_table',
    'analyze_sequence_commands',
    'extract_command_parameters',
    'get_command_names',
    'extract_from_siddump',

    # Note utilities
    'laxity_note_to_name',
    'note_name_to_laxity',
    'extract_notes_from_siddump',
    'extract_first_notes_from_siddump',
    'extract_notes_from_sequences',
    'compare_notes',
    'generate_note_comparison_report',

    # Writer
    'SF2Writer',

    # Logging
    'setup_logging',
    'get_logger',

    # Confidence scoring
    'ExtractionConfidence',
    'ComponentScore',
    'ConfidenceCalculator',
    'calculate_extraction_confidence',

    # Exceptions
    'SIDError',
    'SIDParseError',
    'TableExtractionError',
    'SF2WriteError',

    # Player system
    'PlayerProfile',
    'BasePlayerAnalyzer',
    'PlayerRegistry',
    'get_laxity_profile',
    'LaxityPlayerAnalyzerV2',
    'LAXITY_PROFILE',
]
