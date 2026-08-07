#!/usr/bin/env python3
"""Build every MoN native target BOTH WAYS and compare parts + fidelity.

R17's structural prongs (`MON_ARP_STRUCT` / `MON_PULSE_CANON` / `MON_WAVE_CANON`)
re-compress the per-note unrolled synth tables back into the player's own looping
programs, which is the only proven LOSSLESS way to cut part count. They are
opt-in, and `docs/players/MON.md`'s published fidelity table is already measured
with them ON -- so the open question is not whether they work but whether they
are safe to make the DEFAULT.

This answers that question the way R17 demands: part count is the prize, but
fidelity is the gate. A part-count win with any fidelity loss is a failure.
(Which is also why part count is carried as a row field and not as a scored
dimension: putting the prize inside the gate would let a compression win vote
on whether the compression was safe.)

Each tune is built twice and part01 is scored against the ORIGINAL on the window
both builds share (their part01 windows differ, so scoring each on its own window
would compare different music). Myth is excluded: it is not buildable through
`build_mon_native_song` at all -- its pseudo-parse gate refuses it (speed byte
255) -- and needs `bin/build_myth_native_song.py`, which this driver does not
speak. Measure Myth separately.

The A/B apparatus itself -- what counts as a regression, which settings make two
runs incomparable, whether the build output moved at all, and which SID registers
this comparison is blind to -- lives in `sidm2.fidelity_common`, not here. This
script only knows how to build a MoN part and read a fidelity table.

    py -3 pyscript/mon_struct_sweep.py            # whole corpus
    py -3 pyscript/mon_struct_sweep.py Hawkeye:2  # one target
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sidm2 import fidelity_common as FC          # noqa: E402

BUILDER = os.path.join(ROOT, "bin", "build_mon_native_song.py")
FIDELITY = os.path.join(ROOT, "bin", "mon_part_fidelity.py")
STRUCT_ENV = {"MON_ARP_STRUCT": "1", "MON_PULSE_CANON": "1",
              "MON_WAVE_CANON": "1"}
PLAIN_ENV = {k: None for k in STRUCT_ENV}      # the same options, unset

# (tune, subtune) -- the natively-built MoN corpus per docs/players/MON.md.
TARGETS = [("Hawkeye", 0), ("Hawkeye", 2), ("Hawkeye", 3),
           ("Cybernoid", 0), ("Cybernoid_II", 0),
           ("Supremacy", 0), ("Supremacy", 1), ("Supremacy", 2)]

PART_RE = re.compile(r"part (\d+)/(\d+) \((\d+)-(\d+)s")
OSC_RE = re.compile(r"^\s*osc(\d)\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+"
                    r"\(\s*([\d.]+)/\s*([\d.]+)/\s*([\d.]+)\)", re.M)

# The three columns OSC_RE captures are mon_part_fidelity's skew-tolerant
# (f/w/p) triple. Naming them as registry dimensions is what lets the run print
# its own blind spots instead of relying on someone remembering them: these read
# $D400/$D401, $D404 and $D402/$D403, so $D405/$D406 -- the envelope pair that
# MON_WAVE_CANON re-compresses -- is NOT read here at all, and "no regression"
# from this sweep has never meant "the envelope survived". `format_run_delta`
# now says that in the output of every run.
SCORE_KEYS = ("freq", "wf", "pul")


def build(tune, sub, structural):
    env = dict(os.environ)
    if structural:
        env.update(STRUCT_ENV)
    else:                      # make sure an inherited flag cannot leak in
        for k in STRUCT_ENV:
            env.pop(k, None)
    sid = os.path.join(ROOT, "SID", "Tel_Jeroen", f"{tune}.sid")
    p = subprocess.run([sys.executable, BUILDER, sid, str(sub), "auto"],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=3600, env=env)
    text = (p.stdout or "") + (p.stderr or "")
    parts = PART_RE.findall(text)
    if not parts:
        return None, None, text
    n_parts = int(parts[0][1])
    first_end = int(parts[0][3])          # part01's window end, seconds
    return n_parts, first_end, text


def score(part_path, sub, secs):
    """part01 vs the original over `secs` -- the best-delay (aligned) columns.

    -> {"osc1/freq": 99.8, "osc1/wf": ..., ...}. A voice mon_part_fidelity
    printed as `n/a` simply has no key, which `fidelity_common.regressions`
    reads as a lost measurement rather than as unchanged.
    """
    p = subprocess.run([sys.executable, FIDELITY, part_path, str(sub), str(secs)],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800)
    out = (p.stdout or "") + (p.stderr or "")
    return {f"osc{m.group(1)}/{k}": float(m.group(2 + i))
            for m in OSC_RE.finditer(out)
            for i, k in enumerate(SCORE_KEYS)}


def _voices(keys):
    """score keys -> the sorted osc numbers they mention, for the report line."""
    return sorted({int(FC.split_key(k)[0][3:]) for k in keys})


def _triple(row, v):
    return tuple(row["scores"].get(f"osc{v}/{k}") for k in SCORE_KEYS)


def sweep_one(tune, sub, label):
    """-> (baseline_row, structural_row), or None if either build failed."""
    part01 = os.path.join(ROOT, "out", "mon", f"{tune}_sub{sub}_part01.sf2")
    # `mon_part_fidelity` infers the original SID from the filename by splitting
    # on "_sub", so the stash MUST keep "<Tune>_sub" as its prefix -- a name like
    # "_sweep_Hawkeye_sub2.sf2" resolves to tune "_sweep_Hawkeye", the trace
    # comes back empty, and every voice reads as a regression.
    stash = os.path.join(ROOT, "out", "mon", f"{tune}_sub{sub}SWEEP_part01.sf2")
    on_parts, on_end, _ = build(tune, sub, True)
    if on_parts is None:
        return _failed(tune, sub, "structural")
    shutil.copyfile(part01, stash)
    off_parts, off_end, _ = build(tune, sub, False)
    if off_parts is None:
        return _failed(tune, sub, "baseline")
    # Score both on the window they SHARE; part01 spans differ between builds.
    # window/subtune are `measurement` (compare_runs refuses a delta across
    # them); the MON_* flags are `options` -- the change under test.
    secs = min(on_end, off_end)
    off_row, on_row = FC.ab_pair(
        f"{tune} sub{sub}",
        dict(scores=score(part01, sub, secs), options=PLAIN_ENV,
             paths=part01, parts=off_parts),
        dict(scores=score(stash, sub, secs), options=STRUCT_ENV,
             paths=stash, parts=on_parts),
        measurement={"window_secs": secs, "subtune": sub}, label=label)
    os.remove(stash)

    regressed = _voices(k for k, _, _ in FC.regressions(off_row, on_row))
    verdict = "REGRESSED" if regressed else ("WIN" if on_parts < off_parts
                                             else "same")
    print(f"{tune} sub{sub}: parts {off_parts} -> {on_parts}  [{secs}s window]  "
          f"{verdict}" + (f"  osc{regressed} worse" if regressed else ""),
          flush=True)
    for v in _voices(set(off_row["scores"]) | set(on_row["scores"])):
        print(f"    osc{v}  off {_triple(off_row, v)}   "
              f"on {_triple(on_row, v)}", flush=True)
    return off_row, on_row


def _failed(tune, sub, which):
    print(f"{tune} sub{sub}: BUILD FAILED ({which}) -- skipped", flush=True)
    return None


def main(argv):
    targets = ([(t, int(s or 0)) for t, _, s in (a.partition(":") for a in argv)]
               if argv else TARGETS)
    label = FC.git_label() or "unlabelled"
    pairs = [r for r in (sweep_one(t, s, label) for t, s in targets) if r]
    delta = FC.compare_runs([a for a, _ in pairs], [b for _, b in pairs])
    off = sum(a["parts"] for a, _ in pairs)
    on = sum(b["parts"] for _, b in pairs)
    bad = [(t, _voices(k for k, _, _ in reg)) for t, reg in delta.regressed]
    print(f"\n{len(pairs)} target(s): {off} parts -> {on} parts "
          f"({off - on} fewer), {len(bad)} regressed")
    for t, voices in bad:
        print(f"  !! {t} osc{voices}")
    print("\n" + FC.format_run_delta(delta))
    return delta.exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
