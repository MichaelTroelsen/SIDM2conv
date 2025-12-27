#!/usr/bin/env python3
"""
Analyze Laxity SID files to find good test candidates.

Identifies files with:
- Filter usage
- 3-voice usage
- Diverse characteristics
"""

import sys
import os
from pathlib import Path
import subprocess
import re

import struct

sys.path.insert(0, str(Path(__file__).parent.parent))


def analyze_sid_file(sid_path):
    """Analyze a SID file for test characteristics."""
    result = {
        'file': sid_path.name,
        'size': sid_path.stat().st_size,
        'voices': set(),
        'filter_frames': 0,
        'total_frames': 0,
        'error': None
    }

    # Parse basic header info
    try:
        with open(sid_path, 'rb') as f:
            header_data = f.read(124)

        # Check magic
        magic = header_data[0:4].decode('ascii')
        if magic not in ('PSID', 'RSID'):
            result['error'] = f"Invalid magic: {magic}"
            return result

        # Get basic fields
        result['version'] = struct.unpack('>H', header_data[4:6])[0]
        result['load_address'] = struct.unpack('>H', header_data[8:10])[0]
    except Exception as e:
        result['error'] = f"Header parse error: {str(e)[:50]}"
        return result

    # Run siddump to analyze register usage
    try:
        cmd = [sys.executable, 'pyscript/siddump_complete.py', str(sid_path), '-t5']
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if proc.returncode != 0:
            result['error'] = "siddump failed"
            return result

        # Parse siddump output (table format with | separators)
        for line in proc.stdout.split('\n'):
            # Skip header and separator lines
            if not line.startswith('|') or '---' in line or 'Frame' in line:
                continue

            # Data line format: | Frame | Voice1 data | Voice2 data | Voice3 data | Filter data |
            parts = line.split('|')
            if len(parts) < 6:
                continue

            result['total_frames'] += 1

            # Check voice activity (columns 2, 3, 4)
            # Voice is active if frequency is not 0000 or ....
            for voice_num, voice_col in enumerate([2, 3, 4], 1):
                voice_data = parts[voice_col].strip()
                # Extract frequency (first 4 characters)
                if len(voice_data) >= 4:
                    freq = voice_data[:4].strip()
                    if freq and freq != '....' and freq != '0000':
                        result['voices'].add(voice_num)

            # Check filter activity (column 5)
            filter_data = parts[5].strip()
            # Filter format: "CCCC RR Typ V"
            # Extract cutoff (first 4 characters)
            if len(filter_data) >= 4:
                cutoff = filter_data[:4].strip()
                if cutoff and cutoff != '0000':
                    result['filter_frames'] += 1

    except subprocess.TimeoutExpired:
        result['error'] = "siddump timeout"
    except Exception as e:
        result['error'] = f"Analysis error: {e}"

    return result


def main():
    """Analyze all Laxity files and categorize them."""
    laxity_dir = Path('Laxity')

    if not laxity_dir.exists():
        print("Error: Laxity directory not found")
        return 1

    # Get all SID files
    sid_files = sorted(laxity_dir.glob('*.sid'))
    print(f"Analyzing {len(sid_files)} Laxity SID files...\n")

    # Categories
    filter_files = []
    three_voice_files = []
    two_voice_files = []
    one_voice_files = []
    large_files = []
    small_files = []
    errors = []

    # Analyze each file
    for i, sid_file in enumerate(sid_files, 1):
        if i % 50 == 0:
            print(f"Progress: {i}/{len(sid_files)}...")

        result = analyze_sid_file(sid_file)

        if result['error']:
            errors.append(result)
            continue

        # Categorize
        voice_count = len(result['voices'])

        if result['filter_frames'] > 0:
            filter_files.append(result)

        if voice_count == 3:
            three_voice_files.append(result)
        elif voice_count == 2:
            two_voice_files.append(result)
        elif voice_count == 1:
            one_voice_files.append(result)

        if result['size'] > 10000:
            large_files.append(result)
        elif result['size'] < 5000:
            small_files.append(result)

    # Print results
    print("\n" + "=" * 70)
    print("ANALYSIS RESULTS")
    print("=" * 70)

    print(f"\nTotal files analyzed: {len(sid_files)}")
    print(f"Errors: {len(errors)}")

    print(f"\n--- Voice Usage ---")
    print(f"3-voice files: {len(three_voice_files)}")
    print(f"2-voice files: {len(two_voice_files)}")
    print(f"1-voice files: {len(one_voice_files)}")

    print(f"\n--- Filter Usage ---")
    print(f"Files with filter: {len(filter_files)}")

    print(f"\n--- File Size ---")
    print(f"Large files (>10KB): {len(large_files)}")
    print(f"Small files (<5KB): {len(small_files)}")

    # Print top candidates
    print("\n" + "=" * 70)
    print("TOP CANDIDATES FOR TEST SUITE")
    print("=" * 70)

    print("\n--- 3-Voice Files (Top 10) ---")
    for result in sorted(three_voice_files, key=lambda x: x['filter_frames'], reverse=True)[:10]:
        filter_pct = (result['filter_frames'] / max(result['total_frames'], 1)) * 100
        print(f"  {result['file']:40s} - Voices: {sorted(result['voices'])}, "
              f"Filter: {filter_pct:.1f}%, Size: {result['size']:,} bytes")

    print("\n--- Files with Heavy Filter Usage (Top 10) ---")
    for result in sorted(filter_files, key=lambda x: x['filter_frames'], reverse=True)[:10]:
        filter_pct = (result['filter_frames'] / max(result['total_frames'], 1)) * 100
        print(f"  {result['file']:40s} - Filter: {filter_pct:.1f}% ({result['filter_frames']} frames), "
              f"Voices: {sorted(result['voices'])}")

    print("\n--- Large Complex Files (Top 5) ---")
    for result in sorted(large_files, key=lambda x: x['size'], reverse=True)[:5]:
        voice_count = len(result['voices'])
        print(f"  {result['file']:40s} - Size: {result['size']:,} bytes, "
              f"Voices: {voice_count}, Filter: {result['filter_frames']} frames")

    print("\n--- Small Simple Files (Top 5) ---")
    for result in sorted(small_files, key=lambda x: x['size'])[:5]:
        voice_count = len(result['voices'])
        print(f"  {result['file']:40s} - Size: {result['size']:,} bytes, "
              f"Voices: {voice_count}, Filter: {result['filter_frames']} frames")

    if errors:
        print(f"\n--- Errors ({len(errors)}) ---")
        for result in errors[:5]:
            print(f"  {result['file']:40s} - {result['error']}")

    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
