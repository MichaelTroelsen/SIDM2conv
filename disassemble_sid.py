#!/usr/bin/env python3
"""Disassemble SID file into annotated 6502/6510 assembly."""

import struct
import sys
from pathlib import Path

# 6502 instruction set
OPCODES = {
    # ADC
    0x69: ("ADC", "#${:02x}", 2), 0x65: ("ADC", "${:02x}", 2), 0x75: ("ADC", "${:02x},X", 2),
    0x6D: ("ADC", "${:04x}", 3), 0x7D: ("ADC", "${:04x},X", 3), 0x79: ("ADC", "${:04x},Y", 3),
    0x61: ("ADC", "(${:02x},X)", 2), 0x71: ("ADC", "(${:02x}),Y", 2),
    # AND
    0x29: ("AND", "#${:02x}", 2), 0x25: ("AND", "${:02x}", 2), 0x35: ("AND", "${:02x},X", 2),
    0x2D: ("AND", "${:04x}", 3), 0x3D: ("AND", "${:04x},X", 3), 0x39: ("AND", "${:04x},Y", 3),
    0x21: ("AND", "(${:02x},X)", 2), 0x31: ("AND", "(${:02x}),Y", 2),
    # ASL
    0x0A: ("ASL", "A", 1), 0x06: ("ASL", "${:02x}", 2), 0x16: ("ASL", "${:02x},X", 2),
    0x0E: ("ASL", "${:04x}", 3), 0x1E: ("ASL", "${:04x},X", 3),
    # BCC, BCS, BEQ, BMI, BNE, BPL, BVC, BVS
    0x90: ("BCC", "${:04x}", 2), 0xB0: ("BCS", "${:04x}", 2), 0xF0: ("BEQ", "${:04x}", 2),
    0x30: ("BMI", "${:04x}", 2), 0xD0: ("BNE", "${:04x}", 2), 0x10: ("BPL", "${:04x}", 2),
    0x50: ("BVC", "${:04x}", 2), 0x70: ("BVS", "${:04x}", 2),
    # BIT
    0x24: ("BIT", "${:02x}", 2), 0x2C: ("BIT", "${:04x}", 3),
    # BRK
    0x00: ("BRK", "", 1),
    # CLC, CLD, CLI, CLV
    0x18: ("CLC", "", 1), 0xD8: ("CLD", "", 1), 0x58: ("CLI", "", 1), 0xB8: ("CLV", "", 1),
    # CMP
    0xC9: ("CMP", "#${:02x}", 2), 0xC5: ("CMP", "${:02x}", 2), 0xD5: ("CMP", "${:02x},X", 2),
    0xCD: ("CMP", "${:04x}", 3), 0xDD: ("CMP", "${:04x},X", 3), 0xD9: ("CMP", "${:04x},Y", 3),
    0xC1: ("CMP", "(${:02x},X)", 2), 0xD1: ("CMP", "(${:02x}),Y", 2),
    # CPX
    0xE0: ("CPX", "#${:02x}", 2), 0xE4: ("CPX", "${:02x}", 2), 0xEC: ("CPX", "${:04x}", 3),
    # CPY
    0xC0: ("CPY", "#${:02x}", 2), 0xC4: ("CPY", "${:02x}", 2), 0xCC: ("CPY", "${:04x}", 3),
    # DEC
    0xC6: ("DEC", "${:02x}", 2), 0xD6: ("DEC", "${:02x},X", 2),
    0xCE: ("DEC", "${:04x}", 3), 0xDE: ("DEC", "${:04x},X", 3),
    # DEX, DEY
    0xCA: ("DEX", "", 1), 0x88: ("DEY", "", 1),
    # EOR
    0x49: ("EOR", "#${:02x}", 2), 0x45: ("EOR", "${:02x}", 2), 0x55: ("EOR", "${:02x},X", 2),
    0x4D: ("EOR", "${:04x}", 3), 0x5D: ("EOR", "${:04x},X", 3), 0x59: ("EOR", "${:04x},Y", 3),
    0x41: ("EOR", "(${:02x},X)", 2), 0x51: ("EOR", "(${:02x}),Y", 2),
    # INC
    0xE6: ("INC", "${:02x}", 2), 0xF6: ("INC", "${:02x},X", 2),
    0xEE: ("INC", "${:04x}", 3), 0xFE: ("INC", "${:04x},X", 3),
    # INX, INY
    0xE8: ("INX", "", 1), 0xC8: ("INY", "", 1),
    # JMP
    0x4C: ("JMP", "${:04x}", 3), 0x6C: ("JMP", "(${:04x})", 3),
    # JSR
    0x20: ("JSR", "${:04x}", 3),
    # LDA
    0xA9: ("LDA", "#${:02x}", 2), 0xA5: ("LDA", "${:02x}", 2), 0xB5: ("LDA", "${:02x},X", 2),
    0xAD: ("LDA", "${:04x}", 3), 0xBD: ("LDA", "${:04x},X", 3), 0xB9: ("LDA", "${:04x},Y", 3),
    0xA1: ("LDA", "(${:02x},X)", 2), 0xB1: ("LDA", "(${:02x}),Y", 2),
    # LDX
    0xA2: ("LDX", "#${:02x}", 2), 0xA6: ("LDX", "${:02x}", 2), 0xB6: ("LDX", "${:02x},Y", 2),
    0xAE: ("LDX", "${:04x}", 3), 0xBE: ("LDX", "${:04x},Y", 3),
    # LDY
    0xA0: ("LDY", "#${:02x}", 2), 0xA4: ("LDY", "${:02x}", 2), 0xB4: ("LDY", "${:02x},X", 2),
    0xAC: ("LDY", "${:04x}", 3), 0xBC: ("LDY", "${:04x},X", 3),
    # LSR
    0x4A: ("LSR", "A", 1), 0x46: ("LSR", "${:02x}", 2), 0x56: ("LSR", "${:02x},X", 2),
    0x4E: ("LSR", "${:04x}", 3), 0x5E: ("LSR", "${:04x},X", 3),
    # NOP
    0xEA: ("NOP", "", 1),
    # ORA
    0x09: ("ORA", "#${:02x}", 2), 0x05: ("ORA", "${:02x}", 2), 0x15: ("ORA", "${:02x},X", 2),
    0x0D: ("ORA", "${:04x}", 3), 0x1D: ("ORA", "${:04x},X", 3), 0x19: ("ORA", "${:04x},Y", 3),
    0x01: ("ORA", "(${:02x},X)", 2), 0x11: ("ORA", "(${:02x}),Y", 2),
    # PHA, PHP, PLA, PLP
    0x48: ("PHA", "", 1), 0x08: ("PHP", "", 1), 0x68: ("PLA", "", 1), 0x28: ("PLP", "", 1),
    # ROL
    0x2A: ("ROL", "A", 1), 0x26: ("ROL", "${:02x}", 2), 0x36: ("ROL", "${:02x},X", 2),
    0x2E: ("ROL", "${:04x}", 3), 0x3E: ("ROL", "${:04x},X", 3),
    # ROR
    0x6A: ("ROR", "A", 1), 0x66: ("ROR", "${:02x}", 2), 0x76: ("ROR", "${:02x},X", 2),
    0x6E: ("ROR", "${:04x}", 3), 0x7E: ("ROR", "${:04x},X", 3),
    # RTI, RTS
    0x40: ("RTI", "", 1), 0x60: ("RTS", "", 1),
    # SBC
    0xE9: ("SBC", "#${:02x}", 2), 0xE5: ("SBC", "${:02x}", 2), 0xF5: ("SBC", "${:02x},X", 2),
    0xED: ("SBC", "${:04x}", 3), 0xFD: ("SBC", "${:04x},X", 3), 0xF9: ("SBC", "${:04x},Y", 3),
    0xE1: ("SBC", "(${:02x},X)", 2), 0xF1: ("SBC", "(${:02x}),Y", 2),
    # SEC, SED, SEI
    0x38: ("SEC", "", 1), 0xF8: ("SED", "", 1), 0x78: ("SEI", "", 1),
    # STA
    0x85: ("STA", "${:02x}", 2), 0x95: ("STA", "${:02x},X", 2),
    0x8D: ("STA", "${:04x}", 3), 0x9D: ("STA", "${:04x},X", 3), 0x99: ("STA", "${:04x},Y", 3),
    0x81: ("STA", "(${:02x},X)", 2), 0x91: ("STA", "(${:02x}),Y", 2),
    # STX
    0x86: ("STX", "${:02x}", 2), 0x96: ("STX", "${:02x},Y", 2), 0x8E: ("STX", "${:04x}", 3),
    # STY
    0x84: ("STY", "${:02x}", 2), 0x94: ("STY", "${:02x},X", 2), 0x8C: ("STY", "${:04x}", 3),
    # TAX, TAY, TSX, TXA, TXS, TYA
    0xAA: ("TAX", "", 1), 0xA8: ("TAY", "", 1), 0xBA: ("TSX", "", 1),
    0x8A: ("TXA", "", 1), 0x9A: ("TXS", "", 1), 0x98: ("TYA", "", 1),
}


