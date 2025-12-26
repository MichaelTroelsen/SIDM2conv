#!/usr/bin/env python3
"""
Convert SID files to WAV using VSID (VICE SID player).

Usage:
    python pyscript/sid_to_wav_vsid.py input.sid output.wav [--time SECONDS]

Examples:
    python pyscript/sid_to_wav_vsid.py music.sid music.wav
    python pyscript/sid_to_wav_vsid.py music.sid music.wav --time 120
"""

import argparse
import subprocess
import sys
from pathlib import Path

def find_vsid():
    """Locate vsid.exe in the tools directory or system PATH."""
    # Check common VICE installation locations
    project_root = Path(__file__).parent.parent
    vice_paths = [
        Path(r'C:\winvice\bin\vsid.exe'),  # Common Windows installation
        project_root / 'tools' / 'vice' / 'bin' / 'vsid.exe',
        project_root / 'tools' / 'vice' / 'vsid.exe',
    ]

    for path in vice_paths:
        if path.exists():
            return path

    # Check system PATH
    import shutil
    vsid_path = shutil.which('vsid')
    if vsid_path:
        return Path(vsid_path)

    return None

def convert_sid_to_wav(input_sid, output_wav, time_seconds=None):
    """
    Convert SID file to WAV using vsid.

    Args:
        input_sid: Path to input SID file
        output_wav: Path to output WAV file
        time_seconds: Optional playback time in seconds (default: vsid decides)

    Returns:
        True if successful, False otherwise
    """
    input_path = Path(input_sid)
    output_path = Path(output_wav)

    # Validate input
    if not input_path.exists():
        print(f"[X] Error: Input file not found: {input_path}")
        return False

    # Find vsid
    vsid_exe = find_vsid()
    if not vsid_exe:
        print("[X] Error: vsid.exe not found")
        print("\nPlease install VICE:")
        print("  python pyscript/install_vice.py")
        print("  OR")
        print("  install-vice.bat")
        return False

    print(f"Using vsid: {vsid_exe}")

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build command
    # vsid -sounddev wav -soundarg output.wav input.sid
    # Note: VSID runs indefinitely, so we use subprocess timeout to stop it
    cmd = [
        str(vsid_exe),
        '-sounddev', 'wav',
        '-soundarg', str(output_path),
        str(input_path)
    ]

    print(f"\nConverting: {input_path.name} -> {output_path.name}")
    if time_seconds:
        print(f"Duration: {time_seconds} seconds")
        timeout_value = time_seconds + 10  # Add 10 seconds buffer
    else:
        print(f"Duration: Until stopped manually")
        timeout_value = 300  # 5 minute default

    try:
        # Run vsid with timeout (VSID runs indefinitely, timeout kills it)
        print(f"\nCommand: {' '.join(cmd)}")
        print(f"Timeout: {timeout_value} seconds")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_value
        )

        # VSID runs indefinitely, so timeout is expected
        # Check if WAV file was created successfully
        if not output_path.exists():
            print(f"\n[X] Output file not created: {output_path}")
            if result.returncode != 0:
                print(f"VSID exit code: {result.returncode}")
                if result.stderr:
                    print(f"Error: {result.stderr}")
            return False

        file_size = output_path.stat().st_size
        if file_size == 0:
            print(f"\n[X] Output file is empty")
            return False

        print(f"\n[OK] Conversion successful!")
        print(f"  Output: {output_path}")
        print(f"  Size: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")

        return True

    except subprocess.TimeoutExpired:
        # This is expected - VSID runs indefinitely, timeout stops it
        # Check if WAV file was created
        if output_path.exists() and output_path.stat().st_size > 0:
            file_size = output_path.stat().st_size
            print(f"\n[OK] Conversion completed (stopped after timeout)")
            print(f"  Output: {output_path}")
            print(f"  Size: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")
            return True
        else:
            print("\n[X] Error: Timeout but no output file created")
            return False
    except Exception as e:
        print(f"\n[X] Error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Convert SID files to WAV using VSID',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s music.sid music.wav
  %(prog)s music.sid music.wav --time 120
  %(prog)s input.sid output.wav -t 180
        """
    )

    parser.add_argument('input_sid', help='Input SID file')
    parser.add_argument('output_wav', help='Output WAV file')
    parser.add_argument(
        '-t', '--time',
        type=int,
        metavar='SECONDS',
        help='Playback time in seconds (default: vsid decides)'
    )

    args = parser.parse_args()

    success = convert_sid_to_wav(
        args.input_sid,
        args.output_wav,
        args.time
    )

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
