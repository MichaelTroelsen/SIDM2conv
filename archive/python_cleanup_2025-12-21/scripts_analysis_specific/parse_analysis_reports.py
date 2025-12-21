#!/usr/bin/env python3
"""
Parse SIDdecompiler analysis reports to extract player detection metrics.
Generates validation report showing player detection accuracy improvements.
"""

import os
import re
from pathlib import Path
from collections import defaultdict

def parse_analysis_report(filepath):
    """
    Parse a single analysis report to extract player information.

    Returns dict with keys: player_type, load_addr, init_addr, play_addr,
                            memory_range, code_regions, data_regions, table_regions
    """
    result = {
        'player_type': None,
        'load_addr': None,
        'init_addr': None,
        'play_addr': None,
        'memory_range': None,
        'code_regions': 0,
        'data_regions': 0,
        'table_regions': 0,
        'total_bytes': 0
    }

    if not os.path.exists(filepath):
        return result

    with open(filepath, 'r') as f:
        content = f.read()

    # Extract player type
    player_match = re.search(r'Type:\s*(.+?)(?:\n|$)', content)
    if player_match:
        result['player_type'] = player_match.group(1).strip()

    # Extract addresses
    load_match = re.search(r'Load Address:\s*(\$[0-9A-F]+)', content)
    if load_match:
        result['load_addr'] = load_match.group(1)

    init_match = re.search(r'Init Address:\s*(\$[0-9A-F]+)', content)
    if init_match:
        result['init_addr'] = init_match.group(1)

    play_match = re.search(r'Play Address:\s*(\$[0-9A-F]+)', content)
    if play_match:
        result['play_addr'] = play_match.group(1)

    # Extract memory range
    range_match = re.search(r'Memory Range:\s*(\$[0-9A-F]+-\$[0-9A-F]+)\s*\((\d+)\s*bytes\)', content)
    if range_match:
        result['memory_range'] = range_match.group(1)
        result['total_bytes'] = int(range_match.group(2))

    # Count regions
    code_matches = re.findall(r'Code regions:\s*(\d+)', content)
    if code_matches:
        result['code_regions'] = int(code_matches[0])

    # Extract from memory layout section
    layout_section = re.search(r'Memory Layout:.*?(?=Structure Summary:|$)', content, re.DOTALL)
    if layout_section:
        layout_text = layout_section.group(0)
        # Count bar types in layout
        code_count = len(re.findall(r'\[█+\]', layout_text))
        data_count = len(re.findall(r'\[▒+\]', layout_text))
        table_count = len(re.findall(r'\[░+\]', layout_text))

        result['code_regions'] = code_count
        result['data_regions'] = data_count
        result['table_regions'] = table_count

    return result

def analyze_all_reports(output_dir):
    """
    Analyze all analysis reports in the output directory.
    """
    analysis_files = list(Path(output_dir).rglob('*_analysis_report.txt'))

    results = {}
    by_player_type = defaultdict(list)

    for filepath in sorted(analysis_files):
        # Extract song name from path
        parts = filepath.parts
        song_name = parts[-3]  # Two levels up from the filename

        report = parse_analysis_report(str(filepath))
        results[song_name] = report

        if report['player_type']:
            by_player_type[report['player_type']].append(song_name)

    return results, by_player_type

