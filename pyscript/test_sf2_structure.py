"""Tests for sidm2.verify_sf2_structure (the static SF2 validator).

Confirms each of the v3.5.35 reference SF2s parses without structural
issues — including Exorcist_preview which has the Block 2 native
redirect applied. The validator catches:
- missing 0x1337 magic
- truncated block chain / missing 0xFF terminator
- absent required blocks (1, 2, 3, 5)
- Block 2 declaring init/play/stop = $0000
- $1006 being inert zero gap (no #211 stamp where SF2II's scan
  would crash on F10-load)
"""
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pyscript.verify_sf2_structure import verify_sf2

ROOT = Path(__file__).parent.parent
SID_TO_SF2 = ROOT / "scripts" / "sid_to_sf2.py"


def _build_sf2(sid_path: Path) -> bytes:
    """Convert SID to SF2 and return the resulting bytes."""
    with tempfile.NamedTemporaryFile(suffix=".sf2", delete=False) as f:
        out = Path(f.name)
    out.unlink(missing_ok=True)
    r = subprocess.run(
        [sys.executable, str(SID_TO_SF2), str(sid_path), str(out), "-q"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if not out.exists():
        raise RuntimeError(f"SF2 build failed: {r.stderr[-400:]}")
    try:
        return out.read_bytes()
    finally:
        out.unlink(missing_ok=True)


class TestSF2Structure(unittest.TestCase):
    """Static structural validation of converter output."""

    SID_DIR = ROOT / "SID"

    def _check(self, sid_rel: str):
        sid_path = self.SID_DIR / sid_rel
        if not sid_path.exists():
            self.skipTest(f"reference SID missing: {sid_path}")
        # Build SF2 and write to temp file for validator
        sf2_bytes = _build_sf2(sid_path)
        with tempfile.NamedTemporaryFile(suffix=".sf2", delete=False) as f:
            sf2_path = Path(f.name)
            f.write(sf2_bytes)
        try:
            ok, issues = verify_sf2(sf2_path)
            self.assertTrue(ok,
                             f"{sid_rel} SF2 is structurally invalid: {issues}")
        finally:
            sf2_path.unlink(missing_ok=True)

    def test_stinsen(self):
        """Canonical NP21 (load=$1000)."""
        self._check("Stinsens_Last_Night_of_89.sid")

    def test_exorcist_preview_with_block2_redirect(self):
        """High-load file where v3.5.35 gate rewrote Block 2 to native
        PSID entry ($9000/$9006). Structurally identical except for
        Block 2 body bytes [0..1] and [4..5]; the rest is intact."""
        self._check("Laxity/Exorcist_preview.sid")

    def test_alliance(self):
        """Vibrants V20 (load=$E000) recovered by v3.5.31 init+3 fix."""
        self._check("Laxity/Alliance.sid")

    def test_dark_fun_gate_reverted_patches(self):
        """Dark_Fun: ch_seq_ptr gate reverts patches (file has
        binary diffs = 0 vs SID). Structure must still be valid
        with the reverted bytes."""
        self._check("Laxity/Dark_Fun.sid")

    def test_patterns_gate_nopped_wave_copy(self):
        """Patterns: gate NOPs the wave-copy JSR. Structure unchanged."""
        self._check("Laxity/Patterns.sid")

    def test_wizax_tune_low_load_alt_scan_window(self):
        """Wizax_tune (load=$0900): low-load layout. Block 1's
        m_DriverCodeTop is overridden to point at the post-binary
        handler region (NOT $1000-$18FF gap), and a `9D 00 D4 60`
        scan-bait sequence sits at HI+14. The #211 check must look
        up the actual scan window from Block 1, NOT assume the
        standard $1000 base — pins the v3.5.36 validator fix that
        eliminated a false positive on this file."""
        self._check("Laxity/Wizax_tune.sid")


if __name__ == "__main__":
    unittest.main(verbosity=2)
