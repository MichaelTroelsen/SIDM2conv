"""Blackbird (Linus Åkesson / "lft") parser locks.

Validates `sidm2.blackbird_parser` against:
  1. Two independent RetroDebugger live-CPU captures (real frame numbers,
     real register values, breakpoint at `unpackvoice+11` — see
     docs/players/BLACKBIRD.md "2026-07-19 live-trace session"), using a
     STRICT exact-contiguous-subsequence match: the full ground-truth
     record run must appear, in order with no gaps, at exactly ONE offset
     in the decoder's own piece-emission stream. A prior scratch validator
     used a looser "found somewhere after the last match" check — this is
     the independently-rewritten strict version referenced in
     BLACKBIRD.md's "Verification" section.
  2. The full 11-file v1.2-exact bucket: every file must freeze cleanly
     (genuine end-of-stream reached) with zero out-of-grammar bytes across
     all 3 voices.
  3. `locate_blackbird` correctly rejecting non-Blackbird / non-v1.2-exact
     files (both Åkesson's other engines and the near-v1.2 variant bucket
     compiled by older birdcruncher tool versions) — a locate
     false-positive would be a real regression risk since it would feed a
     bogus streamstart into the decoder.
"""
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LFT = os.path.join(ROOT, "SID", "LFT")

FARGO = os.path.join(LFT, "Fargo.sid")
GLYPTODONT = os.path.join(LFT, "Glyptodont.sid")

FARGO_GT = os.path.join(ROOT, "SID", "blackbird_fargo_trace_4199_5371.json")
GLYPTODONT_GT = os.path.join(ROOT, "SID", "blackbird_glyptodont_trace_4248_5026.json")

V12_EXACT_BUCKET = [
    "Fargo", "Glyptodont", "Dishwasher_Groove", "Dithered_Island", "Elvendance",
    "Euclid_Was_Here", "Into_the_Unknown", "Maple_Leaf_Rag",
    "Revolutions_Delivered", "Thus_Spoke_the_PC_Speaker", "Toy_Rocket",
]

# A sample of the ~25 files that are Åkesson's OTHER, unrelated engines
# (per BLACKBIRD.md's corpus-scope table — these diverge almost completely
# from the compiled template, ~1000+/1030 bytes).
NOT_BLACKBIRD_SAMPLE = [
    "Platform_Hopping", "Sideways", "Air_on_a_Rasterline", "King_Fisher_0x28",
]

# "variant A" (2026-07-22, RESOLVED): NOT a different birdcruncher tool
# version after all -- the SAME v1.2 source, compiled with player.s's
# `#if REPEAT` flag enabled (loop-on-end support). locate_blackbird now
# recognizes this as `variant='v1.2-repeat'` (see BLACKBIRD.md/
# _templates_repeat1's own docstring for the full derivation).
V12_REPEAT_BUCKET = [
    "Crank_Crank_Airwolf", "Fugue_on_a_Theme_by_D_M_Hanlon", "Quintessence",
    "To_Die_For_II", "Trinket",
]

# Still NOT supported: "variant A'" (close to variant A but not identical --
# has its own additional differences beyond REPEAT=1, not yet investigated)
# and the older "variant B" bucket (a substantially rewritten wave/pulse
# engine section, first diff at offset ~204; likely birdcruncher 1.0).
NEAR_V12_VARIANTS = [
    "Crank_Crank_Revolution",
    "Arrow_of_Time", "Fjaellevator_Music", "Hachi_Bitto_Whirlwind",
    "In_Darkness_Hope", "Nine", "Scene_Spirit_v2",
]


def _skip_unless_corpus():
    return unittest.skipUnless(
        os.path.exists(FARGO) and os.path.exists(GLYPTODONT),
        "SID/LFT corpus not staged")


