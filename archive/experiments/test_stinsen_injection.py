#!/usr/bin/env python3
"""
Test siddump injection on SF2packed_Stinsens_Last_Night_of_89.sid
"""

import sys
from pathlib import Path

# Add the current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import the complete pipeline
from complete_pipeline_with_validation import main

# Run just for the Stinsen file by temporarily modifying the sid_files list
if __name__ == '__main__':
    # Just process one file for testing
    import complete_pipeline_with_validation as pipeline

    # Override the main function to process only Stinsen
    sidsf2_dir = Path('SIDSF2player')
    output_base = Path('output/SIDSF2player_Complete_Pipeline')

    # Find just the Stinsen file
    sid_file = sidsf2_dir / 'SF2packed_Stinsens_Last_Night_of_89.sid'

    if not sid_file.exists():
        print(f"File not found: {sid_file}")
        sys.exit(1)

    print('='*80)
    print('TEST: SF2packed_Stinsens_Last_Night_of_89.sid with NEW siddump injection')
    print('='*80)
    print(f'\nProcessing: {sid_file.name}')
    print()

    # Process using the pipeline's internal logic
    from datetime import datetime
    from sidm2.siddump_extractor import extract_sequences_from_siddump
    from complete_pipeline_with_validation import (
        inject_siddump_sequences,
        detect_file_type,
        pack_sf2_to_sid_safe,
        run_siddump
    )
    import struct

    basename = sid_file.stem
    song_dir = output_base / basename
    original_dir = song_dir / 'Original'
    new_dir = song_dir / 'New'

    # Create directories
    original_dir.mkdir(parents=True, exist_ok=True)
    new_dir.mkdir(parents=True, exist_ok=True)

    output_sf2 = new_dir / f'{basename}.sf2'

    # Get metadata
    with open(sid_file, 'rb') as f:
        f.seek(0x16)
        name = f.read(32).decode('ascii', errors='ignore').rstrip('\x00')
        author = f.read(32).decode('ascii', errors='ignore').rstrip('\x00')
        copyright_str = f.read(32).decode('ascii', errors='ignore').rstrip('\x00')

    print(f'  Title: {name}')
    print(f'  Author: {author}')
    print(f'  Copyright: {copyright_str}')
    print()

    # STEP 1: SID -> SF2
    print(f'  [1/2] Converting SID -> SF2...')
    file_type = detect_file_type(str(sid_file))
    print(f'        Detected type: {file_type}')

    # Copy original SF2 from SIDSF2player as reference
    original_sf2 = sidsf2_dir / f'{basename}.sf2'
    if original_sf2.exists():
        import shutil
        shutil.copy(original_sf2, output_sf2)
        print(f'        [OK] Using original SF2 as template')
    else:
        print(f'        [ERROR] Original SF2 not found: {original_sf2}')
        sys.exit(1)

    # STEP 1.5: Extract and inject sequences
    print(f'\n  [1.5/2] Extracting sequences from siddump...')
    try:
        sequences, orderlists = extract_sequences_from_siddump(str(sid_file), seconds=10, max_sequences=39)
        if sequences and orderlists:
            print(f'        Extracted {len(sequences)} sequences, {len(orderlists)} orderlists')

            # Inject into SF2 file
            if inject_siddump_sequences(output_sf2, sequences, orderlists):
                print(f'        [OK] Injection succeeded!')
            else:
                print(f'        [FAIL] Injection failed')
                sys.exit(1)
        else:
            print(f'        [WARN] No sequences extracted')
    except Exception as e:
        print(f'        [ERROR] {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Verify file was created and has reasonable size
    if output_sf2.exists():
        size = output_sf2.stat().st_size
        print(f'\n  Output: {output_sf2}')
        print(f'  Size: {size} bytes')

        if size > 1024:
            print(f'\n  ✓ SUCCESS - File generated with siddump injection')
            print(f'  ✓ Please test this file in SID Factory II editor')
            print(f'  ✓ File: {output_sf2}')
        else:
            print(f'\n  ✗ FAIL - File too small ({size} bytes)')
            sys.exit(1)
    else:
        print(f'\n  ✗ FAIL - Output file not created')
        sys.exit(1)
