"""Driver11 template-path section injectors.

Extracted from sf2_writer.py at the v3.5.48 Phase 13 refactor.

A cluster of 4 functions that all share the same shape — they mutate
the SF2 PRG output buffer with a specific section's data (orderlists,
sequences, instruments, commands) and have the exact same parameter
needs:

    inject_orderlists(output, data, driver_info, load_address)
    inject_sequences(output, data, driver_info, load_address)
    inject_instruments(output, data, driver_info, load_address)
    inject_commands(output, data, driver_info, load_address)

All four:
  - Read source data from `data` (ExtractedData).
  - Look up table addresses via `driver_info.table_addresses` or
    `driver_info.orderlist_start` etc.
  - Convert C64 addresses to file offsets via `_addr_to_offset(addr,
    load_address)`.
  - Mutate `output` in place with the section's bytes.

This module is used by the legacy driver11 template path (when a SID
is converted via the bundled `Driver 11 Test - Arpeggio.sf2` template
rather than the raw-NP21 inject path). It's the second cluster of
deduplicated helpers added during the v3.5.27+ decomposition (the
first being `sidm2.driver11_table_helpers` with `find_table` and
`write_column_major`).

# A note on the addr_to_offset helper

All four functions need to translate a C64 address into a file offset
in the PRG buffer. The translation is the same:

    file_offset = c64_addr - load_address + 2

(+2 for the 2-byte PRG load-address prefix at file offset 0).

This helper now lives at the module level rather than as
`SF2Writer._addr_to_offset` because all callers need to pass
`load_address` explicitly.
"""
from __future__ import annotations
import logging
import struct
from typing import Optional

from .table_extraction import find_and_extract_wave_table, extract_all_laxity_tables
from .instrument_extraction import extract_laxity_instruments, extract_laxity_wave_table
from .laxity_converter import LaxityConverter
from .sequence_extraction import (
    extract_command_parameters,
    build_sf2_command_table,
)
from .instrument_transposition import transpose_instruments
from . import driver11_table_helpers
from . import sf2_parser

# v3.5.52 — the Phase 17-moved _inject_*_table methods call into
# additional helpers that need module-level imports:
from .sequence_extraction import (
    extract_arpeggio_indices,
    find_arpeggio_table_in_memory,
    build_sf2_arp_table,
    analyze_sequence_commands,
    get_command_names,
)

logger = logging.getLogger(__name__)


def _addr_to_offset(addr: int, load_address: int) -> int:
    """Convert a C64 absolute address to a file offset in the PRG buffer.

    PRG files store [load_lo, load_hi] as the first 2 bytes, then the
    binary content starts at offset 2 in the file. So a C64 address
    X maps to file offset (X - load_address + 2).
    """
    return addr - load_address + 2


