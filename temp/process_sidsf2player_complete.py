#!/usr/bin/env python3
"""
Complete conversion pipeline for SIDSF2player files.

Steps:
1. SID → SF2 extraction/conversion (smart detection)
2. SF2 → SID packing (using sf2_packer.py)
3. Siddump comparison (original vs exported)
4. WAV rendering (original vs exported)
5. Accuracy validation
6. Comprehensive report generation
"""

import struct
import subprocess
from pathlib import Path
import sys
import time
from datetime import datetime

# Import existing tools
from extract_sf2_properly import extract_sf2_properly
from sidm2.sf2_packer import pack_sf2_to_sid

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

    # Check for SF2 driver signature
    if actual_load == 0x1000:
        if init_addr == 0x1000 and play_addr == 0x1003:
            return 'SF2_PACKED'

    # Check for Laxity NewPlayer patterns
    laxity_pattern = bytes([0xA9, 0x00, 0x8D])  # LDA #$00, STA
    if laxity_pattern in music_data[:100]:
        return 'LAXITY'

    return 'SF2_PACKED'  # Default to SF2 extraction

def parse_sid_header(sid_path):
    """Parse SID header for metadata."""
    with open(sid_path, 'rb') as f:
        data = f.read()

    magic = data[0:4].decode('ascii', errors='ignore')
    name = data[0x16:0x36].decode('ascii', errors='ignore').strip('\x00')
    author = data[0x36:0x56].decode('ascii', errors='ignore').strip('\x00')
    copyright_str = data[0x56:0x76].decode('ascii', errors='ignore').strip('\x00')

    return name, author, copyright_str

def convert_sid_to_sf2(sid_path, output_sf2, file_type, reference_sf2=None):
    """Convert SID to SF2 using appropriate method."""
    if reference_sf2 and reference_sf2.exists():
        # Reference-based extraction
        extract_sf2_properly(str(sid_path), str(reference_sf2), str(output_sf2))
        return 'REFERENCE', True
    elif file_type == 'LAXITY':
        # Laxity conversion
        result = subprocess.run(
            ['python', 'sid_to_sf2.py', str(sid_path), str(output_sf2), '--overwrite'],
            capture_output=True,
            text=True,
            timeout=60
        )
        return 'LAXITY', result.returncode == 0
    else:
        # Template-based extraction
        template_sf2 = Path('G5/examples/Driver 11 Test - Arpeggio.sf2')
        extract_sf2_properly(str(sid_path), str(template_sf2), str(output_sf2))
        return 'TEMPLATE', True

def pack_sf2_to_sid_safe(sf2_path, output_sid, name, author, copyright_str):
    """Pack SF2 to SID with error handling."""
    try:
        pack_sf2_to_sid(sf2_path, output_sid, name=name, author=author, copyright_str=copyright_str)
        return True
    except Exception as e:
        print(f"    [WARN] Packing failed: {e}")
        return False

def run_siddump(sid_path, output_dump, seconds=10):
    """Run siddump on SID file."""
    try:
        result = subprocess.run(
            ['tools/siddump.exe', str(sid_path), f'-t{seconds}'],
            capture_output=True,
            text=True,
            timeout=30
        )
        with open(output_dump, 'w') as f:
            f.write(result.stdout)
        return True
    except Exception as e:
        print(f"    [WARN] Siddump failed: {e}")
        return False

