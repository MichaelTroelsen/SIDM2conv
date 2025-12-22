#!/usr/bin/env python3
"""
Check which voices are used in Laxity SID files by analyzing orderlist data.

This script parses Laxity files and checks which voices have non-empty orderlists.
A voice is considered "used" if its orderlist contains at least one sequence.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.laxity_parser import LaxityParser
from sidm2.sid_parser import SIDParser


def check_voice_usage(sid_file: Path) -> dict:
    """
    Check which voices are used in a Laxity SID file.

    Args:
        sid_file: Path to Laxity SID file

    Returns:
        dict with voice usage info:
        - voices_used: list of voice indices (0, 1, 2)
        - orderlist_lengths: list of orderlist lengths for each voice
        - error: error message if parsing failed
    """
    result = {
        'voices_used': [],
        'orderlist_lengths': [0, 0, 0],
        'error': None
    }

    try:
        # Parse SID header and get C64 data
        sid_parser = SIDParser(str(sid_file))
        header = sid_parser.parse_header()
        c64_data, load_address = sid_parser.get_c64_data(header)

        # Parse Laxity data
        parser = LaxityParser(c64_data, load_address)
        laxity_data = parser.parse()

        # Check orderlist for each voice
        for voice_idx in range(3):
            orderlist_len = len(laxity_data.orderlists[voice_idx])
            result['orderlist_lengths'][voice_idx] = orderlist_len

            if orderlist_len > 0:
                result['voices_used'].append(voice_idx)

    except Exception as e:
        result['error'] = str(e)[:100]

    return result


def analyze_laxity_collection(laxity_dir: Path, sample_size: int = None):
    """
    Analyze voice usage in Laxity collection.

    Args:
        laxity_dir: Path to Laxity directory
        sample_size: Number of files to sample (None = all)
    """
    print(f"Analyzing Laxity collection: {laxity_dir}")
    print(f"Checking orderlist data to determine voice usage...\n")

    # Get all .sid files
    sid_files = sorted(laxity_dir.glob("*.sid"))
    total = len(sid_files)
    print(f"Found {total} Laxity SID files")

    # Sample if requested
    if sample_size and total > sample_size:
        step = total // sample_size
        sid_files = sid_files[::step][:sample_size]
        print(f"Sampling {len(sid_files)} files evenly\n")
    else:
        print(f"Analyzing all {len(sid_files)} files\n")

    # Statistics
    voice_usage_stats = {
        '1 voice': 0,
        '2 voices': 0,
        '3 voices': 0,
        'errors': 0
    }

    voice_count_distribution = {}  # voice pattern -> count
    three_voice_files = []  # Files using all 3 voices
    errors = []

    # Analyze files
    for i, sid_file in enumerate(sid_files, 1):
        print(f"[{i}/{len(sid_files)}] {sid_file.name:50s} ", end='')
        sys.stdout.flush()

        result = check_voice_usage(sid_file)

        if result['error']:
            print(f"[ERROR] {result['error']}")
            errors.append((sid_file.name, result['error']))
            voice_usage_stats['errors'] += 1
        else:
            num_voices = len(result['voices_used'])
            voice_pattern = ''.join(str(v+1) for v in result['voices_used'])

            # Count distribution
            if voice_pattern not in voice_count_distribution:
                voice_count_distribution[voice_pattern] = []
            voice_count_distribution[voice_pattern].append(sid_file.name)

            # Update stats
            if num_voices == 1:
                voice_usage_stats['1 voice'] += 1
                print(f"[Voice {voice_pattern}] ({result['orderlist_lengths']})")
            elif num_voices == 2:
                voice_usage_stats['2 voices'] += 1
                print(f"[Voices {voice_pattern}] ({result['orderlist_lengths']})")
            elif num_voices == 3:
                voice_usage_stats['3 voices'] += 1
                three_voice_files.append((sid_file.name, result['orderlist_lengths']))
                print(f"[Voices 123] ({result['orderlist_lengths']}) [OK]")

    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total analyzed: {len(sid_files)}")
    print(f"1 voice:        {voice_usage_stats['1 voice']} ({100*voice_usage_stats['1 voice']/len(sid_files):.1f}%)")
    print(f"2 voices:       {voice_usage_stats['2 voices']} ({100*voice_usage_stats['2 voices']/len(sid_files):.1f}%)")
    print(f"3 voices:       {voice_usage_stats['3 voices']} ({100*voice_usage_stats['3 voices']/len(sid_files):.1f}%)")
    print(f"Errors:         {voice_usage_stats['errors']}")

    print("\n" + "="*80)
    print("VOICE PATTERN DISTRIBUTION")
    print("="*80)
    for pattern in sorted(voice_count_distribution.keys()):
        count = len(voice_count_distribution[pattern])
        percentage = 100 * count / len(sid_files)
        print(f"  Voices {pattern:3s}: {count:3d} files ({percentage:5.1f}%)")

    if three_voice_files:
        print("\n" + "="*80)
        print(f"FILES USING ALL 3 VOICES ({len(three_voice_files)} files)")
        print("="*80)
        print(f"{'Filename':<50s} {'Voice1':>8s} {'Voice2':>8s} {'Voice3':>8s}")
        print("-" * 80)
        for name, lengths in three_voice_files[:20]:  # Show first 20
            print(f"{name:<50s} {lengths[0]:8d} {lengths[1]:8d} {lengths[2]:8d}")
        if len(three_voice_files) > 20:
            print(f"... and {len(three_voice_files) - 20} more")

    if errors and len(errors) <= 10:
        print("\n" + "="*80)
        print("ERRORS")
        print("="*80)
        for name, error in errors:
            print(f"  {name}: {error}")

    return voice_usage_stats, voice_count_distribution, three_voice_files


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Analyze voice usage in Laxity SID files'
    )
    parser.add_argument('--all', action='store_true',
                       help='Analyze all files (default: sample 30)')
    parser.add_argument('--sample', type=int, default=30, metavar='N',
                       help='Sample N files evenly (default: 30)')
    parser.add_argument('--laxity-dir', type=Path, default=Path('Laxity'),
                       help='Path to Laxity directory (default: ./Laxity)')
    parser.add_argument('file', nargs='?', type=Path,
                       help='Analyze single file instead of collection')

    args = parser.parse_args()

    # Single file mode
    if args.file:
        result = check_voice_usage(args.file)
        if result['error']:
            print(f"Error: {result['error']}")
            sys.exit(1)
        else:
            print(f"File: {args.file.name}")
            print(f"Voices used: {[v+1 for v in result['voices_used']]}")
            print(f"Orderlist lengths: Voice1={result['orderlist_lengths'][0]}, "
                  f"Voice2={result['orderlist_lengths'][1]}, "
                  f"Voice3={result['orderlist_lengths'][2]}")
            sys.exit(0)

    # Collection mode
    if not args.laxity_dir.exists():
        print(f"Error: Laxity directory not found: {args.laxity_dir}")
        sys.exit(1)

    sample_size = None if args.all else args.sample

    stats, distribution, three_voice = analyze_laxity_collection(
        args.laxity_dir,
        sample_size=sample_size
    )

    # Exit with success
    sys.exit(0)
