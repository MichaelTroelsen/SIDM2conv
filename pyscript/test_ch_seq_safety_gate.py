"""Tests for sidm2.ch_seq_safety_gate.

The gate emulates the ch_seq_ptr → shadow patch under py65 and decides
whether patching $1A1C-$1A21 changes audio. Patch-safe = player uses
those bytes as ch_seq_ptr; patch-unsafe = player uses them for other
data (Dark_Fun-class).
"""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.ch_seq_safety_gate import is_ch_seq_patch_safe


def _parse_psid(path: Path):
    """Extract (c64_data, sid_la, init_addr, play_addr) from a PSID file."""
    data = path.read_bytes()
    do = struct.unpack(">H", data[6:8])[0]
    la = struct.unpack(">H", data[8:10])[0]
    ia = struct.unpack(">H", data[10:12])[0]
    pa = struct.unpack(">H", data[12:14])[0]
    c = data[do:]
    if la == 0:
        la = struct.unpack("<H", c[:2])[0]
        c = c[2:]
    if pa == 0:
        pa = ia + 3
    return c, la, ia, pa


class TestChSeqSafetyGate(unittest.TestCase):
    """Functional verification using real Laxity SID files in SID/."""

    SID_DIR = Path(__file__).parent.parent / "SID"

    def test_stinsen_passes_safety_gate(self):
        """Stinsen uses ch_seq_ptr standard layout — gate must pass."""
        path = self.SID_DIR / "Stinsens_Last_Night_of_89.sid"
        if not path.exists():
            self.skipTest(f"reference SID not present: {path}")
        c, la, ia, pa = _parse_psid(path)
        lo_off = 0x1A1C - la
        hi_off = 0x1A1F - la
        self.assertTrue(
            is_ch_seq_patch_safe(c, la, ia, pa, lo_off, hi_off, n_play=3),
            "Stinsen should pass the safety gate (real ch_seq_ptr layout)"
        )

    def test_unboxed_passes_safety_gate(self):
        """Unboxed also uses ch_seq_ptr — gate must pass."""
        path = self.SID_DIR / "Unboxed_Ending_8580.sid"
        if not path.exists():
            self.skipTest(f"reference SID not present: {path}")
        c, la, ia, pa = _parse_psid(path)
        lo_off = 0x1A1C - la
        hi_off = 0x1A1F - la
        self.assertTrue(
            is_ch_seq_patch_safe(c, la, ia, pa, lo_off, hi_off, n_play=3),
            "Unboxed should pass the safety gate"
        )

    def test_dark_fun_fails_safety_gate(self):
        """Dark_Fun has in-range pointer-shaped bytes at $1A1C-$1A21
        but the player uses them for a DATA table (LDA $1A1E,Y at
        $10C1), not as ch_seq_ptr. Patching corrupts the data → gate
        must catch this."""
        path = self.SID_DIR / "Laxity" / "Dark_Fun.sid"
        if not path.exists():
            self.skipTest(f"reference SID not present: {path}")
        c, la, ia, pa = _parse_psid(path)
        lo_off = 0x1A1C - la
        hi_off = 0x1A1F - la
        self.assertFalse(
            is_ch_seq_patch_safe(c, la, ia, pa, lo_off, hi_off, n_play=3),
            "Dark_Fun should FAIL the safety gate (bytes are data, "
            "not ch_seq_ptr — patching them corrupts audio)"
        )

    def test_out_of_range_pointers_rejected(self):
        """If the pointer bytes don't point into the binary, the gate
        returns False (we can't meaningfully test the patch)."""
        # Synthetic: 256B binary with $1A1C = $99 $99 $99 / $99 $99 $99
        # → pointers $9999 (way out of range)
        c64 = bytearray(0x800)
        c64[0:3] = bytes([0x4C, 0x10, 0x10])  # JMP $1010
        # Make $1A1C-$1A21 = 99 99 99 99 99 99
        lo_off = 0x1A1C - 0x1000
        for i in range(6):
            if lo_off + i < len(c64):
                c64[lo_off + i] = 0x99
        # Above $1800, so offsets 0xA1C+ are NOT inside the 0x800 binary.
        # Use larger binary so offsets ARE in range.
        c64 = bytearray(0xB00)
        c64[0:3] = bytes([0x4C, 0x10, 0x10])
        for i in range(6):
            c64[lo_off + i] = 0x99
        self.assertFalse(
            is_ch_seq_patch_safe(bytes(c64), 0x1000, 0x1010, 0x1013,
                                  lo_off, lo_off + 3, n_play=2),
            "out-of-range pointers must return False"
        )

    def test_offsets_outside_binary_rejected(self):
        """If lo_off/hi_off are outside the binary length, the gate
        returns False (can't read pointer bytes)."""
        c64 = bytes([0x4C, 0x10, 0x10] + [0] * 0x100)
        # offset 0x0A1C is past end (binary is only ~0x103 bytes)
        self.assertFalse(
            is_ch_seq_patch_safe(c64, 0x1000, 0x1010, 0x1013,
                                  0x0A1C, 0x0A1F, n_play=2),
            "out-of-bounds offsets must return False"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
