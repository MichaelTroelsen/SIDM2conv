#!/usr/bin/env python3
"""
Extract actual instrument data from Laxity SID files.

Based on analysis:
- Laxity uses separate tables for AD, SR, and waveforms
- Tables are indexed by instrument number (0-15)
- Need to find table base addresses by analyzing code patterns
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

def get_byte(data, load_addr, addr):
    offset = addr - load_addr
    if 0 <= offset < len(data):
        return data[offset]
    return 0

def find_lda_table_refs(data, load_addr):
    """Find all LDA table,X patterns"""
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

def find_sid_writes(data, load_addr):
    """Find STA $D4xx patterns"""
    writes = []

    for i in range(len(data) - 3):
        # STA $D4xx (8D xx D4)
        if data[i] == 0x8D and data[i + 2] == 0xD4:
            reg = data[i + 1]
            writes.append((load_addr + i, reg))

        # STA $D4xx,X (9D xx D4)
        if data[i] == 0x9D and data[i + 2] == 0xD4:
            reg = data[i + 1]
            writes.append((load_addr + i, reg))

    return writes

def find_instrument_tables(data, load_addr):
    """
    Find the actual instrument table locations.

    Strategy: Look for table loads that are close to SID register writes.
    """

    table_refs = find_lda_table_refs(data, load_addr)
    sid_writes = find_sid_writes(data, load_addr)

    # Map table addresses to which SID registers they might control
    table_to_regs = {}

    for ref_type, code_addr, table_addr in table_refs:
        # Skip tables outside data range
        if not (load_addr <= table_addr < load_addr + len(data)):
            continue

        # Find SID writes close to this table load
        for write_addr, reg in sid_writes:
            if 0 < write_addr - code_addr < 30:  # Within 30 bytes
                if table_addr not in table_to_regs:
                    table_to_regs[table_addr] = set()
                table_to_regs[table_addr].add(reg)

    # Identify likely AD, SR, waveform tables
    ad_tables = []
    sr_tables = []
    ctrl_tables = []

    for addr, regs in table_to_regs.items():
        # AD registers: $05, $0C, $13 (or base $05)
        if regs & {0x05, 0x0C, 0x13, 0x00}:
            ad_tables.append(addr)

        # SR registers: $06, $0D, $14 (or base $06)
        if regs & {0x06, 0x0D, 0x14, 0x01}:
            sr_tables.append(addr)

        # Control registers: $04, $0B, $12 (waveform + gate)
        if regs & {0x04, 0x0B, 0x12}:
            ctrl_tables.append(addr)

    return {
        'ad': ad_tables,
        'sr': sr_tables,
        'ctrl': ctrl_tables,
        'all': table_to_regs
    }

def find_instrument_data_heuristic(data, load_addr):
    """
    Use heuristics to find the actual instrument data.

    Look for patterns that match typical instrument configurations:
    - AD values: typical attack/decay combinations
    - SR values: typical sustain/release combinations
    - Waveform: 0x11 (tri), 0x21 (saw), 0x41 (pulse), 0x81 (noise)
    """

    results = {
        'ad_table': None,
        'sr_table': None,
        'wave_table': None,
        'instruments': []
    }

    # Strategy 1: Find consecutive SR-like values
    # SR values typically have patterns like 0xF8, 0x98, 0xA8, etc.

    best_sr_addr = None
    best_sr_score = 0

    for addr in range(load_addr + 0x800, load_addr + len(data) - 32):
        offset = addr - load_addr

        # Check 16 bytes as potential SR table
        table = data[offset:offset + 16]

        score = 0
        for b in table:
            # SR values often have high sustain (0x?8, 0x?0)
            if (b & 0x0F) in [0x00, 0x08]:  # Common release values
                score += 1
            if (b & 0xF0) >= 0x80:  # High sustain
                score += 2
            if b in [0xF8, 0x98, 0xA8, 0xE8, 0x88, 0x00]:  # Common SR
                score += 3

        if score > best_sr_score:
            best_sr_score = score
            best_sr_addr = addr

    # Strategy 2: Find waveform table (most distinctive)
    valid_waves = {0x11, 0x21, 0x41, 0x81, 0x10, 0x20, 0x40, 0x80, 0x7F}

    best_wave_addr = None
    best_wave_score = 0

    for addr in range(load_addr + 0x800, load_addr + len(data) - 64):
        offset = addr - load_addr

        # Check for waveform patterns
        table = data[offset:offset + 32]

        score = 0
        for b in table:
            if b in valid_waves:
                score += 3
            elif b < 0x10:  # Small values (offsets)
                score += 1

        if score > best_wave_score:
            best_wave_score = score
            best_wave_addr = addr

    results['sr_table'] = best_sr_addr
    results['wave_table'] = best_wave_addr

    # Strategy 3: AD table is often 16 bytes before SR table
    if best_sr_addr:
        results['ad_table'] = best_sr_addr - 16

    return results

def extract_instruments_from_tables(data, load_addr, tables):
    """Extract instrument data from identified tables"""

    instruments = []

    ad_addr = tables.get('ad_table')
    sr_addr = tables.get('sr_table')
    wave_addr = tables.get('wave_table')

    print(f"  AD table: ${ad_addr:04X}" if ad_addr else "  AD table: not found")
    print(f"  SR table: ${sr_addr:04X}" if sr_addr else "  SR table: not found")
    print(f"  Wave table: ${wave_addr:04X}" if wave_addr else "  Wave table: not found")

    for i in range(16):
        ad = get_byte(data, load_addr, ad_addr + i) if ad_addr else 0x09
        sr = get_byte(data, load_addr, sr_addr + i) if sr_addr else 0xA0

        # Wave is more complex - need to determine waveform for each instrument
        # For now, use default based on pattern
        wave = 0x21  # Default saw

        if wave_addr:
            # Look for wave patterns
            wave_byte = get_byte(data, load_addr, wave_addr + i)
            if wave_byte in [0x11, 0x21, 0x41, 0x81]:
                wave = wave_byte

        instruments.append({
            'ad': ad,
            'sr': sr,
            'wave': wave,
            'pulse': 0x00,
            'filter': 0x00,
            'hr': 0x00
        })

    return instruments

def find_specific_patterns(data, load_addr):
    """
    Find specific byte patterns that indicate instrument tables.

    Looking for:
    - Pattern: F8 98 A8 E2 (common SR values)
    - Pattern: 41 21 11 81 (waveform values)
    """

    results = {}

    # Search for SR pattern
    sr_pattern = bytes([0xF8, 0x98])

    for i in range(len(data) - 4):
        if data[i:i+2] == sr_pattern:
            addr = load_addr + i
            context = data[max(0, i-8):i+16]

            # Check if this looks like a table start
            # Look backwards for potential AD values
            ad_start = i - 16
            if ad_start >= 0:
                ad_table = data[ad_start:i]

                # AD values typically have patterns
                if any(b > 0 for b in ad_table[:8]):
                    results['sr_pattern'] = addr
                    results['ad_pattern'] = load_addr + ad_start
                    break

    # Search for waveform pattern
    for i in range(len(data) - 8):
        b = data[i]
        if b in [0x41, 0x21, 0x11, 0x81]:
            # Check if followed by more waveform values
            wave_count = 0
            for j in range(8):
                if i + j < len(data):
                    if data[i + j] in [0x41, 0x21, 0x11, 0x81, 0x20, 0x40]:
                        wave_count += 1

            if wave_count >= 4:
                results['wave_pattern'] = load_addr + i
                break

    return results

def analyze_angular_specific(data, load_addr):
    """
    Specific analysis for Angular.sid based on earlier findings.

    Key data found:
    - $1984: F8 98 28 41 20 21 - this is inline instrument data!
    - $193C: 00 F8 98 A8 E2 14 15 04 1A 1A 01 02 06 - SR table

    The Laxity player seems to store instruments in a compact format.
    """

    print("\n  Angular-specific analysis:")

    # Check the data at $193C which looks like SR table
    sr_table_addr = 0x193C
    offset = sr_table_addr - load_addr

    if offset >= 0 and offset + 16 <= len(data):
        sr_data = data[offset:offset + 16]
        print(f"    SR table at ${sr_table_addr:04X}: {' '.join(f'{b:02X}' for b in sr_data)}")

        # The pattern is: 00 F8 98 A8 E2 14 15 04 1A 1A 01 02 06 00 00 00
        # This suggests:
        # - Instrument 0: SR = 0x00
        # - Instrument 1: SR = 0xF8
        # - Instrument 2: SR = 0x98
        # - Instrument 3: SR = 0xA8
        # etc.

    # Look for AD table 16 bytes before
    ad_table_addr = 0x192C
    offset = ad_table_addr - load_addr

    if offset >= 0 and offset + 16 <= len(data):
        ad_data = data[offset:offset + 16]
        print(f"    AD table at ${ad_table_addr:04X}: {' '.join(f'{b:02X}' for b in ad_data)}")

    # The waveform data appears elsewhere - need to find it
    # Look in the $19E0-$1A20 range which had waveform patterns

    for addr in [0x19E0, 0x19F0, 0x1A00]:
        offset = addr - load_addr
        if offset >= 0 and offset + 16 <= len(data):
            wave_data = data[offset:offset + 16]
            wave_count = sum(1 for b in wave_data if b in [0x11, 0x21, 0x41, 0x81])
            if wave_count >= 4:
                print(f"    Wave area at ${addr:04X}: {' '.join(f'{b:02X}' for b in wave_data)}")

    return {
        'ad_table': 0x192C,
        'sr_table': 0x193C,
        'wave_table': 0x19F0
    }

def main():
    sid_dir = 'SID'

    all_instruments = {}

    for filename in sorted(os.listdir(sid_dir)):
        if not filename.endswith('.sid'):
            continue

        filepath = os.path.join(sid_dir, filename)
        data, load_addr = load_sid(filepath)

        print("=" * 70)
        print(f"FILE: {filename}")
        print("=" * 70)
        print(f"Load address: ${load_addr:04X}, Size: {len(data)} bytes")

        # Find tables using various methods
        tables = find_instrument_data_heuristic(data, load_addr)
        patterns = find_specific_patterns(data, load_addr)

        # Special case for Angular
        if 'Angular' in filename:
            tables = analyze_angular_specific(data, load_addr)

        # Extract instruments
        print("\n  Extracted instruments:")
        instruments = extract_instruments_from_tables(data, load_addr, tables)

        for i, inst in enumerate(instruments[:16]):
            ad = inst['ad']
            sr = inst['sr']
            wave = inst['wave']

            # Describe the waveform
            wave_name = ""
            if wave & 0x80:
                wave_name = "noise"
            elif wave & 0x40:
                wave_name = "pulse"
            elif wave & 0x20:
                wave_name = "saw"
            elif wave & 0x10:
                wave_name = "tri"

            if ad != 0 or sr != 0:
                print(f"    {i:2d}: AD={ad:02X} SR={sr:02X} Wave={wave:02X} ({wave_name})")

        all_instruments[filename] = instruments
        print()

    return all_instruments

if __name__ == '__main__':
    main()
