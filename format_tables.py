#!/usr/bin/env python3
"""Format music data tables in hex dump format for easy comparison."""

import struct
from pathlib import Path


def format_hex_table(data, columns=16, bytes_per_entry=1, name="Table", start_addr=None, end_addr=None, size=None):
    """
    Format binary data as a hex table with 16 bytes per row.

    Args:
        data: Binary data to format
        columns: Number of bytes to display per row (default: 16)
        bytes_per_entry: Bytes per entry (1 for simple display)
        name: Table name for header
        start_addr: Start address in memory (hex)
        end_addr: End address in memory (hex)
        size: Size in bytes
    """
    lines = []
    lines.append(f"\n{name}")
    if start_addr is not None and end_addr is not None:
        lines.append(f"Start: ${start_addr:04X}  End: ${end_addr:04X}  Size: {size if size else end_addr - start_addr} bytes")
    lines.append("=" * 80)

    if not data or len(data) == 0:
        lines.append("(empty)")
        return "\n".join(lines)

    # Display 16 bytes per row
    bytes_per_row = 16
    total_bytes = len(data)
    rows = (total_bytes + bytes_per_row - 1) // bytes_per_row

    for row in range(rows):
        row_offset = row * bytes_per_row
        row_label = f"{row_offset:02x}:"
        hex_parts = []

        for col in range(bytes_per_row):
            byte_offset = row_offset + col

            if byte_offset < len(data):
                hex_parts.append(f"{data[byte_offset]:02x}")
            else:
                hex_parts.append("  ")

        # Join bytes with spaces
        hex_line = " ".join(hex_parts)
        lines.append(f"{row_label} {hex_line}")

    return "\n".join(lines)


def format_commands_table(data, columns=4):
    """Format commands table (3 bytes per command)."""
    return format_hex_table(data, columns=columns, bytes_per_entry=3, name="Commands")


def format_instruments_table(data, columns=6, layout='column'):
    """
    Format instruments table.
    Driver 11: 6 bytes per instrument, column-major (32 instruments)
    """
    lines = []
    lines.append("\nInstruments")
    lines.append("=" * 80)

    if not data or len(data) == 0:
        lines.append("(empty)")
        return "\n".join(lines)

    if layout == 'column':
        # Column-major: 6 rows × 32 columns
        # But display as rows of instruments
        num_instruments = 32
        bytes_per_row = 6

        for row in range(16):  # Show 16 rows
            row_label = f"{row:02x}:"
            hex_parts = []

            for col in range(columns):
                instr_idx = row + col * 16
                if instr_idx < num_instruments:
                    # Extract 6 bytes for this instrument
                    instr_bytes = []
                    for byte_row in range(bytes_per_row):
                        byte_offset = byte_row * num_instruments + instr_idx
                        if byte_offset < len(data):
                            instr_bytes.append(data[byte_offset])
                        else:
                            instr_bytes.append(0)
                    hex_str = " ".join(f"{b:02x}" for b in instr_bytes)
                    hex_parts.append(hex_str)
                else:
                    hex_parts.append("  " * bytes_per_row)

            lines.append(f"{row_label} {' '.join(hex_parts)}")

    return "\n".join(lines)


def format_wave_table(data, columns=8):
    """Format wave table (2 bytes per entry: waveform, note)."""
    return format_hex_table(data, columns=columns, bytes_per_entry=2, name="Wave")


def format_pulse_table(data, columns=4):
    """Format pulse table (3 bytes per entry in SF2, 4 in Laxity)."""
    # Try to detect format - SF2 uses 3 bytes, Laxity uses 4
    if len(data) % 4 == 0 and len(data) % 3 != 0:
        return format_hex_table(data, columns=columns, bytes_per_entry=4, name="Pulse")
    else:
        return format_hex_table(data, columns=columns, bytes_per_entry=3, name="Pulse")


def format_filter_table(data, columns=4):
    """Format filter table (3 bytes per entry)."""
    return format_hex_table(data, columns=columns, bytes_per_entry=3, name="Filter")


def format_arp_table(data, columns=8):
    """Format arpeggio table (typically 4 bytes per entry)."""
    return format_hex_table(data, columns=columns, bytes_per_entry=4, name="Arp")


def format_tempo_table(data, columns=8):
    """Format tempo table (1 byte per entry)."""
    return format_hex_table(data, columns=columns, bytes_per_entry=1, name="Tempo")


def format_hr_table(data, columns=8):
    """Format hard restart table (2 bytes per entry: AD, SR)."""
    return format_hex_table(data, columns=columns, bytes_per_entry=2, name="HR")


def format_init_table(data, columns=8):
    """Format init table (2 bytes: tempo row, volume)."""
    return format_hex_table(data, columns=columns, bytes_per_entry=2, name="Init")


