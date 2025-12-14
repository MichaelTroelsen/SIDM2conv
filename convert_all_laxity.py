#!/usr/bin/env python3
"""Batch convert all Laxity SID files to SF2 using custom Laxity driver"""

import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

def main():
    sid_dir = Path("Laxity")
    output_dir = Path("output")
    
    # Get all Laxity files
    files = sorted(sid_dir.glob("*.sid"))
    
    print("=" * 80)
    print("LAXITY SID BATCH CONVERSION - FULL COLLECTION")
    print("=" * 80)
    print(f"\nStart time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total files to convert: {len(files)}")
    print()
    
    results = {
        'success': [],
        'failed': [],
        'skipped': [],
    }
    
    total_size = 0
    start_time = time.time()
    
    for i, sid_file in enumerate(files, 1):
        base_name = sid_file.stem
        output_file = output_dir / f"{base_name}_laxity.sf2"
        
        # Progress indicator
        pct = (i / len(files)) * 100
        print(f"[{i:3d}/{len(files)}] ({pct:5.1f}%) {sid_file.name:50s} ", end="", flush=True)
        
        # Skip if file already exists (optional)
        if output_file.exists():
            size = output_file.stat().st_size
            total_size += size
            results['skipped'].append((base_name, size))
            print(f"SKIPPED (exists: {size:,} bytes)")
            continue
        
        try:
            result = subprocess.run(
                [sys.executable, "scripts/sid_to_sf2.py", str(sid_file), str(output_file), "--driver", "laxity"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and output_file.exists():
                size = output_file.stat().st_size
                total_size += size
                results['success'].append((base_name, size))
                print(f"OK ({size:,} bytes)")
            else:
                results['failed'].append(base_name)
                print(f"FAILED")
                if result.stderr:
                    err = result.stderr.split('\n')[0]
                    if err:
                        print(f"       Error: {err[:70]}")
                        
        except subprocess.TimeoutExpired:
            results['failed'].append(base_name)
            print(f"TIMEOUT")
        except Exception as e:
            results['failed'].append(base_name)
            print(f"ERROR: {str(e)[:50]}")
    
    elapsed = time.time() - start_time
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    success_count = len(results['success'])
    failed_count = len(results['failed'])
    skipped_count = len(results['skipped'])
    
    print(f"\nConversion Results:")
    print(f"  Successful: {success_count}/{len(files)} ({100*success_count/len(files):.1f}%)")
    print(f"  Failed:     {failed_count}/{len(files)} ({100*failed_count/len(files):.1f}%)")
    print(f"  Skipped:    {skipped_count}/{len(files)} ({100*skipped_count/len(files):.1f}%)")
    
    total_success = success_count + skipped_count
    total_size_skipped = sum(size for _, size in results['skipped'])
    total_size_new = total_size - total_size_skipped
    
    print(f"\nOutput Size Statistics:")
    print(f"  New files:      {total_size_new:,} bytes")
    print(f"  Skipped files:  {total_size_skipped:,} bytes")
    print(f"  Total output:   {total_size:,} bytes")
    
    if success_count > 0:
        avg_size = total_size_new / success_count
        print(f"  Average file:   {avg_size:,.0f} bytes")
    
    print(f"\nTiming:")
    print(f"  Elapsed time: {elapsed:.1f} seconds")
    print(f"  Files/second: {len(files)/elapsed:.1f}")
    print(f"  Time/file:    {elapsed/len(files):.1f} seconds")
    
    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if failed_count > 0:
        print(f"\nFailed files ({failed_count}):")
        for name in results['failed'][:10]:  # Show first 10
            print(f"  - {name}")
        if failed_count > 10:
            print(f"  ... and {failed_count - 10} more")
    
    return 0 if failed_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