# ---------------------------------------------------------------------------
# Strict exact-contiguous-subsequence ground-truth validation
# ---------------------------------------------------------------------------
def _mine_triples(result):
    """(voice, L mod 256, ctrl) triples in true piece-emission order,
    dropping post-terminator filler (not ground-truth comparable — the
    live captures only recorded genuine literal/copy pieces)."""
    return [(p.voice, p.pos % 256, p.ctrl) for p in result.pieces
            if p.kind in ('literal', 'copy')]


def _gt_triples(json_path, voice_map):
    d = json.load(open(json_path))
    out = []
    for rec in d['records']:
        frame, voice, L, ctrl_hex = rec[0], rec[1], rec[2], rec[3]
        out.append((voice_map[voice], L % 256, int(ctrl_hex, 16)))
    return out


def _find_exact_contiguous(haystack, needle):
    """Offsets where `needle` appears as an EXACT CONTIGUOUS subsequence of
    `haystack` — every element equal, in order, with no gaps. Stricter than
    "appears somewhere after the last match": this requires the whole
    ground-truth run to line up back-to-back in the decoder's own output."""
    offsets = []
    n, m = len(haystack), len(needle)
    if m == 0 or m > n:
        return offsets
    for i in range(n - m + 1):
        if haystack[i:i + m] == needle:
            offsets.append(i)
    return offsets


@_skip_unless_corpus()
class TestBlackbirdGroundTruth(unittest.TestCase):
    """Strict validation against real 6502 hardware, not just self-
    consistency: both captures must appear as a UNIQUE, exact, contiguous
    run inside this decoder's own piece stream."""

    def test_fargo_matches_live_trace_uniquely(self):
        from sidm2.blackbird_parser import decode_file
        _, result = decode_file(FARGO)
        mine = _mine_triples(result)
        gt = _gt_triples(FARGO_GT, {0: 0, 1: 1, 2: 2})
        self.assertEqual(len(gt), 68)
        offsets = _find_exact_contiguous(mine, gt)
        self.assertEqual(
            len(offsets), 1,
            f"expected a UNIQUE contiguous match, got {len(offsets)}: {offsets}")

    def test_glyptodont_matches_live_trace_uniquely(self):
        from sidm2.blackbird_parser import decode_file
        _, result = decode_file(GLYPTODONT)
        mine = _mine_triples(result)
        # Glyptodont's raw capture records voice by SID register offset
        # (X = 0/7/14), not decoder voice index — see bb_sweep.py's
        # original voice_map.
        gt = _gt_triples(GLYPTODONT_GT, {0: 0, 7: 1, 14: 2})
        self.assertEqual(len(gt), 80)
        offsets = _find_exact_contiguous(mine, gt)
        self.assertEqual(
            len(offsets), 1,
            f"expected a UNIQUE contiguous match, got {len(offsets)}: {offsets}")


@_skip_unless_corpus()
class TestBlackbirdSweep(unittest.TestCase):
    """The full 11-file v1.2-exact bucket: every file must locate, decode,
    and freeze cleanly with zero out-of-grammar bytes on all 3 voices."""

    def test_all_bucket_files_freeze_clean(self):
        from sidm2.blackbird_parser import (classify_byte, decode_file,
                                            locate_blackbird)
        for name in V12_EXACT_BUCKET:
            path = os.path.join(LFT, f"{name}.sid")
            with self.subTest(file=name):
                self.assertTrue(os.path.exists(path), f"{path} missing")
                lay = locate_blackbird(path)
                self.assertIsNotNone(lay, f"{name}: locate failed")
                _, result = decode_file(path)
                self.assertTrue(result.frozen, f"{name}: did not freeze cleanly")
                for v in range(3):
                    real = result.real(v)
                    unk = [b for b in real if classify_byte(b) == 'unknown']
                    self.assertEqual(
                        unk, [],
                        f"{name} voice{v}: {len(unk)} out-of-grammar byte(s)")
                    self.assertGreater(
                        len(real), 0, f"{name} voice{v}: decoded zero bytes")


