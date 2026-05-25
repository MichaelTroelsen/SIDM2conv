"""Unit tests for sidm2.sf2_metadata_trailer.

The encoder + decoder pair govern PSID metadata round-trip
(SID → SF2 → SID preserves title/author/copyright). Tests pin:
  - Encoder: b"META" magic + 3 pascal strings, latin-1, 255-byte cap
  - Decoder: reverse-scan, malformed-trailer handling
  - Round-trip symmetry: encode → decode = identity (modulo strip + truncation)

The round-trip property is the load-bearing one — both halves are
tested individually but the symmetry test catches drift between them.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2 import sf2_metadata_trailer as mt


# ---------------------------------------------------------------------------
# Encoder
# ---------------------------------------------------------------------------

class TestEncode(unittest.TestCase):
    def test_magic_prefix(self):
        out = mt.encode_metadata_trailer("", "", "")
        self.assertEqual(out[:4], b"META")

    def test_three_empty_pascal_strings(self):
        out = mt.encode_metadata_trailer("", "", "")
        # b"META" + [len=0][len=0][len=0]
        self.assertEqual(out, b"META\x00\x00\x00")

    def test_normal_strings(self):
        out = mt.encode_metadata_trailer("Stinsen", "Laxity", "(C) 1989")
        # b"META" + len(7)+"Stinsen" + len(6)+"Laxity" + len(8)+"(C) 1989"
        expected = b"META\x07Stinsen\x06Laxity\x08(C) 1989"
        self.assertEqual(out, expected)

    def test_whitespace_stripped(self):
        """Leading/trailing whitespace gets stripped before encoding."""
        out = mt.encode_metadata_trailer("  Title  ", "Author", "")
        # Length should reflect stripped string
        self.assertEqual(out[4], 5)  # len("Title")
        self.assertEqual(out[5:10], b"Title")

    def test_none_strings_treated_as_empty(self):
        out = mt.encode_metadata_trailer(None, None, None)
        self.assertEqual(out, b"META\x00\x00\x00")

    def test_string_truncated_at_255(self):
        long = "A" * 400
        out = mt.encode_metadata_trailer(long, "", "")
        # len byte = 255, then 255 'A's
        self.assertEqual(out[4], 255)
        self.assertEqual(out[5:5 + 255], b"A" * 255)

    def test_non_ascii_latin1_encoded(self):
        out = mt.encode_metadata_trailer("Café", "", "")
        # "Café" → 4 bytes latin-1
        self.assertEqual(out[4], 4)
        self.assertEqual(out[5:9], "Café".encode('latin-1'))

    def test_unencodable_char_replaced(self):
        out = mt.encode_metadata_trailer("中国", "", "")
        # Both Chinese chars unencodable → '?' replacements
        self.assertEqual(out[4], 2)
        self.assertEqual(out[5:7], b"??")


# ---------------------------------------------------------------------------
# Decoder
# ---------------------------------------------------------------------------

class TestDecode(unittest.TestCase):
    def test_empty_input(self):
        self.assertIsNone(mt.decode_metadata_trailer(b""))

    def test_no_magic(self):
        # 200 bytes of random data, no MEAT magic
        self.assertIsNone(mt.decode_metadata_trailer(b"\x00" * 200))

    def test_minimal_trailer(self):
        trailer = b"META\x00\x00\x00"
        # Embed it in a fake SF2 (some prefix bytes then the trailer)
        sf2 = b"\xAB" * 100 + trailer
        result = mt.decode_metadata_trailer(sf2)
        self.assertEqual(result, ("", "", ""))

    def test_normal_decode(self):
        sf2 = b"\xAB" * 100 + b"META\x07Stinsen\x06Laxity\x08(C) 1989"
        result = mt.decode_metadata_trailer(sf2)
        self.assertEqual(result, ("Stinsen", "Laxity", "(C) 1989"))

    def test_truncated_string_returns_none(self):
        """A pascal-length byte that claims more bytes than exist
        should yield None (graceful failure, not exception)."""
        # META + length=100 but only 5 bytes follow
        sf2 = b"\xAB" * 50 + b"META\x64Short"
        result = mt.decode_metadata_trailer(sf2)
        self.assertIsNone(result)

    def test_missing_third_string_returns_none(self):
        """Trailer with only 2 pascal strings (insufficient data) → None."""
        sf2 = b"\xAB" * 50 + b"META\x03One\x03Two"
        result = mt.decode_metadata_trailer(sf2)
        self.assertIsNone(result)

    def test_finds_last_magic_when_multiple(self):
        """If b"META" appears multiple times, decoder should find the
        most recent (rightmost) occurrence — rfind semantics."""
        # First META is a red herring with garbage after
        # Last META is the actual trailer
        sf2 = (b"\xAB" * 50
               + b"META\xFFnotpascal"     # red herring (invalid lengths)
               + b"\xCD" * 100
               + b"META\x03Aaa\x03Bbb\x03Ccc")   # real trailer
        result = mt.decode_metadata_trailer(sf2)
        self.assertEqual(result, ("Aaa", "Bbb", "Ccc"))

    def test_only_tail_scanned_for_speed(self):
        """A trailer further than 2048B from the file end is ignored —
        this is the documented performance optimization for the
        common case where the trailer is appended at file end."""
        far_trailer = b"META\x03Aaa\x03Bbb\x03Ccc"
        sf2 = far_trailer + b"\xAB" * (mt.TAIL_SCAN_WINDOW + 100)
        result = mt.decode_metadata_trailer(sf2)
        self.assertIsNone(result, "trailer at start should not be found")


# ---------------------------------------------------------------------------
# Round-trip — encode then decode = identity (modulo strip + truncation)
# ---------------------------------------------------------------------------

class TestRoundTrip(unittest.TestCase):
    def _round_trip(self, title, author, copyright):
        encoded = mt.encode_metadata_trailer(title, author, copyright)
        sf2 = b"\xAB" * 100 + encoded
        return mt.decode_metadata_trailer(sf2)

    def test_round_trip_normal(self):
        self.assertEqual(
            self._round_trip("Title", "Author", "Copyright"),
            ("Title", "Author", "Copyright"),
        )

    def test_round_trip_empty(self):
        self.assertEqual(
            self._round_trip("", "", ""),
            ("", "", ""),
        )

    def test_round_trip_whitespace_stripped(self):
        # Whitespace stripped on encode, so decoded == stripped
        self.assertEqual(
            self._round_trip("  Title  ", "Author", ""),
            ("Title", "Author", ""),
        )

    def test_round_trip_truncates_at_255(self):
        long = "A" * 400
        result = self._round_trip(long, "x", "y")
        self.assertEqual(result[0], "A" * 255)
        self.assertEqual(result[1], "x")
        self.assertEqual(result[2], "y")

    def test_round_trip_latin1_preserved(self):
        self.assertEqual(
            self._round_trip("Café", "Müller", "(C) 2025"),
            ("Café", "Müller", "(C) 2025"),
        )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants(unittest.TestCase):
    def test_magic_value(self):
        self.assertEqual(mt.METADATA_MAGIC, b"META")

    def test_pascal_length_cap(self):
        self.assertEqual(mt.MAX_PASCAL_LEN, 255)

    def test_tail_scan_window(self):
        self.assertEqual(mt.TAIL_SCAN_WINDOW, 2048)


if __name__ == "__main__":
    unittest.main(verbosity=2)
