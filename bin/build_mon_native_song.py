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
BUNDLE_TOL = int(os.environ.get("BUNDLE_TOL", "0"))  # 0 = OFF (lossless split). Raising it
# lets NEAR-identical (same-pulse) FM contours merge inaudibly so a window fits more of the
# song -> fewer SF2 parts. See docs/analysis/PART_REDUCTION_PLAN.md (Phase 1).


def fm_program_for(frames, v, onset, dur_f, base, allow_loop=False):
    """Per-note FM program (B2): reproduce the original's exact per-frame freq for
    this note. offset[k] = (trace_freq[onset+k] - base) & $FFFF; the driver's FM
    runner accumulates per-frame deltas, so emit delta[k]=offset[k]-offset[k-1] as
    (lo,hi,run) RLE entries + a freeze. Handles BOTH portamento slides (constant
    delta) and arps (per-frame deltas) byte-exactly. base = the note's freqtable
    value (== the driver's vfreq), so offset[0]=0 (frame 0 plays at base).
    allow_loop (shim flag `fm_loop`, notes longer than FM_CAP only): a periodic
    delta tail (SM's constant-depth triangle vibrato) is emitted as cycle
    entries + a $7f LOOP instead of freezing at the capture cap — the freeze
    held Dreamix_Two's lead at the vibrato PEAK for the rest of every long
    note (v1 freq 79.9). Guard: >=2 observed cycles, zero net delta per cycle,
    and the unrolled program must reproduce the whole capture exactly."""
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

    def rle(seq):
        r_, n_ = None, 0
        for d in seq:
            if d == r_:
                n_ += 1
            else:
                if r_ is not None:
                    flush(r_, n_)
                r_, n_ = d, 1
        if r_ is not None:
            flush(r_, n_)

    if allow_loop and dur_f > FM_CAP and len(deltas) >= 60:
        N = len(deltas)
        for p_ in range(2, 41):
            k = N - 1
            while k >= p_ and deltas[k] == deltas[k - p_]:
                k -= 1
            cs = k + 1                              # deltas[cs:] repeat with period p_
            if (N - cs >= 2 * p_
                    and sum(deltas[cs:cs + p_]) & 0xFFFF == 0):
                rle(deltas[:cs])
                tgt = len(prog)                     # loop target = cycle start entry
                rle(deltas[cs:cs + p_])
                prog.append((tgt, 0, 0x7F))         # $7f LOOP to the cycle start
                # exactness guard: the unrolled loop must reproduce the capture
                acc, tv = 0, [0]
                for d in deltas:
                    acc = (acc + d) & 0xFFFF
                    tv.append(acc)
                if _fm_unroll(prog, N + 1) == tv:
                    return prog
                prog.clear()                        # guard failed -> plain path
                break
    rle(deltas)
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
# PART REDUCTION Phase 2 (docs/analysis/PART_REDUCTION_PLAN.md): collapse the PULSE side
# of the (FM,pulse) bundle to ONE canonical program per instrument, so the command channel
# holds ~distinct-FM (Hubbard ~24) instead of distinct-pairs (~68) -> far fewer parts. Just
# the pulse-canonical, without ARP_STRUCT's FM changes. Opt-in per shim (`pulse_canon`) or
# via MON_PULSE_CANON=1.
PULSE_CANON = os.environ.get("MON_PULSE_CANON", "") == "1"
# INSTRUMENT-CAP OPTIMIZER wave prong (user directive 2026-07-11; see
# memory/soundmonitor-player.md "THE INSTRUMENT-CAP OPTIMIZER"): first-row
# boundary-bleed normalization + frame-0-tolerant canonical acceptance.
# Opt-in per shim (`wave_canon`) or via MON_WAVE_CANON=1.
WAVE_CANON = os.environ.get("MON_WAVE_CANON", "") == "1"


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
    unroll (non-arp notes, non-Supremacy engines, flag off). Shims can opt in
    per-player via `arp_struct` (SM: the row-header chord tables) without the
    global MON_ARP_STRUCT env."""
    if ((not ARP_STRUCT and not getattr(m, "arp_struct", 0))
            or not hasattr(m, "arp_program")
            or getattr(m, "tbl_arp_idx", 0) == 0):
        return None
    try:
        arp = m.arp_program(ev.wprog)
    except Exception:
        return None
    if not arp or not arp.get('steps') or arp['steps'] == [0]:
        return None
    return arp_fm_program(arp)


def pulse_program_for(frames, v, onset, dur_f, cap=FM_CAP, allow_loop=False):
    """Per-note PULSE program (B3 PWM): reproduce the original's per-frame pulse
    width. 8X = set width frame 0; 0X = add per-frame delta (12-bit) for `run`
    frames; 7f = freeze. The driver restarts the pulse program per note (PPTR=
    VIPUL/VPC=0), so frame 0 sets the base — no 1-frame offset (unlike FM).
    cap > FM_CAP is used for the free-running per-voice STREAM programs.

    allow_loop (v2 Hubbard): PERIODIC pulse (Delta's sawtooth PWM wraps every
    ~9 frames for the whole note; a capped capture froze mid-ramp) is emitted
    as set + ONE cycle of adds + a $7F LOOP row — exact forever, 3 rows."""
    targ, hold = [], None
    for k in range(min(dur_f, cap if not allow_loop else dur_f)):
        idx = onset + k
        pv = frames[idx][0][v]['pul'] if idx < len(frames) else None
        if pv is not None:
            hold = pv
        targ.append(hold if hold is not None else 0x800)
    if allow_loop and len(targ) >= 24:
        for p in range(2, min(128, len(targ) // 2)):
            if all(targ[k] == targ[k + p] for k in range(1, len(targ) - p)):
                prog = [(0x80 | ((targ[0] >> 8) & 0x0F), targ[0] & 0xFF, 1)]
                prev = targ[0]
                run, rl = None, 0
                for k in range(1, 1 + p):
                    delta = (targ[k] - prev) & 0xFFF
                    prev = targ[k]
                    if delta == run:
                        rl += 1
                    else:
                        if run is not None:
                            prog.append(((run >> 8) & 0x0F, run & 0xFF, rl))
                        run, rl = delta, 1
                if run is not None:
                    prog.append(((run >> 8) & 0x0F, run & 0xFF, rl))
                prog.append((0x7F, 1, 0))          # LOOP to row 1 (first add)
                return prog
        # OFFSET-PERIODIC: a transient prefix then a steady cycle (SM's long
        # one-way ramps settle into a 12-bit-wrap sawtooth; the from-frame-1
        # check above fails on the transient and the capture FROZE mid-sweep —
        # a 17-second audible pulse freeze on Fuck_Off osc2). The capture's
        # last frames hold the NEXT note's base-reset bleed (tie-chain spans),
        # which breaks tail periodicity — detect on a bleed-trimmed copy.
        tt = targ[:-3] if len(targ) > 27 else targ
        for p in range(2, min(128, len(tt) // 3)):
            if len(tt) < 2 * p + 2:
                break
            if not all(tt[-k] == tt[-k - p] for k in range(1, p + 1)):
                continue
            s = len(tt) - 2 * p                    # extend the cycle backwards
            while s > 1 and tt[s - 1] == tt[s - 1 + p]:
                s -= 1
            prog = [(0x80 | ((tt[0] >> 8) & 0x0F), tt[0] & 0xFF, 1)]
            prev = tt[0]
            loop_row = None
            run, rl = None, 0
            for k in range(1, s + p):
                if k == s:                          # cycle start: flush + mark row
                    if run is not None:
                        prog.append(((run >> 8) & 0x0F, run & 0xFF, rl))
                        run, rl = None, 0
                    loop_row = len(prog)
                delta = (tt[k] - prev) & 0xFFF
                prev = tt[k]
                if delta == run:
                    rl += 1
                else:
                    if run is not None:
                        prog.append(((run >> 8) & 0x0F, run & 0xFF, rl))
                    run, rl = delta, 1
            if run is not None:
                prog.append(((run >> 8) & 0x0F, run & 0xFF, rl))
            if loop_row is None or loop_row > 250:  # byte1 is one byte; keep sane
                break
            prog.append((0x7F, loop_row, 0))
            return prog
        targ = targ[:cap]                          # no cycle: bound the RLE
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
            fr = _snap_onset(m, frames, v, m.tick_to_frame(tk) + delay)
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


def _hr_rows(rows, hard_restart):
    """HARD_RESTART builds: turn the FINAL gate-off row before each note into the
    $7D hard-restart row (driver: gate off + AD/SR=0). Matches the ROM's timing —
    the "kill adsr" fires at note-length end, 1-3 frames before the next fetch;
    killing at the gate fall instead executed the drums' release ring."""
    if not hard_restart:
        return rows
    HR = 0x7D
    for i in range(1, len(rows)):
        r = rows[i]
        if (r.note not in (0x00, SF2_GATE_ON, HR)
                and not getattr(r, 'tie', False)
                and rows[i - 1].note in (0x00, SF2_GATE_ON)):
            # ...GATE_ON rows too: Hubbard notes chain back-to-back with no
            # gate-off tail, and the ROM's release routine kills gate + ADSR
            # TOGETHER at length end — without this, gated-note chains never
            # hard-restart and the mix washes out (the Commando lead drowned)
            rows[i - 1] = D11Row(note=HR)
    return rows


