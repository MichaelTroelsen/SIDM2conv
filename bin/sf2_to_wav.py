"""One-shot 'listen' pipeline: .sf2 -> .sid (PSID wrap via scripts/sf2_to_sid) ->
.wav (SID2WAV / reSID) so output can be auditioned + compared headlessly.

Usage: py -3 bin/sf2_to_wav.py in.sf2 [seconds] [subtune]
       py -3 bin/sf2_to_wav.py in.sid [seconds] [subtune]   (skips the SF2 step)
Writes <stem>.sid + <stem>.wav next to the input and prints the WAV's RMS
energy (SILENT vs AUDIBLE). Pair with bin/wav_energy.py to compare two WAVs."""
import os
import sys
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))
SID2WAV = os.path.join(ROOT, "tools", "SID2WAV.EXE")
SF2_TO_SID = os.path.join(ROOT, "scripts", "sf2_to_sid.py")


def main():
    inp = sys.argv[1]
    secs = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    subtune = sys.argv[3] if len(sys.argv) > 3 else None
    stem = os.path.splitext(inp)[0]
    sid = inp if inp.lower().endswith(".sid") else stem + ".sid"
    wav = stem + ".wav"

    if not inp.lower().endswith(".sid"):
        r = subprocess.run([sys.executable, SF2_TO_SID, inp, sid, "-q"],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0:
            sys.stderr.write(r.stdout + r.stderr)
            raise SystemExit("sf2_to_sid failed")

    cmd = [SID2WAV, "-16", f"-t{secs}"]
    if subtune is not None:
        cmd.append(f"-o{subtune}")
    cmd += [sid, wav]
    subprocess.run(cmd, capture_output=True, text=True)
    if not os.path.exists(wav):
        raise SystemExit("SID2WAV produced no WAV")

    import wav_energy
    fr, ss = wav_energy.rms_per_second(wav)
    peak = max(ss) if ss else 0
    overall = (sum(s * s for s in ss) / len(ss)) ** 0.5 if ss else 0
    print(f"{wav}: {len(ss)}s overall RMS {overall:.4f} peak/s {peak:.4f} "
          f"-> {'SILENT' if peak < 0.002 else 'AUDIBLE'}")


if __name__ == "__main__":
    main()
