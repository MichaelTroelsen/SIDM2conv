"""Unit tests for sidm2.high_load_layout.

build_high_load_sf2 is used by minimal_embed_builder and
laxity_raw_np21_builder as a fallback for binaries that load near $F000
where there's insufficient post-binary space for the SF2 edit area.
The layout places the edit area BEFORE the binary (at $1000+).

Tests pin:
  - Returns (bytes, skip_aux=False) for representative high-load case
  - LOAD_BASE at $0D7E with magic 0x1337
  - Handlers at $0F90 (INIT/PLAY/STOP)
  - #211 scan bait at $0F9E (HANDLER_BASE + 14)
  - Edit area at $1000 (the SF2 placeholder)
  - Binary embedded byte-exact at sid_la
  - Returns None when sid_la too low (binary would overlap edit area)
  - Returns None when file would exceed 64K
"""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2 import high_load_layout


def _read_word(buf: bytes, off: int) -> int:
    return buf[off] | (buf[off + 1] << 8)


class TestSuccessfulBuild(unittest.TestCase):
    """Magic_Sound-class: sid_la=$F000, ~2.6KB binary."""

    def setUp(self):
        self.c64_data = bytes(range(256)) * 10   # 2560 bytes
        self.sid_la = 0xF000
        self.init_addr = 0xF0B9
        self.play_addr = 0xF0BF

    def test_returns_bytes_and_skip_aux_false(self):
        result = high_load_layout.build_high_load_sf2(
            self.c64_data, self.sid_la, self.init_addr, self.play_addr)
        self.assertIsNotNone(result)
        sf2_bytes, skip_aux = result
        self.assertIsInstance(sf2_bytes, bytes)
        self.assertFalse(skip_aux,
                         "high-load doesn't span $0FFB, so no need to skip aux")

    def test_load_base_is_0d7e(self):
        sf2, _ = high_load_layout.build_high_load_sf2(
            self.c64_data, self.sid_la, self.init_addr, self.play_addr)
        self.assertEqual(_read_word(sf2, 0), 0x0D7E)

    def test_magic_0x1337_present(self):
        sf2, _ = high_load_layout.build_high_load_sf2(
            self.c64_data, self.sid_la, self.init_addr, self.play_addr)
        self.assertEqual(_read_word(sf2, 2), 0x1337)

    def test_binary_embedded_at_sid_la(self):
        sf2, _ = high_load_layout.build_high_load_sf2(
            self.c64_data, self.sid_la, self.init_addr, self.play_addr)
        # File offset of binary = 2 + sid_la - LOAD_BASE
        off = 2 + self.sid_la - 0x0D7E
        self.assertEqual(bytes(sf2[off:off + len(self.c64_data)]),
                         self.c64_data,
                         "binary must be byte-identical at sid_la")

    def test_init_handler_jsrs_init_addr(self):
        sf2, _ = high_load_layout.build_high_load_sf2(
            self.c64_data, self.sid_la, self.init_addr, self.play_addr)
        # INIT_HANDLER at $0F90 — file offset = 2 + $0F90 - $0D7E
        hnd_off = 2 + 0x0F90 - 0x0D7E
        self.assertEqual(
            bytes(sf2[hnd_off:hnd_off + 4]),
            bytes([0x20, self.init_addr & 0xFF, self.init_addr >> 8, 0x60]),
            "INIT handler should be JSR init_addr; RTS"
        )

    def test_play_handler_jsrs_play_addr(self):
        sf2, _ = high_load_layout.build_high_load_sf2(
            self.c64_data, self.sid_la, self.init_addr, self.play_addr)
        hnd_off = 2 + 0x0F90 - 0x0D7E + 4   # PLAY_HANDLER = INIT + 4
        self.assertEqual(
            bytes(sf2[hnd_off:hnd_off + 4]),
            bytes([0x20, self.play_addr & 0xFF, self.play_addr >> 8, 0x60]),
        )

    def test_stop_handler_silences_voice3(self):
        sf2, _ = high_load_layout.build_high_load_sf2(
            self.c64_data, self.sid_la, self.init_addr, self.play_addr)
        hnd_off = 2 + 0x0F90 - 0x0D7E + 8   # STOP_HANDLER = INIT + 8
        # LDA #0; STA $D418; RTS
        self.assertEqual(
            bytes(sf2[hnd_off:hnd_off + 6]),
            bytes([0xA9, 0x00, 0x8D, 0x18, 0xD4, 0x60]),
        )

    def test_211_bait_at_0f9e(self):
        sf2, _ = high_load_layout.build_high_load_sf2(
            self.c64_data, self.sid_la, self.init_addr, self.play_addr)
        # BAIT_ADDR = HANDLER_BASE + 14 = $0F9E
        bait_off = 2 + 0x0F9E - 0x0D7E
        self.assertEqual(
            bytes(sf2[bait_off:bait_off + 4]),
            bytes([0x9D, 0x00, 0xD4, 0x60]),
            "scan bait should be STA $D400,X; RTS at $0F9E"
        )

    def test_edit_area_starts_at_1000(self):
        sf2, _ = high_load_layout.build_high_load_sf2(
            self.c64_data, self.sid_la, self.init_addr, self.play_addr)
        # Edit area at $1000 — first byte is OL ptr lo for voice 0,
        # which should be ol_track1_addr & 0xFF where
        # ol_track1_addr = $1000 + 6 + 2*$80 = $1106 → low byte = 0x06.
        edit_off = 2 + 0x1000 - 0x0D7E
        self.assertEqual(sf2[edit_off], 0x06,
                         "OL ptr lo for voice 0 should be low byte of ol_track1_addr")

    def test_file_size_within_64k(self):
        sf2, _ = high_load_layout.build_high_load_sf2(
            self.c64_data, self.sid_la, self.init_addr, self.play_addr)
        self.assertLess(len(sf2), 0x10000,
                        "PRG file must stay under 64KB")


