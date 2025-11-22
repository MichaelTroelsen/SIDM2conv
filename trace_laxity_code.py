#!/usr/bin/env python3
"""
Trace the actual Laxity player code to find exact table references.

Laxity player typically:
1. Loads instrument number into X or Y
2. Uses LDA table,X to get AD/SR/waveform values
3. Stores to SID registers

We need to find the actual LDA xxxx,X sequences that precede STA $D4xx writes.
"""

import struct
import os

def load_sid(path):
    with open(path, 'rb') as f:
        data = f.read()

    data_offset = struct.unpack('>H', data[6:8])[0]
    load_address = struct.unpack('>H', data[8:10])[0]

    c64_data = data[data_offset:]
    if load_address == 0:
        load_address = struct.unpack('<H', c64_data[0:2])[0]
        c64_data = c64_data[2:]

    return c64_data, load_address

def disassemble_region(data, load_addr, start, end):
    """Simple disassembler for 6502"""

    opcodes = {
        0xA9: ('LDA #', 2), 0xA5: ('LDA zp', 2), 0xAD: ('LDA abs', 3),
        0xBD: ('LDA abs,X', 3), 0xB9: ('LDA abs,Y', 3),
        0x8D: ('STA abs', 3), 0x9D: ('STA abs,X', 3), 0x99: ('STA abs,Y', 3),
        0x85: ('STA zp', 2),
        0xA2: ('LDX #', 2), 0xA6: ('LDX zp', 2), 0xAE: ('LDX abs', 3),
        0xA0: ('LDY #', 2), 0xA4: ('LDY zp', 2), 0xAC: ('LDY abs', 3),
        0xE8: ('INX', 1), 0xC8: ('INY', 1),
        0xCA: ('DEX', 1), 0x88: ('DEY', 1),
        0x4C: ('JMP abs', 3), 0x20: ('JSR abs', 3), 0x60: ('RTS', 1),
        0xD0: ('BNE', 2), 0xF0: ('BEQ', 2), 0xB0: ('BCS', 2), 0x90: ('BCC', 2),
        0x29: ('AND #', 2), 0x09: ('ORA #', 2), 0x49: ('EOR #', 2),
        0xC9: ('CMP #', 2), 0xE0: ('CPX #', 2), 0xC0: ('CPY #', 2),
        0x18: ('CLC', 1), 0x38: ('SEC', 1),
        0x69: ('ADC #', 2), 0x65: ('ADC zp', 2), 0x6D: ('ADC abs', 3),
        0xE9: ('SBC #', 2), 0xE5: ('SBC zp', 2), 0xED: ('SBC abs', 3),
        0x0A: ('ASL A', 1), 0x4A: ('LSR A', 1), 0x2A: ('ROL A', 1), 0x6A: ('ROR A', 1),
        0xEA: ('NOP', 1),
        0xBC: ('LDY abs,X', 3), 0xBE: ('LDX abs,Y', 3),
    }

    offset = start - load_addr
    result = []

    while offset < end - load_addr and offset < len(data):
        addr = load_addr + offset
        opcode = data[offset]

        if opcode in opcodes:
            mnemonic, size = opcodes[opcode]

            if size == 1:
                result.append(f"${addr:04X}: {mnemonic}")
                offset += 1
            elif size == 2:
                if offset + 1 < len(data):
                    operand = data[offset + 1]
                    result.append(f"${addr:04X}: {mnemonic} ${operand:02X}")
                offset += 2
            elif size == 3:
                if offset + 2 < len(data):
                    operand = data[offset + 1] | (data[offset + 2] << 8)
                    result.append(f"${addr:04X}: {mnemonic} ${operand:04X}")
                offset += 3
        else:
            result.append(f"${addr:04X}: .byte ${opcode:02X}")
            offset += 1

    return result

def find_sid_write_sequences(data, load_addr):
    """
    Find sequences where table loads precede SID register writes.
    This reveals the actual instrument table addresses.
    """

    sequences = []

    for i in range(len(data) - 10):
        # Look for STA $D4xx patterns
        if data[i] == 0x8D and i + 2 < len(data) and data[i + 2] == 0xD4:
            reg = data[i + 1]
            write_addr = load_addr + i

            # Look backwards for LDA table,X or LDA table,Y
            for j in range(1, 30):
                if i - j < 0:
                    break

                if data[i - j] == 0xBD:  # LDA abs,X
                    if i - j + 2 < len(data):
                        table_addr = data[i - j + 1] | (data[i - j + 2] << 8)
                        sequences.append({
                            'write_addr': write_addr,
                            'reg': reg,
                            'table_addr': table_addr,
                            'load_addr': load_addr + i - j,
                            'index': 'X'
                        })
                    break
                elif data[i - j] == 0xB9:  # LDA abs,Y
                    if i - j + 2 < len(data):
                        table_addr = data[i - j + 1] | (data[i - j + 2] << 8)
                        sequences.append({
                            'write_addr': write_addr,
                            'reg': reg,
                            'table_addr': table_addr,
                            'load_addr': load_addr + i - j,
                            'index': 'Y'
                        })
                    break

        # Also check STA $D4xx,X and STA $D4xx,Y
        if data[i] == 0x9D and i + 2 < len(data) and data[i + 2] == 0xD4:
            reg = data[i + 1]
            write_addr = load_addr + i

            for j in range(1, 30):
                if i - j < 0:
                    break

                if data[i - j] == 0xBD or data[i - j] == 0xB9:
                    if i - j + 2 < len(data):
                        table_addr = data[i - j + 1] | (data[i - j + 2] << 8)
                        idx = 'X' if data[i - j] == 0xBD else 'Y'
                        sequences.append({
                            'write_addr': write_addr,
                            'reg': reg,
                            'table_addr': table_addr,
                            'load_addr': load_addr + i - j,
                            'index': idx
                        })
                    break

    return sequences

