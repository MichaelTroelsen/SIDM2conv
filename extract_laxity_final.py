#!/usr/bin/env python3
"""
Final Laxity instrument extractor based on discovered format.

Laxity stores instruments in a packed 3-byte format:
  AD, SR, CTRL (waveform)

The tables are consecutive: instrument_table + 0 = AD
                           instrument_table + 3 = SR
                           instrument_table + 6 = CTRL
But indexed differently - uses instrument * 3 to get offset.

Actually, the pattern shows:
$1981: 03 01 00 F8 98 28 41 20 21 FF FF FF
       ^^^^^^^ ^^^^^^^ ^^^^^^^ ^^^^^^^^^
       Instr0  Instr1  Instr2  End markers

So each instrument is 3 bytes: AD, SR, CTRL
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

def find_instrument_table(data, load_addr):
    """
    Find the instrument table by looking for the pattern:
    - LDA xxxx,Y followed by STA $D405 (AD)
    - LDA xxxx+3,Y followed by STA $D406 (SR)
    - LDA xxxx+6,Y followed by STA $D404 (CTRL)

    The base address is where AD is loaded from.
    """

    ad_table = None
    sr_table = None
    ctrl_table = None

    for i in range(len(data) - 10):
        # LDA $xxxx,Y (B9 lo hi)
        if data[i] == 0xB9 and i + 5 < len(data):
            table_addr = data[i + 1] | (data[i + 2] << 8)

            # Check if followed by STA to AD register
            # STA $D405 (8D 05 D4) or STA $D400,X with offset
            for j in range(3, 20):
                if i + j + 2 < len(data):
                    # STA $D4xx
                    if data[i + j] == 0x8D and data[i + j + 2] == 0xD4:
                        reg = data[i + j + 1]
                        if reg == 0x05:
                            ad_table = table_addr
                        elif reg == 0x06:
                            sr_table = table_addr
                        elif reg == 0x04:
                            ctrl_table = table_addr

                    # STA $D400,X (9D 00 D4)
                    if data[i + j] == 0x9D and data[i + j + 2] == 0xD4:
                        reg = data[i + j + 1]
                        if reg == 0x05:
                            ad_table = table_addr
                        elif reg == 0x06:
                            sr_table = table_addr
                        elif reg == 0x04:
                            ctrl_table = table_addr

    return ad_table, sr_table, ctrl_table

def extract_instruments(data, load_addr, base_table):
    """
    Extract instruments from the packed 3-byte format.

    Format: [AD0 SR0 CTRL0] [AD1 SR1 CTRL1] [AD2 SR2 CTRL2] ... [FF FF FF]
    """

    instruments = []
    offset = base_table - load_addr

    if offset < 0 or offset >= len(data):
        return instruments

    i = 0
    while i < 48:  # Max 16 instruments * 3 bytes
        if offset + i + 2 >= len(data):
            break

        ad = data[offset + i]
        sr = data[offset + i + 1]
        ctrl = data[offset + i + 2]

        # End marker is FF FF FF
        if ad == 0xFF and sr == 0xFF and ctrl == 0xFF:
            break

        # Determine waveform from ctrl byte
        waveform = ctrl & 0xF0  # High nibble is waveform
        gate = ctrl & 0x0F  # Low nibble has gate and other flags

        instruments.append({
            'ad': ad,
            'sr': sr,
            'ctrl': ctrl,
            'waveform': waveform
        })

        i += 3

    return instruments

def analyze_file(filepath):
    data, load_addr = load_sid(filepath)

    filename = os.path.basename(filepath)
    print("=" * 70)
    print(f"FILE: {filename}")
    print("=" * 70)
    print(f"Load address: ${load_addr:04X}, Size: {len(data)} bytes")

    ad_table, sr_table, ctrl_table = find_instrument_table(data, load_addr)

    ad_str = f"${ad_table:04X}" if ad_table else "None"
    sr_str = f"${sr_table:04X}" if sr_table else "None"
    ctrl_str = f"${ctrl_table:04X}" if ctrl_table else "None"
    print(f"\nTable addresses: AD={ad_str}, SR={sr_str}, CTRL={ctrl_str}")

    # The packed format means AD table is the base
    if ad_table:
        # Calculate base from the differences
        # If SR = AD + 3, CTRL = AD + 6, then it's packed format
        if sr_table == ad_table + 3 and ctrl_table == ad_table + 6:
            print("  -> Packed 3-byte format confirmed!")
            base_table = ad_table
        else:
            # Separate tables - use AD as base for now
            base_table = ad_table

        # Raw dump of table area
        offset = base_table - load_addr
        table_data = data[offset:offset + 48]
        print(f"\nRaw table data at ${base_table:04X}:")
        for row in range(0, 48, 12):
            hex_str = ' '.join(f'{b:02X}' for b in table_data[row:row+12])
            print(f"  {hex_str}")

        # Extract instruments
        instruments = extract_instruments(data, load_addr, base_table)

        print(f"\nExtracted {len(instruments)} instruments:")
        for i, inst in enumerate(instruments):
            ad = inst['ad']
            sr = inst['sr']
            ctrl = inst['ctrl']

            # Decode waveform
            wave_name = ""
            if ctrl & 0x80:
                wave_name = "noise"
            elif ctrl & 0x40:
                wave_name = "pulse"
            elif ctrl & 0x20:
                wave_name = "saw"
            elif ctrl & 0x10:
                wave_name = "tri"

            # Decode envelope
            attack = (ad >> 4) & 0x0F
            decay = ad & 0x0F
            sustain = (sr >> 4) & 0x0F
            release = sr & 0x0F

            print(f"  {i:2d}: AD={ad:02X} SR={sr:02X} CTRL={ctrl:02X} "
                  f"({wave_name}) A={attack} D={decay} S={sustain} R={release}")

        return instruments

    return []

def main():
    sid_dir = 'SID'

    all_instruments = {}

    for filename in sorted(os.listdir(sid_dir)):
        if not filename.endswith('.sid'):
            continue

        filepath = os.path.join(sid_dir, filename)
        instruments = analyze_file(filepath)
        all_instruments[filename] = instruments
        print()

    return all_instruments

if __name__ == '__main__':
    main()
