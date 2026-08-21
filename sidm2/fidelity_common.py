"""Shared plumbing for the fidelity/validation tools (roadmap A3).

Before this module, six validators (mon_fidelity, mon_sf2_validate, mon_validate,
romuzak_validate, romuzak_native_validate, fc_validate, plus sf2ii_vs_real and
build_mon_native_song.filter_trace) each carried private copies of the same
helpers: PSID probe wrapping, freq->semitone conversion, siddump table parsing,
and the zig64 fill-forward serializer. The copies had drifted — most notably the
semitone reference frequency (0x1168 vs 0x1167 vs an inline log2), a latent
inconsistency this module fixes by canonicalizing on one reference.

Everything here is measurement plumbing only: no player knowledge, no policy.
"""
import hashlib
import json
import math
import os
import re
import subprocess
from dataclasses import dataclass, field

# Canonical semitone reference: the PAL SID freq value for C-4 (261.63 Hz at
# phi2 = 985248 Hz -> 261.63 * 2^24 / 985248 ~= 4455 = $1167). "+48" maps C-4 to
# note index 48, matching the 96-entry note-table space. The pre-consolidation
# copies used $1168 (mon) / $1167 (romuzak) — a ~0.004-semitone difference that
# never crosses a rounding boundary for 16-bit SID freq pairs, verified by
# baseline-diffing every validator's output during the extraction.
SEMI_REF = 0x1167


def score_pct(ok, tot):
    """ok/tot as a percentage, or **None when tot == 0** (no evidence).

    NEVER returns a perfect score for an empty comparison. `0/0` is "no test
    ran", not "100% agreement" — a distinction this project has now been bitten
    by three separate times:

    - v3.21.0: `zig64_audio_gate.verify_sf2_audio` compared two traces for
      equality; when the tracer could not drive a file both came back empty,
      `len(0) == len(0)`, and the gate certified 64 zero bytes as byte-identical
      to `SID/Laxity/Broken_Ass.sid`.
    - The `secs <= 0` vacuous-100 documented in `docs/players/HUBBARD.md` — fixed
      there, but every sibling scorer kept its own `if tot else 100.0` copy.
    - 2026-07-16 fidelity audit: those copies were still live in 10 files, and in
      two of them (`build_dmc_native_song`, `build_soundmonitor_native_song`) the
      fabricated 100.0 fed a real A/B build decision — a voice with no data
      silently voted, because 100.0 vs 100.0 compares equal.

    Callers MUST handle None explicitly. That is the point: "I measured nothing"
    should be impossible to confuse with "it matched perfectly", and impossible
    to accidentally compare. Use `fmt_pct` to render it.
    """
    return 100.0 * ok / tot if tot else None


def exercised(a_vals, b_vals):
    """Can this register distinguish the two sides at all over the window?

    The companion to `score_pct`. `score_pct` stops an EMPTY comparison from
    reporting 100%; this stops a comparison that is full of frames but empty of
    information from reporting it either.

    False when both series hold a single value for the whole window and it is
    the SAME value. That is the shape of the vacuous pass: `siddump` force-
    displays every register on its first row whether or not the playroutine
    wrote it, so a tune that never touches $D405/$D406 or the filter still hands
    back a full-length, entirely non-None series of zeroes on BOTH sides.
    Comparing those frame by frame gives `tot == n`, `ok == n`, and a confident
    100.0 that means only "neither side did anything". `docs/players/HUBBARD.md`
    had to retract a published "filter 100%" for exactly this — Hubbard's player
    never writes a cutoff, so the column had been comparing 0 against 0.

    True when either series MOVES, and also when both are constant at DIFFERENT
    constants: a permanently wrong master volume or sustain level is a real,
    total disagreement that must score ~0%, not disappear into n/a.

    Deliberately conservative in the remaining case — constant and equal scores
    n/a even where the value was genuinely written by both sides — because a
    register neither side varies cannot be evidence FOR anything, while a change
    that makes it vary, or shifts the constant, flips this to True and is caught
    (an n/a on one side and a number on the other is a regression by
    `Dimension.worse`).
    """
    a = [x for x in a_vals if x is not None]
    b = [x for x in b_vals if x is not None]
    if not a or not b:
        return False
    return len(set(a)) > 1 or len(set(b)) > 1 or a[0] != b[0]


# A per-voice percentage over fewer than this many compared frames is not a
# fidelity claim. 250 frames is 5 seconds of PAL playback -- chosen as the point
# below which the corpus stops containing songs and starts containing jingles,
# not from a significance test, and stated here rather than buried in a caller
# so it can be argued with. Matt Gray's Stage B corpus is the worked example:
# 30 of its 36 tunes compare 1,500-6,300 frames per voice, and the other 6 are
# 1-3 second stingers compared over 46-136 -- one of which reported a confident
# 100.0/100.0/100.0 on n=46.
MIN_INFORMATIVE_FRAMES = 250


# A CORPUS SWEEP THAT CANNOT LAUNCH A PROCESS HAS STOPPED MEASURING.
# The first full-corpus SDI sweep returned these codes for every file from #275
# of 441 onward -- about 5 h in, the long-lived parent could no longer spawn a
# child. Nothing noticed: all 167 were counted in the same `errored` column as
# real per-file failures, and the published per-variant medians silently became
# an alphabetical A-O sample of a corpus the headline claimed was complete.
# Three of those files build cleanly on a fresh invocation.
#
# This lives here rather than in one sweep because `soundmonitor_sweep.py` and
# `blackbird_sweep.py` have the identical shape -- `subprocess.run`, then "the
# line I wanted is missing, record an error" -- so a launch failure is
# indistinguishable from a genuine build failure in all three.
LAUNCH_FAILURE_RCS = {
    3221225794: "STATUS_DLL_INIT_FAILED (0xC0000142)",
    3221225495: "STATUS_NO_MEMORY (0xC0000017)",
    3221225781: "STATUS_DLL_NOT_FOUND (0xC0000135)",
}


def launch_failure(rc, output=""):
    """Name the infrastructure failure behind `rc`, or None if this is a result.

    `errored` means *we asked and the tool could not*. `unmeasured` means *we
    never asked*. Pooling the second into the first turns a host collapse into a
    claim about the corpus, so the two must not share a column.

    A child that produced OUTPUT is never classified here however it exited: it
    ran, it had an opinion about the file, and suppressing that would hide a
    genuine failure. Only a silent child with one of these codes qualifies.
    """
    if output and output.strip():
        return None
    return LAUNCH_FAILURE_RCS.get(rc)


def underpowered(tot, min_n=MIN_INFORMATIVE_FRAMES):
    """True when a percentage over `tot` comparisons is too small to quote.

    The third guard, and the one this harness was missing. `score_pct` asks
    "were there ANY frames?" and `exercised` asks "did those frames carry
    INFORMATION?" -- neither asks "were there ENOUGH?". A voice compared over
    46 frames scores 100.0% exactly as confidently as one compared over 6,000,
    and prints identically, so a corpus table silently averages a 1-second
    stinger against a 2-minute song.

    This does NOT reject the measurement -- a short tune is real music and its
    score is real. It marks the number as unquotable on its own, which is the
    same distinction `insufficient-data` draws from `no-trace` in
    `sidm2/instrument_map.py`: absence of evidence, recorded as such, rather
    than silently promoted to evidence of absence or of success.
    """
    return tot is not None and tot < min_n


