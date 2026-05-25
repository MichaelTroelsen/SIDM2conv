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
