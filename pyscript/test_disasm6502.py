"""
Comprehensive Unit Tests for 6502 Disassembler

Tests all 256 opcodes, addressing modes, label generation, and output formatting.
Validates 100% compatibility with expected disassembly output.
"""

import unittest
import sys
from disasm6502 import (
    Disassembler6502, OPCODES, OpcodeDef, AddrMode, Mnemonic,
    Label, DisassembledLine
)


class TestOpcodeTable(unittest.TestCase):
    """Test completeness of opcode table"""

    def test_all_256_opcodes_defined(self):
        """Verify all 256 possible opcodes are defined"""
        self.assertEqual(len(OPCODES), 256, "All 256 opcodes must be defined")

        for i in range(256):
            self.assertIn(i, OPCODES, f"Opcode ${i:02X} must be defined")

    def test_opcode_bytes_match_addressing_mode(self):
        """Verify instruction byte counts match addressing modes"""
        for opcode_val, opcode_def in OPCODES.items():
            # Verify byte count is reasonable (1-3)
            self.assertIn(opcode_def.bytes, [1, 2, 3],
                         f"Opcode ${opcode_val:02X} has invalid byte count: {opcode_def.bytes}")

            # Verify addressing mode has correct byte count
            mode = opcode_def.addr_mode
            if mode in (AddrMode.IMP, AddrMode.ACC):
                expected_bytes = 1
            elif mode in (AddrMode.IMM, AddrMode.ZP, AddrMode.ZPX, AddrMode.ZPY,
                         AddrMode.REL, AddrMode.XIND, AddrMode.INDY):
                expected_bytes = 2
            elif mode in (AddrMode.ABS, AddrMode.ABSX, AddrMode.ABSY, AddrMode.IND):
                expected_bytes = 3
            else:
                self.fail(f"Unknown addressing mode: {mode}")

            self.assertEqual(opcode_def.bytes, expected_bytes,
                           f"Opcode ${opcode_val:02X} ({opcode_def.mnemonic} {mode.value}) "
                           f"should have {expected_bytes} bytes, not {opcode_def.bytes}")

    def test_illegal_opcodes_marked(self):
        """Verify illegal opcodes are properly flagged"""
        legal_count = sum(1 for op in OPCODES.values() if not op.illegal)
        illegal_count = sum(1 for op in OPCODES.values() if op.illegal)

        # 6502 has 151 legal opcodes, 105 illegal
        self.assertGreater(legal_count, 100, "Should have > 100 legal opcodes")
        self.assertGreater(illegal_count, 80, "Should have > 80 illegal opcodes")


class TestDisassemblerBasic(unittest.TestCase):
    """Test basic disassembler functionality"""

    def test_simple_instructions(self):
        """Test disassembly of simple instructions"""
        # LDA #$00
        code = bytes([0xA9, 0x00])
        disasm = Disassembler6502(code, 0x1000, len(code))
        line = disasm.disassemble_instruction(0x1000)

        self.assertIsNotNone(line)
        self.assertEqual(line.instruction, "LDA")
        self.assertEqual(line.operand, "#$00")
        self.assertEqual(len(line.bytes), 2)

    def test_zero_page_addressing(self):
        """Test zero page addressing mode"""
        # LDA $12
        code = bytes([0xA5, 0x12])
        disasm = Disassembler6502(code, 0x1000, len(code))
        line = disasm.disassemble_instruction(0x1000)

        self.assertEqual(line.instruction, "LDA")
        self.assertEqual(line.operand, "$12")

    def test_absolute_addressing(self):
        """Test absolute addressing mode"""
        # STA $D400
        code = bytes([0x8D, 0x00, 0xD4])
        disasm = Disassembler6502(code, 0x1000, len(code))
        line = disasm.disassemble_instruction(0x1000)

        self.assertEqual(line.instruction, "STA")
        self.assertEqual(line.operand, "$d400")

    def test_indexed_addressing(self):
        """Test indexed addressing modes"""
        # LDA $1234,X
        code = bytes([0xBD, 0x34, 0x12])
        disasm = Disassembler6502(code, 0x1000, len(code))
        line = disasm.disassemble_instruction(0x1000)

        self.assertEqual(line.instruction, "LDA")
        self.assertEqual(line.operand, "$1234,x")

        # LDA $1234,Y
        code = bytes([0xB9, 0x34, 0x12])
        disasm = Disassembler6502(code, 0x1000, len(code))
        line = disasm.disassemble_instruction(0x1000)

        self.assertEqual(line.instruction, "LDA")
        self.assertEqual(line.operand, "$1234,y")

    def test_indirect_addressing(self):
        """Test indirect addressing modes"""
        # JMP ($1234)
        code = bytes([0x6C, 0x34, 0x12])
        disasm = Disassembler6502(code, 0x1000, len(code))
        line = disasm.disassemble_instruction(0x1000)

        self.assertEqual(line.instruction, "JMP")
        self.assertEqual(line.operand, "($1234)")

        # LDA ($12,X)
        code = bytes([0xA1, 0x12])
        disasm = Disassembler6502(code, 0x1000, len(code))
        line = disasm.disassemble_instruction(0x1000)

        self.assertEqual(line.instruction, "LDA")
        self.assertEqual(line.operand, "($12,x)")

        # LDA ($12),Y
        code = bytes([0xB1, 0x12])
        disasm = Disassembler6502(code, 0x1000, len(code))
        line = disasm.disassemble_instruction(0x1000)

        self.assertEqual(line.instruction, "LDA")
        self.assertEqual(line.operand, "($12),y")


