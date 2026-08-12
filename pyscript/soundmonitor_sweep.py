#!/usr/bin/env python3
"""Sound Monitor corpus fidelity sweep -- build all 11 Fun Fun songs and score
every part's freq/waveform/pulse (+ filter) against the original SID.

Promoted from untracked scratch (R21, 2026-07-30): `bin/_opt_sweep_corpus.py`
computed the fidelity math but READ a log file that only existed if
`bin/_sm_build_all.py` had separately been run first -- both scripts were
untracked and gitignored, so the 99.23% freq+wf headline quoted throughout
docs/players/SOUNDMONITOR.md, docs/reference/ACCURACY_MATRIX.md and CLAUDE.md
was, in the matrix's own words, "not reproducible from a fresh clone".

This version is self-contained the way pyscript/blackbird_sweep.py is:
`build_one()` invokes the native builder itself and parses the part windows
straight out of THAT SAME subprocess call's stdout, so one command reproduces
the corpus sweep from nothing but a fresh checkout (SID/Fun_Fun/ is tracked).
The fidelity math (best-delay search, per-voice audible-start skip, the
grand-tally exclusion of voices with no gated frames in a window) is ported
UNCHANGED from bin/_opt_sweep_corpus.py -- it is already tuned and its results
are quoted throughout the docs; do not re-derive it.

Usage:
    py -3 pyscript/soundmonitor_sweep.py <label> [ENV=VAL ...]
    py -3 pyscript/soundmonitor_sweep.py --compare <before.json> <after.json>

Writes out/soundmonitor/sweep_<label>.json.
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))

from sidm2.fidelity_common import siddump_per_frame as per_frame
from sidm2.fidelity_common import launch_failure
from sidm2.fidelity_common import freq_to_semi as _semi
from sidm2.fidelity_common import psid_wrap as _psid
from sidm2.sf2_parser import parse_sf2_blocks, SF2DriverInfo

# The 11-file Fun Fun corpus (bin/_sm_build_all.py's NAMES list).
CORPUS = ["Final_Luv", "Dance_at_Night_remix", "Dreamix", "Fun_Mix", "Times_Up",
          "Poppy_Road", "No_Title", "Just_Cant_Get_Enough", "Thats_All",
          "Dreamix_Two", "Fuck_Off"]

# Tie-chain-heavy files: the step grid regressed them (Final_Luv pulse 100->8);
# keep them frame-mode per the v3.17.0 corpus decision (bin/_sm_build_all.py).
NO_GRID = {"Final_Luv", "Thats_All"}

_PART = re.compile(r"part (\d+)/\d+ \((\d+)-(\d+)s(?:, (\d+)-(\d+)f)?\)")


def parse_parts(build_text):
    """[(part, frame_lo, frame_hi), ...] from one build's stdout+stderr.

    Prefers exact frame bounds (the ", Af-Bf" group) over the second-rounded
    ones -- same preference bin/_opt_sweep_corpus.py's log parser used.
    Reading this straight from the build's own live output (rather than a
    separately captured log file) is also what fixes the historical
    "Dance_at_Night_remix part01 missing" gap: there is no second capture
    step across which a line could go missing.
    """
    out = []
    for line in build_text.splitlines():
        m = _PART.search(line)
        if not m:
            continue
        part = int(m.group(1))
        if m.group(4) is not None:
            out.append((part, int(m.group(4)), int(m.group(5))))
        else:
            out.append((part, int(m.group(2)) * 50, int(m.group(3)) * 50))
    return out


def score_part(name, part, t0, t1f, orig):
    """Fidelity for one already-built part vs `orig` (per_frame() of the
    ORIGINAL SID, from frame 0). Ported unchanged from
    bin/_opt_sweep_corpus.py: a single GLOBAL best-delay per part (a per-voice
    delay would mask inter-voice desync -- the bug class fixed in a210d83),
    scored from each voice's own first audible frame within the window."""
    pf = os.path.join(ROOT, "out", "soundmonitor", f"{name}_part{part:02d}.sf2")
    if not os.path.exists(pf):
        return {"error": f"part{part:02d} missing"}
    sf2 = bytearray(open(pf, "rb").read())
    info = SF2DriverInfo()
    sla = parse_sf2_blocks(sf2, info)
    probe = os.path.join(ROOT, "out", f"_sw_{name}_{part}.sid")
    open(probe, "wb").write(_psid(bytes(sf2[2:]), sla, 0x1000, 0x1003))
    secs = (t1f - t0) // 50 + 2
    prb = per_frame(probe, [f"-t{secs}"])
    n = min(len(prb), t1f - t0, len(orig) - t0) - 4
    if n <= 10:
        return {"error": f"window too short ({n})"}
    starts = [next((i for i in range(n)
                    if 0 <= t0 + i < len(orig)
                    and orig[t0 + i][0][v]['wf'] & 1), n)
              for v in range(3)]
    best = None
    for dly in (-2, -1, 0, 1, 2):
        cols, tots = [], 0
        for v in range(3):
            okf = okw = okp = tot = 0
            for i in range(starts[v], n):
                if not (0 <= t0 + i + dly < len(orig)):
                    continue
                a = orig[t0 + i + dly][0][v]
                b = prb[i][0][v]
                tot += 1
                okf += (_semi(a['freq']) == _semi(b['freq']))
                okw += (a['wf'] == b['wf'])
                okp += (a['pul'] == b['pul'])
            # tot may legitimately be 0 (a voice with no gated frames in this
            # window) -- excluded from the tally below, never scored 0/2.
            cols.append((okf, okw, okp, tot))
            tots += okf + okw
        fok = ftot = 0
        for i in range(min(starts), n):
            if not (0 <= t0 + i + dly < len(orig)):
                continue
            o, p = orig[t0 + i + dly][1], prb[i][1]
            if o is None and p is None:
                continue
            ftot += 1
            fok += (o == p)
        if best is None or tots > best[0]:
            best = (tots, dly, cols, fok, ftot)
    _, dly, cols, fok, ftot = best
    return {
        "delay": dly,
        "voices": [{"freq_ok": c[0], "wf_ok": c[1], "pulse_ok": c[2], "tot": c[3]}
                   for c in cols],
        "filter_ok": fok, "filter_tot": ftot,
        "t0f": t0, "t1f": t1f,
    }


