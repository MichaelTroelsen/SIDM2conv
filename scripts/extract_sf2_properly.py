#!/usr/bin/env python3
"""
Proper SF2 extraction - preserves original structure, only replaces tables we can extract.
"""

import struct
from pathlib import Path


def extract_sf2_packed_wave_2col(sf2_packed_raw, packed_load):
    """
    Extract 2-column wave data from SF2-packed SID.
    Columns are stored consecutively at $0958: col0 (waveform), col1 (note_offset).

    Args:
        sf2_packed_raw: Full raw file data (including PSID header)
        packed_load: Load address from PSID header

    Returns: 2-column Driver 11 format (512 bytes)
    """
    # SF2-packed wave table is at file offset $0958 (absolute)
    # This is in the PSID header area, not relative to load address
    file_offset = 0x0958
    col_size = 50  # 50 entries per column

    # Extract 2 consecutive columns from raw file
    col0 = sf2_packed_raw[file_offset:file_offset + col_size]
    col1 = sf2_packed_raw[file_offset + col_size:file_offset + 2*col_size]

    # Convert to 2-column Driver 11 format (256 rows × 2 columns, column-major)
    wave_2col = bytearray(256 * 2)  # 512 bytes, initialized to 0

    # Copy the 2 columns to Driver 11 format
    for i in range(col_size):
        wave_2col[i] = col0[i]         # Column 0: Waveform
        wave_2col[256 + i] = col1[i]   # Column 1: Note offset

    return bytes(wave_2col)


def extract_sf2_packed_pulse_3col(sf2_packed_raw, packed_load):
    """
    Extract 3-column pulse data from SF2-packed SID.
    Columns are stored consecutively at $09BC: col0, col1, col2.

    Args:
        sf2_packed_raw: Full raw file data (including PSID header)
        packed_load: Load address from PSID header

    Returns: 4-column Driver 11 format (1024 bytes)
    """
    # SF2-packed pulse table is at file offset $09BC (absolute)
    # This is in the PSID header area, not relative to load address
    file_offset = 0x09BC
    col_size = 25

    # Extract 3 consecutive columns from raw file
    col0 = sf2_packed_raw[file_offset:file_offset + col_size]
    col1 = sf2_packed_raw[file_offset + col_size:file_offset + 2*col_size]
    col2 = sf2_packed_raw[file_offset + 2*col_size:file_offset + 3*col_size]

    # Convert to 4-column Driver 11 format (256 rows × 4 columns, column-major)
    pulse_4col = bytearray(256 * 4)  # 1024 bytes, initialized to 0

    # Copy the 3 columns to the first 3 columns of Driver 11 format
    for i in range(col_size):
        pulse_4col[i] = col0[i]              # Column 0: Value
        pulse_4col[256 + i] = col1[i]        # Column 1: Delta
        pulse_4col[512 + i] = col2[i]        # Column 2: Duration
        # Column 3 (Next) remains 0

    return bytes(pulse_4col)


def extract_sf2_packed_filter_3col(sf2_packed_raw, packed_load):
    """
    Extract 3-column filter data from SF2-packed SID.
    Columns are stored consecutively at $0A07: col0, col1, col2.

    Args:
        sf2_packed_raw: Full raw file data (including PSID header)
        packed_load: Load address from PSID header

    Returns: 4-column Driver 11 format (1024 bytes)
    """
    # SF2-packed filter table is at file offset $0A07 (absolute)
    # This is in the PSID header area, not relative to load address
    file_offset = 0x0A07
    col_spacing = 26  # 26 bytes ($1A) between column starts
    col_size = 26     # 26 bytes ($1A) per column

    # Extract 3 consecutive columns from raw file
    col0 = sf2_packed_raw[file_offset:file_offset + col_size]
    col1 = sf2_packed_raw[file_offset + col_spacing:file_offset + col_spacing + col_size]
    col2 = sf2_packed_raw[file_offset + 2*col_spacing:file_offset + 2*col_spacing + col_size]

    # Convert to 4-column Driver 11 format (256 rows × 4 columns, column-major)
    filter_4col = bytearray(256 * 4)  # 1024 bytes, initialized to 0

    # Copy the 3 columns to the first 3 columns of Driver 11 format
    for i in range(col_size):
        filter_4col[i] = col0[i]              # Column 0
        filter_4col[256 + i] = col1[i]        # Column 1
        filter_4col[512 + i] = col2[i]        # Column 2
        # Column 3 remains 0

    return bytes(filter_4col)