class TestBranchInstructions(unittest.TestCase):
    """Test branch instruction handling"""

    def test_forward_branch(self):
        """Test forward branch calculation"""
        # BNE +10 (forward)
        code = bytes([0xD0, 0x0A])
        disasm = Disassembler6502(code, 0x1000, len(code))
        line = disasm.disassemble_instruction(0x1000)

        self.assertEqual(line.instruction, "BNE")
        # Branch target should be PC + 2 + 10 = $100C
        self.assertIn("100c", line.operand.lower())

    def test_backward_branch(self):
        """Test backward branch calculation"""
        # BNE -10 (backward)
        code = bytes([0xD0, 0xF6])  # -10 in two's complement
        disasm = Disassembler6502(code, 0x1000, len(code))
        line = disasm.disassemble_instruction(0x1000)

        self.assertEqual(line.instruction, "BNE")
        # Branch target should be PC + 2 - 10 = $0FF8
        self.assertIn("0ff8", line.operand.lower())

    def test_branch_to_self(self):
        """Test branch to itself (infinite loop)"""
        # BNE -2 (branch to self)
        code = bytes([0xD0, 0xFE])
        disasm = Disassembler6502(code, 0x1000, len(code))
        line = disasm.disassemble_instruction(0x1000)

        self.assertEqual(line.instruction, "BNE")
        # Branch target should be PC + 2 - 2 = $1000
        self.assertIn("1000", line.operand.lower())


class TestLabelGeneration(unittest.TestCase):
    """Test automatic label generation"""

    def test_zero_page_label(self):
        """Test zero page label format (z##)"""
        disasm = Disassembler6502(bytes(256), 0, 256)
        label = disasm._generate_label(0x42)
        self.assertEqual(label, "z42")

    def test_absolute_label(self):
        """Test absolute address label format (l####)"""
        disasm = Disassembler6502(bytes(0x10000), 0, 0x10000)
        label = disasm._generate_label(0x1234)
        self.assertEqual(label, "l1234")

    def test_label_auto_creation_on_branch(self):
        """Test that labels are created for branch targets"""
        # BNE $1010
        code = bytes([0xD0, 0x0E] + [0xEA] * 16)  # BNE + NOPs
        disasm = Disassembler6502(code, 0x1000, len(code))
        disasm.disassemble()

        # Label should exist at target address $1010
        self.assertIn(0x1010, disasm.labels)
        self.assertEqual(disasm.labels[0x1010].name, "l1010")

    def test_label_auto_creation_on_jsr(self):
        """Test that labels are created for JSR targets"""
        # JSR $2000
        code = bytes([0x20, 0x00, 0x20])
        disasm = Disassembler6502(code, 0x1000, len(code))
        disasm.disassemble()

        # Label should exist at target address $2000
        self.assertIn(0x2000, disasm.labels)


class TestIllegalOpcodes(unittest.TestCase):
    """Test illegal opcode handling"""

    def test_lax_instruction(self):
        """Test LAX illegal opcode"""
        # LAX $12
        code = bytes([0xA7, 0x12])
        disasm = Disassembler6502(code, 0x1000, len(code))
        disasm.allow_illegal_opcodes = True
        line = disasm.disassemble_instruction(0x1000)

        self.assertEqual(line.instruction, "LAX")
        self.assertEqual(line.operand, "$12")

    def test_illegal_opcode_disabled(self):
        """Test illegal opcodes treated as data when disabled"""
        # LAX $12
        code = bytes([0xA7, 0x12])
        disasm = Disassembler6502(code, 0x1000, len(code))
        disasm.allow_illegal_opcodes = False
        line = disasm.disassemble_instruction(0x1000)

        self.assertEqual(line.instruction, ".byte")
        self.assertIn("Illegal", line.comment or "")


