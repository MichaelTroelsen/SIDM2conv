"""Stage B (native driver) — emit a Hawkeye/MoN tune as a native-driver .sf2.

Feeds the RE'd + validated MoN decode (sidm2/mon_parser.py + bin/mon_to_sf2.py)
into the from-scratch native SF2 driver (drivers_src/mon/, a copy of the
ROMUZAK/Galway engine: SF2 sequencer + wave/pulse/filter runners + per-frame FM
pitch program + the song's OWN freq table). The engine is player-agnostic; the
MoN-specific work is the extraction here.

Milestone B1: notes + MoN's own freq table (correct tuning) + AD/SR/waveform +
static pulse width, played through the native driver, loadable in stock SF2II.
PWM / filter sweeps / per-frame slides / the gate envelope follow (B2+).

Usage:  py -3 bin/build_mon_native_song.py [SID/Tel_Jeroen/Hawkeye.sid] [subtune]
"""
import bisect
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))

import build_romuzak_driver_full as B
import build_romuzak_native_song as RN
import mon_to_sf2
from sidm2.mon_parser import load_sid, MON

MON_DIR = os.path.join(ROOT, "drivers_src", "mon")
ROM_DIR = os.path.join(ROOT, "drivers_src", "romuzak")


def write_mon_freqtable(m):
    """MoN's own note->freq table ($8337, 2 bytes/note) -> mon/freqtable.inc, so the
    native driver's frequencies match the original byte-for-byte (fixes the ~0.35
    semitone tuning gap vs Driver-11's PAL table). Indexed by note byte ($00=C-0)."""
    words = [m.note_freq(i) & 0xFFFF for i in range(0x70)]
    with open(os.path.join(MON_DIR, "freqtable.inc"), "w") as f:
        f.write("; MoN $8337 note->freq table (exact tuning, for byte fidelity)\n")
        for k in range(0, len(words), 8):
            f.write("        .word " + ", ".join(f"${w:04x}" for w in words[k:k + 8]) + "\n")


def static_pulse(pw):
    """Milestone-B1 pulse program: hold the instrument's base width (no PWM yet).
    Format: 8X XX = set width (X|XX) for 1 frame; 7f = freeze."""
    return [(0x80 | ((pw >> 8) & 0x0F), pw & 0xFF, 1), (0x7F, 0, 0)]


from sidm2.galway_to_driver11 import D11Row, SF2_NOTE_MIN, SF2_NOTE_MAX, SF2_GATE_ON
from sidm2.galway_driver11_emitter import segment_track
from sidm2.fidelity_common import freq_to_semi

FM_CAP = 256                                       # max frames of FM captured per note
                                                   # (covers long held-note vibrato; the
                                                   # offset is pitch-independent so vibrato
                                                   # programs dedup across notes)
WAVE_CAP = 96                                      # max frames of wave/gate envelope/note

# NEAR-LOSSLESS bundle clustering: the $c0-$ff command channel holds <=64 (FM,pulse)
# bundles. Dense windows have more DISTINCT bundles than that, almost all from slightly-
# different per-note FM (pitch) contours. Rather than splitting the window (the lossless
# default), allow merging two bundles when their pitch contours differ by less than
# BUNDLE_TOL (cumulative |freq-offset| over the first 24 frames) AND their pulse program
# is identical — an inaudible merge. The packer grows a window as long as greedy
# within-tol merging can still fit it to 63 bundles. Tuned so freq fidelity stays ~100%.
BUNDLE_TOL = 0                                      # 0 = OFF (lossless split); raised below


def fm_program_for(frames, v, onset, dur_f, base):
    """Per-note FM program (B2): reproduce the original's exact per-frame freq for
    this note. offset[k] = (trace_freq[onset+k] - base) & $FFFF; the driver's FM
    runner accumulates per-frame deltas, so emit delta[k]=offset[k]-offset[k-1] as
    (lo,hi,run) RLE entries + a freeze. Handles BOTH portamento slides (constant
    delta) and arps (per-frame deltas) byte-exactly. base = the note's freqtable
    value (== the driver's vfreq), so offset[0]=0 (frame 0 plays at base)."""
    targ, hold = [], 0
    for k in range(min(dur_f, FM_CAP)):
        idx = onset + k
        tf = frames[idx][0][v]['freq'] if idx < len(frames) else None
        hold = ((tf - base) & 0xFFFF) if tf is not None else hold
        targ.append(hold)
    # The driver's pr_note holds base pitch on the TRIGGER frame (FM_CNT=1/FM_OFF=0),
    # so FM entries apply from frame 1 onward. Measure the offset from 0 (not targ[0]):
    # the cumulative reaches targ[f] at frame f>=1, so a note whose first frame is
    # DETUNED from its nominal note_freq (targ[0]!=0 — portamento/slide starts) keeps
    # that offset instead of losing it. (For clean retriggers targ[0]==0 -> unchanged,
    # so Hawkeye/Cybernoid byte-exact notes are not affected.) Only frame 0 plays base.
    deltas, prev = [], 0
    for k in range(1, len(targ)):
        deltas.append((targ[k] - prev) & 0xFFFF)
        prev = targ[k]
    prog, run, rl = [], None, 0

    def flush(r, n):
        # byte2 must stay $01-$7e: $7f is the LOOP entry and $80+ the SEMITONE
        # entry in the driver's FM dispatch — split longer runs.
        while n > 0:
            c = min(n, 126)
            prog.append((r & 0xFF, (r >> 8) & 0xFF, c))
            n -= c
    for delta in deltas:
        if delta == run:
            rl += 1
        else:
            if run is not None:
                flush(run, rl)
            run, rl = delta, 1
    if run is not None:
        flush(run, rl)
    if not prog or all(e[0] == 0 and e[1] == 0 for e in prog):
        return [(0, 0, 0)]                          # flat -> program 0 (freeze)
    prog.append((0, 0, 0))                          # hold the last offset
    return prog


# --- STRUCTURAL ARPS (whats-next step 2): emit the player's own compact looping
# semitone arp table (MON.arp_program) as a LOOPING SEMITONE FM program instead of
# the per-note Hz-delta unroll. Pitch-independent -> one program per chord shape
# (the ROM has ~16), collapsing the FM side of the bundle explosion. Gated by
# MON_ARP_STRUCT=1 while the wave/pulse structural prongs land (all three caps must
# drop for the part count to fall).
ARP_STRUCT = os.environ.get("MON_ARP_STRUCT", "") == "1"


def arp_fm_program(arp):
    """MON.arp_program dict -> looping SEMITONE FM program, phase-aligned to the ROM:
    step k occupies frames [k*fps, (k+1)*fps) of the note (fps = (dur>>4)+1, the
    $106A -$10/frame counter). The driver's pr_note holds BASE pitch on the trigger
    frame, which covers frame 0 of step0 — so entry 0 is step0 for the REMAINING
    fps-1 frames (omitted at fps==1), then steps 1..N-1, then step0 again at full
    fps, looping over that rotation. (Residual: when steps[0] != 0 the trigger
    frame plays base instead of base+steps[0] — 1 frame/note, the same class as
    the unreproducible onset spike.)"""
    fps = min((arp['dur'] >> 4) + 1, 0x7F)
    steps = arp['steps']
    prog = []
    if fps > 1:
        prog.append((steps[0] & 0xFF, 0, 0x80 | (fps - 1)))
    lead = len(prog)                                # loop target = start of the rotation
    for s in steps[1:] + steps[:1]:
        prog.append((s & 0xFF, 0, 0x80 | fps))
    if arp.get('loop'):
        prog.append((lead, 0, 0x7F))
    else:
        prog.append((0, 0, 0))                      # $fe END -> hold
    return prog


def _arp_fm_for(m, ev):
    """The structural FM program for a note, or None to fall back to the trace
    unroll (non-arp notes, non-Supremacy engines, flag off)."""
    if not ARP_STRUCT or not hasattr(m, "arp_program") or getattr(m, "tbl_arp_idx", 0) == 0:
        return None
    try:
        arp = m.arp_program(ev.wprog)
    except Exception:
        return None
    if not arp or not arp.get('steps') or arp['steps'] == [0]:
        return None
    return arp_fm_program(arp)


