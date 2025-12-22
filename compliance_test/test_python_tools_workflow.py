#!/usr/bin/env python3
"""
Test Python Tools Workflow
Demonstrates all three Python tools working together on a SID file
"""

import sys
import subprocess
from pathlib import Path

def run_tool(description, command):
    """Run a tool and report success/failure"""
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"{'='*80}")
    print(f"Command: {' '.join(command)}")
    print()

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("[OK] SUCCESS")
            # Show first 10 lines of output
            output_lines = result.stdout.strip().split('\n')
            if len(output_lines) > 10:
                for line in output_lines[:10]:
                    print(f"  {line}")
                print(f"  ... ({len(output_lines)} total lines)")
            else:
                for line in output_lines:
                    print(f"  {line}")
            return True
        else:
            print(f"[FAIL] Exit code: {result.returncode}")
            if result.stderr:
                print(f"Error: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def main():
    test_file = Path("../Laxity/Broware.sid")

    if not test_file.exists():
        print(f"[ERROR] Test file not found: {test_file}")
        return 1

    print("="*80)
    print("Python Tools Workflow Test")
    print("="*80)
    print(f"Test file: {test_file.name}")
    print(f"Testing: siddump_complete.py, siddecompiler_complete.py, sidwinder_trace.py")
    print()

    results = {}

    # Test 1: siddump
    results['siddump'] = run_tool(
        "TEST 1: siddump_complete.py - SID Register Dump",
        ["python", "../pyscript/siddump_complete.py", "-t", "10", str(test_file)]
    )

    # Test 2: SIDdecompiler
    results['siddecompiler'] = run_tool(
        "TEST 2: siddecompiler_complete.py - Player Detection",
        ["python", "../pyscript/siddecompiler_complete.py",
         "-o", "test_decompiler_output.asm", str(test_file)]
    )

    # Test 3: SIDwinder
    results['sidwinder'] = run_tool(
        "TEST 3: sidwinder_trace.py - Register Trace",
        ["python", "../pyscript/sidwinder_trace.py",
         "-trace=test_workflow_trace.txt", "-frames=50", str(test_file)]
    )

    # Check if trace file was created
    if Path("test_workflow_trace.txt").exists():
        lines = len(Path("test_workflow_trace.txt").read_text().splitlines())
        print(f"  Trace file created: {lines} lines")

    # Summary
    print("\n" + "="*80)
    print("WORKFLOW TEST SUMMARY")
    print("="*80)

    total = len(results)
    passed = sum(1 for r in results.values() if r)

    for tool, success in results.items():
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} {tool}")

    print(f"\nTotal: {passed}/{total} tests passed ({passed*100//total}%)")

    if passed == total:
        print("\n[SUCCESS] All Python tools working correctly!")
        return 0
    else:
        print("\n[PARTIAL] Some tools failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