def extract_sf2_packed_arpeggio_1col(sf2_packed_raw, packed_load):
    """
    Extract 1-column arpeggio data from SF2-packed SID.
    Data is stored at $0A55 with 66 bytes ($42).

    Args:
        sf2_packed_raw: Full raw file data (including PSID header)
        packed_load: Load address from PSID header

    Returns: 1-column Driver 11 format (256 bytes)
    """
    # SF2-packed arpeggio table is at file offset $0A55 (absolute)
    # This is in the PSID header area, not relative to load address
    file_offset = 0x0A55
    col_size = 0x42  # 66 bytes

    # Extract arpeggio data from raw file
    arp_data = sf2_packed_raw[file_offset:file_offset + col_size]

    # Convert to 1-column Driver 11 format (256 rows, column-major)
    arp_1col = bytearray(256)  # 256 bytes, initialized to 0

    # Copy the data to Driver 11 format
    for i in range(col_size):
        arp_1col[i] = arp_data[i]

    return bytes(arp_1col)


def extract_sf2_packed_tempo_1col(sf2_packed_raw, packed_load):
    """
    Extract 1-column tempo data from SF2-packed SID.
    Data is stored at $0A97 with 4 bytes.

    Args:
        sf2_packed_raw: Full raw file data (including PSID header)
        packed_load: Load address from PSID header

    Returns: 1-column Driver 11 format (256 bytes)
    """
    # SF2-packed tempo table is at file offset $0A97 (absolute)
    # This is in the PSID header area, not relative to load address
    file_offset = 0x0A97
    col_size = 4  # 4 bytes

    # Extract tempo data from raw file
    tempo_data = sf2_packed_raw[file_offset:file_offset + col_size]

    # Convert to 1-column Driver 11 format (256 rows, column-major)
    tempo_1col = bytearray(256)  # 256 bytes, initialized to 0

    # Copy the data to Driver 11 format
    for i in range(col_size):
        tempo_1col[i] = tempo_data[i]

    return bytes(tempo_1col)


def extract_sf2_packed_commands_3col(sf2_packed_raw, packed_load):
    """
    Extract 3-column commands data from SF2-packed SID.
    Columns are stored consecutively at $08F3: col0, col1, col2.

    Args:
        sf2_packed_raw: Full raw file data (including PSID header)
        packed_load: Load address from PSID header

    Returns: 3-column Driver 11 format (192 bytes)
    """
    # SF2-packed commands table is at file offset $08F3 (absolute)
    # This is in the PSID header area, not relative to load address
    file_offset = 0x08F3
    col_spacing = 33  # 33 bytes ($21) between column starts
    col_size = 33     # 33 bytes per column (same as spacing)

    # Extract 3 consecutive columns from raw file
    col0 = sf2_packed_raw[file_offset:file_offset + col_size]
    col1 = sf2_packed_raw[file_offset + col_spacing:file_offset + col_spacing + col_size]
    col2 = sf2_packed_raw[file_offset + 2*col_spacing:file_offset + 2*col_spacing + col_size]

    # Convert to 3-column Driver 11 format (64 rows × 3 columns, column-major)
    # Driver 11 Commands table: 192 bytes total (64 rows × 3 columns)
    commands_3col = bytearray(192)  # 192 bytes, initialized to 0

    # Copy the 3 columns to Driver 11 format
    for i in range(col_size):
        commands_3col[i] = col0[i]         # Column 0
        commands_3col[64 + i] = col1[i]    # Column 1
        commands_3col[128 + i] = col2[i]   # Column 2

    return bytes(commands_3col)