def prune_stale_parts(prefix, nparts):
    """Delete `<prefix>_partNN.sf2` files with NN > nparts. A rebuild that packs
    into fewer parts than a previous era otherwise leaves the old higher-numbered
    parts on disk — the inventory then reports phantom files (Supremacy_sub2
    showed 70 when the real build was 10) and a listener plays a stale tail."""
    import glob
    import re
    removed = 0
    for f in glob.glob(f"{prefix}_part*.sf2"):
        mm = re.search(r"_part(\d+)\.sf2$", f)
        if mm and int(mm.group(1)) > nparts:
            os.remove(f)
            removed += 1
    if removed:
        print(f"  pruned {removed} stale part files beyond part{nparts:02d}")


def _snap_onset(m, frames, v, fr):
    """Per-note capture alignment (shim opt-in `snap_gate`): snap `fr` to the
    actual GATE-RISE frame in the trace. Hubbard drums gate for exactly ONE
    frame ($15 for one frame, then $80 noise, then released $14 — VICE-dump
    verified); a global capture phase that lands one frame late drops that
    frame out of the wave program and the note's ATTACK never fires. A ±2/+3
    window around the grid frame recovers the true onset per note."""
    if not getattr(m, 'snap_gate', False):
        return fr

    def g(k):
        return (frames[k][0][v]['wf'] & 1) if 0 <= k < len(frames) else 0
    for k in range(max(0, fr - 2), min(len(frames), fr + 4)):
        if g(k) and not g(k - 1):
            return k
    return fr


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


def detect_filter_drives(ftr, onsets_by_voice, routed=None, dynamic=False):
    """Find the filter-envelope restarts = the note-ons of the filter-routed voice.
    Each envelope ATTACK shows as a fast cutoff jump (>= FILT_FAST in 11-bit); map it
    back to the nearest note-on within a few frames — that note triggers the envelope.
    When `routed` (0/1/2) is given, only that voice's note-ons are eligible (the engine
    restarts the envelope on the ROUTED voice only); else any voice. `dynamic` (SM's
    filter_tie): credit the voice the $D417 routing bits point at ON THE ATTACK FRAME —
    SM tunes switch filter routing per section (Dance routes v1 globally-dominant but
    v0 in whole sections; the fixed `routed` restriction dropped every v0 re-attack,
    leaving them embedded in per-drive captures = distinct programs). Returns
    {onset_frame: voice}."""
    import bisect
    n = len(ftr)
    voices = (routed,) if routed is not None and not dynamic else range(3)
    pairs = sorted({(o, v) for v in voices for o in onsets_by_voice[v]})
    by_voice = {v: sorted(o for o, vv in pairs if vv == v) for v in range(3)}
    of_frames = sorted({o for o, _ in pairs})
    drives, f = {}, 1
    while f < n:
        if abs(ftr[f][0] - ftr[f - 1][0]) >= FILT_FAST:
            frames_ = of_frames
            v_at = None
            if dynamic:
                v_at = {1: 0, 2: 1, 4: 2}.get(ftr[f][1] & 0x07)
                if v_at is not None:
                    frames_ = by_voice[v_at]
            j = bisect.bisect_right(frames_, f) - 1          # nearest onset <= f
            cand = [frames_[k] for k in (j, j + 1)
                    if 0 <= k < len(frames_) and -1 <= (f - frames_[k]) <= 4]
            if cand:
                o = min(cand, key=lambda x: abs(x - f))
                if o not in drives:
                    drives[o] = (v_at if v_at is not None
                                 else next(v for oo, v in pairs if oo == o))
            f += 1
            while f < n and abs(ftr[f][0] - ftr[f - 1][0]) >= FILT_FAST:
                if (dynamic
                        and (ftr[f][0] - ftr[f - 1][0])
                        * (ftr[f - 1][0] - ftr[f - 2][0]) < 0):
                    # SM: a FAST envelope (-136/frame > FILT_FAST) makes the
                    # whole descent one "jump run", swallowing the NEXT attack
                    # embedded in it (Dance part02: re-attacks +608 mid-sweep
                    # never credited -> the probe froze while the original
                    # kept enveloping; filter 33.6%). A direction REVERSAL
                    # inside the run is a new attack — re-process it.
                    break
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
    # cap at 256 (not WAVE_CAP=96): a long note + rest tail can change $D404 past
    # frame 96 (Supremacy's wave-off lands at frame 98 of a 100-frame note);
    # settle-trim keeps hold-tails free and the table stores RLE, so a generous
    # cap costs rows only where the trace genuinely keeps changing.
    for k in range(min(dur_f, 256)):
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


