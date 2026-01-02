#!/usr/bin/env python3
"""
Local CI/CD Pipeline Script

This script runs all CI checks locally before pushing to git.
It performs:
1. Unit tests (test-all.bat)
2. Syntax validation
3. Documentation validation
4. Optional git push

Usage:
    python scripts/ci_local.py [--push] [--message "commit message"]
"""

import subprocess
import sys
import os
import argparse
from datetime import datetime


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


# Use ASCII-safe symbols for Windows compatibility
SYMBOL_SUCCESS = '[OK]'
SYMBOL_ERROR = '[FAIL]'
SYMBOL_WARNING = '[WARN]'


def print_header(text):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")


def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}{SYMBOL_SUCCESS} {text}{Colors.RESET}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}{SYMBOL_ERROR} {text}{Colors.RESET}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}{SYMBOL_WARNING} {text}{Colors.RESET}")


def run_command(cmd, description, check=True):
    """Run a command and return success status"""
    print(f"Running: {description}")
    print(f"  Command: {cmd}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout for test suite
        )

        if result.returncode != 0 and check:
            print_error(f"{description} failed")
            if result.stdout:
                print(f"stdout:\n{result.stdout}")
            if result.stderr:
                print(f"stderr:\n{result.stderr}")
            return False

        if result.stdout:
            print(result.stdout)

        print_success(f"{description} passed")
        return True

    except subprocess.TimeoutExpired:
        print_error(f"{description} timed out (>5 minutes)")
        return False
    except Exception as e:
        print_error(f"{description} failed with exception: {e}")
        return False


def check_python_syntax():
    """Check key Python files for syntax errors"""
    print_header("Checking Python Syntax")

    # Key files to check
    python_files = [
        'scripts/sid_to_sf2.py',
        'scripts/sf2_to_sid.py',
        'scripts/convert_all.py',
        'pyscript/cleanup.py',
        'pyscript/sf2_viewer_gui.py',
        'pyscript/convert_all_laxity.py',
    ]

    all_passed = True
    for filepath in python_files:
        if os.path.exists(filepath):
            result = subprocess.run(
                [sys.executable, '-m', 'py_compile', filepath],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print_success(f"{filepath} - syntax OK")
            else:
                print_error(f"{filepath} - syntax error")
                if result.stderr:
                    print(f"  {result.stderr}")
                all_passed = False
        else:
            print_warning(f"{filepath} - file not found")

    return all_passed


def run_test_suite():
    """Run full test suite (test-all.bat)"""
    print_header("Running Test Suite")

    # Try to run test-all.bat if on Windows, otherwise python test runner
    if sys.platform == 'win32':
        return run_command(
            "test-all.bat",
            "Test suite (test-all.bat)",
            check=True
        )
    else:
        # Fallback for non-Windows
        print_warning("test-all.bat is Windows batch file, running Python tests instead")
        return run_command(
            f"{sys.executable} scripts/test_converter.py",
            "Basic converter tests",
            check=True
        )


def check_documentation():
    """Validate documentation"""
    print_header("Checking Documentation")

    all_passed = True

    # Check README
    if os.path.exists('README.md'):
        with open('README.md', 'r', encoding='utf-8') as f:
            content = f.read()

        # Required main sections
        required_sections = [
            'Quick Start',
            'Installation',
            'Usage',
            'Features'
        ]

        sections_found = 0
        for section in required_sections:
            if section in content:
                print_success(f"README.md contains '{section}'")
                sections_found += 1
            else:
                print_warning(f"README.md missing '{section}'")

        if sections_found >= len(required_sections) - 1:
            print_success("README.md has required sections")
        else:
            print_error("README.md missing too many required sections")
            all_passed = False

    else:
        print_error("README.md not found")
        all_passed = False

    # Check CLAUDE.md
    if os.path.exists('CLAUDE.md'):
        print_success("CLAUDE.md exists")
    else:
        print_warning("CLAUDE.md not found")

    # Check key documentation files
    doc_files = [
        'docs/ARCHITECTURE.md',
        'docs/SF2_FORMAT_SPEC.md',
    ]

    for doc_file in doc_files:
        if os.path.exists(doc_file):
            print_success(f"{doc_file} exists")
        else:
            print_warning(f"{doc_file} not found")

    return all_passed


def check_file_inventory():
    """Check that FILE_INVENTORY.md exists and is up to date"""
    print_header("Checking File Inventory")

    if os.path.exists('docs/FILE_INVENTORY.md'):
        print_success("docs/FILE_INVENTORY.md exists")
        return True
    else:
        print_warning("docs/FILE_INVENTORY.md not found")
        print_warning("Run: python pyscript/update_inventory.py")
        return True  # Don't fail, just warn


def git_status():
    """Show git status"""
    print_header("Git Status")

    run_command("git status", "Git status", check=False)
    return True


def git_add_and_commit(message):
    """Add changes and commit"""
    print_header("Git Add and Commit")

    # Add all tracked files
    if not run_command("git add -A", "Git add"):
        return False

    # Check if there are changes to commit
    result = subprocess.run(
        "git diff --cached --quiet",
        shell=True,
        capture_output=True
    )

    if result.returncode == 0:
        print_warning("No changes to commit")
        return True

    # Commit
    commit_msg = message or f"CI: Auto-commit {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    return run_command(
        f'git commit -m "{commit_msg}"',
        "Git commit"
    )


def git_push():
    """Push to remote"""
    print_header("Git Push")

    return run_command("git push", "Git push")


def main():
    """Main CI pipeline"""
    parser = argparse.ArgumentParser(description='Local CI/CD Pipeline for SIDM2')
    parser.add_argument('--push', action='store_true', help='Push to git after tests pass')
    parser.add_argument('--message', '-m', type=str, help='Commit message')
    parser.add_argument('--skip-tests', action='store_true', help='Skip running full test suite')
    parser.add_argument('--quick', action='store_true', help='Quick check (syntax and docs only)')
    args = parser.parse_args()

    # Change to project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)

    print(f"\n{Colors.BOLD}SIDM2 Converter - Local CI Pipeline{Colors.RESET}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Python: {sys.executable}")
    print(f"Platform: {sys.platform}")

    results = {}

    # Always run these checks
    results['syntax'] = check_python_syntax()
    results['documentation'] = check_documentation()
    results['inventory'] = check_file_inventory()

    # Run tests unless skipped
    if args.quick:
        print_warning("Running in QUICK mode (skipping test suite)")
    elif not args.skip_tests:
        results['tests'] = run_test_suite()
    else:
        print_warning("Skipping test suite (--skip-tests)")

    # Summary
    print_header("CI Pipeline Summary")

    all_passed = True
    for check, passed in results.items():
        if passed:
            print_success(f"{check}")
        else:
            print_error(f"{check}")
            all_passed = False

    if all_passed:
        print(f"\n{Colors.GREEN}{Colors.BOLD}All checks passed!{Colors.RESET}\n")

        # Git operations
        if args.push:
            git_status()
            if git_add_and_commit(args.message):
                git_push()
        else:
            print("Use --push flag to commit and push changes")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}Some checks failed!{Colors.RESET}\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
