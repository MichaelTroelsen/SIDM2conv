#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MD File Cleanup Script
Organizes and removes duplicate/old markdown files
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

# Base directory
BASE_DIR = Path(__file__).parent

# Create archive directory for today
ARCHIVE_DATE = datetime.now().strftime("%Y-%m-%d")
ARCHIVE_DIR = BASE_DIR / "archive" / ARCHIVE_DATE
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

print(f"MD File Cleanup - {ARCHIVE_DATE}")
print("=" * 60)

# 1. Delete INDEX_OLD.md (explicitly marked as old)
old_index = BASE_DIR / "docs" / "INDEX_OLD.md"
if old_index.exists():
    print(f"\n[OK] Deleting: {old_index.relative_to(BASE_DIR)}")
    old_index.unlink()
else:
    print(f"\n[SKIP] Not found: {old_index.relative_to(BASE_DIR)}")

# 2. Move root-level summary files to archive
root_summaries = [
    "CLEANUP_SUMMARY.md",
    "SIDDUMP_INTEGRATION_SUMMARY.md",
    "FILE_MANAGEMENT_RULES.md"
]

print(f"\n[ARCHIVE] Moving root-level summaries to archive/{ARCHIVE_DATE}/")
for filename in root_summaries:
    src = BASE_DIR / filename
    if src.exists():
        dst = ARCHIVE_DIR / filename
        print(f"  [OK] {filename} -> archive/{ARCHIVE_DATE}/")
        shutil.move(str(src), str(dst))
    else:
        print(f"  [SKIP] Not found: {filename}")

# 3. Check for duplicate archive directories
archived_dir = BASE_DIR / "archived"
if archived_dir.exists():
    print(f"\n[WARN] Found duplicate directory: archived/")
    print(f"    Contents:")
    for item in archived_dir.iterdir():
        print(f"      - {item.name}")
    print(f"\n    Recommendation: Merge into archive/ or remove if obsolete")
else:
    print(f"\n[OK] No duplicate 'archived/' directory found")

# 4. Check temp directories
temp_dirs = [BASE_DIR / "temp-exp", BASE_DIR / "temp"]
for temp_dir in temp_dirs:
    if temp_dir.exists():
        md_files = list(temp_dir.glob("*.md"))
        if md_files:
            print(f"\n[TEMP] Found temp directory: {temp_dir.relative_to(BASE_DIR)}/")
            for md_file in md_files:
                print(f"  - {md_file.name}")
            print(f"    Recommendation: Archive or delete if no longer needed")

# 5. Report on output/ MD files (these are generated, should stay)
output_md = list((BASE_DIR / "output").glob("*.md")) if (BASE_DIR / "output").exists() else []
if output_md:
    print(f"\n[KEEP] Generated reports in output/ (keeping):")
    for md_file in output_md:
        size_kb = md_file.stat().st_size // 1024
        print(f"  [OK] {md_file.name} ({size_kb} KB)")

# 6. Summary
print("\n" + "=" * 60)
print("Cleanup Summary:")
print(f"  [OK] Deleted: docs/INDEX_OLD.md")
print(f"  [OK] Archived: {len(root_summaries)} root-level summary files")
print(f"  [TODO] Next: Review duplicate 'archived/' directory")
print(f"  [TODO] Next: Review temp-exp/ directory")
print("\n[DONE] Cleanup complete!")
