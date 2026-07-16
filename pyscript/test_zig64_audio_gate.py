"""Tests for sidm2.zig64_audio_gate.

Cycle-accurate post-build audio verification. Run zig64 on the SF2 vs
the original SID over a short window; the gate returns True iff their
(frame, register, value) tuples match exactly.
"""
import shutil
import struct
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.zig64_audio_gate import verify_sf2_audio


class TestZig64AudioGate(unittest.TestCase):
    """End-to-end checks against the project's bundled .sid/.sf2 corpus."""

    ROOT = Path(__file__).parent.parent
    SID_DIR = ROOT / "SID"
    TRACER = ROOT / "tools" / "sidm2-sid-trace.exe"

    @classmethod
    def setUpClass(cls):
        if not cls.TRACER.exists():
            raise unittest.SkipTest(f"tracer not present: {cls.TRACER}")

    def _build_sf2(self, sid_path: Path) -> bytes:
        """Convert sid -> sf2 via the project's CLI and return SF2 bytes."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".sf2", delete=False) as f:
            out = Path(f.name)
        out.unlink(missing_ok=True)
        r = subprocess.run(
            [sys.executable, str(self.ROOT / "scripts" / "sid_to_sf2.py"),
             str(sid_path), str(out), "-q"],
            capture_output=True, text=True, cwd=str(self.ROOT),
        )
        if not out.exists():
            self.fail(f"SF2 build failed for {sid_path}: {r.stderr[-500:]}")
        try:
            return out.read_bytes()
        finally:
            out.unlink(missing_ok=True)

    def _psid_init_play(self, sid_path: Path):
        d = sid_path.read_bytes()
        ia = struct.unpack(">H", d[10:12])[0]
        pa = struct.unpack(">H", d[12:14])[0]
        if pa == 0:
            pa = ia + 3
        return ia, pa

    def test_stinsen_audio_matches(self):
        """Stinsen is the canonical perfect-pass reference. Gate must
        return True."""
        sid = self.SID_DIR / "Stinsens_Last_Night_of_89.sid"
        if not sid.exists():
            self.skipTest(f"missing {sid}")
        sf2 = self._build_sf2(sid)
        ia, pa = self._psid_init_play(sid)
        self.assertTrue(
            verify_sf2_audio(sf2, sid, 0x0F90, 0x0F94, ia, pa,
                              tracer_path=self.TRACER, frames=16),
            "Stinsen SF2 audio must match SID under zig64"
        )

    def test_returns_true_when_tracer_missing(self):
        """If the tracer binary isn't installed, the gate degrades
        gracefully: return True (= caller proceeds as before)."""
        sid = self.SID_DIR / "Stinsens_Last_Night_of_89.sid"
        if not sid.exists():
            self.skipTest(f"missing {sid}")
        sf2 = self._build_sf2(sid)
        ia, pa = self._psid_init_play(sid)
        bogus_tracer = self.ROOT / "no_such_tool.exe"
        self.assertFalse(bogus_tracer.exists(),
                          "test setup error: bogus path must NOT exist")
        self.assertTrue(
            verify_sf2_audio(sf2, sid, 0x0F90, 0x0F94, ia, pa,
                              tracer_path=bogus_tracer, frames=4),
            "Missing tracer → gate should return True (skip verification)"
        )

    def test_corrupted_sf2_audio_diverges(self):
        """If we deliberately corrupt the SF2 binary at a sensitive
        location (e.g. zero out the embedded NP21 player at $1000+),
        the gate must return False."""
        sid = self.SID_DIR / "Stinsens_Last_Night_of_89.sid"
        if not sid.exists():
            self.skipTest(f"missing {sid}")
        sf2 = bytearray(self._build_sf2(sid))
        sf2_load = struct.unpack("<H", sf2[0:2])[0]
        # Zero 256 bytes of the embedded binary at $1000 (the player's
        # entry region — this WILL break audio).
        o = 0x1000 - sf2_load + 2
        for i in range(256):
            if o + i < len(sf2):
                sf2[o + i] = 0
        ia, pa = self._psid_init_play(sid)
        self.assertFalse(
            verify_sf2_audio(bytes(sf2), sid, 0x0F90, 0x0F94, ia, pa,
                              tracer_path=self.TRACER, frames=8),
            "Corrupted SF2 must diverge from SID under zig64"
        )


class TestZig64AudioGateFailsClosed(unittest.TestCase):
    """The gate must never treat *absence of evidence* as a match.

    Regression for a silent false-pass: when the tracer could not drive a
    file at all it emitted an empty trace, so an empty SID trace and an
    empty SF2 trace compared equal (len 0 == len 0, loop body never ran)
    and the gate returned True — certifying output it had never checked.
    """

    ROOT = Path(__file__).parent.parent
    SID_DIR = ROOT / "SID"
    TRACER = ROOT / "tools" / "sidm2-sid-trace.exe"

    def test_empty_reference_trace_returns_false(self):
        """An empty reference trace means nothing was verified → False."""
        from unittest import mock
        sid = self.SID_DIR / "Stinsens_Last_Night_of_89.sid"
        if not sid.exists():
            self.skipTest(f"missing {sid}")
        if not self.TRACER.exists():
            self.skipTest("tracer not present")
        with mock.patch("sidm2.zig64_audio_gate._trace", return_value=[]):
            self.assertFalse(
                verify_sf2_audio(b"\x00\x10" + bytes(64), sid,
                                  0x0F90, 0x0F94, 0x1000, 0x1003,
                                  tracer_path=self.TRACER, frames=4),
                "Two empty traces must NOT be certified as a match"
            )

    def test_tracer_failure_returns_false(self):
        """_trace returning None (tracer failed) → False, not a pass.

        The vsid fallback is stubbed out here: this test covers the
        no-fallback-available path, which must stay fail-closed.
        """
        from unittest import mock
        sid = self.SID_DIR / "Stinsens_Last_Night_of_89.sid"
        if not sid.exists():
            self.skipTest(f"missing {sid}")
        if not self.TRACER.exists():
            self.skipTest("tracer not present")
        with mock.patch("sidm2.zig64_audio_gate._trace", return_value=None), \
             mock.patch("sidm2.zig64_audio_gate._verify_via_vsid",
                        return_value=(None, None)):
            self.assertFalse(
                verify_sf2_audio(b"\x00\x10" + bytes(64), sid,
                                  0x0F90, 0x0F94, 0x1000, 0x1003,
                                  tracer_path=self.TRACER, frames=4),
                "A tracer failure must NOT be certified as a match"
            )

    def test_no_vsid_fallback_stays_fail_closed(self):
        """With the VICE wrapper absent, an untraceable RSID must return
        False — never silently pass for lack of a fallback."""
        from unittest import mock
        sid = self.SID_DIR / "Laxity" / "Broken_Ass.sid"
        if not sid.exists():
            self.skipTest(f"missing {sid}")
        if not self.TRACER.exists():
            self.skipTest("tracer not present")
        d = sid.read_bytes()
        ia = struct.unpack(">H", d[10:12])[0]
        pa = struct.unpack(">H", d[12:14])[0]
        with mock.patch("sidm2.zig64_audio_gate._vsid_trace_js",
                        return_value=None):
            self.assertFalse(
                verify_sf2_audio(b"\x00\x10" + bytes(64), sid,
                                  0x0F90, 0x0F94, ia, pa,
                                  tracer_path=self.TRACER, frames=8),
                "No fallback available → must fail closed, not pass"
            )

    def test_untraceable_rsid_does_not_certify_garbage(self):
        """End-to-end: Broken_Ass is an RSID whose IRQ this tracer cannot
        drive. Feeding the gate pure garbage as the 'SF2' must fail.

        Before the fix this returned True — 64 zero bytes were certified
        byte-identical to the tune.
        """
        sid = self.SID_DIR / "Laxity" / "Broken_Ass.sid"
        if not sid.exists():
            self.skipTest(f"missing {sid}")
        if not self.TRACER.exists():
            self.skipTest("tracer not present")
        d = sid.read_bytes()
        ia = struct.unpack(">H", d[10:12])[0]
        pa = struct.unpack(">H", d[12:14])[0]
        self.assertFalse(
            verify_sf2_audio(b"\x00\x10" + bytes(64), sid,
                              0x0F90, 0x0F94, ia, pa,
                              tracer_path=self.TRACER, frames=16),
            "Untraceable SID must not certify arbitrary SF2 bytes"
        )


class TestVsidRsidFallback(unittest.TestCase):
    """The VICE fallback: zig64 cannot drive an RSID whose player installs
    its own IRQ (play=$0000), so both sides are re-traced under vsid.

    Skipped unless the wrapper (a separate project) + node + vsid.exe are
    present — absence is normal and simply leaves the gate fail-closed.
    """

    ROOT = Path(__file__).parent.parent
    SID_DIR = ROOT / "SID"
    TRACER = ROOT / "tools" / "sidm2-sid-trace.exe"

    @classmethod
    def setUpClass(cls):
        from sidm2.zig64_audio_gate import _vsid_trace_js
        if _vsid_trace_js() is None:
            raise unittest.SkipTest("vsid-trace.js wrapper not available")
        if not cls.TRACER.exists():
            raise unittest.SkipTest("tracer not present")

    def _psid_init_play(self, p: Path):
        d = p.read_bytes()
        return (struct.unpack(">H", d[10:12])[0],
                struct.unpack(">H", d[12:14])[0])

    def test_fallback_traces_an_rsid_zig64_cannot(self):
        """Broken_Ass (RSID, play=$0000) yields nothing from zig64 but a
        real trace from vsid."""
        from sidm2.zig64_audio_gate import _trace_vsid, _vsid_trace_js
        sid = self.SID_DIR / "Laxity" / "Broken_Ass.sid"
        if not sid.exists():
            self.skipTest(f"missing {sid}")
        rows = _trace_vsid(sid, 8, _vsid_trace_js())
        self.assertIsNotNone(rows, "vsid must drive this RSID")
        self.assertGreater(len(rows), 50,
                           "expected a substantial trace, not a trickle")
        # rows must be (frame, register_name, "$XX") like zig64's
        f, reg, val = rows[0]
        self.assertTrue(f.isdigit(), f"frame should be numeric, got {f!r}")
        self.assertRegex(reg, r"^(osc\d|filter|volume|pot|env|adc)",
                         f"unexpected register name {reg!r}")
        self.assertRegex(val, r"^\$[0-9A-F]{2}$", f"bad value {val!r}")

    def test_rsid_sf2_verifies_against_real_evidence(self):
        """End-to-end: a real SF2 built from an RSID now VERIFIES — and the
        pass is backed by a non-empty comparison, not an empty-vs-empty one
        (the bug this whole gate exists to prevent)."""
        import subprocess as sp
        import tempfile as tf
        from unittest import mock
        import sidm2.zig64_audio_gate as G

        sid = self.SID_DIR / "Laxity" / "Broken_Ass.sid"
        if not sid.exists():
            self.skipTest(f"missing {sid}")
        out = Path(tf.mktemp(suffix=".sf2"))
        sp.run([sys.executable, str(self.ROOT / "scripts" / "sid_to_sf2.py"),
                str(sid), str(out), "-q"],
               capture_output=True, text=True, cwd=str(self.ROOT))
        if not out.exists():
            self.skipTest("SF2 build failed for Broken_Ass")
        sf2 = out.read_bytes()
        out.unlink(missing_ok=True)
        ia, pa = self._psid_init_play(sid)

        seen = {}
        real = G._verify_via_vsid

        def spy(*a, **k):
            s, f = real(*a, **k)
            seen["sid"], seen["sf2"] = s, f
            return s, f

        with mock.patch.object(G, "_verify_via_vsid", side_effect=spy):
            ok = G.verify_sf2_audio(sf2, sid, 0x0F90, 0x0F94, ia, pa,
                                     tracer_path=self.TRACER, frames=16)
        self.assertTrue(seen, "the vsid fallback should have fired")
        self.assertTrue(seen["sid"], "fallback produced no reference evidence")
        self.assertGreater(len(seen["sid"]), 100,
                           "a True here must rest on real rows")
        self.assertTrue(ok, "a faithful SF2 from an RSID must verify")

    def test_rsid_garbage_rejected_through_fallback(self):
        """The fallback must not become a new way to pass garbage."""
        sid = self.SID_DIR / "Laxity" / "Broken_Ass.sid"
        if not sid.exists():
            self.skipTest(f"missing {sid}")
        ia, pa = self._psid_init_play(sid)
        self.assertFalse(
            verify_sf2_audio(b"\x00\x10" + bytes(64), sid,
                              0x0F90, 0x0F94, ia, pa,
                              tracer_path=self.TRACER, frames=8),
            "garbage must be rejected even when the fallback runs"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