def parse_psid_header(data):
    """Parse PSID header."""
    magic = data[0:4].decode('ascii', errors='ignore')
    version = struct.unpack('>H', data[4:6])[0]
    load_addr = struct.unpack('>H', data[8:10])[0]
    init_addr = struct.unpack('>H', data[10:12])[0]
    play_addr = struct.unpack('>H', data[12:14])[0]

    name = data[0x16:0x36].decode('ascii', errors='ignore').rstrip('\x00')
    author = data[0x36:0x56].decode('ascii', errors='ignore').rstrip('\x00')
    copyright = data[0x56:0x76].decode('ascii', errors='ignore').rstrip('\x00')

    header_size = 0x7C if version == 2 else 0x76
    if load_addr == 0:
        load_addr = struct.unpack('<H', data[header_size:header_size+2])[0]

    return {
        'magic': magic,
        'version': version,
        'load_addr': load_addr,
        'init_addr': init_addr,
        'play_addr': play_addr,
        'header_size': header_size,
        'name': name,
        'author': author,
        'copyright': copyright
    }


def disassemble_instruction(data, pc, load_addr):
    """Disassemble a single instruction."""
    if pc >= len(data):
        return None

    opcode = data[pc]
    if opcode not in OPCODES:
        return {
            'addr': load_addr + pc,
            'bytes': [opcode],
            'mnemonic': 'DCB',
            'operand': f"${opcode:02x}",
            'size': 1,
            'comment': '; Unknown opcode'
        }

    mnem, operand_fmt, size = OPCODES[opcode]

    # Get instruction bytes
    instr_bytes = [data[pc + i] if pc + i < len(data) else 0 for i in range(size)]

    # Format operand
    if size == 1:
        operand = operand_fmt
    elif size == 2:
        operand_val = instr_bytes[1]
        # For branch instructions, calculate relative address
        if mnem in ['BCC', 'BCS', 'BEQ', 'BMI', 'BNE', 'BPL', 'BVC', 'BVS']:
            # Signed byte offset
            offset = operand_val if operand_val < 128 else operand_val - 256
            target = load_addr + pc + 2 + offset
            operand = f"${target:04x}"
        else:
            operand = operand_fmt.format(operand_val)
    else:  # size == 3
        operand_val = instr_bytes[1] | (instr_bytes[2] << 8)
        operand = operand_fmt.format(operand_val)

    return {
        'addr': load_addr + pc,
        'bytes': instr_bytes,
        'mnemonic': mnem,
        'operand': operand,
        'size': size,
        'comment': ''
    }


