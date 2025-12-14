#!/usr/bin/env python3
"""
Batch test Laxity driver on full SID collection.

Converts all .sid files using the custom Laxity driver and generates
comprehensive statistics and validation reports.

Usage:
    python scripts/batch_test_laxity_driver.py
    python scripts/batch_test_laxity_driver.py --input-dir SID --output-dir output
    python scripts/batch_test_laxity_driver.py --limit 10  # Test first 10 files
"""

import os
import sys
import argparse
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def convert_sid_to_laxity_sf2(sid_file: str, output_file: str) -> Tuple[bool, int, str]:
    """Convert a single SID file to SF2 using Laxity driver.

    Args:
        sid_file: Path to input SID file
        output_file: Path for output SF2 file

    Returns:
        Tuple of (success: bool, file_size: int, error_message: str)
    """
    try:
        result = subprocess.run(
            [sys.executable, 'scripts/sid_to_sf2.py', sid_file, output_file, '--driver', 'laxity'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            error_msg = result.stderr.split('\n')[0] if result.stderr else "Unknown error"
            return False, 0, error_msg

        # Check if output file was created
        if not os.path.exists(output_file):
            return False, 0, "Output file not created"

        file_size = os.path.getsize(output_file)
        return True, file_size, ""

    except subprocess.TimeoutExpired:
        return False, 0, "Conversion timeout (>30s)"
    except Exception as e:
        return False, 0, str(e)


def main():
    parser = argparse.ArgumentParser(
        description='Batch test Laxity driver on SID collection'
    )
    parser.add_argument(
        '--input-dir', '-i',
        default='Fun_Fun',
        help='Input directory containing SID files (default: Fun_Fun)'
    )
    parser.add_argument(
        '--output-dir', '-o',
        default='output/laxity_batch_test',
        help='Output directory for SF2 files (default: output/laxity_batch_test)'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=None,
        help='Limit number of files to test (default: all)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    # Setup directories
    input_dir = args.input_dir
    output_dir = args.output_dir

    if not os.path.exists(input_dir):
        logger.error(f"Input directory not found: {input_dir}")
        sys.exit(1)

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Find all SID files
    sid_files = sorted(Path(input_dir).glob('*.sid'))

    if args.limit:
        sid_files = sid_files[:args.limit]

    if not sid_files:
        logger.error(f"No SID files found in {input_dir}")
        sys.exit(1)

    logger.info(f"Found {len(sid_files)} SID files to convert")
    logger.info(f"Output directory: {output_dir}")
    logger.info("")

    # Batch conversion
    results = {
        'total': len(sid_files),
        'passed': 0,
        'failed': 0,
        'files': [],
        'start_time': datetime.now().isoformat(),
        'total_input_size': 0,
        'total_output_size': 0,
    }

    failed_files = []

    for idx, sid_file in enumerate(sid_files, 1):
        filename = sid_file.name
        base_name = sid_file.stem
        output_file = os.path.join(output_dir, f"{base_name}.sf2")

        input_size = os.path.getsize(sid_file)
        results['total_input_size'] += input_size

        # Convert
        success, output_size, error_msg = convert_sid_to_laxity_sf2(str(sid_file), output_file)

        # Record result
        file_result = {
            'filename': filename,
            'success': success,
            'input_size': input_size,
            'output_size': output_size if success else 0,
            'error': error_msg if not success else None,
        }
        results['files'].append(file_result)

        if success:
            results['passed'] += 1
            results['total_output_size'] += output_size
            status = "[OK] PASS"
            size_info = f"{output_size:,} bytes"
        else:
            results['failed'] += 1
            failed_files.append((filename, error_msg))
            status = "[FAIL]"
            size_info = error_msg

        # Print progress
        pct = (idx / len(sid_files)) * 100
        print(f"[{idx:3d}/{len(sid_files)}] {pct:5.1f}% {status} {filename:40s} -> {size_info}")

        if args.verbose and not success:
            print(f"  Error: {error_msg}")

    results['end_time'] = datetime.now().isoformat()

    # Summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("BATCH CONVERSION SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total files:      {results['total']}")
    logger.info(f"Passed:           {results['passed']} ({results['passed']/results['total']*100:.1f}%)")
    logger.info(f"Failed:           {results['failed']} ({results['failed']/results['total']*100:.1f}%)")
    logger.info(f"Total input:      {results['total_input_size']:,} bytes")
    logger.info(f"Total output:     {results['total_output_size']:,} bytes")

    if results['passed'] > 0:
        avg_size = results['total_output_size'] / results['passed']
        logger.info(f"Average SF2 size: {avg_size:,.0f} bytes")

    if failed_files:
        logger.info("")
        logger.info("Failed files:")
        for filename, error in failed_files:
            logger.info(f"  - {filename}: {error}")

    # Save detailed results
    results_file = os.path.join(output_dir, 'batch_test_results.json')
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to: {results_file}")

    # Generate report
    report_file = os.path.join(output_dir, 'batch_test_report.txt')
    with open(report_file, 'w') as f:
        f.write("LAXITY DRIVER BATCH TEST REPORT\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Test Date: {datetime.now().isoformat()}\n")
        f.write(f"Total Files: {results['total']}\n")
        f.write(f"Passed: {results['passed']} ({results['passed']/results['total']*100:.1f}%)\n")
        f.write(f"Failed: {results['failed']} ({results['failed']/results['total']*100:.1f}%)\n\n")

        f.write("STATISTICS\n")
        f.write("-" * 70 + "\n")
        f.write(f"Total Input Size:  {results['total_input_size']:,} bytes\n")
        f.write(f"Total Output Size: {results['total_output_size']:,} bytes\n")
        if results['passed'] > 0:
            f.write(f"Average SF2 Size:  {results['total_output_size']/results['passed']:,.0f} bytes\n")
        f.write("\n")

        f.write("DETAILED RESULTS\n")
        f.write("-" * 70 + "\n")
        for file_result in results['files']:
            status = "[OK]" if file_result['success'] else "[FAIL]"
            f.write(f"{status} {file_result['filename']:40s} {file_result['input_size']:8,d} -> ")
            if file_result['success']:
                f.write(f"{file_result['output_size']:8,d}\n")
            else:
                f.write(f"ERROR: {file_result['error']}\n")

        if failed_files:
            f.write("\nFAILED FILES\n")
            f.write("-" * 70 + "\n")
            for filename, error in failed_files:
                f.write(f"{filename}: {error}\n")

    logger.info(f"Report saved to: {report_file}")
    logger.info("")

    # Exit code
    if results['failed'] == 0:
        logger.info("[OK] All files converted successfully!")
        sys.exit(0)
    else:
        logger.warning(f"[FAIL] {results['failed']} file(s) failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
