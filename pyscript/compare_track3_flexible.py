#!/usr/bin/env python3
"""
Flexible Track 3 Comparison Tool

Compares Track 3 extracted from SF2 files with user's reference format.
Handles various reference formats and generates detailed side-by-side comparison.

Usage:
    python compare_track3_flexible.py <sf2_file> <reference_file> [--html output.html]
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Tuple
import argparse

sys.path.insert(0, str(Path(__file__).parent))
from sf2_viewer_core import SF2Parser


class FlexibleReferenceParser:
    """Parse user's Track 3 reference file in various formats"""

    def __init__(self, ref_file: str):
        self.ref_file = ref_file
        self.entries = []
        self.header_info = {}
        self._parse()

    def _parse(self):
        """Parse reference file flexibly"""
        with open(self.ref_file, 'r') as f:
            lines = f.readlines()

        step = 0
        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Skip empty lines
            if not line_stripped:
                continue

            # Check if it's a header line
            if line_stripped.lower().startswith('track'):
                self.header_info['track'] = line_stripped
                continue

            # Parse data lines
            # Format can be:
            # 1. "a00a 0b -- F-3" (header with address)
            # 2. "     -- -- +++" (continuation)
            # 3. "0000  01 -- C-3" (step + data)

            parts = line_stripped.split()
            if not parts:
                continue

            # Try to identify format
            if len(parts) >= 3:
                # Check if first part is address/step marker (hex)
                first_part = parts[0]

                # Format: "a00a 0b -- F-3" or "0000 01 -- C-3"
                if len(first_part) == 4 and all(c in '0123456789abcdefABCDEF' for c in first_part):
                    # This is a step/address marker
                    if len(parts) >= 4:
                        # parts = ['a00a', '0b', '--', 'F-3']
                        # or parts = ['0000', '01', '--', 'C-3']
                        instr = parts[1]
                        cmd = parts[2]
                        note = parts[3] if len(parts) > 3 else '---'
                    else:
                        # Only 3 parts, treat as: addr instr note or instr cmd note
                        instr = parts[1]
                        cmd = '--'
                        note = parts[2] if len(parts) > 2 else '---'

                    self.entries.append({
                        'step': step,
                        'step_hex': f'{step:04X}',
                        'instrument': instr,
                        'command': cmd,
                        'note': note,
                        'raw_line': line.strip()
                    })
                    step += 1

                # Format: "-- -- +++" (no step marker, continuation)
                elif len(parts) == 3 or len(parts) == 4:
                    # parts = ['--', '--', '+++']
                    # or parts = ['01', '--', 'C-3']
                    # or parts = ['--', '02', '+++']
                    instr = parts[0]
                    cmd = parts[1]
                    note = parts[2] if len(parts) > 2 else '---'

                    self.entries.append({
                        'step': step,
                        'step_hex': f'{step:04X}',
                        'instrument': instr,
                        'command': cmd,
                        'note': note,
                        'raw_line': line.strip()
                    })
                    step += 1


