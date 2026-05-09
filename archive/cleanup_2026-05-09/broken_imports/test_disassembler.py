"""Comprehensive test suite for 6502 Disassembler.

Tests all addressing modes, edge cases, and real-world code patterns.
"""

import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from disassembler_6502 import Disassembler6502, Instruction


class TestDisassembler6502:
    """Test suite for 6502 disassembler."""

    @pytest.fixture
    def disasm(self):
        """Create fresh disassembler for each test."""
        return Disassembler6502()

    # ========================================================================
    # Addressing Mode Tests
    # ========================================================================

    def test_implied(self, disasm):
        """Test implied addressing mode."""
        tests = [
            (bytes([0x00]), "BRK"),  # BRK
            (bytes([0x18]), "CLC"),  # CLC
            (bytes([0x38]), "SEC"),  # SEC
            (bytes([0x58]), "CLI"),  # CLI
            (bytes([0x78]), "SEI"),  # SEI
            (bytes([0x98]), "TYA"),  # TYA
            (bytes([0xAA]), "TAX"),  # TAX
            (bytes([0xBA]), "TSX"),  # TSX
            (bytes([0xCA]), "DEX"),  # DEX
            (bytes([0xE8]), "INX"),  # INX
            (bytes([0xEA]), "NOP"),  # NOP
            (bytes([0x60]), "RTS"),  # RTS
            (bytes([0x40]), "RTI"),  # RTI
        ]

        for code, expected_mnem in tests:
            instr = disasm.disassemble_instruction(code, 0x1000)
            result = f"{instr.mnemonic} {instr.operand_str}".strip()
            assert result == expected_mnem, f"Expected {expected_mnem}, got {result}"

    def test_accumulator(self, disasm):
        """Test accumulator addressing mode."""
        tests = [
            (bytes([0x0A]), "ASL A"),  # ASL A
            (bytes([0x2A]), "ROL A"),  # ROL A
            (bytes([0x4A]), "LSR A"),  # LSR A
            (bytes([0x6A]), "ROR A"),  # ROR A
        ]

        for code, expected in tests:
            instr = disasm.disassemble_instruction(code, 0x1000)
            result = f"{instr.mnemonic} {instr.operand_str}".strip()
            assert result == expected, f"Expected {expected}, got {result}"

    def test_immediate(self, disasm):
        """Test immediate addressing mode."""
        tests = [
            (bytes([0xA9, 0x00]), "LDA #$00"),
            (bytes([0xA2, 0xFF]), "LDX #$FF"),
            (bytes([0xA0, 0x12]), "LDY #$12"),
            (bytes([0x09, 0x80]), "ORA #$80"),
            (bytes([0x29, 0x7F]), "AND #$7F"),
            (bytes([0x49, 0x42]), "EOR #$42"),
            (bytes([0xC9, 0x20]), "CMP #$20"),
            (bytes([0xE0, 0x18]), "CPX #$18"),
            (bytes([0xC0, 0x08]), "CPY #$08"),
        ]

        for code, expected in tests:
            instr = disasm.disassemble_instruction(code, 0x1000)
            result = f"{instr.mnemonic} {instr.operand_str}".strip()
            assert result == expected, f"Expected {expected}, got {result}"

    def test_zeropage(self, disasm):
        """Test zero page addressing mode."""
        tests = [
            (bytes([0xA5, 0x42]), "LDA $42"),
            (bytes([0x85, 0xFB]), "STA $FB"),
            (bytes([0xA6, 0x00]), "LDX $00"),
            (bytes([0x86, 0xFF]), "STX $FF"),
            (bytes([0x24, 0x01]), "BIT $01"),
            (bytes([0x06, 0x80]), "ASL $80"),
        ]

        for code, expected in tests:
            instr = disasm.disassemble_instruction(code, 0x1000)
            result = f"{instr.mnemonic} {instr.operand_str}".strip()
            assert result == expected, f"Expected {expected}, got {result}"

    def test_zeropage_x(self, disasm):
        """Test zero page,X addressing mode."""
        tests = [
            (bytes([0xB5, 0x42]), "LDA $42,X"),
            (bytes([0x95, 0xFB]), "STA $FB,X"),
            (bytes([0x16, 0x80]), "ASL $80,X"),
            (bytes([0x36, 0x90]), "ROL $90,X"),
        ]

        for code, expected in tests:
            instr = disasm.disassemble_instruction(code, 0x1000)
            result = f"{instr.mnemonic} {instr.operand_str}".strip()
            assert result == expected, f"Expected {expected}, got {result}"

    def test_zeropage_y(self, disasm):
        """Test zero page,Y addressing mode."""
        tests = [
            (bytes([0xB6, 0x42]), "LDX $42,Y"),
            (bytes([0x96, 0xFB]), "STX $FB,Y"),
        ]

        for code, expected in tests:
            instr = disasm.disassemble_instruction(code, 0x1000)
            result = f"{instr.mnemonic} {instr.operand_str}".strip()
            assert result == expected, f"Expected {expected}, got {result}"

    def test_absolute(self, disasm):
        """Test absolute addressing mode."""
        tests = [
            (bytes([0xAD, 0x00, 0xD4]), "LDA $D400"),
            (bytes([0x8D, 0x00, 0xD4]), "STA $D400"),
            (bytes([0xAE, 0x12, 0x34]), "LDX $3412"),
            (bytes([0x8E, 0x34, 0x12]), "STX $1234"),
            (bytes([0x4C, 0x00, 0x10]), "JMP $1000"),
            (bytes([0x20, 0x49, 0x13]), "JSR $1349"),
            (bytes([0x2C, 0x18, 0xD4]), "BIT $D418"),
        ]

        for code, expected in tests:
            instr = disasm.disassemble_instruction(code, 0x1000)
            result = f"{instr.mnemonic} {instr.operand_str}".strip()
            assert result == expected, f"Expected {expected}, got {result}"

    def test_absolute_x(self, disasm):
        """Test absolute,X addressing mode."""
        tests = [
            (bytes([0xBD, 0x00, 0xD4]), "LDA $D400,X"),
            (bytes([0x9D, 0x00, 0xD4]), "STA $D400,X"),
            (bytes([0x1E, 0x00, 0x10]), "ASL $1000,X"),
            (bytes([0x3E, 0x00, 0x20]), "ROL $2000,X"),
        ]

        for code, expected in tests:
            instr = disasm.disassemble_instruction(code, 0x1000)
            result = f"{instr.mnemonic} {instr.operand_str}".strip()
            assert result == expected, f"Expected {expected}, got {result}"

    def test_absolute_y(self, disasm):
        """Test absolute,Y addressing mode."""
        tests = [
            (bytes([0xB9, 0x00, 0xD4]), "LDA $D400,Y"),
            (bytes([0x99, 0x00, 0xD4]), "STA $D400,Y"),
            (bytes([0xBE, 0x00, 0x1A]), "LDX $1A00,Y"),
        ]

        for code, expected in tests:
            instr = disasm.disassemble_instruction(code, 0x1000)
            result = f"{instr.mnemonic} {instr.operand_str}".strip()
            assert result == expected, f"Expected {expected}, got {result}"

    def test_indexed_indirect(self, disasm):
        """Test indexed indirect (zp,X) addressing mode."""
        tests = [
            (bytes([0xA1, 0x42]), "LDA ($42,X)"),
            (bytes([0x81, 0xFB]), "STA ($FB,X)"),
            (bytes([0x01, 0x80]), "ORA ($80,X)"),
            (bytes([0x21, 0x90]), "AND ($90,X)"),
        ]

        for code, expected in tests:
            instr = disasm.disassemble_instruction(code, 0x1000)
            result = f"{instr.mnemonic} {instr.operand_str}".strip()
            assert result == expected, f"Expected {expected}, got {result}"

    def test_indirect_indexed(self, disasm):
        """Test indirect indexed (zp),Y addressing mode."""
        tests = [
            (bytes([0xB1, 0x42]), "LDA ($42),Y"),
            (bytes([0x91, 0xFB]), "STA ($FB),Y"),
            (bytes([0x11, 0x80]), "ORA ($80),Y"),
            (bytes([0x31, 0x90]), "AND ($90),Y"),
        ]

        for code, expected in tests:
            instr = disasm.disassemble_instruction(code, 0x1000)
            result = f"{instr.mnemonic} {instr.operand_str}".strip()
            assert result == expected, f"Expected {expected}, got {result}"

    def test_indirect(self, disasm):
        """Test indirect addressing mode (JMP only)."""
        tests = [
            (bytes([0x6C, 0x00, 0x03]), "JMP ($0300)"),
            (bytes([0x6C, 0xFC, 0xFF]), "JMP ($FFFC)"),
        ]

        for code, expected in tests:
            instr = disasm.disassemble_instruction(code, 0x1000)
            result = f"{instr.mnemonic} {instr.operand_str}".strip()
            assert result == expected, f"Expected {expected}, got {result}"

    def test_relative(self, disasm):
        """Test relative addressing mode (branches)."""
        # Branch forward
        instr = disasm.disassemble_instruction(bytes([0xD0, 0x0E]), 0x1000)
        assert instr.operand_str == "$1010"  # 0x1000 + 2 + 0x0E = 0x1010

        # Branch backward (negative offset)
        instr = disasm.disassemble_instruction(bytes([0xD0, 0xFB]), 0x1009)
        assert instr.operand_str == "$1006"  # 0x1009 + 2 + (-5) = 0x1006

        # All branch opcodes
        branches = [
            (0x10, "BPL"),
            (0x30, "BMI"),
            (0x50, "BVC"),
            (0x70, "BVS"),
            (0x90, "BCC"),
            (0xB0, "BCS"),
            (0xD0, "BNE"),
            (0xF0, "BEQ"),
        ]

        for opcode, mnem in branches:
            instr = disasm.disassemble_instruction(bytes([opcode, 0x00]), 0x1000)
            assert instr.mnemonic == mnem

    # ========================================================================
    # Edge Cases
    # ========================================================================

    def test_empty_buffer(self, disasm):
        """Test disassembly of empty buffer."""
        instr = disasm.disassemble_instruction(bytes([]), 0x1000)
        assert instr.is_code is False

    def test_incomplete_instruction(self, disasm):
        """Test incomplete instruction (missing operand bytes)."""
        # LDA abs needs 2 operand bytes, but only 1 provided
        instr = disasm.disassemble_instruction(bytes([0xAD, 0x00]), 0x1000)
        assert instr.is_code is False

    def test_undefined_opcode(self, disasm):
        """Test undefined/illegal opcodes."""
        # These are marked as ??? in the table
        undefined = [0x02, 0x03, 0x04, 0x07, 0x0B, 0x0C, 0x0F]

        for opcode in undefined:
            instr = disasm.disassemble_instruction(bytes([opcode]), 0x1000)
            assert instr.mnemonic == "???" or instr.mnemonic == "JAM"

    def test_instruction_size(self, disasm):
        """Test instruction size calculation."""
        tests = [
            (bytes([0xEA]), 1),              # NOP (implied)
            (bytes([0xA9, 0x00]), 2),        # LDA #$00 (immediate)
            (bytes([0x8D, 0x00, 0xD4]), 3),  # STA $D400 (absolute)
        ]

        for code, expected_size in tests:
            instr = disasm.disassemble_instruction(code, 0x1000)
            assert instr.size == expected_size

    # ========================================================================
    # Real-World Code Patterns
    # ========================================================================

    def test_sid_clear_routine(self, disasm):
        """Test classic SID register clear routine."""
        code = bytes([
            0xA9, 0x00,        # LDA #$00
            0xAA,              # TAX
            0x9D, 0x00, 0xD4,  # STA $D400,X
            0xE8,              # INX
            0xE0, 0x18,        # CPX #$18
            0xD0, 0xF9,        # BNE $1003
            0x60,              # RTS
        ])

        instructions = disasm.disassemble_range(code, 0x1000, len(code))

        assert len(instructions) == 7
        assert instructions[0].mnemonic == "LDA"
        assert instructions[1].mnemonic == "TAX"
        assert instructions[2].mnemonic == "STA"
        assert instructions[6].mnemonic == "RTS"

    def test_laxity_init_pattern(self, disasm):
        """Test Laxity player initialization pattern."""
        code = bytes([
            0x78,              # SEI
            0xA9, 0x00,        # LDA #$00
            0x8D, 0x12, 0xD4,  # STA $D412
        ])

        instructions = disasm.disassemble_range(code, 0x1000, len(code))

        assert len(instructions) == 3
        assert instructions[0].mnemonic == "SEI"
        assert instructions[1].operand_str == "#$00"
        assert instructions[2].operand_str == "$D412"

    def test_jsr_rts_pattern(self, disasm):
        """Test JSR/RTS subroutine pattern."""
        code = bytes([
            0x20, 0x00, 0x20,  # JSR $2000
            0xA9, 0x00,        # LDA #$00
            0x60,              # RTS
        ])

        instructions = disasm.disassemble_range(code, 0x1000, len(code))

        assert instructions[0].mnemonic == "JSR"
        assert instructions[0].operand_str == "$2000"
        assert instructions[2].mnemonic == "RTS"

    def test_loop_pattern(self, disasm):
        """Test typical loop pattern."""
        code = bytes([
            0xA2, 0x00,        # LDX #$00
            0xBD, 0x00, 0x10,  # LDA $1000,X
            0xE8,              # INX
            0xE0, 0x10,        # CPX #$10
            0xD0, 0xF8,        # BNE $1003
        ])

        instructions = disasm.disassemble_range(code, 0x1000, len(code))

        assert len(instructions) == 5
        assert instructions[4].addr_mode == "rel"

    # ========================================================================
    # Output Formatting
    # ========================================================================

    def test_listing_format_with_hex(self, disasm):
        """Test formatted listing output with hex bytes."""
        code = bytes([0xA9, 0x00, 0x60])
        instructions = disasm.disassemble_range(code, 0x1000, len(code))
        listing = disasm.format_listing(instructions, show_hex=True)

        assert "$1000:" in listing
        assert "A9 00" in listing
        assert "LDA #$00" in listing
        assert "$1002:" in listing
        assert "60" in listing
        assert "RTS" in listing

    def test_listing_format_without_hex(self, disasm):
        """Test formatted listing output without hex bytes."""
        code = bytes([0xA9, 0x00, 0x60])
        instructions = disasm.disassemble_range(code, 0x1000, len(code))
        listing = disasm.format_listing(instructions, show_hex=False)

        assert "$1000:" in listing
        assert "LDA #$00" in listing
        assert "A9 00" not in listing  # Hex should not be present

    def test_uppercase_lowercase(self):
        """Test uppercase vs lowercase mnemonics."""
        disasm_upper = Disassembler6502(uppercase=True)
        disasm_lower = Disassembler6502(uppercase=False)

        code = bytes([0xA9, 0x00])

        instr_upper = disasm_upper.disassemble_instruction(code, 0x1000)
        instr_lower = disasm_lower.disassemble_instruction(code, 0x1000)

        assert instr_upper.mnemonic == "LDA"
        assert instr_lower.mnemonic == "lda"

    # ========================================================================
    # Operand Size Tests
    # ========================================================================

    def test_operand_sizes(self, disasm):
        """Test operand size calculation for all addressing modes."""
        assert disasm.get_operand_size('imp') == 0
        assert disasm.get_operand_size('acc') == 0
        assert disasm.get_operand_size('imm') == 1
        assert disasm.get_operand_size('zp') == 1
        assert disasm.get_operand_size('zpx') == 1
        assert disasm.get_operand_size('zpy') == 1
        assert disasm.get_operand_size('rel') == 1
        assert disasm.get_operand_size('izx') == 1
        assert disasm.get_operand_size('izy') == 1
        assert disasm.get_operand_size('abs') == 2
        assert disasm.get_operand_size('absx') == 2
        assert disasm.get_operand_size('absy') == 2
        assert disasm.get_operand_size('ind') == 2

    # ========================================================================
    # Boundary Conditions
    # ========================================================================

    def test_address_wrap(self, disasm):
        """Test address wrapping at $FFFF."""
        # Branch from $FFFE with offset +5 should wrap to $0005
        instr = disasm.disassemble_instruction(bytes([0xD0, 0x05]), 0xFFFE)
        # $FFFE + 2 (instruction size) + 5 (offset) = $10005 -> wraps to $0005
        assert instr.operand_str == "$0005"

    def test_negative_branch(self, disasm):
        """Test negative branch offset."""
        # Branch with offset -5 (0xFB)
        instr = disasm.disassemble_instruction(bytes([0xD0, 0xFB]), 0x1009)
        # $1009 + 2 - 5 = $1006
        assert instr.operand_str == "$1006"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
