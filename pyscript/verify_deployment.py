"""
Deployment Verification Script - AutoIt Hybrid Automation

Verifies that all components of the AutoIt hybrid automation system
are properly deployed and configured.

Usage:
    python pyscript/verify_deployment.py
    python pyscript/verify_deployment.py --fix  # Attempt to fix issues
"""

import sys
import os
from pathlib import Path
import argparse
import subprocess

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.automation_config import AutomationConfig


class DeploymentVerifier:
    """Verify AutoIt hybrid automation deployment"""

    def __init__(self, fix_issues=False):
        self.fix_issues = fix_issues
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = 0

    def check(self, condition, name, fix_func=None):
        """Check a condition and optionally fix it"""
        if condition:
            print(f"[OK]   {name}")
            self.checks_passed += 1
            return True
        else:
            if fix_func and self.fix_issues:
                print(f"[FIX]  {name}")
                try:
                    fix_func()
                    print(f"       Fixed successfully")
                    self.checks_passed += 1
                    return True
                except Exception as e:
                    print(f"       Fix failed: {e}")
                    self.checks_failed += 1
                    return False
            else:
                print(f"[FAIL] {name}")
                self.checks_failed += 1
                return False

    def warn(self, condition, name, recommendation=None):
        """Warn if condition is false"""
        if condition:
            print(f"[OK]   {name}")
            return True
        else:
            print(f"[WARN] {name}")
            if recommendation:
                print(f"       {recommendation}")
            self.warnings += 1
            return False

    def verify_files(self):
        """Verify all required files exist"""
        print("\n" + "=" * 70)
        print("File Verification")
        print("=" * 70 + "\n")

        files = {
            "AutoIt source": "scripts/autoit/sf2_loader.au3",
            "AutoIt compile script": "scripts/autoit/compile.bat",
            "AutoIt README": "scripts/autoit/README.md",
            "AutoIt deployment guide": "scripts/autoit/DEPLOYMENT.md",
            "Configuration file": "config/sf2_automation.ini",
            "Config module": "sidm2/automation_config.py",
            "Automation module": "sidm2/sf2_editor_automation.py",
            "Integration tests": "pyscript/test_autoit_integration.py",
            "Config tests": "pyscript/test_automation_config.py",
            "Example usage": "pyscript/example_autoit_usage.py",
        }

        for name, path in files.items():
            self.check(
                Path(path).exists(),
                f"{name}: {path}"
            )

        # AutoIt executable (warning only)
        autoit_exe = Path("scripts/autoit/sf2_loader.exe")
        self.warn(
            autoit_exe.exists(),
            f"AutoIt executable: {autoit_exe}",
            "Run: scripts/autoit/compile.bat to compile"
        )

    def verify_configuration(self):
        """Verify configuration is valid"""
        print("\n" + "=" * 70)
        print("Configuration Verification")
        print("=" * 70 + "\n")

        try:
            config = AutomationConfig()

            self.check(
                config.config_path.exists(),
                f"Config file exists: {config.config_path}"
            )

            # Editor path
            editor_path = config.find_editor_path()
            self.check(
                editor_path is not None,
                f"Editor path configured and found: {editor_path}"
            )

            # AutoIt configuration
            self.check(
                isinstance(config.autoit_enabled, bool),
                f"AutoIt enabled flag valid: {config.autoit_enabled}"
            )

            self.check(
                config.autoit_timeout > 0,
                f"AutoIt timeout positive: {config.autoit_timeout}s"
            )

            # Logging configuration
            self.check(
                config.logging_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                f"Log level valid: {config.logging_level}"
            )

            print(f"\nConfiguration summary:")
            print(f"  AutoIt enabled: {config.autoit_enabled}")
            print(f"  AutoIt available: {config.autoit_script_path.exists()}")
            print(f"  Editor found: {bool(editor_path)}")
            print(f"  Log level: {config.logging_level}")

        except Exception as e:
            print(f"[FAIL] Configuration loading failed: {e}")
            self.checks_failed += 1

    def verify_python_packages(self):
        """Verify required Python packages are installed"""
        print("\n" + "=" * 70)
        print("Python Package Verification")
        print("=" * 70 + "\n")

        packages = {
            "psutil": "Process management",
            "pywin32": "Windows API (Windows only)",
        }

        for package, description in packages.items():
            try:
                __import__(package.replace('pywin32', 'win32gui'))  # pywin32 installs as win32gui
                print(f"[OK]   {package}: {description}")
                self.checks_passed += 1
            except ImportError:
                if package == "pywin32" and sys.platform != "win32":
                    print(f"[SKIP] {package}: Not required on {sys.platform}")
                else:
                    print(f"[FAIL] {package}: {description}")
                    print(f"       Install: pip install {package}")
                    self.checks_failed += 1

    def verify_autoit_installation(self):
        """Verify AutoIt3 is installed (for compilation)"""
        print("\n" + "=" * 70)
        print("AutoIt Installation Verification")
        print("=" * 70 + "\n")

        if sys.platform != "win32":
            print("[SKIP] AutoIt is Windows-only")
            return

        autoit_paths = [
            Path("C:/Program Files (x86)/AutoIt3/Aut2Exe/Aut2exe.exe"),
            Path("C:/Program Files/AutoIt3/Aut2Exe/Aut2exe.exe"),
        ]

        autoit_found = False
        for path in autoit_paths:
            if path.exists():
                print(f"[OK]   AutoIt compiler found: {path}")
                autoit_found = True
                self.checks_passed += 1
                break

        if not autoit_found:
            self.warn(
                False,
                "AutoIt compiler not found",
                "Install from: https://www.autoitscript.com/"
            )
            print("       Note: Only required for compiling, not for using pre-compiled sf2_loader.exe")

    def verify_functionality(self):
        """Verify basic functionality"""
        print("\n" + "=" * 70)
        print("Functionality Verification")
        print("=" * 70 + "\n")

        try:
            from sidm2.sf2_editor_automation import SF2EditorAutomation

            automation = SF2EditorAutomation()

            self.check(
                automation.editor_path is not None,
                f"Can create automation instance"
            )

            self.check(
                hasattr(automation, 'launch_editor_with_file'),
                "launch_editor_with_file method exists"
            )

            self.check(
                hasattr(automation, '_launch_with_autoit'),
                "_launch_with_autoit method exists"
            )

            self.check(
                hasattr(automation, '_launch_manual_workflow'),
                "_launch_manual_workflow method exists"
            )

            self.check(
                automation.config is not None,
                "Config integration works"
            )

        except Exception as e:
            print(f"[FAIL] Functionality verification failed: {e}")
            self.checks_failed += 1

    def run_integration_tests(self):
        """Run integration test suite"""
        print("\n" + "=" * 70)
        print("Integration Test Suite")
        print("=" * 70 + "\n")

        test_script = Path("pyscript/test_autoit_integration.py")

        if not test_script.exists():
            print(f"[FAIL] Test script not found: {test_script}")
            self.checks_failed += 1
            return

        print("Running integration tests...")
        print()

        try:
            result = subprocess.run(
                [sys.executable, str(test_script)],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                print("[OK]   All integration tests passed")
                self.checks_passed += 1

                # Show summary
                for line in result.stdout.split('\n'):
                    if 'Tests run:' in line or 'Tests passed:' in line or 'Tests failed:' in line:
                        print(f"       {line.strip()}")
            else:
                print("[FAIL] Some integration tests failed")
                print(f"       Exit code: {result.returncode}")
                self.checks_failed += 1

                # Show failures
                for line in result.stdout.split('\n'):
                    if '[FAIL]' in line:
                        print(f"       {line.strip()}")

        except subprocess.TimeoutExpired:
            print("[FAIL] Integration tests timeout")
            self.checks_failed += 1
        except Exception as e:
            print(f"[FAIL] Integration tests error: {e}")
            self.checks_failed += 1

    def print_summary(self):
        """Print deployment verification summary"""
        print("\n" + "=" * 70)
        print("Deployment Verification Summary")
        print("=" * 70 + "\n")

        total = self.checks_passed + self.checks_failed
        print(f"Checks run: {total}")
        print(f"Checks passed: {self.checks_passed}")
        print(f"Checks failed: {self.checks_failed}")
        print(f"Warnings: {self.warnings}")
        print()

        if self.checks_failed == 0:
            print("[OK] Deployment verified successfully!")
            print()
            print("Status: READY FOR USE")
            print()
            print("Next steps:")
            print("  1. Review: docs/guides/SF2_EDITOR_AUTOIT_HYBRID_GUIDE.md")
            print("  2. Try: python pyscript/example_autoit_usage.py")
            print("  3. Integrate into your workflow")
        else:
            print(f"[FAIL] Deployment verification failed ({self.checks_failed} issues)")
            print()
            print("Status: NEEDS ATTENTION")
            print()
            print("Actions required:")
            print("  1. Review failed checks above")
            print("  2. See: scripts/autoit/DEPLOYMENT.md")
            print("  3. Run: python pyscript/verify_deployment.py --fix")

        if self.warnings > 0:
            print()
            print(f"Note: {self.warnings} warnings (optional features not available)")

        print()

    def verify_all(self):
        """Run all verification checks"""
        print("\n" + "=" * 70)
        print("AutoIt Hybrid Automation - Deployment Verification")
        print("=" * 70)

        self.verify_files()
        self.verify_python_packages()
        self.verify_configuration()
        self.verify_autoit_installation()
        self.verify_functionality()
        self.run_integration_tests()
        self.print_summary()

        return self.checks_failed == 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Verify AutoIt hybrid automation deployment'
    )
    parser.add_argument(
        '--fix', action='store_true',
        help='Attempt to fix issues automatically'
    )
    args = parser.parse_args()

    verifier = DeploymentVerifier(fix_issues=args.fix)
    success = verifier.verify_all()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
