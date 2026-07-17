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
import math
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
from sidm2.galway_driver11_emitter import (
    _MAX_SEQUENCES, emit_driver11_sf2, segment_track)


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
            s = freq_to_semi((val << 8) | val)
            # A raw byte whose freq is sub-audio (b<<8|b < 8, i.e. b==0) is a
            # SILENT frame in the real engine -- it writes freq 0 to the SID. An
            # absolute-note row can't say "silence" (note 0 is a real low pitch),
            # so emit a waveform-off row instead. Astro instr 8 opens on two of
            # these; without this the SF2 skips the gap and the sweep starts a
            # frame early (caught by deenen_sf2_validate: was 0/207, then 100%).
            row = (0x00, 0x00) if s < 0 else (wf, 0x80 | min(95, s))
        elif val >= 0x7F:                                # absolute note
            row = (wf, 0x80 | max(0, min(95, val & 0x7F)))
        else:                                            # relative semitone
            row = (wf, val & 0x7F)
        for _ in range(wp['speed']):                     # frames per step
            rows.append(row)
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
    rest = (frames) GATE_OFF rows.

    ONE playthrough (`stop_on_loop=True`), because the emitted orderlist already
    ends in `FF 00` = loop-to-start: emitting the decoder's default 8000-event
    stream re-emitted the same song a dozen times over as *literal* rows. That
    was not merely wasteful -- it was SILENTLY LOSSY. It inflated these tracks to
    30k-150k rows and 200-330 distinct sequences, and the emitter's pointer table
    holds only `_MAX_SEQUENCES` = 128, past which it drops orderlist entries
    without a word. Voice 2 is packed last, so voice 2 lost EVERY entry it had:
    Constant_Runner 68/68, Zamzara 107/107, After_the_War 87/87, Astro 80/80
    dropped -- an entire voice missing from the SF2 -- and Lord_of_the_Rings lost
    voices 1 AND 2. One playthrough puts every located file under 52 sequences
    with zero drops; `main()` still checks `dropped_orderlist()` and refuses
    loudly if any future file overflows anyway.
    """
    out = []
    cur = None
    for e in m.decode_voice(v, stop_on_loop=True):
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


def tempo_chain(m):
    """Driver 11 tempo row(s) for this file's own groove clock.

    The Deenen note-duration counter advances only ~2 of every 5 frames, so one
    decoded tick (= one emitted row) is `m.groove_rate()` REAL frames -- and the
    rate is per-file (measured: Astro/LotR 2.0, Ding/After_the_War 2.5, B_A_T/
    Constant_Runner/Zamzara 3.0). Driver 11 plays `value + 1` frames per row
    (MEASURED against siddump, off by one from SF2_FORMAT_SPEC.md's "value =
    frames per row" -- see GalwayDriver11Song.tempo), so value = R - 1.

    This builder previously hardcoded `tempo=1` = 2 frames/row, which is right
    only for the R=2.0 files: Constant_Runner and B_A_T were shipping SF2s that
    played 1.5x too fast. Verified by rebuilding at R-1 and diffing real onset
    deltas against the original SID -- Constant_Runner voice1 goes from
    [12,12,8,4,8,4,12] to [18,18,12,6,12,6,18], which is the original exactly.

    A fractional rate can't be one integer, so alternate the two neighbours: the
    format averages a chain ("02 03 7F 00"), and 2.5 -> [1,2] = 2,3 frames/row.
    Falls back to the historical [1] when the rate is unmeasurable (0.0 on the
    files py65 can't drive, e.g. Mantalos/Eye_to_Eye) -- those are refused by
    plausible() anyway, and 0 is the chain terminator, never a legal value.
    """
    r = m.groove_rate()
    if not r or r < 2:
        return [1]
    lo, hi = math.floor(r), math.ceil(r)
    return [lo - 1] if lo == hi else [lo - 1, hi - 1]


def build_song(m, subtune=0):
    """The exact SF2 payload the builder ships: (song, sequences, orderlists).

    Shared with bin/deenen_sf2_validate.py ON PURPOSE. That validator re-built
    the song with its own copy of this assembly, so it could only ever audit an
    SF2 that happened to match the one we ship; any drift and it would certify a
    file no user ever gets. One source of truth instead.
    """
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
        tracks=[], tempo=tempo_chain(m), pitch_base=0, subtune=subtune)
    return song, sequences, orderlists, idx_map


def dropped_orderlist(sequences, orderlists):
    """Per-voice count of orderlist entries emit_driver11_sf2 will SILENTLY drop.

    The emitter keeps only `sequences[:_MAX_SEQUENCES]` and filters every
    orderlist entry at or past that index -- no exception, no warning, and the
    build still prints a byte count and exits 0. Whole voices vanished this way
    for four of the six clean wins. Never let that go out unannounced.
    """
    return [sum(1 for s in orderlists[v] if s >= _MAX_SEQUENCES) for v in range(3)]


def main():
    # Positional args, minus flags -- so `--force` can appear anywhere without
    # being mistaken for the out-path or parsed as the subtune (int('--force')).
    force = '--force' in sys.argv
    pos = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not pos:
        print(__doc__)
        return 1
    path = pos[0]
    out = pos[1] if len(pos) > 1 else os.path.join(
        'out', 'deenen_sf2', os.path.splitext(os.path.basename(path))[0] + '.sf2')
    subtune = int(pos[2]) if len(pos) > 2 else 0

    d, la, h = load_sid(path)
    m = DeenenModule(d, la, subtune, h)
    if not m.loc.ok():
        print(f"deenen locate FAILED ({m.loc.summary()}) for {path}")
        return 1
    if not m.plausible() and not force:
        print(f"deenen decode IMPLAUSIBLE (degenerate/filler) for {path}; "
              f"refusing to build garbage. Pass --force to override.")
        return 1

    song, sequences, orderlists, idx_map = build_song(m, subtune)
    drop = dropped_orderlist(sequences, orderlists)
    if any(drop):
        print(f"deenen SEQUENCE CAP EXCEEDED for {path}: {len(sequences)} sequences "
              f"> {_MAX_SEQUENCES}; the emitter would DROP orderlist entries "
              f"{drop} of {[len(o) for o in orderlists]} (per voice) -- a voice "
              f"with all entries dropped is SILENT in the SF2. Refusing to emit "
              f"a song that is missing part of itself. Pass --force to override.")
        if not force:
            return 1

    print(f"load=${la:04X} {m.loc.summary()} instruments={len(song.instruments)} "
          f"sequences={len(sequences)} tempo={song.tempo} (R={m.groove_rate()}) "
          f"notes/voice={[sum(1 for e in m.decode_voice(v, stop_on_loop=True) if e['kind']=='note') for v in range(3)]}")
    sf2 = emit_driver11_sf2(song, sequences=sequences, orderlists=orderlists)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    open(out, 'wb').write(sf2)
    print(f"emitted {len(sf2)} bytes -> {out}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
