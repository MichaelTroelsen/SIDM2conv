#!/usr/bin/env python3
"""
Track 3 Comparison Test Tool

Compares Track 3 data extracted from SF2 files with expected reference data.
Generates side-by-side comparison reports showing differences.

Usage:
    # Compare SF2 Track 3 with reference file
    python test_track3_comparison.py path/to/file.sf2 track_3.txt --sequence 0

    # Extract Track 3 from SF2 to create reference file
    python test_track3_comparison.py path/to/file.sf2 --extract --sequence 0 > track_3_reference.txt

    # Compare and generate HTML report
    python test_track3_comparison.py path/to/file.sf2 track_3.txt --html comparison.html
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import argparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from sf2_viewer_core import SF2Parser, SequenceEntry


class Track3Extractor:
    """Extract Track 3 data from SF2 files"""

    def __init__(self, sf2_file: str):
        self.sf2_file = sf2_file
        self.parser = SF2Parser(sf2_file)

    def extract_track3(self, sequence_idx: int = 0) -> List[Dict[str, str]]:
        """Extract Track 3 data from a sequence.

        Returns list of dicts with keys: step, instrument, command, note
        """
        if not self.parser.sequences:
            raise ValueError(f"No sequences found in {self.sf2_file}")

        if sequence_idx not in self.parser.sequences:
            raise ValueError(f"Sequence {sequence_idx} not found (available: {list(self.parser.sequences.keys())})")

        seq_data = self.parser.sequences[sequence_idx]
        track3_data = []

        # Extract every 3rd entry starting from index 2 (Track 3)
        # Entry 0, 1, 2 = Track 1, 2, 3 at Step 0
        # Entry 3, 4, 5 = Track 1, 2, 3 at Step 1, etc.
        step = 0
        for i in range(2, len(seq_data), 3):  # Start at index 2, increment by 3
            entry = seq_data[i]

            track3_data.append({
                'step': f"{step:04X}",
                'instrument': entry.instrument_display(),
                'command': entry.command_display(),
                'note': entry.note_name()
            })
            step += 1

        return track3_data

    def format_track3(self, track3_data: List[Dict[str, str]]) -> str:
        """Format Track 3 data as text matching SF2 viewer format"""
        lines = []
        lines.append("Step  In Cmd Note")
        lines.append("----  -- --- ----")

        for entry in track3_data:
            step = entry['step']
            instr = entry['instrument']
            cmd = entry['command']
            note = entry['note'][:4]  # Limit to 4 chars

            lines.append(f"{step}  {instr:2s} {cmd:>2s} {note:4s}")

        return "\n".join(lines)


class Track3Reference:
    """Load and parse Track 3 reference data from text file"""

    def __init__(self, reference_file: str):
        self.reference_file = reference_file
        self.data = []
        self._load()

    def _load(self):
        """Load reference file and parse Track 3 data"""
        with open(self.reference_file, 'r') as f:
            lines = f.readlines()

        # Skip header lines (first 2 lines)
        for line in lines[2:]:
            line = line.strip()
            if not line:
                continue

            # Parse line format: "STEP  In Cmd Note"
            # Example: "0000  01 -- C-3 "
            if len(line) < 17:
                continue  # Skip malformed lines

            try:
                step = line[0:4]
                instr = line[6:8]
                cmd = line[9:11]
                note = line[12:16]

                self.data.append({
                    'step': step,
                    'instrument': instr.strip(),
                    'command': cmd.strip(),
                    'note': note.strip()
                })
            except (ValueError, IndexError) as e:
                print(f"Warning: Could not parse line: {line} ({e})", file=sys.stderr)
                continue


class Track3Comparator:
    """Compare Track 3 extracted data with reference data"""

    def __init__(self, extracted: List[Dict], reference: List[Dict]):
        self.extracted = extracted
        self.reference = reference
        self.differences = []

    def compare(self) -> Tuple[int, int, List[Dict]]:
        """Compare extracted vs reference data.

        Returns: (matched_count, total_count, differences_list)
        """
        matched = 0
        total = max(len(self.extracted), len(self.reference))
        self.differences = []

        for i in range(total):
            # Get entries (may be None if one list is shorter)
            extracted_entry = self.extracted[i] if i < len(self.extracted) else None
            reference_entry = self.reference[i] if i < len(self.reference) else None

            # Compare entries
            if extracted_entry and reference_entry:
                # Both exist, compare fields
                fields_match = (
                    extracted_entry['instrument'] == reference_entry['instrument'] and
                    extracted_entry['command'] == reference_entry['command'] and
                    extracted_entry['note'] == reference_entry['note']
                )

                if fields_match:
                    matched += 1
                else:
                    self.differences.append({
                        'step': extracted_entry['step'],
                        'extracted': extracted_entry,
                        'reference': reference_entry,
                        'type': 'mismatch'
                    })
            elif extracted_entry and not reference_entry:
                # Extra entry in extracted data
                self.differences.append({
                    'step': extracted_entry['step'],
                    'extracted': extracted_entry,
                    'reference': None,
                    'type': 'extra'
                })
            elif reference_entry and not extracted_entry:
                # Missing entry in extracted data
                self.differences.append({
                    'step': reference_entry['step'],
                    'extracted': None,
                    'reference': reference_entry,
                    'type': 'missing'
                })

        return matched, total, self.differences

    def generate_text_report(self) -> str:
        """Generate text comparison report"""
        lines = []
        lines.append("=" * 80)
        lines.append("TRACK 3 COMPARISON REPORT")
        lines.append("=" * 80)
        lines.append("")

        matched, total, diffs = self.compare()

        # Summary
        lines.append(f"Total steps:     {total}")
        lines.append(f"Matched:         {matched} ({100*matched/total:.1f}%)")
        lines.append(f"Differences:     {len(diffs)} ({100*len(diffs)/total:.1f}%)")
        lines.append("")

        if not diffs:
            lines.append("✓ Perfect match! Track 3 data is identical.")
            return "\n".join(lines)

        # Differences detail
        lines.append("DIFFERENCES:")
        lines.append("-" * 80)
        lines.append("")

        for diff in diffs:
            step = diff['step']
            dtype = diff['type']

            if dtype == 'mismatch':
                lines.append(f"Step {step}: MISMATCH")
                ext = diff['extracted']
                ref = diff['reference']
                lines.append(f"  Extracted: {ext['instrument']:2s} {ext['command']:>2s} {ext['note']:4s}")
                lines.append(f"  Reference: {ref['instrument']:2s} {ref['command']:>2s} {ref['note']:4s}")

                # Show field-level differences
                if ext['instrument'] != ref['instrument']:
                    lines.append(f"    • Instrument: {ext['instrument']} ≠ {ref['instrument']}")
                if ext['command'] != ref['command']:
                    lines.append(f"    • Command: {ext['command']} ≠ {ref['command']}")
                if ext['note'] != ref['note']:
                    lines.append(f"    • Note: {ext['note']} ≠ {ref['note']}")
                lines.append("")

            elif dtype == 'extra':
                ext = diff['extracted']
                lines.append(f"Step {step}: EXTRA (in extracted, not in reference)")
                lines.append(f"  Extracted: {ext['instrument']:2s} {ext['command']:>2s} {ext['note']:4s}")
                lines.append("")

            elif dtype == 'missing':
                ref = diff['reference']
                lines.append(f"Step {step}: MISSING (in reference, not in extracted)")
                lines.append(f"  Reference: {ref['instrument']:2s} {ref['command']:>2s} {ref['note']:4s}")
                lines.append("")

        return "\n".join(lines)

    def generate_side_by_side_report(self) -> str:
        """Generate side-by-side comparison with differences highlighted"""
        lines = []
        lines.append("=" * 80)
        lines.append("TRACK 3 SIDE-BY-SIDE COMPARISON")
        lines.append("=" * 80)
        lines.append("")

        # Header
        lines.append("Step  EXTRACTED          REFERENCE          STATUS")
        lines.append("      In Cmd Note        In Cmd Note")
        lines.append("----  -- --- ----        -- --- ----        ------")

        # Data rows
        total = max(len(self.extracted), len(self.reference))
        for i in range(total):
            extracted_entry = self.extracted[i] if i < len(self.extracted) else None
            reference_entry = self.reference[i] if i < len(self.reference) else None

            # Format extracted side
            if extracted_entry:
                step = extracted_entry['step']
                ext_str = f"{extracted_entry['instrument']:2s} {extracted_entry['command']:>2s} {extracted_entry['note']:4s}"
            else:
                step = reference_entry['step'] if reference_entry else f"{i:04X}"
                ext_str = "-- --- ----"

            # Format reference side
            if reference_entry:
                ref_str = f"{reference_entry['instrument']:2s} {reference_entry['command']:>2s} {reference_entry['note']:4s}"
            else:
                ref_str = "-- --- ----"

            # Determine status
            if extracted_entry and reference_entry:
                if (extracted_entry['instrument'] == reference_entry['instrument'] and
                    extracted_entry['command'] == reference_entry['command'] and
                    extracted_entry['note'] == reference_entry['note']):
                    status = "✓ OK"
                else:
                    status = "✗ DIFF"
            elif extracted_entry:
                status = "+ EXTRA"
            else:
                status = "- MISS"

            lines.append(f"{step}  {ext_str:15s}    {ref_str:15s}    {status}")

        return "\n".join(lines)

    def generate_html_report(self, sf2_file: str, reference_file: str) -> str:
        """Generate HTML comparison report with color coding"""
        matched, total, diffs = self.compare()

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Track 3 Comparison Report</title>
    <style>
        body {{ font-family: 'Courier New', monospace; margin: 20px; background: #1e1e1e; color: #d4d4d4; }}
        h1 {{ color: #4ec9b0; }}
        h2 {{ color: #569cd6; margin-top: 30px; }}
        .summary {{ background: #2d2d30; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .summary-stat {{ margin: 5px 0; }}
        .match-rate {{ font-size: 24px; font-weight: bold; color: #4ec9b0; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th {{ background: #2d2d30; color: #4ec9b0; padding: 10px; text-align: left; border: 1px solid #3e3e42; }}
        td {{ padding: 8px; border: 1px solid #3e3e42; }}
        tr:nth-child(even) {{ background: #252526; }}
        tr:nth-child(odd) {{ background: #1e1e1e; }}
        .match {{ background: #1e3a1e !important; }}
        .mismatch {{ background: #3a1e1e !important; }}
        .extra {{ background: #3a3a1e !important; }}
        .missing {{ background: #1e1e3a !important; }}
        .diff-field {{ color: #f48771; font-weight: bold; }}
        .status-ok {{ color: #4ec9b0; }}
        .status-diff {{ color: #f48771; }}
        .status-extra {{ color: #dcdcaa; }}
        .status-miss {{ color: #569cd6; }}
    </style>
</head>
<body>
    <h1>Track 3 Comparison Report</h1>

    <div class="summary">
        <div class="summary-stat"><strong>SF2 File:</strong> {sf2_file}</div>
        <div class="summary-stat"><strong>Reference:</strong> {reference_file}</div>
        <div class="summary-stat"><strong>Total Steps:</strong> {total}</div>
        <div class="summary-stat"><strong>Matched:</strong> {matched} ({100*matched/total:.1f}%)</div>
        <div class="summary-stat"><strong>Differences:</strong> {len(diffs)} ({100*len(diffs)/total:.1f}%)</div>
        <div class="match-rate">Match Rate: {100*matched/total:.1f}%</div>
    </div>

    <h2>Side-by-Side Comparison</h2>
    <table>
        <thead>
            <tr>
                <th>Step</th>
                <th colspan="3">Extracted (SF2 File)</th>
                <th colspan="3">Reference (Expected)</th>
                <th>Status</th>
            </tr>
            <tr>
                <th></th>
                <th>In</th>
                <th>Cmd</th>
                <th>Note</th>
                <th>In</th>
                <th>Cmd</th>
                <th>Note</th>
                <th></th>
            </tr>
        </thead>
        <tbody>
"""

        # Data rows
        total_rows = max(len(self.extracted), len(self.reference))
        for i in range(total_rows):
            extracted_entry = self.extracted[i] if i < len(self.extracted) else None
            reference_entry = self.reference[i] if i < len(self.reference) else None

            # Determine row class and status
            if extracted_entry and reference_entry:
                fields_match = (
                    extracted_entry['instrument'] == reference_entry['instrument'] and
                    extracted_entry['command'] == reference_entry['command'] and
                    extracted_entry['note'] == reference_entry['note']
                )
                row_class = "match" if fields_match else "mismatch"
                status = '<span class="status-ok">✓ OK</span>' if fields_match else '<span class="status-diff">✗ DIFF</span>'
            elif extracted_entry:
                row_class = "extra"
                status = '<span class="status-extra">+ EXTRA</span>'
            else:
                row_class = "missing"
                status = '<span class="status-miss">- MISS</span>'

            # Get step number
            step = extracted_entry['step'] if extracted_entry else (reference_entry['step'] if reference_entry else f"{i:04X}")

            # Build extracted cells
            if extracted_entry:
                ext_in = extracted_entry['instrument']
                ext_cmd = extracted_entry['command']
                ext_note = extracted_entry['note']
            else:
                ext_in = ext_cmd = ext_note = "--"

            # Build reference cells
            if reference_entry:
                ref_in = reference_entry['instrument']
                ref_cmd = reference_entry['command']
                ref_note = reference_entry['note']
            else:
                ref_in = ref_cmd = ref_note = "--"

            # Highlight differing fields
            in_class = "diff-field" if extracted_entry and reference_entry and ext_in != ref_in else ""
            cmd_class = "diff-field" if extracted_entry and reference_entry and ext_cmd != ref_cmd else ""
            note_class = "diff-field" if extracted_entry and reference_entry and ext_note != ref_note else ""

            html += f"""            <tr class="{row_class}">
                <td>{step}</td>
                <td class="{in_class}">{ext_in}</td>
                <td class="{cmd_class}">{ext_cmd}</td>
                <td class="{note_class}">{ext_note}</td>
                <td class="{in_class}">{ref_in}</td>
                <td class="{cmd_class}">{ref_cmd}</td>
                <td class="{note_class}">{ref_note}</td>
                <td>{status}</td>
            </tr>
"""

        html += """        </tbody>
    </table>
</body>
</html>"""

        return html


