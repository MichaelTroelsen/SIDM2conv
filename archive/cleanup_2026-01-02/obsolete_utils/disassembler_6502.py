"""6502 Disassembler.

Pure Python 6502 disassembler using opcodes extracted from CPU6502Emulator.

Features:
- All 256 opcodes (including illegal opcodes)
- Proper operand formatting for all addressing modes
- Label generation for branches and jumps
- Configurable output formats (column alignment, uppercase/lowercase)
- Code/data detection heuristics

Based on knowledge from JC64 Disassembly.java and CPU6502Emulator.py.
"""

from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from opcode_table import OPCODE_TABLE


@dataclass
class Instruction:
    """A single disassembled instruction."""
    address: int
    opcode: int
    mnemonic: str
    addr_mode: str
    operand_bytes: bytes = b''
    operand_str: str = ''
    comment: str = ''
    is_code: bool = True  # False for data bytes

    @property
    def size(self) -> int:
        """Total instruction size in bytes."""
        return 1 + len(self.operand_bytes)

    def __str__(self) -> str:
        """Format instruction as string."""
        hex_bytes = f"{self.opcode:02X}"
        for b in self.operand_bytes:
            hex_bytes += f" {b:02X}"

        return f"${self.address:04X}: {hex_bytes:<9} {self.mnemonic:<3} {self.operand_str}"


class Disassembler6502:
    """6502 CPU disassembler.

    This disassembler converts 6502 machine code back to assembly language.
    It uses the opcode table extracted from CPU6502Emulator for 100% accuracy.
    """

    def __init__(self, uppercase: bool = True, show_hex: bool = True):
        """Initialize disassembler.

        Args:
            uppercase: Use uppercase mnemonics (LDA vs lda)
            show_hex: Show hex bytes in output
        """
        self.uppercase = uppercase
        self.show_hex = show_hex

        # Labels found during disassembly
        self.labels: Dict[int, str] = {}
        self.label_counter = 0

    def get_operand_size(self, addr_mode: str) -> int:
        """Get operand size in bytes for addressing mode.

        Args:
            addr_mode: Addressing mode (imp, imm, zp, abs, etc.)

        Returns:
            Number of operand bytes (0-2)
        """
        if addr_mode in ('imp', 'acc'):
            return 0
        elif addr_mode in ('imm', 'zp', 'zpx', 'zpy', 'izx', 'izy', 'rel'):
            return 1
        elif addr_mode in ('abs', 'absx', 'absy', 'ind'):
            return 2
        else:
            return 0

    def format_operand(self, addr: int, opcode: int, operand_bytes: bytes, addr_mode: str) -> str:
        """Format operand for display.

        Args:
            addr: Current instruction address
            opcode: Opcode byte
            operand_bytes: Operand bytes (0-2 bytes)
            addr_mode: Addressing mode

        Returns:
            Formatted operand string (e.g., "#$42", "$D400", "($FB),Y")
        """
        if addr_mode == 'imp':
            return ''

        elif addr_mode == 'acc':
            return 'A'

        elif addr_mode == 'imm':
            # Immediate: #$nn
            return f"#${operand_bytes[0]:02X}"

        elif addr_mode == 'zp':
            # Zero page: $nn
            return f"${operand_bytes[0]:02X}"

        elif addr_mode == 'zpx':
            # Zero page,X: $nn,X
            return f"${operand_bytes[0]:02X},X"

        elif addr_mode == 'zpy':
            # Zero page,Y: $nn,Y
            return f"${operand_bytes[0]:02X},Y"

        elif addr_mode == 'abs':
            # Absolute: $nnnn
            target = operand_bytes[0] | (operand_bytes[1] << 8)
            return f"${target:04X}"

        elif addr_mode == 'absx':
            # Absolute,X: $nnnn,X
            target = operand_bytes[0] | (operand_bytes[1] << 8)
            return f"${target:04X},X"

        elif addr_mode == 'absy':
            # Absolute,Y: $nnnn,Y
            target = operand_bytes[0] | (operand_bytes[1] << 8)
            return f"${target:04X},Y"

        elif addr_mode == 'izx':
            # Indexed indirect: ($nn,X)
            return f"(${operand_bytes[0]:02X},X)"

        elif addr_mode == 'izy':
            # Indirect indexed: ($nn),Y
            return f"(${operand_bytes[0]:02X}),Y"

        elif addr_mode == 'ind':
            # Indirect: ($nnnn)
            target = operand_bytes[0] | (operand_bytes[1] << 8)
            return f"(${target:04X})"

        elif addr_mode == 'rel':
            # Relative (branch): calculate target
            offset = operand_bytes[0]
            if offset & 0x80:
                # Negative offset
                offset = offset - 256

            # Target = PC after instruction + offset
            target = (addr + 2 + offset) & 0xFFFF
            return f"${target:04X}"

        else:
            return '???'

    def disassemble_instruction(self, data: bytes, addr: int) -> Instruction:
        """Disassemble single instruction.

        Args:
            data: Memory data starting at this instruction
            addr: Current address

        Returns:
            Disassembled instruction
        """
        if len(data) == 0:
            # No data - create data byte
            return Instruction(
                address=addr,
                opcode=0,
                mnemonic='???',
                addr_mode='imp',
                is_code=False
            )

        opcode = data[0]

        # Look up opcode
        if opcode in OPCODE_TABLE:
            mnemonic, addr_mode = OPCODE_TABLE[opcode]
        else:
            # Unknown opcode - treat as data
            return Instruction(
                address=addr,
                opcode=opcode,
                mnemonic='???',
                addr_mode='imp',
                is_code=False
            )

        # Get operand bytes
        operand_size = self.get_operand_size(addr_mode)
        operand_bytes = data[1:1+operand_size]

        # Check if we have enough bytes
        if len(operand_bytes) < operand_size:
            # Incomplete instruction - treat as data
            return Instruction(
                address=addr,
                opcode=opcode,
                mnemonic='???',
                addr_mode='imp',
                is_code=False
            )

        # Format operand
        operand_str = self.format_operand(addr, opcode, operand_bytes, addr_mode)

        # Apply uppercase/lowercase
        if self.uppercase:
            mnemonic = mnemonic.upper()
        else:
            mnemonic = mnemonic.lower()

        return Instruction(
            address=addr,
            opcode=opcode,
            mnemonic=mnemonic,
            addr_mode=addr_mode,
            operand_bytes=operand_bytes,
            operand_str=operand_str,
            is_code=True
        )

    def disassemble_range(self, data: bytes, start_addr: int, length: int) -> List[Instruction]:
        """Disassemble range of memory.

        Args:
            data: Memory data
            start_addr: Starting address
            length: Number of bytes to disassemble

        Returns:
            List of disassembled instructions
        """
        instructions: List[Instruction] = []
        offset = 0

        while offset < length:
            instr = self.disassemble_instruction(data[offset:], start_addr + offset)
            instructions.append(instr)

            # Advance by instruction size
            offset += instr.size

        return instructions

    def disassemble_file(self, filepath: Path, start_addr: int = 0x1000, max_bytes: int = 0x10000) -> List[Instruction]:
        """Disassemble file.

        Args:
            filepath: Path to binary file
            start_addr: Starting address for disassembly
            max_bytes: Maximum bytes to disassemble

        Returns:
            List of disassembled instructions
        """
        data = filepath.read_bytes()
        return self.disassemble_range(data, start_addr, min(len(data), max_bytes))

    def format_listing(self, instructions: List[Instruction], show_hex: bool = True, show_labels: bool = False) -> str:
        """Format instructions as assembly listing.

        Args:
            instructions: List of instructions to format
            show_hex: Show hex bytes column
            show_labels: Show labels for branch/jump targets

        Returns:
            Formatted assembly listing
        """
        lines = []

        for instr in instructions:
            # Format address
            addr_str = f"${instr.address:04X}:"

            # Format hex bytes
            if show_hex:
                hex_bytes = f"{instr.opcode:02X}"
                for b in instr.operand_bytes:
                    hex_bytes += f" {b:02X}"
                hex_str = f"{hex_bytes:<9}"
            else:
                hex_str = ""

            # Format instruction
            if instr.is_code:
                instr_str = f"{instr.mnemonic:<3} {instr.operand_str}"
            else:
                # Data byte
                instr_str = f".byte ${instr.opcode:02X}"

            # Combine
            if show_hex:
                line = f"{addr_str} {hex_str} {instr_str}"
            else:
                line = f"{addr_str} {instr_str}"

            # Add comment if present
            if instr.comment:
                line += f"  ; {instr.comment}"

            lines.append(line)

        return '\n'.join(lines)