def _relwf_of(m, mon_i):
    """The instrument's RELEASE waveform (SM sound-record byte 8) or None.
    Non-None enables the tail split (_rel_split) + the driver's RELEASE_WF
    feature for this instrument; only shims that set `release_wf` (SM) and
    expose 'release_wf' per instrument participate — MoN/Hubbard/DMC paths
    are untouched."""
    if not getattr(m, 'release_wf', 0):
        return None
    rw = m.instrument(mon_i).get('release_wf')
    return rw & 0xFF if rw is not None else None


def _rel_split(m, frames, v, fr, dur_f, tk, ticks, relwf):
    """RELEASE-WF split (the instrument-cap optimizer's class-2 fix): SM-class
    engines write the instrument's release waveform (sound-record byte 8) at
    note-off — a DURATION-relative frame — so per-note wave captures differ per
    duration and explode the 32-slot instrument cap (Dance part 1: 10 source
    instruments -> 31 slots, almost all trailing-run variants). Find the
    trailing run of `relwf` in the capture and move it OUT of the wave program
    into sequence GATE-OFF rows: the driver's RELEASE_WF feature writes VRELWF
    (poked per instrument = relwf) VERBATIM on gated-off frames, so the tail is
    reproduced by the note's row schedule and the program collapses to the
    duration-independent body. Returns (gate_ticks, wfs, off_k, end) like
    _gate_split; off_k None = no split (exact per-note program kept).
    Guard: the release frame must sit within 1 frame of a row tick (SM's
    note-offs land on the step grid, so grid builds align exactly)."""
    wfs, last = [], 0x41
    for k in range(min(dur_f, 256)):
        idx = fr + k
        w = frames[idx][0][v]['wf'] if idx < len(frames) else None
        last = w if w is not None else last
        wfs.append(last & 0xFF)
    end = len(wfs)
    off_k = end
    while off_k > 0 and wfs[off_k - 1] == relwf:
        off_k -= 1
    if off_k == 0 or end - off_k < 2:
        return ticks, wfs, None, end             # no (meaningful) trailing run
    base_f = m.tick_to_frame(tk)
    # nearest row tick to the observed release frame (frame_to_tick is not a
    # true inverse on the SM grid shim, so derive frames-per-tick locally)
    fpt = max(1, m.tick_to_frame(tk + 1) - base_f)
    t_off = max(1, min(ticks - 1, round(off_k / fpt))) if ticks > 1 else 0
    if t_off < 1:
        return ticks, wfs, None, end
    drv_off = m.tick_to_frame(tk + t_off) - base_f
    if abs(drv_off - off_k) > 1:
        return ticks, wfs, None, end             # off the row grid: keep exact
    return t_off, wfs, off_k, end


def _first_row_norm(wp):
    """WAVE-CANON first-row normalization (the optimizer's class-1 fix): frame
    0 of a capture can hold the pre-note boundary state (gate-off $40 / $80
    bleed from SM's within-frame retrigger), making [64,65,..] / [128,65,..] /
    [65,..] distinct programs for the same instrument. Replace a gate-CLEAR
    frame 0 followed by a gate-SET frame 1 with frame 1's value (the note's
    own waveform) — unroll-equal from frame 1 by construction; the loss is one
    boundary frame per note, the same accepted class as the onset spikes.
    A real gated noise attack ([129,65,..]) has bit0 SET and is never touched."""
    if len(wp) >= 2 and not (wp[0] & 1) and (wp[1] & 1):
        return _settle_trim((wp[1],) + tuple(wp[1:]))
    return wp


