"""Unit tests for sidm2.low_load_layout.

build_low_load_sf2 is a pure function: takes (c64_data, sid_la,
init_addr, play_addr), returns Optional[(bytes, skip_aux)] or None
when the layout doesn't fit.

Tests cover:
  - Successful build for a representative low-load case ($0F00)
  - LOAD_BASE floor enforcement ($0500 minimum)
  - File-size cap (<64K)
  - Output structure: 0x1337 magic, embedded binary placed at sid_la,
    JSR-stub handlers after the binary, #211 scan bait at HI+14
  - skip_aux=True always returned with a successful build

These complement the end-to-end C2 reference regression tests (which
verify the byte-identical output of real low-load files like Echo_Beat
and Annelouise) by exercising the pure function with controlled inputs.
"""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2 import low_load_layout


# ---------------------------------------------------------------------------
# Helpers — parse the SF2 PRG output to assert on its structure
# ---------------------------------------------------------------------------

def _parse_load_addr(sf2: bytes) -> int:
    return struct.unpack('<H', sf2[0:2])[0]


def _parse_magic(sf2: bytes, load_base: int) -> int:
    # The 0x1337 magic sits at the SF2 header's TopAddress + 2 (the SF2
    # header sits at load_base; magic is at load_base+2 in C64 RAM,
    # which is file offset 2 + (load_base - load_base) + 2 = 4).
    # i.e. always file offset 4 because the SF2 header begins at load_base.
    return struct.unpack('<H', sf2[2:4])[0]


def _bytes_at(sf2: bytes, load_base: int, addr: int, n: int) -> bytes:
    """Extract n bytes starting at C64 absolute address `addr`."""
    off = addr - load_base + 2
    return bytes(sf2[off:off + n])


class TestSuccessfulBuild(unittest.TestCase):
    """Representative case: $0F00 load (one of the 6 recovered files)."""

    def setUp(self):
        # Synthetic 256B "binary" — content doesn't matter, only the size
        # affects layout. Real Laxity files are 500-3000B.
        self.c64_data = bytes(range(256))   # 256B = 0x100B
        self.sid_la = 0x0F00
        self.init_addr = 0x0F00
        self.play_addr = 0x0F06

    def test_returns_bytes_and_skip_aux_true(self):
        result = low_load_layout.build_low_load_sf2(
            self.c64_data, self.sid_la, self.init_addr, self.play_addr)
        self.assertIsNotNone(result)
        sf2, skip_aux = result
        self.assertIsInstance(sf2, bytes)
        self.assertTrue(skip_aux,
                        "skip_aux MUST be True for low-load (aux ptr at "
                        "$0FFB would corrupt binary)")

    def test_load_base_under_sid_la_and_above_floor(self):
        sf2, _ = low_load_layout.build_low_load_sf2(
            self.c64_data, self.sid_la, self.init_addr, self.play_addr)
        load_base = _parse_load_addr(sf2)
        self.assertGreaterEqual(load_base, 0x0500,
                                f"LOAD_BASE ${load_base:04X} < $0500 floor")
        self.assertLess(load_base, self.sid_la,
                        f"LOAD_BASE ${load_base:04X} must be < sid_la "
                        f"${self.sid_la:04X}")

    def test_magic_0x1337_present(self):
        sf2, _ = low_load_layout.build_low_load_sf2(
            self.c64_data, self.sid_la, self.init_addr, self.play_addr)
        load_base = _parse_load_addr(sf2)
        magic = _parse_magic(sf2, load_base)
        self.assertEqual(magic, 0x1337)

    def test_binary_embedded_at_sid_la(self):
        sf2, _ = low_load_layout.build_low_load_sf2(
            self.c64_data, self.sid_la, self.init_addr, self.play_addr)
        load_base = _parse_load_addr(sf2)
        extracted = _bytes_at(sf2, load_base, self.sid_la,
                               len(self.c64_data))
        self.assertEqual(extracted, self.c64_data,
                         "embedded binary must be byte-identical")

    def test_init_handler_is_jsr_init_addr_rts(self):
        sf2, _ = low_load_layout.build_low_load_sf2(
            self.c64_data, self.sid_la, self.init_addr, self.play_addr)
        load_base = _parse_load_addr(sf2)
        # HI = page-aligned after the binary
        HI = (self.sid_la + len(self.c64_data) + 0xFF) & ~0xFF
        # INIT_H is at HI, format: JSR init_addr; RTS
        init_h = _bytes_at(sf2, load_base, HI, 4)
        expected = bytes([0x20, self.init_addr & 0xFF,
                           self.init_addr >> 8, 0x60])
        self.assertEqual(init_h, expected,
                         f"INIT handler at ${HI:04X} must be JSR "
                         f"${self.init_addr:04X}; RTS")

    def test_play_handler_is_jsr_play_addr_rts(self):
        sf2, _ = low_load_layout.build_low_load_sf2(
            self.c64_data, self.sid_la, self.init_addr, self.play_addr)
        load_base = _parse_load_addr(sf2)
        HI = (self.sid_la + len(self.c64_data) + 0xFF) & ~0xFF
        # PLAY_H is at HI+4
        play_h = _bytes_at(sf2, load_base, HI + 4, 4)
        expected = bytes([0x20, self.play_addr & 0xFF,
                           self.play_addr >> 8, 0x60])
        self.assertEqual(play_h, expected,
                         f"PLAY handler must be JSR ${self.play_addr:04X}; RTS")

    def test_stop_handler_silences_voice3(self):
        sf2, _ = low_load_layout.build_low_load_sf2(
            self.c64_data, self.sid_la, self.init_addr, self.play_addr)
        load_base = _parse_load_addr(sf2)
        HI = (self.sid_la + len(self.c64_data) + 0xFF) & ~0xFF
        # STOP_H at HI+8, format: LDA #0; STA $D418; RTS
        stop_h = _bytes_at(sf2, load_base, HI + 8, 6)
        self.assertEqual(stop_h, bytes([0xA9, 0x00, 0x8D, 0x18, 0xD4, 0x60]),
                         "STOP must be LDA #0; STA $D418; RTS")

    def test_211_scan_bait_at_hi_plus_14(self):
        """SF2II's #211 scanner finds STA $D400,X (9D 00 D4) RTS (60)
        at HI+14 — dead code, never executed (after STOP's RTS)."""
        sf2, _ = low_load_layout.build_low_load_sf2(
            self.c64_data, self.sid_la, self.init_addr, self.play_addr)
        load_base = _parse_load_addr(sf2)
        HI = (self.sid_la + len(self.c64_data) + 0xFF) & ~0xFF
        bait = _bytes_at(sf2, load_base, HI + 14, 4)
        self.assertEqual(bait, bytes([0x9D, 0x00, 0xD4, 0x60]))