def pulse_program_for(frames, v, onset, dur_f, cap=FM_CAP):
    """Per-note PULSE program (B3 PWM): reproduce the original's per-frame pulse
    width. 8X = set width frame 0; 0X = add per-frame delta (12-bit) for `run`
    frames; 7f = freeze. The driver restarts the pulse program per note (PPTR=
    VIPUL/VPC=0), so frame 0 sets the base — no 1-frame offset (unlike FM).
    cap > FM_CAP is used for the free-running per-voice STREAM programs."""
    targ, hold = [], None
    for k in range(min(dur_f, cap)):
        idx = onset + k
        pv = frames[idx][0][v]['pul'] if idx < len(frames) else None
        if pv is not None:
            hold = pv
        targ.append(hold if hold is not None else 0x800)
    prog = [(0x80 | ((targ[0] >> 8) & 0x0F), targ[0] & 0xFF, 1)]   # 8X set frame 0

    def flush(r, n):
        while n > 0:                                              # byte2 is one byte
            c = min(n, 255)
            prog.append(((r >> 8) & 0x0F, r & 0xFF, c))
            n -= c
    prev, run, rl = targ[0], None, 0
    for k in range(1, len(targ)):
        delta = (targ[k] - prev) & 0xFFF                          # 12-bit signed add
        prev = targ[k]
        if delta == run:
            rl += 1
        else:
            if run is not None:
                flush(run, rl)
            run, rl = delta, 1
    if run is not None:
        flush(run, rl)
    prog.append((0x7F, 0, 0))                                     # freeze (hold last)
    return prog


def extract_wave_programs(m, sid, sub, idx_map, instr_rows, frames):
    """Per-instrument WAVE program (B3 gate envelope): wave_step advances one row per
    FRAME and writes col0 to $D404 (gate bit preserved, VGMASK=$ff on a note). Sample
    the original's per-frame waveform over a note that uses each instrument, hold the
    last change point, and loop there — reproduces the $43->$42 / $41->$40 gate-off
    (note release) mid-note. col1 = 0 (pitch comes from the FM program, not semitones).
    Returns {slot: [(wf,0),...,(7f,loop_row)]}."""
    delay = getattr(m, "onset_delay", 0)
    progs = {}
    for v in range(3):
        tk = 0
        for ev in m.voices[v]:
            slot = idx_map.get(ev.instr, 0)
            fr = m.tick_to_frame(tk) + delay
            dur_f = m.tick_to_frame(tk + ev.dur) - m.tick_to_frame(tk)
            if ev.retrig and slot not in progs and dur_f >= 2:
                wfs, last = [], 0x41
                for k in range(min(dur_f, WAVE_CAP)):
                    idx = fr + k
                    w = frames[idx][0][v]['wf'] if idx < len(frames) else None
                    last = w if w is not None else last
                    wfs.append(last & 0xFF)
                settle = max((k for k in range(1, len(wfs)) if wfs[k] != wfs[k - 1]),
                             default=0)
                prog = [(wfs[k], 0x00) for k in range(settle + 1)]
                prog.append((0x7F, settle))               # loop on the settled waveform
                progs[slot] = prog
            tk += ev.dur
    return progs


def filter_trace(sid, sub, secs):
    """Per-frame global filter state from siddump (fill-forward): (cutoff11, ctrl)
    where cutoff11 = ($D415&7)|($D416<<3) and ctrl = $D417 (res+routing)."""
    from sidm2.fidelity_common import siddump_filter_trace
    return siddump_filter_trace(sid, [f'-a{sub}', f'-t{secs}'])


def _filt_set_row(cutoff11, ctrl):
    """A filt_prog_step SET row reproducing $D416 = cutoff11>>3 (low 3 bits 0),
    passband LOW, res/routing = ctrl. byte0 = $90|Y (X=1 Low, Y=cutoff hi nibble),
    byte1 = (C&$0f)<<4, byte2 = ctrl."""
    C = (cutoff11 >> 3) & 0xFF
    return (0x90 | ((C >> 4) & 0x0F), (C & 0x0F) << 4, ctrl & 0xFF)


def _filt_add_row(d416_delta, count):
    """A filt_prog_step ADD-to-cutoff row changing $D416 by `d416_delta` per frame
    for `count` frames. The driver applies ((byte0&f):byte1) << 4 to the 16-bit cutoff
    (F_CHI = $D416), so to step $D416 by d416_delta the pre-shift 12-bit value is
    (d416_delta << 4). byte0's low nibble = hi, byte1 = lo, byte2 = frame count.
    (byte0 <= $0F so the driver reads it as an ADD, not a $90+ SET or $7F jump.)"""
    twelve = (d416_delta << 4) & 0xFFF        # signed delta -> 12-bit
    return ((twelve >> 8) & 0x0F, twelve & 0xFF, max(1, min(count, 255)))


# MoN's filter is a per-note cutoff ENVELOPE (RE'd: $90F6,X frame counter reset on
# note-on drives a threshold/delta table -> attack/decay/sustain on $D416; see
# memory/hawkeye-mon-filter-engine-re.md). It restarts on each note of the filter-
# routed voice, so it maps onto filt_prog_step as ONE program restarted per note.
FILT_FAST = 0x40                              # 11-bit cutoff jump that marks an attack


def routed_voice(ftr):
    """The single voice routed to the filter, from the dominant $D417 low-nibble routing
    bit (bit n = voice n). Returns 0/1/2, or None if no routing or >1 voice is routed
    (then drives map to any voice, as before). Restricting drive detection to the routed
    voice's note-ons is what fixes long-ramp tunes: the envelope restarts ONLY on that
    voice's notes, so crediting an unrouted voice's note (Myth sub0 mis-credited 7 to the
    unrouted voice 0) corrupts the canonical envelope capture."""
    from collections import Counter
    c = Counter(ct & 0x07 for _, ct in ftr if (ct & 0x07))
    if not c:
        return None
    route = c.most_common(1)[0][0]
    return {1: 0, 2: 1, 4: 2}.get(route)         # single-bit routing only


def detect_filter_drives(ftr, onsets_by_voice, routed=None):
    """Find the filter-envelope restarts = the note-ons of the filter-routed voice.
    Each envelope ATTACK shows as a fast cutoff jump (>= FILT_FAST in 11-bit); map it
    back to the nearest note-on within a few frames — that note triggers the envelope.
    When `routed` (0/1/2) is given, only that voice's note-ons are eligible (the engine
    restarts the envelope on the ROUTED voice only); else any voice. Returns
    {onset_frame: voice}."""
    import bisect
    n = len(ftr)
    voices = (routed,) if routed is not None else range(3)
    pairs = sorted({(o, v) for v in voices for o in onsets_by_voice[v]})
    of_frames = sorted({o for o, _ in pairs})
    drives, f = {}, 1
    while f < n:
        if abs(ftr[f][0] - ftr[f - 1][0]) >= FILT_FAST:
            j = bisect.bisect_right(of_frames, f) - 1        # nearest onset <= f
            cand = [of_frames[k] for k in (j, j + 1)
                    if 0 <= k < len(of_frames) and -1 <= (f - of_frames[k]) <= 4]
            if cand:
                o = min(cand, key=lambda x: abs(x - f))
                if o not in drives:
                    drives[o] = next(v for oo, v in pairs if oo == o)
            f += 1
            while f < n and abs(ftr[f][0] - ftr[f - 1][0]) >= FILT_FAST:
                f += 1
        else:
            f += 1
    return drives


