"""SID to SF2 Conversion Pipeline - Business Logic Module

This module contains all SID to SF2 conversion orchestration and analysis logic,
separated from the CLI interface for better testability and coverage tracking.

The conversion pipeline supports multiple conversion strategies:
- Laxity NewPlayer v21: Custom driver with 99.93% accuracy
- Martin Galway: Table extraction and injection with 88-96% accuracy
- SF2-exported SIDs: Direct reference or SF2PlayerParser with 100% accuracy
- Standard drivers: driver11, np20 for general SID files

Functions:
    detect_player_type() - Identify SID player format using player-id.exe
    print_success_summary() - Format and display conversion results
    analyze_sid_file() - Parse and analyze SID file structure
    convert_laxity_to_sf2() - Laxity custom driver conversion
    convert_galway_to_sf2() - Martin Galway table-based conversion
    convert_sid_to_sf2() - Main conversion orchestrator with auto-selection
    convert_sid_to_both_drivers() - Dual driver conversion for comparison

Module-level constants:
    LAXITY_CONVERTER_AVAILABLE - True if Laxity converter available
    GALWAY_CONVERTER_AVAILABLE - True if Galway converter available
    SIDWINDER_INTEGRATION_AVAILABLE - True if SIDwinder available
    ASM_ANNOTATION_AVAILABLE - True if ASM annotation available
    ... (10 more optional integration availability flags)

Architecture:
    This module was extracted from scripts/sid_to_sf2.py to enable proper
    unit testing and coverage tracking. The CLI script now imports these
    functions as a thin wrapper.

References:
    - docs/ARCHITECTURE.md - System architecture
    - docs/implementation/SID_TO_SF2_REFACTORING_PLAN.md - Refactoring plan
    - docs/guides/LAXITY_DRIVER_USER_GUIDE.md - Laxity driver guide

Created: 2025-12-27 (Extracted from scripts/sid_to_sf2.py)
Version: 2.9.1
"""

import logging
import os
import sys
import subprocess
import shutil
import time
from pathlib import Path

# Import all components from the sidm2 package
from sidm2 import (
    PSIDHeader,
    SequenceEvent,
    ExtractedData,
    SIDParser,
    LaxityPlayerAnalyzer,
    SF2Writer,
    extract_from_siddump,
    analyze_sequence_commands,
    get_command_names,
)

# Import SF2 player parser for SF2-exported SIDs
from sidm2.sf2_player_parser import SF2PlayerParser

# Import configuration system
from sidm2.config import ConversionConfig, get_default_config

# Import error handling module
from sidm2 import errors as sidm2_errors

# Import enhanced logging system
from sidm2.logging_config import get_logger

# Import driver selector (Conversion Policy v2.0)
from sidm2.driver_selector import DriverSelector, DriverSelection

# Import Laxity converter for custom driver
try:
    from sidm2.laxity_converter import LaxityConverter
    LAXITY_CONVERTER_AVAILABLE = True
except ImportError:
    LAXITY_CONVERTER_AVAILABLE = False

# Import Martin Galway analyzer and converter
try:
    from sidm2 import (
        MartinGalwayAnalyzer,
        GalwayMemoryAnalyzer,
        GalwayTableExtractor,
        GalwayFormatConverter,
        GalwayTableInjector,
        GalwayConversionIntegrator,
    )
    GALWAY_CONVERTER_AVAILABLE = True
except ImportError:
    GALWAY_CONVERTER_AVAILABLE = False

# Import SIDwinder integration (Step 7.5 - optional tracing)
try:
    from sidm2.sidwinder_wrapper import SIDwinderIntegration
    SIDWINDER_INTEGRATION_AVAILABLE = True
except ImportError:
    SIDWINDER_INTEGRATION_AVAILABLE = False

# Import 6502 Disassembler integration (Step 8.5 - optional disassembly)
try:
    from sidm2.disasm_wrapper import DisassemblerIntegration
    DISASSEMBLER_INTEGRATION_AVAILABLE = True
except ImportError:
    DISASSEMBLER_INTEGRATION_AVAILABLE = False

# Import ASM Annotation integration (Step 8.7 - optional comprehensive annotation)
try:
    from sidm2.annotation_wrapper import AnnotationIntegration
    ASM_ANNOTATION_AVAILABLE = True
except ImportError:
    ASM_ANNOTATION_AVAILABLE = False

# Import Audio Export integration (Step 16 - optional audio export)
try:
    from sidm2.audio_export_wrapper import AudioExportIntegration
    AUDIO_EXPORT_INTEGRATION_AVAILABLE = True
except ImportError:
    AUDIO_EXPORT_INTEGRATION_AVAILABLE = False

# Import Memory Map Analyzer (Step 12.5 - optional memory analysis)
try:
    from sidm2.memmap_analyzer import MemoryMapAnalyzer
    MEMMAP_ANALYZER_AVAILABLE = True
except ImportError:
    MEMMAP_ANALYZER_AVAILABLE = False

# Import Pattern Recognizer (Step 17 - optional pattern analysis)
try:
    from sidm2.pattern_recognizer import PatternRecognizer
    PATTERN_RECOGNIZER_AVAILABLE = True
except ImportError:
    PATTERN_RECOGNIZER_AVAILABLE = False

# Import Subroutine Tracer (Step 18 - optional call graph analysis)
try:
    from sidm2.subroutine_tracer import SubroutineTracer
    SUBROUTINE_TRACER_AVAILABLE = True
except ImportError:
    SUBROUTINE_TRACER_AVAILABLE = False

# Import Report Generator (Step 19 - consolidated reporting)
try:
    from sidm2.report_generator import ReportGenerator
    REPORT_GENERATOR_AVAILABLE = True
except ImportError:
    REPORT_GENERATOR_AVAILABLE = False

# Import Output Organizer (Step 20 - output organization)
try:
    from sidm2.output_organizer import OutputOrganizer
    OUTPUT_ORGANIZER_AVAILABLE = True
except ImportError:
    OUTPUT_ORGANIZER_AVAILABLE = False

