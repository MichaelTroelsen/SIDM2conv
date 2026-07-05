"""Objective note-for-note validation of the ROMUZAK -> SF2 converter.

For each ROMUZAK tune this:
  1. converts it to a Driver-11 SF2 (the structured-orderlist path),
  2. wraps that SF2 driver image as a PSID probe (load=la, init=$1000, play=$1006),
  3. siddumps BOTH the probe and the original rip (its own header init/play),
  4. compares, per voice, the ordered list of UNBRACKETED note-onsets (the melody;
     arps/drums emit bracketed intermediate notes which are skipped),

so the converter is checked against the real player's output, not by ear.

  py -3 bin/romuzak_validate.py                 # both corpus tunes
  py -3 bin/romuzak_validate.py path/to.sid     # one tune
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from romuzak_to_sf2 import (
    load_sid, RMZ, calibrate_base, build_instruments, build_structured,
    _append_silent_instrument, find_tempo,
)
from sidm2.galway_to_driver11 import GalwayDriver11Song
from sidm2.galway_driver11_emitter import emit_driver11_sf2
from sidm2.sf2_parser import parse_sf2_blocks, SF2DriverInfo
from sidm2.fidelity_common import psid_wrap as _psid
from sidm2.fidelity_common import siddump_note_onsets

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECONDS = 40

CORPUS = [os.path.join('SID', 'Fun_Fun', n + '.sid') for n in (
    'Delirious_9_tune_1', 'Road_of_Excess_end')]


def _probe(path):
    """Convert a ROMUZAK rip -> Driver-11 SF2 -> PSID probe (init=$1000/play=$1006)."""
    d, la = load_sid(path)
    rmz = RMZ(d, la)
    base = calibrate_base(rmz)
    instr_rows, wave_table, pulse_table = build_instruments(rmz)
    silent_idx = _append_silent_instrument(instr_rows, wave_table, pulse_table)
    sequences, orderlists = build_structured(rmz, base, silent_idx)
    song = GalwayDriver11Song(
        instruments=instr_rows, wave_table=wave_table, pulse_table=pulse_table,
        tracks=[], tempo=find_tempo(d), pitch_base=base, subtune=0)
    sf2 = emit_driver11_sf2(song, sequences=sequences, orderlists=orderlists)
    info = SF2DriverInfo()
    sla = parse_sf2_blocks(sf2, info)
    return _psid(sf2[2:], sla, 0x1000, 0x1006)


def _notes(sidpath):
    """-> {0,1,2: [note_name, ...]} ordered unbracketed note-onsets per voice."""
    V = siddump_note_onsets(sidpath, [f'-t{SECONDS}'])
    return {v: [name for _, name in V[v]] for v in range(3)}


def validate(path):
    name = os.path.splitext(os.path.basename(path))[0]
    probe_sid = os.path.join('out', f'_rmzval_probe_{name}.sid')
    os.makedirs('out', exist_ok=True)
    open(probe_sid, 'wb').write(_probe(path))
    o, b = _notes(path), _notes(probe_sid)
    rows = []
    for v in range(3):
        n = min(len(o[v]), len(b[v]))
        match = sum(1 for i in range(n) if o[v][i] == b[v][i])
        rows.append((v, len(o[v]), len(b[v]), match, o[v] == b[v]))
    return name, rows


def main():
    os.chdir(ROOT)
    targets = sys.argv[1:] or CORPUS
    print(f"{'tune':28} {'voice':5} {'orig':>5} {'probe':>5} {'match':>12}")
    n_ok = n_total = 0
    for path in targets:
        if not os.path.exists(path):
            print(f"{os.path.basename(path):28} MISSING")
            continue
        name, rows = validate(path)
        for v, no, nb, m, exact in rows:
            n_total += 1
            edge = (not exact) and m == min(no, nb) and abs(no - nb) <= 2
            tag = 'EXACT' if exact else (f'{m}/{max(no,nb)} edge' if edge
                                         else f'{m}/{max(no,nb)}')
            if exact or edge:
                n_ok += 1
            print(f"{name:28} osc{v+1:<2} {no:5} {nb:5} {tag:>12}")
        print()
    print(f"note-accurate voices: {n_ok}/{n_total}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