def categorize_tables(sequences):
    """
    Categorize tables by what SID registers they write to.

    Voice 1: $D400-$D406
    Voice 2: $D407-$D40D
    Voice 3: $D40E-$D414

    AD: offset 5 from voice base
    SR: offset 6 from voice base
    Control: offset 4 from voice base
    """

    categories = {
        'ad': set(),
        'sr': set(),
        'ctrl': set(),
        'freq': set(),
        'pulse': set(),
        'other': set()
    }

    for seq in sequences:
        reg = seq['reg']
        table = seq['table_addr']

        # AD registers
        if reg in [0x05, 0x0C, 0x13]:
            categories['ad'].add(table)
        # SR registers
        elif reg in [0x06, 0x0D, 0x14]:
            categories['sr'].add(table)
        # Control (waveform) registers
        elif reg in [0x04, 0x0B, 0x12]:
            categories['ctrl'].add(table)
        # Frequency registers
        elif reg in [0x00, 0x01, 0x07, 0x08, 0x0E, 0x0F]:
            categories['freq'].add(table)
        # Pulse width registers
        elif reg in [0x02, 0x03, 0x09, 0x0A, 0x10, 0x11]:
            categories['pulse'].add(table)
        else:
            categories['other'].add(table)

    return categories

def analyze_file(filepath):
    data, load_addr = load_sid(filepath)

    filename = os.path.basename(filepath)
    print("=" * 70)
    print(f"FILE: {filename}")
    print("=" * 70)
    print(f"Load address: ${load_addr:04X}, Size: {len(data)} bytes")

    # Find all sequences
    sequences = find_sid_write_sequences(data, load_addr)

    # Categorize
    categories = categorize_tables(sequences)

    print("\nTable categories:")
    for cat, tables in sorted(categories.items()):
        if tables:
            tables_str = ', '.join(f'${t:04X}' for t in sorted(tables))
            print(f"  {cat.upper()}: {tables_str}")

    # Dump the actual data at these tables
    print("\nTable contents:")

    all_tables = set()
    for tables in categories.values():
        all_tables.update(tables)

    for table_addr in sorted(all_tables):
        offset = table_addr - load_addr
        if 0 <= offset < len(data) - 16:
            table_data = data[offset:offset + 16]
            hex_str = ' '.join(f'{b:02X}' for b in table_data)

            # Determine what type this might be
            table_type = []
            if table_addr in categories['ad']:
                table_type.append('AD')
            if table_addr in categories['sr']:
                table_type.append('SR')
            if table_addr in categories['ctrl']:
                table_type.append('CTRL')
            if table_addr in categories['pulse']:
                table_type.append('PULSE')

            type_str = '/'.join(table_type) if table_type else '?'
            print(f"  ${table_addr:04X} ({type_str}): {hex_str}")

    # Extract instruments based on AD and SR tables
    if categories['ad'] and categories['sr']:
        ad_table = min(categories['ad'])  # Assume lowest address
        sr_table = min(categories['sr'])

        print(f"\nUsing AD=${ad_table:04X}, SR=${sr_table:04X}")
        print("\nExtracted instruments:")

        for i in range(16):
            ad_off = ad_table - load_addr + i
            sr_off = sr_table - load_addr + i

            if 0 <= ad_off < len(data) and 0 <= sr_off < len(data):
                ad = data[ad_off]
                sr = data[sr_off]

                if ad != 0 or sr != 0:
                    print(f"  {i:2d}: AD={ad:02X} SR={sr:02X}")

    print()
    return categories, sequences

def main():
    sid_dir = 'SID'

    for filename in sorted(os.listdir(sid_dir)):
        if not filename.endswith('.sid'):
            continue

        filepath = os.path.join(sid_dir, filename)
        analyze_file(filepath)

if __name__ == '__main__':
    main()
