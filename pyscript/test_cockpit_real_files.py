#!/usr/bin/env python3
"""
Real File Integration Test for Conversion Cockpit

Tests end-to-end conversion with actual SID files.
Verifies that the pipeline executes correctly and produces expected outputs.

Version: 1.0.0
Date: 2025-12-22
"""

import sys
import os
import time
import tempfile
import shutil
from pathlib import Path
from typing import List

# Add pyscript directory to path
sys.path.insert(0, str(Path(__file__).parent))

from pipeline_config import PipelineConfig
from conversion_executor import ConversionExecutor


class TestResults:
    """Track test results"""
    def __init__(self):
        self.batch_started = False
        self.files_started = []
        self.files_completed = []
        self.steps_completed = []
        self.errors = []
        self.logs = []
        self.batch_completed = False
        self.summary = None


def run_real_file_test():
    """Run conversion test with real SID files"""

    print("=" * 70)
    print("CONVERSION COCKPIT - REAL FILE INTEGRATION TEST")
    print("=" * 70)
    print()

    # Setup
    test_results = TestResults()

    # Find SID files
    sid_dir = Path(__file__).parent.parent / "SID"
    if not sid_dir.exists():
        print(f"❌ ERROR: SID directory not found: {sid_dir}")
        return 1

    # Select 3 test files (small, medium, large complexity)
    test_files = [
        "Angular.sid",      # Known good file
        "Beast.sid",        # Medium complexity
        "Delicate.sid"      # Another test file
    ]

    sid_files = []
    for filename in test_files:
        filepath = sid_dir / filename
        if filepath.exists():
            sid_files.append(str(filepath))
        else:
            print(f"⚠️  WARNING: Test file not found: {filename}")

    if not sid_files:
        print("❌ ERROR: No test files found")
        return 1

    print(f"[FILES] Test Files ({len(sid_files)}):")
    for f in sid_files:
        print(f"   - {Path(f).name}")
    print()

    # Create temporary output directory
    output_dir = Path(tempfile.mkdtemp(prefix="cockpit_test_"))
    print(f"[OUTPUT] Output Directory: {output_dir}")
    print()

    try:
        # Create configuration (Simple mode)
        config = PipelineConfig()
        config.set_mode("simple")
        config.output_directory = str(output_dir)
        config.primary_driver = "laxity"
        config.overwrite_existing = True

        print("[CONFIG] Configuration:")
        print(f"   Mode: {config.mode}")
        print(f"   Driver: {config.primary_driver}")
        print(f"   Steps: {len(config.get_enabled_steps())}")
        print(f"   Enabled: {', '.join(config.get_enabled_steps())}")
        print()

        # Create executor
        executor = ConversionExecutor(config)

        # Connect signals
        def on_batch_started(total_files):
            test_results.batch_started = True
            print(f"[START] Batch Started: {total_files} files")

        def on_file_started(filename, index, total):
            test_results.files_started.append(filename)
            print(f"\n[FILE] File {index + 1}/{total}: {Path(filename).name}")

        def on_step_started(step_name, step_num, total_steps):
            print(f"   [{step_num}/{total_steps}] {step_name}...", end="", flush=True)

        def on_step_completed(step_name, success, message):
            test_results.steps_completed.append((step_name, success))
            status = "[OK]" if success else "[FAIL]"
            print(f" {status}")
            if not success:
                print(f"      Error: {message}")

        def on_file_completed(filename, results):
            test_results.files_completed.append((filename, results))
            status = results.get("status", "unknown")
            accuracy = results.get("accuracy", 0.0)
            steps = results.get("steps_completed", 0)
            total_steps = results.get("total_steps", 0)

            print(f"\n   [DONE] Completed: {Path(filename).name}")
            print(f"      Status: {status}")
            print(f"      Steps: {steps}/{total_steps}")
            if accuracy > 0:
                print(f"      Accuracy: {accuracy:.2f}%")

        def on_batch_completed(summary):
            test_results.batch_completed = True
            test_results.summary = summary

        def on_log_message(level, message):
            test_results.logs.append((level, message))

        def on_error_occurred(filename, error):
            test_results.errors.append((filename, error))
            print(f"\n   [ERROR] ERROR in {Path(filename).name}: {error}")

        # Connect signals
        executor.batch_started.connect(on_batch_started)
        executor.file_started.connect(on_file_started)
        executor.step_started.connect(on_step_started)
        executor.step_completed.connect(on_step_completed)
        executor.file_completed.connect(on_file_completed)
        executor.batch_completed.connect(on_batch_completed)
        executor.log_message.connect(on_log_message)
        executor.error_occurred.connect(on_error_occurred)

        # Start conversion
        print("[RUN] Starting Batch Conversion...")
        print()

        start_time = time.time()
        executor.start_batch(sid_files)

        # Wait for completion
        while executor.is_running:
            time.sleep(0.5)

        duration = time.time() - start_time

        # Print results
        print()
        print("=" * 70)
        print("TEST RESULTS")
        print("=" * 70)
        print()

        print(f"[PASS] Batch Started: {test_results.batch_started}")
        print(f"[PASS] Files Started: {len(test_results.files_started)}/{len(sid_files)}")
        print(f"[PASS] Files Completed: {len(test_results.files_completed)}/{len(sid_files)}")
        print(f"[PASS] Steps Completed: {len(test_results.steps_completed)}")
        print(f"[PASS] Batch Completed: {test_results.batch_completed}")
        print(f"[TIME] Duration: {duration:.1f} seconds")
        print()

        # Summary
        if test_results.summary:
            summary = test_results.summary
            total = summary.get("total_files", 0)
            passed = summary.get("passed", 0)
            failed = summary.get("failed", 0)
            avg_accuracy = summary.get("avg_accuracy", 0.0)

            print("[SUMMARY] Summary:")
            print(f"   Total: {total}")
            print(f"   Passed: {passed}")
            print(f"   Failed: {failed}")
            print(f"   Success Rate: {(passed/total*100) if total > 0 else 0:.1f}%")
            if avg_accuracy > 0:
                print(f"   Average Accuracy: {avg_accuracy:.2f}%")
            print()

        # Check output files
        print("[OUTPUT] Output Files Created:")
        output_files = list(output_dir.rglob("*"))
        output_files = [f for f in output_files if f.is_file()]

        file_types = {}
        for f in output_files:
            ext = f.suffix
            file_types[ext] = file_types.get(ext, 0) + 1

        print(f"   Total files: {len(output_files)}")
        for ext, count in sorted(file_types.items()):
            print(f"   {ext}: {count}")
        print()

        # Errors
        if test_results.errors:
            print("[ERRORS] Errors:")
            for filename, error in test_results.errors:
                print(f"   - {Path(filename).name}: {error}")
            print()

        # Verify expected outputs
        print("[VERIFY] Verification:")
        all_verified = True

        for sid_file in sid_files:
            base_name = Path(sid_file).stem
            expected_sf2 = output_dir / base_name / "New" / f"{base_name}_d11.sf2"

            if expected_sf2.exists():
                print(f"   [OK] {base_name}_d11.sf2 created ({expected_sf2.stat().st_size} bytes)")
            else:
                print(f"   [FAIL] {base_name}_d11.sf2 NOT FOUND")
                all_verified = False

        print()

        # Final verdict
        print("=" * 70)
        if test_results.batch_completed and all_verified and not test_results.errors:
            print("[PASS] TEST PASSED - All conversions successful")
            print("=" * 70)
            return 0
        else:
            print("[FAIL] TEST FAILED - See errors above")
            print("=" * 70)
            return 1

    finally:
        # Cleanup
        if output_dir.exists():
            print(f"\n[CLEANUP] Cleaning up: {output_dir}")
            shutil.rmtree(output_dir)


if __name__ == "__main__":
    sys.exit(run_real_file_test())
