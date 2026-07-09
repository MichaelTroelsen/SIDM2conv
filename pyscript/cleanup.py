#!/usr/bin/env python3
"""
SIDM2 Project Cleanup Tool

Identifies and optionally removes experimental, temporary, and test files
that accumulate during development.

Usage:
    python cleanup.py --scan             # Scan and show what would be cleaned
    python cleanup.py --archive          # MOVE flagged files into archive/cleanup_<date>/ (safe, reversible)
    python cleanup.py --clean            # Actually DELETE files (requires confirmation)
    python cleanup.py --archive --force  # Archive without confirmation
    python cleanup.py --output-only      # Clean only output directory

By default --archive is recommended over --clean: it moves files into
archive/cleanup_<date>/ (mirroring their relative path) instead of hard-deleting,
per the project's archive-before-explain protocol. --clean deletes irreversibly.
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
    'test_laxity_accuracy.py',  # Production validation script (in pyscript/)
    'complete_pipeline_with_validation.py',  # Pipeline script (in pyscript/)
    'test_track_view_parity.py',  # Test script (in pyscript/)
    'SIDwinder.log',  # Keep main log
]

# Standard root documentation files (should stay in root)
STANDARD_ROOT_DOCS = [
    'README.md',
    'CONTRIBUTING.md',
    'CHANGELOG.md',
    'CLAUDE.md',
]

# Misplaced documentation mapping (root → docs/)
MISPLACED_DOC_MAPPING = {
    # Analysis and research reports
    '*_ANALYSIS.md': 'docs/analysis/',
    '*_RESEARCH*.md': 'docs/analysis/',
    '*_REPORT.md': 'docs/reference/',

    # Implementation documents
    '*_IMPLEMENTATION.md': 'docs/implementation/',

    # Status and validation documents
    'STATUS.md': 'docs/',
    '*_STATUS.md': 'docs/analysis/',
    '*_NOTES.md': 'docs/guides/',

    # Consolidation and knowledge documents
    '*_CONSOLIDATION*.md': 'docs/archive/',
    'CONSOLIDATION_*.md': 'docs/archive/',
    'KNOWLEDGE_*.md': 'docs/archive/',

    # System and guide documents
    '*_SYSTEM.md': 'docs/guides/',
    'VALIDATION_*.md': 'docs/guides/',

    # Repository references
    'external-repositories.md': 'docs/reference/',
    'sourcerepository.md': 'docs/reference/',
}

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

    def is_git_tracked(self, path):
        """Check if a file is tracked by git"""
        import subprocess
        try:
            rel_path = str(path.relative_to(self.root_dir))
            result = subprocess.run(
                ['git', 'ls-files', '--error-unmatch', rel_path],
                cwd=self.root_dir,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def should_keep(self, path):
        """Check if a file/directory should be kept"""
        rel_path = str(path.relative_to(self.root_dir))

        # RULE 1: NEVER clean files tracked by git
        if self.is_git_tracked(path):
            return True

        # RULE 2: Check against explicit keep list
        for keep in KEEP_FILES:
            if path.name == keep or rel_path == keep:
                return True

        # RULE 3: Check against keep directories
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
        print("\n[1/5] Scanning root directory...")

        for category, patterns in CLEANUP_PATTERNS.items():
            for pattern in patterns:
                for path in self.root_dir.glob(pattern):
                    if path.is_file() and not self.should_keep(path):
                        self.files_to_clean.append((path, category))
                        self.total_size += path.stat().st_size

    def scan_output_dirs(self):
        """Scan output directory for test/experiment directories"""
        print("[2/5] Scanning output directory...")

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
        print("[3/5] Scanning for temporary outputs...")

        # Look for orphaned output files
        for ext in ['.sf2', '.sid', '.dump', '.wav', '.hex']:
            for path in self.root_dir.glob(f'*{ext}'):
                if path.is_file() and not self.should_keep(path):
                    # Check if it's in a known good location
                    if path.parent == self.root_dir:  # In root, likely temporary
                        self.files_to_clean.append((path, 'orphaned_output'))
                        self.total_size += path.stat().st_size

    def scan_python_scripts(self):
        """Scan for Python scripts in root (NEW - v2.5)

        All Python scripts should be in pyscript/ directory.
        Any .py file in root is flagged for cleanup.
        """
        print("[4/5] Scanning for Python scripts in root...")

        for path in self.root_dir.glob('*.py'):
            if path.is_file() and not self.should_keep(path):
                # All .py files should be in pyscript/
                self.files_to_clean.append((path, 'misplaced_python_script'))
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

    def _archive_dest(self, archive_root, path):
        """Destination inside the archive that mirrors `path`'s location relative
        to the project root (so `output/test_x` -> `<archive>/output/test_x` and a
        root file keeps its name). Adds a numeric suffix if the target already
        exists (repeat runs the same day never overwrite an earlier archive)."""
        dest = archive_root / path.relative_to(self.root_dir)
        if dest.exists():
            stem, suffix, n = dest.stem, dest.suffix, 1
            while dest.exists():
                dest = dest.with_name(f"{stem}_{n}{suffix}")
                n += 1
        return dest

    def clean(self, force=False, update_inventory=False, archive=False):
        """Remove the flagged files/directories, or (archive=True) MOVE them into
        archive/cleanup_<date>/ preserving their relative path — the project's
        archive-before-explain protocol (see feedback-archive-protocol): reversible,
        nothing is hard-deleted."""
        # A file can match several patterns and a dir several scan passes, so the
        # lists carry duplicates (harmless when deleting, but archiving the same
        # path twice errors "not found" on the second move). Dedupe by path, first
        # occurrence wins, order preserved.
        seen = set()
        self.files_to_clean = [(p, c) for p, c in self.files_to_clean
                               if not (p in seen or seen.add(p))]
        seen = set()
        self.dirs_to_clean = [p for p in self.dirs_to_clean
                              if not (p in seen or seen.add(p))]

        if not self.files_to_clean and not self.dirs_to_clean:
            print("\n[OK] Nothing to clean!")
            return False

        verb = "archive" if archive else "remove"
        archive_root = None
        if archive:
            archive_root = self.root_dir / 'archive' / f'cleanup_{datetime.now().strftime("%Y-%m-%d")}'

        # Confirmation
        if not force:
            print(f"\n[WARNING] About to {verb} {len(self.files_to_clean)} files and {len(self.dirs_to_clean)} directories")
            print(f"          Total size: {self.total_size / (1024 * 1024):.1f} MB")
            if archive:
                print(f"          Destination: {archive_root.relative_to(self.root_dir)}/")
            response = input("\nProceed? (yes/no): ")
            if response.lower() != 'yes':
                print("Cleanup cancelled.")
                return False

        # Manifest of what was touched. In archive mode it lives INSIDE the archive
        # dir (travels with the files); otherwise at the root as a delete record.
        if archive:
            archive_root.mkdir(parents=True, exist_ok=True)
            backup_list = archive_root / 'MANIFEST.txt'
        else:
            backup_list = self.root_dir / f'cleanup_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        with open(backup_list, 'w') as f:
            f.write("SIDM2 Cleanup Report\n")
            f.write(f"Date: {datetime.now().isoformat()}\n")
            f.write(f"Mode: {'archive (moved)' if archive else 'clean (deleted)'}\n\n")
            f.write(f"Files {verb}d:\n")
            for path, category in self.files_to_clean:
                f.write(f"  {path.relative_to(self.root_dir)} ({category})\n")
            f.write(f"\nDirectories {verb}d:\n")
            for path in self.dirs_to_clean:
                f.write(f"  {path.relative_to(self.root_dir)}\n")

        print(f"\n[INFO] Manifest created: {backup_list.relative_to(self.root_dir)}")

        # Files
        print(f"\n[CLEANUP] {'Archiving' if archive else 'Removing'} files...")
        for path, category in self.files_to_clean:
            rel = path.relative_to(self.root_dir)
            try:
                if archive:
                    dest = self._archive_dest(archive_root, path)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(path), str(dest))
                    print(f"  [OK] {rel} -> {dest.relative_to(self.root_dir)}")
                else:
                    path.unlink()
                    print(f"  [OK] {rel}")
            except Exception as e:
                print(f"  [ERROR] {rel}: {e}")

        # Directories
        print(f"\n[CLEANUP] {'Archiving' if archive else 'Removing'} directories...")
        for path in self.dirs_to_clean:
            rel = path.relative_to(self.root_dir)
            try:
                if archive:
                    dest = self._archive_dest(archive_root, path)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(path), str(dest))
                    print(f"  [OK] {rel} -> {dest.relative_to(self.root_dir)}")
                else:
                    shutil.rmtree(path)
                    print(f"  [OK] {rel}")
            except Exception as e:
                print(f"  [ERROR] {rel}: {e}")

        action = "archived" if archive else "removed"
        print(f"\n[COMPLETE] Cleanup finished! {len(self.files_to_clean)} files and {len(self.dirs_to_clean)} directories {action}.")
        if archive:
            print(f"           Archived to: {archive_root.relative_to(self.root_dir)}/")
        print(f"           Manifest: {backup_list.relative_to(self.root_dir)}")

        # Update inventory if requested
        if update_inventory:
            print("\n[INVENTORY] Updating FILE_INVENTORY.md...")
            try:
                import subprocess
                result = subprocess.run(
                    [sys.executable, 'update_inventory.py'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    print("[INVENTORY] Updated successfully")
                    # Show summary from output
                    for line in result.stdout.strip().split('\n'):
                        if line.startswith('[OK]') or line.startswith('    '):
                            print(f"            {line}")
                else:
                    print(f"[INVENTORY] Update failed: {result.stderr}")
            except Exception as e:
                print(f"[INVENTORY] Update failed: {e}")

        return True

    def scan_experiments(self):
        """Scan experiments directory"""
        print("[+] Scanning experiments directory...")

        experiments_dir = self.root_dir / 'experiments'
        if not experiments_dir.exists():
            return

        # Find all experiment subdirectories
        for exp_dir in experiments_dir.iterdir():
            if exp_dir.is_dir() and exp_dir.name not in ['TEMPLATE', 'ARCHIVE', '.git']:
                # Check if it has a cleanup script (indicates it's a real experiment)
                if (exp_dir / 'cleanup.sh').exists() or (exp_dir / 'cleanup.bat').exists():
                    # Calculate size
                    size = sum(f.stat().st_size for f in exp_dir.rglob('*') if f.is_file())
                    if size > 0:  # Only include if it has content
                        self.dirs_to_clean.append(exp_dir)
                        self.total_size += size

    def scan_misplaced_docs(self):
        """Scan root directory for misplaced documentation files"""
        print("[5/5] Scanning for misplaced documentation...")

        import fnmatch

        # Find all .md files in root
        for md_file in self.root_dir.glob('*.md'):
            if md_file.is_file():
                # Skip standard root documentation
                if md_file.name in STANDARD_ROOT_DOCS:
                    continue

                # RULE 1: Check if file should be kept (git-tracked, etc.)
                if self.should_keep(md_file):
                    continue

                # Check against misplaced doc patterns
                for pattern, target_dir in MISPLACED_DOC_MAPPING.items():
                    if fnmatch.fnmatch(md_file.name, pattern):
                        # Add to files to clean with special category
                        self.files_to_clean.append((md_file, f'misplaced_doc -> {target_dir}'))
                        self.total_size += md_file.stat().st_size
                        break
                else:
                    # No pattern match - generic misplaced doc
                    if md_file.name not in STANDARD_ROOT_DOCS:
                        self.files_to_clean.append((md_file, 'misplaced_doc -> docs/'))
                        self.total_size += md_file.stat().st_size

def main():
    parser = argparse.ArgumentParser(description='SIDM2 Project Cleanup Tool')
    parser.add_argument('--scan', action='store_true', help='Scan and show what would be cleaned')
    parser.add_argument('--archive', action='store_true', help='MOVE flagged files into archive/cleanup_<date>/ (safe, reversible)')
    parser.add_argument('--clean', action='store_true', help='Actually DELETE files (irreversible)')
    parser.add_argument('--force', action='store_true', help='Skip confirmation')
    parser.add_argument('--output-only', action='store_true', help='Clean only output directory')
    parser.add_argument('--experiments', action='store_true', help='Clean only experiments directory')
    parser.add_argument('--all', action='store_true', help='Clean everything (root + output + experiments)')
    parser.add_argument('--update-inventory', action='store_true', help='Update FILE_INVENTORY.md after cleanup')

    args = parser.parse_args()

    # Default to scan if no action specified
    if not args.scan and not args.clean and not args.archive:
        args.scan = True

    tool = CleanupTool()

    # Scan based on flags
    if args.experiments:
        tool.scan_experiments()
    elif args.output_only:
        tool.scan_output_dirs()
    elif args.all:
        tool.scan_root_files()
        tool.scan_output_dirs()
        tool.scan_temp_outputs()
        tool.scan_python_scripts()  # NEW - v2.5: Check for .py files in root
        tool.scan_experiments()
        tool.scan_misplaced_docs()
    else:
        tool.scan_root_files()
        tool.scan_output_dirs()
        tool.scan_temp_outputs()
        tool.scan_python_scripts()  # NEW - v2.5: Check for .py files in root
        tool.scan_misplaced_docs()

    # Report
    tool.print_report()

    # Act if requested (archive is preferred over delete)
    if args.clean or args.archive:
        cleaned = tool.clean(force=args.force, update_inventory=args.update_inventory,
                             archive=args.archive)
        if cleaned and args.update_inventory:
            print("\n[TIP] FILE_INVENTORY.md has been updated")
    else:
        print("\n[TIP] To archive these files (safe, reversible): python cleanup.py --archive")
        print("[TIP] To delete them irreversibly:              python cleanup.py --clean")
        if args.update_inventory:
            print("[TIP] Add --update-inventory to auto-update FILE_INVENTORY.md after cleanup")

if __name__ == '__main__':
    main()
