#!/usr/bin/env python3
"""
Deep analysis tool for SID files using Laxity player format.
This helps understand the data structure for conversion to SF2.
"""

import struct
import sys
import os


def read_sid_file(filepath: str):
    """Read and parse SID file"""
    with open(filepath, 'rb') as f:
        data = f.read()

    # Parse header
    magic = data[0:4].decode('ascii')
    version = struct.unpack('>H', data[4:6])[0]
    data_offset = struct.unpack('>H', data[6:8])[0]
    load_address = struct.unpack('>H', data[8:10])[0]
    init_address = struct.unpack('>H', data[10:12])[0]
    play_address = struct.unpack('>H', data[12:14])[0]

    # Get C64 data
    c64_data = data[data_offset:]

    # Handle embedded load address
    if load_address == 0:
        load_address = struct.unpack('<H', c64_data[0:2])[0]
        c64_data = c64_data[2:]

    return c64_data, load_address, init_address, play_address


def disassemble_6502(data: bytes, start_addr: int, num_bytes: int = 64):
    """Simple 6502 disassembler for analysis"""

    # Opcode table: opcode -> (mnemonic, size, addressing_mode)
    opcodes = {
        0x00: ('BRK', 1, 'imp'), 0x01: ('ORA', 2, 'izx'), 0x05: ('ORA', 2, 'zp'),
        0x06: ('ASL', 2, 'zp'), 0x08: ('PHP', 1, 'imp'), 0x09: ('ORA', 2, 'imm'),
        0x0A: ('ASL', 1, 'acc'), 0x0D: ('ORA', 3, 'abs'), 0x0E: ('ASL', 3, 'abs'),
        0x10: ('BPL', 2, 'rel'), 0x11: ('ORA', 2, 'izy'), 0x15: ('ORA', 2, 'zpx'),
        0x16: ('ASL', 2, 'zpx'), 0x18: ('CLC', 1, 'imp'), 0x19: ('ORA', 3, 'aby'),
        0x1D: ('ORA', 3, 'abx'), 0x1E: ('ASL', 3, 'abx'),
        0x20: ('JSR', 3, 'abs'), 0x21: ('AND', 2, 'izx'), 0x24: ('BIT', 2, 'zp'),
        0x25: ('AND', 2, 'zp'), 0x26: ('ROL', 2, 'zp'), 0x28: ('PLP', 1, 'imp'),
        0x29: ('AND', 2, 'imm'), 0x2A: ('ROL', 1, 'acc'), 0x2C: ('BIT', 3, 'abs'),
        0x2D: ('AND', 3, 'abs'), 0x2E: ('ROL', 3, 'abs'), 0x30: ('BMI', 2, 'rel'),
        0x31: ('AND', 2, 'izy'), 0x35: ('AND', 2, 'zpx'), 0x36: ('ROL', 2, 'zpx'),
        0x38: ('SEC', 1, 'imp'), 0x39: ('AND', 3, 'aby'), 0x3D: ('AND', 3, 'abx'),
        0x3E: ('ROL', 3, 'abx'),
        0x40: ('RTI', 1, 'imp'), 0x41: ('EOR', 2, 'izx'), 0x45: ('EOR', 2, 'zp'),
        0x46: ('LSR', 2, 'zp'), 0x48: ('PHA', 1, 'imp'), 0x49: ('EOR', 2, 'imm'),
        0x4A: ('LSR', 1, 'acc'), 0x4C: ('JMP', 3, 'abs'), 0x4D: ('EOR', 3, 'abs'),
        0x4E: ('LSR', 3, 'abs'), 0x50: ('BVC', 2, 'rel'), 0x51: ('EOR', 2, 'izy'),
        0x55: ('EOR', 2, 'zpx'), 0x56: ('LSR', 2, 'zpx'), 0x58: ('CLI', 1, 'imp'),
        0x59: ('EOR', 3, 'aby'), 0x5D: ('EOR', 3, 'abx'), 0x5E: ('LSR', 3, 'abx'),
        0x60: ('RTS', 1, 'imp'), 0x61: ('ADC', 2, 'izx'), 0x65: ('ADC', 2, 'zp'),
        0x66: ('ROR', 2, 'zp'), 0x68: ('PLA', 1, 'imp'), 0x69: ('ADC', 2, 'imm'),
        0x6A: ('ROR', 1, 'acc'), 0x6C: ('JMP', 3, 'ind'), 0x6D: ('ADC', 3, 'abs'),
        0x6E: ('ROR', 3, 'abs'), 0x70: ('BVS', 2, 'rel'), 0x71: ('ADC', 2, 'izy'),
        0x75: ('ADC', 2, 'zpx'), 0x76: ('ROR', 2, 'zpx'), 0x78: ('SEI', 1, 'imp'),
        0x79: ('ADC', 3, 'aby'), 0x7D: ('ADC', 3, 'abx'), 0x7E: ('ROR', 3, 'abx'),
        0x81: ('STA', 2, 'izx'), 0x84: ('STY', 2, 'zp'), 0x85: ('STA', 2, 'zp'),
        0x86: ('STX', 2, 'zp'), 0x88: ('DEY', 1, 'imp'), 0x8A: ('TXA', 1, 'imp'),
        0x8C: ('STY', 3, 'abs'), 0x8D: ('STA', 3, 'abs'), 0x8E: ('STX', 3, 'abs'),
        0x90: ('BCC', 2, 'rel'), 0x91: ('STA', 2, 'izy'), 0x94: ('STY', 2, 'zpx'),
        0x95: ('STA', 2, 'zpx'), 0x96: ('STX', 2, 'zpy'), 0x98: ('TYA', 1, 'imp'),
        0x99: ('STA', 3, 'aby'), 0x9A: ('TXS', 1, 'imp'), 0x9D: ('STA', 3, 'abx'),
        0xA0: ('LDY', 2, 'imm'), 0xA1: ('LDA', 2, 'izx'), 0xA2: ('LDX', 2, 'imm'),
        0xA4: ('LDY', 2, 'zp'), 0xA5: ('LDA', 2, 'zp'), 0xA6: ('LDX', 2, 'zp'),
        0xA8: ('TAY', 1, 'imp'), 0xA9: ('LDA', 2, 'imm'), 0xAA: ('TAX', 1, 'imp'),
        0xAC: ('LDY', 3, 'abs'), 0xAD: ('LDA', 3, 'abs'), 0xAE: ('LDX', 3, 'abs'),
        0xB0: ('BCS', 2, 'rel'), 0xB1: ('LDA', 2, 'izy'), 0xB4: ('LDY', 2, 'zpx'),
        0xB5: ('LDA', 2, 'zpx'), 0xB6: ('LDX', 2, 'zpy'), 0xB8: ('CLV', 1, 'imp'),
        0xB9: ('LDA', 3, 'aby'), 0xBA: ('TSX', 1, 'imp'), 0xBC: ('LDY', 3, 'abx'),
        0xBD: ('LDA', 3, 'abx'), 0xBE: ('LDX', 3, 'aby'),
        0xC0: ('CPY', 2, 'imm'), 0xC1: ('CMP', 2, 'izx'), 0xC4: ('CPY', 2, 'zp'),
        0xC5: ('CMP', 2, 'zp'), 0xC6: ('DEC', 2, 'zp'), 0xC8: ('INY', 1, 'imp'),
        0xC9: ('CMP', 2, 'imm'), 0xCA: ('DEX', 1, 'imp'), 0xCC: ('CPY', 3, 'abs'),
        0xCD: ('CMP', 3, 'abs'), 0xCE: ('DEC', 3, 'abs'), 0xD0: ('BNE', 2, 'rel'),
        0xD1: ('CMP', 2, 'izy'), 0xD5: ('CMP', 2, 'zpx'), 0xD6: ('DEC', 2, 'zpx'),
        0xD8: ('CLD', 1, 'imp'), 0xD9: ('CMP', 3, 'aby'), 0xDD: ('CMP', 3, 'abx'),
        0xDE: ('DEC', 3, 'abx'),
        0xE0: ('CPX', 2, 'imm'), 0xE1: ('SBC', 2, 'izx'), 0xE4: ('CPX', 2, 'zp'),
        0xE5: ('SBC', 2, 'zp'), 0xE6: ('INC', 2, 'zp'), 0xE8: ('INX', 1, 'imp'),
        0xE9: ('SBC', 2, 'imm'), 0xEA: ('NOP', 1, 'imp'), 0xEC: ('CPX', 3, 'abs'),
        0xED: ('SBC', 3, 'abs'), 0xEE: ('INC', 3, 'abs'), 0xF0: ('BEQ', 2, 'rel'),
        0xF1: ('SBC', 2, 'izy'), 0xF5: ('SBC', 2, 'zpx'), 0xF6: ('INC', 2, 'zpx'),
        0xF8: ('SED', 1, 'imp'), 0xF9: ('SBC', 3, 'aby'), 0xFD: ('SBC', 3, 'abx'),
        0xFE: ('INC', 3, 'abx'),
    }

    result = []
    i = 0
    addr = start_addr

    while i < num_bytes and i < len(data):
        opcode = data[i]
        if opcode in opcodes:
            mnem, size, mode = opcodes[opcode]
            if size == 1:
                result.append(f"${addr:04X}: {opcode:02X}       {mnem}")
            elif size == 2:
                if i + 1 < len(data):
                    operand = data[i + 1]
                    if mode == 'rel':
                        # Branch - calculate target
                        if operand > 127:
                            offset = operand - 256
                        else:
                            offset = operand
                        target = addr + 2 + offset
                        result.append(f"${addr:04X}: {opcode:02X} {operand:02X}    {mnem} ${target:04X}")
                    elif mode == 'imm':
                        result.append(f"${addr:04X}: {opcode:02X} {operand:02X}    {mnem} #${operand:02X}")
                    else:
                        result.append(f"${addr:04X}: {opcode:02X} {operand:02X}    {mnem} ${operand:02X}")
                else:
                    result.append(f"${addr:04X}: {opcode:02X}       {mnem} ???")
            elif size == 3:
                if i + 2 < len(data):
                    lo = data[i + 1]
                    hi = data[i + 2]
                    operand = lo | (hi << 8)
                    result.append(f"${addr:04X}: {opcode:02X} {lo:02X} {hi:02X} {mnem} ${operand:04X}")
                else:
                    result.append(f"${addr:04X}: {opcode:02X}       {mnem} ???")
            i += size
            addr += size
        else:
            result.append(f"${addr:04X}: {opcode:02X}       .byte ${opcode:02X}")
            i += 1
            addr += 1

    return result