def fmt_pct(p, width=5, prec=1, n=None):
    """Render a `score_pct` result. None -> 'n/a', never a number.

    `n` (optional) is the comparison count behind `p`. When it is below
    `MIN_INFORMATIVE_FRAMES` the number is suffixed with `!` -- see
    `underpowered`. Callers that do not pass `n` are unchanged, so the ~40
    existing call sites and the scripts that parse their output keep their
    exact format.
    """
    if p is None:
        return "n/a".rjust(width)
    out = f"{p:{width}.{prec}f}"
    return out + "!" if underpowered(n) else out


def series_shape(vals):
    """(number of change events, total travel) over a value series.

    `None`s are skipped rather than treated as a value: siddump only prints a
    register on the frames the playroutine wrote it, so a held value reads as
    one write followed by `None`s, and counting those as changes would score a
    static register as constant motion.
    """
    prev = None
    moves = travel = 0
    for v in vals:
        if v is None:
            continue
        if prev is not None and v != prev:
            moves += 1
            travel += abs(v - prev)
        prev = v
    return moves, travel


def shape_agreement(a_vals, b_vals):
    """Phase-INVARIANT companion to per-frame equality: did the register move
    the same NUMBER of times, and the same total DISTANCE?

    Per-frame equality answers "was the value the same on frame i". For a
    swept register (pulse width, filter cutoff) that question is dominated by
    phase: a sweep that is correct in rate, depth and direction but starts a
    few frames late disagrees on nearly every frame and scores near zero, which
    reads as a broken engine when it is a timing offset. The ±1-frame skew
    tolerance the per-voice scorers carry does not reach a multi-frame offset.
    Both numbers here are computed from consecutive DIFFERENCES, so a constant
    lag shifts them by at most the frames that fall off the window ends.

    NECESSARY, NOT SUFFICIENT — and never quote it alone. Two sweeps that share
    a movement count and a travel total need not share a shape (up-then-down
    versus down-then-up travel identically), so this can only ever say "the
    motion is the right size", never "the motion matched". Read it next to the
    strict per-frame column: strict low + shape high = phase/alignment; both
    low = the engine really is producing different motion.

    Returns `(moves_pct, travel_pct, (a_moves, b_moves), (a_travel, b_travel))`,
    each percentage the smaller total over the larger via `score_pct` — so a
    register NEITHER side moves gives 0/0 -> **None**, not 100.0 (see
    `score_pct`; a flat pulse on both sides is no evidence the pulse engine
    works), and one side moving while the other sits still gives 0.0%.
    Two series constant at DIFFERENT values also score n/a here: this metric
    measures motion and there is none: that disagreement is the strict
    column's to report, and `exercised` keeps it visible there.
    """
    am, at = series_shape(a_vals)
    bm, bt = series_shape(b_vals)
    return (score_pct(min(am, bm), max(am, bm)),
            score_pct(min(at, bt), max(at, bt)),
            (am, bm), (at, bt))


def freq_to_semi(freq):
    """16-bit SID freq value -> nearest note index (0..95), or -1 for silence.

    None / 0 / sub-audio (<8, below the note table) all map to -1 so a silent
    voice compares equal to a silent voice.
    """
    if not freq or freq < 8:
        return -1
    return max(0, min(95, round(12 * math.log2(freq / SEMI_REF) + 48)))


def psid_wrap(data, load, init, play, songs=1, start_song=1):
    """Wrap a raw C64 binary as a minimal PSID so trace tools can drive it."""
    from scripts.sf2_to_sid import PSIDHeader
    h = PSIDHeader(load_address=load, init_address=init, play_address=play)
    h.songs = songs
    h.start_song = start_song
    return h.to_bytes() + data


# ---------------------------------------------------------------------------
# siddump (pyscript/siddump_complete.py) — run + table parsing
# ---------------------------------------------------------------------------

def run_siddump(path, args):
    """Run the Python siddump on `path` with extra `args`; returns its stdout.

    RAISES on a non-zero exit instead of returning ''. A failed siddump used to
    come back as an empty string, and an empty trace is NOT inert: the native
    builders derive their per-note (FM, pulse) bundles from it, so `fits()` sees
    counts under every cap and packs the whole song into ONE part — emitting a
    silently wrong artifact with rc=0 that then scores clean. That is exactly
    the 1-part `Predictable_main` an 88-file `-j8` corpus build produced and no
    serial build ever reproduced. The trigger is spawn pressure, which is real
    here: a `-j16` build running beside other work caused 3 process-launch
    failures. Same discipline the zig64 tracer already has ("fails honestly …
    check the exit code, don't just parse stderr") — this path simply never had
    it, while four SCORERS guard emptiness and none of the three builders did.

    `rc == 0` with empty stdout is deliberately left alone: that is a tune that
    writes nothing, which `passband_check` and `validate_filter_accuracy` read
    as *unexercised* rather than broken, and conflating the two would trade one
    silent wrong answer for another.

    A hung siddump is the same class of failure as a bad exit code — silently
    blocking a corpus build forever — so this also enforces a `timeout=`,
    scaled to the `-tN` (trace seconds) requested rather than a single fixed
    constant, because trace wall-time scales with `-t` and there is no reason
    to assume the corpus has already produced its longest song. `_siddump_timeout`
    documents the measurements the budget is based on.
    """
    timeout = _siddump_timeout(args)
    try:
        r = subprocess.run(['py', '-3', 'pyscript/siddump_complete.py', path] + list(args),
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"siddump timed out (>{timeout:.0f}s) on {path} with {list(args)} — "
            f"a hung siddump would otherwise block a corpus build forever")
    if r.returncode != 0:
        raise RuntimeError(
            f"siddump failed (rc={r.returncode}) on {path} with {list(args)}: "
            f"{(r.stderr or r.stdout).strip()[:400] or '<no output>'}")
    return r.stdout


# Budget for one run_siddump() call. Measured (clean single run, no other
# process contention) on the -tN each native builder actually uses for a full
# trace (`secs = span // 50 + 4`, i.e. the whole song plus a 4s margin):
#
#   SID/JohannesBjerregaard/Balloon.sid                 -t404 -> 19.3s wall
#     (0.0478 s wall / s trace) -- documented project-wide as the long pole:
#     "Balloon: 77 parts merged into ONE 400s SF2 ... the best-evidenced
#     number in the project" (docs/players/DMC.md)
#   SID/Gallefoss_Glenn/Ghosts_n_Goblins_Arcade.sid     -t300 -> 13.9s wall
#     (0.0464 s wall / s trace)
#   SID/Shogoon/Music_Box.sid                            -t300 ->  4.1s wall
#     (0.0137 s wall / s trace)
#
# The slowest observed rate is ~0.048 s wall per s of trace requested. The
# per-second budget below (0.5) is ~10x that, and the fixed floor covers
# `py -3` interpreter startup plus the spawn contention this module's
# docstring already documents (3 real process-launch failures under a -j16
# build) — a hang caused by spawn pressure, not by trace length, still needs
# room to clear before the timeout fires. This scales with the `-t` actually
# requested rather than pinning to Balloon's 404s, because a future corpus
# song longer than Balloon would otherwise silently convert a legitimate
# trace into a hard failure — exactly the class of silent wrongness the rc
# check above was added to remove, arriving from the other direction.
_SIDDUMP_TIMEOUT_FLOOR_S = 30.0
_SIDDUMP_TIMEOUT_PER_TRACE_SECOND_S = 0.5


