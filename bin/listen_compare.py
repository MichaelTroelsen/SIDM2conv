"""LISTEN & COMPARE: render the ORIGINAL and MY output, then compare them as audio over
time -- an autocorrelation PITCH track (robust to the digi's harmonics/modulation) plus a
log-mel SPECTRAL distance per 40 ms window. Prints where they diverge so the digi build
can be matched to the original by ear-equivalent measurement.

Usage: py -3 bin/listen_compare.py <orig .sid|.wav> <mine .sid|.wav> [seconds] [tune]
"""
import os, sys, subprocess, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))
import build_galway_digi as G
VSID = G.VSID; PAL = 985248
seconds = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
tune = sys.argv[4] if len(sys.argv) > 4 else "1"


def get_audio(path):
    if path.endswith(".sid"):
        wav = os.path.join(ROOT, "out", "_lc_tmp.wav")
        subprocess.run([VSID, "-console", "-sounddev", "wav", "-soundarg", wav,
                        "-limitcycles", str(int((seconds + 0.3) * PAL)), "-tune", tune, path],
                       capture_output=True)
        path = wav
    w = wave.open(path, "rb"); sr = w.getframerate(); ch = w.getnchannels()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    w.close()
    return x / 32768.0, sr


def logmel(seg, sr, nb=24):
    X = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    fq = np.fft.rfftfreq(len(seg), 1.0 / sr)
    edges = np.linspace(200, 5000, nb + 1)
    out = []
    for i in range(nb):
        m = (fq >= edges[i]) & (fq < edges[i + 1])
        out.append(X[m].sum())
    e = np.array(out)
    return np.log(e / (e.sum() + 1e-9) + 1e-6)


a, sr = get_audio(os.path.abspath(sys.argv[1]))
b, _ = get_audio(os.path.abspath(sys.argv[2]))
hop = int(0.04 * sr); win = int(0.06 * sr)
n = min(len(a), len(b)) - win
print(" t(s) | orig Hz | mine Hz | semis | spec-dist")
perr, sdist = [], []
for i in range(0, min(n, int(seconds * sr)), hop):
    pa = G._peak_pitch(a[i:i + win], sr)
    pb = G._peak_pitch(b[i:i + win], sr)
    sd = float(np.abs(logmel(a[i:i + win], sr) - logmel(b[i:i + win], sr)).mean())
    sdist.append(sd)
    s = ""
    if pa > 60 and pb > 60:
        import math
        sv = 12 * math.log2(pb / pa); perr.append(abs(sv)); s = f"{sv:+5.2f}"
    flag = "  <-- " + ("PITCH" if (s and abs(float(s)) > 0.4) else "") + (" SPEC" if sd > 0.5 else "")
    print(f"{i/sr:5.2f} | {pa:6.0f}  | {pb:6.0f}  | {s:>5} | {sd:.2f}{flag if flag.strip('< -') else ''}")
print(f"\nSUMMARY: mean |pitch err| {np.mean(perr):.3f} semitones (max {np.max(perr):.2f}); "
      f"mean spectral dist {np.mean(sdist):.3f}")
