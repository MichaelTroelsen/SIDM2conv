"""Unit tests for sidm2.vibrants_2000ad_detector.

The detector identifies files using the 1988 2000 A.D. cluster
shared player (Echo_Beat + Galax_it_y). Tests use both real cluster
files AND non-cluster files to verify true-positive and true-negative
behavior.
"""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.vibrants_2000ad_detector import (
    detect_2000ad_layout,
    Vibrants2000ADLayout,
)


ROOT = Path(__file__).parent.parent


def _load_sid(name: str):
    """Return (load_addr, c64_binary, copyright_str) for a Laxity SID."""
    sid = (ROOT / "SID" / "Laxity" / f"{name}.sid").read_bytes()
    do = struct.unpack('>H', sid[6:8])[0]
    c64_data = sid[do:]
    psid_load = struct.unpack('>H', sid[8:10])[0]
    if psid_load == 0:
        load = c64_data[0] | (c64_data[1] << 8)
        binary = c64_data[2:]
    else:
        load = psid_load
        binary = c64_data
    copyright = sid[0x56:0x76].rstrip(b'\x00').decode('latin-1', errors='replace')
    return load, binary, copyright


def _build_synthetic_2000ad_binary(load: int = 0x1000) -> bytes:
    """Build a minimal 1KB binary with the 2000 A.D. signature + valid
    orderlist ptrs, for testing the detector in isolation."""
    binary = bytearray(0x800)
    # Signature at [0..15]
    binary[0:3]   = bytes([0x4C, 0x4B, 0x14])   # JMP $144B
    binary[3:6]   = bytes([0x4C, 0x83, 0x14])   # JMP $1483
    binary[6:9]   = bytes([0x2C, 0xA3, 0x14])   # BIT $14A3
    binary[9:12]  = bytes([0x30, 0x01, 0x60])   # BMI +1; RTS
    binary[12:16] = bytes([0xA9, 0x00, 0x8D, 0x0E])  # LDA #$00; STA $0E,…
    # Voice orderlist ptrs at $493 / $496 — point at $107A0/$1A3/$1A6 (in-range)
    # In-range means load <= addr < load + len(binary).
    binary[0x493] = 0xA0  # V0 LO
    binary[0x494] = 0xA3  # V1 LO
    binary[0x495] = 0xA6  # V2 LO
    binary[0x496] = 0x17  # V0 HI (= $17A0)
    binary[0x497] = 0x17  # V1 HI (= $17A3)
    binary[0x498] = 0x17  # V2 HI (= $17A6)
    # Padding to make file load=$1000 → $17A0 within range
    # binary is 0x800 bytes; load=$1000 → ends at $1800. $17A0 in range.
    return bytes(binary)


class TestRealClusterFiles(unittest.TestCase):
    def test_echo_beat_matches(self):
        load, binary, copyright = _load_sid("Echo_Beat")
        result = detect_2000ad_layout(binary, load, copyright)
        self.assertIsNotNone(result, "Echo_Beat should be detected")
        self.assertIsInstance(result, Vibrants2000ADLayout)
        # Expected per RE: voice OL addrs at $0A47/$0A50/$0A54 for Echo_Beat
        self.assertEqual(result.voice_orderlist_addrs,
                         (0x0A47, 0x0A50, 0x0A54))
        self.assertEqual(result.voice_orderlist_lo_addr, 0x0400 + 0x493)
        self.assertEqual(result.voice_orderlist_hi_addr, 0x0400 + 0x496)
        self.assertEqual(result.pattern_ptr_lo_addr, 0x0400 + 0x788)
        self.assertEqual(result.pattern_ptr_hi_addr, 0x0400 + 0x78E)

    def test_galax_it_y_matches(self):
        load, binary, copyright = _load_sid("Galax_it_y")
        result = detect_2000ad_layout(binary, load, copyright)
        self.assertIsNotNone(result, "Galax_it_y should be detected")
        # Expected per RE: voice OL addrs at $17A8/$17AB/$17AE for Galax_it_y
        self.assertEqual(result.voice_orderlist_addrs,
                         (0x17A8, 0x17AB, 0x17AE))


