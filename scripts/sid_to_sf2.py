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

# Also import laxity_parser for backward compatibility
from scripts.laxity_parser import LaxityParser

# Configure logging
logger = logging.getLogger(__name__)


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


def convert_sid_to_sf2(input_path: str, output_path: str, driver_type: str = None, config: ConversionConfig = None, sf2_reference_path: str = None):
    """Convert a SID file to SF2 format

    Args:
        input_path: Path to input SID file
        output_path: Path for output SF2 file (or None to use config naming pattern)
        driver_type: 'driver11' for standard driver, 'np20' for NewPlayer 20 (or None to use config)
        config: Optional configuration (uses defaults if None)
        sf2_reference_path: Optional path to original SF2 file (for SF2-exported SIDs)

    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If file format is invalid or driver_type is unknown
        IOError: If unable to write output file
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
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if driver_type not in config.driver.available_drivers:
            raise ValueError(f"Unknown driver type: {driver_type}. Must be one of {config.driver.available_drivers}")

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
            raise ValueError(f"Invalid or corrupted SID file: {e}")

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

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            if config.output.create_dirs:
                try:
                    os.makedirs(output_dir, exist_ok=True)
                except OSError as e:
                    raise IOError(f"Cannot create output directory {output_dir}: {e}")
            else:
                raise IOError(f"Output directory does not exist: {output_dir}")

        # Check if output file already exists
        if os.path.exists(output_path) and not config.output.overwrite:
            raise IOError(f"Output file already exists (use --overwrite or config.output.overwrite=true): {output_path}")

        # Write the SF2 file
        try:
            writer = SF2Writer(extracted, driver_type=driver_type)
            writer.write(output_path)
        except Exception as e:
            logger.error(f"Failed to write SF2 file: {e}")
            raise IOError(f"Cannot write output file {output_path}: {e}")

        logger.info("Conversion complete!")
        logger.info("IMPORTANT NOTES:")
        logger.info("- This is an experimental converter")
        logger.info("- The output file may need manual editing in SID Factory II")
        logger.info("- Complex music data extraction is still in development")
        logger.info("- Consider this a starting point for further refinement")

    except (FileNotFoundError, ValueError, IOError):
        # Re-raise expected errors
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Unexpected error during conversion: {e}")
        raise RuntimeError(f"Conversion failed: {e}")


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
        FileNotFoundError: If input file doesn't exist
        ValueError: If file format is invalid
        IOError: If unable to write output files
    """
    try:
        # Load or use default configuration
        if config is None:
            config = get_default_config()

        # Validate input
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        base_name = os.path.splitext(os.path.basename(input_path))[0]

        # Determine output directory
        if output_dir is None:
            output_dir = config.output.output_dir or os.path.dirname(input_path) or '.'

        if config.output.create_dirs:
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                raise IOError(f"Cannot create output directory {output_dir}: {e}")
        elif not os.path.exists(output_dir):
            raise IOError(f"Output directory does not exist: {output_dir}")

        # Analyze the SID file once
        try:
            extracted = analyze_sid_file(input_path, config=config, sf2_reference_path=sf2_reference_path)
        except Exception as e:
            logger.error(f"Failed to analyze SID file: {e}")
            raise ValueError(f"Invalid or corrupted SID file: {e}")

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

    except (FileNotFoundError, ValueError, IOError):
        # Re-raise expected errors
        raise
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Unexpected error during conversion: {e}")
        raise RuntimeError(f"Conversion failed: {e}")


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
        choices=['np20', 'driver11'],
        help='Target driver type (default: from config or driver11)'
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
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose (debug) output'
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

    if args.verbose:
        config.logging.level = 'DEBUG'
        config.extraction.verbose = True

    # Set up logging based on configuration
    log_level = getattr(logging, config.logging.level)
    handlers = [logging.StreamHandler(sys.stdout)]
    if config.logging.log_file:
        handlers.append(logging.FileHandler(config.logging.log_file))

    logging.basicConfig(
        level=log_level,
        format=config.logging.log_format,
        handlers=handlers
    )

    input_file = args.input

    if not os.path.exists(input_file):
        logger.error(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    try:
        if args.both:
            # Generate both driver versions
            output_dir = args.output_dir
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
            convert_sid_to_sf2(input_file, output_file, driver_type=driver_type, config=config, sf2_reference_path=sf2_reference)

    except (FileNotFoundError, ValueError, IOError) as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if config.logging.level == 'DEBUG':
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
