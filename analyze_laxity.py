#!/usr/bin/env python3
"""
Deep analysis of Laxity player format in DRAX SID files.
Goal: Find the actual pointer tables and music data structures.
"""

import struct
import sys

def load_sid(path):
    """Load SID file and extract C64 data"""
    with open(path, 'rb') as f:
        data = f.read()

    # Parse PSID header
    version = struct.unpack('>H', data[4:6])[0]
    data_offset = struct.unpack('>H', data[6:8])[0]
    load_address = struct.unpack('>H', data[8:10])[0]
    init_address = struct.unpack('>H', data[10:12])[0]
    play_address = struct.unpack('>H', data[12:14])[0]

    c64_data = data[data_offset:]

    # If load_address is 0, first two bytes are the actual load address
    if load_address == 0:
        load_address = struct.unpack('<H', c64_data[0:2])[0]
        c64_data = c64_data[2:]

    return c64_data, load_address, init_address, play_address

def get_byte(data, load_addr, addr):
    """Get byte at C64 address"""
    offset = addr - load_addr
    if 0 <= offset < len(data):
        return data[offset]
    return 0

def get_word(data, load_addr, addr):
    """Get word at C64 address"""
    return get_byte(data, load_addr, addr) | (get_byte(data, load_addr, addr + 1) << 8)

def find_jmp_table(data, load_addr, play_addr):
    """Find the jump table at play address - this often points to key routines"""
    print(f"\n=== PLAY ROUTINE ANALYSIS (${play_addr:04X}) ===")

    # Read bytes at play address
    offset = play_addr - load_addr
    if offset < 0 or offset >= len(data) - 20:
        print("Play address out of range")
        return

    print(f"Bytes at play address:")
    for i in range(20):
        b = data[offset + i]
        addr = play_addr + i
        if b == 0x4C:  # JMP
            target = data[offset + i + 1] | (data[offset + i + 2] << 8)
            print(f"  ${addr:04X}: JMP ${target:04X}")
        elif b == 0x20:  # JSR
            target = data[offset + i + 1] | (data[offset + i + 2] << 8)
            print(f"  ${addr:04X}: JSR ${target:04X}")
        elif b == 0xA9:  # LDA immediate
            print(f"  ${addr:04X}: LDA #${data[offset + i + 1]:02X}")
        elif b == 0xAD:  # LDA absolute
            target = data[offset + i + 1] | (data[offset + i + 2] << 8)
            print(f"  ${addr:04X}: LDA ${target:04X}")

def find_pointer_tables(data, load_addr):
    """Find pointer tables that look like sequence/orderlist pointers"""
    print(f"\n=== SEARCHING FOR POINTER TABLES ===")

    data_end = load_addr + len(data)

    # Look for tables where entries point within the data range
    # and are spaced somewhat regularly

    best_tables = []

    for table_addr in range(load_addr, data_end - 32):
        # Read 16 potential low bytes
        lo_bytes = [get_byte(data, load_addr, table_addr + i) for i in range(16)]

        # Look for corresponding high byte table
        for hi_offset in [16, 32, 64, 128, 256]:
            hi_addr = table_addr + hi_offset
            if hi_addr >= data_end - 16:
                continue

            hi_bytes = [get_byte(data, load_addr, hi_addr + i) for i in range(16)]

            # Form pointers and check validity
            pointers = []
            valid = 0
            for i in range(16):
                ptr = lo_bytes[i] | (hi_bytes[i] << 8)
                pointers.append(ptr)
                if load_addr <= ptr < data_end:
                    valid += 1

            # Check if pointers are reasonably spaced (not all same, not random)
            if valid >= 8:
                # Check for sequential or regular spacing
                diffs = [pointers[i+1] - pointers[i] for i in range(min(valid-1, 8)) if pointers[i+1] > pointers[i]]
                if diffs:
                    avg_diff = sum(diffs) / len(diffs)
                    if 4 <= avg_diff <= 256:  # Reasonable sequence sizes
                        score = valid + (10 if 16 <= avg_diff <= 128 else 0)
                        best_tables.append((table_addr, hi_addr, valid, pointers[:8], avg_diff, score))

    # Sort by score
    best_tables.sort(key=lambda x: x[5], reverse=True)

    print(f"Found {len(best_tables)} potential pointer tables")
    for i, (lo, hi, valid, ptrs, avg, score) in enumerate(best_tables[:10]):
        print(f"\n  Table {i}: lo=${lo:04X}, hi=${hi:04X}, valid={valid}, avg_spacing={avg:.1f}")
        ptr_str = ', '.join(f'${p:04X}' for p in ptrs)
        print(f"    Pointers: {ptr_str}")

        # Show what's at first pointer
        if ptrs[0] >= load_addr:
            first_data = [get_byte(data, load_addr, ptrs[0] + j) for j in range(16)]
            hex_str = ' '.join(f'{b:02X}' for b in first_data)
            print(f"    Data at ${ptrs[0]:04X}: {hex_str}")

    return best_tables