def _siddump_timeout(args):
    """Timeout (seconds) for a run_siddump() call, from the `-tN` in `args`.

    Falls back to siddump_complete.py's own default trace length (60s, from
    its argparse `-t/--seconds` default) when no `-tN` token is present.
    """
    requested = 60
    for a in args:
        m = re.match(r'^-t(\d+)$', str(a))
        if m:
            requested = int(m.group(1))
            break
    return _SIDDUMP_TIMEOUT_FLOOR_S + requested * _SIDDUMP_TIMEOUT_PER_TRACE_SECOND_S


def iter_siddump_rows(txt):
    """Yield (frame_or_None, cells) for each data row of a siddump table.

    cells = the '|'-split, stripped columns (cells[1]=frame, cells[2..4]=voices,
    cells[5]=filter). frame is None when the column isn't an int (callers that
    key on frames skip those rows; callers that count rows keep them).
    """
    for ln in txt.splitlines():
        if not ln.startswith('|') or 'Frame' in ln:
            continue
        c = [x.strip() for x in ln.split('|')]
        if len(c) < 6:
            continue
        try:
            fr = int(c[1])
        except ValueError:
            fr = None
        yield fr, c


# The classic siddump filter column renders $D418's mode bits as a NAME rather
# than a number: `pyscript/siddump_complete.py` prints FILTER_NAMES[($D418>>4)&7]
# followed by the master-volume nibble. Reversing the name is the only way to
# recover the byte from the default table without switching siddump into `-b`
# mode (which reformats the voice columns too, so it cannot be mixed with the
# freq/wf/pul parse above). Kept in sync with the producer by
# test_fidelity_common.test_filter_mode_names_match_siddump.
#
# NOTE the resulting byte carries $D418 bits 0-6 only: the classic column has no
# room for bit 7 (voice-3-off), which `-b` mode shows as the '3' of "LBH3". Every
# consumer of `volmode` is therefore blind to that one bit, and says so.
FILTER_MODE_NAMES = ("Off", "Low", "Bnd", "L+B", "Hi ", "L+H", "B+H", "LBH")


def siddump_frames_full(path, args):
    """siddump -> per-frame fill-forwarded voice + SPLIT global filter state.

    frames[i] = ({0,1,2: {'freq','wf','pul','adsr'}},
                 {'cutoff': int|None, 'filtctl': int|None, 'volmode': int|None})

    The superset of `siddump_per_frame`, which is now a projection of this so
    the two can never drift into disagreeing about the same table. Two fields
    exist only here:

      'adsr'    the $D405/$D406 pair as one 16-bit value, the register
                `MON_WAVE_CANON`-style wave-program re-compression can move
                without touching freq/wf/pulse at all.
      'filtctl' / 'volmode'   $D417 and $D418 separately, where
                `siddump_per_frame` collapses the whole filter column to cutoff.

    All values are None until siddump first shows the register. **That is not
    the same as "until the tune writes it"**: siddump force-displays every
    register on frame 0 whatever the playroutine did, so frame 0 hands back the
    pre-init bus state (Hawkeye reads $D418 = $FF there, i.e. bit 7 set, before
    its own init writes $1F). Callers scoring these registers must decide what
    counts as evidence rather than trusting non-None — see the `_exercised`
    guard in `bin/mon_part_fidelity.py`, and `score_pct` for why 0 == 0 over a
    thousand frames is not a pass.
    """
    txt = run_siddump(path, args)
    st = [{'freq': None, 'wf': None, 'pul': None, 'adsr': None} for _ in range(3)]
    ft = {'cutoff': None, 'filtctl': None, 'volmode': None}
    mode_idx, vol = [None], [None]
    frames = []

    def cv(x):
        return None if (not x or '.' in x) else int(x, 16)

    for fr, c in iter_siddump_rows(txt):
        if fr is None:
            continue
        for vi in range(3):
            m = re.match(r'^([0-9A-F\.]{4})\s+\S+\s+\S+\s+([0-9A-F\.]{2})\s+'
                         r'([0-9A-F\.]{4})\s+([0-9A-F\.]{3})', c[2 + vi])
            if m:
                for k, val in zip(('freq', 'wf', 'adsr', 'pul'), m.groups()):
                    cvv = cv(val)
                    if cvv is not None:
                        st[vi][k] = cvv
        # cutoff keeps its own LENIENT match, byte-for-byte the one
        # siddump_per_frame used before this function existed: a filter cell
        # that does not parse in full must not change what the older, narrower
        # reader saw.
        fm = re.match(r'^([0-9A-F\.]{4})', c[5])
        if fm:
            cvv = cv(fm.group(1))
            if cvv is not None:
                ft['cutoff'] = cvv
        # `FCut RC Typ V` at fixed widths; Typ is 3 chars and may itself END in a
        # space ("Hi "), so it is matched by width, not by \S+.
        gm = re.match(r'^[0-9A-F\.]{4} ([0-9A-F\.]{2}) (.{3}) ([0-9A-F\.])', c[5])
        if gm:
            cvv = cv(gm.group(1))
            if cvv is not None:
                ft['filtctl'] = cvv
            if gm.group(2) in FILTER_MODE_NAMES:
                mode_idx[0] = FILTER_MODE_NAMES.index(gm.group(2))
            cvv = cv(gm.group(3))
            if cvv is not None:
                vol[0] = cvv
            if mode_idx[0] is not None and vol[0] is not None:
                ft['volmode'] = (mode_idx[0] << 4) | vol[0]
        frames.append(({vi: dict(st[vi]) for vi in range(3)}, dict(ft)))
    return frames


def siddump_per_frame(path, args):
    """siddump -> per-frame fill-forwarded voice + filter state.

    Returns frames[i] = ({0,1,2: {'freq','wf','pul'}}, fcut) with ints
    (None until a register is first written). This is the per-frame state the
    MoN fidelity metrics compare on.

    A projection of `siddump_frames_full`; the extra fields that function
    carries ($D405/$D406, $D417, $D418) are dropped here so the ~40 callers of
    this shape keep the exact dict they were written against.
    """
    return [({vi: {k: v[vi][k] for k in ('freq', 'wf', 'pul')} for vi in range(3)},
             f['cutoff']) for v, f in siddump_frames_full(path, args)]


def siddump_note_onsets(path, args, require_wf=False):
    """siddump -> {0,1,2: [(frame, note_name), ...]} unbracketed note onsets.

    require_wf=True additionally demands the waveform column be present on the
    onset row (a fresh gated onset), matching the MoN validators; the
    ROMUZAK/FC validators accept any unbracketed note.
    """
    txt = run_siddump(path, args)
    pat = (re.compile(r'^([0-9A-F]{4})\s+([A-G][-#]\d)\s+([0-9A-F]{2})\b') if require_wf
           else re.compile(r'^([0-9A-F]{4})\s+([A-G][-#]\d)\b'))
    V = {0: [], 1: [], 2: []}
    for fr, c in iter_siddump_rows(txt):
        if fr is None:
            continue
        for vi, cell in enumerate(c[2:5]):
            m = pat.match(cell)
            if m and m.group(1) != '0000':
                V[vi].append((fr, m.group(2)))
    return V


