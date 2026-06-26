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
    reg = T.run_trace(sid, nframes * ms + 8, h.init_address, h.play_address, subtune)

    def rser(vi, fld, n):
        d = reg.get((vi, fld), {})
        out, cur = [], 0
        for i in range(n):
            if i in d:
                cur = d[i]
            out.append(cur)
        return out

    n = nframes * ms + 8
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

    # The dbg frame counter includes SF2II's startup (silent) before playback,
    # so dbg-frame != song-frame. Find the alignment offset that maximises the
    # voice-0..2 frequency match (search a window of leading offsets).
    import math as _m
    have = sorted(ours)

    def score(off):
        s = 0
        for f in have:
            sf = f - off
            if sf < 0 or sf * ms + ms - 1 >= n:
                continue
            for v in range(3):
                ov = o(f, v)
                pc = sf * ms + ms - 1
                rf = real[v]["freq"][pc]
                if (real[v]["ctl"][pc] & 1 and ov and ov["freq"] > 0 and rf > 0
                        and abs(_m.log2(ov["freq"] / rf)) <= 1.0 / 12):
                    s += 1
        return s
    import math as _m
    off = max(range(0, 400), key=score)
    print(f"\nglobal dbg->song offset = {off} frames; comparing (multispeed={ms}):")
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
