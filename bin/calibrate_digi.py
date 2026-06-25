"""Closed-loop digi-lead pitch calibration: render the ORIGINAL and MINE, measure each
note's pitch in both, and iteratively correct my per-frame gap until mine matches the
original note-for-note. (The reSID 6581 smooths the digi in a way that's hard to model
analytically; this just measures the real output and converges to it.)

Usage: py -3 bin/calibrate_digi.py <sid-name> <out-stem> [mode hybrid|nco] [seconds]
       [tune] [budget] [iters]
"""
import os, sys, subprocess, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))
import build_galway_digi as G

VSID = G.VSID; CPF = G.CYC_PER_FRAME; PAL = 985248
name = sys.argv[1]
stem = sys.argv[2]
mode = sys.argv[3] if len(sys.argv) > 3 else "hybrid"
seconds = int(sys.argv[4]) if len(sys.argv) > 4 else 14
tune = int(sys.argv[5]) if len(sys.argv) > 5 else 1
budget = sys.argv[6] if len(sys.argv) > 6 else "15000"
iters = int(sys.argv[7]) if len(sys.argv) > 7 else 4
sidrel = os.path.join("SID", "Galway_Martin", name + ".sid")
sidpath = os.path.join(ROOT, sidrel)
frames = str(seconds * 50)
corrfile = os.path.join(ROOT, "out", "_gapcorr_%s.npy" % stem)


def render(sid, wav):
    subprocess.run([VSID, "-console", "-sounddev", "wav", "-soundarg", wav,
                    "-limitcycles", str(int((seconds + 0.3) * PAL)), "-tune", str(tune), sid],
                   capture_output=True)


def readwav(p):
    w = wave.open(p, "rb"); sr = w.getframerate(); ch = w.getnchannels()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    w.close(); return x / 32768.0, sr


def note_pitches(x, sr, notes):
    return [G._peak_pitch(x[int(s / 50.0 * sr):int((e + 1) / 50.0 * sr)], sr) for s, e in notes]


def build(env_extra):
    env = dict(os.environ); env.update(env_extra)
    env["GALWAY_NCO_BUDGET"] = budget; env["GALWAY_GAPCORR"] = corrfile
    cap = {"hybrid": "GALWAY_DIGI_HYBRID", "nco": "GALWAY_DIGI_NCO"}[mode]
    env[cap] = "1"
    r = subprocess.run([sys.executable, "bin/build_galway_digi.py", name, str(seconds), str(tune)],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    if r.returncode: sys.exit("capture failed:\n" + r.stderr[-1500:])
    env["GALWAY_DIGI_SPIKE"] = "1"
    r = subprocess.run([sys.executable, "bin/build_galway_trace_song.py", sidrel, frames],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    if r.returncode: sys.exit("song build failed:\n" + r.stderr[-1500:])


# 1) original: note structure + per-note pitch
writes = G.dump_d418(sidpath, seconds, tune)
nframes = max(c // CPF for c, _ in writes) + 1
notes = G.lead_notes(writes, nframes)
render(sidpath, os.path.join(ROOT, "out", "_cal_orig.wav"))
xo, sr = readwav(os.path.join(ROOT, "out", "_cal_orig.wav"))
P_orig = note_pitches(xo, sr, notes)
print(f"{len(notes)} lead notes; original pitches (first 8 Hz): {[int(p) for p in P_orig[:8]]}")

# 2) iterate: build -> render mine -> measure -> correct per note
# (resume from a saved correction if present, so reruns refine instead of restarting)
if os.path.exists(corrfile) and len(np.load(corrfile)) == nframes:
    corr = np.load(corrfile); print("resuming from saved correction")
else:
    corr = np.ones(nframes)
for it in range(iters):
    np.save(corrfile, corr)
    build({cap: "1"} if False else {})       # env set inside build()
    render(os.path.join(ROOT, "out", "galway_trace_song.sid"), os.path.join(ROOT, "out", "_cal_mine.wav"))
    xm, _ = readwav(os.path.join(ROOT, "out", "_cal_mine.wav"))
    P_mine = note_pitches(xm, sr, notes)
    errs = [abs(12 * np.log2(m / o)) for o, m in zip(P_orig, P_mine) if o > 60 and m > 60]
    print(f"iter {it}: pitch error  max {max(errs):.3f}  mean {np.mean(errs):.3f} semitones "
          f"(over {len(errs)} notes)")
    for (s, e), o, m in zip(notes, P_orig, P_mine):
        if o > 60 and m > 60:
            factor = min(1.3, max(0.77, o / m))          # clamp per-iteration
            corr[s:e + 1] *= factor

# 3) final build with the converged correction, save under the stem
np.save(corrfile, corr)
build({})
for ext in (".sf2", ".sid"):
    import shutil
    shutil.copy(os.path.join(ROOT, "out", "galway_trace_song" + ext),
                os.path.join(ROOT, "out", stem + ext))
print(f"saved out/{stem}.sf2 + out/{stem}.sid (corr: out/_gapcorr_{stem}.npy)")
