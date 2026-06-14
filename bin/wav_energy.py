"""Report per-second RMS energy of a WAV (and optionally compare two), so we can
objectively tell whether a rendered SID is SILENT or AUDIBLE, and roughly how
two renders differ — a headless stand-in for listening."""
import sys
import wave
import struct


def rms_per_second(path):
    w = wave.open(path, "rb")
    sw, ch, fr, n = w.getsampwidth(), w.getnchannels(), w.getframerate(), w.getnframes()
    raw = w.readframes(n)
    w.close()
    if sw == 2:
        samples = struct.unpack("<%dh" % (len(raw) // 2), raw)
        scale = 32768.0
    else:
        samples = [b - 128 for b in raw]
        scale = 128.0
    if ch == 2:
        samples = samples[::2]
    secs = []
    step = fr
    for i in range(0, len(samples), step):
        chunk = samples[i:i + step]
        if not chunk:
            break
        ms = (sum(s * s for s in chunk) / len(chunk)) ** 0.5 / scale
        secs.append(ms)
    return fr, secs


def main():
    for path in sys.argv[1:]:
        fr, secs = rms_per_second(path)
        peak = max(secs) if secs else 0
        overall = (sum(s * s for s in secs) / len(secs)) ** 0.5 if secs else 0
        print(f"\n{path}")
        print(f"  {len(secs)}s @ {fr}Hz | overall RMS {overall:.4f} | peak/s {peak:.4f}"
              f" | {'SILENT' if peak < 0.002 else 'AUDIBLE'}")
        print("  per-second RMS: " + " ".join(f"{s:.3f}" for s in secs[:20]))


if __name__ == "__main__":
    main()