def siddump_freq_track(path, args, voice):
    """siddump -> {frame: raw_16bit_freq} (fill-forward) for one voice (0,1,2).

    Unlike siddump_note_onsets (which only yields rows siddump considers a fresh
    onset), this tracks the register continuously frame-by-frame -- needed to see
    a frequency that SETTLES a frame or two after the onset row (e.g. a one-frame
    attack-transient value before the target pitch locks in). A '....' cell means
    "unchanged this frame", so the last written value carries forward."""
    txt = run_siddump(path, args)
    freq_re = re.compile(r'^([0-9A-F.]{4})')
    out = {}
    last = 0
    for fr, c in iter_siddump_rows(txt):
        if fr is None:
            continue
        mm = freq_re.match(c[2 + voice])
        if mm and '.' not in mm.group(1):
            last = int(mm.group(1), 16)
        out[fr] = last
    return out


def siddump_filter_trace(path, args):
    """siddump -> per-row global filter state (fill-forward): [(cutoff11, ctrl)]
    where cutoff11 = ($D415&7)|($D416<<3) and ctrl = $D417 (res+routing).
    One entry per siddump data row (frame-parse failures still emit a row, so
    the list length matches the dump length)."""
    txt = run_siddump(path, args)
    cut, ctrl, out = 0, 0xF1, []
    for fr, c in iter_siddump_rows(txt):
        mm = re.match(r'^([0-9A-F\.]{4})\s+([0-9A-F\.]{2})', c[5])
        if mm:
            if '.' not in mm.group(1):
                cut = int(mm.group(1), 16)
            if '.' not in mm.group(2):
                ctrl = int(mm.group(2), 16)
        out.append((cut, ctrl))
    return out


# ---------------------------------------------------------------------------
# zig64 cycle-accurate trace — fill-forward serialization
# ---------------------------------------------------------------------------

def fill_forward(writes, n, initial=0):
    """{frame: value} sparse write dict -> length-n per-frame list, carrying the
    last written value forward (frames before the first write get `initial`)."""
    out, cur = [], initial
    for i in range(n):
        if i in writes:
            cur = writes[i]
        out.append(cur)
    return out


def zig64_voices(reg, n):
    """zig64 trace dict {(voice, field): {frame: val}} -> per-voice per-frame state.

    Returns {v: {'freq' (16-bit), 'wf', 'pw' (12-bit), 'ad', 'sr'}} — the shape
    the deterministic native validators diff on.
    """
    def ser(vi, fld):
        return fill_forward(reg.get((vi, fld), {}), n)
    V = {}
    for v in range(3):
        fh, fl = ser(v, 'freq_hi'), ser(v, 'freq_lo')
        ph, pl = ser(v, 'pw_hi'), ser(v, 'pw_lo')
        V[v] = {
            'freq': [(fh[i] << 8) | fl[i] for i in range(n)],
            'wf': ser(v, 'control'),
            'pw': [((ph[i] & 0xF) << 8) | pl[i] for i in range(n)],
            'ad': ser(v, 'attack_decay'),
            'sr': ser(v, 'sustain_release'),
        }
    return V


def zig64_trace_voices(path, n, init, play, subtune):
    """Run the zig64 tracer on `path` and return zig64_voices(...) for n frames."""
    from sidm2 import galway_trace_extract as T
    return zig64_voices(T.run_trace(path, n, init, play, subtune), n)


# ---------------------------------------------------------------------------
# offset alignment
# ---------------------------------------------------------------------------

def best_gated_offset(offsets, count_fn):
    """Try each offset, keep the one with the most hits.

    count_fn(off) -> (hits, total, extra) where extra is any per-offset payload
    (e.g. a delta Counter). Returns (best_off, hits, total, extra); ties keep
    the earliest offset (matching the pre-consolidation loops).
    """
    bo, bh, bt, bx = 0, -1, 1, None
    for off in offsets:
        h, t, x = count_fn(off)
        if h > bh:
            bo, bh, bt, bx = off, h, t, x
    return bo, bh, bt, bx


# ---------------------------------------------------------------------------
# dimension registry — making blindness STRUCTURAL instead of remembered
# ---------------------------------------------------------------------------
#
# The standing rule in this repo is already written down in a dozen places:
# a metric that cannot see a change is not evidence the change did nothing.
# Up to now it was enforced entirely by whoever happened to remember it, and
# the record shows what that is worth. `docs/players/HUBBARD.md` had to retract
# "filter 100%" once someone noticed Hubbard never writes a cutoff at all, so
# the column was comparing 0 against 0 for every tune. `pyscript/
# mon_struct_sweep.py` was written to decide whether three structural build
# options are safe as defaults, and scores freq/wf/pulse only — it cannot see
# $D405/$D406 at all, so "no regression" from it has never meant "the envelope
# survived". Neither was a mistake anyone made twice; both were mistakes
# nobody's tooling could make impossible.
#
# So: a comparison declares which SID registers it is computed from, a run
# records which of those it actually exercised, and the harness derives the
# complement — the registers a change would have to land in to be invisible
# here. That turns blindness from something an author remembers into something
# a report prints.
#
# Adding a score column means adding a Dimension. `dimension()` RAISES on an
# unregistered key rather than defaulting, because a silently-defaulted
# dimension is a column that reads as measured and is not — the exact failure
# this registry exists to prevent.

SID_REGISTERS = (
    ("$D400/$D401", "voice frequency"),
    ("$D402/$D403", "pulse width"),
    ("$D404", "control: waveform select, gate, sync, ring, test"),
    ("$D405/$D406", "envelope: attack/decay, sustain/release"),
    ("$D415/$D416", "filter cutoff"),
    ("$D417", "filter resonance and per-voice routing"),
    ("$D418", "filter mode and master volume"),
)


@dataclass(frozen=True)
class Dimension:
    """One number a validator prints, and the SID registers it is derived from.

    `reads=()` is legal and meaningful: a build-shape number (part count, byte
    size, sequence-slot usage) reads no register, and saying so explicitly is
    what stops it from being counted as register coverage it does not provide.

    `kind` controls only how movement is ranked, never how the number is
    scored — scoring stays in the validator that owns it:
      fraction  0..100 percent (this repo's `score_pct` scale)
      ratio     a bare multiple
      count     an integer whose movement is relativised (2 -> 2823 and
                0.94 -> 0.95 are not the same size of finding)

    `higher_is_better=False` for the ones where less is the win (part count,
    residual frames), so a shared regression test does not need to know which
    is which per caller.
    """
    key: str
    reads: tuple
    of: str
    kind: str = "fraction"
    higher_is_better: bool = True

    def movement(self, a, b):
        """How far this dimension moved between two runs, for ranking only.

        A value that APPEARED or DISAPPEARED ranks `inf`, above any numeric
        move. Losing the ability to measure something is not a small delta —
        `score_pct` returns None for an empty comparison precisely so that
        case stays visible, and ranking it as a small number would bury it
        under the noise it was separated from.
        """
        if a is None or b is None:
            return 0.0 if a is None and b is None else math.inf
        if self.kind == "count":
            return abs(a - b) / max(abs(a), abs(b), 1)
        return abs(a - b)

    def worse(self, a, b, tol=1e-9):
        """Did `b` (the new run) regress against `a` (the baseline)?

        None on exactly one side counts as a regression. A voice the baseline
        could score and the new run cannot is not "unchanged": it is a
        measurement that stopped existing, and calling that clean is how a
        silent build passes a gate. Both-None is not a regression — nothing
        was ever compared on either side.
        """
        if a is None or b is None:
            return not (a is None and b is None)
        return (b + tol < a) if self.higher_is_better else (a + tol < b)