def build_one(name, env=None):
    """Build one song (all its parts) and score every part against the
    original. Returns {"parts": {"1": record, ...}} or {"error": ...}."""
    sid = os.path.join(ROOT, "SID", "Fun_Fun", f"{name}.sid")
    e = dict(env if env is not None else os.environ)
    if name in NO_GRID:
        e["SM_GRID"] = "0"
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "bin", "build_soundmonitor_native_song.py"),
         sid, "auto"],
        capture_output=True, text=True, cwd=ROOT, env=e, timeout=600)
    text = r.stdout + r.stderr
    parts = parse_parts(text)
    if not parts:
        # A silent child that never started is not this song failing to build.
        infra = launch_failure(r.returncode, text)
        if infra:
            return {"unmeasured": infra, "rc": r.returncode}
        return {"error": "no part line in build output", "rc": r.returncode}
    maxs = max(p[2] for p in parts) // 50 + 2
    orig = per_frame(sid, ["-a0", f"-t{maxs}"])
    scored = {}
    for part, t0, t1f in parts:
        scored[str(part)] = score_part(name, part, t0, t1f, orig)
    return {"parts": scored}


def song_freq_wf(record):
    """(ok, tot) freq+wf strict tally for one song's build_one() record,
    summed across every part and voice that has data. Voices/parts with no
    measurable frames are excluded, never counted as 0-of-something."""
    ok = tot = 0
    for rec in record.get("parts", {}).values():
        for v in rec.get("voices", ()):
            if v["tot"]:
                ok += v["freq_ok"] + v["wf_ok"]
                tot += 2 * v["tot"]
    return ok, tot


