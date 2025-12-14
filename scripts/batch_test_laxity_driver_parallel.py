#!/usr/bin/env python3
"""
Optimized batch test with parallel processing support.

Processes multiple SID files in parallel using multiprocessing for
significant performance improvements on multi-core systems.

Usage:
    # Sequential (original behavior)
    python scripts/batch_test_laxity_driver_parallel.py --sequential

    # Parallel (default, auto-detects CPU count)
    python scripts/batch_test_laxity_driver_parallel.py

    # Parallel with custom worker count
    python scripts/batch_test_laxity_driver_parallel.py --workers 4

    # Benchmark both methods
    python scripts/batch_test_laxity_driver_parallel.py --benchmark
"""

import os
import sys
import argparse
import subprocess
import logging
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from multiprocessing import Pool, cpu_count
from functools import partial

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


def convert_and_report(args: Tuple) -> Dict:
    """Worker function for parallel processing.

    Args:
        args: Tuple of (sid_file_path, output_file_path, index, total)

    Returns:
        Dictionary with conversion result
    """
    sid_file, output_file, index, total = args
    filename = os.path.basename(sid_file)
    input_size = os.path.getsize(sid_file)

    # Convert
    success, output_size, error_msg = convert_sid_to_laxity_sf2(sid_file, output_file)

    # Build result
    result = {
        'filename': filename,
        'success': success,
        'input_size': input_size,
        'output_size': output_size if success else 0,
        'error': error_msg if not success else None,
        'index': index,
        'total': total
    }

    return result


