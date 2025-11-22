#!/usr/bin/env python3
"""
Extract actual instrument data from Laxity SID files.

Laxity player stores instrument data in tables. We need to find:
- AD (Attack/Decay) values
- SR (Sustain/Release) values
- Waveform settings
- Pulse width settings

Based on code analysis, Laxity uses indexed tables accessed by instrument number.
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

def find_sid_register_writes(data, load_addr):
    """Find all SID register write patterns in the code"""

    writes = []

    for i in range(len(data) - 3):
        # STA $D4xx (8D xx D4) - absolute store
        if data[i] == 0x8D and data[i + 2] == 0xD4:
            reg = data[i + 1]
            addr = load_addr + i
            writes.append(('STA', addr, reg))

        # STA $D4xx,X (9D xx D4) - indexed store
        if data[i] == 0x9D and data[i + 2] == 0xD4:
            reg = data[i + 1]
            addr = load_addr + i
            writes.append(('STA,X', addr, reg))

        # STA $D4xx,Y (99 xx D4) - indexed store
        if data[i] == 0x99 and data[i + 2] == 0xD4:
            reg = data[i + 1]
            addr = load_addr + i
            writes.append(('STA,Y', addr, reg))

    return writes

def find_table_references(data, load_addr):
    """Find LDA table,X patterns that reference instrument tables"""

    refs = []

    for i in range(len(data) - 3):
        # LDA $xxxx,X (BD lo hi)
        if data[i] == 0xBD:
            table_addr = data[i + 1] | (data[i + 2] << 8)
            code_addr = load_addr + i
            refs.append(('LDA,X', code_addr, table_addr))

        # LDA $xxxx,Y (B9 lo hi)
        if data[i] == 0xB9:
            table_addr = data[i + 1] | (data[i + 2] << 8)
            code_addr = load_addr + i
            refs.append(('LDA,Y', code_addr, table_addr))

    return refs

def analyze_instrument_tables(data, load_addr, sid_writes, table_refs):
    """
    Correlate table references with SID writes to identify instrument tables.

    Key SID registers for instruments:
    - $D405/$D40C/$D413: AD (Attack/Decay) for voices 1/2/3
    - $D406/$D40D/$D414: SR (Sustain/Release) for voices 1/2/3
    - $D404/$D40B/$D412: Control register (waveform + gate)
    - $D402-03/$D409-0A/$D410-11: Pulse width
    """

    # Group SID writes by register type
    ad_writes = [w for w in sid_writes if w[2] in [0x05, 0x0C, 0x13]]
    sr_writes = [w for w in sid_writes if w[2] in [0x06, 0x0D, 0x14]]
    ctrl_writes = [w for w in sid_writes if w[2] in [0x04, 0x0B, 0x12]]

    print(f"  AD writes: {len(ad_writes)}")
    print(f"  SR writes: {len(sr_writes)}")
    print(f"  Control writes: {len(ctrl_writes)}")

    # Find table references near these writes
    # A table reference followed by SID write suggests instrument data

    potential_tables = {}

    for ref_type, code_addr, table_addr in table_refs:
        # Check if table is in valid range
        if not (load_addr <= table_addr < load_addr + len(data)):
            continue

        # Check what's near this reference
        for write_type, write_addr, reg in sid_writes:
            # If table load is within ~20 bytes before SID write
            if 0 < write_addr - code_addr < 20:
                if table_addr not in potential_tables:
                    potential_tables[table_addr] = {'refs': [], 'regs': set()}
                potential_tables[table_addr]['refs'].append(code_addr)
                potential_tables[table_addr]['regs'].add(reg)

    return potential_tables

def dump_potential_instrument_data(data, load_addr, tables):
    """Dump data at potential instrument table addresses"""

    print("\nPotential instrument tables:")

    for addr, info in sorted(tables.items()):
        regs = info['regs']

        # Determine what kind of table this might be
        table_type = []
        if regs & {0x05, 0x0C, 0x13}:
            table_type.append("AD")
        if regs & {0x06, 0x0D, 0x14}:
            table_type.append("SR")
        if regs & {0x04, 0x0B, 0x12}:
            table_type.append("CTRL")
        if regs & {0x02, 0x03, 0x09, 0x0A, 0x10, 0x11}:
            table_type.append("PULSE")

        if not table_type:
            continue

        offset = addr - load_addr
        if offset < 0 or offset + 16 > len(data):
            continue

        # Dump 16 bytes
        table_data = data[offset:offset + 16]
        hex_str = ' '.join(f'{b:02X}' for b in table_data)

        print(f"\n  ${addr:04X} ({', '.join(table_type)}): {hex_str}")

def extract_instruments_heuristic(data, load_addr):
    """
    Use heuristics to find instrument data tables.

    Look for patterns typical of instrument data:
    - AD values: typically 0x00-0x0F for attack, 0x00-0xF0 for decay
    - SR values: typically 0x00-0xF0 for sustain, 0x00-0x0F for release
    - Waveforms: 0x11 (tri), 0x21 (saw), 0x41 (pulse), 0x81 (noise)
    """

    print("\nSearching for instrument data patterns...")

    instruments = []

    # Strategy: Look for consecutive bytes that look like AD/SR pairs
    # Followed by waveform bytes

    best_match = None
    best_score = 0

    for addr in range(load_addr + 0x800, load_addr + len(data) - 128):
        offset = addr - load_addr

        # Try to interpret as 16 instruments with various byte sizes
        for instr_size in [3, 4, 5, 6, 7, 8]:
            score = 0
            found_instruments = []

            for i in range(16):
                instr_off = offset + i * instr_size
                if instr_off + instr_size > len(data):
                    break

                instr = data[instr_off:instr_off + instr_size]

                # Score based on typical instrument characteristics
                ad = instr[0]
                sr = instr[1] if len(instr) > 1 else 0

                # Check for reasonable AD/SR values
                # AD: attack in high nibble (0-F), decay in low nibble (0-F)
                # SR: sustain in high nibble (0-F), release in low nibble (0-F)

                # Most instruments have some envelope
                if ad != 0 or sr != 0:
                    score += 1

                # Check for waveform byte (if present)
                if len(instr) > 2:
                    wave = instr[2]
                    if wave in [0x11, 0x21, 0x41, 0x81, 0x10, 0x20, 0x40, 0x80]:
                        score += 2

                found_instruments.append(instr)

            if score > best_score and len(found_instruments) >= 8:
                best_score = score
                best_match = (addr, instr_size, found_instruments)

    if best_match:
        addr, size, instruments = best_match
        print(f"\nBest match at ${addr:04X} ({size}-byte format, score={best_score}):")
        for i, instr in enumerate(instruments[:16]):
            hex_str = ' '.join(f'{b:02X}' for b in instr)
            print(f"  Instr {i:2d}: {hex_str}")

        return addr, size, instruments

    return None, 0, []

def find_waveform_table(data, load_addr):
    """Find waveform/wave table data"""

    print("\nSearching for waveform tables...")

    # Look for sequences of waveform bytes
    valid_waves = {0x11, 0x21, 0x41, 0x81, 0x10, 0x20, 0x40, 0x80}

    best_addr = None
    best_count = 0

    for addr in range(load_addr + 0x800, load_addr + len(data) - 32):
        offset = addr - load_addr

        count = 0
        for i in range(32):
            if offset + i >= len(data):
                break
            b = data[offset + i]
            if b in valid_waves or b == 0x7F or b == 0x00:
                count += 1

        if count > best_count:
            best_count = count
            best_addr = addr

    if best_addr and best_count > 10:
        offset = best_addr - load_addr
        table_data = data[offset:offset + 32]
        print(f"  Best waveform table at ${best_addr:04X}:")
        for i in range(0, 32, 8):
            row = table_data[i:i+8]
            hex_str = ' '.join(f'{b:02X}' for b in row)
            print(f"    {hex_str}")

        return best_addr

    return None

def main():
    sid_dir = 'SID'

    for filename in sorted(os.listdir(sid_dir)):
        if not filename.endswith('.sid'):
            continue

        filepath = os.path.join(sid_dir, filename)

        print("=" * 70)
        print(f"FILE: {filename}")
        print("=" * 70)

        data, load_addr = load_sid(filepath)
        print(f"Load address: ${load_addr:04X}, Size: {len(data)} bytes")

        # Find SID register writes
        sid_writes = find_sid_register_writes(data, load_addr)
        print(f"\nTotal SID writes: {len(sid_writes)}")

        # Find table references
        table_refs = find_table_references(data, load_addr)
        print(f"Table references: {len(table_refs)}")

        # Analyze potential instrument tables
        tables = analyze_instrument_tables(data, load_addr, sid_writes, table_refs)
        dump_potential_instrument_data(data, load_addr, tables)

        # Heuristic search for instrument data
        addr, size, instruments = extract_instruments_heuristic(data, load_addr)

        # Find waveform table
        wave_addr = find_waveform_table(data, load_addr)

        print()

if __name__ == '__main__':
    main()
