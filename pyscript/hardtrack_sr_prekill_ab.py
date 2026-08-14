#!/usr/bin/env python3
"""HardTrack SR pre-kill A/B -- the decisive experiment for the rung-4 residual.

`docs/players/HARDTRACK.md` recorded one unattempted experiment: HardTrack zeroes
`$D406` for exactly two frames before every note (the classic hard restart), the
Stage B driver does not, and a row type cannot express the write because it lands
between two row boundaries. The named fix was a per-note lookahead in the driver.
It is now built -- `SR_PREKILL` in `drivers_src/mon/romuzak_driver.asm`, off by
default, enabled per build with `HT_SR_PREKILL=2` -- and this is the tool that
measures whether it is worth turning on.

It is tracked, and that is the point. Every DMC figure in CLAUDE.md came from a
script that was never in the repo, and the Sound Monitor headline was
unreproducible from a fresh clone for months. This one builds both sides itself
and quotes nothing it did not just measure.

For each tune it builds part 1 twice (pre-kill off, then on), then reports:

  * SR      -- frames where the render's `$D406` differs from the original's,
               summed over three voices at the render's -3 alignment. This is
               what the fix targets and it is unambiguous.
  * centroid / rolloff -- whole-file spectral deltas against the original. These
               are the *brightness gap* the experiment was supposed to close.

⚠️ **Every window here is that file's own asserted part-1 span**, taken from the
2026-08-13 brightness table in HARDTRACK.md. Measuring past a part's end is the
error this session made five times in three tools: our part LOOPS there against
the original's continuing music, and the difference scores as a defect. Five of
these nine files have 10-14 s part 1s. Do not raise a window without re-deriving
it from the builder's own `part 1/N (0-Xs)` line.

  py -3 pyscript/hardtrack_sr_prekill_ab.py [--first N] [--last N] [--prekill K]

Chunk long runs (--first/--last): a single parent process died at ~275 builds.
"""
import argparse
import glob
import hashlib
import os
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import numpy as np                                              # noqa: E402
from sidm2.audio_listen import extract_features                 # noqa: E402
from sidm2.fidelity_common import siddump_frames_full           # noqa: E402
from sidm2.sidplayfp_wrapper import export_to_wav               # noqa: E402

# (file stem, part-1 span in seconds). The spans are the builder's own, not
# guesses -- see the warning above.
CASES = [
    ("Muminki_Rooooolz", 28),
    ("Ritual_II_tune_2", 10),
    ("Rune-T_Noter", 14),
    ("Muza_Do_Dema", 28),
    ("Takisobie", 12),
    ("Walk_to_Soul", 10),
    ("Something_to_Eat", 10),
    ("Teekkno", 28),
    ("Love_tune_2", 28),
]

SID_DIR = os.path.join("SID", "Shogoon")
OUT_DIR = os.path.join("out", "hardtrack_native")
WORK = os.path.join("out", "_ht_sr_prekill")

# The render leads the original by 3 frames. It is a single global startup delay,
# NOT a per-voice one -- a per-voice search picked 5/317/147 for three voices that
# in fact share -3, because a repetitive tune has many spurious alignment peaks.
ALIGN = -3


# `part 1/6 (0-28s, 0-1400f): ...` -- the builder's own span for part 1. Read
# it from the SAME subprocess call that produced the build, never from a
# separate run and never guessed: measuring past a part's end is the error this
# whole file warns about.
PART1 = re.compile(r"part 1/\d+ \(0-(\d+)s")


def build(stem, prekill):
    """Build part 1 with SR_PREKILL=`prekill`.

    Returns (wrapper .sid path, part-1 span in seconds, error).
    """
    sid = os.path.join(SID_DIR, stem + ".sid")
    env = dict(os.environ, HT_SR_PREKILL=str(prekill))
    r = subprocess.run(["py", "-3", "bin/build_hardtrack_native_song.py", sid],
                       capture_output=True, text=True, env=env, cwd=ROOT)
    out = os.path.join(OUT_DIR, stem + "_part01.sid")
    if not os.path.exists(out):
        return None, None, (r.stdout[-300:] + r.stderr[-300:]).strip()
    m = PART1.search(r.stdout or "")
    keep = os.path.join(WORK, "%s_k%d.sid" % (stem, prekill))
    shutil.copyfile(out, keep)
    return keep, (int(m.group(1)) if m else None), None


def features(path, secs, tag):
    key = hashlib.md5(("%s|%d|%s" % (path, secs, tag)).encode()).hexdigest()[:10]
    wav_path = os.path.join(WORK, "%s.wav" % key)
    if not os.path.exists(wav_path):
        export_to_wav(Path(path), Path(wav_path), duration=secs)
    with wave.open(wav_path, 'rb') as w:
        sr, nch = w.getframerate(), w.getnchannels()
        raw = w.readframes(w.getnframes())
    x = np.frombuffer(raw, dtype='<i2').astype(np.float64) / 32768.0
    if nch > 1:
        x = x.reshape(-1, nch).mean(axis=1)
    return extract_features(x, sr)


