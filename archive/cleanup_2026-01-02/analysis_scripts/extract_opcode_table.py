"""Extract opcode table from CPU6502Emulator.

This script parses cpu6502_emulator.py and extracts the complete opcode table
including mnemonics and addressing modes for use in the disassembler.
"""

import re
from pathlib import Path
from typing import Dict, Tuple, Optional


def parse_addressing_mode(comment: str) -> str:
    """Parse addressing mode from opcode comment.

    Examples:
        "ORA (zp,X)" -> "izx"    # Indexed indirect
        "ORA (zp),Y" -> "izy"    # Indirect indexed
        "ORA zp" -> "zp"         # Zero page
        "ORA zp,X" -> "zpx"      # Zero page,X
        "ORA zp,Y" -> "zpy"      # Zero page,Y
        "ORA abs" -> "abs"       # Absolute
        "ORA abs,X" -> "absx"    # Absolute,X
        "ORA abs,Y" -> "absy"    # Absolute,Y
        "ORA #imm" -> "imm"      # Immediate
        "ASL A" -> "acc"         # Accumulator
        "BPL" -> "rel"           # Relative (branches)
        "JMP" -> "abs" or "ind"  # Absolute or indirect
    """
    comment = comment.strip()

    # Accumulator
    if ' A' in comment or comment.endswith('A'):
        return 'acc'

    # Indexed indirect (zp,X)
    if '(zp,X)' in comment or '($' in comment and ',X)' in comment:
        return 'izx'

    # Indirect indexed (zp),Y
    if '(zp),Y' in comment or '($' in comment and '),Y' in comment:
        return 'izy'

    # Indirect (for JMP only)
    if 'ind' in comment.lower() or '($' in comment and ')' in comment and ',X)' not in comment:
        return 'ind'

    # Absolute,X
    if 'abs,X' in comment or '$' in comment and ',X' in comment and '(' not in comment:
        return 'absx'

    # Absolute,Y
    if 'abs,Y' in comment or '$' in comment and ',Y' in comment and '(' not in comment:
        return 'absy'

    # Absolute
    if 'abs' in comment or ('$' in comment and ',' not in comment and '(' not in comment):
        return 'abs'

    # Zero page,X
    if 'zp,X' in comment:
        return 'zpx'

    # Zero page,Y
    if 'zp,Y' in comment:
        return 'zpy'

    # Zero page
    if 'zp' in comment:
        return 'zp'

    # Immediate
    if '#imm' in comment or '#$' in comment or 'imm' in comment.lower():
        return 'imm'

    # Relative (branches)
    if any(mnem in comment for mnem in ['BPL', 'BMI', 'BVC', 'BVS', 'BCC', 'BCS', 'BNE', 'BEQ']):
        return 'rel'

    # Implied (no operands)
    return 'imp'


def parse_mnemonic(comment: str) -> str:
    """Extract mnemonic from comment.

    Examples:
        "ORA (zp,X)" -> "ORA"
        "ASL zp" -> "ASL"
        "BRK" -> "BRK"
    """
    # Take first word before space or (
    match = re.match(r'^([A-Z]{3})', comment.strip())
    if match:
        return match.group(1)
    return "???"


