"""Rebuild the WHOLE Galway corpus fresh into out/galway_sf2/<name>.sf2 (the on-disk
corpus had a mix of fresh + stale/wrong-subtune builds). Each tune uses its PSID-default
subtune (= the music for all tunes except Combat_School, whose default 0 is a sparse
jingle -> override to subtune 1). Trace-driven native-driver build (SID voices; the
$D418 digi layer is a separate deliverable). Prints per-tune FAITHFUL/CHECK + note count.

Usage: py -3 bin/build_galway_corpus.py [frames] [name-substr]
"""
import os, re, sys, glob, shutil, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sidm2.sid_parser import SIDParser

FRAMES = sys.argv[1] if len(sys.argv) > 1 else "3500"
FILT = sys.argv[2] if len(sys.argv) > 2 else ""
SIDD = os.path.join(ROOT, "SID", "Galway_Martin")
OUTD = os.path.join(ROOT, "out", "galway_sf2")
os.makedirs(OUTD, exist_ok=True)

# subtune index (0-based) overrides; everything else uses the PSID default (start_song-1)
# PSID-default subtune is a sparse jingle for these; the music is a later subtune:
SUBTUNE = {"Combat_School": 1, "Yie_Ar_Kung_Fu_II": 3}

ok = bad = 0
for sid in sorted(glob.glob(os.path.join(SIDD, "*.sid"))):
    name = os.path.splitext(os.path.basename(sid))[0]
    if FILT and FILT not in name:
        continue
    h = SIDParser(sid).parse_header()
    st = SUBTUNE.get(name, (h.start_song or 1) - 1)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "bin", "build_galway_trace_song.py"),
                        sid, FRAMES, str(st)], capture_output=True, text=True, cwd=ROOT)
    faithful = "TRACE BUILD FAITHFUL" in r.stdout
    notes = sum(int(m) for m in re.findall(r"(\d+) notes", r.stdout)[:1]) if "notes" in r.stdout else 0
    voiced = len(re.findall(r"osc\d: \d+ notes", r.stdout))
    if r.returncode == 0 and os.path.exists(os.path.join(ROOT, "out", "galway_trace_song.sf2")):
        shutil.copy(os.path.join(ROOT, "out", "galway_trace_song.sf2"), os.path.join(OUTD, name + ".sf2"))
        shutil.copy(os.path.join(ROOT, "out", "galway_trace_song.sid"), os.path.join(OUTD, name + ".sid"))
        ok += 1
        print(f"{name:34s} st{st} {notes:5d} notes {voiced}v  {'FAITHFUL' if faithful else 'CHECK'}")
    else:
        bad += 1
        print(f"{name:34s} st{st}  BUILD FAILED: {r.stderr.strip().splitlines()[-1][:80] if r.stderr.strip() else '?'}")
    sys.stdout.flush()
print(f"\n=== rebuilt {ok}, failed {bad} ===")
