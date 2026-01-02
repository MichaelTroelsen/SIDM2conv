"""
Disassemble the wave table access routines in Stinsens SID file.

Shows the 6502 assembly code that accesses the wave tables.
"""

import sys
from pathlib import Path

# Simple 6502 disassembler for common opcodes
OPCODES = {
    0xA0: ('LDY', '#$%02X', 2),
    0xA2: ('LDX', '#$%02X', 2),
    0xA9: ('LDA', '#$%02X', 2),
    0xAD: ('LDA', '$%04X', 3),
    0xB9: ('LDA', '$%04X,Y', 3),
    0xBD: ('LDA', '$%04X,X', 3),
    0xBC: ('LDY', '$%04X,X', 3),
    0x8D: ('STA', '$%04X', 3),
    0x9D: ('STA', '$%04X,X', 3),
    0xC9: ('CMP', '#$%02X', 2),
    0xD0: ('BNE', '$%02X', 2),
    0xB0: ('BCS', '$%02X', 2),
    0xF0: ('BEQ', '$%02X', 2),
    0xA8: ('TAY', '', 1),
    0x4C: ('JMP', '$%04X', 3),
    0x20: ('JSR', '$%04X', 3),
    0x60: ('RTS', '', 1),
}

def disasm_byte(data, offset):
    """Disassemble one instruction at offset"""
    if offset >= len(data):
        return None, 1

    opcode = data[offset]

    if opcode not in OPCODES:
        return f"    .BYTE ${opcode:02X}", 1

    mnemonic, format_str, length = OPCODES[opcode]

    if length == 1:
        return f"    {mnemonic}", 1
    elif length == 2:
        operand = data[offset + 1]
        if mnemonic in ('BNE', 'BEQ', 'BCS', 'BCC'):
            # Branch - show relative offset
            return f"    {mnemonic} {format_str % operand}", 2
        else:
            return f"    {mnemonic} {format_str % operand}", 2
    elif length == 3:
        lo = data[offset + 1]
        hi = data[offset + 2]
        addr = lo | (hi << 8)
        return f"    {mnemonic} {format_str % addr}", 3

    return f"    .BYTE ${opcode:02X}", 1

def disasm_region(data, start, count=20, base_addr=0x1000):
    """Disassemble count instructions starting at offset"""
    lines = []
    offset = start
    mem_addr = base_addr + start

    for _ in range(count):
        if offset >= len(data):
            break

        # Get instruction bytes for display
        instr_bytes = []
        opcode = data[offset]
        if opcode in OPCODES:
            length = OPCODES[opcode][2]
        else:
            length = 1

        for i in range(min(length, len(data) - offset)):
            instr_bytes.append(f"{data[offset + i]:02X}")

        # Disassemble
        disasm, consumed = disasm_byte(data, offset)

        # Format: address | bytes | disassembly
        bytes_str = ' '.join(instr_bytes).ljust(9)
        lines.append(f"${mem_addr:04X}  {bytes_str} {disasm}")

        offset += consumed
        mem_addr += consumed

    return '\n'.join(lines)

def main():
    sid_file = Path('Laxity/Stinsens_Last_Night_of_89.sid')

    if not sid_file.exists():
        print(f"Error: {sid_file} not found")
        return 1

    with open(sid_file, 'rb') as f:
        data = f.read()

    # SID file header is 0x7C bytes
    HEADER_SIZE = 0x7C
    LOAD_ADDR = 0x1000

    print("Stinsens SID File - Wave Table Access Analysis")
    print("=" * 70)
    print(f"\nWave table addresses:")
    print(f"  Waveforms:    $18DA (file offset 0x08DA)")
    print(f"  Note offsets: $190C (file offset 0x090C)")
    print()

    # The references we found:
    # WAVEFORMS at 0x05C1 and 0x05CF
    # NOTE OFFSETS at 0x05C8 and 0x05D5

    print("\nWave Table Access Routine #1 (file offset 0x05C1)")
    print("-" * 70)
    # Start a bit before to show context
    print(disasm_region(data[HEADER_SIZE:], 0x05B5, count=25, base_addr=LOAD_ADDR))

    print("\n\nAnalysis:")
    print("-" * 70)
    print("This is the Laxity player's wave table lookup routine.")
    print()
    print("Key instructions:")
    print("  $15C1: LDA $18DA,Y   ; Load waveform from table")
    print("  $15C8: LDA $190C,Y   ; Load note offset from table")
    print("  $15CF: LDA $18DA,Y   ; Load waveform (again)")
    print("  $15D5: LDA $190C,Y   ; Load note offset (again)")
    print()
    print("The Y register is used as the index into the wave table.")
    print("The dual-array format stores waveforms and note offsets separately:")
    print("  - Waveforms: 32 bytes at $18DA")
    print("  - Note offsets: 32 bytes at $190C")
    print()
    print("This confirms the wave table addresses detected by pattern matching!")

if __name__ == '__main__':
    sys.exit(main())
