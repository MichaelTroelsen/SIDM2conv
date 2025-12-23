#!/usr/bin/env python3
"""
Comprehensive test runner for SIDM2 project.

Runs all unit tests and reports results with detailed error information.
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

# Change to project root
os.chdir(Path(__file__).parent)

class TestRunner:
    def __init__(self):
        self.results = {}
        self.passed = 0
        self.failed = 0

    def run_test(self, name, cmd, timeout=300):
        """Run a single test and record results."""
        print(f"\n{'='*70}")
        print(f"[TEST] {name}")
        print(f"{'='*70}")
        print(f"Command: {cmd}\n")

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # Print output
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)

            # Check result
            if result.returncode == 0:
                print(f"\n[PASS] PASSED: {name}")
                self.results[name] = {'status': 'PASS', 'code': 0}
                self.passed += 1
                return True
            else:
                print(f"\n[FAIL] FAILED: {name} (exit code: {result.returncode})")
                self.results[name] = {'status': 'FAIL', 'code': result.returncode}
                self.failed += 1
                return False

        except subprocess.TimeoutExpired:
            print(f"\n[TIMEOUT] TIMEOUT: {name} (exceeded {timeout}s)")
            self.results[name] = {'status': 'TIMEOUT', 'code': -1}
            self.failed += 1
            return False
        except Exception as e:
            print(f"\n[ERROR] ERROR: {name} - {e}")
            self.results[name] = {'status': 'ERROR', 'code': -1}
            self.failed += 1
            return False

    def print_summary(self):
        """Print test summary."""
        print(f"\n\n{'='*70}")
        print("TEST SUMMARY")
        print(f"{'='*70}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Total:  {self.passed + self.failed}")

        if self.failed > 0:
            print(f"\nFailed tests:")
            for name, result in self.results.items():
                if result['status'] != 'PASS':
                    symbol = '[FAIL]' if result['status'] == 'FAIL' else f'[{result["status"]}]'
                    print(f"  {symbol} {name}: {result['status']}")

        print(f"\n{'='*70}\n")

        return self.failed == 0


def main():
    print("SIDM2 Comprehensive Test Runner")
    print(f"Started: {datetime.now()}")
    print(f"Directory: {os.getcwd()}")
    print(f"Python: {sys.executable}\n")

    runner = TestRunner()

    # Test 1: Converter tests (83 test methods - needs longer timeout)
    runner.run_test(
        "Converter Tests",
        f"{sys.executable} scripts/test_converter.py",
        timeout=600
    )

    # Test 2: SF2 Format tests
    runner.run_test(
        "SF2 Format Tests",
        f"{sys.executable} scripts/test_sf2_format.py",
        timeout=300
    )

    # Test 3: Laxity Driver tests
    runner.run_test(
        "Laxity Driver Tests",
        f"{sys.executable} scripts/test_laxity_driver.py",
        timeout=300
    )

    # Test 4: 6502 Disassembler tests
    runner.run_test(
        "6502 Disassembler Tests",
        f"{sys.executable} pyscript/test_disasm6502.py",
        timeout=300
    )

    # Test 5: SIDdecompiler tests
    runner.run_test(
        "SIDdecompiler Tests",
        f"{sys.executable} pyscript/test_siddecompiler_complete.py",
        timeout=300
    )

    # Test 6: SIDwinder Trace tests
    runner.run_test(
        "SIDwinder Trace Tests",
        f"{sys.executable} pyscript/test_sidwinder_trace.py",
        timeout=300
    )

    # Test 7: SIDwinder Real-world tests
    runner.run_test(
        "SIDwinder Real-world Tests",
        f"{sys.executable} pyscript/test_sidwinder_realworld.py",
        timeout=300
    )

    # Test 8: Siddump tests
    runner.run_test(
        "Siddump Tests",
        f"{sys.executable} pyscript/test_siddump.py",
        timeout=300
    )

    # Test 9: Roundtrip tests
    runner.run_test(
        "Roundtrip Tests",
        f"{sys.executable} scripts/test_roundtrip.py",
        timeout=600
    )

    # Print summary and exit
    all_pass = runner.print_summary()
    sys.exit(0 if all_pass else 1)


if __name__ == '__main__':
    main()