class Track3Comparator:
    """Compare extracted Track 3 with reference"""

    def __init__(self, sf2_file: str, ref_file: str, sequence_idx: int = 0):
        self.sf2_file = sf2_file
        self.ref_file = ref_file
        self.sequence_idx = sequence_idx

        # Parse SF2 and extract Track 3
        self.parser = SF2Parser(sf2_file)
        self.extracted = self._extract_track3()

        # Parse reference
        self.reference = FlexibleReferenceParser(ref_file)

    def _extract_track3(self) -> List[Dict]:
        """Extract Track 3 from SF2 sequence"""
        if self.sequence_idx not in self.parser.sequences:
            raise ValueError(f"Sequence {self.sequence_idx} not found")

        seq = self.parser.sequences[self.sequence_idx]
        track3 = []

        # Check sequence format (single-track or 3-track interleaved)
        seq_format = self.parser.sequence_formats.get(self.sequence_idx, 'interleaved')

        if seq_format == 'single':
            # Single-track format: use all entries as Track 3
            entries_to_process = enumerate(seq)
        else:
            # 3-track interleaved format: use every 3rd entry starting at index 2
            entries_to_process = ((i, seq[i]) for i in range(2, len(seq), 3))

        step = 0
        for i, entry in entries_to_process:

            # Format instrument display
            if entry.instrument == 0x80:
                instr_str = '--'
            elif entry.instrument >= 0xA0:
                instr_str = f'{entry.instrument & 0x1F:02X}'
            else:
                instr_str = f'{entry.instrument:02X}'

            # Format command display
            if entry.command == 0x80:
                cmd_str = '--'
            elif entry.command >= 0xC0:
                cmd_str = f'{entry.command & 0x3F:02X}'
            else:
                cmd_str = f'{entry.command:02X}'

            # Format note
            note_str = entry.note_name().strip()

            track3.append({
                'step': step,
                'step_hex': f'{step:04X}',
                'instrument': instr_str,
                'instrument_raw': entry.instrument,
                'command': cmd_str,
                'command_raw': entry.command,
                'note': note_str,
                'note_raw': entry.note
            })
            step += 1

        return track3

    def compare(self) -> Tuple[int, int, List[Dict]]:
        """Compare extracted vs reference.

        Returns: (matches, total, differences)
        """
        matches = 0
        total = max(len(self.extracted), len(self.reference.entries))
        differences = []

        for i in range(total):
            ext = self.extracted[i] if i < len(self.extracted) else None
            ref = self.reference.entries[i] if i < len(self.reference.entries) else None

            if ext and ref:
                # Compare fields (normalize)
                ext_i = ext['instrument'].lower().strip()
                ext_c = ext['command'].lower().strip()
                ext_n = ext['note'].lower().strip()

                ref_i = ref['instrument'].lower().strip()
                ref_c = ref['command'].lower().strip()
                ref_n = ref['note'].lower().strip()

                # Check match
                if ext_i == ref_i and ext_c == ref_c and ext_n == ref_n:
                    matches += 1
                else:
                    differences.append({
                        'step': i,
                        'extracted': ext,
                        'reference': ref,
                        'type': 'mismatch',
                        'diff_fields': {
                            'instrument': ext_i != ref_i,
                            'command': ext_c != ref_c,
                            'note': ext_n != ref_n
                        }
                    })
            elif ext:
                differences.append({
                    'step': i,
                    'extracted': ext,
                    'reference': None,
                    'type': 'extra'
                })
            elif ref:
                differences.append({
                    'step': i,
                    'extracted': None,
                    'reference': ref,
                    'type': 'missing'
                })

        return matches, total, differences

    def generate_text_report(self) -> str:
        """Generate detailed text comparison report"""
        lines = []
        lines.append("=" * 100)
        lines.append("TRACK 3 COMPARISON REPORT")
        lines.append("=" * 100)
        lines.append("")

        lines.append(f"SF2 File:     {self.sf2_file}")
        lines.append(f"Reference:    {self.ref_file}")
        lines.append(f"Sequence:     {self.sequence_idx}")
        lines.append("")

        matches, total, diffs = self.compare()

        lines.append(f"Total Steps:  {total}")
        lines.append(f"Matches:      {matches} ({100*matches/total:.1f}%)")
        lines.append(f"Differences:  {len(diffs)} ({100*len(diffs)/total:.1f}%)")
        lines.append("")

        if matches == total:
            lines.append("PERFECT MATCH - Track 3 data is identical!")
            return "\n".join(lines)

        # Show side-by-side comparison
        lines.append("SIDE-BY-SIDE COMPARISON:")
        lines.append("-" * 100)
        lines.append("")
        lines.append("Step  | EXTRACTED (SF2)      | REFERENCE (Expected) | Status")
        lines.append("      | In  Cmd  Note        | In  Cmd  Note        |")
        lines.append("------|----------------------|----------------------|--------")

        for i in range(total):
            ext = self.extracted[i] if i < len(self.extracted) else None
            ref = self.reference.entries[i] if i < len(self.reference.entries) else None

            step_str = f"{i:04X}"

            if ext:
                ext_str = f"{ext['instrument']:3s} {ext['command']:3s} {ext['note']:6s}"
            else:
                ext_str = "---  --- ------"

            if ref:
                ref_str = f"{ref['instrument']:3s} {ref['command']:3s} {ref['note']:6s}"
            else:
                ref_str = "---  --- ------"

            # Status
            if ext and ref:
                if (ext['instrument'].lower() == ref['instrument'].lower() and
                    ext['command'].lower() == ref['command'].lower() and
                    ext['note'].lower() == ref['note'].lower()):
                    status = "OK"
                else:
                    status = "DIFF"
            elif ext:
                status = "EXTRA"
            else:
                status = "MISS"

            lines.append(f"{step_str}  | {ext_str:20s} | {ref_str:20s} | {status}")

        # Show detailed differences
        if diffs:
            lines.append("")
            lines.append("")
            lines.append("DETAILED DIFFERENCES:")
            lines.append("-" * 100)
            lines.append("")

            for diff in diffs[:20]:  # Limit to first 20
                step = diff['step']
                dtype = diff['type']

                if dtype == 'mismatch':
                    lines.append(f"Step {step:04X}: MISMATCH")
                    ext = diff['extracted']
                    ref = diff['reference']

                    lines.append(f"  Extracted: Inst={ext['instrument']:3s} ({ext['instrument_raw']:02X}), Cmd={ext['command']:3s} ({ext['command_raw']:02X}), Note={ext['note']:6s} ({ext['note_raw']:02X})")
                    lines.append(f"  Reference: Inst={ref['instrument']:3s}, Cmd={ref['command']:3s}, Note={ref['note']:6s}")
                    lines.append(f"  Raw line:  {ref['raw_line']}")

                    # Show which fields differ
                    diff_fields = diff['diff_fields']
                    if diff_fields['instrument']:
                        lines.append(f"    > Instrument: {ext['instrument']} != {ref['instrument']}")
                    if diff_fields['command']:
                        lines.append(f"    > Command: {ext['command']} != {ref['command']}")
                    if diff_fields['note']:
                        lines.append(f"    > Note: {ext['note']} != {ref['note']}")
                    lines.append("")

                elif dtype == 'extra':
                    ext = diff['extracted']
                    lines.append(f"Step {step:04X}: EXTRA in extracted")
                    lines.append(f"  Extracted: {ext['instrument']:3s} {ext['command']:3s} {ext['note']:6s}")
                    lines.append("")

                elif dtype == 'missing':
                    ref = diff['reference']
                    lines.append(f"Step {step:04X}: MISSING from extracted")
                    lines.append(f"  Reference: {ref['instrument']:3s} {ref['command']:3s} {ref['note']:6s}")
                    lines.append(f"  Raw line:  {ref['raw_line']}")
                    lines.append("")

            if len(diffs) > 20:
                lines.append(f"... and {len(diffs) - 20} more differences")

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Flexible Track 3 Comparison")
    parser.add_argument("sf2_file", help="Path to SF2 file")
    parser.add_argument("reference_file", help="Path to reference Track 3 file")
    parser.add_argument("--sequence", "-s", type=int, default=0, help="Sequence index (default: 0)")
    parser.add_argument("--html", help="Generate HTML report to this file")

    args = parser.parse_args()

    if not os.path.exists(args.sf2_file):
        print(f"Error: SF2 file not found: {args.sf2_file}", file=sys.stderr)
        return 1

    if not os.path.exists(args.reference_file):
        print(f"Error: Reference file not found: {args.reference_file}", file=sys.stderr)
        return 1

    try:
        comparator = Track3Comparator(args.sf2_file, args.reference_file, args.sequence)
        print(comparator.generate_text_report())

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
