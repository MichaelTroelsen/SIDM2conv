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
        # transpose, and its wfprg row-1 = ($81, $48) = a DRUM program
        # carrying the ABSOLUTE pitch 72 — matching the traced onset freq
        # table[72] exactly (STRICT validation 99.6%)
        self.assertEqual(notes[0].note, 72)
        self.assertEqual(notes[1].frame, 24)         # dur 7+1 ticks * 3 f/t

    def test_freq_table(self):
        """96-note table; doubles per octave (rounding tolerance)."""
        f36 = self.m.note_freq(36 + 12)
        f48 = self.m.note_freq(48 + 12)
        self.assertAlmostEqual(f48 / f36, 2.0, delta=0.01)


MICRO = os.path.join(ROOT, "SID", "Gallefoss_Glenn", "Micro_Mix.sid")


@unittest.skipUnless(os.path.exists(MICRO), "Gallefoss corpus not staged")
class TestSDIVariantCWalk(unittest.TestCase):
    """Variant-C wfprg walk locks — py65-verified 2026-07-12 on
    Micro_Mix + Bahbar (bin/_sdi_c_walk_trace.py): 11-byte instrument
    records (sound-set tail = ASL x3 + ADC x3), walk start = record
    byte +2, one row/frame, wf >= $90 jumps BACK (wf-$90) rows."""
    @classmethod
    def setUpClass(cls):
        from sidm2.sdi_parser import load_sid, SDIModule
        cls.d, cls.la, cls.h = load_sid(MICRO)
        cls.m = SDIModule(cls.d, cls.la)

    def test_variant_and_stride(self):
        lay = self.m.lay
        self.assertEqual(lay.variant, 'C')
        self.assertEqual(lay.c_rec_stride, 11)   # emu: Y = instr * 11
        self.assertEqual(lay.wfprg_start_col, 0x17B9)
        self.assertEqual(lay.wf_col, 0x18AD)

    def test_walk_start_rows(self):
        """Emulated record reads: instr 4 -> row 132, instr 16 -> 77,
        instr 9 -> 22 (the wrong-stride bug read row st=const for ALL)."""
        lay = self.m.lay
        for instr, row in ((4, 132), (16, 77), (9, 22)):
            self.assertEqual(
                self.m._u8(lay.wfprg_start_col + instr * lay.c_rec_stride),
                row)

    def test_instr_pitch(self):
        """instr 16 = the looping {+12,+7,+4} chord arp (emu fr+0 heard
        note2+12); instr 4 parks at arg 0 -> None (note2 exact)."""
        self.assertEqual(self.m.instr_pitch(16), ('rel', 12))
        self.assertIsNone(self.m.instr_pitch(4))


ARABIA = os.path.join(ROOT, "SID", "Gallefoss_Glenn", "Arabia.sid")


@unittest.skipUnless(os.path.exists(ARABIA), "Gallefoss corpus not staged")
class TestSDIVariantETrackDelay(unittest.TestCase):
    """Variant-E $Cx track-delay is TRAILING, not leading — emulation
    (bin/_sdi_e_gatewatch.py / _sdi_e_trackwatch.py, 2026-07-13): the
    player ($EE8F) stores b&$3f to the delay cell $e910,X and the gate
    ($EE50) pays it only AFTER the seq it was read with (before advancing
    to the NEXT track entry). Arabia v2 track = a0 00 c3 0a...: seq00
    (2 ticks) then c3, then seq0a. The c3=3 delay must NOT push seq0a's
    onset — real seq0a starts at fr4 (gate rise fr6), tick ~2, not tick 5.
    Regression guard for the +3-tick / +6-frame drift that collapsed the
    E strict window."""
    @classmethod
    def setUpClass(cls):
        from sidm2.sdi_parser import load_sid, SDIModule
        cls.d, cls.la, cls.h = load_sid(ARABIA)
        cls.m = SDIModule(cls.d, cls.la)
        cls.m.fpt = 1                             # decode in ticks

    def test_trailing_delay_no_preshift(self):
        ev = self.m.events()
        ticks = [e.frame for e in ev[2] if e.kind == 'note'][:5]
        # tick 0 = seq00 note-21 blip (real gate rise fr1); tick 2 =
        # seq0a's first note (real fr6). If the c3=3 delay were applied
        # BEFORE seq0a (the old bug) this would be tick 5.
        self.assertEqual(ticks, [0, 2, 8, 16, 18])


DELTA = os.path.join(ROOT, "SID", "Gallefoss_Glenn", "Delta.sid")


@unittest.skipUnless(os.path.exists(DELTA), "Gallefoss corpus not staged")
class TestSDIVariantDelta(unittest.TestCase):
    """Variant DELTA locks — the play+3 JMP-wrapped, zero-page-state
    E-family cluster (Commando/Delta/Lightforce/...), RE'd + emulation-
    verified 2026-07-13 (bin/_sdi_delta_seqwatch.py). Track grammar = E's;
    tables located by relocation-safe signatures; SEQ row =
    [sound $80-$bf][dur $60-$7f][note <$5f +transpose], $00 = seq END."""
    @classmethod
    def setUpClass(cls):
        from sidm2.sdi_parser import load_sid, SDIModule
        cls.d, cls.la, cls.h = load_sid(DELTA)
        cls.m = SDIModule(cls.d, cls.la)

    def test_variant_and_tables(self):
        lay = self.m.lay
        self.assertEqual(lay.variant, 'DELTA')
        self.assertEqual(lay.track_lo_arr, 0x13E8)
        self.assertEqual(lay.seq_lo, 0x148D)
        self.assertEqual(lay.freq_lo, 0x0FFA)
        self.assertEqual(lay.e_f, 0x13B9)         # wfprg arg/pitch column
        self.assertEqual(self.m.track_ptrs,
                         [0x13EE, 0x144C, 0x146E])

    def test_seq_row_decode(self):
        """v0 seq00 = 81 61 1b 85 1b 27..: sound-set + dur-1 + note $1b,
        rows every 2 ticks (dur 1 persists); base note = byte + transpose."""
        self.m.fpt = 1
        ev = self.m.events()
        ticks = [(e.frame, e.note) for e in ev[0] if e.kind == 'note'][:4]
        self.assertEqual(ticks, [(0, 27), (2, 27), (4, 39), (6, 27)])

    def test_abs_form_page03_straggler(self):
        """The page-$03-state sub-variant (Invention_1) locates as DELTA via
        the abs (BC) track/seq form + the play-dispatch guard — NOT a false
        positive (it decodes: strict ~98.7). The dispatch guard C9 02 F0 ??
        C9 01 F0 keeps the 9 abs-form false-positives out."""
        from sidm2.sdi_parser import load_sid, SDIModule
        p = os.path.join(ROOT, "SID", "Gallefoss_Glenn", "Invention_1.sid")
        if not os.path.exists(p):
            self.skipTest("Invention_1 not staged")
        d, la, h = load_sid(p)
        m = SDIModule(d, la)
        self.assertEqual(m.lay.variant, 'DELTA')
        self.assertGreater(len([e for e in m.events()[0]
                                if e.kind == 'note']), 100)


if __name__ == "__main__":
    unittest.main()
