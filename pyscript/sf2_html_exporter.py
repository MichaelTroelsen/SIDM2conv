#!/usr/bin/env python3
"""
SF2 HTML Exporter - Export SF2 files to interactive HTML reports

Generates professional interactive HTML analysis of SF2 files using the
HTML components library. Includes orderlists, sequences, instruments,
and tables with cross-references and search functionality.

Version: 1.0.0
Date: 2026-01-01
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyscript.html_components import (
    HTMLComponents, StatCard, NavItem, StatCardType, ColorScheme
)
from pyscript.sf2_viewer_core import SF2Parser


class SF2HTMLExporter:
    """Export SF2 files to interactive HTML reports"""

    def __init__(self, sf2_file: str):
        """
        Initialize exporter with SF2 file.

        Args:
            sf2_file: Path to SF2 file
        """
        self.sf2_file = Path(sf2_file)
        self.parser = SF2Parser(str(sf2_file))
        self.file_size = self.sf2_file.stat().st_size

    def export(self, output_html: str) -> bool:
        """
        Export SF2 to interactive HTML.

        Args:
            output_html: Output HTML file path

        Returns:
            True if successful, False otherwise
        """
        try:
            html = self._generate_html()
            Path(output_html).write_text(html, encoding='utf-8')
            print(f"[OK] SF2 HTML export successful: {output_html}")
            print(f"     File size: {self.file_size:,} bytes")
            print(f"     Sequences: {len(self.parser.sequences)}")
            return True
        except Exception as e:
            print(f"[ERROR] SF2 HTML export failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _generate_html(self) -> str:
        """Generate complete HTML document"""

        # Document header
        html = HTMLComponents.get_document_header(
            title=f"{self.sf2_file.name} - SF2 Analysis",
            include_chartjs=False
        )

        html += '<div class="container">'

        # Sidebar
        html += self._create_sidebar()

        # Main content
        html += '<div class="main-content">'
        html += self._create_header()
        html += self._create_stats_grid()
        html += self._create_search_box()
        html += self._create_file_info()
        html += self._create_orderlists_section()
        html += self._create_sequences_section()
        html += self._create_instruments_section()
        html += self._create_tables_section()
        html += HTMLComponents.create_footer("3.0.1", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        html += '</div>'  # main-content

        html += '</div>'  # container

        # Document footer
        html += HTMLComponents.get_document_footer()

        return html

    def _create_sidebar(self) -> str:
        """Create sidebar navigation"""

        # Count sequences (sequences is a dict)
        non_empty_seqs = len(self.parser.sequences) if isinstance(self.parser.sequences, dict) else 0

        # Count orderlists
        num_orderlists = len(self.parser.orderlist_unpacked) if hasattr(self.parser, 'orderlist_unpacked') else 0

        # Navigation items
        nav_items = [
            NavItem("Overview", "overview"),
            NavItem("File Info", "file-info"),
            NavItem("Orderlists", "orderlists", count=num_orderlists),
            NavItem("Sequences", "sequences", count=non_empty_seqs),
            NavItem("Instruments", "instruments", count=8),
            NavItem("Tables", "tables", count=4)
        ]

        # Sidebar stats
        stats = [
            StatCard("File Size", f"{self.file_size:,} bytes", StatCardType.INFO),
            StatCard("Sequences", str(non_empty_seqs), StatCardType.PRIMARY)
        ]

        return HTMLComponents.create_sidebar("SF2 Analysis", nav_items, stats)

    def _create_header(self) -> str:
        """Create page header"""
        return f'''
        <div id="overview" class="header">
            <h1>{self.sf2_file.name}</h1>
            <div class="subtitle">SF2 Format Analysis - Interactive Report</div>
        </div>
'''

    def _create_stats_grid(self) -> str:
        """Create statistics grid"""

        # Count sequences (sequences is a dict)
        non_empty_seqs = len(self.parser.sequences) if isinstance(self.parser.sequences, dict) else 0

        # Count orderlists
        non_empty_orderlists = len(self.parser.orderlist_unpacked) if hasattr(self.parser, 'orderlist_unpacked') else 0

        # Get driver type from file info
        driver_type = "Unknown"
        if hasattr(self.parser, 'driver_type'):
            driver_type = self.parser.driver_type
        elif self.parser.load_address == 0x0D7E:
            driver_type = "Driver 11"

        cards = [
            StatCard("File Size", f"{self.file_size:,} bytes", StatCardType.INFO),
            StatCard("Orderlists", str(non_empty_orderlists), StatCardType.PRIMARY),
            StatCard("Sequences", str(non_empty_seqs), StatCardType.SUCCESS),
            StatCard("Instruments", "8", StatCardType.WARNING),
            StatCard("Driver", driver_type, StatCardType.INFO),
            StatCard("Load Address", f"${self.parser.load_address:04X}", StatCardType.PRIMARY)
        ]

        return HTMLComponents.create_stat_grid(cards)

    def _create_search_box(self) -> str:
        """Create search box"""
        return HTMLComponents.create_search_box(
            placeholder="Search sequences, instruments, tables...",
            target_class=".searchable"
        )

    def _create_file_info(self) -> str:
        """Create file information section"""

        info_rows = [
            ["File Name", self.sf2_file.name],
            ["File Size", f"{self.file_size:,} bytes"],
            ["Load Address", f"${self.parser.load_address:04X}"],
            ["Init Address", f"${self.parser.init_address:04X}" if hasattr(self.parser, 'init_address') else "N/A"],
            ["Play Address", f"${self.parser.play_address:04X}" if hasattr(self.parser, 'play_address') else "N/A"]
        ]

        table = HTMLComponents.create_table(
            headers=["Property", "Value"],
            rows=info_rows
        )

        return HTMLComponents.create_collapsible(
            "file-info",
            "File Information",
            table,
            collapsed=False
        )

    def _create_orderlists_section(self) -> str:
        """Create orderlists section"""

        # Build orderlist table using orderlist_unpacked (list of 3 tracks)
        rows = []

        if hasattr(self.parser, 'orderlist_unpacked') and self.parser.orderlist_unpacked:
            for voice_idx, track_entries in enumerate(self.parser.orderlist_unpacked[:3], 1):
                if track_entries:
                    # Format sequence indices from unpacked entries
                    seq_indices = [entry['sequence_index'] for entry in track_entries if entry.get('sequence_index') is not None]
                    seq_list = ' '.join(f"{seq:02X}" for seq in seq_indices[:20])  # Limit to first 20
                    if len(seq_indices) > 20:
                        seq_list += " ..."
                    if not seq_list:
                        seq_list = "(empty)"
                    rows.append([f"Voice {voice_idx}", seq_list])
                else:
                    rows.append([f"Voice {voice_idx}", "(empty)"])
        else:
            # Fallback to raw orderlist if unpacked not available
            for voice_idx in range(1, 4):
                rows.append([f"Voice {voice_idx}", "(not available)"])

        table = HTMLComponents.create_table(
            headers=["Voice", "Sequence Order"],
            rows=rows
        )

        content = f"""
        <p>Orderlists define the playback order of sequences for each voice.</p>
        {table}
        <p style="color: {ColorScheme.TEXT_SECONDARY}; font-size: 0.9em; margin-top: 10px;">
            Note: Sequences are referenced by index (00-FF). 0xFF marks the end of the orderlist.
        </p>
