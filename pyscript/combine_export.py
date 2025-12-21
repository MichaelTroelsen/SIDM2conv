#!/usr/bin/env python3
"""Combine all SF2 export files into one comprehensive Markdown document"""

import os
from pathlib import Path

export_dir = Path("output/stinsen_final_export")
output_file = "SF2_COMPLETE_EXPORT.md"

# File organization order
file_order = [
    "summary.txt",
    "orderlist.txt",
    # Sequences in order
    *[f"sequence_{i:02X}.txt" for i in range(0x16)],
    "instruments.txt",
    "wave.txt",
    "pulse.txt",
    "filter.txt",
    "arp.txt",
    "commands.txt",
    "tempo.txt",
    "hr.txt",
    "init.txt",
]

print(f"Combining SF2 export files into {output_file}...")

with open(output_file, 'w', encoding='utf-8') as out:
    # Write header
    out.write("# SF2 Complete Export - Laxity Stinsen Last Night Of 89\n\n")
    out.write("**Generated:** 2025-12-19 20:22:00\n")
    out.write("**Source:** learnings/Laxity - Stinsen - Last Night Of 89.sf2\n")
    out.write("**Player:** Laxity NewPlayer v21\n\n")
    out.write("---\n\n")
    out.write("## Table of Contents\n\n")
    
    # Generate TOC
    toc_entries = []
    for filename in file_order:
        file_path = export_dir / filename
        if file_path.exists():
            section_name = filename.replace('.txt', '').replace('_', ' ').title()
            anchor = section_name.lower().replace(' ', '-')
            toc_entries.append(f"- [{section_name}](#{anchor})")
    
    out.write("\n".join(toc_entries))
    out.write("\n\n---\n\n")
    
    # Process each file
    files_processed = 0
    for filename in file_order:
        file_path = export_dir / filename
        
        if not file_path.exists():
            continue
        
        files_processed += 1
        section_name = filename.replace('.txt', '').replace('_', ' ').title()
        
        print(f"  [{files_processed}/33] Processing {filename}...")
        
        # Write section header
        out.write(f"## {section_name}\n\n")
        
        # Read and write file content
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            # Wrap in code block for formatted display
            out.write("```\n")
            out.write(content)
            out.write("\n```\n\n")
        
        # Add separator
        out.write("---\n\n")

print(f"\nComplete! Combined {files_processed} files into {output_file}")
print(f"File size: {os.path.getsize(output_file) / 1024:.1f} KB")