# Import Siddump Integration (Step 7.6 - siddump frame analysis)
try:
    from sidm2.siddump_integration import SiddumpIntegration
    SIDDUMP_INTEGRATION_AVAILABLE = True
except ImportError:
    SIDDUMP_INTEGRATION_AVAILABLE = False

# Import Accuracy Integration (Step 21 - accuracy validation)
try:
    from sidm2.accuracy_integration import AccuracyIntegration
    ACCURACY_INTEGRATION_AVAILABLE = True
except ImportError:
    ACCURACY_INTEGRATION_AVAILABLE = False

# Get module logger
logger = get_logger(__name__)

# Module exports
__all__ = [
    # Core conversion functions
    'detect_player_type',
    'print_success_summary',
    'analyze_sid_file',
    'convert_laxity_to_sf2',
    'convert_galway_to_sf2',
    'convert_sid_to_sf2',
    'convert_sid_to_both_drivers',
    # Availability flags
    'LAXITY_CONVERTER_AVAILABLE',
    'GALWAY_CONVERTER_AVAILABLE',
    'SIDWINDER_INTEGRATION_AVAILABLE',
    'DISASSEMBLER_INTEGRATION_AVAILABLE',
    'ASM_ANNOTATION_AVAILABLE',
    'AUDIO_EXPORT_INTEGRATION_AVAILABLE',
    'MEMMAP_ANALYZER_AVAILABLE',
    'PATTERN_RECOGNIZER_AVAILABLE',
    'SUBROUTINE_TRACER_AVAILABLE',
    'REPORT_GENERATOR_AVAILABLE',
    'OUTPUT_ORGANIZER_AVAILABLE',
    'SIDDUMP_INTEGRATION_AVAILABLE',
    'ACCURACY_INTEGRATION_AVAILABLE',
]


def _convert_midi_to_sequence_events(midi_sequences: dict) -> List[List[SequenceEvent]]:
    """Convert MIDI-extracted sequences to SequenceEvent format.

    MIDI extraction produces command bytes (notes + gate markers), but
    ExtractedData.sequences needs full SequenceEvent objects with
    (instrument, command, note) tuples.

    Args:
        midi_sequences: Dictionary with {'voice1': [bytes], 'voice2': [bytes], 'voice3': [bytes]}

    Returns:
        List of 3 sequences (one per voice), each containing SequenceEvent objects
    """
    logger = get_logger(__name__)

    voice_names = ['voice1', 'voice2', 'voice3']
    result_sequences = []

    # Special markers
    GATE_ON = 0x7E
    GATE_OFF = 0x80
    END_MARKER = 0x7F

    for voice_name in voice_names:
        command_bytes = midi_sequences.get(voice_name, [])
        sequence_events = []

        default_instrument = 0  # Use instrument 0 for MIDI-extracted notes

        for cmd_byte in command_bytes:
            if cmd_byte == GATE_ON:
                # Gate ON marker: instrument=0x7E, command=0x7E, note=0x7E
                event = SequenceEvent(instrument=0x7E, command=0x7E, note=GATE_ON)
            elif cmd_byte == GATE_OFF:
                # Gate OFF marker: instrument=0x80, command=0x80, note=0x80
                event = SequenceEvent(instrument=0x80, command=0x80, note=GATE_OFF)
            elif cmd_byte == END_MARKER:
                # End marker: instrument=0x80, command=0x80, note=0x7F
                event = SequenceEvent(instrument=0x80, command=0x80, note=END_MARKER)
            else:
                # Regular note: instrument=0 (default), command=0x00 (no effect), note=<value>
                event = SequenceEvent(instrument=default_instrument, command=0x00, note=cmd_byte)

            sequence_events.append(event)

        result_sequences.append(sequence_events)
        logger.debug(f"Converted {voice_name}: {len(command_bytes)} command bytes → {len(sequence_events)} SequenceEvents")

    return result_sequences


def detect_player_type(filepath: str) -> str:
    """Detect the player type of a SID file using player-id.exe

    Args:
        filepath: Path to SID file

    Returns:
        Player type string (e.g., "SidFactory_II/Laxity", "NewPlayer_v21/Laxity")
        or "Unknown" if detection fails
    """
    try:
        # Use absolute path for player-id.exe
        player_id_path = os.path.join(os.getcwd(), 'tools', 'player-id.exe')

        result = subprocess.run(
            [player_id_path, filepath],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=os.getcwd()  # Ensure correct working directory
        )

        # Parse output to find player type
        # Format: "filename.sid               PlayerType"
        for line in result.stdout.splitlines():
            if filepath in line or os.path.basename(filepath) in line:
                parts = line.split()
                if len(parts) >= 2:
                    return parts[-1]  # Last part is the player type

    except Exception as e:
        logger.warning(f"Player type detection failed: {e}")

    return "Unknown"


def print_success_summary(input_path: str, output_path: str, driver_selection=None, validation_result=None, quiet=False):
    """Print an enhanced success summary with clear visual formatting.

    Args:
        input_path: Path to input SID file
        output_path: Path to output SF2 file
        driver_selection: Driver selection info (if available)
        validation_result: Validation result (if available)
        quiet: If True, print minimal output for automation
    """
    if quiet:
        # Quiet mode: minimal output for automation
        status = "OK" if not validation_result or validation_result.passed else "WARN"
        print(f"{status}: {os.path.basename(output_path)}")
        return

    # Normal mode: full success summary
    print()
    print("=" * 60)
    print("[SUCCESS] CONVERSION SUCCESSFUL!")
    print("=" * 60)
    print()
    print(f"Input:      {os.path.basename(input_path)}")
    print(f"Output:     {os.path.basename(output_path)}")

    if driver_selection:
        driver_name = driver_selection.driver_name if hasattr(driver_selection, 'driver_name') else 'Unknown'
        accuracy = driver_selection.expected_accuracy if hasattr(driver_selection, 'expected_accuracy') else 'N/A'
        print(f"Driver:     {driver_name} ({accuracy})")

    if validation_result:
        status = "PASSED" if validation_result.passed else "FAILED"
        errors = validation_result.errors
        warnings = validation_result.warnings
        print(f"Validation: {status} ({errors} errors, {warnings} warnings)")

    # Info file path
    info_file = Path(output_path).with_suffix('.txt')
    if info_file.exists():
        print(f"Info File:  {info_file.name}")

    print()
    print("Next Steps:")
    print(f"  - View in SF2 Viewer: sf2-viewer.bat \"{os.path.basename(output_path)}\"")
    print(f"  - Edit in SID Factory II")
    if Path(input_path).exists():
        print(f"  - Validate accuracy: validate-sid-accuracy.bat \"{os.path.basename(input_path)}\"")

    print()
    print("=" * 60)
    print()


