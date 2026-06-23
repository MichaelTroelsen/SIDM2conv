"""Build BOTH Arkanoid digi variants side by side, into out/ with distinct names:

  out/Arkanoid_tonal.sf2  -- main Arkanoid.sid, NCO sawtooth LEAD only (no drums;
                             that rip's digi is 100% tonal).
  out/Arkanoid_drums.sf2  -- Arkanoid_alternative_drums.sid, HYBRID engine:
                             NCO sawtooth lead + PCM drum samples (the real beat).

Each variant regenerates the shared drivers_src/galway/digi_addrs.inc + out/digi_blob.bin
during its build, so they must build sequentially (this script does that). A PSID
(.sid) is emitted alongside each .sf2 for VICE/SID2WAV rendering.

Usage: py -3 bin/build_arkanoid_both.py [seconds]
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
SECONDS = sys.argv[1] if len(sys.argv) > 1 else "14"
FRAMES = str(int(SECONDS) * 50)


def run(env_extra, *cmd):
    env = dict(os.environ)
    env.update(env_extra)
    r = subprocess.run([sys.executable, *cmd], env=env, cwd=ROOT,
                       capture_output=True, text=True)
    sys.stdout.write(r.stdout[-1500:])
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-2000:])
        raise SystemExit(f"FAILED: {' '.join(cmd)}")


def save(stem):
    for ext in (".sf2", ".sid"):
        shutil.copy(os.path.join(OUT, "galway_trace_song" + ext),
                    os.path.join(OUT, stem + ext))
    print(f"  -> out/{stem}.sf2 + out/{stem}.sid")


def main():
    sidd = os.path.join("SID", "Galway_Martin")

    print("=== 1/2  Arkanoid (tonal lead, no drums) ===")
    run({"GALWAY_DIGI_NCO": "1"},
        "bin/build_galway_digi.py", "Arkanoid", SECONDS, "1")
    run({"GALWAY_DIGI_SPIKE": "1", "GALWAY_DIGI_NCO": "1"},
        "bin/build_galway_trace_song.py", os.path.join(sidd, "Arkanoid.sid"), FRAMES)
    save("Arkanoid_tonal")

    print("\n=== 2/2  Arkanoid alternative drums (hybrid: lead + PCM drums) ===")
    run({"GALWAY_DIGI_HYBRID": "1"},
        "bin/build_galway_digi.py", "Arkanoid_alternative_drums", SECONDS, "1")
    run({"GALWAY_DIGI_SPIKE": "1", "GALWAY_DIGI_HYBRID": "1"},
        "bin/build_galway_trace_song.py",
        os.path.join(sidd, "Arkanoid_alternative_drums.sid"), FRAMES)
    save("Arkanoid_drums")

    print("\nDone. Load either .sf2 in SID Factory II, or render the .sid via VICE.")


if __name__ == "__main__":
    main()
