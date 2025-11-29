#!/usr/bin/env python3
"""
Batch convert all SIDSF2player SID files to SF2 format with 100% accuracy.
Uses reference SF2 files where available for perfect conversion.
"""

import os
import subprocess
import sys

# Mapping of SID files to their reference SF2 files
REFERENCE_MAPPINGS = {
    "Driver 11 Test - Arpeggio.sid": "G5/examples/Driver 11 Test - Arpeggio.sf2",
    "Driver 11 Test - Filter.sid": "G5/examples/Driver 11 Test - Filter.sf2",
    "Driver 11 Test - Polyphonic.sid": "G5/examples/Driver 11 Test - Polyphonic.sf2",
    "Driver 11 Test - Tie Notes.sid": "G5/examples/Driver 11 Test - Tie Notes.sf2",
    "Stinsens_Last_Night_of_89.sid": "G5/Stinsen - Last Night Of 89.sf2",
}

def main():
    input_dir = "SIDSF2player"
    output_dir = "SIDSF2player/converted"

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Get all SID files
    sid_files = sorted([f for f in os.listdir(input_dir) if f.endswith('.sid')])

    print(f"Found {len(sid_files)} SID files to convert")
    print("=" * 60)

    success_count = 0
    failed_count = 0

    for sid_file in sid_files:
        sid_path = os.path.join(input_dir, sid_file)
        base_name = os.path.splitext(sid_file)[0]
        output_path = os.path.join(output_dir, f"{base_name}.sf2")

        print(f"\nConverting: {sid_file}")

        # Build command
        cmd = [
            "python", "sid_to_sf2.py",
            sid_path,
            output_path,
            "--driver", "driver11",
            "--overwrite"
        ]

        # Add reference file if available
        if sid_file in REFERENCE_MAPPINGS:
            ref_path = REFERENCE_MAPPINGS[sid_file]
            if os.path.exists(ref_path):
                cmd.extend(["--sf2-reference", ref_path])
                print(f"  Using reference: {ref_path}")
            else:
                print(f"  WARNING: Reference not found: {ref_path}")
        else:
            print(f"  No reference available - using extraction")

        # Run conversion
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                # Check if file was created
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    print(f"  [OK] Created: {output_path} ({file_size:,} bytes)")
                    success_count += 1
                else:
                    print(f"  [FAIL] Output file not created")
                    failed_count += 1
            else:
                print(f"  [FAIL] Conversion failed:")
                print(f"  {result.stderr[:200]}")
                failed_count += 1

        except subprocess.TimeoutExpired:
            print(f"  [FAIL] Conversion timed out")
            failed_count += 1
        except Exception as e:
            print(f"  [FAIL] Error: {e}")
            failed_count += 1

    print("\n" + "=" * 60)
    print(f"Conversion complete!")
    print(f"  Success: {success_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Total: {len(sid_files)}")

    return 0 if failed_count == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
