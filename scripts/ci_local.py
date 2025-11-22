#!/usr/bin/env python3
"""
Local CI/CD Pipeline Script

This script runs all CI checks locally before pushing to git.
It performs:
1. Code quality checks
2. Unit tests
3. Documentation validation
4. Smoke tests
5. Optional git push

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
            text=True
        )

        if result.returncode != 0 and check:
            print_error(f"{description} failed")
            if result.stdout:
                print(f"stdout: {result.stdout}")
            if result.stderr:
                print(f"stderr: {result.stderr}")
            return False

        if result.stdout:
            print(result.stdout)

        print_success(f"{description} passed")
        return True

    except Exception as e:
        print_error(f"{description} failed with exception: {e}")
        return False


def check_python_syntax():
    """Check Python files for syntax errors"""
    print_header("Checking Python Syntax")

    python_files = [
        'sid_to_sf2.py',
        'analyze_sid.py',
        'laxity_analyzer.py',
        'test_converter.py'
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
                print(result.stderr)
                all_passed = False
        else:
            print_warning(f"{filepath} - file not found")

    return all_passed


def run_tests():
    """Run unit tests"""
    print_header("Running Unit Tests")

    return run_command(
        f"{sys.executable} -m unittest test_converter -v",
        "Unit tests"
    )


def run_smoke_test():
    """Run smoke test with actual SID file"""
    print_header("Running Smoke Test")

    # Check if input file exists in SID directory
    sid_file = os.path.join('SID', 'Unboxed_Ending_8580.sid')
    if not os.path.exists(sid_file):
        print_warning(f"{sid_file} not found, skipping smoke test")
        return True

    # Run converter
    success = run_command(
        f"{sys.executable} sid_to_sf2.py {sid_file} ci_test_output.sf2",
        "Converter smoke test"
    )

    if success:
        # Check output exists
        if os.path.exists('ci_test_output.sf2'):
            size = os.path.getsize('ci_test_output.sf2')
            print_success(f"Output file created: {size} bytes")
            # Clean up
            os.remove('ci_test_output.sf2')
            return True
        else:
            print_error("Output file not created")
            return False

    return False


def convert_all_sid_files():
    """Convert all SID files to SF2 and save in SF2 directory"""
    print_header("Converting All SID Files to SF2")

    sid_dir = 'SID'
    sf2_dir = 'SF2'

    # Check directories exist
    if not os.path.exists(sid_dir):
        print_warning(f"{sid_dir} directory not found, skipping conversion")
        return True

    # Create SF2 directory if it doesn't exist
    if not os.path.exists(sf2_dir):
        os.makedirs(sf2_dir)
        print_success(f"Created {sf2_dir} directory")

    # Get list of SID files
    sid_files = [f for f in os.listdir(sid_dir) if f.endswith('.sid')]
    if not sid_files:
        print_warning("No SID files found")
        return True

    # Convert each file
    all_success = True
    for sid_file in sid_files:
        input_path = os.path.join(sid_dir, sid_file)
        output_file = sid_file.replace('.sid', '.sf2')
        output_path = os.path.join(sf2_dir, output_file)

        success = run_command(
            f"{sys.executable} sid_to_sf2.py {input_path} {output_path}",
            f"Converting {sid_file}",
            check=False
        )

        if success and os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print_success(f"{output_file}: {size} bytes")
        else:
            print_error(f"Failed to convert {sid_file}")
            all_success = False

    print(f"\nConverted {len(sid_files)} SID files to SF2 directory")
    return all_success


def check_documentation():
    """Validate documentation"""
    print_header("Checking Documentation")

    all_passed = True

    # Check README
    if os.path.exists('README.md'):
        with open('README.md', 'r', encoding='utf-8') as f:
            content = f.read()

        required_sections = [
            '## Usage',
            '## File Formats',
            '## Development',
            '## Limitations'
        ]

        for section in required_sections:
            if section in content:
                print_success(f"README.md contains '{section}'")
            else:
                print_warning(f"README.md missing '{section}'")

        print_success("README.md exists and has content")
    else:
        print_error("README.md not found")
        all_passed = False

    # Check CONTRIBUTING
    if os.path.exists('CONTRIBUTING.md'):
        print_success("CONTRIBUTING.md exists")
    else:
        print_error("CONTRIBUTING.md not found")
        all_passed = False

    return all_passed


def check_docstrings():
    """Check that functions have docstrings"""
    print_header("Checking Docstrings")

    import ast

    files = ['sid_to_sf2.py', 'analyze_sid.py', 'laxity_analyzer.py']
    missing = []

    for filename in files:
        if not os.path.exists(filename):
            continue

        with open(filename, 'r', encoding='utf-8') as f:
            try:
                tree = ast.parse(f.read())
            except SyntaxError as e:
                print_error(f"{filename} has syntax error: {e}")
                continue

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not ast.get_docstring(node):
                    missing.append(f"{filename}:{node.lineno} - {node.name}()")
            elif isinstance(node, ast.ClassDef):
                if not ast.get_docstring(node):
                    missing.append(f"{filename}:{node.lineno} - class {node.name}")

    if missing:
        print_warning(f"Found {len(missing)} items without docstrings:")
        for item in missing[:5]:
            print(f"  - {item}")
        if len(missing) > 5:
            print(f"  ... and {len(missing) - 5} more")
    else:
        print_success("All functions and classes have docstrings")

    # Don't fail on missing docstrings, just warn
    return True


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
    parser = argparse.ArgumentParser(description='Local CI/CD Pipeline')
    parser.add_argument('--push', action='store_true', help='Push to git after tests pass')
    parser.add_argument('--message', '-m', type=str, help='Commit message')
    parser.add_argument('--skip-tests', action='store_true', help='Skip running tests')
    args = parser.parse_args()

    # Change to project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)

    print(f"\n{Colors.BOLD}SID to SF2 Converter - Local CI Pipeline{Colors.RESET}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Python: {sys.executable}")

    results = {}

    # Run checks
    results['syntax'] = check_python_syntax()
    results['docstrings'] = check_docstrings()
    results['documentation'] = check_documentation()

    if not args.skip_tests:
        results['tests'] = run_tests()
        results['smoke'] = run_smoke_test()
        results['conversion'] = convert_all_sid_files()
    else:
        print_warning("Skipping tests")

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
            print("Use --push to commit and push changes")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}Some checks failed!{Colors.RESET}\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