def corpus_freq_wf_strict(out):
    """The corpus headline: freq+wf strict %, frame-weighted over every
    scored voice-part in the sweep. Matches
    bin/_opt_sweep_corpus.py's final "corpus freq+wf strict" line."""
    grand_ok = grand_tot = 0
    for rec in out.values():
        ok, tot = song_freq_wf(rec)
        grand_ok += ok
        grand_tot += tot
    return 100 * grand_ok / max(1, grand_tot)


def sweep(label, env=None, corpus=None, verbose=True):
    out = {}
    for name in (corpus or CORPUS):
        rec = build_one(name, env)
        out[name] = rec
        if verbose:
            if "error" in rec:
                print(f"{name:24s} BUILD FAILED ({rec['error']})", flush=True)
            else:
                ok, tot = song_freq_wf(rec)
                pct = 100 * ok / tot if tot else float("nan")
                nparts = len(rec["parts"])
                print(f"{name:24s} freq+wf={pct:5.1f} parts={nparts}", flush=True)
    if label:
        dest = os.path.join(ROOT, "out", "soundmonitor", f"sweep_{label}.json")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w") as f:
            json.dump(out, f, indent=2)
        if verbose:
            print(f"\nwrote {dest}")
    return out


def compare(before, after, tol=0.05):
    """Diff two sweeps, one row per song. Part-count moves are reported
    separately from regressions -- exactly as blackbird_sweep.py's compare()
    does -- because a part-count change means the window a song's percentage
    was measured over is not the same window any more."""
    rep = {"regressed": [], "improved": [], "part_moves": [], "errors": [],
           "rows": []}
    for name in before:
        x, y = before[name], after.get(name, {})
        if "parts" not in x or "parts" not in y:
            rep["errors"].append(name)
            continue
        xok, xtot = song_freq_wf(x)
        yok, ytot = song_freq_wf(y)
        xp = 100 * xok / xtot if xtot else float("nan")
        yp = 100 * yok / ytot if ytot else float("nan")
        d = yp - xp
        xparts, yparts = len(x["parts"]), len(y["parts"])
        rep["rows"].append((name, xp, yp, d, xparts, yparts))
        if d < -tol:
            rep["regressed"].append(name)
        elif d > tol:
            rep["improved"].append(name)
        if xparts != yparts:
            rep["part_moves"].append(name)
    rep["corpus_before"] = corpus_freq_wf_strict(before)
    rep["corpus_after"] = corpus_freq_wf_strict(after)
    return rep


def print_comparison(rep):
    print(f"{'song':24s} {'before':>7s} {'after':>7s} {'delta':>7s}  parts")
    for name, a, b, d, xp, yp in rep["rows"]:
        flag = ("  <== REGRESSION" if name in rep["regressed"] else
                "  <== IMPROVED" if name in rep["improved"] else "")
        pm = "  *** PART MOVE ***" if name in rep["part_moves"] else ""
        parts = f"{xp}->{yp}" if xp != yp else str(xp)
        print(f"{name:24s} {a:7.1f} {b:7.1f} {d:+7.1f}  {parts}{pm}{flag}")
    print(f"\ncorpus freq+wf strict: {rep['corpus_before']:.3f} -> "
          f"{rep['corpus_after']:.3f} ({rep['corpus_after'] - rep['corpus_before']:+.3f})")
    print(f"improved={len(rep['improved'])} regressed={len(rep['regressed'])} "
          f"{rep['regressed']}  part-moves={rep['part_moves']}")
    if rep["errors"]:
        print(f"ERRORS: {rep['errors']}")


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "--compare":
        before = json.load(open(argv[1]))
        after = json.load(open(argv[2]))
        rep = compare(before, after)
        print_comparison(rep)
        return 1 if (rep["regressed"] or rep["part_moves"]) else 0
    label = argv[0]
    env = dict(os.environ)
    for kv in argv[1:]:
        k, v = kv.split("=", 1)
        env[k] = v
    out = sweep(label, env)
    print(f"\ncorpus freq+wf strict: {corpus_freq_wf_strict(out):.3f}% over "
          f"{sum(len(v.get('parts', {})) for v in out.values())} parts / "
          f"{sum(1 for v in out.values() if 'parts' in v)} songs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
