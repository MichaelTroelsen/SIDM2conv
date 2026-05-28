"""Unit tests for sidm2.drax_record_table_detector.

Supersedes test_np21_packed_wave_detector (v3.5.67). The detector
LOCATES the DRAX/NP21-G4 8-byte-record table; it does NOT claim to
interpret the full record format (v3.5.68 correction — the table is
8-byte structured records, not a flat single-byte wave program).

It is a FALLBACK locator — the +0-field read idiom also appears at
pulse/filter sites in 2-byte-format players (Beast/Angular), so these
tests document that the locator must NOT override a successful 2-byte
detection.
"""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.drax_record_table_detector import (
    detect_drax_record_table,
    DraxRecordTableLayout,
)


ROOT = Path(__file__).parent.parent


def _load_sid(path: Path):
    raw = path.read_bytes()
    do = struct.unpack('>H', raw[6:8])[0]
    lo = struct.unpack('>H', raw[8:10])[0]
    body = raw[do:]
    if lo == 0:
        load = body[0] | (body[1] << 8)
        binary = body[2:]
    else:
        load = lo
        binary = body
    return load, binary


# RE-verified table LOCATIONS (semantics TBD — see
# memory/drax-np21-cluster-re.md).
_DRAX_EXPECTED = {
    "Colorama": 0x1BDD,
    "Delicate": 0x1C51,
    "Dreams": 0x1B8A,
    "Omniphunk": 0x1B73,
}

_LAXITY_G4 = ["21_G4_demo_tune_1", "21_G4_demo_tune_2",
              "21_G4_demo_tune_3", "Ocean_Reloaded"]


class TestDraxClusterDetection(unittest.TestCase):
    def test_drax_files_locate_expected_table(self):
        for name, expected in _DRAX_EXPECTED.items():
            load, binary = _load_sid(ROOT / "SID" / f"{name}.sid")
            result = detect_drax_record_table(binary, load)
            self.assertIsNotNone(result, f"{name} should match")
            self.assertIsInstance(result, DraxRecordTableLayout)
            self.assertEqual(
                result.record_table_addr, expected,
                f"{name}: expected record table ${expected:04X}, "
                f"got ${result.record_table_addr:04X}")
            self.assertEqual(result.field0_high_mask, 0xC0,
                             f"{name}: expected $C0 high-bit mask")

    def test_table_in_binary_range(self):
        for name in _DRAX_EXPECTED:
            load, binary = _load_sid(ROOT / "SID" / f"{name}.sid")
            result = detect_drax_record_table(binary, load)
            self.assertGreaterEqual(result.record_table_addr, load)
            self.assertLess(result.record_table_addr, load + len(binary))


class TestLaxityG4Detection(unittest.TestCase):
    def test_laxity_g4_files_match(self):
        for name in _LAXITY_G4:
            load, binary = _load_sid(ROOT / "SID" / "Laxity" / f"{name}.sid")
            result = detect_drax_record_table(binary, load)
            self.assertIsNotNone(result, f"{name} should match the G4 sig")
            self.assertEqual(result.field0_high_mask, 0xC0)


class TestFallbackContract(unittest.TestCase):
    def test_stinsen_does_not_match(self):
        load, binary = _load_sid(
            ROOT / "SID" / "Stinsens_Last_Night_of_89.sid")
        self.assertIsNone(detect_drax_record_table(binary, load))

    def test_beast_match_is_not_its_real_wave_table(self):
        """Beast's real wave table is $19AD (2-byte detector). The +0-field
        idiom matches Beast at a different address (pulse/filter read),
        documenting why this locator is fallback-only."""
        load, binary = _load_sid(ROOT / "SID" / "Beast.sid")
        result = detect_drax_record_table(binary, load)
        if result is not None:
            self.assertNotEqual(result.record_table_addr, 0x19AD)


class TestSyntheticBinaries(unittest.TestCase):
    def _build(self, tbl_addr=0x1B8A, load=0x1000, mask=0xC0):
        b = bytearray(0x1000)
        p = 0x200
        b[p:p + 6] = bytes([0xB9, tbl_addr & 0xFF, tbl_addr >> 8,
                            0xA8, 0x29, 0x0F])
        b[p + 6:p + 12] = bytes([0x9D, 0x24, 0x19, 0x9D, 0x1E, 0x19])
        b[p + 12] = 0x98
        b[p + 13] = 0x29
        b[p + 14] = mask
        return bytes(b), load

    def test_synthetic_match(self):
        binary, load = self._build(tbl_addr=0x1B8A)
        result = detect_drax_record_table(binary, load)
        self.assertIsNotNone(result)
        self.assertEqual(result.record_table_addr, 0x1B8A)
        self.assertEqual(result.field0_high_mask, 0xC0)

    def test_missing_tya_and_mask_rejected(self):
        binary, load = self._build()
        binary = bytearray(binary)
        for i in range(0x206, 0x220):
            if binary[i] == 0x98:
                binary[i] = 0xEA
        self.assertIsNone(detect_drax_record_table(bytes(binary), load))

    def test_out_of_range_table_rejected(self):
        binary, load = self._build(tbl_addr=0x9999)
        self.assertIsNone(detect_drax_record_table(binary, load))

    def test_no_low_nibble_mask_rejected(self):
        b = bytearray(0x1000)
        p = 0x200
        b[p:p + 6] = bytes([0xB9, 0x8A, 0x1B, 0xA8, 0x29, 0xF0])
        self.assertIsNone(detect_drax_record_table(bytes(b), 0x1000))


if __name__ == "__main__":
    unittest.main(verbosity=2)