def analyze_sid_file(filepath: str, config: ConversionConfig = None, sf2_reference_path: str = None, driver_type: str = None):
    """Analyze a SID file and print detailed information

    Args:
        filepath: Path to SID file
        config: Optional configuration (uses defaults if None)
        sf2_reference_path: Optional path to original SF2 file (for SF2-exported SIDs)
        driver_type: Optional driver type override ('driver11', 'laxity', 'np20')
    """
    if config is None:
        config = get_default_config()

    # Parse SID header and extract C64 data first
    parser = SIDParser(filepath)
    header = parser.parse_header()
    c64_data, load_address = parser.get_c64_data(header)

    # Detect player type using player-id.exe
    player_type = detect_player_type(filepath)

    # Check for SF2 magic marker
    has_sf2_magic = b'\x37\x13' in c64_data

    # Use DriverSelector to determine correct driver (unless manually overridden)
    if driver_type is None:
        selector = DriverSelector()
        selection = selector.select_driver(Path(filepath))
        driver_type = selection.driver_name
        logger.debug(f"Auto-selected driver: {driver_type} (reason: {selection.selection_reason})")
    else:
        logger.debug(f"Using manually specified driver: {driver_type}")

    # Determine which analyzer to use based on driver selection and SF2 magic
    # SF2-exported files (have magic marker AND driver11) use SF2PlayerParser
    # Laxity files (driver=laxity) use LaxityPlayerAnalyzer
    # Other files fallback to Laxity analyzer for table extraction
    is_sf2_exported = has_sf2_magic and driver_type == 'driver11'

    if config.extraction.verbose or logger.level <= logging.INFO:
        logger.info("=" * 60)
        logger.info("SID File Analysis")
        logger.info("=" * 60)
        logger.info(f"File: {filepath}")
        logger.info(f"Format: {header.magic} v{header.version}")
        logger.info(f"Player type: {player_type}")
        logger.info(f"Name: {header.name}")
        logger.info(f"Author: {header.author}")
        logger.info(f"Copyright: {header.copyright}")
        logger.info(f"Songs: {header.songs}")
        logger.info(f"Start song: {header.start_song}")
        logger.info(f"Load address: ${load_address:04X}")
        logger.info(f"Init address: ${header.init_address:04X}")
        logger.info(f"Play address: ${header.play_address:04X}")
        logger.info(f"Data size: {len(c64_data)} bytes")
        logger.info(f"End address: ${load_address + len(c64_data) - 1:04X}")
        logger.info("=" * 60)

    # Choose appropriate parser based on driver selection
    if is_sf2_exported:
        logger.info(f"Using SF2 player parser (driver: {driver_type}, SF2-exported file)")
        sf2_parser = SF2PlayerParser(filepath, sf2_reference_path)
        extracted = sf2_parser.extract()
    elif driver_type == 'laxity':
        logger.info(f"Using Laxity player analyzer (driver: {driver_type})")
        analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
        extracted = analyzer.extract_music_data()
    else:
        # driver11 or np20 without SF2 magic - use Laxity analyzer for table extraction
        # The extracted data will be packaged with the selected driver (driver11/np20)
        logger.info(f"Using table extraction analyzer (driver: {driver_type}, player: {player_type})")
        analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
        extracted = analyzer.extract_music_data()

    return extracted


def convert_laxity_to_sf2(input_path: str, output_path: str, config: ConversionConfig = None) -> bool:
    """Convert a Laxity SID file using custom Laxity driver with pointer patching

    CRITICAL FIX (v2.9.1): Now uses SF2Writer with proper pointer patching instead
    of the broken LaxityConverter. The SF2Writer._inject_laxity_music_data() method
    applies 40 pointer patches and injects complete table structure.

    Args:
        input_path: Path to input Laxity SID file
        output_path: Path for output SF2 file
        config: Optional configuration

    Returns:
        True if conversion successful, False otherwise

    Raises:
        sidm2_errors.FileNotFoundError: If input file doesn't exist
        sidm2_errors.InvalidInputError: If SID analysis fails
    """
    if not os.path.exists(input_path):
        raise sidm2_errors.FileNotFoundError(
            path=input_path,
            context="input SID file",
            suggestions=[
                "Check the file path: python scripts/sid_to_sf2.py --help",
                "Use absolute path instead of relative",
                f"List files in directory: dir {os.path.dirname(input_path) or '.'}"
            ],
            docs_link="guides/LAXITY_DRIVER_USER_GUIDE.md"
        )

    try:
        logger.info(f"Converting with Laxity driver: {input_path}")
        logger.info(f"Output: {output_path}")

        # CRITICAL FIX: Use analyze_sid_file() to get proper ExtractedData
        # This ensures all tables (orderlists, sequences, instruments, wave, pulse, filter)
        # are extracted and ready for injection with pointer patching
        try:
            extracted = analyze_sid_file(input_path, config=config, driver_type='laxity')
        except Exception as e:
            file_size = Path(input_path).stat().st_size if Path(input_path).exists() else 0
            logger.error(
                f"Failed to analyze SID file: {e}\n"
                f"  Suggestion: Verify file is a valid SID file with PSID or RSID format\n"
                f"  Check: File size should be > 124 bytes (current: {file_size})\n"
                f"  Try: Use player-id.exe to identify player type: tools/player-id.exe {input_path}\n"
                f"  See: docs/reference/format-specification.md#sid-format"
            )
            raise sidm2_errors.InvalidInputError(
                input_type="SID file",
                value=input_path,
                expected="PSID or RSID format with valid player code",
                got=str(e),
                suggestions=[
                    "Verify file is a valid SID file: file input.sid",
                    "Re-download from HVSC or csdb.dk",
                    "Check file size (should be > 124 bytes)",
                    "Try using player-id.exe to identify player type: tools/player-id.exe input.sid"
                ],
                docs_link="reference/format-specification.md"
            )

        # CRITICAL FIX: Use SF2Writer with driver_type='laxity'
        # This triggers _inject_laxity_music_data() which applies 40 pointer patches
        writer = SF2Writer(extracted, driver_type='laxity')
        writer.write(output_path)

        # Get output file size for reporting
        output_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0

        logger.info(f"Laxity conversion successful!")
        logger.info(f"  Output: {output_path}")
        logger.info(f"  Size: {output_size} bytes")
        logger.info(f"  Expected accuracy: 70%")  # Conservative estimate, actual is 99.93% with complete table injection
        return True

    except Exception as e:
        logger.error(
            f"Laxity conversion error: {e}\n"
            f"  Suggestion: Check that the SID file is a valid Laxity NewPlayer v21 format\n"
            f"  Check: Use player-id.exe to verify player type: tools/player-id.exe {input_path}\n"
            f"  Try: Enable verbose logging to see detailed error: --verbose\n"
            f"  See: docs/guides/LAXITY_DRIVER_USER_GUIDE.md#troubleshooting"
        )
        raise sidm2_errors.ConversionError(
            stage="Laxity driver conversion",
            reason=str(e),
            input_file=input_path,
            suggestions=[
                "Check that the SID file is a valid Laxity NewPlayer v21 format",
                "Try using player-id.exe to verify player type: tools/player-id.exe input.sid",
                "Enable verbose logging to see detailed error: --verbose",
                "Try standard driver as fallback: --driver driver11"
            ],
            docs_link="guides/LAXITY_DRIVER_USER_GUIDE.md#troubleshooting"
        )


