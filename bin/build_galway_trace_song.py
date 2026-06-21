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


def extract_filter_program(song, sid_path, init, play, subtune):
    """Reproduce the tune's REAL filter (was hardcoded to Wizball's). Galway runs
    one routed voice through a resonant low-pass whose cutoff RESETS and sweeps on
    each note (a per-note "pluck"). Returns (filter_rows, routed_voice):

    - routed_voice: the SID voice whose notes restart the filter (from $D417's
      routing nibble) — the build flags its instruments $40.
    - filter_rows: the cutoff envelope as per-frame SET rows
      `(0x90|mode, cutoff, res:route)` captured at a representative routed-voice
      note, then a $7f freeze. One SET per frame reproduces the envelope EXACTLY
      (it's only ~12 frames before the next note restarts it); the driver's
      filt_prog_step writes $D415/6 (cutoff) + $D417 (res/route) + $D418 mode.

    Returns (None, None) when the tune uses no filter (routing nibble 0)."""
    import struct
    from collections import Counter
    from py65.devices.mpu6502 import MPU
    rescnt = Counter(r for r in song.filt_res if r)
    if not rescnt:
        return None, None
    rb = rescnt.most_common(1)[0][0]            # $D417 = res<<4 | routing
    route = rb & 0x0F
    rv = next((v for v in range(3) if route & (1 << v)), None)
    if rv is None or not song.voices[rv].active:
        return None, None
    # $D418 mode bits are set at INIT (not in the play trace) — emulate init to read.
    d = open(sid_path, "rb").read()
    off = struct.unpack(">H", d[6:8])[0]; la = struct.unpack(">H", d[8:0x0A])[0]
    body = d[off:]
    if la == 0:
        la = body[0] | (body[1] << 8); body = body[2:]
    m = MPU()
    for i, b in enumerate(body):
        m.memory[(la + i) & 0xFFFF] = b
    m.memory[0x1FF] = 0xFE; m.memory[0x1FE] = 0xFF; m.sp = 0xFD; m.pc = init; m.a = subtune
    for _ in range(3000000):
        if m.pc == 0xFF00:
            break
        m.step()
    mode_bits = (m.memory[0xD418] >> 4) & 7      # SID filter mode (1=LP, 2=BP, 4=HP)
    if not mode_bits:
        mode_bits = 1                            # default low-pass
    # capture the cutoff envelope at a representative routed-voice note (skip the
    # first, which can be atypical); 24 frames covers the sweep + the slow tail.
    onsets = [n.onset for n in song.voices[rv].notes if not n.tie]
    if not onsets:
        return None, None
    on = onsets[min(2, len(onsets) - 1)]
    d416 = [(song.filt_cutoff[fr] >> 8) & 0xFF
            for fr in range(on, min(on + 24, song.frames))]
    hi = (0x8 | mode_bits) << 4                  # byte0 high nibble: set-bit + mode
    rows = [(hi | (c >> 4), (c & 0x0F) << 4, rb) for c in d416]
    rows.append((0x7F, 0, len(rows)))            # self-jump = freeze (hold last cutoff)
    return rows, rv


def pulse_program(seg, step):
    """Encode the real per-play-call pulse-width envelope as an ADD-based program:
    one 8X 'set width' at the start value, then a 0X 'add delta' command spanning
    each run of CONSTANT per-frame delta, then a $7f freeze. Galway's pulse is a
    smooth linear sweep (e.g. lead: $064 + $46/frame), so a whole ramp collapses
    to ONE add row — reproduced at full per-frame resolution (the old 8X-set
    downsampling aliased the smooth ramp into a 4-frame staircase, pulse 62%) and
    far more compact. The driver restarts the pulse program on each note trigger,
    so the per-note reset is automatic. Negative deltas use 12-bit two's
    complement (the driver's 12-bit add wraps correctly). `step` downsamples (every
    `step`th frame) only as a fallback to fit the 256-row table on pathological
    envelopes; step=1 is exact."""
    if not seg:
        return [(0x7F, 0, 0)]
    pts = list(seg[::step]) if step > 1 else list(seg)
    v0 = pts[0]
    if len(pts) == 1:
        return [(0x80 | ((v0 >> 8) & 0x0F), v0 & 0xFF, 1), (0x7F, 0, 1)]
    rows = [(0x80 | ((v0 >> 8) & 0x0F), v0 & 0xFF, 1)]   # set start (holds 1 frame)
    i = 1
    while i < len(pts):
        delta = pts[i] - pts[i - 1]
        j = i
        while j < len(pts) and (pts[j] - pts[j - 1]) == delta:
            j += 1
        run = (j - i) * step                          # frames this delta spans
        d12 = delta & 0xFFF                            # 12-bit two's complement
        b0, b1 = (d12 >> 8) & 0x0F, d12 & 0xFF         # 0X add (bit7 clear)
        while run > 255:
            rows.append((b0, b1, 255))
            run -= 255
        if run > 0:
            rows.append((b0, b1, run))
        i = j
    rows.append((0x7F, 0, len(rows)))                  # freeze (holds last value)
    return rows


