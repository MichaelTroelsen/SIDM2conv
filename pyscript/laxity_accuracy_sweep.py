#!/usr/bin/env python3
"""Measure native-Laxity frame accuracy over the whole locatable corpus.

WHY THIS FILE IS TRACKED, stated first because it is the entire point. CLAUDE.md
rates native Laxity NP21 -> Laxity driver at 99.93-100% and admits in the same
row that 99.93 is a TARGET, not a measurement: the only measurement on record is
99.98% over **n=2** (`Stinsens_Last_Night_of_89`, `Broware`, 2025-12-28,
CHANGELOG.md:10450) and **its script is no longer in the tree**. A headline
number whose method cannot be re-run is not quotable, so the method lives here
now and the number is whatever this prints.

WHAT IT MEASURES, and the round trip is deliberate. Per file:

    SID  --scripts/sid_to_sf2.py --driver laxity-->  SF2
    SF2  --scripts/sf2_to_sid.py -->  SID'
    SID vs SID'  --scripts/validate_sid_accuracy.py-->  frame accuracy

That is the same shape as the retired n=2 measurement, so the new number is
comparable to the old claim rather than a different quantity wearing its name.
`frame_accuracy` is the mean per-frame register agreement (the tool's own
v2.9.1 fix -- exact-frame-match percentage is reported separately and is much
harsher; both are recorded here).

WHAT IT REFUSES TO DO, because this repo has shipped each of these once:

* It never prints a percentage without its `n`. `fidelity_common.fmt_pct`
  suffixes an underpowered sample with `!`, and a corpus mean over files with
  wildly different lengths is reported as a DISTRIBUTION (min / median / max
  plus every per-file row), never as a lone mean. A 1-second stinger and a
  2-minute song do not average.
* It never reports a file that failed to convert as 0%. A conversion or
  round-trip failure is recorded as `error`, kept out of the statistics, and
  counted separately -- unmeasured is not measured-zero.
* It scores nothing it did not actually compare: a file whose validation
  produced no frames is `no-frames`, not 100%.

Usage:
    python pyscript/laxity_accuracy_sweep.py                 # whole corpus
    python pyscript/laxity_accuracy_sweep.py --only Angular  # one file
    python pyscript/laxity_accuracy_sweep.py --duration 60   # longer window
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.append(str(_ROOT))

from sidm2.fidelity_common import fmt_pct, underpowered   # noqa: E402

# RESULTS go under out/; INTERMEDIATES do not, and the difference is enforced by
# a test rather than by taste. out/ is the corpus tree: pyscript/test_player_index.py
# asserts that every out/ directory holding .sf2 files is classified in
# player_index.py, so dropping this sweep's round-trip .sf2 files there broke
# test_every_built_directory_is_classified -- a scratch directory masquerading as
# a built corpus. The .sf2/.sid/.html a round trip produces are disposable working
# files, so they go to the system temp dir; only sweep.json, which is the evidence,
# belongs under out/.
RESULTS = _ROOT / "out" / "laxity_sweep"
WORK = Path(tempfile.gettempdir()) / "sidm2_laxity_sweep"


def laxity_corpus() -> list[Path]:
    """Every SID/*.sid the driver selector routes to the Laxity driver.

    Deliberately the selector's own answer rather than a hand-listed corpus --
    a hand list is how the last measurement's population became unrecoverable.
    """
    from sidm2.driver_selector import DriverSelector
    sel = DriverSelector()
    out = []
    for f in sorted((_ROOT / "SID").glob("*.sid")):
        try:
            if sel.select_driver(f).driver_name == "laxity":
                out.append(f)
        except Exception:                                    # noqa: BLE001
            continue
    return out


def _run(cmd: list[str], timeout: int) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           cwd=str(_ROOT))
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return -9, "TIMEOUT"


def measure_one(sid: Path, duration: int, timeout: int) -> dict:
    """Round-trip one file and return its row. Never raises, never invents a score."""
    WORK.mkdir(parents=True, exist_ok=True)
    stem = sid.stem
    sf2 = WORK / f"{stem}.sf2"
    back = WORK / f"{stem}_rt.sid"
    js = WORK / f"{stem}.json"
    row = {"file": stem, "status": None, "frame_accuracy": None,
           "exact_match_pct": None, "frames": None, "note": None}

    rc, out = _run([sys.executable, "scripts/sid_to_sf2.py", str(sid), str(sf2),
                    "--driver", "laxity", "-q"], timeout)
    if rc != 0 or not sf2.exists():
        row["status"] = "error"
        row["note"] = "sid_to_sf2 rc=%d" % rc
        return row

    rc, out = _run([sys.executable, "scripts/sf2_to_sid.py", str(sf2), str(back), "-q"],
                   timeout)
    if rc != 0 or not back.exists():
        row["status"] = "error"
        row["note"] = "sf2_to_sid rc=%d" % rc
        return row

    # --output is NOT optional: without it the validator writes
    # validation_<stem>_<timestamp>.html into the CURRENT DIRECTORY, i.e. the
    # repo root. It is gitignored (.gitignore:200) so git status never shows it,
    # which is exactly why it is easy to miss -- and it violates CLAUDE.md's
    # "keep root clean" rule and any touches list that does not name the root.
    # A tool's scratch output is a write you did not author; redirect it.
    #
    # --comparison-json, not --json: --json writes the two RAW CAPTURES
    # (<stem>_original.json / <stem>_exported.json, ~1.3 MB each) and no
    # comparison at all. The first version of this script asked for the wrong
    # file and reported every row as an error.
    rc, out = _run([sys.executable, "scripts/validate_sid_accuracy.py", str(sid),
                    str(back), "--duration", str(duration),
                    "--comparison-json", str(js),
                    "--output", str(WORK / f"{stem}_report.html")], timeout)
    if not js.exists():
        row["status"] = "error"
        row["note"] = "validate rc=%d (no comparison json)" % rc
        return row
    try:
        data = json.loads(js.read_text(encoding="utf-8"))
    except Exception as e:                                   # noqa: BLE001
        row["status"] = "error"
        row["note"] = "unreadable json: %s" % type(e).__name__
        return row

    summary = data.get("summary", {})
    fa = summary.get("frame_accuracy")
    # THE FRAME COUNT IS ONLY IN STDOUT. The comparison JSON carries no n, and a
    # percentage without its n is the thing fidelity_common exists to prevent --
    # so parse the count the validator printed rather than deriving it from
    # duration*50, which would be the WINDOW rather than what was compared.
    frames = None
    exact = None
    for line in out.splitlines():
        t = line.strip()
        if t.startswith("Captured ") and frames is None:
            try:
                frames = int(t.split()[1])
            except (IndexError, ValueError):
                pass
        if "Exact Frame Matches:" in t:
            try:
                exact = float(t.split("(")[1].split("%")[0])
            except (IndexError, ValueError):
                pass
    if fa is None or not frames:
        # A validation that compared nothing is UNMEASURED. Scoring it 100
        # (registers agree vacuously) or 0 (no evidence of disagreement) would
        # both be inventions.
        row["status"] = "no-frames"
        row["note"] = "validator returned no comparable frames"
        return row
    row.update(status="ok", frame_accuracy=float(fa), exact_match_pct=exact,
               frames=int(frames))
    return row


def summarise(rows: list[dict]) -> dict:
    ok = [r for r in rows if r["status"] == "ok"]
    accs = sorted(r["frame_accuracy"] for r in ok)
    return {
        "measured": len(ok),
        "errors": len([r for r in rows if r["status"] == "error"]),
        "no_frames": len([r for r in rows if r["status"] == "no-frames"]),
        "min": accs[0] if accs else None,
        "median": accs[len(accs) // 2] if accs else None,
        "max": accs[-1] if accs else None,
        "n_frames_min": min((r["frames"] for r in ok), default=None),
        "n_frames_max": max((r["frames"] for r in ok), default=None),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", help="substring filter on the file stem")
    ap.add_argument("--duration", type=int, default=30,
                    help="validation window in seconds (default 30)")
    ap.add_argument("--timeout", type=int, default=600, help="per-step timeout, seconds")
    ap.add_argument("--json", help="write the full per-file table here")
    a = ap.parse_args()

    corpus = laxity_corpus()
    if a.only:
        corpus = [c for c in corpus if a.only.lower() in c.stem.lower()]
    if not corpus:
        print("no Laxity files selected")
        return 1

    print("Laxity corpus: %d files (driver selector), window %ds\n"
          % (len(corpus), a.duration))
    rows = []
    for i, sid in enumerate(corpus, 1):
        r = measure_one(sid, a.duration, a.timeout)
        rows.append(r)
        if r["status"] == "ok":
            print("%2d/%d %-34s frame %s  exact %5.1f%%  n=%d"
                  % (i, len(corpus), r["file"],
                     fmt_pct(r["frame_accuracy"], n=r["frames"]),
                     r["exact_match_pct"] or 0.0, r["frames"]))
        else:
            print("%2d/%d %-34s %-10s %s"
                  % (i, len(corpus), r["file"], r["status"].upper(), r["note"]))

    s = summarise(rows)
    # THE WINDOW TRAVELS WITH EVERY FIGURE, which is why it is repeated here
    # when the header already said it once. A number gets QUOTED from the
    # distribution block, not from a header twenty lines above it -- so a window
    # named only once is a window that falls off the moment anyone copies a
    # line. fidelity_common.fmt_pct already suffixes an underpowered n for the
    # same reason: a figure has to carry the condition that makes it true, in
    # the same breath, or the condition is lost and the figure survives.
    s["window_seconds"] = a.duration
    print("\n--- DISTRIBUTION, not a mean --- (%ds window)" % a.duration)
    print("measured %d | errors %d | no-frames %d" % (s["measured"], s["errors"], s["no_frames"]))
    if s["measured"]:
        print("frame accuracy over a %ds window  min %.2f%%  median %.2f%%  max %.2f%%"
              % (a.duration, s["min"], s["median"], s["max"]))
        print("frames compared per file: %d .. %d%s"
              % (s["n_frames_min"], s["n_frames_max"],
                 "   (! = underpowered sample)" if underpowered(s["n_frames_min"]) else ""))
        print("QUOTE THE WINDOW WITH THE NUMBER: these figures describe the first %ds"
              % a.duration)
        print("of each song, not the whole song. A defect that starts later scores clean here.")
    if a.json:
        Path(a.json).write_text(
            json.dumps({"window_seconds": a.duration, "rows": rows, "summary": s},
                       indent=1),
            encoding="utf-8")
        print("wrote %s (window_seconds recorded in it)" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
