#!/usr/bin/env python3
"""
SIDM2 Project Cleanup Tool

Identifies and optionally removes experimental, temporary, and test files
that accumulate during development.

Usage:
    python cleanup.py --scan           # Scan and show what would be cleaned
    python cleanup.py --clean          # Actually remove files (requires confirmation)
    python cleanup.py --clean --force  # Remove without confirmation
    python cleanup.py --output-only    # Clean only output directory
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
import shutil

# File patterns to identify for cleanup
CLEANUP_PATTERNS = {
    'test_files': [
        'test_*.py',
        'test_*.log',
        'test_*.sf2',
        'test_*.sid',
        'test_*.wav',
        'test_*.dump',
        'test_*.html',
        'test_*.txt',
    ],
    'temp_files': [
        'temp_*',
        'tmp_*',
        '*.tmp',
        '*.temp',
        '*_temp.*',
        '*_tmp.*',
    ],
    'backup_files': [
        '*_backup.*',
        '*_old.*',
        '*.bak',
        '*.backup',
    ],
    'experiment_files': [
        'experiment_*',
        'debug_*',
        'scratch_*',
    ],
    'log_files': [
        '*.log',
        'pipeline_*.log',
    ],
    'validation_html': [
        'validation_test_*.html',
    ],
}

# Directories to clean in output/
OUTPUT_TEST_DIRS = [
    'test_*',
    'Test_*',
    'midi_comparison',
    'Laxity_Test',
]

# Files to ALWAYS keep (never clean)
KEEP_FILES = [
    'test_laxity_accuracy.py',  # Production validation script
    'complete_pipeline_with_validation.py',
    'SIDwinder.log',  # Keep main log
]

# Directories to ALWAYS keep
KEEP_DIRS = [
    'output/SIDSF2player_Complete_Pipeline',  # Main pipeline output
    'validation',  # Validation system data
    'scripts/test_*.py',  # Unit tests in scripts/
]

class CleanupTool:
    def __init__(self, root_dir='.'):
        self.root_dir = Path(root_dir)
        self.files_to_clean = []
        self.dirs_to_clean = []
        self.total_size = 0

    def should_keep(self, path):
        """Check if a file/directory should be kept"""
        rel_path = str(path.relative_to(self.root_dir))

        # Check against keep list
        for keep in KEEP_FILES:
            if path.name == keep or rel_path == keep:
                return True

        # Check against keep directories
        for keep_dir in KEEP_DIRS:
            if rel_path.startswith(keep_dir.replace('*', '')):
                return True

        return False

    def matches_pattern(self, path, patterns):
        """Check if path matches any cleanup pattern"""
        import fnmatch
        for pattern in patterns:
            if fnmatch.fnmatch(path.name, pattern):
                return True
        return False

    def scan_root_files(self):
        """Scan root directory for cleanup candidates"""
        print("\n[1/3] Scanning root directory...")

        for category, patterns in CLEANUP_PATTERNS.items():
            for pattern in patterns:
                for path in self.root_dir.glob(pattern):
                    if path.is_file() and not self.should_keep(path):
                        self.files_to_clean.append((path, category))
                        self.total_size += path.stat().st_size

    def scan_output_dirs(self):
        """Scan output directory for test/experiment directories"""
        print("[2/3] Scanning output directory...")

        output_dir = self.root_dir / 'output'
        if not output_dir.exists():
            return

        for pattern in OUTPUT_TEST_DIRS:
            for path in output_dir.glob(pattern):
                if path.is_dir() and not self.should_keep(path):
                    self.dirs_to_clean.append(path)
                    # Calculate directory size
                    size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
                    self.total_size += size

    def scan_temp_outputs(self):
        """Scan for temporary output files in root"""
        print("[3/3] Scanning for temporary outputs...")

        # Look for orphaned output files
        for ext in ['.sf2', '.sid', '.dump', '.wav', '.hex']:
            for path in self.root_dir.glob(f'*{ext}'):
                if path.is_file() and not self.should_keep(path):
                    # Check if it's in a known good location
                    if path.parent == self.root_dir:  # In root, likely temporary
                        self.files_to_clean.append((path, 'orphaned_output'))
                        self.total_size += path.stat().st_size

    def print_report(self):
        """Print cleanup report"""
        print("\n" + "="*80)
        print("CLEANUP REPORT")
        print("="*80)

        # Group by category
        by_category = {}
        for path, category in self.files_to_clean:
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(path)

        # Print files by category
        print("\n[FILES TO CLEAN]")
        if self.files_to_clean:
            for category, paths in sorted(by_category.items()):
                print(f"\n  {category.replace('_', ' ').title()} ({len(paths)} files):")
                for path in sorted(paths)[:10]:  # Show first 10
                    rel_path = path.relative_to(self.root_dir)
                    size_kb = path.stat().st_size / 1024
                    print(f"    - {rel_path} ({size_kb:.1f} KB)")
                if len(paths) > 10:
                    print(f"    ... and {len(paths) - 10} more")
        else:
            print("  None found")

        # Print directories
        print("\n[DIRECTORIES TO CLEAN]")
        if self.dirs_to_clean:
            for path in sorted(self.dirs_to_clean):
                rel_path = path.relative_to(self.root_dir)
                size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
                size_mb = size / (1024 * 1024)
                file_count = sum(1 for _ in path.rglob('*') if _.is_file())
                print(f"    - {rel_path} ({file_count} files, {size_mb:.1f} MB)")
        else:
            print("  None found")

        # Summary
        print("\n" + "="*80)
        print(f"Total items: {len(self.files_to_clean)} files + {len(self.dirs_to_clean)} directories")
        print(f"Total size: {self.total_size / (1024 * 1024):.1f} MB")
        print("="*80)

    def clean(self, force=False):
        """Actually remove the files and directories"""
        if not self.files_to_clean and not self.dirs_to_clean:
            print("\n[OK] Nothing to clean!")
            return

        # Confirmation
        if not force:
            print(f"\n[WARNING] About to remove {len(self.files_to_clean)} files and {len(self.dirs_to_clean)} directories")
            print(f"          Total size: {self.total_size / (1024 * 1024):.1f} MB")
            response = input("\nProceed? (yes/no): ")
            if response.lower() != 'yes':
                print("Cleanup cancelled.")
                return

        # Create backup list
        backup_list = self.root_dir / f'cleanup_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        with open(backup_list, 'w') as f:
            f.write("SIDM2 Cleanup Report\n")
            f.write(f"Date: {datetime.now().isoformat()}\n\n")
            f.write("Files removed:\n")
            for path, category in self.files_to_clean:
                f.write(f"  {path.relative_to(self.root_dir)} ({category})\n")
            f.write("\nDirectories removed:\n")
            for path in self.dirs_to_clean:
                f.write(f"  {path.relative_to(self.root_dir)}\n")

        print(f"\n[INFO] Backup list created: {backup_list}")

        # Remove files
        print("\n[CLEANUP] Removing files...")
        for path, category in self.files_to_clean:
            try:
                path.unlink()
                print(f"  [OK] {path.relative_to(self.root_dir)}")
            except Exception as e:
                print(f"  [ERROR] {path.relative_to(self.root_dir)}: {e}")

        # Remove directories
        print("\n[CLEANUP] Removing directories...")
        for path in self.dirs_to_clean:
            try:
                shutil.rmtree(path)
                print(f"  [OK] {path.relative_to(self.root_dir)}")
            except Exception as e:
                print(f"  [ERROR] {path.relative_to(self.root_dir)}: {e}")

        print(f"\n[COMPLETE] Cleanup finished! {len(self.files_to_clean)} files and {len(self.dirs_to_clean)} directories removed.")
        print(f"           Backup list: {backup_list}")

def main():
    parser = argparse.ArgumentParser(description='SIDM2 Project Cleanup Tool')
    parser.add_argument('--scan', action='store_true', help='Scan and show what would be cleaned')
    parser.add_argument('--clean', action='store_true', help='Actually remove files')
    parser.add_argument('--force', action='store_true', help='Skip confirmation')
    parser.add_argument('--output-only', action='store_true', help='Clean only output directory')

    args = parser.parse_args()

    # Default to scan if no action specified
    if not args.scan and not args.clean:
        args.scan = True

    tool = CleanupTool()

    # Scan
    if args.output_only:
        tool.scan_output_dirs()
    else:
        tool.scan_root_files()
        tool.scan_output_dirs()
        tool.scan_temp_outputs()

    # Report
    tool.print_report()

    # Clean if requested
    if args.clean:
        tool.clean(force=args.force)
    else:
        print("\n[TIP] To clean these files, run: python cleanup.py --clean")

if __name__ == '__main__':
    main()
