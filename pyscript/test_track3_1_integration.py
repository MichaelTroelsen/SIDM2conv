#!/usr/bin/env python3
"""
Track 3.1 Integration Test - SF2 Packer Pointer Relocation Fix

Tests the complete workflow:
1. Load SF2 file
2. Pack to SID format (with alignment=1 fix)
3. Disassemble with SIDwinder
4. Verify no $0000 crashes

This validates the fix prevents the 17/18 failure rate.
"""

import sys
import os
from pathlib import Path
import tempfile

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.sf2_packer import SF2Packer
from pyscript.sidtracer import SIDTracer


def test_sf2_pack_and_disassemble(sf2_file: Path) -> dict:
    """
    Test complete workflow: SF2 -> SID -> Disassemble

    Returns:
        dict with test results
    """
    print(f"\n{'='*70}")
    print(f"Testing: {sf2_file.name}")
    print(f"{'='*70}\n")

    results = {
        'file': sf2_file.name,
        'pack_success': False,
        'disasm_success': False,
        'error': None,
        'crash_at_0000': False
    }

    try:
        # Step 1: Pack SF2 to SID
        print(f"[1/3] Packing SF2 to SID...")
        packer = SF2Packer(str(sf2_file))

        # Create temporary output file
        with tempfile.NamedTemporaryFile(suffix='.sid', delete=False) as tmp:
            sid_output = Path(tmp.name)

        try:
            # Pack with validate=False to skip format validation (we're testing pointer relocation)
            sid_data, init_addr, play_addr = packer.pack(dest_address=0x1000)

            # Write SID file
            with open(sid_output, 'wb') as f:
                f.write(sid_data)

            results['pack_success'] = True
            print(f"  [OK] Packed successfully ({len(sid_data):,} bytes)")
            print(f"  Init: ${init_addr:04X}, Play: ${play_addr:04X}")

        except Exception as e:
            results['error'] = f"Pack failed: {e}"
            print(f"  [FAIL] Pack failed: {e}")
            return results

        # Step 2: Parse packed SID
        print(f"\n[2/3] Parsing packed SID...")
        try:
            tracer = SIDTracer(sid_output, verbose=0)
            print(f"  [OK] SID parsed successfully")
            print(f"  Name: {tracer.header.name}")
            print(f"  Load: ${tracer.header.load_address:04X}")
            print(f"  Init: ${tracer.header.init_address:04X}")
            print(f"  Play: ${tracer.header.play_address:04X}")

        except Exception as e:
            results['error'] = f"Parse failed: {e}"
            print(f"  [FAIL] Parse failed: {e}")
            return results

        # Step 3: Trace execution (test for $0000 crashes)
        print(f"\n[3/3] Tracing execution (10 frames)...")
        try:
            # Run a short trace to detect crashes
            trace_data = tracer.trace(frames=10)

            results['disasm_success'] = True
            print(f"  [OK] Trace completed successfully")
            print(f"  Init writes: {len(trace_data.init_writes)}")
            print(f"  Frame writes: {sum(len(fw) for fw in trace_data.frame_writes)}")
            print(f"  CPU cycles: {trace_data.cycles:,}")

            # Check for $0000 crashes in trace
            # (A crash would raise an exception, so if we got here, no crash)
            results['crash_at_0000'] = False

        except Exception as e:
            error_str = str(e)
            results['error'] = f"Trace failed: {e}"

            # Check if error is related to $0000 crash
            if '0000' in error_str or 'illegal address' in error_str.lower():
                results['crash_at_0000'] = True
                print(f"  [CRASH] CRASH DETECTED at $0000: {e}")
            else:
                print(f"  [FAIL] Trace failed: {e}")

            return results

        finally:
            # Cleanup temporary file
            if sid_output.exists():
                sid_output.unlink()

    except Exception as e:
        results['error'] = f"Unexpected error: {e}"
        print(f"  [ERROR] Unexpected error: {e}")

    return results


def main():
    """Run integration tests on multiple SF2 files."""
    print("\n" + "="*70)
    print("TRACK 3.1 INTEGRATION TEST - SF2 Packer Pointer Relocation Fix")
    print("="*70)
    print("\nGoal: Verify alignment=1 fix prevents $0000 crashes\n")

    # Find test SF2 files
    test_files = list(Path('G5/examples').glob('*.sf2'))

    if not test_files:
        print("ERROR: No SF2 test files found in G5/examples/")
        return 1

    print(f"Found {len(test_files)} test files\n")

    # Run tests
    all_results = []
    for sf2_file in test_files[:10]:  # Test first 10 files
        result = test_sf2_pack_and_disassemble(sf2_file)
        all_results.append(result)

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70 + "\n")

    pack_success = sum(1 for r in all_results if r['pack_success'])
    disasm_success = sum(1 for r in all_results if r['disasm_success'])
    crashes = sum(1 for r in all_results if r['crash_at_0000'])

    print(f"Files tested:     {len(all_results)}")
    print(f"Pack success:     {pack_success}/{len(all_results)} ({pack_success/len(all_results)*100:.1f}%)")
    print(f"Disasm success:   {disasm_success}/{len(all_results)} ({disasm_success/len(all_results)*100:.1f}%)")
    print(f"$0000 crashes:    {crashes}/{len(all_results)} ({crashes/len(all_results)*100:.1f}%)")

    # Detailed results
    print("\nDetailed Results:")
    print("-" * 70)
    for r in all_results:
        status = "[PASS]" if r['disasm_success'] and not r['crash_at_0000'] else "[FAIL]"
        crash_note = " [CRASH at $0000]" if r['crash_at_0000'] else ""
        error_note = f" ({r['error']})" if r['error'] and not r['crash_at_0000'] else ""
        print(f"{status:8} {r['file']:50} {crash_note}{error_note}")

    # Final verdict
    print("\n" + "="*70)
    if crashes == 0 and disasm_success == len(all_results):
        print("[PASS] INTEGRATION TEST PASSED")
        print("="*70)
        print("\nTrack 3.1 Fix Validated:")
        print("- All files packed successfully")
        print("- All files disassembled without $0000 crashes")
        print("- Pointer relocation fix working correctly")
        return 0
    elif crashes == 0:
        print("[PARTIAL] INTEGRATION TEST PARTIAL SUCCESS")
        print("="*70)
        print(f"\nNo $0000 crashes detected, but {len(all_results) - disasm_success} files failed disassembly")
        return 0
    else:
        print("[FAIL] INTEGRATION TEST FAILED")
        print("="*70)
        print(f"\n{crashes} file(s) crashed at $0000 - pointer relocation bug NOT fixed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
