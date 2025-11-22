"""
SID to SF2 Converter Package

Converts Commodore 64 SID music files to SID Factory II format.
"""

__version__ = "0.5.0"
__build_date__ = "2025-11-22"

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
from .logging_config import setup_logging, get_logger

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

    # Writer
    'SF2Writer',

    # Logging
    'setup_logging',
    'get_logger',

    # Exceptions
    'SIDError',
    'SIDParseError',
    'TableExtractionError',
    'SF2WriteError',
]