_DIMENSIONS = {}


def register_dimension(dim, replace=False):
    """Add a Dimension to the shared registry; returns it.

    Refuses to silently redefine an existing key: two tools disagreeing about
    what `freq` reads is the drift this module was extracted to end (see the
    SEMI_REF note at the top of the file). Pass replace=True to mean it.
    """
    if not replace and dim.key in _DIMENSIONS and _DIMENSIONS[dim.key] != dim:
        raise ValueError(f"dimension {dim.key!r} already registered differently; "
                         "pass replace=True if you mean to redefine it")
    _DIMENSIONS[dim.key] = dim
    return dim


def _reg(key, reads, of, kind="fraction", higher_is_better=True):
    return register_dimension(Dimension(key, reads, of, kind, higher_is_better))


# The register-derived dimensions every validator in this repo already
# computes, under the names they already print. Player-specific columns
# (part counts, onset coverage variants) register their own.
_reg("freq", ("$D400/$D401",), "per-frame voice pitch, compared by semitone")
_reg("wf", ("$D404",), "per-frame waveform/control byte")
_reg("pul", ("$D402/$D403",), "per-frame 12-bit duty cycle")
_reg("adsr", ("$D405/$D406",), "per-frame envelope pair")
_reg("cutoff", ("$D415/$D416",), "per-frame filter cutoff")
_reg("filtctl", ("$D417",), "filter resonance + per-voice routing byte")
_reg("volmode", ("$D418",), "filter mode + master volume byte")
_reg("note", ("$D400/$D401", "$D404"), "ordered unbracketed note-onset names")
_reg("onset", ("$D404",), "note-on frames (gate edges)")


def split_key(key):
    """'osc1/freq' -> ('osc1', 'freq'); 'freq' -> ('', 'freq').

    Scores are keyed per scope (voice, part, subtune) so one row can carry a
    whole validator's table, while the dimension — and therefore the register
    account — stays shared across scopes.
    """
    scope, _, dim = str(key).rpartition("/")
    return scope, dim


def dimension(key):
    """Registry lookup for a (possibly scoped) score key. Raises on unknown.

    Deliberately not permissive. A defaulted dimension would count toward the
    'registers read' account without anyone having said which register it
    reads, which is the one thing this registry must never do.
    """
    dim = split_key(key)[1]
    try:
        return _DIMENSIONS[dim]
    except KeyError:
        raise KeyError(
            f"unregistered fidelity dimension {dim!r} (from score key {key!r}); "
            "call fidelity_common.register_dimension() so the run can say "
            "which SID registers this column reads") from None


def dimensions_present(scores):
    """The dimension keys a row actually compared, unscoped and deduped.

    Recorded per row so a run reports what it COVERED, not what it intended to
    cover: a voice whose pulse column came back n/a contributes no $D402/$D403
    coverage, and a row that failed to build contributes none at all.
    """
    return sorted({split_key(k)[1] for k, v in (scores or {}).items()
                   if v is not None})


def registers_read(dim_keys):
    return {r for k in set(dim_keys) if k in _DIMENSIONS
            for r in _DIMENSIONS[k].reads}


def registers_unread(dim_keys):
    """The SID registers no dimension in `dim_keys` is computed from.

    This is the list a change has to land in to be invisible to the run that
    produced those dimensions. Printing it beside a verdict is the difference
    between "nothing regressed" and "nothing regressed in the three registers
    we looked at".
    """
    seen = registers_read(dim_keys)
    return [(reg, what) for reg, what in SID_REGISTERS if reg not in seen]


def format_coverage(dim_keys):
    """Render the 'what this run compared' block from the dimensions a run
    exercised. Generated from the rows, never hand-maintained — a hand-written
    coverage note is a comment, and comments do not fail."""
    keys = sorted(set(dim_keys))
    lines = ["what this run compared:"]
    for k in keys:
        d = _DIMENSIONS.get(k)
        regs = ", ".join(d.reads) if (d and d.reads) else "no SID register"
        lines.append(f"  {k:8} {regs:24} {d.of if d else ''}")
    if not keys:
        lines.append("  (nothing -- no row carried a comparable score)")
    unread = registers_unread(keys)
    if unread:
        lines.append("  NOT read by anything in this run -- a change landing "
                     "here moves no number above:")
        for reg, what in unread:
            lines.append(f"    {reg:14} {what}")
    else:
        lines.append("  every SID register is read by some dimension above")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# run rows: the unit an A/B compares
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Part-1 spans: where a windowed build actually ends
# ---------------------------------------------------------------------------

def part_span(build_path):
    """Seconds part 1 of this build actually covers, or None.

    The builders write a `.span` sidecar beside every part they emit (the label
    already said so; it was printed and thrown away). Reading it turns 41
    UNCONFIRMED rows into measured ones without asking a human for numbers the
    build had already computed.

    None means NO span was recorded -- an older artifact, or a builder whose
    label carries no window. That must stay distinguishable from a span of 0:
    defaulting to the global window is exactly the over-run this guards.
    """
    # Half the players in PLAYERS are keyed on the `.sid` PSID wrapper and half
    # on the `.sf2` -- `emit_one` writes the sidecar beside the `.sf2` it built,
    # so a `.sid`-keyed player must look there too. Getting this wrong is silent:
    # every span reads absent and every row stays UNCONFIRMED, which is exactly
    # what the first run of this did across all 33 HardTrack builds.
    cands = [build_path + ".span"]
    if build_path.lower().endswith(".sid"):
        cands.append(build_path[:-4] + ".sf2.span")
    for c in cands:
        try:
            with open(c) as f:
                t0, t1 = f.read().split()[:2]
        except (OSError, ValueError):
            continue
        t0, t1 = int(t0), int(t1)
        return t1 if t1 > t0 else None
    return None


