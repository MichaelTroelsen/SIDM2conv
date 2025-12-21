#!/usr/bin/env python3
"""
Combine all SF2 text export files into a single markdown document.

Usage:
    python combine_sf2_export.py <export_directory> <output_md_file>

Example:
    python combine_sf2_export.py output/stinsen_fixed stinsen_complete.md
"""

import os
import sys
from pathlib import Path


def combine_export_files(export_dir, output_md):
    """Combine all txt files from export directory into single markdown."""

    export_path = Path(export_dir)
    if not export_path.exists():
        print(f"Error: Export directory not found: {export_dir}")
        return False

    # Define file order for organized output
    file_order = [
        'summary.txt',
        'orderlist.txt',
        'instruments.txt',
        'wave.txt',
        'pulse.txt',
        'filter.txt',
        'arp.txt',
        'tempo.txt',
        'hr.txt',
        'init.txt',
        'commands.txt',
    ]

    # Add all sequence files (sequence_00.txt, sequence_01.txt, etc.)
    sequence_files = sorted([f.name for f in export_path.glob('sequence_*.txt')])

    # Collect all files to process
    all_files = []

    # Add ordered files first
    for fname in file_order:
        fpath = export_path / fname
        if fpath.exists():
            all_files.append((fname, fpath))

    # Add sequence files
    for fname in sequence_files:
        fpath = export_path / fname
        if fpath.exists():
            all_files.append((fname, fpath))

    if not all_files:
        print(f"Error: No txt files found in {export_dir}")
        return False

    # Write combined markdown
    output_path = Path(output_md)
    with open(output_path, 'w', encoding='utf-8') as out:
        # Write header
        out.write("# SF2 Complete Export\n\n")
        out.write(f"**Source Directory**: `{export_dir}`\n\n")
        out.write(f"**Files Combined**: {len(all_files)}\n\n")
        out.write("---\n\n")

        # Write table of contents
        out.write("## Table of Contents\n\n")
        for idx, (fname, _) in enumerate(all_files, 1):
            section_name = fname.replace('.txt', '').replace('_', ' ').title()
            anchor = fname.replace('.txt', '').replace('_', '-').lower()
            out.write(f"{idx}. [{section_name}](#{anchor})\n")
        out.write("\n---\n\n")

        # Write each file as a section
        for fname, fpath in all_files:
            section_name = fname.replace('.txt', '').replace('_', ' ').title()

            out.write(f"## {section_name}\n\n")
            out.write(f"**Source**: `{fname}`\n\n")

            # Read and write file content (try multiple encodings)
            content = None
            for encoding in ['utf-8', 'cp1252', 'latin-1']:
                try:
                    with open(fpath, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue

            if content is None:
                out.write("```\n")
                out.write(f"Error: Could not decode file with any known encoding\n")
                out.write("```\n\n")
            else:
                # Wrap content in code block for better formatting
                out.write("```\n")
                out.write(content)
                if not content.endswith('\n'):
                    out.write('\n')
                out.write("```\n\n")

            out.write("---\n\n")

    print(f"[OK] Combined {len(all_files)} files into: {output_md}")
    return True


def main():
    if len(sys.argv) != 3:
        print("Usage: python combine_sf2_export.py <export_directory> <output_md_file>")
        print()
        print("Example:")
        print("  python combine_sf2_export.py output/stinsen_fixed stinsen_complete.md")
        sys.exit(1)

    export_dir = sys.argv[1]
    output_md = sys.argv[2]

    success = combine_export_files(export_dir, output_md)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
