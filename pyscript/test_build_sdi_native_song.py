#!/usr/bin/env python3
"""The SDI-only filter-flag override, and why it must stay SDI-only.

`detect_filter_drives` and `_filt_exact` live in bin/build_mon_native_song.py
and are shared by the NINE builders that route through `build_native_song`.
Their two opt-in flags, FILT_LEAD and FILT_EXACT_PB, were measured across six
corpora on 2026-08-19 with BOTH arms rebuilt at HEAD, and the result was that
they help exactly ONE player:

    SDI          Arabia 97.8 -> 100.0, Funk_Facet 99.0 -> 100.0, parts 3111 -> 3111
    HardTrack    passband 32/33 both arms, parts 313 -> 315   (+2 for no gain)
    DMC          passband 50/70 both arms, parts 992 -> 995   (+3, and
                 Predictable_main's audible v1 freq falls 100.0 -> 99.35)
    SoundMonitor 99.252 -> 99.252, --compare clean, no part moves
    Blackbird    99.963 -> 99.963, byte-changes 0
    FC           passband 5/5 both arms, 0 of 19 artifacts differ

So the flags are turned on by ASSIGNING THE IMPORTED MODULE'S ATTRIBUTES in
bin/build_sdi_native_song.py rather than by changing the shared builder or
mutating os.environ. That choice is load-bearing in three ways, and each is
pinned below:

  * BM reads both flags AT IMPORT TIME, so mutating os.environ after importing
    it would be a no-op, and mutating it before would leak into every
    subprocess the builder spawns -- including HardTrack's and DMC's.
  * The shared builder keeps the shipped defaults (FILT_LEAD=4,
    FILT_EXACT_PB=False), so the other eight builders are untouched. A test
    that only checked "SDI has 64" would still pass if someone flipped the
    global default, which is the change this whole arrangement exists to
    prevent -- so the global default is asserted too.
  * An explicit env var must still win, because every A/B in this repo is
    driven that way.

These tests do NOT build anything: bin/build_sdi_native_song.py has a
`__name__ == '__main__'` guard, so importing it applies the override and
nothing else.
"""
import ast
import os
import subprocess
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BUILDER = os.path.join(_ROOT, "bin", "build_sdi_native_song.py")

_PROBE = (
    "import sys, os, io, contextlib\n"
    "sys.path.insert(0, os.path.join(%r, 'bin'))\n"
    "sys.path.insert(0, %r)\n"
    "sys.path.insert(0, os.path.join(%r, 'pyscript'))\n"
    "import build_mon_native_song as BM\n"
    "before = (BM.FILT_LEAD, BM.FILT_EXACT_PB)\n"
    "buf = io.StringIO()\n"
    "with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):\n"
    "    import build_sdi_native_song\n"
    "print(repr((before, (BM.FILT_LEAD, BM.FILT_EXACT_PB))))\n"
) % (_ROOT, _ROOT, _ROOT)


def _probe(env_extra=None):
    """(shipped_defaults, after_sdi_import), measured in a clean interpreter."""
    env = dict(os.environ)
    env.pop("FILT_LEAD", None)
    env.pop("FILT_EXACT_PB", None)
    if env_extra:
        env.update(env_extra)
    out = subprocess.run([sys.executable, "-c", _PROBE], cwd=_ROOT, env=env,
                         capture_output=True, text=True, timeout=300)
    if out.returncode != 0:
        raise AssertionError("probe failed: " + (out.stderr or "")[-800:])
    # literal_eval, not eval: the probe prints a tuple literal, and this
    # refuses anything that is not one.
    return ast.literal_eval(out.stdout.strip().splitlines()[-1])