def _add_linear_pulse(seg, tol):
    """Approximate a pulse series by piecewise-linear, integer-slope ADD segments
    (one row per segment) kept within `tol` of the real value. Correct where naive
    step-downsampling is not: the segment slope IS the per-frame add, so it never
    over-applies (skipping samples and adding the step-spanning delta every frame
    ramps `step`x too fast). Greedy longest-run: at each point pick the integer
    slope that stays within `tol` for the most frames. Compresses both the lead's
    fast sweep AND a slow accompaniment ramp to few rows, so a 2-minute song's
    pulse fits the shared 256-row table."""
    n = len(seg)
    if n == 0:
        return [(0x7F, 0, 0)]
    v = seg[0]
    rows = [(0x80 | ((v >> 8) & 0x0F), v & 0xFF, 1)]   # set start (holds frame 0)
    cur, i = v, 1
    while i < n:
        # candidate slopes ADAPTED to the signal (local average over several
        # windows + the immediate gap) so a steep jump gets a steep slope without
        # a huge brute-force search; a fixed small range explodes on big deltas.
        cand_d = {seg[i] - cur}
        for w in (1, 2, 4, 8, 16, 32, 64):
            if i - 1 + w < n:
                cand_d.add(round((seg[i - 1 + w] - seg[i - 1]) / w))
        best_d, best_len = 0, 0
        for d in cand_d:
            d = max(-0x7ff, min(0x7ff, d))
            val, k = cur, 0
            while i + k < n:
                val += d
                if abs(val - seg[i + k]) > tol:
                    break
                k += 1
            if k > best_len:
                best_len, best_d = k, d
        if best_len == 0:                              # can't stay in tol -> 1-frame jump
            best_len, best_d = 1, max(-0x7ff, min(0x7ff, seg[i] - cur))
        run, d12 = best_len, best_d & 0xFFF
        b0, b1 = (d12 >> 8) & 0x0F, d12 & 0xFF          # 0X add (bit7 clear)
        while run > 255:
            rows.append((b0, b1, 255)); run -= 255
        rows.append((b0, b1, run))
        cur += best_d * best_len
        i += best_len
    rows.append((0x7F, 0, len(rows)))                  # self-jump = freeze
    return rows