class TestInfeasibility(unittest.TestCase):
    """Cases where high-load layout shouldn't fit."""

    def test_returns_none_when_sid_la_too_low(self):
        """sid_la < $2000 means binary would overlap edit area at $1000+."""
        result = high_load_layout.build_high_load_sf2(
            c64_data=bytes(256),
            sid_la=0x1500,
            init_addr=0x1500,
            play_addr=0x1503,
        )
        self.assertIsNone(result)

    def test_returns_none_when_binary_exceeds_64k(self):
        """sid_la + len(c64_data) > 64K → None.

        File size = 2 + (sid_la + len - LOAD_BASE). For overflow, we
        need that sum > 0x10000, i.e. sid_la + len > 0x10000 - 2 + LOAD_BASE
        = 0xEDFC. Use sid_la=$8000, binary=$7000 → ends at $F000
        → file_size = 2 + ($F000 - $0D7E) = $E284 (fits).
        Use sid_la=$8000, binary=$9000 → ends at $11000 → file_size
        = 2 + ($11000 - $0D7E) = $10284 (overflows).
        """
        result = high_load_layout.build_high_load_sf2(
            c64_data=bytes(0x9000),
            sid_la=0x8000,
            init_addr=0x8000,
            play_addr=0x8003,
        )
        self.assertIsNone(result)


class TestDifferentLoadAddresses(unittest.TestCase):
    """Tests across the high-load range."""

    def test_E000_load(self):
        # 1KB binary at $E000 — plenty of room post-binary; not strictly
        # "high-load" but the function should still work.
        result = high_load_layout.build_high_load_sf2(
            bytes(1024), 0xE000, 0xE000, 0xE003)
        self.assertIsNotNone(result)

    def test_F000_load_2613b(self):
        # Magic_Sound-class
        result = high_load_layout.build_high_load_sf2(
            bytes(2613), 0xF000, 0xF0B9, 0xF0BF)
        self.assertIsNotNone(result)

    def test_F000_load_3363b(self):
        # Crosswords-class
        result = high_load_layout.build_high_load_sf2(
            bytes(3363), 0xF000, 0xF000, 0xF006)
        self.assertIsNotNone(result)


class TestConstants(unittest.TestCase):
    def test_constants_match_normal_path(self):
        self.assertEqual(high_load_layout.LOAD_BASE, 0x0D7E)
        self.assertEqual(high_load_layout.HANDLER_BASE, 0x0F90)
        self.assertEqual(high_load_layout.EDIT_AREA_BASE, 0x1000)
        self.assertEqual(high_load_layout.MIN_POST_BINARY, 0x800)


if __name__ == "__main__":
    unittest.main(verbosity=2)