@unittest.skipIf(not os.path.isfile(_BUILDER), "build_sdi_native_song.py absent")
class TestSdiFilterFlagOverride(unittest.TestCase):

    def test_the_shared_builder_keeps_the_shipped_defaults(self):
        """The global default must stay OFF -- eight other builders depend on it.

        This is the assertion that actually protects the other players. The
        A/B says the flags cost HardTrack +2 parts and cost DMC a real (if
        small) audible regression, so a global flip is a measured loss.
        """
        before, _after = _probe()
        self.assertEqual(before, (4, False),
                         "build_mon_native_song's shipped flag defaults moved; "
                         "the six-player A/B says they must stay off globally")

    def test_importing_the_sdi_builder_turns_them_on(self):
        before, after = _probe()
        self.assertEqual(after, (64, True))
        self.assertNotEqual(before, after,
                            "the SDI override is a no-op -- it must differ from "
                            "the shared default or it is not doing anything")

    def test_an_explicit_env_var_still_wins(self):
        """The escape hatch: every A/B here is driven by the env var, so the
        SDI default must be overridable back to the shared behaviour."""
        _before, after = _probe({"FILT_LEAD": "4"})
        self.assertEqual(after[0], 4,
                         "FILT_LEAD=4 did not survive the SDI override")

    def test_the_override_is_a_module_attribute_not_an_environ_mutation(self):
        """Pinned because the mechanism is not interchangeable.

        Writing os.environ here would leak the flags into every subprocess the
        builder spawns, which is precisely how the other eight players would
        silently acquire a default the A/B refuted for them.
        """
        src = open(_BUILDER, encoding="utf-8").read()
        self.assertIn("BM.FILT_LEAD", src)
        self.assertIn("BM.FILT_EXACT_PB", src)
        self.assertNotIn('os.environ["FILT_LEAD"]', src)
        self.assertNotIn("os.environ['FILT_LEAD']", src)
        self.assertNotIn('os.environ.setdefault("FILT_LEAD"', src)


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# The part-count anomaly: CAP_B saturation, not a windowing defect.
#
# Measured 2026-09-05 by calling build_song's own `fits` probe at several left
# edges: one STEP of End_94 costs 36-52 command bundles, two cost 65-118, and
# CAP_B is 63 -- so the adaptive window can never grow and 1185 of its 1190
# parts are exactly STEP wide. GT_Groove sustains two STEPs (385 of 405 at
# 2*STEP). No other cap comes close: instruments peaked at 39/32 once, wave
# rows 69/256, filter rows 89/256, sequences 8/120.
#
# These tests read the SHIPPED spans rather than rebuilding -- End_94 is a
# 2401s song and rebuilding it costs hours (see runs.jsonl:sdi-control-rerun-
# at-j8, where a single-sample cost extrapolation went badly wrong). They skip
# cleanly on a fresh clone with no corpus.
# ---------------------------------------------------------------------------

_OUT_SDI = os.path.join(_ROOT, "out", "sdi")


def _part_widths(base):
    """[(t1-t0), ...] in seconds, from the .span sidecars; [] if not built."""
    import glob
    out = []
    for f in sorted(glob.glob(os.path.join(
            _OUT_SDI, base + "_native_part*.sf2.span"))):
        try:
            t0, t1 = open(f).read().split()
        except ValueError:
            continue
        out.append(int(t1) - int(t0))
    return out


class TestPartCountIsDensityNotDefect(unittest.TestCase):
    """Pins the SHAPE of the split, which is what a regression would change."""

    def test_end_94_is_saturated_at_one_step(self):
        w = _part_widths("End_94")
        if not w:
            self.skipTest("out/sdi/End_94_native_part*.span not built")
        at_step = sum(1 for x in w if x == 2)
        self.assertGreater(len(w), 100, "positive control: too few parts read")
        self.assertGreater(
            at_step / len(w), 0.95,
            "End_94 is no longer saturated at one STEP (%d of %d parts are 2s) "
            "-- either CAP_B moved, STEP moved, or the bundle emitter got "
            "cheaper. That is a REAL change worth re-measuring, not a "
            "regression to paper over." % (at_step, len(w)))

    def test_the_other_flagged_songs_are_NOT_saturated(self):
        """The half of the 2026-09-05 finding that is easy to lose.

        L-Forza_long_edit, Stort_Plaster and L-Forza_Remix were flagged in the
        same breath as End_94 and GT_Groove, on part COUNT. They are ordinary:
        their widths spread 2-18s like any other song. If they ever collapse
        to a single width they have joined the saturated class and the doc in
        build_song's docstring needs revisiting.
        """
        checked = 0
        for base in ("L-Forza_long_edit", "Stort_Plaster", "L-Forza_Remix"):
            w = _part_widths(base)
            if not w:
                continue
            checked += 1
            self.assertGreater(
                len(set(w)), 3,
                "%s collapsed to %d distinct part widths %s -- it used to "
                "spread 2-18s" % (base, len(set(w)), sorted(set(w))))
        if not checked:
            self.skipTest("none of the three comparison songs are built")


