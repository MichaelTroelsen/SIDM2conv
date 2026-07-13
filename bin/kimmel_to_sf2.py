"""Jeroen Kimmel SID -> editable Driver 11 SF2 (Stage A, cut 1).

Maps the decoded Kimmel event streams (sidm2/kimmel_parser.py) onto Driver 11:
one Kimmel note-tick = one Driver-11 row, pitch = the tune's own split freq
table resolved to the PAL semitone grid, AD/SR/waveform/pulse-width taken from
the located 8-byte instrument records (unlike SDI cut-1, Kimmel's instruments
ARE located, so no default-timbre fallback is needed).

Cut-1 approximations (all logged, none silent):
  - the per-frame effects engine ($12CC: arpeggio, freq slide, pulse-width
    sweep, octave/waveform toggles, drum blips) is NOT ported — Stage A emits
    the base note/instrument only (Stage B material),
  - every note re-gates (the runtime Driver 11 has no ties — the Sound Monitor
    lesson); Kimmel's note stream has no explicit tie/rest byte anyway,
  - only subtune 0 is decoded (Radax has 6).

Usage:  py -3 bin/kimmel_to_sf2.py SID/Red_kommel_jeroen/Think_Twice_V.sid [out.sf2]
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.kimmel_parser import KimmelModule
from sidm2.fidelity_common import freq_to_semi
from sidm2.galway_to_driver11 import (
    D11Instrument, D11Row, GalwayDriver11Song,
    SF2_NOTE_MIN, SF2_NOTE_MAX, SF2_GATE_ON, SF2_GATE_OFF,
    _pulse_program,
)
from sidm2.galway_driver11_emitter import emit_driver11_sf2, segment_track

MAX_INSTRUMENTS = 31


def build_instruments(m, used):
    """One Driver-11 slot per used Kimmel instrument (usage-ranked, capped).
    ADSR/waveform/pulse-width come from the located 8-byte record."""
    instr_rows, wave_table, pulse_table = [], [], []
    slot_of = {}
    for idx, _n in used.most_common():
        if len(instr_rows) >= MAX_INSTRUMENTS:
            slot_of[idx] = 0
            continue
        ins = m.instrument(idx)
        wave = ins["wave"] or 0x41            # base waveform+gate
        wrow = len(wave_table)
        wave_table.append((wave, 0x00))       # play waveform ...
        wave_table.append((0x7F, wrow))       # ... then hold (jump to self)
        width = (ins["pwhi"] & 0x0F) << 8
        prow = len(pulse_table)
        pulse_table.extend(_pulse_program(width or 0x800, prow))
        slot_of[idx] = len(instr_rows)
        instr_rows.append(D11Instrument(
            ad=ins["ad"], sr=ins["sr"] if ins["sr"] else 0xF9,
            flags=0x80, filter_idx=0x00,
            pulse_idx=prow, wave_idx=wrow, pulse_width=(width >> 8) or 0x08))
    return instr_rows, wave_table, pulse_table, slot_of


def _append_silent_instrument(instr_rows, wave_table):
    wrow = len(wave_table)
    wave_table.append((0x00, 0x00))
    wave_table.append((0x7F, wrow))
    idx = len(instr_rows)
    instr_rows.append(D11Instrument(ad=0, sr=0, flags=0x80, filter_idx=0,
                                    pulse_idx=0, wave_idx=wrow, pulse_width=0))
    return idx


_MAX_REST_RUN = 64


def build_rows(m, ev, slot_of, silent_idx):
    """Event streams (tick-domain) -> per-voice Driver-11 rows."""
    all_rows = []
    for v in range(3):
        rows, cur, rest_run, tick = [], None, 0, 0
        for e in ev[v]:
            etick = e.frame // max(1, m.fpt)
            while tick < etick:                       # decode gaps -> rests
                rows.append(D11Row(note=SF2_GATE_OFF))
                tick += 1
            dur = max(1, e.dur_ticks)
            semi = freq_to_semi(m.note_freq(e.note))
            n = max(SF2_NOTE_MIN, min(semi, SF2_NOTE_MAX))
            slot = slot_of.get(e.instr, 0)
            inst = slot if slot != cur else None
            cur = slot if inst is not None else cur
            rows.append(D11Row(note=n, instrument=inst))
            rows.extend(D11Row(note=SF2_GATE_ON) for _ in range(dur - 1))
            tick += dur
            rest_run = 0
        if rows and all(r.note == SF2_GATE_OFF for r in rows):
            rows[-1] = D11Row(note=1, instrument=silent_idx)
        all_rows.append(rows)
    return all_rows


def convert(path, out, subtune=0):
    m = KimmelModule(path, subtune=subtune)
    ev = m.events()
    used = Counter(e.instr for v in range(3) for e in ev[v])
    instr_rows, wave_table, pulse_table, slot_of = build_instruments(m, used)
    silent_idx = _append_silent_instrument(instr_rows, wave_table)
    all_rows = build_rows(m, ev, slot_of, silent_idx)

    sequences, orderlists = [], [[], [], []]
    seq_index = {}
    for v in range(3):
        for pk in segment_track(all_rows[v]):
            idx = seq_index.get(pk)
            if idx is None:
                idx = len(sequences)
                seq_index[pk] = idx
                sequences.append(pk)
            orderlists[v].append(idx)
    tempo = max(0, m.fpt - 1)
    song = GalwayDriver11Song(
        instruments=instr_rows, wave_table=wave_table,
        pulse_table=pulse_table, tracks=[], tempo=tempo, pitch_base=0,
        subtune=0)
    print(f"load=${m.la:04X} fpt={m.fpt} instr_base=${m.instr_base:04X} "
          f"instruments={len(instr_rows)} sequences={len(sequences)} "
          f"events={[len(e) for e in ev]}")
    sf2 = emit_driver11_sf2(song, sequences=sequences, orderlists=orderlists)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    open(out, 'wb').write(sf2)
    print(f"emitted {len(sf2)} bytes -> {out}")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    subtune = 0
    if "--subtune" in sys.argv:
        i = sys.argv.index("--subtune")
        subtune = int(sys.argv[i + 1])
        del sys.argv[i:i + 2]
    path = sys.argv[1]
    base = os.path.splitext(os.path.basename(path))[0]
    if subtune:
        base += f"_sub{subtune}"
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        'out', 'kimmel_sf2', base + '.sf2')
    return convert(path, out, subtune=subtune)


if __name__ == '__main__':
    sys.exit(main())
