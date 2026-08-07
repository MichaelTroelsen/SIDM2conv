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
ALL_OPTS = ("MON_ARP_STRUCT", "MON_PULSE_CANON", "MON_WAVE_CANON")
# `MON_SWEEP_OPTS=MON_WAVE_CANON` measures ONE prong instead of all three. The
# corpus run answers "are these safe together"; when a target regresses, the
# next question is always which of the three did it, and a three-way A/B needs
# to be a rerun of the same apparatus rather than a hand-edited copy of it --
# otherwise the isolation run and the run it is explaining are not comparable.
# The unselected options are still explicitly UNSET on both sides, so they
# cannot leak in from the environment and be credited to the one under test.
_SEL = [o.strip() for o in os.environ.get("MON_SWEEP_OPTS", "").split(",") if o.strip()]
for _o in _SEL:
    if _o not in ALL_OPTS:
        sys.exit(f"MON_SWEEP_OPTS: unknown option {_o!r}; pick from {ALL_OPTS}")
STRUCT_ENV = {k: "1" for k in (_SEL or ALL_OPTS)}
PLAIN_ENV = {k: None for k in STRUCT_ENV}      # the same options, unset

# (tune, subtune) -- the natively-built MoN corpus per docs/players/MON.md.
TARGETS = [("Hawkeye", 0), ("Hawkeye", 2), ("Hawkeye", 3),
           ("Cybernoid", 0), ("Cybernoid_II", 0),
           ("Supremacy", 0), ("Supremacy", 1), ("Supremacy", 2)]

PART_RE = re.compile(r"part (\d+)/(\d+) \((\d+)-(\d+)s")
OSC_RE = re.compile(r"^\s*osc(\d)\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+"
                    r"\(\s*([\d.]+)/\s*([\d.]+)/\s*([\d.]+)\)", re.M)
# The envelope column is appended after the (f/w/p) triple rather than inserted
# into it, so OSC_RE above is untouched and every number it already read still
# comes from the same place. Both an absent voice and an `n/a` envelope leave the
# key out of the row, which `fidelity_common.regressions` reads as a measurement
# that stopped existing -- not as agreement.
ADSR_RE = re.compile(r"^\s*osc(\d)\b.*?\)\s+adsr\s+\S+\s+\(\s*([\d.]+)\)", re.M)
# Global filter registers, one line each. `n/a` lines deliberately do not match:
# an unexercised register contributes no score, instead of a fake 100.
FILT_RE = re.compile(r"^\s*filter (cutoff|ctrl|mode\+vol)\s*\([^)]*\) match: "
                     r"([\d.]+)%", re.M)
FILT_DIM = {"cutoff": "cutoff", "ctrl": "filtctl", "mode+vol": "volmode"}

# The columns OSC_RE captures are mon_part_fidelity's skew-tolerant (f/w/p)
# triple, reading $D400/$D401, $D404 and $D402/$D403. Until 2026-08-07 that was
# the WHOLE gate, and the R17 question it was built to answer -- are
# MON_ARP_STRUCT / MON_PULSE_CANON / MON_WAVE_CANON safe as defaults -- is about
# options that re-compress wave and pulse PROGRAMS, whose most obvious place to
# lose something was $D405/$D406: a re-derived program can hold pitch, waveform
# and duty exactly and still restart an envelope a frame early. That register was
# not read here at all, so "7 clean wins" meant "clean in three registers".
# `adsr` closes it; `cutoff`/`filtctl`/`volmode` close the filter side. What is
# still unread by this run is printed by `format_run_delta` at the end, from the
# rows themselves, so this comment can never be the only thing that knows.
SCORE_KEYS = ("freq", "wf", "pul")


def build(tune, sub, structural):
    env = dict(os.environ)
    for k in ALL_OPTS:         # make sure an inherited flag cannot leak in --
        env.pop(k, None)       # including one this run is NOT measuring
    if structural:
        env.update(STRUCT_ENV)
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

    -> {"osc1/freq": 99.8, ..., "osc1/adsr": ..., "cutoff": ..., "filtctl": ...}.
    A voice or register mon_part_fidelity printed as `n/a` simply has no key,
    which `fidelity_common.regressions` reads as a lost measurement rather than
    as unchanged -- so a register that stops being comparable between the two
    builds is a finding, not a silent pass.
    """
    p = subprocess.run([sys.executable, FIDELITY, part_path, str(sub), str(secs)],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800)
    out = (p.stdout or "") + (p.stderr or "")
    scores = {f"osc{m.group(1)}/{k}": float(m.group(2 + i))
              for m in OSC_RE.finditer(out)
              for i, k in enumerate(SCORE_KEYS)}
    scores.update({f"osc{m.group(1)}/adsr": float(m.group(2))
                   for m in ADSR_RE.finditer(out)})
    scores.update({FILT_DIM[m.group(1)]: float(m.group(2))
                   for m in FILT_RE.finditer(out)})
    return scores


def _voices(keys):
    """score keys -> the sorted osc numbers they mention, for the report line.

    Global registers (`cutoff`, `filtctl`, `volmode`) are unscoped and belong to
    no voice; they are reported by name instead of being forced into this list.
    """
    return sorted({int(s[3:]) for s in (FC.split_key(k)[0] for k in keys)
                   if s.startswith("osc") and s[3:].isdigit()})


def _globals(keys):
    """score keys -> the sorted global (unscoped) dimension names they mention."""
    return sorted({FC.split_key(k)[1] for k in keys if not FC.split_key(k)[0]})


def _triple(row, v):
    return tuple(row["scores"].get(f"osc{v}/{k}")
                 for k in SCORE_KEYS + ("adsr",))


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

    bad = [k for k, _, _ in FC.regressions(off_row, on_row)]
    regressed, glob = _voices(bad), _globals(bad)
    verdict = "REGRESSED" if bad else ("WIN" if on_parts < off_parts else "same")
    print(f"{tune} sub{sub}: parts {off_parts} -> {on_parts}  [{secs}s window]  "
          f"{verdict}" + (f"  osc{regressed} worse" if regressed else "")
          + (f"  {glob} worse" if glob else ""), flush=True)
    allk = set(off_row["scores"]) | set(on_row["scores"])
    for v in _voices(allk):
        print(f"    osc{v}  off {_triple(off_row, v)}   "
              f"on {_triple(on_row, v)}   (f/w/p/adsr)", flush=True)
    for g in _globals(allk):
        print(f"    {g:8} off {off_row['scores'].get(g)}   "
              f"on {on_row['scores'].get(g)}", flush=True)
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
    bad = [(t, [k for k, _, _ in reg]) for t, reg in delta.regressed]
    print(f"\n{len(pairs)} target(s): {off} parts -> {on} parts "
          f"({off - on} fewer), {len(bad)} regressed")
    for t, keys in bad:
        print(f"  !! {t} osc{_voices(keys)}"
              + (f" {_globals(keys)}" if _globals(keys) else ""))
    print("\n" + FC.format_run_delta(delta))
    return delta.exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
