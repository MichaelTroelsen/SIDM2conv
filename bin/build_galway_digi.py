"""Galway DIGI capture -> sample bank + trigger sequence (asm data).

Galway's "4th channel" samples ($D418 volume digi) live in the RSID rips but are
driven by a fast IRQ/main-loop that py65/zig64 don't emulate. VICE does. This
tool:
  1. renders the tune through VICE with -sounddev dump (the full SID register
     stream, cycle-accurate),
  2. filters $D418 (reg 24), segments the nibble stream into bursts (drum hits),
  3. FUZZY-dedupes the bursts into a small unique sample bank,
  4. emits an asm include (digi_data.inc): the packed-as-1-nibble/byte bank, the
     per-sample offset/length index, and a per-onset trigger list (frame, sid).

The native Galway driver streams the active sample to $D418 from do_play (proven
to play in stock SF2II — no separate IRQ needed).

Usage: py -3 bin/build_galway_digi.py <SID name> [seconds] [tune]
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VSID = r"C:/winvice/bin/vsid.exe"
PAL = 985248
CYC_PER_FRAME = PAL // 50          # 19704
BANK_ADDR = 0x8000                 # sample bank base (free above the edit area)


def dump_d418(sidpath, seconds, tune):
    """Render via VICE, return the $D418 nibble stream as [(abs_cycle, nibble)]."""
    dump = os.path.join(ROOT, "out", "_digi.dump")
    try:                                   # vsid runs forever; timeout-kill is expected
        subprocess.run([VSID, "-console", "-sounddev", "dump", "-soundarg", dump,
                        "-tune", str(tune), sidpath],
                       capture_output=True, timeout=seconds + 2)
    except subprocess.TimeoutExpired:
        pass
    cum = 0
    out = []
    for line in open(dump):
        p = line.split()
        if len(p) != 3:
            continue
        try:
            c, r, v = int(p[0]), int(p[1]), int(p[2])
        except ValueError:
            continue
        cum += c
        if r == 24:
            out.append((cum, v & 0x0F))
    os.remove(dump)
    return out


def segment(writes, gap=3000, minlen=24):
    """Split the stream into bursts (a drum hit = a run of close-spaced writes).
    gap must exceed the music IRQ's mid-drum pause (~1-2k cycles on Arkanoid's
    2-raster player) so a single hit isn't fragmented, yet stay well below the
    inter-drum spacing (tens of thousands of cycles)."""
    bursts, cur = [], [writes[0]]
    for i in range(1, len(writes)):
        if writes[i][0] - writes[i - 1][0] > gap:
            if len(cur) >= minlen:
                bursts.append(cur)
            cur = []
        cur.append(writes[i])
    if len(cur) >= minlen:
        bursts.append(cur)
    return bursts


def fuzzy_dedupe(pcms, len_tol=12, diff_tol=float(os.environ.get("GALWAY_DRUM_DIFFTOL", "1.4"))):
    """Greedy-cluster near-identical sample PCMs. Returns (bank, sid_per_pcm).
    Two samples match if their lengths are within len_tol and the mean per-sample
    abs difference over the overlap is below diff_tol (4-bit scale 0..15)."""
    bank, sids = [], []
    for pcm in pcms:
        best = None
        for sid, rep in enumerate(bank):
            if abs(len(rep) - len(pcm)) > len_tol:
                continue
            n = min(len(rep), len(pcm))
            d = sum(abs(rep[i] - pcm[i]) for i in range(n)) / n
            if d < diff_tol and (best is None or d < best[1]):
                best = (sid, d)
        if best is not None:
            sids.append(best[0])
        else:
            sids.append(len(bank))
            bank.append(pcm)
    return bank, sids


# NCO loop fixed per-write cost: actual driver gap = NCO_FIXED + 5*ldx cycles
# (measured: ldx=4 -> ~57 cyc). The lead now carries a per-frame ldx so each note
# is written at the SOURCE's own gap; pitch falls out of (step, gap) directly with
# no global write-rate assumption.
NCO_FIXED = 37


def saw_step_gap(items):
    """(step, gap_cyc) for a clean sawtooth-lead frame, else None. step = signed
    dominant per-nibble delta (the original's 4-bit accumulator increment); gap =
    median within-frame $D418 write spacing (cycles)."""
    import numpy as np
    from collections import Counter
    if len(items) < 8:
        return None
    cs = [c for c, _ in items]
    ns = [n for _, n in items]
    gaps = np.diff(cs)
    inner = gaps[gaps < 1000]
    # The source writes the digi in FAST bursts with pauses; reSID SMOOTHS that down in
    # pitch (~2.9x lower than the bare fundamental). My driver writes a clean sawtooth
    # that reSID follows, so to land on the same perceived pitch I must write ~2.9x
    # SLOWER than the source's median gap. (Empirical reSID-smoothing factor.)
    g = float(np.median(inner)) * 2.9 if len(inner) else float(np.median(gaps))
    ds = [((ns[i] - ns[i - 1]) % 16) for i in range(1, len(ns))]
    ds = [d - 16 if d > 8 else d for d in ds]
    step, sc = Counter(ds).most_common(1)[0]
    if sc / len(ds) < 0.5 or step == 0 or g <= 0:
        return None
    return step, g


# Per-frame NCO cycle budget. SF2II emulates the WHOLE do_play (music engine + digi)
# within one PAL frame (~19704 cyc) and errors ("6510 emulation exceeded cycle
# window") if it overruns. The original voices its lead heavily (~150 writes * 108 =
# ~16200 cyc/frame), so the lead's count*gap must fit in (frame - music-engine cost).
# That music cost is per-tune (idle voices = cheap; busy = dear), so the budget is an
# env var. count is then min(source count, budget/gap): full notes when there's room,
# trimmed (as the source itself trims at wide gaps) when not.
NCO_BUDGET = int(os.environ.get("GALWAY_NCO_BUDGET", "14000"))


# Tight-NCO loop fixed per-write cost: driver gap = LEAD_FIXED + 5*ldx cycles (measured:
# ldx=2 -> ~48 cyc, so LEAD_FIXED~38). The lead is a 4-bit-accumulator sawtooth (incr =
# step<<4) regenerated by a tight loop. We set its write gap so its CLEAN-sawtooth
# fundamental == the original's actually-rendered (reSID-smoothed) pitch -- see below.
LEAD_FIXED = 38


def _peak_pitch(seg, sr):
    """Robust perceived-pitch estimate via AUTOCORRELATION (window-independent, immune
    to the FFT's bin quantization and to the digi's on/off-modulation sidebands that
    bias a spectral peak). Finds the fundamental PERIOD: the first strong autocorrelation
    peak, parabola-interpolated for sub-sample accuracy. 0 = silent/unvoiced."""
    import numpy as np
    if len(seg) < 512 or np.sqrt((seg ** 2).mean()) < 0.004:
        return 0.0
    x = (seg - seg.mean()) * np.hanning(len(seg))
    n = len(x)
    spec = np.fft.rfft(x, 2 * n)
    ac = np.fft.irfft(spec * np.conj(spec))[:n]
    if ac[0] <= 0:
        return 0.0
    ac = ac / ac[0]
    lo = max(2, int(sr / 3500))            # 200..3500 Hz search
    hi = min(n - 2, int(sr / 200))
    if hi <= lo + 2:
        return 0.0
    # first local max above 0.55 of the best peak in range -> the true fundamental,
    # not an octave-down (highest) or octave-up (sub-peak) alias.
    region = ac[lo:hi]
    thr = 0.55 * region.max()
    k = None
    for j in range(1, len(region) - 1):
        if region[j] >= thr and region[j] >= region[j - 1] and region[j] >= region[j + 1]:
            k = lo + j
            break
    if k is None:
        k = lo + int(np.argmax(region))
    a, b, c = ac[k - 1], ac[k], ac[k + 1]
    d = a - 2 * b + c
    lag = k + (0.5 * (a - c) / d if d != 0 else 0.0)
    return float(sr / lag)


def lead_notes(writes, nframes):
    """Group lead frames into NOTES: maximal runs of the same saw-step (rests within a
    note kept). Returns [(start_frame, end_frame)]. Used to measure/correct per note."""
    fr = {}
    for c, n in writes:
        fr.setdefault(c // CYC_PER_FRAME, []).append((c, n))
    steps = [(saw_step_gap(fr.get(f, [])) or (None,))[0] for f in range(nframes)]
    notes = []
    f = 0
    while f < nframes:
        if steps[f] is None:
            f += 1
            continue
        s = steps[f]
        start = end = f
        g = f + 1
        while g < nframes and (steps[g] == s or steps[g] is None):
            if steps[g] == s:
                end = g
            g += 1
        notes.append((start, end))
        f = end + 1
    return notes


# Closed-loop gap correction (per frame): the calibration wrapper renders MY output,
# measures it vs the original, and writes a per-frame multiplier here. With it, the
# capture targets pitch * corr[f] so MINE lands exactly on the original (iterated). When
# unset, fall back to the analytic reSID-smoothing model.
_GAPCORR = None
if os.environ.get("GALWAY_GAPCORR") and os.path.exists(os.environ["GALWAY_GAPCORR"]):
    import numpy as _np
    _GAPCORR = _np.load(os.environ["GALWAY_GAPCORR"])


def render_pitch_track(sidpath, tune, seconds, nframes, writes):
    """Render the ORIGINAL to WAV and measure the perceived pitch PER NOTE (not per
    frame): group consecutive same-step lead frames (rests within a note kept) and FFT
    the original's audio over the whole note -> a clean carrier pitch, free of the
    on/off-envelope bias a short per-frame window suffers. The driver's clean sawtooth
    fundamental is then set to exactly this, matching the original's SOUND note-for-note."""
    import wave
    import numpy as np
    wav = os.path.join(ROOT, "out", "_pitch.wav")
    try:
        subprocess.run([VSID, "-console", "-sounddev", "wav", "-soundarg", wav,
                        "-limitcycles", str(int((seconds + 0.3) * 985248)),
                        "-tune", str(tune), sidpath], capture_output=True, timeout=seconds + 30)
    except subprocess.TimeoutExpired:
        pass
    w = wave.open(wav, "rb"); sr = w.getframerate(); ch = w.getnchannels()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    w.close(); os.remove(wav)
    x /= 32768.0
    pitch = [0.0] * nframes
    for start, end in lead_notes(writes, nframes):
        p = _peak_pitch(x[int(start / 50.0 * sr):int((end + 1) / 50.0 * sr)], sr)
        if p > 0:
            for k in range(start, end + 1):
                pitch[k] = p
    return pitch


def lead_params(writes, pitch):
    """Parametric lead: per frame (incr, ldx, count). incr = (step&15)*16 (the source's
    4-bit sawtooth step). The gap is set so the driver's clean-sawtooth fundamental
    |step|*PAL/(16*gap) equals `pitch[f]` -- the original's actually-rendered pitch."""
    fr = {}
    for c, n in writes:
        fr.setdefault(c // CYC_PER_FRAME, []).append((c, n))
    nframes = max(fr) + 1
    table, kinds = [], []
    last_p = 1000.0
    for f in range(nframes):
        items = fr.get(f, [])
        sg = saw_step_gap(items)
        if sg is None:
            table.append((0, 1, 0))
            kinds.append('rest' if len(items) < 8 else 'drum')
            continue
        step, _ = sg
        p = pitch[f] if (f < len(pitch) and pitch[f] >= 80) else last_p
        last_p = p
        if _GAPCORR is not None and f < len(_GAPCORR) and _GAPCORR[f] > 0:
            target = p * float(_GAPCORR[f])             # closed-loop: measured correction
        else:
            sm = 0.890 + 6.31e-5 * p                    # analytic reSID-smoothing fallback
            target = p / sm if sm > 0.5 else p
        gap = abs(step) * 985248.0 / (16.0 * target)    # mine then renders == p
        ldx = max(1, min(255, int(round((gap - LEAD_FIXED) / 5.0))))
        gap_cyc = LEAD_FIXED + 5 * ldx
        count = max(1, min(len(items), NCO_BUDGET // gap_cyc, 255))
        incr = (step & 0x0F) << 4
        table.append((incr, ldx, count))
        kinds.append('saw')
    return nframes, table, kinds


# --- DIGI_SWEEP lead: reproduce the source's intra-frame gap SWEEP -------------------
# The source doesn't write at one steady gap -- within a frame the base gap sweeps in
# stepwise chunks (e.g. 32->39->53 cyc) plus a periodic +43-cyc player-loop hiccup. A
# single gap/frame matches the pitch but flattens the TIMBRE (the sweep's spectral
# richness -- the "1600 Hz band"). DIGI_SWEEP emits per-frame variable-length records
# [incr][nsegs][ldx,run]*nsegs so the driver's tight 4-bit loop reproduces the sweep.
LEAD_FIXED_SWEEP = 32          # sweep loop: driver gap = 32 + 5*ldx (measured: ldx=1 -> ~37
                               # cyc rendered; floor ~37 so the source's fastest 32-cyc
                               # writes land ~+0.25 semitone, larger gaps track closely)


def _sweep_ldx(gap):
    return max(1, min(255, int(round((gap - LEAD_FIXED_SWEEP) / 5.0))))


def rle_gaps(gaps, tol=8):
    """De-hiccup (snap a gap that's ~base+43 back to base) then RLE the gap sequence
    into [(gap, runlen)] segments (runlen = #writes at that gap)."""
    if not gaps:
        return []
    base = gaps[0]
    clean = []
    for g in gaps:
        if 33 <= g - base <= 52:           # periodic +43 player-loop hiccup -> base
            clean.append(base)
        else:
            base = g
            clean.append(g)
    segs = []
    cur = clean[0]
    run = 1
    for g in clean[1:]:
        if abs(g - cur) <= tol:
            run += 1
        else:
            segs.append((cur, run))
            cur = g
            run = 1
    segs.append((cur, run))
    return segs


# Optional knobs for FULL-LENGTH builds (the 20KB digi bank can't hold a full-resolution
# sweep for a multi-minute tune). GALWAY_SWEEP_CAP merges each frame's gap segments down
# to <=N (N=2 keeps the bright-start->pause character; N=1 is a flat gap). GALWAY_DIGI_RLE
# run-length-encodes consecutive identical frame-records ([rep][incr][nsegs][ldx,run]*),
# which the DIGI_RLE driver holds for `rep` frames -- together these fit a 2:22 tune.
SWEEP_CAP = int(os.environ.get("GALWAY_SWEEP_CAP", "0"))   # 0 = unlimited (full sweep)
SWEEP_RLE = bool(os.environ.get("GALWAY_DIGI_RLE"))
# Frames [0:INTRO) always use the FULL sweep (the exposed solo digi intro, where timbre
# matters most); the busier body honors SWEEP_CAP. Lets a full-length build keep the
# validated bright intro while the flat-capped body fits the 20KB bank.
SWEEP_INTRO = int(os.environ.get("GALWAY_SWEEP_INTRO", "0"))


def _cap_segments(segs, cap):
    """Merge a frame's (gap,run) segments down to <=cap, preserving total run count
    (count-weighted mean gap per merged group) so the sweep coarsens but stays in time."""
    if not cap or len(segs) <= cap:
        return segs
    n = len(segs)
    out = []
    for k in range(cap):
        grp = segs[k * n // cap:(k + 1) * n // cap] or [segs[min(k, n - 1)]]
        tot = sum(r for _, r in grp)
        gap = sum(g * r for g, r in grp) // max(1, tot)
        out.append((gap, tot))
    return out


def sweep_records(writes):
    """Per-frame DIGI_SWEEP records reproducing the source's gap sweep. Lead frame ->
    [incr][nsegs][ldx,run]*nsegs (incr = raw 4-bit step). Rest/drum frame -> [0][0].
    Honors GALWAY_SWEEP_CAP (coarsen) + GALWAY_DIGI_RLE (repeat-prefix, full-length).
    Returns the complete blob bytes (incl. terminator)."""
    fr = {}
    for c, n in writes:
        fr.setdefault(c // CYC_PER_FRAME, []).append((c, n))
    nframes = max(fr) + 1
    recs = []                              # per-frame (incr, [(ldx,run),...])
    nseg_tot = 0
    for f in range(nframes):
        items = fr.get(f, [])
        sg = saw_step_gap(items)
        if sg is None:
            recs.append((0, ()))           # rest/drum -> empty record
            continue
        step, _ = sg
        cs = [c for c, _ in items]
        gaps = [cs[i + 1] - cs[i] for i in range(len(cs) - 1)]
        gaps = gaps + [gaps[-1]] if gaps else []   # pad to len(writes) (per-write delay)
        fcap = 0 if f < SWEEP_INTRO else SWEEP_CAP  # intro = full sweep; body = capped
        segs = _cap_segments(rle_gaps(gaps), fcap)
        # cycle-budget cap: keep whole segments while sum(run*gap_cyc) <= NCO_BUDGET
        capped, used = [], 0
        for gap, run in segs:
            ldx = _sweep_ldx(gap)
            gap_cyc = LEAD_FIXED_SWEEP + 5 * ldx
            if used + run * gap_cyc > NCO_BUDGET:
                room = (NCO_BUDGET - used) // gap_cyc
                if not capped:
                    room = max(1, room)        # ALWAYS bound the 1st seg (cap1 frames have
                                               # only one -> else it blows the cycle window)
                if room:
                    capped.append((ldx, min(room, run, 255)))
                break
            capped.append((ldx, min(run, 255)))
            used += run * gap_cyc
        recs.append((step & 0x0F, tuple(capped)))
        nseg_tot += len(capped)
    # serialize: RLE (repeat-prefixed, holds consecutive dups) or plain (1 record/frame)
    out = bytearray()
    if SWEEP_RLE:
        i = 0
        while i < nframes:
            j = i
            while j + 1 < nframes and recs[j + 1] == recs[i] and j - i < 254:
                j += 1
            incr, caps = recs[i]
            out += bytes((j - i + 1, incr, len(caps)))   # [rep][incr][nsegs]
            for ldx, run in caps:
                out += bytes((ldx, run))
            i = j + 1
        out += bytes((0, 0, 0))            # rep=0 terminator
    else:
        for incr, caps in recs:
            out += bytes((incr, len(caps)))
            for ldx, run in caps:
                out += bytes((ldx, run))
        out += bytes((0, 0))
    mode = f"RLE cap{SWEEP_CAP or '-'}" if SWEEP_RLE else "plain"
    print(f"  sweep lead ({mode}): {nframes} frames, {nseg_tot} gap segments, {len(out)} B")
    return bytes(out)


def emit_nco(name, tune, writes, pitch):
    nframes, table, kinds = lead_params(writes, pitch)
    voiced = sum(1 for _, _, c in table if c)
    print(f"  NCO melody: {nframes} frames, {voiced} voiced (tight-NCO, fast gap)")
    blob = b"".join(bytes((i, l, c)) for i, l, c in table) + bytes((0, 1, 0))
    open(os.path.join(ROOT, "out", "digi_blob.bin"), "wb").write(blob)
    inc = os.path.join(ROOT, "drivers_src", "galway", "digi_addrs.inc")
    with open(inc, "w") as f:
        f.write(f"; auto-generated tight-NCO lead for {name} (tune {tune}); data in "
                f"out/digi_blob.bin @ ${BANK_ADDR:04x} (3 B/frame: incr,ldx,count)\n")
        f.write(f"DIGI_NCO_FRAMES = {nframes}\n")
        f.write(f"DIGI_BLOB_ADDR = ${BANK_ADDR:04x}\n")
        f.write(f"digi_nco_tab   = ${BANK_ADDR:04x}\n")
    print(f"  wrote {inc} + out/digi_blob.bin ({len(blob)} B @ ${BANK_ADDR:04x})")


def emit_hybrid(name, tune, writes, pitch):
    """HYBRID digi: EXACT-replay sawtooth lead (the 'S' frames, byte-for-byte the
    original's $D418 nibbles) + PCM drum samples (the 'D' frames), in one blob. The
    driver replays the lead nibbles each frame UNLESS a drum sample is active, in
    which case it streams the drum (it ducks the lead, as the single channel does)."""
    fr = {}
    for c, n in writes:
        fr.setdefault(c // CYC_PER_FRAME, []).append((c, n))
    nframes, table, kinds = lead_params(writes, pitch)

    # Segment maximal runs of consecutive 'drum' frames into one PCM sample each;
    # onset = the run's first frame. fuzzy-dedupe into a small bank (kick/snare/...).
    runs = []
    f = 0
    while f < nframes:
        if kinds[f] == 'drum':
            start = f
            nib = []
            while f < nframes and kinds[f] == 'drum':
                nib += [n for _, n in fr.get(f, [])]
                f += 1
            if len(nib) >= 24:
                runs.append((start, nib))
        else:
            f += 1
    onsets = [r[0] for r in runs]
    pcms = [r[1] for r in runs]
    bank, sids = fuzzy_dedupe(pcms)

    # Drum PLAYBACK RATE: the driver must stream the PCM at the SAME $D418 write
    # spacing the original used, else the drum is pitch-shifted (Arkanoid's drums
    # run at a ~60-cycle gap = ~16.4 kHz; the old fixed ~101-cycle gap played them
    # 0.59x too slow/low). Measure the median within-frame gap + writes/frame over
    # the drum frames and emit them as driver constants.
    import numpy as np
    dgaps, dwpf = [], []
    for f in range(nframes):
        if kinds[f] != 'drum':
            continue
        items = fr.get(f, [])
        if len(items) < 8:
            continue
        g = np.diff([c for c, _ in items])
        dgaps += g[g < 1000].tolist()
        dwpf.append(len(items))
    gap_cyc = float(np.median(dgaps)) if dgaps else 101.0
    # Measured calibration: hbpcm gap = 52 + 5*ldx cycles (per-write fixed overhead
    # ~52 cyc; delay loop `ldx #N: dex/bne` = 5N-1). Solve ldx for the source gap.
    drum_ldx = max(1, min(255, int(round((gap_cyc - 52) / 5.0))))
    drum_wpf = max(32, min(190, int(np.median(dwpf)))) if dwpf else 128
    # --- lead bytes FIRST, so the drum bank auto-fits whatever bank space remains:
    #     truncating a drum mid-decay leaves a non-zero tail -> audible CLICK, so keep
    #     each sample as long as the budget allows (ideally its full natural decay). ---
    if os.environ.get("GALWAY_DIGI_SWEEP"):
        nco_bytes = sweep_records(writes)                   # gap-sweep lead (incl. terminator)
    else:
        nco_bytes = b"".join(bytes((i, l, c)) for i, l, c in table) + bytes((0, 1, 0))
    n = len(bank)
    # triggers ([frame-delta, sample-id] pairs); length independent of sample size
    trig = bytearray()
    prev = 0
    for fr_on, sid in sorted(zip(onsets, sids)):
        delta = fr_on - prev
        while delta > 254:
            trig += bytes((0xFE, 0xFE))
            delta -= 254
        trig += bytes((delta & 0xFF, sid & 0xFF))
        prev = fr_on
    trig += bytes((0x00, 0xFF))
    # auto-fit: max nibbles/sample that still fits the bank after lead + tables + triggers
    # (GALWAY_DRUM_MAX is an UPPER cap, default large -> samples kept full unless squeezed).
    BANK_LIMIT = 0xD000 - BANK_ADDR    # $8000-$CFFF; past $D000 is I/O (would corrupt SID)
    drum_budget = BANK_LIMIT - len(nco_bytes) - 4 * n - len(trig) - 64   # 64B safety
    fit = max(64, drum_budget // max(1, n))
    MAX_DRUM_NIB = min(int(os.environ.get("GALWAY_DRUM_MAX", "8192")), fit)
    def representative(s):
        members = sorted((pcms[i] for i in range(len(pcms)) if sids[i] == s), key=len)
        rep = members[len(members) // 2]
        if len(rep) > MAX_DRUM_NIB:        # truncated mid-ring -> abrupt stop = a CLICK.
            rep = list(rep[:MAX_DRUM_NIB])  # linearly fade the tail to silence so it
            F = min(80, len(rep) // 4)      # releases cleanly (full-length samples: as-is).
            for k in range(F):
                idx = len(rep) - F + k
                rep[idx] = rep[idx] * (F - 1 - k) // (F - 1) if F > 1 else 0
            return bytes(rep)
        return bytes(rep)
    reps = [representative(s) for s in range(len(bank))]
    voiced = sum(1 for _, _, c in table if c)
    print(f"  lead: {nframes} frames, {voiced} voiced; drums: {len(runs)} hits -> {n} "
          f"samples, <={MAX_DRUM_NIB} nib/sample ({sum(len(r) for r in reps)} nibbles)")

    # Blob layout @ BANK_ADDR: [lead][bank flat][off_lo][off_hi][len_lo][len_hi][triggers]
    a_nco = BANK_ADDR
    flat = bytearray(b for r in reps for b in r)
    offs, cur = [], 0
    for r in reps:
        offs.append(cur)
        cur += len(r)
    a_bank = a_nco + len(nco_bytes)
    off_lo = bytes((a_bank + o) & 0xFF for o in offs)
    off_hi = bytes(((a_bank + o) >> 8) & 0xFF for o in offs)
    len_lo = bytes(len(r) & 0xFF for r in reps)
    len_hi = bytes((len(r) >> 8) & 0xFF for r in reps)

    blob = nco_bytes + bytes(flat) + off_lo + off_hi + len_lo + len_hi + bytes(trig)
    if len(blob) > BANK_LIMIT:
        print(f"  !! WARNING: digi blob {len(blob)} B EXCEEDS the {BANK_LIMIT} B bank "
              f"(${BANK_ADDR:04x}-$cfff) by {len(blob)-BANK_LIMIT} B -> would overrun "
              f"$D000 I/O. Reduce GALWAY_SWEEP_CAP / GALWAY_DRUM_MAX or shorten the tune.")
    a_offlo = a_bank + len(flat)
    a_offhi = a_offlo + n
    a_lenlo = a_offhi + n
    a_lenhi = a_lenlo + n
    a_trig = a_lenhi + n
    open(os.path.join(ROOT, "out", "digi_blob.bin"), "wb").write(blob)
    inc = os.path.join(ROOT, "drivers_src", "galway", "digi_addrs.inc")
    with open(inc, "w") as f:
        f.write(f"; auto-generated HYBRID digi (tight-NCO lead + PCM drums) for {name} "
                f"(tune {tune}); data in out/digi_blob.bin @ ${BANK_ADDR:04x}\n")
        f.write(f"DIGI_NCO_FRAMES = {nframes}\n")
        f.write(f"DIGI_NSAMP    = {n}\n")
        f.write(f"DRUM_GAP_LDX  = {drum_ldx}    ; drum $D418 gap ~{gap_cyc:.0f} cyc "
                f"(~{985248/gap_cyc:.0f} Hz)\n")
        f.write(f"DRUM_WPF      = {drum_wpf}    ; drum writes per frame (source rate)\n")
        f.write(f"DIGI_BLOB_ADDR = ${a_nco:04x}\n")
        f.write(f"DIGI_BLOB_LEN  = {len(blob)}\n")
        f.write(f"digi_nco_tab  = ${a_nco:04x}\n")
        f.write(f"digi_bank     = ${a_bank:04x}\n")
        f.write(f"digi_off_lo   = ${a_offlo:04x}\n")
        f.write(f"digi_off_hi   = ${a_offhi:04x}\n")
        f.write(f"digi_len_lo   = ${a_lenlo:04x}\n")
        f.write(f"digi_len_hi   = ${a_lenhi:04x}\n")
        f.write(f"digi_triggers = ${a_trig:04x}\n")
    print(f"  wrote {inc} + out/digi_blob.bin ({len(blob)} B @ "
          f"${a_nco:04x}-${a_nco+len(blob):04x})")


def main():
    name = sys.argv[1]
    seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    tune = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    sidpath = os.path.join(ROOT, "SID", "Galway_Martin", name + ".sid")

    print(f"VICE dump of {name} ({seconds}s, tune {tune})...")
    writes = dump_d418(sidpath, seconds, tune)
    if os.environ.get("GALWAY_DIGI_HYBRID") or os.environ.get("GALWAY_DIGI_NCO"):
        nframes = (max(c // CYC_PER_FRAME for c, _ in writes) + 1) if writes else 0
        print(f"  measuring original perceived pitch per frame ({nframes} frames)...")
        pitch = render_pitch_track(sidpath, tune, seconds, nframes, writes)
    if os.environ.get("GALWAY_DIGI_HYBRID"):
        emit_hybrid(name, tune, writes, pitch)
        return
    if os.environ.get("GALWAY_DIGI_NCO"):
        emit_nco(name, tune, writes, pitch)
        return
    bursts = segment(writes)
    pcms = [[n for _, n in b] for b in bursts]
    onsets = [b[0][0] // CYC_PER_FRAME for b in bursts]   # onset video frame
    bank, sids = fuzzy_dedupe(pcms)

    # representative bank: the LONGEST member of each cluster (most complete hit)
    reps = [max((pcms[i] for i in range(len(pcms)) if sids[i] == s), key=len)
            for s in range(len(bank))]
    total = sum(len(r) for r in reps)
    print(f"  {len(bursts)} hits -> {len(reps)} unique samples, "
          f"{total} nibbles ({total/1024:.1f} KB @ 1 nibble/byte)")
    print(f"  trigger frames: {len(onsets)} onsets over {max(onsets)} frames")

    # Build a single BINARY blob (the build injects it high, separate from the
    # driver PRG): [bank nibbles][off_lo][off_hi][len_lo][len_hi][triggers].
    # The driver just gets the addresses (digi_addrs.inc, equates only) — keeping
    # the 3.7 KB bank out of the compact driver PRG / edit-area layout.
    n = len(reps)
    flat = bytearray(b for r in reps for b in r)
    offs, cur = [], 0
    for r in reps:
        offs.append(cur)
        cur += len(r)
    off_lo = bytes((BANK_ADDR + o) & 0xFF for o in offs)
    off_hi = bytes(((BANK_ADDR + o) >> 8) & 0xFF for o in offs)
    len_lo = bytes(len(r) & 0xFF for r in reps)
    len_hi = bytes((len(r) >> 8) & 0xFF for r in reps)
    trig = bytearray()
    prev = 0
    for fr, sid in sorted(zip(onsets, sids)):
        delta = fr - prev
        while delta > 254:
            trig += bytes((0xFE, 0xFE))     # wait 254, no-op
            delta -= 254
        trig += bytes((delta & 0xFF, sid & 0xFF))
        prev = fr
    trig += bytes((0x00, 0xFF))             # end marker

    blob = bytes(flat) + off_lo + off_hi + len_lo + len_hi + bytes(trig)
    a_bank = BANK_ADDR
    a_offlo = a_bank + len(flat)
    a_offhi = a_offlo + n
    a_lenlo = a_offhi + n
    a_lenhi = a_lenlo + n
    a_trig = a_lenhi + n
    open(os.path.join(ROOT, "out", "digi_blob.bin"), "wb").write(blob)
    inc = os.path.join(ROOT, "drivers_src", "galway", "digi_addrs.inc")
    with open(inc, "w") as f:
        f.write(f"; auto-generated digi addresses for {name} (tune {tune}); "
                f"data in out/digi_blob.bin @ ${BANK_ADDR:04x}\n")
        f.write(f"DIGI_NSAMP    = {n}\n")
        f.write(f"DIGI_BLOB_ADDR = ${a_bank:04x}\n")
        f.write(f"DIGI_BLOB_LEN  = {len(blob)}\n")
        f.write(f"digi_bank     = ${a_bank:04x}\n")
        f.write(f"digi_off_lo   = ${a_offlo:04x}\n")
        f.write(f"digi_off_hi   = ${a_offhi:04x}\n")
        f.write(f"digi_len_lo   = ${a_lenlo:04x}\n")
        f.write(f"digi_len_hi   = ${a_lenhi:04x}\n")
        f.write(f"digi_triggers = ${a_trig:04x}\n")
    print(f"  wrote {inc} + out/digi_blob.bin ({len(blob)} B @ ${BANK_ADDR:04x}-${BANK_ADDR+len(blob):04x})")


if __name__ == "__main__":
    main()
