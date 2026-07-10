"""Sound Monitor (Huelsbeck) SID -> editable Driver 11 SF2 (Stage A), like
bin/romuzak_to_sf2.py.

Sound Monitor maps onto Driver 11 unusually directly:
  - one SM step = one Driver-11 row (notes sustain via TIE steps, rest = gate off),
  - SM note index = SF2 chromatic semitone (validated corpus-wide, base 0),
  - row speed s = s+1 frames/step -> Driver-11 tempo = s (speed is 2 on the whole
    cluster except Dreamix's few speed-3 rows -> dominant speed, logged),
  - the per-note ARPEGGIO (data&$40; 8 semitone offsets cycled per frame from the
    row-header chord bank) = a Driver-11 wave-table program (wf, offset) x8 + loop.

Per-note arps mean one SM instrument plays both plain and arpeggiated, so each
(sound record, arp table) COMBO becomes a Driver-11 instrument. Driver 11 has 32
slots; combos are kept by usage and dropped combos fall back to the same record's
plain combo (arp loss is LOGGED loudly, never silent -- only Dance_at_Night_remix
exceeds the cap today, 51 combos).

Not yet modeled (Stage A first cut): glide/portamento (plays the target note),
pulse width + vibrato/bend sound-record fields (default $800 pulse program),
per-row speed changes, the volume-fade row field.

Usage:  py -3 bin/soundmonitor_to_sf2.py SID/Fun_Fun/Dreamix.sid [out.sf2]
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.soundmonitor_parser import load_sid, is_soundmonitor, SoundMonitorModule
from sidm2.galway_to_driver11 import (
    D11Instrument, D11Row, GalwayDriver11Song,
    SF2_NOTE_MIN, SF2_NOTE_MAX, SF2_GATE_ON, SF2_GATE_OFF,
    _norm_waveform, _pulse_program,
)
from sidm2.galway_driver11_emitter import emit_driver11_sf2, segment_track

MAX_INSTRUMENTS = 31          # 32 slots minus the silent-anchor instrument


def collect_combos(m):
    """-> (events, Counter{(instr, arp): uses}). arp is the 8-tuple or None."""
    ev = m.events()
    uses = Counter()
    for v in range(3):
        for e in ev[v]:
            if e[2] in ('note', 'legato'):
                uses[(e[4], e[5])] += 1
    return ev, uses


def assign_instruments(m, uses):
    """Rank (instr, arp) combos by usage into <= MAX_INSTRUMENTS Driver-11 slots,
    dedup by CONTENT (sound record bytes + arp). Dropped combos fall back to the
    same record's plain combo. -> (combo_map {(instr,arp): slot}, slot_defs
    [(record_bytes, arp)], n_dropped_arp_notes)."""
    content_slot = {}
    slot_defs = []
    combo_map = {}
    dropped = 0
    for (instr, arp), n in uses.most_common():
        rec = m.sound(instr)
        key = (rec, arp)
        if key in content_slot:
            combo_map[(instr, arp)] = content_slot[key]
            continue
        if len(slot_defs) < MAX_INSTRUMENTS:
            slot = len(slot_defs)
            content_slot[key] = slot
            slot_defs.append((rec, arp))
            combo_map[(instr, arp)] = slot
        else:
            # over the cap: fall back to this record's plain (no-arp) combo
            dropped += n
            plain = (rec, None)
            if plain not in content_slot:
                if len(slot_defs) < MAX_INSTRUMENTS:
                    content_slot[plain] = len(slot_defs)
                    slot_defs.append(plain)
                else:
                    # find any slot with the same record, else same waveform, else 0
                    slot = next((s for s, (r, _) in enumerate(slot_defs) if r == rec),
                                next((s for s, (r, _) in enumerate(slot_defs)
                                      if r[0] == rec[0]), 0))
                    combo_map[(instr, arp)] = slot
                    continue
            combo_map[(instr, arp)] = content_slot[plain]
    return combo_map, slot_defs, dropped


def build_instruments(slot_defs):
    """slot defs -> Driver-11 instrument rows + shared wave/pulse tables.
    Wave programs are dedup'd by content (many combos share e.g. the octave arp)."""
    instr_rows, wave_table, pulse_table = [], [], []
    wave_progs = {}
    pulse_progs = {}

    def wave_program(wf, arp):
        key = (wf, arp)
        if key in wave_progs:
            return wave_progs[key]
        row = len(wave_table)
        if arp is None:
            wave_table.append((wf, 0x00))
            wave_table.append((0x7F, row))
        else:
            for off in arp:
                # relative semitone offset column; clamp garbage (the arp-base-0
                # rows) into the 0-95 note space rather than emitting junk
                wave_table.append((wf, min(off, 95) & 0x7F))
            wave_table.append((0x7F, row))
        wave_progs[key] = row
        return row

    def pulse_program(pw):
        if pw in pulse_progs:
            return pulse_progs[pw]
        row = len(pulse_table)
        pulse_table.extend(_pulse_program(pw, row))
        pulse_progs[pw] = row
        return row

    for rec, arp in slot_defs:
        wf = _norm_waveform(rec[0])
        wave_row = wave_program(wf, arp)
        pulse_row = pulse_program(0x800)      # PW field not yet decoded (TODO)
        instr_rows.append(D11Instrument(
            ad=rec[1], sr=rec[2], flags=0x80, filter_idx=0x00,
            pulse_idx=pulse_row, wave_idx=wave_row, pulse_width=0x08))
    return instr_rows, wave_table, pulse_table


