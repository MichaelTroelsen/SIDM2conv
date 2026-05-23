"""C2 (audio byte-identical) regression test against the 14 reference files.

Codifies the v3.5.35 state: every file the converter produces a SF2
for plays back BYTE-IDENTICAL to the original SID over 300 PAL frames,
measured via the cycle-accurate zig64 tracer.

This test is the canonical guard against future converter changes
that might regress one of the documented byte-identical reference
files (which would silently break audio fidelity in ways the unit
tests don't catch). Each reference file represents a distinct
architectural class:

- Stinsen / Unboxed       — canonical NP21 Stinsen-class
- Beast / Angular         — NP21 Beast/Angular variant layouts
- Dark_Fun                — ch_seq_ptr safety gate fires
                            (bytes at $1A1C are data, not pointers)
- Twone_Five              — minimal-embed post-binary zero guard
- Patterns                — gate's wave-copy NOP fallback
- Edie_Ball               — gate's ch_seq_ptr revert (Zetrex/YP)
- Joe_Gunn_Extras / SFd2  — init+3 patch safety check
- SFd1                    — gate's late-divergence detection
- Alliance / Racer        — formerly "deferred V20/Zetrex"; now
                             recovered via init+3 patch safety
- Exorcist_preview        — gate's Block 2 native-redirect fallback

If any of these regress, the converter's audio-correctness invariant
is broken and a new fix is needed.

Slow test (~30s wall clock for 14 files × convert + 2 zig64 traces).
Skipped automatically if the zig64 tracer binary isn't installed.
"""
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

ROOT = Path(__file__).parent.parent
TRACER = ROOT / "tools" / "sidm2-sid-trace.exe"
SID_TO_SF2 = ROOT / "scripts" / "sid_to_sf2.py"


def _parse_psid(p: Path):
    d = p.read_bytes()
    do = struct.unpack(">H", d[6:8])[0]
    la = struct.unpack(">H", d[8:10])[0]
    ia = struct.unpack(">H", d[10:12])[0]
    pa = struct.unpack(">H", d[12:14])[0]
    c = d[do:]
    if la == 0:
        la = struct.unpack("<H", c[:2])[0]
        c = c[2:]
    if pa == 0:
        pa = ia + 3
    return la, ia, pa, c


