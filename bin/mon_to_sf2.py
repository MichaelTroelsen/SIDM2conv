"""Maniacs of Noise (Jeroen Tel / Hawkeye) SID -> editable Driver 11 SF2 (Stage A).

Decodes the MoN player (note/orderlist/pattern format + per-note instrument records,
fully RE'd — see the `hawkeye-mon-player-re` memory + sidm2/mon_parser.py) and transpiles
it onto a real Driver 11 SF2, reusing the Galway/ROMUZAK IR + emitter. The editor edits
the tables and Driver 11 plays them. Notes + frame timing + AD/SR/waveform/pulse are
byte-validated against siddump; the per-frame wave/pulse/arp modulation programs are
Stage-B polish (not emitted here).

Usage:  py -3 bin/mon_to_sf2.py SID/Tel_Jeroen/Hawkeye.sid [out.sf2] [subtune]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.mon_parser import load_sid, MON
from sidm2.galway_to_driver11 import (
    D11Instrument, D11Row, GalwayDriver11Song,
    SF2_NOTE_MIN, SF2_NOTE_MAX, SF2_GATE_ON,
    _norm_waveform, _pulse_program,
)
from sidm2.galway_driver11_emitter import emit_driver11_sf2, segment_track

N_INSTR = 32                                       # $90DA is masked & $1F -> 32 records


def build_instruments(m):
    """One Driver 11 instrument per MoN instrument index (0..31), from the $860C
    record (AD/SR/waveform/PW — byte-verified vs siddump). Held waveform + flat
    pulse program at the record's pulse width. D11 slot == MoN index, so a note's
    instr byte indexes directly."""
    instr_rows, wave_table, pulse_table = [], [], []
    for idx in range(N_INSTR):
        ins = m.instrument(idx)
        wf = _norm_waveform(ins['waveform'])
        wave_row = len(wave_table)
        wave_table.append((wf, 0x00))              # hold the note's pitch
        wave_table.append((0x7F, wave_row))        # loop
        pulse_row = len(pulse_table)
        pulse_table.extend(_pulse_program(ins['pw'] or 0x800, pulse_row))
        instr_rows.append(D11Instrument(
            ad=ins['ad'], sr=ins['sr'], flags=0x80, filter_idx=0x00,
            pulse_idx=pulse_row, wave_idx=wave_row,
            pulse_width=(ins['pw'] >> 8) & 0x0F))
    return instr_rows, wave_table, pulse_table


def block_rows(events, base):
    """One pattern block's MONEvents -> Driver 11 rows. cur=None per block so each
    sequence sets its own instrument on the first note (dedup-safe). A note = one
    row + (dur-1) GATE_ON sustain rows (dur is in ticks = SF2 rows)."""
    out = []
    cur = None
    for ev in events:
        n = max(SF2_NOTE_MIN, min(ev.note + base, SF2_NOTE_MAX))
        inst = None
        if ev.instr != cur:
            inst = ev.instr
            cur = ev.instr
        out.append(D11Row(note=n, instrument=inst))
        out.extend(D11Row(note=SF2_GATE_ON) for _ in range(max(0, ev.dur - 1)))
    return out


def build_structured(m, base):
    """One deduplicated Driver 11 sequence per pattern instance + a per-voice
    orderlist that replays them — so the editor shows the song's real patterns."""
    seq_index = {}
    sequences = []
    orderlists = [[], [], []]

    def add(rows, v):
        for pk in segment_track(rows):
            idx = seq_index.get(pk)
            if idx is None:
                idx = len(sequences)
                seq_index[pk] = idx
                sequences.append(pk)
            orderlists[v].append(idx)

    for v in range(3):
        for _pat, events in m._voice_blocks(v):
            add(block_rows(events, base), v)
    return sequences, orderlists


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        'out', os.path.splitext(os.path.basename(path))[0] + '.sf2')
    subtune = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    d, la, _ = load_sid(path)
    m = MON(d, la, subtune)
    base = 0                                        # MoN note byte == SF2 semitone ($00=C-0)
    tempo = m.speed                                 # tempo+1 frames/row == speed+1 frames/tick
    instr_rows, wave_table, pulse_table = build_instruments(m)
    sequences, orderlists = build_structured(m, base)
    song = GalwayDriver11Song(
        instruments=instr_rows, wave_table=wave_table, pulse_table=pulse_table,
        tracks=[], tempo=tempo, pitch_base=base, subtune=subtune)
    used = sorted({ev.instr for v in range(3) for ev in m.voices[v]})
    print(f"load=${la:04X} subtune={subtune} speed={m.speed} tempo={tempo} "
          f"blocks/voice={[len(m._voice_blocks(v)) for v in range(3)]} "
          f"sequences={len(sequences)} instruments_used={[hex(i) for i in used]}")
    sf2 = emit_driver11_sf2(song, sequences=sequences, orderlists=orderlists)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    open(out, 'wb').write(sf2)
    print(f"emitted {len(sf2)} bytes -> {out}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