"""

        return HTMLComponents.create_collapsible(
            "orderlists",
            "Orderlists (3 voices)",
            content,
            collapsed=False
        )

    def _format_note(self, note_value: int) -> str:
        """
        Convert note value to musical notation.

        Args:
            note_value: Note byte (0x00-0x7F)

        Returns:
            Musical notation string (C-4, F#-2, ---, +++, END)
        """
        if note_value == 0x00:
            return "---"  # Gate off / silence
        elif note_value == 0x7E:
            return "+++"  # Gate on / sustain
        elif note_value == 0x7F:
            return "END"  # End marker
        elif note_value >= 0x80:
            return f"0x{note_value:02X}"  # Control byte
        else:
            # Valid note (0x01-0x7D)
            notes = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']
            octave = note_value // 12
            note_idx = note_value % 12
            return f"{notes[note_idx]}{octave}"

    def _create_sequences_section(self) -> str:
        """Create sequences section"""

        # Get sequences (dict of seq_idx -> list of SequenceEntry objects)
        if not isinstance(self.parser.sequences, dict) or not self.parser.sequences:
            content = "<p>No sequences found in this SF2 file.</p>"
            return HTMLComponents.create_collapsible(
                "sequences",
                "Sequences (0)",
                content,
                collapsed=True
            )

        # Convert dict to list of (idx, entries)
        non_empty_seqs = [(idx, entries) for idx, entries in sorted(self.parser.sequences.items()) if entries]

        if not non_empty_seqs:
            content = "<p>No sequences found in this SF2 file.</p>"
            return HTMLComponents.create_collapsible(
                "sequences",
                "Sequences (0)",
                content,
                collapsed=True
            )

        # Create summary table
        summary_rows = []
        for seq_idx, entries in non_empty_seqs[:20]:  # Limit to first 20 for summary
            # Get first few notes
            notes_preview = []
            for entry in entries[:3]:  # First 3 entries
                if entry.note == 0x7F:  # END marker
                    notes_preview.append("END")
                    break
                # Use entry's note_name method if available
                if hasattr(entry, 'note_name'):
                    notes_preview.append(entry.note_name())
                else:
                    notes_preview.append(self._format_note(entry.note))

            notes_str = ' '.join(notes_preview)
            if len(entries) > 3:
                notes_str += " ..."

            summary_rows.append([
                f"{seq_idx:02X}",
                f"{len(entries)}",  # Number of entries
                notes_str
            ])

        summary_table = HTMLComponents.create_table(
            headers=["Seq #", "Length", "Preview (first 3 notes)"],
            rows=summary_rows,
            table_class="searchable"
        )

        # Create detailed view for each sequence (collapsible)
        detailed_html = ""
        for seq_idx, entries in non_empty_seqs:
            detailed_html += self._create_sequence_detail(seq_idx, entries)

        content = f"""
        <p>Sequences contain the actual musical notes and instrument references.</p>
        <p>Total sequences: {len(non_empty_seqs)} (showing top 20 in summary)</p>

        <h3>Sequence Summary</h3>
        {summary_table}

        <h3>Detailed Sequences</h3>
        <p style="color: {ColorScheme.TEXT_SECONDARY}; font-size: 0.9em;">
            Click to expand individual sequences for full note data.
        </p>
        {detailed_html}
"""

        return HTMLComponents.create_collapsible(
            "sequences",
            f"Sequences ({len(non_empty_seqs)})",
            content,
            collapsed=True
        )

    def _create_sequence_detail(self, seq_idx: int, entries: List) -> str:
        """Create detailed view for a single sequence"""

        # Build table from SequenceEntry objects
        rows = []
        for step, entry in enumerate(entries):
            # Get note name
            if hasattr(entry, 'note_name'):
                note_str = entry.note_name()
            else:
                note_str = self._format_note(entry.note)

            # Color code special notes
            if entry.note == 0x00:
                note_style = f'style="color: {ColorScheme.TEXT_SECONDARY};"'
            elif entry.note == 0x7E:
                note_style = f'style="color: {ColorScheme.SUCCESS};"'
            elif entry.note == 0x7F:
                note_style = f'style="color: {ColorScheme.ERROR};"'
            elif entry.note >= 0x80:
                note_style = f'style="color: {ColorScheme.WARNING};"'
            else:
                note_style = f'style="color: {ColorScheme.ACCENT_TEAL};"'

            # Instrument reference (clickable link)
            # Instrument field: 0x80=no change, 0x90=tie, 0xA0-0xBF=instrument index
            if entry.instrument >= 0xA0 and entry.instrument <= 0xBF:
                inst_idx = entry.instrument & 0x1F  # Lower 5 bits
                inst_str = f'<a href="#instrument-{inst_idx:02X}" style="color: {ColorScheme.ACCENT_BLUE};">{inst_idx:02X}</a>'
            elif entry.instrument == 0x80:
                inst_str = '<span style="color: {ColorScheme.TEXT_SECONDARY};">--</span>'
            elif entry.instrument == 0x90:
                inst_str = '<span style="color: {ColorScheme.WARNING};">Tie</span>'
            else:
                inst_str = f"0x{entry.instrument:02X}"

            rows.append([
                f"{step:03d}",
                f'<span {note_style}>{note_str}</span>',
                inst_str,
                f"0x{entry.note:02X}",
                f"0x{entry.instrument:02X}"
            ])

            # Stop at END marker
            if entry.note == 0x7F:
                break

        table = HTMLComponents.create_table(
            headers=["Step", "Note", "Inst", "Note Hex", "Inst Hex"],
            rows=rows,
            table_class="searchable"
        )

        detail_content = f"""
        <p>Sequence {seq_idx:02X} - {len(rows)} steps</p>
        {table}
"""

        return HTMLComponents.create_collapsible(
            f"seq-{seq_idx:02X}",
            f"Sequence {seq_idx:02X} ({len(rows)} steps)",
            detail_content,
            collapsed=True
        )

    def _create_instruments_section(self) -> str:
        """Create instruments section"""

        # SF2 has 8 instruments (8 bytes each)
        instruments_data = []

        if hasattr(self.parser, 'instruments') and self.parser.instruments:
            # Parse instruments block (8 instruments × 8 bytes = 64 bytes)
            for i in range(8):
                offset = i * 8
                if offset + 8 <= len(self.parser.instruments):
                    inst_bytes = self.parser.instruments[offset:offset + 8]
                    instruments_data.append((i, inst_bytes))

        if not instruments_data:
            content = "<p>No instrument data found in this SF2 file.</p>"
            return HTMLComponents.create_collapsible(
                "instruments",
                "Instruments (0)",
                content,
                collapsed=True
            )

        # Create instruments table
        rows = []
        for inst_idx, inst_bytes in instruments_data:
            # Format as hex
            hex_str = ' '.join(f"{b:02X}" for b in inst_bytes)

            # Decode parameters (SF2 Driver 11 format)
            ad = inst_bytes[0] if len(inst_bytes) > 0 else 0
            sr = inst_bytes[1] if len(inst_bytes) > 1 else 0
            wave_idx = inst_bytes[2] if len(inst_bytes) > 2 else 0
            pulse_idx = inst_bytes[3] if len(inst_bytes) > 3 else 0

            params = f"AD:{ad:02X} SR:{sr:02X} Wave:{wave_idx:02X} Pulse:{pulse_idx:02X}"

            rows.append([
                f'<span id="instrument-{inst_idx:02X}">{inst_idx:02X}</span>',
                hex_str,
                params
            ])

        table = HTMLComponents.create_table(
            headers=["Inst #", "Raw Bytes (8 bytes)", "Parameters"],
            rows=rows,
            table_class="searchable"
        )

        content = f"""
        <p>Instruments define the sound characteristics for each note.</p>
        <p>Each instrument is 8 bytes defining ADSR envelope, waveform, pulse, etc.</p>
        {table}
        <p style="color: {ColorScheme.TEXT_SECONDARY}; font-size: 0.9em; margin-top: 10px;">
            Note: Parameters shown are for SF2 Driver 11 format. Click instrument numbers from sequences to jump here.
        </p>
"""

        return HTMLComponents.create_collapsible(
            "instruments",
            f"Instruments ({len(instruments_data)})",
            content,
            collapsed=True
        )

    def _create_tables_section(self) -> str:
        """Create tables section (wave, pulse, filter, arpeggio)"""

        tables_html = ""

        # Wave table
        if hasattr(self.parser, 'wave_table') and self.parser.wave_table:
            tables_html += self._create_wave_table()

        # Pulse table
        if hasattr(self.parser, 'pulse_table') and self.parser.pulse_table:
            tables_html += self._create_pulse_table()

        # Filter table
        if hasattr(self.parser, 'filter_table') and self.parser.filter_table:
            tables_html += self._create_filter_table()

        # Arpeggio table
        if hasattr(self.parser, 'arp_table') and self.parser.arp_table:
            tables_html += self._create_arp_table()

        if not tables_html:
            tables_html = "<p>No table data found in this SF2 file.</p>"

        content = f"""
        <p>Tables define various musical parameters used by instruments.</p>
        {tables_html}
"""

        return HTMLComponents.create_collapsible(
            "tables",
            "Tables (Wave, Pulse, Filter, Arpeggio)",
            content,
            collapsed=True
        )

    def _create_wave_table(self) -> str:
        """Create wave table section"""

        wave_data = self.parser.wave_table
        rows = []

        # Display in groups of 16
        for i in range(0, len(wave_data), 16):
            chunk = wave_data[i:i+16]
            hex_str = ' '.join(f"{b:02X}" for b in chunk)

            # Decode waveforms (bits 4-7 of each byte)
            waveforms = []
            for b in chunk:
                wave = (b >> 4) & 0x0F
                wave_names = {
                    0x0: "---",
                    0x1: "Tri",
                    0x2: "Saw",
                    0x3: "T+S",
                    0x4: "Pul",
                    0x5: "T+P",
                    0x6: "S+P",
                    0x7: "T+S+P",
                    0x8: "Noi"
                }
                waveforms.append(wave_names.get(wave, f"{wave:X}"))

            wave_str = ' '.join(waveforms)

            rows.append([
                f"{i:03d}-{i+15:03d}",
                hex_str,
                wave_str
            ])

        table = HTMLComponents.create_table(
            headers=["Index", "Raw Bytes", "Waveforms"],
            rows=rows[:10]  # Limit to first 10 rows
        )

        return f"""
        <h3>Wave Table ({len(wave_data)} bytes)</h3>
        <p>Defines waveform types: Triangle, Sawtooth, Pulse, Noise</p>
        {table}
"""

    def _create_pulse_table(self) -> str:
        """Create pulse table section"""

        pulse_data = self.parser.pulse_table
        rows = []

        # Display in groups of 16
        for i in range(0, min(len(pulse_data), 64), 16):
            chunk = pulse_data[i:i+16]
            hex_str = ' '.join(f"{b:02X}" for b in chunk)

            rows.append([
                f"{i:03d}-{i+15:03d}",
                hex_str
            ])

        table = HTMLComponents.create_table(
            headers=["Index", "Raw Bytes"],
            rows=rows
        )

        return f"""
        <h3>Pulse Table ({len(pulse_data)} bytes)</h3>
        <p>Defines pulse width modulation values</p>
        {table}
"""

    def _create_filter_table(self) -> str:
        """Create filter table section"""

        filter_data = self.parser.filter_table
        rows = []

        # Display in groups of 16
        for i in range(0, min(len(filter_data), 64), 16):
            chunk = filter_data[i:i+16]
            hex_str = ' '.join(f"{b:02X}" for b in chunk)

            rows.append([
                f"{i:03d}-{i+15:03d}",
                hex_str
            ])

        table = HTMLComponents.create_table(
            headers=["Index", "Raw Bytes"],
            rows=rows
        )

        return f"""
        <h3>Filter Table ({len(filter_data)} bytes)</h3>
        <p>Defines filter cutoff and resonance values</p>
        {table}
"""

    def _create_arp_table(self) -> str:
        """Create arpeggio table section"""

        arp_data = self.parser.arp_table
        rows = []

        # Display in groups of 16
        for i in range(0, min(len(arp_data), 64), 16):
            chunk = arp_data[i:i+16]
            hex_str = ' '.join(f"{b:02X}" for b in chunk)

            rows.append([
                f"{i:03d}-{i+15:03d}",
                hex_str
            ])

        table = HTMLComponents.create_table(
            headers=["Index", "Raw Bytes"],
            rows=rows
        )

        return f"""
        <h3>Arpeggio Table ({len(arp_data)} bytes)</h3>
        <p>Defines arpeggio patterns for chord effects</p>
        {table}
"""


def main():
    """Command-line interface"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Export SF2 file to interactive HTML report"
    )
    parser.add_argument("sf2_file", help="Input SF2 file")
    parser.add_argument(
        "-o", "--output",
        help="Output HTML file (default: <sf2_file>.html)",
        default=None
    )

    args = parser.parse_args()

    # Determine output file
    if args.output:
        output_html = args.output
    else:
        output_html = str(Path(args.sf2_file).with_suffix('.html'))

    # Export
    exporter = SF2HTMLExporter(args.sf2_file)
    success = exporter.export(output_html)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
