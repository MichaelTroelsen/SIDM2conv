#!/usr/bin/env python3
"""Analyze SF2 template to find table addresses"""

import struct

def main():
    # Load template
    with open(r'C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master\SIDFactoryII\music\Driver 11 Test - Arpeggio.sf2', 'rb') as f:
        data = f.read()

    load_addr = struct.unpack('<H', data[0:2])[0]
    print(f"Load address: ${load_addr:04X}")

    # Parse header blocks
    offset = 4
    while offset < len(data) - 2:
        block_id = data[offset]
        if block_id == 0xFF:
            break

        block_size = data[offset + 1]
        block_data = data[offset + 2:offset + 2 + block_size]

        if block_id == 3:  # BLOCK_DRIVER_TABLES
            print(f"\nTable definitions block at offset {offset}:")
            print(f"  Size: {block_size} bytes")

            # Parse table entries
            idx = 0
            table_num = 0
            while idx < len(block_data) - 8:
                table_type = block_data[idx]
                if table_type == 0:
                    break

                table_id = block_data[idx + 1]
                # Name is null-terminated
                name_end = idx + 2
                while name_end < len(block_data) and block_data[name_end] != 0:
                    name_end += 1
                name = block_data[idx + 2:name_end].decode('latin-1')

                # After name: address (2 bytes), columns, rows, etc.
                if name_end + 5 < len(block_data):
                    addr_lo = block_data[name_end + 1]
                    addr_hi = block_data[name_end + 2]
                    addr = addr_lo | (addr_hi << 8)
                    cols = block_data[name_end + 3]
                    rows = block_data[name_end + 4]

                    print(f"  Table {table_num}: type={table_type}, id={table_id}, name='{name}', addr=${addr:04X}, cols={cols}, rows={rows}")

                    # Show data at this address
                    file_offset = addr - load_addr + 2
                    if file_offset >= 0 and file_offset + 32 < len(data):
                        table_data = data[file_offset:file_offset + 32]
                        hex_str = ' '.join(f'{b:02X}' for b in table_data)
                        print(f"    Data: {hex_str}")

                table_num += 1
                # Move to next entry (estimate)
                idx = name_end + 6

        offset += 2 + block_size

    # Also check if instruments have specific location
    # In SF2, instruments are typically stored after driver code
    print("\n\nSearching for instrument-like patterns:")

    # Look for patterns that look like AD/SR bytes
    for addr in range(load_addr, load_addr + 0x1000):
        file_offset = addr - load_addr + 2
        if file_offset + 32 >= len(data):
            break

        # Check for multiple instrument-like patterns
        count = 0
        for i in range(8):
            instr_offset = file_offset + i * 8
            if instr_offset + 8 > len(data):
                break

            # Get 8-byte instrument
            instr = data[instr_offset:instr_offset + 8]
            ad = instr[0]
            sr = instr[1]

            # AD/SR should be non-zero for most instruments
            if ad > 0 and sr > 0:
                count += 1

        if count >= 4:
            print(f"\n  Potential instruments at ${addr:04X} (offset {file_offset}):")
            for i in range(min(count, 4)):
                instr = data[file_offset + i * 8:file_offset + (i + 1) * 8]
                hex_str = ' '.join(f'{b:02X}' for b in instr)
                print(f"    Instr {i}: {hex_str}")
            break


if __name__ == '__main__':
    main()