def find_orderlist_pattern(data, load_addr):
    """Find orderlists - they typically have small values (sequence indices) and end markers"""
    print(f"\n=== SEARCHING FOR ORDERLISTS ===")

    data_end = load_addr + len(data)
    candidates = []

    for addr in range(load_addr, data_end - 32):
        # Orderlists have:
        # - Small values (0-127 for sequence indices)
        # - May have transposition bytes (0x80-0xBF)
        # - End with 0xFF or 0xFE

        values = [get_byte(data, load_addr, addr + i) for i in range(32)]

        small_count = 0
        has_end = False
        trans_count = 0

        for i, v in enumerate(values):
            if v <= 0x3F:  # Likely sequence index
                small_count += 1
            elif 0x80 <= v <= 0xBF:  # Likely transposition
                trans_count += 1
            elif v == 0xFF or v == 0xFE:
                has_end = True
                break

        if small_count >= 3 and has_end and trans_count <= small_count:
            candidates.append((addr, small_count, values[:16]))

    print(f"Found {len(candidates)} potential orderlists")
    for i, (addr, count, vals) in enumerate(candidates[:10]):
        hex_str = ' '.join(f'{v:02X}' for v in vals)
        print(f"  ${addr:04X}: {hex_str}")

    return candidates

def find_sequence_pattern(data, load_addr):
    """Find sequences - they have note values and end with 0x7F"""
    print(f"\n=== SEARCHING FOR SEQUENCES ===")

    data_end = load_addr + len(data)
    candidates = []

    for addr in range(load_addr, data_end - 32):
        values = [get_byte(data, load_addr, addr + i) for i in range(64)]

        # Look for pattern: notes (0x00-0x60), possibly commands, ending with 0x7F
        note_count = 0
        has_end = False
        end_pos = 0

        for i, v in enumerate(values):
            if 0x00 <= v <= 0x60:
                note_count += 1
            elif v == 0x7F:
                has_end = True
                end_pos = i
                break

        # Good sequence: multiple notes, ends with 0x7F, reasonable length
        if note_count >= 4 and has_end and 8 <= end_pos <= 48:
            candidates.append((addr, note_count, end_pos, values[:end_pos+1]))

    print(f"Found {len(candidates)} potential sequences")
    for i, (addr, notes, end, vals) in enumerate(candidates[:15]):
        hex_str = ' '.join(f'{v:02X}' for v in vals)
        print(f"  ${addr:04X} (notes={notes}, len={end}): {hex_str}")

    return candidates

