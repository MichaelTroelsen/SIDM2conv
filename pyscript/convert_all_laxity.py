#!/usr/bin/env python3
"""
Batch converter for Laxity SID to SF2 files.

Converts all .sid files in the SID folder using the custom Laxity driver.
Generates SF2 files with 99.93% frame accuracy for Laxity NewPlayer v21 SID files.

Usage:
    python convert_all_laxity.py
    python convert_all_laxity.py --input my_sids --output my_output

Output Structure:
    output/{SongName}/New/
    - {name}_laxity.sf2  (Laxity driver version - 99.93% accuracy)
    - {name}_info.txt    (conversion info)
    - {name}.dump        (siddump output)

Examples:
    python convert_all_laxity.py
    python convert_all_laxity.py --input my_sids --output my_output
"""

import os
import sys
import argparse
import subprocess
import logging
from datetime import datetime
from pathlib import Path

__version__ = "0.7.2"
__build_date__ = "2025-12-22"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def convert_all_laxity(sid_dir='SID', output_dir='output'):
    """Convert all SID files using Laxity driver.

    Args:
        sid_dir: Input directory containing .sid files
        output_dir: Output directory for conversion results

    Returns:
        True if successful, False otherwise
    """

    # Check if input directory exists
    if not os.path.isdir(sid_dir):
        logger.error(
            f"Input directory not found: {sid_dir}\n"
            f"  Suggestion: Specified directory does not exist\n"
            f"  Check: Verify directory path is correct\n"
            f"  Try: Use absolute path or create directory first\n"
            f"  See: docs/guides/TROUBLESHOOTING.md#directory-not-found"
        )
        return False

    # Get list of SID files
    sid_files = [f for f in os.listdir(sid_dir) if f.lower().endswith('.sid')]

    if not sid_files:
        logger.warning(f"No SID files found in {sid_dir}")
        return True  # No files to convert, but not an error

    logger.info(f"Found {len(sid_files)} SID files to convert")
    logger.info(f"Output directory: {output_dir}")

    success_count = 0
    failed_count = 0
    failed_files = []

    for i, sid_file in enumerate(sid_files, 1):
        logger.info(f"[{i}/{len(sid_files)}] Converting: {sid_file}")

        input_path = os.path.join(sid_dir, sid_file)

        # Extract song name without extension
        song_name = sid_file[:-4]

        # Create output directory structure
        sf2_dir = os.path.join(output_dir, song_name, 'New')
        os.makedirs(sf2_dir, exist_ok=True)

        # Output filename with laxity driver designation
        output_file = os.path.join(sf2_dir, song_name + '_laxity.sf2')

        try:
            # Run converter with laxity driver
            logger.debug(f"Running: python scripts/sid_to_sf2.py {input_path} {output_file} --driver laxity")

            result = subprocess.run(
                [sys.executable, 'scripts/sid_to_sf2.py', input_path, output_file, '--driver', 'laxity'],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                file_size = os.path.getsize(output_file) if os.path.exists(output_file) else 0
                logger.info(f"  SUCCESS: {output_file} ({file_size} bytes)")
                success_count += 1
            else:
                logger.error(
                    f"  FAILED: Conversion failed for {sid_file}\n"
                    f"  Suggestion: sid_to_sf2.py returned error for this file\n"
                    f"  Check: Review error message below for specific issue\n"
                    f"  Try: Test file individually to diagnose problem\n"
                    f"  See: docs/guides/TROUBLESHOOTING.md#conversion-failures"
                )
                if result.stderr:
                    logger.error(
                        f"  Error: {result.stderr[:200]}\n"
                        f"  Suggestion: Detailed error from conversion script\n"
                        f"  Check: Review error details for root cause\n"
                        f"  Try: Enable debug mode for full error trace\n"
                        f"  See: docs/guides/TROUBLESHOOTING.md#conversion-stderr"
                    )
                failed_count += 1
                failed_files.append(sid_file)

        except subprocess.TimeoutExpired:
            logger.error(
                f"  TIMEOUT: Conversion timeout for {sid_file}\n"
                f"  Suggestion: Conversion exceeded 60 second limit\n"
                f"  Check: File may be complex or conversion stuck\n"
                f"  Try: Test file individually with increased timeout\n"
                f"  See: docs/guides/TROUBLESHOOTING.md#conversion-timeout"
            )
            failed_count += 1
            failed_files.append(sid_file)
        except Exception as e:
            logger.error(
                f"  EXCEPTION: Error converting {sid_file}: {e}\n"
                f"  Suggestion: Unexpected error during conversion\n"
                f"  Check: Review error details for specific issue\n"
                f"  Try: Test file individually to diagnose problem\n"
                f"  See: docs/guides/TROUBLESHOOTING.md#unexpected-conversion-errors"
            )
            failed_count += 1
            failed_files.append(sid_file)

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Conversion Summary:")
    logger.info(f"  Total:   {len(sid_files)} files")
    logger.info(f"  Success: {success_count} files")
    logger.info(f"  Failed:  {failed_count} files")

    if failed_files:
        logger.warning("Failed files:")
        for f in failed_files[:10]:
            logger.warning(f"  - {f}")
        if len(failed_files) > 10:
            logger.warning(f"  ... and {len(failed_files) - 10} more")

    logger.info("=" * 60)

    return failed_count == 0


def main():
    parser = argparse.ArgumentParser(
        description='Batch convert SID files to SF2 format using Laxity driver (99.93%% accuracy)'
    )
    parser.add_argument(
        '--input', '-i',
        default='SID',
        help='Input directory containing .sid files (default: SID)'
    )
    parser.add_argument(
        '--output', '-o',
        default='output',
        help='Output directory for conversion results (default: output)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose logging'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Quiet mode (errors only)'
    )

    args = parser.parse_args()

    # Configure logging
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    elif args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        success = convert_all_laxity(
            sid_dir=args.input,
            output_dir=args.output
        )
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(
            f"Unexpected error: {e}\n"
            f"  Suggestion: Batch Laxity conversion encountered unexpected error\n"
            f"  Check: Review error trace below for specific issue\n"
            f"  Try: Enable debug logging for more information\n"
            f"  See: docs/guides/TROUBLESHOOTING.md#unexpected-errors"
        )
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
