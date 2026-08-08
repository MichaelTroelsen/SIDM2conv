"""Scratch: measure fidelity of a NATIVE windowed part SF2 vs the original window.
Part 1 starts at song frame 0 (no leading-rest offset), so it aligns directly to
the original's first N frames. Wraps the part's SF2 bytes as a PSID (native driver
play=$1003) and compares freq(semitone)/wf/pulse/filter per voice.

Usage: py -3 bin/_verify_part.py out/mon/Hawkeye_sub0_part01.sf2 0 106
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))
os.chdir(ROOT)

import bin.mon_sf2_validate as v
import bin.mon_fidelity as F
from sidm2.sf2_parser import parse_sf2_blocks, SF2DriverInfo

part = sys.argv[1]
sub = int(sys.argv[2])
secs = int(sys.argv[3])
if secs <= 0:
    # secs=0 used to make n negative -> ALL comparison loops empty -> a
    # VACUOUS "100.0" (real, painful lesson: a silent SF2 measured perfect).
    # Default to 20s, capped below by the probe's actual length.
    secs = 20
# 4th arg = the part's start second in the original song (its window t0). The part
# plays from its own frame 0 (a leading rest positions the first note), so part frame
# k == original frame off0+k.
off0 = int(sys.argv[4]) * 50 if len(sys.argv) > 4 else 0

sf2 = bytearray(open(part, "rb").read())
info = SF2DriverInfo()
sla = parse_sf2_blocks(sf2, info)
# probe name derived from the part file: concurrent fidelity runs previously
# clobbered a single shared probe and measured each other's SF2s (near-zero
# freq/pulse with wf ~25-45% = the corrupted-probe signature)
probe = os.path.join(
    "out", f"_verify_probe_{os.path.splitext(os.path.basename(part))[0]}.sid")
open(probe, "wb").write(v._psid(bytes(sf2[2:]), sla, 0x1000, 0x1003))

# infer the original SID from the part filename ("<Tune>_sub<N>..." -> <Tune>.sid).
# strip the _partNN suffix too (Fun_Fun/Bjerregaard parts have no _sub segment).
tune = os.path.basename(part).split("_sub")[0].split("_song")[0].split("_native")[0]
if "_part" in tune:
    tune = tune.split("_part")[0]
for folder in ("Tel_Jeroen", "Hubbard_Rob", "Fun_Fun", "JohannesBjerregaard"):
    orig_sid = os.path.join("SID", folder, f"{tune}.sid")
    if os.path.exists(orig_sid):
        break
from sidm2.fidelity_common import (siddump_frames_full as _full,  # noqa: E402
                                   exercised as _exercised,
                                   shape_agreement as _shape)
# `siddump_frames_full`, not `per_frame`: the same siddump run, parsed for the
# registers per_frame throws away. $D405/$D406 (per voice) and $D417/$D418
# (global) are exactly the registers a wave-program / pulse-program
# re-compression can move while freq, waveform and pulse width all stay put, so
# scoring only those three was never evidence the envelope survived.
orig = _full(orig_sid, [f"-a{sub}", f"-t{(off0 // 50) + secs + 1}"])
prb = _full(probe, [f"-t{secs + 1}"])
n = min(len(orig) - off0, len(prb), secs * 50) - 4
if n <= 0:
    sys.exit(f"FIDELITY ERROR: empty comparison window (n={n}) — "
             f"orig={len(orig)} off0={off0} probe={len(prb)} secs={secs}")
# AUTO-CAP at the part's end: a windowed part covers only its own span, then the
# driver LOOPS it from the start — measuring past that compares the replayed
# beginning against later song content and fabricates a giant tail "residual"
# (Shockway part01 = 0-22s, measured at 25s -> a phantom 148-frame freq run at
# 1098+). Detect the loop restart by self-similarity: the earliest late frame
# where a 40-frame window of all-voice freqs equals the probe's own opening.
def _sig(i):
    return tuple(prb[i + j][0][v]["freq"] for j in range(40) for v in range(3))
if n > 300:
    head = _sig(2)
    for i in range(250, n - 45):
        if _sig(i) == head:
            print(f"  [note] probe loops back to its start at frame {i} — "
                  f"capping the window there (was {n} frames; the part ends "
                  f"before `secs`)")
            n = i
            break

# constant engine output delay (e.g. Supremacy writes SID registers 2 frames after
# the sequencer tick, which the native driver doesn't reproduce): align it out with
# a small freq-match search, like every other fidelity tool (mon_fidelity etc.).
def _score(d):
    s = 0
    for i in range(0, n, 2):
        for vi in range(3):
            a = orig[off0 + d + i][0][vi]["freq"]
            b = prb[i][0][vi]["freq"]
            if a and b and F._semi(a) == F._semi(b):
                s += 1
    return s
# bidirectional: a window whose boundary-continuation tick rounds off the swing
# grid can start a frame or two EARLY relative to the window label (negative
# delay) — a one-sided search mis-aligns the whole part (39% "loss" that was
# really a constant -1 shift). Constant shifts are a nuisance parameter.
dly = max(range(-4 if off0 >= 4 else -off0, 7), key=_score)
off0 += dly

# PER-VOICE delay refinement: voices can sit a frame apart from the shared delay
# (the original staggers its per-voice register writes across the play call, the
# driver writes them together). One global dly then costs a phantom ~1-2% on the
# offset voice. Refine ±2 frames per voice by freq agreement.
def _vscore(vi, extra):
    s = 0
    base = off0 + extra
    for i in range(0, n, 2):
        if 0 <= base + i < len(orig):
            a = orig[base + i][0][vi]["freq"]
            b = prb[i][0][vi]["freq"]
            if a and b and F._semi(a) == F._semi(b):
                s += 1
    return s
vdly = [max(range(-2, 3), key=lambda e, v=vi: _vscore(v, e)) for vi in range(3)]

print(f"{os.path.basename(part)}  {n} frames from {off0 // 50}s "
      f"(native play=$1003, engine delay={dly}, per-voice {vdly})\n")
# Only the columns added for the R17 widening (adsr, cutoff, $D417, $D418) run
# through `fidelity_common.exercised`. freq/wf/pul keep their original
# denominator untouched, so every number already published for this corpus stays
# comparable with the ones this tool printed before the widening.
print(f"  {'voice':6} {'freq%':>6} {'wf%':>6} {'pulse%':>7}   skew-tolerant (f/w/p)"
      f"   + adsr% ($D405/$D406, skew-tolerant)")
for vi in range(3):
    keys = ("freq", "wf", "pul", "adsr")
    tot = {k: 0 for k in keys}
    ok = {k: 0 for k in keys}
    skew = {k: 0 for k in keys}          # mismatch that equals a ±1-frame neighbour
    seen = {k: ([], []) for k in keys}   # (orig, probe) value series, for _exercised
    o0 = off0 + vdly[vi]

    def _val(frames_row, k):
        v = frames_row[0][vi][k]
        return None if v is None else (F._semi(v) if k == "freq" else v)
    for i in range(n):
        if not (0 <= o0 + i < len(orig)):
            continue
        o, p = orig[o0 + i], prb[i]
        for k in keys:
            a, b = _val(o, k), _val(p, k)
            seen[k][0].append(a)
            seen[k][1].append(b)
            if a is None and b is None:
                continue
            tot[k] += 1
            if a == b:
                ok[k] += 1
                continue
            # RESIDUAL CLASSIFICATION: if the probe value matches the original one
            # frame earlier/later (a value TRANSITION landing a frame off), the
            # mismatch is 1-frame SKEW — an inaudible register-write phase artifact,
            # not a content error. Whatever remains after skew is REAL residual.
            prev = _val(orig[o0 + i - 1], k) if o0 + i - 1 >= 0 else None
            nxt = _val(orig[o0 + i + 1], k) if o0 + i + 1 < len(orig) else None
            if b is not None and (b == prev or b == nxt):
                skew[k] += 1
    # adsr is scored only where the register can tell the two sides apart at
    # all; a silent voice's envelope pair is 0 on both sides forever.
    if not _exercised(*seen["adsr"]):
        tot["adsr"] = 0

    def pct(k):
        # None when nothing was comparable — see fidelity_common.score_pct.
        return F.score_pct(ok[k], tot[k])
    def spct(k):
        return F.score_pct(ok[k] + skew[k], tot[k])
    # adsr is APPENDED, never inserted: the existing three columns and the
    # (f/w/p) triple keep their exact positions so older parsers of this table
    # (pyscript/mon_struct_sweep.py's OSC_RE, bin/_sm_measure_all.py) and any
    # saved baseline still read the same numbers out of the same places.
    print(f"  osc{vi + 1:<3} {F.fmt_pct(pct('freq'), 6)} {F.fmt_pct(pct('wf'), 6)}"
          f" {F.fmt_pct(pct('pul'), 7)}"
          f"   ({F.fmt_pct(spct('freq'))}/{F.fmt_pct(spct('wf'))}"
          f"/{F.fmt_pct(spct('pul'))})"
          f"   adsr {F.fmt_pct(pct('adsr'), 6)} ({F.fmt_pct(spct('adsr'))})")
    # MISMATCH CLUSTERS: where the real residual lives. For any register under
    # 99.5% strict, compress its mismatch frames into runs and show the top 3 —
    # a cluster at a note onset = capture/base problem there; a long sustained
    # run = a wrong program; scattered singletons = timing jitter.
    for k in keys:
        if not tot[k] or pct(k) >= 99.5:   # tot first: pct is None when tot==0
            continue
        miss = []
        for i in range(n):
            if not (0 <= o0 + i < len(orig)):
                continue
            a, b = _val(orig[o0 + i], k), _val(prb[i], k)
            if (a is None and b is None) or a == b:
                continue
            miss.append(i)
        runs, s = [], None
        for j, f in enumerate(miss):
            if s is None:
                s = f
            if j + 1 == len(miss) or miss[j + 1] > f + 3:   # gap>3 ends a run
                runs.append((s, f))
                s = None
        runs.sort(key=lambda r: r[0] - r[1])                 # longest first
        top = "  ".join(f"{a}-{b}({b - a + 1}f)" for a, b in runs[:3])
        print(f"        {k:4} residual: {len(miss)}f in {len(runs)} runs; "
              f"top: {top}")
        # PHASE-INVARIANT SHAPE, for the swept register only. Per-frame
        # equality asks "same value on frame i", which for a pulse SWEEP is
        # mostly a question about phase: a sweep with the right rate, depth and
        # direction that starts a few frames late disagrees on nearly every
        # frame and prints a near-zero pul% that reads as a dead pulse engine.
        # The ±1-frame skew column above does not reach a multi-frame offset.
        # Movement count and travel are computed from consecutive differences,
        # so a constant lag barely moves them. NOT a pass on their own — equal
        # totals do not mean equal shapes — so this prints only BESIDE the
        # strict number, never instead of it. Not applied to wf (an enum, where
        # |difference| is meaningless) or freq (already semitone-quantised and
        # skew-classified).
        if k == "pul":
            mp, tp, (am, bm), (at, bt) = _shape(*seen[k])
            print(f"        {k:4} shape   : moves {am}/{bm} = "
                  f"{F.fmt_pct(mp)}%   travel {at}/{bt} = {F.fmt_pct(tp)}%"
                  f"   (phase-invariant; size of the motion, not its match)")
            # BEST-LAG READOUT -- informational only. Never written into
            # ok/tot/pct, never changes the strict number above. vdly aligns
            # each voice by FREQ agreement only (see the vdly comment above);
            # a voice whose pulse writes trail its freq writes by more than a
            # couple of frames stays misaligned in THIS column alone, and the
            # +-1 skew classification cannot reach a multi-frame offset --
            # exactly the gap this readout is for. Search is +-8 because
            # that is wider than vdly's own +-2 refinement search. This
            # answers "is the pulse engine dead, or just offset" for a
            # human reading the report; it is NOT a proposal to realign
            # pulse independently of freq in the strict scoring above --
            # that is a separate, unmade decision (it would move published
            # freq/wf/pul numbers for every file in the corpus, not just
            # this one). See docs/players/PATTERNS.md D9.
            def _lag_pct(extra):
                o1 = o0 + extra
                s = t = 0
                for i in range(n):
                    if not (0 <= o1 + i < len(orig)):
                        continue
                    a, b = _val(orig[o1 + i], k), _val(prb[i], k)
                    if a is None and b is None:
                        continue
                    t += 1
                    s += (a == b)
                return F.score_pct(s, t)
            lags = {e: _lag_pct(e) for e in range(-8, 9) if e}
            best_extra = max(lags, key=lambda e: (lags[e] is not None, lags[e] or -1))
            best_pct = lags[best_extra]
            strict = pct(k)
            if best_pct is not None and (strict is None or best_pct > strict + 5):
                print(f"        {k:4} best lag: {best_extra:+d} frames beyond vdly -> "
                      f"{F.fmt_pct(best_pct)}%  (diagnostic only -- NOT the strict "
                      f"number above; aligning pulse independently of freq is a "
                      f"separate, unmade decision)")
# GLOBAL FILTER REGISTERS. Frame 0 is skipped: siddump force-displays the whole
# filter column on its first row regardless of what the playroutine wrote, so
# frame 0 reports pre-init bus state (Hawkeye reads $D418 = $FF there, then its
# own init sets $1F) and the two traces' garbage need not agree.
FILT = [("cutoff", "cutoff  ($D415/$D416)"),
        ("filtctl", "ctrl    ($D417 res+routing)"),
        ("volmode", "mode+vol($D418 bits 0-6)")]
print()
for key, label in FILT:
    # Paired in one comprehension, not two zipped lists: a dropped out-of-range
    # frame must drop from BOTH sides at once or the whole tail shifts by one
    # and a perfect match reads as a total mismatch.
    pairs = [(orig[off0 + i][1][key], prb[i][1][key])
             for i in range(1, n) if 0 <= off0 + i < len(orig)]
    a_vals, b_vals = [p[0] for p in pairs], [p[1] for p in pairs]
    ftot = fok = 0
    if _exercised(a_vals, b_vals):
        for a, b in pairs:
            if a is None and b is None:
                continue
            ftot += 1
            fok += a == b
    _f = F.score_pct(fok, ftot)
    # n/a, NEVER 100.0. Both sides holding one identical value for the whole
    # window is the vacuous case: nothing was distinguished, so nothing passed.
    print(f"  filter {label} match: "
          + (f"{_f:.1f}%  (n={ftot})" if _f is not None
             else "n/a (constant and identical on both sides — this tune never "
                  "moves the register, so there is nothing here to pass)"))
    # Same phase-invariant companion as the pulse column, for the same reason:
    # a cutoff SWEEP that is a few frames out of step scores near zero per
    # frame. cutoff ONLY — $D417/$D418 are bitfields (resonance nibble, routing
    # bits, mode bits, volume nibble), where |difference| between two packed
    # bytes is not a distance and "travel" would be noise.
    if key == "cutoff" and _f is not None and _f < 99.5:
        mp, tp, (am, bm), (at, bt) = _shape(a_vals, b_vals)
        print(f"         shape   : moves {am}/{bm} = {F.fmt_pct(mp)}%"
              f"   travel {at}/{bt} = {F.fmt_pct(tp)}%"
              f"   (phase-invariant; size of the motion, not its match)")
