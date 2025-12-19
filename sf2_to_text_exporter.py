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

    def export_all(self):
        """Export all SF2 data to text files"""
        print(f"Exporting SF2 data from: {self.sf2_file}")
        print(f"Output directory: {self.output_dir}")
        print()

        self.export_orderlist()
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
        """Export OrderList to orderlist.txt"""
        output_file = os.path.join(self.output_dir, "orderlist.txt")

        with open(output_file, 'w') as f:
            f.write("ORDER LIST\n")
            f.write("=" * 80 + "\n")
            f.write("\n")
            f.write("Format: Step | Track 1 | Track 2 | Track 3\n")
            f.write("        Each entry: TT SS (TT=transpose, SS=sequence)\n")
            f.write("\n")
            f.write("Step  | Track 1    | Track 2    | Track 3\n")
            f.write("------|------------|------------|------------\n")

            # Get orderlist data - stored as 3 separate columns
            if hasattr(self.parser, 'music_data_info') and self.parser.music_data_info:
                addr_col1 = self.parser.music_data_info.orderlist_address
                addr_col2 = getattr(self.parser, 'orderlist_col2_addr', addr_col1 + 0x100)
                addr_col3 = getattr(self.parser, 'orderlist_col3_addr', addr_col1 + 0x200)

                # Read all 3 columns
                for step in range(256):  # Max 256 entries
                    if addr_col1 + step >= len(self.parser.memory):
                        break

                    # Read sequence numbers from each column
                    t1_seq = self.parser.memory[addr_col1 + step]
                    t2_seq = self.parser.memory[addr_col2 + step] if addr_col2 + step < len(self.parser.memory) else 0x7F
                    t3_seq = self.parser.memory[addr_col3 + step] if addr_col3 + step < len(self.parser.memory) else 0x7F

                    # Check for end marker
                    if t1_seq == 0x7F:
                        f.write(f"{step:04X}  | END        | END        | END\n")
                        break

                    # For now, assume no transpose (most SF2 files)
                    # Transpose would be in a separate table if present
                    t1_trans_str = "--"
                    t2_trans_str = "--"
                    t3_trans_str = "--"

                    f.write(f"{step:04X}  | {t1_trans_str} {t1_seq:02X}      | {t2_trans_str} {t2_seq:02X}      | {t3_trans_str} {t3_seq:02X}\n")
            elif hasattr(self.parser, 'orderlist') and self.parser.orderlist:
                # Fallback: single column orderlist
                for step, seq in enumerate(self.parser.orderlist):
                    if seq == 0x7F:
                        f.write(f"{step:04X}  | END\n")
                        break

                    f.write(f"{step:04X}  | -- {seq:02X}\n")
            else:
                f.write("(No orderlist data found)\n")

        print(f"[OK] Exported OrderList -> {output_file}")

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

                if seq_format == 'single':
                    # Single-track format
                    f.write("Step  | Inst | Cmd  | Note\n")
                    f.write("------|------|------|------\n")

                    for step, entry in enumerate(seq_data):
                        inst = entry.instrument_display()
                        cmd = entry.command_display()
                        note = entry.note_name()

                        f.write(f"{step:04X}  | {inst:4s} | {cmd:4s} | {note:6s}\n")

                else:
                    # 3-track interleaved format
                    f.write("Step  | Track 1           | Track 2           | Track 3\n")
                    f.write("      | In  Cmd  Note     | In  Cmd  Note     | In  Cmd  Note\n")
                    f.write("------|-------------------|-------------------|-------------------\n")

                    num_steps = (len(seq_data) + 2) // 3

                    for step in range(num_steps):
                        idx = step * 3

                        # Track 1 (index 0)
                        if idx < len(seq_data):
                            e1 = seq_data[idx]
                            t1_str = f"{e1.instrument_display():3s} {e1.command_display():3s} {e1.note_name():6s}"
                        else:
                            t1_str = "--- --- ------"

                        # Track 2 (index 1)
                        if idx + 1 < len(seq_data):
                            e2 = seq_data[idx + 1]
                            t2_str = f"{e2.instrument_display():3s} {e2.command_display():3s} {e2.note_name():6s}"
                        else:
                            t2_str = "--- --- ------"

                        # Track 3 (index 2)
                        if idx + 2 < len(seq_data):
                            e3 = seq_data[idx + 2]
                            t3_str = f"{e3.instrument_display():3s} {e3.command_display():3s} {e3.note_name():6s}"
                        else:
                            t3_str = "--- --- ------"

                        f.write(f"{step:04X}  | {t1_str:17s} | {t2_str:17s} | {t3_str}\n")

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
            f.write("Inst | AD   SR   Wave Puls Wvtb HR   | Description\n")
            f.write("-----|------------------------------|----------------------------------\n")

            if hasattr(self.parser, 'instruments') and self.parser.instruments:
                for idx, inst in enumerate(self.parser.instruments):
                    if len(inst) >= 6:
                        ad = inst[0]
                        sr = inst[1]
                        wave = inst[2]
                        pulse = inst[3]
                        wavetbl = inst[4]
                        hr = inst[5]

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
                            wave_name = f"${wave:02X}{gate}"

                        # Format display
                        pulse_str = "--" if pulse == 0x80 else f"{pulse:02X}"
                        wave_str = "--" if wavetbl == 0x80 else f"{wavetbl:02X}"

                        f.write(f"{idx:02X}   | {ad:02X}   {sr:02X}   {wave:02X}   {pulse_str:4s} {wave_str:4s} {hr:02X}   | {wave_name}\n")
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
            f.write("  0x7F = End marker\n")
            f.write("  0x7E = Loop marker\n")
            f.write("  Other = Waveform value\n")
            f.write("\n")
            f.write("Index | Waveform Sequence\n")
            f.write("------|--------------------------------------------------\n")

            if hasattr(self.parser, 'wave_table') and self.parser.wave_table:
                # Wave table is stored as bytes
                idx = 0
                entry_num = 0
                while idx < len(self.parser.wave_table):
                    sequence = []
                    start_idx = idx

                    # Collect until end/loop marker
                    while idx < len(self.parser.wave_table):
                        byte = self.parser.wave_table[idx]
                        sequence.append(byte)
                        idx += 1

                        if byte == 0x7F or byte == 0x7E:
                            break

                        if len(sequence) > 64:  # Safety limit
                            break

                    # Format sequence
                    seq_str = " ".join(f"{b:02X}" for b in sequence)
                    f.write(f"{entry_num:02X}    | {seq_str}\n")

                    entry_num += 1

                    if entry_num > 64:  # Safety limit
                        break
            else:
                f.write("(No wave table data found)\n")

        print(f"[OK] Exported Wave Table -> {output_file}")

    def export_pulse_table(self):
        """Export pulse table to pulse.txt"""
        output_file = os.path.join(self.output_dir, "pulse.txt")

        with open(output_file, 'w') as f:
            f.write("PULSE TABLE\n")
            f.write("=" * 80 + "\n")
            f.write("\n")
            f.write("Format: Pulse width sequences (16-bit values)\n")
            f.write("  0x7F = End marker\n")
            f.write("\n")
            f.write("Index | Pulse Width Sequence\n")
            f.write("------|--------------------------------------------------\n")

            if hasattr(self.parser, 'pulse_table') and self.parser.pulse_table:
                idx = 0
                entry_num = 0

                while idx < len(self.parser.pulse_table):
                    sequence = []

                    # Collect until end marker
                    while idx < len(self.parser.pulse_table):
                        byte = self.parser.pulse_table[idx]

                        if byte == 0x7F:
                            sequence.append(0x7F)
                            idx += 1
                            break

                        # Read 16-bit pulse width (little-endian)
                        if idx + 1 < len(self.parser.pulse_table):
                            pw_lo = byte
                            pw_hi = self.parser.pulse_table[idx + 1]
                            pw = (pw_hi << 8) | pw_lo
                            sequence.append(pw)
                            idx += 2
                        else:
                            idx += 1
                            break

                        if len(sequence) > 32:  # Safety limit
                            break

                    # Format sequence
                    seq_str = " ".join(f"{w:04X}" if w != 0x7F else "END" for w in sequence)
                    f.write(f"{entry_num:02X}    | {seq_str}\n")

                    entry_num += 1

                    if entry_num > 64:  # Safety limit
                        break
            else:
                f.write("(No pulse table data found)\n")

        print(f"[OK] Exported Pulse Table -> {output_file}")

    def export_filter_table(self):
        """Export filter table to filter.txt"""
        output_file = os.path.join(self.output_dir, "filter.txt")

        with open(output_file, 'w') as f:
            f.write("FILTER TABLE\n")
            f.write("=" * 80 + "\n")
            f.write("\n")
            f.write("Format: Filter cutoff sequences\n")
            f.write("  0x7F = End marker\n")
            f.write("\n")
            f.write("Index | Filter Sequence\n")
            f.write("------|--------------------------------------------------\n")

            if hasattr(self.parser, 'filter_table') and self.parser.filter_table:
                idx = 0
                entry_num = 0

                while idx < len(self.parser.filter_table):
                    sequence = []

                    # Collect until end marker
                    while idx < len(self.parser.filter_table):
                        byte = self.parser.filter_table[idx]
                        sequence.append(byte)
                        idx += 1

                        if byte == 0x7F:
                            break

                        if len(sequence) > 64:  # Safety limit
                            break

                    # Format sequence
                    seq_str = " ".join(f"{b:02X}" for b in sequence)
                    f.write(f"{entry_num:02X}    | {seq_str}\n")

                    entry_num += 1

                    if entry_num > 64:  # Safety limit
                        break
            else:
                f.write("(No filter table data found)\n")

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
            f.write("  0x7F = End marker\n")
            f.write("\n")
            f.write("(Note: Arpeggio table not commonly used in SF2 format)\n")
            f.write("\n")

            # Most SF2 files don't have arpeggio tables, but include placeholder
            f.write("(No arpeggio table data found)\n")

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

            # Tempo is usually a single value or not stored separately in SF2
            # Check if we have tempo information
            f.write("(Tempo typically embedded in player code, not in data tables)\n")
            f.write("Default tempo: Variable (player-dependent)\n")

        print(f"[OK] Exported Tempo Table -> {output_file}")

    def export_hr_table(self):
        """Export Hard Restart table to hr.txt"""
        output_file = os.path.join(self.output_dir, "hr.txt")

        with open(output_file, 'w') as f:
            f.write("HARD RESTART (HR) TABLE\n")
            f.write("=" * 80 + "\n")
            f.write("\n")
            f.write("Format: Hard Restart settings per instrument\n")
            f.write("  Bit 7: HR enable (1=on, 0=off)\n")
            f.write("  Bits 0-6: Settings\n")
            f.write("\n")
            f.write("(Note: HR values are stored in Instrument table, byte 5)\n")
            f.write("See instruments.txt for details\n")

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

            # Init table not always present in SF2 format
            f.write("(Init values typically embedded in player code)\n")

        print(f"[OK] Exported Init Table -> {output_file}")

    def export_commands_reference(self):
        """Export command reference to commands.txt"""
        output_file = os.path.join(self.output_dir, "commands.txt")

        with open(output_file, 'w') as f:
            f.write("COMMAND REFERENCE\n")
            f.write("=" * 80 + "\n")
            f.write("\n")
            f.write("SF2 Sequence Commands\n")
            f.write("\n")
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
            f.write("--      | No command (80 in hex)\n")
            f.write("\n")
            f.write("Special Values:\n")
            f.write("  +++   | Note continue/gate on (7E)\n")
            f.write("  ---   | Rest/no note (00 or 80)\n")
            f.write("  END   | End marker (7F)\n")

        print(f"[OK] Exported Commands Reference -> {output_file}")

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
