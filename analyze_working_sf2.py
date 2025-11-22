#!/usr/bin/env python3
"""
Analyze a working SF2 file to understand the exact table formats.
"""

import struct

def main():
    filepath = r'C:\Users\mit\claude\c64server\SIDM2\test89\Laxity - Stinsen - Last Night Of 89.sf2'

    with open(filepath, 'rb') as f:
        data = f.read()

    load_addr = struct.unpack('<H', data[0:2])[0]
    print(f"Load address: ${load_addr:04X}")
    print(f"File size: {len(data)} bytes")

    # Parse header blocks
    offset = 4
    tables = {}

    while offset < len(data) - 2:
        block_id = data[offset]
        if block_id == 0xFF:
            break

        block_size = data[offset + 1]
        block_data = data[offset + 2:offset + 2 + block_size]

        if block_id == 3:  # Tables block
            print(f"\n=== TABLES BLOCK (size {block_size}) ===")
            tables = parse_tables(block_data)

        offset += 2 + block_size

    # Dump each table's data
    print("\n" + "="*70)
    print("TABLE DATA DUMPS")
    print("="*70)

    for name, info in tables.items():
        dump_table(data, load_addr, name, info)

def parse_tables(block_data):
    """Parse table definitions"""
    tables = {}
    idx = 0

    while idx < len(block_data):
        if idx >= len(block_data):
            break

        table_type = block_data[idx]
        if table_type == 0xFF:
            break

        if idx + 3 > len(block_data):
            break

        table_id = block_data[idx + 1]
        text_field_size = block_data[idx + 2]

        # Find null-terminated name
        name_start = idx + 3
        name_end = name_start
        while name_end < len(block_data) and block_data[name_end] != 0:
            name_end += 1
        name = block_data[name_start:name_end].decode('latin-1', errors='replace')

        pos = name_end + 1
        if pos + 12 <= len(block_data):
            addr = struct.unpack('<H', block_data[pos+5:pos+7])[0]
            columns = struct.unpack('<H', block_data[pos+7:pos+9])[0]
            rows = struct.unpack('<H', block_data[pos+9:pos+11])[0]

            type_str = f"0x{table_type:02X}"
            if table_type == 0x80:
                type_str = "Instruments"
            elif table_type == 0x81:
                type_str = "Commands"

            print(f"  {name}: type={type_str}, addr=${addr:04X}, {columns}×{rows}")

            tables[name] = {
                'type': table_type,
                'addr': addr,
                'columns': columns,
                'rows': rows
            }

            idx = pos + 12
        else:
            break

    return tables

def dump_table(data, load_addr, name, info):
    """Dump table data in readable format"""
    addr = info['addr']
    cols = info['columns']
    rows = info['rows']
    table_type = info['type']

    file_offset = addr - load_addr + 2

    if file_offset < 0 or file_offset >= len(data):
        return

    print(f"\n--- {name} at ${addr:04X} ({cols}×{rows}) ---")

    # Show first 16 rows in column-major format (transposed to row view)
    if name == 'I' or table_type == 0x80:  # Instruments
        print("Format: AD SR Wave Pulse Filter HR")
        for row in range(min(16, rows)):
            row_data = []
            for col in range(cols):
                byte_off = file_offset + col * rows + row
                if byte_off < len(data):
                    row_data.append(data[byte_off])
            if any(b != 0 for b in row_data):
                hex_str = ' '.join(f'{b:02X}' for b in row_data)
                print(f"  {row:02X}: {hex_str}")

    elif name == 'C' or table_type == 0x81:  # Commands
        print("Format: Type Param1 Param2")
        for row in range(min(16, rows)):
            row_data = []
            for col in range(cols):
                byte_off = file_offset + col * rows + row
                if byte_off < len(data):
                    row_data.append(data[byte_off])
            if any(b != 0 for b in row_data):
                hex_str = ' '.join(f'{b:02X}' for b in row_data)
                print(f"  {row:02X}: {hex_str}")

    elif 'W' in name:  # Wave
        print("Format: Waveform NoteOffset")
        for row in range(min(32, rows)):
            row_data = []
            for col in range(cols):
                byte_off = file_offset + col * rows + row
                if byte_off < len(data):
                    row_data.append(data[byte_off])
            if any(b != 0 for b in row_data) or row < 16:
                hex_str = ' '.join(f'{b:02X}' for b in row_data)
                # Decode waveform
                wave = row_data[0] if row_data else 0
                wave_name = ""
                if wave == 0x7F:
                    wave_name = "END"
                elif wave & 0x80:
                    wave_name = "noise"
                elif wave & 0x40:
                    wave_name = "pulse"
                elif wave & 0x20:
                    wave_name = "saw"
                elif wave & 0x10:
                    wave_name = "tri"
                print(f"  {row:02X}: {hex_str}  {wave_name}")

    elif 'P' in name:  # Pulse
        print("Format: PulseWidth columns")
        for row in range(min(16, rows)):
            row_data = []
            for col in range(cols):
                byte_off = file_offset + col * rows + row
                if byte_off < len(data):
                    row_data.append(data[byte_off])
            if any(b != 0 for b in row_data):
                hex_str = ' '.join(f'{b:02X}' for b in row_data)
                print(f"  {row:02X}: {hex_str}")

    elif 'F' in name:  # Filter
        for row in range(min(16, rows)):
            row_data = []
            for col in range(cols):
                byte_off = file_offset + col * rows + row
                if byte_off < len(data):
                    row_data.append(data[byte_off])
            if any(b != 0 for b in row_data):
                hex_str = ' '.join(f'{b:02X}' for b in row_data)
                print(f"  {row:02X}: {hex_str}")

    elif 'HR' in name:  # Hard Restart
        print("Format: Frames Waveform")
        for row in range(min(16, rows)):
            row_data = []
            for col in range(cols):
                byte_off = file_offset + col * rows + row
                if byte_off < len(data):
                    row_data.append(data[byte_off])
            if any(b != 0 for b in row_data):
                hex_str = ' '.join(f'{b:02X}' for b in row_data)
                print(f"  {row:02X}: {hex_str}")

    elif 'A' in name:  # Arp
        for row in range(min(16, rows)):
            byte_off = file_offset + row
            if byte_off < len(data):
                b = data[byte_off]
                if b != 0:
                    print(f"  {row:02X}: {b:02X}")

    elif 'T' in name:  # Tempo
        for row in range(min(16, rows)):
            byte_off = file_offset + row
            if byte_off < len(data):
                b = data[byte_off]
                if b != 0:
                    print(f"  {row:02X}: {b:02X}")

    else:
        # Generic dump
        total_bytes = min(cols * rows, 64)
        for i in range(0, total_bytes, 16):
            row_data = data[file_offset + i:file_offset + i + 16]
            if any(b != 0 for b in row_data):
                hex_str = ' '.join(f'{b:02X}' for b in row_data)
                print(f"  {hex_str}")

if __name__ == '__main__':
    main()
