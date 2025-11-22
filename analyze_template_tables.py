#!/usr/bin/env python3
"""
Analyze SF2 template to understand exact table structure for Driver 11.
"""

import struct

def parse_sf2_header(data):
    """Parse SF2 file header blocks to get table definitions"""

    load_addr = struct.unpack('<H', data[0:2])[0]
    print(f"Load address: ${load_addr:04X}")
    print(f"File size: {len(data)} bytes")

    tables = []
    offset = 4  # Skip load address (2) + file ID (2)

    while offset < len(data) - 2:
        block_id = data[offset]
        if block_id == 0xFF:
            break

        block_size = data[offset + 1]
        block_data = data[offset + 2:offset + 2 + block_size]

        if block_id == 3:  # BLOCK_DRIVER_TABLES
            print(f"\n=== Driver Tables Block (size {block_size}) ===")
            tables = parse_table_definitions(block_data, load_addr)

        elif block_id == 4:  # BLOCK_INSTRUMENT_DESCRIPTOR
            print(f"\n=== Instrument Descriptors Block ===")
            parse_instrument_descriptors(block_data)

        offset += 2 + block_size

    return tables, load_addr

def parse_table_definitions(block_data, load_addr):
    """Parse table definitions from driver tables block"""

    tables = []
    idx = 0

    while idx < len(block_data):
        if idx >= len(block_data):
            break

        table_type = block_data[idx]

        if table_type == 0xFF:
            break

        # Format from driver_info.cpp:
        # type(1), id(1), textfieldsize(1), name(null-terminated),
        # datalayout(1), properties(1), insertdeleteruleid(1),
        # enteractionruleid(1), colorruleid(1),
        # address(2), columns(2), rows(2), visiblerowcount(1)

        table_id = block_data[idx + 1]
        text_field_size = block_data[idx + 2]

        # Find end of name
        name_start = idx + 3
        name_end = name_start
        while name_end < len(block_data) and block_data[name_end] != 0:
            name_end += 1
        name = block_data[name_start:name_end].decode('latin-1')

        # After name null terminator
        pos = name_end + 1

        if pos + 10 <= len(block_data):
            data_layout = block_data[pos]
            properties = block_data[pos + 1]
            insert_delete_rule_id = block_data[pos + 2]
            enter_action_rule_id = block_data[pos + 3]
            color_rule_id = block_data[pos + 4]
            addr = struct.unpack('<H', block_data[pos+5:pos+7])[0]
            columns = struct.unpack('<H', block_data[pos+7:pos+9])[0]
            rows = struct.unpack('<H', block_data[pos+9:pos+11])[0]
            visible_row_count = block_data[pos + 11] if pos + 11 < len(block_data) else 0

            # Calculate table size
            size = columns * rows

            table_info = {
                'type': table_type,
                'id': table_id,
                'name': name,
                'addr': addr,
                'columns': columns,
                'rows': rows,
                'size': size,
                'data_layout': data_layout  # 0=RowMajor, 1=ColumnMajor
            }
            tables.append(table_info)

            layout = "ColumnMajor" if data_layout == 1 else "RowMajor"
            type_name = "Instruments" if table_type == 0x80 else "Commands" if table_type == 0x81 else f"0x{table_type:02X}"
            print(f"  Table '{name}': type={type_name}, addr=${addr:04X}, {columns}×{rows} ({layout})")

            # Move to next entry
            idx = pos + 12
        else:
            break

    return tables

def parse_instrument_descriptors(block_data):
    """Parse instrument descriptor strings"""
    idx = 0
    instr_num = 0
    while idx < len(block_data):
        end = idx
        while end < len(block_data) and block_data[end] != 0:
            end += 1
        if end > idx:
            name = block_data[idx:end].decode('latin-1', errors='replace')
            print(f"  Byte {instr_num}: '{name}'")
            instr_num += 1
        idx = end + 1
        if idx >= len(block_data):
            break

def dump_table_data(data, tables, load_addr):
    """Dump actual data for each table"""

    print("\n" + "="*60)
    print("TABLE DATA DUMP")
    print("="*60)

    for table in tables:
        name = table['name']
        addr = table['addr']
        cols = table['columns']
        rows = table['rows']

        # Calculate file offset
        file_offset = addr - load_addr + 2

        if file_offset < 0 or file_offset + (cols * rows) > len(data):
            print(f"\n{name}: Invalid address ${addr:04X}")
            continue

        print(f"\n--- {name} at ${addr:04X} ({cols} columns × {rows} rows) ---")

        # SF2 stores data in column-major format
        # So bytes 0..rows-1 are column 0, rows..2*rows-1 are column 1, etc.

        if name == "Instruments" or table['type'] == 0x80:
            # Show instruments as rows (transposed from column-major)
            print("Format: Row = AD, SR, Wave, Pulse, Filter, HR (6 bytes)")
            for row in range(min(rows, 16)):
                instr_data = []
                for col in range(cols):
                    byte_offset = file_offset + col * rows + row
                    if byte_offset < len(data):
                        instr_data.append(data[byte_offset])
                hex_str = ' '.join(f'{b:02X}' for b in instr_data)
                print(f"  Instr {row:2d}: {hex_str}")

        elif name == "Commands" or table['type'] == 0x81:
            # Show commands
            print("Format: Row = Type, Parameter")
            for row in range(min(rows, 16)):
                cmd_data = []
                for col in range(cols):
                    byte_offset = file_offset + col * rows + row
                    if byte_offset < len(data):
                        cmd_data.append(data[byte_offset])
                hex_str = ' '.join(f'{b:02X}' for b in cmd_data)
                print(f"  Cmd {row:2d}: {hex_str}")

        else:
            # Generic table dump
            table_data = data[file_offset:file_offset + min(cols * rows, 64)]
            for i in range(0, len(table_data), 16):
                row_data = table_data[i:i+16]
                hex_str = ' '.join(f'{b:02X}' for b in row_data)
                print(f"  {hex_str}")

def main():
    # Load template
    template_path = r'C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master\SIDFactoryII\music\Driver 11 Test - Arpeggio.sf2'

    with open(template_path, 'rb') as f:
        data = f.read()

    tables, load_addr = parse_sf2_header(data)

    if tables:
        dump_table_data(data, tables, load_addr)

if __name__ == '__main__':
    main()
