"""SDI (SID Duzz' It, Gallefoss/Tjelta) parser locks — the play+3 1992
generation, table location + decode against RE'd ground truth
(30seconds.sid disasm + the authors' own SDI 2.1 source)."""
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SID = os.path.join(ROOT, "SID", "Gallefoss_Glenn", "30seconds.sid")


@unittest.skipUnless(os.path.exists(SID), "Gallefoss corpus not staged")
class TestSDIParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from sidm2.sdi_parser import load_sid, SDIModule
        cls.d, cls.la, cls.h = load_sid(SID)
        cls.m = SDIModule(cls.d, cls.la)

    def test_layout_matches_disasm(self):
        """Table addresses RE'd from the 30seconds disassembly."""
        lay = self.m.lay
        self.assertEqual(lay.state, 0x0334)
        self.assertEqual(lay.init_block, 0x162F)
        self.assertEqual(lay.seq_lo, 0x167A)
        self.assertEqual(lay.seq_hi, 0x1684)
        self.assertEqual(lay.freq_lo, 0x14E2)
        self.assertEqual(lay.freq_hi, 0x1482)
        self.assertEqual(lay.stride, 10)          # 10 instruments this song

    def test_detection(self):
        from sidm2.sdi_parser import is_sdi_play3
        self.assertTrue(is_sdi_play3(self.d, self.la, self.h))

    def test_tempo_and_tracks(self):
        self.assertEqual(self.m.fpt, 3)           # tempo reload 2 -> 3 f/tick
        self.assertEqual(self.m.track_ptrs, [0x1636, 0x164D, 0x1663])

    def test_decode_shape(self):
        """Row model: v0's first rows = dur 7 + notes every 24/6 frames
        (validated 99.5% onset+pitch vs siddump)."""
        ev = self.m.events()
        notes = [e for e in ev[0] if e.kind == 'note']
        self.assertGreater(len(notes), 300)
        self.assertEqual(notes[0].frame, 0)
        # raw $24; instr 4's flag bit0 suppresses the $ec (+12) track
        # transpose (validated: trace agrees 99.5% with suppression on)
        self.assertEqual(notes[0].note, 0x24)
        self.assertEqual(notes[1].frame, 24)         # dur 7+1 ticks * 3 f/t

    def test_freq_table(self):
        """96-note table; doubles per octave (rounding tolerance)."""
        f36 = self.m.note_freq(36 + 12)
        f48 = self.m.note_freq(48 + 12)
        self.assertAlmostEqual(f48 / f36, 2.0, delta=0.01)


if __name__ == "__main__":
    unittest.main()
