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

Approach (v3.5.66): build the SF2 for canonical files via the full
conversion pipeline, then check the OUTPUT BYTES for each Stage 7
routine signature in addition to the log lines. The byte-signature
check protects against log-message rewording (someone renames the
log string but the emission is still working); the log-line check
remains as a sanity guard that the eligibility path was taken.
"""
import io
import logging
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2 import np21_codegen


ROOT = Path(__file__).parent.parent


def _convert_capture_logs_and_sf2(sid_path: Path):
    """Convert a SID in-process. Return (log_text, sf2_bytes).

    `sf2_bytes` is None if the conversion didn't produce a file.
    """
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
    root_logger = logging.getLogger()
    prev_level = root_logger.level
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    out_sf2 = ROOT / "out" / f"_test_{sid_path.stem[:36]}.sf2"
    try:
        from sidm2.conversion_pipeline import convert_sid_to_sf2
        out_sf2.parent.mkdir(parents=True, exist_ok=True)
        try:
            convert_sid_to_sf2(str(sid_path), str(out_sf2), quiet=True)
        except SystemExit:
            pass
    finally:
        root_logger.removeHandler(handler)
        root_logger.setLevel(prev_level)
    sf2_bytes = out_sf2.read_bytes() if out_sf2.exists() else None
    return buf.getvalue(), sf2_bytes


def _wave_split_copy_signature(n_rows: int = 32) -> bytes:
    """Return the first 8 bytes of the wave-split-copy routine emitted
    by np21_codegen for the canonical Stinsens addresses. These bytes
    are deterministic and form an in-output signature we can search
    for to verify the routine was actually emitted (not just logged)."""
    routine = np21_codegen.emit_wave_split_copy_routine(
        sf2_wave_addr=0x2000,
        np21_wave_data_addr=0x18DA,
        np21_note_addr=0x190C,
        n_rows=n_rows,
    )
    # First 4 bytes are the routine's opcode prelude — they're stable
    # across the addresses. We use a shorter prefix (4 bytes) so any
    # configured-address variant matches.
    return routine[:4]


def _cleanup_test_outputs():
    """Remove `out/_test_*.sf2` files left by past runs."""
    out_dir = ROOT / "out"
    if not out_dir.exists():
        return
    for f in out_dir.glob("_test_*.sf2"):
        try:
            f.unlink()
        except OSError:
            pass
    for f in out_dir.glob("_test_*.txt"):
        try:
            f.unlink()
        except OSError:
            pass


class TestStinsenStage7Emissions(unittest.TestCase):
    """Stinsens_Last_Night_of_89 is the canonical all-5-columns file.
    All 4 Stage 7 copy routines must fire for it."""

    @classmethod
    def setUpClass(cls):
        cls.log, cls.sf2 = _convert_capture_logs_and_sf2(
            ROOT / "SID" / "Stinsens_Last_Night_of_89.sid")

    @classmethod
    def tearDownClass(cls):
        _cleanup_test_outputs()

    def test_wave_split_copy_emitted_in_log(self):
        """Log signal that the F3 wave-copy emission path ran."""
        self.assertIn("Stage 7 wave-split-copy routine", self.log,
                      "F3 wave-split-copy must emit for Stinsens — this "
                      "test catches the v3.5.54 → v3.5.62 import-bug "
                      "class of silent regression")

    def test_wave_split_copy_bytes_in_sf2(self):
        """Output-byte signal that the routine was actually written —
        survives log-message rewording. v3.5.66."""
        self.assertIsNotNone(self.sf2, "SF2 file must be produced")
        sig = _wave_split_copy_signature(n_rows=32)
        self.assertIn(sig, self.sf2,
                      "wave-split-copy routine bytes not found in SF2 output")

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
        cls.log, cls.sf2 = _convert_capture_logs_and_sf2(
            ROOT / "SID" / "Beast.sid")

    @classmethod
    def tearDownClass(cls):
        _cleanup_test_outputs()

    def test_wave_split_copy_emitted(self):
        """Beast has wave_addr + wave_data_addr like Stinsen — wave-copy
        must emit (same v3.5.63-class import-bug guard)."""
        self.assertIn("Stage 7 wave-split-copy routine", self.log)

    def test_wave_split_copy_bytes_in_sf2(self):
        """v3.5.66: log-independent byte-signature check."""
        self.assertIsNotNone(self.sf2)
        sig = _wave_split_copy_signature(n_rows=32)
        self.assertIn(sig, self.sf2)

    def test_table_address_detection_did_not_fail(self):
        self.assertNotIn("Per-file table-address detection failed",
                         self.log)


class TestAngularStage7Emissions(unittest.TestCase):
    """Angular has F2+F3+F4+F5 wired (F1 skipped by ch_seq_ptr safety
    gate). The Angular-variant pulse/filter routines use different
    addresses from Stinsen/Beast."""

    @classmethod
    def setUpClass(cls):
        cls.log, cls.sf2 = _convert_capture_logs_and_sf2(
            ROOT / "SID" / "Angular.sid")

    @classmethod
    def tearDownClass(cls):
        _cleanup_test_outputs()

    def test_wave_split_copy_emitted(self):
        self.assertIn("Stage 7 wave-split-copy routine", self.log)

    def test_wave_split_copy_bytes_in_sf2(self):
        """v3.5.66: log-independent byte-signature check."""
        self.assertIsNotNone(self.sf2)
        sig = _wave_split_copy_signature(n_rows=32)
        self.assertIn(sig, self.sf2)

    def test_table_address_detection_did_not_fail(self):
        self.assertNotIn("Per-file table-address detection failed",
                         self.log)


class TestImportSurfaceMatchesUsage(unittest.TestCase):
    """Static check: any symbol used by the laxity_raw_np21_builder
    module at module-call sites must be importable from the module's
    namespace. Catches the import-vs-usage gap class of bug at test
    time, not at conversion-runtime time inside a broad except.

    v3.5.66: removed the duplicate Stinsens conversion that previously
    re-ran the full pipeline just to re-check the warning string.
    `TestStinsenStage7Emissions.test_table_address_detection_did_not_fail`
    already covers that case using the class-level log.
    """

    def test_extract_all_laxity_tables_is_importable(self):
        """The v3.5.63 regression: this symbol was used at line 267 of
        laxity_raw_np21_builder but missing from its import block."""
        from sidm2 import laxity_raw_np21_builder
        self.assertTrue(hasattr(laxity_raw_np21_builder,
                                "extract_all_laxity_tables"),
                        "extract_all_laxity_tables must be importable "
                        "in the module namespace — v3.5.63 fix")


if __name__ == "__main__":
    unittest.main(verbosity=2)