def process_sequential(sid_files: List[Path], output_dir: str, verbose: bool = False) -> Tuple[Dict, float]:
    """Process files sequentially (original implementation).

    Args:
        sid_files: List of SID file paths
        output_dir: Output directory for SF2 files
        verbose: Enable verbose output

    Returns:
        Tuple of (results_dict, elapsed_time)
    """
    start_time = time.time()

    results = {
        'total': len(sid_files),
        'passed': 0,
        'failed': 0,
        'files': [],
        'start_time': datetime.now().isoformat(),
        'total_input_size': 0,
        'total_output_size': 0,
        'processing_mode': 'sequential'
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
            status = "[OK]"
            size_info = f"{output_size:,} bytes"
        else:
            results['failed'] += 1
            failed_files.append((filename, error_msg))
            status = "[FAIL]"
            size_info = error_msg

        # Print progress
        pct = (idx / len(sid_files)) * 100
        print(f"[{idx:3d}/{len(sid_files)}] {pct:5.1f}% {status} {filename:40s} -> {size_info}")

        if verbose and not success:
            print(f"  Error: {error_msg}")

    results['end_time'] = datetime.now().isoformat()
    elapsed = time.time() - start_time

    return results, elapsed


def process_parallel(sid_files: List[Path], output_dir: str, workers: int, verbose: bool = False) -> Tuple[Dict, float]:
    """Process files in parallel using multiprocessing.

    Args:
        sid_files: List of SID file paths
        output_dir: Output directory for SF2 files
        workers: Number of worker processes
        verbose: Enable verbose output

    Returns:
        Tuple of (results_dict, elapsed_time)
    """
    start_time = time.time()

    results = {
        'total': len(sid_files),
        'passed': 0,
        'failed': 0,
        'files': [],
        'start_time': datetime.now().isoformat(),
        'total_input_size': 0,
        'total_output_size': 0,
        'processing_mode': f'parallel (workers={workers})'
    }

    failed_files = []

    # Prepare work queue
    work_items = []
    for idx, sid_file in enumerate(sid_files, 1):
        base_name = sid_file.stem
        output_file = os.path.join(output_dir, f"{base_name}.sf2")
        work_items.append((str(sid_file), output_file, idx, len(sid_files)))

    # Process in parallel
    with Pool(processes=workers) as pool:
        for result in pool.imap_unordered(convert_and_report, work_items):
            filename = result['filename']
            success = result['success']
            input_size = result['input_size']
            output_size = result['output_size']
            error_msg = result['error']
            index = result['index']
            total = result['total']

            results['total_input_size'] += input_size

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
                status = "[OK]"
                size_info = f"{output_size:,} bytes"
            else:
                results['failed'] += 1
                failed_files.append((filename, error_msg))
                status = "[FAIL]"
                size_info = error_msg

            # Print progress
            pct = (index / total) * 100
            print(f"[{index:3d}/{total}] {pct:5.1f}% {status} {filename:40s} -> {size_info}")

            if verbose and not success:
                print(f"  Error: {error_msg}")

    results['end_time'] = datetime.now().isoformat()
    elapsed = time.time() - start_time

    return results, elapsed


def benchmark_methods(sid_files: List[Path], output_dir: str) -> None:
    """Benchmark sequential vs parallel processing.

    Args:
        sid_files: List of SID file paths
        output_dir: Output directory for SF2 files
    """
    logger.info("=" * 70)
    logger.info("PERFORMANCE BENCHMARK")
    logger.info("=" * 70)

    # Sequential benchmark
    logger.info("\n[1/2] Running sequential benchmark...")
    logger.info(f"Processing {len(sid_files)} files sequentially...")
    seq_results, seq_time = process_sequential(sid_files, f"{output_dir}_seq", verbose=False)
    logger.info(f"Sequential time: {seq_time:.2f} seconds")
    logger.info(f"Speed: {len(sid_files) / seq_time:.2f} files/second")

    # Parallel benchmark
    workers = cpu_count()
    logger.info(f"\n[2/2] Running parallel benchmark ({workers} workers)...")
    logger.info(f"Processing {len(sid_files)} files in parallel...")
    par_results, par_time = process_parallel(sid_files, f"{output_dir}_par", workers, verbose=False)
    logger.info(f"Parallel time: {par_time:.2f} seconds")
    logger.info(f"Speed: {len(sid_files) / par_time:.2f} files/second")

    # Comparison
    logger.info("\n" + "=" * 70)
    logger.info("COMPARISON")
    logger.info("=" * 70)
    speedup = seq_time / par_time
    improvement = (1 - par_time / seq_time) * 100
    logger.info(f"Sequential:     {seq_time:.2f}s ({len(sid_files)/seq_time:.2f} files/sec)")
    logger.info(f"Parallel ({workers}):   {par_time:.2f}s ({len(sid_files)/par_time:.2f} files/sec)")
    logger.info(f"Speedup:        {speedup:.2f}x faster")
    logger.info(f"Time saved:     {improvement:.1f}%")
    logger.info(f"Saved:          {seq_time - par_time:.2f} seconds")
    logger.info("")


def main():
    parser = argparse.ArgumentParser(
        description='Optimized batch test with parallel processing support'
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
        '--workers', '-w',
        type=int,
        default=None,
        help='Number of parallel workers (default: CPU count)'
    )
    parser.add_argument(
        '--sequential', '-s',
        action='store_true',
        help='Use sequential processing (original behavior)'
    )
    parser.add_argument(
        '--benchmark', '-b',
        action='store_true',
        help='Benchmark both sequential and parallel methods'
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

    # Process files
    if args.benchmark:
        benchmark_methods(sid_files, output_dir)
        sys.exit(0)

    if args.sequential:
        logger.info("Using sequential processing")
        results, elapsed = process_sequential(sid_files, output_dir, args.verbose)
    else:
        workers = args.workers or cpu_count()
        logger.info(f"Using parallel processing ({workers} workers)")
        results, elapsed = process_parallel(sid_files, output_dir, workers, args.verbose)

    results['elapsed_seconds'] = elapsed
    results['processing_speed'] = len(sid_files) / elapsed

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

    logger.info(f"Processing mode:  {results['processing_mode']}")
    logger.info(f"Total time:       {elapsed:.2f} seconds")
    logger.info(f"Speed:            {results['processing_speed']:.2f} files/second")

    # Save detailed results
    results_file = os.path.join(output_dir, 'batch_test_results.json')
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to: {results_file}")

    # Generate report
    report_file = os.path.join(output_dir, 'batch_test_report.txt')
    with open(report_file, 'w') as f:
        f.write("LAXITY DRIVER BATCH TEST REPORT (OPTIMIZED)\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Test Date: {datetime.now().isoformat()}\n")
        f.write(f"Processing Mode: {results['processing_mode']}\n")
        f.write(f"Total Files: {results['total']}\n")
        f.write(f"Passed: {results['passed']} ({results['passed']/results['total']*100:.1f}%)\n")
        f.write(f"Failed: {results['failed']} ({results['failed']/results['total']*100:.1f}%)\n\n")

        f.write("PERFORMANCE METRICS\n")
        f.write("-" * 70 + "\n")
        f.write(f"Total Time:       {elapsed:.2f} seconds\n")
        f.write(f"Speed:            {results['processing_speed']:.2f} files/second\n")
        f.write(f"Total Input:      {results['total_input_size']:,} bytes\n")
        f.write(f"Total Output:     {results['total_output_size']:,} bytes\n")
        if results['passed'] > 0:
            f.write(f"Average SF2 Size: {results['total_output_size']/results['passed']:,.0f} bytes\n")
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