def format_sequences(sequences, max_rows=32):
    """Format sequence data."""
    lines = []
    lines.append("\nSequences")
    lines.append("=" * 80)

    if not sequences or len(sequences) == 0:
        lines.append("(empty)")
        return "\n".join(lines)

    for seq_idx, seq_data in enumerate(sequences):
        lines.append(f"\nSequence {seq_idx}:")
        lines.append("-" * 40)

        if isinstance(seq_data, (list, tuple)):
            # Format as rows
            for row in range(min(max_rows, len(seq_data))):
                if row < len(seq_data):
                    event = seq_data[row]
                    if isinstance(event, dict):
                        instr = event.get('instrument', 0x80)
                        cmd = event.get('command', 0x80)
                        note = event.get('note', 0)
                        lines.append(f"{row:03d}: I:{instr:02x} C:{cmd:02x} N:{note:02x}")
                    else:
                        lines.append(f"{row:03d}: {event}")

            if len(seq_data) > max_rows:
                lines.append(f"... ({len(seq_data) - max_rows} more rows)")
        else:
            lines.append(f"(binary data, {len(seq_data)} bytes)")

    return "\n".join(lines)


def extract_sf2_tables(sf2_file):
    """Extract tables from SF2 file for display."""
    with open(sf2_file, 'rb') as f:
        data = f.read()

    # These offsets are for Driver 11
    tables = {}

    # Commands: $1844, 3 bytes × 64 entries = 192 bytes
    tables['commands'] = {
        'data': data[0x1844:0x1844 + 192],
        'start': 0x1844,
        'end': 0x1844 + 192,
        'size': 192
    }

    # Instruments: $1784, 6 bytes × 32 entries (column-major) = 192 bytes
    tables['instruments'] = {
        'data': data[0x1784:0x1784 + 192],
        'start': 0x1784,
        'end': 0x1784 + 192,
        'size': 192
    }

    # Wave: $1924, 2 bytes × 256 entries = 512 bytes
    tables['wave'] = {
        'data': data[0x1924:0x1924 + 512],
        'start': 0x1924,
        'end': 0x1924 + 512,
        'size': 512
    }

    # Pulse: $1B24, 3 bytes × 256 entries = 768 bytes
    tables['pulse'] = {
        'data': data[0x1B24:0x1B24 + 768],
        'start': 0x1B24,
        'end': 0x1B24 + 768,
        'size': 768
    }

    # Filter: $1E24, 3 bytes × 256 entries = 768 bytes
    tables['filter'] = {
        'data': data[0x1E24:0x1E24 + 768],
        'start': 0x1E24,
        'end': 0x1E24 + 768,
        'size': 768
    }

    # Arp: $2124, 1 byte × 256 entries = 256 bytes (actually 4-byte groups)
    tables['arp'] = {
        'data': data[0x2124:0x2124 + 256],
        'start': 0x2124,
        'end': 0x2124 + 256,
        'size': 256
    }

    # Tempo: $2224, 1 byte × 256 entries = 256 bytes
    tables['tempo'] = {
        'data': data[0x2224:0x2224 + 256],
        'start': 0x2224,
        'end': 0x2224 + 256,
        'size': 256
    }

    # HR: Usually at $1684, 2 bytes per entry
    tables['hr'] = {
        'data': data[0x1684:0x1684 + 32],
        'start': 0x1684,
        'end': 0x1684 + 32,
        'size': 32
    }

    # Init: Usually at $1664, 2 bytes
    tables['init'] = {
        'data': data[0x1664:0x1664 + 2],
        'start': 0x1664,
        'end': 0x1664 + 2,
        'size': 2
    }

    return tables


def extract_sid_tables(sid_file):
    """Extract tables from original SID file for display."""
    with open(sid_file, 'rb') as f:
        data = f.read()

    # Parse PSID header
    header_size = 0x7C
    load_addr_offset = struct.unpack('>H', data[8:10])[0]
    if load_addr_offset == 0:
        load_addr = struct.unpack('<H', data[header_size:header_size+2])[0]
    else:
        load_addr = load_addr_offset

    music_data = data[header_size:]

    tables = {}

    # Standard Laxity offsets (Stinsens layout)
    # Wave table (notes): $1914 - $1000 = $0914
    wave_offset = 0x0914
    wave_size = 64
    if wave_offset + wave_size <= len(music_data):
        tables['wave'] = {
            'data': music_data[wave_offset:wave_offset + wave_size],
            'start': load_addr + wave_offset,
            'end': load_addr + wave_offset + wave_size,
            'size': wave_size
        }

    # Instruments: $1A6B - $1000 = $0A6B
    instr_offset = 0x0A6B
    instr_size = 64
    if instr_offset + instr_size <= len(music_data):
        tables['instruments'] = {
            'data': music_data[instr_offset:instr_offset + instr_size],
            'start': load_addr + instr_offset,
            'end': load_addr + instr_offset + instr_size,
            'size': instr_size
        }

    # Pulse: $1A3B - $1000 = $0A3B
    pulse_offset = 0x0A3B
    pulse_size = 64
    if pulse_offset + pulse_size <= len(music_data):
        tables['pulse'] = {
            'data': music_data[pulse_offset:pulse_offset + pulse_size],
            'start': load_addr + pulse_offset,
            'end': load_addr + pulse_offset + pulse_size,
            'size': pulse_size
        }

    # Filter: $1A1E - $1000 = $0A1E
    filter_offset = 0x0A1E
    filter_size = 48
    if filter_offset + filter_size <= len(music_data):
        tables['filter'] = {
            'data': music_data[filter_offset:filter_offset + filter_size],
            'start': load_addr + filter_offset,
            'end': load_addr + filter_offset + filter_size,
            'size': filter_size
        }

    # Arp: $1A8B - $1000 = $0A8B
    arp_offset = 0x0A8B
    arp_size = 64
    if arp_offset + arp_size <= len(music_data):
        tables['arp'] = {
            'data': music_data[arp_offset:arp_offset + arp_size],
            'start': load_addr + arp_offset,
            'end': load_addr + arp_offset + arp_size,
            'size': arp_size
        }

    # Commands: $1ADB - $1000 = $0ADB
    cmd_offset = 0x0ADB
    cmd_size = 192
    if cmd_offset + cmd_size <= len(music_data):
        tables['commands'] = {
            'data': music_data[cmd_offset:cmd_offset + cmd_size],
            'start': load_addr + cmd_offset,
            'end': load_addr + cmd_offset + cmd_size,
            'size': cmd_size
        }

    return tables


