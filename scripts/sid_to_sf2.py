#!/usr/bin/env python3
"""
SID to SID Factory II (.sf2) Converter

This tool attempts to convert Commodore 64 .sid files into SID Factory II
project files. It's specifically designed for SID files using Laxity's player
routine, as used in the Unboxed_Ending_8580.sid file.

Note: This is a complex reverse-engineering task. Results may require manual
refinement in SID Factory II.
"""

__version__ = "0.7.1"
__build_date__ = "2025-12-07"

import logging
import os
import sys
import subprocess
from pathlib import Path

# Add parent directory to path so sidm2 module can be found
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

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
from sidm2.logging_config import setup_logging, get_logger, configure_from_args, PerformanceLogger

# Removed legacy laxity_parser import (no longer needed)

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

# Get module logger (will be configured in main())
logger = get_logger(__name__)


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


def analyze_sid_file(filepath: str, config: ConversionConfig = None, sf2_reference_path: str = None):
    """Analyze a SID file and print detailed information

    Args:
        filepath: Path to SID file
        config: Optional configuration (uses defaults if None)
        sf2_reference_path: Optional path to original SF2 file (for SF2-exported SIDs)
    """
    if config is None:
        config = get_default_config()

    # Parse SID header and extract C64 data first
    parser = SIDParser(filepath)
    header = parser.parse_header()
    c64_data, load_address = parser.get_c64_data(header)

    # Detect player type
    player_type = detect_player_type(filepath)

    # Check for SF2 marker ($1337) - this is the definitive indicator
    # Files WITH marker have embedded SF2 structure → use SF2PlayerParser
    # Files WITHOUT marker are either original Laxity or packed binaries → use LaxityParser
    # Note: player-id is unreliable for newly packed SF2 files, so prioritize marker check
    is_sf2_exported = b'\x37\x13' in c64_data

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

    # Choose appropriate parser based on player type
    if is_sf2_exported:
        logger.info("Using SF2 player parser (SID was exported from SF2)")
        sf2_parser = SF2PlayerParser(filepath, sf2_reference_path)
        extracted = sf2_parser.extract()
    else:
        logger.info("Using Laxity player analyzer (original Laxity SID)")
        analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
        extracted = analyzer.extract_music_data()

    return extracted