def filter_program_for(ftr, onset, span):
    """Per-note FILTER program = the cutoff ENVELOPE captured from the note-on frame
    `onset` for `span` frames, compressed into a SET row + ADD-rows (one per run of
    constant per-frame delta) + a freeze. Reproduces the full attack/decay/rise/sustain
    exactly. Capture starts at the onset (row 0 is applied on the note frame, matching the
    driver's per-note restart), so the note-on frame's own cutoff is the SET base."""
    n = len(ftr)
    if onset + 1 >= n:
        return 0, None
    cap = max(2, min(span, 220))
    seq = [ftr[onset + k] if onset + k < n else ftr[-1] for k in range(cap)]
    cut = [c >> 3 for c, _ in seq]                    # $D416 (8-bit) per frame
    ctl = [ct for _, ct in seq]
    prog = [_filt_set_row(seq[0][0], seq[0][1])]      # SET base cutoff + res/routing
    k = 1
    while k < len(seq):
        if ctl[k] != ctl[k - 1]:                      # res/routing change -> SET row
            prog.append(_filt_set_row(seq[k][0], seq[k][1]))
            k += 1
            continue
        delta = cut[k] - cut[k - 1]
        run = 1
        while (k + run < len(seq) and ctl[k + run] == ctl[k]
               and cut[k + run] - cut[k + run - 1] == delta):
            run += 1
        prog.append(_filt_add_row(delta, run))
        k += run
    prog.append((0x7F, 0, len(prog)))                 # freeze on the final cutoff
    return 0x40, prog


def _rle_wave(wfs):
    if os.environ.get("WAVE_RLE") == "0":           # diagnostic: unrolled (count=1/row)
        return [(w & 0xFF, 1) for w in wfs] + [(0x7F, len(wfs) - 1)]
    return _rle_wave_impl(wfs)


def _rle_wave_impl(wfs):
    """Run-length encode a per-frame waveform list into the native driver's RLE wave
    table: each row = (waveform, frame_count) holding that waveform for `count` frames
    (col1 is a count, not a semitone — MoN's pitch is the FM program). A long gate-off
    ($41 x48 then $40) packs into ~2 rows instead of 49. Ends with a $7f row looping
    back to the last run (the settled waveform = the sustain). Counts are <= WAVE_CAP
    (96) < 256, so they fit the 1-byte column."""
    runs = []
    for w in wfs:
        if runs and runs[-1][0] == w:
            runs[-1][1] += 1
        else:
            runs.append([w, 1])
    rows = [(w & 0xFF, c) for w, c in runs]
    rows.append((0x7F, len(rows) - 1))          # loop to the settled run
    return rows


def _wave_prog_for(frames, v, onset, dur_f):
    """Per-note WAVE program (waveform/gate envelope) sampled per FRAME from the
    trace, trimmed to the settle point. MoN's waveform attack varies per note (the
    $7x wprog), so it's captured per note, not per instrument. Cap covers the
    note's GATE-OFF (release): a note gated on then released ($41->$40) needs rows up
    to the release frame (~48 in Cybernoid). settle trims trailing constant frames,
    so a generous cap is free for short/constant notes."""
    wfs, last = [], 0x41
    for k in range(min(dur_f, WAVE_CAP)):
        idx = onset + k
        w = frames[idx][0][v]['wf'] if idx < len(frames) else None
        last = w if w is not None else last
        wfs.append(last & 0xFF)
    settle = max((k for k in range(1, len(wfs)) if wfs[k] != wfs[k - 1]), default=0)
    return tuple(wfs[:settle + 1])


def _wave_unroll_eq(a, b, n):
    """True iff wave programs a and b (per-frame wf tuples; the driver loops on
    the LAST/settled value) produce identical $D404 output for n frames."""
    m_ = min(n, max(len(a), len(b)))
    for k in range(m_):
        if (a[k] if k < len(a) else a[-1]) != (b[k] if k < len(b) else b[-1]):
            return False
    return True


def _gate_split(m, frames, v, fr, dur_f, tk, ticks):
    """STRUCTURAL WAVE step 3b: MoN's release is a terminal GATE-OFF whose position
    is duration-RELATIVE (Supremacy v1: near tick 17 of 24, frame 1 of a short echo
    note), so per-note wave captures differ per duration and explode the instrument
    cap. Split the release out of the wave program into sequence GATE-OFF rows
    (note byte $00 -> VGMASK=$fe; wave_step then outputs program&$fe = the captured
    $40 tail). Returns (gate_ticks, wfs, off_k, end):
      gate_ticks : gate-on rows for the note (== ticks when no split found)
      wfs        : the raw per-frame capture (for the masked-reproduction check)
      off_k      : original gate-off frame within the note (None = no split)
      end        : capture end minus next-note attack bleed
    Residuals (why this is flag-gated): the engine writes $D404 ~1 frame before the
    freq, so the gate-off can sit 1 frame off the tick grid (accepted skew) and the
    last 1-2 captured frames can hold the next note's attack bleed — <=2-3 frames
    per note, the same unreproducible boundary class as the onset spikes."""
    if not ARP_STRUCT or dur_f < 2 or dur_f > WAVE_CAP:
        return ticks, None, None, dur_f
    wfs, last = [], 0x41
    for k in range(dur_f):
        idx = fr + k
        w = frames[idx][0][v]['wf'] if idx < len(frames) else None
        last = w if w is not None else last
        wfs.append(last & 0xFF)
    end = dur_f
    while end > 0 and (wfs[end - 1] & 1) and end >= dur_f - 2:
        end -= 1                                 # drop next-note attack bleed
    off_k = end
    while off_k > 0 and (wfs[off_k - 1] & 1) == 0:
        off_k -= 1                               # start of the terminal gate-off run
    if off_k == end or off_k < 1 or (end - off_k) < 2:
        return ticks, wfs, None, end             # no (meaningful) terminal release
    steady = wfs[off_k - 1]
    if any(w != (steady & 0xFE) for w in wfs[off_k:end]):
        return ticks, wfs, None, end             # tail is not a pure gate drop
    base_f = m.tick_to_frame(tk)
    # gate-off row = first tick at/after the observed gate-off (<=1-frame skew from
    # the wf-leads-freq register timing is accepted)
    t_off = m.frame_to_tick(base_f + off_k) - tk
    drv_off = m.tick_to_frame(tk + t_off) - base_f
    if t_off < 1 or t_off >= ticks or drv_off - off_k > 1:
        return ticks, wfs, None, end
    return t_off, wfs, off_k, end


def _fm_unroll(prog, n, step=0):
    """Per-frame accumulated freq offsets (relative to the note's base) an FM
    program produces over n frames (model of fm_step: frame 0 = base hold,
    entries apply offset per frame for byte2 frames, (0,0,0) = freeze,
    byte2=$7f = loop to entry byte0, hi=$40/$41 = SCALED +-(step*lo)>>8)."""
    out, acc, i, guard = [0], 0, 0, 64
    while len(out) < n and i < len(prog):
        lo, hi, run = prog[i]
        if run == 0:
            break                                # freeze: hold acc
        if run == 0x7F:                          # loop entry
            i = lo
            guard -= 1
            if guard == 0:
                break
            continue
        if (hi & 0xFC) == 0x40:                  # scaled (pitch-proportional);
            rnd = 0 if (hi & 2) else 128         # bit1 = truncate
            off = (step * lo + rnd) >> 8
            if hi & 1:
                off = (-off) & 0xFFFF
        else:
            off = lo | (hi << 8)
        for _ in range(run):
            acc = (acc + off) & 0xFFFF
            out.append(acc)
            if len(out) >= n:
                break
        i += 1
    while len(out) < n:
        out.append(acc)
    return out