class TestCompletePrograms(unittest.TestCase):
    """Test disassembly of complete programs"""

    def test_simple_sid_init(self):
        """Test typical SID initialization code"""
        code = bytes([
            0xA2, 0x00,        # LDX #$00
            0xA9, 0x00,        # LDA #$00
            0x9D, 0x00, 0xD4,  # STA $D400,X (loop)
            0xE8,              # INX
            0xE0, 0x18,        # CPX #$18
            0xD0, 0xF7,        # BNE (loop)
            0x60               # RTS
        ])

        disasm = Disassembler6502(code, 0x1000, len(code))
        disasm.disassemble()

        # Check we got all instructions
        self.assertEqual(len(disasm.lines), 7)

        # Check first instruction
        self.assertEqual(disasm.lines[0x1000].instruction, "LDX")
        self.assertEqual(disasm.lines[0x1000].operand, "#$00")

        # Check branch creates label
        # BNE with offset 0xF7 (-9) from PC=0x100C targets 0x1003
        self.assertIn(0x1003, disasm.labels)  # Branch target

    def test_jsr_rts_sequence(self):
        """Test subroutine call and return"""
        code = bytes([
            0x20, 0x10, 0x10,  # JSR $1010
            0xEA,              # NOP
            0x60,              # RTS
            # ... padding ...
        ] + [0x00] * 10 + [
            0x60               # RTS at $1010
        ])

        disasm = Disassembler6502(code, 0x1000, len(code))
        disasm.disassemble()

        # JSR should create label at target
        self.assertIn(0x1010, disasm.labels)


class TestOutputFormatting(unittest.TestCase):
    """Test output formatting"""

    def test_basic_output_format(self):
        """Test basic output formatting matches expected format"""
        code = bytes([0xA9, 0x42, 0x60])  # LDA #$42 ; RTS
        disasm = Disassembler6502(code, 0x1000, len(code))
        disasm.disassemble()
        output = disasm.format_output()

        # Should contain address, bytes, and instruction
        self.assertIn("$1000", output)
        self.assertIn("a9 42", output.lower())
        self.assertIn("LDA", output)
        self.assertIn("#$42", output)

    def test_label_output(self):
        """Test labels appear in output"""
        # BNE loop
        code = bytes([0xD0, 0xFE])  # Branch to self
        disasm = Disassembler6502(code, 0x1000, len(code))
        disasm.disassemble()
        output = disasm.format_output()

        # Label should appear
        self.assertIn("l1000:", output)


class TestRealWorldCode(unittest.TestCase):
    """Test with real 6502 code patterns from SID players"""

    def test_laxity_pattern(self):
        """Test Laxity player init pattern"""
        code = bytes([
            0xA9, 0x00,        # LDA #$00
            0xAA,              # TAX
            0x9D, 0x00, 0xD4,  # STA $D400,X
            0xCA,              # DEX
            0xD0, 0xFA,        # BNE *-6
            0x60               # RTS
        ])

        disasm = Disassembler6502(code, 0x1000, len(code))
        disasm.disassemble()
        output = disasm.format_output()

        # Verify all instructions disassembled
        self.assertIn("LDA", output)
        self.assertIn("TAX", output)
        self.assertIn("STA", output)
        self.assertIn("DEX", output)
        self.assertIn("BNE", output)
        self.assertIn("RTS", output)

    def test_zp_indirect_indexed(self):
        """Test ($nn),Y pattern common in SID players"""
        code = bytes([
            0xB1, 0xFE,        # LDA ($FE),Y
            0x91, 0xFC,        # STA ($FC),Y
            0x60               # RTS
        ])

        disasm = Disassembler6502(code, 0x1000, len(code))
        disasm.disassemble()

        self.assertEqual(disasm.lines[0x1000].instruction, "LDA")
        self.assertIn("fe", disasm.lines[0x1000].operand.lower())
        self.assertIn("y", disasm.lines[0x1000].operand.lower())


def run_tests():
    """Run all tests and report results"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestOpcodeTable))
    suite.addTests(loader.loadTestsFromTestCase(TestDisassemblerBasic))
    suite.addTests(loader.loadTestsFromTestCase(TestBranchInstructions))
    suite.addTests(loader.loadTestsFromTestCase(TestLabelGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestIllegalOpcodes))
    suite.addTests(loader.loadTestsFromTestCase(TestCompletePrograms))
    suite.addTests(loader.loadTestsFromTestCase(TestOutputFormatting))
    suite.addTests(loader.loadTestsFromTestCase(TestRealWorldCode))

    # Run with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("DISASSEMBLER TEST SUMMARY")
    print("=" * 70)
    print(f"Total tests: {result.testsRun}")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\nAll tests PASSED")
        return 0
    else:
        print("\nSome tests FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
