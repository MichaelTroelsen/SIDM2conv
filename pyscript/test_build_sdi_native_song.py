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
    return eval(out.stdout.strip().splitlines()[-1])          # noqa: S307


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
