#!/usr/bin/env python3
"""Test batch conversion with Laxity driver"""

import os
import subprocess
import sys
from pathlib import Path

def main():
    sid_dir = Path("Laxity")
    output_dir = Path("output")
    
    # Get first 18 Laxity files
    files = sorted(sid_dir.glob("*.sid"))[:18]
    
    print(f"Testing {len(files)} Laxity files with custom driver\n")
    print("=" * 80)
    
    results = []
    for i, sid_file in enumerate(files, 1):
        base_name = sid_file.stem
        output_file = output_dir / f"{base_name}_laxity.sf2"
        
        print(f"\n[{i:2d}/18] Testing: {sid_file.name}")
        
        try:
            result = subprocess.run(
                [sys.executable, "scripts/sid_to_sf2.py", str(sid_file), str(output_file), "--driver", "laxity"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Extract size from output
                for line in result.stderr.split("\n") + result.stdout.split("\n"):
                    if "Size:" in line or "Output:" in line:
                        print(f"  [OK] {line.strip()}")
                
                if output_file.exists():
                    size = output_file.stat().st_size
                    results.append((base_name, size, True))
                    print(f"  File size: {size:,} bytes")
                else:
                    print(f"  [ERROR] Output file not created")
                    results.append((base_name, 0, False))
            else:
                print(f"  [ERROR] Conversion failed")
                if result.stderr:
                    err_line = result.stderr.split("\n")[0]
                    if err_line:
                        print(f"    Error: {err_line}")
                results.append((base_name, 0, False))
                
        except subprocess.TimeoutExpired:
            print(f"  [ERROR] Timeout")
            results.append((base_name, 0, False))
        except Exception as e:
            print(f"  [ERROR] Exception: {e}")
            results.append((base_name, 0, False))
    
    print("\n" + "=" * 80)
    print("\nSUMMARY")
    print("=" * 80)
    
    success_count = sum(1 for _, _, success in results if success)
    total_size = sum(size for _, size, success in results if success)
    
    print(f"\nConversions successful: {success_count}/{len(results)}")
    print(f"Total output size: {total_size:,} bytes")
    if success_count > 0:
        print(f"Average file size: {total_size // success_count:,} bytes")

if __name__ == "__main__":
    main()
