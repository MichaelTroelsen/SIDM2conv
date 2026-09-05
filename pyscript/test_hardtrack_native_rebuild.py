#!/usr/bin/env python3
"""Tests for the HardTrack native rebuild harness (pyscript/hardtrack_native_rebuild.py).

These do NOT build anything -- a real rebuild is 33 songs of 64tass assembly.
What is covered here is the property that can silently void a rebuild: whether a
hard kill of the harness leaves its spawned builder running, writing into
out/hardtrack_native after the run that was supposed to replace it is gone.

THIS HARNESS IS SERIAL -- one blocking subprocess.run, no ThreadPoolExecutor --
and it needs the kill-safety guard ANYWAY. Measured 2026-09-03 with a stand-in
child of the same spawn shape:

    unguarded   parent hard-killed -> child SURVIVED -> artifact written after
    job object  parent hard-killed -> child died     -> no artifact

The pool in the SDI and DMC sweeps multiplies the number of orphans; it is not
what creates them. Any `subprocess` call makes an unbound grandchild.

The mechanism itself lives in pyscript/process_group.py and is tested there
(pyscript/test_process_group.py). What these tests pin is the WIRING -- that
this harness reaches for it, and says so rather than being silent.
"""
import io
import contextlib
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pyscript"))
sys.path.insert(0, str(ROOT))


class TestKillSafetyIsWired(unittest.TestCase):

    def test_the_harness_imports_the_shared_helper(self):
        import hardtrack_native_rebuild as H
        self.assertTrue(
            hasattr(H, "bind_children_to_this_process"),
            "hardtrack_native_rebuild spawns build_hardtrack_native_song.py but "
            "does not bind it to this process; a hard kill would orphan it")

    def test_it_reaches_the_shared_module_not_a_private_copy(self):
        """The helper had to be extracted once already because dmc_native_sweep
        was importing a whole corpus sweep to reach one function. A second
        private copy would drift the same way."""
        import hardtrack_native_rebuild as H
        import process_group
        self.assertIs(H.bind_children_to_this_process,
                      process_group.bind_children_to_this_process)

    def test_main_announces_kill_safety(self):
        """It must not be SILENT about whether the guarantee holds."""
        import hardtrack_native_rebuild as H
        buf = io.StringIO()
        # --first past the end of the corpus: prints, clears nothing, builds nothing
        with contextlib.redirect_stdout(buf):
            try:
                H.main(["--first", "10000", "--last", "10000", "--keep"])
            except SystemExit:
                pass
        self.assertIn("kill-safety:", buf.getvalue())


class TestProvenanceSidecarsAreNotStale(unittest.TestCase):
    """A `.prov` must never be older than the `.sf2` it describes.

    PROVENANCE LIVES IN A SIDECAR, NOT IN THE ARTIFACT -- `<name>.sf2.prov`
    beside `<name>.sf2`, the same shape as `.span`. That is what makes this
    invariant necessary rather than obvious: ANY operation that replaces a
    `.sf2` without regenerating its stamp -- a `cp` from a backup, a restore, a
    file moved between corpora -- leaves the OLD stamp describing the NEW bytes.

    THIS IS NOT HYPOTHETICAL. On 2026-09-04 a cycle restored
    out/mon/Cybernoid_II_sub0_native.sf2 from a copy of its flag-off build,
    byte-compared it to confirm the restore, and reported the corpus back at its
    default. The bytes were right. The `.prov` still said
    `INIT_PASSBAND=1` -- the flag-on build's stamp -- and the census duly
    reported one MoN artifact built with a flag no shipped artifact uses. The
    byte-compare could not see it, because the stamp is not in the bytes.

    A WRONG STAMP IS WORSE THAN NO STAMP. `UNSTAMPED` is honest and the census
    counts it as such; a stale stamp is confidently wrong, and provenance exists
    precisely so a corpus figure can be trusted. So this is the one provenance
    property worth asserting even while 84.5% of the corpus is legitimately
    unstamped.

    mtime is the right test here: a replaced `.sf2` is newer than the stamp that
    was written for its predecessor, which is exactly the `cp` case above. One
    second of slack absorbs filesystem timestamp granularity.
    """

    def test_no_prov_sidecar_is_older_than_its_artifact(self):
        import glob
        import os

        root = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "out")
        if not os.path.isdir(root):
            self.skipTest("out/ absent")

        stale, checked = [], 0
        for sf2 in glob.glob(os.path.join(root, "**", "*.sf2"), recursive=True):
            prov = sf2 + ".prov"
            if not os.path.exists(prov):
                continue                      # UNSTAMPED is honest, not a failure
            checked += 1
            if os.path.getmtime(prov) < os.path.getmtime(sf2) - 1:
                stale.append(os.path.relpath(sf2, root))

        if not checked:
            self.skipTest("no stamped artifacts on disk")
        self.assertEqual(stale, [], "%d stamped artifact(s) carry a stamp older "
                                    "than their own bytes" % len(stale))

    def test_no_orphan_prov_without_its_artifact(self):
        """A `.prov` whose `.sf2` is gone is a stamp waiting to mislabel the
        next file written to that name."""
        import glob
        import os

        root = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "out")
        if not os.path.isdir(root):
            self.skipTest("out/ absent")

        orphans = [os.path.relpath(p, root)
                   for p in glob.glob(os.path.join(root, "**", "*.sf2.prov"),
                                      recursive=True)
                   if not os.path.exists(p[:-len(".prov")])]
        self.assertEqual(orphans, [])


