#!/usr/bin/env python3
"""
Deep analysis of Laxity player to find instrument tables.

The Laxity player uses STA $D400,X where X contains voice offset (0, 7, 14).
So we need to look for patterns like:
  LDA table,Y  ; Y = instrument number
  STA $D400+offset,X  ; X = voice offset
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

def find_all_sid_writes(data, load_addr):
    """Find all SID register writes"""
    writes = []

    for i in range(len(data) - 3):
        # STA $D4xx (8D xx D4)
        if data[i] == 0x8D and data[i + 2] == 0xD4:
            reg = data[i + 1]
            writes.append({
                'type': 'abs',
                'addr': load_addr + i,
                'reg': reg
            })

        # STA $D4xx,X (9D xx D4)
        if data[i] == 0x9D and data[i + 2] == 0xD4:
            reg = data[i + 1]
            writes.append({
                'type': 'abs,X',
                'addr': load_addr + i,
                'reg': reg
            })

        # STA $D4xx,Y (99 xx D4)
        if data[i] == 0x99 and data[i + 2] == 0xD4:
            reg = data[i + 1]
            writes.append({
                'type': 'abs,Y',
                'addr': load_addr + i,
                'reg': reg
            })

    return writes

def find_all_table_loads(data, load_addr):
    """Find all indexed table loads"""
    loads = []

    for i in range(len(data) - 3):
        # LDA $xxxx,X (BD lo hi)
        if data[i] == 0xBD:
            table_addr = data[i + 1] | (data[i + 2] << 8)
            loads.append({
                'type': 'abs,X',
                'addr': load_addr + i,
                'table': table_addr
            })

        # LDA $xxxx,Y (B9 lo hi)
        if data[i] == 0xB9:
            table_addr = data[i + 1] | (data[i + 2] << 8)
            loads.append({
                'type': 'abs,Y',
                'addr': load_addr + i,
                'table': table_addr
            })

    return loads

def analyze_file(filepath):
    data, load_addr = load_sid(filepath)

    filename = os.path.basename(filepath)
    print("=" * 70)
    print(f"FILE: {filename}")
    print("=" * 70)
    print(f"Load address: ${load_addr:04X}, Size: {len(data)} bytes")

    writes = find_all_sid_writes(data, load_addr)
    loads = find_all_table_loads(data, load_addr)

    print(f"\nTotal SID writes: {len(writes)}")
    print(f"Total table loads: {len(loads)}")

    # Group writes by register
    reg_groups = {}
    for w in writes:
        reg = w['reg']
        if reg not in reg_groups:
            reg_groups[reg] = []
        reg_groups[reg].append(w)

    print("\nSID writes by register:")
    for reg in sorted(reg_groups.keys()):
        count = len(reg_groups[reg])
        reg_name = ""
        if reg in [0x05, 0x0C, 0x13]:
            reg_name = "(AD)"
        elif reg in [0x06, 0x0D, 0x14]:
            reg_name = "(SR)"
        elif reg in [0x04, 0x0B, 0x12]:
            reg_name = "(CTRL)"
        elif reg in [0x00, 0x01]:
            reg_name = "(FREQ)"
        elif reg in [0x02, 0x03]:
            reg_name = "(PULSE)"
        print(f"  ${reg:02X} {reg_name}: {count} writes")

    # Find table loads that feed into AD/SR/CTRL writes
    # For each AD/SR write, look backwards for the nearest table load

    print("\nTable references for instrument data:")

    instrument_tables = {
        'ad': set(),
        'sr': set(),
        'ctrl': set()
    }

    for w in writes:
        reg = w['reg']
        w_addr = w['addr']
        w_offset = w_addr - load_addr

        # Find nearest preceding table load
        nearest_load = None
        min_dist = 100

        for l in loads:
            l_addr = l['addr']
            dist = w_addr - l_addr

            if 0 < dist < min_dist:
                min_dist = dist
                nearest_load = l

        if nearest_load and min_dist < 30:
            table = nearest_load['table']

            if reg in [0x05, 0x0C, 0x13]:  # AD
                instrument_tables['ad'].add(table)
            elif reg in [0x06, 0x0D, 0x14]:  # SR
                instrument_tables['sr'].add(table)
            elif reg in [0x04, 0x0B, 0x12]:  # CTRL
                instrument_tables['ctrl'].add(table)

    print(f"  AD tables: {', '.join(f'${t:04X}' for t in sorted(instrument_tables['ad']))}")
    print(f"  SR tables: {', '.join(f'${t:04X}' for t in sorted(instrument_tables['sr']))}")
    print(f"  CTRL tables: {', '.join(f'${t:04X}' for t in sorted(instrument_tables['ctrl']))}")

    # Dump table contents
    print("\nTable contents:")

    all_tables = set()
    for tables in instrument_tables.values():
        all_tables.update(tables)

    for table_addr in sorted(all_tables):
        if not (load_addr <= table_addr < load_addr + len(data)):
            continue

        offset = table_addr - load_addr
        if offset + 16 > len(data):
            continue

        table_data = data[offset:offset + 16]
        hex_str = ' '.join(f'{b:02X}' for b in table_data)

        # Identify type
        types = []
        if table_addr in instrument_tables['ad']:
            types.append('AD')
        if table_addr in instrument_tables['sr']:
            types.append('SR')
        if table_addr in instrument_tables['ctrl']:
            types.append('CTRL')

        type_str = '/'.join(types)
        print(f"  ${table_addr:04X} ({type_str}): {hex_str}")

    # Build instruments
    if instrument_tables['ad'] and instrument_tables['sr']:
        ad_table = min(t for t in instrument_tables['ad'] if load_addr <= t < load_addr + len(data))
        sr_table = min(t for t in instrument_tables['sr'] if load_addr <= t < load_addr + len(data))

        print(f"\nExtracted instruments (AD=${ad_table:04X}, SR=${sr_table:04X}):")

        instruments = []
        for i in range(16):
            ad_off = ad_table - load_addr + i
            sr_off = sr_table - load_addr + i

            ad = data[ad_off] if ad_off < len(data) else 0
            sr = data[sr_off] if sr_off < len(data) else 0

            instruments.append({'ad': ad, 'sr': sr})

            if ad != 0 or sr != 0:
                print(f"  {i:2d}: AD={ad:02X} SR={sr:02X}")

        return instruments

    print()
    return None

def main():
    sid_dir = 'SID'

    for filename in sorted(os.listdir(sid_dir)):
        if not filename.endswith('.sid'):
            continue

        filepath = os.path.join(sid_dir, filename)
        analyze_file(filepath)

if __name__ == '__main__':
    main()