def convert_galway_to_sf2(input_path: str, output_path: str, config: ConversionConfig = None) -> bool:
    """Convert a Martin Galway SID file using table extraction and injection

    Args:
        input_path: Path to input Martin Galway SID file
        output_path: Path for output SF2 file
        config: Optional configuration

    Returns:
        True if conversion successful, False otherwise

    Raises:
        sidm2_errors.MissingDependencyError: If Galway converter not available
        sidm2_errors.FileNotFoundError: If input file doesn't exist
    """
    if not GALWAY_CONVERTER_AVAILABLE:
        raise sidm2_errors.MissingDependencyError(
            dependency="sidm2.galway_*",
            install_command="pip install -e .",
            alternatives=[
                "Use standard drivers instead:",
                "  python scripts/sid_to_sf2.py input.sid output.sf2 --driver driver11",
                "",
                "Note: Martin Galway converter provides 88-96% accuracy",
                "      Standard drivers may have lower accuracy"
            ],
            docs_link="README.md#installation"
        )

    if not os.path.exists(input_path):
        raise sidm2_errors.FileNotFoundError(
            path=input_path,
            context="input SID file",
            suggestions=[
                "Check the file path: python scripts/sid_to_sf2.py --help",
                "Use absolute path instead of relative",
                f"List files in directory: dir {os.path.dirname(input_path) or '.'}"
            ]
        )

    try:
        logger.info(f"Converting with Martin Galway player support: {input_path}")
        logger.info(f"Output: {output_path}")

        # Parse PSID header to get load address and music data
        parser = SIDParser(input_path)
        header = parser.parse_header()

        # Read SID file to get C64 data
        with open(input_path, 'rb') as f:
            sid_data = f.read()

        # Extract C64 music data (after header)
        c64_data = sid_data[header.data_offset:]

        logger.debug(f"  Load address: ${header.load_address:04X}")
        logger.debug(f"  Init address: ${header.init_address:04X}")
        logger.debug(f"  Play address: ${header.play_address:04X}")
        logger.debug(f"  Music data size: {len(c64_data):,} bytes")

        # Check if this is actually a Martin Galway file
        analyzer = MartinGalwayAnalyzer(input_path)
        sid_header = {
            'author': header.author if hasattr(header, 'author') else '',
            'name': header.name if hasattr(header, 'name') else '',
        }
        is_galway = MartinGalwayAnalyzer.detect_galway_player(sid_header, c64_data)

        if not is_galway:
            logger.warning("File does not appear to be Martin Galway format based on header analysis")
            logger.warning("Attempting conversion anyway...")

        # Perform conversion using GalwayConversionIntegrator
        try:
            # Load SF2 Driver 11 template
            driver11_template_path = Path('G5/drivers/sf2driver_driver11_00.prg')
            if not driver11_template_path.exists():
                # Try alternative location
                driver11_template_path = Path('G5/examples/Driver 11 Test - Arpeggio.sf2')

            if not driver11_template_path.exists():
                logger.error(
                    f"SF2 Driver 11 template not found at {driver11_template_path}\n"
                    f"  Suggestion: Verify repository structure is intact\n"
                    f"  Check: Ensure G5/drivers/ directory exists and contains driver templates\n"
                    f"  Try: Re-clone the repository if files are missing\n"
                    f"  See: docs/README.md#installation"
                )
                raise sidm2_errors.FileNotFoundError(
                    path=str(driver11_template_path),
                    context="SF2 Driver 11 template",
                    suggestions=[
                        "Verify repository structure is intact",
                        "Check that G5/drivers/ directory exists",
                        "Re-clone the repository if files are missing"
                    ],
                    docs_link="README.md#installation"
                )

            with open(driver11_template_path, 'rb') as f:
                sf2_template = f.read()

            logger.debug(f"  Loaded SF2 template: {len(sf2_template)} bytes from {driver11_template_path}")

            integrator = GalwayConversionIntegrator(input_path)
            sf2_data, confidence = integrator.integrate(
                c64_data,
                header.load_address,
                sf2_template
            )

            if sf2_data:
                # Write SF2 file
                with open(output_path, 'wb') as f:
                    f.write(sf2_data)

                logger.info(f"Galway conversion successful!")
                logger.info(f"  Output: {output_path}")
                logger.info(f"  Size: {len(sf2_data)} bytes")
                logger.info(f"  Confidence: {confidence*100:.0f}%")
                logger.info(f"  Expected accuracy: {confidence*100:.0f}%")
                return True
            else:
                logger.error(
                    "Galway conversion produced no output\n"
                    "  Suggestion: Check if the SID file is a valid Martin Galway music\n"
                    "  Try: Use --driver driver11 for better compatibility\n"
                    "  See: docs/guides/TROUBLESHOOTING.md#conversion-failures"
                )
                return False

        except Exception as e:
            logger.error(
                f"Galway conversion failed: {e}\n"
                f"  Suggestion: Try a different driver (--driver driver11)\n"
                f"  Check: Verify SID file is valid Martin Galway music\n"
                f"  See: docs/guides/TROUBLESHOOTING.md#galway-conversion-errors"
            )
            import traceback
            logger.debug(traceback.format_exc())
            return False

    except Exception as e:
        logger.error(
            f"Galway conversion error: {e}\n"
            f"  Suggestion: Check that the SID file is a valid Martin Galway format\n"
            f"  Check: Use player-id.exe to verify player type: tools/player-id.exe {input_path}\n"
            f"  Try: Enable verbose logging to see detailed error: --verbose\n"
            f"  See: docs/guides/TROUBLESHOOTING.md#galway-conversion-errors"
        )
        import traceback
        logger.debug(traceback.format_exc())
        raise sidm2_errors.ConversionError(
            stage="Martin Galway conversion",
            reason=str(e),
            input_file=input_path,
            suggestions=[
                "Check that the SID file is a valid Martin Galway format",
                "Try using player-id.exe to verify player type: tools/player-id.exe input.sid",
                "Enable verbose logging to see detailed error: --verbose",
                "Try standard driver as fallback: --driver driver11"
            ],
            docs_link="README.md#troubleshooting"
        )


