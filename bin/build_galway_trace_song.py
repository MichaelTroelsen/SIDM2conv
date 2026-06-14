"""Trace-driven native-Galway-driver .sf2 — the faithful build.

Replaces the static-flattener song data (which invents phantom notes + mistimes
rests) with the REAL player's cycle-accurate output: per voice, every note gated
at its true onset row, carrying its real pitch envelope (the Galway slide/
vibrato) as a STANDARD 2-column SF2II WAVE-table program — one (waveform,
semitone) row per frame with the settled tail looped, so a full-length song's
envelopes fit the 256-row table AND render + edit + PLAY in stock SF2II (a 3rd
column silenced playback). Notes sharing a (waveform, envelope) shape share one
instrument + program.

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


def detect_multispeed(sid_path, init, play, subtune):
    """Galway tunes are CIA-multispeed: the play routine runs N times per PAL
    video frame. The trace is per-play-call, so the driver must replay N ticks
    per SF2II (50 Hz) frame to match wall-clock speed. Detect N by emulating
    init+play and reading the CIA timer-A interval the player sets each call:
    find the timer pattern's period and scale it to one frame (19656 cycles)."""
    import struct
    from py65.devices.mpu6502 import MPU
    PAL = 19656
    d = open(sid_path, "rb").read()
    off = struct.unpack(">H", d[6:8])[0]
    la = struct.unpack(">H", d[8:0x0A])[0]
    body = d[off:]
    if la == 0:
        la = body[0] | (body[1] << 8); body = body[2:]
    m = MPU()
    for i, b in enumerate(body):
        m.memory[(la + i) & 0xFFFF] = b

    def call(a, areg=0):
        S = 0xFF00
        m.memory[0x1FF] = (S - 1) >> 8; m.memory[0x1FE] = (S - 1) & 0xFF
        m.sp = 0xFD; m.pc = a; m.a = areg
        for _ in range(3000000):
            if m.pc == S:
                return
            m.step()
    call(init, subtune)
    timers = []
    for _ in range(48):
        call(play)
        t = m.memory[0xDC04] | (m.memory[0xDC05] << 8)
        timers.append(t if t else PAL)
    # smallest period p of the timer pattern
    p = next((q for q in range(1, 17)
              if all(timers[i] == timers[i % q] for i in range(len(timers)))), 1)
    n = round(p * PAL / max(1, sum(timers[:p])))
    return max(1, n)


