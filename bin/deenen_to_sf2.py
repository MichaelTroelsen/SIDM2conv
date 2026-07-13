"""Charles Deenen / MoN game-replay SID -> editable Driver 11 SF2 (Stage A DRAFT).

Standalone (NOT wired into driver_selector / conversion_pipeline yet), modelled on
bin/mon_to_sf2.py. Decodes the Deenen replay via sidm2/deenen_parser.py and
transpiles onto the shared Galway/ROMUZAK/MoN Driver 11 IR + emitter.

STATUS: the locate + engine map are solid (see sidm2/deenen_parser.py); note
PITCHES and instrument records are byte-correct, and sparse voices onset-match
siddump exactly. The top-level multi-segment orderlist ($106C/$195C) is not yet
modelled, so dense voices are truncated -- this builder emits what the one-pass
decoder yields. Onset fidelity: see bin/deenen_validate.py (do not overstate it).

Usage:  py -3 bin/deenen_to_sf2.py SID/deenen/Ding_van_Charles.sid [out.sf2] [subtune]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.deenen_parser import DeenenModule, load_sid
from sidm2.fidelity_common import freq_to_semi
from sidm2.galway_to_driver11 import (
    D11Instrument, D11Row, GalwayDriver11Song,
    SF2_NOTE_MIN, SF2_NOTE_MAX, SF2_GATE_ON, SF2_GATE_OFF,
    _norm_waveform, _pulse_program,
)
from sidm2.galway_driver11_emitter import emit_driver11_sf2, segment_track


def used_instruments(m):
    used = set()
    for v in range(3):
        for e in m.decode_voice(v, stop_on_loop=True):
            if e['kind'] == 'note':
                used.add(e['instr'])
    return sorted(used) or [0]


def build_instruments(m, used):
    """One Driver 11 instrument per used Deenen instrument record (8-byte:
    packed-PW, waveform, AD, SR, flags...)."""
    instr_rows, wave_table, pulse_table, idx_map = [], [], [], {}
    for di in used:
        ins = m.instrument(di)
        idx_map[di] = len(instr_rows)
        wf = _norm_waveform(ins['wf'])
        wave_row = len(wave_table)
        wave_table.append((wf, 0x00))
        wave_table.append((0x7F, wave_row))
        pulse_row = len(pulse_table)
        pulse_table.extend(_pulse_program(ins['pw'] or 0x800, pulse_row))
        instr_rows.append(D11Instrument(
            ad=ins['ad'], sr=ins['sr'], flags=0x80, filter_idx=0x00,
            pulse_idx=pulse_row, wave_idx=wave_row,
            pulse_width=(ins['pw'] >> 8) & 0x0F))
    return instr_rows, wave_table, pulse_table, idx_map


def _semi(m, note):
    """Deenen freq-table index -> SF2 chromatic semitone via the actual freq."""
    s = freq_to_semi(m._freq(note))
    return max(SF2_NOTE_MIN, min(s, SF2_NOTE_MAX)) if s >= 0 else SF2_NOTE_MIN


def voice_rows(m, v, idx_map):
    """Decoded events -> Driver 11 rows. note = 1 row + (dur-1) GATE_ON sustains;
    rest = (frames) GATE_OFF rows."""
    out = []
    cur = None
    for e in m.decode_voice(v):
        if e['kind'] == 'rest':
            out.extend(D11Row(note=SF2_GATE_OFF) for _ in range(max(1, e['frames'])))
            continue
        slot = idx_map.get(e['instr'], 0)
        inst = None
        if slot != cur:
            inst, cur = slot, slot
        out.append(D11Row(note=_semi(m, e['note']), instrument=inst))
        out.extend(D11Row(note=SF2_GATE_ON) for _ in range(max(0, e['frames'] - 1)))
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        'out', 'deenen_sf2', os.path.splitext(os.path.basename(path))[0] + '.sf2')
    subtune = int(sys.argv[3]) if len(sys.argv) > 3 else 0

    d, la, h = load_sid(path)
    m = DeenenModule(d, la, subtune, h)
    if not m.loc.ok():
        print(f"deenen locate FAILED ({m.loc.summary()}) for {path}")
        return 1
    force = '--force' in sys.argv
    if not m.plausible() and not force:
        print(f"deenen decode IMPLAUSIBLE (degenerate/filler) for {path}; "
              f"refusing to build garbage. Pass --force to override.")
        return 1

    used = used_instruments(m)
    instr_rows, wave_table, pulse_table, idx_map = build_instruments(m, used)

    seq_index, sequences, orderlists = {}, [], [[], [], []]
    for v in range(3):
        for pk in segment_track(voice_rows(m, v, idx_map)):
            idx = seq_index.get(pk)
            if idx is None:
                idx = len(sequences)
                seq_index[pk] = idx
                sequences.append(pk)
            orderlists[v].append(idx)

    song = GalwayDriver11Song(
        instruments=instr_rows, wave_table=wave_table, pulse_table=pulse_table,
        tracks=[], tempo=1, pitch_base=0, subtune=subtune)
    print(f"load=${la:04X} {m.loc.summary()} instruments={len(instr_rows)} "
          f"sequences={len(sequences)} notes/voice="
          f"{[sum(1 for e in m.decode_voice(v) if e['kind']=='note') for v in range(3)]}")
    sf2 = emit_driver11_sf2(song, sequences=sequences, orderlists=orderlists)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    open(out, 'wb').write(sf2)
    print(f"emitted {len(sf2)} bytes -> {out}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