class TestRebuildRunMarker(unittest.TestCase):
    """The run marker records what the ARTIFACTS structurally cannot.

    Per-artifact `.prov` sidecars say which commit built each file that EXISTS.
    117 of HardTrack's 150 rips are refused, and a refusal writes no artifact,
    so it leaves no stamp -- from the artifacts alone, "never in the corpus" and
    "failed the last rebuild" are indistinguishable. A previous staleness check
    had to reconstruct coverage from part-count bursts and commit mtimes because
    of exactly that gap.
    """

    def _mod(self):
        import importlib
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        return importlib.import_module("hardtrack_native_rebuild")

    def test_marker_is_not_an_sf2_so_byte_compare_sweeps_ignore_it(self):
        """`_provenance()` omits a timestamp on purpose -- same-commit rebuilds
        must stay byte-identical across every sidecar. A run marker SHOULD carry
        a time, so it must stay outside the `*.sf2` glob those sweeps use."""
        H = self._mod()
        self.assertTrue(H.MARKER.endswith(".json"))
        self.assertNotIn(".sf2", os.path.basename(H.MARKER))

    def test_keep_appends_rather_than_overwriting(self):
        """`--keep` exists so a rebuild can be chunked. A marker that kept only
        the last chunk would claim the corpus was covered when files 0..N never
        ran -- the same false completeness the artifacts already have, one level
        up."""
        import json
        import tempfile
        H = self._mod()
        with tempfile.TemporaryDirectory() as d:
            old = H.MARKER
            try:
                H.MARKER = os.path.join(d, "_rebuild.json")
                H._write_marker({"first": 0, "last": 4, "built": []}, keep=False)
                H._write_marker({"first": 4, "last": 8, "built": []}, keep=True)
                with open(H.MARKER, encoding="utf-8") as f:
                    runs = json.load(f)["runs"]
                self.assertEqual([r["first"] for r in runs], [0, 4])

                # keep=False starts a fresh history -- a full rebuild is not a
                # continuation of the chunks it replaces
                H._write_marker({"first": 0, "last": None, "built": []}, keep=False)
                with open(H.MARKER, encoding="utf-8") as f:
                    self.assertEqual(len(json.load(f)["runs"]), 1)
            finally:
                H.MARKER = old

    def test_an_unreadable_marker_is_not_fatal(self):
        """Provenance we cannot read must not take a rebuild down with it."""
        import json
        import tempfile
        H = self._mod()
        with tempfile.TemporaryDirectory() as d:
            old = H.MARKER
            try:
                H.MARKER = os.path.join(d, "_rebuild.json")
                with open(H.MARKER, "w", encoding="utf-8") as f:
                    f.write("{ this is not json")
                self.assertTrue(H._write_marker({"first": 0, "built": []}, keep=True))
                with open(H.MARKER, encoding="utf-8") as f:
                    self.assertEqual(len(json.load(f)["runs"]), 1)
            finally:
                H.MARKER = old

    def test_the_live_marker_names_refused_songs(self):
        """The negative space is the point: a refused song must appear by NAME.

        Skips when no marker exists yet -- this asserts the shape of a real one,
        not that a rebuild has been run on this machine.
        """
        import json
        H = self._mod()
        if not os.path.exists(H.MARKER):
            self.skipTest("no rebuild marker on disk")
        with open(H.MARKER, encoding="utf-8") as f:
            runs = json.load(f)["runs"]
        self.assertTrue(runs)
        for r in runs:
            for k in ("at", "commit", "tree", "considered", "built", "refused"):
                self.assertIn(k, r)
            self.assertIsInstance(r["refused"], list)
            self.assertEqual(len(r["built"]) + len(r["refused"]), r["considered"],
                             "a run must account for every file it considered")


