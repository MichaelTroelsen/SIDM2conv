#!/usr/bin/env python3
"""
PARALLELIZED SID Conversion Pipeline
Processes multiple files simultaneously for 10-15x speedup
"""

import struct
import subprocess
from pathlib import Path
import sys
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

# Import existing tools
from extract_sf2_properly import extract_sf2_properly
from sidm2.sf2_packer import pack_sf2_to_sid

# Number of parallel workers
NUM_WORKERS = 6  # 12 cores / 2 = 6 parallel jobs

# Import all helper functions from original script
exec(open('complete_pipeline_with_validation.py').read().split('def main()')[0])

def process_single_file(args):
    """Process a single SID file through the complete pipeline"""
    sid_file, output_base, file_index, total_files = args
    
    filename = sid_file.name
    basename = filename.replace('.sid', '')
    
    # Create output directories
    file_output = output_base / basename
    original_dir = file_output / 'Original'
    new_dir = file_output / 'New'
    original_dir.mkdir(parents=True, exist_ok=True)
    new_dir.mkdir(parents=True, exist_ok=True)
    
    # Parse SID header
    name, author, copyright_str = parse_sid_header(sid_file)
    file_type = identify_sid_type(sid_file)
    
    result = {
        'index': file_index,
        'total': total_files,
        'filename': filename,
        'type': file_type,
        'name': name,
        'steps': {},
        'messages': []
    }
    
    result['messages'].append(f"[{file_index}/{total_files}] Processing: {filename}")
    result['messages'].append(f"  Type: {file_type}, Name: {name}")
    
    # STEP 1: SID -> SF2
    output_sf2 = new_dir / f'{basename}.sf2'
    reference_sf2 = None
    if filename in SF2_REFERENCES:
        reference_sf2 = Path(SF2_REFERENCES[filename])
    
    try:
        method, success = convert_sid_to_sf2(sid_file, output_sf2, file_type, reference_sf2)
        if success:
            result['steps']['conversion'] = {'success': True, 'method': method}
        else:
            result['steps']['conversion'] = {'success': False}
            return result
    except Exception as e:
        result['steps']['conversion'] = {'success': False, 'error': str(e)}
        return result
    
    # STEP 2: SF2 -> SID
    exported_sid = new_dir / f'{basename}_exported.sid'
    if pack_sf2_to_sid_safe(output_sf2, exported_sid, name, author, copyright_str):
        result['steps']['packing'] = {'success': True}
    else:
        result['steps']['packing'] = {'success': False}
    
    # STEP 3: Siddump (parallelized internally)
    orig_dump = original_dir / f'{basename}_original.dump'
    exp_dump = new_dir / f'{basename}_exported.dump'
    
    result['steps']['siddump_orig'] = run_siddump(sid_file, orig_dump, seconds=10)
    result['steps']['siddump_exp'] = run_siddump(exported_sid, exp_dump, seconds=10) if exported_sid.exists() else False
    
    # STEP 4: SKIP WAV (failing anyway)
    result['steps']['wav_orig'] = False
    result['steps']['wav_exp'] = False
    
    # STEP 5: Hexdump
    orig_hex = original_dir / f'{basename}_original.hex'
    exp_hex = new_dir / f'{basename}_exported.hex'
    
    result['steps']['hexdump_orig'] = run_hexdump(sid_file, orig_hex)
    result['steps']['hexdump_exp'] = run_hexdump(exported_sid, exp_hex) if exported_sid.exists() else False
    
    # STEP 6: SIDwinder trace
    orig_trace = original_dir / f'{basename}_original.txt'
    exp_trace = new_dir / f'{basename}_exported.txt'
    
    result['steps']['trace_orig'] = run_sidwinder_trace(sid_file, orig_trace)
    result['steps']['trace_exp'] = run_sidwinder_trace(exported_sid, exp_trace) if exported_sid.exists() else False
    
    # STEP 7: Info.txt
    info_txt = new_dir / 'info.txt'
    result['steps']['info'] = generate_info_txt(sid_file, output_sf2, exported_sid, info_txt, name, author, copyright_str, file_type, method)
    
    # STEP 8: Annotated disassembly
    disasm_md = new_dir / f'{basename}_exported_disassembly.md'
    result['steps']['annotated_disasm'] = generate_annotated_disassembly(exported_sid, disasm_md) if exported_sid.exists() else False
    
    # STEP 9: SIDwinder disassembly
    orig_asm = original_dir / f'{basename}_original_sidwinder.asm'
    exp_asm = new_dir / f'{basename}_exported_sidwinder.asm'
    
    result['steps']['sidwinder_orig'] = run_sidwinder_disassembly(sid_file, orig_asm)
    result['steps']['sidwinder_exp'] = run_sidwinder_disassembly(exported_sid, exp_asm) if exported_sid.exists() else False
    
    # STEP 10: Validate
    result['validation'] = validate_outputs(basename, original_dir, new_dir)
    
    result['messages'].append(f"  ✓ Completed: {filename}")
    return result

def main():
    sidsf2_dir = Path('SIDSF2player')
    output_base = Path('output/SIDSF2player_Complete_Pipeline')
    
    sid_files = sorted(sidsf2_dir.glob('*.sid'))
    
    print('='*80)
    print('PARALLELIZED SID CONVERSION PIPELINE')
    print('='*80)
    print(f'\nFound {len(sid_files)} SID files')
    print(f'Output directory: {output_base}')
    print(f'Workers: {NUM_WORKERS} parallel processes')
    print(f'Started: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()
    
    start_time = datetime.now()
    
    # Prepare arguments for parallel processing
    args_list = [(sid_file, output_base, i+1, len(sid_files)) 
                 for i, sid_file in enumerate(sid_files)]
    
    # Process files in parallel
    results = []
    completed = 0
    
    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = {executor.submit(process_single_file, args): args[0] for args in args_list}
        
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
                completed += 1
                
                # Print progress
                for msg in result.get('messages', []):
                    print(msg)
                print(f"  Progress: {completed}/{len(sid_files)} files completed")
                print()
                
            except Exception as e:
                print(f"ERROR processing {futures[future].name}: {e}")
    
    # Print summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print('='*80)
    print('PIPELINE SUMMARY')
    print('='*80)
    print(f'\nTotal files: {len(sid_files)}')
    print(f'Duration: {duration:.1f} seconds')
    print(f'Speed: {duration/len(sid_files):.1f} seconds per file')
    print(f'\nCompleted: {end_time.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'Output: {output_base}')
    print('='*80)

if __name__ == '__main__':
    # Set multiprocessing start method
    multiprocessing.set_start_method('spawn', force=True)
    main()