@_skip_unless_corpus()
class TestBlackbirdRepeatSweep(unittest.TestCase):
    """The 5-file v1.2+REPEAT=1 bucket ("variant A"): every file must
    locate, decode, and freeze cleanly with zero out-of-grammar bytes on
    all 3 voices, and Stage A (Driver 11 transpile) must build without
    raising. Locked in 2026-07-22 after fixing (1) the REPEAT=1 copy-op
    source-index formula + 256-byte ring-buffer zero-fill, and (2) three
    prepare1/2/3 grammar-boundary bugs (found by diffing against
    `bin/blackbird_everyframe_sim.py`'s already-trace-validated
    `BlackbirdSim`) that were pre-existing in the v1.2 code but never
    triggered by any of the 11 v1.2-exact files' own data."""

    def test_all_repeat_bucket_files_freeze_clean(self):
        from sidm2.blackbird_parser import (classify_byte, decode_file,
                                            locate_blackbird)
        for name in V12_REPEAT_BUCKET:
            path = os.path.join(LFT, f"{name}.sid")
            with self.subTest(file=name):
                self.assertTrue(os.path.exists(path), f"{path} missing")
                lay = locate_blackbird(path)
                self.assertIsNotNone(lay, f"{name}: locate failed")
                self.assertEqual(lay.variant, 'v1.2-repeat')
                _, result = decode_file(path)
                self.assertTrue(result.frozen, f"{name}: did not freeze cleanly")
                for v in range(3):
                    real = result.real(v)
                    unk = [b for b in real if classify_byte(b) == 'unknown']
                    self.assertEqual(
                        unk, [],
                        f"{name} voice{v}: {len(unk)} out-of-grammar byte(s)")
                    self.assertGreater(
                        len(real), 0, f"{name} voice{v}: decoded zero bytes")

    def test_all_repeat_bucket_files_build_stage_a(self):
        from sidm2.blackbird_driver11 import build_blackbird_driver11_song
        for name in V12_REPEAT_BUCKET:
            path = os.path.join(LFT, f"{name}.sid")
            with self.subTest(file=name):
                song = build_blackbird_driver11_song(path)
                self.assertEqual(len(song.tracks), 3)
                for track in song.tracks:
                    self.assertGreater(len(track), 0)
                self.assertGreater(len(song.instruments), 0)


@_skip_unless_corpus()
class TestBlackbirdLocateFalsePositives(unittest.TestCase):
    """`locate_blackbird` must reject files that are NOT this exact engine
    generation — a false positive would feed a bogus streamstart into the
    decoder (see BLACKBIRD.md's corpus-scope table)."""

    def test_rejects_other_akesson_engines(self):
        from sidm2.blackbird_parser import locate_blackbird
        for name in NOT_BLACKBIRD_SAMPLE:
            path = os.path.join(LFT, f"{name}.sid")
            if not os.path.exists(path):
                continue
            with self.subTest(file=name):
                self.assertIsNone(locate_blackbird(path),
                                  f"{name}: false-positive match")

    def test_rejects_near_v12_variants(self):
        """Scoping guard: variant A' and the older variant B bucket are NOT
        yet supported (different compiled bytes at the documented diff
        offsets — see BLACKBIRD.md). If this ever starts returning a match,
        the template comparison has gotten too loose, or variant support
        was added without updating this test."""
        from sidm2.blackbird_parser import locate_blackbird
        checked = 0
        for name in NEAR_V12_VARIANTS:
            path = os.path.join(LFT, f"{name}.sid")
            if not os.path.exists(path):
                continue
            checked += 1
            with self.subTest(file=name):
                self.assertIsNone(locate_blackbird(path),
                                  f"{name}: unexpectedly located — near-v1.2 "
                                  f"variant support may have been added; "
                                  f"update this test's scope note")
        self.assertGreater(checked, 0, "no near-v1.2 variant files found to check")

    def test_locates_v12_repeat_bucket(self):
        """variant A (2026-07-22): the SAME v1.2 source compiled with
        REPEAT=1, not a different tool version — see BLACKBIRD.md's
        "REPEAT=1 locate support" section. Every file must locate with
        variant='v1.2-repeat' and pass the SAME nins/init-template
        consistency checks the v1.2-exact bucket already gets."""
        from sidm2.blackbird_parser import locate_blackbird
        checked = 0
        for name in V12_REPEAT_BUCKET:
            path = os.path.join(LFT, f"{name}.sid")
            if not os.path.exists(path):
                continue
            checked += 1
            with self.subTest(file=name):
                lay = locate_blackbird(path)
                self.assertIsNotNone(lay, f"{name}: failed to locate")
                self.assertEqual(lay.variant, 'v1.2-repeat')
                self.assertTrue(lay.nins_consistent,
                                f"{name}: instrument table spacing inconsistent")
                self.assertFalse(lay.init_template_mismatch,
                                 f"{name}: init segment template mismatch")
                self.assertGreater(lay.streamstart, 0)
        self.assertGreater(checked, 0, "no v1.2-repeat bucket files found to check")


