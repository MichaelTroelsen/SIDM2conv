#!/usr/bin/env python3
"""Extract start and end addresses of music data structures from SID file."""

import sys
import struct
from pathlib import Path


def parse_psid_header(data):
    """Parse PSID header."""
    magic = data[0:4].decode('ascii', errors='ignore')
    version = struct.unpack('>H', data[4:6])[0]
    load_addr = struct.unpack('>H', data[8:10])[0]
    init_addr = struct.unpack('>H', data[10:12])[0]
    play_addr = struct.unpack('>H', data[12:14])[0]

    # If load_addr is 0, read from first two bytes of data
    header_size = 0x7C if version == 2 else 0x76
    if load_addr == 0:
        load_addr = struct.unpack('<H', data[header_size:header_size+2])[0]

    return {
        'magic': magic,
        'version': version,
        'load_addr': load_addr,
        'init_addr': init_addr,
        'play_addr': play_addr,
        'header_size': header_size
    }


def find_wave_table(data, load_addr):
    """Find wave table in data."""
    # Stinsens layout uses offset $0914 from load address
    offset = 0x0914
    if offset + 32 * 2 > len(data):
        return None

    # Check for valid wave entries
    valid_count = 0
    for i in range(32):
        note = data[offset + i]
        waveform = data[offset + 32 + i] if offset + 32 + i < len(data) else 0
        # Valid note range: 0-95, valid waveforms have certain bits
        if note <= 95 or note in [0x7F, 0x7E]:
            valid_count += 1

    if valid_count >= 20:  # At least 20 valid entries
        return {
            'note_addr': load_addr + offset,
            'wave_addr': load_addr + offset + 32,
            'count': 32
        }

    # Try Angular layout at offset $09E7
    offset = 0x09E7
    if offset + 32 * 2 > len(data):
        return None

    valid_count = 0
    for i in range(32):
        waveform = data[offset + i]
        note = data[offset + 32 + i] if offset + 32 + i < len(data) else 0
        if note <= 95 or note in [0x7F, 0x7E]:
            valid_count += 1

    if valid_count >= 20:
        return {
            'wave_addr': load_addr + offset,
            'note_addr': load_addr + offset + 32,
            'count': 32
        }

    return None


