#!/usr/bin/env python3
"""
Complete SID Conversion Pipeline with Validation

This script implements the COMPLETE pipeline with ALL required steps:
1. SID → SF2 conversion
2. SF2 → SID packing
3. Siddump generation (original + exported)
4. WAV rendering (original + exported)
5. Hexdump generation (original SID + exported SID) - xxd format
6. SIDwinder trace generation (original + exported) - NEW: requires rebuilt SIDwinder
7. Info.txt generation with all metadata and analysis
8. Annotated disassembly generation (exported SID)
9. SIDwinder disassembly generation (exported SID)
10. Validation to ensure all expected files exist

Author: SIDM2 Project
Date: 2025-12-06
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

# Required files per conversion - separated by directory
NEW_FILES = [
    '{basename}.sf2',                    # Step 1: SID → SF2
    '{basename}_exported.sid',           # Step 2: SF2 → SID
    '{basename}_exported.dump',          # Step 3b: Siddump exported
    '{basename}_exported.wav',           # Step 4b: WAV exported
    '{basename}_exported.hex',           # Step 5b: Hexdump exported
    '{basename}_exported.txt',           # Step 6b: SIDwinder trace exported
    'info.txt',                          # Step 7: Complete conversion report
    '{basename}_exported_disassembly.md', # Step 8: Annotated disassembly
    '{basename}_exported_sidwinder.asm',  # Step 9: SIDwinder disassembly
]

ORIGINAL_FILES = [
    '{basename}_original.dump',          # Step 3a: Siddump original
    '{basename}_original.wav',           # Step 4a: WAV original
    '{basename}_original.hex',           # Step 5a: Hexdump original
    '{basename}_original.txt',           # Step 6a: SIDwinder trace original
    '{basename}_original_sidwinder.asm', # Step 9a: SIDwinder disassembly original
]

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

    # High load addresses indicate Laxity format
    if actual_load >= 0xA000:
        return 'LAXITY'

    if actual_load == 0x1000:
        if init_addr == 0x1000 and play_addr == 0x1003:
            return 'SF2_PACKED'

    laxity_pattern = bytes([0xA9, 0x00, 0x8D])
    if laxity_pattern in music_data[:100]:
        return 'LAXITY'

    return 'SF2_PACKED'

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
        extract_sf2_properly(str(sid_path), str(reference_sf2), str(output_sf2))
        return 'REFERENCE', True
    elif file_type == 'LAXITY':
        result = subprocess.run(
            ['python', 'sid_to_sf2.py', str(sid_path), str(output_sf2), '--overwrite'],
            capture_output=True,
            text=True,
            timeout=60
        )
        return 'LAXITY', result.returncode == 0
    else:
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
        siddump_tool = Path('tools') / 'siddump.exe'
        result = subprocess.run(
            [str(siddump_tool), str(sid_path), f'-t{seconds}'],
            capture_output=True,
            text=True,
            timeout=120
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
        sid2wav_tool = Path('tools') / 'SID2WAV.EXE'
        result = subprocess.run(
            [str(sid2wav_tool), str(sid_path), '-o', str(output_wav), f'-t{seconds}'],
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode == 0
    except Exception as e:
        print(f"    [WARN] WAV rendering failed: {e}")
        return False

def generate_hexdump(sid_path, output_hex):
    """Generate hexdump of SID file using xxd."""
    try:
        result = subprocess.run(
            ['xxd', str(sid_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        with open(output_hex, 'w') as f:
            f.write(result.stdout)
        return True
    except Exception as e:
        print(f"    [WARN] Hexdump failed: {e}")
        return False

def generate_sidwinder_trace(sid_path, output_trace, seconds=30):
    """Generate SIDwinder trace of SID register writes."""
    try:
        # Use absolute path for SIDwinder on Windows
        sidwinder_exe = Path('tools/SIDwinder.exe').absolute()
        # Use .txt extension for text format trace
        result = subprocess.run(
            [str(sidwinder_exe), f'-trace={output_trace}', f'-frames={seconds*50}', str(sid_path)],
            capture_output=True,
            text=True,
            timeout=120
        )
        # SIDwinder returns error code even on success due to generateOutput bug
        # Check if file was created instead
        return output_trace.exists() and output_trace.stat().st_size > 0
    except Exception as e:
        print(f"    [WARN] SIDwinder trace failed: {e}")
        return False

def generate_annotated_disassembly(sid_path, output_md):
    """Generate annotated disassembly using annotating_disassembler.py."""
    try:
        result = subprocess.run(
            ['python', 'annotating_disassembler.py', str(sid_path), str(output_md)],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0 and output_md.exists()
    except Exception as e:
        print(f"    [WARN] Disassembly generation failed: {e}")
        return False

def generate_sidwinder_disassembly(sid_path, output_asm):
    """Generate disassembly using SIDwinder."""
    try:
        # Use absolute path for SIDwinder on Windows
        sidwinder_exe = Path('tools/SIDwinder.exe').absolute()
        result = subprocess.run(
            [str(sidwinder_exe), '-disassemble', str(sid_path), str(output_asm)],
            capture_output=True,
            text=True,
            timeout=60
        )
        # SIDwinder has buggy exit codes, check file existence instead
        return output_asm.exists() and output_asm.stat().st_size > 0
    except Exception as e:
        print(f"    [WARN] SIDwinder disassembly failed: {e}")
        return False

def generate_info_txt_comprehensive(sid_path, sf2_path, output_dir):
    """Generate comprehensive info.txt using generate_info.py script."""
    try:
        # Use the existing comprehensive generate_info.py script
        result = subprocess.run(
            ['python', 'generate_info.py', str(sid_path), str(sf2_path), str(output_dir)],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0
    except Exception as e:
        print(f"    [WARN] Info generation failed: {e}")
        return False

def generate_info_txt(sid_path, sf2_path, exported_sid, output_dir, method, file_type):
    """Generate comprehensive info.txt file - DEPRECATED, use generate_info_txt_comprehensive."""
    try:
        # Parse SID header
        name, author, copyright_str = parse_sid_header(sid_path)

        with open(sid_path, 'rb') as f:
            data = f.read()

        magic = data[0:4].decode('ascii', errors='ignore')
        version = struct.unpack('>H', data[4:6])[0]
        load_addr = struct.unpack('>H', data[8:10])[0]
        init_addr = struct.unpack('>H', data[10:12])[0]
        play_addr = struct.unpack('>H', data[12:14])[0]
        songs = struct.unpack('>H', data[14:16])[0]
        start_song = struct.unpack('>H', data[16:18])[0]

        info_content = f"""================================================================================