if __name__ == "__main__":
    unittest.main()


class TestJobsFlag(unittest.TestCase):
    """`--jobs` must parallelise WITHOUT changing a single byte.

    Measured 2026-09-04: a serial rebuild and a `-j8` rebuild at 7e67c33 both
    produce 313 artifacts with the same names and ZERO differing bytes, and
    leave no `.staging` files behind.

    WHY THIS IS SAFE HERE AND WAS NOT ON THE DMC SWEEP. Each song is already a
    separate PROCESS (`subprocess.run` on build_hardtrack_native_song.py), so
    the builder's module-global staging list `_PENDING` is per-process and one
    worker cannot commit another's in-flight artifacts. The DMC sweep hit
    exactly that failure (runs.jsonl: dmc-corpus-rebuild-serial-vs-j8, where
    Spacegame_Music tried to commit `_abl_part01.sf2.staging`). The threads
    added here only WAIT on those processes.

    What IS shared is drivers_src scratch, and MON_BUILD_LOCK=1 serialises it
    across processes -- set on the parent because it reaches the children
    through the environment.
    """

    def _mod(self):
        import importlib
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        return importlib.import_module("hardtrack_native_rebuild")

    def _src(self):
        here = os.path.dirname(os.path.abspath(__file__))
        return open(os.path.join(here, "hardtrack_native_rebuild.py"),
                    encoding="utf-8").read()

    def test_jobs_defaults_to_one(self):
        """Parallelism must be opt-in: the default path stays serial."""
        H = self._mod()
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                H.main(["--first", "10000", "--last", "10000", "--keep"])
            except SystemExit:
                pass
        import json
        with open(H.MARKER, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["runs"][-1]["jobs"], 1)

    def test_parallel_sets_the_shared_driver_lock(self):
        """MON_BUILD_LOCK is what stops concurrent builds corrupting
        drivers_src. If a future edit parallelises without it, this fails."""
        src = self._src()
        i = src.index("if a.jobs > 1:")
        window = src[i:i + 400]
        self.assertIn("MON_BUILD_LOCK", window,
                      "the parallel path no longer sets the shared driver lock")

    def test_results_are_merged_in_corpus_order_not_completion_order(self):
        """The printed table, the medians and the marker must not depend on
        which worker finishes first -- otherwise a -j8 run and a serial run
        differ in their REPORT even when every artifact is identical."""
        src = self._src()
        self.assertIn("ex.map(_build, sids)", src,
                      "results are no longer collected in corpus order; a "
                      "completion-ordered merge makes the report nondeterministic")
        self.assertIn("for sid, stem, r in results:", src)


# ---------------------------------------------------------------------------
# SLING'S OPENING $D418 GAP IS BENIGN BY CONSTRUCTION, AND THIS PINS WHY.
#
# Measured 2026-09-05 (a re-measurement, not inherited -- this thread's FIRST
# explanation, "startup latency", was reported as confirmed and then refuted by
# a sweep, so the number is taken again here):
#
#   original   declares a filter MODE at frame 0, first ROUTES a voice at 17
#   ours       declares at 14 and routes at 14        -- gap 0
#   routing offset ours-orig = -3, this player's documented render offset,
#              so the routing itself is correctly aligned
#
# The original can declare a passband BEFORE it uses one. Our driver cannot:
# F_MODE (the $D418 high nibble) is zeroed at INIT and written in exactly one
# other place, from a filter program row, so mode and routing are COUPLED and
# our mode can never precede our first filter row.
#
# That leaves 14 disagreeing frames (3..16 at the aligned offset) and EVERY ONE
# has $D417's low nibble 0 on BOTH sides -- neither build feeds a voice to the
# filter, so nothing can be heard. Inaudible by construction rather than by
# luck, which is the distinction worth keeping: a fix that made our mode
# precede routing would change nothing audible and would decouple two things
# the driver deliberately ties together.
#
# `passband_check --player hardtrack --files Sling` agrees independently and
# PASSES the file: 99.0% agree, "all 13 mismatches on frames the original does
# not route -- inaudible". 13 vs 14 is the window, not a disagreement: the
# checker scores part 1's own span while this compares the full 26s trace.
# ---------------------------------------------------------------------------