def extract_sf2_packed_instruments_6col(sf2_packed_raw, packed_load):
    """
    Extract 6-column instruments data from SF2-packed SID.
    Columns are stored consecutively at $087B: col0, col1, col2, col3, col4, col5.

    Args:
        sf2_packed_raw: Full raw file data (including PSID header)
        packed_load: Load address from PSID header

    Returns: 6-column Driver 11 format (192 bytes)
    """
    # SF2-packed instruments table is at file offset $087B (absolute)
    # This is in the PSID header area, not relative to load address
    file_offset = 0x087B
    col_spacing = 20  # 20 bytes ($14) between column starts
    col_size = 20     # 20 bytes ($14) per column

    # Extract 6 consecutive columns from raw file
    col0 = sf2_packed_raw[file_offset:file_offset + col_size]
    col1 = sf2_packed_raw[file_offset + col_spacing:file_offset + col_spacing + col_size]
    col2 = sf2_packed_raw[file_offset + 2*col_spacing:file_offset + 2*col_spacing + col_size]
    col3 = sf2_packed_raw[file_offset + 3*col_spacing:file_offset + 3*col_spacing + col_size]
    col4 = sf2_packed_raw[file_offset + 4*col_spacing:file_offset + 4*col_spacing + col_size]
    col5 = sf2_packed_raw[file_offset + 5*col_spacing:file_offset + 5*col_spacing + col_size]

    # Convert to 6-column Driver 11 format (32 rows × 6 columns, column-major)
    # Driver 11 Instruments table: 192 bytes total (32 rows × 6 columns)
    instruments_6col = bytearray(192)  # 192 bytes, initialized to 0

    # Copy the 6 columns to Driver 11 format (first 20 rows of each column)
    for i in range(col_size):
        instruments_6col[i] = col0[i]         # Column 0
        instruments_6col[32 + i] = col1[i]    # Column 1
        instruments_6col[64 + i] = col2[i]    # Column 2
        instruments_6col[96 + i] = col3[i]    # Column 3
        instruments_6col[128 + i] = col4[i]   # Column 4
        instruments_6col[160 + i] = col5[i]   # Column 5

    return bytes(instruments_6col)


