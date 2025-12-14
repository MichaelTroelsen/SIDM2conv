#!/usr/bin/env python3
"""
Analyze SID collections and generate inventory document.
Lists files, metadata, and detected player types for each collection.
"""

import os
import struct
from pathlib import Path
from collections import defaultdict

def parse_sid_header(filepath):
    """
    Parse PSID/RSID header to extract metadata.

    Returns dict with:
    - load_addr: Load address
    - init_addr: Init address
    - play_addr: Play address
    - name: Song name
    - author: Author name
    - released: Release info
    - subtunes: Number of subtunes
    """
    result = {
        'load_addr': None,
        'init_addr': None,
        'play_addr': None,
        'name': None,
        'author': None,
        'released': None,
        'subtunes': 0,
    }

    try:
        with open(filepath, 'rb') as f:
            header = f.read(126)

            if len(header) < 122:
                return result

            # Parse header fields
            magic = header[0:4].decode('ascii', errors='ignore')
            version = struct.unpack('>H', header[4:6])[0]

            result['load_addr'] = struct.unpack('>H', header[8:10])[0]
            result['init_addr'] = struct.unpack('>H', header[10:12])[0]
            result['play_addr'] = struct.unpack('>H', header[12:14])[0]
            result['subtunes'] = struct.unpack('>H', header[14:16])[0]

            # Extract name, author, released (null-terminated strings)
            name = header[16:48].split(b'\x00')[0].decode('ascii', errors='ignore').strip()
            author = header[48:80].split(b'\x00')[0].decode('ascii', errors='ignore').strip()
            released = header[80:112].split(b'\x00')[0].decode('ascii', errors='ignore').strip()

            if name:
                result['name'] = name
            if author:
                result['author'] = author
            if released:
                result['released'] = released

    except Exception as e:
        pass

    return result

def detect_player_type(init_addr, play_addr):
    """
    Guess player type based on init/play addresses.
    This is a heuristic - actual detection needs disassembly analysis.
    """
    # Laxity patterns
    if init_addr == 0x1000 or init_addr == 0xA000:
        if play_addr in (init_addr, 0x10A1, init_addr + 0xA1):
            return "Laxity NewPlayer v21 (likely)"

    # Driver 11 patterns
    if init_addr == 0x0D7E:
        return "Driver 11 (SF2)"

    if play_addr == 0x0D7E or play_addr == 0x0D81:
        return "Driver 11 or SF2 variant (likely)"

    return "Unknown"

def analyze_collection(dirpath):
    """
    Analyze a SID collection directory.

    Returns dict with file info and statistics.
    """
    results = {
        'total_files': 0,
        'files': [],
        'stats': defaultdict(int),
    }

    if not os.path.isdir(dirpath):
        return results

    sid_files = sorted(Path(dirpath).glob("*.sid"))
    results['total_files'] = len(sid_files)

    for sid_file in sid_files:
        metadata = parse_sid_header(str(sid_file))
        player = detect_player_type(metadata['load_addr'], metadata['play_addr'])

        file_info = {
            'filename': sid_file.name,
            'size': sid_file.stat().st_size,
            'load_addr': f"${metadata['load_addr']:04X}" if metadata['load_addr'] else "N/A",
            'init_addr': f"${metadata['init_addr']:04X}" if metadata['init_addr'] else "N/A",
            'play_addr': f"${metadata['play_addr']:04X}" if metadata['play_addr'] else "N/A",
            'subtunes': metadata['subtunes'],
            'author': metadata['author'] or "Unknown",
            'player_type': player,
        }

        results['files'].append(file_info)
        results['stats'][player] += 1

    return results