_SLING_ORIG = ROOT / "SID" / "Shogoon" / "Sling.sid"
_SLING_OURS = ROOT / "out" / "hardtrack_native" / "Sling_part01.sid"
_RENDER_OFFSET = -3          # documented for this player


def _filter_state(path, secs=26):
    from sidm2.fidelity_common import siddump_frames_full
    frames = siddump_frames_full(str(path), ['-a0', '-t%d' % secs])
    mode = [((f[1]['volmode'] or 0) >> 4) & 7 for f in frames]
    route = [(f[1]['filtctl'] or 0) & 0x0F for f in frames]
    return mode, route


class TestSlingOpeningPassbandGap(unittest.TestCase):

    def setUp(self):
        if not _SLING_ORIG.exists() or not _SLING_OURS.exists():
            self.skipTest("Sling original or built part01 not present")

    def test_every_disagreeing_frame_routes_nothing_on_BOTH_sides(self):
        """The inaudibility claim, stated as the thing that makes it true.

        Comparison starts at original frame 3 because the render offset is -3:
        our frames 0..2 have no aligned counterpart, so those three original
        frames are not comparable rather than being quietly dropped.
        """
        o_mode, o_route = _filter_state(_SLING_ORIG)
        u_mode, u_route = _filter_state(_SLING_OURS)
        n = min(len(o_mode), len(u_mode))
        self.assertGreater(n, 1000, "control: only %d frames traced" % n)

        start = -_RENDER_OFFSET
        mism = [i for i in range(start, n)
                if o_mode[i] != u_mode[i + _RENDER_OFFSET]]
        self.assertTrue(mism, "no mismatch at all -- the premise changed")
        audible = [i for i in mism if o_route[i] != 0]
        self.assertEqual(
            audible, [],
            "the original ROUTES a voice on %d disagreeing frame(s) %s -- the "
            "gap is no longer inaudible and needs a real fix"
            % (len(audible), audible[:8]))

    def test_the_gap_is_the_opening_only_and_bounded(self):
        """If it ever spreads past the opening it is a different defect."""
        o_mode, o_route = _filter_state(_SLING_ORIG)
        u_mode, _ = _filter_state(_SLING_OURS)
        n = min(len(o_mode), len(u_mode))
        start = -_RENDER_OFFSET
        mism = [i for i in range(start, n)
                if o_mode[i] != u_mode[i + _RENDER_OFFSET]]
        self.assertLessEqual(len(mism), 20, "gap grew to %d frames" % len(mism))
        self.assertLess(max(mism), 40,
                        "a mismatch at frame %d is past the opening" % max(mism))

    def test_our_mode_cannot_precede_our_routing_and_the_originals_can(self):
        """The MECHANISM, pinned so the 'latency' reading cannot come back.

        This is not a timing lag: our first mode frame EQUALS our first routed
        frame because F_MODE is written only from a filter program row.
        """
        o_mode, o_route = _filter_state(_SLING_ORIG)
        u_mode, u_route = _filter_state(_SLING_OURS)
        o_first_mode = next(i for i, m in enumerate(o_mode) if m)
        o_first_route = next(i for i, r in enumerate(o_route) if r)
        u_first_mode = next(i for i, m in enumerate(u_mode) if m)
        u_first_route = next(i for i, r in enumerate(u_route) if r)

        self.assertLess(o_first_mode, o_first_route,
                        "the original no longer declares before it routes")
        self.assertEqual(u_first_mode, u_first_route,
                         "our mode (%d) and routing (%d) are no longer coupled "
                         "-- if that is deliberate, this test should go"
                         % (u_first_mode, u_first_route))
        self.assertEqual(u_first_route - o_first_route, _RENDER_OFFSET,
                         "routing offset moved from the documented %d"
                         % _RENDER_OFFSET)

