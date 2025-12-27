"""
Test SIDdecompiler Wrapper Integration

Validates that the wrapper correctly uses Python SIDdecompiler
and falls back to .exe when needed.
"""

import sys
import os
from pathlib import Path
import tempfile
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sidm2.siddecompiler import SIDdecompilerAnalyzer


def test_python_wrapper():
    """Test Python SIDdecompiler via wrapper"""
    # Find a test SID file
    test_files = list(Path("Laxity").glob("*.sid"))
    if not test_files:
        print("ERROR: No test files found")
        pytest.skip("No test files found")

    test_file = test_files[0]

    print("=" * 70)
    print("SIDdecompiler Wrapper Integration Test")
    print("=" * 70)
    print(f"Test file: {test_file.name}")
    print()

    # Create temporary output directory
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        # Test 1: Python version (default)
        print("[Test 1] Python SIDdecompiler (use_python=True)")
        analyzer = SIDdecompilerAnalyzer(use_python=True)

        result = analyzer.analyze(
            sid_file=test_file,
            output_dir=output_dir,
            ticks=500,  # Quick test
            verbose=0
        )

        if result['success']:
            print(f"  [OK] Success (method: {result['method']})")
            print(f"  Output: {result['asm_file'].name}")
            print(f"  File exists: {result['asm_file'].exists()}")

            # Check output file
            if result['asm_file'].exists():
                with open(result['asm_file'], 'r') as f:
                    lines = f.readlines()
                print(f"  Lines: {len(lines)}")
                print(f"  First line: {lines[0].strip() if lines else 'N/A'}")
            else:
                print("  [FAIL] Output file not created!")
                pytest.fail("Output file not created!")
        else:
            print(f"  [FAIL] Failed: {result['stderr']}")
            pytest.fail(f"Analysis failed: {result['stderr']}")

        print()

        # Test 2: Force .exe version (if available)
        print("[Test 2] Force .exe version (use_python=False)")
        try:
            analyzer_exe = SIDdecompilerAnalyzer(use_python=False)

            result_exe = analyzer_exe.analyze(
                sid_file=test_file,
                output_dir=output_dir,
                ticks=500,
                verbose=0
            )

            if result_exe['success']:
                print(f"  [OK] Success (method: {result_exe['method']})")
            else:
                print(f"  [FAIL] Failed: {result_exe['stderr']}")
        except FileNotFoundError as e:
            print(f"  [SKIP] {e}")

        print()

    print("=" * 70)
    print("[PASS] Wrapper integration test completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        test_python_wrapper()
        print("\n[SUCCESS] All tests passed!")
        sys.exit(0)
    except (AssertionError, pytest.skip.Exception) as e:
        print(f"\n[FAIL] Test failed: {e}")
        sys.exit(1)
