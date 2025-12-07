#!/usr/bin/env python3
"""
Smart batch extraction/conversion of SID files in SIDSF2player folder.
- SF2-packed files: Extract using template or reference
- Laxity SIDs: Convert using SID→SF2 pipeline
"""

import struct
import subprocess
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

def identify_sid_type(sid_path):
    """Identify if SID is SF2-packed or Laxity format."""
    with open(sid_path, 'rb') as f:
        data = f.read()

    # Parse PSID header
    magic = data[0:4].decode('ascii', errors='ignore')
    if magic not in ['PSID', 'RSID']:
        return 'UNKNOWN'

    version = struct.unpack('>H', data[4:6])[0]
    data_offset = struct.unpack('>H', data[6:8])[0]
    load_addr = struct.unpack('>H', data[8:10])[0]
    init_addr = struct.unpack('>H', data[10:12])[0]
    play_addr = struct.unpack('>H', data[12:14])[0]

    if load_addr == 0:
        actual_load = struct.unpack('<H', data[data_offset:data_offset+2])[0]
    else:
        actual_load = load_addr

    music_data = data[data_offset:]

    # Check for SF2 driver signature at typical location
    # SF2 files typically load at $1000 and have specific driver code
    if actual_load == 0x1000:
        # Check for SF2 driver patterns
        # Look for init code at $1000 and play at $1003
        if init_addr == 0x1000 and play_addr == 0x1003:
            # This looks like SF2-packed
            return 'SF2_PACKED'

    # Check for Laxity NewPlayer patterns
    # Laxity typically has specific init patterns
    laxity_pattern = bytes([0xA9, 0x00, 0x8D])  # LDA #$00, STA
    if laxity_pattern in music_data[:100]:
        return 'LAXITY'

    # Default to trying SF2 extraction
    return 'SF2_PACKED'

def extract_from_template(sid_path, output_sf2, template_sf2='G5/examples/Driver 11 Test - Arpeggio.sf2'):
    """Extract SF2 using a template SF2 file."""
    return extract_sf2_properly(str(sid_path), str(template_sf2), str(output_sf2))

def convert_laxity_to_sf2(sid_path, output_dir):
    """Convert Laxity SID to SF2 using sid_to_sf2.py."""
    try:
        result = subprocess.run(
            ['python', 'sid_to_sf2.py', str(sid_path), str(output_dir)],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)

def main():
    sidsf2_dir = Path('SIDSF2player')
    output_base = Path('output/SIDSF2player_Smart_Extraction')

    # Find all SID files
    sid_files = sorted(sidsf2_dir.glob('*.sid'))

    print('='*80)
    print('SMART SF2 EXTRACTION/CONVERSION FROM SIDSF2PLAYER FILES')
    print('='*80)
    print(f'\nFound {len(sid_files)} SID files')
    print()

    results = []

    for sid_file in sid_files:
        filename = sid_file.name
        print(f'\nProcessing: {filename}')
        print('-'*80)

        # Identify file type
        file_type = identify_sid_type(sid_file)
        print(f'  File type: {file_type}')

        # Create output directory
        output_dir = output_base / filename.replace('.sid', '')
        output_dir.mkdir(parents=True, exist_ok=True)

        output_sf2 = output_dir / f'{filename.replace(".sid", "_converted.sf2")}'

        # Check if we have a reference SF2
        if filename in SF2_REFERENCES:
            ref_sf2 = Path(SF2_REFERENCES[filename])
            if ref_sf2.exists():
                print(f'  Using reference: {ref_sf2.name}')
                try:
                    extract_sf2_properly(str(sid_file), str(ref_sf2), str(output_sf2))
                    print(f'  [OK] Extracted with reference to: {output_sf2}')
                    results.append((filename, file_type, 'SUCCESS', str(output_sf2)))
                    continue
                except Exception as e:
                    print(f'  [WARN] Reference extraction failed: {e}')

        # No reference - use appropriate method based on file type
        if file_type == 'LAXITY':
            print(f'  Converting Laxity SID to SF2...')
            success, output = convert_laxity_to_sf2(sid_file, output_dir)
            if success:
                # Find the generated SF2 file
                sf2_files = list(output_dir.glob('*.sf2'))
                if sf2_files:
                    print(f'  [OK] Converted Laxity to: {sf2_files[0]}')
                    results.append((filename, file_type, 'SUCCESS', str(sf2_files[0])))
                else:
                    print(f'  [ERROR] Conversion completed but no SF2 found')
                    results.append((filename, file_type, 'ERROR', 'No output file'))
            else:
                print(f'  [ERROR] Laxity conversion failed: {output}')
                results.append((filename, file_type, 'ERROR', 'Conversion failed'))

        elif file_type == 'SF2_PACKED':
            print(f'  Extracting SF2-packed using template...')
            try:
                extract_from_template(sid_file, output_sf2)
                print(f'  [OK] Extracted with template to: {output_sf2}')
                results.append((filename, file_type, 'SUCCESS', str(output_sf2)))
            except Exception as e:
                print(f'  [ERROR] Template extraction failed: {e}')
                results.append((filename, file_type, 'ERROR', str(e)))

        else:
            print(f'  [SKIP] Unknown file type')
            results.append((filename, file_type, 'SKIP', 'Unknown type'))

    # Summary
    print()
    print('='*80)
    print('EXTRACTION/CONVERSION SUMMARY')
    print('='*80)
    print()

    success_count = sum(1 for _, _, status, _ in results if status == 'SUCCESS')
    error_count = sum(1 for _, _, status, _ in results if status == 'ERROR')
    skip_count = sum(1 for _, _, status, _ in results if status == 'SKIP')

    print(f'Total files: {len(results)}')
    print(f'  [OK] Successful: {success_count}')
    print(f'  [ERROR] Errors: {error_count}')
    print(f'  [SKIP] Skipped: {skip_count}')
    print()

    # Details
    print('DETAILS:')
    print()
    print(f'{"Status":<8} {"Filename":<50} {"Type":<15} {"Output":<50}')
    print('-'*125)
    for filename, file_type, status, detail in results:
        icon = '[OK]' if status == 'SUCCESS' else '[ERROR]' if status == 'ERROR' else '[SKIP]'
        print(f'{icon:<8} {filename:<50} {file_type:<15} {detail[:47] if len(detail) > 47 else detail}')

    print()
    print('='*80)

if __name__ == '__main__':
    main()
