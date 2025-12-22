"""
Real-World Test: SIDdecompiler on Multiple SID Files

Tests the Python SIDdecompiler on a variety of real SID files
to validate production readiness.
"""

import sys
import os
from pathlib import Path
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pyscript.siddecompiler_complete import SIDDecompiler


def test_file(sid_path: Path, output_dir: Path, verbose: int = 1):
    """
    Test decompilation of a single SID file.

    Returns:
        (success, stats) where stats is a dict of metrics
    """
    decompiler = SIDDecompiler(verbose=verbose)

    # Parse
    if not decompiler.parse_sid_file(str(sid_path)):
        return False, {}

    # Analyze
    if not decompiler.analyze_memory_access(ticks=1000):  # Quick analysis
        return False, {}

    # Disassemble
    if not decompiler.disassemble():
        return False, {}

    # Detect tables
    if not decompiler.detect_tables():
        return False, {}

    # Generate output
    output_path = output_dir / f"{sid_path.stem}.asm"
    if not decompiler.generate_output(str(output_path)):
        return False, {}

    # Collect statistics
    stats = {
        'name': sid_path.name,
        'load_addr': decompiler.sid_header.load_address,
        'init_addr': decompiler.sid_header.init_address,
        'play_addr': decompiler.sid_header.play_address,
        'data_size': len(decompiler.sid_data),
        'code_regions': len(decompiler.code_regions),
        'data_regions': len(decompiler.data_regions),
        'code_bytes': sum(end - start for start, end in decompiler.code_regions),
        'instructions': len(decompiler.disassembler.lines),
        'labels': len(decompiler.disassembler.labels),
        'tables': len(decompiler.tables),
        'output_size': output_path.stat().st_size
    }

    return True, stats


def main():
    """Test on multiple real SID files"""
    # Setup logging
    logging.basicConfig(level=logging.WARNING, format='%(message)s')

    # Find SID files
    laxity_dir = Path("Laxity")
    if not laxity_dir.exists():
        print("Error: Laxity directory not found")
        return 1

    sid_files = list(laxity_dir.glob("*.sid"))[:10]  # Test first 10
    if not sid_files:
        print("Error: No SID files found in Laxity directory")
        return 1

    # Create output directory
    output_dir = Path("output/siddecompiler_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("SIDdecompiler Real-World Test")
    print("=" * 70)
    print(f"Testing {len(sid_files)} SID files from Laxity collection")
    print()

    # Test each file
    results = []
    for i, sid_path in enumerate(sid_files, 1):
        print(f"[{i}/{len(sid_files)}] {sid_path.name:40}", end=" ... ", flush=True)

        success, stats = test_file(sid_path, output_dir, verbose=0)

        if success:
            print(f"OK  ({stats['instructions']:4d} instr, {stats['labels']:3d} labels)")
            results.append((sid_path.name, True, stats))
        else:
            print("FAIL")
            results.append((sid_path.name, False, {}))

    # Print summary
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)

    passed = sum(1 for _, success, _ in results if success)
    failed = len(results) - passed

    print(f"Total files: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print()

    if passed > 0:
        all_stats = [stats for _, success, stats in results if success]

        print("Statistics (successful conversions):")
        print(f"  Code bytes: {sum(s['code_bytes'] for s in all_stats):,} total")
        print(f"  Instructions: {sum(s['instructions'] for s in all_stats):,} total")
        print(f"  Labels: {sum(s['labels'] for s in all_stats):,} total")
        print(f"  Output size: {sum(s['output_size'] for s in all_stats):,} bytes")
        print()

        print("Load addresses found:")
        load_addrs = set(f"${s['load_addr']:04X}" for s in all_stats)
        print(f"  {', '.join(sorted(load_addrs))}")

    print("=" * 70)

    if failed == 0:
        print("\n[PASS] All files decompiled successfully!")
        return 0
    else:
        print(f"\n[FAIL] {failed} file(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
