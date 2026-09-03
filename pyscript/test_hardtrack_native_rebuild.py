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


if __name__ == "__main__":
    unittest.main()
