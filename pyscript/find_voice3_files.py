#!/usr/bin/env python3
"""
Find Laxity SID files that use Voice 3.

This script scans Laxity files by running SIDwinder traces and checking
for Voice 3 register writes ($D40E-$D414).
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

# Voice 3 register addresses (relative to SID base $D400)
VOICE3_REGISTERS = {
    0x0E: "Voice3_FreqLo",
    0x0F: "Voice3_FreqHi",
    0x10: "Voice3_PulseLo",
    0x11: "Voice3_PulseHi",
    0x12: "Voice3_Control",
    0x13: "Voice3_Attack_Decay",
    0x14: "Voice3_Sustain_Release",
}

def check_voice3_usage(sid_file: Path, max_frames: int = 100) -> dict:
    """
    Check if a SID file uses Voice 3 by running SIDwinder trace.

    Args:
        sid_file: Path to SID file
        max_frames: Number of frames to trace

    Returns:
        dict with 'uses_voice3' (bool) and 'voice3_writes' (int)
    """
    result = {
        'uses_voice3': False,
        'voice3_writes': 0,
        'error': None
    }

    try:
        # Run SIDwinder trace for limited frames
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp_path = tmp.name

        # Get absolute path to SIDwinder.exe (relative to script location)
        script_dir = Path(__file__).parent.parent
        sidwinder = script_dir / 'tools' / 'SIDwinder.exe'

        cmd = [
            str(sidwinder),
            '-trace', str(sid_file.absolute()),
            tmp_path,
            '-frames', str(max_frames)
        ]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if proc.returncode != 0:
            result['error'] = f"SIDwinder failed: {proc.stderr[:100]}"
            return result

        # Read trace output and count Voice 3 writes
        if os.path.exists(tmp_path):
            with open(tmp_path, 'r', encoding='utf-8', errors='ignore') as f:
                trace_data = f.read()

            # Count writes to Voice 3 registers
            # SIDwinder format: "  $D40E = $XX" or "STA $D40E"
            voice3_count = 0
            for reg_offset in VOICE3_REGISTERS.keys():
                reg_addr = f"$D4{reg_offset:02X}"
                # Look for register writes in trace
                voice3_count += trace_data.count(reg_addr)

            result['voice3_writes'] = voice3_count
            result['uses_voice3'] = voice3_count > 0

            # Cleanup
            os.unlink(tmp_path)
        else:
            result['error'] = "Trace file not created"

    except subprocess.TimeoutExpired:
        result['error'] = "SIDwinder timeout"
    except Exception as e:
        result['error'] = str(e)

    return result


def scan_laxity_collection(laxity_dir: Path, max_files: int = None, sample_size: int = 20):
    """
    Scan Laxity collection for Voice 3 usage.

    Args:
        laxity_dir: Path to Laxity directory
        max_files: Maximum files to scan (None = all)
        sample_size: Number of files to sample if max_files not specified
    """
    print(f"Scanning Laxity collection in: {laxity_dir}")
    print(f"Looking for Voice 3 register writes ($D40E-$D414)...\n")

    # Get all .sid files
    sid_files = sorted(laxity_dir.glob("*.sid"))
    total = len(sid_files)
    print(f"Found {total} Laxity SID files")

    # Sample or limit
    if max_files is not None:
        sid_files = sid_files[:max_files]
        print(f"Scanning first {len(sid_files)} files\n")
    elif sample_size and total > sample_size:
        # Sample evenly across collection
        step = total // sample_size
        sid_files = sid_files[::step][:sample_size]
        print(f"Sampling {len(sid_files)} files evenly across collection\n")

    # Scan files
    voice3_files = []
    no_voice3_files = []
    errors = []

    for i, sid_file in enumerate(sid_files, 1):
        print(f"[{i}/{len(sid_files)}] {sid_file.name}...", end=' ')
        sys.stdout.flush()

        result = check_voice3_usage(sid_file)

        if result['error']:
            print(f"[ERROR] {result['error']}")
            errors.append((sid_file.name, result['error']))
        elif result['uses_voice3']:
            print(f"[OK] Voice 3 USED ({result['voice3_writes']} writes)")
            voice3_files.append((sid_file.name, result['voice3_writes']))
        else:
            print(f"[SKIP] No Voice 3")
            no_voice3_files.append(sid_file.name)

    # Print summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total scanned: {len(sid_files)}")
    print(f"Voice 3 used:  {len(voice3_files)} ({100*len(voice3_files)/len(sid_files):.1f}%)")
    print(f"No Voice 3:    {len(no_voice3_files)} ({100*len(no_voice3_files)/len(sid_files):.1f}%)")
    print(f"Errors:        {len(errors)}")

    if voice3_files:
        print("\n" + "="*70)
        print("FILES USING VOICE 3")
        print("="*70)
        for name, writes in sorted(voice3_files, key=lambda x: -x[1]):
            print(f"  {name:50s} ({writes:4d} writes)")

    if errors and len(errors) <= 5:
        print("\n" + "="*70)
        print("ERRORS")
        print("="*70)
        for name, error in errors:
            print(f"  {name}: {error}")

    return voice3_files, no_voice3_files, errors


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Find Laxity files using Voice 3')
    parser.add_argument('--all', action='store_true',
                       help='Scan all files (default: sample 20)')
    parser.add_argument('--max', type=int, metavar='N',
                       help='Scan first N files')
    parser.add_argument('--sample', type=int, default=20, metavar='N',
                       help='Sample N files evenly (default: 20)')
    parser.add_argument('--laxity-dir', type=Path, default=Path('Laxity'),
                       help='Path to Laxity directory (default: ./Laxity)')

    args = parser.parse_args()

    if not args.laxity_dir.exists():
        print(f"Error: Laxity directory not found: {args.laxity_dir}")
        sys.exit(1)

    # Determine scan mode
    if args.all:
        max_files = None
        sample_size = None
    elif args.max:
        max_files = args.max
        sample_size = None
    else:
        max_files = None
        sample_size = args.sample

    voice3_files, no_voice3, errors = scan_laxity_collection(
        args.laxity_dir,
        max_files=max_files,
        sample_size=sample_size
    )

    # Exit with success if we found Voice 3 files
    sys.exit(0 if voice3_files else 1)