def _fm_unroll_full(prog, n, m, note):
    """Per-frame accumulated freq offsets for a program using ANY entry type
    (freeze / Hz run / loop / SCALED vibrato / SEMITONE / SLIDE), matching the
    driver's fm_step exactly. Needs the song's freq table (via m.note_freq) for
    semitone/slide targets and the scaled-vibrato step."""
    nf = m.note_freq
    base = nf(note & 0x7F)
    step = nf((note + 1) & 0x7F) - base
    out, acc, off, i, guard = [0], 0, 0, 0, 64
    slide_tgt = None

    def s16(v):
        return v - 0x10000 if v >= 0x8000 else v
    while len(out) < n and i < len(prog):
        b0, b1, b2 = prog[i]
        if b2 == 0:
            off, slide_tgt = 0, None            # freeze: hold acc
            break
        if b2 == 0x7F:                          # loop entry
            i = b0
            guard -= 1
            if guard == 0:
                break
            continue
        if b2 >= 0x80:                          # semitone family
            dur = b2 & 0x7F
            s = b0 - 256 if b0 >= 0x80 else b0
            tgt = (nf((note + s) & 0x7F) - base) & 0xFFFF
            if b1 == 0:                         # instant semitone set (arps)
                acc, off, slide_tgt = tgt, 0, None
            else:                               # SLIDE: ramp toward tgt, clamp
                rate = 7 << (b1 - 1)
                off = rate if not (tgt & 0x8000) else (-rate) & 0xFFFF
                slide_tgt = tgt
        elif (b1 & 0xFC) == 0x40:               # scaled vibrato leg (bit1 = trunc)
            dur = b2
            o = (step * b0 + (0 if (b1 & 2) else 128)) >> 8
            off = ((-o) & 0xFFFF) if (b1 & 1) else o
            slide_tgt = None
        else:                                   # plain Hz run
            dur = b2
            off = b0 | (b1 << 8)
            slide_tgt = None
        i += 1
        for _ in range(dur):
            acc = (acc + off) & 0xFFFF
            if slide_tgt is not None:
                d = s16((slide_tgt - acc) & 0xFFFF)
                if d == 0 or (d < 0) != (s16(off) < 0):
                    acc, off, slide_tgt = slide_tgt, 0, None
            out.append(acc)
            if len(out) >= n:
                break
    while len(out) < n:
        out.append(acc)
    return out


def _slide_fm_program(m, ev, note_c, capture, dur_f):
    """Structural program for a $FD slide note: ONE pitch-independent SLIDE entry
    (interval + speed; the DRIVER computes the target from the freqtable and
    clamps on arrival — the clamp frame varies with pitch, which is why this
    can't be unrolled) plus the tail vibrato when the capture shows one.
    Trace-calibrated: rate = 7 << (speed-1) Hz/frame from the frame after the
    trigger. Returns None unless the unrolled candidate reproduces the capture
    exactly (minus 3 boundary frames) — e.g. the speed-26 down-jumps stay
    trace-Hz."""
    speed, target = ev.slide
    if not (1 <= speed <= 8):
        return None
    ivl = ((target - ev.note + 64) & 0x7F) - 64
    if ivl == 0:
        return None
    cap = _fm_unroll(capture, dur_f)
    cmp_f = max(1, dur_f - 3)
    dur_e = min(dur_f, 0x7F)
    cands = [[(ivl & 0xFF, speed, 0x80 | dur_e), (0, 0, 0)]]
    # tail vibrato: deltas resume after the arrival hold — splice a vibrato
    # program after a shorter slide entry (the entry's tail just holds the
    # clamped target, so its length is pitch-independent)
    deltas = [cap[k + 1] - cap[k] for k in range(len(cap) - 1)]
    v = next((k + 1 for k in range(3, len(deltas)) if deltas[k] and not deltas[k - 1]), None)
    if v is not None and v >= 4:
        tail = []
        run, rl = None, 0
        for dlt in deltas[v - 1:cmp_f - 1]:
            d16 = dlt & 0xFFFF
            if d16 == run:
                rl += 1
            else:
                if run is not None:
                    tail.append((run & 0xFF, (run >> 8) & 0xFF, rl))
                run, rl = d16, 1
        if run is not None:
            tail.append((run & 0xFF, (run >> 8) & 0xFF, rl))
        step = m.note_freq((note_c + 1) & 0x7F) - m.note_freq(note_c)
        vib = _vibrato_program(tail + [(0, 0, 0)], step) if step > 0 else None
        if vib is not None and v >= 2:
            # head covers frames 1..v-1 (the slide + clamped hold); the first
            # vibrato leg then lands on frame v, matching the capture. Loop
            # targets inside vib are entry indices relative to ITS start —
            # shift them past the head entry.
            head = [(ivl & 0xFF, speed, 0x80 | min(v - 1, 0x7F))]
            fixed = [(b0 + len(head), b1, b2) if b2 == 0x7F else (b0, b1, b2)
                     for b0, b1, b2 in vib]
            cands.insert(0, head + fixed)
    for cand in cands:
        if _fm_unroll_full(cand, cmp_f, m, note_c) == cap[:cmp_f]:
            return cand
    return None


def _vibrato_program(prog, step):
    """Detect a pitch-proportional VIBRATO in a captured Hz FM program and re-emit
    it as a duration- AND pitch-independent looping SCALED program:
        [0,0,delay] [scale,$40|dir,half-leg] loop{ [scale,$41^dir,L] [scale,$40|dir,L] }
    The ROM computes the wobble as a fixed fraction of the note's semitone step
    (depth = (step*scale+128)>>8, ROUNDED like the ROM), so ONE program serves every pitch — collapsing v2's
    per-note FM explosion. Returns None unless the captured legs are EXACTLY
    (step*scale+128)>>8 for an integer scale (the caller additionally guards with an
    unrolled comparison over the note's frames)."""
    if step <= 0:
        return None
    rows = [r for r in prog if r[2] != 0]        # strip the freeze terminator
    i, delay = 0, 0
    if rows and rows[0][:2] == (0, 0):
        delay = rows[0][2]
        i = 1
    legs = rows[i:]
    if len(legs) < 3:
        return None
    # drop up to 2 trailing boundary rows (the end-of-note freq drop)
    def sval(lo, hi):
        v = lo | (hi << 8)
        return v - 0x10000 if v >= 0x8000 else v
    d0 = abs(sval(*legs[0][:2]))
    while legs and (abs(sval(*legs[-1][:2])) != d0 or legs[-1][2] > legs[0][2] + 8):
        legs.pop()
        if len(rows) - i - len(legs) > 2:
            return None
    if len(legs) < 3:
        return None
    L = legs[1][2]                               # steady leg length
    if not (1 <= L <= 126 and 1 <= legs[0][2] <= L):
        return None
    vals = [sval(lo, hi) for lo, hi, _ in legs]
    if any(abs(v) != d0 or v == 0 for v in vals):
        return None
    if any(vals[k] * vals[k + 1] >= 0 for k in range(len(vals) - 1)):
        return None                              # signs must alternate
    if any(r[2] != L for r in legs[1:-1]) or legs[-1][2] > L:
        return None
    scale = round(d0 * 256 / step)
    trunc = 0
    if not (1 <= scale <= 255) or (step * scale + 128) >> 8 != d0:
        # the ROM's depth rule is neither pure rounding nor truncation — try the
        # TRUNCATED multiply (marker bit1) before giving up
        scale = next((k for k in range(max(1, scale - 1), min(256, scale + 2))
                      if (step * k) >> 8 == d0), None)
        if scale is None:
            return None                          # no exact step fraction either way
        trunc = 2
    dir0 = (0 if vals[0] > 0 else 1) | trunc
    out = []
    if delay:
        out.append((0, 0, min(delay, 126)))
    out.append((scale, 0x40 | dir0, legs[0][2]))
    lead = len(out)
    out.append((scale, 0x40 | (dir0 ^ 1), L))
    out.append((scale, 0x40 | dir0, L))
    out.append((lead, 0, 0x7F))                  # loop over the two steady legs
    return out


def _pulse_unroll(prog, n):
    """Per-frame 12-bit pulse values a pulse program produces over n frames
    (model of pulse_step: 8X set / 0X add per frame, byte2 = frame count,
    $7f = freeze)."""
    out, cur, i = [], 0, 0
    while len(out) < n and i < len(prog):
        b0, b1, b2 = prog[i]
        if b0 == 0x7F:
            break                                # freeze: hold cur
        val12 = ((b0 & 0x0F) << 8) | b1
        for _ in range(max(1, b2)):
            if b0 & 0x80:
                cur = val12
            else:
                cur = (cur + val12) & 0xFFF
            out.append(cur)
            if len(out) >= n:
                break
        i += 1
    while len(out) < n:
        out.append(cur)
    return out


def _settle_trim(body):
    """Trim a per-frame wf list at its settle point (driver loops on the last row)."""
    settle = max((k for k in range(1, len(body)) if body[k] != body[k - 1]), default=0)
    return tuple(body[:settle + 1])