def disassemble_sid(sid_file, max_bytes=None):
    """Disassemble SID file."""
    with open(sid_file, 'rb') as f:
        data = f.read()

    header = parse_psid_header(data)
    music_data = data[header['header_size']:]

    # Limit disassembly
    if max_bytes:
        music_data = music_data[:max_bytes]

    instructions = []
    pc = 0

    while pc < len(music_data):
        instr = disassemble_instruction(music_data, pc, header['load_addr'])
        if instr:
            instructions.append(instr)
            pc += instr['size']
        else:
            break

    return header, instructions


def main():
    if len(sys.argv) < 2:
        print("Usage: python disassemble_sid.py <sid_file>")
        sys.exit(1)

    sid_file = sys.argv[1]
    header, instructions = disassemble_sid(sid_file)

    print(f"; {header['name']}")
    print(f"; {header['author']}")
    print(f"; {header['copyright']}")
    print(f";")
    print(f"; Load: ${header['load_addr']:04X}")
    print(f"; Init: ${header['init_addr']:04X}")
    print(f"; Play: ${header['play_addr']:04X}")
    print()

    for instr in instructions:  # All instructions
        addr_str = f"${instr['addr']:04X}"
        bytes_str = " ".join(f"{b:02X}" for b in instr['bytes'])
        bytes_str = f"{bytes_str:12}"

        # Format instruction
        if instr['operand']:
            asm = f"{instr['mnemonic']:6} {instr['operand']}"
        else:
            asm = instr['mnemonic']

        print(f"{addr_str}  {bytes_str}  {asm:20} {instr['comment']}")


if __name__ == '__main__':
    main()
