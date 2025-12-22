#!/usr/bin/env python3
"""
Concurrent Processing Test - Measure speed improvement

Tests concurrent file processing with 1, 2, and 4 workers to measure speed improvement.

Version: 1.0.0
Date: 2025-12-22
"""

import sys
import os
import time
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict

# Add pyscript directory to path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtCore import QCoreApplication

from pipeline_config import PipelineConfig
from conversion_executor import ConversionExecutor

# Create Qt application for event processing
app = QCoreApplication([])


class ConcurrentTestResults:
    """Track test results for concurrent processing"""
    def __init__(self):
        self.files_completed = []
        self.batch_completed = False
        self.summary = None
        self.start_time = 0.0
        self.end_time = 0.0


def run_test_batch(files: List[str], workers: int, output_dir: Path) -> ConcurrentTestResults:
    """Run a test batch with specified number of workers"""
    results = ConcurrentTestResults()

    # Create configuration
    config = PipelineConfig()
    config.set_mode("simple")  # Use simple mode (7 steps) for faster testing
    config.output_directory = str(output_dir)
    config.primary_driver = "laxity"
    config.overwrite_existing = True
    config.concurrent_workers = workers  # Set worker count

    # Create executor
    executor = ConversionExecutor(config)

    # Connect signals
    def on_file_completed(filename, file_results):
        results.files_completed.append(filename)

    def on_batch_completed(summary):
        results.batch_completed = True
        results.summary = summary
        results.end_time = time.time()

    executor.file_completed.connect(on_file_completed)
    executor.batch_completed.connect(on_batch_completed)

    # Start batch
    results.start_time = time.time()
    executor.start_batch(files)

    # Wait for completion (process Qt events while waiting)
    max_wait = 300  # 5 minutes max
    start_wait = time.time()

    while not results.batch_completed and (time.time() - start_wait) < max_wait:
        app.processEvents()  # Process Qt events (signals/slots)
        time.sleep(0.1)

    # If still not done, force completion
    if not results.batch_completed:
        results.end_time = time.time()
        print(f"      [TIMEOUT] Batch did not complete within {max_wait} seconds")
    else:
        print(f"      [SUCCESS] Batch completed successfully")

    return results


def run_concurrent_test():
    """Run concurrent processing test with speed measurements"""

    print("=" * 70)
    print("CONCURRENT PROCESSING TEST")
    print("=" * 70)
    print()

    # Find SID files
    sid_dir = Path(__file__).parent.parent / "SID"
    if not sid_dir.exists():
        print(f"[ERROR] SID directory not found: {sid_dir}")
        return 1

    # Select 10 test files for speed comparison
    all_files = sorted(list(sid_dir.glob("*.sid")))
    test_files = [str(f) for f in all_files[:10]]

    if len(test_files) < 10:
        print(f"[WARN] Only {len(test_files)} files available (need 10 for good measurement)")
        if len(test_files) < 3:
            print("[ERROR] Need at least 3 files to test")
            return 1

    print(f"[TEST] Using {len(test_files)} files:")
    for i, f in enumerate(test_files, 1):
        print(f"   {i}. {Path(f).name}")
    print()

    # Test configurations: 1, 2, 4 workers
    worker_counts = [1, 2, 4]
    test_results: Dict[int, ConcurrentTestResults] = {}

    for workers in worker_counts:
        print(f"[TEST] Running with {workers} worker(s)...")

        # Create temporary output directory
        output_dir = Path(tempfile.mkdtemp(prefix=f"concurrent_test_{workers}w_"))

        try:
            # Run test
            results = run_test_batch(test_files, workers, output_dir)

            # Store results
            test_results[workers] = results

            # Calculate duration
            duration = results.end_time - results.start_time

            # Print results
            print(f"[DONE] {workers} worker(s):")
            print(f"       Duration: {duration:.2f} seconds")
            print(f"       Files: {len(results.files_completed)}/{len(test_files)}")
            print(f"       Speed: {len(test_files)/duration:.2f} files/second")
            print()

        finally:
            # Cleanup
            if output_dir.exists():
                shutil.rmtree(output_dir)

    # Calculate speed improvements
    print("=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print()

    baseline_duration = test_results[1].end_time - test_results[1].start_time

    print(f"[BASELINE] 1 worker (sequential):")
    print(f"   Duration: {baseline_duration:.2f} seconds")
    print(f"   Speed: {len(test_files)/baseline_duration:.2f} files/second")
    print()

    for workers in [2, 4]:
        if workers in test_results:
            results = test_results[workers]
            duration = results.end_time - results.start_time
            speedup = baseline_duration / duration
            percent_faster = ((baseline_duration - duration) / baseline_duration) * 100

            print(f"[TEST] {workers} workers:")
            print(f"   Duration: {duration:.2f} seconds")
            print(f"   Speed: {len(test_files)/duration:.2f} files/second")
            print(f"   Speedup: {speedup:.2f}x faster")
            print(f"   Improvement: {percent_faster:.1f}% faster than sequential")
            print()

    # Success criteria
    print("=" * 70)
    print("SUCCESS CRITERIA")
    print("=" * 70)
    print()

    # Check 2 workers is at least 1.5x faster
    if 2 in test_results:
        duration_2w = test_results[2].end_time - test_results[2].start_time
        speedup_2w = baseline_duration / duration_2w

        if speedup_2w >= 1.5:
            print(f"[PASS] 2 workers achieved {speedup_2w:.2f}x speedup (target: >=1.5x)")
        else:
            print(f"[WARN] 2 workers only achieved {speedup_2w:.2f}x speedup (target: >=1.5x)")

    # Check 4 workers is at least 2.0x faster
    if 4 in test_results:
        duration_4w = test_results[4].end_time - test_results[4].start_time
        speedup_4w = baseline_duration / duration_4w

        if speedup_4w >= 2.0:
            print(f"[PASS] 4 workers achieved {speedup_4w:.2f}x speedup (target: >=2.0x)")
        else:
            print(f"[WARN] 4 workers only achieved {speedup_4w:.2f}x speedup (target: >=2.0x)")

    # Check all files completed
    all_completed = all(len(r.files_completed) == len(test_files) for r in test_results.values())
    if all_completed:
        print(f"[PASS] All tests completed all {len(test_files)} files")
    else:
        print(f"[FAIL] Some tests did not complete all files")

    print()
    print("=" * 70)
    if all_completed and speedup_2w >= 1.5:
        print("[PASS] CONCURRENT PROCESSING TEST PASSED")
        print("=" * 70)
        return 0
    else:
        print("[WARN] CONCURRENT PROCESSING TEST COMPLETED WITH WARNINGS")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(run_concurrent_test())