def _append_silent_instrument(instr_rows, wave_table):
    wrow = len(wave_table)
    wave_table.append((0x00, 0x00))
    wave_table.append((0x7F, wrow))
    idx = len(instr_rows)
    instr_rows.append(D11Instrument(ad=0, sr=0, flags=0x80, filter_idx=0,
                                    pulse_idx=0, wave_idx=wrow, pulse_width=0))
    return idx


_MAX_REST_RUN = 64


def _bar_rows(bar_events, combo_map, rest_gate, silent_idx, state):
    """One voice-row's step events -> Driver-11 rows (1 step = 1 row).

    GATE SEMANTICS: a REST writes the current instrument's byte-8 "release
    waveform" to the WF register ($C633) -- for most instruments that is
    gate-off, but some carry a GATED release waveform ($11/$81...) so their
    rests keep the voice ringing (a waveform switch we approximate as
    sustain). A note only restarts the envelope when the gate is actually
    off; a legato pitch change re-gates in Stage A (see the tie note below).

    state = [gated, last_instr] carried across rows (bars re-used with a
    different entry state dedup as distinct sequences via their differing
    tie/gate rows, which is correct). cur (slot dedup) is per-bar so each
    sequence sets its own instrument."""
    out = []
    cur = None
    rest_run = 0
    gated, last_instr = state
    for kind, note, instr, arp in bar_events:
        if kind == 'rest':
            if gated and last_instr is not None and rest_gate.get(last_instr):
                out.append(D11Row(note=SF2_GATE_ON))   # gated release wf: keeps ringing
                continue
            gated = False
            if rest_run >= _MAX_REST_RUN:
                out.append(D11Row(note=1, instrument=silent_idx))
                cur = silent_idx
                rest_run = 0
            else:
                out.append(D11Row(note=SF2_GATE_OFF))
                rest_run += 1
            continue
        if kind == 'tie':
            out.append(D11Row(note=SF2_GATE_ON if gated else SF2_GATE_OFF))
            continue
        rest_run = 0
        slot = combo_map[(instr, arp)]
        n = max(SF2_NOTE_MIN, min(note, SF2_NOTE_MAX))
        # NO tie marks: the $90-$9F tie duration bytes are an EDITOR feature
        # (datasource_sequence.cpp) that the runtime Driver 11 player does NOT
        # parse -- emitting them desyncs its sequence reader into garbage
        # (wrong pitches/noise, found empirically on Dreamix osc3). Legato
        # notes therefore re-gate in Stage A; exact legato is a Stage B
        # (native driver) item.
        inst = None
        if slot != cur:
            inst = slot
            cur = slot
        out.append(D11Row(note=n, instrument=inst))
        gated = True
        last_instr = instr
    if out and all(r.note == SF2_GATE_OFF for r in out):
        out[-1] = D11Row(note=1, instrument=silent_idx)
    state[0], state[1] = gated, last_instr
    return out