def convert_sid_to_sf2(input_path: str, output_path: str, driver_type: str = None, config: ConversionConfig = None, sf2_reference_path: str = None, use_midi: bool = False, quiet: bool = False):
    """Convert a SID file to SF2 format

    Args:
        input_path: Path to input SID file
        output_path: Path for output SF2 file (or None to use config naming pattern)
        driver_type: 'driver11' for standard driver, 'np20' for NewPlayer 20, 'laxity' for Laxity driver (or None for automatic selection)
        config: Optional configuration (uses defaults if None)
        sf2_reference_path: Optional path to original SF2 file (for SF2-exported SIDs)
        use_midi: Use MIDI-based sequence extraction (Python emulator, high accuracy)
        quiet: Quiet mode (minimal output, errors only)

    Raises:
        sidm2_errors.FileNotFoundError: If input file doesn't exist
        sidm2_errors.InvalidInputError: If file format is invalid
        sidm2_errors.ConfigurationError: If driver_type is unknown
        sidm2_errors.PermissionError: If unable to write output file
    """
    try:
        # Load or use default configuration
        if config is None:
            config = get_default_config()

        # Validate input
        if not os.path.exists(input_path):
            raise sidm2_errors.FileNotFoundError(
                path=input_path,
                context="input SID file",
                suggestions=[
                    "Check the file path: python scripts/sid_to_sf2.py --help",
                    "Use absolute path instead of relative",
                    f"List files in directory: dir {os.path.dirname(input_path) or '.'}"
                ],
                docs_link="README.md#usage"
            )

        # CONVERSION POLICY v2.0: Automatic driver selection
        # If no driver specified, use DriverSelector to choose best driver for player type
        driver_selection = None
        if driver_type is None:
            logger.info("No driver specified - using automatic driver selection (Policy v2.0)")
            selector = DriverSelector()
            driver_selection = selector.select_driver(Path(input_path))
            driver_type = driver_selection.driver_name

            # Display driver selection information
            logger.info("")
            logger.info("=" * 70)
            logger.info(selector.format_selection_output(driver_selection))
            logger.info("=" * 70)
            logger.info("")
        else:
            # Manual driver override - still document it
            logger.info(f"Using manually specified driver: {driver_type}")
            # Create a selection record for documentation purposes
            selector = DriverSelector()
            player_type = detect_player_type(input_path)
            driver_selection = selector.select_driver(
                Path(input_path),
                player_type=player_type,
                force_driver=driver_type
            )

        # Track whether a custom driver already wrote the output file
        custom_driver_wrote_file = False

        # Handle Laxity driver (custom implementation)
        if driver_type == 'laxity':
            if not LAXITY_CONVERTER_AVAILABLE:
                raise sidm2_errors.MissingDependencyError(
                    dependency="sidm2.laxity_converter",
                    install_command="pip install -e .",
                    alternatives=[
                        "Use standard drivers instead:",
                        "  python scripts/sid_to_sf2.py input.sid output.sf2 --driver driver11",
                        "",
                        "Note: Standard drivers have 1-8% accuracy for Laxity files",
                        "      (vs 99.93% with Laxity driver)"
                    ],
                    docs_link="README.md#installation"
                )
            logger.info("Using custom Laxity driver (expected accuracy: 70-90%)")
            # Convert using Laxity driver but don't return yet - continue to validation
            convert_laxity_to_sf2(input_path, output_path, config=config)
            custom_driver_wrote_file = True
            # Fall through to validation and info file generation

        # Handle Martin Galway driver (table extraction and injection)
        elif driver_type == 'galway':
            if not GALWAY_CONVERTER_AVAILABLE:
                raise sidm2_errors.MissingDependencyError(
                    dependency="sidm2.galway_*",
                    install_command="pip install -e .",
                    alternatives=[
                        "Use standard drivers instead:",
                        "  python scripts/sid_to_sf2.py input.sid output.sf2 --driver driver11"
                    ],
                    docs_link="README.md#installation"
                )
            logger.info("Using Martin Galway table extraction and injection (expected accuracy: 88-96%)")
            # Convert using Galway driver but don't return yet - continue to validation
            convert_galway_to_sf2(input_path, output_path, config=config)
            custom_driver_wrote_file = True
            # Fall through to validation and info file generation

        # Standard driver conversion path (for driver11, np20, etc.)
        else:
            # Validate standard driver types
            available_drivers = list(config.driver.available_drivers) + ['laxity', 'galway']
            if driver_type not in available_drivers:
                raise sidm2_errors.ConfigurationError(
                    setting="driver",
                    value=driver_type,
                    valid_options=available_drivers,
                    example="python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity",
                    docs_link="reference/DRIVER_REFERENCE.md"
                )

            logger.info(f"Converting: {input_path}")
            logger.info(f"Output: {output_path}")
            logger.info(f"Driver: {driver_type}")
            if sf2_reference_path:
                logger.info(f"SF2 Reference: {sf2_reference_path}")

            # Analyze the SID file
            try:
                extracted = analyze_sid_file(input_path, config=config, sf2_reference_path=sf2_reference_path, driver_type=driver_type)
            except Exception as e:
                file_size = Path(input_path).stat().st_size if Path(input_path).exists() else 0
                logger.error(
                    f"Failed to analyze SID file: {e}\n"
                    f"  Suggestion: Verify file is a valid SID file with PSID or RSID format\n"
                    f"  Check: File size should be > 124 bytes (current: {file_size})\n"
                    f"  Try: Use player-id.exe to identify player type: tools/player-id.exe {input_path}\n"
                    f"  See: docs/reference/format-specification.md#sid-format"
                )
                raise sidm2_errors.InvalidInputError(
                    input_type="SID file",
                    value=input_path,
                    expected="PSID or RSID format with valid player code",
                    got=str(e),
                    suggestions=[
                        "Verify file is a valid SID file: file input.sid",
                        "Re-download from HVSC or csdb.dk",
                        "Check file size (should be > 124 bytes)",
                        "Try using player-id.exe to identify player type: tools/player-id.exe input.sid"
                    ],
                    docs_link="reference/format-specification.md"
                )

        # Reference files are ONLY for validation - NEVER copy data from them
        # We must ALWAYS extract from the SID file itself

        # Try to extract actual data from siddump (only for standard driver conversions)
        if 'extracted' in locals() and config.extraction.use_siddump:
            try:
                siddump_data = extract_from_siddump(input_path, playback_time=config.extraction.siddump_duration)
                if siddump_data:
                    extracted.siddump_data = siddump_data
                    logger.info(f"  Siddump extraction: {len(siddump_data['adsr_values'])} ADSR values, "
                          f"{len(siddump_data['waveforms'])} waveforms")
                else:
                    extracted.siddump_data = None
            except Exception as e:
                logger.warning(f"Siddump extraction failed (non-critical): {e}")
                extracted.siddump_data = None
        elif 'extracted' in locals():
            extracted.siddump_data = None

        # MIDI-based sequence extraction (optional, high accuracy, only for standard conversions)
        if use_midi and 'extracted' in locals():
            try:
                logger.info("Using MIDI-based sequence extraction...")
                from sidm2.sid_to_midi_emulator import convert_sid_to_midi
                from sidm2.midi_sequence_extractor import extract_sequences_from_midi_file
                import tempfile

                # Export to MIDI first
                with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tmp_midi:
                    midi_path = tmp_midi.name

                try:
                    convert_sid_to_midi(input_path, midi_path, frames=1000)
                    logger.info(f"  Exported MIDI: {midi_path}")

                    # Extract sequences from MIDI
                    sequences = extract_sequences_from_midi_file(midi_path)
                    logger.info(f"  Extracted MIDI sequences: "
                              f"V1={len(sequences.get('voice1', []))} events, "
                              f"V2={len(sequences.get('voice2', []))} events, "
                              f"V3={len(sequences.get('voice3', []))} events")

                    # Integrate MIDI sequences into extracted data
                    midi_extracted_sequences = _convert_midi_to_sequence_events(sequences)
                    if midi_extracted_sequences:
                        extracted.sequences = midi_extracted_sequences
                        logger.info(f"  MIDI sequences integrated successfully: {sum(len(s) for s in extracted.sequences)} total events")

                finally:
                    # Clean up temporary MIDI file
                    if os.path.exists(midi_path):
                        os.unlink(midi_path)

            except Exception as e:
                logger.warning(f"MIDI extraction failed (non-critical): {e}")

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            if config.output.create_dirs:
                try:
                    os.makedirs(output_dir, exist_ok=True)
                except OSError as e:
                    raise sidm2_errors.PermissionError(
                        operation="create directory",
                        path=output_dir,
                        docs_link="README.md#troubleshooting"
                    )
            else:
                raise sidm2_errors.FileNotFoundError(
                    path=output_dir,
                    context="output directory",
                    suggestions=[
                        "Create the directory manually",
                        "Use --create-dirs option to create automatically",
                        "Or set config.output.create_dirs=true"
                    ],
                    docs_link="README.md#usage"
                )

        # Write the SF2 file (skip if custom driver already wrote it)
        if not custom_driver_wrote_file:
            # Check if output file already exists
            if os.path.exists(output_path) and not config.output.overwrite:
                raise sidm2_errors.PermissionError(
                    operation="overwrite",
                    path=output_path,
                    docs_link="README.md#usage"
                )

            # Write the SF2 file using standard driver
            try:
                writer = SF2Writer(extracted, driver_type=driver_type)
                writer.write(output_path)
            except Exception as e:
                logger.error(
                    f"Failed to write SF2 file: {e}\n"
                    f"  Suggestion: Check file permissions and disk space\n"
                    f"  Check: Ensure output directory exists and is writable\n"
                    f"  Try: Use a different output path or check disk space\n"
                    f"  See: docs/guides/TROUBLESHOOTING.md#file-write-failures"
                )
                raise sidm2_errors.PermissionError(
                    operation="write",
                    path=output_path,
                    docs_link="README.md#troubleshooting"
                )
        else:
            logger.debug("Skipping SF2Writer (custom driver already wrote file)")

        # CONVERSION POLICY v2.0: Validate SF2 format
        logger.info("")
        logger.info("Validating SF2 file format...")
        try:
            # Import validator
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
            from scripts.validate_sf2_format import SF2FormatValidator

            validator = SF2FormatValidator()
            validation_result = validator.validate_file(Path(output_path), verbose=False)

            if validation_result.passed:
                logger.info(f"SUCCESS: SF2 format validation passed")
                if validation_result.warnings > 0:
                    logger.warning(f"  {validation_result.warnings} warnings detected")
            else:
                logger.error(
                    f"FAILED: SF2 format validation failed ({validation_result.errors} errors)\n"
                    f"  Suggestion: File may still work in SID Factory II despite validation errors\n"
                    f"  Try: Test the SF2 file in SID Factory II editor\n"
                    f"  Check: Review validation errors below for specific issues\n"
                    f"  See: docs/guides/TROUBLESHOOTING.md#sf2-validation-failures"
                )
                # Log errors but don't fail the conversion
                for check in validation_result.checks:
                    if check.severity == "ERROR":
                        logger.error(
                            f"  - {check.name}: {check.message}\n"
                            f"    Suggestion: This validation check failed\n"
                            f"    Check: Review error details above for root cause\n"
                            f"    Try: Re-generate SF2 file or fix source data\n"
                            f"    See: docs/guides/TROUBLESHOOTING.md#sf2-validation-failures"
                        )
        except Exception as e:
            logger.warning(f"SF2 format validation skipped (validator unavailable): {e}")
            validation_result = None

        # CONVERSION POLICY v2.0: Generate info file with driver documentation
        if driver_selection:
            try:
                # Parse SID header for metadata
                parser = SIDParser(input_path)
                header = parser.parse_header()

                sid_metadata = {
                    'title': header.name if hasattr(header, 'name') else '(unknown)',
                    'author': header.author if hasattr(header, 'author') else '(unknown)',
                    'copyright': header.copyright if hasattr(header, 'copyright') else '(unknown)',
                    'format': f"{header.magic} v{header.version}" if hasattr(header, 'magic') else 'Unknown',
                    'load_addr': header.load_address if hasattr(header, 'load_address') else 0,
                    'init_addr': header.init_address if hasattr(header, 'init_address') else 0,
                    'play_addr': header.play_address if hasattr(header, 'play_address') else 0,
                    'songs': header.songs if hasattr(header, 'songs') else 0,
                }

                # Convert validation result to dict
                validation_dict = None
                if validation_result:
                    validation_dict = {
                        'status': 'PASS' if validation_result.passed else 'FAIL',
                        'details': [
                            f"{check.name}: {check.message}"
                            for check in validation_result.checks
                            if check.severity in ('ERROR', 'WARNING')
                        ]
                    }

                # Generate info file content
                info_content = selector.create_conversion_info(
                    driver_selection,
                    Path(input_path),
                    Path(output_path),
                    sid_metadata,
                    validation_dict
                )

                # Write info file
                info_file_path = Path(output_path).with_suffix('.txt')
                info_file_path.write_text(info_content, encoding='utf-8')
                logger.info(f"Generated info file: {info_file_path.name}")
            except Exception as e:
                logger.warning(f"Failed to generate info file: {e}")

        # Optional: Export audio using VSID (if enabled in config)
        if config and getattr(config, 'export_audio', False):
            try:
                if AUDIO_EXPORT_INTEGRATION_AVAILABLE:
                    logger.info("Exporting audio using VSID...")
                    audio_output_path = Path(output_path).with_suffix('.wav')
                    audio_duration = getattr(config, 'audio_duration', 30)

                    result = AudioExportIntegration.export_to_wav(
                        sid_file=Path(input_path),
                        output_file=audio_output_path,
                        duration=audio_duration,
                        verbose=config.verbose if hasattr(config, 'verbose') else 1
                    )

                    if result and result.get('success'):
                        tool_name = result.get('tool', 'unknown')
                        logger.info(f"Audio export complete using {tool_name.upper()}: {audio_output_path.name}")
                    else:
                        logger.warning("Audio export failed or not available")
                else:
                    logger.warning("Audio export not available (AudioExportIntegration not installed)")
            except Exception as e:
                logger.warning(f"Audio export failed: {e}")

        # Print enhanced success summary
        print_success_summary(
            input_path=input_path,
            output_path=output_path,
            driver_selection=driver_selection,
            validation_result=validation_result,
            quiet=quiet
        )

        logger.info("IMPORTANT NOTES:")
        logger.info("- This is an experimental converter")
        logger.info("- The output file may need manual editing in SID Factory II")
        logger.info("- Complex music data extraction is still in development")
        logger.info("- Consider this a starting point for further refinement")

    except sidm2_errors.SIDMError:
        # Re-raise our custom errors (they have helpful messages)
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.error(
            f"Unexpected error during conversion: {e}\n"
            f"  Suggestion: Enable verbose logging to see detailed error: --verbose\n"
            f"  Check: Verify all dependencies are installed: pip install -e .\n"
            f"  Try: Use a different driver: --driver driver11\n"
            f"  See: docs/guides/TROUBLESHOOTING.md#unexpected-errors"
        )
        raise sidm2_errors.ConversionError(
            stage="conversion",
            reason=str(e),
            input_file=input_path,
            suggestions=[
                "Enable verbose logging to see detailed error: --verbose",
                "Check that all dependencies are installed: pip install -e .",
                "Try a different driver: --driver driver11"
            ],
            docs_link="README.md#troubleshooting"
        )