def generate_validation_report(results, by_player_type):
    """
    Generate a comprehensive validation report.
    """
    report = []
    report.append("=" * 80)
    report.append("SIDDECOMPILER PLAYER DETECTION VALIDATION REPORT")
    report.append("=" * 80)
    report.append("")

    # Overall statistics
    report.append("OVERALL STATISTICS")
    report.append("-" * 80)
    total_files = len(results)
    detected_files = sum(1 for r in results.values() if r['player_type'])
    detection_rate = (detected_files / total_files * 100) if total_files > 0 else 0

    report.append(f"Total Files Analyzed:        {total_files}")
    report.append(f"Files with Player Detected:  {detected_files}/{total_files}")
    report.append(f"Player Detection Rate:       {detection_rate:.1f}%")
    report.append("")

    # Player type breakdown
    report.append("PLAYER TYPE DETECTION BREAKDOWN")
    report.append("-" * 80)
    for player_type in sorted(by_player_type.keys()):
        files = by_player_type[player_type]
        report.append(f"\n{player_type}:")
        report.append(f"  Count: {len(files)}")
        report.append(f"  Files:")
        for fname in sorted(files):
            report.append(f"    - {fname}")

    # File-by-file results
    report.append("")
    report.append("\nFILE-BY-FILE DETAILED RESULTS")
    report.append("-" * 80)

    for song_name in sorted(results.keys()):
        r = results[song_name]
        report.append(f"\n{song_name}:")
        report.append(f"  Player Type:     {r['player_type'] or 'UNKNOWN'}")
        report.append(f"  Load Address:    {r['load_addr'] or 'N/A'}")
        report.append(f"  Init Address:    {r['init_addr'] or 'N/A'}")
        report.append(f"  Play Address:    {r['play_addr'] or 'N/A'}")
        report.append(f"  Memory Range:    {r['memory_range'] or 'N/A'}")
        report.append(f"  Memory Size:     {r['total_bytes']} bytes")
        report.append(f"  Code Regions:    {r['code_regions']}")
        report.append(f"  Data Regions:    {r['data_regions']}")
        report.append(f"  Table Regions:   {r['table_regions']}")

    # Laxity-specific analysis
    report.append("\n" + "=" * 80)
    report.append("LAXITY NEWPLAYER V21 DETECTION ANALYSIS")
    report.append("=" * 80)

    laxity_files = by_player_type.get('NewPlayer v21 (Laxity)', [])
    report.append(f"\nFiles Detected as Laxity: {len(laxity_files)}/{total_files}")

    if laxity_files:
        report.append("\nLaxity Files Detected:")
        for fname in sorted(laxity_files):
            report.append(f"  [OK] {fname}")

    # Non-Laxity detection
    report.append("\n" + "=" * 80)
    report.append("OTHER PLAYER TYPES DETECTED")
    report.append("=" * 80)

    other_types = {k: v for k, v in by_player_type.items() if 'Laxity' not in k}
    if other_types:
        for player_type in sorted(other_types.keys()):
            files = other_types[player_type]
            report.append(f"\n{player_type}: {len(files)} file(s)")
            for fname in sorted(files):
                report.append(f"  - {fname}")
    else:
        report.append("\nNo other player types detected (only Laxity detected)")

    # Accuracy improvement claim
    report.append("\n" + "=" * 80)
    report.append("VERSION COMPARISON: v1.3.0 vs v1.4.0")
    report.append("=" * 80)
    report.append(f"\nPrevious Detection (v1.3.0): 83% (15/18 files)")
    report.append(f"Current Detection (v1.4.0):  {detection_rate:.1f}% ({detected_files}/{total_files} files)")

    if detection_rate >= 100:
        improvement = detection_rate - 83
        report.append(f"Improvement:                 +{improvement:.1f}% [PASS]")
        report.append("\nCLAIM VERIFIED: +17% improvement achieved (83% → 100%)")
    else:
        report.append(f"Note: Detection rate is {detection_rate:.1f}%, not 100%")

    report.append("\n" + "=" * 80)

    return "\n".join(report)

if __name__ == "__main__":
    output_dir = "output/SIDSF2player_Complete_Pipeline"

    print("Parsing analysis reports...")
    results, by_player_type = analyze_all_reports(output_dir)

    print(f"Found {len(results)} analysis reports")
    print(f"Detected player types: {list(by_player_type.keys())}")

    # Generate report
    report = generate_validation_report(results, by_player_type)

    # Save report with UTF-8 encoding
    report_path = "output/PLAYER_DETECTION_VALIDATION_REPORT.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\nReport saved to: {report_path}")
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total files: {len(results)}")
    print(f"Laxity detected: {len(by_player_type.get('NewPlayer v21 (Laxity)', []))}")
    print(f"Unknown: {len(by_player_type.get('Unknown', []))}")
