"""Deenen-corpus Sound Monitor Stage A shim.

The 3 Sound Monitor rips misfiled in SID/deenen/ (Aids_See_Ass, Super_Heavy,
I_Saw_2_HC-Ass_5005s_Fucking) are genuine Sound Monitor songs at the STANDARD
fixed table addresses ($A000 bars / $AE00 sound / $C416 freq), but their
PSID init/play is a bank-switch WRAPPER: play=$C020 does
    LDA $01 / STA $02C5 / LDA #$36 / STA $01 / JSR $C475 ...
so the real play body lives at $C475 as usual -- except this SM build carries a
2-byte prefix (`28 14`) there, pushing the play SIGNATURE to $C477. That is the
ONLY reason sidm2.soundmonitor_parser.is_soundmonitor() rejects them; the parser
tables themselves decode perfectly (verified: sane row_count/notes-per-voice).

Rather than edit the shared parser (a concurrent agent owns sidm2/), this shim
imports bin/soundmonitor_to_sf2.py, relaxes the gate to also accept the +2
signature offset, and reuses the exact Stage A build path.

Usage:  py -3 bin/deenen_sm_build.py SID/deenen/Aids_See_Ass.sid [out.sf2]
"""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sidm2 import soundmonitor_parser as smp

# Relaxed detector: accept the standard sig at SM_PLAY OR the +2 wrapper variant.
_orig_is_sm = smp.is_soundmonitor


def _is_sm_relaxed(data, la, h):
    if _orig_is_sm(data, la, h):
        return True
    off = smp.SM_PLAY - la
    sig = smp._PLAY_SIG
    for delta in (0, 1, 2, 3):  # sig sits at SM_PLAY; play addr is a wrapper ($C020)
        if data[off + delta:off + delta + len(sig)] == sig:
            return True
    return False


# Load the real builder module by path and patch its gate.
_spec = importlib.util.spec_from_file_location(
    "soundmonitor_to_sf2", os.path.join(ROOT, "bin", "soundmonitor_to_sf2.py"))
_b = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_b)
_b.is_soundmonitor = _is_sm_relaxed


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        "out", "deenen_sf2", os.path.splitext(os.path.basename(path))[0] + ".sf2")
    return _b.convert(path, out)


if __name__ == "__main__":
    sys.exit(main())
