"""Unit tests for sidm2.universal_211_workaround.

Pure-function tests of the SF2II #211 protection stamp. Synthetic
input buffers exercise the two paths:
  - Trampoline at $1000 + inert gap at $1006 → stamp `9D 00 D4`
  - No trampoline + no natural ABX/ABY $D40x write → append stub
                                                       + patch Block 1

These are tighter than the end-to-end SF2 structural tests because
they exercise the function directly with controlled bytes.
"""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2 import universal_211_workaround as u211


def _build_min_sf2(load_base: int = 0x0D7E,
                    bytes_at_1000: bytes = b"\x00" * 16) -> bytearray:
    """Build a minimal synthetic SF2 buffer:
      [load:2 LE][magic:2][Block 1 stub][0xFF][...zeros...][bytes_at_1000]
    Returns a bytearray ready for the workaround to inspect.
    """
    out = bytearray(0x2000)
    out[0:2] = load_base.to_bytes(2, 'little')
    out[2:4] = b"\x37\x13"  # 0x1337 magic
    # Block 1 (Descriptor) stub at file off 4. We need a valid format:
    # [Type:1=00][Size:2 LE = $1000][Name:'X'+NUL][CodeTop:2 LE][CodeSize:2 LE][3 ver bytes]
    b1_body = bytes([0x00,        # Type
                     0x00, 0x10,  # Size LE = $1000
                     ord('X'), 0x00,
                     0x00, 0x10,  # CodeTop = $1000
                     0x00, 0x09,  # CodeSize = $0900
                     1, 0, 0])    # ver bytes
    out[4] = 1                  # Block id
    out[5] = len(b1_body)
    out[6:6 + len(b1_body)] = b1_body
    out[6 + len(b1_body)] = 0xFF  # block chain end
    # Place bytes_at_1000 at the file offset corresponding to $1000
    one000_off = 0x1000 - load_base + 2
    out[one000_off:one000_off + len(bytes_at_1000)] = bytes_at_1000
    return out


class TestTrampolineStamp(unittest.TestCase):
    """When $1000 is `4C ?? ?? 4C ?? ??` and $1006 is `00 00 00`,
    stamp `9D 00 D4` at $1006."""

    def test_stamps_when_inert_gap(self):
        # 2-JMP trampoline + inert gap
        bytes_1000 = (
            bytes([0x4C, 0x00, 0x10,    # JMP $1000
                   0x4C, 0x03, 0x10])   # JMP $1003
            + b"\x00\x00\x00"            # $1006 = inert gap
            + b"\x00" * 7
        )
        out = _build_min_sf2(bytes_at_1000=bytes_1000)
        result = u211.ensure_sid_write_in_scan_window_universal(out)
        self.assertIsNotNone(result, "should return modified buffer")
        # Read $1006 from result
        load_base = 0x0D7E
        o1006 = 0x1006 - load_base + 2
        self.assertEqual(bytes(result[o1006:o1006 + 3]), b"\x9d\x00\xd4",
                          "$1006 should be stamped")

    def test_idempotent_when_already_stamped(self):
        bytes_1000 = (
            bytes([0x4C, 0x00, 0x10, 0x4C, 0x03, 0x10])
            + b"\x9d\x00\xd4"           # already stamped
            + b"\x00" * 7
        )
        out = _build_min_sf2(bytes_at_1000=bytes_1000)
        result = u211.ensure_sid_write_in_scan_window_universal(out)
        self.assertIsNone(result, "no change when already stamped")

    def test_skips_when_live_code_at_1006(self):
        bytes_1000 = (
            bytes([0x4C, 0x00, 0x10, 0x4C, 0x03, 0x10])
            + b"\xA9\x01\x85"           # LDA #$01; STA — live code
            + b"\x00" * 7
        )
        out = _build_min_sf2(bytes_at_1000=bytes_1000)
        result = u211.ensure_sid_write_in_scan_window_universal(out)
        self.assertIsNone(result, "live code at $1006 must be preserved")


class TestNaturalHit(unittest.TestCase):
    """When $1000 is live code AND a natural ABX/ABY $D40x write exists
    in the scan window, do nothing."""

    def test_skips_when_natural_abx_d404(self):
        # Live $1000: STA $D404,X (natural ABX write)
        bytes_1000 = bytes([0x9D, 0x04, 0xD4, 0x60]) + b"\x00" * 12
        out = _build_min_sf2(bytes_at_1000=bytes_1000)
        result = u211.ensure_sid_write_in_scan_window_universal(out)
        self.assertIsNone(result, "natural ABX write at $1000 = no change")


class TestDigidagFallback(unittest.TestCase):
    """When $1000 is live code AND no natural ABX/ABY $D40x write in
    the scan window, append a stub and patch Block 1."""

    def test_appends_stub_and_patches_block1(self):
        # Live $1000: PLA TYA PLA (Digidag's actual opening). No ABX $D40x.
        bytes_1000 = bytes([0x68, 0x98, 0x68]) + b"\x00" * 13
        out = _build_min_sf2(bytes_at_1000=bytes_1000)
        before_len = len(out)
        result = u211.ensure_sid_write_in_scan_window_universal(out)
        self.assertIsNotNone(result)
        # File got 4 bytes longer (stub appended)
        self.assertEqual(len(result), before_len + 4)
        # Stub is `9D 00 D4 60`
        self.assertEqual(bytes(result[-4:]), b"\x9d\x00\xd4\x60")
        # Block 1's CodeTop should now point at the stub
        load_base = 0x0D7E
        stub_addr = load_base + (before_len - 2)
        # Block 1 body offset: file off 6
        # body layout: Type(1) + Size(2) + Name(2: 'X' + NUL) + CodeTop(2) + CodeSize(2) + ver(3)
        ct_off = 6 + 1 + 2 + 2
        code_top = result[ct_off] | (result[ct_off + 1] << 8)
        self.assertEqual(code_top, stub_addr,
                          f"Block 1 CodeTop must point at stub ${stub_addr:04X}")
        code_size = result[ct_off + 2] | (result[ct_off + 3] << 8)
        self.assertEqual(code_size, 3, "stub region size = 3 (STA $D400,X)")


class TestNoOpEdgeCases(unittest.TestCase):
    """Buffers that shouldn't be touched."""

    def test_returns_none_for_tiny_buffer(self):
        result = u211.ensure_sid_write_in_scan_window_universal(bytearray(2))
        self.assertIsNone(result)

    def test_returns_none_when_1000_out_of_buffer(self):
        # Very small buffer that doesn't reach $1000
        out = bytearray([0x7E, 0x0D, 0x37, 0x13])  # load=$0D7E, magic
        result = u211.ensure_sid_write_in_scan_window_universal(out)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
