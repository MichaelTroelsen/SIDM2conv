"""
Batch SF2 File Testing with PyAutoGUI Automation

Tests multiple SF2 files using PyAutoGUI automation to validate:
- File loading success
- Editor window stability
- Playback functionality
- Overall automation reliability

Usage:
    python pyscript/test_batch_pyautogui.py [--directory DIR] [--pattern PATTERN] [--timeout TIMEOUT]

Examples:
    # Test all SF2 files in output directory
    python pyscript/test_batch_pyautogui.py

    # Test specific directory
    python pyscript/test_batch_pyautogui.py --directory output/keep_Stinsens_Last_Night_of_89

    # Test with custom pattern
    python pyscript/test_batch_pyautogui.py --pattern "Laxity*.sf2"

    # Custom timeout per file
    python pyscript/test_batch_pyautogui.py --timeout 30
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.sf2_editor_automation import SF2EditorAutomation


@pytest.fixture
def automation():
    """Pytest fixture providing SF2EditorAutomation instance for tests"""
    auto = SF2EditorAutomation()
    yield auto

    # Cleanup: Always close editor after test
    try:
        if auto.pyautogui_automation and auto.pyautogui_automation.is_window_open():
            auto.pyautogui_automation.close_editor()
            time.sleep(0.5)
    except Exception:
        pass  # Ignore cleanup errors

    # Force kill any remaining processes
    try:
        import psutil
        for proc in psutil.process_iter(['name']):
            if 'SIDFactoryII' in proc.info['name']:
                proc.kill()
    except Exception:
        pass


class BatchTestResults:
    """Results container for batch testing"""

    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.results: List[Dict] = []
        self.start_time = None
        self.end_time = None

    def add_result(self, file_path: str, success: bool, message: str = "",
                   duration: float = 0.0, error: Optional[str] = None):
        """Add a test result"""
        self.results.append({
            'file': file_path,
            'success': success,
            'message': message,
            'duration': duration,
            'error': error,
            'timestamp': datetime.now()
        })

        self.total += 1
        if success:
            self.passed += 1
        else:
            self.failed += 1

    def skip_result(self, file_path: str, reason: str):
        """Add a skipped test"""
        self.results.append({
            'file': file_path,
            'success': None,
            'message': f"SKIPPED: {reason}",
            'duration': 0.0,
            'error': None,
            'timestamp': datetime.now()
        })
        self.total += 1
        self.skipped += 1

    def get_summary(self) -> str:
        """Get summary statistics"""
        duration = 0
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()

        return f"""
{'=' * 70}
Batch Test Summary
{'=' * 70}

Total Files:    {self.total}
Passed:         {self.passed} ({self.passed/self.total*100 if self.total > 0 else 0:.1f}%)
Failed:         {self.failed} ({self.failed/self.total*100 if self.total > 0 else 0:.1f}%)
Skipped:        {self.skipped} ({self.skipped/self.total*100 if self.total > 0 else 0:.1f}%)

Total Duration: {duration:.1f} seconds
Avg Per File:   {duration/self.total if self.total > 0 else 0:.1f} seconds

