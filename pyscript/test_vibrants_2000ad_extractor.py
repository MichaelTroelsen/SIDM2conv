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


class TestChromaticMapping(unittest.TestCase):
    """v3.5.61: byte_2 -> NP21 chromatic note (byte_2 + 1, clamped to $6F).
    byte_2 = 0 stays as NP21 $00 (rest)."""

    def test_galax_v0_first_notes_chromatic_with_transpose(self):
        """First V0 pattern of Galax_it_y has byte pairs starting with
        duration=$0A note=$03 then $16/$03, etc. Galax's V0 orderlist
        is `$8C 01 $FF` so command $8C sets transpose = $8C & $1F = 12.

        After transpose+chromatic shift: NP21_note = byte_2 + 12 + 1.
        First 5 byte_2 values are $03 $03 $07 $03 $07 →
        NP21 $10 $10 $14 $10 $14 (D#-1, D#-1, F#-1, D#-1, F#-1)."""
        load, binary, copyright = _load_sid("Galax_it_y")
        layout = detect_2000ad_layout(binary, load, copyright)
        streams = extract_2000ad_voice_streams(binary, load, layout)
        v0 = streams[0]
        self.assertEqual(v0[0], 0xA0, "stream starts with instrument marker")
        notes = [v0[i] for i in range(1, min(len(v0), 11), 2)]
        self.assertEqual(notes[:5], [0x10, 0x10, 0x14, 0x10, 0x14],
                         "byte_2 + transpose($0C) + 1 mapping")

    def _build_synth_binary_with_pattern(self, pattern_bytes: bytes) -> bytes:
        """Synthesize a 2000 A.D.-shape binary that the extractor will
        walk into `pattern_bytes` for voice 0's pattern 0."""
        binary = bytearray(0x600)
        # Pattern at body offset $400 (= $1400 absolute)
        binary[0x400:0x400 + len(pattern_bytes)] = pattern_bytes
        # Pattern ptr table at body $200/$206 → pat 0 at $1400
        binary[0x200] = 0x00
        binary[0x206] = 0x14
        # Orderlist at $300 ($1300): [pat_idx=0, $FF (loop)]
        binary[0x300:0x302] = bytes([0x00, 0xFF])
        return bytes(binary)

    def _layout(self) -> "Vibrants2000ADLayout":
        from sidm2.vibrants_2000ad_detector import Vibrants2000ADLayout
        return Vibrants2000ADLayout(
            voice_orderlist_lo_addr=0x1000,
            voice_orderlist_hi_addr=0x1000,
            pattern_ptr_lo_addr=0x1200,
            pattern_ptr_hi_addr=0x1206,
            voice_orderlist_addrs=(0x1300, 0x1300, 0x1300),
        )

    def test_byte_2_zero_stays_rest(self):
        """A (duration, note=0) pair: byte_2 = 0 emits NP21 $00 (rest),
        not chromatic +1."""
        # 2000 A.D. pattern: (dur=$02, note=$00) then end-of-pattern $FF
        binary = self._build_synth_binary_with_pattern(
            bytes([0x02, 0x00, 0xFF]))
        streams = extract_2000ad_voice_streams(binary, 0x1000, self._layout())
        # V0 stream: $A0 marker, then (note=$00, dur=$82) pair
        self.assertEqual(streams[0][0], 0xA0)
        self.assertEqual(streams[0][1], 0x00,
                         "byte_2 = 0 must stay $00 (rest), not get +1 shifted")
        self.assertEqual(streams[0][2], 0x82,
                         "duration low 5 bits = 2 → NP21 byte $82")

    def test_byte_2_one_maps_to_chromatic_two(self):
        """byte_2 = 1 (semitone 1 from C-0 per LUT) maps to NP21 $02 (C#-0)."""
        binary = self._build_synth_binary_with_pattern(
            bytes([0x05, 0x01, 0xFF]))
        streams = extract_2000ad_voice_streams(binary, 0x1000, self._layout())
        self.assertEqual(streams[0][1], 0x02,
                         "byte_2=1 -> NP21 $02 (C#-0)")

    def test_chromatic_clamp_at_6f(self):
        """byte_2 = $6F → byte_2 + 1 = $70, clamped to NP21 $6F."""
        binary = self._build_synth_binary_with_pattern(
            bytes([0x05, 0x6F, 0xFF]))
        streams = extract_2000ad_voice_streams(binary, 0x1000, self._layout())
        self.assertEqual(streams[0][1], 0x6F,
                         "byte_2 $6F maps to NP21 $6F (clamped, not $70)")


