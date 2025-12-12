#!/usr/bin/env python3
"""
Single-file Complete SID Conversion Pipeline
Fast testing version of complete_pipeline_with_validation.py for a single SID file.
All 10 steps identical to full pipeline, just processes one file instead of batch.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
import struct
import time

# Import packer from sidm2
sys.path.insert(0, str(Path(__file__).parent))
from sidm2.sf2_packer import pack_sf2_to_sid
from scripts.extract_sf2_properly import extract_sf2_properly

# SF2 references for files that have known reference SF2s
SF2_REFERENCES = {
    'Driver 11 Test - Arpeggio.sid': 'G5/examples/Driver 11 Test - Arpeggio.sf2',
    'Driver 11 Test - Filter.sid': 'G5/examples/Driver 11 Test - Filter.sf2',
}

# Required files for validation
REQUIRED_FILES = [
    'New/{}_exported.dump',
    'New/{}_exported.hex',
    'New/{}_exported.sid',
    'New/{}_exported.txt',
    'New/{}_exported_disassembly.md',
    'New/{}_exported_sidwinder.asm',
    'New/{}.sf2',
    'New/{}.sid',  # Original SID copy
    'New/info.txt',
    'Original/{}_original.dump',
    'Original/{}_original.hex',
    'Original/{}_original.txt',
    'Original/{}_original.wav',
    'Original/{}_original_sidwinder.asm',
]

def identify_sid_type(sid_path):
    """Identify if SID is SF2-packed or Laxity format."""
    with open(sid_path, 'rb') as f:
        data = f.read()

    # Read header
    load_addr = struct.unpack('>H', data[8:10])[0]
    init_addr = struct.unpack('>H', data[10:12])[0]
    play_addr = struct.unpack('>H', data[12:14])[0]

    # Handle load address = 0 (use first 2 bytes of data)
    if load_addr == 0:
        actual_load = struct.unpack('<H', data[0x7C:0x7E])[0]
    else:
        actual_load = load_addr

    # SF2-packed files: load=$1000, init=$1000, play=$1003
    if actual_load == 0x1000 and init_addr == 0x1000 and play_addr == 0x1003:
        return 'SF2_PACKED'

    # Laxity files: load >= $A000 or load=$1000 with different play address
    if actual_load >= 0xA000:
        return 'LAXITY'
    if actual_load == 0x1000 and play_addr != 0x1003:
        return 'LAXITY'

    return 'UNKNOWN'

def parse_sid_header(sid_path):
    """Parse SID header for metadata."""
    with open(sid_path, 'rb') as f:
        data = f.read()

    name = data[0x16:0x36].decode('latin-1', errors='replace').rstrip('\x00')
    author = data[0x36:0x56].decode('latin-1', errors='replace').rstrip('\x00')
    copyright_str = data[0x56:0x76].decode('latin-1', errors='replace').rstrip('\x00')

    return name, author, copyright_str

def convert_sid_to_sf2(sid_path, output_sf2, file_type, reference_sf2=None):
    """Convert SID to SF2 using appropriate method (matches full pipeline)."""
    if file_type == 'SF2_PACKED' and reference_sf2 and reference_sf2.exists():
        extract_sf2_properly(str(sid_path), str(output_sf2), str(reference_sf2))
        return 'REFERENCE', True
    elif file_type == 'SF2_PACKED':
        extract_sf2_properly(str(sid_path), str(output_sf2), None)
        return 'TEMPLATE', True
    elif file_type == 'LAXITY':
        result = subprocess.run(
            ['python', 'sid_to_sf2.py', str(sid_path), str(output_sf2)],
            capture_output=True, text=True
        )
        # Check if output file was created as success indicator
        success = output_sf2.exists() and output_sf2.stat().st_size > 1000
        return 'LAXITY', success
    else:
        return 'UNKNOWN', False

def pack_sf2_to_sid_safe(sf2_path, output_sid, name, author, copyright_str):
    """Pack SF2 to SID with error handling (matches full pipeline)."""
    try:
        pack_sf2_to_sid(str(sf2_path), str(output_sid), name, author, copyright_str)
        return output_sid.exists()
    except Exception as e:
        print(f'        Pack error: {e}')
        return False

def run_siddump(sid_path, output_dump, seconds=10):
    """Run siddump tool (matches full pipeline)."""
    try:
        siddump_tool = Path('tools') / 'siddump.exe'
        result = subprocess.run(
            [str(siddump_tool), str(sid_path), '-t', str(seconds)],
            capture_output=True,
            text=True,
            timeout=120
        )
        with open(output_dump, 'w') as f:
            f.write(result.stdout)
        return output_dump.exists() and output_dump.stat().st_size > 0
    except Exception as e:
        print(f'    [WARN] Siddump failed: {e}')
        return False

def render_wav(sid_path, output_wav, seconds=30):
    """Render SID to WAV (matches full pipeline)."""
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
        print(f'    [WARN] WAV rendering failed: {e}')
        return False

def generate_hexdump(sid_path, output_hex):
    """Generate hexdump of SID file using xxd (matches full pipeline)."""
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
        print(f'    [WARN] Hexdump failed: {e}')
        return False

def generate_sidwinder_trace(sid_path, output_trace, seconds=30):
    """Generate SIDwinder trace of SID register writes (matches full pipeline)."""
    try:
        sidwinder_exe = Path('tools/SIDwinder.exe').absolute()
        result = subprocess.run(
            [str(sidwinder_exe), f'-trace={output_trace}', f'-frames={seconds*50}', str(sid_path)],
            capture_output=True,
            text=True,
            timeout=120
        )
        return output_trace.exists() and output_trace.stat().st_size > 0
    except Exception as e:
        print(f'    [WARN] SIDwinder trace failed: {e}')
        return False

def generate_annotated_disassembly(sid_path, output_md):
    """Generate annotated disassembly using annotating_disassembler.py (matches full pipeline)."""
    try:
        result = subprocess.run(
            ['python', 'annotating_disassembler.py', str(sid_path), str(output_md)],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0 and output_md.exists()
    except Exception as e:
        print(f'    [WARN] Disassembly generation failed: {e}')
        return False

def generate_sidwinder_disassembly(sid_path, output_asm):
    """Generate disassembly using SIDwinder (matches full pipeline)."""
    try:
        sidwinder_exe = Path('tools/SIDwinder.exe').absolute()
        result = subprocess.run(
            [str(sidwinder_exe), '-disassemble', str(sid_path), str(output_asm)],
            capture_output=True,
            text=True,
            timeout=60
        )
        return output_asm.exists() and output_asm.stat().st_size > 0
    except Exception as e:
        print(f'    [WARN] SIDwinder disassembly failed: {e}')
        return False

def generate_info_txt_comprehensive(sid_path, sf2_path, output_dir):
    """Generate comprehensive info.txt using generate_info.py script (matches full pipeline)."""
    try:
        result = subprocess.run(
            ['python', 'generate_info.py', str(sid_path), str(sf2_path), str(output_dir)],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0
    except Exception as e:
        print(f'    [WARN] Info generation failed: {e}')
        return False

def validate_pipeline_completion(output_dir, basename):
    """Validate that all required files were generated (matches full pipeline)."""
    missing_files = []
    for file_pattern in REQUIRED_FILES:
        file_path = output_dir / file_pattern.format(basename)
        if not file_path.exists():
            missing_files.append(file_pattern.format(basename))

    total = len(REQUIRED_FILES)
    success = total - len(missing_files)

    return {
        'total': total,
        'success': success,
        'missing': missing_files,
        'complete': len(missing_files) == 0
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python pipeline_single.py <sid_file>")
        print("\nExample:")
        print("  python pipeline_single.py SID/Stinsens_Last_Night_of_89.sid")
        print("  python pipeline_single.py SIDSF2player/Angular.sid")
        sys.exit(1)

    sid_file = Path(sys.argv[1])
    if not sid_file.exists():
        print(f"ERROR: File not found: {sid_file}")
        sys.exit(1)

    filename = sid_file.name
    basename = filename.replace('.sid', '')
    output_base = Path('output/Pipeline_Single')

    print('='*80)
    print('SINGLE-FILE COMPLETE PIPELINE - FAST TESTING')
    print('='*80)
    print(f'\nInput: {sid_file}')
    print(f'Output: {output_base / basename}')
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

    # Create output directory structure
    file_output = output_base / basename
    original_dir = file_output / 'Original'
    new_dir = file_output / 'New'
    original_dir.mkdir(parents=True, exist_ok=True)
    new_dir.mkdir(parents=True, exist_ok=True)

    # Parse SID header
    name, author, copyright_str = parse_sid_header(sid_file)
    file_type = identify_sid_type(sid_file)

    print(f'Type: {file_type}')
    print(f'Name: {name}')
    print()

    start_time = time.time()

    # STEP 1: SID -> SF2
    print(f'[1/10] Converting SID -> SF2...')
    output_sf2 = new_dir / f'{basename}.sf2'

    reference_sf2 = None
    if filename in SF2_REFERENCES:
        reference_sf2 = Path(SF2_REFERENCES[filename])

    method, success = convert_sid_to_sf2(sid_file, output_sf2, file_type, reference_sf2)
    if success:
        print(f'        [OK] Method: {method}')
    else:
        print(f'        [ERROR] Conversion failed')
        sys.exit(1)

    # STEP 2: SF2 -> SID
    print(f'\n[2/10] Packing SF2 -> SID...')
    exported_sid = new_dir / f'{basename}_exported.sid'

    if pack_sf2_to_sid_safe(output_sf2, exported_sid, name, author, copyright_str):
        print(f'        [OK] Size: {exported_sid.stat().st_size} bytes')
    else:
        print(f'        [ERROR] Packing failed')

    # Copy original SID to New/ directory (ADDED - matches full pipeline)
    original_sid_copy = new_dir / f'{basename}.sid'
    import shutil
    shutil.copy2(sid_file, original_sid_copy)

    # STEP 3: Siddump
    print(f'\n[3/10] Generating siddumps...')
    orig_dump = original_dir / f'{basename}_original.dump'
    exp_dump = new_dir / f'{basename}_exported.dump'

    orig_dump_ok = run_siddump(sid_file, orig_dump, seconds=10)
    exp_dump_ok = run_siddump(exported_sid, exp_dump, seconds=10) if exported_sid.exists() else False

    print(f'        Original: {"[OK]" if orig_dump_ok else "[ERROR]"}')
    print(f'        Exported: {"[OK]" if exp_dump_ok else "[ERROR]"}')

    # STEP 4: WAV
    print(f'\n[4/10] Rendering WAV files...')
    orig_wav = original_dir / f'{basename}_original.wav'
    exp_wav = new_dir / f'{basename}_exported.wav'

    # Only render original WAV (exported WAV causes same issues as full pipeline)
    orig_wav_ok = render_wav(sid_file, orig_wav, seconds=30)
    print(f'        Original: {"[OK]" if orig_wav_ok else "[ERROR]"}')
    print(f'        Exported: [SKIPPED - same as full pipeline]')

    # STEP 5: Hexdump
    print(f'\n[5/10] Generating hexdumps...')
    orig_hex = original_dir / f'{basename}_original.hex'
    exp_hex = new_dir / f'{basename}_exported.hex'

    orig_hex_ok = generate_hexdump(sid_file, orig_hex)
    exp_hex_ok = generate_hexdump(exported_sid, exp_hex) if exported_sid.exists() else False

    print(f'        Original: {"[OK]" if orig_hex_ok else "[ERROR]"}')
    print(f'        Exported: {"[OK]" if exp_hex_ok else "[ERROR]"}')

    # STEP 6: SIDwinder Trace
    print(f'\n[6/10] Generating SIDwinder traces...')
    orig_trace = original_dir / f'{basename}_original.txt'
    exp_trace = new_dir / f'{basename}_exported.txt'

    orig_trace_ok = generate_sidwinder_trace(sid_file, orig_trace, seconds=30)
    exp_trace_ok = generate_sidwinder_trace(exported_sid, exp_trace, seconds=30) if exported_sid.exists() else False

    print(f'        Original: {"[OK]" if orig_trace_ok else "[WARN - needs rebuilt SIDwinder]"}')
    print(f'        Exported: {"[OK]" if exp_trace_ok else "[WARN - needs rebuilt SIDwinder]"}')

    # STEP 7: Info.txt
    print(f'\n[7/10] Generating info.txt...')
    info_ok = generate_info_txt_comprehensive(sid_file, output_sf2, new_dir)
    print(f'        {"[OK]" if info_ok else "[ERROR]"}')

    # STEP 8: Annotated Disassembly
    print(f'\n[8/10] Generating annotated disassembly...')
    disasm_md = new_dir / f'{basename}_exported_disassembly.md'
    disasm_ok = generate_annotated_disassembly(exported_sid, disasm_md) if exported_sid.exists() else False
    print(f'        {"[OK]" if disasm_ok else "[ERROR]"}')

    # STEP 9: SIDwinder Disassembly
    print(f'\n[9/10] Generating SIDwinder disassembly...')
    orig_sidwinder_asm = original_dir / f'{basename}_original_sidwinder.asm'
    sidwinder_asm = new_dir / f'{basename}_exported_sidwinder.asm'

    orig_sidwinder_ok = generate_sidwinder_disassembly(sid_file, orig_sidwinder_asm)
    exp_sidwinder_ok = generate_sidwinder_disassembly(exported_sid, sidwinder_asm) if exported_sid.exists() else False

    print(f'        Original: {"[OK]" if orig_sidwinder_ok else "[ERROR]"}')
    print(f'        Exported: {"[OK]" if exp_sidwinder_ok else "[ERROR]"}')

    # STEP 10: Validation
    print(f'\n[10/10] Validating completion...')
    validation = validate_pipeline_completion(file_output, basename)

    print(f'        Files: {validation["success"]}/{validation["total"]}')
    if validation['missing']:
        print(f'        Missing: {", ".join(validation["missing"][:3])}...')
    print(f'        Status: {"[COMPLETE]" if validation["complete"] else "[PARTIAL]"}')

    # Final summary
    elapsed = time.time() - start_time
    print()
    print('='*80)
    print('PIPELINE COMPLETE')
    print('='*80)
    print(f'Time: {elapsed:.1f} seconds')
    print(f'Output: {file_output}')
    print(f'Files: {validation["success"]}/{validation["total"]} generated')
    print(f'Status: {"COMPLETE" if validation["complete"] else "PARTIAL"}')
    print('='*80)

if __name__ == '__main__':
    main()
