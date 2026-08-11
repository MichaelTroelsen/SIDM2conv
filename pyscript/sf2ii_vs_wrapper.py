"""Does SF2II play our .sf2 the same way our own .sid wrapper does?

This is the comparison PLAYBOOK sec.4 rung 3 actually needs, and until now
nothing in the repo did it -- it lived in a scratch file that would have
vanished with the temp directory.

`bin/sf2ii_vs_real.py` answers a DIFFERENT question: it diffs the editor
against the ORIGINAL tune, so it scores the conversion and the editor together
and cannot separate them. Rung 3 only asks whether the editor executes our
build the way we think it does. Our `.sid` wrapper and our `.sf2` carry the
SAME driver and the SAME data, so comparing SF2II against the wrapper isolates
exactly that: any disagreement is an SF2II-only hazard, and agreement means the
remaining gap to the original is conversion, not editor.

Getting this wrong cost two retracted conclusions (docs/players/HARDTRACK.md):
"the tool is unreliable" came from calling a Driver 11 Stage A build the
control for a native Stage B claim, and "Stage B fails rung 3" came from
scoring the editor against the original with a single mis-fitted offset.

    py -3 pyscript/sf2ii_vs_wrapper.py <ours.sf2> <ours_wrapper.sid> [seconds]

Reports, per voice, the % of gated frames where frequency / waveform / pulse
agree. A passing rung 3 looks like 100% on every column at offset 0.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))

from sidm2.fidelity_common import iter_siddump_rows, run_siddump  # noqa: E402

# How far the search may look. It is symmetric on purpose: a render can LEAD as
# well as lag, and a search that cannot express a negative offset silently
# reports the offset-0 value as though it were the result -- the defect that
# made sf2ii_vs_real.py mis-score HardTrack by 25-70 points per voice.
MAX_LEAD = 32
MAX_LAG = 400


def wrapper_registers(sid, seconds):
    """{frame: [(freq, control, pulse)] * 3} from the wrapper's own siddump."""
    txt = run_siddump(sid, [f"-t{seconds}"])
    out = {}
    last = [[0, 0, 0] for _ in range(3)]
    for fr, cells in iter_siddump_rows(txt):
        if fr is None:
            continue
        for vi in range(3):
            tok = cells[2 + vi].split()
            if len(tok) > 5:
                for slot, ti in ((0, 0), (1, 3), (2, 5)):
                    if "." not in tok[ti]:
                        last[vi][slot] = int(tok[ti], 16)
        out[fr] = [tuple(x) for x in last]
    return out


def sf2ii_registers(frame, voice, cap):
    """One voice's (freq, control, pulse) from a captured SF2II frame."""
    b = cap.get(frame)
    if b is None:
        return None
    base = 7 * voice
    return (b[base] | (b[base + 1] << 8), b[base + 4],
            b[base + 2] | ((b[base + 3] & 0xF) << 8))


def score(cap, wrap, voice, off):
    """(freq hits, waveform hits, pulse hits, gated total) at this offset."""
    hit = [0, 0, 0]
    tot = 0
    for f in cap:
        w = wrap.get(f - off)
        o = sf2ii_registers(f, voice, cap)
        if w is None or o is None or not (w[voice][1] & 1):
            continue
        tot += 1
        hit[0] += o[0] == w[voice][0]
        hit[1] += (o[1] & 0xF0) == (w[voice][1] & 0xF0)
        hit[2] += o[2] == w[voice][2]
    return hit[0], hit[1], hit[2], tot


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2:
        raise SystemExit(__doc__)
    sf2, wrapper = argv[0], argv[1]
    seconds = int(argv[2]) if len(argv) > 2 else 18

    import sf2ii_vs_real as V
    print(f"capturing {seconds}s of SF2II playback of {sf2} ...")
    cap = V.capture_sf2ii(sf2, seconds + 2)
    print(f"  captured {len(cap)} SF2II frames")
    wrap = wrapper_registers(wrapper, seconds)

    # Rank by match RATE, not by raw hits: how many frames an offset leaves
    # inside the window varies with the offset, so raw hits reward whichever
    # alignment simply compares more frames. Coverage is a fairness filter.
    cand = {}
    for off in range(-MAX_LEAD, MAX_LAG):
        per = [score(cap, wrap, v, off) for v in range(3)]
        cov = sum(t for *_, t in per)
        if cov:
            cand[off] = (per, cov)
    if not cand:
        raise SystemExit("no overlapping frames -- wrong wrapper, or too short")
    covmax = max(c for _, c in cand.values())
    ok = [o for o, (_, c) in cand.items() if c >= 0.5 * covmax] or list(cand)
    off = max(ok, key=lambda o: sum(h / t for h, _, _, t in cand[o][0] if t >= 20))

    print(f"\nSF2II -> wrapper offset = {off} frames")
    print(f"{'voice':>6} {'freq':>9} {'waveform':>9} {'pulse':>9} {'n':>7}")
    worst = 100.0
    for v in range(3):
        fh, wh, ph, tot = cand[off][0][v]
        if not tot:
            print(f"{v:>6} {'(never gated)':>29}")
            continue
        pct = [100 * fh / tot, 100 * wh / tot, 100 * ph / tot]
        worst = min(worst, *pct)
        print(f"{v:>6} {pct[0]:8.1f}% {pct[1]:8.1f}% {pct[2]:8.1f}% {tot:7}")
    print()
    if worst >= 99.95 and off == 0:
        print("RUNG 3 PASSES: the editor plays our SF2 exactly as our own render does.")
    else:
        print(f"RUNG 3 DOES NOT PASS CLEANLY (worst column {worst:.1f}%, offset {off}).")
        print("Before blaming the editor, check the inputs: the .sf2 and the .sid")
        print("wrapper must come from the SAME build of the SAME part.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
