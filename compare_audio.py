"""
Audio Comparison Tool for SID to SF2 Conversion Validation

This script helps compare original SID files with converted SF2 output
by rendering both to WAV format.

Workflow:
1. Original SID → WAV (automatic via SID2WAV)
2. SF2 → PRG → SID (manual in SID Factory II)
3. Exported SID → WAV (automatic via SID2WAV)
4. Compare waveforms (visual/audio)
"""

import os
import sys
import subprocess
from pathlib import Path

# Configuration
SIDM2_DIR = Path(__file__).parent
TOOLS_DIR = SIDM2_DIR / "tools"
SID_DIR = SIDM2_DIR / "SID"
SF2_DIR = SIDM2_DIR / "SF2"

SID2WAV = TOOLS_DIR / "SID2WAV.EXE"

# Default settings for WAV generation
WAV_FREQUENCY = 44100
WAV_BITS = 16
WAV_DURATION = 60  # seconds


def sid_to_wav(sid_path: Path, wav_path: Path, duration: int = WAV_DURATION) -> bool:
    """
    Convert a SID file to WAV using SID2WAV.

    Args:
        sid_path: Path to input SID file
        wav_path: Path to output WAV file
        duration: Duration in seconds

    Returns:
        True if conversion succeeded
    """
    if not SID2WAV.exists():
        print(f"Error: SID2WAV not found at {SID2WAV}")
        return False

    if not sid_path.exists():
        print(f"Error: SID file not found: {sid_path}")
        return False

    cmd = [
        str(SID2WAV),
        f"-f{WAV_FREQUENCY}",
        f"-{WAV_BITS}",
        f"-t{duration}",
        str(sid_path),
        str(wav_path)
    ]

    print(f"Converting {sid_path.name} to WAV...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if wav_path.exists():
        size = wav_path.stat().st_size
        print(f"  Created: {wav_path.name} ({size:,} bytes)")
        return True
    else:
        print(f"  Error: {result.stderr}")
        return False


def print_sf2_export_instructions(sf2_path: Path, output_sid_name: str):
    """
    Print instructions for exporting SF2 to SID in SID Factory II.
    """
    print("\n" + "="*60)
    print("SID Factory II Export Instructions")
    print("="*60)
    print(f"\n1. Open SID Factory II")
    print(f"2. Load: {sf2_path}")
    print(f"3. Press SPACE to play and listen")
    print(f"\nTo export as PRG:")
    print(f"4. Press F10 (Utilities menu)")
    print(f"5. Select 'Pack' to pack the music")
    print(f"6. Press F3 to save, choose .prg extension")
    print(f"7. Save as: {output_sid_name.replace('.sid', '.prg')}")
    print(f"\nNote: PRG can be loaded directly in VICE emulator.")
    print(f"To convert PRG to SID, you need PRG2SID or similar tool.")
    print("="*60 + "\n")


def compare_files(name: str, duration: int = 30):
    """
    Set up comparison for a SID/SF2 pair.

    Args:
        name: Base name (without extension)
        duration: Duration in seconds for WAV files
    """
    sid_path = SID_DIR / f"{name}.sid"
    sf2_path = SF2_DIR / f"{name}.sf2"

    # Output paths
    original_wav = SID_DIR / f"{name}_original.wav"
    converted_wav = SID_DIR / f"{name}_converted.wav"
    converted_sid = SID_DIR / f"{name}_converted.sid"

    print(f"\n{'='*60}")
    print(f"Audio Comparison: {name}")
    print(f"{'='*60}\n")

    # Step 1: Convert original SID to WAV
    if sid_path.exists():
        print("Step 1: Converting original SID to WAV")
        sid_to_wav(sid_path, original_wav, duration)
    else:
        print(f"Warning: Original SID not found: {sid_path}")

    # Step 2: Show SF2 export instructions
    if sf2_path.exists():
        print("\nStep 2: Export SF2 from SID Factory II")
        print_sf2_export_instructions(sf2_path, f"{name}_converted.sid")

        # Check if converted SID exists (from previous export)
        if converted_sid.exists():
            print(f"\nStep 3: Converting exported SID to WAV")
            sid_to_wav(converted_sid, converted_wav, duration)
        else:
            print(f"\nStep 3: Waiting for exported SID")
            print(f"  Expected file: {converted_sid}")
            print(f"  Once you export from SF2, run this script again.")
    else:
        print(f"Warning: SF2 file not found: {sf2_path}")

    # Summary
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")

    if original_wav.exists():
        print(f"  Original WAV:  {original_wav}")
    if converted_wav.exists():
        print(f"  Converted WAV: {converted_wav}")

    print(f"\nTo compare:")
    print(f"  - Play both WAV files in your audio player")
    print(f"  - Or use VICE/VSID to play both SID files")
    print(f"  - Or use Audacity to compare waveforms\n")


def batch_convert_originals(duration: int = 30):
    """
    Convert all original SID files to WAV for reference.
    """
    print("\nBatch converting all SID files to WAV...\n")

    sid_files = list(SID_DIR.glob("*.sid"))
    # Exclude already-converted files
    sid_files = [f for f in sid_files if not f.stem.endswith("_converted")]

    if not sid_files:
        print("No SID files found.")
        return

    for sid_path in sorted(sid_files):
        wav_path = SID_DIR / f"{sid_path.stem}_original.wav"
        if not wav_path.exists():
            sid_to_wav(sid_path, wav_path, duration)
        else:
            print(f"Skipping {sid_path.stem} (WAV exists)")

    print(f"\nConverted {len(sid_files)} files.")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Audio comparison tool for SID to SF2 conversion validation"
    )
    parser.add_argument(
        "name",
        nargs="?",
        help="Base name of SID/SF2 file (without extension)"
    )
    parser.add_argument(
        "-t", "--duration",
        type=int,
        default=30,
        help="Duration in seconds (default: 30)"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Convert all SID files to WAV"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available SID/SF2 pairs"
    )

    args = parser.parse_args()

    if args.list:
        # List available files
        sid_files = {f.stem for f in SID_DIR.glob("*.sid") if not f.stem.endswith(("_original", "_converted"))}
        sf2_files = {f.stem for f in SF2_DIR.glob("*.sf2")}

        print("\nAvailable files:\n")
        print(f"{'Name':<30} {'SID':<6} {'SF2':<6}")
        print("-" * 42)

        all_names = sorted(sid_files | sf2_files)
        for name in all_names:
            has_sid = "Yes" if name in sid_files else "No"
            has_sf2 = "Yes" if name in sf2_files else "No"
            print(f"{name:<30} {has_sid:<6} {has_sf2:<6}")

        print()
        return

    if args.batch:
        batch_convert_originals(args.duration)
        return

    if not args.name:
        # Default to Angular
        args.name = "Angular"

    compare_files(args.name, args.duration)


if __name__ == "__main__":
    main()