SID to SF2 Complete Conversion Pipeline Report
================================================================================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Pipeline: Complete Round-Trip with Validation
Version: 1.0

================================================================================
Source File Information
================================================================================
File: {sid_path}
Format: {magic} v{version}
File Type: {file_type}

Title: {name}
Author: {author}
Copyright: {copyright_str}

Songs: {songs}
Start song: {start_song}
Load address: ${load_addr:04X}
Init address: ${init_addr:04X}
Play address: ${play_addr:04X}
Data size: {len(data):,} bytes

================================================================================
Conversion Results
================================================================================
Output SF2: {sf2_path.name}
Conversion Method: {method}
File Size: {sf2_path.stat().st_size if sf2_path.exists() else 0:,} bytes

Exported SID: {exported_sid.name if exported_sid else 'N/A'}
Export Size: {exported_sid.stat().st_size if exported_sid and exported_sid.exists() else 0:,} bytes

================================================================================
Pipeline Steps Completed
================================================================================

Step 1: SID -> SF2 Conversion
  Method: {method}
  Input:  {sid_path.name}
  Output: {sf2_path.name}
  Status: {'COMPLETE' if sf2_path.exists() else 'FAILED'}

Step 2: SF2 -> SID Packing
  Input:  {sf2_path.name}
  Output: {exported_sid.name if exported_sid else 'N/A'}
  Status: {'COMPLETE' if exported_sid and exported_sid.exists() else 'FAILED'}

Step 3: Siddump Register Capture
  Original: {sid_path.stem}_original.dump
  Exported: {sid_path.stem}_exported.dump
  Duration: 10 seconds (500 frames @ 50Hz)
  Status: Check individual files