def extract_opcodes_from_source(source_file: Path) -> Dict[int, Tuple[str, str]]:
    """Extract opcode table from cpu6502_emulator.py.

    Returns:
        Dictionary mapping opcode (0x00-0xFF) to (mnemonic, addressing_mode)
    """
    opcodes: Dict[int, Tuple[str, str]] = {}

    # Read source file
    content = source_file.read_text()

    # Find all opcode handlers
    # Pattern: elif op == 0xNN:  # COMMENT
    single_pattern = re.compile(r"elif op == (0x[0-9A-Fa-f]{2}):\s*#\s*(.+)")

    # Pattern: elif op in (0xNN, 0xMM, ...):  # COMMENT
    multi_pattern = re.compile(r"elif op in \(([^)]+)\):\s*#\s*(.+)")

    # Pattern: if op == 0xNN:  # COMMENT (for BRK at start)
    if_pattern = re.compile(r"if op == (0x[0-9A-Fa-f]{2}):\s*#\s*(.+)")

    for line in content.split('\n'):
        # Try single opcode pattern
        match = single_pattern.search(line)
        if match:
            opcode = int(match.group(1), 16)
            comment = match.group(2)
            mnemonic = parse_mnemonic(comment)
            addr_mode = parse_addressing_mode(comment)
            opcodes[opcode] = (mnemonic, addr_mode)
            continue

        # Try if pattern (for BRK)
        match = if_pattern.search(line)
        if match:
            opcode = int(match.group(1), 16)
            comment = match.group(2)
            mnemonic = parse_mnemonic(comment)
            addr_mode = parse_addressing_mode(comment)
            opcodes[opcode] = (mnemonic, addr_mode)
            continue

        # Try multi-opcode pattern
        match = multi_pattern.search(line)
        if match:
            opcodes_str = match.group(1)
            comment = match.group(2)
            mnemonic = parse_mnemonic(comment)
            addr_mode = parse_addressing_mode(comment)

            # Parse all opcodes in the list
            for op_str in opcodes_str.split(','):
                op_str = op_str.strip()
                if op_str.startswith('0x'):
                    opcode = int(op_str, 16)
                    opcodes[opcode] = (mnemonic, addr_mode)

    return opcodes


def generate_opcode_table_code(opcodes: Dict[int, Tuple[str, str]]) -> str:
    """Generate Python code for the opcode table."""

    code = '''"""6502 Opcode Table for Disassembler.

This table was automatically extracted from CPU6502Emulator.
Each entry contains (mnemonic, addressing_mode) for all 256 opcodes.

Addressing modes:
    imp  - Implied (no operands)
    acc  - Accumulator
    imm  - Immediate (#$nn)
    zp   - Zero page ($nn)
    zpx  - Zero page,X ($nn,X)
    zpy  - Zero page,Y ($nn,Y)
    abs  - Absolute ($nnnn)
    absx - Absolute,X ($nnnn,X)
    absy - Absolute,Y ($nnnn,Y)
    izx  - Indexed indirect (($nn,X))
    izy  - Indirect indexed (($nn),Y)
    ind  - Indirect (($nnnn))
    rel  - Relative (branch target)
"""

OPCODE_TABLE = {
'''

    # Generate entries for all 256 opcodes
    for opcode in range(256):
        if opcode in opcodes:
            mnem, mode = opcodes[opcode]
            code += f'    0x{opcode:02X}: ("{mnem}", "{mode}"),\n'
        else:
            # Undefined opcode
            code += f'    0x{opcode:02X}: ("???", "imp"),\n'

    code += '}\n'

    return code


def main():
    """Main extraction script."""
    print("Extracting opcode table from CPU6502Emulator...")

    # Find cpu6502_emulator.py
    cpu_file = Path(__file__).parent.parent / "sidm2" / "cpu6502_emulator.py"

    if not cpu_file.exists():
        print(f"ERROR: File not found: {cpu_file}")
        return 1

    print(f"Reading {cpu_file}...")

    # Extract opcodes
    opcodes = extract_opcodes_from_source(cpu_file)

    print(f"Extracted {len(opcodes)} opcode definitions")

    # Generate code
    code = generate_opcode_table_code(opcodes)

    # Write to file
    output_file = Path(__file__).parent / "opcode_table.py"
    output_file.write_text(code)

    print(f"Written to {output_file}")
    print(f"\nSample opcodes:")
    for opcode in [0x00, 0x01, 0x09, 0x4C, 0x20, 0xA9, 0x8D, 0xEA]:
        if opcode in opcodes:
            mnem, mode = opcodes[opcode]
            print(f"  0x{opcode:02X}: {mnem:3} {mode}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