@_skip_unless_corpus()
class TestBlackbirdLayout(unittest.TestCase):
    """Symbol-recovery sanity checks on Fargo (cross-checked in
    BLACKBIRD.md's 'Detection / locate' table)."""

    @classmethod
    def setUpClass(cls):
        from sidm2.blackbird_parser import locate_blackbird
        cls.lay = locate_blackbird(FARGO)

    def test_recovered_symbols(self):
        self.assertEqual(self.lay.zp_base, 0xE0)
        self.assertEqual(self.lay.seg_init, 0x16A6)
        self.assertEqual(self.lay.ins_ad, 0x1500)
        self.assertEqual(self.lay.ins_sr, 0x1523)
        self.assertEqual(self.lay.ins_wave, 0x1546)
        self.assertEqual(self.lay.ins_filt, 0x1569)
        self.assertEqual(self.lay.fx_start, 0x158C)
        self.assertEqual(self.lay.filttable, 0x15AF)
        self.assertEqual(self.lay.fxtable, 0x15CD)
        self.assertEqual(self.lay.wavetable, 0x1675)
        self.assertEqual(self.lay.streamstart, 0x1CA6)

    def test_nins_consistency(self):
        self.assertEqual(self.lay.nins, 35)
        self.assertTrue(self.lay.nins_consistent)


@_skip_unless_corpus()
class TestBlackbirdGrammar(unittest.TestCase):
    """Event-byte grammar classification (no frame timing)."""

    def test_classify_ranges(self):
        from sidm2.blackbird_parser import classify_byte
        self.assertEqual(classify_byte(0x00), 'note')
        self.assertEqual(classify_byte(0x7f), 'note')
        self.assertEqual(classify_byte(0x80), 'gate_off')
        self.assertEqual(classify_byte(0x81), 'legato')
        self.assertEqual(classify_byte(0x82), 'unknown')
        self.assertEqual(classify_byte(0x83), 'instrument')
        self.assertEqual(classify_byte(0xb2), 'instrument')
        self.assertEqual(classify_byte(0xb3), 'unknown')
        self.assertEqual(classify_byte(0xb8), 'delay')
        self.assertEqual(classify_byte(0xc7), 'delay')
        self.assertEqual(classify_byte(0xc8), 'unknown')
        self.assertEqual(classify_byte(0xc9), 'arp')
        self.assertEqual(classify_byte(0xf8), 'arp')
        self.assertEqual(classify_byte(0xf9), 'oob')
        self.assertEqual(classify_byte(0xff), 'oob')

    def test_parse_grammar_args(self):
        from sidm2.blackbird_parser import parse_grammar
        tokens = parse_grammar([0x04, 0x80, 0x81, 0x85, 0xb9, 0xca])
        self.assertEqual(
            [(t.kind, t.arg) for t in tokens],
            [('note', 2), ('gate_off', None), ('legato', None),
             ('instrument', 3), ('delay', 1), ('arp', 1)])


if __name__ == '__main__':
    unittest.main()
