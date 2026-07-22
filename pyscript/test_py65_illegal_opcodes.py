"""Verifies bin/py65_illegal_opcodes.py's LAX/SBX patch against known
6502 illegal-opcode semantics -- see that module's own docstring for why
this patch exists (py65's stock MPU silently no-ops these, which cost a
full investigation session before being caught, see
docs/players/BLACKBIRD.md's "REPEAT=1 locate support" section)."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))

import py65_illegal_opcodes  # noqa: E402 -- patches MPU before any instance exists
from py65.devices.mpu6502 import MPU  # noqa: E402


def _mpu_at(pc, bytes_):
    m = MPU()
    for i, b in enumerate(bytes_):
        m.memory[(pc + i) & 0xFFFF] = b
    m.pc = pc
    return m


class TestLAX(unittest.TestCase):
    def test_lax_zp_loads_both_a_and_x(self):
        m = _mpu_at(0x1000, [0xa7, 0x50])  # LAX $50
        m.memory[0x50] = 0x42
        m.step()
        self.assertEqual(m.a, 0x42)
        self.assertEqual(m.x, 0x42)
        self.assertEqual(m.pc, 0x1002)

    def test_lax_sets_zero_flag(self):
        m = _mpu_at(0x1000, [0xa7, 0x50])
        m.memory[0x50] = 0x00
        m.step()
        self.assertEqual(m.a, 0)
        self.assertEqual(m.x, 0)
        self.assertTrue(m.p & m.ZERO)

    def test_lax_sets_negative_flag(self):
        m = _mpu_at(0x1000, [0xa7, 0x50])
        m.memory[0x50] = 0x80
        m.step()
        self.assertTrue(m.p & m.NEGATIVE)

    def test_lax_indirect_y(self):
        m = _mpu_at(0x1000, [0xb3, 0x50])  # LAX ($50),Y
        m.memory[0x50] = 0x00
        m.memory[0x51] = 0x30
        m.y = 2
        m.memory[0x3002] = 0x77
        m.step()
        self.assertEqual(m.a, 0x77)
        self.assertEqual(m.x, 0x77)


class TestSBX(unittest.TestCase):
    def test_sbx_basic_subtraction(self):
        # Blackbird's own usage: LAX zp_master (A=X=7), then SBX #7 -> X=0.
        m = _mpu_at(0x1000, [0xcb, 0x07])  # SBX #7
        m.a = 7
        m.x = 7
        m.step()
        self.assertEqual(m.x, 0)
        self.assertEqual(m.pc, 0x1002)
        self.assertTrue(m.p & m.CARRY, "no borrow -> carry set")
        self.assertTrue(m.p & m.ZERO)

    def test_sbx_ands_a_and_x_first(self):
        m = _mpu_at(0x1000, [0xcb, 0x02])  # SBX #2
        m.a = 0b1100
        m.x = 0b1010  # A & X = 0b1000 = 8
        m.step()
        self.assertEqual(m.x, 8 - 2)

    def test_sbx_borrow_clears_carry(self):
        m = _mpu_at(0x1000, [0xcb, 0x10])  # SBX #$10 -- operand > (A&X)
        m.a = 0x05
        m.x = 0x05
        m.step()
        self.assertFalse(m.p & m.CARRY, "borrow occurred -> carry clear")
        self.assertEqual(m.x, (5 - 0x10) & 0xFF)

    def test_sbx_matches_blackbird_countdown_sequence(self):
        """The exact real-hardware sequence this patch was built to fix:
        LAX $e6 (zp_master=21); SBX #7 -> X=14 (not the pre-patch
        silent-no-op value)."""
        m = _mpu_at(0x1000, [0xa7, 0xe6, 0xcb, 0x07])
        m.memory[0xe6] = 21
        m.step()  # LAX $e6
        self.assertEqual(m.a, 21)
        self.assertEqual(m.x, 21)
        m.step()  # SBX #7
        self.assertEqual(m.x, 14)


if __name__ == "__main__":
    unittest.main()
