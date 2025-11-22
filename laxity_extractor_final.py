#!/usr/bin/env python3
"""
Final working Laxity instrument extractor.

Laxity player uses:
  LDA table,X where X = instrument_index * 3
  STA $D4xx,Y where Y = voice offset (0, 7, 14)

Tables:
  $1981,X -> AD (D405)
  $1984,X -> SR (D406)
  $1987,X -> CTRL (D404)
  $197B,X -> Pulse Lo (D402)
  $197E,X -> Pulse Hi (D403)

So instrument data is at: base + instrument * 3
"""

import struct
import os
import json

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

def find_sid_register_tables(data, load_addr):
    """
    Find table addresses for each SID register by tracing
    STA $D4xx,Y instructions back to their LDA source.
    """

    tables = {}

    for i in range(len(data) - 3):
        # STA $D4xx,Y (99 lo hi)
        if data[i] == 0x99:
            addr = data[i + 1] | (data[i + 2] << 8)
            if not (0xD400 <= addr <= 0xD418):
                continue

            reg = addr - 0xD400

            # Look backwards for LDA table,X
            for j in range(1, 30):
                if i - j < 0:
                    break

                # LDA $xxxx,X (BD lo hi)
                if data[i - j] == 0xBD:
                    table = data[i - j + 1] | (data[i - j + 2] << 8)
                    tables[reg] = table
                    break

    return tables

def extract_instruments(data, load_addr, tables):
    """
    Extract instrument data from the tables.

    Format: Each table is separate, indexed by instrument number.
    AD_table[i], SR_table[i], CTRL_table[i] = instrument i's data
    """

    instruments = []

    ad_table = tables.get(0x05)  # AD register
    sr_table = tables.get(0x06)  # SR register
    ctrl_table = tables.get(0x04)  # Control register

    if not ad_table:
        return instruments

    # The format uses 3-byte groups: AD[0], AD[1], AD[2], SR[0], SR[1], SR[2], CTRL[0], ...
    # So with tables at AD, AD+3, AD+6, the number of instruments is (sr_table - ad_table)
    # But actually looking at data, it seems like sequential bytes per table

    # Calculate how many instruments we have based on table spacing
    if sr_table and ctrl_table:
        num_instr = sr_table - ad_table  # Number of AD bytes = number of instruments
    else:
        num_instr = 16

    for i in range(min(num_instr, 16)):
        ad_off = ad_table - load_addr + i
        sr_off = sr_table - load_addr + i if sr_table else ad_off
        ctrl_off = ctrl_table - load_addr + i if ctrl_table else ad_off

        if ad_off >= len(data) or sr_off >= len(data) or ctrl_off >= len(data):
            break

        ad = data[ad_off]
        sr = data[sr_off]
        ctrl = data[ctrl_off]

        # Skip if all zeros (unused instrument)
        # Note: don't use FF as end marker since it might be valid data

        # Decode waveform from control byte
        wave_name = ""
        wave_for_sf2 = 0x21  # Default saw

        if ctrl & 0x80:
            wave_name = "noise"
            wave_for_sf2 = 0x81
        elif ctrl & 0x40:
            wave_name = "pulse"
            wave_for_sf2 = 0x41
        elif ctrl & 0x20:
            wave_name = "saw"
            wave_for_sf2 = 0x21
        elif ctrl & 0x10:
            wave_name = "tri"
            wave_for_sf2 = 0x11
        else:
            wave_name = "none"
            wave_for_sf2 = 0x00

        instruments.append({
            'index': i,
            'ad': ad,
            'sr': sr,
            'ctrl': ctrl,
            'wave_name': wave_name,
            'wave_for_sf2': wave_for_sf2
        })

    return instruments

def analyze_file(filepath):
    data, load_addr = load_sid(filepath)
    filename = os.path.basename(filepath)

    tables = find_sid_register_tables(data, load_addr)

    print("=" * 70)
    print(f"FILE: {filename}")
    print("=" * 70)
    print(f"Load address: ${load_addr:04X}, Size: {len(data)} bytes")

    print("\nSID register tables:")
    for reg in sorted(tables.keys()):
        table_addr = tables[reg]
        reg_names = {
            0x00: 'Freq Lo', 0x01: 'Freq Hi',
            0x02: 'Pulse Lo', 0x03: 'Pulse Hi',
            0x04: 'Control', 0x05: 'AD', 0x06: 'SR'
        }
        name = reg_names.get(reg, f'Reg {reg:02X}')
        print(f"  {name}: ${table_addr:04X}")

    instruments = extract_instruments(data, load_addr, tables)

    print(f"\nExtracted {len(instruments)} instruments:")
    for inst in instruments:
        i = inst['index']
        ad = inst['ad']
        sr = inst['sr']
        ctrl = inst['ctrl']
        wave_name = inst['wave_name']

        attack = (ad >> 4) & 0x0F
        decay = ad & 0x0F
        sustain = (sr >> 4) & 0x0F
        release = sr & 0x0F

        print(f"  {i:2d}: AD={ad:02X} SR={sr:02X} CTRL={ctrl:02X} "
              f"({wave_name:5s}) A={attack:2d} D={decay:2d} S={sustain:2d} R={release:2d}")

    return {
        'filename': filename,
        'load_addr': load_addr,
        'tables': tables,
        'instruments': instruments
    }

def main():
    sid_dir = 'SID'

    all_results = {}

    for filename in sorted(os.listdir(sid_dir)):
        if not filename.endswith('.sid'):
            continue

        filepath = os.path.join(sid_dir, filename)
        result = analyze_file(filepath)
        all_results[filename] = result
        print()

    # Save results as JSON
    json_results = {}
    for fname, result in all_results.items():
        json_results[fname] = {
            'load_addr': result['load_addr'],
            'tables': result['tables'],
            'instruments': result['instruments']
        }

    with open('extracted_instruments.json', 'w') as f:
        json.dump(json_results, f, indent=2)

    print(f"Saved results to extracted_instruments.json")

    return all_results

if __name__ == '__main__':
    main()
