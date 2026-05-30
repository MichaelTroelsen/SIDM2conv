#!/usr/bin/env python3
"""Build the Galway SF2 driver skeleton with 64tass.

Stage B build helper. Locates 64tass (Downloads or PATH), assembles
galway_driver.asm -> out/galway_driver.prg. The .sf2 wrapper (descriptor +
edit area pointing init/play/stop at this driver) is the next Stage B step.

Usage:  py -3 drivers_src/galway/build.py
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ASM = os.path.join(HERE, "galway_driver.asm")
OUT = os.path.join(ROOT, "out", "galway_driver.prg")

# Known 64tass locations (PATH first, then the copies found in Downloads).
_CANDIDATES = [
    shutil.which("64tass"),
    r"C:\Users\mit\Downloads\64tass-1.60\64tass-1.60.3243\64tass.exe",
    r"C:\Users\mit\Downloads\SIDdecompiler-master\SIDdecompiler-master\test\64tass.exe",
]


def find_64tass():
    for c in _CANDIDATES:
        if c and os.path.exists(c):
            return c
    raise FileNotFoundError(
        "64tass not found. Install it or extract 64tass-1.60.3243.zip from "
        "Downloads; update _CANDIDATES with the path.")


def main():
    tass = find_64tass()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    r = subprocess.run([tass, "--cbm-prg", "-o", OUT, ASM],
                       capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    if r.returncode != 0 or not os.path.exists(OUT):
        print("BUILD FAILED")
        return 1
    d = open(OUT, "rb").read()
    load = d[0] | (d[1] << 8)
    print(f"OK: {OUT} ({len(d)} bytes, load ${load:04X})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