def inject_instruments(output: bytearray, data, driver_info, load_address: int) -> None:
    """Inject instrument data into the SF2 file using extracted Laxity data"""
    logger.info("  Injecting instruments...")

    if 'Instruments' not in driver_info.table_addresses:
        logger.debug("    Warning: No instrument table found in driver")
        return

    instr_table = driver_info.table_addresses['Instruments']
    instr_addr = instr_table['addr']
    columns = instr_table['columns']
    rows = instr_table['rows']

    wave_addr, wave_entries = find_and_extract_wave_table(data.c64_data, data.load_address)

    # Use instruments from laxity_parser (already in data.instruments as raw bytes)
    # Convert them to the format expected by SF2
    laxity_instruments = []
    for i, instr_bytes in enumerate(data.instruments[:16]):
        if len(instr_bytes) >= 8:
            # Laxity instrument format (8 bytes):
            # 0: AD, 1: SR, 2-4: flags/unknown, 5: Pulse param, 6: Pulse Ptr, 7: Wave Ptr
            ad = instr_bytes[0]
            sr = instr_bytes[1]
            restart = instr_bytes[2]
            filter_setting = instr_bytes[4]
            pulse_ptr = instr_bytes[6]
            wave_ptr = instr_bytes[7]
            filter_ptr = 0  # Not directly in instrument table

            # Determine waveform from wave table
            wave_for_sf2 = 0x41  # Default pulse
            if wave_entries and wave_ptr < len(wave_entries):
                waveform, _ = wave_entries[wave_ptr]
                wave_for_sf2 = waveform

            laxity_instruments.append({
                'index': i,
                'ad': ad,
                'sr': sr,
                'restart': restart,
                'filter_setting': filter_setting,
                'filter_ptr': filter_ptr,
                'pulse_ptr': pulse_ptr,
                'pulse_property': 0,
                'wave_ptr': wave_ptr,
                'ctrl': 0x41,
                'wave_for_sf2': wave_for_sf2,
                'name': f"{i:02d} Instr"
            })

    # Fill remaining slots with defaults
    while len(laxity_instruments) < 16:
        i = len(laxity_instruments)
        laxity_instruments.append({
            'index': i,
            'ad': 0x09,
            'sr': 0x00,
            'restart': 0x00,
            'filter_setting': 0x00,
            'filter_ptr': 0x00,
            'pulse_ptr': 0x00,
            'pulse_property': 0x00,
            'wave_ptr': 0x00,
            'ctrl': 0x41,
            'wave_for_sf2': 0x41,
            'name': f"{i:02d} Pulse"
        })

    data.laxity_instruments = laxity_instruments

    logger.info(f"    Converted {len(data.instruments)} Laxity instruments from parser")

    if hasattr(data, 'siddump_data') and data.siddump_data:
        siddump_adsr = set(data.siddump_data['adsr_values'])
        laxity_adsr = set((i['ad'], i['sr']) for i in laxity_instruments)
        matches = len(siddump_adsr & laxity_adsr)
        match_rate = matches / len(siddump_adsr) if siddump_adsr else 0
        logger.debug(f"    Validation: {match_rate*100:.0f}% of siddump ADSR values found in extraction")

    def waveform_to_wave_index(wave_for_sf2) -> int:
        if wave_for_sf2 == 0x21:
            return 0x00
        elif wave_for_sf2 == 0x41:
            return 0x02
        elif wave_for_sf2 == 0x11:
            return 0x04
        elif wave_for_sf2 == 0x81:
            return 0x06
        else:
            return 0x00

    is_np20 = columns == 8

    # Get valid wave entry points for validation
    from .table_extraction import get_valid_wave_entry_points
    valid_wave_points = get_valid_wave_entry_points(wave_entries) if wave_entries else {0}
    wave_table_size = len(wave_entries) if wave_entries else 0

    # Use new instrument transposition for Driver 11 (6 columns)
    if not is_np20 and columns == 6:
        logger.info("    Using instrument transposition module (Track B3)")

        # Prepare Laxity 8-byte instruments for transposition
        laxity_instr_bytes = []
        for i, instr_bytes in enumerate(data.instruments[:32]):  # Up to 32 instruments
            if len(instr_bytes) >= 8:
                # Process wave and pulse pointers
                instr_copy = bytearray(instr_bytes)
                wave_ptr = instr_copy[7]
                pulse_ptr = instr_copy[6]

                # Convert Laxity pulse_ptr from Y*4 indexing to direct index
                if pulse_ptr != 0 and pulse_ptr % 4 == 0:
                    pulse_ptr = pulse_ptr // 4
                instr_copy[3] = pulse_ptr  # LAXITY_PULSE = 3

                # Validate and clamp wave pointer
                if wave_table_size > 0 and wave_ptr >= wave_table_size:
                    valid_in_bounds = [p for p in valid_wave_points if p < wave_table_size]
                    if valid_in_bounds:
                        wave_ptr = min(valid_in_bounds, key=lambda p: abs(p - wave_ptr))
                    else:
                        wave_ptr = 0
                    logger.debug(f"    Clamped wave_ptr for instrument {i} to {wave_ptr}")
                instr_copy[2] = wave_ptr  # LAXITY_WAVEFORM = 2

                laxity_instr_bytes.append(bytes(instr_copy))

        # Transpose using B3 module (Laxity 8-byte → SF2 column-major 256-byte)
        sf2_table = transpose_instruments(laxity_instr_bytes, pad_to=rows)

        # Write transposed table directly
        base_offset = _addr_to_offset(instr_addr, load_address)
        table_size = min(len(sf2_table), rows * columns)

        for i in range(table_size):
            offset = base_offset + i
            if offset < len(output):
                output[offset] = sf2_table[i]

        instruments_written = len(laxity_instr_bytes)
        logger.info(f"    Written {instruments_written} instruments using transposition (B3)")

        # Log instrument details
        for i in range(min(instruments_written, 16)):
            if i < len(laxity_instruments):
                lax_instr = laxity_instruments[i]
                name = lax_instr.get('name', f'{i:02d} Instr')
                logger.debug(f"      {i}: {name} (AD={lax_instr['ad']:02X} SR={lax_instr['sr']:02X})")

    else:
        # Legacy path for NP20 or non-standard column counts
        logger.info("    Using legacy instrument format (NP20 or non-standard)")
        sf2_instruments = []

        for lax_instr in laxity_instruments:
            wave_ptr = lax_instr.get('wave_ptr', 0)
            pulse_ptr = lax_instr.get('pulse_ptr', 0)
            filter_ptr = lax_instr.get('filter_ptr', 0)

            # Convert Laxity pulse_ptr from Y*4 indexing to direct index
            if pulse_ptr != 0 and pulse_ptr % 4 == 0:
                pulse_ptr = pulse_ptr // 4

            if wave_ptr == 0:
                wave_ptr = waveform_to_wave_index(lax_instr['wave_for_sf2'])

            # Validate wave pointer
            if wave_table_size > 0 and wave_ptr >= wave_table_size:
                valid_in_bounds = [p for p in valid_wave_points if p < wave_table_size]
                if valid_in_bounds:
                    wave_ptr = min(valid_in_bounds, key=lambda p: abs(p - wave_ptr))
                else:
                    wave_ptr = 0
                logger.debug(f"    Clamped wave_ptr for instrument {lax_instr['index']} to {wave_ptr}")

            if is_np20:
                # NP20 instrument format (8 columns)
                sf2_instr = [
                    lax_instr['ad'],
                    lax_instr['sr'],
                    0x00,
                    0x00,
                    wave_ptr,
                    pulse_ptr,
                    filter_ptr,
                    0x00
                ]
            else:
                # Non-standard format fallback
                restart = lax_instr.get('restart', 0)
                flags = 0x00
                if restart & 0x80:
                    flags |= 0x80
                if restart & 0x10:
                    flags |= 0x10
                if lax_instr.get('filter_setting', 0):
                    flags |= 0x40

                sf2_instr = [
                    lax_instr['ad'],
                    lax_instr['sr'],
                    flags,
                    filter_ptr,
                    pulse_ptr,
                    wave_ptr
                ]
            sf2_instruments.append(sf2_instr)

        while len(sf2_instruments) < 16:
            if is_np20:
                sf2_instruments.append([0x09, 0xA0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            else:
                sf2_instruments.append([0x09, 0xA0, 0x00, 0x00, 0x00, 0x00])

        for i, lax_instr in enumerate(laxity_instruments):
            if i < len(sf2_instruments):
                instr = sf2_instruments[i]
                wave_names = {0x00: 'saw', 0x02: 'pulse', 0x04: 'tri', 0x06: 'noise'}
                wave_idx_pos = 4 if is_np20 else 5
                wave_name = wave_names.get(instr[wave_idx_pos], '?')
                name = lax_instr.get('name', f'{i:02d} {wave_name}')
                logger.debug(f"      {i}: {name} (AD={instr[0]:02X} SR={instr[1]:02X})")

        instruments_written = 0

        for col in range(columns):
            for row in range(rows):
                offset = _addr_to_offset(instr_addr, load_address) + col * rows + row

                if offset >= len(output):
                    continue

                if row < len(sf2_instruments) and col < len(sf2_instruments[row]):
                    output[offset] = sf2_instruments[row][col]
                else:
                    output[offset] = 0

            if col == 0:
                instruments_written = min(len(sf2_instruments), rows)

        logger.info(f"    Written {instruments_written} instruments (legacy path)")

def inject_sequences(output: bytearray, data, driver_info, load_address: int) -> None:
    """Inject sequence data into the SF2 file using packed variable-length format (Tetris-style)"""
    logger.debug("\n  Injecting sequences...")

    seq_start = _addr_to_offset(driver_info.sequence_start, load_address)
    ptr_lo_offset = _addr_to_offset(driver_info.sequence_ptrs_lo, load_address)
    ptr_hi_offset = _addr_to_offset(driver_info.sequence_ptrs_hi, load_address)

    if seq_start >= len(output) or seq_start < 0:
        logger.warning(f"     Invalid sequence start offset {seq_start}")
        return

    # PACKED MODE: Calculate actual size needed for each sequence
    # Sequences are written contiguously (Tetris-style stacking)
    # Only write sequences with actual data (skip empty placeholders)
    sequences_written = 0
    current_offset = seq_start  # Track current write position
    current_addr = driver_info.sequence_start  # Current address in C64 memory

    # Determine max sequence to write (up to driver limit or actual sequences)
    max_sequences = min(len(data.sequences), 256)

    for i in range(max_sequences):
        if i >= len(data.sequences):
            break

        seq = data.sequences[i]

        # Skip empty placeholder sequences (just end marker with 0x80 persistence)
        if len(seq) == 1 and seq[0].note == 0x7F and seq[0].instrument == 0x80 and seq[0].command == 0x80:
            # Write null pointer for empty sequence
            if ptr_lo_offset + i < len(output):
                output[ptr_lo_offset + i] = 0x00
            if ptr_hi_offset + i < len(output):
                output[ptr_hi_offset + i] = 0x00
            continue

        # Write sequence pointer (points to where this sequence will be written)
        if ptr_lo_offset + i < len(output):
            output[ptr_lo_offset + i] = current_addr & 0xFF
        if ptr_hi_offset + i < len(output):
            output[ptr_hi_offset + i] = (current_addr >> 8) & 0xFF

        seq_offset = current_offset  # Write at current packed position

        # SF2 sequences use packed format: only write instrument/command when they change
        # Format: [instr] [cmd] note [instr] [cmd] note ... 0x7F
        # Where instrument bytes are 0xA0-0xBF and command bytes are 0x01-0x3F
        #
        # Phase 1: Sequences now come pre-formatted from sequence_translator with:
        # - Proper SF2 command indices (0-63) from command_index_map
        # - Gate markers (0x7E sustain, 0x80 gate-off) already inserted
        # - Duration expansion already applied

        sequence_start_offset = seq_offset  # Remember where this sequence started
        rows_written = 0

        # Ensure we have enough space - resize output buffer if needed
        estimated_size = len(seq) * 3 + 10  # Conservative estimate
        if seq_offset + estimated_size > len(output):
            output.extend(bytearray(seq_offset + estimated_size - len(output)))

        # SF2 format requires DURATION byte (0x80-0x9F) before each note
        # Format: [instrument?] [command?] [DURATION] [note]
        # For now, use default duration of 0x80 (duration=0, no tie)
        # TODO: Add proper duration tracking to SequenceEvent structure
        DEFAULT_DURATION = 0x80

        for event in seq:
            # Skip duration bytes (0x80-0x9F) - shouldn't appear but be safe
            if 0x80 <= event.note <= 0x9F:
                continue

            # Write instrument change if not "no change" (0x80)
            if event.instrument != 0x80:
                output[seq_offset] = event.instrument
                seq_offset += 1

            # Write command index directly (Phase 1: already mapped to 0-63)
            # event.command is either 0x80 (no change) or 0-63 (command index)
            if event.command != 0x80:
                output[seq_offset] = event.command
                seq_offset += 1

            # *** CRITICAL FIX: Write duration byte (REQUIRED by SF2 format) ***
            # Duration bytes are 0x80-0x9F where lower 4 bits = ticks, bit 4 = tie flag
            output[seq_offset] = DEFAULT_DURATION
            seq_offset += 1

            # Write note (including gate markers 0x7E, 0x80)
            output[seq_offset] = event.note
            seq_offset += 1
            rows_written += 1

            # Stop at end marker
            if event.note == 0x7F:
                break

        # Ensure sequence ends with 0x7F
        if rows_written > 0 and seq_offset > 0:
            if output[seq_offset - 1] != 0x7F:
                output[seq_offset] = 0x7F
                seq_offset += 1

        # Calculate actual bytes written for this sequence
        bytes_written = seq_offset - sequence_start_offset

        # Update position for next sequence (pack them tightly)
        current_offset = seq_offset
        current_addr += bytes_written

        sequences_written += 1

    logger.info(f"    Written {sequences_written} sequences (packed, total {current_offset - seq_start} bytes)")

def inject_commands(output: bytearray, data, driver_info, load_address: int) -> None:
    """Inject command table data extracted from Laxity sequences"""
    logger.info("  Injecting Commands table...")

    if 'Commands' not in driver_info.table_addresses:
        logger.debug("    Warning: No Commands table found in driver")
        return

    cmd_table = driver_info.table_addresses['Commands']
    cmd_addr = cmd_table['addr']
    columns = cmd_table['columns']
    rows = cmd_table['rows']

    # Extract command parameters from raw sequences
    # Phase 1: Use pre-built command_index_map if available (from sequence_translator)
    if hasattr(data, 'command_index_map') and data.command_index_map:
        # Convert command_index_map to SF2 command table format
        # command_index_map is {(type, param1, param2): index}
        # We need to build array where sf2_commands[index] = (type, param1, param2)
        sf2_commands = [(0, 0, 0)] * 64
        for (cmd_type, param1, param2), index in data.command_index_map.items():
            if 0 <= index < 64:
                sf2_commands[index] = (cmd_type, param1, param2)

        logger.info(f"    Using pre-built command table with {len(data.command_index_map)} entries (Phase 1)")
    elif hasattr(data, 'sequences') and data.sequences:
        # Extract commands from parsed sequences (SequenceEvent format)
        sf2_commands = [(0, 0, 0)] * 64
        command_set = set()

        # Scan all sequences to find unique command combinations
        for seq in data.sequences:
            for event in seq:
                if event.command > 0:  # Non-zero command
                    # For SF2 format, command is (type, param1, param2)
                    # SequenceEvent.command contains the command value
                    command_set.add((event.command, event.instrument, 0))

        # Assign command indices
        for idx, (cmd_type, param1, param2) in enumerate(sorted(command_set)):
            if idx < 64:
                sf2_commands[idx] = (cmd_type, param1, param2)

        logger.info(f"    Extracted {len(command_set)} unique commands from parsed sequences")
    elif hasattr(data, 'raw_sequences') and data.raw_sequences:
        # Legacy path: extract from raw sequences
        command_params = extract_command_parameters(
            data.c64_data,
            data.load_address,
            data.raw_sequences
        )

        # Build the full 64-entry command table
        sf2_commands = build_sf2_command_table(command_params)

        logger.info(f"    Extracted {len(command_params)} unique commands from sequences (legacy)")
    else:
        # Default commands if no sequences available
        sf2_commands = [(0, 0, 0)] * 64
        logger.debug("    Using default command table (no sequences available)")

    # Write commands to SF2 file
    # SF2 command table: 3 columns (type, param1, param2), 64 rows
    # Format is column-major: all types first, then all param1s, then all param2s
    base_offset = _addr_to_offset(cmd_addr, load_address)

    commands_written = 0
    for col in range(min(columns, 3)):
        for row in range(min(rows, 64)):
            offset = base_offset + (col * rows) + row
            if offset < len(output) and row < len(sf2_commands):
                cmd_type, param1, param2 = sf2_commands[row]
                if col == 0:
                    output[offset] = cmd_type
                elif col == 1:
                    output[offset] = param1
                else:
                    output[offset] = param2

                if col == 0:
                    commands_written += 1

    logger.info(f"    Written {commands_written} command entries")

def inject_orderlists(output: bytearray, data, driver_info, load_address: int) -> None:
    """Inject orderlist data into the SF2 file using fixed 256-byte slots"""
    logger.info("  Injecting orderlists...")

    ol_start = _addr_to_offset(driver_info.orderlist_start, load_address)
    ptr_lo_offset = _addr_to_offset(driver_info.orderlist_ptrs_lo, load_address)
    ptr_hi_offset = _addr_to_offset(driver_info.orderlist_ptrs_hi, load_address)

    if ol_start >= len(output) or ol_start < 0:
        logger.warning(f"     Invalid orderlist start offset {ol_start}")
        return

    ORDERLIST_SLOT_SIZE = 256
    tracks_written = 0

    for track, orderlist in enumerate(data.orderlists[:3]):
        current_addr = driver_info.orderlist_start + (track * ORDERLIST_SLOT_SIZE)

        # Ensure buffer is large enough for pointers
        if ptr_lo_offset + track >= len(output):
            output.extend(bytearray(ptr_lo_offset + track - len(output) + 1))
        if ptr_hi_offset + track >= len(output):
            output.extend(bytearray(ptr_hi_offset + track - len(output) + 1))

        output[ptr_lo_offset + track] = current_addr & 0xFF
        output[ptr_hi_offset + track] = (current_addr >> 8) & 0xFF

        ol_offset = _addr_to_offset(current_addr, load_address)
        last_trans = -1

        # Pre-expand buffer for this orderlist
        estimated_ol_size = len(orderlist) * 2 + 10  # 2 bytes per entry + end marker
        if ol_offset + estimated_ol_size >= len(output):
            output.extend(bytearray(ol_offset + estimated_ol_size - len(output) + 1))

        for item in orderlist:
            # Handle both formats: simple int or (transposition, seq_idx) tuple
            if isinstance(item, tuple):
                transposition, seq_idx = item
            else:
                transposition = 0  # Default transposition
                seq_idx = item

            sf2_trans = 0xA0 + (transposition if transposition < 32 else transposition - 256)
            sf2_trans = max(0x80, min(0xBF, sf2_trans))

            if sf2_trans != last_trans:
                output[ol_offset] = sf2_trans
                ol_offset += 1
                last_trans = sf2_trans

            output[ol_offset] = seq_idx & 0x7F
            ol_offset += 1

        # Write end marker
        output[ol_offset] = 0xFF
        output[ol_offset + 1] = 0x00

        tracks_written += 1

    logger.info(f"    Written {tracks_written} orderlists")


# ---------------------------------------------------------------------------
# v3.5.52 Phase 17 additions — 7 more _inject_*_table methods.
# All follow the same (output, data, driver_info, load_address) shape.
# ---------------------------------------------------------------------------

def inject_init_table(output: bytearray, data, driver_info, load_address: int) -> None:
    """Inject Init table data."""
    logger.info("  Injecting Init table...")

    result = driver11_table_helpers.find_table(driver_info, 'Init')
    if result is None:
        logger.debug("    Warning: No Init table found in driver")
        return
    init_addr, columns, rows = result

    # Use extracted init table or build from defaults
    init_entries = getattr(data, 'init_table', None)
    if not init_entries:
        # Fallback to building from init_volume
        init_volume = getattr(data, 'init_volume', 0x0F)
        init_entries = [0x00, init_volume, 0x00, 0x01, 0x02]

    base_offset = _addr_to_offset(init_addr, load_address)

    for i, val in enumerate(init_entries):
        if i < rows * columns and base_offset + i < len(output):
            output[base_offset + i] = val

    init_volume = init_entries[1] if len(init_entries) > 1 else 0x0F
    logger.info(f"    Written {len(init_entries)} Init table entries (volume={init_volume})")

def inject_tempo_table(output: bytearray, data, driver_info, load_address: int) -> None:
    """Inject Tempo table data."""
    logger.info("  Injecting Tempo table...")

    result = driver11_table_helpers.find_table(
        driver_info, 'Tempo', 'T')
    if result is None:
        logger.debug("    Warning: No Tempo table found in driver")
        return
    tempo_addr, _columns, rows = result

    tempo = data.tempo if hasattr(data, 'tempo') else 6
    multi_speed = getattr(data, 'multi_speed', 1)

    # Adjust tempo for multi-speed tunes
    # Multi-speed tunes call the play routine multiple times per frame
    # To maintain correct playback speed, we divide tempo by multi-speed factor
    if multi_speed > 1:
        adjusted_tempo = max(1, tempo // multi_speed)
        logger.info(f"    Multi-speed tune detected ({multi_speed}x), adjusting tempo: {tempo} -> {adjusted_tempo}")
        tempo = adjusted_tempo

    tempo_entries = [tempo, 0x7F]

    base_offset = _addr_to_offset(tempo_addr, load_address)

    for i, val in enumerate(tempo_entries):
        if i < rows and base_offset + i < len(output):
            output[base_offset + i] = val

    logger.info(f"    Written tempo: {tempo}")

def inject_hr_table(output: bytearray, data, driver_info, load_address: int) -> None:
    """Inject HR (Hard Restart) table data."""
    logger.info("  Injecting HR table...")

    result = driver11_table_helpers.find_table(driver_info, 'HR')
    if result is None:
        logger.debug("    Warning: No HR table found")
        return
    hr_addr, _columns, rows = result

    # Use extracted HR table or default
    hr_entries = getattr(data, 'hr_table', None)
    if not hr_entries:
        hr_entries = [(0x0F, 0x00)]  # Default fallback

    # HR table is 2-column (frames, wave). Each entry is a 2-tuple.
    driver11_table_helpers.write_column_major(
        output, _addr_to_offset(hr_addr, load_address),
        hr_entries, columns=2, rows=rows)

    logger.info(f"    Written {len(hr_entries)} HR table entries (frames={hr_entries[0][0]})")

def inject_pulse_table(output: bytearray, data, driver_info, load_address: int) -> None:
    """Inject pulse table data extracted from Laxity SID"""
    logger.info("  Injecting Pulse table...")

    result = driver11_table_helpers.find_table(
        driver_info, 'Pulse', 'P')
    if result is None:
        logger.debug("    Warning: No Pulse table found in driver")
        return
    pulse_addr, columns, rows = result

    laxity_tables = extract_all_laxity_tables(data.c64_data, data.load_address)
    pulse_entries = laxity_tables.get('pulse_table', [])

    if not pulse_entries:
        pulse_entries = [(0x08, 0x01, 0x40, 0x00)]

    # Pad pulse table to minimum size to avoid missing entry errors
    # Neutral entry: 0xFF=keep value, 0x00=no modulation, 0x00=instant, 0x00=no chain
    MIN_PULSE_ENTRIES = 16
    neutral_entry = (0xFF, 0x00, 0x00, 0x00)
    while len(pulse_entries) < MIN_PULSE_ENTRIES:
        pulse_entries.append(neutral_entry)

    # Convert from Laxity format (Y*4 indexing) to SF2 format (direct indexing)
    # Laxity: (val, cnt, dur, next_y) where next_y is pre-multiplied by 4
    # SF2: (val, cnt, dur, next_idx) where next_idx is direct entry number
    # Index already converted during extraction (Y*4 → direct).
    driver11_table_helpers.write_column_major(
        output, _addr_to_offset(pulse_addr, load_address),
        pulse_entries, columns, rows)

    logger.info(f"    Written {len(pulse_entries)} Pulse table entries (padded from {len(laxity_tables.get('pulse_table', []))})")

def inject_filter_table(output: bytearray, data, driver_info, load_address: int) -> None:
    """Inject filter table data extracted from Laxity SID."""
    logger.info("  Injecting Filter table...")

    result = driver11_table_helpers.find_table(
        driver_info, 'Filter', 'F')
    if result is None:
        logger.debug("    Warning: No Filter table found in driver")
        return
    filter_addr, columns, rows = result

    laxity_tables = extract_all_laxity_tables(data.c64_data, data.load_address)
    laxity_filter_entries = laxity_tables.get('filter_table', [])

    if not laxity_filter_entries:
        laxity_filter_entries = [(0x40, 0x01, 0x20, 0x00)]

    # Convert Laxity filter format to SF2 filter format.
    logger.info(f"    Converting {len(laxity_filter_entries)} Laxity filter entries to SF2 format...")
    filter_entries = LaxityConverter.convert_filter_table(laxity_filter_entries)
    logger.info(f"    Converted to {len(filter_entries)} SF2 filter entries")

    # Pad to minimum size with neutral entry: no filter, no modulation,
    # instant, end marker.
    MIN_FILTER_ENTRIES = 16
    neutral_entry = (0x00, 0x00, 0x00, 0x7F)
    while len(filter_entries) < MIN_FILTER_ENTRIES:
        filter_entries.append(neutral_entry)

    driver11_table_helpers.write_column_major(
        output, _addr_to_offset(filter_addr, load_address),
        filter_entries, columns, rows)

    logger.info(f"    Written {len(filter_entries)} Filter table entries (padded from {len(laxity_tables.get('filter_table', []))})")

def inject_arp_table(output: bytearray, data, driver_info, load_address: int) -> None:
    """Inject Arpeggio table data."""
    logger.info("  Injecting Arp table...")

    result = driver11_table_helpers.find_table(
        driver_info, 'Arp', 'A')
    if result is None:
        logger.debug("    Warning: No Arp table found in driver")
        return
    arp_addr, columns, rows = result

    # Use extracted arpeggio table if available, otherwise try to extract
    if hasattr(data, 'arp_table') and data.arp_table:
        arp_entries = data.arp_table
        logger.info(f"    Using {len(arp_entries)} extracted arpeggio entries")
    elif hasattr(data, 'raw_sequences') and data.raw_sequences:
        # Try to extract arpeggio table from raw sequences
        arp_indices = extract_arpeggio_indices(data.raw_sequences)
        if arp_indices:
            logger.debug(f"    Found arpeggio indices: {sorted(arp_indices)}")
            _, extracted_entries = find_arpeggio_table_in_memory(
                data.c64_data,
                data.load_address,
                arp_indices
            )
            if extracted_entries:
                arp_entries = build_sf2_arp_table(extracted_entries)
                logger.info(f"    Extracted {len(extracted_entries)} arpeggio patterns")
            else:
                # Use defaults
                arp_entries = [
                    (0x00, 0x04, 0x07, 0x7F),  # Major chord
                    (0x00, 0x03, 0x07, 0x7F),  # Minor chord
                    (0x00, 0x0C, 0x7F, 0x00),  # Octave
                ]
                logger.debug("    No arpeggio table found, using defaults")
        else:
            # No arpeggios used, use defaults
            arp_entries = [
                (0x00, 0x04, 0x07, 0x7F),  # Major chord
                (0x00, 0x03, 0x07, 0x7F),  # Minor chord
                (0x00, 0x0C, 0x7F, 0x00),  # Octave
            ]
            logger.debug("    No arpeggio commands in sequences, using defaults")
    else:
        # Default arpeggio patterns
        arp_entries = [
            (0x00, 0x04, 0x07, 0x7F),  # Major chord
            (0x00, 0x03, 0x07, 0x7F),  # Minor chord
            (0x00, 0x0C, 0x7F, 0x00),  # Octave
        ]
        logger.debug("    Using default arpeggio patterns")

    base_offset = _addr_to_offset(arp_addr, load_address)

    for col in range(min(columns, 4)):
        for i, entry in enumerate(arp_entries):
            if i < rows:
                offset = base_offset + (col * rows) + i
                if offset < len(output) and col < len(entry):
                    output[offset] = entry[col]

    logger.info(f"    Written {len(arp_entries)} Arp table entries")

def inject_wave_table(output: bytearray, data, driver_info, load_address: int) -> None:
    """Inject wave table data extracted from Laxity SID"""
    logger.info("  Injecting wave table...")

    if 'Wave' not in driver_info.table_addresses:
        logger.debug("    Warning: No wave table found in driver")
        return

    wave_table = driver_info.table_addresses['Wave']
    wave_addr = wave_table['addr']
    columns = wave_table['columns']
    rows = wave_table['rows']

    logger.info(f"    Wave table address: ${wave_addr:04X}, columns={columns}, rows={rows}")
    logger.info(f"    Extracting from c64_data (len={len(data.c64_data)}), load_address=${data.load_address:04X}")
    logger.info(f"    First 16 bytes of c64_data: {data.c64_data[:16].hex(' ').upper()}")

    extracted_waves = extract_laxity_wave_table(data.c64_data, data.load_address)

    if extracted_waves:
        wave_data = extracted_waves
        logger.info(f"    Extracted {len(extracted_waves)} wave entries from SID")
        logger.info(f"    First 5 entries: {extracted_waves[:5]}")
    else:
        # Default: (col0, col1) = (waveform, note) or (0x7F, target)
        wave_data = [
            (0x41, 0x00), (0x7F, 0x00),  # Pulse, jump to 0
            (0x21, 0x00), (0x7F, 0x02),  # Saw, jump to 2
            (0x11, 0x00), (0x7F, 0x04),  # Tri, jump to 4
            (0x81, 0x00), (0x7F, 0x06),  # Noise, jump to 6
        ]

    if hasattr(data, 'siddump_data') and data.siddump_data:
        siddump_waveforms = set(data.siddump_data['waveforms'])
        # Waveform is in column 0 (first element), except for $7F jump commands
        existing_waveforms = set(col0 for col0, _ in wave_data if col0 != 0x7F)
        missing = siddump_waveforms - existing_waveforms
        missing = {wf for wf in missing
                  if (wf | 0x01) not in existing_waveforms
                  and wf not in (0x01, 0x09, 0xF0)}
        if missing:
            logger.debug(f"    Validation: {len(missing)} waveforms from siddump not in wave table")

    base_offset = _addr_to_offset(wave_addr, load_address)

    logger.info(f"    Base offset: ${base_offset:04X} ({base_offset}), load_addr=${load_address:04X}")

    # SF2 wave table format is column-major storage:
    # Bytes 0-255 (Column 0): Waveforms ($11=tri, $21=saw, $41=pulse, $81=noise) or $7F for jump
    # Bytes 256-511 (Column 1): Note offsets
    # Extraction returns (waveform, note) tuples - write waveforms first, then notes

    # Write Column 0: Waveforms (bytes 0-255)
    logger.info(f"    Writing waveforms: rows={rows}, base_offset=${base_offset:04X}, file_size={len(output)}, wave_data_len={len(wave_data)}")
    waveforms_written = 0
    for i, (waveform, note) in enumerate(wave_data):
        if i < rows and base_offset + i < len(output):
            old_val = output[base_offset + i]  # Capture old value
            output[base_offset + i] = waveform
            waveforms_written += 1
            if i < 3:  # Log first 3 for debugging
                logger.info(f"      [{i}] Wrote waveform ${waveform:02X} at offset ${base_offset+i:04X} (was ${old_val:02X})")
        elif i < rows:
            logger.warning(f"    Skipping wave entry {i}: offset ${base_offset+i:04X} out of bounds (file size {len(output)})")
    logger.info(f"    Wrote {waveforms_written} waveforms")

    # Write Column 1: Note offsets (bytes 256-511)
    note_offset = base_offset + rows
    logger.debug(f"    Writing notes: note_offset=${note_offset:04X}")
    notes_written = 0
    for i, (waveform, note) in enumerate(wave_data):
        if i < rows and note_offset + i < len(output):
            output[note_offset + i] = note
            notes_written += 1
            if i < 5:  # Log first 5 for debugging
                logger.debug(f"      [{i}] Writing note ${note:02X} at offset ${note_offset+i:04X}")
    logger.debug(f"    Wrote {notes_written} note offsets")

    logger.info(f"    Written {len(wave_data)} wave table entries (column-major: waveforms first, then notes)")



# ---------------------------------------------------------------------------
# v3.5.53 Phase 18 additions:
#   - inject_music_data_into_template: top-level dispatcher that parses
#     the SF2 header, pre-allocates the buffer, and invokes all 11
#     section injectors in the correct order. Mirrors the legacy
#     driver11-template path's `_inject_music_data_into_template`.
#   - print_extraction_summary: debug-log dump of extracted sequence /
#     instrument / orderlist / command counts.
# Both functions consume only (output, data, driver_info) state.
# ---------------------------------------------------------------------------


def print_extraction_summary(data) -> None:
    """Log a summary of extracted sequences / instruments / orderlists /
    commands used. Pure read-only diagnostic.
    """
    if data.sequences:
        logger.debug(f"\n  Extracted {len(data.sequences)} sequences:")
        for i, seq in enumerate(data.sequences[:5]):
            logger.debug(f"    Sequence {i}: {len(seq)} events")
        if len(data.sequences) > 5:
            logger.debug(f"    ... and {len(data.sequences) - 5} more")

    if data.instruments:
        logger.debug(f"\n  Extracted {len(data.instruments)} instruments")

    if data.orderlists:
        logger.debug(f"\n  Created {len(data.orderlists)} orderlists")

    if hasattr(data, 'raw_sequences') and data.raw_sequences:
        cmd_analysis = analyze_sequence_commands(data.raw_sequences)
        if cmd_analysis['commands_used']:
            logger.debug(f"\n  Commands used in sequences:")
            cmd_names = get_command_names()
            for cmd in sorted(cmd_analysis['commands_used']):
                count = cmd_analysis['command_counts'].get(cmd, 0)
                name = cmd_names[cmd] if cmd < len(cmd_names) else f"Cmd {cmd}"
                logger.debug(f"    {cmd:2d}: {name} ({count}x)")


def inject_music_data_into_template(
    output: bytearray,
    data,
    driver_info,
) -> Optional[int]:
    """Top-level driver11 template-path dispatcher.

    Parses the SF2 header from `output` (populating `driver_info`),
    pre-allocates the buffer for sequences + orderlists, then invokes
    each section injector in the correct order:

        instruments -> sequences -> orderlists -> wave -> pulse ->
        filter -> hr -> init -> tempo -> arp -> commands

    Args:
        output: SF2 PRG buffer (mutated in place — pre-allocated +
            section data written by the inject functions).
        data: ExtractedData providing instruments / sequences /
            orderlists / raw_sequences / c64_data / load_address.
        driver_info: SF2DriverInfo (mutated by sf2_parser.parse_sf2_blocks).

    Returns:
        The PRG load address on success, or None if the SF2 header
        couldn't be parsed.
    """
    logger.info("Injecting music data into template...")
    logger.debug(f"Template size: {len(output)} bytes")

    load_address = sf2_parser.parse_sf2_blocks(output, driver_info)
    if load_address is None:
        logger.warning(" Could not parse SF2 header, using fallback")
        print_extraction_summary(data)
        return None

    # PACKED MODE: pre-allocate enough space for sequences + orderlists
    # so the inject calls don't overrun the buffer.
    sequence_space = sum(len(seq) * 4 for seq in (data.sequences or [])) + 2048
    orderlist_space = sum(len(ol) * 2 for ol in (data.orderlists or [])) + 1024
    required_size = _addr_to_offset(driver_info.sequence_start, load_address) + sequence_space + orderlist_space
    if len(output) < required_size:
        logger.debug(
            f"  Pre-allocating buffer: {required_size} bytes "
            f"(sequences: {sequence_space}, orderlists: {orderlist_space})"
        )
        output.extend(bytearray(required_size - len(output)))

    if data.instruments or data.raw_sequences:
        inject_instruments(output, data, driver_info, load_address)

    if data.sequences and driver_info.sequence_start:
        inject_sequences(output, data, driver_info, load_address)

    if data.orderlists and driver_info.orderlist_start:
        inject_orderlists(output, data, driver_info, load_address)

    inject_wave_table(output, data, driver_info, load_address)
    inject_pulse_table(output, data, driver_info, load_address)
    inject_filter_table(output, data, driver_info, load_address)
    inject_hr_table(output, data, driver_info, load_address)
    inject_init_table(output, data, driver_info, load_address)
    inject_tempo_table(output, data, driver_info, load_address)
    inject_arp_table(output, data, driver_info, load_address)
    inject_commands(output, data, driver_info, load_address)

    print_extraction_summary(data)
    return load_address