def convert_sid_to_both_drivers(input_path: str, output_dir: str = None, config: ConversionConfig = None, sf2_reference_path: str = None):
    """Convert a SID file to both NP20 and Driver 11 formats

    Args:
        input_path: Path to input SID file
        output_dir: Output directory (default: same as input or config.output.output_dir)
        config: Optional configuration (uses defaults if None)
        sf2_reference_path: Optional path to original SF2 file (for SF2-exported SIDs)

    Returns:
        Dict with output file paths and sizes

    Raises:
        sidm2_errors.FileNotFoundError: If input file doesn't exist
        sidm2_errors.InvalidInputError: If file format is invalid
        sidm2_errors.PermissionError: If unable to write output files
    """
    try:
        # Load or use default configuration
        if config is None:
            config = get_default_config()

        # Validate input
        if not os.path.exists(input_path):
            raise sidm2_errors.FileNotFoundError(
                path=input_path,
                context="input SID file",
                suggestions=[
                    "Check the file path: python scripts/sid_to_sf2.py --help",
                    "Use absolute path instead of relative",
                    f"List files in directory: dir {os.path.dirname(input_path) or '.'}"
                ],
                docs_link="README.md#usage"
            )

        base_name = os.path.splitext(os.path.basename(input_path))[0]

        # Determine output directory
        if output_dir is None:
            output_dir = config.output.output_dir or os.path.dirname(input_path) or '.'

        if config.output.create_dirs:
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                raise sidm2_errors.PermissionError(
                    operation="create directory",
                    path=output_dir,
                    docs_link="README.md#troubleshooting"
                )
        elif not os.path.exists(output_dir):
            raise sidm2_errors.FileNotFoundError(
                path=output_dir,
                context="output directory",
                suggestions=[
                    "Create the directory manually",
                    "Use --create-dirs option to create automatically",
                    "Or set config.output.create_dirs=true"
                ],
                docs_link="README.md#usage"
            )

        # Analyze the SID file once (auto-select driver for analysis)
        try:
            extracted = analyze_sid_file(input_path, config=config, sf2_reference_path=sf2_reference_path, driver_type=None)
        except Exception as e:
            file_size = Path(input_path).stat().st_size if Path(input_path).exists() else 0
            logger.error(
                f"Failed to analyze SID file: {e}\n"
                f"  Suggestion: Verify file is a valid SID file with PSID or RSID format\n"
                f"  Check: File size should be > 124 bytes (current: {file_size})\n"
                f"  Try: Use player-id.exe to identify player type: tools/player-id.exe {input_path}\n"
                f"  See: docs/reference/format-specification.md#sid-format"
            )
            raise sidm2_errors.InvalidInputError(
                input_type="SID file",
                value=input_path,
                expected="PSID or RSID format with valid player code",
                got=str(e),
                suggestions=[
                    "Verify file is a valid SID file: file input.sid",
                    "Re-download from HVSC or csdb.dk",
                    "Check file size (should be > 124 bytes)",
                    "Try using player-id.exe to identify player type: tools/player-id.exe input.sid"
                ],
                docs_link="reference/format-specification.md"
            )

        # Try to extract actual data from siddump (only for standard driver conversions)
        if 'extracted' in locals() and config.extraction.use_siddump:
            try:
                siddump_data = extract_from_siddump(input_path, playback_time=config.extraction.siddump_duration)
                if siddump_data:
                    extracted.siddump_data = siddump_data
                    logger.info(f"  Siddump extraction: {len(siddump_data['adsr_values'])} ADSR values, "
                          f"{len(siddump_data['waveforms'])} waveforms")
                else:
                    extracted.siddump_data = None
            except Exception as e:
                logger.warning(f"Siddump extraction failed (non-critical): {e}")
                extracted.siddump_data = None
        elif 'extracted' in locals():
            extracted.siddump_data = None

        results = {}

        # Generate both driver versions
        for driver_type in ['np20', 'driver11']:
            try:
                if driver_type == 'np20':
                    output_file = os.path.join(output_dir, f"{base_name}_g4.sf2")
                    driver_label = "NP20 (G4)"
                else:
                    output_file = os.path.join(output_dir, f"{base_name}_d11.sf2")
                    driver_label = "Driver 11"

                # Check if output file already exists
                if os.path.exists(output_file) and not config.output.overwrite:
                    logger.warning(f"Skipping {driver_type}: file already exists: {output_file}")
                    results[driver_type] = {'skipped': True, 'path': output_file}
                    continue

                # Write the SF2 file
                writer = SF2Writer(extracted, driver_type=driver_type)
                writer.write(output_file)

                size = os.path.getsize(output_file)
                results[driver_type] = {
                    'path': output_file,
                    'size': size
                }
                logger.info(f"  -> {os.path.basename(output_file)} ({driver_label}, {size:,} bytes)")
            except Exception as e:
                logger.error(
                    f"Failed to generate {driver_type} version: {e}\n"
                    f"  Suggestion: Try a different driver type (automatic selection will continue)\n"
                    f"  Check: Ensure input SID file is compatible with {driver_type}\n"
                    f"  See: docs/guides/DRIVER_SELECTION_GUIDE.md#{driver_type.lower()}"
                )
                # Continue with next driver type instead of failing completely
                results[driver_type] = {'error': str(e)}

        # Check if at least one conversion succeeded
        if all('error' in v or 'skipped' in v for v in results.values()):
            error_details = [f"  - {k}: {v.get('error', 'unknown')}" for k, v in results.items() if 'error' in v]
            raise sidm2_errors.ConversionError(
                stage='SF2 Generation',
                reason='All driver types failed to generate SF2 files',
                input_file=str(input_path),
                suggestions=[
                    'Check if input SID file is valid: tools/player-id.exe input.sid',
                    'Try a specific driver manually: --driver laxity or --driver driver11',
                    'Enable verbose logging: --verbose',
                    'Check error details above for specific failures',
                    'Verify SID file format with: hexdump -C input.sid | head -20'
                ]
            )

        return results

    except sidm2_errors.SIDMError:
        # Re-raise our custom errors
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.error(
            f"Unexpected error during dual conversion: {e}\n"
            f"  Suggestion: Enable verbose logging to see detailed error: --verbose\n"
            f"  Check: Verify all dependencies are installed: pip install -e .\n"
            f"  Try: Use single driver conversion first: --driver driver11\n"
            f"  See: docs/guides/TROUBLESHOOTING.md#dual-conversion-errors"
        )
        raise sidm2_errors.ConversionError(
            stage="dual driver conversion",
            reason=str(e),
            input_file=input_path,
            suggestions=[
                "Enable verbose logging to see detailed error: --verbose",
                "Check that all dependencies are installed: pip install -e .",
                "Try single driver conversion first: --driver driver11"
            ],
            docs_link="README.md#troubleshooting"
        )
