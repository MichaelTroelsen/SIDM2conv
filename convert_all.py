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
import re


def run_player_id(sid_path):
    """Run player-id.exe on a SID file and return the detected player."""
    player_id_exe = os.path.join('tools', 'player-id.exe')

    if not os.path.exists(player_id_exe):
        return "player-id.exe not found"

    try:
        result = subprocess.run(
            [player_id_exe, sid_path],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Parse output to find player name
        for line in result.stdout.split('\n'):
            if sid_path in line or os.path.basename(sid_path) in line:
                # Line format: "filename    PlayerName"
                parts = line.strip().split()
                if len(parts) >= 2:
                    return parts[-1]

        return "Unknown"
    except Exception as e:
        return f"Error: {str(e)}"


def generate_info_file(sf2_dir, sid_file, output_file, converter_output, player_name,
                       sequences, instruments, orderlists, file_size, driver_type):
    """Generate an info text file for a converted SID."""
    info_file = os.path.join(sf2_dir, sid_file[:-4] + '_info.txt')

    # Extract more details from converter output
    sid_name = ""
    sid_author = ""
    sid_copyright = ""
    load_addr = ""
    init_addr = ""
    play_addr = ""
    data_size = ""
    tempo = ""
    instrument_names = []

    for line in converter_output.split('\n'):
        if line.startswith('Name:'):
            sid_name = line.split(':', 1)[1].strip()
        elif line.startswith('Author:'):
            sid_author = line.split(':', 1)[1].strip()
        elif line.startswith('Copyright:'):
            sid_copyright = line.split(':', 1)[1].strip()
        elif 'Load address:' in line:
            load_addr = line.split(':', 1)[1].strip()
        elif 'Init address:' in line:
            init_addr = line.split(':', 1)[1].strip()
        elif 'Play address:' in line:
            play_addr = line.split(':', 1)[1].strip()
        elif 'Data size:' in line:
            data_size = line.split(':', 1)[1].strip()
        elif 'Tempo:' in line:
            tempo = line.split(':', 1)[1].strip()
        elif re.match(r'\s+\d+:', line) and '(AD=' in line:
            # Instrument line like "      0: 00 Lead Saw (AD=07 SR=B9)"
            instrument_names.append(line.strip())

    # Write info file
    with open(info_file, 'w', encoding='utf-8') as f:
        f.write(f"SID to SF2 Conversion Info\n")
        f.write(f"=" * 50 + "\n\n")

        f.write(f"Source File\n")
        f.write(f"-" * 50 + "\n")
        f.write(f"Filename:      {sid_file}\n")
        f.write(f"Name:          {sid_name}\n")
        f.write(f"Author:        {sid_author}\n")
        f.write(f"Copyright:     {sid_copyright}\n")
        f.write(f"Player:        {player_name}\n")
        f.write(f"\n")

        f.write(f"Memory Layout\n")
        f.write(f"-" * 50 + "\n")
        f.write(f"Load address:  {load_addr}\n")
        f.write(f"Init address:  {init_addr}\n")
        f.write(f"Play address:  {play_addr}\n")
        f.write(f"Data size:     {data_size}\n")
        f.write(f"\n")

        f.write(f"Conversion Result\n")
        f.write(f"-" * 50 + "\n")
        f.write(f"Output file:   {output_file}\n")
        f.write(f"File size:     {file_size:,} bytes\n")
        f.write(f"Driver:        {driver_type}\n")
        f.write(f"Tempo:         {tempo}\n")
        f.write(f"Sequences:     {sequences}\n")
        f.write(f"Instruments:   {instruments}\n")
        f.write(f"Orderlists:    {orderlists}\n")
        f.write(f"\n")

        if instrument_names:
            f.write(f"Instrument List\n")
            f.write(f"-" * 50 + "\n")
            for instr in instrument_names:
                f.write(f"{instr}\n")
            f.write(f"\n")

        f.write(f"Generated:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    return info_file


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

        # Run player-id.exe first
        player_name = run_player_id(input_path)
        print(f"       Player: {player_name}")

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
            orderlists = 3
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
                elif 'Created' in line and 'orderlists' in line:
                    try:
                        orderlists = int(line.split()[1])
                    except (ValueError, IndexError):
                        pass

            # Generate info file
            info_file = generate_info_file(
                sf2_dir, sid_file, output_file, result.stdout,
                player_name, sequences, instruments, orderlists, size, driver_type
            )

            print(f"       -> {output_file} ({size:,} bytes, {sequences} seq, {instruments} instr)")
            print(f"       -> {os.path.basename(info_file)}")
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