def build_structured(m, ev, combo_map, silent_idx):
    """One (deduplicated) Driver-11 sequence per voice-row bar + per-voice
    orderlists -- the editor shows the song's real row structure."""
    seq_index = {}
    sequences = []
    orderlists = [[], [], []]
    # per-instrument gated-release flag (sound record byte 8, the rest wf)
    rest_gate = {}
    for v in range(3):
        for e in ev[v]:
            if e[2] in ('note', 'legato') and e[4] not in rest_gate:
                rest_gate[e[4]] = bool(m.sound(e[4])[8] & 0x01)
    # regroup the flat event stream by (voice, row)
    by_row = {v: {} for v in range(3)}
    for v in range(3):
        for row, step, kind, note, instr, arp, glide in ev[v]:
            by_row[v].setdefault(row, []).append((kind, note, instr, arp))
    for v in range(3):
        state = [False, None]
        for row, _ in m.row_chain():
            rows = _bar_rows(by_row[v].get(row, []), combo_map, rest_gate,
                             silent_idx, state)
            for pk in segment_track(rows):
                idx = seq_index.get(pk)
                if idx is None:
                    idx = len(sequences)
                    seq_index[pk] = idx
                    sequences.append(pk)
                orderlists[v].append(idx)
    return sequences, orderlists


def find_tempo(m):
    """Dominant row speed -> Driver-11 tempo (speed s = s+1 frames/step, tempo t =
    t+1 frames/row). Logged when rows disagree (Dreamix has a few speed-3 rows)."""
    speeds = Counter(hdr['speed'] for _, hdr in m.row_chain())
    tempo = speeds.most_common(1)[0][0]
    if len(speeds) > 1:
        print(f"WARN: mixed row speeds {dict(speeds)} -> using dominant {tempo} "
              f"(per-row tempo not yet emitted)")
    return tempo


def convert(path, out):
    d, la, h = load_sid(path)
    if not is_soundmonitor(d, la, h):
        print(f"not a Sound Monitor rip: {path}")
        return 1
    m = SoundMonitorModule(d, la)
    ev, uses = collect_combos(m)
    combo_map, slot_defs, dropped = assign_instruments(m, uses)
    if dropped:
        total = sum(uses.values())
        print(f"WARN: instrument cap -- {dropped}/{total} notes lost their arp "
              f"(fell back to the plain timbre); {len(uses)} combos > "
              f"{MAX_INSTRUMENTS} slots")
    instr_rows, wave_table, pulse_table = build_instruments(slot_defs)
    silent_idx = _append_silent_instrument(instr_rows, wave_table)
    sequences, orderlists = build_structured(m, ev, combo_map, silent_idx)
    tempo = find_tempo(m)
    song = GalwayDriver11Song(
        instruments=instr_rows, wave_table=wave_table, pulse_table=pulse_table,
        tracks=[], tempo=tempo, pitch_base=0, subtune=0)
    print(f"load=${la:04X} rows={len(m.row_chain())} tempo={tempo} "
          f"instruments={len(instr_rows)} wave_rows={len(wave_table)} "
          f"sequences={len(sequences)}")
    sf2 = emit_driver11_sf2(song, sequences=sequences, orderlists=orderlists)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    open(out, 'wb').write(sf2)
    print(f"emitted {len(sf2)} bytes -> {out}")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        'out', os.path.splitext(os.path.basename(path))[0] + '.sf2')
    return convert(path, out)


if __name__ == '__main__':
    sys.exit(main())
