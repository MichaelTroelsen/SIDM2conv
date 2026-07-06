"""Rob Hubbard v1 SID -> editable Driver 11 SF2 (Stage A).

Decodes the Hubbard v1 player (sidm2/hubbard_parser.py — onset-validated ~100%
on the 11-tune v1 set) and transpiles it onto a real Driver 11 SF2 via the
shared Galway/ROMUZAK/MoN IR + emitter. Hubbard's structure maps 1:1 onto the
SF2 model: track = orderlist of patterns, pattern = note+duration rows,
8-byte instrument records -> Driver 11 instruments. Appended notes (ties)
become GATE_ON sustain rows. Portamento/vibrato/drum/skydive/octarp timbre is
Stage-B polish (native driver), not emitted here.

Usage:  py -3 bin/hubbard_to_sf2.py SID/Hubbard_Rob/Monty_on_the_Run.sid [out.sf2] [song]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.hubbard_parser import HubbardModule, decode_pattern, load_sid
from sidm2.fidelity_common import freq_to_semi
from sidm2.galway_to_driver11 import (
    D11Instrument, D11Row, GalwayDriver11Song,
    SF2_NOTE_MIN, SF2_NOTE_MAX, SF2_GATE_ON,
    _norm_waveform, _pulse_program,
)
from sidm2.galway_driver11_emitter import emit_driver11_sf2, segment_track


def used_instruments(m, song=0):
    """Instrument indices referenced by this song's notes (sorted)."""
    used = set()
    for v in range(3):
        pats, _ = m.track_patterns(song, v)
        for p in set(pats):
            for n in decode_pattern(m, p):
                if n.instr >= 0:
                    used.add(n.instr)
    return sorted(used) or [0]


def build_instruments(m, used):
    """One Driver 11 instrument per used Hubbard instrument (8-byte record:
    PW lo/hi, ctrl, AD, SR, vibdepth, pulsespeed, fx)."""
    instr_rows, wave_table, pulse_table, idx_map = [], [], [], {}
    for hub_idx in used:
        ins = m.instrument(hub_idx)
        idx_map[hub_idx] = len(instr_rows)
        wf = _norm_waveform(ins["ctrl"])
        wave_row = len(wave_table)
        wave_table.append((wf, 0x00))              # hold the note's pitch
        wave_table.append((0x7F, wave_row))        # loop
        pw = (ins["pwlo"] | (ins["pwhi"] << 8)) & 0x0FFF
        pulse_row = len(pulse_table)
        pulse_table.extend(_pulse_program(pw or 0x800, pulse_row))
        instr_rows.append(D11Instrument(
            ad=ins["ad"], sr=ins["sr"], flags=0x80, filter_idx=0x00,
            pulse_idx=pulse_row, wave_idx=wave_row,
            pulse_width=(pw >> 8) & 0x0F))
    return instr_rows, wave_table, pulse_table, idx_map


def _semi_mapper(m, path=None, song=0):
    """pitch -> standard semitone via the module's OWN freq lookup. Identity
    for in-range pitches. OUT-OF-RANGE pitches (drum notes past the 96-entry
    table — Commando's drums use pitch 104) read the PLAYER'S RUNTIME STATE
    (statically zero / garbage), so they are resolved TRACE-INFORMED: sample
    the original's freq register at that pitch's first onset frame."""
    k = freq_to_semi(m.note_freq(48)) - 48       # tuning offset, one probe
    runtime = {}
    if path is not None:
        # each unresolvable pitch's first onset PER VOICE (the runtime value
        # is live player state — the same pitch resolves differently on
        # different voices)
        from sidm2.hubbard_parser import decode_song
        voices, _ = decode_song(m, song)
        fpt = m.frames_per_tick
        need = {}
        for v in range(3):
            for tk, n in voices[v]:
                if (not n.append and n.pitch >= 0 and m.note_freq(n.pitch) == 0
                        and (v, n.pitch) not in need):
                    need[(v, n.pitch)] = tk * fpt
        if need:
            # resolve from the original's ONSET NAMES (same frame origin as
            # the validator; siddump names the sounding pitch at each gate-on)
            from sidm2.fidelity_common import siddump_note_onsets
            names = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#',
                     'A-', 'A#', 'B-']
            maxf = max(need.values()) + 8
            real = siddump_note_onsets(path, [f'-a{song}', f'-t{maxf // 50 + 2}'])
            for (v, p), fr in need.items():
                rl = real[v] if isinstance(real, (list, tuple)) else real.get(v, [])
                # +-8: drum gate-ons can register several frames late (the
                # drum's own frame-1 write is gate-OFF ctrl)
                cand = [(abs(f - fr), nm) for f, nm in rl if abs(f - fr) <= 8]
                if cand:
                    nm = min(cand)[1]
                    try:
                        runtime[(v, p)] = names.index(nm[:2]) + 12 * int(nm[2:])
                    except (ValueError, IndexError):
                        pass

    def semi(pitch, voice=0):
        f = m.note_freq(pitch)
        if f == 0:
            return runtime.get((voice, pitch), SF2_NOTE_MIN)
        return freq_to_semi(f) - k
    return semi