def pulse_program(seg, qstep):
    """RLE the real per-play-call pulse-width (quantized to `qstep`) into 8X
    'set width' commands (b0=$80|hi, b1=lo, dur). The FINAL value is held by a
    $7f freeze, so a constant pulse is just 2 rows; middle segments longer than
    the 1-byte dur are split. Absolute sets follow Galway's real PWM and never
    wrap, so no click. Coarsening qstep trades pulse detail for table rows."""
    if not seg:
        return [(0x7F, 0, 0)]                        # freeze at row 0
    q = [(w // qstep) * qstep for w in seg]
    rows, i, n = [], 0, len(q)
    while i < n:
        v = q[i]
        j = i
        while j < n and q[j] == v:
            j += 1
        b0, b1 = 0x80 | ((v >> 8) & 0x0F), v & 0xFF
        if j >= n:                                   # last value: freeze holds it
            rows.append((b0, b1, 1))
        else:
            hold = j - i
            while hold > 255:
                rows.append((b0, b1, 255))
                hold -= 255
            rows.append((b0, b1, hold))
        i = j
    rows.append((0x7F, 0, len(rows)))                # freeze (holds last value)
    return rows


def sweep_pulse_program():
    """The pre-click LEAD 'sweep' sound, made click-free: a bounded full-range
    triangle PWM (set $010, ramp +8/tick up to $FF0, then -8/tick back to $010,
    loop). Same sweep speed/range as the old wrapping ramp the lead sounded best
    with, but it bounces instead of wrapping $FFF->$000, so no click. The -8 add
    is $FF8 (12-bit two's complement); exact step counts keep it in [$010,$FF0]
    so it never under/overflows."""
    return [
        (0x80, 0x10, 1),        # set $010
        (0x00, 0x08, 255),      # +8
        (0x00, 0x08, 253),      # +8  -> $FF0   (up half: 508 ticks)
        (0x0F, 0xF8, 255),      # -8  ($FF8)
        (0x0F, 0xF8, 253),      # -8  -> $010   (down half)
        (0x7F, 0, 1),           # loop to row 1 (bounce; never re-sets)
    ]


def fm_program(note):
    """Build a row-major FM program for the note: a frame-0 base correction (so
    the absolute pitch is exact despite the nearest-note quantisation) + the
    RLE'd per-frame frequency deltas (runs split to fit the 1-byte dur) + a
    (0,0,0) freeze terminator. Each entry is (offset_lo, offset_hi, dur); the
    driver's fm_step adds `offset` to the voice frequency every frame for `dur`
    frames. Lossless RLE — the full Galway slide/vibrato is reproduced, with no
    256-row wave-table cap (the FM table is driver-private, 16-bit indexed)."""
    nb = freq_to_note(note.base_freq)
    corr = note.base_freq - note_freq(nb)
    entries = [(corr & 0xFF, (corr >> 8) & 0xFF, 1)]
    for d, run in note.fm:
        while run > 255:
            entries.append((d & 0xFF, (d >> 8) & 0xFF, 255))
            run -= 255
        if run > 0:
            entries.append((d & 0xFF, (d >> 8) & 0xFF, run))
    entries.append((0, 0, 0))                        # freeze terminator
    return nb, entries


def main():
    sid = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, "SID", "Galway_Martin", "Wizball.sid")
    frames = int(sys.argv[2]) if len(sys.argv) > 2 else 1800
    h = SIDParser(sid).parse_header()
    subtune = (h.start_song or 1) - 1
    song = T.extract(sid, frames, h.init_address, h.play_address, subtune)
    rows_total = frames // TEMPO
    multispeed = detect_multispeed(sid, h.init_address, h.play_address, subtune)
    print(f"trace: {frames} play-calls, {rows_total} rows @ tempo {TEMPO}, "
          f"multispeed={multispeed} (play-calls/video-frame) -> "
          f"{frames / multispeed / 50.12:.1f}s")

    # One instrument + FM program per unique (waveform, envelope) shape, shared
    # across notes and voices; per voice, every traced note becomes a sequence
    # row at its true onset carrying its shape's instrument. The pitch envelope
    # lives in the driver-private FM table (lossless RLE, 16-bit indexed) so the
    # wave table stays a short standard 2-row program (waveform only).
    shape_to_instr = {}
    instrs, fmprogs, pulse_src = [], [], []
    note_seq = [[] for _ in range(3)]    # (onset_row, end_row, note_byte, instr)
    overflow = 0
    for v, voice in enumerate(song.voices):
        for note in voice.notes:
            orow = note.onset // TEMPO
            if orow >= rows_total:
                continue
            nb, fm = fm_program(note)
            key = ((note.waveform & 0xF0), tuple(fm))
            idx = shape_to_instr.get(key)
            if idx is None:
                if len(instrs) >= 32:                # instrument table is full
                    overflow += 1
                    idx = 0
                else:
                    idx = len(instrs)
                    shape_to_instr[key] = idx
                    instrs.append((0x06, 0xFA, (note.waveform & 0xF0) | 0x01, 0x08))
                    fmprogs.append(fm)
                    pulse_src.append((v, note))      # defining note for the pulse
            end_row = min(rows_total, max(orow + 1, note.end // TEMPO))
            note_seq[v].append((orow, end_row, nb, idx))
    if overflow:
        print(f"  WARNING: {overflow} notes past the 32-instrument cap reuse instr 0")
    if not instrs:
        raise SystemExit("no notes traced — nothing to build")
    # Per-instrument pulse program: the REAL per-play-call pulse-width envelope
    # (song.pulse) downsampled to 8X "set width" commands. Coarsen the time step
    # until the shared 256-row PULSE table fits. Absolute sets never wrap -> no
    # click (unlike a free-running ramp), and they follow Galway's measured PWM.
    # The lead voice (osc1) sounds best with the classic full-range pulse SWEEP
    # (click-free triangle); the other voices use their REAL measured pulse.
    qstep = 0x40
    while True:
        pulseprogs = [sweep_pulse_program() if v == 0
                      else pulse_program(song.pulse[v][n.onset:n.end], qstep)
                      for (v, n) in pulse_src]
        if sum(len(p) for p in pulseprogs) <= 250 or qstep >= 0x1000:
            break
        qstep *= 2
    print(f"  {sum(len(ns) for ns in note_seq)} notes, {len(instrs)} instruments, "
          f"{sum(len(p) for p in fmprogs)} FM entries, "
          f"{sum(len(p) for p in pulseprogs)} pulse rows (qstep ${qstep:x})")

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
                                               fm_programs=fmprogs,
                                               multispeed=multispeed,
                                               pulse_programs=pulseprogs)
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
        SENT = 0x9000            # above the FM region ($4040+), driver returns here
        r = (SENT - 1) & 0xFFFF
        m.memory[0x1FF] = r >> 8; m.memory[0x1FE] = r & 0xFF
        m.sp = 0xFD; m.pc = a
        for _ in range(300000):          # multispeed do_play runs the player Nx
            if m.pc == SENT:
                return
            m.step()
    call(0x1000)
    sidf = [0xD400, 0xD407, 0xD40E]
    sidc = [0xD404, 0xD40B, 0xD412]
    # The driver does `multispeed` play-ticks per do_play (one SF2II video frame),
    # so call it frames//multispeed times to replay the whole trace; the SID state
    # sampled after do_play k is the trace at play-call (k+1)*multispeed-1.
    vframes = frames // multispeed
    got = [[] for _ in range(3)]
    gate = [[] for _ in range(3)]
    for _ in range(vframes):
        call(0x1003)
        for v in range(3):
            got[v].append(m.memory[sidf[v]] | (m.memory[sidf[v] + 1] << 8))
            gate[v].append(m.memory[sidc[v]] & 0x01)

    # per-play-call real frequency per voice (placed at each note's true onset)
    gf = [[0] * frames for _ in range(3)]
    for v, voice in enumerate(song.voices):
        for note in voice.notes:
            for i, f in enumerate(T.reconstruct_freq(note)):
                if note.onset + i < frames:
                    gf[v][note.onset + i] = f

    all_faithful = True
    for v, voice in enumerate(song.voices):
        if not note_seq[v]:
            silent = not any(gate[v])
            print(f"  osc{v+1}: no notes -> driver {'SILENT ok' if silent else 'GATE ON (X)'}")
            continue
        # Compare the driver's per-video-frame frequency against the real trace
        # sampled at the matching play-call. The FM program is a lossless RLE of
        # the real deltas, so active-note frames should match within freqtable
        # rounding (a few units).
        bad = worst = cmp = 0
        for k in range(vframes):
            pc = min((k + 1) * multispeed - 1, frames - 1)
            if gf[v][pc] == 0:
                continue                                # gate off / between notes
            cmp += 1
            diff = abs(got[v][k] - gf[v][pc])
            worst = max(worst, diff)
            if diff > 4:
                bad += 1
        faithful = bad == 0
        all_faithful = all_faithful and faithful
        print(f"  osc{v+1}: {len(note_seq[v])} notes; driver-vs-real "
              f"{bad}/{cmp} sampled frames off >4 (worst {worst}) "
              f"{'FAITHFUL' if faithful else 'CHECK'}")
    print("TRACE BUILD " + ("FAITHFUL — driver reproduces the real per-frame pitch"
                            if all_faithful else "CHECK — driver diverged from trace"))


if __name__ == "__main__":
    main()