def find_jsr_targets(data: bytes, start_addr: int):
    """Find all JSR targets (subroutine calls)"""
    targets = []
    i = 0
    while i < len(data) - 2:
        if data[i] == 0x20:  # JSR
            target = data[i + 1] | (data[i + 2] << 8)
            targets.append((start_addr + i, target))
        i += 1
    return targets


def find_absolute_addresses(data: bytes, start_addr: int):
    """Find all absolute address references"""
    end_addr = start_addr + len(data)
    addresses = {}

    i = 0
    while i < len(data) - 2:
        # Check for potential address (within data range)
        addr = data[i] | (data[i + 1] << 8)
        if start_addr <= addr < end_addr:
            if addr not in addresses:
                addresses[addr] = []
            addresses[addr].append(start_addr + i)
        i += 1

    return addresses


def analyze_data_regions(data: bytes, start_addr: int):
    """Identify potential data regions vs code"""

    # Score each region for "data-likeness"
    region_size = 32
    regions = []

    for i in range(0, len(data), region_size):
        chunk = data[i:i + region_size]
        if len(chunk) < region_size:
            continue

        # Calculate various metrics
        zeros = sum(1 for b in chunk if b == 0)
        high_bytes = sum(1 for b in chunk if b >= 0x80)
        repeated = len(chunk) - len(set(chunk))

        # Note-like values (C64 note range)
        notes = sum(1 for b in chunk if 0x00 <= b <= 0x60)

        # Check for ASCII text
        ascii_chars = sum(1 for b in chunk if 0x20 <= b <= 0x7E)

        # Opcodes that rarely appear in data
        code_opcodes = sum(1 for b in chunk if b in [0x20, 0x4C, 0x60, 0xA9, 0x8D, 0xBD])

        score = {
            'addr': start_addr + i,
            'zeros': zeros,
            'high_bytes': high_bytes,
            'repeated': repeated,
            'notes': notes,
            'ascii': ascii_chars,
            'code_like': code_opcodes
        }

        # Classify
        if code_opcodes > 3:
            score['type'] = 'CODE'
        elif ascii_chars > 20:
            score['type'] = 'TEXT'
        elif notes > 15:
            score['type'] = 'NOTES?'
        elif repeated > 10:
            score['type'] = 'TABLE?'
        else:
            score['type'] = 'DATA'

        regions.append(score)

    return regions