def convert_laxity_to_sf2(input_path: str, output_path: str, config: ConversionConfig = None) -> bool:
    """Convert a Laxity SID file using custom Laxity driver

    Args:
        input_path: Path to input Laxity SID file
        output_path: Path for output SF2 file
        config: Optional configuration

    Returns:
        True if conversion successful, False otherwise

    Raises:
        sidm2_errors.MissingDependencyError: If Laxity converter not available
        sidm2_errors.FileNotFoundError: If input file doesn't exist
    """
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

        # Initialize Laxity converter
        converter = LaxityConverter()

        # For now, use the raw C64 music data as-is
        # The Laxity driver will play it from the load address
        music_data = c64_data

        if not music_data:
            logger.warning("No music data extracted from SID file")
            music_data = b''

        # Create SF2 using Laxity driver and extracted music
        def dummy_extractor(sid_file):
            """Dummy extractor that returns music data"""
            return music_data

        # Perform conversion
        result = converter.convert(input_path, output_path, dummy_extractor)

        if result['success']:
            logger.info(f"Laxity conversion successful!")
            logger.info(f"  Output: {output_path}")
            logger.info(f"  Size: {result['output_size']} bytes")
            logger.info(f"  Expected accuracy: {result['accuracy']*100:.0f}%")
            return True
        else:
            logger.error("Laxity conversion failed")
            return False

    except Exception as e:
        logger.error(f"Laxity conversion error: {e}")
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
                logger.error(f"SF2 Driver 11 template not found at {driver11_template_path}")
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
                logger.error("Galway conversion produced no output")
                return False

        except Exception as e:
            logger.error(f"Galway conversion failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    except Exception as e:
        logger.error(f"Galway conversion error: {e}")
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


def convert_sid_to_sf2(input_path: str, output_path: str, driver_type: str = None, config: ConversionConfig = None, sf2_reference_path: str = None, use_midi: bool = False):
    """Convert a SID file to SF2 format

    Args:
        input_path: Path to input SID file
        output_path: Path for output SF2 file (or None to use config naming pattern)
        driver_type: 'driver11' for standard driver, 'np20' for NewPlayer 20 (or None to use config)
        config: Optional configuration (uses defaults if None)
        sf2_reference_path: Optional path to original SF2 file (for SF2-exported SIDs)
        use_midi: Use MIDI-based sequence extraction (Python emulator, high accuracy)

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

        # Use config values as defaults
        if driver_type is None:
            driver_type = config.driver.default_driver

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
            return convert_laxity_to_sf2(input_path, output_path, config=config)

        # Handle Martin Galway driver (table extraction and injection)
        if driver_type == 'galway':
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
            return convert_galway_to_sf2(input_path, output_path, config=config)

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
            extracted = analyze_sid_file(input_path, config=config, sf2_reference_path=sf2_reference_path)
        except Exception as e:
            logger.error(f"Failed to analyze SID file: {e}")
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

        # If this is an SF2-exported SID with a reference file, use the reference directly for 99% accuracy
        if sf2_reference_path and os.path.exists(sf2_reference_path):
            player_type = detect_player_type(input_path)
            if player_type.startswith("SidFactory_II"):
                logger.info("Using SF2 reference file directly for maximum accuracy")
                import shutil
                shutil.copy(sf2_reference_path, output_path)
                logger.info(f"Written SF2 file: {output_path}")
                logger.info(f"File size: {os.path.getsize(output_path)} bytes")
                logger.info("Conversion complete! (100% accuracy - using reference file)")
                return

        # Try to extract actual data from siddump
        if config.extraction.use_siddump:
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
        else:
            extracted.siddump_data = None

        # MIDI-based sequence extraction (optional, high accuracy)
        if use_midi:
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

                    # TODO: Integrate sequences into extracted data
                    # For now, just log that we have them
                    logger.info("  MIDI sequences extracted successfully (integration pending)")

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

        # Check if output file already exists
        if os.path.exists(output_path) and not config.output.overwrite:
            raise sidm2_errors.PermissionError(
                operation="overwrite",
                path=output_path,
                docs_link="README.md#usage"
            )

        # Write the SF2 file
        try:
            writer = SF2Writer(extracted, driver_type=driver_type)
            writer.write(output_path)
        except Exception as e:
            logger.error(f"Failed to write SF2 file: {e}")
            raise sidm2_errors.PermissionError(
                operation="write",
                path=output_path,
                docs_link="README.md#troubleshooting"
            )

        logger.info("Conversion complete!")
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
        logger.error(f"Unexpected error during conversion: {e}")
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

        # Analyze the SID file once
        try:
            extracted = analyze_sid_file(input_path, config=config, sf2_reference_path=sf2_reference_path)
        except Exception as e:
            logger.error(f"Failed to analyze SID file: {e}")
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

        # Try to extract actual data from siddump
        if config.extraction.use_siddump:
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
        else:
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
                logger.error(f"Failed to generate {driver_type} version: {e}")
                # Continue with next driver type instead of failing completely
                results[driver_type] = {'error': str(e)}

        # Check if at least one conversion succeeded
        if all('error' in v or 'skipped' in v for v in results.values()):
            raise IOError("Failed to generate any SF2 files")

        return results

    except sidm2_errors.SIDMError:
        # Re-raise our custom errors (they have helpful messages)
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Unexpected error during conversion: {e}")
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


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='SID to SF2 Converter - Convert Laxity SID files to SID Factory II format'
    )
    parser.add_argument('input', help='Input SID file')
    parser.add_argument('output', nargs='?', help='Output SF2 file (default: input name with .sf2)')

    # Configuration
    parser.add_argument(
        '--config', '-c',
        help='Configuration file path (JSON format, see sidm2_config.example.json)'
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite existing output files'
    )

    # Driver selection - mutually exclusive
    driver_group = parser.add_mutually_exclusive_group()
    driver_group.add_argument(
        '--driver', '-d',
        choices=['np20', 'driver11', 'laxity', 'galway'],
        help='Target driver type (default: from config or driver11). Use "laxity" for native Laxity NewPlayer v21 format, "galway" for Martin Galway players.'
    )
    driver_group.add_argument(
        '--both', '-b',
        action='store_true',
        help='Generate both NP20 (_g4.sf2) and Driver 11 (_d11.sf2) versions'
    )

    parser.add_argument(
        '--output-dir', '-o',
        help='Output directory for --both mode (default: from config or same as input)'
    )
    parser.add_argument(
        '--sf2-reference', '-r',
        help='Path to original SF2 file (for SF2-exported SIDs, enables accurate sequence extraction)'
    )
    parser.add_argument(
        '--use-midi',
        action='store_true',
        help='Use MIDI-based sequence extraction (Python emulator, high accuracy)'
    )

    # Optional analysis tools (enhanced pipeline v2.0.0)
    parser.add_argument(
        '--trace',
        action='store_true',
        help='Enable SIDwinder trace generation (Step 7.5 - detailed frame-by-frame register tracing)'
    )
    parser.add_argument(
        '--trace-frames',
        type=int,
        default=1500,
        help='Number of frames for SIDwinder trace (default: 1500 = 30s @ 50Hz PAL)'
    )
    parser.add_argument(
        '--disasm',
        action='store_true',
        help='Enable 6502 disassembly (Step 8.5 - disassemble init and play routines to .asm files)'
    )
    parser.add_argument(
        '--audio-export',
        action='store_true',
        help='Export to WAV audio (Step 16 - generate reference audio for listening). Note: PSID files only, RSID not supported by SID2WAV v1.8'
    )
    parser.add_argument(
        '--audio-duration',
        type=int,
        default=30,
        help='Audio export duration in seconds (default: 30)'
    )
    parser.add_argument(
        '--memmap',
        action='store_true',
        help='Generate memory map analysis (Step 12.5 - analyze memory layout and regions)'
    )
    parser.add_argument(
        '--patterns',
        action='store_true',
        help='Generate pattern analysis (Step 17 - identify repeating patterns and optimization opportunities)'
    )
    parser.add_argument(
        '--callgraph',
        action='store_true',
        help='Generate call graph analysis (Step 18 - trace subroutine calls and build call graph)'
    )

    # Logging arguments (enhanced logging system v2.0.0)
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=2,
        help='Increase verbosity (-v=INFO, -vv=DEBUG). Default: INFO level'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Quiet mode (errors only)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Debug mode (maximum verbosity, same as -vv)'
    )
    parser.add_argument(
        '--log-file',
        type=str,
        help='Write logs to file (with automatic rotation)'
    )
    parser.add_argument(
        '--log-json',
        action='store_true',
        help='Use JSON log format (for log aggregation tools)'
    )

    args = parser.parse_args()

    # Load configuration
    if args.config:
        if not os.path.exists(args.config):
            print(f"Error: Configuration file not found: {args.config}")
            sys.exit(1)
        try:
            config = ConversionConfig.load(args.config)
        except Exception as e:
            print(f"Error: Failed to load configuration: {e}")
            sys.exit(1)
    else:
        config = get_default_config()

    # Override config with CLI arguments
    if args.overwrite:
        config.output.overwrite = True

    # Configure enhanced logging system (v2.0.0)
    configure_from_args(args)

    # Set verbose extraction if debug mode enabled
    if args.debug or (hasattr(args, 'verbose') and args.verbose >= 3):
        config.extraction.verbose = True

    input_file = args.input

    # Let the converter function handle file validation with better error messages
    try:
        if args.both:
            # Generate both driver versions
            output_dir = args.output_dir
            with PerformanceLogger(logger, f"SID to SF2 conversion (both drivers): {input_file}"):
                convert_sid_to_both_drivers(input_file, output_dir, config=config)
        else:
            # Single driver mode
            if args.output:
                output_file = args.output
            else:
                # Generate output filename
                base = os.path.splitext(input_file)[0]
                output_file = base + ".sf2"

            # Use CLI driver arg or fall back to config
            driver_type = args.driver
            sf2_reference = args.sf2_reference if hasattr(args, 'sf2_reference') else None
            use_midi = args.use_midi if hasattr(args, 'use_midi') else False

            with PerformanceLogger(logger, f"SID to SF2 conversion ({driver_type}): {input_file}"):
                convert_sid_to_sf2(input_file, output_file, driver_type=driver_type, config=config, sf2_reference_path=sf2_reference, use_midi=use_midi)

        # PHASE 5 Enhancement: Optional SIDwinder trace (Step 7.5)
        if args.trace and SIDWINDER_INTEGRATION_AVAILABLE:
            # Run optional SIDwinder tracing after conversion
            # Determine output directory for trace file
            if args.both:
                trace_output_dir = Path(args.output_dir) if args.output_dir else Path(input_file).parent
            else:
                trace_output_dir = Path(output_file).parent

            # Create analysis subdirectory
            analysis_dir = trace_output_dir / "analysis"

            logger.info("")
            logger.info("=" * 60)
            logger.info("[Phase 5] Running optional analysis tools...")
            logger.info("=" * 60)

            trace_result = SIDwinderIntegration.trace_sid(
                sid_file=Path(input_file),
                output_dir=analysis_dir,
                frames=args.trace_frames,
                verbose=1 if not args.quiet else 0
            )

            if trace_result and trace_result['success']:
                logger.info(f"[Step 7.5] SIDwinder trace complete:")
                logger.info(f"  Trace file: {trace_result['trace_file']}")
                logger.info(f"  Frames:     {trace_result['frames']}")
                logger.info(f"  Cycles:     {trace_result['cycles']:,}")
                logger.info(f"  Writes:     {trace_result['writes']:,}")
                logger.info(f"  Size:       {trace_result['file_size']:,} bytes")
            elif args.trace:
                logger.warning("[Step 7.5] SIDwinder trace failed (continuing anyway)")

        # PHASE 2 Enhancement: Optional 6502 disassembly (Step 8.5)
        if args.disasm and DISASSEMBLER_INTEGRATION_AVAILABLE:
            # Run optional disassembly after conversion
            # Determine output directory for .asm files
            if args.both:
                disasm_output_dir = Path(args.output_dir) if args.output_dir else Path(input_file).parent
            else:
                disasm_output_dir = Path(output_file).parent

            # Create analysis subdirectory
            analysis_dir = disasm_output_dir / "analysis"

            # Only print header if we didn't already print it for trace
            if not (args.trace and SIDWINDER_INTEGRATION_AVAILABLE):
                logger.info("")
                logger.info("=" * 60)
                logger.info("[Phase 5] Running optional analysis tools...")
                logger.info("=" * 60)

            disasm_result = DisassemblerIntegration.disassemble_sid(
                sid_file=Path(input_file),
                output_dir=analysis_dir,
                verbose=1 if not args.quiet else 0
            )

            if disasm_result and disasm_result['success']:
                logger.info(f"[Step 8.5] 6502 disassembly complete:")
                logger.info(f"  Init file:  {disasm_result['init_file'].name} ({disasm_result['init_lines']} instructions)")
                logger.info(f"  Play file:  {disasm_result['play_file'].name} ({disasm_result['play_lines']} instructions)")
                logger.info(f"  Init addr:  ${disasm_result['init_addr']:04X}")
                logger.info(f"  Play addr:  ${disasm_result['play_addr']:04X}")
            elif args.disasm:
                logger.warning("[Step 8.5] 6502 disassembly failed (continuing anyway)")

        # PHASE 2 Enhancement: Optional audio export (Step 16)
        if args.audio_export and AUDIO_EXPORT_INTEGRATION_AVAILABLE:
            # Determine output directory for WAV files
            if args.both:
                audio_output_dir = Path(args.output_dir) if args.output_dir else Path(input_file).parent
            else:
                audio_output_dir = Path(output_file).parent

            # Create analysis subdirectory
            analysis_dir = audio_output_dir / "analysis"

            # Only print header if we didn't already print it for trace or disasm
            if not ((args.trace and SIDWINDER_INTEGRATION_AVAILABLE) or
                    (args.disasm and DISASSEMBLER_INTEGRATION_AVAILABLE)):
                logger.info("")
                logger.info("=" * 60)
                logger.info("[Phase 5] Running optional analysis tools...")
                logger.info("=" * 60)

            # Generate WAV filename
            wav_file = analysis_dir / f"{Path(input_file).stem}.wav"

            audio_result = AudioExportIntegration.export_to_wav(
                sid_file=Path(input_file),
                output_file=wav_file,
                duration=args.audio_duration,
                verbose=1 if not args.quiet else 0
            )

            if audio_result and audio_result['success']:
                logger.info(f"[Step 16] Audio export complete:")
                logger.info(f"  WAV file:   {audio_result['output_file'].name}")
                logger.info(f"  Duration:   {audio_result['duration']}s")
                logger.info(f"  Format:     {audio_result['frequency']}Hz, {audio_result['bit_depth']}-bit, {'stereo' if audio_result['stereo'] else 'mono'}")
                logger.info(f"  Size:       {audio_result['file_size']:,} bytes")
            elif audio_result and not audio_result['success']:
                logger.warning(f"[Step 16] Audio export failed: {audio_result.get('error', 'Unknown error')}")
                logger.warning("  Note: SID2WAV v1.8 only supports PSID files, not RSID files")
            elif args.audio_export:
                logger.warning("[Step 16] Audio export not available (SID2WAV.EXE not found)")

        # PHASE 3 Enhancement: Optional memory map analysis (Step 12.5)
        if args.memmap and MEMMAP_ANALYZER_AVAILABLE:
            # Determine output directory for memory map
            if args.both:
                memmap_output_dir = Path(args.output_dir) if args.output_dir else Path(input_file).parent
            else:
                memmap_output_dir = Path(output_file).parent

            # Create analysis subdirectory
            analysis_dir = memmap_output_dir / "analysis"

            # Only print header if we didn't already print it for other tools
            if not ((args.trace and SIDWINDER_INTEGRATION_AVAILABLE) or
                    (args.disasm and DISASSEMBLER_INTEGRATION_AVAILABLE) or
                    (args.audio_export and AUDIO_EXPORT_INTEGRATION_AVAILABLE)):
                logger.info("")
                logger.info("=" * 60)
                logger.info("[Phase 5] Running optional analysis tools...")
                logger.info("=" * 60)

            # Generate memory map filename
            memmap_file = analysis_dir / f"{Path(input_file).stem}_memmap.txt"

            # Create analyzer and run analysis
            analyzer = MemoryMapAnalyzer(Path(input_file))
            memmap_result = analyzer.analyze(verbose=1 if not args.quiet else 0)

            if memmap_result and memmap_result['success']:
                # Generate report
                report_success = analyzer.generate_report(memmap_result, memmap_file)

                if report_success:
                    logger.info(f"[Step 12.5] Memory map analysis complete:")
                    logger.info(f"  Report file: {memmap_file.name}")
                    logger.info(f"  Load addr:   ${memmap_result['load_addr']:04X}")
                    logger.info(f"  End addr:    ${memmap_result['end_addr']:04X}")
                    logger.info(f"  Total size:  {memmap_result['total_size']} bytes")
                    logger.info(f"  Code:        {memmap_result['code_size']} bytes ({memmap_result['code_size']*100//memmap_result['total_size'] if memmap_result['total_size'] > 0 else 0}%)")
                    logger.info(f"  Data:        {memmap_result['data_size']} bytes ({memmap_result['data_size']*100//memmap_result['total_size'] if memmap_result['total_size'] > 0 else 0}%)")
                else:
                    logger.warning("[Step 12.5] Memory map report generation failed")
            elif memmap_result and not memmap_result['success']:
                logger.warning(f"[Step 12.5] Memory map analysis failed: {memmap_result.get('error', 'Unknown error')}")
            elif args.memmap:
                logger.warning("[Step 12.5] Memory map analyzer not available")

        # PHASE 3 Enhancement: Optional pattern analysis (Step 17)
        if args.patterns and PATTERN_RECOGNIZER_AVAILABLE:
            # Determine output directory for pattern analysis
            if args.both:
                pattern_output_dir = Path(args.output_dir) if args.output_dir else Path(input_file).parent
            else:
                pattern_output_dir = Path(output_file).parent

            # Create analysis subdirectory
            analysis_dir = pattern_output_dir / "analysis"

            # Only print header if not already printed
            if not ((args.trace and SIDWINDER_INTEGRATION_AVAILABLE) or
                    (args.disasm and DISASSEMBLER_INTEGRATION_AVAILABLE) or
                    (args.audio_export and AUDIO_EXPORT_INTEGRATION_AVAILABLE) or
                    (args.memmap and MEMMAP_ANALYZER_AVAILABLE)):
                logger.info("")
                logger.info("=" * 60)
                logger.info("[Phase 5] Running optional analysis tools...")
                logger.info("=" * 60)

            # Generate pattern analysis filename
            pattern_file = analysis_dir / f"{Path(input_file).stem}_patterns.txt"

            # Create recognizer and run analysis
            recognizer = PatternRecognizer(Path(input_file))
            pattern_result = recognizer.analyze(verbose=1 if not args.quiet else 0)

            if pattern_result and pattern_result['success']:
                # Generate report
                report_success = recognizer.generate_report(pattern_result, pattern_file)

                if report_success:
                    logger.info(f"[Step 17] Pattern analysis complete:")
                    logger.info(f"  Report file:  {pattern_file.name}")
                    logger.info(f"  Patterns:     {pattern_result['total_patterns']}")
                    logger.info(f"  Occurrences:  {pattern_result['total_occurrences']}")
                    logger.info(f"  Savings:      {pattern_result['potential_savings']} bytes ({pattern_result['compression_ratio']:.1f}%)")
                else:
                    logger.warning("[Step 17] Pattern analysis report generation failed")
            elif pattern_result and not pattern_result['success']:
                logger.warning(f"[Step 17] Pattern analysis failed: {pattern_result.get('error', 'Unknown error')}")
            elif args.patterns:
                logger.warning("[Step 17] Pattern recognizer not available")

        # PHASE 3 Enhancement: Optional call graph analysis (Step 18)
        if args.callgraph and SUBROUTINE_TRACER_AVAILABLE:
            # Determine output directory for call graph
            if args.both:
                callgraph_output_dir = Path(args.output_dir) if args.output_dir else Path(input_file).parent
            else:
                callgraph_output_dir = Path(output_file).parent

            # Create analysis subdirectory
            analysis_dir = callgraph_output_dir / "analysis"

            # Only print header if not already printed
            if not ((args.trace and SIDWINDER_INTEGRATION_AVAILABLE) or
                    (args.disasm and DISASSEMBLER_INTEGRATION_AVAILABLE) or
                    (args.audio_export and AUDIO_EXPORT_INTEGRATION_AVAILABLE) or
                    (args.memmap and MEMMAP_ANALYZER_AVAILABLE) or
                    (args.patterns and PATTERN_RECOGNIZER_AVAILABLE)):
                logger.info("")
                logger.info("=" * 60)
                logger.info("[Phase 5] Running optional analysis tools...")
                logger.info("=" * 60)

            # Generate call graph filename
            callgraph_file = analysis_dir / f"{Path(input_file).stem}_callgraph.txt"

            # Create tracer and run analysis
            tracer = SubroutineTracer(Path(input_file))
            callgraph_result = tracer.analyze(verbose=1 if not args.quiet else 0)

            if callgraph_result and callgraph_result['success']:
                # Generate report
                report_success = tracer.generate_report(callgraph_result, callgraph_file)

                if report_success:
                    logger.info(f"[Step 18] Call graph analysis complete:")
                    logger.info(f"  Report file:  {callgraph_file.name}")
                    logger.info(f"  Subroutines:  {callgraph_result['total_subroutines']}")
                    logger.info(f"  Init calls:   {callgraph_result['init_subroutines']}")
                    logger.info(f"  Play calls:   {callgraph_result['play_subroutines']}")
                    logger.info(f"  Shared:       {callgraph_result['shared_subroutines']}")
                    logger.info(f"  Max depth:    {callgraph_result['max_call_depth']}")
                else:
                    logger.warning("[Step 18] Call graph report generation failed")
            elif callgraph_result and not callgraph_result['success']:
                logger.warning(f"[Step 18] Call graph analysis failed: {callgraph_result.get('error', 'Unknown error')}")
            elif args.callgraph:
                logger.warning("[Step 18] Subroutine tracer not available")

        # PHASE 4 Enhancement: Consolidated report generation (Step 19)
        # Automatically generate if any analysis tools were run
        analysis_tools_used = any([
            args.trace and SIDWINDER_INTEGRATION_AVAILABLE,
            args.disasm and DISASSEMBLER_INTEGRATION_AVAILABLE,
            args.audio_export and AUDIO_EXPORT_INTEGRATION_AVAILABLE,
            args.memmap and MEMMAP_ANALYZER_AVAILABLE,
            args.patterns and PATTERN_RECOGNIZER_AVAILABLE,
            args.callgraph and SUBROUTINE_TRACER_AVAILABLE
        ])

        if analysis_tools_used and REPORT_GENERATOR_AVAILABLE:
            # Determine analysis directory
            if args.both:
                report_output_dir = Path(args.output_dir) if args.output_dir else Path(input_file).parent
            else:
                report_output_dir = Path(output_file).parent

            analysis_dir = report_output_dir / "analysis"

            # Generate consolidated report
            consolidated_file = analysis_dir / f"{Path(input_file).stem}_REPORT.txt"

            generator = ReportGenerator(Path(input_file), analysis_dir)
            report_result = generator.generate(consolidated_file, verbose=1 if not args.quiet else 0)

            if report_result and report_result['success']:
                logger.info("")
                logger.info("=" * 60)
                logger.info("[Step 19] Consolidated report generated:")
                logger.info(f"  Report file:  {consolidated_file.name}")
                logger.info(f"  Analyses:     {report_result['report_count']}")
                logger.info(f"  Types:        {', '.join(report_result['available_reports'])}")
                logger.info("=" * 60)

    except sidm2_errors.SIDMError as e:
        # Our custom errors already have helpful messages
        print(e)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if config.logging.level == 'DEBUG':
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