class TestOrderlistTranspose(unittest.TestCase):
    """v3.5.62: orderlist command bytes ($80-$FE before pattern indices)
    set the per-voice transpose: `transpose = command_byte & $1F`. The
    extractor applies the transpose to each pattern note."""

    def _layout(self):
        from sidm2.vibrants_2000ad_detector import Vibrants2000ADLayout
        return Vibrants2000ADLayout(
            voice_orderlist_lo_addr=0x1000,
            voice_orderlist_hi_addr=0x1000,
            pattern_ptr_lo_addr=0x1200,
            pattern_ptr_hi_addr=0x1206,
            voice_orderlist_addrs=(0x1300, 0x1300, 0x1300),
        )

    def _build(self, *, orderlist_bytes: bytes, pattern_bytes: bytes) -> bytes:
        binary = bytearray(0x600)
        binary[0x400:0x400 + len(pattern_bytes)] = pattern_bytes
        binary[0x200] = 0x00     # pat 0 lo
        binary[0x206] = 0x14     # pat 0 hi
        binary[0x300:0x300 + len(orderlist_bytes)] = orderlist_bytes
        return bytes(binary)

    def test_command_8c_transposes_pattern_by_12(self):
        """Orderlist `$8C $00 $FF`: cmd $8C & $1F = 12 → transpose +12."""
        binary = self._build(
            orderlist_bytes=bytes([0x8C, 0x00, 0xFF]),
            pattern_bytes=bytes([0x05, 0x03, 0xFF]))   # dur=$05 note=$03
        streams = extract_2000ad_voice_streams(binary, 0x1000, self._layout())
        # byte_2=$03 + transpose=$0C + 1 = $10
        self.assertEqual(streams[0][1], 0x10,
                         "$8C transposes by +12 → byte_2=$03 emits as $10")

    def test_command_88_transposes_pattern_by_8(self):
        """$88 & $1F = 8 → transpose +8."""
        binary = self._build(
            orderlist_bytes=bytes([0x88, 0x00, 0xFF]),
            pattern_bytes=bytes([0x05, 0x03, 0xFF]))
        streams = extract_2000ad_voice_streams(binary, 0x1000, self._layout())
        self.assertEqual(streams[0][1], 0x0C,
                         "$88 transposes by +8 → byte_2=$03 emits as $0C")

    def test_multiple_orderlist_iterations_use_different_transposes(self):
        """Echo_Beat-style orderlist: same pattern, different transposes
        per iteration produces different chromatic labels per sub-pattern."""
        binary = self._build(
            orderlist_bytes=bytes([0x8C, 0x00, 0x88, 0x00, 0xFF]),
            pattern_bytes=bytes([0x05, 0x03, 0xFF]))   # one note per pattern
        streams = extract_2000ad_voice_streams(binary, 0x1000, self._layout())
        # Stream: $A0 note1 dur $A0 note2 dur
        # Iter 1: transpose=12 → byte_2=$03 → $10
        # Iter 2: transpose=8  → byte_2=$03 → $0C
        s = streams[0]
        self.assertEqual(s[0], 0xA0)
        self.assertEqual(s[1], 0x10, "iter 1: +12 transpose → $10")
        self.assertEqual(s[3], 0xA0, "second sub-pattern marker")
        self.assertEqual(s[4], 0x0C, "iter 2: +8 transpose → $0C")

    def test_rest_byte_2_zero_ignores_transpose(self):
        """A note byte of $00 is the gate-off path; the transpose does
        NOT apply (matches the player's runtime branch order)."""
        binary = self._build(
            orderlist_bytes=bytes([0x8C, 0x00, 0xFF]),     # transpose = 12
            pattern_bytes=bytes([0x05, 0x00, 0xFF]))       # note = $00 (rest)
        streams = extract_2000ad_voice_streams(binary, 0x1000, self._layout())
        self.assertEqual(streams[0][1], 0x00,
                         "byte_2=$00 stays $00 regardless of transpose")

    def test_no_command_default_transpose_zero(self):
        """Orderlist starting with a bare pattern index (no command)
        uses transpose = 0 → bare +1 chromatic mapping."""
        binary = self._build(
            orderlist_bytes=bytes([0x00, 0xFF]),
            pattern_bytes=bytes([0x05, 0x03, 0xFF]))
        streams = extract_2000ad_voice_streams(binary, 0x1000, self._layout())
        self.assertEqual(streams[0][1], 0x04,
                         "no command → transpose=0 → byte_2=$03 emits as $04")


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
