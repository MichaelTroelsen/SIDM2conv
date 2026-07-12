"""SID Duzz' It (SDI, Gallefoss/Tjelta) SID -> editable Driver 11 SF2
(Stage A, cut 1), like bin/soundmonitor_to_sf2.py.

Maps the decoded SDI event streams (sidm2/sdi_parser.py — variants A-E)
onto Driver 11: one SDI tick = one Driver-11 row, pitch = the song's own
freq-table value resolved to the PAL semitone grid, AD/SR from the located
instrument tables where the variant provides them (A: column-major;
B: interleaved records). Cut-1 approximations (all logged, none silent):
  - ties/legato re-gate (the runtime Driver 11 cannot parse tie bytes —
    the Sound Monitor lesson; exact legato = Stage B),
  - glide plays the target note,
  - timbre defaults to $41 pulse wave + $800 pulse width where the
    variant's instrument tables are not yet located (C/D/E),
  - E tempo = the extracted tempo program's dominant tick.

Usage:  py -3 bin/sdi_to_sf2.py SID/Gallefoss_Glenn/30seconds.sid [out.sf2]
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.sdi_parser import load_sid, locate, SDIModule
from sidm2.fidelity_common import freq_to_semi
from sidm2.galway_to_driver11 import (
    D11Instrument, D11Row, GalwayDriver11Song,
    SF2_NOTE_MIN, SF2_NOTE_MAX, SF2_GATE_ON, SF2_GATE_OFF,
    _pulse_program,
)
from sidm2.galway_driver11_emitter import emit_driver11_sf2, segment_track

MAX_INSTRUMENTS = 31


def instrument_adsr(m, idx):
    """(ad, sr) from the located tables, or a safe default (logged by the
    caller when defaults are in play)."""
    lay = m.lay
    d, la = m.d, m.la
    if lay.variant == 'A' and lay.ad_col and lay.stride:
        k = idx % max(1, lay.stride)
        return d[lay.ad_col - la + k], d[lay.sr_col - la + k]
    if lay.variant == 'B' and lay.ad_col and lay.stride == 8:
        base = lay.ad_col - la + (idx & 0x1F) * 8
        if 0 <= base + 1 < len(d):
            return d[base], d[base + 1]
    return 0x09, 0x00


def build_instruments(m, used):
    """One Driver-11 slot per used SDI instrument (usage-ranked, capped)."""
    instr_rows, wave_table, pulse_table = [], [], []
    slot_of = {}
    defaults = 0
    wrow0 = len(wave_table)
    wave_table.append((0x41, 0x00))
    wave_table.append((0x7F, wrow0))
    prow0 = len(pulse_table)
    pulse_table.extend(_pulse_program(0x800, prow0))
    for idx, _n in used.most_common():
        if len(instr_rows) >= MAX_INSTRUMENTS:
            slot_of[idx] = 0
            continue
        ad, sr = instrument_adsr(m, idx)
        if (ad, sr) == (0x09, 0x00) and m.lay.variant not in ('A', 'B'):
            defaults += 1
        slot_of[idx] = len(instr_rows)
        instr_rows.append(D11Instrument(
            ad=ad, sr=sr if sr else 0xF9, flags=0x80, filter_idx=0x00,
            pulse_idx=prow0, wave_idx=wrow0, pulse_width=0x08))
    return instr_rows, wave_table, pulse_table, slot_of, defaults


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
        rows = []
        cur = None
        rest_run = 0
        tick = 0
        for e in ev[v]:
            etick = e.frame // max(1, m.fpt)
            while tick < etick:                      # decode gaps -> rests
                rows.append(D11Row(note=SF2_GATE_OFF))
                tick += 1
            dur = max(1, e.dur_ticks)
            if e.kind in ('rest', 'off'):
                for _ in range(dur):
                    if rest_run >= _MAX_REST_RUN:
                        rows.append(D11Row(note=1, instrument=silent_idx))
                        cur = silent_idx
                        rest_run = 0
                    else:
                        rows.append(D11Row(note=SF2_GATE_OFF))
                        rest_run += 1
                tick += dur
                continue
            rest_run = 0
            semi = freq_to_semi(m.note_freq(e.note)) if e.note is not None else 1
            n = max(SF2_NOTE_MIN, min(semi, SF2_NOTE_MAX))
            slot = slot_of.get(e.instr, 0)
            inst = slot if slot != cur else None
            cur = slot if inst is not None else cur
            # ties/glides re-gate in Stage A (runtime Driver 11 has no ties)
            rows.append(D11Row(note=n, instrument=inst))
            rows.extend(D11Row(note=SF2_GATE_ON) for _ in range(dur - 1))
            tick += dur
        if rows and all(r.note == SF2_GATE_OFF for r in rows):
            rows[-1] = D11Row(note=1, instrument=silent_idx)
        all_rows.append(rows)
    return all_rows


def convert(path, out, c_pitch_model=None):
    d, la, h = load_sid(path)
    lay = locate(d, la)
    if lay is None:
        print(f"not a located SDI rip: {path}")
        return 1
    m = SDIModule(d, la)
    if c_pitch_model:                # C walk-restart model ('onset' is
        m.c_pitch_model = c_pitch_model   # the default; 'steady' for
    ev = m.events()                  # free-running tie-drum files)
    used = Counter(e.instr for v in range(3) for e in ev[v]
                   if e.kind in ('note', 'tie', 'glide'))
    instr_rows, wave_table, pulse_table, slot_of, defaults = \
        build_instruments(m, used)
    silent_idx = _append_silent_instrument(instr_rows, wave_table)
    if defaults:
        print(f"WARN: {defaults} instruments use DEFAULT timbre/ADSR "
              f"(variant {lay.variant} instrument tables not yet located)")
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
    print(f"variant {lay.variant} load=${la:04X} fpt={m.fpt} "
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
    model = None
    if "--c-steady" in sys.argv:     # per-file calibrated via the sweep
        sys.argv.remove("--c-steady")
        model = "steady"
    path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        'out', 'sdi_sf2',
        os.path.splitext(os.path.basename(path))[0] + '.sf2')
    return convert(path, out, c_pitch_model=model)


if __name__ == '__main__':
    sys.exit(main())
