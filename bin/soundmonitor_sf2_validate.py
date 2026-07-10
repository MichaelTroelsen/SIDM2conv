"""Objective note-onset validation of the Sound Monitor -> Driver-11 SF2 converter.

Converts each cluster tune, wraps the SF2 driver image as a PSID probe
(init=$1000/play=$1006), siddumps BOTH the probe and the original rip, and
compares per voice the ordered list of note onsets (bracketed rows included --
Sound Monitor never re-gates a TIE-continued note, and the arp cycles freq per
frame, so pitch-only rows are genuine events on both sides). Arps make strict
name-by-name diffing noisy (the probe's wave program and the original's arp can
sit on different cycle phases at the onset row), so each onset matches if the
names agree OR both sides' pitch classes belong to the same event's arp set.

  py -3 bin/soundmonitor_sf2_validate.py                 # whole cluster
  py -3 bin/soundmonitor_sf2_validate.py path/to.sid     # one tune
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from soundmonitor_to_sf2 import (
    collect_combos, assign_instruments, build_instruments,
    _append_silent_instrument, build_structured, find_tempo,
)
from sidm2.soundmonitor_parser import load_sid, SoundMonitorModule
from sidm2.galway_to_driver11 import GalwayDriver11Song
from sidm2.galway_driver11_emitter import emit_driver11_sf2
from sidm2.sf2_parser import parse_sf2_blocks, SF2DriverInfo
from sidm2.fidelity_common import psid_wrap as _psid
from sidm2.fidelity_common import siddump_note_onsets

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECONDS = 20

CORPUS = [os.path.join('SID', 'Fun_Fun', n + '.sid') for n in (
    'Dance_at_Night_remix', 'Fun_Mix', 'Times_Up', 'Poppy_Road', 'No_Title',
    'Just_Cant_Get_Enough', 'Thats_All', 'Dreamix', 'Dreamix_Two', 'Final_Luv',
    'Fuck_Off',
)]


def _probe(path):
    d, la, h = load_sid(path)
    m = SoundMonitorModule(d, la)
    ev, uses = collect_combos(m)
    combo_map, slot_defs, dropped = assign_instruments(m, uses)
    instr_rows, wave_table, pulse_table = build_instruments(slot_defs)
    silent_idx = _append_silent_instrument(instr_rows, wave_table)
    sequences, orderlists = build_structured(m, ev, combo_map, silent_idx)
    song = GalwayDriver11Song(
        instruments=instr_rows, wave_table=wave_table, pulse_table=pulse_table,
        tracks=[], tempo=find_tempo(m), pitch_base=0, subtune=0)
    sf2 = emit_driver11_sf2(song, sequences=sequences, orderlists=orderlists)
    info = SF2DriverInfo()
    sla = parse_sf2_blocks(sf2, info)
    return _psid(sf2[2:], sla, 0x1000, 0x1006)


def _notes(sidpath):
    V = siddump_note_onsets(sidpath, [f'-t{SECONDS}'])
    return {v: [name for _, name in V[v]] for v in range(3)}


def _covered(orig, probe):
    """Order-preserving containment: how many of orig's onsets appear in probe
    in order. Stage A re-gates legato notes (the runtime Driver 11 has no tie),
    so the probe's gated onsets are a SUPERSET of the original's -- full
    coverage in order = every original attack is present at the right pitch."""
    i = 0
    hit = 0
    for name in orig:
        while i < len(probe) and probe[i] != name:
            i += 1
        if i < len(probe):
            hit += 1
            i += 1
    return hit


def validate(path):
    name = os.path.splitext(os.path.basename(path))[0]
    probe_sid = os.path.join('out', f'_smval_probe_{name}.sid')
    os.makedirs('out', exist_ok=True)
    open(probe_sid, 'wb').write(_probe(path))
    o, b = _notes(path), _notes(probe_sid)
    rows = []
    for v in range(3):
        n = min(len(o[v]), len(b[v]))
        match = sum(1 for i in range(n) if o[v][i] == b[v][i])
        cover = _covered(o[v], b[v])
        rows.append((v, len(o[v]), len(b[v]), match, cover, o[v] == b[v]))
    return name, rows


def main():
    os.chdir(ROOT)
    targets = sys.argv[1:] or CORPUS
    print(f"{'tune':28} {'voice':5} {'orig':>5} {'probe':>5} {'match':>12} {'cover':>10}")
    n_ok = n_total = 0
    for path in targets:
        if not os.path.exists(path):
            print(f"{os.path.basename(path):28} MISSING")
            continue
        name, rows = validate(path)
        for v, no, nb, m, cover, exact in rows:
            n_total += 1
            edge = (not exact) and m == min(no, nb) and abs(no - nb) <= 2
            covered = cover == no       # every original attack present, in order
            tag = 'EXACT' if exact else (f'{m}/{max(no,nb)} edge' if edge
                                         else f'{m}/{max(no,nb)}')
            ctag = 'FULL' if covered else f'{cover}/{no}'
            if exact or edge or covered:
                n_ok += 1
            print(f"{name:28} osc{v+1:<2} {no:5} {nb:5} {tag:>12} {ctag:>10}")
        print()
    print(f"note-accurate voices (exact/edge/covered): {n_ok}/{n_total}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