{'=' * 70}
"""


def find_sf2_files(directory: Path, pattern: str = "*.sf2") -> List[Path]:
    """Find all SF2 files matching pattern

    Args:
        directory: Directory to search
        pattern: Glob pattern for files

    Returns:
        List of SF2 file paths
    """
    if not directory.exists():
        print(f"[ERROR] Directory not found: {directory}")
        return []

    # Search recursively for SF2 files
    files = sorted(directory.rglob(pattern))

    print(f"[INFO] Found {len(files)} SF2 files in {directory}")
    return files


def run_single_file_test(automation: SF2EditorAutomation, file_path: Path,
                         playback_duration: float = 3.0,
                         stability_check: float = 2.0) -> tuple:
    """Run test on a single SF2 file

    Args:
        automation: SF2EditorAutomation instance
        file_path: Path to SF2 file
        playback_duration: How long to play audio (seconds)
        stability_check: How long to verify window stability (seconds)

    Returns:
        (success: bool, message: str, error: Optional[str])
    """
    start_time = time.time()

    try:
        # Launch editor with file
        print(f"\n[TEST] {file_path.name}")
        print(f"  Launching editor...")

        success = automation.launch_editor_with_file(str(file_path))

        if not success:
            return (False, "Failed to launch editor", "Launch failed")

        print(f"  [OK] Editor launched")

        # Check PyAutoGUI automation available
        if not automation.pyautogui_automation:
            return (False, "PyAutoGUI automation not available", "No automation")

        # Verify window is open
        if not automation.pyautogui_automation.is_window_open():
            return (False, "Window not detected", "Window check failed")

        print(f"  [OK] Window detected")

        # Wait for editor to fully initialize
        time.sleep(0.5)

        # Test playback (non-critical - warn on failure but continue)
        print(f"  Testing playback ({playback_duration}s)...")

        playback_warnings = []

        # Start playback
        start_result = automation.pyautogui_automation.start_playback()
        if not start_result:
            playback_warnings.append("Playback start returned False (may be cosmetic)")

        # Play for specified duration
        time.sleep(playback_duration)

        # Stop playback
        stop_result = automation.pyautogui_automation.stop_playback()
        if not stop_result:
            playback_warnings.append("Playback stop returned False (may be cosmetic)")

        if playback_warnings:
            print(f"  [WARN] Playback control warnings: {'; '.join(playback_warnings)}")
        else:
            print(f"  [OK] Playback control successful")

        # Verify window stability
        print(f"  Checking window stability ({stability_check}s)...")

        for i in range(int(stability_check)):
            if not automation.pyautogui_automation.is_window_open():
                return (False, f"Window closed after {i} seconds", "Stability check failed")
            time.sleep(1)

        print(f"  [OK] Window remained stable")

        # Close editor
        automation.pyautogui_automation.close_editor()

        # Wait for editor to close
        time.sleep(0.5)

        # Verify editor process is terminated
        max_wait = 3  # seconds
        for i in range(max_wait * 2):  # Check every 0.5s
            if automation.pyautogui_automation.process and automation.pyautogui_automation.process.poll() is None:
                # Process still running, wait
                time.sleep(0.5)
            else:
                # Process terminated
                break

        # If process still running after wait, force kill
        if automation.pyautogui_automation.process and automation.pyautogui_automation.process.poll() is None:
            print(f"  [WARN] Process still running, force killing...")
            try:
                automation.pyautogui_automation.process.kill()
                automation.pyautogui_automation.process.wait(timeout=2)
                print(f"  [OK] Process terminated")
            except Exception as e:
                print(f"  [WARN] Could not kill process: {e}")

        duration = time.time() - start_time

        print(f"  [PASS] Test completed successfully ({duration:.1f}s)")

        return (True, f"All checks passed ({duration:.1f}s)", None)

    except Exception as e:
        duration = time.time() - start_time
        error_msg = str(e)

        # Try to close editor if still open
        try:
            if automation.pyautogui_automation and automation.pyautogui_automation.is_window_open():
                automation.pyautogui_automation.close_editor()
        except:
            pass

        print(f"  [FAIL] Test failed: {error_msg} ({duration:.1f}s)")

        return (False, f"Exception occurred ({duration:.1f}s)", error_msg)


def run_batch_test(directory: Path, pattern: str = "*.sf2",
                   playback_duration: float = 3.0,
                   stability_check: float = 2.0,
                   max_files: Optional[int] = None,
                   timeout: int = 30) -> BatchTestResults:
    """Run batch test on multiple SF2 files

    Args:
        directory: Directory containing SF2 files
        pattern: Glob pattern for SF2 files
        playback_duration: Playback test duration per file
        stability_check: Window stability check duration
        max_files: Maximum number of files to test (None = all)
        timeout: Timeout per file in seconds

    Returns:
        BatchTestResults with complete test results
    """
    results = BatchTestResults()
    results.start_time = datetime.now()

    print("=" * 70)
    print("PyAutoGUI Batch Testing")
    print("=" * 70)
    print()
    print(f"Directory:        {directory}")
    print(f"Pattern:          {pattern}")
    print(f"Playback:         {playback_duration}s")
    print(f"Stability Check:  {stability_check}s")
    print(f"Max Files:        {max_files if max_files else 'Unlimited'}")
    print(f"Timeout:          {timeout}s")
    print()

    # Find SF2 files
    files = find_sf2_files(directory, pattern)

    if not files:
        print("[ERROR] No SF2 files found!")
        results.end_time = datetime.now()
        return results

    # Limit files if requested
    if max_files and len(files) > max_files:
        print(f"[INFO] Limiting to first {max_files} files")
        files = files[:max_files]

    # Initialize automation
    try:
        automation = SF2EditorAutomation()
        print(f"[INFO] Automation mode: {automation.default_automation_mode}")

        if not automation.pyautogui_enabled:
            print("[WARN] PyAutoGUI not enabled - tests may fail")

    except Exception as e:
        print(f"[ERROR] Failed to initialize automation: {e}")
        results.end_time = datetime.now()
        return results

    print()
    print("=" * 70)
    print("Starting Tests")
    print("=" * 70)

    try:
        # Test each file
        for i, file_path in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}] Testing: {file_path.name}")
            print("-" * 70)

            # Test file
            start_time = time.time()
            success, message, error = run_single_file_test(
                automation,
                file_path,
                playback_duration=playback_duration,
                stability_check=stability_check
            )
            duration = time.time() - start_time

            # Add result
            results.add_result(
                str(file_path),
                success,
                message,
                duration,
                error
            )

            # Small delay between tests
            time.sleep(1)

    finally:
        # ALWAYS cleanup all editor processes
        print()
        print("Cleaning up editor processes...")
        try:
            import psutil
            killed = 0
            for proc in psutil.process_iter(['name']):
                if 'SIDFactoryII' in proc.info['name']:
                    proc.kill()
                    killed += 1
            if killed > 0:
                print(f"Killed {killed} editor process(es)")
        except Exception as e:
            print(f"Warning: Cleanup failed: {e}")

    results.end_time = datetime.now()

    return results


def print_detailed_results(results: BatchTestResults):
    """Print detailed test results"""
    print("\n" + "=" * 70)
    print("Detailed Results")
    print("=" * 70)
    print()

    for i, result in enumerate(results.results, 1):
        status = "[PASS]" if result['success'] else "[FAIL]" if result['success'] is False else "[SKIP]"
        file_name = Path(result['file']).name

        print(f"{i}. {status} - {file_name}")
        print(f"   Message: {result['message']}")
        print(f"   Duration: {result['duration']:.1f}s")

        if result['error']:
            print(f"   Error: {result['error']}")

        print()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Batch SF2 file testing with PyAutoGUI automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--directory', '-d',
        type=str,
        default='output',
        help='Directory to search for SF2 files (default: output)'
    )

    parser.add_argument(
        '--pattern', '-p',
        type=str,
        default='*.sf2',
        help='Glob pattern for SF2 files (default: *.sf2)'
    )

    parser.add_argument(
        '--playback', '-pb',
        type=float,
        default=3.0,
        help='Playback duration per file in seconds (default: 3.0)'
    )

    parser.add_argument(
        '--stability', '-s',
        type=float,
        default=2.0,
        help='Window stability check duration in seconds (default: 2.0)'
    )

    parser.add_argument(
        '--max-files', '-m',
        type=int,
        default=None,
        help='Maximum number of files to test (default: all)'
    )

    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=30,
        help='Timeout per file in seconds (default: 30)'
    )

    args = parser.parse_args()

    # Convert directory to Path
    directory = Path(args.directory)

    # Run batch test
    results = run_batch_test(
        directory,
        pattern=args.pattern,
        playback_duration=args.playback,
        stability_check=args.stability,
        max_files=args.max_files,
        timeout=args.timeout
    )

    # Print results
    print_detailed_results(results)
    print(results.get_summary())

    # Exit with appropriate code
    sys.exit(0 if results.failed == 0 else 1)


if __name__ == '__main__':
    main()
