#!/usr/bin/env python3
"""
Parallel Galway Pipeline - Process all 40 Martin Galway files with full validation in parallel.

Runs the complete 11-step pipeline on multiple files simultaneously for fast batch processing.
With 4 parallel workers and ~1 min per file, processes 40 files in ~10 minutes.

Usage:
    python parallel_galway_pipeline.py              # All 40 files, 4 workers
    python parallel_galway_pipeline.py --workers 2  # All 40 files, 2 workers
    python parallel_galway_pipeline.py --files 5    # First 5 files, 4 workers
    python parallel_galway_pipeline.py --skip-wav   # Skip WAV rendering (faster)
"""

import os
import sys
import subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import argparse
from datetime import datetime


def run_pipeline_for_file(sid_path, skip_wav=False, skip_midi=False):
    """
    Run the complete pipeline for a single SID file.

    Args:
        sid_path: Path to input SID file
        skip_wav: If True, skip WAV rendering
        skip_midi: If True, skip MIDI comparison

    Returns:
        tuple: (sid_filename, success, error_message)
    """
    sid_path = Path(sid_path)
    filename = sid_path.stem

    try:
        # Build command
        cmd = [
            sys.executable,
            'complete_pipeline_with_validation.py',
            str(sid_path)
        ]

        # Add skip flags if requested
        if skip_wav:
            cmd.append('--skip-wav')
        if skip_midi:
            cmd.append('--skip-midi')

        # Run pipeline
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
            cwd=os.getcwd()
        )

        success = result.returncode == 0
        error = result.stderr if result.returncode != 0 else ""

        return (filename, success, error)

    except subprocess.TimeoutExpired:
        return (filename, False, "Timeout after 10 minutes")
    except Exception as e:
        return (filename, False, str(e))


def main():
    parser = argparse.ArgumentParser(
        description='Run Galway pipeline on all files in parallel'
    )
    parser.add_argument(
        '--workers', type=int, default=4,
        help='Number of parallel workers (default: 4)'
    )
    parser.add_argument(
        '--files', type=int, default=None,
        help='Process only first N files (for testing)'
    )
    parser.add_argument(
        '--skip-wav', action='store_true',
        help='Skip WAV rendering (faster)'
    )
    parser.add_argument(
        '--skip-midi', action='store_true',
        help='Skip MIDI comparison (faster)'
    )

    args = parser.parse_args()

    # Find all Galway files
    galway_dir = Path('Galway_Martin')
    if not galway_dir.exists():
        print(f"Error: {galway_dir} directory not found")
        sys.exit(1)

    sid_files = sorted(galway_dir.glob('*.sid'))

    if not sid_files:
        print(f"Error: No SID files found in {galway_dir}")
        sys.exit(1)

    # Limit files if specified
    if args.files:
        sid_files = sid_files[:args.files]

    print(f"Starting parallel Galway pipeline")
    print(f"  Files: {len(sid_files)}")
    print(f"  Workers: {args.workers}")
    print(f"  Start time: {datetime.now().strftime('%H:%M:%S')}")
    print()

    # Process in parallel
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(run_pipeline_for_file, sid_file, args.skip_wav, args.skip_midi): sid_file
            for sid_file in sid_files
        }

        # Process as they complete
        completed = 0
        for future in as_completed(futures):
            completed += 1
            filename, success, error = future.result()
            results.append((filename, success, error))

            status = "[OK]" if success else "[FAIL]"
            print(f"[{completed:2d}/{len(sid_files)}] {status} {filename}")
            if error and not success:
                print(f"       Error: {error[:80]}")

    print()
    print("=" * 70)
    print(f"Parallel pipeline complete - {datetime.now().strftime('%H:%M:%S')}")
    print()

    # Summary
    successful = sum(1 for _, success, _ in results if success)
    failed = len(results) - successful

    print(f"Results Summary:")
    print(f"  Successful: {successful}/{len(results)}")
    print(f"  Failed: {failed}/{len(results)}")
    print(f"  Success rate: {100*successful/len(results):.1f}%")
    print()

    if failed > 0:
        print("Failed files:")
        for filename, success, error in results:
            if not success:
                print(f"  - {filename}: {error[:60]}")
        print()

    # Check output directories
    print("Output verification:")
    output_ok = 0
    for filename, success, _ in results:
        if success:
            output_dir = Path('output') / filename / 'New'
            if output_dir.exists():
                files = list(output_dir.glob('*'))
                output_ok += 1
                print(f"  [OK] {filename}: {len(files)} files generated")

    print()
    print(f"Pipeline outputs ready: {output_ok}/{successful} files")

    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