def extract_addresses(sid_file):
    """Extract all data structure addresses from SID file."""

    # Read SID file
    with open(sid_file, 'rb') as f:
        data = f.read()

    # Parse header
    header = parse_psid_header(data)

    # Extract music data
    music_data = data[header['header_size']:]
    load_addr = header['load_addr']
    data_end = load_addr + len(music_data)

    addresses = {}

    # Player code
    addresses['player_code'] = {
        'start': header['init_addr'],
        'end': 0x1900,  # Typically player code ends before data area
        'size': 0x1900 - header['init_addr'],
        'note': f"Init: ${header['init_addr']:04X}, Play: ${header['play_addr']:04X}"
    }

    # Sequence pointers table (standard Laxity location)
    addresses['sequence_ptrs'] = {
        'start': 0x199F,
        'end': 0x19A5,
        'size': 6,
        'entries': 3
    }

    # Read sequence pointers to find actual sequence data
    seq_ptr_offset = 0x199F - load_addr
    if seq_ptr_offset < len(music_data) - 6:
        seq_start = 0xFFFF
        seq_end = 0
        for i in range(3):
            ptr_offset = seq_ptr_offset + i * 2
            if ptr_offset + 1 < len(music_data):
                ptr = struct.unpack('<H', music_data[ptr_offset:ptr_offset+2])[0]
                if load_addr <= ptr < data_end:
                    seq_start = min(seq_start, ptr)
                    # Scan for end marker
                    scan_offset = ptr - load_addr
                    for j in range(scan_offset, min(scan_offset + 2000, len(music_data))):
                        if music_data[j] == 0x7F:
                            seq_end = max(seq_end, load_addr + j + 1)
                            break

        if seq_start < 0xFFFF and seq_end > 0:
            addresses['sequences'] = {
                'start': seq_start,
                'end': seq_end,
                'size': seq_end - seq_start,
                'entries': 1
            }

    # Wave table
    wave_result = find_wave_table(music_data, load_addr)
    if wave_result:
        addresses['wave_table_notes'] = {
            'start': wave_result['note_addr'],
            'end': wave_result['note_addr'] + wave_result['count'],
            'size': wave_result['count'],
            'entries': wave_result['count']
        }
        addresses['wave_table_waveforms'] = {
            'start': wave_result['wave_addr'],
            'end': wave_result['wave_addr'] + wave_result['count'],
            'size': wave_result['count'],
            'entries': wave_result['count']
        }

    # Instrument table (standard Laxity location)
    instr_start = 0x1A6B
    instr_count = 8
    addresses['instrument_table'] = {
        'start': instr_start,
        'end': instr_start + instr_count * 8,
        'size': instr_count * 8,
        'entries': instr_count
    }

    # Pulse table (standard Laxity location)
    pulse_start = 0x1A3B
    pulse_count = 16
    addresses['pulse_table'] = {
        'start': pulse_start,
        'end': pulse_start + pulse_count * 4,
        'size': pulse_count * 4,
        'entries': pulse_count
    }

    # Filter table (standard Laxity location)
    filter_start = 0x1A1E
    filter_count = 16
    addresses['filter_table'] = {
        'start': filter_start,
        'end': filter_start + filter_count * 3,
        'size': filter_count * 3,
        'entries': filter_count
    }

    # Arpeggio table (standard Laxity location)
    arp_start = 0x1A8B
    arp_count = 16
    addresses['arpeggio_table'] = {
        'start': arp_start,
        'end': arp_start + arp_count * 4,
        'size': arp_count * 4,
        'entries': arp_count
    }

    # Command table (standard Laxity location)
    cmd_start = 0x1ADB
    cmd_count = 64
    addresses['command_table'] = {
        'start': cmd_start,
        'end': cmd_start + cmd_count * 3,
        'size': cmd_count * 3,
        'entries': cmd_count
    }

    # Tempo (in filter table area)
    addresses['tempo'] = {
        'start': filter_start,
        'end': filter_start + 2,
        'size': 2,
        'entries': 1,
        'note': 'Embedded in filter table'
    }

    # Orderlists (embedded in player state)
    addresses['orderlists'] = {
        'start': 0x1900,
        'end': 0x199F,
        'size': 0x199F - 0x1900,
        'entries': 3,
        'note': 'Embedded in player state area'
    }

    return addresses, header


def format_addresses(addresses):
    """Format addresses for display."""
    lines = []

    # Order of display
    order = [
        ('player_code', 'Player Code'),
        ('sequences', 'Sequences'),
        ('orderlists', 'Orderlists'),
        ('instrument_table', 'Instruments'),
        ('wave_table_notes', 'Wave Table (Notes)'),
        ('wave_table_waveforms', 'Wave Table (Waveforms)'),
        ('pulse_table', 'Pulse Table'),
        ('filter_table', 'Filter Table'),
        ('arpeggio_table', 'Arpeggio Table'),
        ('tempo', 'Tempo'),
        ('command_table', 'Command Table'),
        ('sequence_ptrs', 'Sequence Pointers')
    ]

    for key, name in order:
        if key in addresses:
            addr = addresses[key]
            lines.append(f"{name}:")
            lines.append(f"  Start: ${addr['start']:04X}")
            lines.append(f"  End:   ${addr['end']:04X}")
            lines.append(f"  Size:  {addr['size']} bytes")
            if 'entries' in addr:
                lines.append(f"  Count: {addr['entries']} entries")
            if 'note' in addr:
                lines.append(f"  Note:  {addr['note']}")
            lines.append("")

    return '\n'.join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_addresses.py <sid_file>")
        sys.exit(1)

    sid_file = sys.argv[1]

    addresses, header = extract_addresses(sid_file)

    print(format_addresses(addresses))


if __name__ == '__main__':
    main()