def main():
    parser = argparse.ArgumentParser(description="Track 3 Comparison Tool")
    parser.add_argument("sf2_file", help="Path to SF2 file")
    parser.add_argument("reference_file", nargs='?', help="Path to reference Track 3 text file")
    parser.add_argument("--sequence", "-s", type=int, default=0, help="Sequence index to extract (default: 0)")
    parser.add_argument("--extract", "-e", action="store_true", help="Extract Track 3 and output as reference format")
    parser.add_argument("--html", help="Generate HTML comparison report to this file")
    parser.add_argument("--side-by-side", "-sbs", action="store_true", help="Generate side-by-side text comparison")

    args = parser.parse_args()

    # Validate inputs
    if not os.path.exists(args.sf2_file):
        print(f"Error: SF2 file not found: {args.sf2_file}", file=sys.stderr)
        return 1

    # Extract Track 3 from SF2
    try:
        extractor = Track3Extractor(args.sf2_file)
        track3_data = extractor.extract_track3(args.sequence)
    except Exception as e:
        print(f"Error extracting Track 3: {e}", file=sys.stderr)
        return 1

    # If extract mode, just output the data
    if args.extract:
        print(extractor.format_track3(track3_data))
        return 0

    # Otherwise, we need a reference file for comparison
    if not args.reference_file:
        print("Error: Reference file required for comparison (or use --extract to generate reference)", file=sys.stderr)
        return 1

    if not os.path.exists(args.reference_file):
        print(f"Error: Reference file not found: {args.reference_file}", file=sys.stderr)
        return 1

    # Load reference data
    try:
        reference = Track3Reference(args.reference_file)
    except Exception as e:
        print(f"Error loading reference: {e}", file=sys.stderr)
        return 1

    # Compare
    comparator = Track3Comparator(track3_data, reference.data)

    # Generate HTML report if requested
    if args.html:
        html = comparator.generate_html_report(args.sf2_file, args.reference_file)
        with open(args.html, 'w') as f:
            f.write(html)
        print(f"HTML report generated: {args.html}")

    # Generate side-by-side text report if requested
    if args.side_by_side:
        print(comparator.generate_side_by_side_report())
    else:
        # Default: generate summary report
        print(comparator.generate_text_report())

    return 0


if __name__ == "__main__":
    sys.exit(main())
