#!/usr/bin/env python3
"""Analyze SF2 driver headers to understand table descriptor format."""

import struct
from pathlib import Path

def parse_prg_header(data):
    """Parse PRG file header (load address)."""
    if len(data) < 2:
        return None, None
    load_addr = struct.unpack('<H', data[0:2])[0]
    return load_addr, data[2:]

def analyze_sf2_headers(driver_path):
    """Analyze SF2 header blocks in driver file."""
    with open(driver_path, 'rb') as f:
        data = f.read()

    load_addr, content = parse_prg_header(data)
    print(f"\n{'='*80}")
    print(f"Driver: {driver_path.name}")
    print(f"{'='*80}")
    print(f"Load Address: ${load_addr:04X}")
    print(f"Total Size: {len(data) + 2} bytes ({len(data)} bytes code)")

    # Find SF2 magic number (0x1337)
    magic_offset = None
    for i in range(len(content) - 1):
        if content[i:i+2] == b'\x37\x13':
            magic_offset = i
            break

    if magic_offset is None:
        print("ERROR: SF2 magic number 0x1337 not found!")
        return

    print(f"SF2 Magic Number Found: Offset ${magic_offset:04X} (${load_addr + magic_offset:04X} in memory)")

    # Parse header blocks
    offset = magic_offset + 2  # Skip magic number
    block_num = 0

    print(f"\nHeader Blocks:")
    print(f"{'Block':<8} {'ID':<8} {'Size':<8} {'Data (first 16 bytes)':<50}")
    print(f"{'-'*80}")

    while offset < len(content):
        if offset + 2 > len(content):
            break

        block_id = content[offset]
        block_size = content[offset + 1]

        if block_id == 0xFF:
            print(f"\n[END] Block terminator found at offset ${offset:04X}")
            break

        block_data = content[offset + 2:offset + 2 + block_size] if block_size > 0 else b''

        # Show first 16 bytes in hex
        hex_str = ' '.join(f'{b:02X}' for b in block_data[:16])

        block_name = get_block_name(block_id)
        print(f"[{block_num:<2}]   0x{block_id:02X}    {block_size:<8} {hex_str}")

        # Parse specific block types
        if block_id == 1:  # Descriptor
            parse_descriptor_block(block_data)
        elif block_id == 2:  # Driver Common
            parse_driver_common_block(block_data)
        elif block_id == 3:  # Driver Tables
            parse_driver_tables_block(block_data)

        offset += 2 + block_size
        block_num += 1

def get_block_name(block_id):
    """Get human-readable name for block ID."""
    names = {
        1: "Descriptor",
        2: "DriverCommon",
        3: "DriverTables",
        4: "DriverInstrumentDescriptor",
        5: "MusicData",
        6: "TableColorRules",
        7: "TableInsertDeleteRules",
        8: "TableActionRules",
        9: "DriverInstrumentDataDescriptor",
        0xFF: "END"
    }
    return names.get(block_id, f"Unknown(0x{block_id:02X})")

def parse_descriptor_block(data):
    """Parse Block 1: Descriptor."""
    if len(data) < 10:
        return

    print(f"\n  Descriptor Block:")
    print(f"    Driver Type: 0x{data[0]:02X}")

    if len(data) >= 3:
        driver_size = struct.unpack('<H', data[1:3])[0]
        print(f"    Driver Size: {driver_size} bytes")

    # Parse driver name (null-terminated)
    name_start = 3
    name_end = data.find(b'\x00', name_start)
    if name_end != -1:
        name = data[name_start:name_end].decode('ascii', errors='ignore')
        print(f"    Driver Name: {name}")

def parse_driver_common_block(data):
    """Parse Block 2: Driver Common."""
    if len(data) < 20:
        return

    print(f"\n  Driver Common Block:")
    print(f"    Init Address: ${struct.unpack('<H', data[0:2])[0]:04X}")
    print(f"    Stop Address: ${struct.unpack('<H', data[2:4])[0]:04X}")
    print(f"    Play Address: ${struct.unpack('<H', data[4:6])[0]:04X}")

def parse_driver_tables_block(data):
    """Parse Block 3: Driver Tables."""
    print(f"\n  Driver Tables Block:")
    print(f"    Size: {len(data)} bytes")

    if len(data) == 0:
        return

    # Each table descriptor is typically 16+ bytes
    offset = 0
    table_num = 0

    while offset < len(data) and table_num < 20:
        if offset + 1 > len(data):
            break

        table_type = data[offset] if offset < len(data) else None
        if table_type is None:
            break

        # Estimate descriptor size (varies, but typically 16-32 bytes)
        # Look for next table marker (starts with specific value)
        next_offset = offset + 16  # Assume minimum 16 bytes

        # Extract table info if possible
        if offset + 4 < len(data):
            table_data = data[offset:min(offset+32, len(data))]
            hex_str = ' '.join(f'{b:02X}' for b in table_data[:16])
            print(f"    Table {table_num}: {hex_str}")

        offset = next_offset
        table_num += 1

def main():
    """Analyze all available drivers."""
    drivers = [
        'G5/drivers/sf2driver11_00.prg',
        'G5/drivers/sf2driver_np20_00.prg',
    ]

    for driver in drivers:
        path = Path(driver)
        if path.exists():
            try:
                analyze_sf2_headers(path)
            except Exception as e:
                print(f"\nError analyzing {driver}: {e}")
        else:
            print(f"\nDriver not found: {driver}")

if __name__ == '__main__':
    main()
