"""
Real-World Validation: Python SIDwinder on Multiple SID Files

Tests the Python SIDwinder on a variety of real Laxity SID files
to validate production readiness.

Part of Python SIDwinder replacement (v2.8.0).
"""

import sys
import os
from pathlib import Path
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pyscript.sidtracer import SIDTracer
from pyscript.trace_formatter import TraceFormatter


def test_file(sid_path: Path, output_dir: Path, frames: int = 100, verbose: int = 0):
    """
    Test trace generation for a single SID file.

    Returns:
        (success, stats) where stats is a dict of metrics
    """
    try:
        tracer = SIDTracer(sid_path, verbose=verbose)
        trace_data = tracer.trace(frames=frames)

        # Write output
        output_path = output_dir / f"{sid_path.stem}_trace.txt"
        TraceFormatter.write_trace_file(trace_data, output_path)

        # Collect statistics
        total_writes = len(trace_data.init_writes) + sum(len(fw) for fw in trace_data.frame_writes)

        stats = {
            'name': sid_path.name,
            'frames': trace_data.frames,
            'cycles': trace_data.cycles,
            'init_writes': len(trace_data.init_writes),
            'frame_writes': sum(len(fw) for fw in trace_data.frame_writes),
            'total_writes': total_writes,
            'output_size': output_path.stat().st_size,
            'output_path': str(output_path)
        }

        return True, stats

    except Exception as e:
        return False, {'name': sid_path.name, 'error': str(e)}


def main():
    """Test on multiple real SID files."""
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
    output_dir = Path("output/sidwinder_realworld_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("Python SIDwinder Real-World Validation")
    print("=" * 70)
    print(f"Testing {len(sid_files)} SID files from Laxity collection")
    print()

    # Test each file
    results = []
    for i, sid_path in enumerate(sid_files, 1):
        print(f"[{i}/{len(sid_files)}] {sid_path.name:40}", end=" ... ", flush=True)

        success, stats = test_file(sid_path, output_dir, frames=100, verbose=0)

        if success:
            print(f"OK  ({stats['total_writes']:5d} writes, {stats['output_size']:7,} bytes)")
            results.append((sid_path.name, True, stats))
        else:
            print(f"FAIL: {stats.get('error', 'Unknown error')}")
            results.append((sid_path.name, False, stats))

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
        print(f"  Total cycles: {sum(s['cycles'] for s in all_stats):,}")
        print(f"  Total SID writes: {sum(s['total_writes'] for s in all_stats):,}")
        print(f"  Output size: {sum(s['output_size'] for s in all_stats):,} bytes")
        print()

        avg_writes = sum(s['total_writes'] for s in all_stats) / len(all_stats)
        avg_size = sum(s['output_size'] for s in all_stats) / len(all_stats)
        print(f"  Avg writes per file: {avg_writes:,.0f}")
        print(f"  Avg output size: {avg_size:,.0f} bytes")

    print("=" * 70)

    if failed == 0:
        print()
        print("[PASS] All files traced successfully!")
        return 0
    else:
        print()
        print(f"[FAIL] {failed} file(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