def _wave_rel_ok(prog, wfs, drv_gate_f, off_k, end, relwf, skip0):
    """True iff `prog` (driver wave program; loops on its last value), gated
    off from row-frame drv_gate_f with RELEASE_WF output `relwf`, reproduces
    the captured wfs[:end]. Frames between the observed and driver gate-off
    ([min,max) of off_k/drv_gate_f) are the accepted <=1-frame skew; frame 0
    is skipped under WAVE-CANON (the normalized boundary-bleed frame)."""
    lo, hi = ((min(off_k, drv_gate_f), max(off_k, drv_gate_f))
              if off_k is not None else (end, end))
    for k in range(1 if skip0 else 0, end):
        if lo <= k < hi:
            continue                             # declared skew frame
        out = prog[k] if k < len(prog) else prog[-1]
        if k >= drv_gate_f:
            out = relwf
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
    # FILTER-TIE (shim flag `filter_tie`, SM-class): the engine restarts its
    # cutoff envelope on EVERY note-set of the routed voice incl. legato — tie
    # events are rows the driver's filter restart already fires on (the
    # VIFLAGS $40 check runs for ties too), so make them drive-ELIGIBLE.
    # Without this, mid-span re-attacks stay embedded in per-drive captures
    # and every drive gets a distinct program (Dance part 8: 15 programs /
    # 247 rows, 32 slots — nearly all identical envelopes at different
    # re-attack schedules).
    ftie = getattr(m, 'filter_tie', 0)
    drive_onsets = [set() for _ in range(3)]
    for v in range(3):
        tk = 0
        for ev in m.voices[v]:
            if ev.retrig:
                fr = _snap_onset(m, frames, v, m.tick_to_frame(tk) + delay)
                onsets[v].add(fr)
                drive_onsets[v].add(fr)
                onset_instr[v][fr] = ev.instr
                dur_f = m.tick_to_frame(tk + ev.dur) - m.tick_to_frame(tk)
                k = (ev.instr, ev.wprog)
                if dur_f >= 2 and (k not in canon_pick or dur_f > canon_pick[k][0]):
                    canon_pick[k] = (dur_f, v, fr, tk, ev.dur, ev.note)
            elif ftie and getattr(ev, 'tie', False):
                fr = _snap_onset(m, frames, v, m.tick_to_frame(tk) + delay)
                drive_onsets[v].add(fr)
                onset_instr[v][fr] = ev.instr
            tk += ev.dur
    # WAVE-CANON (the instrument-cap optimizer, shim flag `wave_canon`):
    # first-row boundary-bleed normalization + frame-0-tolerant canonical
    # acceptance. RELEASE-WF (shim flag `release_wf` + per-instrument
    # 'release_wf' byte): duration-positioned release tails split into
    # gate-off rows. Both SM-gated; MoN/Hubbard/DMC behavior unchanged.
    wcanon = WAVE_CANON or getattr(m, 'wave_canon', 0)
    canon_wave, canon_pulse, canon_fm = {}, {}, {}
    for k, (df_, v_, fr_, tk_, dur_, note_) in canon_pick.items():
        relwf_ = _relwf_of(m, k[0])
        if relwf_ is not None:
            _gt, wfs_, offk_, end_ = _rel_split(m, frames, v_, fr_, df_, tk_,
                                                dur_, relwf_)
        else:
            _gt, wfs_, offk_, end_ = _gate_split(m, frames, v_, fr_, df_, tk_, dur_)
        if offk_ is not None:
            cwp = _settle_trim(wfs_[:offk_])
        else:
            cwp = _wave_prog_for(frames, v_, fr_, df_)
        canon_wave[k] = _first_row_norm(cwp) if wcanon else cwp
        # STRUCTURAL PULSE (step 4): a shorter note's captured program is a PREFIX
        # of the longest note's when the sweep restarts per note — substituting the
        # canonical is exact when the unrolled outputs match over the note's frames
        # (minus the 1-frame boundary bleed; guard in the main pass).
        cpk = pulse_program_for(frames, v_, fr_, df_)
        if (getattr(m, 'hard_restart', 0) and len(cpk) >= 3
                and cpk[-1][0] == 0x7F):
            # loop the wobble cycle instead of freezing (row 1 = first ADD);
            # the driver's $7f+byte1 LOOP rows + cross-note phase keep make
            # this the engine's per-instrument free-running pulse
            cpk = cpk[:-1] + [(0x7F, 1, 0)]
        canon_pulse[k] = cpk
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
    # NO STREAMS for pulse_tie engines (SM): their note-set RE-INITS the PW on
    # every note (that's what pulse_tie models), so a phase-keeping stream is
    # categorically wrong — and the drift detector false-positives on the ±1
    # frame register-timing split of the SAME reset value ({$600,$630} = 2
    # "distinct" starts). Dance part03 v0 ran one looping stream across 23
    # notes, ignoring every PW reset: pulse 4.0% strict. freerun_pulse on an
    # SM shim means allow_loop + tie-chain capture spans only.
    if ((ARP_STRUCT or getattr(m, 'freerun_pulse', 0))
            and not getattr(m, 'pulse_tie', 0)):
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
        explicit = bool(getattr(m, 'freerun_pulse', 0))
        min_drift = 2 if explicit else 3
        max_rows = 2600 if explicit else 700
        for v in range(3):
            drift = any(len(starts.get((v,) + k, ())) >= min_drift
                        for k in vkeys[v])
            shared = vkeys[v] & (vkeys[(v + 1) % 3] | vkeys[(v + 2) % 3])
            if drift and not shared and vnotes[v]:
                on0 = vnotes[v][0][0]
                span = min(t1w, vnotes[v][-1][0] + vnotes[v][-1][1]) - on0
                stream = pulse_program_for(frames, v, on0, span, cap=span)
                # sanity: keep PULSETAB bounded (Delta's continuous PWM barely
                # RLE-compresses — explicit v2 free-run mode allows long streams;
                # rows are 3B and the table space above the code is ample)
                if len(stream) <= max_rows:
                    freerun[v] = stream
        if os.environ.get("MON_DEBUG_FREERUN"):
            print(f"    freerun: t0w={t0w} t1w={t1w} delay={delay} "
                  f"starts={dict(list(starts.items())[:4])} "
                  f"nnotes={[len(x) for x in vnotes]} "
                  f"streams={[len(s) if s else None for s in freerun]}")
    routed = routed_voice(ftr)                              # restart only on this voice
    drive_map = detect_filter_drives(ftr, drive_onsets if ftie else onsets,
                                     routed,
                                     dynamic=bool(ftie))    # {onset_frame: voice}
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

    # PER-DRIVE EXACTNESS GUARD (same model as wave/pulse/FM): the canonical program
    # reproduces its SOURCE's ftr slice, so substituting it for drive `o` is exact iff
    # the two slices agree over o's span (driver freezes past the 220-frame capture
    # cap). Inexact drives fall back to their OWN captured program — lossless; the
    # extra rows/instruments are counted by the window-fit probes.
    def _filt_exact(o, span, key):
        oc, sc = canon_src[key]
        cap = max(2, min(sc, 220))
        for j in range(min(span, 220)):
            a = ftr[min(o + j, nftr - 1)]
            b = ftr[min(oc + min(j, cap - 1), nftr - 1)]
            if (a[0] >> 3, a[1]) != (b[0] >> 3, b[1]):
                return False
        fz = ftr[min(oc + cap - 1, nftr - 1)]         # driver holds the frozen value
        for j in range(220, span):
            a = ftr[min(o + j, nftr - 1)]
            if (a[0] >> 3, a[1]) != (fz[0] >> 3, fz[1]):
                return False
        return True

    canon_filt = {}                                                       # keyed by onset
    for o, key in drive_key.items():
        span = _gap(o)
        canon_filt[o] = (canon_prog[key] if _filt_exact(o, span, key)
                         else filter_program_for(ftr, o, span))

    # WINDOW-START residual filter (the "seam"): a window beginning between drives
    # played the previous drive's envelope TAIL in the original, but the part's
    # driver has no filter program until the first in-window drive. Attach a
    # synthetic restart to the window's first note (any voice — the filter is
    # global) capturing the residual ftr from that note to the first drive.
    # Lossless (pure capture); also covers song start when the original sets the
    # filter at init before any envelope drive.
    first_drive = next((o for o in drive_frames if t0w <= o < t1w), None)
    lead_end = first_drive if first_drive is not None else min(t1w, nftr)
    cands = [(o, v) for v in range(3) for o in onsets[v] if t0w <= o < lead_end]
    # a tune whose filter is TRULY UNUSED (no drives, cutoff AND res/routing
    # both zero throughout) must not get the synthetic residual program:
    # emitting one sets a passband bit in F_MODE and the driver then writes
    # $D418 = mode|$0f every frame (Hubbard v1 never touches the filter; its
    # $D418 must stay $0F — VICE-dump-verified: vol match 0% -> 100%)
    if not drive_frames and all(c == 0 and ct == 0
                                for c, ct in ftr[:min(nftr, 3000)]):
        cands = []
    if cands and (first_drive is None or first_drive > t0w):
        o0, v0 = min(cands)
        if (v0, o0) not in drives and lead_end - o0 >= 2:
            canon_filt[o0] = filter_program_for(ftr, o0, lead_end - o0)
            drives.add((v0, o0))
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
        relwf = _relwf_of(m, mon_i)
        key = (ad, sr, raw, wp, flag, tuple(filt) if filt else None, relwf)
        if getattr(m, 'hp_engine', 0):
            # the HP pulse engine keys live PW state by ROM instrument — two
            # timbre-identical instruments with different PW/pulseval/fx must
            # stay distinct slots or one drum inherits the other's pulse
            key += (ins.get('pw', 0x800), ins.get('pulseval', 0),
                    ins.get('fx', 0))
        if key not in iidx:
            iidx[key] = len(exi)
            exi.append((ad, sr, raw, _rle_wave(wp), flag, filt, mon_i, relwf))
            icount.append(0)
        icount[iidx[key]] += 1
        return iidx[key]

    t0, t1 = win if win else (0, 1 << 30)
    for v in range(3):
        tk = 0
        for _pat, events in m._voice_blocks(v):
            blk = []
            for ei, ev in enumerate(events):
                fr = m.tick_to_frame(tk) + delay
                dur_f = m.tick_to_frame(tk + ev.dur) - m.tick_to_frame(tk)
                etk, edur = tk, ev.dur                        # effective tick/duration
                if not (t0 <= fr < t1):                       # outside the window
                    # BOUNDARY CONTINUATION: a note gated across the window START
                    # otherwise leaves its voice silent until its next onset (a 6s
                    # window lost 44% of a voice — Cybernoid_II part7 V1). Re-enter
                    # the note at t0: every program is captured from the t0 phase,
                    # so the tail replays the original's remaining frames exactly
                    # (the exactness guards reject phase-0 structural substitutions
                    # for these mid-note captures automatically).
                    end_f = m.tick_to_frame(tk + ev.dur) + delay
                    if (win is None or getattr(ev, 'rest', False)
                            or not (fr < t0 < end_f)):
                        tk += ev.dur
                        continue
                    etk = m.frame_to_tick(max(0, t0 - delay))
                    edur = tk + ev.dur - etk
                    fr = m.tick_to_frame(etk) + delay
                    dur_f = m.tick_to_frame(etk + edur) - m.tick_to_frame(etk)
                    if edur < 1 or dur_f < 1:
                        tk += ev.dur
                        continue
                if getattr(ev, 'rest', False):                # REST: gate-off rows only
                    blk.append((None, ev.dur, None, None, tk, 0, False))
                    tk += ev.dur
                    continue
                ticks = edur
                while ticks > 1 and (m.tick_to_frame(etk + ticks)
                                     + delay) > t1:           # clip the last note to the window
                    ticks -= 1
                # base = the freq the DRIVER plays for the (clamped) note, so the FM
                # offsets reconstruct exactly. Use the clamped note for the base too —
                # else a note clamped to SF2_NOTE_MIN (e.g. MoN's $00 silent note) drifts
                # the whole note's freq by note_freq(clamped)-note_freq(raw).
                note_c = max(SF2_NOTE_MIN, min(ev.note, SF2_NOTE_MAX))
                base = m.note_freq(note_c)
                cfr = _snap_onset(m, frames, v, fr)           # capture onset (gate-rise)
                if base == 0:
                    # OUT-OF-RANGE pitch (Hubbard drums read runtime state past
                    # the freq table; static lookup = 0): the driver's base-hold
                    # trigger frame played SILENCE (1 bad frame per drum note).
                    # Resolve the row's note from the trace so the hold frame
                    # plays the sounding semitone; the FM offsets re-absorb.
                    for kk in (1, 0, 2):
                        tf = (frames[cfr + kk][0][v]['freq']
                              if cfr + kk < len(frames) else 0)
                        if tf:
                            note_c = max(SF2_NOTE_MIN,
                                         min(freq_to_semi(tf), SF2_NOTE_MAX))
                            base = m.note_freq(note_c)
                            break
                flag, filt = (canon_filt.get(cfr, (0, None))
                              if (v, cfr) in drives else (0, None))
                if (getattr(m, 'hard_restart', 0)
                        and not getattr(m, 'freerun_pulse', 0)):
                    flag |= 0x08                  # free-running pulse (PFREE) —
                                                  # v1 captured-mode wobbles keep
                                                  # phase; v2 (Delta) FETCH RESETS
                                                  # the PW from the record, so the
                                                  # program must restart per note
                fmp = fm_program_for(frames, v, cfr, dur_f, base,
                                     allow_loop=bool(getattr(m, 'fm_loop', 0)))
                # guard-compare window: skip the ~3 end-of-note boundary frames,
                # but NEVER go below 2 — _fm_unroll's frame 0 is always the base
                # hold, so fcmp=1 compares nothing and any canonical/arp/vibrato
                # substitution passes vacuously (Cybernoid part7's 3-frame notes
                # took a +$46/frame slide canonical -> +0.25-semitone runs).
                fcmp = max(2, dur_f - 3)
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
                    # tolerance must scale with the COMPARED frames: short
                    # notes compare fcmp=3 frames, so the flat max(4,...)
                    # accepted ANY arp vacuously (Fuck_Off's drum section
                    # played garbage steps — 143 five-frame runs)
                    tol = min(max(1, fcmp // 3), max(4, dur_f // 8))
                    if bad <= tol:
                        fmp = arp
                if not _is_struct_fm(fmp):
                    if ARP_STRUCT and getattr(ev, 'slide', None):
                        sl = _slide_fm_program(m, ev, note_c, fmp, dur_f)
                        if sl is not None:
                            fmp = sl
                    # scaled-vibrato entries need FMSCALE_ON in the driver —
                    # disabled for hard_restart (Hubbard) builds, so skip the
                    # vibrato substitution there (canon_fm below is enough)
                    if (ARP_STRUCT and not _is_struct_fm(fmp)
                            and not getattr(m, 'hard_restart', 0)):
                        # pitch-proportional VIBRATO -> one looping SCALED program
                        # for every pitch/duration (exact-guarded via unroll)
                        step = m.note_freq((note_c + 1) & 0x7F) - base
                        vib = _vibrato_program(fmp, step) if step > 0 else None
                        if (vib is not None
                                and _fm_unroll(vib, fcmp, step) == _fm_unroll(fmp, fcmp)):
                            fmp = vib
                    cf = canon_fm.get((ev.instr, ev.wprog))
                    if (ARP_STRUCT and cf is not None and cf != fmp
                            and not _is_struct_fm(fmp) and not _is_struct_fm(cf)):
                        if _fm_unroll(cf, fcmp) == _fm_unroll(fmp, fcmp):
                            fmp = cf
                        elif getattr(m, 'hard_restart', 0):
                            # SEMITONE-grid acceptance (Hubbard): same-instrument
                            # vibratos/drum-dives at different pitches differ by
                            # sub-semitone Hz but share the audible contour — one
                            # canonical serves all pitches (bundle collapse:
                            # Commando 1191 raw bundles for the whole song)
                            cu = _fm_unroll(cf, fcmp)
                            pu = _fm_unroll(fmp, fcmp)

                            def _sg(off):
                                return freq_to_semi((base + (off - 0x10000
                                                    if off >= 0x8000 else off))
                                                    & 0xFFFF)
                            bad = sum(1 for a, b in zip(cu, pu)
                                      if _sg(a) != _sg(b))
                            if bad <= max(2, dur_f // 8):
                                fmp = cf
                if freerun[v] is not None:
                    pp = freerun[v]               # one per-voice stream, phase kept
                    flag |= 0x08                  # driver: no pulse reset on note-on
                else:
                    pdur = dur_f
                    if getattr(m, 'freerun_pulse', 0) and not getattr(ev, 'tie', False):
                        # ties never restart the pulse program — only the chain
                        # HEAD's program runs, so its capture must span the
                        # whole tie chain (Delta's drones froze mid-ramp)
                        ct, j = etk + edur, ei + 1
                        while j < len(events) and getattr(events[j], 'tie', False):
                            ct += events[j].dur
                            j += 1
                        cf = min(m.tick_to_frame(ct) + delay, t1)
                        pdur = max(dur_f, cf - fr)
                    # loops ONLY where a capped capture would FREEZE (pdur past
                    # the cap): the driver's loop row costs a 1-frame hold per
                    # lap, which drifts a fully-captured short note that the
                    # plain program reproduces exactly (SM v0 pulse 100 -> 58.9
                    # when loops applied unconditionally — measured)
                    pp = pulse_program_for(
                        frames, v, cfr, pdur,
                        allow_loop=bool(getattr(m, 'freerun_pulse', 0))
                        and pdur > FM_CAP)
                    cp = canon_pulse.get((ev.instr, ev.wprog))
                    # compare minus the last frame: the capture's final frame holds
                    # the NEXT note's base reset (the same 1-frame register skew as
                    # the wave bleed) — the note's own program reproduces that bleed,
                    # the canonical continues the sweep instead (<=1 frame/note)
                    # floor 2: same vacuous-guard class as the FM fcmp fix —
                    # short notes compared over <=1 frame accept any canonical
                    cmp_f = max(2, dur_f - 1)
                    pcanon = ARP_STRUCT or PULSE_CANON or getattr(m, 'pulse_canon', 0)
                    if pcanon and cp is not None and cp != pp:
                        if getattr(m, 'hard_restart', 0):
                            # Hubbard: the per-instrument pulse wobble free-runs;
                            # per-note captures differ only in PHASE. Use the
                            # instrument canonical ALWAYS (phase restarts per
                            # note — PWM phase is inaudible; this is the
                            # whole-song bundle-collapse trade, ear-gated)
                            pp = cp
                        elif _pulse_unroll(cp, cmp_f) == _pulse_unroll(pp, cmp_f):
                            pp = cp
                bi = bundle_of(fmp, pp)
                relwf = _relwf_of(m, ev.instr)
                if relwf is not None:
                    gate_ticks, wfs_c, off_k, end_c = _rel_split(
                        m, frames, v, cfr, dur_f, etk, ticks, relwf)
                else:
                    gate_ticks, wfs_c, off_k, end_c = _gate_split(
                        m, frames, v, cfr, dur_f, etk, ticks)
                cw = canon_wave.get((ev.instr, ev.wprog))
                drv_gate = m.tick_to_frame(etk + gate_ticks) - m.tick_to_frame(etk)
                skew0 = off_k if off_k is not None else end_c
                if (cw is not None and wfs_c is not None
                        and (_wave_rel_ok(cw, wfs_c, drv_gate, off_k, end_c,
                                          relwf, wcanon)
                             if relwf is not None
                             else _wave_masked_ok(cw, wfs_c, drv_gate, skew0,
                                                  end_c))):
                    wp = cw                       # canonical reproduces this note's capture
                elif off_k is not None:
                    wp = _settle_trim(wfs_c[:off_k])
                    if wcanon:
                        wp = _first_row_norm(wp)
                else:
                    # keep the full capture INCLUDING the trailing next-note attack
                    # bleed: reproducing it is byte-better (osc3 wf 97.8 vs 91.6
                    # trimmed — measured); the "phantom onset" it causes in onset
                    # metrics is a metric artifact, not a register error.
                    # WAVE REST-TAIL: the engine can change $D404 during the REST
                    # after a note (Supremacy writes wf $00 = wave-off mid-rest;
                    # holding the release waveform instead cost a 60-frame run =
                    # its whole osc2 residual). Extend the capture window across
                    # the following rest events up to the next note — settle-trim
                    # keeps hold-tails free, so rows are added only where the
                    # trace actually changes; gate-off rows output program&$fe,
                    # so a captured $00 row reproduces the wave-off exactly.
                    wave_dur = dur_f
                    jr, gtk = ei + 1, etk + edur
                    while jr < len(events) and getattr(events[jr], 'rest', False):
                        gtk += events[jr].dur
                        jr += 1
                    if gtk > etk + edur:
                        rest_end = min(m.tick_to_frame(gtk) + delay, t1)
                        wave_dur = max(dur_f, min(rest_end - cfr, WAVE_CAP))
                    wp = _wave_prog_for(frames, v, cfr, wave_dur)
                    if wcanon:
                        wp = _first_row_norm(wp)
                ii = instr_of(ev.instr, wp, flag, filt)
                blk.append((note_c, ticks, bi, ii, etk, gate_ticks,
                            getattr(ev, 'tie', False)))
                tk += ev.dur
            if blk:
                note_recs[v].append(blk)

    # INSTR_DECOMPOSE=1: pre-cluster instrument decomposition — how many SLOTS each
    # SOURCE instrument exploded into and why (the wave program is the usual culprit:
    # first-byte boundary bleed / duration-positioned release tails / hold-length
    # variants — see memory/soundmonitor-player.md "THE INSTRUMENT-CAP OPTIMIZER").
    if os.environ.get("INSTR_DECOMPOSE"):
        by_src = {}
        for k in range(len(exi)):
            by_src.setdefault(exi[k][6], []).append(k)
        print(f"  INSTR_DECOMPOSE {win}: {len(by_src)} source instruments -> "
              f"{len(exi)} slots")
        for src in sorted(by_src):
            ks = by_src[src]
            print(f"    src {src}: {len(ks)} slot(s)")
            for k in sorted(ks, key=lambda k: -icount[k]):
                ad, sr, raw, wrle, flag, filt, _s, rw = exi[k][:8]
                print(f"      n={icount[k]:3d} ad={ad:02x} sr={sr:02x} "
                      f"flag={flag:02x} filt={'Y' if filt else '-'} "
                      f"rel={'%02x' % rw if rw is not None else '--'} wave={wrle}")
        fprogs = {tuple(filt) for e in exi for filt in [e[5]] if filt}
        print(f"    filter: {len(fprogs)} distinct programs, "
              f"{sum(len(p) for p in fprogs)} rows")

    # Adaptive packing probes the PRE-cluster resource counts for a candidate window
    # (cheap: pass-1 only, no clustering / assemble) to grow windows up to the caps.
    # Returns (#bundles, #instruments, #wave-rows, #filter-rows, #sequences). The two
    # row counts are the deduped totals laid into the 256-row WAVE/FILTER tables; the
    # sequence count is the total packed sequences across all voices (the native
    # driver's seq-pointer table holds 128 — overflow corrupts the LAST voice, osc3).
    if count_only:
        wkeys, wrows, fkeys, frows = set(), 0, set(), 0
        for _ad, _sr, _raw, waveprog, _flag, filt, _src, _rw in exi:
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
                for note, dur, bi, ii, _ontk, gate, tie in blk:
                    if note is None:                          # REST -> gate-off rows
                        rows.extend(D11Row(note=0x00) for _ in range(dur))
                        continue
                    rows.append(D11Row(note=note, tie=tie,
                                       instrument=ii if ii != cur_inst else None,
                                       command=bi if bi != cur_cmd else None))
                    cur_inst, cur_cmd = ii, bi
                    rows.extend(D11Row(note=SF2_GATE_ON) for _ in range(max(0, gate - 1)))
                    rows.extend(D11Row(note=0x00) for _ in range(max(0, dur - gate)))
                nseg += len(segment_track(_hr_rows(rows, getattr(m, 'hard_restart', 0))))
        # effective (not raw) bundle count: a window can grow past 64 raw bundles if the
        # excess merges away inaudibly (see effective_bundle_count / BUNDLE_TOL).
        nb = effective_bundle_count(exb, bcount, BUNDLE_TOL)
        if os.environ.get("BUNDLE_DECOMPOSE"):
            nfm = len({tuple(fp) for fp, pp in exb})
            npul = len({tuple(pp) for fp, pp in exb})
            print(f"  DECOMPOSE {win}: pairs={len(exb)} distinct_FM={nfm} "
                  f"distinct_pulse={npul} effective@tol{BUNDLE_TOL}={nb}")
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
        d += 0 if a[7] == b[7] else 150          # release wf differs (RELEASE_WF)
        return d

    def bgate(i, j):                         # an INAUDIBLE bundle merge: same pulse +
        if exb[i][1] != exb[j][1]:           # FM-contour L1 within tolerance
            return False                     # (also protects free-run stream bundles)
        if _is_struct_fm(exb[i][0]) or _is_struct_fm(exb[j][0]):
            return False                     # structural programs never gate-merge
        return sum(abs(a - b) for a, b in zip(bcurves[i], bcurves[j])) <= BUNDLE_TOL
    bmap, breps = greedy_cluster(exb, bcount, bdist, 63, gate=bgate if BUNDLE_TOL > 0 else None)
    if len(exb) > len(breps):
        print(f"  WARNING: {len(exb) - len(breps)} of {len(exb)} bundles FORCE-MERGED "
              f"(ungated) — the window exceeds the 63-bundle cap; freq/pulse programs "
              f"WILL be wrong for merged notes. Use adaptive ('auto') windows.")
    imap, ireps = greedy_cluster(exi, icount, idist, 32)
    bundles = [exb[r] for r in breps]
    instrs = [exi[r][:3] for r in ireps]
    wave_programs = [exi[r][3] for r in ireps]
    instr_flags = [exi[r][4] for r in ireps]
    filter_programs = [exi[r][5] for r in ireps]
    instr_src = [exi[r][6] for r in ireps]        # source (engine) instrument index
    instr_relwf = [exi[r][7] for r in ireps]      # per-slot release wf (RELEASE_WF)

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
            for note, dur, bi, ii, _ontk, gate, tie in blk:
                if note is None:                              # REST -> gate-off rows
                    rows.extend(D11Row(note=0x00) for _ in range(dur))
                    continue
                slot, cmd = imap[ii], bmap[bi]
                rows.append(D11Row(note=note, tie=tie,
                                   instrument=slot if slot != cur_inst else None,
                                   command=cmd if cmd != cur_cmd else None))
                cur_inst, cur_cmd = slot, cmd
                rows.extend(D11Row(note=SF2_GATE_ON) for _ in range(max(0, gate - 1)))
                rows.extend(D11Row(note=0x00) for _ in range(max(0, dur - gate)))
            for pk in segment_track(_hr_rows(rows, getattr(m, 'hard_restart', 0))):
                segs[v].append(pk)
    return (segs, bundles, instrs, wave_programs, instr_flags, filter_programs,
            instr_src, instr_relwf)


def emit_one(m, br, out_path, label):
    """Assemble + wrap one build result (segs, bundles, instrs, ...) into an SF2."""
    (segs, bundles, instrs, wave_programs, instr_flags, filter_programs,
     instr_src, instr_relwf) = br
    pulse_programs = [static_pulse(0x800) for _ in instrs]
    B.GAL = MON_DIR
    B.TEMPO = m.frames_per_tick
    # swing tunes (Supremacy $80 speed flag): the driver's row grid alternates
    # TEMPO2 (short) / TEMPO (long), matching MON.tick_to_frame. Constant tunes
    # set TEMPO2 == TEMPO (the driver toggle is inert).
    B.TEMPO2 = m.speed if getattr(m, "tempo_toggle", False) else m.frames_per_tick
    # Supremacy engine hard-restart preamble: EVERY retrigger frame plays freq $0000
    # + wf $41 for one frame before the note proper (trace-RE'd; the Hawkeye-family
    # engines have no such frame — measured 100% without it).
    B.NOTE_PREAMBLE = 1 if getattr(m, "ol_mode", None) == "supremacy" else 0
    # Hubbard release "kill adsr" (AD=SR=0 on gate-off) + per-retrigger ADSR re-arm —
    # decisive for the audible attack punch, invisible to register-state metrics.
    B.HARD_RESTART = 1 if getattr(m, "hard_restart", 0) else 0
    # $7f+byte1 pulse LOOP rows standalone (periodic PWM: the SM triangle) — a
    # HARD_RESTART build already compiles the path, this enables it without HR
    B.PULSE_LOOP = 1 if getattr(m, "pulse_loop", 0) else 0
    # SM-class: the note-set re-inits the PW base on EVERY note incl. tie/legato
    B.PULSE_TIE = 1 if getattr(m, "pulse_tie", 0) else 0
    # SM-class: gated-off frames write the instrument's RELEASE waveform (poked
    # IRELWF) verbatim instead of program&$fe — the instrument-cap optimizer's
    # tail split (only meaningful when the shim provides per-instrument
    # 'release_wf'; mutually exclusive with HP_ENGINE/TEMPO_SCHED, see the asm)
    B.RELEASE_WF = 1 if getattr(m, "release_wf", 0) else 0
    # scaled FM entries collide with real $40-$43xx Hz deltas (Hubbard drum dives)
    B.FM_SCALED = 0 if getattr(m, "hard_restart", 0) else 1
    B.HP_ENGINE = 1 if getattr(m, "hp_engine", 0) else 0
    # Hubbard v2 fractional tempo (the swallow counter): the shim sets
    # swallow = (period, frames-until-first-skip) per part window
    B.TEMPO_SWALLOW = 1 if getattr(m, "swallow", None) else 0
    # Hubbard v2 IRREGULAR tempo: the shim sets sched = (bitmap, phase) per part
    # (a per-frame stretch pattern from measure_tick_schedule). Takes precedence
    # over the single swallow counter.
    B.TEMPO_SCHED = 1 if getattr(m, "sched", None) else 0
    if B.TEMPO_SCHED:
        B.TEMPO_SWALLOW = 0
        B.TEMPO = getattr(m, "sched_tempo", B.TEMPO)
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
    if getattr(m, "hp_engine", 0):
        # poke the HP pulse-engine tables, keyed by ROM INSTRUMENT (the ROM's
        # live PW state is per instrument record; the emit pipeline splits one
        # ROM instrument across several slots — HPMAP $19E0 maps slot -> src):
        # HPVAL $1940 (pulseval), HPFX $1960 (fx: bit3 = fast-PWM),
        # HPW_LO/HI $1980/$19A0 (live PW at window start), PDLY/PDIR $19C3/$19C6
        # (per-voice counters at window start — the ROM ships nonzero initials
        # and never resets them at note fetch).
        prg = bytearray(prg)
        pload = prg[0] | (prg[1] << 8)
        need = 0x1A00 - pload + 2
        if len(prg) < need:                       # the tables are EQUATES past
            prg.extend(bytes(need - len(prg)))    #   the assembled image end

        def poke(addr, val):
            off = addr - pload + 2
            if 0 <= off < len(prg):
                prg[off] = val & 0xFF
        hp = getattr(m, "hp_state", None) or {}
        live_pw = hp.get("live_pw", {})
        for slot, src in enumerate(instr_src[:32]):
            ins = m.instrument(src)
            rom_i = src & 0x1F
            poke(0x19E0 + slot, rom_i)                       # HPMAP
            pw = live_pw.get(rom_i, ins.get('pw', 0x800))
            fx = ins.get('fx', 0)
            if not hp.get('mode_a', True):
                fx &= ~0x08          # this ROM revision has no fast-PWM mode;
            elif fx & 0x08:
                # mode A integrates pv per FRAME of absolute time; the emitted
                # stream starts `phase` frames earlier than the original, so
                # pre-advance the accumulator or it lags by pv*phase forever
                pw = (pw + ins.get('pulseval', 0)
                      * getattr(m, 'onset_delay', 0)) & 0x0FFF
            poke(0x1940 + rom_i, ins.get('pulseval', 0))     # HPVAL
            poke(0x1960 + rom_i, fx)                         # HPFX
            poke(0x1980 + rom_i, pw & 0xFF)                  # HPW_LO
            poke(0x19A0 + rom_i, (pw >> 8) & 0x0F)           # HPW_HI
        for v in range(3):
            poke(0x19C3 + v, hp.get("pdly", [0, 0, 0])[v])   # PDLY
            poke(0x19C6 + v, hp.get("pdir", [0, 0, 0])[v])   # PDIR
        prg = bytes(prg)
    if B.RELEASE_WF:
        # poke IRELWF ($1960, 32 bytes): per-slot release waveform. Slots whose
        # instrument declared none get 0 (their notes never emit gate-off rows
        # under the tail split, so the byte is only reached on true rests —
        # where wf 0 matches the original's idle wave-off)
        prg = bytearray(prg)
        pload = prg[0] | (prg[1] << 8)
        need = 0x1A00 - pload + 2
        if len(prg) < need:
            prg.extend(bytes(need - len(prg)))
        for slot, rw in enumerate(instr_relwf[:32]):
            prg[0x1960 + slot - pload + 2] = (rw or 0) & 0xFF
        prg = bytes(prg)
    sw = getattr(m, "swallow", None)
    sched = getattr(m, "sched", None)
    if sw or sched:
        # fractional tempo pokes are INDEPENDENT of the HP pulse engine —
        # leaving them inside the hp_engine block shipped an SF2 whose driver
        # read SWP=0 and swallowed EVERY tick (silence)
        prg = bytearray(prg)
        pload = prg[0] | (prg[1] << 8)
        need = 0x1A00 - pload + 2
        if len(prg) < need:
            prg.extend(bytes(need - len(prg)))
        if sched:
            # TEMPO_SCHED: poke the per-frame stretch bitmap ($1940), the period
            # length ($19CE) and the part's starting phase ($19CF)
            bitmap, phase = sched
            bm = bitmap[:128]
            for i, b in enumerate(bm):
                prg[0x1940 + i - pload + 2] = 1 if b else 0
            prg[0x19CE - pload + 2] = len(bm) & 0xFF             # SCHEDLEN
            prg[0x19CF - pload + 2] = phase % max(1, len(bm))    # SCHEDIDX
        else:
            per, first = sw
            prg[0x19CC - pload + 2] = max(0, first) & 0xFF       # SWC (countdown)
            prg[0x19CD - pload + 2] = max(0, per - 1) & 0xFF     # SWP (reload)
        prg = bytes(prg)
    sf2 = B.wrap(prg, gen, edit, mdp,
                 instr_names=[f"instr {i}" for i in range(len(instrs))],
                 sid_model=getattr(m, "sid_model", 6581))
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
    # PSEUDO-PARSE GATE: files from OTHER engine generations sometimes "parse"
    # with a mis-located speed table (Turbo_Outrun speed=255 -> a 3280s trace
    # that looks like a hang). Real MoN tunes run speed 1-8.
    if not (1 <= m.frames_per_tick <= 8):
        sys.exit(f"{os.path.basename(sid)} sub{sub}: implausible speed byte "
                 f"{m.speed} (frames/tick={m.frames_per_tick}) — this is a "
                 f"pseudo-parse of an unsupported engine variant, not a real "
                 f"MoN decode. Refusing to build.")
    used = mon_to_sf2.used_instruments(m)
    instr_rows, wave_table, pulse_table, idx_map = mon_to_sf2.build_instruments(m, used)
    base = os.path.splitext(os.path.basename(sid))[0]
    print(f"{os.path.basename(sid)} sub{sub}: load=${la:04X}")

    if adaptive or winsec > 0:
        import mon_fidelity as F
        span = m.tick_to_frame(max(sum(ev.dur for ev in m.voices[v])
                                   for v in range(3)))
        # events are placed at tick_to_frame(tk) + onset_delay, so the last note's
        # end lands delay frames past the raw tick span — without this the final
        # window's clip loop shaves the song's last tick (3007-vs-3008 rows).
        span += getattr(m, "onset_delay", 0)
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
        prune_stale_parts(os.path.join(ROOT, "out", "mon", f"{base}_sub{sub}"),
                          nparts)
        return

    br = build_native_song(m, sid, sub, idx_map, instr_rows)
    out = os.path.join(ROOT, "out", "mon", f"{base}_sub{sub}_native.sf2")
    emit_one(m, br, out, f"{base}_sub{sub}")


if __name__ == "__main__":
    main()