def generate_formatted_tables(sid_file, sf2_file):
    """Generate formatted table output for both SID and SF2."""
    lines = []

    lines.append("\n" + "=" * 80)
    lines.append("ORIGINAL SID DATA TABLES (HEX VIEW)")
    lines.append("=" * 80)

    sid_tables = extract_sid_tables(sid_file)

    if 'commands' in sid_tables:
        t = sid_tables['commands']
        lines.append(format_hex_table(t['data'], name="Commands",
                                     start_addr=t['start'], end_addr=t['end'], size=t['size']))
    if 'instruments' in sid_tables:
        t = sid_tables['instruments']
        lines.append(format_hex_table(t['data'], name="Instruments",
                                     start_addr=t['start'], end_addr=t['end'], size=t['size']))
    if 'wave' in sid_tables:
        t = sid_tables['wave']
        lines.append(format_hex_table(t['data'], name="Wave",
                                     start_addr=t['start'], end_addr=t['end'], size=t['size']))
    if 'pulse' in sid_tables:
        t = sid_tables['pulse']
        lines.append(format_hex_table(t['data'], name="Pulse",
                                     start_addr=t['start'], end_addr=t['end'], size=t['size']))
    if 'filter' in sid_tables:
        t = sid_tables['filter']
        lines.append(format_hex_table(t['data'], name="Filter",
                                     start_addr=t['start'], end_addr=t['end'], size=t['size']))
    if 'arp' in sid_tables:
        t = sid_tables['arp']
        lines.append(format_hex_table(t['data'], name="Arp",
                                     start_addr=t['start'], end_addr=t['end'], size=t['size']))

    lines.append("\n" + "=" * 80)
    lines.append("CONVERTED SF2 DATA TABLES (HEX VIEW)")
    lines.append("=" * 80)

    sf2_tables = extract_sf2_tables(sf2_file)

    # Commands
    t = sf2_tables['commands']
    lines.append(format_hex_table(t['data'], name="Commands",
                                 start_addr=t['start'], end_addr=t['end'], size=t['size']))

    # Instruments
    t = sf2_tables['instruments']
    lines.append(format_hex_table(t['data'], name="Instruments",
                                 start_addr=t['start'], end_addr=t['end'], size=t['size']))

    # Wave
    t = sf2_tables['wave']
    lines.append(format_hex_table(t['data'], name="Wave",
                                 start_addr=t['start'], end_addr=t['end'], size=t['size']))

    # Pulse
    t = sf2_tables['pulse']
    lines.append(format_hex_table(t['data'], name="Pulse",
                                 start_addr=t['start'], end_addr=t['end'], size=t['size']))

    # Filter
    t = sf2_tables['filter']
    lines.append(format_hex_table(t['data'], name="Filter",
                                 start_addr=t['start'], end_addr=t['end'], size=t['size']))

    # Arp
    t = sf2_tables['arp']
    lines.append(format_hex_table(t['data'], name="Arp",
                                 start_addr=t['start'], end_addr=t['end'], size=t['size']))

    # Tempo
    t = sf2_tables['tempo']
    lines.append(format_hex_table(t['data'], name="Tempo",
                                 start_addr=t['start'], end_addr=t['end'], size=t['size']))

    # HR
    t = sf2_tables['hr']
    lines.append(format_hex_table(t['data'], name="HR",
                                 start_addr=t['start'], end_addr=t['end'], size=t['size']))

    # Init
    t = sf2_tables['init']
    lines.append(format_hex_table(t['data'], name="Init",
                                 start_addr=t['start'], end_addr=t['end'], size=t['size']))

    return "\n".join(lines)


def main():
    import sys

    if len(sys.argv) < 3:
        print("Usage: python format_tables.py <sid_file> <sf2_file>")
        sys.exit(1)

    sid_file = sys.argv[1]
    sf2_file = sys.argv[2]

    output = generate_formatted_tables(sid_file, sf2_file)
    print(output)


if __name__ == '__main__':
    main()
