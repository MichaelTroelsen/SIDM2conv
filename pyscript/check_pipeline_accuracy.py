#!/usr/bin/env python3
"""
Check accuracy results for all files in the pipeline output.
"""

import os
import re
from pathlib import Path

def extract_accuracy(info_file):
    """Extract accuracy metrics from info.txt file."""
    try:
        with open(info_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract register-level accuracy
        register_match = re.search(r'Register-Level Accuracy:\s+([\d.]+)%', content)
        register_acc = float(register_match.group(1)) if register_match else None

        # Extract frame-by-frame accuracy
        frame_match = re.search(r'Frame-by-Frame Accuracy:\s+([\d.]+)%', content)
        frame_acc = float(frame_match.group(1)) if frame_match else None

        # Extract filter accuracy
        filter_match = re.search(r'Filter Accuracy:\s+([\d.]+)%', content)
        filter_acc = float(filter_match.group(1)) if filter_match else None

        # Extract conversion method
        method_match = re.search(r'Conversion Method:\s+(.+)', content)
        method = method_match.group(1).strip() if method_match else "N/A"

        return {
            'register': register_acc,
            'frame': frame_acc,
            'filter': filter_acc,
            'method': method
        }
    except Exception as e:
        return None

def main():
    pipeline_dir = Path('output/SIDSF2player_Complete_Pipeline')

    if not pipeline_dir.exists():
        print("Pipeline output directory not found!")
        return

    results = []

    # Scan all subdirectories
    for subdir in sorted(pipeline_dir.iterdir()):
        if subdir.is_dir():
            info_file = subdir / 'New' / 'info.txt'
            if info_file.exists():
                accuracy = extract_accuracy(info_file)
                if accuracy:
                    results.append({
                        'name': subdir.name,
                        'accuracy': accuracy
                    })

    # Print summary table
    print("=" * 100)
    print("PIPELINE ACCURACY SUMMARY - ALL 18 FILES")
    print("=" * 100)
    print(f"{'File Name':<50} {'Register':<12} {'Frame':<12} {'Filter':<12} {'Method':<15}")
    print("-" * 100)

    register_sum = 0
    frame_sum = 0
    filter_sum = 0
    count = 0

    for result in results:
        name = result['name']
        acc = result['accuracy']

        # Truncate long names
        if len(name) > 48:
            name = name[:45] + "..."

        register = f"{acc['register']:.2f}%" if acc['register'] is not None else "N/A"
        frame = f"{acc['frame']:.2f}%" if acc['frame'] is not None else "N/A"
        filter_val = f"{acc['filter']:.2f}%" if acc['filter'] is not None else "N/A"
        method = acc['method'][:14] if acc['method'] else "N/A"

        print(f"{name:<50} {register:<12} {frame:<12} {filter_val:<12} {method:<15}")

        # Sum for averages
        if acc['register'] is not None:
            register_sum += acc['register']
        if acc['frame'] is not None:
            frame_sum += acc['frame']
        if acc['filter'] is not None:
            filter_sum += acc['filter']
        count += 1

    print("-" * 100)

    # Print averages
    if count > 0:
        avg_register = register_sum / count
        avg_frame = frame_sum / count
        avg_filter = filter_sum / count

        print(f"{'AVERAGE (18 files)':<50} {avg_register:>6.2f}%     {avg_frame:>6.2f}%     {avg_filter:>6.2f}%")
        print("=" * 100)

        # Success summary
        perfect = sum(1 for r in results if r['accuracy']['register'] == 100.0)
        print(f"\nPERFECT ACCURACY (100%): {perfect}/{count} files ({perfect/count*100:.1f}%)")

        high_acc = sum(1 for r in results if r['accuracy']['register'] and r['accuracy']['register'] >= 99.0)
        print(f"HIGH ACCURACY (>=99%):   {high_acc}/{count} files ({high_acc/count*100:.1f}%)")

        print("\n[OK] All files successfully validated!")
    else:
        print("No results found!")

if __name__ == '__main__':
    main()
