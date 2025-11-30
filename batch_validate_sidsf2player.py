#!/usr/bin/env python3
"""
Batch Validation for SIDSF2player Files
Runs full SID→SF2→SID conversion pipeline and validates accuracy
"""

import os
import sys
import subprocess
from pathlib import Path
import json
from datetime import datetime

def run_conversion_pipeline(sid_file, output_dir):
    """Run full SID→SF2→SID conversion and validation"""
    sid_path = Path(sid_file)
    stem = sid_path.stem

    # Create output directory
    out_path = Path(output_dir) / stem
    out_path.mkdir(parents=True, exist_ok=True)

    # Paths
    sf2_file = out_path / f"{stem}.sf2"
    exported_sid = out_path / f"{stem}_exported.sid"
    validation_html = out_path / f"{stem}_validation.html"

    results = {
        'original_sid': str(sid_file),
        'stem': stem,
        'conversion_success': False,
        'packing_success': False,
        'validation_success': False,
        'accuracy': {
            'overall': 0.0,
            'frame': 0.0,
            'filter': 0.0,
            'voices': {}
        },
        'errors': []
    }

    print(f"\n{'='*70}")
    print(f"Processing: {stem}")
    print(f"{'='*70}")

    # Step 1: SID -> SF2
    print(f"[1/3] Converting SID -> SF2...")
    try:
        result = subprocess.run(
            ['python', 'sid_to_sf2.py', str(sid_file), str(sf2_file)],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0 and sf2_file.exists():
            print(f"  SUCCESS: Created {sf2_file.name}")
            results['conversion_success'] = True
        else:
            error_msg = f"SID->SF2 conversion failed: {result.stderr}"
            print(f"  ERROR: {error_msg}")
            results['errors'].append(error_msg)
            return results
    except Exception as e:
        error_msg = f"SID->SF2 exception: {e}"
        print(f"  ERROR: {error_msg}")
        results['errors'].append(error_msg)
        return results

    # Step 2: SF2 -> SID
    print(f"[2/3] Packing SF2 -> SID...")
    try:
        result = subprocess.run(
            ['python', 'sf2_to_sid.py', str(sf2_file), str(exported_sid)],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0 and exported_sid.exists():
            print(f"  SUCCESS: Created {exported_sid.name}")
            results['packing_success'] = True
        else:
            error_msg = f"SF2->SID packing failed: {result.stderr}"
            print(f"  ERROR: {error_msg}")
            results['errors'].append(error_msg)
            return results
    except Exception as e:
        error_msg = f"SF2->SID exception: {e}"
        print(f"  ERROR: {error_msg}")
        results['errors'].append(error_msg)
        return results

    # Step 3: Validate accuracy
    print(f"[3/3] Validating accuracy...")
    try:
        result = subprocess.run(
            ['python', 'validate_sid_accuracy.py',
             str(sid_file), str(exported_sid),
             '--duration', '10',
             '--output', str(validation_html)],
            capture_output=True,
            text=True,
            timeout=60
        )

        # Parse validation output
        output = result.stdout
        if 'Overall Accuracy:' in output:
            for line in output.split('\n'):
                if 'Overall Accuracy:' in line:
                    accuracy = float(line.split(':')[1].strip().replace('%', ''))
                    results['accuracy']['overall'] = accuracy
                elif 'Frame Accuracy:' in line:
                    accuracy = float(line.split(':')[1].strip().replace('%', ''))
                    results['accuracy']['frame'] = accuracy
                elif 'Filter Accuracy:' in line:
                    accuracy = float(line.split(':')[1].strip().replace('%', ''))
                    results['accuracy']['filter'] = accuracy
                elif 'Frequency:' in line:
                    accuracy = float(line.split(':')[1].strip().replace('%', ''))
                    voice_num = len(results['accuracy']['voices']) + 1
                    if f'Voice{voice_num}' not in results['accuracy']['voices']:
                        results['accuracy']['voices'][f'Voice{voice_num}'] = {}
                    results['accuracy']['voices'][f'Voice{voice_num}']['frequency'] = accuracy
                elif 'Waveform:' in line and 'Voice' not in line:
                    accuracy = float(line.split(':')[1].strip().replace('%', ''))
                    voice_num = len(results['accuracy']['voices'])
                    results['accuracy']['voices'][f'Voice{voice_num}']['waveform'] = accuracy

            results['validation_success'] = True

            # Determine grade
            overall = results['accuracy']['overall']
            if overall >= 99:
                grade = "EXCELLENT"
            elif overall >= 95:
                grade = "GOOD"
            elif overall >= 80:
                grade = "FAIR"
            else:
                grade = "POOR"

            results['grade'] = grade

            print(f"  SUCCESS: {overall:.2f}% accuracy ({grade})")
            print(f"    Frame: {results['accuracy']['frame']:.2f}%")
            print(f"    Filter: {results['accuracy']['filter']:.2f}%")

        else:
            error_msg = "Validation output parsing failed"
            print(f"  ERROR: {error_msg}")
            results['errors'].append(error_msg)

    except Exception as e:
        error_msg = f"Validation exception: {e}"
        print(f"  ERROR: {error_msg}")
        results['errors'].append(error_msg)

    return results


def main():
    # Find all SID files in SIDSF2player (but not in subdirectories like converted/)
    sidsf2player_dir = Path('SIDSF2player')
    sid_files = [f for f in sidsf2player_dir.glob('*.sid')]

    print(f"Found {len(sid_files)} SID files in SIDSF2player/")

    # Create output directory
    output_dir = Path('SIDSF2player/validation_results')
    output_dir.mkdir(exist_ok=True)

    # Process each file
    all_results = []
    success_count = 0
    excellent_count = 0
    good_count = 0
    fair_count = 0
    poor_count = 0

    for sid_file in sorted(sid_files):
        results = run_conversion_pipeline(sid_file, output_dir)
        all_results.append(results)

        if results['validation_success']:
            success_count += 1
            grade = results.get('grade', 'UNKNOWN')
            if grade == 'EXCELLENT':
                excellent_count += 1
            elif grade == 'GOOD':
                good_count += 1
            elif grade == 'FAIR':
                fair_count += 1
            elif grade == 'POOR':
                poor_count += 1

    # Generate summary report
    print(f"\n{'='*70}")
    print("BATCH VALIDATION SUMMARY")
    print(f"{'='*70}")
    print(f"Total files: {len(sid_files)}")
    print(f"Successfully validated: {success_count}")
    print(f"")
    print(f"Accuracy grades:")
    print(f"  EXCELLENT (99%+): {excellent_count}")
    print(f"  GOOD (95-99%):    {good_count}")
    print(f"  FAIR (80-95%):    {fair_count}")
    print(f"  POOR (<80%):      {poor_count}")
    print(f"")

    # Files needing work
    needs_work = [r for r in all_results if r['validation_success'] and r['accuracy']['overall'] < 99]
    if needs_work:
        print(f"Files needing improvement ({len(needs_work)}):")
        for r in sorted(needs_work, key=lambda x: x['accuracy']['overall']):
            print(f"  {r['stem']}: {r['accuracy']['overall']:.2f}% ({r['grade']})")
    else:
        print("All files achieved 99%+ accuracy!")

    # Save JSON report
    report_file = output_dir / f"batch_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total': len(sid_files),
                'validated': success_count,
                'excellent': excellent_count,
                'good': good_count,
                'fair': fair_count,
                'poor': poor_count
            },
            'results': all_results
        }, f, indent=2)

    print(f"\nFull report saved to: {report_file}")
    print(f"{'='*70}\n")

    # Return exit code
    if excellent_count == len(sid_files):
        return 0  # All excellent
    elif good_count + excellent_count == len(sid_files):
        return 0  # All good or excellent
    else:
        return 1  # Some files need work


if __name__ == '__main__':
    sys.exit(main())