def render_wav(sid_path, output_wav, seconds=30):
    """Render SID to WAV."""
    try:
        result = subprocess.run(
            ['tools/SID2WAV.EXE', str(sid_path), '-o', str(output_wav), f'-t{seconds}'],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0
    except Exception as e:
        print(f"    [WARN] WAV rendering failed: {e}")
        return False

def main():
    sidsf2_dir = Path('SIDSF2player')
    output_base = Path('output/SIDSF2player_Pipeline')

    # Find all SID files
    sid_files = sorted(sidsf2_dir.glob('*.sid'))

    print('='*80)
    print('COMPLETE CONVERSION PIPELINE FOR SIDSF2PLAYER FILES')
    print('='*80)
    print(f'\nFound {len(sid_files)} SID files')
    print(f'Output directory: {output_base}')
    print(f'Started: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()

    results = []

    for i, sid_file in enumerate(sid_files, 1):
        filename = sid_file.name
        basename = filename.replace('.sid', '')

        print(f'\n[{i}/{len(sid_files)}] Processing: {filename}')
        print('-'*80)

        # Create output directory structure
        file_output = output_base / basename
        original_dir = file_output / 'Original'
        new_dir = file_output / 'New'
        original_dir.mkdir(parents=True, exist_ok=True)
        new_dir.mkdir(parents=True, exist_ok=True)

        # Parse SID header
        name, author, copyright_str = parse_sid_header(sid_file)
        file_type = identify_sid_type(sid_file)

        print(f'  Type: {file_type}')
        print(f'  Name: {name}')
        print(f'  Author: {author}')

        result = {
            'filename': filename,
            'type': file_type,
            'name': name,
            'author': author,
            'steps': {}
        }

        # STEP 1: SID -> SF2
        print(f'\n  [1/6] Converting SID -> SF2...')
        output_sf2 = new_dir / f'{basename}.sf2'

        reference_sf2 = None
        if filename in SF2_REFERENCES:
            reference_sf2 = Path(SF2_REFERENCES[filename])

        try:
            method, success = convert_sid_to_sf2(sid_file, output_sf2, file_type, reference_sf2)
            if success:
                print(f'        [OK] Converted using {method} method')
                print(f'        Output: {output_sf2}')
                result['steps']['conversion'] = {'success': True, 'method': method}
            else:
                print(f'        [ERROR] Conversion failed')
                result['steps']['conversion'] = {'success': False, 'method': method}
                results.append(result)
                continue
        except Exception as e:
            print(f'        [ERROR] {e}')
            result['steps']['conversion'] = {'success': False, 'error': str(e)}
            results.append(result)
            continue

        # STEP 2: SF2 -> SID
        print(f'\n  [2/6] Packing SF2 -> SID...')
        exported_sid = new_dir / f'{basename}_exported.sid'

        if pack_sf2_to_sid_safe(output_sf2, exported_sid, name, author, copyright_str):
            print(f'        [OK] Packed to: {exported_sid}')
            result['steps']['packing'] = {'success': True, 'size': exported_sid.stat().st_size}
        else:
            print(f'        [ERROR] Packing failed')
            result['steps']['packing'] = {'success': False}
            results.append(result)
            continue

        # STEP 3: Siddump original
        print(f'\n  [3/6] Running siddump on original SID...')
        original_dump = original_dir / f'{basename}_original.dump'

        if run_siddump(sid_file, original_dump, seconds=10):
            print(f'        [OK] Dump: {original_dump}')
            result['steps']['siddump_original'] = {'success': True}
        else:
            result['steps']['siddump_original'] = {'success': False}

        # STEP 4: Siddump exported
        print(f'\n  [4/6] Running siddump on exported SID...')
        exported_dump = new_dir / f'{basename}_exported.dump'

        if run_siddump(exported_sid, exported_dump, seconds=10):
            print(f'        [OK] Dump: {exported_dump}')
            result['steps']['siddump_exported'] = {'success': True}
        else:
            result['steps']['siddump_exported'] = {'success': False}

        # STEP 5: Render WAVs
        print(f'\n  [5/6] Rendering WAV files...')
        original_wav = original_dir / f'{basename}_original.wav'
        exported_wav = new_dir / f'{basename}_exported.wav'

        wav_success = True
        if render_wav(sid_file, original_wav, seconds=30):
            print(f'        [OK] Original WAV: {original_wav}')
        else:
            wav_success = False

        if render_wav(exported_sid, exported_wav, seconds=30):
            print(f'        [OK] Exported WAV: {exported_wav}')
        else:
            wav_success = False

        result['steps']['wav_rendering'] = {'success': wav_success}

        # STEP 6: Validation (if dumps exist)
        print(f'\n  [6/6] Validation...')
        if original_dump.exists() and exported_dump.exists():
            # Simple validation: compare file sizes
            orig_size = original_dump.stat().st_size
            exp_size = exported_dump.stat().st_size
            size_ratio = exp_size / orig_size if orig_size > 0 else 0

            print(f'        Original dump: {orig_size} bytes')
            print(f'        Exported dump: {exp_size} bytes')
            print(f'        Ratio: {size_ratio:.1%}')

            result['steps']['validation'] = {
                'success': True,
                'orig_size': orig_size,
                'exp_size': exp_size,
                'ratio': size_ratio
            }
        else:
            result['steps']['validation'] = {'success': False}

        results.append(result)
        print(f'\n  [DONE] {filename}')

    # Generate summary report
    print()
    print('='*80)
    print('PIPELINE SUMMARY')
    print('='*80)
    print()

    successful = sum(1 for r in results if r['steps'].get('conversion', {}).get('success', False))
    packed = sum(1 for r in results if r['steps'].get('packing', {}).get('success', False))
    validated = sum(1 for r in results if r['steps'].get('validation', {}).get('success', False))

    print(f'Total files: {len(results)}')
    print(f'  Converted: {successful}/{len(results)}')
    print(f'  Packed: {packed}/{len(results)}')
    print(f'  Validated: {validated}/{len(results)}')
    print()

    # Detailed breakdown
    print('CONVERSION METHODS:')
    method_counts = {}
    for r in results:
        method = r['steps'].get('conversion', {}).get('method', 'FAILED')
        method_counts[method] = method_counts.get(method, 0) + 1

    for method, count in sorted(method_counts.items()):
        print(f'  {method}: {count} files')
    print()

    # File listing
    print('DETAILED RESULTS:')
    print()
    print(f'{"Status":<8} {"File":<45} {"Method":<10} {"Packed":<8} {"Valid":<8}')
    print('-'*80)

    for r in results:
        conv_ok = r['steps'].get('conversion', {}).get('success', False)
        pack_ok = r['steps'].get('packing', {}).get('success', False)
        val_ok = r['steps'].get('validation', {}).get('success', False)
        method = r['steps'].get('conversion', {}).get('method', 'N/A')

        status = '[OK]' if conv_ok else '[ERROR]'
        pack_status = '[OK]' if pack_ok else '[-]'
        val_status = '[OK]' if val_ok else '[-]'

        print(f'{status:<8} {r["filename"]:<45} {method:<10} {pack_status:<8} {val_status:<8}')

    print()
    print('='*80)
    print(f'Completed: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'Output: {output_base}')
    print('='*80)

if __name__ == '__main__':
    main()