def extract_sf2_properly(packed_sid_path, original_sf2_path, output_path):
    """Extract SF2 by using original structure and injecting extracted tables."""

    # Read packed SID
    with open(packed_sid_path, 'rb') as f:
        packed_raw = f.read()

    # Read original SF2 (for structure reference only)
    with open(original_sf2_path, 'rb') as f:
        original_data = bytearray(f.read())

    # Parse packed SID
    packed_load = struct.unpack('>H', packed_raw[8:10])[0]
    packed_init = struct.unpack('>H', packed_raw[10:12])[0]
    packed_play = struct.unpack('>H', packed_raw[12:14])[0]

    if packed_load == 0:
        packed_load = struct.unpack('<H', packed_raw[0x7C:0x7C+2])[0]
        packed_music = packed_raw[0x7E:]
    else:
        packed_music = packed_raw[0x7C:]

    # Parse original SF2
    orig_load = struct.unpack('<H', original_data[0:2])[0]

    print(f'Packed SID: load=${packed_load:04X}, init=${packed_init:04X}, play=${packed_play:04X}')
    print(f'Original SF2: load=${orig_load:04X}, size={len(original_data):,}')
    print()

    # Tables at absolute addresses (Driver 11 format)
    tables = [
        ('Instruments', 0x1784, 192),   # 6 columns × 32 rows
        ('Commands', 0x1844, 192),      # 3 columns × 64 rows
        ('Wave', 0x1924, 512),          # 2 columns × 256 rows
        ('Pulse', 0x1B24, 1024),        # 4 columns × 256 rows
        ('Filter', 0x1E24, 1024),       # 4 columns × 256 rows
        ('Arpeggio', 0x2124, 256),      # 1 column × 256 rows
        ('Tempo', 0x2224, 256),         # 1 column × 256 rows
    ]

    print('Extracting tables from packed SID and injecting into original structure:')
    print()

    # For each table, extract from packed SID and inject into original structure
    for name, addr, size in tables:
        # Special handling for Instruments table - use 6-column extraction
        if name == 'Instruments' and packed_load == 0x1000:
            try:
                table_data = extract_sf2_packed_instruments_6col(packed_raw, packed_load)
                print(f'{name:<15} ${addr:04X}: extracted from 6 consecutive columns at $087B')
            except Exception as e:
                print(f'{name:<15} ${addr:04X}: ERROR in 6-column extraction: {e}')
                # Fall back to standard extraction
                packed_offset = addr - packed_load
                table_data = packed_music[packed_offset:packed_offset+size]
        # Special handling for Commands table - use 3-column extraction
        elif name == 'Commands' and packed_load == 0x1000:
            try:
                table_data = extract_sf2_packed_commands_3col(packed_raw, packed_load)
                print(f'{name:<15} ${addr:04X}: extracted from 3 consecutive columns at $08F3')
            except Exception as e:
                print(f'{name:<15} ${addr:04X}: ERROR in 3-column extraction: {e}')
                # Fall back to standard extraction
                packed_offset = addr - packed_load
                table_data = packed_music[packed_offset:packed_offset+size]
        # Special handling for Wave table - use 2-column extraction
        elif name == 'Wave' and packed_load == 0x1000:
            try:
                table_data = extract_sf2_packed_wave_2col(packed_raw, packed_load)
                print(f'{name:<15} ${addr:04X}: extracted from 2 consecutive columns at $0958')
            except Exception as e:
                print(f'{name:<15} ${addr:04X}: ERROR in 2-column extraction: {e}')
                # Fall back to standard extraction
                packed_offset = addr - packed_load
                table_data = packed_music[packed_offset:packed_offset+size]
        # Special handling for Pulse table - use 3-column extraction
        elif name == 'Pulse' and packed_load == 0x1000:
            try:
                table_data = extract_sf2_packed_pulse_3col(packed_raw, packed_load)
                print(f'{name:<15} ${addr:04X}: extracted from 3 consecutive columns at $09BC')
            except Exception as e:
                print(f'{name:<15} ${addr:04X}: ERROR in 3-column extraction: {e}')
                # Fall back to standard extraction
                packed_offset = addr - packed_load
                table_data = packed_music[packed_offset:packed_offset+size]
        # Special handling for Filter table - use 3-column extraction
        elif name == 'Filter' and packed_load == 0x1000:
            try:
                table_data = extract_sf2_packed_filter_3col(packed_raw, packed_load)
                print(f'{name:<15} ${addr:04X}: extracted from 3 consecutive columns at $0A07')
            except Exception as e:
                print(f'{name:<15} ${addr:04X}: ERROR in 3-column extraction: {e}')
                # Fall back to standard extraction
                packed_offset = addr - packed_load
                table_data = packed_music[packed_offset:packed_offset+size]
        # Special handling for Arpeggio table - use 1-column extraction
        elif name == 'Arpeggio' and packed_load == 0x1000:
            try:
                table_data = extract_sf2_packed_arpeggio_1col(packed_raw, packed_load)
                print(f'{name:<15} ${addr:04X}: extracted from 1 column at $0A55')
            except Exception as e:
                print(f'{name:<15} ${addr:04X}: ERROR in 1-column extraction: {e}')
                # Fall back to standard extraction
                packed_offset = addr - packed_load
                table_data = packed_music[packed_offset:packed_offset+size]
        # Special handling for Tempo table - use 1-column extraction
        elif name == 'Tempo' and packed_load == 0x1000:
            try:
                table_data = extract_sf2_packed_tempo_1col(packed_raw, packed_load)
                print(f'{name:<15} ${addr:04X}: extracted from 1 column at $0A97')
            except Exception as e:
                print(f'{name:<15} ${addr:04X}: ERROR in 1-column extraction: {e}')
                # Fall back to standard extraction
                packed_offset = addr - packed_load
                table_data = packed_music[packed_offset:packed_offset+size]
        else:
            # Standard extraction
            packed_offset = addr - packed_load
            table_data = packed_music[packed_offset:packed_offset+size]

        # Inject into original SF2 structure
        orig_offset = addr - orig_load + 2  # +2 for load address

        if orig_offset >= 0 and orig_offset + size <= len(original_data):
            # Verify it's the same data (skip for Instruments, Commands, Wave, Pulse, Filter, Arpeggio, Tempo since we're converting format)
            if (name not in ['Instruments', 'Commands', 'Wave', 'Pulse', 'Filter', 'Arpeggio', 'Tempo']) or packed_load != 0x1000:
                original_table = original_data[orig_offset:orig_offset+size]
                matches = sum(1 for i in range(size) if table_data[i] == original_table[i])
                match_pct = matches / size * 100
            else:
                matches = 0
                match_pct = 0.0

            # Inject
            original_data[orig_offset:orig_offset+size] = table_data

            if name == 'Wave' and packed_load == 0x1000:
                print(f'{name:<15} ${addr:04X}: 50 entries (2-column conversion) - injected')
            elif name == 'Pulse' and packed_load == 0x1000:
                print(f'{name:<15} ${addr:04X}: 25 entries (3->4 column conversion) - injected')
            elif name == 'Filter' and packed_load == 0x1000:
                print(f'{name:<15} ${addr:04X}: 26 entries (3->4 column conversion) - injected')
            elif name == 'Arpeggio' and packed_load == 0x1000:
                print(f'{name:<15} ${addr:04X}: 66 entries (1-column extraction) - injected')
            elif name == 'Tempo' and packed_load == 0x1000:
                print(f'{name:<15} ${addr:04X}: 4 entries (1-column extraction) - injected')
            elif name == 'Commands' and packed_load == 0x1000:
                print(f'{name:<15} ${addr:04X}: 33 entries (3-column extraction) - injected')
            elif name == 'Instruments' and packed_load == 0x1000:
                print(f'{name:<15} ${addr:04X}: 20 entries (6-column extraction) - injected')
            else:
                print(f'{name:<15} ${addr:04X}: {matches}/{size} ({match_pct:5.1f}%) - injected')
        else:
            print(f'{name:<15} ${addr:04X}: SKIP (out of bounds)')

    # Update DriverCommon structure with correct init/play addresses
    # DriverCommon is at fixed file offsets: 0x31-0x32 (init), 0x33-0x34 (play)
    # File offset = memory offset + 2 (for load address header)
    # Memory offset = address - load_address
    print()
    print('Updating DriverCommon with correct addresses:')

    # Calculate the actual init/play routines from the packed SID
    # The PSID header init/play are entry points, but DriverCommon needs the actual routine addresses
    # For SF2 Driver 11: entry stubs are at $1000 and $1003, pointing to actual routines

    # Read the JMP targets from the packed SID to get the actual routine addresses
    if len(packed_music) >= 6:
        # Check if there are JMP instructions at $1000 and $1003
        if packed_music[0] == 0x4C:  # JMP opcode at offset 0 ($1000)
            actual_init = struct.unpack('<H', packed_music[1:3])[0]
        else:
            actual_init = packed_init

        if packed_music[3] == 0x4C:  # JMP opcode at offset 3 ($1003)
            actual_play = struct.unpack('<H', packed_music[4:6])[0]
        else:
            actual_play = packed_play
    else:
        actual_init = packed_init
        actual_play = packed_play

    # Read old values before updating
    old_init = struct.unpack('<H', original_data[0x31:0x33])[0]
    old_play = struct.unpack('<H', original_data[0x33:0x35])[0]

    # Write to DriverCommon structure (file offset 0x31 and 0x33)
    # Init address at file offset 0x31 (little-endian)
    struct.pack_into('<H', original_data, 0x31, actual_init)
    # Play address at file offset 0x33 (little-endian)
    struct.pack_into('<H', original_data, 0x33, actual_play)

    print(f'  Init: ${actual_init:04X} (was ${old_init:04X})')
    print(f'  Play: ${actual_play:04X} (was ${old_play:04X})')

    # Write output
    with open(output_path, 'wb') as f:
        f.write(original_data)

    print()
    print(f'Created: {output_path}')
    print(f'Size: {len(original_data):,} bytes')

    return True


if __name__ == '__main__':
    import sys

    if len(sys.argv) != 4:
        print('Usage: python extract_sf2_properly.py <packed_sid> <original_sf2> <output_sf2>')
        sys.exit(1)

    extract_sf2_properly(sys.argv[1], sys.argv[2], sys.argv[3])