def _set_stride_pulse(seg, budget):
    """Guaranteed-fit fallback: a SET staircase sampled at a fixed stride so the
    program is always <= `budget` rows. Coarse in value but correctly TIMED (each
    SET holds its real sample for `stride` frames — no over-apply), and it tracks
    the real envelope's shape. Used only when a multi-minute voice's pulse is too
    complex for any in-tolerance fit (the lead's continuous PWM over 2+ minutes
    has more slope changes than the shared 256-row table can hold)."""
    n = len(seg)
    if n == 0:
        return [(0x7F, 0, 0)]
    stride = max(1, -(-n // max(1, budget - 1)))       # ceil(n / (budget-1))
    rows = []
    for s in range(0, n, stride):
        v = seg[s]
        rows.append((0x80 | ((v >> 8) & 0x0F), v & 0xFF, min(stride, n - s)))
    rows.append((0x7F, 0, len(rows)))                  # self-jump = freeze
    return rows


def _set_threshold_pulse(seg, thresh):
    """SET-staircase encoding of a pulse series: hold one absolute width until the
    real value drifts more than `thresh` from it, then set the new value. The
    staircase stays within `thresh` of the real envelope everywhere (pick
    thresh < the tool/ear pulse tolerance $80), and a slow wide ramp collapses to
    ~range/(2*thresh) rows regardless of length — the add engine can't, because it
    adds an integer EVERY frame so it can't render a sub-1/frame slope without
    over-applying."""
    rows, i, n = [], 0, len(seg)
    while i < n:
        anchor = seg[i]
        j = i + 1
        while j < n and abs(seg[j] - anchor) <= thresh:
            j += 1
        b0, b1, ln = 0x80 | ((anchor >> 8) & 0x0F), anchor & 0xFF, j - i
        while ln > 255:
            rows.append((b0, b1, 255)); ln -= 255
        rows.append((b0, b1, ln))
        i = j
    rows.append((0x7F, 0, len(rows)))                # self-jump = freeze
    return rows


def faithful_pulse_program(seg, max_rows=80):
    """Encode a pulse SEGMENT (one gate-region's real per-frame pulse) faithfully,
    fitting `max_rows`. The driver restarts the pulse on each gate-on (VPI=VIPULSE,
    VPC=0) and free-runs it across the region's legato ties, so ONE program per
    gate-region reproduces that region's pulse in phase.

    A smooth fast sweep (the lead) compresses exactly with the add-based RLE, so
    use it whenever it fits. A slow wide ramp (the accompaniment) explodes the
    add-RLE — per-frame SID 12-bit quantization stores a +0.5/frame slope as a
    +1,0,+1,0 dither (1-frame runs) AND the add engine can't reproduce a sub-1/
    frame slope without over-applying — so fall back, finest-first, to linear
    integer-slope add-fits then SET staircases within the $80 pulse tolerance, and
    finally a guaranteed-fit stride staircase."""
    if not seg:
        return [(0x7F, 0, 0)]
    exact = pulse_program(seg, 1)                    # exact per-frame add (best for sweeps)
    if len(exact) <= max_rows:
        return exact
    cands = ([_add_linear_pulse(seg, tol) for tol in (16, 24, 32, 48, 64, 96, 128)] +
             [_set_threshold_pulse(seg, th) for th in (16, 32, 48, 64, 96)])
    for c in cands:
        if len(c) <= max_rows:
            return c
    return _set_stride_pulse(seg, max_rows)          # guaranteed-fit coarse fallback


def faithful_legato_pulse_program(series, on0, max_rows=80, end=None):
    """Thin wrapper: faithfully encode `series[on0:end]` (a gate-region, or the
    whole voice when it gates once)."""
    return faithful_pulse_program(series[on0:end], max_rows)


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


FLAT_DEV = 16        # within-note pitch deviation (SID units) treated as "flat"


def fm_program(note, flat_dev=FLAT_DEV):
    """Build a row-major FM program carrying the note's within-note pitch
    MODULATION (slide/vibrato) relative to its base note, as RLE'd per-frame
    deltas (runs split to the 1-byte dur) + a (0,0,0) freeze terminator. Each
    entry is (offset_lo, offset_hi, dur); fm_step adds `offset` to the voice
    frequency each frame for `dur` frames.

    The note's PITCH comes from the note byte (nb) in the sequence; the FM only
    carries the relative modulation, and the per-note sub-semitone correction is
    dropped. That lets notes sharing a modulation SHAPE share one instrument
    (and flat notes collapse to a single no-FM instrument) — essential for
    melodic tunes (1000s of notes) to fit the 32-instrument table. Pitch stays
    semitone-accurate (correct for a chromatic melody)."""
    nb = freq_to_note(note.base_freq)
    recon = T.reconstruct_freq(note)
    dev = max((abs(f - note.base_freq) for f in recon), default=0)
    # Detect arp/vibrato = NON-monotonic pitch motion (goes both up and down).
    # Always keep its FM so raising the flat threshold (to fit the instrument
    # table) flattens only monotonic slides/flat notes, never arpeggios.
    arp = False
    if len(recon) > 2:
        up = any(recon[i] > recon[i - 1] for i in range(1, len(recon)))
        dn = any(recon[i] < recon[i - 1] for i in range(1, len(recon)))
        arp = up and dn
    if dev <= flat_dev and not arp:
        return nb, [(0, 0, 0)]                        # flat/slide note: no FM (shared)
    entries = []
    for d, run in note.fm:
        while run > 255:
            entries.append((d & 0xFF, (d >> 8) & 0xFF, 255))
            run -= 255
        if run > 0:
            entries.append((d & 0xFF, (d >> 8) & 0xFF, run))
    entries.append((0, 0, 0))                        # freeze terminator
    return nb, entries


def fm_curve(fm, npts=5):
    """Sample the cumulative pitch-offset curve of an FM shape at npts positions
    across its active span — a shape signature that captures the slide CONTOUR
    (not just its endpoint, so a vibrato that settles near 0 doesn't collide with
    a flat note or a monotonic slide)."""
    seq, acc = [], 0
    for lo, hi, dur in fm:
        off = lo | (hi << 8)
        if off >= 0x8000:
            off -= 0x10000
        for _ in range(min(dur or 1, 300)):
            acc += off
            seq.append(acc)
    if not seq:
        return (0,) * npts
    return tuple(seq[min(len(seq) - 1, (i * len(seq)) // npts)] for i in range(npts))


def fm_sig(fm, fmq):
    """Cluster key for an FM shape: flat notes are their own class; slides are
    bucketed by their quantised contour. Larger fmq merges more similar slides
    into one shared instrument (a near-inaudible pitch approximation), which frees
    instrument slots WITHOUT coarsening AD/SR (the audible timbre)."""
    if fm == [(0, 0, 0)]:
        return ("flat",)
    if fmq <= 1:
        return tuple(fm)
    return tuple(round(x / fmq) for x in fm_curve(fm))


def main():
    sid = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, "SID", "Galway_Martin", "Wizball.sid")
    frames = int(sys.argv[2]) if len(sys.argv) > 2 else 1800
    h = SIDParser(sid).parse_header()
    subtune = int(sys.argv[3]) if len(sys.argv) > 3 else (h.start_song or 1) - 1
    song = T.extract(sid, frames, h.init_address, h.play_address, subtune)
    # Per-tune FILTER: reproduce the real cutoff envelope + routing (was hardcoded
    # to Wizball's). filt_voice = the routed voice whose instruments restart it.
    filt_prog, filt_voice = extract_filter_program(
        song, sid, h.init_address, h.play_address, subtune)
    # Adaptive tempo: the editor row grid must be fine enough for the fastest
    # notes. Use the GCD of all note onsets as frames-per-row (clamped 1..8) so
    # rapid melodies/arps (notes a few play-calls apart) land on row boundaries
    # instead of being quantised away.
    import math
    global TEMPO
    multispeed = detect_multispeed(sid, h.init_address, h.play_address, subtune)
    # Row budget: the edit area (sequences + tables) must clear the $D000 memory
    # wall, so cap total rows (~12000 fits; ~13500 overflows osc3). budget_tempo is
    # the coarsest grid forced by length; the finer the better for accuracy, so it's
    # a FLOOR, not the value.
    ROW_BUDGET = 12000
    budget_tempo = max(1, -(-frames // ROW_BUDGET))
    has_ties = any(n.tie for v in song.voices for n in v.notes)
    if any(v.legato for v in song.voices):
        # Legato tunes need ONE row per video frame for frame-accurate pulse resets
        # (the lead's pulse fell to ~19% at a coarse grid). TEMPO=multispeed.
        TEMPO = max(multispeed, budget_tempo)
    elif has_ties:
        # A held-note voice has within-gate SPLIT melody at arbitrary frames; a
        # coarse gate-on grid drops it (Terra Cresta's lead needs tempo 1). Place it
        # as finely as the memory budget allows.
        TEMPO = budget_tempo
    else:
        # Pure re-gated (no within-gate splits): align the grid to the note spacing
        # for a clean editor, but never coarser than the budget.
        g = 0
        for voice in song.voices:
            for n in voice.notes:
                if n.onset and not n.tie:
                    g = math.gcd(g, n.onset)
        if g >= 2:
            TEMPO = max(budget_tempo, min(8, g))
        else:
            from collections import Counter
            gc = Counter()
            for voice in song.voices:
                on = sorted(n.onset for n in voice.notes if not n.tie)
                for a, b in zip(on, on[1:]):
                    if b > a:
                        gc[b - a] += 1
            TEMPO = max(budget_tempo, min(32, gc.most_common(1)[0][0]) if gc else 8)
    if os.environ.get("GALWAY_TEMPO"):
        TEMPO = int(os.environ["GALWAY_TEMPO"])
    rows_total = frames // TEMPO
    print(f"trace: {frames} play-calls, {rows_total} rows @ tempo {TEMPO}, "
          f"multispeed={multispeed} (play-calls/video-frame) -> "
          f"{frames / multispeed / 50.12:.1f}s")

    # DECOUPLED model: an INSTRUMENT is just a timbre (waveform, AD, SR) and the
    # SLIDE/VIBRATO shape is a SEPARATE per-note "FM program" selected by the
    # sequence command channel ($c0-$ff -> index 0..62, see the driver's
    # pr_setfm). Timbre fits the <=32 instrument table; slide shapes fit a much
    # larger, independent FM-program table. So a long song keeps EXACT AD/SR AND
    # EXACT slides (no clustering) where the old single-table model had to merge
    # mismatched slides into one instrument and corrupt the pitch. Each note row
    # carries (note, instrument, fm-index); pitch = the note byte; the FM program
    # carries the within-note modulation; the instrument carries AD/SR+waveform.
    #
    # adq/fmq are FALLBACK quantisers, only engaged if a pathological tune blows
    # the 32-instrument or 63-FM budget (Ocean Loader uses neither: 18 + 24).
    # A per-note "synth program" (the command) BUNDLES the slide (FM) AND the
    # pulse-width envelope, both decoupled from the instrument. pulse, like the
    # slide, varies per note in Galway; keying it on the instrument made many
    # notes share one wrong pulse (osc2/osc3 pulse 8-13% in SF2II). Bundling
    # (fm, pulse) into the one command channel (<=63 distinct) gives each note its
    # exact pulse too. Ocean Loader: 18 instruments + 32 bundles.
    def build(adq, fmq, pq):
        s2i, ins = {}, []                  # timbre instruments (wf,ad,sr)
        b2i, bfm, bpul = {}, [], []        # synth bundles: (fm, pulse) per command
        nseq = [[] for _ in range(3)]
        iov = bov = 0
        # PULSE is restarted by the driver on each gate-on (a non-tie note;
        # VPI=VIPULSE, VPC=0) and free-runs across that region's legato ties — so a
        # voice's pulse is one program PER GATE-REGION (gate-on -> next gate-on),
        # not one per voice. A sustained voice that gates once is just the single-
        # region case; a re-gating voice (the full Wizball lead gates 177x) gets
        # many SHORT regions that compress well and dedup across repeated phrases,
        # so the whole song's pulse fits the shared 256-row table. Tie notes never
        # restart the pulse, so their program is unused -> empty (keeps bundles
        # deduping by fm only). `pq` is the per-region row budget (raised by the fit
        # loop only if the pulse table overflows).
        def _region_ends(notes):
            ends = [frames] * len(notes)
            nxt = frames
            for k in range(len(notes) - 1, -1, -1):
                ends[k] = nxt
                if not notes[k].tie:
                    nxt = notes[k].onset
            return ends
        rends = [_region_ends(voice.notes) for voice in song.voices]
        EMPTY_PUL = [(0x7F, 0, 0)]
        # A voice needs the per-GATE-REGION pulse model whenever it has TIE notes
        # (held regions split into sub-notes) — not only when the whole voice is
        # legato. Otherwise a held note's per-note pulse would cover only up to the
        # first split and then freeze across the ties (the driver doesn't restart
        # pulse on a tie). Re-gated voices with no ties keep the per-note pulse.
        region_pulse = [vc.legato or any(n.tie for n in vc.notes) for vc in song.voices]
        for v, voice in enumerate(song.voices):
            for ni, note in enumerate(voice.notes):
                orow = note.onset // TEMPO
                if orow >= rows_total:
                    continue
                nb, fm = fm_program(note, FLAT_DEV)
                if region_pulse[v]:
                    # Budget each region's pulse rows PROPORTIONAL to its length:
                    # a long sustained region (e.g. the 36s intro) needs many rows
                    # for its slow sweep, a 60-frame re-gate needs ~3. A flat budget
                    # starved the intro -> its ramp collapsed to a coarse staircase
                    # (pulse frozen for ~80 frames). `pq` (raised by the fit loop on
                    # table overflow) scales the divisor to keep the table <=256.
                    if note.tie:
                        pul = EMPTY_PUL
                    else:
                        # `faithful_pulse_program` returns the EXACT per-frame program
                        # when it fits the budget, else coarsens. Give a generous flat
                        # budget so SHORT regions (Comic Bakery's held lead notes) stay
                        # exact; only genuinely long sweeps (Wizball's 36s intro) hit
                        # the cap and coarsen. pq (from the fit loop) shrinks it only
                        # if the shared pulse table overflows.
                        pul = faithful_pulse_program(song.pulse[v][note.onset:rends[v][ni]],
                                                     max(8, 96 // pq))
                else:
                    pul = pulse_program(song.pulse[v][note.onset:note.end], pq)
                # coarsen AD/SR PER NIBBLE only as a fallback (Galway ramps Attack);
                # per-nibble keeps Decay + Release alive.
                def qn(b):
                    return (((b >> 4) // adq * adq) << 4) | ((b & 0xF) // adq * adq)
                ad, sr = qn(note.ad), qn(note.sr)
                ikey = ((note.waveform & 0xF0), ad, sr)
                iidx = s2i.get(ikey)
                if iidx is None:
                    if len(ins) >= 32:
                        iov += 1
                        iidx = 0
                    else:
                        iidx = len(ins)
                        s2i[ikey] = iidx
                        ins.append((ad, sr, (note.waveform & 0xF0) | 0x01, 0x08))
                bkey = (fm_sig(fm, fmq), tuple(pul))
                bidx = b2i.get(bkey)
                if bidx is None:
                    if len(bfm) >= 63:
                        bov += 1
                        bidx = 0
                    else:
                        bidx = len(bfm)
                        b2i[bkey] = bidx
                        bfm.append(fm)               # 1st note in bundle = its fm+pulse
                        bpul.append(pul)
                end_row = min(rows_total, max(orow + 1, note.end // TEMPO))
                nseq[v].append((orow, end_row, nb, iidx, bidx, note.tie))
        return s2i, ins, bfm, bpul, nseq, iov, bov

    # Fit both INDEPENDENT budgets (32 instruments, 63 synth bundles). Only a
    # pathological tune trips either; coarsen the offending one minimally
    # (cluster fm shapes, then downsample pulse, then quantise AD/SR).
    PULSE_TABLE_ROWS = 1024      # row-major PULSETAB via 16-bit pointer (was 256)
    adq = fmq = pq = 1
    while True:
        _, instrs, fmprogs, pulse_by_cmd, note_seq, iov, bov = build(adq, fmq, pq)
        # the PULSE table holds the DISTINCT bundle pulse programs (gen_includes_song
        # dedups); if they overflow 256 rows, shrink the per-region budget (pq).
        prows = sum(len(p) for p in {tuple(p) for p in pulse_by_cmd})
        pov = prows > PULSE_TABLE_ROWS
        if iov == 0 and bov == 0 and not pov:
            break
        if bov and fmq < 0x800:
            fmq *= 2
        elif (bov or pov) and pq < 8:
            pq *= 2
        elif iov and adq < 16:
            adq *= 2
        else:
            break
    if iov:
        print(f"  WARNING: {iov} notes past the 32-instrument cap reuse instr 0")
    if bov:
        print(f"  WARNING: {bov} notes past the 63-bundle cap reuse bundle 0")
    if pov:
        print(f"  WARNING: pulse table {prows} > {PULSE_TABLE_ROWS} rows — will be truncated")
    if not instrs:
        raise SystemExit("no notes traced — nothing to build")
    if fmq != 1 or adq != 1 or pq != 1:
        print(f"  (fallback quant: fm fmq=${fmq:02x}, pulse step={pq}, "
              f"AD/SR nibble-q={adq})")
    print(f"  {sum(len(ns) for ns in note_seq)} notes, {len(instrs)} instruments, "
          f"{len(fmprogs)} synth bundles (fm+pulse), "
          f"{sum(len(p) for p in fmprogs)} FM entries, "
          f"{sum(len(p) for p in pulse_by_cmd)} pulse rows")

    # Sequence rows packed via segment_track — the SAME packer the SF2II-playable
    # static build uses (datasource_sequence.cpp format) so SF2II parses + plays.
    # Pad to rows_total so the orderlist doesn't wrap early and re-trigger.
    # Each note row carries its instrument (timbre) AND its FM-program index (the
    # slide shape) via the command channel. Both are emitted only on CHANGE; the
    # driver carries the voice's instrument + FM pointer across rows/patterns, and
    # the orderlist plays sequences linearly, so carryover across a segment split
    # is correct (verified by the headless per-frame check below).
    segs = []
    for v in range(3):
        drows, cur = [], 0
        last_i = last_f = -1
        nv = note_seq[v]
        for ni, (orow, end_row, nb, iidx, fidx, tie) in enumerate(nv):
            orow = max(orow, cur)
            # Clamp this note's end to the NEXT note's onset so a long note's
            # reconstructed tail never pushes the next note late. Without this the
            # delay accumulates over a long song -> the whole voice drifts behind
            # the trace (audible on the lead + dense arp; clean-boundary voices
            # were unaffected, which is why osc3 stayed faithful).
            if ni + 1 < len(nv):
                end_row = min(end_row, max(nv[ni + 1][0], orow + 1))
            if orow >= end_row:
                continue
            drows += [D11Row(note=SF2_GATE_OFF) for _ in range(orow - cur)]
            # tie = legato note change: keep the gate (no re-attack) + let pulse
            # free-run. Only on a sustained voice (a tie at row 0 / after a rest has
            # nothing to continue, so drop it there).
            drows.append(D11Row(note=nb,
                                instrument=(iidx if iidx != last_i else None),
                                command=(fidx if fidx != last_f else None),
                                tie=bool(tie) and cur > 0))
            last_i, last_f = iidx, fidx
            drows += [D11Row(note=SF2_GATE_ON) for _ in range(end_row - orow - 1)]
            cur = end_row
        drows += [D11Row(note=SF2_GATE_OFF) for _ in range(rows_total - cur)]
        packed = segment_track(drows) if drows else [bytes([0x7F])]
        segs.append(packed)
        if os.environ.get("GALWAY_DEBUG_NOTES"):
            from sidm2.galway_driver11_emitter import unpack_sequence
            emitted = sum(1 for r in drows if 1 <= (r.note or 0) <= 0x6F)
            unp = sum(1 for s in packed for n in unpack_sequence(s) if 1 <= n <= 0x6F)
            print(f"  [dbg] osc{v+1}: note-ons emitted={emitted} unpacked(editor)={unp} "
                  f"sequences={len(packed)} rows={rows_total}")

    def _wftag(wf):
        for bit, t in ((0x80, "noise"), (0x40, "pulse"), (0x20, "saw"), (0x10, "tri")):
            if wf & bit:
                return t
        return "inst"
    names = [f"{_wftag(ins[2])} {i + 1:02d}" for i, ins in enumerate(instrs)]

    B.TEMPO = TEMPO
    # Flag the routed voice's instruments $40 so the filter envelope restarts on
    # each of its notes (the filter affects whichever voice $D417 routes).
    filt_instr_set = ({row[3] for row in note_seq[filt_voice]}
                      if filt_voice is not None else None)
    if filt_prog:
        print(f"  filter: routed osc{filt_voice + 1}, {len(filt_prog)}-row cutoff "
              f"envelope, {len(filt_instr_set)} instr(s) flagged")
    gen, edit, mdp, seq0 = N.gen_includes_song(segs, instrs,
                                               filter_lead=False,
                                               fm_programs=fmprogs,
                                               multispeed=multispeed,
                                               pulse_by_cmd=pulse_by_cmd,
                                               filter_program=filt_prog,
                                               filter_instr_set=filt_instr_set)
    prg = B.assemble()
    sf2 = B.wrap(prg, gen, edit, mdp, instr_names=names)
    out = os.path.join(ROOT, "out", "galway_trace_song.sf2")
    open(out, "wb").write(sf2)
    print(f"wrote {out} ({len(sf2)} bytes)")

    # Also emit a PSID of the raw driver image so the tune can be rendered to WAV
    # (SID2WAV) for listening / A-B vs the original. The native Galway driver
    # doesn't round-trip through scripts/sf2_to_sid (built for Driver 11/Laxity),
    # so wrap the driver's own memory image directly: prg at its load addr + the
    # edit area (tables/sequences/FM) at EDIT_BASE, INIT=$1000 PLAY=$1003.
    import struct
    load = prg[0] | (prg[1] << 8)
    body = prg[2:]
    end = max(load + len(body), B.EDIT_BASE + len(edit))
    img = bytearray(end - load)
    img[0:len(body)] = body
    img[B.EDIT_BASE - load:B.EDIT_BASE - load + len(edit)] = edit
    hdr = bytearray(0x7C)
    hdr[0:4] = b"PSID"
    struct.pack_into(">H", hdr, 4, 2)            # version 2
    struct.pack_into(">H", hdr, 6, 0x7C)         # data offset
    struct.pack_into(">H", hdr, 8, 0)            # load=0 -> first 2 data bytes
    struct.pack_into(">H", hdr, 10, 0x1000)      # init
    struct.pack_into(">H", hdr, 12, 0x1003)      # play
    struct.pack_into(">H", hdr, 14, 1)           # songs
    struct.pack_into(">H", hdr, 16, 1)           # start song
    nm = os.path.splitext(os.path.basename(sid))[0].encode()[:31]
    hdr[0x16:0x16 + len(nm)] = nm
    sidout = os.path.join(ROOT, "out", "galway_trace_song.sid")
    open(sidout, "wb").write(bytes(hdr) + struct.pack("<H", load) + bytes(img))
    print(f"wrote {sidout} ({end - load} byte image, init=$1000 play=$1003)")

    from sidm2.models import SF2DriverInfo
    from sidm2 import sf2_parser
    di = SF2DriverInfo()
    la = sf2_parser.parse_sf2_blocks(bytearray(sf2), di)
    print(f"PARSE: load=${la:04X} tracks={di.track_count}",
          "OK" if la == 0x0D7E else "FAIL")

    # headless: driver per-frame note vs the emitted program, per note
    from py65.devices.mpu6502 import MPU
    # GALWAY_BUGGY_CMP=1 -> emulate SF2II's cpumos6510 CMP (carry = !bit7(A-op),
    # only correct for |A-op|<=$7f) to reproduce/localise SF2II-only divergences.
    if os.environ.get("GALWAY_BUGGY_CMP") == "1":
        _dbg = os.environ.get("GALWAY_CMP_LOG") == "1"
        def buggy_cmpr(self, get_address, register_value):
            addr = get_address()
            tbyte = self.ByteAt(addr)
            res = (register_value - tbyte) & 0xFF
            self.p &= ~(self.CARRY | self.ZERO | self.NEGATIVE)
            if res == 0:
                self.p |= self.ZERO
            if not (res & 0x80):          # buggy carry = NOT sign bit of (A-op)
                self.p |= self.CARRY
            self.p |= res & self.NEGATIVE
            if _dbg and (register_value >= tbyte) != bool(res & 0x80 and False or not (res & 0x80)):
                pass
            if _dbg:
                correct_c = register_value >= tbyte
                buggy_c = not (res & 0x80)
                if correct_c != buggy_c:
                    print(f"    CMP-DIVERGE pc=${self.pc-2:04x} A=${register_value:02x} op=${tbyte:02x} correct_C={int(correct_c)} buggy_C={int(buggy_c)}")
            return
        MPU.opCMPR = buggy_cmpr
        print("  [BUGGY CMP emulation ON]")
    load = prg[0] | (prg[1] << 8)
    m = MPU()
    for i, b in enumerate(prg[2:]):
        m.memory[(load + i) & 0xFFFF] = b
    for i, b in enumerate(edit):
        m.memory[(B.EDIT_BASE + i) & 0xFFFF] = b

    # sentinel return address above all loaded data (edit + relocated tables + FM)
    SENT = min(0xCF00, (B.EDIT_BASE + len(edit) + 0x200) & ~0xFF)

    def call(a):
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
        # Compare the driver's per-video-frame PITCH (note index) against the
        # real trace sampled at the matching play-call. Pitch is semitone-
        # quantised (the note byte) + relative FM modulation, so compare in
        # note-index space (a 1-semitone tolerance absorbs the dropped
        # sub-semitone correction and vibrato edges).
        bad = worst = cmp = 0
        for k in range(vframes):
            pc = min((k + 1) * multispeed - 1, frames - 1)
            if gf[v][pc] == 0:
                continue                                # gate off / between notes
            cmp += 1
            diff = abs(freq_to_note(got[v][k]) - freq_to_note(gf[v][pc]))
            worst = max(worst, diff)
            if diff > 1:
                bad += 1
        ok_pct = 100 * (cmp - bad) // cmp if cmp else 0
        faithful = ok_pct >= 95
        all_faithful = all_faithful and faithful
        print(f"  osc{v+1}: {len(note_seq[v])} notes; pitch match "
              f"{ok_pct}% ({cmp-bad}/{cmp} frames within 1 semitone, worst {worst})"
              f" {'OK' if faithful else 'CHECK'}")
    print("TRACE BUILD " + ("FAITHFUL — driver reproduces the real per-frame pitch"
                            if all_faithful else "CHECK — driver diverged from trace"))


if __name__ == "__main__":
    main()
