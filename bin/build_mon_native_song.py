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

FM_CAP = 128                                       # max frames of FM captured per note
WAVE_CAP = 96                                      # max frames of wave/gate envelope per note


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
    # so FM entries apply from frame 1 onward — drop delta[0] (frame 0 = base).
    deltas = [(targ[k] - targ[k - 1]) & 0xFFFF for k in range(1, len(targ))]
    prog, run, rl = [], None, 0
    for delta in deltas:
        if delta == run:
            rl += 1
        else:
            if run is not None:
                prog.append((run & 0xFF, (run >> 8) & 0xFF, rl))
            run, rl = delta, 1
    if run is not None:
        prog.append((run & 0xFF, (run >> 8) & 0xFF, rl))
    if not prog or all(e[0] == 0 and e[1] == 0 for e in prog):
        return [(0, 0, 0)]                          # flat -> program 0 (freeze)
    prog.append((0, 0, 0))                          # hold the last offset
    return prog


def pulse_program_for(frames, v, onset, dur_f):
    """Per-note PULSE program (B3 PWM): reproduce the original's per-frame pulse
    width. 8X = set width frame 0; 0X = add per-frame delta (12-bit) for `run`
    frames; 7f = freeze. The driver restarts the pulse program per note (PPTR=
    VIPUL/VPC=0), so frame 0 sets the base — no 1-frame offset (unlike FM)."""
    targ, hold = [], None
    for k in range(min(dur_f, FM_CAP)):
        idx = onset + k
        pv = frames[idx][0][v]['pul'] if idx < len(frames) else None
        if pv is not None:
            hold = pv
        targ.append(hold if hold is not None else 0x800)
    prog = [(0x80 | ((targ[0] >> 8) & 0x0F), targ[0] & 0xFF, 1)]   # 8X set frame 0
    prev, run, rl = targ[0], None, 0
    for k in range(1, len(targ)):
        delta = (targ[k] - prev) & 0xFFF                          # 12-bit signed add
        prev = targ[k]
        if delta == run:
            rl += 1
        else:
            if run is not None:
                prog.append(((run >> 8) & 0x0F, run & 0xFF, rl))
            run, rl = delta, 1
    if run is not None:
        prog.append(((run >> 8) & 0x0F, run & 0xFF, rl))
    prog.append((0x7F, 0, 0))                                     # freeze (hold last)
    return prog


def extract_wave_programs(m, sid, sub, idx_map, instr_rows, frames):
    """Per-instrument WAVE program (B3 gate envelope): wave_step advances one row per
    FRAME and writes col0 to $D404 (gate bit preserved, VGMASK=$ff on a note). Sample
    the original's per-frame waveform over a note that uses each instrument, hold the
    last change point, and loop there — reproduces the $43->$42 / $41->$40 gate-off
    (note release) mid-note. col1 = 0 (pitch comes from the FM program, not semitones).
    Returns {slot: [(wf,0),...,(7f,loop_row)]}."""
    fpt = m.frames_per_tick
    progs = {}
    for v in range(3):
        fr = 0
        for ev in m.voices[v]:
            slot = idx_map.get(ev.instr, 0)
            dur_f = ev.dur * fpt
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
            fr += dur_f
    return progs


def filter_trace(sid, sub, secs):
    """Per-frame global filter state from siddump (fill-forward): (cutoff11, ctrl)
    where cutoff11 = ($D415&7)|($D416<<3) and ctrl = $D417 (res+routing)."""
    import subprocess
    import re
    txt = subprocess.run(['py', '-3', 'pyscript/siddump_complete.py', sid,
                          f'-a{sub}', f'-t{secs}'], capture_output=True, text=True).stdout
    cut, ctrl, out = 0, 0xF1, []
    for ln in txt.splitlines():
        if not ln.startswith('|') or 'Frame' in ln:
            continue
        c = [x.strip() for x in ln.split('|')]
        if len(c) < 6:
            continue
        mm = re.match(r'^([0-9A-F\.]{4})\s+([0-9A-F\.]{2})', c[5])
        if mm:
            if '.' not in mm.group(1):
                cut = int(mm.group(1), 16)
            if '.' not in mm.group(2):
                ctrl = int(mm.group(2), 16)
        out.append((cut, ctrl))
    return out


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


