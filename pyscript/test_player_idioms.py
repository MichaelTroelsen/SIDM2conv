"""Locks for sidm2/player_idioms.py — the shared 6502 idiom library.

Each idiom is locked against a known file so a pattern that stops matching
fails a test instead of silently going stale (the whole point of
knowledge-as-code; see docs/players/PATTERNS.md).
"""
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SDI_A = os.path.join(ROOT, "SID", "Gallefoss_Glenn", "30seconds.sid")
SDI_V = os.path.join(ROOT, "SID", "Gallefoss_Glenn", "Oh_Boy_VE-2x.sid")


class TestFindPattern(unittest.TestCase):
    def test_wildcards_and_extraction(self):
        from sidm2.player_idioms import find_pattern, word_at
        d = bytes([0xEA, 0xB9, 0x34, 0x12, 0x85, 0xFC])
        i = find_pattern(d, [0xB9, -1, -1, 0x85])
        self.assertEqual(i, 1)
        self.assertEqual(word_at(d, i + 1), 0x1234)

    def test_find_all(self):
        from sidm2.player_idioms import find_all
        d = bytes([0x9D, 0x04, 0x04, 0x00, 0x9D, 0x04, 0x04])
        self.assertEqual(find_all(d, [0x9D, 0x04, 0x04]), [0, 4])

    def test_no_match(self):
        from sidm2.player_idioms import find_pattern
        self.assertIsNone(find_pattern(bytes(8), [0xB9, -1, -1]))


@unittest.skipUnless(os.path.exists(SDI_A), "Gallefoss corpus not staged")
class TestAgainstCorpus(unittest.TestCase):
    def test_freq_scan_30seconds(self):
        """Content-verified freq locate matches the RE'd 30seconds tables."""
        from sidm2.player_idioms import scan_freq_tables
        from sidm2.sdi_parser import load_sid
        d, la, h = load_sid(SDI_A)
        got = scan_freq_tables(d, la)
        self.assertEqual(got, (0x14E2, 0x1482))

    @unittest.skipUnless(os.path.exists(SDI_V), "VE file not staged")
    def test_bounded_init_wrapper_class(self):
        """play=$0000 wrapper: init spins after installing $0F4D/$0F48."""
        from sidm2.player_idioms import bounded_init
        from sidm2.sdi_parser import load_sid
        d, la, h = load_sid(SDI_V)
        img, irq, hw = bounded_init(d, la, h.init_address)
        self.assertIsNotNone(img)
        self.assertEqual(irq, 0x0F4D)
        self.assertEqual(hw, 0x0F48)


if __name__ == "__main__":
    unittest.main()