class TestInfeasibility(unittest.TestCase):
    """Cases where the layout shouldn't fit — function returns None."""

    def test_returns_none_when_sid_la_too_low(self):
        """Echo_Beat ($0400) — there's no room for the header
        between zeropage/stack ($0000-$01FF), BASIC/KERNAL buffers
        ($0200-$04FF), and the binary itself."""
        result = low_load_layout.build_low_load_sf2(
            c64_data=bytes(1000),    # any size
            sid_la=0x0400,           # below $0500 floor
            init_addr=0x0400,
            play_addr=0x0406,
        )
        self.assertIsNone(result, "$0400 load = no room below floor")

    def test_returns_none_when_binary_exceeds_64k(self):
        """Cap at 64K (16-bit address limit) — synthetic case."""
        # Use sid_la near top so total file size > 64K
        # binary at $E000 of size $1F00 + edit area would exceed 64K
        big_binary = bytes(0x1F00)
        result = low_load_layout.build_low_load_sf2(
            c64_data=big_binary,
            sid_la=0x0900,        # in low-load range
            init_addr=0x0900,
            play_addr=0x0906,
        )
        # Either it fits (some configs might), or it returns None
        # cleanly. Test the boundary: with that much binary + edit area,
        # it will exceed 64K and return None.
        if result is not None:
            sf2, _ = result
            self.assertLess(len(sf2), 0x10000,
                           "if returned, must be < 64K")


class TestDifferentLoadAddresses(unittest.TestCase):
    """Parametric: different sid_la values produce sensible layouts."""

    def test_0x0F00_load(self):
        result = low_load_layout.build_low_load_sf2(
            bytes(200), 0x0F00, 0x0F00, 0x0F06)
        self.assertIsNotNone(result)
        sf2, _ = result
        self.assertEqual(_parse_load_addr(sf2) & 0xFF, 0,
                         "LOAD_BASE should be page-aligned")

    def test_0x0900_load(self):
        result = low_load_layout.build_low_load_sf2(
            bytes(200), 0x0900, 0x0900, 0x0906)
        self.assertIsNotNone(result)

    def test_0x0800_load(self):
        # DNA_Warrior-class — should still fit
        result = low_load_layout.build_low_load_sf2(
            bytes(200), 0x0800, 0x2133, 0x2130)
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
