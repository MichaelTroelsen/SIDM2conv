#!/usr/bin/env python3
"""
Focused analysis of Laxity player - looking at specific memory regions.
"""

import struct

def load_sid(path):
    with open(path, 'rb') as f:
        data = f.read()
    version = struct.unpack('>H', data[4:6])[0]
    data_offset = struct.unpack('>H', data[6:8])[0]
    load_address = struct.unpack('>H', data[8:10])[0]
    c64_data = data[data_offset:]
    if load_address == 0:
        load_address = struct.unpack('<H', c64_data[0:2])[0]
        c64_data = c64_data[2:]
    return c64_data, load_address

def hex_dump(data, load_addr, start, length, label=""):
    """Hex dump a region"""
    print(f"\n{label} (${start:04X} - ${start+length-1:04X}):")
    offset = start - load_addr
    for i in range(0, length, 16):
        addr = start + i
        if offset + i >= len(data):
            break
        line = data[offset + i:offset + i + 16]
        hex_str = ' '.join(f'{b:02X}' for b in line)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in line)
        print(f"  ${addr:04X}: {hex_str:<48} {ascii_str}")

def get_byte(data, load_addr, addr):
    offset = addr - load_addr
    if 0 <= offset < len(data):
        return data[offset]
    return 0

def get_word(data, load_addr, addr):
    return get_byte(data, load_addr, addr) | (get_byte(data, load_addr, addr + 1) << 8)

def analyze_angular():
    """Specific analysis for Angular.sid"""
    c64_data, load_addr = load_sid('SID/Angular.sid')

    print("=" * 70)
    print("ANGULAR.SID DETAILED ANALYSIS")
    print("=" * 70)
    print(f"Load: ${load_addr:04X}, End: ${load_addr + len(c64_data) - 1:04X}")

    # The init code references $199F - let's look around there
    # This is likely the start of music data tables

    hex_dump(c64_data, load_addr, 0x1990, 64, "Region around $199F (referenced by init)")

    # Look at the end of the file - music data is often at the end
    hex_dump(c64_data, load_addr, 0x1E00, 128, "Near end of file ($1E00)")

    # Look for typical Laxity orderlist structure
    # Orderlists usually have 3 pointers (one per voice)
    # followed by the actual orderlist data

    # Let's examine $19xx region more carefully
    hex_dump(c64_data, load_addr, 0x19A0, 64, "Region $19A0-$19E0")

    # Look for small consecutive numbers that could be sequence indices
    print("\n\nSearching for orderlist patterns (small numbers ending in FF):")
    for addr in range(0x1900, 0x1F00):
        offset = addr - load_addr
        if offset < 0 or offset >= len(c64_data) - 20:
            continue

        vals = [c64_data[offset + i] for i in range(20)]

        # Check for pattern: mostly small values, ends with FF
        small = sum(1 for v in vals[:15] if v <= 0x20)
        has_ff = 0xFF in vals[:20]
        ff_pos = vals.index(0xFF) if has_ff else 20

        # Good orderlist: many small values before FF
        if small >= 5 and has_ff and ff_pos >= 4 and ff_pos <= 16:
            hex_str = ' '.join(f'{v:02X}' for v in vals[:ff_pos+2])
            print(f"  ${addr:04X}: {hex_str}")

    # Look for pointer tables (pairs of lo/hi bytes)
    print("\n\nSearching for pointer table pairs:")

    for lo_addr in range(0x19A0, 0x1B00):
        offset = lo_addr - load_addr
        if offset < 0 or offset >= len(c64_data) - 48:
            continue

        # Try hi table at +32 bytes (common spacing)
        for hi_offset in [3, 6, 16, 32]:
            hi_addr = lo_addr + hi_offset

            # Read 3 pointers (for 3 voices)
            ptrs = []
            valid = True
            for i in range(3):
                lo = c64_data[offset + i]
                hi = c64_data[offset + hi_offset + i]
                ptr = lo | (hi << 8)

                # Check if pointer is within data range
                if not (load_addr <= ptr <= load_addr + len(c64_data)):
                    valid = False
                    break
                ptrs.append(ptr)

            if valid and len(set(ptrs)) > 1:  # Not all same
                # Check if pointers point to orderlist-like data
                looks_good = True
                for ptr in ptrs:
                    ptr_off = ptr - load_addr
                    first_byte = c64_data[ptr_off] if ptr_off < len(c64_data) else 0xFF
                    if first_byte > 0x30 and first_byte < 0x80:
                        looks_good = False

                if looks_good:
                    print(f"  lo=${lo_addr:04X}, hi=${hi_addr:04X}: ", end='')
                    print(', '.join(f'${p:04X}' for p in ptrs))

                    # Show data at each pointer
                    for i, ptr in enumerate(ptrs):
                        ptr_off = ptr - load_addr
                        if ptr_off < len(c64_data) - 16:
                            pdata = c64_data[ptr_off:ptr_off+16]
                            hex_str = ' '.join(f'{b:02X}' for b in pdata)
                            print(f"      Voice {i}: {hex_str}")

    # Look specifically for 0x7F end markers (sequence terminators)
    print("\n\nLocating 0x7F end markers (potential sequence ends):")
    end_markers = []
    for i, b in enumerate(c64_data):
        if b == 0x7F:
            addr = load_addr + i
            end_markers.append(addr)

    # Group consecutive/nearby end markers
    if end_markers:
        groups = []
        current_group = [end_markers[0]]
        for addr in end_markers[1:]:
            if addr - current_group[-1] <= 64:  # Within 64 bytes
                current_group.append(addr)
            else:
                if len(current_group) >= 3:
                    groups.append(current_group)
                current_group = [addr]
        if len(current_group) >= 3:
            groups.append(current_group)

        for group in groups[:5]:
            print(f"  Group at ${group[0]:04X}-${group[-1]:04X}: {len(group)} markers")

            # Show data before first marker
            first_addr = group[0]
            offset = first_addr - load_addr
            if offset > 32:
                pre_data = c64_data[offset-32:offset+1]
                hex_str = ' '.join(f'{b:02X}' for b in pre_data)
                print(f"    Data before first: ...{hex_str}")

    # Examine region $1B00-$1E00 which seems to have music data
    hex_dump(c64_data, load_addr, 0x1B00, 64, "Region $1B00 (potential sequences)")
    hex_dump(c64_data, load_addr, 0x1C00, 64, "Region $1C00")
    hex_dump(c64_data, load_addr, 0x1D00, 64, "Region $1D00")

if __name__ == '__main__':
    analyze_angular()