def _wave_masked_ok(prog, wfs, drv_gate_f, off_k, end):
    """True iff `prog` (driver wave program; loops on its last value), gated off
    from row-frame drv_gate_f, reproduces the captured wfs[:end] — frames in
    [off_k, drv_gate_f) are the accepted <=1-frame gate skew and are skipped."""
    for k in range(end):
        out = prog[k] if k < len(prog) else prog[-1]
        if k >= drv_gate_f:
            out &= 0xFE
        elif k >= off_k:
            continue                             # declared skew frame
        if out != wfs[k]:
            return False
    return True


def _is_struct_fm(fp):
    """True for FM programs containing SEMITONE/LOOP entries (byte2 >= $7f) —
    their pitch shape is note-relative, so the Hz-based cluster curve is
    meaningless for them; they must never be similarity-merged (they already
    dedup exactly, being pitch-independent)."""
    return any(e[2] >= 0x7F for e in fp)


def _fm_curve(fp, length=FM_CAP):
    """Cumulative FM offset shape (signed) over `length` frames (freeze-extended) —
    the audible pitch contour, for clustering distance. fp = [(lo,hi,dur),...].
    MUST cover the full program, not a prefix: same-arp notes of different DURATIONS
    are identical for their common prefix but a shorter program's tail (the captured
    end-of-note freq-0 spike, offset -> -base, then freeze) played on a longer note
    freezes the voice at freq 0 for the rest of the note — a 24-frame prefix curve
    let exactly that forced merge through (Supremacy sub2 v1, 20 silent frames)."""
    acc, cur = 0, []
    for lo, hi, dur in fp:
        off = lo | (hi << 8)
        if off >= 0x8000:
            off -= 0x10000
        for _ in range(max(1, dur)):
            acc += off
            cur.append(acc)
            if len(cur) >= length:
                return cur
    while len(cur) < length:
        cur.append(acc)
    return cur


def greedy_cluster(items, count, dist, cap, gate=None):
    """Map `items` onto <=cap representatives by greedy nearest-merge: repeatedly
    fuse the two whose merge costs the least (per-item distance * the SMALLER item's
    note count, so the loss lands on the fewest notes). dist(i,j) -> float. Returns
    (mapping[old_idx]->rep_idx_in_items, sorted_unique_reps).
    Optional gate(i,j)->bool marks INAUDIBLE merges: gated merges are always preferred,
    and an ungated (audible) merge is used only when no gated merge exists but the count
    is still over cap (a forced fallback the adaptive packer is sized to avoid)."""
    n = len(items)
    if n <= cap:
        return list(range(n)), list(range(n))
    parent = list(range(n))
    cnt = list(count)
    active = list(range(n))
    while len(active) > cap:
        best = best_gated = None
        for x in range(len(active)):
            i = active[x]
            for y in range(x + 1, len(active)):
                j = active[y]
                cost = dist(i, j) * min(cnt[i], cnt[j])
                if best is None or cost < best[0]:
                    best = (cost, x, y)
                if gate is not None and gate(i, j) and (best_gated is None or cost < best_gated[0]):
                    best_gated = (cost, x, y)
        _, x, y = best_gated if best_gated is not None else best
        i, j = active[x], active[y]
        if cnt[j] > cnt[i]:                  # keep the rep used by MORE notes
            i, j = j, i
        parent[j] = i
        cnt[i] += cnt[j]
        active.remove(j)

    def find(k):
        while parent[k] != k:
            k = parent[k]
        return k
    reps = sorted(set(find(k) for k in range(n)))
    reppos = {r: p for p, r in enumerate(reps)}
    mapping = [reppos[find(k)] for k in range(n)]
    return mapping, reps


def effective_bundle_count(items, counts, tol, cap=63):
    """How few bundles a window needs AFTER merging only INAUDIBLE pairs (same pulse
    program, FM-contour L1 <= tol). Greedy nearest-merge within tol until <=cap or no
    within-tol pair remains. The packer compares this (not the raw count) to the 63-
    bundle cap, so a window can grow past 64 raw bundles as long as the excess collapses
    losslessly. tol==0 disables (returns the raw count = lossless split behaviour)."""
    n = len(items)
    if tol <= 0 or n <= cap:
        return n
    if n > 96:                                  # bound the probe work; too big to fit anyway
        return n
    curves = [_fm_curve(fp) for fp, _ in items]
    pulses = [p for _, p in items]
    INF = 1 << 30
    D = [[0] * n for _ in range(n)]
    for i in range(n):
        ci = curves[i]
        for j in range(i + 1, n):
            if (pulses[i] != pulses[j]
                    or _is_struct_fm(items[i][0]) or _is_struct_fm(items[j][0])):
                dd = INF                     # structural programs never merge
            else:
                dd = sum(abs(a - b) for a, b in zip(ci, curves[j]))
            D[i][j] = D[j][i] = dd
    active = list(range(n))
    cnt = list(counts)
    while len(active) > cap:
        best = None
        for x in range(len(active)):
            i = active[x]
            for y in range(x + 1, len(active)):
                j = active[y]
                if D[i][j] > tol:
                    continue
                c = D[i][j] * (cnt[i] if cnt[i] < cnt[j] else cnt[j])
                if best is None or c < best[0]:
                    best = (c, x, y)
        if best is None:
            break                               # no inaudible merge left -> can't shrink
        _, x, y = best
        i, j = active[x], active[y]
        if cnt[j] > cnt[i]:
            i, j = j, i
        cnt[i] += cnt[j]
        active.remove(j)
    return len(active)


