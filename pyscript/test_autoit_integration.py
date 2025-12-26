"""
Test Script: AutoIt Integration Tests

Tests the AutoIt hybrid automation system including:
- Configuration loading
- AutoIt script execution
- Status file communication
- Error handling
- Timeout handling
- Integration with SF2EditorAutomation

Usage:
    python pyscript/test_autoit_integration.py
    python pyscript/test_autoit_integration.py --verbose
"""

import sys
import os
import time
import tempfile
from pathlib import Path
import subprocess
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.automation_config import AutomationConfig
from sidm2.sf2_editor_automation import SF2EditorAutomation


class AutoItIntegrationTester:
    """Test suite for AutoIt integration"""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.config = AutomationConfig()
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0

    def log(self, message, level="INFO"):
        """Print log message"""
        if self.verbose or level != "DEBUG":
            print(f"[{level}] {message}")

    def assert_true(self, condition, message):
        """Assert condition is True"""
        self.tests_run += 1
        if condition:
            self.tests_passed += 1
            self.log(f"[OK] {message}", "PASS")
            return True
        else:
            self.tests_failed += 1
            self.log(f"[FAIL] {message}", "FAIL")
            return False

    def assert_false(self, condition, message):
        """Assert condition is False"""
        return self.assert_true(not condition, message)

    def assert_equal(self, actual, expected, message):
        """Assert actual equals expected"""
        condition = actual == expected
        if not condition:
            self.log(f"       Expected: {expected}", "FAIL")
            self.log(f"       Actual: {actual}", "FAIL")
        return self.assert_true(condition, message)

    def test_configuration_loading(self):
        """Test 1: Configuration loading"""
        print("\n" + "=" * 70)
        print("Test 1: Configuration Loading")
        print("=" * 70 + "\n")

        self.assert_true(
            self.config.config_path.exists(),
            "Config file exists"
        )

        self.assert_equal(
            self.config.autoit_script_path,
            Path("scripts/autoit/sf2_loader.exe"),
            "AutoIt script path correct"
        )

        self.assert_true(
            self.config.autoit_timeout > 0,
            f"AutoIt timeout is positive ({self.config.autoit_timeout}s)"
        )

        editor_path = self.config.find_editor_path()
        self.assert_true(
            editor_path is not None,
            f"Editor path found: {editor_path}"
        )

    def test_autoit_script_exists(self):
        """Test 2: AutoIt script existence"""
        print("\n" + "=" * 70)
        print("Test 2: AutoIt Script Existence")
        print("=" * 70 + "\n")

        autoit_source = Path("scripts/autoit/sf2_loader.au3")
        compile_script = Path("scripts/autoit/compile.bat")
        autoit_exe = self.config.autoit_script_path

        self.assert_true(
            autoit_source.exists(),
            f"AutoIt source exists: {autoit_source}"
        )

        self.assert_true(
            compile_script.exists(),
            f"Compile script exists: {compile_script}"
        )

        if autoit_exe.exists():
            self.log(f"[OK] AutoIt executable found: {autoit_exe}", "PASS")
            self.tests_passed += 1
            return True
        else:
            self.log(f"[SKIP] AutoIt executable not found: {autoit_exe}", "WARN")
            self.log(f"       Run: {compile_script} to compile", "WARN")
            self.log(f"       Requires AutoIt3 installation", "WARN")
            return False

    def test_status_file_communication(self):
        """Test 3: Status file communication protocol"""
        print("\n" + "=" * 70)
        print("Test 3: Status File Communication")
        print("=" * 70 + "\n")

        # Create temp status file
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='_status.txt') as f:
            status_file = f.name

        try:
            # Test writing status
            statuses = ["STARTING", "LAUNCHING", "WAITING_WINDOW", "SUCCESS:Test"]

            for status in statuses:
                with open(status_file, 'w') as f:
                    f.write(status + "\n")

                with open(status_file, 'r') as f:
                    read_status = f.read().strip()

                self.assert_equal(
                    read_status,
                    status,
                    f"Status file read/write: {status}"
                )

        finally:
            # Cleanup
            if os.path.exists(status_file):
                os.unlink(status_file)

    def test_sf2_editor_automation_init(self):
        """Test 4: SF2EditorAutomation initialization"""
        print("\n" + "=" * 70)
        print("Test 4: SF2EditorAutomation Initialization")
        print("=" * 70 + "\n")

        try:
            automation = SF2EditorAutomation()

            self.assert_true(
                automation.config is not None,
                "Config instance created"
            )

            self.assert_true(
                automation.editor_path is not None,
                f"Editor path set: {automation.editor_path}"
            )

            self.assert_equal(
                automation.autoit_script,
                self.config.autoit_script_path,
                "AutoIt script path matches config"
            )

            self.assert_equal(
                automation.autoit_timeout,
                self.config.autoit_timeout,
                f"AutoIt timeout matches config ({automation.autoit_timeout}s)"
            )

            expected_enabled = self.config.autoit_enabled and self.config.autoit_script_path.exists()
            self.assert_equal(
                automation.autoit_enabled,
                expected_enabled,
                f"AutoIt enabled status correct: {automation.autoit_enabled}"
            )

        except Exception as e:
            self.log(f"[FAIL] Initialization failed: {e}", "FAIL")
            self.tests_failed += 1

    def test_launch_modes(self):
        """Test 5: Launch mode selection"""
        print("\n" + "=" * 70)
        print("Test 5: Launch Mode Selection")
        print("=" * 70 + "\n")

        automation = SF2EditorAutomation()

        # Test mode logic
        autoit_available = automation.autoit_enabled

        self.log(f"AutoIt available: {autoit_available}", "DEBUG")

        if autoit_available:
            self.assert_true(
                automation.use_autoit_by_default,
                "AutoIt mode is default when available"
            )
        else:
            self.assert_false(
                automation.use_autoit_by_default,
                "Manual mode is default when AutoIt unavailable"
            )

        # Test that methods exist
        self.assert_true(
            hasattr(automation, 'launch_editor_with_file'),
            "launch_editor_with_file method exists"
        )

        self.assert_true(
            hasattr(automation, '_launch_with_autoit'),
            "_launch_with_autoit method exists"
        )

        self.assert_true(
            hasattr(automation, '_launch_manual_workflow'),
            "_launch_manual_workflow method exists"
        )

    def test_example_scripts(self):
        """Test 6: Example scripts existence"""
        print("\n" + "=" * 70)
        print("Test 6: Example Scripts")
        print("=" * 70 + "\n")

        example_file = Path("pyscript/example_autoit_usage.py")

        self.assert_true(
            example_file.exists(),
            f"Example script exists: {example_file}"
        )

        if example_file.exists():
            # Check that it can be imported
            try:
                with open(example_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for key functions
                has_auto_detect = "example_auto_detect" in content
                has_force_autoit = "example_force_autoit" in content
                has_manual_mode = "example_manual_mode" in content
                has_batch = "example_batch_validation" in content

                self.assert_true(has_auto_detect, "Has auto-detect example")
                self.assert_true(has_force_autoit, "Has force AutoIt example")
                self.assert_true(has_manual_mode, "Has manual mode example")
                self.assert_true(has_batch, "Has batch validation example")

            except Exception as e:
                self.log(f"[FAIL] Could not read example script: {e}", "FAIL")
                self.tests_failed += 1

    def test_documentation(self):
        """Test 7: Documentation existence"""
        print("\n" + "=" * 70)
        print("Test 7: Documentation")
        print("=" * 70 + "\n")

        docs = {
            "AutoIt README": Path("scripts/autoit/README.md"),
            "AutoIt Hybrid Guide": Path("docs/guides/SF2_EDITOR_AUTOIT_HYBRID_GUIDE.md"),
            "Manual Workflow Guide": Path("docs/guides/SF2_EDITOR_MANUAL_WORKFLOW_GUIDE.md"),
        }

        for name, path in docs.items():
            self.assert_true(
                path.exists(),
                f"{name} exists: {path}"
            )

    def test_autoit_live_execution(self):
        """Test 8: AutoIt live execution (if compiled)"""
        print("\n" + "=" * 70)
        print("Test 8: AutoIt Live Execution (Optional)")
        print("=" * 70 + "\n")

        autoit_exe = self.config.autoit_script_path

        if not autoit_exe.exists():
            self.log("[SKIP] AutoIt not compiled - test skipped", "WARN")
            self.log("       Run: scripts/autoit/compile.bat to enable", "WARN")
            return

        # This is a live test that requires AutoIt to be compiled
        # We'll just test that it can be executed (not full file loading)

        self.log("AutoIt executable found - testing execution...", "DEBUG")

        # Test with invalid arguments (should fail gracefully)
        try:
            result = subprocess.run(
                [str(autoit_exe)],
                capture_output=True,
                text=True,
                timeout=5
            )

            # Should fail with error about invalid arguments
            self.assert_true(
                result.returncode != 0,
                "AutoIt exits with error code for invalid arguments"
            )

            # Check for usage message in output
            has_usage = "Usage:" in result.stdout or "ERROR:" in result.stdout
            self.assert_true(
                has_usage,
                "AutoIt shows usage/error message"
            )

        except subprocess.TimeoutExpired:
            self.log("[FAIL] AutoIt execution timeout", "FAIL")
            self.tests_failed += 1
        except Exception as e:
            self.log(f"[FAIL] AutoIt execution error: {e}", "FAIL")
            self.tests_failed += 1

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("Test Summary")
        print("=" * 70 + "\n")

        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Tests failed: {self.tests_failed}")
        print()

        if self.tests_failed == 0:
            print("[OK] All tests passed!")
        else:
            print(f"[FAIL] {self.tests_failed} test(s) failed")

        print()

        # Recommendations
        autoit_exe = self.config.autoit_script_path
        if not autoit_exe.exists():
            print("[WARN] RECOMMENDATION: Compile AutoIt script")
            print("       Run: scripts/autoit/compile.bat")
            print("       This will enable fully automated file loading")
            print()

    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "=" * 70)
        print("AutoIt Integration Test Suite")
        print("=" * 70 + "\n")

        self.test_configuration_loading()
        autoit_available = self.test_autoit_script_exists()
        self.test_status_file_communication()
        self.test_sf2_editor_automation_init()
        self.test_launch_modes()
        self.test_example_scripts()
        self.test_documentation()

        if autoit_available:
            self.test_autoit_live_execution()

        self.print_summary()

        return self.tests_failed == 0


def main():
    """Run AutoIt integration tests"""
    parser = argparse.ArgumentParser(description='AutoIt Integration Tests')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output')
    args = parser.parse_args()

    tester = AutoItIntegrationTester(verbose=args.verbose)
    success = tester.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