def generate_inventory_document():
    """
    Generate comprehensive inventory document for all SID collections.
    """
    collections = {
        'Hubbard_Rob': './Hubbard_Rob',
        'Galway_Martin': './Galway_Martin',
        'Tel_Jeroen': './Tel_Jeroen',
        'Fun_Fun': './Fun_Fun',
        'Laxity': './Laxity',
    }

    doc = []
    doc.append("=" * 80)
    doc.append("SID COLLECTIONS INVENTORY & ANALYSIS")
    doc.append("=" * 80)
    doc.append("")
    doc.append(f"Generated: 2025-12-14")
    doc.append(f"Collections Analyzed: {len(collections)}")
    doc.append("")

    total_all_files = 0
    all_player_stats = defaultdict(int)

    # Analyze each collection
    for coll_name, coll_path in collections.items():
        doc.append("")
        doc.append("=" * 80)
        doc.append(f"{coll_name.upper()}")
        doc.append("=" * 80)

        analysis = analyze_collection(coll_path)
        total_files = analysis['total_files']
        total_all_files += total_files

        doc.append(f"\nTotal Files: {total_files}")
        doc.append(f"Path: {coll_path}")
        doc.append("")

        # Player type statistics
        doc.append("PLAYER TYPE DISTRIBUTION:")
        doc.append("-" * 80)
        for player_type in sorted(analysis['stats'].keys()):
            count = analysis['stats'][player_type]
            percentage = (count / total_files * 100) if total_files > 0 else 0
            doc.append(f"  {player_type:<40} {count:3d} files ({percentage:5.1f}%)")
            all_player_stats[player_type] += count

        doc.append("")
        doc.append("FILE LISTING:")
        doc.append("-" * 80)
        doc.append(f"{'Filename':<40} {'Size':<8} {'Player Type':<20} {'Subtunes':<4}")
        doc.append("-" * 80)

        for file_info in analysis['files']:
            filename = file_info['filename']
            size = file_info['size']
            player = file_info['player_type']
            subtunes = file_info['subtunes']

            # Truncate long filenames
            if len(filename) > 39:
                filename = filename[:36] + "..."

            doc.append(f"{filename:<40} {size:>7} {player:<20} {subtunes:>3}")

        doc.append("")

    # Summary statistics
    doc.append("")
    doc.append("=" * 80)
    doc.append("OVERALL STATISTICS")
    doc.append("=" * 80)
    doc.append("")
    doc.append(f"Total Files Across All Collections: {total_all_files}")
    doc.append("")
    doc.append("COMBINED PLAYER TYPE DISTRIBUTION:")
    doc.append("-" * 80)
    for player_type in sorted(all_player_stats.keys()):
        count = all_player_stats[player_type]
        percentage = (count / total_all_files * 100) if total_all_files > 0 else 0
        doc.append(f"  {player_type:<40} {count:3d} files ({percentage:5.1f}%)")

    doc.append("")
    doc.append("=" * 80)
    doc.append("COLLECTION COMPARISON")
    doc.append("=" * 80)
    doc.append("")

    doc.append(f"{'Collection':<20} {'Files':<8} {'Laxity':<10} {'Driver 11':<12} {'Unknown':<10}")
    doc.append("-" * 80)

    for coll_name, coll_path in collections.items():
        analysis = analyze_collection(coll_path)
        stats = analysis['stats']
        total = analysis['total_files']

        laxity = sum(v for k, v in stats.items() if 'Laxity' in k)
        driver11 = sum(v for k, v in stats.items() if 'Driver 11' in k)
        unknown = sum(v for k, v in stats.items() if 'Unknown' in k)

        doc.append(f"{coll_name:<20} {total:<8} {laxity:<10} {driver11:<12} {unknown:<10}")

    doc.append("")
    doc.append("=" * 80)
    doc.append("IMPORTANT NOTES")
    doc.append("=" * 80)
    doc.append("")
    doc.append("1. PLAYER TYPE DETECTION METHOD:")
    doc.append("   This document uses heuristic-based player detection based on init/play")
    doc.append("   addresses. For accurate detection, use SIDdecompiler analysis.")
    doc.append("")
    doc.append("2. LAXITY DETECTION:")
    doc.append("   Files with init address $1000 or $A000 are likely Laxity NewPlayer v21.")
    doc.append("   This needs validation with actual disassembly.")
    doc.append("")
    doc.append("3. DRIVER 11 DETECTION:")
    doc.append("   Files with init address $0D7E (SF2 standard) are likely SF2 drivers.")
    doc.append("")
    doc.append("4. CONVERSION IMPLICATIONS:")
    doc.append("   - Laxity files: Expected conversion accuracy 1-8% with Driver 11/NP20")
    doc.append("   - Laxity files: Expected conversion accuracy 70-90% with custom Laxity driver")
    doc.append("   - Driver 11 files: Already in correct format")
    doc.append("")
    doc.append("5. FUTURE IMPROVEMENTS:")
    doc.append("   Use SIDdecompiler disassembly analysis for 95%+ accurate player detection.")
    doc.append("   Current code size heuristic discovered in research can achieve >90% accuracy.")
    doc.append("")
    doc.append("=" * 80)
    doc.append(f"Document generated: 2025-12-14")
    doc.append(f"Analysis tool: analyze_sid_collections.py")
    doc.append("=" * 80)

    return "\n".join(doc)

if __name__ == "__main__":
    print("Analyzing SID collections...")
    document = generate_inventory_document()

    # Save to file
    output_path = "SID_COLLECTIONS_INVENTORY.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(document)

    print(f"Document saved to: {output_path}")
    print(f"\nDocument preview:")
    print(document[:2000])
    print(f"\n... (document truncated, full content saved to {output_path})")
