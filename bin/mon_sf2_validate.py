"""Validate the MoN Stage-A SF2 (bin/mon_to_sf2.py) against the original SID.

Builds the Driver-11 SF2, wraps it as a PSID probe (init=$1000/play=$1006), siddumps
both the probe and the original rip, and compares per-voice note onsets (frame + note).
The Driver-11 boot adds a small CONSTANT startup offset (a few frames); we align it out
(median first-onset delta) and compare within ONE song length — the original halts at the
orderlist $FE while the SF2 loops, so we only compare up to the original's last onset.

  py -3 bin/mon_sf2_validate.py                       # Hawkeye subtune 3
  py -3 bin/mon_sf2_validate.py path.sid SUBTUNE
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from sidm2.mon_parser import load_sid, MON          # noqa: E402
from sidm2.sf2_parser import parse_sf2_blocks, SF2DriverInfo  # noqa: E402
from sidm2.fidelity_common import psid_wrap as _psid          # noqa: E402,F401 (re-exported)
from sidm2.fidelity_common import siddump_note_onsets         # noqa: E402
import bin.mon_to_sf2 as mon_to_sf2                  # noqa: E402

from sidm2.galway_to_driver11 import GalwayDriver11Song  # noqa: E402
from sidm2.galway_driver11_emitter import emit_driver11_sf2  # noqa: E402


def build_probe(path, subtune):
    d, la, _ = load_sid(path)
    m = MON(d, la, subtune)
    base = 0
    used = mon_to_sf2.used_instruments(m)
    instr_rows, wave_table, pulse_table, idx_map = mon_to_sf2.build_instruments(m, used)
    sequences, orderlists = mon_to_sf2.build_structured(m, base, idx_map)
    song = GalwayDriver11Song(
        instruments=instr_rows, wave_table=wave_table, pulse_table=pulse_table,
        tracks=[], tempo=m.speed, pitch_base=base, subtune=subtune)
    sf2 = emit_driver11_sf2(song, sequences=sequences, orderlists=orderlists)
    info = SF2DriverInfo()
    sla = parse_sf2_blocks(sf2, info)
    return _psid(sf2[2:], sla, 0x1000, 0x1006)


def onsets(path, args):
    return siddump_note_onsets(path, args, require_wf=True)


def main():
    os.chdir(ROOT)
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join('SID', 'Tel_Jeroen', 'Hawkeye.sid')
    subtune = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    seconds = 12

    os.makedirs('out', exist_ok=True)
    probe = os.path.join('out', '_mon_sf2_probe.sid')
    open(probe, 'wb').write(build_probe(path, subtune))

    orig = onsets(path, [f'-a{subtune}', f'-t{seconds}'])
    sf2 = onsets(probe, [f'-t{seconds}'])

    # global startup offset = median of per-voice first-onset deltas
    deltas = [sf2[v][0][0] - orig[v][0][0] for v in range(3) if orig[v] and sf2[v]]
    off = sorted(deltas)[len(deltas) // 2] if deltas else 0
    print(f"{os.path.basename(path)} subtune {subtune}  startup offset={off} frames\n")

    n_ok = n_tot = 0
    for v in range(3):
        o = orig[v]
        # only compare within one song length (original halts; SF2 loops)
        limit = o[-1][0] if o else 0
        s = [(f - off, nm) for (f, nm) in sf2[v] if f - off <= limit + 1]
        n = min(len(o), len(s))
        match = sum(1 for i in range(n) if o[i] == s[i])
        exact = (match == len(o) == len(s))
        n_ok += match
        n_tot += max(len(o), len(s))
        tag = 'EXACT' if exact else f'{match}/{max(len(o), len(s))}'
        print(f"  V{v}: orig={len(o):2} sf2(aligned)={len(s):2}  note+frame match={tag}")
        for i in range(n):
            if o[i] != s[i]:
                print(f"       first diff @{i}: orig {o[i]} vs sf2 {s[i]}")
                break
    print(f"\nnote+frame onsets matched: {n_ok}/{n_tot}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
