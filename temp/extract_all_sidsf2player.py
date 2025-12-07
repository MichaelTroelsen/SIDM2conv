#!/usr/bin/env python3
"""
Batch extraction of SF2 files from SF2-packed SID files in SIDSF2player folder.
"""

import struct
from pathlib import Path
import sys

# Import the extraction function
from extract_sf2_properly import extract_sf2_properly

# Mapping of SID files to their corresponding SF2 reference files
SF2_REFERENCES = {
    'Driver 11 Test - Arpeggio.sid': 'G5/examples/Driver 11 Test - Arpeggio.sf2',
    'Driver 11 Test - Filter.sid': 'G5/examples/Driver 11 Test - Filter.sf2',
    'Driver 11 Test - Polyphonic.sid': 'G5/examples/Driver 11 Test - Polyphonic.sf2',
    'Driver 11 Test - Tie Notes.sid': 'G5/examples/Driver 11 Test - Tie Notes.sf2',
    'Stinsens_Last_Night_of_89.sid': 'learnings/Stinsen - Last Night Of 89.sf2',
}

def main():
    sidsf2_dir = Path('SIDSF2player')
    output_base = Path('output/SIDSF2player_Extracted')

    # Find all SID files
    sid_files = sorted(sidsf2_dir.glob('*.sid'))

    print('='*80)
    print('SF2 EXTRACTION FROM SIDSF2PLAYER FILES')
    print('='*80)
    print(f'\nFound {len(sid_files)} SID files')
    print()

    results = []

    for sid_file in sid_files:
        filename = sid_file.name
        print(f'\nProcessing: {filename}')
        print('-'*80)

        # Check if we have a reference SF2
        if filename in SF2_REFERENCES:
            ref_sf2 = Path(SF2_REFERENCES[filename])

            if not ref_sf2.exists():
                print(f'  [WARN] Reference SF2 not found: {ref_sf2}')
                results.append((filename, 'SKIP', 'No reference'))
                continue

            # Create output directory
            output_dir = output_base / filename.replace('.sid', '')
            output_dir.mkdir(parents=True, exist_ok=True)

            output_sf2 = output_dir / f'{filename.replace(".sid", "_extracted.sf2")}'

            try:
                # Extract SF2
                extract_sf2_properly(str(sid_file), str(ref_sf2), str(output_sf2))
                print(f'  [OK] Extracted to: {output_sf2}')
                results.append((filename, 'SUCCESS', str(output_sf2)))

            except Exception as e:
                print(f'  [ERROR] Error: {e}')
                results.append((filename, 'ERROR', str(e)))
        else:
            print(f'  [INFO] No reference SF2 mapping (skipping)')
            results.append((filename, 'SKIP', 'No reference mapping'))

    # Summary
    print()
    print('='*80)
    print('EXTRACTION SUMMARY')
    print('='*80)
    print()

    success_count = sum(1 for _, status, _ in results if status == 'SUCCESS')
    error_count = sum(1 for _, status, _ in results if status == 'ERROR')
    skip_count = sum(1 for _, status, _ in results if status == 'SKIP')

    print(f'Total files: {len(results)}')
    print(f'  [OK] Successful: {success_count}')
    print(f'  [ERROR] Errors: {error_count}')
    print(f'  [SKIP] Skipped: {skip_count}')
    print()

    # Details
    print('DETAILS:')
    print()
    for filename, status, detail in results:
        icon = '[OK]' if status == 'SUCCESS' else '[ERROR]' if status == 'ERROR' else '[SKIP]'
        print(f'{icon} {filename:<50} {status:<10} {detail}')

    print()
    print('='*80)

if __name__ == '__main__':
    main()
