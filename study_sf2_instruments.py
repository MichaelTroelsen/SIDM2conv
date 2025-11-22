#!/usr/bin/env python3
"""
Study SF2 instrument format by examining the template file structure.
"""

import struct

def main():
    # Load template
    template_path = r'C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master\SIDFactoryII\music\Driver 11 Test - Arpeggio.sf2'

    with open(template_path, 'rb') as f:
        data = f.read()

    load_addr = struct.unpack('<H', data[0:2])[0]
    print(f"Load address: ${load_addr:04X}")
    print(f"File size: {len(data)} bytes")

    # Parse header blocks to find instrument table address
    offset = 4
    instrument_addr = None

    print("\nParsing header blocks:")
    while offset < len(data) - 2:
        block_id = data[offset]
        if block_id == 0xFF:
            print(f"  End marker at offset {offset}")
            break

        block_size = data[offset + 1]
        block_data = data[offset + 2:offset + 2 + block_size]

        print(f"\n  Block ID {block_id} at offset {offset}, size {block_size}")

        if block_id == 3:  # Tables block
            print("    (Driver Tables block)")
            # Parse table definitions
            # Format appears to be: type, id, name (null-terminated), address, dimensions...
            idx = 0
            while idx < len(block_data):
                if block_data[idx] == 0:
                    break

                table_type = block_data[idx]
                table_id = block_data[idx + 1]

                # Find end of name
                name_start = idx + 2
                name_end = name_start
                while name_end < len(block_data) and block_data[name_end] != 0:
                    name_end += 1
                name = block_data[name_start:name_end].decode('latin-1', errors='replace')

                # Address is after the null terminator
                if name_end + 3 < len(block_data):
                    addr_lo = block_data[name_end + 1]
                    addr_hi = block_data[name_end + 2]
                    addr = addr_lo | (addr_hi << 8)

                    # Check if this is the instrument table
                    if 'nstr' in name.lower() or table_id == 0 or 'Inst' in name:
                        print(f"    Table: type={table_type:02X}, id={table_id}, name='{name}', addr=${addr:04X}")

                        if name and 'nstr' in name.lower():
                            instrument_addr = addr

                idx = name_end + 6  # Move past address and dimensions

        elif block_id == 4:  # Instrument descriptions
            print("    (Instrument Descriptions block)")
            # This block contains instrument name strings
            idx = 0
            instr_num = 0
            while idx < len(block_data):
                # Find null terminator
                end = idx
                while end < len(block_data) and block_data[end] != 0:
                    end += 1
                if end > idx:
                    name = block_data[idx:end].decode('latin-1', errors='replace')
                    print(f"      Instr {instr_num}: '{name}'")
                    instr_num += 1
                idx = end + 1
                if instr_num >= 5:
                    print(f"      ... and more")
                    break

        offset += 2 + block_size

    # Now let's look at the actual instrument data area
    # Based on typical SF2 structure, instruments are usually around $1000-$1500
    print("\n" + "="*60)
    print("SEARCHING FOR INSTRUMENT DATA")
    print("="*60)

    # Look for the pattern shown in screenshot: columns of 5 bytes per instrument
    # The screenshot shows "00: 00 c5 80 00 00" which is row 00

    # Search for areas that look like instrument tables
    # In SF2 Driver 11, instruments are typically 6 bytes each:
    # Byte 0: AD (Attack/Decay)
    # Byte 1: SR (Sustain/Release)
    # Byte 2: Wave table index
    # Byte 3: Pulse table index
    # Byte 4: Filter table index
    # Byte 5: HR (hard restart) settings

    print("\nLooking for instrument table patterns (16 instruments × 6 bytes):")

    for check_addr in range(load_addr + 0x500, load_addr + 0x1200):
        file_offset = check_addr - load_addr + 2
        if file_offset + 96 > len(data):
            break

        # Read 16 potential instruments
        instruments = []
        valid = True
        for i in range(16):
            instr = data[file_offset + i*6 : file_offset + (i+1)*6]
            if len(instr) < 6:
                valid = False
                break
            instruments.append(instr)

        if not valid:
            continue

        # Check if this looks like an instrument table
        # Wave index (byte 2) should be small or zero
        # Pulse/Filter indices should be small or zero
        score = 0
        for instr in instruments:
            ad, sr, wave, pulse, filt, hr = instr[0], instr[1], instr[2], instr[3], instr[4], instr[5]
            # Typical AD/SR values are in range 0-FF
            # Wave/Pulse/Filter indices should be 0-15 typically
            if wave <= 0x10:
                score += 1
            if pulse <= 0x10:
                score += 1
            if filt <= 0x10:
                score += 1

        if score >= 30:  # At least 30 good bytes out of 48
            print(f"\n  Potential instrument table at ${check_addr:04X} (score {score}):")
            for i, instr in enumerate(instruments[:8]):
                ad, sr, wave, pulse, filt, hr = instr
                print(f"    Instr {i:2d}: AD={ad:02X} SR={sr:02X} Wave={wave:02X} Pulse={pulse:02X} Filter={filt:02X} HR={hr:02X}")
            break

    # Also dump the area around common instrument locations
    print("\n\nRaw dump of likely instrument area ($1010-$1070):")
    for addr in range(0x1010, 0x1070, 0x10):
        file_offset = addr - load_addr + 2
        if file_offset >= 0 and file_offset + 16 < len(data):
            row = data[file_offset:file_offset+16]
            hex_str = ' '.join(f'{b:02X}' for b in row)
            print(f"  ${addr:04X}: {hex_str}")

    # The screenshot shows 5 columns, let's see if it's actually displayed differently
    print("\n\nLooking at what screenshot shows (5 bytes per instrument displayed):")
    print("The screenshot shows 'Instruments' with format: 00: 00 c5 80 00 00")
    print("This could be: index: AD SR Wave Pulse Filter")
    print("Or: index: column data for visualization")

    # Find where template has non-zero instrument-like data
    print("\nSearching for non-zero instrument data:")
    for check_addr in range(load_addr, load_addr + 0x1500):
        file_offset = check_addr - load_addr + 2
        if file_offset + 80 > len(data):
            break

        # Check if there's meaningful data here
        chunk = data[file_offset:file_offset + 80]
        non_zero = sum(1 for b in chunk if b != 0)

        if non_zero >= 40:  # At least half non-zero
            # Check if it looks like instruments (not code or strings)
            has_jmp = any(chunk[i] == 0x4C for i in range(0, len(chunk)-2, 3))
            has_jsr = any(chunk[i] == 0x20 for i in range(0, len(chunk)-2, 3))

            if not has_jmp and not has_jsr:
                print(f"\n  Non-zero data at ${check_addr:04X}:")
                for i in range(0, 48, 16):
                    row = chunk[i:i+16]
                    hex_str = ' '.join(f'{b:02X}' for b in row)
                    print(f"    {hex_str}")
                break


if __name__ == '__main__':
    main()
