"""Trace-driven native-Galway-driver .sf2 — the faithful build.

Replaces the static-flattener song data (which invents phantom notes + mistimes
rests) with the REAL player's cycle-accurate output: per voice, a note gated at
its true onset row + a per-frame FM offset list (the actual slide/vibrato pitch
envelope). Silent voices stay empty. Pulse/filter/wave reuse the v3.9.0
verified programs. The native driver's fm_step replays the FM lists from FMTAB.

Usage:  py -3 bin/build_galway_trace_song.py [SID/Galway_Martin/Wizball.sid] [frames]
Verifies headless that the driver's per-frame frequency matches the trace.
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

TEMPO = 8        # frames per editor row (keeps sequences small; FM is per-frame)


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


def emit_rest(rows):
    out = bytearray()
    while rows > 0:
        d = min(16, rows)
        out += bytes([0x80 | (d - 1), 0x00])
        rows -= d
    return out


def emit_note(instr, note_byte, rows):
    out = bytearray()
    first = True
    while rows > 0:
        d = min(16, rows)
        if first:
            out += bytes([0xA0 | (instr & 0x1F), 0x80 | (d - 1), note_byte])
            first = False
        else:
            out += bytes([0x80 | (d - 1), 0x7E])
        rows -= d
    return out


def fm_entries_for_note(note):
    """Build FMTAB entries (lo,hi,dur) for a note: a frame-0 base correction (so
    the absolute pitch is exact despite the nearest-note quantisation) followed
    by the RLE'd per-frame deltas, then a freeze terminator."""
    nb = freq_to_note(note.base_freq)
    corr = note.base_freq - note_freq(nb)
    entries = [(corr & 0xFF, (corr >> 8) & 0xFF, 1)]
    for d, run in note.fm:
        entries.append((d & 0xFF, (d >> 8) & 0xFF, run))
    entries.append((0, 0, 0))     # freeze terminator
    return nb, entries


def main():
    sid = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, "SID", "Galway_Martin", "Wizball.sid")
    frames = int(sys.argv[2]) if len(sys.argv) > 2 else 1800
    h = SIDParser(sid).parse_header()
    song = T.extract(sid, frames, h.init_address, h.play_address,
                     (h.start_song or 1) - 1)
    rows_total = frames // TEMPO
    print(f"trace: {frames} frames, {rows_total} rows @ tempo {TEMPO}")

    # Build per-voice sequence + FM list. One note per active voice (Wizball);
    # multi-note voices would chain emit_note segments + per-note FM (future).
    segs = [[bytes([0x7F])] for _ in range(3)]
    instrs = []
    fm_all = []
    vfmstart = [0, 0, 0]
    note_bytes = [0, 0, 0]
    for v, voice in enumerate(song.voices):
        if not voice.active:
            instrs.append((0x06, 0xFA, 0x41, 0x08))   # placeholder (unused)
            continue
        note = voice.notes[0]
        nb, entries = fm_entries_for_note(note)
        note_bytes[v] = nb
        vfmstart[v] = len(fm_all)
        fm_all.extend(entries)
        onset_rows = note.onset // TEMPO
        hold_rows = max(1, (note.end - note.onset) // TEMPO)
        # Build the voice as D11Rows and pack via segment_track — the SAME packer
        # the SF2II-playable static build uses (mirrors datasource_sequence.cpp),
        # so SF2II's editor parses + plays it. (Hand-built packing didn't play.)
        rows = [D11Row(note=SF2_GATE_OFF) for _ in range(onset_rows)]
        rows.append(D11Row(note=nb, instrument=v))
        rows += [D11Row(note=SF2_GATE_ON) for _ in range(hold_rows - 1)]
        segs[v] = segment_track(rows)
        # instrument v: waveform from the note WITH the gate bit set ($x1) so the
        # wave program gates the voice on; AD/SR Galway lead defaults. Lead voices
        # get the filter flag via gen_includes_song (instr 0/1).
        instrs.append((0x06, 0xFA, (note.waveform & 0xF0) | 0x01, 0x08))
    while len(instrs) < 3:
        instrs.append((0x06, 0xFA, 0x41, 0x08))

    print(f"  note bytes per voice: {note_bytes}, FM entries total: {len(fm_all)}, "
          f"vfmstart: {vfmstart}")

    B.TEMPO = TEMPO
    gen, edit, mdp, seq0 = N.gen_includes_song(segs, instrs,
                                               fm_data=(vfmstart, fm_all),
                                               filter_lead=False)
    prg = B.assemble()
    names = ["lead", "", "harmony"]
    sf2 = B.wrap(prg, gen, edit, mdp, instr_names=[n for n in names])
    out = os.path.join(ROOT, "out", "galway_trace_song.sf2")
    open(out, "wb").write(sf2)
    print(f"wrote {out} ({len(sf2)} bytes)")

    from sidm2.models import SF2DriverInfo
    from sidm2 import sf2_parser
    di = SF2DriverInfo()
    la = sf2_parser.parse_sf2_blocks(bytearray(sf2), di)
    print(f"PARSE: load=${la:04X} tracks={di.track_count}",
          "OK" if la == 0x0D7E else "FAIL")

    # headless: driver per-frame freq vs the trace reconstruction, per active voice
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
    got = [[] for _ in range(3)]
    for _ in range(frames):
        call(0x1003)
        for v in range(3):
            got[v].append(m.memory[sidf[v]] | (m.memory[sidf[v] + 1] << 8))

    for v, voice in enumerate(song.voices):
        if not voice.active:
            silent = all(x == 0 for x in got[v])
            print(f"  osc{v+1}: inactive -> driver {'SILENT ok' if silent else 'SOUNDS (X)'}")
            continue
        exp = T.reconstruct_freq(voice.notes[0])   # per-frame real freq
        on = voice.notes[0].onset
        # compare from onset; allow <=4 (rounding of the base correction)
        bad = 0; n = 0
        for f in range(on, min(frames, on + len(exp))):
            n += 1
            if abs(got[v][f] - exp[f - on]) > 4:
                bad += 1
        worst = max((abs(got[v][f] - exp[f - on])
                     for f in range(on, min(frames, on + len(exp)))), default=0)
        print(f"  osc{v+1}: {bad}/{n} frames off >4 (worst abs diff={worst})  "
              f"{'FAITHFUL' if bad == 0 else 'MISMATCH'}")


if __name__ == "__main__":
    main()