# ---------------------------------------------------------------------------
# The onset gate's REPORT (not its verdict).
#
# The gate pools three voices into one agree/tot and prints only the emulated
# counts, so Culture_Mix_1 [1, 1, 535] (quiet in both traces, PASSES) and
# Jessie_Jazz [1, 415, 1] (a busy voice collapsed only in emulation, REFUSED at
# 0.055) read identically on the one line a human sees. These tests pin the
# trace column that separates them -- and pin that the VERDICT did not move.
# ---------------------------------------------------------------------------

def _rows(real, onsets):
    sys.path.insert(0, os.path.join(_ROOT, "bin"))
    from build_sdi_native_song import onset_gate_rows
    return onset_gate_rows(real, onsets)


class TestOnsetGateReport(unittest.TestCase):

    def test_a_quiet_voice_and_a_collapsed_voice_no_longer_look_alike(self):
        """The whole point: same emulated count, opposite meanings."""
        quiet_real = {0: [(10, 1)], 1: [(12, 1)], 2: [(f, 1) for f in range(0, 500, 3)]}
        quiet_em = [[10], [12], list(range(0, 500, 3))]
        collapsed_real = {0: [(10, 1)],
                          1: [(f, 1) for f in range(0, 350, 5)],
                          2: [(11, 1)]}
        collapsed_em = [[10], [0], [11]]

        quiet = _rows(quiet_real, quiet_em)
        collapsed = _rows(collapsed_real, collapsed_em)

        # voice 1 emulates ONE onset in both -- indistinguishable before
        self.assertEqual(quiet[1][1], 1)
        self.assertEqual(collapsed[1][1], 1)
        # ...and the trace column says one really has 1 and the other has 70
        self.assertEqual(quiet[1][0], 1)
        self.assertEqual(collapsed[1][0], 70)

    def test_matched_is_the_gate_numerator_split_by_voice(self):
        real = {0: [(5, 1), (9, 1)], 1: [(20, 1)], 2: []}
        onsets = [[5, 9], [999], []]
        rows = _rows(real, onsets)
        self.assertEqual([m for _, _, m in rows], [2, 0, 0])
        self.assertEqual(sum(m for _, _, m in rows), 2)
        self.assertEqual(sum(t for t, _, _ in rows), 3)

    def test_a_one_frame_slip_still_counts_as_matched(self):
        """The gate's +-1 tolerance is behaviour, not an accident."""
        rows = _rows({0: [(100, 1)], 1: [], 2: []}, [[101], [], []])
        self.assertEqual(rows[0][2], 1)
        rows = _rows({0: [(100, 1)], 1: [], 2: []}, [[102], [], []])
        self.assertEqual(rows[0][2], 0)

    def test_the_horizon_that_bounds_the_trace_side_is_still_700(self):
        rows = _rows({0: [(699, 1), (700, 1), (1200, 1)], 1: [], 2: []},
                     [[699], [], []])
        self.assertEqual(rows[0][0], 1)      # only frame 699 counts

    def test_the_emulated_column_is_the_number_the_old_line_printed(self):
        """len(onsets[v]), NOT the de-duplicated set -- so no reader is surprised."""
        rows = _rows({0: [], 1: [], 2: []}, [[7, 7, 8], [], []])
        self.assertEqual(rows[0][1], 3)

    def test_a_list_shaped_real_is_accepted_as_well_as_a_dict(self):
        as_dict = _rows({0: [(5, 1)], 1: [], 2: []}, [[5], [], []])
        as_list = _rows([[(5, 1)], [], []], [[5], [], []])
        self.assertEqual(as_dict, as_list)

    def test_the_verdict_is_unchanged_by_this_report(self):
        """agree/tot recomputed from the rows must equal the old pooled arithmetic."""
        real = {0: [(5, 1), (9, 1)], 1: [(20, 1), (30, 1)], 2: [(40, 1)]}
        onsets = [[5, 9], [21], [999]]
        rows = _rows(real, onsets)
        agree = sum(m for _, _, m in rows)
        tot = sum(t for t, _, _ in rows)
        old_agree = old_tot = 0
        for v in range(3):
            rl = set(fr for fr, _ in real[v] if fr < 700)
            em = set(onsets[v])
            old_agree += sum(1 for fr in rl if em & {fr - 1, fr, fr + 1})
            old_tot += len(rl)
        self.assertEqual((agree, tot), (old_agree, old_tot))
        self.assertEqual(bool(tot) and agree / tot >= 0.85,
                         bool(old_tot) and old_agree / old_tot >= 0.85)


