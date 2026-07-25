#!/usr/bin/env python3
"""Blackbird corpus fidelity sweep -- build all 16 v1.2-exact files and record
per-file register accuracy, part counts and byte sizes.

Promoted from untracked scratch (2026-07-25). Every Blackbird percentage quoted
in CLAUDE.md and docs/reference/ACCURACY_MATRIX.md comes from this harness, so
it living only in a scratchpad meant those figures were not reproducible from a
fresh clone -- the same "headline comes from untracked scratch" caveat Sound
Monitor still carries.

Usage:
    py -3 pyscript/blackbird_sweep.py <label> [ENV=VAL ...]
    py -3 pyscript/blackbird_sweep.py --compare <before.json> <after.json>

Writes out/blackbird/sweep_<label>.json.

PART COUNTS ARE PART OF THE RESULT, not decoration. A changed part count shifts
the measurement window, so a file whose part count moved is NOT comparable to
its own baseline -- percentages either side of such a move measure different
spans of the song (the "B10 trap"). compare() reports those separately from
regressions and EXPECTED_PARTS pins the known-good values.
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The v1.2-exact corpus: the files the native Blackbird driver is validated on.
CORPUS = [
    "Fargo", "Glyptodont", "Dishwasher_Groove", "Dithered_Island",
    "Elvendance", "Euclid_Was_Here", "Into_the_Unknown", "Maple_Leaf_Rag",
    "Revolutions_Delivered", "Thus_Spoke_the_PC_Speaker", "Toy_Rocket",
    "Crank_Crank_Airwolf", "Trinket", "To_Die_For_II",
    "Fugue_on_a_Theme_by_D_M_Hanlon", "Quintessence",
]

# Known-good part counts. Anything else means the adaptive splitter chose a
# different windowing and the file's percentages are not comparable to history.
EXPECTED_PARTS = {name: 1 for name in CORPUS}
EXPECTED_PARTS.update({"Fargo": 2, "Dithered_Island": 2, "Into_the_Unknown": 3})

REGISTERS = ("freq", "waveform", "pulse", "adsr", "filter")

_AVG = re.compile(
    r"WEIGHTED AVERAGE.*?overall=([\d.]+)%\s+freq=([\d.]+)%,\s+waveform=([\d.]+)%,"
    r"\s+pulse=([\d.]+)%,\s+adsr=([\d.]+)%,\s+filter=([\d.]+)%")
_PARTS = re.compile(r"packed into (\d+) adaptive part")


def parse_build_output(text):
    """Extract the fidelity record from one build's stdout+stderr.

    Returns None when the build produced no WEIGHTED AVERAGE line -- a failed
    or refused build must NOT silently read as 0% or as a missing key that a
    caller might treat as unchanged.
    """
    m = _AVG.search(text)
    if not m:
        return None
    rec = dict(zip(("overall",) + REGISTERS, [float(g) for g in m.groups()]))
    p = _PARTS.search(text)
    rec["parts"] = int(p.group(1)) if p else None
    return rec


def build_one(name, env=None):
    """Build one corpus file; returns its fidelity record (or an error dict)."""
    sid = os.path.join(ROOT, "SID", "LFT", f"{name}.sid")
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "bin", "build_blackbird_native_song.py"), sid],
        capture_output=True, text=True, cwd=ROOT, env=env or dict(os.environ))
    rec = parse_build_output(r.stdout + r.stderr)
    if rec is None:
        return {"error": "no WEIGHTED AVERAGE line", "rc": r.returncode}
    sf2 = os.path.join(ROOT, "out", "blackbird", f"{name}_native_part01.sf2")
    rec["bytes"] = os.path.getsize(sf2) if os.path.exists(sf2) else None
    return rec


def sweep(label, env=None, corpus=None, verbose=True):
    out = {}
    for name in (corpus or CORPUS):
        rec = build_one(name, env)
        out[name] = rec
        if verbose:
            if "error" in rec:
                print(f"{name:32s} BUILD FAILED ({rec['error']})", flush=True)
            else:
                warn = ""
                if rec["parts"] != EXPECTED_PARTS.get(name):
                    warn = f"  *** PARTS {rec['parts']} != expected " \
                           f"{EXPECTED_PARTS.get(name)} ***"
                print(f"{name:32s} overall={rec['overall']:5.1f} "
                      f"parts={rec['parts']} bytes={rec['bytes']}{warn}", flush=True)
    if label:
        dest = os.path.join(ROOT, "out", "blackbird", f"sweep_{label}.json")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w") as f:
            json.dump(out, f, indent=2)
        if verbose:
            print(f"\nwrote {dest}")
    return out


def mean_overall(records):
    ok = [v["overall"] for v in records.values() if "overall" in v]
    return sum(ok) / len(ok) if ok else 0.0


def compare(before, after, tol=0.05):
    """Diff two sweeps.

    Part-count moves are reported SEPARATELY from regressions because they are
    not the same kind of finding: a regression is a worse number over the same
    window, a part move means the windows differ and the numbers cannot be
    compared at all.
    """
    rep = {"regressed": [], "improved": [], "part_moves": [], "byte_changes": [],
           "errors": [], "rows": []}
    for name in before:
        x, y = before[name], after.get(name, {})
        if "overall" not in x or "overall" not in y:
            rep["errors"].append(name)
            continue
        d = y["overall"] - x["overall"]
        rep["rows"].append((name, x["overall"], y["overall"], d, y.get("parts")))
        if d < -tol:
            rep["regressed"].append(name)
        elif d > tol:
            rep["improved"].append(name)
        if x.get("parts") != y.get("parts"):
            rep["part_moves"].append(name)
        if x.get("bytes") != y.get("bytes"):
            rep["byte_changes"].append(name)
    rep["mean_before"] = mean_overall(before)
    rep["mean_after"] = mean_overall(after)
    return rep


def print_comparison(rep):
    print(f"{'file':34s} {'before':>7s} {'after':>7s} {'delta':>7s}  parts")
    for name, a, b, d, parts in rep["rows"]:
        flag = ("  <== REGRESSION" if name in rep["regressed"] else
                "  <== IMPROVED" if name in rep["improved"] else "")
        pm = "  *** PART MOVE ***" if name in rep["part_moves"] else ""
        print(f"{name:34s} {a:7.1f} {b:7.1f} {d:+7.1f}  {parts}{pm}{flag}")
    print(f"\nmean {rep['mean_before']:.3f} -> {rep['mean_after']:.3f} "
          f"({rep['mean_after'] - rep['mean_before']:+.3f})")
    print(f"improved={len(rep['improved'])} regressed={len(rep['regressed'])} "
          f"{rep['regressed']}  part-moves={rep['part_moves']}  "
          f"byte-changes={len(rep['byte_changes'])}")
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
    print(f"mean overall = {mean_overall(out):.3f} over "
          f"{sum(1 for v in out.values() if 'overall' in v)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
