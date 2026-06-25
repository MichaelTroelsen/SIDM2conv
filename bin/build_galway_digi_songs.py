"""Build the Galway $D418-digi tunes to out/, each as a stock-SF2II .sf2 (+ a PSID
.sid for VICE/SID2WAV rendering). Config-driven so new digi tunes drop in as a row.

Modes:
  nco     -- NCO sawtooth LEAD only (the tune's digi is 100% tonal; no drums).
  hybrid  -- NCO lead + PCM drum samples (the real beat ducks the lead per frame).

Each tune regenerates the shared drivers_src/galway/digi_addrs.inc + out/digi_blob.bin
during its build, so builds run sequentially (this script handles that).

Usage: py -3 bin/build_galway_digi_songs.py [name-substr]
       (optional filter builds only tunes whose stem contains the substring)
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
SIDD = os.path.join("SID", "Galway_Martin")

# (output stem, source .sid stem, mode, capture seconds, NCO cycle budget)
# budget = (PAL frame ~19704) - this tune's SF2II music-engine cost - safety. Arkanoid's
# SID voices are idle (cheap music) -> the lead can voice almost the whole frame; Game
# Over's voices are busy (dear music) -> leave more headroom (its leads are short anyway).
# All tunes use HYBRID mode + the gap-SWEEP lead (DIGI_SWEEP): the driver reproduces the
# source's intra-frame $D418 gap sweep (fast bursts -> long pauses) so reSID renders the
# right pitch AND timbre. Tonal tunes (no drums) play lead-only through the same path.
TUNES = [
    ("Arkanoid_tonal",   "Arkanoid",                    "hybrid", 14, 15000),
    ("Arkanoid_drums",   "Arkanoid_alternative_drums",  "hybrid", 14, 15000),
    ("Game_Over_drums",  "Game_Over",                   "hybrid", 40, 11000),
]


def run(env_extra, *cmd):
    env = dict(os.environ)
    env.update(env_extra)
    r = subprocess.run([sys.executable, *cmd], env=env, cwd=ROOT,
                       capture_output=True, text=True)
    sys.stdout.write(r.stdout[-1200:])
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-2000:])
        raise SystemExit(f"FAILED: {' '.join(cmd)}")


def build(stem, src, mode, seconds, budget):
    frames = str(seconds * 50)
    cap = {"nco": {"GALWAY_DIGI_NCO": "1"},
           "hybrid": {"GALWAY_DIGI_HYBRID": "1"}}[mode]
    cap["GALWAY_NCO_BUDGET"] = str(budget)
    cap["GALWAY_DIGI_SWEEP"] = "1"          # gap-sweep lead (hybrid path); see TUNES note
    song = dict(cap); song["GALWAY_DIGI_SPIKE"] = "1"
    print(f"=== {stem}  ({src}.sid, {mode}, {seconds}s, budget {budget}) ===")
    run(cap, "bin/build_galway_digi.py", src, str(seconds), "1")
    run(song, "bin/build_galway_trace_song.py", os.path.join(SIDD, src + ".sid"), frames)
    for ext in (".sf2", ".sid"):
        shutil.copy(os.path.join(OUT, "galway_trace_song" + ext),
                    os.path.join(OUT, stem + ext))
    print(f"  -> out/{stem}.sf2 + out/{stem}.sid\n")


def main():
    filt = sys.argv[1] if len(sys.argv) > 1 else ""
    for stem, src, mode, seconds, budget in TUNES:
        if filt and filt not in stem and filt not in src:
            continue
        build(stem, src, mode, seconds, budget)
    print("Done. Load any .sf2 in SID Factory II, or render the .sid via VICE.")


if __name__ == "__main__":
    main()
