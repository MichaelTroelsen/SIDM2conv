"""ROADMAP A4: the native dispatcher is wired in and no longer inert.

WHAT "WIRED IN" MEANS HERE, AND WHAT IT DELIBERATELY DOES NOT MEAN.
`sidm2.conversion_pipeline.native_builder_for()` NAMES the `bin/` builder that
owns a file; it never runs one and never sets `driver_type`. Every
`bin/build_*_native_song.py` reads `SID = sys.argv[1]` at module scope and then
siddumps, emulates and traces the tune for tens of seconds to minutes, so it is
a subprocess entry point rather than an importable converter.

The corpus figures quoted below were measured 2026-08-21 over 734 files. They
are recorded as prose, not asserted: a test that pins "160 of 441" fails the day
a probe learns a variant, which is a doc update and not a regression. What IS
asserted is the mechanism -- that a signature family answers confidently, that a
construct-only family answers as a candidate only, and that neither ever moves
the selected SF2 driver.
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.conversion_pipeline import native_builder_for
from sidm2.driver_selector import DriverSelector

REPO = Path(__file__).resolve().parents[1]

# Both are TRACKED in git, so this suite runs from a fresh clone.
# Both also have shipped Stage B artifacts, which is the external ground truth
# the HardTrack probe was validated against: out/sdi holds 93 Bahbar parts and
# out/dmc holds 2 Balloon parts (2026-08-21 disk count).
SDI_RIP = REPO / 'SID' / 'Gallefoss_Glenn' / 'Bahbar.sid'
DMC_RIP = REPO / 'SID' / 'JohannesBjerregaard' / 'Balloon.sid'


class TestNativeBuilderRouting(unittest.TestCase):
    """The verify clause: a known DMC and a known SDI rip reach their builders."""

    def test_a_known_sdi_rip_routes_to_the_sdi_native_builder(self):
        r = native_builder_for(str(SDI_RIP))
        self.assertIsNotNone(r, 'no family accepted a known SDI rip')
        self.assertEqual(r['family'], 'sdi')
        self.assertEqual(r['builder'], 'bin/build_sdi_native_song.py')
        # `is_sdi_play3` is a real signature, so this one is answerable.
        self.assertTrue(r['confident'])

    def test_a_known_dmc_rip_names_the_dmc_builder_but_only_as_a_candidate(self):
        """AND THE UNCONFIDENT HALF IS THE POINT, NOT A SHORTFALL.

        `_probe_dmc` has no signature -- `_locate` finds plausible tables in
        anything and `decode_song` still yields notes -- so `dmc` accepted all
        48 files of the original spread sample and all 88 of its own corpus.
        `rank()` therefore returns best=None for every DMC file, by design and
        by measurement, and promoting it would re-run a scoring rule this repo
        has already refuted twice (see the comments in native_dispatch.rank).

        So the builder is NAMED and the answer is graded `confident=False`. A
        caller that reads `family` without reading `confident` gets a plausible
        wrong answer, which is why the pipeline's own warning path tests
        `native_confident` and not `native_family`.
        """
        r = native_builder_for(str(DMC_RIP))
        self.assertIsNotNone(r)
        self.assertEqual(r['family'], 'dmc')
        self.assertEqual(r['builder'], 'bin/build_dmc_native_song.py')
        self.assertFalse(r['confident'])
        self.assertIn('dmc', r['candidates'])

    def test_the_two_answers_are_graded_differently(self):
        """If both came back the same grade the grading would be decorative."""
        self.assertNotEqual(native_builder_for(str(SDI_RIP))['confident'],
                            native_builder_for(str(DMC_RIP))['confident'])


class TestAdvisoryNeverChangesTheDriver(unittest.TestCase):
    """The safety property. A misroute must stay a log line, never an SF2.

    Measured over 734 files there are zero signature collisions -- but six
    SID/Gray_Matt files rank `soundmonitor` CONFIDENTLY, among them
    `Sanxion_Re-load` and `Crazy_Comets_Special_Re-Mix`, while `is_soundmonitor`
    accepts only 11 of the 20 files in its own SID/Fun_Fun corpus. A unique
    signature match is the strongest evidence this dispatcher has and it is
    still not proof of ownership, so the driver decision must not depend on it.
    """

    def test_selection_carries_the_advisory_without_changing_driver_name(self):
        sel_with = DriverSelector().select_driver(SDI_RIP)
        # The driver the string-based policy would have chosen, computed
        # WITHOUT the dispatcher, must be unchanged by the dispatcher.
        s = DriverSelector()
        expected = s._select_best_driver(s.identify_player(SDI_RIP))
        self.assertEqual(sel_with.driver_name, expected)
        self.assertEqual(sel_with.native_family, 'sdi')
        self.assertTrue(sel_with.native_confident)

    def test_a_forced_driver_still_gets_told_a_native_builder_exists(self):
        """The expert-override path is where the advisory matters MOST: forcing
        driver11 on a native rip is exactly the 1-8% case."""
        sel = DriverSelector().select_driver(SDI_RIP, force_driver='driver11')
        self.assertEqual(sel.driver_name, 'driver11')
        self.assertEqual(sel.native_family, 'sdi')

    def test_an_unconfident_advisory_prints_as_a_candidate(self):
        sel = DriverSelector().select_driver(DMC_RIP)
        out = DriverSelector().format_selection_output(sel)
        self.assertIn('CANDIDATE ONLY', out)
        self.assertIn('build_dmc_native_song.py', out)

    def test_a_confident_advisory_does_not_print_as_a_candidate(self):
        sel = DriverSelector().select_driver(SDI_RIP)
        out = DriverSelector().format_selection_output(sel)
        self.assertNotIn('CANDIDATE ONLY', out)
        self.assertIn('build_sdi_native_song.py', out)


class TestBuilderMapIsHonest(unittest.TestCase):
    """A mapping that names a script which is not there is worse than no map:
    the advisory would print a command the user cannot run."""

    def test_every_named_builder_exists_on_disk(self):
        missing = [(f, b) for f, b in DriverSelector.NATIVE_BUILDERS.items()
                   if not (REPO / b).exists()]
        self.assertEqual(missing, [])

    def test_every_probed_family_has_a_builder(self):
        from sidm2.native_dispatch import PROBE_ORDER
        families = {p for p, _ in PROBE_ORDER}
        self.assertEqual(families - set(DriverSelector.NATIVE_BUILDERS), set())
        self.assertEqual(set(DriverSelector.NATIVE_BUILDERS) - families, set())


class TestDispatcherFailureIsNotADriverFailure(unittest.TestCase):
    """A broken probe must never degrade driver selection silently -- and must
    never crash it either. `identify_native_builder` swallows ProbeBug on
    purpose: the dispatcher's own suite is where a probe bug belongs."""

    def test_a_probe_bug_leaves_the_driver_choice_intact(self):
        from sidm2 import native_dispatch

        def boom(path, player_id=None):
            raise native_dispatch.ProbeBug('deliberate')

        real, native_dispatch.rank = native_dispatch.rank, boom
        try:
            sel = DriverSelector().select_driver(SDI_RIP)
        finally:
            native_dispatch.rank = real
        self.assertEqual(sel.native_family, '')
        self.assertTrue(sel.driver_name)      # still chose a driver

    def test_any_other_dispatcher_failure_is_tolerated(self):
        """AND HERE IS WHAT THIS TEST DOES NOT COVER, WRITTEN DOWN RATHER THAN
        LEFT AS A GREEN TICK. `identify_native_builder` also guards the IMPORT
        of `sidm2.native_dispatch` with `except ImportError`, and that branch is
        not reachable from here: `from sidm2 import native_dispatch` resolves
        the attribute already bound on the package, so stubbing
        `sys.modules['sidm2.native_dispatch']` does not raise -- the first
        version of this test asserted it did and FAILED, returning `sdi`.

        The guard stays because a partial checkout is a real shape, but the
        branch it protects is untested and this docstring is the record of it.
        What is tested is the reachable half: any exception out of `rank()`
        (ImportError included, since the handler is broad) degrades to "no
        advisory" rather than taking down driver selection.
        """
        from sidm2 import native_dispatch

        def boom(path, player_id=None):
            raise ImportError('deliberate: a dependency of a probe is missing')

        real, native_dispatch.rank = native_dispatch.rank, boom
        try:
            sel = DriverSelector().select_driver(SDI_RIP)
        finally:
            native_dispatch.rank = real
        self.assertEqual(sel.native_family, '')
        self.assertTrue(sel.driver_name)


if __name__ == '__main__':
    unittest.main()