def build_native_song(m, sid, sub, idx_map, instr_rows, win=None, traces=None,
                      count_only=False):
    """Walk the MoN song -> per-voice packed sequences. Each note carries:
      - an INSTRUMENT byte ($a0-$bf) = a distinct (AD/SR/waveform + per-note WAVE
        program) — captures the waveform attack/gate envelope, which varies per note
        via the $7x wprog (so per-note, deduped into <=32 instruments);
      - a COMMAND byte ($c0-$ff) = an (FM, pulse) bundle = the note's per-frame pitch
        (slide/arp) + PWM from the trace.
    Returns (segs, bundles, instrs, wave_programs)."""
    import mon_fidelity as F
    # trace the WHOLE one-pass song length (the longest voice), else notes past the
    # window get degenerate held programs. Traces can be passed in (windowed builds
    # reuse one trace across all windows instead of re-siddumping per window).
    if traces is not None:
        frames, ftr = traces
    else:
        span = m.tick_to_frame(max(sum(ev.dur for ev in m.voices[v])
                                   for v in range(3)))
        secs = span // 50 + 4
        frames = F.per_frame(sid, [f'-a{sub}', f'-t{secs}'])
        ftr = filter_trace(sid, sub, secs)
    # The filter is ONE GLOBAL per-note cutoff ENVELOPE on the filter-routed voice;
    # it restarts on that voice's note-ons. Find those note-ons (the envelope attacks,
    # mapped back to the triggering note) -> `drives`; the span until the next restart
    # is how long each envelope program runs before re-triggering.
    delay = getattr(m, "onset_delay", 0)
    onsets = [set() for _ in range(3)]
    onset_instr = [dict() for _ in range(3)]               # onset_frame -> MoN instrument
    # STRUCTURAL WAVE (whats-next step 3): the per-note wave capture unrolls the
    # engine's attack+steady+release gate envelope, so notes of different DURATIONS
    # get distinct programs and explode the 32-instrument cap. Canonicalize per
    # (MoN instrument, wprog) to the LONGEST note's program, substituted per note
    # ONLY when its unrolled output is byte-identical over that note's frames —
    # lossless by construction (the substitution guard in the main pass).
    canon_pick = {}                              # (instr, wprog) -> (dur_f, v, fr, tk, dur)
    for v in range(3):
        tk = 0
        for ev in m.voices[v]:
            if ev.retrig:
                fr = m.tick_to_frame(tk) + delay
                onsets[v].add(fr)
                onset_instr[v][fr] = ev.instr
                dur_f = m.tick_to_frame(tk + ev.dur) - m.tick_to_frame(tk)
                k = (ev.instr, ev.wprog)
                if dur_f >= 2 and (k not in canon_pick or dur_f > canon_pick[k][0]):
                    canon_pick[k] = (dur_f, v, fr, tk, ev.dur, ev.note)
            tk += ev.dur
    canon_wave, canon_pulse, canon_fm = {}, {}, {}
    for k, (df_, v_, fr_, tk_, dur_, note_) in canon_pick.items():
        _gt, wfs_, offk_, end_ = _gate_split(m, frames, v_, fr_, df_, tk_, dur_)
        if offk_ is not None:
            canon_wave[k] = _settle_trim(wfs_[:offk_])
        else:
            canon_wave[k] = _wave_prog_for(frames, v_, fr_, df_)
        # STRUCTURAL PULSE (step 4): a shorter note's captured program is a PREFIX
        # of the longest note's when the sweep restarts per note — substituting the
        # canonical is exact when the unrolled outputs match over the note's frames
        # (minus the 1-frame boundary bleed; guard in the main pass).
        canon_pulse[k] = pulse_program_for(frames, v_, fr_, df_)
        # STRUCTURAL FM for NON-arp notes: the capture tail holds the duration-
        # relative end-of-note freq drop (offset -> -base), so same-contour notes
        # of different durations get distinct programs. Hz offsets are relative to
        # the note's own base (pitch-independent contours), so one canonical
        # serves all pitches; guard = contour equality minus ~3 boundary frames.
        nb_ = max(SF2_NOTE_MIN, min(note_, SF2_NOTE_MAX))
        canon_fm[k] = fm_program_for(frames, v_, fr_, df_, m.note_freq(nb_))

    # FREE-RUNNING PULSE (the 45s+ binding constraint): some MoN sweeps never
    # reset — each note continues the previous note's phase, so per-note captures
    # get a distinct set-row start per note. Detect phase drift per voice (a key
    # with >= 3 distinct set-row starts) and emit ONE per-voice STREAM program
    # (the whole window's per-frame pulse, RLE'd) shared by every note on the
    # voice; the driver's VIFLAGS $08 keeps PPTR across note-ons (PFREE latch).
    # Only when the voice's instruments are not shared with other voices (the
    # $08 flag lives in the shared instrument record).
    t0w, t1w = win if win else (0, 1 << 30)
    freerun = [None, None, None]
    if ARP_STRUCT:
        vkeys, vnotes = [set() for _ in range(3)], [[] for _ in range(3)]
        starts = {}
        for v in range(3):
            tk = 0
            for ev in m.voices[v]:
                fr = m.tick_to_frame(tk) + delay
                dur_f = m.tick_to_frame(tk + ev.dur) - m.tick_to_frame(tk)
                if ev.retrig and t0w <= fr < t1w and dur_f >= 2:
                    vkeys[v].add((ev.instr, ev.wprog))
                    vnotes[v].append((fr, dur_f))
                    pv = frames[fr][0][v]['pul'] if fr < len(frames) else None
                    starts.setdefault((v, ev.instr, ev.wprog), set()).add(pv)
                tk += ev.dur
        for v in range(3):
            drift = any(len(starts.get((v,) + k, ())) >= 3 for k in vkeys[v])
            shared = vkeys[v] & (vkeys[(v + 1) % 3] | vkeys[(v + 2) % 3])
            if drift and not shared and vnotes[v]:
                on0 = vnotes[v][0][0]
                span = min(t1w, vnotes[v][-1][0] + vnotes[v][-1][1]) - on0
                stream = pulse_program_for(frames, v, on0, span, cap=span)
                if len(stream) <= 700:           # sanity: keep PULSETAB bounded
                    freerun[v] = stream
    routed = routed_voice(ftr)                              # restart only on this voice
    drive_map = detect_filter_drives(ftr, onsets, routed)   # {onset_frame: voice}
    drives = {(v, o) for o, v in drive_map.items()}
    drive_frames = sorted(drive_map)

    def _gap(onset):
        j = bisect.bisect_right(drive_frames, onset)
        return (drive_frames[j] - onset) if j < len(drive_frames) else 220

    # The cutoff envelope restarts on each drive (a note-on-aligned restart, correctly
    # found by detect_filter_drives) and is deterministic from there. Capture ONE canonical
    # program per (MoN instrument, envelope shape), from the FULLEST (longest-span) drive of
    # that key. The capture starts at the drive onset (phase-correct, as the original did —
    # the driver restarts on the same note frame) and runs the full span to the next drive
    # so the whole ramp->sustain is captured (short notes reuse it, truncated by the driver's
    # per-note restart). NB: the shape signature reads one frame PAST the onset to skip the
    # note-on frame's transitional value.
    nftr = len(ftr)

    def _shape_sig(o):
        """Length-invariant shape signature (settled attack-base hi, initial delta hi)
        read from o+1 to skip the note-on frame's transitional cutoff."""
        s = min(o + 1, nftr - 1)
        base = ftr[s][0] >> 3
        d = 0
        for k in range(1, min(4, nftr - s)):
            d = (ftr[s + k][0] >> 3) - base
            if d:
                break
        return (base & 0xF8, max(-8, min(8, d)))

    # Key the canonical by the composite (MoN instrument, shape): this unifies the two
    # regimes. When a tune's filter shape is fixed per instrument (Hawkeye — each instrument
    # selects one sel-table), (instr, shape) collapses to per-instrument. When an instrument
    # plays across sections with different envelopes (Myth sub0), it splits into one
    # canonical per shape it actually uses, so each note gets its own section's envelope.
    canon_src = {}                                        # (instr, shape) -> (onset, span)
    drive_key = {}                                        # drive onset -> (instr, shape)
    for o, v in drive_map.items():
        key = (onset_instr[v].get(o, -1), _shape_sig(o))
        drive_key[o] = key
        span = _gap(o)
        if key not in canon_src or span > canon_src[key][1]:
            canon_src[key] = (o, span)
    canon_prog = {key: filter_program_for(ftr, o, span)
                  for key, (o, span) in canon_src.items()}
    canon_filt = {o: canon_prog[drive_key[o]] for o in drive_key}         # keyed by onset
    if os.environ.get("FILT_DEBUG"):
        print(f"  [FILT_DEBUG] drives={len(drive_frames)} canon={len(canon_src)} "
              f"routed={routed}")
        for (i, sig), (o, span) in sorted(canon_src.items()):
            flag, prog = canon_prog[(i, sig)]
            print(f"    instr {i} shape base={sig[0]} d={sig[1]:+d}: onset={o} span={span} "
                  f"rows={len(prog) if prog else 0}")
    # --- PASS 1: collect EXACT bundles + instruments (with note counts) + per-note records
    exb, bidx, bcount = [], {}, []          # exact (fm,pulse) bundles
    exi, iidx, icount = [], {}, []          # exact (ad,sr,raw,wave,flag,filt) instruments
    note_recs = [[] for _ in range(3)]      # per voice: list of blocks; each = list of notes

    def bundle_of(fp, pp):
        k = (tuple(fp), tuple(pp))
        if k not in bidx:
            bidx[k] = len(exb)
            exb.append((fp, pp))
            bcount.append(0)
        bcount[bidx[k]] += 1
        return bidx[k]

    def instr_of(mon_i, wp, flag, filt):
        ins = m.instrument(mon_i)
        ad, sr, raw = ins['ad'], ins['sr'], ins['waveform'] or 0x41
        key = (ad, sr, raw, wp, flag, tuple(filt) if filt else None)
        if key not in iidx:
            iidx[key] = len(exi)
            exi.append((ad, sr, raw, _rle_wave(wp), flag, filt))
            icount.append(0)
        icount[iidx[key]] += 1
        return iidx[key]

    t0, t1 = win if win else (0, 1 << 30)
    for v in range(3):
        tk = 0
        for _pat, events in m._voice_blocks(v):
            blk = []
            for ev in events:
                fr = m.tick_to_frame(tk) + delay
                dur_f = m.tick_to_frame(tk + ev.dur) - m.tick_to_frame(tk)
                if not (t0 <= fr < t1):                       # outside the window
                    tk += ev.dur
                    continue
                if getattr(ev, 'rest', False):                # REST: gate-off rows only
                    blk.append((None, ev.dur, None, None, tk, 0))
                    tk += ev.dur
                    continue
                ticks = ev.dur
                while ticks > 1 and (m.tick_to_frame(tk + ticks)
                                     + delay) > t1:           # clip the last note to the window
                    ticks -= 1
                # base = the freq the DRIVER plays for the (clamped) note, so the FM
                # offsets reconstruct exactly. Use the clamped note for the base too —
                # else a note clamped to SF2_NOTE_MIN (e.g. MoN's $00 silent note) drifts
                # the whole note's freq by note_freq(clamped)-note_freq(raw).
                note_c = max(SF2_NOTE_MIN, min(ev.note, SF2_NOTE_MAX))
                base = m.note_freq(note_c)
                flag, filt = (canon_filt.get(fr, (0, None))
                              if (v, fr) in drives else (0, None))
                fmp = fm_program_for(frames, v, fr, dur_f, base)
                fcmp = max(1, dur_f - 3)
                arp = _arp_fm_for(m, ev)
                if arp is not None:
                    # SEMITONE-level guard: the $60-$7F selector is not always a
                    # pitch arp (sub1 v0's wprog $14 is a wave shape — unguarded
                    # arps broke its osc1 to 32%), but detuned notes (the canon
                    # voices) differ from the pure arp by a constant few Hz at
                    # EVERY frame while sounding identical. Accept when the arp
                    # matches the capture on the audible semitone grid minus the
                    # per-note onset-spike frames; a wrong arp shape differs by
                    # whole semitones and is rejected.
                    cap_u = _fm_unroll(fmp, fcmp)
                    arp_u = _fm_unroll_full(arp, fcmp, m, note_c)

                    def _s(off):
                        return freq_to_semi((base + (off - 0x10000 if off >= 0x8000
                                                     else off)) & 0xFFFF)
                    bad = sum(1 for a, b in zip(cap_u, arp_u) if _s(a) != _s(b))
                    if bad <= max(4, dur_f // 8):
                        fmp = arp
                if not _is_struct_fm(fmp):
                    if ARP_STRUCT and getattr(ev, 'slide', None):
                        sl = _slide_fm_program(m, ev, note_c, fmp, dur_f)
                        if sl is not None:
                            fmp = sl
                    if ARP_STRUCT and not _is_struct_fm(fmp):
                        # pitch-proportional VIBRATO -> one looping SCALED program
                        # for every pitch/duration (exact-guarded via unroll)
                        step = m.note_freq((note_c + 1) & 0x7F) - base
                        vib = _vibrato_program(fmp, step) if step > 0 else None
                        if (vib is not None
                                and _fm_unroll(vib, fcmp, step) == _fm_unroll(fmp, fcmp)):
                            fmp = vib
                    cf = canon_fm.get((ev.instr, ev.wprog))
                    if (ARP_STRUCT and cf is not None and cf != fmp
                            and not _is_struct_fm(fmp) and not _is_struct_fm(cf)
                            and _fm_unroll(cf, fcmp) == _fm_unroll(fmp, fcmp)):
                        fmp = cf
                if freerun[v] is not None:
                    pp = freerun[v]               # one per-voice stream, phase kept
                    flag |= 0x08                  # driver: no pulse reset on note-on
                else:
                    pp = pulse_program_for(frames, v, fr, dur_f)
                    cp = canon_pulse.get((ev.instr, ev.wprog))
                    # compare minus the last frame: the capture's final frame holds
                    # the NEXT note's base reset (the same 1-frame register skew as
                    # the wave bleed) — the note's own program reproduces that bleed,
                    # the canonical continues the sweep instead (<=1 frame/note)
                    cmp_f = max(1, dur_f - 1)
                    if (ARP_STRUCT and cp is not None and cp != pp
                            and _pulse_unroll(cp, cmp_f) == _pulse_unroll(pp, cmp_f)):
                        pp = cp
                bi = bundle_of(fmp, pp)
                gate_ticks, wfs_c, off_k, end_c = _gate_split(m, frames, v, fr,
                                                              dur_f, tk, ticks)
                cw = canon_wave.get((ev.instr, ev.wprog))
                drv_gate = m.tick_to_frame(tk + gate_ticks) - m.tick_to_frame(tk)
                skew0 = off_k if off_k is not None else end_c
                if (cw is not None and wfs_c is not None
                        and _wave_masked_ok(cw, wfs_c, drv_gate, skew0, end_c)):
                    wp = cw                       # canonical reproduces this note's capture
                elif off_k is not None:
                    wp = _settle_trim(wfs_c[:off_k])
                else:
                    # keep the full capture INCLUDING the trailing next-note attack
                    # bleed: reproducing it is byte-better (osc3 wf 97.8 vs 91.6
                    # trimmed — measured); the "phantom onset" it causes in onset
                    # metrics is a metric artifact, not a register error.
                    wp = _wave_prog_for(frames, v, fr, dur_f)
                ii = instr_of(ev.instr, wp, flag, filt)
                blk.append((note_c, ticks, bi, ii, tk, gate_ticks))
                tk += ev.dur
            if blk:
                note_recs[v].append(blk)

    # Adaptive packing probes the PRE-cluster resource counts for a candidate window
    # (cheap: pass-1 only, no clustering / assemble) to grow windows up to the caps.
    # Returns (#bundles, #instruments, #wave-rows, #filter-rows, #sequences). The two
    # row counts are the deduped totals laid into the 256-row WAVE/FILTER tables; the
    # sequence count is the total packed sequences across all voices (the native
    # driver's seq-pointer table holds 128 — overflow corrupts the LAST voice, osc3).
    if count_only:
        wkeys, wrows, fkeys, frows = set(), 0, set(), 0
        for _ad, _sr, _raw, waveprog, _flag, filt in exi:
            wk = tuple(waveprog)
            if wk not in wkeys:
                wkeys.add(wk)
                wrows += len(waveprog)
            if filt:
                fk = tuple(filt)
                if fk not in fkeys:
                    fkeys.add(fk)
                    frows += len(filt)
        # mirror pass-2's row build (raw indices — exact while under the cluster caps,
        # where the cluster map is the identity) to count sequences accurately.
        nseg = 0
        for v in range(3):
            first = True
            for blk in note_recs[v]:
                rows = []
                if win and first and blk:
                    lead = blk[0][4] - m.frame_to_tick(max(0, t0 - delay))
                    rows.extend(D11Row(note=0x00) for _ in range(max(0, lead)))
                first = False
                cur_inst = cur_cmd = None
                for note, dur, bi, ii, _ontk, gate in blk:
                    if note is None:                          # REST -> gate-off rows
                        rows.extend(D11Row(note=0x00) for _ in range(dur))
                        continue
                    rows.append(D11Row(note=note,
                                       instrument=ii if ii != cur_inst else None,
                                       command=bi if bi != cur_cmd else None))
                    cur_inst, cur_cmd = ii, bi
                    rows.extend(D11Row(note=SF2_GATE_ON) for _ in range(max(0, gate - 1)))
                    rows.extend(D11Row(note=0x00) for _ in range(max(0, dur - gate)))
                nseg += len(segment_track(rows))
        # effective (not raw) bundle count: a window can grow past 64 raw bundles if the
        # excess merges away inaudibly (see effective_bundle_count / BUNDLE_TOL).
        nb = effective_bundle_count(exb, bcount, BUNDLE_TOL)
        return nb, len(exi), wrows, frows, nseg

    # --- CLUSTER to fit the driver caps (64 commands, 32 instruments) ---
    bcurves = [_fm_curve(fp) for fp, _ in exb]

    stream_set = {tuple(s) for s in freerun if s}

    def bdist(i, j):
        if _is_struct_fm(exb[i][0]) or _is_struct_fm(exb[j][0]):
            return 1 << 20                    # structural programs: never force-merge
        pi, pj = tuple(exb[i][1]), tuple(exb[j][1])
        if pi != pj and (pi in stream_set or pj in stream_set):
            return 1 << 20                    # never merge a free-run STREAM bundle away
        fd = sum(abs(a - b) for a, b in zip(bcurves[i], bcurves[j]))
        pp = 0 if exb[i][1] == exb[j][1] else 300
        return fd + pp

    def idist(i, j):
        a, b = exi[i], exi[j]
        d = abs(a[0] - b[0]) + abs(a[1] - b[1]) + (200 if a[2] != b[2] else 0)
        d += 60 * sum(1 for x, y in zip(a[3], b[3]) if x != y) + 60 * abs(len(a[3]) - len(b[3]))
        d += 0 if (a[4] == b[4] and a[5] == b[5]) else 150
        return d

    def bgate(i, j):                         # an INAUDIBLE bundle merge: same pulse +
        if exb[i][1] != exb[j][1]:           # FM-contour L1 within tolerance
            return False                     # (also protects free-run stream bundles)
        if _is_struct_fm(exb[i][0]) or _is_struct_fm(exb[j][0]):
            return False                     # structural programs never gate-merge
        return sum(abs(a - b) for a, b in zip(bcurves[i], bcurves[j])) <= BUNDLE_TOL
    bmap, breps = greedy_cluster(exb, bcount, bdist, 63, gate=bgate if BUNDLE_TOL > 0 else None)
    imap, ireps = greedy_cluster(exi, icount, idist, 32)
    bundles = [exb[r] for r in breps]
    instrs = [exi[r][:3] for r in ireps]
    wave_programs = [exi[r][3] for r in ireps]
    instr_flags = [exi[r][4] for r in ireps]
    filter_programs = [exi[r][5] for r in ireps]

    # --- PASS 2: emit rows with the clustered indices ---
    segs = [[] for _ in range(3)]
    for v in range(3):
        first = True
        for blk in note_recs[v]:
            rows = []
            if win and first and blk:                        # leading rest to position the
                lead = blk[0][4] - m.frame_to_tick(max(0, t0 - delay))   # window's first note tick
                rows.extend(D11Row(note=0x00) for _ in range(max(0, lead)))
            first = False
            cur_inst = cur_cmd = None
            for note, dur, bi, ii, _ontk, gate in blk:
                if note is None:                              # REST -> gate-off rows
                    rows.extend(D11Row(note=0x00) for _ in range(dur))
                    continue
                slot, cmd = imap[ii], bmap[bi]
                rows.append(D11Row(note=note,
                                   instrument=slot if slot != cur_inst else None,
                                   command=cmd if cmd != cur_cmd else None))
                cur_inst, cur_cmd = slot, cmd
                rows.extend(D11Row(note=SF2_GATE_ON) for _ in range(max(0, gate - 1)))
                rows.extend(D11Row(note=0x00) for _ in range(max(0, dur - gate)))
            for pk in segment_track(rows):
                segs[v].append(pk)
    return segs, bundles, instrs, wave_programs, instr_flags, filter_programs


def emit_one(m, br, out_path, label):
    """Assemble + wrap one build result (segs, bundles, instrs, ...) into an SF2."""
    segs, bundles, instrs, wave_programs, instr_flags, filter_programs = br
    pulse_programs = [static_pulse(0x800) for _ in instrs]
    B.GAL = MON_DIR
    B.TEMPO = m.frames_per_tick
    # swing tunes (Supremacy $80 speed flag): the driver's row grid alternates
    # TEMPO2 (short) / TEMPO (long), matching MON.tick_to_frame. Constant tunes
    # set TEMPO2 == TEMPO (the driver toggle is inert).
    B.TEMPO2 = m.speed if getattr(m, "tempo_toggle", False) else m.frames_per_tick
    nfilt = sum(1 for f in instr_flags if f & 0x40)
    flags = ""
    if len(bundles) > 64:
        flags += " BUNDLES>64"
    if len(instrs) > 32:
        flags += " INSTR>32"
    gen, edit, mdp, seq0 = RN.gen_includes_song(segs, instrs, wave_programs,
                                                pulse_programs, bundles=bundles,
                                                instr_flags=instr_flags,
                                                filter_programs=filter_programs)
    shutil.copyfile(os.path.join(ROM_DIR, "layout.inc"), os.path.join(MON_DIR, "layout.inc"))
    write_mon_freqtable(m)
    prg = B.assemble()
    sf2 = B.wrap(prg, gen, edit, mdp, instr_names=[f"instr {i}" for i in range(len(instrs))])
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    open(out_path, "wb").write(sf2)
    from sidm2.models import SF2DriverInfo
    from sidm2 import sf2_parser
    di = SF2DriverInfo()
    pla = sf2_parser.parse_sf2_blocks(bytearray(sf2), di)
    if gen.filter_addr >= 0xC000:                # approaching the $D000 memory wall
        flags += " MEMWALL"
    print(f"  {label}: instr={len(instrs)} bundles={len(bundles)} filter={nfilt} "
          f"{len(sf2)}B top~${gen.filter_addr:04X} parse={'OK' if pla == B.LOAD_BASE else 'FAIL'}{flags}")
    return gen.filter_addr


def main():
    sid = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, "SID", "Tel_Jeroen", "Hawkeye.sid")
    sub = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    # 3rd arg: a number N = fixed N-second windows; "auto" = adaptive max-size windows
    # (grow each window right up to the driver caps -> fewest files, NO clustering loss);
    # absent/0 = whole song in one file.
    warg = sys.argv[3] if len(sys.argv) > 3 else "0"
    adaptive = warg.lower() in ("auto", "a", "-1")
    winsec = 0 if adaptive else int(warg)

    d, la, _ = load_sid(sid)
    m = MON(d, la, sub)
    used = mon_to_sf2.used_instruments(m)
    instr_rows, wave_table, pulse_table, idx_map = mon_to_sf2.build_instruments(m, used)
    base = os.path.splitext(os.path.basename(sid))[0]
    print(f"{os.path.basename(sid)} sub{sub}: load=${la:04X}")

    if adaptive or winsec > 0:
        import mon_fidelity as F
        span = m.tick_to_frame(max(sum(ev.dur for ev in m.voices[v])
                                   for v in range(3)))
        secs = span // 50 + 4
        print(f"  tracing full song ({secs}s) once...")
        traces = (F.per_frame(sid, [f'-a{sub}', f'-t{secs}']), filter_trace(sid, sub, secs))

        if adaptive:
            # Greedily grow each window to the largest span whose PRE-cluster resource
            # counts still fit ALL the driver caps (so the build stays clustering-free
            # AND no table overflows = byte-exact), probing with the cheap count_only
            # path. Caps: <=63 bundles, <=32 instruments (greedy_cluster identity
            # thresholds) and <=256 rows in each of the WAVE / FILTER tables.
            # Caps: bundles, instruments, WAVE/FILTER table rows, and total sequences
            # (the native seq-pointer table = 128 entries; 120 leaves margin so osc3,
            # laid last, never overflows).
            CAP_B, CAP_I, CAP_TBL, CAP_SEG, STEP = 63, 32, 256, 120, 100   # 2s probe step

            def fits(t0, t1):
                nb, ni, nw, nf, ns = build_native_song(
                    m, sid, sub, idx_map, instr_rows, win=(t0, t1),
                    traces=traces, count_only=True)
                return (nb <= CAP_B and ni <= CAP_I and nw <= CAP_TBL
                        and nf <= CAP_TBL and ns <= CAP_SEG)

            bounds, t0 = [], 0
            while t0 < span:
                t1 = min(t0 + STEP, span)
                while t1 < span and fits(t0, min(t1 + STEP, span)):
                    t1 = min(t1 + STEP, span)
                bounds.append((t0, t1))
                t0 = t1
            was30 = (span + 1499) // 1500
            print(f"  packed into {len(bounds)} adaptive parts (vs {was30} at fixed 30s)")
        else:
            winf = winsec * 50
            bounds = [(t0, min(t0 + winf, span)) for t0 in range(0, span, winf)]

        nparts = len(bounds)
        for part, (t0, t1) in enumerate(bounds, 1):
            br = build_native_song(m, sid, sub, idx_map, instr_rows,
                                   win=(t0, t1), traces=traces)
            out = os.path.join(ROOT, "out", "mon", f"{base}_sub{sub}_part{part:02d}.sf2")
            emit_one(m, br, out, f"part {part}/{nparts} ({t0 // 50}-{t1 // 50}s)")
        return

    br = build_native_song(m, sid, sub, idx_map, instr_rows)
    out = os.path.join(ROOT, "out", "mon", f"{base}_sub{sub}_native.sf2")
    emit_one(m, br, out, f"{base}_sub{sub}")


if __name__ == "__main__":
    main()