def build_provenance(build_path):
    """Which commit built this artifact, and under what flags. None if unstamped.

    Reconstructing this once cost NINE worktree builds -- the tree carried no
    record of which commit produced an artifact, so the only way to date a
    corpus was to rebuild it at candidate commits and compare. `emit_one` now
    drops a `.prov` beside every artifact it writes; this reads it back.

    Returns a dict with `commit`, `tree` ("clean"/"dirty"/"unknown"), `builder`
    and `flags`, or None when the sidecar is absent -- an artifact built before
    the stamp existed. None must stay distinguishable from a clean build at an
    unknown commit: "not stamped" and "stamped as unknown" are different facts,
    and collapsing them is how a stale corpus passes for a fresh one.

    `tree` is the load-bearing field. An artifact built from a modified working
    tree is NOT reproducible from its commit, so a bare sha would overstate what
    is known about it.
    """
    # Same `.sid`-vs-`.sf2` keying as `part_span`: half the players are keyed on
    # the PSID wrapper, and `emit_one` writes the sidecar beside the `.sf2`.
    cands = [build_path + ".prov"]
    if build_path.lower().endswith(".sid"):
        cands.append(build_path[:-4] + ".sf2.prov")
    for c in cands:
        try:
            with open(c) as f:
                text = f.read()
        except OSError:
            continue
        out = {"commit": "unknown", "tree": "unknown", "builder": "?", "flags": ""}
        for line in text.splitlines():
            k, _, v = line.partition(" ")
            if k in out:
                out[k] = v.strip()
        return out
    return None


def provenance_census(build_paths):
    """Group artifacts by their (commit, tree, flags) stamp.

    The question this answers is the one that matters for a corpus number: were
    these built TOGETHER? A sweep that averages artifacts from three different
    commits is measuring its own build history, not the player. Returns
    (census, unstamped) where census maps the stamp tuple -> count.
    """
    census, unstamped = {}, 0
    for p in build_paths:
        pr = build_provenance(p)
        if pr is None:
            unstamped += 1
            continue
        key = (pr["commit"], pr["tree"], pr["flags"])
        census[key] = census.get(key, 0) + 1
    return census, unstamped


def window_for(span, seconds):
    """The comparison window for one build: (seconds, derived).

    The rule is deliberately ONE-DIRECTIONAL. A recorded span may only NARROW
    the window; it may never widen it past `--seconds`. Over-running a part is
    the error this whole guard exists for -- past its end our build LOOPS while
    the original plays on, and the difference scores as a defect -- and it cost
    five retracted readings across three tools in one session. Narrowing can
    only ever remove manufactured disagreement, so it is safe in a way widening
    is not.

    `derived` is True only when a span actually changed the window, so the
    report can say which rows were measured over their own part rather than
    leaving the reader to assume it.
    """
    if span and span < seconds:
        return span, True
    return seconds, False


def output_digest(paths):
    """sha256 (12 hex) over the artifacts a run BUILT, or None if any is missing.

    This is the half of an A/B that "no number moved" cannot supply on its own.
    That sentence has two readings — the change is invisible to everything
    measured, or the change reached nothing — and they call for opposite next
    steps. Hashing the build output separates them.

    Returns None, never a hash, when a path does not exist. The digest of
    nothing is `e3b0c44298fc`, which compares equal to itself: two failed
    builds would otherwise report "byte-identical output", the same empty==empty defect that
    let the v3.21.0 zig64 gate certify 64 zero bytes as a match (see
    `score_pct`). No evidence is not agreement.

    The basename and length are folded in before the bytes so that renaming or
    truncating a part cannot collide with the unchanged build.
    """
    if isinstance(paths, (str, bytes, os.PathLike)):
        paths = [paths]
    paths = list(paths)
    if not paths:
        return None
    # sha256, not sha1: this is a content fingerprint, not a security digest,
    # but bandit B324 fails the CI security scan on sha1 regardless, and
    # `usedforsecurity=False` needs Python 3.9 (the CI matrix still runs 3.8).
    h = hashlib.sha256()
    for p in sorted(paths, key=lambda x: os.path.basename(str(x))):
        try:
            with open(p, "rb") as fh:
                data = fh.read()
        except OSError:
            return None
        h.update(os.path.basename(str(p)).encode("utf-8", "replace"))
        h.update(b"\0")
        h.update(len(data).to_bytes(8, "little"))
        h.update(data)
    return h.hexdigest()[:12]


def git_label(root=None):
    """`git rev-parse --short HEAD` plus `-dirty` when this repo is modified.

    A version string does not identify a measurement: many commits share one
    `__version__` across a branch's life, and a half-applied edit shares its
    version with the commit it is NOT. This repo has re-run corpus sweeps for
    that reason.

    Scoped to THIS repo. `C:\\Users\\mit\\claude\\` holds several unrelated
    checkouts side by side and their edits say nothing about a SID conversion;
    `git -C <root> status --porcelain -- .` is already scoped correctly by git
    itself. Returns None wherever git does not answer — an unlabelled run is
    worse than a labelled one, but not worth failing a measurement over.
    """
    root = root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        head = subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=15,
                              stdin=subprocess.DEVNULL)
        rev = head.stdout.strip()
        if head.returncode != 0 or not rev:
            return None
        st = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--", "."],
                            capture_output=True, text=True, timeout=120,
                            stdin=subprocess.DEVNULL)
        return rev + ("-dirty" if st.stdout.strip() else "")
    except (OSError, subprocess.SubprocessError):
        return None


def result_row(target, scores, measurement=None, options=None,
               output_sha=None, label=None, **extra):
    """One measured target, in the shape `compare_runs` and the JSON both take.

    The only judgement this function asks of a caller is which bucket a setting
    goes in, and it is the whole point of the split:

      `measurement`  how the number was TAKEN — window length, subtune, offset
                     policy. A delta across two of these is a delta between
                     numbers about different music, so `compare_runs` refuses.
      `options`      what was BUILT — the converter/builder flags under test.
                     A delta here is not contamination, it is the experiment;
                     it is surfaced at the head of the report instead.

    `dimensions` is derived, not passed: it is what the row actually scored,
    which is the only thing a coverage claim may be built from.
    """
    scores = dict(scores or {})
    for k in scores:                    # fail loudly at build time, not report time
        dimension(k)
    row = {
        "target": str(target),
        "scores": scores,
        "dimensions": dimensions_present(scores),
        "measurement": dict(measurement or {}),
        "options": dict(options or {}),
        "output_sha": output_sha,
        "label": label,
    }
    row.update(extra)
    return row


def ab_pair(target, base, new, measurement=None, label=None):
    """One target measured two ways in the SAME process -> (base_row, new_row).

    `base` and `new` are dicts: `scores` and `options` as `result_row` takes
    them, `paths` naming the artifacts that side BUILT, and anything else
    carried through as row fields. The measurement settings and the tree label
    are shared by construction, because they are properties of the run and not
    of a side — half the value of refusing a settings mismatch is lost if a
    caller can accidentally give the two sides different windows.

    `paths` is hashed here rather than by the caller, and that is the point:
    every in-process A/B in this tree builds both sides into ONE output
    directory, so the second build overwrites the first and a digest taken at
    the wrong moment silently hashes the other side's file. Calling this once,
    at the end, forces both paths to be named while both still exist — one
    ordering decision instead of two.
    """
    def _row(side):
        side = dict(side)
        return result_row(target, side.pop("scores", None),
                          measurement=measurement, label=label,
                          options=side.pop("options", None),
                          output_sha=output_digest(side.pop("paths", [])),
                          **side)
    return _row(base), _row(new)


