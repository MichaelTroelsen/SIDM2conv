#!/usr/bin/env python3
"""
Extract Laxity instruments using the proven analysis method.

Based on analyze_laxity_deep.py, we know:
- AD table at $1981
- SR table at $1984 (= AD + 3)
- CTRL table at $1987 (= AD + 6)

The format is: instruments are stored with 3-byte stride
  table[i*3 + 0] = AD for instrument i
  table[i*3 + 1] = SR for instrument i
  table[i*3 + 2] = CTRL for instrument i
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

def find_table_loads_before_sid_write(data, load_addr, reg_offset):
    """
    Find table address that gets loaded and then written to SID register.

    reg_offset: 0x05 for AD, 0x06 for SR, 0x04 for CTRL
    """

    for i in range(len(data) - 10):
        # Look for STA $D4xx (8D xx D4) or STA $D400,X (9D xx D4)
        is_sta_abs = (data[i] == 0x8D and i + 2 < len(data) and data[i + 2] == 0xD4)
        is_sta_idx = (data[i] == 0x9D and i + 2 < len(data) and data[i + 2] == 0xD4)

        if not (is_sta_abs or is_sta_idx):
            continue

        reg = data[i + 1]
        if reg != reg_offset:
            continue

        # Found STA to our register, look backwards for LDA table
        for j in range(1, 30):
            if i - j < 0:
                break

            # LDA $xxxx,Y (B9 lo hi)
            if data[i - j] == 0xB9 and i - j + 2 < len(data):
                table_addr = data[i - j + 1] | (data[i - j + 2] << 8)
                return table_addr

            # LDA $xxxx,X (BD lo hi)
            if data[i - j] == 0xBD and i - j + 2 < len(data):
                table_addr = data[i - j + 1] | (data[i - j + 2] << 8)
                return table_addr

    return None

def extract_instruments_from_file(filepath):
    data, load_addr = load_sid(filepath)

    filename = os.path.basename(filepath)

    # Find table addresses
    ad_table = find_table_loads_before_sid_write(data, load_addr, 0x05)
    sr_table = find_table_loads_before_sid_write(data, load_addr, 0x06)
    ctrl_table = find_table_loads_before_sid_write(data, load_addr, 0x04)

    if not ad_table:
        print(f"{filename}: Could not find AD table")
        return None

    # Calculate the base table and stride
    # If packed format: SR = AD + 3, CTRL = AD + 6, stride = 3
    # If separate tables: different addresses

    if sr_table == ad_table + 3 and ctrl_table == ad_table + 6:
        stride = 3
        base = ad_table
    else:
        # Fallback: assume stride 3 from AD table
        stride = 3
        base = ad_table

    print(f"{filename}: AD=${ad_table:04X}, SR=${sr_table:04X if sr_table else 0:04X}, "
          f"CTRL=${ctrl_table:04X if ctrl_table else 0:04X}")

    # Extract instruments
    instruments = []
    offset = base - load_addr

    for i in range(16):
        idx = offset + i * stride

        if idx + 2 >= len(data):
            break

        ad = data[idx]
        sr = data[idx + 1]
        ctrl = data[idx + 2]

        # End marker
        if ad == 0xFF and sr == 0xFF and ctrl == 0xFF:
            break

        # Decode waveform
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

        instruments.append({
            'index': i,
            'ad': ad,
            'sr': sr,
            'ctrl': ctrl,
            'wave_name': wave_name,
            'wave_for_sf2': wave_for_sf2
        })

        attack = (ad >> 4) & 0x0F
        decay = ad & 0x0F
        sustain = (sr >> 4) & 0x0F
        release = sr & 0x0F

        print(f"  {i:2d}: AD={ad:02X} SR={sr:02X} CTRL={ctrl:02X} "
              f"({wave_name:5s}) A={attack:2d} D={decay:2d} S={sustain:2d} R={release:2d}")

    return {
        'filename': filename,
        'load_addr': load_addr,
        'ad_table': ad_table,
        'sr_table': sr_table,
        'ctrl_table': ctrl_table,
        'instruments': instruments
    }

def main():
    sid_dir = 'SID'

    all_results = {}

    for filename in sorted(os.listdir(sid_dir)):
        if not filename.endswith('.sid'):
            continue

        filepath = os.path.join(sid_dir, filename)
        result = extract_instruments_from_file(filepath)

        if result:
            all_results[filename] = result

        print()

    # Save results
    with open('extracted_instruments.json', 'w') as f:
        # Convert for JSON serialization
        json_results = {}
        for fname, result in all_results.items():
            json_results[fname] = {
                'load_addr': result['load_addr'],
                'ad_table': result['ad_table'],
                'instruments': result['instruments']
            }
        json.dump(json_results, f, indent=2)

    print(f"\nSaved results to extracted_instruments.json")

    return all_results

if __name__ == '__main__':
    main()