def detect_filter_drives(ftr, onsets_by_voice):
    """Find the filter-envelope restarts = the note-ons of the filter-routed voice.
    Each envelope ATTACK shows as a fast cutoff jump (>= FILT_FAST in 11-bit); map it
    back to the nearest note-on (any voice) within a few frames — that note triggers
    the envelope. Returns {onset_frame: voice}."""
    import bisect
    n = len(ftr)
    pairs = sorted({(o, v) for v in range(3) for o in onsets_by_voice[v]})
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
    """Per-note FILTER program = the cutoff ENVELOPE captured from the note-on until
    the next restart (`span`), compressed into a SET row + ADD-rows (one per run of
    constant per-frame delta) + a freeze. This reproduces the full attack/decay/rise/
    sustain exactly and compactly (vs the old settle-then-freeze, which truncated the
    slow envelopes). The driver applies row 0 on the onset frame, so capture from k=0."""
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


def _fm_curve(fp, length=24):
    """Cumulative FM offset shape (signed) over `length` frames — the audible pitch
    contour, for clustering distance. fp = [(lo,hi,dur),...]."""
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


def greedy_cluster(items, count, dist, cap):
    """Map `items` onto <=cap representatives by greedy nearest-merge: repeatedly
    fuse the two whose merge costs the least (per-item distance * the SMALLER item's
    note count, so the loss lands on the fewest notes). dist(i,j) -> float. Returns
    (mapping[old_idx]->rep_idx_in_items, sorted_unique_reps)."""
    n = len(items)
    if n <= cap:
        return list(range(n)), list(range(n))
    parent = list(range(n))
    cnt = list(count)
    active = list(range(n))
    while len(active) > cap:
        best = None
        for x in range(len(active)):
            i = active[x]
            for y in range(x + 1, len(active)):
                j = active[y]
                cost = dist(i, j) * min(cnt[i], cnt[j])
                if best is None or cost < best[0]:
                    best = (cost, x, y)
        _, x, y = best
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
    fpt = m.frames_per_tick
    # trace the WHOLE one-pass song length (the longest voice), else notes past the
    # window get degenerate held programs. Traces can be passed in (windowed builds
    # reuse one trace across all windows instead of re-siddumping per window).
    if traces is not None:
        frames, ftr = traces
    else:
        span = max(sum(ev.dur for ev in m.voices[v]) for v in range(3)) * fpt
        secs = span // 50 + 4
        frames = F.per_frame(sid, [f'-a{sub}', f'-t{secs}'])
        ftr = filter_trace(sid, sub, secs)
    # The filter is ONE GLOBAL per-note cutoff ENVELOPE on the filter-routed voice;
    # it restarts on that voice's note-ons. Find those note-ons (the envelope attacks,
    # mapped back to the triggering note) -> `drives`; the span until the next restart
    # is how long each envelope program runs before re-triggering.
    onsets = [set() for _ in range(3)]
    onset_instr = [dict() for _ in range(3)]               # onset_frame -> MoN instrument
    for v in range(3):
        fr = 0
        for ev in m.voices[v]:
            if ev.retrig:
                onsets[v].add(fr)
                onset_instr[v][fr] = ev.instr
            fr += ev.dur * fpt
    drive_map = detect_filter_drives(ftr, onsets)           # {onset_frame: voice}
    drives = {(v, o) for o, v in drive_map.items()}
    drive_frames = sorted(drive_map)

    def _gap(onset):
        j = bisect.bisect_right(drive_frames, onset)
        return (drive_frames[j] - onset) if j < len(drive_frames) else 220

    # The cutoff envelope is per-INSTRUMENT and deterministic from note-on, so capture
    # ONE canonical program per driving instrument — from its LONGEST-gap note (the most
    # complete envelope, to sustain). Short notes reuse it; the driver's per-note restart
    # truncates it. This keeps it to a few filter programs (dedup) instead of one per note.
    canon_onset = {}                                       # MoN instrument -> longest-gap onset
    for o, v in drive_map.items():
        i = onset_instr[v].get(o)
        if i is not None and (i not in canon_onset or _gap(o) > _gap(canon_onset[i])):
            canon_onset[i] = o
    canon_filt = {i: filter_program_for(ftr, o, _gap(o)) for i, o in canon_onset.items()}
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
            exi.append((ad, sr, raw, [(w, 0x00) for w in wp] + [(0x7F, len(wp) - 1)],
                        flag, filt))
            icount.append(0)
        icount[iidx[key]] += 1
        return iidx[key]

    t0, t1 = win if win else (0, 1 << 30)
    for v in range(3):
        fr = 0
        for _pat, events in m._voice_blocks(v):
            blk = []
            for ev in events:
                dur_f = ev.dur * fpt
                if not (t0 <= fr < t1):                       # outside the window
                    fr += dur_f
                    continue
                ticks = ev.dur
                if fr + dur_f > t1:                           # clip the last note to the window
                    ticks = max(1, (t1 - fr) // fpt)
                # base = the freq the DRIVER plays for the (clamped) note, so the FM
                # offsets reconstruct exactly. Use the clamped note for the base too —
                # else a note clamped to SF2_NOTE_MIN (e.g. MoN's $00 silent note) drifts
                # the whole note's freq by note_freq(clamped)-note_freq(raw).
                note_c = max(SF2_NOTE_MIN, min(ev.note, SF2_NOTE_MAX))
                base = m.note_freq(note_c)
                flag, filt = (canon_filt.get(ev.instr, (0, None))
                              if (v, fr) in drives else (0, None))
                bi = bundle_of(fm_program_for(frames, v, fr, dur_f, base),
                               pulse_program_for(frames, v, fr, dur_f))
                ii = instr_of(ev.instr, _wave_prog_for(frames, v, fr, dur_f), flag, filt)
                blk.append((note_c, ticks, bi, ii, fr))
                fr += dur_f
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
                    lead = (blk[0][4] - t0) // fpt
                    rows.extend(D11Row(note=0x00) for _ in range(max(0, lead)))
                first = False
                cur_inst = cur_cmd = None
                for note, dur, bi, ii, _onfr in blk:
                    rows.append(D11Row(note=note,
                                       instrument=ii if ii != cur_inst else None,
                                       command=bi if bi != cur_cmd else None))
                    cur_inst, cur_cmd = ii, bi
                    rows.extend(D11Row(note=SF2_GATE_ON) for _ in range(max(0, dur - 1)))
                nseg += len(segment_track(rows))
        return len(exb), len(exi), wrows, frows, nseg

    # --- CLUSTER to fit the driver caps (64 commands, 32 instruments) ---
    bcurves = [_fm_curve(fp) for fp, _ in exb]

    def bdist(i, j):
        fd = sum(abs(a - b) for a, b in zip(bcurves[i], bcurves[j]))
        pp = 0 if exb[i][1] == exb[j][1] else 300
        return fd + pp

    def idist(i, j):
        a, b = exi[i], exi[j]
        d = abs(a[0] - b[0]) + abs(a[1] - b[1]) + (200 if a[2] != b[2] else 0)
        d += 60 * sum(1 for x, y in zip(a[3], b[3]) if x != y) + 60 * abs(len(a[3]) - len(b[3]))
        d += 0 if (a[4] == b[4] and a[5] == b[5]) else 150
        return d

    bmap, breps = greedy_cluster(exb, bcount, bdist, 63)
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
                lead = (blk[0][4] - t0) // fpt               # window's first note at its tick
                rows.extend(D11Row(note=0x00) for _ in range(max(0, lead)))
            first = False
            cur_inst = cur_cmd = None
            for note, dur, bi, ii, _onfr in blk:
                slot, cmd = imap[ii], bmap[bi]
                rows.append(D11Row(note=note,
                                   instrument=slot if slot != cur_inst else None,
                                   command=cmd if cmd != cur_cmd else None))
                cur_inst, cur_cmd = slot, cmd
                rows.extend(D11Row(note=SF2_GATE_ON) for _ in range(max(0, dur - 1)))
            for pk in segment_track(rows):
                segs[v].append(pk)
    return segs, bundles, instrs, wave_programs, instr_flags, filter_programs


def emit_one(m, br, out_path, label):
    """Assemble + wrap one build result (segs, bundles, instrs, ...) into an SF2."""
    segs, bundles, instrs, wave_programs, instr_flags, filter_programs = br
    pulse_programs = [static_pulse(0x800) for _ in instrs]
    B.GAL = MON_DIR
    B.TEMPO = m.speed + 1
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
        fpt = m.frames_per_tick
        span = max(sum(ev.dur for ev in m.voices[v]) for v in range(3)) * fpt
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