def dump_rows(path, rows):
    """Write a run's rows as JSON — the baseline a later run is compared to."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"rows": list(rows)}, fh, indent=1, sort_keys=True)
    return path


def load_rows(path):
    """Read rows written by `dump_rows` (also accepts a bare list)."""
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    return doc["rows"] if isinstance(doc, dict) else list(doc)


# ---------------------------------------------------------------------------
# A/B comparison
# ---------------------------------------------------------------------------
#
# Fifteen scripts in this tree hand-roll the same apparatus: build twice,
# trace twice, diff, decide whether anything regressed. `bin/_verify_f4_*.py`
# (three of them), `bin/_verify_f5_*.py` (two), `bin/_verify_*_source_edit.py`,
# `pyscript/blackbird_sweep.py`, `pyscript/mon_struct_sweep.py` and the rest.
# They disagree about what counts as a regression, none of them records the
# tree they ran against, none records whether the build output changed at all,
# and none states which registers it was blind to while it decided.

@dataclass
class RunDelta:
    """The structured result of `compare_runs`; `format_run_delta` renders it."""
    base_label: str = ""
    new_label: str = ""
    refused: list = field(default_factory=list)
    option_drift: list = field(default_factory=list)
    both: list = field(default_factory=list)
    only_base: list = field(default_factory=list)
    only_new: list = field(default_factory=list)
    bytes_changed: list = field(default_factory=list)
    bytes_same: list = field(default_factory=list)
    bytes_unknown: list = field(default_factory=list)
    moved: list = field(default_factory=list)        # [(target, [(key,a,b,mv)])]
    regressed: list = field(default_factory=list)    # [(target, [(key,a,b)])]
    dimension_summary: dict = field(default_factory=dict)  # key -> (moved, seen)
    dimensions: list = field(default_factory=list)
    verdict: str = ""

    @property
    def exit_code(self):
        """2 = refused (nothing was compared), 1 = a regression, 0 = clean."""
        return 2 if self.refused else (1 if self.regressed else 0)


def settings_mismatch(base, new):
    """Measurement settings that differ per target — the refusal condition.

    EVERY key a caller puts in `measurement` is fatal on mismatch; there is no
    whitelist, because the caller already decided by putting it there. A key
    present on one side only is treated as OLD, not wrong: a baseline taken
    before a field existed is still a baseline, and refusing it would make
    every saved run worthless the first time someone records a new field.
    """
    bad = []
    for name in sorted(base):
        b, n = base[name], new.get(name)
        if n is None:
            continue
        bm, nm = b.get("measurement") or {}, n.get("measurement") or {}
        for k in sorted(set(bm) & set(nm)):
            if bm[k] != nm[k]:
                bad.append(f"{name}: {k} {bm[k]!r} -> {nm[k]!r}")
    return bad


def option_drift(base, new):
    """Build/conversion options that differ, aggregated over affected targets.

    NOT a refusal. An option A/B is the commonest thing this mode is wanted
    for — it is literally what `mon_struct_sweep.py` exists to answer — and
    refusing it would leave the apparatus being rebuilt by hand for exactly
    the change the mode is for. The hazard worth guarding against is options
    drifting between two runs UNNOTICED, and printing them answers that.
    """
    diffs = {}
    for name in base:
        n = new.get(name)
        if n is None:
            continue
        bo, no = base[name].get("options") or {}, n.get("options") or {}
        for k in set(bo) | set(no):
            if bo.get(k) != no.get(k):
                diffs.setdefault((k, repr(bo.get(k)), repr(no.get(k))), set()).add(name)
    return [f"{k} {a} -> {c} on {len(t)} target(s)"
            for (k, a, c), t in sorted(diffs.items())]


def regressions(base_row, new_row, tol=1e-9):
    """[(score_key, baseline, new)] for every score that got worse.

    'Worse' is per-Dimension (`higher_is_better`), so a caller does not have to
    remember that part count goes down and agreement goes up. A key scored on
    one side only is a regression — see `Dimension.worse`.
    """
    a, b = base_row.get("scores") or {}, new_row.get("scores") or {}
    out = []
    for k in sorted(set(a) | set(b)):
        x, y = a.get(k), b.get(k)
        if dimension(k).worse(x, y, tol):
            out.append((k, x, y))
    return out


def _label_of(rows, fallback):
    for r in rows:
        if r.get("label"):
            return r["label"]
    return fallback


def compare_runs(base_rows, new_rows, tol=1e-9):
    """A/B two runs of `result_row`s -> RunDelta, sorted by largest movement.

    Generic over whatever a caller scores: the rows carry `{score_key: number}`
    and the registry supplies the rest. Nothing here knows about MoN parts or
    Hubbard phases.

    The verdict deliberately refuses to say "no effect". "No number moved" has
    two readings and this project has shipped the wrong one before: h2g (the
    sibling port) shipped two dead conversion options believing a flat table
    meant a no-op, and SIDM2's own `docs/players/HUBBARD.md` carried a "filter
    100%" that was 0==0 for the same reason. So the verdict pairs the numbers
    with `output_digest` (did the build change?) and `registers_unread` (could
    we have seen it?), and names which of the two cases it is.
    """
    base = {r["target"]: r for r in base_rows if r.get("target")}
    new = {r["target"]: r for r in new_rows if r.get("target")}
    d = RunDelta(base_label=_label_of(base_rows, "baseline"),
                 new_label=_label_of(new_rows, "current"))
    d.both = sorted(set(base) & set(new))
    d.only_base = sorted(set(base) - set(new))
    d.only_new = sorted(set(new) - set(base))

    d.refused = settings_mismatch(base, new)
    if d.refused:
        return d
    if not d.both:
        d.refused = ["no target appears in both runs"]
        return d

    d.option_drift = option_drift(base, new)
    for t in d.both:
        a, b = base[t].get("output_sha"), new[t].get("output_sha")
        if not a or not b:
            d.bytes_unknown.append(t)
        elif a != b:
            d.bytes_changed.append(t)
        else:
            d.bytes_same.append(t)

    seen, movedn = {}, {}
    for t in d.both:
        sa, sb = base[t].get("scores") or {}, new[t].get("scores") or {}
        deltas = []
        for k in sorted(set(sa) | set(sb)):
            dim = dimension(k)
            x, y = sa.get(k), sb.get(k)
            seen[dim.key] = seen.get(dim.key, 0) + 1
            if x != y:
                movedn[dim.key] = movedn.get(dim.key, 0) + 1
                deltas.append((k, x, y, dim.movement(x, y)))
        if deltas:
            deltas.sort(key=lambda e: e[3], reverse=True)
            d.moved.append((t, deltas))
        reg = regressions(base[t], new[t], tol)
        if reg:
            d.regressed.append((t, reg))
    d.moved.sort(key=lambda e: e[1][0][3], reverse=True)
    d.dimension_summary = {k: (movedn.get(k, 0), seen[k]) for k in sorted(seen)}
    d.dimensions = sorted({k for t in d.both
                           for k in (new[t].get("dimensions")
                                     or dimensions_present(new[t].get("scores")))})

    if d.regressed:
        d.verdict = (f"{len(d.regressed)} of {len(d.both)} target(s) regressed "
                     "on at least one measured dimension")
    elif d.moved:
        d.verdict = (f"no regression; {len(d.moved)} of {len(d.both)} target(s) "
                     "moved at least one number")
    elif d.bytes_changed:
        d.verdict = (f"NO number moved, but the build output differs on "
                     f"{len(d.bytes_changed)} of {len(d.both)} target(s) -- the "
                     "change reached the output and is invisible to what this "
                     "run compares, NOT a no-op")
    elif d.bytes_same and not d.bytes_unknown:
        d.verdict = (f"no number moved and the build output is byte-identical "
                     f"on all {len(d.bytes_same)} target(s) -- the change "
                     "reached nothing here")
    else:
        d.verdict = (f"no number moved, and the build output could not be "
                     f"compared on {len(d.bytes_unknown)} of {len(d.both)} "
                     "target(s), so this run CANNOT say whether the change "
                     "reached the build at all -- record output_sha to tell "
                     "'invisible to the metric' and 'reached nothing' apart")
    return d


def format_run_delta(delta, top=10):
    """Render a RunDelta as plain text: the change under test, the biggest
    movers, the regressions, the verdict, and what the run was blind to."""
    L = [f"A/B  {delta.base_label} -> {delta.new_label}"]
    if delta.refused:
        L.append("REFUSED: these runs were measured at different settings, so a "
                 "delta between them is a delta between different music.")
        L += [f"  - {m}" for m in delta.refused[:top]]
        if len(delta.refused) > top:
            L.append(f"  - ... and {len(delta.refused) - top} more")
        L.append("Re-take the baseline at the settings you are measuring at.")
        return "\n".join(L)

    L.append(f"{len(delta.both)} target(s) in both runs"
             + (f", {len(delta.only_base)} only in baseline" if delta.only_base else "")
             + (f", {len(delta.only_new)} only in current" if delta.only_new else ""))
    L.append("")
    L.append("the change under test:")
    L += ([f"  - options: {o}" for o in delta.option_drift]
          or ["  - options: identical on every target in both runs"])
    if delta.bytes_unknown:
        L.append(f"  - build output: UNKNOWN on {len(delta.bytes_unknown)} "
                 "target(s) (no output_sha recorded)")
    if delta.bytes_changed:
        L.append(f"  - build output: differs on {len(delta.bytes_changed)} target(s)")
    if delta.bytes_same:
        L.append(f"  - build output: byte-identical on {len(delta.bytes_same)} target(s)")

    if delta.moved:
        L.append("")
        L.append("largest movement (by dimension, biggest first):")
        for t, deltas in delta.moved[:top]:
            k, a, b, _ = deltas[0]
            L.append(f"  {t:28} {k:14} {fmt_pct(a)} -> {fmt_pct(b)}"
                     + (f"  (+{len(deltas) - 1} more)" if len(deltas) > 1 else ""))
        if len(delta.moved) > top:
            L.append(f"  ... and {len(delta.moved) - top} more")
    if delta.dimension_summary:
        L.append("")
        L.append("per-dimension: " + ", ".join(
            f"{k} {m}/{s}" for k, (m, s) in delta.dimension_summary.items()))
    if delta.regressed:
        L.append("")
        L.append("REGRESSED:")
        for t, reg in delta.regressed:
            for k, a, b in reg:
                L.append(f"  !! {t:28} {k:14} {fmt_pct(a)} -> {fmt_pct(b)}")
    L.append("")
    L.append(f"verdict: {delta.verdict}")
    L.append("")
    L.append(format_coverage(delta.dimensions))
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Per-voice register agreement (the register half of the audio/register cross-tab)
# ---------------------------------------------------------------------------

def per_voice_register_agreement(orig_path, drv_path, secs, orig_args=(), drv_args=(),
                                  max_delay=6, dims=('freq', 'wf', 'pul')):
    """Per-voice register agreement between two SIDs, one score per dimension.

    Exists so `pyscript/audio_tightness_tool.py` can put a register verdict
    beside its audio verdict for the SAME voice. Neither measurement can make
    that partition alone:

        registers match  + audio diverges  -> driver SYNTHESIS is wrong
                                              (envelope / pulse / filter timing)
        registers diverge + audio diverges -> note data / sequencer is wrong
        registers diverge + audio matches  -> a METRIC artifact, e.g. a
                                              phase-offset but musically correct
                                              pulse sweep scored frame-by-frame

    Scores route through `score_pct` + `exercised` (both guards, per D4) rather
    than reimplementing a weighted scheme -- this is deliberately NOT a sixth
    copy. `freq` is compared as a SEMITONE, not a raw 16-bit value: a vibrato
    that lands on the same note is not a note error, and the audio side cannot
    hear the difference either.

    Returns (rows, meta):
        rows = {voice_index_0_based: {dim: pct_or_None}}
        meta = {'frames': n, 'delay': d, 'orig_frames': .., 'drv_frames': ..}

    A None score means "not measured" -- either no frames, or the dimension was
    not exercised on either side. It is never a 0 and never a 100.
    """
    # siddump's -t takes an INTEGER second count; `-t21.0` parses as nothing and
    # the tool silently returns a zero-row table. `secs` arrives as a float from
    # argparse, so it is rounded here rather than at every call site.
    tsec = int(round(float(secs))) + 1
    orig = siddump_frames_full(orig_path, list(orig_args) + [f"-t{tsec}"])
    drv = siddump_frames_full(drv_path, list(drv_args) + [f"-t{tsec}"])
    # -4: the last few frames of a siddump can be a partial trailing write, the
    # same trim bin/mon_part_fidelity.py applies.
    n = min(len(orig), len(drv), int(secs * 50)) - 4
    if n <= 0:
        raise ValueError(
            f"empty register comparison window (n={n}): orig={len(orig)} frames, "
            f"drv={len(drv)} frames, secs={secs}. Refusing rather than scoring "
            f"an empty window (see score_pct).")

    def _agree_at(d):
        s = 0
        for i in range(0, n, 2):
            oi = i + d
            if not (0 <= oi < len(orig)):
                continue
            for vi in range(3):
                a, b = orig[oi][0][vi]['freq'], drv[i][0][vi]['freq']
                if a and b and freq_to_semi(a) == freq_to_semi(b):
                    s += 1
        return s

    # A constant engine output delay is a nuisance parameter, not an error --
    # aligned out here exactly as every other scorer in this repo does.
    delay = max(range(-max_delay, max_delay + 1), key=_agree_at)

    rows = {}
    for vi in range(3):
        row = {}
        for dim in dims:
            a_vals, b_vals = [], []
            for i in range(n):
                oi = i + delay
                if not (0 <= oi < len(orig)):
                    continue
                a, b = orig[oi][0][vi][dim], drv[i][0][vi][dim]
                if dim == 'freq':
                    a = freq_to_semi(a) if a is not None else None
                    b = freq_to_semi(b) if b is not None else None
                a_vals.append(a)
                b_vals.append(b)
            if not exercised(a_vals, b_vals):
                row[dim] = None
                continue
            tot = sum(1 for a, b in zip(a_vals, b_vals) if a is not None and b is not None)
            ok = sum(1 for a, b in zip(a_vals, b_vals)
                     if a is not None and b is not None and a == b)
            row[dim] = score_pct(ok, tot)
        rows[vi] = row
    return rows, {'frames': n, 'delay': delay,
                  'orig_frames': len(orig), 'drv_frames': len(drv)}