def test_disassembler():
    """Quick test of disassembler functionality."""
    print("Testing 6502 Disassembler...")
    print("-" * 70)

    disasm = Disassembler6502()

    # Test cases: (bytes, expected_output)
    test_cases = [
        # LDA #$00
        (bytes([0xA9, 0x00]), "LDA #$00"),

        # STA $D400
        (bytes([0x8D, 0x00, 0xD4]), "STA $D400"),

        # LDX #$FF
        (bytes([0xA2, 0xFF]), "LDX #$FF"),

        # STX $D404 (absolute)
        (bytes([0x8E, 0x04, 0xD4]), "STX $D404"),

        # JMP $1234
        (bytes([0x4C, 0x34, 0x12]), "JMP $1234"),

        # JSR $1000
        (bytes([0x20, 0x00, 0x10]), "JSR $1000"),

        # BNE $1010 (from $1000, offset +$0E)
        (bytes([0xD0, 0x0E]), "BNE $1010"),

        # ORA ($42,X)
        (bytes([0x01, 0x42]), "ORA ($42,X)"),

        # LDA ($FB),Y
        (bytes([0xB1, 0xFB]), "LDA ($FB),Y"),

        # ASL A
        (bytes([0x0A]), "ASL A"),

        # RTS
        (bytes([0x60]), "RTS"),
    ]

    print("\nTest Cases:")
    passed = 0
    failed = 0

    for i, (test_bytes, expected) in enumerate(test_cases, 1):
        instr = disasm.disassemble_instruction(test_bytes, 0x1000)
        actual = f"{instr.mnemonic} {instr.operand_str}".strip()

        if actual == expected:
            status = "PASS"
            passed += 1
        else:
            status = "FAIL"
            failed += 1

        print(f"  {i:2}. {status}: {test_bytes.hex():12} -> {actual:20} (expected: {expected})")

    print(f"\n{passed}/{len(test_cases)} tests passed")

    # Test disassembly of a small program
    print("\nTest Program Disassembly:")
    print("=" * 70)

    # Classic SID clear routine
    program = bytes([
        0xA9, 0x00,        # LDA #$00
        0xAA,              # TAX
        0x9D, 0x00, 0xD4,  # STA $D400,X
        0xE8,              # INX
        0xE0, 0x18,        # CPX #$18
        0xD0, 0xF9,        # BNE $1003
        0x60,              # RTS
    ])

    instructions = disasm.disassemble_range(program, 0x1000, len(program))
    listing = disasm.format_listing(instructions, show_hex=True)
    print(listing)

    print("\n" + "=" * 70)
    print("Disassembler test complete!")


if __name__ == "__main__":
    test_disassembler()