def find_instrument_table(data, load_addr):
    """Find instrument definitions"""
    print(f"\n=== SEARCHING FOR INSTRUMENTS ===")

    data_end = load_addr + len(data)
    candidates = []

    # Instruments typically have:
    # - Attack/Decay byte
    # - Sustain/Release byte
    # - Waveform byte (0x10, 0x20, 0x40, 0x80, or combinations)

    valid_waves = {0x10, 0x11, 0x20, 0x21, 0x40, 0x41, 0x80, 0x81,
                   0x12, 0x14, 0x22, 0x24, 0x42, 0x44, 0x82, 0x84}

    for addr in range(load_addr, data_end - 64):
        # Check for multiple consecutive instruments
        instr_count = 0
        for i in range(16):
            wave_addr = addr + i * 4 + 2  # Assuming 4-byte instruments
            if wave_addr - load_addr < len(data):
                wave = get_byte(data, load_addr, wave_addr)
                if wave in valid_waves:
                    instr_count += 1
                else:
                    break

        if instr_count >= 3:
            instr_data = [get_byte(data, load_addr, addr + j) for j in range(instr_count * 4)]
            candidates.append((addr, instr_count, instr_data))

    print(f"Found {len(candidates)} potential instrument tables")
    for i, (addr, count, vals) in enumerate(candidates[:5]):
        print(f"\n  ${addr:04X}: {count} instruments")
        for j in range(min(count, 4)):
            instr = vals[j*4:(j+1)*4]
            hex_str = ' '.join(f'{b:02X}' for b in instr)
            print(f"    Instr {j}: {hex_str}")

    return candidates

def analyze_init_routine(data, load_addr, init_addr):
    """Analyze init routine to find data pointers"""
    print(f"\n=== INIT ROUTINE ANALYSIS (${init_addr:04X}) ===")

    offset = init_addr - load_addr
    if offset < 0 or offset >= len(data) - 100:
        print("Init address out of range")
        return

    # Look for pointer loads in init routine
    print("Looking for pointer loads (LDA/STA patterns):")

    addresses_referenced = []

    for i in range(100):
        b = data[offset + i]
        if b == 0xA9:  # LDA immediate - might load pointer low byte
            val = data[offset + i + 1] if offset + i + 1 < len(data) else 0
            # Check if next instruction stores it
            if offset + i + 2 < len(data):
                next_op = data[offset + i + 2]
                if next_op in (0x85, 0x8D):  # STA
                    print(f"  ${init_addr + i:04X}: LDA #${val:02X}")
        elif b == 0xAD:  # LDA absolute
            addr = data[offset + i + 1] | (data[offset + i + 2] << 8) if offset + i + 2 < len(data) else 0
            if load_addr <= addr < load_addr + len(data):
                addresses_referenced.append(addr)
                print(f"  ${init_addr + i:04X}: LDA ${addr:04X}")
        elif b == 0xBD or b == 0xB9:  # LDA abs,X or LDA abs,Y
            addr = data[offset + i + 1] | (data[offset + i + 2] << 8) if offset + i + 2 < len(data) else 0
            if load_addr <= addr < load_addr + len(data):
                addresses_referenced.append(addr)
                mode = "X" if b == 0xBD else "Y"
                print(f"  ${init_addr + i:04X}: LDA ${addr:04X},{mode}")

    return addresses_referenced

def main():
    if len(sys.argv) < 2:
        sid_path = 'SID/Angular.sid'
    else:
        sid_path = sys.argv[1]

    print(f"Analyzing: {sid_path}")
    print("=" * 60)

    c64_data, load_addr, init_addr, play_addr = load_sid(sid_path)

    print(f"Load address: ${load_addr:04X}")
    print(f"Init address: ${init_addr:04X}")
    print(f"Play address: ${play_addr:04X}")
    print(f"Data size: {len(c64_data)} bytes")
    print(f"End address: ${load_addr + len(c64_data) - 1:04X}")

    # Analyze init and play routines
    refs = analyze_init_routine(c64_data, load_addr, init_addr)
    find_jmp_table(c64_data, load_addr, play_addr)

    # Find data structures
    ptr_tables = find_pointer_tables(c64_data, load_addr)
    orderlists = find_orderlist_pattern(c64_data, load_addr)
    sequences = find_sequence_pattern(c64_data, load_addr)
    instruments = find_instrument_table(c64_data, load_addr)

if __name__ == '__main__':
    main()