Step 4: WAV Audio Rendering
  Original: {sid_path.stem}_original.wav
  Exported: {sid_path.stem}_exported.wav
  Format: 16-bit PCM, 44.1kHz
  Duration: 30 seconds
  Status: Check individual files

Step 5: Hexdump Generation
  Original: {sid_path.stem}_original.hex
  Exported: {sid_path.stem}_exported.hex
  Format: xxd hexadecimal dump
  Status: Check individual files

Step 6: Info Report Generation
  Output: info.txt
  Status: COMPLETE (you're reading it!)

================================================================================
Output File Structure
================================================================================

Original/ directory:
  - {sid_path.stem}_original.dump   (Siddump register capture)
  - {sid_path.stem}_original.wav    (30-second audio)
  - {sid_path.stem}_original.hex    (Hexadecimal dump)

New/ directory:
  - {sf2_path.name}                 (Converted SF2 file)
  - {exported_sid.name if exported_sid else 'N/A'}              (Exported SID file)
  - {sid_path.stem}_exported.dump   (Siddump register capture)
  - {sid_path.stem}_exported.wav    (30-second audio)
  - {sid_path.stem}_exported.hex    (Hexadecimal dump)
  - info.txt                        (This file)

================================================================================
Tools Used in Pipeline
================================================================================

Conversion Tools:
  - extract_sf2_properly.py / sid_to_sf2.py
    Purpose: SID -> SF2 conversion
    Method: {method}

  - sidm2/sf2_packer.py
    Purpose: SF2 -> SID packing
    Format: PSID v2

Analysis Tools:
  - tools/player-id.exe
    Purpose: Player type identification
    Result: {file_type}

  - tools/siddump.exe
    Purpose: SID register dump (6502 emulation)
    Output: Frame-by-frame register captures

  - tools/SID2WAV.EXE
    Purpose: Audio rendering
    Output: WAV files for listening comparison

Documentation Tools:
  - xxd
    Purpose: Hexadecimal dump
    Output: .hex files for binary analysis

  - complete_pipeline_with_validation.py
    Purpose: Orchestrate all pipeline steps
    Output: This info.txt file

================================================================================
Validation Status
================================================================================

Expected Files: {len(REQUIRED_FILES)}
Check output directories to verify all files were generated successfully.

For complete validation, ensure:
  [1] SF2 file opens in SID Factory II editor
  [2] Exported SID file plays in VICE emulator
  [3] Siddump files exist for both original and exported
  [4] WAV files exist for both original and exported
  [5] Hexdump files exist for both original and exported
  [6] This info.txt file contains complete information

================================================================================
Next Steps
================================================================================

1. Validation:
   - Compare original vs exported siddump files
   - Listen to original vs exported WAV files
   - Analyze hexdump differences

2. Accuracy Assessment:
   - Run accuracy validation scripts
   - Check register match percentages
   - Grade quality (EXCELLENT/GOOD/FAIR/POOR)

3. Manual Review:
   - Open SF2 in SID Factory II editor
   - Verify instruments, sequences, orderlists
   - Test in VICE emulator

================================================================================
Notes
================================================================================

- This is an automated conversion pipeline
- Results may require manual refinement
- Template-based extractions may have lower accuracy
- Reference-based extractions achieve 100% accuracy
- Laxity conversions are experimental

For questions or issues, check:
  - output/SIDSF2PLAYER_COMPLETE_PIPELINE_REPORT.md
  - docs/SF2_FORMAT_SPEC.md
  - README.md

================================================================================
End of Report
================================================================================
"""

        info_path = output_dir / 'info.txt'
        with open(info_path, 'w') as f:
            f.write(info_content)

        return True
    except Exception as e:
        print(f"    [WARN] Info.txt generation failed: {e}")
        return False

def validate_pipeline_completion(output_dir, basename):
    """Validate that all required files were generated."""
    expected_files = []
    missing_files = []

    # Check New/ directory
    new_dir = output_dir / 'New'
    for file_template in NEW_FILES:
        file_path = new_dir / file_template.format(basename=basename)
        expected_files.append(file_path)
        if not file_path.exists():
            missing_files.append(f'New/{file_path.name}')

    # Check Original/ directory
    orig_dir = output_dir / 'Original'
    for file_template in ORIGINAL_FILES:
        filename = file_template.format(basename=basename)
        file_path = orig_dir / filename
        expected_files.append(file_path)
        if not file_path.exists():
            missing_files.append(f'Original/{filename}')

    total = len(expected_files)
    success = total - len(missing_files)

    return {
        'total': total,
        'success': success,
        'missing': missing_files,
        'complete': len(missing_files) == 0
    }

def main():
    sidsf2_dir = Path('SIDSF2player')
    output_base = Path('output/SIDSF2player_Complete_Pipeline')

    sid_files = sorted(sidsf2_dir.glob('*.sid'))

    print('='*80)
    print('COMPLETE SID CONVERSION PIPELINE WITH VALIDATION')
    print('='*80)
    print(f'\nFound {len(sid_files)} SID files')
    print(f'Output directory: {output_base}')
    print(f'Started: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()
    print('Pipeline Steps:')
    print('  [1] SID -> SF2 conversion')
    print('  [2] SF2 -> SID packing')
    print('  [3] Siddump generation (original + exported)')
    print('  [4] WAV rendering (original + exported)')
    print('  [5] Hexdump generation (original + exported)')
    print('  [6] SIDwinder trace generation (original + exported)')
    print('  [7] Info.txt report generation')
    print('  [8] Annotated disassembly generation')
    print('  [9] SIDwinder disassembly generation (original + exported)')
    print('  [10] Validation check')
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

        result = {
            'filename': filename,
            'type': file_type,
            'name': name,
            'steps': {}
        }

        # STEP 1: SID -> SF2
        print(f'\n  [1/12] Converting SID -> SF2...')
        output_sf2 = new_dir / f'{basename}.sf2'

        reference_sf2 = None
        if filename in SF2_REFERENCES:
            reference_sf2 = Path(SF2_REFERENCES[filename])

        try:
            method, success = convert_sid_to_sf2(sid_file, output_sf2, file_type, reference_sf2)
            if success:
                print(f'        [OK] Method: {method}')
                result['steps']['conversion'] = {'success': True, 'method': method}
            else:
                print(f'        [ERROR] Conversion failed')
                result['steps']['conversion'] = {'success': False}
                results.append(result)
                continue
        except Exception as e:
            print(f'        [ERROR] {e}')
            result['steps']['conversion'] = {'success': False}
            results.append(result)
            continue

        # STEP 2: SF2 -> SID
        print(f'\n  [2/12] Packing SF2 -> SID...')
        exported_sid = new_dir / f'{basename}_exported.sid'

        if pack_sf2_to_sid_safe(output_sf2, exported_sid, name, author, copyright_str):
            print(f'        [OK] Size: {exported_sid.stat().st_size} bytes')
            result['steps']['packing'] = {'success': True}
        else:
            print(f'        [ERROR] Packing failed')
            result['steps']['packing'] = {'success': False}

        # STEP 3: Siddump
        print(f'\n  [3/12] Generating siddumps...')
        orig_dump = original_dir / f'{basename}_original.dump'
        exp_dump = new_dir / f'{basename}_exported.dump'

        orig_dump_ok = run_siddump(sid_file, orig_dump, seconds=10)
        exp_dump_ok = run_siddump(exported_sid, exp_dump, seconds=10) if exported_sid.exists() else False

        print(f'        Original: {"[OK]" if orig_dump_ok else "[ERROR]"}')
        print(f'        Exported: {"[OK]" if exp_dump_ok else "[ERROR]"}')
        result['steps']['siddump'] = {'orig': orig_dump_ok, 'exp': exp_dump_ok}

        # STEP 4: WAV
        print(f'\n  [4/12] Rendering WAV files...')
        orig_wav = original_dir / f'{basename}_original.wav'
        exp_wav = new_dir / f'{basename}_exported.wav'

        orig_wav_ok = render_wav(sid_file, orig_wav, seconds=30)
        exp_wav_ok = render_wav(exported_sid, exp_wav, seconds=30) if exported_sid.exists() else False

        print(f'        Original: {"[OK]" if orig_wav_ok else "[ERROR]"}')
        print(f'        Exported: {"[OK]" if exp_wav_ok else "[ERROR]"}')
        result['steps']['wav'] = {'orig': orig_wav_ok, 'exp': exp_wav_ok}

        # STEP 5: Hexdump
        print(f'\n  [5/12] Generating hexdumps...')
        orig_hex = original_dir / f'{basename}_original.hex'
        exp_hex = new_dir / f'{basename}_exported.hex'

        orig_hex_ok = generate_hexdump(sid_file, orig_hex)
        exp_hex_ok = generate_hexdump(exported_sid, exp_hex) if exported_sid.exists() else False

        print(f'        Original: {"[OK]" if orig_hex_ok else "[ERROR]"}')
        print(f'        Exported: {"[OK]" if exp_hex_ok else "[ERROR]"}')
        result['steps']['hexdump'] = {'orig': orig_hex_ok, 'exp': exp_hex_ok}

        # STEP 6: SIDwinder Trace
        print(f'\n  [6/12] Generating SIDwinder traces...')
        orig_trace = original_dir / f'{basename}_original.txt'
        exp_trace = new_dir / f'{basename}_exported.txt'

        orig_trace_ok = generate_sidwinder_trace(sid_file, orig_trace, seconds=30)
        exp_trace_ok = generate_sidwinder_trace(exported_sid, exp_trace, seconds=30) if exported_sid.exists() else False

        print(f'        Original: {"[OK]" if orig_trace_ok else "[WARN - needs rebuilt SIDwinder]"}')
        print(f'        Exported: {"[OK]" if exp_trace_ok else "[WARN - needs rebuilt SIDwinder]"}')
        result['steps']['trace'] = {'orig': orig_trace_ok, 'exp': exp_trace_ok}

        # STEP 7: Info.txt
        print(f'\n  [7/12] Generating info.txt...')
        info_ok = generate_info_txt_comprehensive(sid_file, output_sf2, new_dir)
        print(f'        {"[OK]" if info_ok else "[ERROR]"}')
        result['steps']['info'] = {'success': info_ok}

        # STEP 8: Annotated Disassembly
        print(f'\n  [8/12] Generating annotated disassembly...')
        disasm_md = new_dir / f'{basename}_exported_disassembly.md'
        disasm_ok = generate_annotated_disassembly(exported_sid, disasm_md) if exported_sid.exists() else False
        print(f'        {"[OK]" if disasm_ok else "[ERROR]"}')
        result['steps']['disassembly'] = {'success': disasm_ok}

        # STEP 9: SIDwinder Disassembly
        print(f'\n  [9/12] Generating SIDwinder disassembly...')
        orig_sidwinder_asm = original_dir / f'{basename}_original_sidwinder.asm'
        sidwinder_asm = new_dir / f'{basename}_exported_sidwinder.asm'

        orig_sidwinder_ok = generate_sidwinder_disassembly(sid_file, orig_sidwinder_asm)
        exp_sidwinder_ok = generate_sidwinder_disassembly(exported_sid, sidwinder_asm) if exported_sid.exists() else False

        print(f'        Original: {"[OK]" if orig_sidwinder_ok else "[ERROR]"}')
        print(f'        Exported: {"[OK]" if exp_sidwinder_ok else "[ERROR]"}')
        result['steps']['sidwinder_disasm'] = {'orig': orig_sidwinder_ok, 'exp': exp_sidwinder_ok}

        # STEP 10: Validation
        print(f'\n  [10/12] Validating completion...')
        validation = validate_pipeline_completion(file_output, basename)
        result['validation'] = validation

        print(f'        Files: {validation["success"]}/{validation["total"]}')
        if validation['missing']:
            print(f'        Missing: {", ".join(validation["missing"][:3])}...')
        print(f'        Status: {"[COMPLETE]" if validation["complete"] else "[PARTIAL]"}')

        results.append(result)

    # Final summary
    print()
    print('='*80)
    print('PIPELINE SUMMARY')
    print('='*80)
    print()

    complete = sum(1 for r in results if r.get('validation', {}).get('complete', False))
    partial = len(results) - complete

    print(f'Total files: {len(results)}')
    print(f'  Complete: {complete}/{len(results)}')
    print(f'  Partial:  {partial}/{len(results)}')
    print()

    print('='*80)
    print(f'Completed: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'Output: {output_base}')
    print('='*80)

if __name__ == '__main__':
    main()
