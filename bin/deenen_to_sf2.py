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


def _wave_program(m, di, wf, base_row):
    """Driver 11 wave rows for Deenen instrument `di`, or None if it has no
    wave program (-> the caller's plain held-waveform default).

    Mirrors the engine RE'd in `sidm2.deenen_parser.wave_program` (see its
    docstring; verified against the live player's own freq shadow). Two
    stream modes, chosen by the stream header's bit7:

    * RAW (bit7 SET) = PERCUSSION. Each byte is written to BOTH SID freq hi
      and lo, so the pitch is `b<<8|b` -- a fixed sweep INDEPENDENT of the
      played note. Emitted as Driver 11 ABSOLUTE-note rows (`col1 $80-$DF`,
      documented in SF2_FORMAT_SPEC.md as "Absolute note (great for drums)"
      and already used by bin/fc_to_sf2.py's drum path + kimmel_to_sf2.py).
      NOTE this QUANTIZES: `b<<8|b` is not exactly a semitone, so the row
      plays the nearest one. Inaudible on a click, but it IS an approximation
      -- the only lossy step here, and it is deliberate, not silent.
    * note mode (bit7 CLEAR) = a real pitch program: `>= $7F` is an absolute
      note, otherwise a RELATIVE semitone added to the played note (`col1
      $01-$7D`). Constant_Runner's instr 0 is this: absolute $81 then
      +5,+4,+3,+2,+1,+0 = a descending slide into pitch.

    The engine plays the note's OWN pitch for exactly ONE frame before the
    stream takes over (observed live: voice1 frame 1 = the base note, frame 2+
    = the drum), so -- exactly like fc_to_sf2's drum path -- lead with one
    root row. `speed` (frames per step, from the header) is honoured by
    repeating each row; `$FE` (hold-forever) becomes a self-jump; `$FF`
    (loop) jumps back to the stream's own loop target.
    """
    wp = m.wave_program(di)
    if wp is None or not wp['steps']:
        return None
    rows = [(wf, 0x00)]                                  # the 1 root frame
    step_row = {}                                        # stream step -> row idx
    for si, (kind, val) in enumerate(wp['steps']):
        if kind == 'hold':                               # $FE: sustain forever
            here = len(rows)
            rows.append((0x7F, here - 1))                # re-play the last row
            return rows
        if kind == 'loop':                               # $FF: back to the loop target
            rows.append((0x7F, step_row.get(val, 0)))
            return rows
        step_row[si] = len(rows)
        if kind == 'raw':                                # percussion: absolute pitch
            col1 = 0x80 | max(0, min(95, freq_to_semi((val << 8) | val)))
        elif val >= 0x7F:                                # absolute note
            col1 = 0x80 | max(0, min(95, val & 0x7F))
        else:                                            # relative semitone
            col1 = val & 0x7F
        for _ in range(wp['speed']):                     # frames per step
            rows.append((wf, col1))
    rows.append((0x7F, len(rows) - 1))                   # ran off the end -> hold
    return rows


def build_instruments(m, used):
    """One Driver 11 instrument per used Deenen instrument record (8-byte:
    packed-PW, waveform, AD, SR, flags...)."""
    instr_rows, wave_table, pulse_table, idx_map = [], [], [], {}
    for di in used:
        ins = m.instrument(di)
        idx_map[di] = len(instr_rows)
        wf = _norm_waveform(ins['wf'])
        wave_row = len(wave_table)
        prog = _wave_program(m, di, wf, wave_row)
        if prog is not None:
            wave_table.extend((c0, c1 if c0 != 0x7F else c1 + wave_row)
                              for c0, c1 in prog)
        else:
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
