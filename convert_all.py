#!/usr/bin/env python3
"""
Batch converter for SID to SF2 files.

Converts all .sid files in the SID folder to .sf2 files in the SF2 folder.
Generates both NP20 (G4) and Driver 11 versions for each SID file.

Usage:
    python convert_all.py

Output:
    For each SID file (e.g., Angular.sid):
    - Angular_g4.sf2     (NP20/G4 version)
    - Angular_d11.sf2    (Driver 11 version)
    - Angular_info.txt   (conversion info with both driver metrics)
    - Angular.dump       (siddump output)

Examples:
    python convert_all.py
    python convert_all.py --input my_sids --output my_sf2s
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime
import re

# Import from sidm2 package for table extraction
from sidm2 import (
    SIDParser,
    extract_from_siddump,
    get_command_names,
    analyze_sequence_commands,
    generate_note_comparison_report,
    calculate_extraction_confidence,
)
from sidm2.table_extraction import (
    extract_all_laxity_tables,
    find_instrument_table,
    find_and_extract_wave_table,
    find_table_addresses_from_player,
)
from sidm2.instrument_extraction import (
    extract_laxity_instruments,
    extract_laxity_wave_table,
)
from sidm2.laxity_analyzer import LaxityPlayerAnalyzer
from laxity_parser import LaxityParser
from validate_extraction import parse_dump_file

# Version info
__version__ = "0.5.1"
__build_date__ = "2025-11-24"


def run_player_id(sid_path):
    """Run player-id.exe on a SID file and return the detected player."""
    player_id_exe = os.path.join('tools', 'player-id.exe')

    if not os.path.exists(player_id_exe):
        return "player-id.exe not found"

    try:
        result = subprocess.run(
            [player_id_exe, sid_path],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Parse output to find player name
        for line in result.stdout.split('\n'):
            if sid_path in line or os.path.basename(sid_path) in line:
                # Line format: "filename    PlayerName"
                parts = line.strip().split()
                if len(parts) >= 2:
                    return parts[-1]

        return "Unknown"
    except Exception as e:
        return f"Error: {str(e)}"


def run_siddump(sid_path, output_path, playback_time=60):
    """Run siddump.exe on a SID file and save output to .dump file.

    Args:
        sid_path: Path to input SID file
        output_path: Path to output .dump file
        playback_time: Playback time in seconds (default 60)

    Returns:
        True if successful, False otherwise
    """
    siddump_exe = os.path.join('tools', 'siddump.exe')

    if not os.path.exists(siddump_exe):
        return False

    try:
        result = subprocess.run(
            [siddump_exe, sid_path, f'-t{playback_time}'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            # Write output to dump file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result.stdout)
            return True
        else:
            return False
    except Exception as e:
        return False


def generate_info_file(sf2_dir, sid_file, sid_dir, output_files, converter_output, player_name,
                       sequences, instruments, orderlists, file_sizes, driver_types):
    """Generate an info text file for a converted SID with all table data.

    Args:
        sf2_dir: Output directory
        sid_file: Source SID filename
        sid_dir: Source SID directory
        output_files: Dict of driver_type -> output_filename
        converter_output: Output from converter
        player_name: Detected player name
        sequences: Number of sequences
        instruments: Number of instruments
        orderlists: Number of orderlists
        file_sizes: Dict of driver_type -> file_size
        driver_types: List of driver types used
    """
    info_file = os.path.join(sf2_dir, sid_file[:-4] + '_info.txt')

    # Extract more details from converter output
    sid_name = ""
    sid_author = ""
    sid_copyright = ""
    load_addr = ""
    init_addr = ""
    play_addr = ""
    data_size = ""
    tempo = ""
    instrument_names = []

    for line in converter_output.split('\n'):
        if line.startswith('Name:'):
            sid_name = line.split(':', 1)[1].strip()
        elif line.startswith('Author:'):
            sid_author = line.split(':', 1)[1].strip()
        elif line.startswith('Copyright:'):
            sid_copyright = line.split(':', 1)[1].strip()
        elif 'Load address:' in line:
            load_addr = line.split(':', 1)[1].strip()
        elif 'Init address:' in line:
            init_addr = line.split(':', 1)[1].strip()
        elif 'Play address:' in line:
            play_addr = line.split(':', 1)[1].strip()
        elif 'Data size:' in line:
            data_size = line.split(':', 1)[1].strip()
        elif 'Tempo:' in line:
            tempo = line.split(':', 1)[1].strip()
        elif re.match(r'\s+\d+:', line) and '(AD=' in line:
            instrument_names.append(line.strip())

    # Extract all table data from SID file
    sid_path = os.path.join(sid_dir, sid_file)
    tables_data = {}
    raw_sequences = []
    try:
        parser = SIDParser(sid_path)
        header = parser.parse_header()
        c64_data, load_address = parser.get_c64_data(header)
        tables_data = extract_all_laxity_tables(c64_data, load_address)

        # Get siddump data for validation info
        siddump_data = extract_from_siddump(sid_path)

        # Extract wave table
        wave_entries = extract_laxity_wave_table(c64_data, load_address)

        # Extract instruments with wave table
        laxity_instruments = extract_laxity_instruments(c64_data, load_address, wave_entries)

        # Merge missing ADSR values from siddump
        # DISABLED: This was causing crashes in SID Factory II
        if False and siddump_data:
            siddump_adsr = set(siddump_data['adsr_values'])
            laxity_adsr = set((i['ad'], i['sr']) for i in laxity_instruments)
            missing = siddump_adsr - laxity_adsr
            for ad, sr in sorted(missing):
                # Determine sound character from ADSR
                attack = (ad >> 4) & 0x0F
                sustain = (sr >> 4) & 0x0F
                release = sr & 0x0F

                if attack == 0 and (ad & 0x0F) <= 3 and release <= 8:
                    char = "Perc"
                elif attack >= 10:
                    char = "Pad"
                elif sustain >= 12:
                    char = "Lead"
                elif release <= 3 and attack <= 2:
                    char = "Stab"
                else:
                    char = ""

                idx = len(laxity_instruments)
                name = f"{idx:02d} {char} Dyn".strip() if char else f"{idx:02d} Dyn"
                laxity_instruments.append({
                    'index': idx,
                    'ad': ad,
                    'sr': sr,
                    'name': name
                })

        # Extract sequences for command analysis
        laxity_parser = LaxityParser(c64_data, load_address)
        raw_sequences, _ = laxity_parser.find_sequences()

        # Extract parsed sequences for note comparison
        analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
        extracted_data = analyzer.extract_music_data()
        parsed_sequences = extracted_data.sequences if extracted_data else []

        # Calculate confidence scores
        confidence = None
        if extracted_data:
            confidence = calculate_extraction_confidence(extracted_data, c64_data, load_address)
    except Exception as e:
        tables_data = {}
        laxity_instruments = []
        wave_entries = []
        raw_sequences = []
        parsed_sequences = []
        confidence = None

    # Write info file
    with open(info_file, 'w', encoding='utf-8') as f:
        f.write(f"SID to SF2 Conversion Info\n")
        f.write(f"=" * 50 + "\n\n")

        f.write(f"Source File\n")
        f.write(f"-" * 50 + "\n")
        f.write(f"Filename:      {sid_file}\n")
        f.write(f"Name:          {sid_name}\n")
        f.write(f"Author:        {sid_author}\n")
        f.write(f"Copyright:     {sid_copyright}\n")
        f.write(f"Player:        {player_name}\n")
        f.write(f"\n")

        f.write(f"Memory Layout\n")
        f.write(f"-" * 50 + "\n")
        f.write(f"Load address:  {load_addr}\n")
        f.write(f"Init address:  {init_addr}\n")
        f.write(f"Play address:  {play_addr}\n")
        f.write(f"Data size:     {data_size}\n")
        f.write(f"\n")

        # Memory Map Table - formatted with addresses
        try:
            # Get table addresses from player code references
            player_tables = find_table_addresses_from_player(c64_data, load_address)

            # Get addresses from extraction functions
            instr_addr, _ = find_instrument_table(c64_data, load_address, verbose=True)
            wave_addr, wave_entries_extracted, _ = find_and_extract_wave_table(c64_data, load_address, verbose=True)

            # Use player references for other tables
            freq_table_addr = player_tables.get('freq_lo', 0)
            pulse_table_addr = player_tables.get('pulse', 0)
            filter_table_addr = player_tables.get('filter', 0)

            # Get sequence data address from laxity parser
            seq_data_addr = 0
            if c64_data:
                lp = LaxityParser(c64_data, load_address)
                orderlists_found = lp.find_orderlists()
                sequences_found, seq_addrs = lp.find_sequences()
                if seq_addrs:
                    seq_data_addr = min(seq_addrs)

            # Calculate sizes
            wave_entries_count = len(wave_entries_extracted) if wave_entries_extracted else 0
            pulse_table_data = tables_data.get('pulse_table', [])
            filter_table_data = tables_data.get('filter_table', [])
            pulse_entries_count = len(pulse_table_data) if pulse_table_data else 0
            filter_entries_count = len(filter_table_data) if filter_table_data else 0
            instr_count = len(laxity_instruments) if laxity_instruments else 0

            f.write(f"Tables Memory Map\n")
            f.write(f"-" * 50 + "\n")
            f.write(f"| Address | Table              | Size               |\n")
            f.write(f"|---------|--------------------|--------------------|")

            # Sort tables by address
            table_entries = []
            if freq_table_addr:
                table_entries.append((freq_table_addr, "Frequency table", "192 bytes (96 × 2)"))
            if wave_addr:
                table_entries.append((wave_addr, "Wave table", f"{wave_entries_count * 2} bytes ({wave_entries_count} × 2)"))
            if pulse_table_addr:
                table_entries.append((pulse_table_addr, "Pulse table", f"{pulse_entries_count * 4} bytes ({pulse_entries_count} × 4)"))
            if filter_table_addr:
                table_entries.append((filter_table_addr, "Filter table", f"{filter_entries_count * 4} bytes ({filter_entries_count} × 4)"))
            if instr_addr:
                table_entries.append((instr_addr, "Instrument table", f"{instr_count * 7} bytes ({instr_count} × 7)"))
            if seq_data_addr:
                table_entries.append((seq_data_addr, "Sequence data", "Variable"))

            # Sort by address and print
            for addr, name, size in sorted(table_entries):
                f.write(f"\n| ${addr:04X}   | {name:18s} | {size:18s} |")

            f.write(f"\n")
            f.write(f"\n")
        except Exception as e:
            f.write(f"Tables Memory Map\n")
            f.write(f"-" * 50 + "\n")
            f.write(f"Error generating memory map: {e}\n")
            f.write(f"\n")

        f.write(f"Conversion Result\n")
        f.write(f"-" * 50 + "\n")
        # Show all generated output files with sizes
        for driver in driver_types:
            if driver in output_files and driver in file_sizes:
                driver_label = "NP20 (G4)" if driver == 'np20' else "Driver 11"
                f.write(f"{driver_label:14s} {output_files[driver]} ({file_sizes[driver]:,} bytes)\n")
        f.write(f"Tempo:         {tempo}\n")
        # Add multi-speed info if detected
        if extracted_data and hasattr(extracted_data, 'multi_speed') and extracted_data.multi_speed > 1:
            f.write(f"Multi-speed:   {extracted_data.multi_speed}x (tempo adjusted to {max(1, int(tempo) // extracted_data.multi_speed)})\n")
        f.write(f"Sequences:     {sequences}\n")
        f.write(f"Instruments:   {instruments}\n")
        f.write(f"Orderlists:    {orderlists}\n")
        f.write(f"\n")

        # Confidence Scores
        if confidence:
            f.write(confidence.format_report())
            f.write(f"\n\n")

        # Instruments table
        if laxity_instruments:
            f.write(f"Instruments Table\n")
            f.write(f"-" * 50 + "\n")
            f.write(f"Idx  AD  SR  Name\n")
            for instr in laxity_instruments:
                f.write(f"{instr['index']:3d}  {instr['ad']:02X}  {instr['sr']:02X}  {instr['name']}\n")
            f.write(f"\n")

        # Commands table with usage info
        command_names = get_command_names()
        cmd_analysis = analyze_sequence_commands(raw_sequences) if raw_sequences else {'command_counts': {}, 'set_adsr_values': []}
        f.write(f"Commands Table\n")
        f.write(f"-" * 50 + "\n")
        f.write(f"Idx  Name          Used\n")
        for i, name in enumerate(command_names):
            count = cmd_analysis['command_counts'].get(i, 0)
            used_str = f"{count}x" if count > 0 else "-"
            f.write(f"{i:3d}  {name:12s}  {used_str}\n")
        f.write(f"\n")

        # Set ADSR values from commands
        set_adsr_values = cmd_analysis.get('set_adsr_values', [])
        if set_adsr_values:
            f.write(f"Set ADSR Values (from commands)\n")
            f.write(f"-" * 50 + "\n")
            for ad, sr in set_adsr_values:
                f.write(f"  AD={ad:02X} SR={sr:02X}\n")
            f.write(f"\n")

        # Wave table
        if wave_entries:
            f.write(f"Wave Table\n")
            f.write(f"-" * 50 + "\n")
            f.write(f"Idx  Note  Wave  Description\n")
            for i, (note, wave) in enumerate(wave_entries):
                wave_name = {0x11: 'Tri', 0x21: 'Saw', 0x41: 'Pulse', 0x81: 'Noise',
                            0x10: 'Tri-', 0x20: 'Saw-', 0x40: 'Pulse-', 0x80: 'Noise-'}.get(wave, f'${wave:02X}')
                if note == 0x7F:
                    desc = f"Jump to {wave}"
                elif note == 0x7E:
                    desc = "End/Hold"
                elif note == 0x80:
                    desc = f"{wave_name} (recalc)"
                else:
                    desc = f"{wave_name} +{note}" if note else wave_name
                f.write(f"{i:3d}   {note:02X}    {wave:02X}   {desc}\n")
            f.write(f"\n")

        # Pulse table
        pulse_entries = tables_data.get('pulse_table', [])
        if pulse_entries:
            f.write(f"Pulse Table\n")
            f.write(f"-" * 50 + "\n")
            f.write(f"Idx  Val  Cnt  Dur  Next\n")
            for i, entry in enumerate(pulse_entries):
                f.write(f"{i:3d}   {entry[0]:02X}   {entry[1]:02X}   {entry[2]:02X}   {entry[3]:02X}\n")
            f.write(f"\n")

        # Filter table
        filter_entries = tables_data.get('filter_table', [])
        if filter_entries:
            f.write(f"Filter Table\n")
            f.write(f"-" * 50 + "\n")
            f.write(f"Idx  Val  Cnt  Dur  Next\n")
            for i, entry in enumerate(filter_entries):
                f.write(f"{i:3d}   {entry[0]:02X}   {entry[1]:02X}   {entry[2]:02X}   {entry[3]:02X}\n")
            f.write(f"\n")

        # HR table (default values)
        f.write(f"HR Table (Hard Restart)\n")
        f.write(f"-" * 50 + "\n")
        f.write(f"  0   0F   00   Default\n")
        f.write(f"\n")

        # Tempo table
        f.write(f"Tempo Table\n")
        f.write(f"-" * 50 + "\n")
        f.write(f"  0   {tempo if tempo else '06'}   Main tempo\n")
        f.write(f"  1   7F   End marker\n")
        f.write(f"\n")

        # Arp table (default values)
        f.write(f"Arp Table (Arpeggio)\n")
        f.write(f"-" * 50 + "\n")
        f.write(f"  0   00 04 07 7F   Major chord\n")
        f.write(f"  1   00 03 07 7F   Minor chord\n")
        f.write(f"  2   00 0C 7F 00   Octave\n")
        f.write(f"\n")

        # Init table
        f.write(f"Init Table\n")
        f.write(f"-" * 50 + "\n")
        f.write(f"  0   00 0F 00 01 02   Default init\n")
        f.write(f"\n")

        # Debug information - table finding details
        f.write(f"Debug Information\n")
        f.write(f"-" * 50 + "\n")
        try:
            # Get instrument table debug info
            instr_addr, instr_debug = find_instrument_table(c64_data, load_address, verbose=True)
            if instr_addr:
                f.write(f"Instrument table: ${instr_addr:04X} (score={instr_debug['best_score']})\n")
                if instr_debug['candidates']:
                    f.write(f"Top candidates:\n")
                    for addr, score, valid in instr_debug['candidates'][:3]:
                        f.write(f"  ${addr:04X}: score={score}, valid={valid}\n")
            else:
                f.write(f"Instrument table: Not found\n")

            # Get wave table debug info
            wave_addr, wave_entries_debug, wave_debug = find_and_extract_wave_table(c64_data, load_address, verbose=True)
            if wave_addr:
                f.write(f"Wave table: ${wave_addr:04X} (score={wave_debug['best_score']}, {len(wave_entries_debug)} entries)\n")
                # Show waveform types in best table
                waveform_types = sorted(set(wf for _, wf in wave_entries_debug))
                if waveform_types:
                    wf_str = ', '.join([f'{wf:02X}' for wf in waveform_types])
                    f.write(f"  Waveforms: [{wf_str}]\n")
                # Show top candidates
                if wave_debug['candidates']:
                    f.write(f"Top wave table candidates:\n")
                    for addr, score, entries, wfs in wave_debug['candidates'][:3]:
                        wf_str = ','.join([f'{wf:02X}' for wf in wfs])
                        f.write(f"  ${addr:04X}: score={score}, entries={entries}, waveforms=[{wf_str}]\n")
            else:
                f.write(f"Wave table: Not found\n")

            # Show table addresses from player code
            player_tables = find_table_addresses_from_player(c64_data, load_address)
            if player_tables:
                f.write(f"Player code references:\n")
                for name, addr in player_tables.items():
                    f.write(f"  {name}: ${addr:04X}\n")
        except Exception as e:
            f.write(f"Error getting debug info: {e}\n")
        f.write(f"\n")

        # ADSR Validation - compare extracted instruments against siddump
        dump_file_path = os.path.join(sf2_dir, sid_file[:-4] + '.dump')
        if os.path.exists(dump_file_path):
            try:
                dump_data = parse_dump_file(dump_file_path)

                # Get extracted instrument ADSR values
                extracted_adsr = set()
                for instr in laxity_instruments:
                    if isinstance(instr, dict):
                        ad = instr.get('ad', 0)
                        sr = instr.get('sr', 0)
                        extracted_adsr.add((ad, sr))

                # Filter out hard restart ADSR values from siddump
                hard_restart_adsr = {(0x0F, 0x00), (0x0F, 0x01)}
                siddump_adsr = dump_data['adsr_values'] - hard_restart_adsr

                f.write(f"ADSR Validation (Siddump Comparison)\n")
                f.write(f"-" * 50 + "\n")
                f.write(f"ADSR observed in playback: {len(siddump_adsr)} unique combinations\n")
                f.write(f"ADSR in instrument table:  {len(extracted_adsr)} entries\n")

                # Find matches
                matches = []
                missing = []

                # Build set of SR values for instant attack matching
                extracted_sr_values = {sr for _, sr in extracted_adsr}

                for ad, sr in sorted(siddump_adsr):
                    if (ad, sr) in extracted_adsr:
                        # Find which instrument has this ADSR
                        instr_idx = None
                        instr_name = 'Unknown'
                        for i, instr in enumerate(laxity_instruments):
                            if isinstance(instr, dict) and instr.get('ad') == ad and instr.get('sr') == sr:
                                instr_idx = i
                                instr_name = instr.get('name', f'Instr {i}')
                                break
                        matches.append((ad, sr, instr_idx, instr_name))
                    elif ad == 0x00 and sr in extracted_sr_values:
                        # Instant attack optimization - AD=00 with matching SR
                        matches.append((ad, sr, None, 'Instant attack (SR matches)'))
                    else:
                        missing.append((ad, sr))

                # Calculate match rate
                total = len(matches) + len(missing)
                match_rate = (len(matches) / total * 100) if total > 0 else 100
                f.write(f"Match rate: {match_rate:.0f}% ({len(matches)}/{total} observed values found)\n")
                f.write(f"\n")

                if matches:
                    f.write(f"Observed ADSR matches:\n")
                    for ad, sr, idx, name in matches[:15]:  # Show first 15
                        if idx is not None:
                            f.write(f"  ${ad:02X}{sr:02X} -> Instrument {idx} ({name})\n")
                        else:
                            f.write(f"  ${ad:02X}{sr:02X} -> {name}\n")
                    if len(matches) > 15:
                        f.write(f"  ... and {len(matches) - 15} more\n")
                    f.write(f"\n")

                if missing:
                    f.write(f"Unmatched observations ({len(missing)}):\n")
                    for ad, sr in missing[:10]:
                        f.write(f"  ${ad:02X}{sr:02X} - NOT in instrument table\n")
                    if len(missing) > 10:
                        f.write(f"  ... and {len(missing) - 10} more\n")
                    f.write(f"\n")
                elif total > 0:
                    f.write(f"All observed ADSR values found in instrument table!\n")
                    f.write(f"\n")

            except Exception as e:
                f.write(f"ADSR Validation (Siddump Comparison)\n")
                f.write(f"-" * 50 + "\n")
                f.write(f"Error validating ADSR: {e}\n")
                f.write(f"\n")
        else:
            f.write(f"ADSR Validation (Siddump Comparison)\n")
            f.write(f"-" * 50 + "\n")
            f.write(f"No siddump file available for validation\n")
            f.write(f"\n")

        # Note comparison analysis - read dump file if it exists
        if parsed_sequences and os.path.exists(dump_file_path):
            try:
                with open(dump_file_path, 'r', encoding='utf-8') as dump_f:
                    dump_content = dump_f.read()
                note_report = generate_note_comparison_report(dump_content, parsed_sequences)
                f.write(note_report)
            except Exception as e:
                f.write(f"Note Comparison Analysis\n")
                f.write(f"-" * 50 + "\n")
                f.write(f"Error generating note comparison: {e}\n")
                f.write(f"\n")
        elif parsed_sequences:
            f.write(f"Note Comparison Analysis\n")
            f.write(f"-" * 50 + "\n")
            f.write(f"No siddump file available for comparison\n")
            f.write(f"\n")

        f.write(f"Generated:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    return info_file


def convert_all(sid_dir='SID', sf2_dir='SF2'):
    """Convert all SID files in sid_dir to SF2 files in sf2_dir.

    Generates both NP20 (G4) and Driver 11 versions for each SID file.
    """

    # Always generate both driver types
    driver_types = ['np20', 'driver11']

    # Check if SID directory exists
    if not os.path.exists(sid_dir):
        print(f"Error: SID directory '{sid_dir}' not found")
        sys.exit(1)

    # Create SF2 directory if it doesn't exist
    if not os.path.exists(sf2_dir):
        os.makedirs(sf2_dir)
        print(f"Created output directory: {sf2_dir}")

    # Get list of SID files
    sid_files = [f for f in os.listdir(sid_dir) if f.lower().endswith('.sid')]

    if not sid_files:
        print(f"No .sid files found in '{sid_dir}'")
        sys.exit(1)

    print(f"SID to SF2 Batch Converter v{__version__}")
    print(f"=" * 50)
    print(f"Build date:       {__build_date__}")
    print(f"Input directory:  {sid_dir}")
    print(f"Output directory: {sf2_dir}")
    print(f"Drivers:          NP20 (G4), Driver 11")
    print(f"Files to convert: {len(sid_files)}")
    print(f"=" * 50)
    print()

    # Track results
    success_count = 0
    failed_files = []

    start_time = datetime.now()

    # Convert each file
    for i, sid_file in enumerate(sorted(sid_files), 1):
        input_path = os.path.join(sid_dir, sid_file)
        base_name = sid_file[:-4]

        print(f"[{i}/{len(sid_files)}] Converting {sid_file}...")

        # Run player-id.exe first
        player_name = run_player_id(input_path)
        print(f"       Player: {player_name}")

        # Convert to both driver types
        output_files = {}
        file_sizes = {}
        converter_output = ""
        sequences = 0
        instruments = 0
        orderlists = 3
        all_success = True

        for driver_type in driver_types:
            # Determine output filename
            if driver_type == 'np20':
                output_file = base_name + '_g4.sf2'
            else:
                output_file = base_name + '_d11.sf2'

            output_path = os.path.join(sf2_dir, output_file)

            # Run converter
            result = subprocess.run(
                [sys.executable, 'sid_to_sf2.py', input_path, output_path, '--driver', driver_type],
                capture_output=True,
                text=True
            )

            # Check result
            if result.returncode == 0 and os.path.exists(output_path):
                size = os.path.getsize(output_path)
                output_files[driver_type] = output_file
                file_sizes[driver_type] = size

                # Extract key info from first conversion
                if driver_type == 'np20':
                    converter_output = result.stdout
                    for line in result.stdout.split('\n'):
                        if 'Extracted' in line and 'sequences' in line:
                            try:
                                sequences = int(line.split()[1])
                            except (ValueError, IndexError):
                                pass
                        elif 'Extracted' in line and 'instruments' in line:
                            try:
                                instruments = int(line.split()[1])
                            except (ValueError, IndexError):
                                pass
                        elif 'Created' in line and 'orderlists' in line:
                            try:
                                orderlists = int(line.split()[1])
                            except (ValueError, IndexError):
                                pass

                driver_label = "NP20" if driver_type == 'np20' else "D11"
                print(f"       -> {output_file} ({driver_label}, {size:,} bytes)")
            else:
                all_success = False
                if result.stderr:
                    print(f"       -> {output_file} FAILED: {result.stderr.strip()[:80]}")
                else:
                    print(f"       -> {output_file} FAILED")

        if all_success and output_files:
            # Generate siddump file FIRST (needed for note comparison in info file)
            dump_file = os.path.join(sf2_dir, base_name + '.dump')
            dump_success = run_siddump(input_path, dump_file)

            # Generate info file (uses dump file for note comparison)
            info_file = generate_info_file(
                sf2_dir, sid_file, sid_dir, output_files, converter_output,
                player_name, sequences, instruments, orderlists, file_sizes, driver_types
            )

            print(f"       -> {os.path.basename(info_file)}")
            if dump_success:
                print(f"       -> {os.path.basename(dump_file)}")
            success_count += 1
        else:
            failed_files.append(sid_file)

    # Print summary
    elapsed = datetime.now() - start_time

    print()
    print(f"=" * 50)
    print(f"Conversion Complete")
    print(f"=" * 50)
    print(f"Successful: {success_count}/{len(sid_files)}")
    print(f"Failed:     {len(failed_files)}")
    print(f"Time:       {elapsed.total_seconds():.1f} seconds")

    if failed_files:
        print()
        print("Failed files:")
        for f in failed_files:
            print(f"  - {f}")

    print()
    print(f"Output files are in: {os.path.abspath(sf2_dir)}")

    return len(failed_files) == 0


def main():
    parser = argparse.ArgumentParser(
        description='Batch convert SID files to SF2 format (generates both NP20 and D11 versions)'
    )
    parser.add_argument(
        '--input', '-i',
        default='SID',
        help='Input directory containing .sid files (default: SID)'
    )
    parser.add_argument(
        '--output', '-o',
        default='SF2',
        help='Output directory for .sf2 files (default: SF2)'
    )

    args = parser.parse_args()

    success = convert_all(
        sid_dir=args.input,
        sf2_dir=args.output
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