def sr_mismatch(orig, rend, frames):
    """Frames where $D406 differs, summed over the three voices."""
    args = ["-t%d" % max(30, frames // 50 + 5)]
    o = siddump_frames_full(orig, args)
    r = siddump_frames_full(rend, args)
    n = 0
    for v in range(3):
        for i in range(frames):
            j = i + ALIGN
            if j < 0 or j >= len(r) or i >= len(o):
                continue
            a, b = o[i][0][v], r[j][0][v]
            if a['adsr'] is None or b['adsr'] is None:
                continue
            n += (a['adsr'] & 0xFF) != (b['adsr'] & 0xFF)
    return n


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", type=int, default=0)
    ap.add_argument("--last", type=int, default=len(CASES))
    ap.add_argument("--prekill", type=int, default=2,
                    help="frames of SR=$00 before a fetch (2 is the MEASURED "
                         "width: every run in the originals is exactly 2)")
    ap.add_argument("--all", action="store_true",
                    help="every SID/Shogoon file the builder accepts, each over "
                         "the part-1 span its OWN build reports, instead of the "
                         "nine-tune brightness table")
    ap.add_argument("--no-audio", action="store_true",
                    help="registers only -- skips the renders, which is most of "
                         "the wall clock on a corpus run")
    a = ap.parse_args(argv)
    os.makedirs(WORK, exist_ok=True)

    cases = CASES
    if a.all:
        cases = [(os.path.basename(p)[:-4], None)
                 for p in sorted(glob.glob(os.path.join(SID_DIR, "*.sid")))]

    print("%-20s %4s | %17s | %17s | %13s"
          % ("file", "win", "centroid off/on", "rolloff  off/on", "SR off/on"))
    rows = []
    for stem, secs in cases[a.first:a.last]:
        sid = os.path.join(SID_DIR, stem + ".sid")
        if not os.path.exists(sid):
            print("%-20s MISSING" % stem)
            continue
        off, span, err = build(stem, 0)
        if off is None:
            if not a.all:               # a refused rip is expected in --all
                print("%-20s BUILD FAILED (off): %s" % (stem, err))
            continue
        if secs is None:
            if span is None:
                print("%-20s SKIPPED: no part-1 span in the build output" % stem)
                continue
            secs = span
        elif span is not None and span < secs:
            # never measure past the part the build actually covers
            print("%-20s NOTE: asserted %ds > built span %ds, using %ds"
                  % (stem, secs, span, span))
            secs = span
        on, _, err = build(stem, a.prekill)
        if on is None:
            print("%-20s BUILD FAILED (on): %s" % (stem, err))
            continue

        nfr = secs * 50
        sb, sp = sr_mismatch(sid, off, nfr), sr_mismatch(sid, on, nfr)
        if a.no_audio:
            row = (stem, secs, 0.0, 0.0, 0.0, 0.0, sb, sp)
            print("%-20s %3ds | %35s | %6d %6d"
                  % (stem, secs, "(--no-audio)", sb, sp))
        else:
            fo = features(sid, secs, "orig")
            fb = features(off, secs, "off")
            fp = features(on, secs, "on")
            row = (stem, secs,
                   fb.centroid_hz_mean - fo.centroid_hz_mean,
                   fp.centroid_hz_mean - fo.centroid_hz_mean,
                   fb.rolloff85_hz_mean - fo.rolloff85_hz_mean,
                   fp.rolloff85_hz_mean - fo.rolloff85_hz_mean, sb, sp)
            print("%-20s %3ds | %+7.1f %+7.1f | %+7.1f %+7.1f | %6d %6d" % row)
        rows.append(row)
        sys.stdout.flush()

    if len(rows) > 1 and a.no_audio:
        worse = [r[0] for r in rows if r[7] > r[6]]
        print("\nSR mismatching frames %d -> %d over %d files; WORSE on %d %s"
              % (sum(r[6] for r in rows), sum(r[7] for r in rows), len(rows),
                 len(worse), worse[:6]))
    elif len(rows) > 1:
        cb = np.mean([abs(r[2]) for r in rows])
        cp = np.mean([abs(r[3]) for r in rows])
        rb = np.mean([abs(r[4]) for r in rows])
        rp = np.mean([abs(r[5]) for r in rows])
        print("\nmean |centroid error| %.1f -> %.1f Hz, |rolloff| %.1f -> %.1f Hz"
              % (cb, cp, rb, rp))
        print("SR mismatching frames %d -> %d over %d files"
              % (sum(r[6] for r in rows), sum(r[7] for r in rows), len(rows)))
        better = sum(1 for r in rows if abs(r[3]) < abs(r[2]))
        print("centroid closer to the original on %d of %d; further on %d"
              % (better, len(rows), len(rows) - better))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
