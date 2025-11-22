#!/usr/bin/env python3
"""
Batch converter for SID to SF2 files.

Converts all .sid files in the SID folder to .sf2 files in the SF2 folder.

Usage:
    python convert_all.py [--driver {np20,driver11}]

Examples:
    python convert_all.py
    python convert_all.py --driver driver11
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime


def convert_all(driver_type='np20', sid_dir='SID', sf2_dir='SF2'):
    """Convert all SID files in sid_dir to SF2 files in sf2_dir."""

    # Check if SID directory exists
    if not os.path.exists(sid_dir):
        print(f"Error: SID directory '{sid_dir}' not found")
        sys.exit(1)

    # Create SF2 directory if it doesn't exist
    if not os.path.exists(sf2_dir):
        os.makedirs(sf2_dir)
        print(f"Created output directory: {sf2_dir}")

    # Get list of SID files
    sid_files = [f for f in os.listdir(sid_dir) if f.lower().endswith('.sid')]

    if not sid_files:
        print(f"No .sid files found in '{sid_dir}'")
        sys.exit(1)

    print(f"SID to SF2 Batch Converter")
    print(f"=" * 50)
    print(f"Input directory:  {sid_dir}")
    print(f"Output directory: {sf2_dir}")
    print(f"Driver type:      {driver_type}")
    print(f"Files to convert: {len(sid_files)}")
    print(f"=" * 50)
    print()

    # Track results
    success_count = 0
    failed_files = []

    start_time = datetime.now()

    # Convert each file
    for i, sid_file in enumerate(sorted(sid_files), 1):
        input_path = os.path.join(sid_dir, sid_file)
        output_file = sid_file[:-4] + '.sf2'  # Replace .sid with .sf2
        output_path = os.path.join(sf2_dir, output_file)

        print(f"[{i}/{len(sid_files)}] Converting {sid_file}...")

        # Run converter
        result = subprocess.run(
            [sys.executable, 'sid_to_sf2.py', input_path, output_path, '--driver', driver_type],
            capture_output=True,
            text=True
        )

        # Check result
        if result.returncode == 0 and os.path.exists(output_path):
            size = os.path.getsize(output_path)

            # Extract key info from output
            sequences = 0
            instruments = 0
            for line in result.stdout.split('\n'):
                if 'Extracted' in line and 'sequences' in line:
                    try:
                        sequences = int(line.split()[1])
                    except (ValueError, IndexError):
                        pass
                elif 'Extracted' in line and 'instruments' in line:
                    try:
                        instruments = int(line.split()[1])
                    except (ValueError, IndexError):
                        pass

            print(f"       -> {output_file} ({size:,} bytes, {sequences} seq, {instruments} instr)")
            success_count += 1
        else:
            print(f"       -> FAILED")
            if result.stderr:
                print(f"          Error: {result.stderr.strip()[:100]}")
            failed_files.append(sid_file)

    # Print summary
    elapsed = datetime.now() - start_time

    print()
    print(f"=" * 50)
    print(f"Conversion Complete")
    print(f"=" * 50)
    print(f"Successful: {success_count}/{len(sid_files)}")
    print(f"Failed:     {len(failed_files)}")
    print(f"Time:       {elapsed.total_seconds():.1f} seconds")

    if failed_files:
        print()
        print("Failed files:")
        for f in failed_files:
            print(f"  - {f}")

    print()
    print(f"Output files are in: {os.path.abspath(sf2_dir)}")

    return len(failed_files) == 0


def main():
    parser = argparse.ArgumentParser(
        description='Batch convert SID files to SF2 format'
    )
    parser.add_argument(
        '--driver', '-d',
        choices=['np20', 'driver11'],
        default='np20',
        help='Target driver type (default: np20)'
    )
    parser.add_argument(
        '--input', '-i',
        default='SID',
        help='Input directory containing .sid files (default: SID)'
    )
    parser.add_argument(
        '--output', '-o',
        default='SF2',
        help='Output directory for .sf2 files (default: SF2)'
    )

    args = parser.parse_args()

    success = convert_all(
        driver_type=args.driver,
        sid_dir=args.input,
        sf2_dir=args.output
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