class TestFiltAnchorDefault(unittest.TestCase):
    """SDI opts in to the pre-onset filter anchor; the shared default stays 0.

    Same shape as FILT_LEAD/FILT_EXACT_PB above: importing the SDI builder must
    raise BM.FILT_ANCHOR to 1, and an explicit env var must still win, because
    the A/B that justified it is driven that way.
    """

    def test_the_shared_default_is_0_and_the_sdi_import_raises_it_to_1(self):
        """Measured in a CLEAN interpreter, because this module's own test run
        has already imported the SDI builder and mutated the shared attribute --
        asserting it in-process reads 1 and proves nothing about the default."""
        code = (
            "import sys, os, io, contextlib\n"
            "sys.path.insert(0, os.path.join(%r, 'bin'))\n"
            "sys.path.insert(0, %r)\n"
            "sys.path.insert(0, os.path.join(%r, 'pyscript'))\n"
            "import build_mon_native_song as BM\n"
            "before = BM.FILT_ANCHOR\n"
            "buf = io.StringIO()\n"
            "with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):\n"
            "    import build_sdi_native_song\n"
            "print(repr((before, BM.FILT_ANCHOR)))\n"
        ) % (_ROOT, _ROOT, _ROOT)
        env = dict(os.environ)
        env.pop("FILT_ANCHOR", None)
        out = subprocess.run([sys.executable, "-c", code], cwd=_ROOT, env=env,
                             capture_output=True, text=True, timeout=300)
        if out.returncode != 0:
            raise AssertionError("probe failed: " + (out.stderr or "")[-800:])
        before, after = ast.literal_eval(out.stdout.strip().splitlines()[-1])
        self.assertEqual(before, 0, "the SHARED default must stay 0")
        self.assertEqual(after, 1, "importing the SDI builder must opt in")

    def test_an_explicit_env_var_still_wins(self):
        code = (
            "import sys, os, io, contextlib\n"
            "sys.path.insert(0, os.path.join(%r, 'bin'))\n"
            "sys.path.insert(0, %r)\n"
            "sys.path.insert(0, os.path.join(%r, 'pyscript'))\n"
            "import build_mon_native_song as BM\n"
            "buf = io.StringIO()\n"
            "with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):\n"
            "    import build_sdi_native_song\n"
            "print(BM.FILT_ANCHOR)\n"
        ) % (_ROOT, _ROOT, _ROOT)
        env = dict(os.environ)
        env["FILT_ANCHOR"] = "0"
        out = subprocess.run([sys.executable, "-c", code], cwd=_ROOT, env=env,
                             capture_output=True, text=True, timeout=300)
        self.assertEqual(out.stdout.strip().splitlines()[-1], "0",
                         out.stderr[-600:])

    def test_the_override_is_a_module_attribute_not_an_environ_mutation(self):
        src = open(os.path.join(_ROOT, "bin", "build_sdi_native_song.py"),
                   encoding="utf-8").read()
        self.assertIn('if "FILT_ANCHOR" not in os.environ:', src)
        self.assertIn("BM.FILT_ANCHOR = 1", src)
        self.assertNotIn('os.environ["FILT_ANCHOR"]', src)
