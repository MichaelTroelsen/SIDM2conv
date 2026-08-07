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

Each tune is built twice and part01 is scored against the ORIGINAL on the window
both builds share (their part01 windows differ, so scoring each on its own window
would compare different music). Myth is excluded: it is not buildable through
`build_mon_native_song` at all -- its pseudo-parse gate refuses it (speed byte
255) -- and needs `bin/build_myth_native_song.py`, which this driver does not
speak. Measure Myth separately.

    py -3 pyscript/mon_struct_sweep.py            # whole corpus
    py -3 pyscript/mon_struct_sweep.py Hawkeye:2  # one target
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDER = os.path.join(ROOT, "bin", "build_mon_native_song.py")
FIDELITY = os.path.join(ROOT, "bin", "mon_part_fidelity.py")
STRUCT_ENV = {"MON_ARP_STRUCT": "1", "MON_PULSE_CANON": "1",
              "MON_WAVE_CANON": "1"}

# (tune, subtune) -- the natively-built MoN corpus per docs/players/MON.md.
TARGETS = [("Hawkeye", 0), ("Hawkeye", 2), ("Hawkeye", 3),
           ("Cybernoid", 0), ("Cybernoid_II", 0),
           ("Supremacy", 0), ("Supremacy", 1), ("Supremacy", 2)]

PART_RE = re.compile(r"part (\d+)/(\d+) \((\d+)-(\d+)s")
OSC_RE = re.compile(r"^\s*osc(\d)\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+"
                    r"\(\s*([\d.]+)/\s*([\d.]+)/\s*([\d.]+)\)", re.M)


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
    """part01 vs the original over `secs` -- the best-delay (aligned) columns."""
    p = subprocess.run([sys.executable, FIDELITY, part_path, str(sub), str(secs)],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800)
    out = (p.stdout or "") + (p.stderr or "")
    return {int(m.group(1)): (float(m.group(2)), float(m.group(3)),
                              float(m.group(4)))
            for m in OSC_RE.finditer(out)}


def sweep_one(tune, sub):
    part01 = os.path.join(ROOT, "out", "mon", f"{tune}_sub{sub}_part01.sf2")
    # `mon_part_fidelity` infers the original SID from the filename by splitting
    # on "_sub", so the stash MUST keep "<Tune>_sub" as its prefix -- a name like
    # "_sweep_Hawkeye_sub2.sf2" resolves to tune "_sweep_Hawkeye", the trace
    # comes back empty, and every voice reads as a regression.
    stash = os.path.join(ROOT, "out", "mon",
                         f"{tune}_sub{sub}SWEEP_part01.sf2")

    on_parts, on_end, _ = build(tune, sub, True)
    if on_parts is None:
        print(f"{tune} sub{sub}: BUILD FAILED (structural) -- skipped", flush=True)
        return None
    shutil.copyfile(part01, stash)

    off_parts, off_end, _ = build(tune, sub, False)
    if off_parts is None:
        print(f"{tune} sub{sub}: BUILD FAILED (baseline) -- skipped", flush=True)
        return None

    # Score both on the window they SHARE; part01 spans differ between builds.
    secs = min(on_end, off_end)
    off_s = score(part01, sub, secs)
    on_s = score(stash, sub, secs)
    os.remove(stash)

    regressed = []
    for v in sorted(set(off_s) | set(on_s)):
        a, b = off_s.get(v), on_s.get(v)
        if a is None or b is None or any(y + 1e-9 < x for x, y in zip(a, b)):
            regressed.append(v)
    verdict = "REGRESSED" if regressed else ("WIN" if on_parts < off_parts
                                             else "same")
    print(f"{tune} sub{sub}: parts {off_parts} -> {on_parts}  "
          f"[{secs}s window]  {verdict}"
          + (f"  osc{regressed} worse" if regressed else ""), flush=True)
    for v in sorted(set(off_s) | set(on_s)):
        print(f"    osc{v}  off {off_s.get(v)}   on {on_s.get(v)}", flush=True)
    return {"tune": tune, "sub": sub, "off": off_parts, "on": on_parts,
            "regressed": regressed}


def main(argv):
    targets = TARGETS
    if argv:
        targets = []
        for a in argv:
            t, _, s = a.partition(":")
            targets.append((t, int(s or 0)))

    rows = [r for r in (sweep_one(t, s) for t, s in targets) if r]
    off = sum(r["off"] for r in rows)
    on = sum(r["on"] for r in rows)
    bad = [r for r in rows if r["regressed"]]
    print(f"\n{len(rows)} target(s): {off} parts -> {on} parts "
          f"({off - on} fewer), {len(bad)} regressed")
    for r in bad:
        print(f"  !! {r['tune']} sub{r['sub']} osc{r['regressed']}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
