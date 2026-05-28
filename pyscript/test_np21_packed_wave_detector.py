"""Unit tests for sidm2.np21_packed_wave_detector.

The detector locates the NP21-G4 single-byte-packed wave table used by
the DRAX cluster (Colorama/Delicate/Dreams/Omniphunk) and Laxity's own
G4 files (21_G4_demo_tune_*, Ocean_Reloaded).

It is a FALLBACK detector — the packed-split idiom also appears at
pulse/filter sites in 2-byte-format players (Beast/Angular), so these
tests document that the detector must NOT be used to override a
successful 2-byte wave detection.
"""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.np21_packed_wave_detector import (
    detect_packed_wave_table,
    PackedWaveLayout,
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


# RE-verified wave table addresses (see memory/drax-np21-cluster-re.md)
_DRAX_EXPECTED = {
    "Colorama": 0x1BDD,
    "Delicate": 0x1C51,
    "Dreams": 0x1B8A,
    "Omniphunk": 0x1B73,
}

_LAXITY_G4 = ["21_G4_demo_tune_1", "21_G4_demo_tune_2",
              "21_G4_demo_tune_3", "Ocean_Reloaded"]


class TestDraxClusterDetection(unittest.TestCase):
    """The 4 DRAX 'None wired' files return their RE-verified wave tables."""

    def test_drax_files_match_expected_addresses(self):
        for name, expected in _DRAX_EXPECTED.items():
            load, binary = _load_sid(ROOT / "SID" / f"{name}.sid")
            result = detect_packed_wave_table(binary, load)
            self.assertIsNotNone(result, f"{name} should match")
            self.assertIsInstance(result, PackedWaveLayout)
            self.assertEqual(
                result.wave_table_addr, expected,
                f"{name}: expected wave table ${expected:04X}, "
                f"got ${result.wave_table_addr:04X}")
            # All four use the $C0 (high-2-bits) waveform mask.
            self.assertEqual(result.waveform_mask, 0xC0,
                             f"{name}: expected $C0 waveform mask")

    def test_wave_table_in_binary_range(self):
        for name in _DRAX_EXPECTED:
            load, binary = _load_sid(ROOT / "SID" / f"{name}.sid")
            result = detect_packed_wave_table(binary, load)
            self.assertGreaterEqual(result.wave_table_addr, load)
            self.assertLess(result.wave_table_addr, load + len(binary))


class TestLaxityG4Detection(unittest.TestCase):
    """Laxity's own G4 files share the single-byte format and match."""

    def test_laxity_g4_files_match(self):
        for name in _LAXITY_G4:
            load, binary = _load_sid(ROOT / "SID" / "Laxity" / f"{name}.sid")
            result = detect_packed_wave_table(binary, load)
            self.assertIsNotNone(result, f"{name} should match the G4 sig")
            self.assertEqual(result.waveform_mask, 0xC0)


class TestFallbackContract(unittest.TestCase):
    """Document the fallback contract: the detector mislocates on
    2-byte-format files (Beast/Angular), so callers must only consult
    it when the standard 2-byte detector fails."""

    def test_stinsen_does_not_match(self):
        """Stinsen uses a completely different player entry; no match."""
        load, binary = _load_sid(
            ROOT / "SID" / "Stinsens_Last_Night_of_89.sid")
        self.assertIsNone(detect_packed_wave_table(binary, load),
                          "Stinsen should not match the packed-wave sig")

    def test_beast_match_is_not_its_real_wave_table(self):
        """Beast's real wave table is $19AD/$19E7 (found by the 2-byte
        detector). The packed-wave signature matches Beast at a
        DIFFERENT address (a pulse/filter packed read), which is why
        this detector is fallback-only. This test pins that behavior so
        a future maintainer doesn't wire it as Beast's primary source."""
        load, binary = _load_sid(ROOT / "SID" / "Beast.sid")
        result = detect_packed_wave_table(binary, load)
        # It DOES match (the idiom is present), but NOT at Beast's real
        # wave table ($19AD). This documents the fallback necessity.
        if result is not None:
            self.assertNotEqual(
                result.wave_table_addr, 0x19AD,
                "if this ever equals Beast's real wave table the "
                "signature got more specific — revisit the fallback note")


class TestSyntheticBinaries(unittest.TestCase):
    def _build(self, tbl_addr=0x1B8A, load=0x1000, mask=0xC0):
        b = bytearray(0x1000)
        # Place the signature at offset $200.
        p = 0x200
        b[p:p + 6] = bytes([0xB9, tbl_addr & 0xFF, tbl_addr >> 8,
                            0xA8, 0x29, 0x0F])
        # Some filler, then TYA; AND #mask.
        b[p + 6:p + 12] = bytes([0x9D, 0x24, 0x19, 0x9D, 0x1E, 0x19])
        b[p + 12] = 0x98          # TYA
        b[p + 13] = 0x29          # AND #
        b[p + 14] = mask
        return bytes(b), load

    def test_synthetic_match(self):
        binary, load = self._build(tbl_addr=0x1B8A)
        result = detect_packed_wave_table(binary, load)
        self.assertIsNotNone(result)
        self.assertEqual(result.wave_table_addr, 0x1B8A)
        self.assertEqual(result.waveform_mask, 0xC0)

    def test_missing_tya_and_mask_rejected(self):
        """Signature prefix present but no TYA+AND# follow-up → no match."""
        binary, load = self._build()
        binary = bytearray(binary)
        # Wipe the TYA (98) at p+12
        binary[0x200 + 12] = 0xEA  # NOP
        # Also wipe any other 98 29 in the window
        for i in range(0x206, 0x220):
            if binary[i] == 0x98:
                binary[i] = 0xEA
        self.assertIsNone(detect_packed_wave_table(bytes(binary), load))

    def test_out_of_range_table_rejected(self):
        binary, load = self._build(tbl_addr=0x9999)  # past binary end
        self.assertIsNone(detect_packed_wave_table(binary, load))

    def test_no_low_nibble_mask_rejected(self):
        """B9...TAY but no AND #$0F → not the packed-split idiom."""
        b = bytearray(0x1000)
        p = 0x200
        b[p:p + 6] = bytes([0xB9, 0x8A, 0x1B, 0xA8, 0x29, 0xF0])  # #$F0 not #$0F
        result = detect_packed_wave_table(bytes(b), 0x1000)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
