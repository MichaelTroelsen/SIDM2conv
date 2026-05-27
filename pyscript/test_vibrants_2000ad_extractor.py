"""Unit tests for sidm2.vibrants_2000ad_extractor.

Tests cover the orderlist walker, pattern walker, and per-voice stream
emission. Integration with `np21_edit_area_builder` is exercised
separately in `test_sf2_writer.py`.
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
from sidm2.vibrants_2000ad_extractor import extract_2000ad_voice_streams


ROOT = Path(__file__).parent.parent


def _load_sid(name: str):
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


class TestRealClusterFiles(unittest.TestCase):
    def test_echo_beat_extracts(self):
        load, binary, copyright = _load_sid("Echo_Beat")
        layout = detect_2000ad_layout(binary, load, copyright)
        self.assertIsNotNone(layout)
        streams = extract_2000ad_voice_streams(binary, load, layout)
        self.assertEqual(len(streams), 3)
        # Each voice must produce a non-empty stream (V0 orderlist has
        # 4 patterns, V1/V2 have non-zero pattern counts too).
        for v, s in enumerate(streams):
            self.assertGreater(len(s), 0, f"V{v} stream empty")
            # Each stream begins with the $A0 instrument-set marker
            # emitted at the start of the first 2000 A.D. pattern.
            self.assertEqual(s[0], 0xA0,
                             f"V{v} stream should start with $A0 marker")

    def test_galax_it_y_extracts(self):
        load, binary, copyright = _load_sid("Galax_it_y")
        layout = detect_2000ad_layout(binary, load, copyright)
        self.assertIsNotNone(layout)
        streams = extract_2000ad_voice_streams(binary, load, layout)
        self.assertEqual(len(streams), 3)
        # Galax_it_y V0 orderlist is `8C 01 FF` — one command then pattern 1.
        # So V0 stream should contain exactly one $A0-prefixed pattern.
        v0 = streams[0]
        self.assertGreater(len(v0), 0)
        self.assertEqual(v0[0], 0xA0)
        # Only one $A0 marker (no subsequent patterns).
        self.assertEqual(v0.count(b'\xA0'), 1,
                         f"Galax V0 should have one pattern; got {v0.count(b'\xA0')}")

    def test_streams_within_size_cap(self):
        """Per-voice streams stay bounded so the segmenter slot fits."""
        for name in ("Echo_Beat", "Galax_it_y"):
            load, binary, copyright = _load_sid(name)
            layout = detect_2000ad_layout(binary, load, copyright)
            streams = extract_2000ad_voice_streams(binary, load, layout)
            for v, s in enumerate(streams):
                self.assertLessEqual(
                    len(s), 600,
                    f"{name} V{v} stream {len(s)}B exceeds 600B cap")


class TestNP21ByteFormat(unittest.TestCase):
    """Emitted bytes must be valid NP21 byte syntax so the SF2 editor
    renders them coherently."""

    def test_all_bytes_in_valid_ranges(self):
        load, binary, copyright = _load_sid("Echo_Beat")
        layout = detect_2000ad_layout(binary, load, copyright)
        streams = extract_2000ad_voice_streams(binary, load, layout)
        for v, s in enumerate(streams):
            for b in s:
                # Valid NP21 bytes: $00 (rest), $01-$6F (note),
                # $80-$9F (duration), $A0-$BF (instrument). Nothing else
                # should appear in our synthesized stream.
                self.assertTrue(
                    (b == 0x00)
                    or (0x01 <= b <= 0x6F)
                    or (0x80 <= b <= 0x9F)
                    or (0xA0 <= b <= 0xBF),
                    f"V{v} stream has invalid byte ${b:02X}")

    def test_note_byte_followed_by_duration(self):
        """Every (note, duration) pair follows the convention:
        note byte in [$00..$6F], then duration byte in [$80..$9F]."""
        load, binary, copyright = _load_sid("Galax_it_y")
        layout = detect_2000ad_layout(binary, load, copyright)
        streams = extract_2000ad_voice_streams(binary, load, layout)
        for v, s in enumerate(streams):
            i = 0
            while i < len(s):
                b = s[i]
                if b == 0xA0:
                    # instrument-set marker — single byte
                    i += 1
                    continue
                # Next two bytes must be (note, duration)
                self.assertLess(i + 1, len(s),
                                f"V{v} stream truncated mid-pair")
                note = s[i]
                dur  = s[i + 1]
                self.assertTrue(note == 0x00 or 0x01 <= note <= 0x6F,
                                f"V{v} byte {i} expected note, got ${note:02X}")
                self.assertTrue(0x80 <= dur <= 0x8F,
                                f"V{v} byte {i+1} expected duration, got ${dur:02X}")
                i += 2


class TestNonClusterReturnsEmpty(unittest.TestCase):
    """Calling the extractor with an obviously bogus layout returns
    empty streams (not a crash)."""

    def test_layout_with_oor_orderlist_returns_empty(self):
        # Use Echo_Beat binary but pass a fake layout whose orderlist
        # ptrs are out of range.
        load, binary, copyright = _load_sid("Echo_Beat")
        fake_layout = Vibrants2000ADLayout(
            voice_orderlist_lo_addr=load + 0x493,
            voice_orderlist_hi_addr=load + 0x496,
            pattern_ptr_lo_addr=load + 0x600,
            pattern_ptr_hi_addr=load + 0x606,
            voice_orderlist_addrs=(0x9000, 0x9003, 0x9006),  # OOR
        )
        streams = extract_2000ad_voice_streams(binary, load, fake_layout)
        self.assertEqual(streams, [b'', b'', b''])


if __name__ == "__main__":
    unittest.main(verbosity=2)