def _trace_csv(prg_path: Path, frames: int, init_addr: int, play_addr: int):
    """Run zig64 and return (frame, register, value) tuples (ignoring cycle)."""
    r = subprocess.run(
        [str(TRACER), str(prg_path), str(frames),
         f"{init_addr:04x}", f"{play_addr:04x}"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    rows = []
    for L in r.stderr.splitlines():
        if not L or L.startswith("frame") or L.startswith("---"):
            continue
        if "," not in L:
            continue
        p = L.split(",")
        if len(p) >= 5:
            rows.append((p[0], p[2], p[4]))
    return rows


def _read_block2_init_play(sf2_path: Path):
    """Read SF2 Block 2's declared init/play addresses. The v3.5.35 gate
    may rewrite these from $0F90/$0F94 → native PSID entry points."""
    sd = sf2_path.read_bytes()
    # Block chain: file off 4 (PRG load:2 + magic:2 = $1337), then
    # [id:1][size:1][body...] until id=0xFF.
    o = 4
    while o + 2 <= len(sd):
        bid = sd[o]
        if bid == 0xFF:
            break
        bsz = sd[o + 1]
        body = sd[o + 2:o + 2 + bsz]
        if bid == 2 and len(body) >= 6:
            init_addr = body[0] | (body[1] << 8)
            # Block 2 body layout: Init, Stop, Play. Play at body[4..5].
            play_addr = body[4] | (body[5] << 8)
            return init_addr, play_addr
        o += 2 + bsz
    return None, None


# (sid_relative_path, expected_write_count, description)
# Counts pinned at v3.5.35. If a count changes the converter changed
# the player's runtime behavior — investigate. ALL must be PASS.
REFERENCE_FILES = [
    ("Stinsens_Last_Night_of_89.sid", 1909, "canonical NP21 Stinsen-class"),
    ("Unboxed_Ending_8580.sid",       2733, "canonical NP21 Unboxed-class"),
    ("Beast.sid",                     2684, "Beast variant"),
    ("Angular.sid",                   2648, "Angular variant"),
    ("Laxity/Dark_Fun.sid",           1719, "ch_seq_ptr safety gate (py65)"),
    ("Laxity/Twone_Five.sid",         1326, "minimal-embed post-binary zero guard"),
    ("Laxity/Patterns.sid",           1793, "zig64 gate wave-copy NOP fallback"),
    ("Laxity/Edie_Ball.sid",           637, "zig64 gate ch_seq_ptr revert (Zetrex/YP)"),
    ("Laxity/Joe_Gunn_Extras.sid",    1756, "init+3 patch safety check"),
    ("Laxity/SID_Factory_demo_tune_1.sid", 1904, "ch_seq_ptr gate late-divergence"),
    ("Laxity/SID_Factory_demo_tune_2.sid", 1133, "init+3 patch safety check"),
    ("Laxity/Alliance.sid",           1283, "formerly 'deferred V20' (init+3 safety)"),
    ("Laxity/Racer.sid",               909, "formerly 'deferred Zetrex/YP' (init+3 safety)"),
    ("Laxity/Exorcist_preview.sid",   1612, "zig64 gate Block 2 native-redirect"),
]


@unittest.skipUnless(TRACER.exists(),
                      f"zig64 tracer not installed: {TRACER}")
class TestC2ReferenceRegression(unittest.TestCase):
    """Byte-identical audio regression test for the 14 v3.5.35 reference
    files. Each represents a distinct architectural class; together they
    cover every safety-gate strategy currently in the converter."""

    FRAMES = 300

    def _verify_one(self, sid_rel: str, expected_writes: int, desc: str):
        sid_path = ROOT / "SID" / sid_rel
        if not sid_path.exists():
            self.skipTest(f"reference SID missing: {sid_path}")
        # Build SF2
        with tempfile.TemporaryDirectory() as td:
            out_sf2 = Path(td) / (sid_path.stem + ".sf2")
            r = subprocess.run(
                [sys.executable, str(SID_TO_SF2),
                 str(sid_path), str(out_sf2), "-q"],
                capture_output=True, text=True, cwd=str(ROOT),
            )
            self.assertTrue(out_sf2.exists(),
                             f"conversion failed for {sid_rel}: {r.stderr[-400:]}")
            sid_la, sid_init, sid_play, c64 = _parse_psid(sid_path)
            # SID PRG
            sid_prg = Path(td) / "sid.prg"
            sid_prg.write_bytes(struct.pack("<H", sid_la) + c64)
            sid_rows = _trace_csv(sid_prg, self.FRAMES, sid_init, sid_play)
            # SF2 traced via Block 2 declared init/play (which v3.5.35
            # may have rewritten to native for Exorcist_preview-class).
            sf2_init, sf2_play = _read_block2_init_play(out_sf2)
            self.assertIsNotNone(sf2_init,
                                  f"Block 2 not found in {sid_rel}'s SF2")
            sf2_rows = _trace_csv(out_sf2, self.FRAMES, sf2_init, sf2_play)
            self.assertEqual(
                len(sid_rows), len(sf2_rows),
                f"{sid_rel} ({desc}): SID has {len(sid_rows)} writes but "
                f"SF2 has {len(sf2_rows)} — count mismatch"
            )
            self.assertEqual(
                len(sid_rows), expected_writes,
                f"{sid_rel} ({desc}): SID write count changed from "
                f"pinned {expected_writes} to {len(sid_rows)} — investigate "
                f"(this would indicate a zig64 / py65 change, not a "
                f"converter regression)"
            )
            self.assertEqual(
                sid_rows, sf2_rows,
                f"{sid_rel} ({desc}): SF2 audio diverges from SID "
                f"({sum(1 for a,b in zip(sid_rows, sf2_rows) if a!=b)} "
                f"diff tuples). Converter regression — check recent "
                f"changes to sf2_writer.py / ch_seq_safety_gate.py / "
                f"zig64_audio_gate.py."
            )


# Generate one test method per file so failures pinpoint the file.
def _make_test(sid_rel, n, desc):
    def test(self):
        self._verify_one(sid_rel, n, desc)
    test.__name__ = "test_" + sid_rel.replace("/", "_").replace(".sid", "")
    test.__doc__ = f"C2 byte-identical for {sid_rel} ({desc})"
    return test


for sid_rel, n, desc in REFERENCE_FILES:
    name = "test_" + sid_rel.replace("/", "_").replace(".sid", "")
    setattr(TestC2ReferenceRegression, name, _make_test(sid_rel, n, desc))


if __name__ == "__main__":
    unittest.main(verbosity=2)
