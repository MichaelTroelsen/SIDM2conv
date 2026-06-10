"""Trace-driven native-Galway-driver .sf2 — the faithful build.

Replaces the static-flattener song data (which invents phantom notes + mistimes
rests) with the REAL player's cycle-accurate output: per voice, every note gated
at its true onset row, carrying its real pitch envelope (the Galway slide/
vibrato) as an SF2-native WAVE-table program — RLE'd to (waveform, semitone,
hold-frames) rows with the settled tail looped, so a full-length song's
envelopes fit the 256-row table AND stay editor-visible/editable in SF2II.
Notes sharing a (waveform, envelope) shape share one instrument + program.

Usage:  py -3 bin/build_galway_trace_song.py [SID/Galway_Martin/Wizball.sid] [frames]
Verifies headless that the driver's per-frame note matches the emitted program
(exact) and reports how closely the program tracks the real trace.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))

import build_galway_native_song as N
import build_galway_driver_full as B
from sidm2.sid_parser import SIDParser
from sidm2 import galway_trace_extract as T
from sidm2.sid_player import FREQ_TABLE_LO, FREQ_TABLE_HI
from sidm2.galway_to_driver11 import D11Row, SF2_GATE_ON, SF2_GATE_OFF
from sidm2.galway_driver11_emitter import segment_track

TEMPO = 8        # frames per editor row (envelopes are per-frame regardless)
WAVE_BUDGET = 256


def freq_to_note(f):
    """Nearest note byte (1..96) to a SID frequency."""
    best, bd = 1, 1 << 30
    for i in range(96):
        tf = FREQ_TABLE_LO[i] | (FREQ_TABLE_HI[i] << 8)
        if abs(tf - f) < bd:
            bd, best = abs(tf - f), i + 1
    return best


def note_freq(note_byte):
    return FREQ_TABLE_LO[note_byte - 1] | (FREQ_TABLE_HI[note_byte - 1] << 8)


def semitone_envelope(note):
    """Per-frame signed semitone offset of the note's real pitch envelope,
    relative to the note's base note byte. The driver's wave_step applies col1 =
    semitone each frame, so this reproduces the Galway slide/vibrato in
    SF2II-native, editor-loaded, editable form (stepped to integer semitones)."""
    nb = freq_to_note(note.base_freq)
    recon = T.reconstruct_freq(note)                 # per-frame absolute freq
    return nb, [freq_to_note(f) - nb for f in recon[:max(1, note.end - note.onset)]]


def _best_loop_split(seq, maxp=128):
    """Split `seq` into (body, loop): Galway sustains settle into vibrato/
    arpeggio cycles, so find the tail period p (<= maxp, >=2 clean periods at
    the end) and strip ALL trailing whole periods — the loop replays them. The
    smallest matching p is NOT enough (a trailing run of equal values matches
    p=1 and hides the real cycle), so pick the p minimising emitted RLE rows.
    Falls back to looping the final value: graceful, in-tune degradation."""
    n = len(seq)
    best_rows, best = None, (seq[:n - 1], seq[n - 1:])
    for p in range(1, min(maxp, n // 2) + 1):
        if seq[n - 2 * p:n - p] != seq[n - p:]:
            continue
        k = n - p
        while k - p >= 0 and seq[k - p:k] == seq[k:k + p]:
            k -= p
        rows = len(_rle(seq[:k])) + len(_rle(seq[k:k + p]))
        if best_rows is None or rows < best_rows:
            best_rows, best = rows, (seq[:k], seq[k:k + p])
    return best


def _rle(seq, max_run=255):
    """(value, run) pairs, runs capped at 255 (the hold column is one byte)."""
    out, i = [], 0
    while i < len(seq):
        j = i
        while j < len(seq) and seq[j] == seq[i] and j - i < max_run:
            j += 1
        out.append((seq[i], j - i))
        i = j
    return out


def wave_program(note):
    """Build a 3-col wave program [(waveform, semitone, hold-frames)... ,
    ($7f, loop_rel, 0)] carrying the note's full stepped pitch envelope:
    RLE'd body at exact per-frame timing + the settled periodic tail looped.
    col1 of the $7f row is the loop target RELATIVE to the program start."""
    nb, sem = semitone_envelope(note)
    wfgate = (note.waveform & 0xF0) | 0x01           # waveform + gate bit
    body, loop = _best_loop_split(sem)
    rows = [(wfgate, s & 0xFF, run) for s, run in _rle(body)]
    loop_rel = len(rows)
    rows += [(wfgate, s & 0xFF, run) for s, run in _rle(loop)]
    rows.append((0x7f, loop_rel, 0))
    return nb, rows


def trim_program(rows, max_rows):
    """Shrink a program to max_rows by dropping body rows just before the loop
    (the envelope jumps into its settled cycle early — graceful, in-tune)."""
    if len(rows) <= max_rows:
        return rows
    loop_rel = rows[-1][1]
    body, loop = rows[:loop_rel], rows[loop_rel:-1]
    keep = max_rows - 1 - len(loop)
    if keep < 0:                                     # loop alone too big
        loop, body, keep = loop[:max_rows - 1], [], 0
    body = body[:keep]
    return body + loop + [(0x7f, len(body), 0)]


def fit_budget(programs, budget=WAVE_BUDGET):
    """Trim the largest programs until the shared WAVE table fits. Logs trims."""
    total = sum(len(p) for p in programs)
    while total > budget:
        i = max(range(len(programs)), key=lambda k: len(programs[k]))
        target = max(8, len(programs[i]) - (total - budget))
        if target >= len(programs[i]):
            target = len(programs[i]) - 1
        if target < 3:
            raise ValueError("wave programs cannot fit the 256-row table")
        print(f"  budget: trimming program {i} {len(programs[i])} -> {target} rows")
        programs[i] = trim_program(programs[i], target)
        total = sum(len(p) for p in programs)


def reconstruct_program(rows, nb, n_frames):
    """Replay a wave program with the driver's exact semantics (resolve $7f
    jumps, hold each row col2 frames with 0 -> 1, clamp note to [0,$6f]) to its
    per-frame note BYTE, for the headless note-index-space check."""
    out, r, cnt, cur = [], 0, 0, 0
    for _ in range(n_frames):
        if cnt == 0:
            guard = 8
            while rows[r][0] == 0x7f and guard:
                r = rows[r][1]
                guard -= 1
            cur = rows[r][1]
            cnt = max(1, rows[r][2] if len(rows[r]) > 2 else 1)
        s = cur - 256 if cur >= 0x80 else cur
        out.append(max(0, min(0x6f, nb + s)))
        cnt -= 1
        if cnt == 0:
            r += 1
    return out


def main():
    sid = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, "SID", "Galway_Martin", "Wizball.sid")
    frames = int(sys.argv[2]) if len(sys.argv) > 2 else 1800
    h = SIDParser(sid).parse_header()
    song = T.extract(sid, frames, h.init_address, h.play_address,
                     (h.start_song or 1) - 1)
    rows_total = frames // TEMPO
    print(f"trace: {frames} frames, {rows_total} rows @ tempo {TEMPO}")

    # One instrument + wave program per unique (waveform, envelope) shape,
    # shared across notes and voices; per voice, every traced note becomes a
    # sequence row at its true onset with its shape's instrument.
    shape_to_instr = {}
    instrs, programs = [], []
    note_seq = [[] for _ in range(3)]    # (onset_row, end_row, note_byte, instr)
    overflow = 0
    for v, voice in enumerate(song.voices):
        for note in voice.notes:
            orow = note.onset // TEMPO
            if orow >= rows_total:
                continue
            nb, rows = wave_program(note)
            key = tuple(rows)
            idx = shape_to_instr.get(key)
            if idx is None:
                if len(instrs) >= 32:                # instrument table is full
                    overflow += 1
                    idx = 0
                else:
                    idx = len(instrs)
                    shape_to_instr[key] = idx
                    instrs.append((0x06, 0xFA, (note.waveform & 0xF0) | 0x01, 0x08))
                    programs.append(rows)
            end_row = min(rows_total, max(orow + 1, note.end // TEMPO))
            note_seq[v].append((orow, end_row, nb, idx))
    if overflow:
        print(f"  WARNING: {overflow} notes past the 32-instrument cap reuse instr 0")
    if not instrs:
        raise SystemExit("no notes traced — nothing to build")
    fit_budget(programs)
    print(f"  {sum(len(ns) for ns in note_seq)} notes, {len(instrs)} instruments/"
          f"programs, wave rows {sum(len(p) for p in programs)}/{WAVE_BUDGET}")

    # Sequence rows packed via segment_track — the SAME packer the SF2II-playable
    # static build uses (datasource_sequence.cpp format) so SF2II parses + plays.
    # Pad to rows_total so the orderlist doesn't wrap early and re-trigger.
    segs = []
    for v in range(3):
        drows, cur = [], 0
        for orow, end_row, nb, idx in note_seq[v]:
            orow = max(orow, cur)
            if orow >= end_row:
                continue
            drows += [D11Row(note=SF2_GATE_OFF) for _ in range(orow - cur)]
            drows.append(D11Row(note=nb, instrument=idx))
            drows += [D11Row(note=SF2_GATE_ON) for _ in range(end_row - orow - 1)]
            cur = end_row
        drows += [D11Row(note=SF2_GATE_OFF) for _ in range(rows_total - cur)]
        segs.append(segment_track(drows) if drows else [bytes([0x7F])])

    def _wftag(wf):
        for bit, t in ((0x80, "noise"), (0x40, "pulse"), (0x20, "saw"), (0x10, "tri")):
            if wf & bit:
                return t
        return "inst"
    names = [f"{_wftag(ins[2])} {i + 1:02d}" for i, ins in enumerate(instrs)]

    B.TEMPO = TEMPO
    gen, edit, mdp, seq0 = N.gen_includes_song(segs, instrs,
                                               filter_lead=False,
                                               wave_programs=programs)
    prg = B.assemble()
    sf2 = B.wrap(prg, gen, edit, mdp, instr_names=names)
    out = os.path.join(ROOT, "out", "galway_trace_song.sf2")
    open(out, "wb").write(sf2)
    print(f"wrote {out} ({len(sf2)} bytes)")

    from sidm2.models import SF2DriverInfo
    from sidm2 import sf2_parser
    di = SF2DriverInfo()
    la = sf2_parser.parse_sf2_blocks(bytearray(sf2), di)
    print(f"PARSE: load=${la:04X} tracks={di.track_count}",
          "OK" if la == 0x0D7E else "FAIL")

    # headless: driver per-frame note vs the emitted program, per note
    from py65.devices.mpu6502 import MPU
    load = prg[0] | (prg[1] << 8)
    m = MPU()
    for i, b in enumerate(prg[2:]):
        m.memory[(load + i) & 0xFFFF] = b
    for i, b in enumerate(edit):
        m.memory[(B.EDIT_BASE + i) & 0xFFFF] = b

    def call(a):
        SENT = 0x4000
        r = (SENT - 1) & 0xFFFF
        m.memory[0x1FF] = r >> 8; m.memory[0x1FE] = r & 0xFF
        m.sp = 0xFD; m.pc = a
        for _ in range(60000):
            if m.pc == SENT:
                return
            m.step()
    call(0x1000)
    sidf = [0xD400, 0xD407, 0xD40E]
    sidc = [0xD404, 0xD40B, 0xD412]
    got = [[] for _ in range(3)]
    gate = [[] for _ in range(3)]
    for _ in range(frames):
        call(0x1003)
        for v in range(3):
            got[v].append(m.memory[sidf[v]] | (m.memory[sidf[v] + 1] << 8))
            gate[v].append(m.memory[sidc[v]] & 0x01)

    all_faithful = True
    for v, voice in enumerate(song.voices):
        if not note_seq[v]:
            # no notes = gate never opens (freq may be nonzero from the shared
            # wave table, but with the gate off the voice is silent).
            silent = not any(gate[v])
            print(f"  osc{v+1}: no notes -> driver {'SILENT ok' if silent else 'GATE ON (X)'}")
            continue
        # Compare in NOTE-INDEX space: the driver's per-frame note byte vs the
        # program's intended note byte (nb + held semitone). Exact, since both
        # quantise through the same freqtable. Allow a small alignment shift for
        # the sequencer's trigger phase (note triggers at onset_row * TEMPO).
        got_note = [freq_to_note(f) for f in got[v]]
        bad_tot = span_tot = rdiff_tot = real_tot = 0
        for k, ((orow, end_row, nb, idx), note) in enumerate(
                zip(note_seq[v], voice.notes)):
            trig = orow * TEMPO
            span = min(end_row * TEMPO, frames) - trig
            if span <= 0:
                continue
            prog = reconstruct_program(programs[idx], nb, span)
            best_bad = span
            for sh in range(0, TEMPO + 1):
                bad = sum(1 for i in range(span - sh)
                          if got_note[trig + sh + i] != prog[i])
                best_bad = min(best_bad, bad)
            bad_tot += best_bad
            span_tot += span
            # program-vs-REAL: how faithfully the RLE'd/looped program tracks
            # the actual trace (informational — a trimmed/looped tail won't
            # match a still-evolving real envelope).
            real = [freq_to_note(f) for f in T.reconstruct_freq(note)]
            cmp_n = min(len(prog), len(real))
            rdiff_tot += sum(1 for i in range(cmp_n) if prog[i] != real[i])
            real_tot += cmp_n
        faithful = bad_tot == 0
        all_faithful = all_faithful and faithful
        print(f"  osc{v+1}: {len(note_seq[v])} notes; driver-vs-program "
              f"{bad_tot}/{span_tot} off {'FAITHFUL' if faithful else 'CHECK'}; "
              f"program-vs-real {rdiff_tot}/{real_tot} note-bytes differ")
    print("TRACE BUILD " + ("FAITHFUL — driver replays the emitted envelopes exactly"
                            if all_faithful else "CHECK — driver diverged from program"))


if __name__ == "__main__":
    main()
