#!/usr/bin/env python3
"""
Generate validation warnings report for all SID conversions.

Scans the SID directory and generates validation warnings for each file,
then creates an HTML summary showing patterns across all files.

Usage:
    python generate_validation_report.py [sid_dir] [output_file]
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict, Counter

# Import our converter modules
from sidm2.sid_parser import SIDParser
from sidm2.laxity_analyzer import LaxityPlayerAnalyzer


def convert_and_validate(sid_file: Path) -> Dict:
    """Run conversion on a SID file and extract validation warnings.

    Args:
        sid_file: Path to SID file

    Returns:
        Dict with song info, warnings, and confidence data
    """
    try:
        # Parse SID file
        parser = SIDParser(str(sid_file))
        header = parser.parse_header()
        c64_data, load_addr = parser.get_c64_data(header)

        # Extract music data
        analyzer = LaxityPlayerAnalyzer(c64_data, load_addr, header)
        extracted = analyzer.extract_music_data()

        # Get confidence score if available
        overall_score = None
        component_scores = {}
        if hasattr(extracted, 'confidence') and extracted.confidence:
            overall_score = extracted.confidence.get('overall', 0)
            component_scores = {k: v for k, v in extracted.confidence.items() if k != 'overall'}

        return {
            'name': getattr(header, 'name', sid_file.stem),
            'author': getattr(header, 'author', 'Unknown'),
            'warnings': extracted.validation_errors if hasattr(extracted, 'validation_errors') else [],
            'confidence': overall_score,
            'component_scores': component_scores,
            'sequences': len(extracted.sequences) if hasattr(extracted, 'sequences') else 0,
            'instruments': len(extracted.instruments) if hasattr(extracted, 'instruments') else 0,
            'orderlists': len(extracted.orderlists) if hasattr(extracted, 'orderlists') else 0,
        }
    except Exception as e:
        return {
            'name': sid_file.stem,
            'author': 'Unknown',
            'warnings': [f'Conversion failed: {str(e)}'],
            'confidence': 0,
            'component_scores': {},
            'sequences': 0,
            'instruments': 0,
            'orderlists': 0,
            'error': str(e)
        }


def categorize_warning(warning: str) -> str:
    """Categorize a warning message.

    Args:
        warning: Warning message string

    Returns:
        Category name
    """
    warning_lower = warning.lower()

    if 'instrument' in warning_lower and 'exceeds' in warning_lower:
        return 'Instrument Pointer Bounds'
    elif 'instrument' in warning_lower and 'too short' in warning_lower:
        return 'Instrument Size'
    elif 'sequence' in warning_lower and 'empty' in warning_lower:
        return 'Empty Sequence'
    elif 'sequence' in warning_lower and 'too long' in warning_lower:
        return 'Sequence Length'
    elif 'note' in warning_lower and 'out of range' in warning_lower:
        return 'Note Range'
    elif 'orderlist' in warning_lower:
        return 'Orderlist'
    elif 'tempo' in warning_lower:
        return 'Tempo'
    else:
        return 'Other'


def scan_sid_directory(sid_dir: Path) -> List[Dict]:
    """Scan SID directory and validate all files.

    Args:
        sid_dir: Directory containing SID files

    Returns:
        List of validation results for each file
    """
    results = []

    if not sid_dir.exists():
        print(f"Error: SID directory not found: {sid_dir}")
        return results

    # Find all .sid files
    sid_files = sorted(sid_dir.glob('*.sid'))

    total = len(sid_files)
    for i, sid_file in enumerate(sid_files, 1):
        print(f"[{i}/{total}] Validating {sid_file.name}...")
        result = convert_and_validate(sid_file)
        result['filename'] = sid_file.name
        results.append(result)

    return results


def analyze_patterns(results: List[Dict]) -> Dict:
    """Analyze warning patterns across all files.

    Args:
        results: List of validation results

    Returns:
        Dict with pattern analysis
    """
    # Count warnings by category
    category_counts = Counter()
    warning_counts = Counter()
    files_with_warnings = set()

    for result in results:
        if result['warnings']:
            files_with_warnings.add(result['filename'])

        for warning in result['warnings']:
            category = categorize_warning(warning)
            category_counts[category] += 1
            warning_counts[warning] += 1

    # Calculate statistics
    total_files = len(results)
    total_warnings = sum(category_counts.values())
    files_clean = total_files - len(files_with_warnings)

    # Find files with most warnings
    file_warning_counts = [(r['filename'], len(r['warnings'])) for r in results]
    file_warning_counts.sort(key=lambda x: x[1], reverse=True)

    return {
        'total_files': total_files,
        'total_warnings': total_warnings,
        'files_clean': files_clean,
        'files_with_warnings': len(files_with_warnings),
        'category_counts': dict(category_counts),
        'warning_counts': dict(warning_counts),
        'top_files': file_warning_counts[:10],
        'avg_warnings_per_file': total_warnings / total_files if total_files > 0 else 0,
    }


def generate_html_report(results: List[Dict], patterns: Dict, output_file: Path):
    """Generate HTML validation report.

    Args:
        results: List of validation results
        patterns: Pattern analysis data
        output_file: Output HTML file path
    """
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SID to SF2 Validation Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .subtitle {{
            margin-top: 10px;
            opacity: 0.9;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        .section {{
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h2 {{
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th {{
            background-color: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #eee;
        }}
        tr:hover {{
            background-color: #f8f9ff;
        }}
        .warning-count {{
            background-color: #ff6b6b;
            color: white;
            padding: 4px 8px;
            border-radius: 12px;
            font-weight: bold;
            font-size: 0.9em;
        }}
        .warning-count.zero {{
            background-color: #51cf66;
        }}
        .category-bar {{
            display: flex;
            align-items: center;
            margin: 10px 0;
        }}
        .category-label {{
            width: 200px;
            font-weight: 500;
        }}
        .category-progress {{
            flex: 1;
            background-color: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 0 10px;
        }}
        .category-fill {{
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            height: 24px;
            display: flex;
            align-items: center;
            padding-left: 10px;
            color: white;
            font-weight: bold;
            font-size: 0.9em;
        }}
        .warning-text {{
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #d63031;
            background-color: #fff5f5;
            padding: 8px;
            border-left: 3px solid #ff6b6b;
            margin: 4px 0;
        }}
        .recommendation {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        .recommendation h3 {{
            margin-top: 0;
            color: #856404;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>SID to SF2 Validation Report</h1>
        <div class="subtitle">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    </div>

    <div class="summary">
        <div class="stat-card">
            <div class="stat-number">{patterns['total_files']}</div>
            <div class="stat-label">Total Files</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{patterns['total_warnings']}</div>
            <div class="stat-label">Total Warnings</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{patterns['files_clean']}</div>
            <div class="stat-label">Clean Files (0 warnings)</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{patterns['avg_warnings_per_file']:.1f}</div>
            <div class="stat-label">Avg Warnings per File</div>
        </div>
    </div>

    <div class="section">
        <h2>Warning Categories</h2>
        <p>Distribution of warnings by category across all files:</p>
"""

    # Add category breakdown
    max_count = max(patterns['category_counts'].values()) if patterns['category_counts'] else 1
    for category, count in sorted(patterns['category_counts'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / max_count) * 100
        html += f"""
        <div class="category-bar">
            <div class="category-label">{category}</div>
            <div class="category-progress">
                <div class="category-fill" style="width: {percentage}%">{count}</div>
            </div>
        </div>
"""

    html += """
    </div>

    <div class="section">
        <h2>Per-File Validation Results</h2>
        <p>Detailed validation results for each SID file:</p>
        <table>
            <thead>
                <tr>
                    <th>Filename</th>
                    <th>Song Name</th>
                    <th>Author</th>
                    <th style="text-align: center;">Warnings</th>
                    <th>Issues</th>
                </tr>
            </thead>
            <tbody>
"""

    # Add per-file results
    for result in sorted(results, key=lambda x: len(x['warnings']), reverse=True):
        warning_count = len(result['warnings'])
        count_class = 'zero' if warning_count == 0 else ''

        warnings_html = ''
        if result['warnings']:
            for warning in result['warnings']:
                warnings_html += f'<div class="warning-text">{warning}</div>'
        else:
            warnings_html = '<em style="color: #51cf66;">No warnings</em>'

        html += f"""
                <tr>
                    <td><strong>{result['filename']}</strong></td>
                    <td>{result['name']}</td>
                    <td>{result['author']}</td>
                    <td style="text-align: center;"><span class="warning-count {count_class}">{warning_count}</span></td>
                    <td>{warnings_html}</td>
                </tr>
"""

    html += """
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>Most Common Warnings</h2>
        <p>Top 10 most frequently occurring warnings:</p>
        <table>
            <thead>
                <tr>
                    <th>Count</th>
                    <th>Warning Message</th>
                </tr>
            </thead>
            <tbody>
"""

    # Add top warnings
    for warning, count in sorted(patterns['warning_counts'].items(), key=lambda x: x[1], reverse=True)[:10]:
        html += f"""
                <tr>
                    <td><span class="warning-count">{count}</span></td>
                    <td class="warning-text">{warning}</td>
                </tr>
"""

    html += """
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>Analysis & Recommendations</h2>
"""

    # Add recommendations based on patterns
    if patterns['total_warnings'] == 0:
        html += """
        <div class="recommendation">
            <h3>All Clear!</h3>
            <p>No validation warnings found across any files. The converter is working excellently!</p>
        </div>
"""
    else:
        # Check for instrument pointer bounds issues
        if 'Instrument Pointer Bounds' in patterns['category_counts']:
            count = patterns['category_counts']['Instrument Pointer Bounds']
            html += f"""
        <div class="recommendation">
            <h3>Instrument Pointer Bounds ({count} warnings)</h3>
            <p>The most common issue is instrument pointers exceeding table sizes. This is likely due to:</p>
            <ul>
                <li>Laxity's Y*4 indexing scheme for pulse/filter tables</li>
                <li>Validation logic using >= instead of > for boundary checks</li>
                <li>Edge cases where pointers equal table size (valid in some contexts)</li>
            </ul>
            <p><strong>Recommendation:</strong> Adjust validation bounds checking in laxity_analyzer.py to account for
            Laxity's indexing scheme. Consider using <code>&gt;</code> instead of <code>&gt;=</code> for boundary checks.</p>
        </div>
"""

        # Check if warnings are concentrated in few files
        files_with_many_warnings = [f for f, c in patterns['top_files'] if c >= 5]
        if len(files_with_many_warnings) <= 3 and patterns['files_with_warnings'] > 3:
            html += f"""
        <div class="recommendation">
            <h3>Warnings Concentrated in Few Files</h3>
            <p>Most warnings are concentrated in {len(files_with_many_warnings)} file(s):
            {', '.join(files_with_many_warnings)}. This suggests the issues may be file-specific rather than systematic.</p>
            <p><strong>Recommendation:</strong> Investigate these specific files to understand if they have unusual
            characteristics that trigger warnings.</p>
        </div>
"""
        else:
            html += """
        <div class="recommendation">
            <h3>Warnings Are Systematic</h3>
            <p>Warnings appear across multiple files, suggesting systematic extraction or validation issues.</p>
            <p><strong>Recommendation:</strong> Focus on fixing the most common warning categories to have the
            greatest impact across all conversions.</p>
        </div>
"""

    html += """
    </div>

</body>
</html>
"""

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\nValidation report generated: {output_file}")


def main():
    """Main entry point."""
    # Parse arguments
    sid_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('SID')
    output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('output/validation_report.html')

    print("=" * 60)
    print("SID to SF2 Validation Report Generator")
    print("=" * 60)
    print(f"SID directory: {sid_dir}")
    print(f"Output file: {output_file}")
    print()

    # Scan SID directory
    print("Scanning SID directory and validating files...")
    results = scan_sid_directory(sid_dir)

    if not results:
        print("No SID files found!")
        return 1

    print(f"\nProcessed {len(results)} files")

    # Analyze patterns
    print("Analyzing warning patterns...")
    patterns = analyze_patterns(results)

    # Generate report
    print("Generating HTML report...")
    generate_html_report(results, patterns, output_file)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total files:           {patterns['total_files']}")
    print(f"Total warnings:        {patterns['total_warnings']}")
    print(f"Files with warnings:   {patterns['files_with_warnings']}")
    print(f"Clean files:           {patterns['files_clean']}")
    print(f"Avg warnings/file:     {patterns['avg_warnings_per_file']:.1f}")
    print()

    if patterns['category_counts']:
        print("Warning breakdown by category:")
        for category, count in sorted(patterns['category_counts'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {category:30s} {count:3d}")

    print("\n" + "=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
