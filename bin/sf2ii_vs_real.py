"""LISTEN/COMPARE tool: diff what SF2II ACTUALLY plays for our .sf2 against the
real SID, per voice, per frame — so the converter can be debugged against the
truth instead of guessing.

  py -3 bin/sf2ii_vs_real.py <orig.sid> <ours.sf2> [seconds] [multispeed]

How: run an instrumented SF2II (bin/SIDFactoryII_dbg.exe, built from the patched
source — dumps 'SIDFR <frame> r0..r24' each update + auto-plays on argv-load) on
ours.sf2 for `seconds`, capturing its per-video-frame SID registers. Trace the
real SID over the matching range. Align by multispeed (SF2II runs the driver N
play-ticks/frame; the real trace is per play-call) and report, per voice, the %
of frames where freq / waveform / pulse / AD-SR match, with example divergences.
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sidm2.sid_parser import SIDParser
from sidm2 import galway_trace_extract as T

DBG_SRC = r"C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master\x64\Release\SIDFactoryII.exe"
DBG = os.path.join(ROOT, "bin", "SIDFactoryII_dbg.exe")


def capture_sf2ii(sf2, seconds):
    import shutil
    if os.path.exists(DBG_SRC):
        shutil.copyfile(DBG_SRC, DBG)
    errf = os.path.join(ROOT, "out", "sf2ii_listen.err")
    fh = open(errf, "w", encoding="utf-8", errors="replace")
    p = subprocess.Popen([DBG, os.path.abspath(sf2), "--skip-intro"],
                         cwd=os.path.join(ROOT, "bin"),
                         stdout=subprocess.DEVNULL, stderr=fh)
    time.sleep(seconds)
    p.kill()
    p.wait(timeout=5)
    fh.close()
    frames = {}
    for ln in open(errf, encoding="utf-8", errors="replace"):
        if "SIDFR " not in ln:
            continue
        p2 = ln.split("SIDFR ", 1)[1].split()
        if len(p2) >= 26:
            frames[int(p2[0])] = [int(x, 16) for x in p2[1:26]]
    return frames


def main():
    sid = sys.argv[1]
    sf2 = sys.argv[2]
    seconds = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    ms = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    sub_arg = int(sys.argv[5]) if len(sys.argv) > 5 else None   # subtune (else PSID default)
    nframes = int(seconds * 50.12)

    print(f"capturing {seconds}s of SF2II playback of {sf2} ...")
    ours = capture_sf2ii(sf2, seconds + 2)
    print(f"  captured {len(ours)} SF2II frames")

    h = SIDParser(sid).parse_header()
    subtune = sub_arg if sub_arg is not None else (h.start_song or 1) - 1
    # MAXLEAD frames of headroom so the search can express a render that LEADS
    # the original (a negative offset) without running off the end of the trace.
    MAXLEAD = 32
    n = (nframes + MAXLEAD + 8) * ms + 8
    reg = T.run_trace(sid, n, h.init_address, h.play_address, subtune)

    from sidm2.fidelity_common import fill_forward

    def rser(vi, fld, n):
        return fill_forward(reg.get((vi, fld), {}), n)

    real = {}
    for v in range(3):
        real[v] = {
            "freq": [(rser(v, "freq_hi", n)[i] << 8) | rser(v, "freq_lo", n)[i] for i in range(n)],
            "ctl": rser(v, "control", n),
            "pw": [((rser(v, "pw_hi", n)[i] & 0xF) << 8) | rser(v, "pw_lo", n)[i] for i in range(n)],
            "ad": rser(v, "attack_decay", n),
            "sr": rser(v, "sustain_release", n),
        }

    # ours SID layout: voice v regs at 7*v: freq_lo,freq_hi,pw_lo,pw_hi,ctl,ad,sr
    def o(fr, v):
        b = ours.get(fr)
        if b is None:
            return None
        base = 7 * v
        return {
            "freq": b[base] | (b[base + 1] << 8),
            "ctl": b[base + 4],
            "pw": b[base + 2] | ((b[base + 3] & 0xF) << 8),
            "ad": b[base + 5], "sr": b[base + 6],
        }

    # The dbg frame counter need not agree with the song frame, so find the
    # alignment offset that maximises the voice-0..2 frequency match.
    #
    # TWO properties this search has to have, each of which it lacked and each
    # of which produced a retracted HardTrack conclusion (docs/players/HARDTRACK.md):
    #
    #  1. The offset CAN BE NEGATIVE. Our render may LEAD the original -- Stage B
    #     HardTrack sits at -3 -- and a search over range(0, 400) simply cannot
    #     say so. It then reports the offset-0 value (23.8/13.2/4.0% on
    #     Love_tune_2) as though it were the build's fidelity; at -3 the same
    #     comparison gives 91.7/93.8/63.0%.
    #
    #  2. It ranks by per-voice match RATE, not by raw hit count. Hits are
    #     confounded by how many captured frames a given offset leaves inside
    #     the trace window: on that same file, offset 157 beat -3 on raw hits
    #     (208+43+52) purely by comparing more frames, at a far worse rate
    #     (67/14/62%). Coverage is handled as a fairness FILTER instead -- an
    #     offset that can only compare half the frames is a smaller experiment,
    #     not a better alignment -- and rate is maximised within it.
    #
    # The offset is GLOBAL on purpose: it is one startup delay, and a per-voice
    # search over the same range overfits a repetitive tune (it picked 5/317/147
    # for three voices that in fact share -3).
    import math as _m
    have = sorted(ours)

    def vhits(v, off):
        """(hits, gated total) for voice v's frequency at this offset."""
        hit = tot = 0
        for f in have:
            sf = f - off
            if sf < 0:
                continue
            pc = sf * ms + ms - 1
            if pc >= n:
                continue
            ov = o(f, v)
            if ov is None or not (real[v]["ctl"][pc] & 1):
                continue
            tot += 1
            rf = real[v]["freq"][pc]
            if ov["freq"] > 0 and rf > 0 and abs(_m.log2(ov["freq"] / rf)) <= 1.0 / 12:
                hit += 1
        return hit, tot

    SEARCH = range(-MAXLEAD, 400)
    cand = {d: [vhits(v, d) for v in range(3)] for d in SEARCH}
    cov = {d: sum(t for _, t in hs) for d, hs in cand.items()}
    covmax = max(cov.values()) or 1
    # a voice needs enough gated frames for its rate to mean anything
    ratesum = lambda d: sum(h / t for h, t in cand[d] if t >= 20)
    ok = [d for d in SEARCH if cov[d] >= 0.5 * covmax] or list(SEARCH)
    off = max(ok, key=ratesum)
    print(f"\nglobal dbg->song offset = {off} frames; comparing (multispeed={ms}):")
    print("  freq match at that offset: " + "  ".join(
        f"osc{v + 1} {100 * cand[off][v][0] // cand[off][v][1] if cand[off][v][1] else 0}%"
        f" ({cand[off][v][0]}/{cand[off][v][1]})" for v in range(3)))
    print("(each metric reported at its OWN best offset in +-8 frames; a freq vs")
    print(" pulse offset gap on one voice = the two envelopes are desynced.)")
    fr_list = [f for f in have if 0 <= f - off < nframes]

    def match(v, metric, dof):
        """count (hits, total) for one metric at offset off+dof, gated frames only."""
        hit = tot = 0
        for f in fr_list:
            ov = o(f, v)
            if ov is None:
                continue
            pc = (f - off - dof) * ms + (ms - 1)
            if pc < 0 or pc >= n:
                continue
            rctl = real[v]["ctl"][pc]
            if not (rctl & 1):
                continue
            rfreq, rpw = real[v]["freq"][pc], real[v]["pw"][pc]
            tot += 1
            if metric == "freq":
                if ov["freq"] > 0 and rfreq > 0 and abs(_m.log2(ov["freq"] / rfreq)) <= 1.0 / 12:
                    hit += 1
            elif metric == "wave":
                if (ov["ctl"] & 0xF0) == (rctl & 0xF0):
                    hit += 1
            elif metric == "pw":
                if abs(ov["pw"] - rpw) <= 0x80:
                    hit += 1
            elif metric == "adsr":
                # match within 1 per nibble (attack/decay/sustain/release)
                rad, rsr = real[v]["ad"][pc], real[v]["sr"][pc]
                ok = all(abs(((x >> 4) & 0xF) - ((y >> 4) & 0xF)) <= 1 and
                         abs((x & 0xF) - (y & 0xF)) <= 1
                         for x, y in ((ov["ad"], rad), (ov["sr"], rsr)))
                if ok:
                    hit += 1
        return hit, tot

    for v in range(3):
        out = []
        for metric, label, search in (("freq", "freq", True), ("wave", "waveform", False),
                                      ("pw", "pulse", True), ("adsr", "AD/SR", False)):
            # only the per-frame ENVELOPES (freq/pulse) get an offset search;
            # waveform + AD/SR are per-note constants (offset-insensitive).
            best = max(range(-4, 5), key=lambda d: match(v, metric, d)[0]) if search else 0
            hit, tot = match(v, metric, best)
            p = 100 * hit // tot if tot else 0
            tag = f"@{best:+d}" if best else ""
            out.append(f"{label} {p}%{tag} ({hit}/{tot})")
        print(f" osc{v+1}: " + "  ".join(out))
        # semitone-delta histogram at the freq-best offset
        bf = max(range(-8, 9), key=lambda d: match(v, "freq", d)[0])
        hist = {}
        for f in fr_list:
            ov = o(f, v)
            if ov is None:
                continue
            pc = (f - off - bf) * ms + (ms - 1)
            if pc < 0 or pc >= n or not (real[v]["ctl"][pc] & 1):
                continue
            if ov["freq"] <= 0 or real[v]["freq"][pc] <= 0:
                continue
            st = int(round(12 * _m.log2(ov["freq"] / real[v]["freq"][pc])))
            hist[st] = hist.get(st, 0) + 1
        if hist:
            top = sorted(hist.items(), key=lambda kv: -kv[1])[:6]
            print("        semitone deltas (ours-real): " +
                  "  ".join(f"{k:+d}:{v2}" for k, v2 in top))

    # --- global FILTER: cutoff ($D416) + res/routing ($D417). ($D418 mode is set
    #     at init, so the play-trace can't see it — skip.) Only compares frames
    #     where the original routes a voice through the filter (res nibble != 0). ---
    rcut = rser(None, "freq_hi", n)
    rres = rser(None, "res_control", n)

    def fmatch(metric, dof):
        hit = tot = 0
        for f in fr_list:
            b = ours.get(f)
            if b is None:
                continue
            pc = (f - off - dof) * ms + (ms - 1)
            if pc < 0 or pc >= n or not (rres[pc] & 0x0F):
                continue
            tot += 1
            if metric == "cut" and abs(b[22] - rcut[pc]) <= 16:
                hit += 1
            elif metric == "res" and b[23] == rres[pc]:
                hit += 1
        return hit, tot

    fb = max(range(-4, 5), key=lambda d: fmatch("cut", d)[0])
    ch, ct = fmatch("cut", fb)
    rh, rt = fmatch("res", 0)
    if ct:
        print(f" filter: cutoff {100 * ch // ct}%@{fb:+d} ({ch}/{ct})  "
              f"res/route {100 * rh // rt if rt else 0}% ({rh}/{rt})")
    else:
        print(" filter: (original routes no voice through the filter)")


if __name__ == "__main__":
    main()
