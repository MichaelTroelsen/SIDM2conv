#!/usr/bin/env python3
"""Conversion Cockpit Real File Test"""

import sys
import subprocess
from pathlib import Path
import time

def test_cockpit_with_real_files():
    print("=" * 80)
    print("CONVERSION COCKPIT REAL FILE TEST")
    print("=" * 80)
    print()

    test_files = [
        "SID/Broware.sid",
        "SID/Aint_Somebody.sid",
        "SID/Stinsens_Last_Night_of_89.sid",
        "SID/Beast.sid",
        "SID/Delicate.sid"
    ]

    existing_files = [f for f in test_files if Path(f).exists()]

    print(f"Found {len(existing_files)} test files:")
    for f in existing_files:
        print(f"  [OK] {f}")
    print()

    output_dir = Path("output/cockpit_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Configuration:")
    print(f"  Driver: laxity (auto)")
    print(f"  Output: {output_dir}/")
    print()

    print("=" * 80)
    print("STARTING CONVERSION")
    print("=" * 80)
    start_time = time.time()

    results = []
    for i, sid_file in enumerate(existing_files, 1):
        file_name = Path(sid_file).stem
        output_file = output_dir / f"{file_name}.sf2"

        print(f"\n[{i}/{len(existing_files)}] Converting: {Path(sid_file).name}")
        print(f"    Output: {output_file.name}")

        file_start = time.time()

        try:
            # Call sid_to_sf2.py with --driver laxity
            result = subprocess.run(
                [sys.executable, "scripts/sid_to_sf2.py", sid_file, str(output_file), "--driver", "laxity", "-q"],
                capture_output=True,
                text=True,
                timeout=30
            )

            file_duration = time.time() - file_start

            # Check if conversion succeeded
            if result.returncode == 0 and output_file.exists():
                file_size = output_file.stat().st_size
                results.append({
                    'input_file': sid_file,
                    'output_file': str(output_file),
                    'status': 'success',
                    'size': file_size,
                    'duration': file_duration,
                    'driver_used': 'laxity'
                })
                print(f"    [OK] Success - {file_size:,} bytes in {file_duration:.2f}s")
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                results.append({
                    'input_file': sid_file,
                    'status': 'failed',
                    'error': error_msg,
                    'duration': file_duration
                })
                print(f"    [FAIL] Failed - {error_msg}")

        except subprocess.TimeoutExpired:
            file_duration = time.time() - file_start
            results.append({
                'input_file': sid_file,
                'status': 'failed',
                'error': 'Timeout (>30s)',
                'duration': file_duration
            })
            print(f"    [FAIL] Timeout (>30s)")
        except Exception as e:
            file_duration = time.time() - file_start
            results.append({
                'input_file': sid_file,
                'status': 'failed',
                'error': str(e),
                'duration': file_duration
            })
            print(f"    [FAIL] Error: {e}")

    duration = time.time() - start_time

    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()

    total = len(results)
    successful = sum(1 for r in results if r.get('status') == 'success')
    failed = total - successful

    print(f"Total files:      {total}")
    print(f"Successful:       {successful} ({successful/total*100:.1f}%)")
    print(f"Failed:           {failed}")
    print(f"Duration:         {duration:.2f}s")
    print(f"Avg per file:     {duration/total:.2f}s")
    print()

    print("File Results:")
    print("-" * 80)

    for i, result in enumerate(results, 1):
        file_name = Path(result['input_file']).name
        status = result.get('status', 'unknown')
        driver = result.get('driver_used', 'unknown')

        status_icon = "[OK]" if status == 'success' else "[FAIL]"

        print(f"{i}. {status_icon} {file_name} - {status.upper()}")
        if status == 'success':
            print(f"   Driver: {driver}")
            print(f"   Output: {result.get('size', 0):,} bytes")
            print(f"   Time: {result.get('duration', 0):.2f}s")
        else:
            print(f"   Error: {result.get('error', 'Unknown')}")
            print(f"   Time: {result.get('duration', 0):.2f}s")

        print()

    print("=" * 80)

    success_rate = successful / total * 100
    test_passed = success_rate >= 80

    if test_passed:
        print(f"[PASSED] Success rate: {success_rate:.1f}% (target: >=80%)")
    else:
        print(f"[FAILED] Success rate: {success_rate:.1f}% (target: >=80%)")

    print()
    print(f"Output directory: {output_dir}/")
    print()

    return test_passed


if __name__ == '__main__':
    success = test_cockpit_with_real_files()
    sys.exit(0 if success else 1)
