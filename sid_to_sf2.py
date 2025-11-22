#!/usr/bin/env python3
"""
SID to SID Factory II (.sf2) Converter

This tool attempts to convert Commodore 64 .sid files into SID Factory II
project files. It's specifically designed for SID files using Laxity's player
routine, as used in the Unboxed_Ending_8580.sid file.

Note: This is a complex reverse-engineering task. Results may require manual
refinement in SID Factory II.
"""

__version__ = "0.5.0"
__build_date__ = "2025-11-22"

import logging
import os
import sys

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

# Also import laxity_parser for backward compatibility
from laxity_parser import LaxityParser

# Configure logging
logger = logging.getLogger(__name__)


def analyze_sid_file(filepath: str):
    """Analyze a SID file and print detailed information"""
    parser = SIDParser(filepath)
    header = parser.parse_header()
    c64_data, load_address = parser.get_c64_data(header)

    logger.info("=" * 60)
    logger.info("SID File Analysis")
    logger.info("=" * 60)
    logger.info(f"File: {filepath}")
    logger.info(f"Format: {header.magic} v{header.version}")
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

    # Analyze the data
    analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
    extracted = analyzer.extract_music_data()

    return extracted


def convert_sid_to_sf2(input_path: str, output_path: str, driver_type: str = 'np20'):
    """Convert a SID file to SF2 format

    Args:
        input_path: Path to input SID file
        output_path: Path for output SF2 file
        driver_type: 'driver11' for standard driver, 'np20' for NewPlayer 20
    """
    logger.info(f"Converting: {input_path}")
    logger.info(f"Output: {output_path}")
    logger.info(f"Driver: {driver_type}")

    # Analyze the SID file
    extracted = analyze_sid_file(input_path)

    # Try to extract actual data from siddump
    siddump_data = extract_from_siddump(input_path, playback_time=60)
    if siddump_data:
        extracted.siddump_data = siddump_data
        logger.info(f"  Siddump extraction: {len(siddump_data['adsr_values'])} ADSR values, "
              f"{len(siddump_data['waveforms'])} waveforms")
    else:
        extracted.siddump_data = None

    # Write the SF2 file
    writer = SF2Writer(extracted, driver_type=driver_type)
    writer.write(output_path)

    logger.info("Conversion complete!")
    logger.info("IMPORTANT NOTES:")
    logger.info("- This is an experimental converter")
    logger.info("- The output file may need manual editing in SID Factory II")
    logger.info("- Complex music data extraction is still in development")
    logger.info("- Consider this a starting point for further refinement")


def main():
    import argparse

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    parser = argparse.ArgumentParser(
        description='SID to SF2 Converter - Convert Laxity SID files to SID Factory II format'
    )
    parser.add_argument('input', help='Input SID file')
    parser.add_argument('output', nargs='?', help='Output SF2 file (default: input name with .sf2)')
    parser.add_argument(
        '--driver', '-d',
        choices=['np20', 'driver11'],
        default='np20',
        help='Target driver type (default: np20 - NewPlayer 20, similar to Laxity)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose (debug) output'
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    input_file = args.input
    if args.output:
        output_file = args.output
    else:
        # Generate output filename
        base = os.path.splitext(input_file)[0]
        output_file = base + ".sf2"

    if not os.path.exists(input_file):
        logger.error(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    convert_sid_to_sf2(input_file, output_file, driver_type=args.driver)


if __name__ == '__main__':
    main()
