#!/usr/bin/env python3
"""
SF2 Data Exporter - Export all SF2 data to text files

Exports SF2 file data to separate text files matching SID Factory II editor format:
- orderlist.txt - OrderList (track sequence order)
- track1.txt, track2.txt, track3.txt - Individual track data
- instruments.txt - Instrument definitions
- wave.txt - Wave table
- pulse.txt - Pulse table
- filter.txt - Filter table
- arp.txt - Arpeggio table
- tempo.txt - Tempo table
- hr.txt - Hard Restart table
- init.txt - Init table
- commands.txt - Command reference

Usage:
    python sf2_to_text_exporter.py <sf2_file> [output_directory]

Example:
    python sf2_to_text_exporter.py "learnings/Laxity - Stinsen.sf2" output/stinsen_export
"""

import sys
import os
from pathlib import Path
from typing import List, Dict
from sf2_viewer_core import SF2Parser

class SF2TextExporter:
    """Export SF2 data to text files matching SID Factory II format"""

    def __init__(self, sf2_file: str, output_dir: str):
        self.sf2_file = sf2_file
        self.output_dir = output_dir
        self.parser = SF2Parser(sf2_file)

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

    def _format_note(self, note_value: int) -> str:
        """Convert note value to musical notation (SF2 Editor format).

        Args:
            note_value: Note byte (0x00-0x7F)

        Returns:
            Musical notation string (C-4, F#-2, +++, ---, END)
        """
        if note_value == 0x00:
            return "---"  # Gate off / silence
        elif note_value == 0x7E:
            return "+++"  # Gate on / sustain
        elif note_value == 0x7F:
            return "END"  # End marker
        elif note_value > 0x7F:
            return f"0x{note_value:02X}"  # Invalid
        else:
            # Valid note (0x01-0x7D)
            notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            octave = note_value // 12
            note_idx = note_value % 12
            return f"{notes[note_idx]}-{octave}"

    def _apply_transpose(self, note_value: int, transpose: int) -> int:
        """Apply transpose to note value.

        Args:
            note_value: Original note (0x00-0x7F)
            transpose: Transpose byte (0x80-0xBF)

        Returns:
            Transposed note value
        """
        # Special values not transposed
        if note_value in [0x00, 0x7E, 0x7F] or note_value >= 0x80:
            return note_value

        # Decode transpose (4-bit signed value in lower nibble)
        # 0xA0 = +0, 0xA2 = +2, 0xAC = -4 (12 wraps to -4)
        # Lower nibble: 0-7 = +0 to +7, 8-15 = -8 to -1
        transpose_nibble = transpose & 0x0F  # Lower nibble!
        if transpose_nibble < 8:
            semitones = transpose_nibble  # 0-7 = +0 to +7
        else:
            semitones = transpose_nibble - 16  # 8-15 = -8 to -1

        # Apply transpose
        transposed = note_value + semitones

        # Clamp to valid range
        if transposed < 0:
            transposed = 0
        elif transposed > 0x7D:
            transposed = 0x7D

        return transposed

    def export_all(self):
        """Export all SF2 data to text files"""
        print(f"Exporting SF2 data from: {self.sf2_file}")
        print(f"Output directory: {self.output_dir}")
        print()

        self.export_orderlist()
        self.export_tracks()  # NEW: Export track files (track_1.txt, track_2.txt, track_3.txt)
        self.export_sequences()
        self.export_instruments()
        self.export_wave_table()
        self.export_pulse_table()
        self.export_filter_table()
        self.export_arp_table()
        self.export_tempo_table()
        self.export_hr_table()
        self.export_init_table()
        self.export_commands_reference()
        self.export_summary()

        print()
        print("Export complete!")

    def export_orderlist(self):
        """Export OrderList to orderlist.txt (SF2 Editor Format)"""
        output_file = os.path.join(self.output_dir, "orderlist.txt")

        with open(output_file, 'w') as f:
            f.write("# OrderList Export (SF2 Editor Format)\n")
            f.write("# Format: Position: Track1 Track2 Track3 (XXYY = transpose + sequence)\n")
            f.write("# End markers: FE = end, FF = loop\n")
            f.write("# -------------------------------------------------------------------\n\n")

            # Track sequence usage for summary
            sequence_usage = {}  # {seq_num: count}
            invalid_sequences = []  # [(step, track, seq_num)]
            available_sequences = set(self.parser.sequences.keys())

            # Use unpacked orderlist data if available (NEW - from sf2_viewer_core.py Phase 1)
            if hasattr(self.parser, 'orderlist_unpacked') and self.parser.orderlist_unpacked:
                # Get all 3 tracks
                tracks = self.parser.orderlist_unpacked

                # Find maximum length
                max_len = max(len(track) for track in tracks) if tracks else 0

                # Export unpacked entries in SF2 editor format
                for pos in range(max_len):
                    f.write(f"{pos:04X}: ")

                    for track_idx, track in enumerate(tracks):
                        if pos < len(track):
                            entry = track[pos]
                            transpose = entry['transpose']
                            sequence = entry['sequence']

                            # Write in XXYY format (XX=transpose, YY=sequence)
                            f.write(f"{transpose:02X}{sequence:02X}")

                            # Track usage
                            sequence_usage[sequence] = sequence_usage.get(sequence, 0) + 1

                            # Validate sequence exists
                            if sequence not in available_sequences:
                                invalid_sequences.append((pos, track_idx + 1, sequence))
                        else:
                            # Track ended, show empty
                            f.write("    ")

                        # Add space between tracks (except last)
                        if track_idx < len(tracks) - 1:
                            f.write(" ")

                    f.write("\n")

            # Fallback: Use raw orderlist if unpacked not available
            elif hasattr(self.parser, 'orderlist') and self.parser.orderlist:
                f.write("# Warning: Using raw orderlist (unpacked data not available)\n")
                f.write("# Format: TT SS (TT=transpose if present, SS=sequence)\n\n")

                for step, seq in enumerate(self.parser.orderlist):
                    if seq == 0x7F:
                        f.write(f"{step:04X}: END\n")
                        break

                    # Track usage and validate
                    if seq != 0x00:
                        sequence_usage[seq] = sequence_usage.get(seq, 0) + 1
                        if seq not in available_sequences:
                            invalid_sequences.append((step, 1, seq))
                            f.write(f"{step:04X}: -- {seq:02X}  (sequence ${seq:02X} not found)\n")
                        else:
                            f.write(f"{step:04X}: -- {seq:02X}\n")
            else:
                f.write("(No orderlist data found)\n")

            # Add summary section
            f.write("\n")
            f.write("SEQUENCE USAGE SUMMARY\n")
            f.write("=" * 80 + "\n")
            f.write("\n")

            if sequence_usage:
                f.write(f"Total sequences referenced: {len(sequence_usage)}\n")
                f.write(f"Total sequences available: {len(available_sequences)}\n")
                f.write("\n")

                # List sequences by usage count
                f.write("Sequences used:\n")
                for seq_num in sorted(sequence_usage.keys()):
                    count = sequence_usage[seq_num]
                    status = "OK" if seq_num in available_sequences else "MISSING"
                    seq_format = self.parser.sequence_formats.get(seq_num, 'unknown')
                    f.write(f"  Sequence ${seq_num:02X}: {count:2d}x {status:10s} ({seq_format})\n")

                # List unused sequences
                unused = sorted(available_sequences - set(sequence_usage.keys()))
                if unused:
                    f.write("\n")
                    f.write(f"Unused sequences ({len(unused)}):\n")
                    for seq_num in unused:
                        seq_format = self.parser.sequence_formats.get(seq_num, 'unknown')
                        f.write(f"  Sequence ${seq_num:02X} ({seq_format})\n")

                # List invalid references
                if invalid_sequences:
                    f.write("\n")
                    f.write(f"VALIDATION ERRORS ({len(invalid_sequences)}):\n")
                    for step, track, seq_num in invalid_sequences:
                        f.write(f"  Step ${step:04X} Track {track}: Sequence ${seq_num:02X} not found\n")
            else:
                f.write("(No sequence references found)\n")

        print(f"[OK] Exported OrderList -> {output_file}")

    def export_tracks(self):
        """Export track files (track_1.txt, track_2.txt, track_3.txt).

        Combines OrderList + Sequences to show unpacked musical notation
        following playback order, matching SF2 editor track display.
        """
        # Check if we have unpacked orderlist data
        if not hasattr(self.parser, 'orderlist_unpacked') or not self.parser.orderlist_unpacked:
            print("[SKIP] Track export requires unpacked orderlist (Phase 1)")
            return

        # Export each of the 3 tracks
        for track_idx in range(3):
            track_num = track_idx + 1
            output_file = os.path.join(self.output_dir, f"track_{track_num}.txt")

            with open(output_file, 'w') as f:
                f.write(f"# Track {track_num} - Unpacked Musical Notation\n")
                f.write(f"# Format: Position | OrderList | Sequence | Transpose | Step | Instrument | Command | Note\n")
                f.write(f"# -----------------------------------------------------------------------------\n\n")

                # Get this track's orderlist
                if track_idx >= len(self.parser.orderlist_unpacked):
                    f.write("(No OrderList data for this track)\n")
                    print(f"[SKIP] Track {track_num} -> {output_file} (no orderlist data)")
                    continue

                track_orderlist = self.parser.orderlist_unpacked[track_idx]

                # Process each OrderList position
                for pos, entry in enumerate(track_orderlist):
                    transpose = entry['transpose']
                    sequence_idx = entry['sequence']

                    # Calculate signed transpose for display
                    transpose_nibble = transpose & 0x0F  # Lower nibble!
                    if transpose_nibble < 8:
                        transpose_signed = transpose_nibble
                        transpose_display = f"+{transpose_signed}"
                    else:
                        transpose_signed = transpose_nibble - 16
                        transpose_display = f"{transpose_signed}"

                    # Write position header
                    f.write(f"Position {pos:03d} | OrderList: {transpose:02X}{sequence_idx:02X} | ")
                    f.write(f"Sequence ${sequence_idx:02X} | Transpose {transpose_display}\n")

                    # Get sequence data
                    if sequence_idx not in self.parser.sequences:
                        f.write(f"  (Sequence ${sequence_idx:02X} not found)\n\n")
                        continue

                    sequence_data = self.parser.sequences[sequence_idx]

                    # Check sequence format
                    seq_format = self.parser.sequence_formats.get(sequence_idx, 'interleaved')

                    if seq_format == 'interleaved':
                        # 3-track interleaved: Extract this track's entries (every 3rd entry starting at track_idx)
                        track_entries = [sequence_data[i] for i in range(track_idx, len(sequence_data), 3)]
                    else:
                        # Single-track: Use all entries
                        track_entries = sequence_data

                    # Export sequence entries with musical notation
                    for step, seq_entry in enumerate(track_entries):
                        # Get values
                        instrument = seq_entry.instrument
                        command = seq_entry.command
                        note = seq_entry.note

                        # Apply transpose to note
                        if note not in [0x00, 0x7E, 0x7F] and note < 0x80:
                            transposed_note = self._apply_transpose(note, transpose)
                        else:
                            transposed_note = note

                        # Format display
                        inst_str = seq_entry.instrument_display()
                        cmd_str = seq_entry.command_display()
                        note_str = self._format_note(transposed_note)

                        # Write line
                        f.write(f"  {step:04X} | {inst_str:4s} | {cmd_str:4s} | {note_str:6s}\n")

                        # Stop at end marker
                        if note == 0x7F:
                            break

                    f.write("  [End of sequence]\n\n")

            print(f"[OK] Exported Track {track_num} -> {output_file}")

    def export_sequences(self):
        """Export all sequences to track1.txt, track2.txt, track3.txt"""

        # First, we need to combine all sequences used by each track
        # across the entire OrderList

        # For now, export all detected sequences separately
        for seq_idx, seq_data in self.parser.sequences.items():
            output_file = os.path.join(self.output_dir, f"sequence_{seq_idx:02X}.txt")

            seq_format = self.parser.sequence_formats.get(seq_idx, 'interleaved')

            with open(output_file, 'w') as f:
                f.write(f"SEQUENCE ${seq_idx:02X} ({seq_idx})\n")
                f.write("=" * 80 + "\n")
                f.write(f"Format: {seq_format}\n")
                f.write(f"Length: {len(seq_data)} entries\n")
                f.write("\n")

                # Add sequence summary
                instruments_used = set()
                commands_used = set()
                note_count = 0
                gate_on_count = 0
                rest_count = 0
                end_count = 0

                for entry in seq_data:
                    if entry.instrument and entry.instrument != 0x80:
                        instruments_used.add(entry.instrument)
                    if entry.command and entry.command != 0x80:
                        commands_used.add(entry.command)

                    # Count special markers
                    if hasattr(entry, 'note'):
                        if entry.note == 0x7E:
                            gate_on_count += 1
                        elif entry.note == 0x80 or entry.note == 0x00:
                            rest_count += 1
                        elif entry.note == 0x7F:
                            end_count += 1
                        elif entry.note and entry.note < 0x60:  # Regular notes
                            note_count += 1

                f.write("SEQUENCE SUMMARY:\n")
                if instruments_used:
                    inst_list = ', '.join(f"${i:02X}" for i in sorted(instruments_used))
                    f.write(f"  Instruments used: {inst_list} ({len(instruments_used)} unique)\n")
                else:
                    f.write(f"  Instruments used: None\n")

                if commands_used:
                    cmd_list = ', '.join(f"${c:02X}" for c in sorted(commands_used))
                    f.write(f"  Commands used: {cmd_list} ({len(commands_used)} unique)\n")
                else:
                    f.write(f"  Commands used: None\n")

                f.write(f"  Musical content: {note_count}× notes, {gate_on_count}× gate on (+++), {rest_count}× rest (---)")
                if end_count > 0:
                    f.write(f", {end_count}× END\n")
                else:
                    f.write("\n")
                f.write("\n")
                f.write("SEQUENCE ENTRY FORMAT (AA BB CCC):\n")
                f.write("  AA  = Instrument number (00-1F)\n")
                f.write("  BB  = Command (00-0F, see commands.txt)\n")
                f.write("  CCC = Note value or special marker\n")
                f.write("\n")
                f.write("NOTE NOTATION:\n")
                f.write("  C-0 to B-7   = Musical notes (8 octaves, 0=lowest)\n")
                f.write("  C#, D#, F#, G#, A# = Sharps (black keys)\n")
                f.write("  +++          = Gate on / note continue (0x7E)\n")
                f.write("  ---          = Rest / no note (0x80 or 0x00)\n")
                f.write("  END          = End of sequence (0x7F)\n")
                f.write("\n")
                f.write("TRANSPOSITION (in OrderList):\n")
                f.write("  80-9F = Transpose down (-32 to -1 semitones)\n")
                f.write("  A0    = No transposition (default)\n")
                f.write("  A1-BF = Transpose up (+1 to +31 semitones)\n")
                f.write("\n")
                f.write("SEQUENCE TYPES:\n")
                f.write("  Interleaved = 3 tracks side-by-side (Track 1, 2, 3)\n")
                f.write("  Single      = 1 track only\n")
                f.write("  Typical size: 32 or 64 rows (0x20 or 0x40)\n")
                f.write("  Maximum: 1000+ rows (with packing)\n")
                f.write("  Total sequences: Up to 128 (0x00-0x7F)\n")
                f.write("\n")

                if seq_format == 'single':
                    # Single-track format
                    f.write("Step  | Inst | Cmd  | Note   | [Hex]       | Type\n")
                    f.write("------|------|------|--------|-------------|-------------\n")

                    for step, entry in enumerate(seq_data):
                        inst = entry.instrument_display()
                        cmd = entry.command_display()
                        note = entry.note_name()

                        # Get hex values
                        inst_hex = f"{entry.instrument:02X}" if entry.instrument else "00"
                        cmd_hex = f"{entry.command:02X}" if entry.command else "00"
                        note_hex = f"{entry.note:02X}" if hasattr(entry, 'note') and entry.note else "00"
                        hex_str = f"[{inst_hex} {cmd_hex} {note_hex}]"

                        # Add type description for special values
                        if entry.note == 0x7E:
                            note_type = "<Gate On>"
                            note = "[+++]"  # Visual emphasis
                        elif entry.note == 0x80 or entry.note == 0x00:
                            note_type = "<Rest>"
                            note = "[---]"  # Visual emphasis
                        elif entry.note == 0x7F:
                            note_type = "*SEQUENCE END*"
                            note = "*END*"  # Strong visual emphasis
                        else:
                            note_type = ""

                        f.write(f"{step:04X}  | {inst:4s} | {cmd:4s} | {note:6s} | {hex_str:11s} | {note_type}\n")

                else:
                    # 3-track interleaved format
                    f.write("Step  | Track 1                      | Track 2                      | Track 3\n")
                    f.write("      | In  Cmd  Note     [Hex]     | In  Cmd  Note     [Hex]     | In  Cmd  Note     [Hex]\n")
                    f.write("------|------------------------------|------------------------------|------------------------------\n")

                    num_steps = (len(seq_data) + 2) // 3

                    for step in range(num_steps):
                        idx = step * 3

                        # Helper function to get emphasized note display
                        def get_note_display(entry):
                            """Get note display with visual emphasis for special values"""
                            if entry.note == 0x7E:
                                return "[+++]"
                            elif entry.note == 0x80 or entry.note == 0x00:
                                return "[---]"
                            elif entry.note == 0x7F:
                                return "*END*"
                            else:
                                return entry.note_name()

                        # Track 1 (index 0)
                        if idx < len(seq_data):
                            e1 = seq_data[idx]
                            inst_hex = f"{e1.instrument:02X}" if e1.instrument else "00"
                            cmd_hex = f"{e1.command:02X}" if e1.command else "00"
                            note_hex = f"{e1.note:02X}" if hasattr(e1, 'note') and e1.note else "00"
                            note_display = get_note_display(e1)
                            t1_str = f"{e1.instrument_display():3s} {e1.command_display():3s} {note_display:6s} [{inst_hex} {cmd_hex} {note_hex}]"
                        else:
                            t1_str = "--- --- ------ [-- -- --]"

                        # Track 2 (index 1)
                        if idx + 1 < len(seq_data):
                            e2 = seq_data[idx + 1]
                            inst_hex = f"{e2.instrument:02X}" if e2.instrument else "00"
                            cmd_hex = f"{e2.command:02X}" if e2.command else "00"
                            note_hex = f"{e2.note:02X}" if hasattr(e2, 'note') and e2.note else "00"
                            note_display = get_note_display(e2)
                            t2_str = f"{e2.instrument_display():3s} {e2.command_display():3s} {note_display:6s} [{inst_hex} {cmd_hex} {note_hex}]"
                        else:
                            t2_str = "--- --- ------ [-- -- --]"

                        # Track 3 (index 2)
                        if idx + 2 < len(seq_data):
                            e3 = seq_data[idx + 2]
                            inst_hex = f"{e3.instrument:02X}" if e3.instrument else "00"
                            cmd_hex = f"{e3.command:02X}" if e3.command else "00"
                            note_hex = f"{e3.note:02X}" if hasattr(e3, 'note') and e3.note else "00"
                            note_display = get_note_display(e3)
                            t3_str = f"{e3.instrument_display():3s} {e3.command_display():3s} {note_display:6s} [{inst_hex} {cmd_hex} {note_hex}]"
                        else:
                            t3_str = "--- --- ------ [-- -- --]"

                        f.write(f"{step:04X}  | {t1_str:28s} | {t2_str:28s} | {t3_str}\n")

            print(f"[OK] Exported Sequence ${seq_idx:02X} -> {output_file}")

    def export_instruments(self):
        """Export instrument table to instruments.txt"""
        output_file = os.path.join(self.output_dir, "instruments.txt")

        with open(output_file, 'w') as f:
            f.write("INSTRUMENTS\n")
            f.write("=" * 80 + "\n")
            f.write("\n")
            f.write("Format: 6 bytes per instrument\n")
            f.write("  Byte 0: Attack/Decay (high nibble=Attack, low=Decay)\n")
            f.write("  Byte 1: Sustain/Release (high nibble=Sustain, low=Release)\n")
            f.write("  Byte 2: Waveform (11=Triangle, 21=Sawtooth, 41=Pulse, 81=Noise, +10=Gate)\n")
            f.write("  Byte 3: Pulse table index (or 80=none)\n")
            f.write("  Byte 4: Wave table index (or 80=none)\n")
            f.write("  Byte 5: Hard Restart (HR) settings\n")
            f.write("\n")
            f.write("FLAGS (Byte 5):\n")
            f.write("  40  Enable HR\n")
            f.write("  20  Fret slide program\n")
            f.write("  10  Clear ADSR\n")
            f.write("  08  Oscillator reset\n")
            f.write("  04  HR tab index\n")
            f.write("  0X  HR tab index\n")
            f.write("\n")
            f.write("ADSR:\n")
            f.write("  01 02 03 04 05 06  Instruments\n")
            f.write("  01=Attack 02=Decay 03=Sustain 04=Release 05=Flags 06=?\n")
            f.write("\n")
            f.write("Inst | AD   SR   Wave Puls Wvtb HR   | Description\n")
            f.write("-----|------------------------------|----------------------------------\n")

            # Find Instruments table in descriptors (actually labeled as "Commands" in SF2)
            inst_desc = None
            for desc in self.parser.table_descriptors:
                if desc.name in ["Commands", "Command"]:
                    inst_desc = desc
                    break

            if inst_desc:
                table_data = self.parser.get_table_data(inst_desc)
                # Skip empty instruments (all zeros)
                non_empty_count = 0
                for idx, inst in enumerate(table_data):
                    # Skip all-zero instruments
                    if all(val == 0 for val in inst):
                        continue

                    non_empty_count += 1

                    # Handle both 3-byte and 6-byte formats
                    if len(inst) >= 6:
                        # 6-byte format: AD, SR, Wave, Pulse, WaveTable, HR
                        ad = inst[0]
                        sr = inst[1]
                        wave = inst[2]
                        pulse = inst[3]
                        wavetbl = inst[4]
                        hr = inst[5]
                    elif len(inst) >= 3:
                        # 3-byte format (simplified)
                        ad = inst[0]
                        sr = inst[1]
                        wave = inst[2] if len(inst) > 2 else 0
                        pulse = 0x80  # No pulse
                        wavetbl = 0x80  # No wave table
                        hr = 0x00  # No HR
                    else:
                        continue

                    # Decode waveform
                    wave_name = "Unknown"
                    if wave & 0x10:
                        gate = "+Gate"
                    else:
                        gate = ""

                    wave_type = wave & 0xF1
                    if wave_type == 0x11:
                        wave_name = f"Triangle{gate}"
                    elif wave_type == 0x21:
                        wave_name = f"Sawtooth{gate}"
                    elif wave_type == 0x41:
                        wave_name = f"Pulse{gate}"
                    elif wave_type == 0x81:
                        wave_name = f"Noise{gate}"
                    else:
                        wave_name = f"${wave:02X}{gate}" if wave != 0 else "Silent"

                    # Format display
                    pulse_str = "--" if pulse == 0x80 else f"{pulse:02X}"
                    wave_str = "--" if wavetbl == 0x80 else f"{wavetbl:02X}"

                    # Show raw hex for debugging
                    raw_hex = ' '.join(f"{val:02X}" for val in inst)

                    f.write(f"{idx:02X}   | {ad:02X}   {sr:02X}   {wave:02X}   {pulse_str:4s} {wave_str:4s} {hr:02X}   | {wave_name} [{raw_hex}]\n")

                if non_empty_count == 0:
                    f.write("(All instruments are empty/zero)\n")
            else:
                f.write("(No instrument data found)\n")

        print(f"[OK] Exported Instruments -> {output_file}")

    def export_wave_table(self):
        """Export wave table to wave.txt"""
        output_file = os.path.join(self.output_dir, "wave.txt")

        with open(output_file, 'w') as f:
            f.write("WAVE TABLE\n")
            f.write("=" * 80 + "\n")
            f.write("\n")
            f.write("Format: Waveform sequences\n")
            f.write("  Values: 00-FF (waveform settings)\n")
            f.write("  Common: 11=Triangle+Gate, 21=Sawtooth+Gate, 41=Pulse+Gate, 81=Noise+Gate\n")
            f.write("\n")
            f.write("WAVEFORM VALUES:\n")
            f.write("  YY = COUNT (## semitones)\n")
            f.write("  00-7F = up    Fret slide table:\n")
            f.write("  80-FF = down  00-7F = up\n")
            f.write("                80-FF = down\n")
            f.write("\n")
            f.write("Row  | Waveform Values\n")
            f.write("-----|--------------------------------------------------\n")

            # Find Wave table in descriptors
            wave_desc = None
            for desc in self.parser.table_descriptors:
                if desc.name == "Wave":
                    wave_desc = desc
                    break

            if wave_desc:
                table_data = self.parser.get_table_data(wave_desc)
                for row_idx, row in enumerate(table_data):
                    row_str = " ".join(f"{val:02X}" for val in row)
                    f.write(f"{row_idx:04X} | {row_str}\n")
                f.write(f"\n(Total: {len(table_data)} rows × {wave_desc.column_count} columns)\n")
            else:
                f.write("(No wave table found)\n")

        print(f"[OK] Exported Wave Table -> {output_file}")

    def export_pulse_table(self):
        """Export pulse table to pulse.txt"""
        output_file = os.path.join(self.output_dir, "pulse.txt")

        with open(output_file, 'w') as f:
            f.write("PULSE TABLE\n")
            f.write("=" * 80 + "\n")
            f.write("\n")
            f.write("Format: Pulse width modulation sequences\n")
            f.write("  3 bytes per row (displayed as raw hex)\n")
            f.write("\n")
            f.write("PULSE COMMAND FORMAT:\n")
            f.write("  8W WW FR  = Set pulse width WWW, hold for FR frames\n")
            f.write("              WWW = width (12-bit), FR = frames\n")
            f.write("  0A AA FR  = Add AAA to pulse width each frame for FR frames\n")
            f.write("              AAA = Add value, FR = frames\n")
            f.write("  7F -- XX  = Jump to pulse index XX\n")
            f.write("\n")
            f.write("Pulse\n")
            f.write("-----|--------------------------------------------------\n")

            # Find Pulse table in descriptors
            pulse_desc = None
            for desc in self.parser.table_descriptors:
                if desc.name == "Pulse":
                    pulse_desc = desc
                    break

            if pulse_desc:
                table_data = self.parser.get_table_data(pulse_desc)
                for row_idx, row in enumerate(table_data):
                    # Display raw hex bytes (3 bytes per row)
                    row_str = " ".join(f"{val:02X}" for val in row)
                    f.write(f"{row_idx:02X}: {row_str}\n")
            else:
                f.write("(No pulse table found)\n")

        print(f"[OK] Exported Pulse Table -> {output_file}")

    def export_filter_table(self):
        """Export filter table to filter.txt"""
        output_file = os.path.join(self.output_dir, "filter.txt")

        with open(output_file, 'w') as f:
            f.write("FILTER TABLE\n")
            f.write("=" * 80 + "\n")
            f.write("\n")
            f.write("Format: Filter cutoff and resonance sequences\n")
            f.write("  3 bytes per row (displayed as raw hex)\n")
            f.write("\n")
            f.write("FILTER COMMAND FORMAT:\n")
            f.write("  CC CC R8  = CCC = Cutoff (11-bit), R8 = Res+Bitmask\n")
            f.write("              9 = L+BP (Low+Band Pass)\n")
            f.write("              A = BP (Band Pass)\n")
            f.write("              B = L+HP+BP (High Stop)\n")
            f.write("              C = HP (High Pass)\n")
            f.write("              D = L+HP (Band Stop)\n")
            f.write("              E = BP+HP (Low Stop)\n")
            f.write("              F = L+BP+HP (All)\n")
            f.write("  0A AA FR  = Add AAA to cutoff each frame for FR frames\n")
            f.write("  7F -- XX  = Jump to filter index XX\n")
            f.write("\n")
            f.write("Filter\n")
            f.write("-----|--------------------------------------------------\n")

            # Find Filter table in descriptors
            filter_desc = None
            for desc in self.parser.table_descriptors:
                if desc.name == "Filter":
                    filter_desc = desc
                    break

            if filter_desc:
                table_data = self.parser.get_table_data(filter_desc)
                for row_idx, row in enumerate(table_data):
                    # Display raw hex bytes (3 bytes per row)
                    row_str = " ".join(f"{val:02X}" for val in row)
                    f.write(f"{row_idx:02X}: {row_str}\n")
            else:
                f.write("(No filter table found)\n")

        print(f"[OK] Exported Filter Table -> {output_file}")

    def export_arp_table(self):
        """Export arpeggio table to arp.txt"""
        output_file = os.path.join(self.output_dir, "arp.txt")

        with open(output_file, 'w') as f:
            f.write("ARPEGGIO TABLE\n")
            f.write("=" * 80 + "\n")
            f.write("\n")
            f.write("Format: Arpeggio note offset sequences\n")
            f.write("  Values are semitone offsets from base note\n")
            f.write("\n")
            f.write("ARP COMMAND FORMAT:\n")
            f.write("  XX        = Note add (semitone offset, or loop to arpeggio index)\n")
            f.write("  7F        = Loop to arpeggio index\n")
            f.write("\n")
            f.write("Row  | Arpeggio Offset Values\n")
            f.write("-----|--------------------------------------------------\n")

            # Find Arp table in descriptors
            arp_desc = None
            for desc in self.parser.table_descriptors:
                if desc.name in ["Arp", "Arpeggio"]:
                    arp_desc = desc
                    break

            if arp_desc:
                table_data = self.parser.get_table_data(arp_desc)
                for row_idx, row in enumerate(table_data):
                    row_str = " ".join(f"{val:02X}" for val in row)
                    f.write(f"{row_idx:04X} | {row_str}\n")
                f.write(f"\n(Total: {len(table_data)} rows × {arp_desc.column_count} columns)\n")
            else:
                f.write("(No arpeggio table found)\n")

        print(f"[OK] Exported Arpeggio Table -> {output_file}")

    def export_tempo_table(self):
        """Export tempo table to tempo.txt"""
        output_file = os.path.join(self.output_dir, "tempo.txt")

        with open(output_file, 'w') as f:
            f.write("TEMPO TABLE\n")
            f.write("=" * 80 + "\n")
            f.write("\n")
            f.write("Format: Tempo values (frame rate)\n")
            f.write("  Lower value = faster tempo\n")
            f.write("  Typical: 04-08 (fast), 10-20 (medium), 30+ (slow)\n")
            f.write("\n")
            f.write("Row  | Tempo Values\n")
            f.write("-----|--------------------------------------------------\n")

            # Find Tempo table in descriptors
            tempo_desc = None
            for desc in self.parser.table_descriptors:
                if desc.name in ["Tempo", "HR/Tempo"]:
                    tempo_desc = desc
                    break

            if tempo_desc:
                table_data = self.parser.get_table_data(tempo_desc)
                for row_idx, row in enumerate(table_data):
                    row_str = " ".join(f"{val:02X}" for val in row)
                    f.write(f"{row_idx:04X} | {row_str}\n")
                f.write(f"\n(Total: {len(table_data)} rows × {tempo_desc.column_count} columns)\n")
            else:
                f.write("(Tempo typically embedded in player code or combined with HR table)\n")

        print(f"[OK] Exported Tempo Table -> {output_file}")

    def export_hr_table(self):
        """Export Hard Restart table to hr.txt"""
        output_file = os.path.join(self.output_dir, "hr.txt")

        with open(output_file, 'w') as f:
            f.write("HARD RESTART (HR) TABLE\n")
            f.write("=" * 80 + "\n")
            f.write("\n")
            f.write("Format: Hard Restart settings\n")
            f.write("  Combined with Tempo in HR/Tempo table\n")
            f.write("\n")
            f.write("Row  | HR Values\n")
            f.write("-----|--------------------------------------------------\n")

            # Find HR or HR/Tempo table in descriptors
            hr_desc = None
            for desc in self.parser.table_descriptors:
                if "HR" in desc.name:
                    hr_desc = desc
                    break

            if hr_desc:
                table_data = self.parser.get_table_data(hr_desc)
                for row_idx, row in enumerate(table_data):
                    row_str = " ".join(f"{val:02X}" for val in row)
                    f.write(f"{row_idx:04X} | {row_str}\n")
                f.write(f"\n(Total: {len(table_data)} rows × {hr_desc.column_count} columns)\n")
            else:
                f.write("(HR values typically stored in Instrument table or HR/Tempo table)\n")
                f.write("See instruments.txt and tempo.txt for details\n")

        print(f"[OK] Exported HR Table -> {output_file}")

    def export_init_table(self):
        """Export Init table to init.txt"""
        output_file = os.path.join(self.output_dir, "init.txt")

        with open(output_file, 'w') as f:
            f.write("INIT TABLE\n")
            f.write("=" * 80 + "\n")
            f.write("\n")
            f.write("Format: Initialization values\n")
            f.write("  Values used for various initializations\n")
            f.write("\n")
            f.write("INIT FORMAT:\n")
            f.write("  XX YY     = XX = Tempo table index\n")
            f.write("              YY = Main Volume (0-15, or $0F)\n")
            f.write("\n")
            f.write("Row  | Init Values\n")
            f.write("-----|--------------------------------------------------\n")

            # Find Init table in descriptors
            init_desc = None
            for desc in self.parser.table_descriptors:
                if desc.name in ["Init", "Initialization"]:
                    init_desc = desc
                    break

            if init_desc:
                table_data = self.parser.get_table_data(init_desc)
                for row_idx, row in enumerate(table_data):
                    row_str = " ".join(f"{val:02X}" for val in row)
                    f.write(f"{row_idx:04X} | {row_str}\n")
                f.write(f"\n(Total: {len(table_data)} rows × {init_desc.column_count} columns)\n")
            else:
                f.write("(Init values typically embedded in player code)\n")

        print(f"[OK] Exported Init Table -> {output_file}")

    def export_commands_reference(self):
        """Export command reference to commands.txt"""
        output_file = os.path.join(self.output_dir, "commands.txt")

        with open(output_file, 'w') as f:
            f.write("COMMANDS TABLE\n")
            f.write("=" * 80 + "\n")
            f.write("\n")
            f.write("Format: Sequence commands (XX YY format)\n")
            f.write("  Used in sequences for note effects and modulation\n")
            f.write("\n")
            f.write("COMMAND LIST (Commands ## XX YY):\n")
            f.write("  00 XX YY  Slide up/down\n")
            f.write("  01 -- YY  Set to FREQ AMPL\n")
            f.write("  02 XX YY  Porta (persist)\n")
            f.write("  03 00 00  Porta off\n")
            f.write("  04 XX YY  Fret slide\n")
            f.write("  05 XX YY  Fret slide & note off\n")
            f.write("  06 XX YY  ADSR (persist)\n")
            f.write("  07 XX YY  Filter index\n")
            f.write("  08 XX YY  Pulse index\n")
            f.write("  09 -- YY  Wave index\n")
            f.write("  0A XX YY  ADSR values\n")
            f.write("  0B XX YY  Arp index\n")
            f.write("  0C -- YY  Wave index\n")
            f.write("  0D -- YY  Pulse index\n")
            f.write("  0E -- -Y  Main volume\n")
            f.write("\n")
            f.write("Row  | Command Name        | Function\n")
            f.write("-----|---------------------|---------------------------------------\n")

            # Find Commands table in descriptors (actually labeled as "Instruments" in SF2)
            cmd_desc = None
            for desc in self.parser.table_descriptors:
                if desc.name == "Instruments":
                    cmd_desc = desc
                    break

            if cmd_desc:
                table_data = self.parser.get_table_data(cmd_desc)

                # Command names for reference
                cmd_names = [
                    "No Command", "Portamento Up", "Portamento Down", "Vibrato",
                    "Gate Off", "Attack/Decay Set", "Sustain/Release Set", "Waveform Set",
                    "Filter Set", "Filter Sweep", "Pulse Width Set", "Pulse Sweep",
                    "Ring Modulation", "Sync", "Detune", "Jump/Pattern Break"
                ]

                for row_idx, row in enumerate(table_data):
                    row_str = " ".join(f"{val:02X}" for val in row)
                    cmd_name = cmd_names[row_idx] if row_idx < len(cmd_names) else f"Command {row_idx:02X}"
                    f.write(f"{row_idx:04X} | {cmd_name:19s} | {row_str}\n")
                f.write(f"\n(Total: {len(table_data)} commands)\n")
            else:
                # Provide reference if no table found
                f.write("\nSF2 Sequence Commands (Reference):\n")
                f.write("Command | Description\n")
                f.write("--------|--------------------------------------------------\n")
                f.write("00      | No command\n")
                f.write("01      | Portamento up\n")
                f.write("02      | Portamento down\n")
                f.write("03      | Vibrato\n")
                f.write("04      | Gate off\n")
                f.write("05      | Attack/Decay set\n")
                f.write("06      | Sustain/Release set\n")
                f.write("07      | Waveform set\n")
                f.write("08      | Filter set\n")
                f.write("09      | Filter sweep\n")
                f.write("0A      | Pulse width set\n")
                f.write("0B      | Pulse sweep\n")
                f.write("0C      | Ring modulation\n")
                f.write("0D      | Sync\n")
                f.write("0E      | Detune\n")
                f.write("0F      | Jump/Pattern break\n")

        print(f"[OK] Exported Commands -> {output_file}")

    def export_summary(self):
        """Export summary information to summary.txt"""
        output_file = os.path.join(self.output_dir, "summary.txt")

        with open(output_file, 'w') as f:
            f.write("SF2 FILE SUMMARY\n")
            f.write("=" * 80 + "\n")
            f.write("\n")
            f.write(f"Source File: {self.sf2_file}\n")
            f.write(f"Export Date: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("\n")

            # File statistics
            f.write("STATISTICS\n")
            f.write("-" * 80 + "\n")

            if hasattr(self.parser, 'sequences'):
                f.write(f"Sequences:       {len(self.parser.sequences)}\n")

                # Count formats
                single_count = sum(1 for fmt in self.parser.sequence_formats.values() if fmt == 'single')
                interleaved_count = sum(1 for fmt in self.parser.sequence_formats.values() if fmt == 'interleaved')
                f.write(f"  Single-track:  {single_count}\n")
                f.write(f"  Interleaved:   {interleaved_count}\n")

            if hasattr(self.parser, 'instruments'):
                f.write(f"Instruments:     {len(self.parser.instruments)}\n")

            if hasattr(self.parser, 'music_data_info') and self.parser.music_data_info:
                # Count non-empty orderlist entries
                addr_col1 = self.parser.music_data_info.orderlist_address
                count = 0
                for i in range(256):
                    if addr_col1 + i >= len(self.parser.memory):
                        break
                    if self.parser.memory[addr_col1 + i] == 0x7F:
                        break
                    count += 1
                f.write(f"OrderList Steps: {count}\n")
            elif hasattr(self.parser, 'orderlist') and self.parser.orderlist:
                # Fallback: count single column
                count = 0
                for seq in self.parser.orderlist:
                    if seq == 0x7F:
                        break
                    count += 1
                f.write(f"OrderList Steps: {count}\n")

            f.write("\n")

            # Detected format
            f.write("DETECTED FORMAT\n")
            f.write("-" * 80 + "\n")

            if hasattr(self.parser, 'is_laxity_driver') and self.parser.is_laxity_driver:
                f.write("Player Type:     Laxity NewPlayer v21\n")
            else:
                f.write("Player Type:     Standard SF2\n")

            f.write("\n")

            # Files exported
            f.write("EXPORTED FILES\n")
            f.write("-" * 80 + "\n")
            f.write("orderlist.txt       - OrderList (sequence playback order)\n")

            if hasattr(self.parser, 'sequences'):
                for seq_idx in sorted(self.parser.sequences.keys()):
                    seq_format = self.parser.sequence_formats.get(seq_idx, 'interleaved')
                    f.write(f"sequence_{seq_idx:02X}.txt    - Sequence ${seq_idx:02X} ({seq_format})\n")

            f.write("instruments.txt     - Instrument definitions\n")
            f.write("wave.txt            - Wave table\n")
            f.write("pulse.txt           - Pulse table\n")
            f.write("filter.txt          - Filter table\n")
            f.write("arp.txt             - Arpeggio table (placeholder)\n")
            f.write("tempo.txt           - Tempo information\n")
            f.write("hr.txt              - Hard Restart info\n")
            f.write("init.txt            - Init values info\n")
            f.write("commands.txt        - Command reference\n")
            f.write("summary.txt         - This file\n")

        print(f"[OK] Exported Summary -> {output_file}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python sf2_to_text_exporter.py <sf2_file> [output_directory]")
        print()
        print("Example:")
        print('  python sf2_to_text_exporter.py "learnings/Laxity - Stinsen.sf2" output/stinsen_export')
        return 1

    sf2_file = sys.argv[1]

    if not os.path.exists(sf2_file):
        print(f"Error: File not found: {sf2_file}")
        return 1

    # Determine output directory
    if len(sys.argv) >= 3:
        output_dir = sys.argv[2]
    else:
        # Auto-generate output directory name from SF2 filename
        base_name = Path(sf2_file).stem
        output_dir = f"output/{base_name}_export"

    try:
        exporter = SF2TextExporter(sf2_file, output_dir)
        exporter.export_all()
        return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
