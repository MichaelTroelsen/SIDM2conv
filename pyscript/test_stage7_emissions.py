"""Stage 7 emission regression tests — defensive guard against the
v3.5.54 → v3.5.62 silent regression class.

This test class is the gap that would have caught the v3.5.63 fix
nine releases earlier. The bug: a missing import in
`laxity_raw_np21_builder` caused `extract_all_laxity_tables` to
NameError inside a broad `try/except`, leaving
`np21_note_binary_addr` / `np21_wave_data_binary_addr` as None.
The wave-split-copy emission's eligibility check tested those
against `is not None`, so wave-split-copy silently didn't emit.

Audio fidelity was preserved (the v3.5.33 gate NOPs wave-copy when
it diverges anyway), so the C2 byte-comparison suite couldn't see
the regression. Only the editor-side F3 propagation was affected,
and nothing in the test suite exercised it.

Approach: build the SF2 for canonical files via the full conversion
pipeline, then check the conversion log for each Stage 7 emission
line. Log-line presence is the cheapest signal that the emission
path took the expected branch; it doesn't depend on the SF2 bytes
matching across refactors.
"""
import logging
import io
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


ROOT = Path(__file__).parent.parent


def _convert_capture_logs(sid_path: Path):
    """Convert a SID to a tmp SF2 and return the captured INFO+WARNING logs.

    Uses the same code path as the CLI converter but runs in-process so
    we get the log stream cleanly. Returns the concatenated log text.
    """
    # Capture all loggers at INFO+ to a single buffer.
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
    root_logger = logging.getLogger()
    prev_level = root_logger.level
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    try:
        from sidm2.conversion_pipeline import convert_sid_to_sf2
        out_sf2 = ROOT / "out" / f"_test_{sid_path.stem[:36]}.sf2"
        out_sf2.parent.mkdir(parents=True, exist_ok=True)
        try:
            convert_sid_to_sf2(str(sid_path), str(out_sf2), quiet=True)
        except SystemExit:
            # Some conversion paths call sys.exit on certain branches;
            # the log capture is what matters here.
            pass
    finally:
        root_logger.removeHandler(handler)
        root_logger.setLevel(prev_level)
    return buf.getvalue()


class TestStinsenStage7Emissions(unittest.TestCase):
    """Stinsens_Last_Night_of_89 is the canonical all-5-columns file.
    All 4 Stage 7 copy routines must fire for it."""

    @classmethod
    def setUpClass(cls):
        cls.log = _convert_capture_logs(
            ROOT / "SID" / "Stinsens_Last_Night_of_89.sid")

    def test_wave_split_copy_emitted(self):
        """F3 wave-copy: the v3.5.63 regression we just fixed."""
        self.assertIn("Stage 7 wave-split-copy routine", self.log,
                      "F3 wave-split-copy must emit for Stinsens — this "
                      "test catches the v3.5.54 → v3.5.62 import-bug "
                      "class of silent regression")

    def test_instr_column_copy_emitted(self):
        """F2 instrument AD+SR column-copy."""
        self.assertIn("Stage 7 instr-column-copy Stinsen", self.log)

    def test_pulse_split_copy_emitted(self):
        """F4 pulse PW lo/hi split-copy."""
        self.assertIn("Stage 7 pulse-split-copy Stinsen", self.log)

    def test_filter_split_copy_emitted(self):
        """F5 filter cmd/val/aux split-copy."""
        self.assertIn("Stage 7 filter-split-copy Stinsen", self.log)

    def test_table_address_detection_did_not_fail(self):
        """v3.5.63 regression class: the bare `except Exception` block
        around extract_all_laxity_tables would emit a
        'Per-file table-address detection failed' warning when any
        symbol inside it was missing or broken. That warning is the
        smoking gun for the import-bug class — if it ever fires for
        Stinsens, something structurally broke."""
        self.assertNotIn("Per-file table-address detection failed",
                         self.log,
                         "table-address detection block raised an "
                         "exception (likely a missing import or "
                         "structural refactor regression — see "
                         "memory/v3.5.63-import-fix.md)")


class TestBeastStage7Emissions(unittest.TestCase):
    """Beast uses Beast-class variants of pulse/filter/instr emitters
    (different addresses from Stinsen). F2/F4/F5 must emit, F1 is
    skipped by the ch_seq_ptr safety gate."""

    @classmethod
    def setUpClass(cls):
        cls.log = _convert_capture_logs(ROOT / "SID" / "Beast.sid")

    def test_wave_split_copy_emitted(self):
        """Beast has wave_addr + wave_data_addr like Stinsen — wave-copy
        must emit (same v3.5.63-class import-bug guard)."""
        self.assertIn("Stage 7 wave-split-copy routine", self.log)

    def test_table_address_detection_did_not_fail(self):
        self.assertNotIn("Per-file table-address detection failed",
                         self.log)


class TestAngularStage7Emissions(unittest.TestCase):
    """Angular has F2+F3+F4+F5 wired (F1 skipped by ch_seq_ptr safety
    gate). The Angular-variant pulse/filter routines use different
    addresses from Stinsen/Beast."""

    @classmethod
    def setUpClass(cls):
        cls.log = _convert_capture_logs(ROOT / "SID" / "Angular.sid")

    def test_wave_split_copy_emitted(self):
        self.assertIn("Stage 7 wave-split-copy routine", self.log)

    def test_table_address_detection_did_not_fail(self):
        self.assertNotIn("Per-file table-address detection failed",
                         self.log)


class TestImportSurfaceMatchesUsage(unittest.TestCase):
    """Static check: any symbol used by the laxity_raw_np21_builder
    module at module-call sites must be importable from the module's
    namespace. Catches the import-vs-usage gap class of bug at test
    time, not at conversion-runtime time inside a broad except."""

    def test_extract_all_laxity_tables_is_importable(self):
        """The v3.5.63 regression: this symbol was used at line 267 of
        laxity_raw_np21_builder but missing from its import block."""
        from sidm2 import laxity_raw_np21_builder
        self.assertTrue(hasattr(laxity_raw_np21_builder,
                                "extract_all_laxity_tables"),
                        "extract_all_laxity_tables must be importable "
                        "in the module namespace — v3.5.63 fix")

    def test_no_nameerror_when_calling_with_known_file(self):
        """End-to-end: convert Stinsens and verify the warning that
        indicates the import-bug class never fires."""
        log = _convert_capture_logs(
            ROOT / "SID" / "Stinsens_Last_Night_of_89.sid")
        # The warning text is the smoking gun for the v3.5.54-class
        # regression. If it appears, something is broken.
        self.assertNotIn("Per-file table-address detection failed",
                         log)
        self.assertNotIn("NameError", log)


if __name__ == "__main__":
    unittest.main(verbosity=2)