def find_note_tables(data: bytes, start_addr: int):
    """Find potential note frequency tables"""
    # Standard C64 note frequency table values
    # These are the PAL frequency values for the SID

    candidates = []

    for i in range(len(data) - 24):
        # Check for ascending sequence (potential note table)
        vals = [data[i + j] for j in range(12)]

        # Check if values are roughly ascending (for low bytes of freq table)
        ascending = all(vals[j] <= vals[j + 1] or vals[j] > 200 for j in range(11))

        if ascending and max(vals) > min(vals) + 20:
            candidates.append((start_addr + i, vals))

    return candidates[:10]  # Return top 10


def hexdump(data: bytes, start_addr: int, length: int = 256):
    """Create a hex dump of data"""
    result = []
    for i in range(0, min(length, len(data)), 16):
        chunk = data[i:i + 16]
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        ascii_part = ''.join(chr(b) if 0x20 <= b <= 0x7E else '.' for b in chunk)
        result.append(f"${start_addr + i:04X}: {hex_part:<48} {ascii_part}")
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_sid.py <file.sid>")
        sys.exit(1)

    filepath = sys.argv[1]
    c64_data, load_addr, init_addr, play_addr = read_sid_file(filepath)

    print("=" * 70)
    print("DEEP SID FILE ANALYSIS")
    print("=" * 70)
    print(f"Load address: ${load_addr:04X}")
    print(f"Init address: ${init_addr:04X}")
    print(f"Play address: ${play_addr:04X}")
    print(f"End address:  ${load_addr + len(c64_data) - 1:04X}")
    print(f"Data size:    {len(c64_data)} bytes")
    print()

    # Disassemble init routine
    print("=" * 70)
    print("INIT ROUTINE DISASSEMBLY")
    print("=" * 70)
    init_offset = init_addr - load_addr
    if 0 <= init_offset < len(c64_data):
        disasm = disassemble_6502(c64_data[init_offset:], init_addr, 48)
        for line in disasm:
            print(line)
    print()

    # Disassemble play routine
    print("=" * 70)
    print("PLAY ROUTINE DISASSEMBLY")
    print("=" * 70)
    play_offset = play_addr - load_addr
    if 0 <= play_offset < len(c64_data):
        disasm = disassemble_6502(c64_data[play_offset:], play_addr, 48)
        for line in disasm:
            print(line)
    print()

    # Find JSR targets
    print("=" * 70)
    print("JSR TARGETS (Subroutines)")
    print("=" * 70)
    jsr_targets = find_jsr_targets(c64_data, load_addr)
    unique_targets = sorted(set(t[1] for t in jsr_targets))
    for target in unique_targets:
        count = sum(1 for t in jsr_targets if t[1] == target)
        in_range = "IN DATA" if load_addr <= target < load_addr + len(c64_data) else "EXTERNAL"
        print(f"  ${target:04X} - called {count} time(s) [{in_range}]")
    print()

    # Analyze data regions
    print("=" * 70)
    print("DATA REGION ANALYSIS")
    print("=" * 70)
    regions = analyze_data_regions(c64_data, load_addr)
    for r in regions:
        print(f"${r['addr']:04X}: {r['type']:8} "
              f"zeros={r['zeros']:2} high={r['high_bytes']:2} "
              f"notes={r['notes']:2} code={r['code_like']:2}")
    print()

    # Find potential pointer tables
    print("=" * 70)
    print("POTENTIAL POINTER TABLES")
    print("=" * 70)
    addr_refs = find_absolute_addresses(c64_data, load_addr)
    # Find addresses referenced multiple times
    multi_refs = [(addr, refs) for addr, refs in addr_refs.items() if len(refs) >= 3]
    multi_refs.sort(key=lambda x: len(x[1]), reverse=True)
    for addr, refs in multi_refs[:20]:
        print(f"${addr:04X}: referenced {len(refs)} times")
    print()

    # Hex dump of first 512 bytes
    print("=" * 70)
    print("HEX DUMP (First 512 bytes)")
    print("=" * 70)
    dump = hexdump(c64_data, load_addr, 512)
    for line in dump:
        print(line)
    print()

    # Hex dump of last 512 bytes (often contains data tables)
    if len(c64_data) > 512:
        print("=" * 70)
        print(f"HEX DUMP (Last 512 bytes from ${load_addr + len(c64_data) - 512:04X})")
        print("=" * 70)
        dump = hexdump(c64_data[-512:], load_addr + len(c64_data) - 512, 512)
        for line in dump:
            print(line)


if __name__ == '__main__':
    main()