class TestNonClusterRejection(unittest.TestCase):
    """These files should NOT match — false positives would corrupt
    edit propagation."""

    def test_james_bond_theme_remix_rejected(self):
        """Same '1988 2000 A.D.' copyright but DIFFERENT player —
        no signature match."""
        load, binary, copyright = _load_sid("James_Bond_Theme_Remix")
        result = detect_2000ad_layout(binary, load, copyright)
        self.assertIsNone(result,
                          "James_Bond is a separate player despite same copyright")

    def test_2000_A_D_rejected(self):
        """2000_A_D.sid is a Wizax-A V20 (different player) with the
        same '2000 A.D.' era label — must not match."""
        load, binary, copyright = _load_sid("2000_A_D")
        result = detect_2000ad_layout(binary, load, copyright)
        self.assertIsNone(result, "2000_A_D is Wizax-A, not 2000 A.D. cluster")

    def test_stinsen_rejected(self):
        load, binary, copyright = _load_sid("Stinsens_Last_Night_of_89")
        self.assertIsNone(detect_2000ad_layout(binary, load, copyright))

    def test_crosswords_rejected(self):
        load, binary, copyright = _load_sid("Crosswords")
        self.assertIsNone(detect_2000ad_layout(binary, load, copyright))

    def test_magic_sound_rejected(self):
        load, binary, copyright = _load_sid("Magic_Sound")
        self.assertIsNone(detect_2000ad_layout(binary, load, copyright))


class TestSyntheticBinaries(unittest.TestCase):
    """Test detector behavior with hand-crafted binaries."""

    def test_synthetic_match(self):
        """A synthetic binary with the right signature + ptrs matches."""
        binary = _build_synthetic_2000ad_binary(load=0x1000)
        result = detect_2000ad_layout(binary, 0x1000)
        self.assertIsNotNone(result)
        self.assertEqual(result.voice_orderlist_addrs,
                         (0x17A0, 0x17A3, 0x17A6))

    def test_bad_byte_at_offset_0_rejected(self):
        """A binary with a different byte at offset 0 doesn't match."""
        binary = bytearray(_build_synthetic_2000ad_binary(load=0x1000))
        binary[0] = 0xEA   # NOP instead of JMP
        result = detect_2000ad_layout(bytes(binary), 0x1000)
        self.assertIsNone(result)

    def test_bad_byte_at_offset_9_rejected(self):
        """Bit pattern check at offsets 9-14: BMI/+1/RTS/LDA #0/STA."""
        binary = bytearray(_build_synthetic_2000ad_binary(load=0x1000))
        binary[9] = 0xEA   # NOP instead of BMI
        result = detect_2000ad_layout(bytes(binary), 0x1000)
        self.assertIsNone(result)

    def test_too_short_buffer_rejected(self):
        """Buffer < 16 bytes can't have the signature."""
        result = detect_2000ad_layout(bytes(10), 0x1000)
        self.assertIsNone(result)

    def test_orderlist_ptrs_out_of_range_rejected(self):
        """Sig matches but ptrs at $493/$496 don't point in-range."""
        binary = bytearray(_build_synthetic_2000ad_binary(load=0x1000))
        # Point orderlist V0 at $9999 (out of range for $1000-$1800)
        binary[0x493] = 0x99   # V0 LO
        binary[0x496] = 0x99   # V0 HI → $9999
        result = detect_2000ad_layout(bytes(binary), 0x1000)
        self.assertIsNone(result)

    def test_buffer_shorter_than_orderlist_offset_rejected(self):
        """Sig matches but buffer is too short to reach offset $493."""
        binary = bytearray(0x400)   # 1024B, < $493 + 3
        # Add the signature
        binary[0:3]   = bytes([0x4C, 0x4B, 0x14])
        binary[3:6]   = bytes([0x4C, 0x83, 0x14])
        binary[6:9]   = bytes([0x2C, 0xA3, 0x14])
        binary[9:12]  = bytes([0x30, 0x01, 0x60])
        binary[12:16] = bytes([0xA9, 0x00, 0x8D, 0x0E])
        result = detect_2000ad_layout(bytes(binary), 0x1000)
        self.assertIsNone(result, "binary too short for ptrs at $493")


class TestReturnValue(unittest.TestCase):
    def test_layout_fields(self):
        """Verify the named tuple fields are populated correctly."""
        load, binary, copyright = _load_sid("Galax_it_y")
        result = detect_2000ad_layout(binary, load, copyright)
        self.assertEqual(result.voice_orderlist_lo_addr, load + 0x493)
        self.assertEqual(result.voice_orderlist_hi_addr, load + 0x496)
        self.assertEqual(result.pattern_ptr_lo_addr, load + 0x788)
        self.assertEqual(result.pattern_ptr_hi_addr, load + 0x78E)
        self.assertEqual(len(result.voice_orderlist_addrs), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
