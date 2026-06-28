"""Objective note-for-note validation of the Future Composer -> SF2 converter.

For each FC tune (SID rip or native $1800 PRG module) this:
  1. converts it to a Driver-15 SF2 (the path that handles long silent intros),
  2. wraps that SF2 driver image as a PSID probe (load=la, init=$1000, play=$1006),
  3. siddumps BOTH the probe and the original tune,
  4. compares, per voice, the ordered list of UNBRACKETED note-onsets (the musical
     melody; arps/drums emit bracketed intermediate notes which are skipped),

so the converter is checked against the real player's actual output instead of by
ear. A perfect prefix with a +/-1 trailing count is just the capture-window edge.

  py -3 bin/fc_validate.py                 # full supported corpus (SID + native)
  py -3 bin/fc_validate.py path/to.sid     # one tune (SID rip or native .prg)

Known residual (Stage-A limitation, not a bug): voices whose melody rides FC's
per-frame synth — instrument-0 "grace notes" that the engine turns into fast
freq ornaments, and dropped glides — can't be reproduced by static Driver-11/15
tables. See docs/players/FUTURECOMPOSER.md.
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fc_to_sf2 import load_sid, fc_to_song, build_structured
from sidm2.fc_parser import parse_fc, detect_player
from sidm2.galway_driver11_emitter import emit_driver11_sf2
from sidm2.sf2_parser import parse_sf2_blocks, SF2DriverInfo
from scripts.sf2_to_sid import PSIDHeader

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECONDS = 40
D15_TEMPLATE = 'G5/examples/Driver 15 Test - Mood.sf2'

# The supported corpus: 5 SID rips ($1800 variant) + 4 native D64 modules.
CORPUS = [os.path.join('SID', 'Fun_Fun', n + '.sid') for n in (
    'Triangle_Intro', 'Triangle_2_years', 'Carillo_part_2',
    'Demo_of_the_Year_88_Elite_1997', 'Is_There_a_Difference')]
CORPUS += [os.path.join('out', 'fc_native', n + '.prg') for n in (
    'GAME_OVER', 'HEART', 'ITS_A_SIN', 'VOICES_IN_SPC_')]


def _psid(data, load, init, play):
    h = PSIDHeader(load_address=load, init_address=init, play_address=play)
    h.songs = 1
    h.start_song = 1
    return h.to_bytes() + data


def _probe(d, la):
    """Convert FC data -> D15 SF2 -> PSID probe (init=$1000/play=$1006)."""
    fc = parse_fc(d, la)
    song = fc_to_song(fc)
    seqs, ols = build_structured(fc, song.pitch_base, merge_rests=False)
    sf2 = emit_driver11_sf2(song, template_path=D15_TEMPLATE,
                            sequences=seqs, orderlists=ols, instr_layout='d15')
    info = SF2DriverInfo()
    sla = parse_sf2_blocks(sf2, info)
    return _psid(sf2[2:], sla, 0x1000, 0x1006)


def _notes(sidpath):
    """-> {0,1,2: [note_name, ...]} ordered unbracketed note-onsets per voice."""
    txt = subprocess.run(['py', '-3', 'pyscript/siddump_complete.py', sidpath,
                          f'-t{SECONDS}'], capture_output=True, text=True).stdout
    V = {0: [], 1: [], 2: []}
    for ln in txt.splitlines():
        if not ln.startswith('|') or 'Frame' in ln:
            continue
        c = [x.strip() for x in ln.split('|')]
        if len(c) < 6:
            continue
        for vi, cell in enumerate(c[2:5]):
            m = re.match(r'^([0-9A-F]{4})\s+([A-G][-#]\d)\b', cell)
            if m and m.group(1) != '0000':
                V[vi].append(m.group(2))
    return V


def validate(path):
    """Returns (name, [(voice, n_orig, n_probe, n_match_prefix, exact_bool)])."""
    name = os.path.splitext(os.path.basename(path))[0]
    d, la = load_sid(path)
    if not detect_player(d, la):
        return name, None
    init, play = (0x1800, 0x1806)
    orig_sid = os.path.join('out', f'_val_orig_{name}.sid')
    open(orig_sid, 'wb').write(_psid(d, la, init, play) if la != 0 else
                               _psid(d, la, init, play))
    probe_sid = os.path.join('out', f'_val_probe_{name}.sid')
    open(probe_sid, 'wb').write(_probe(d, la))
    o, b = _notes(orig_sid), _notes(probe_sid)
    rows = []
    for v in range(3):
        n = min(len(o[v]), len(b[v]))
        match = sum(1 for i in range(n) if o[v][i] == b[v][i])
        rows.append((v, len(o[v]), len(b[v]), match, o[v] == b[v]))
    return name, rows


def main():
    os.chdir(ROOT)
    targets = sys.argv[1:] or CORPUS
    print(f"{'tune':30} {'voice':5} {'orig':>5} {'probe':>5} {'match':>12}")
    n_exact = n_total = 0
    for path in targets:
        if not os.path.exists(path):
            print(f"{os.path.basename(path):30} MISSING")
            continue
        name, rows = validate(path)
        if rows is None:
            print(f"{name:30} (not the supported $1800 FC variant)")
            continue
        for v, no, nb, m, exact in rows:
            n_total += 1
            edge = (not exact) and m == min(no, nb) and abs(no - nb) <= 1
            tag = 'EXACT' if exact else (f'{m}/{max(no,nb)} edge' if edge
                                         else f'{m}/{max(no,nb)}')
            if exact or edge:
                n_exact += 1
            print(f"{name:30} osc{v+1:<2} {no:5} {nb:5} {tag:>12}")
        print()
    print(f"note-accurate voices: {n_exact}/{n_total}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