def pattern_rows(m, pat, idx_map, semi, voice=0):
    """One Hubbard pattern -> Driver 11 rows. A note = 1 row + (ticks-1)
    GATE_ON rows; an APPEND (tie) = ticks more GATE_ON rows (no re-gate,
    pitch continues — faithful to the append semantics). Instrument set only
    on notes that carry one (instrnr persists across patterns in the real
    player, and D11's 'last active instrument' matches that carry-over)."""
    out = []
    for n in decode_pattern(m, pat):
        if n.append:
            out.extend(D11Row(note=SF2_GATE_ON) for _ in range(n.ticks))
            continue
        note = max(SF2_NOTE_MIN, min(semi(n.pitch, voice), SF2_NOTE_MAX))
        inst = idx_map.get(n.instr) if n.instr >= 0 else None
        out.append(D11Row(note=note, instrument=inst))
        out.extend(D11Row(note=SF2_GATE_ON) for _ in range(n.ticks - 1))
    return out


def build_structured(m, song, idx_map, path=None):
    """Per-pattern deduplicated sequences + per-voice orderlists — Hubbard's
    track/pattern hierarchy maps 1:1 onto the SF2 orderlist/sequence model."""
    seq_index, sequences = {}, []
    orderlists = [[], [], []]
    semi = _semi_mapper(m, path, song)
    for v in range(3):
        pats, _loops = m.track_patterns(song, v)
        for p in pats:
            rows = pattern_rows(m, p, idx_map, semi, v)
            for pk in segment_track(rows):
                idx = seq_index.get(pk)
                if idx is None:
                    idx = len(sequences)
                    seq_index[pk] = idx
                    sequences.append(pk)
                orderlists[v].append(idx)
    return sequences, orderlists


def convert(path, out=None, song=0):
    d, la, _ = load_sid(path)
    m = HubbardModule(d, la)
    used = used_instruments(m, song)
    instr_rows, wave_table, pulse_table, idx_map = build_instruments(m, used)
    sequences, orderlists = build_structured(m, song, idx_map, path)
    tempo = m.resetspd                       # tempo+1 frames/row == resetspd+1
    sf2song = GalwayDriver11Song(
        instruments=instr_rows, wave_table=wave_table, pulse_table=pulse_table,
        tracks=[], tempo=tempo, pitch_base=0, subtune=song)
    print(f"{os.path.basename(path)} song{song}: load=${la:04X} fpt={m.frames_per_tick} "
          f"sequences={len(sequences)} instruments={len(instr_rows)} "
          f"orderlists={[len(o) for o in orderlists]}")
    sf2 = emit_driver11_sf2(sf2song, sequences=sequences, orderlists=orderlists)
    out = out or os.path.join('out', os.path.splitext(os.path.basename(path))[0] + '.sf2')
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    open(out, 'wb').write(sf2)
    print(f"emitted {len(sf2)} bytes -> {out}")
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    song = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    convert(path, out, song)
    return 0


if __name__ == '__main__':
    sys.exit(main())
