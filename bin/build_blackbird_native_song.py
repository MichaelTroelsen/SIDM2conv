"""Stage B1 -- emit a REAL Blackbird (Linus Åkesson / "lft") tune as a
native-Blackbird-driver .sf2.

Follows bin/build_romuzak_native_song.py's shape (per docs/players/
PLAYBOOK.md and this task's brief): decode the song via the already-shipped
sidm2.blackbird_parser (locate + LZ decompression, untouched here), build
the per-voice D11Row track using the SAME tick-is-a-row model
sidm2.blackbird_driver11.py's Stage A already established (re-derived here,
not imported, because Stage A's steps_for_voice() drops the fx/arp byte --
this module needs it for the per-note fx command column), then
translate Blackbird's own wave/pulse/filter/fx programs into the shared
native driver's WAVE/FILTER table formats (plus the verbatim fx/freq
tables B10 hands straight through) using the
validated per-frame simulator (bin/blackbird_everyframe_sim.py, copied
verbatim into the repo this session from the scratch path
docs/players/BLACKBIRD.md's "Stage B synth engine" section names) as the
formula oracle -- see each translator function's docstring for exactly how.

## Translation method (formula oracle, not re-derivation)

For WAVE+PULSE and FILTER, the position-walk (wavepos / zp_filtpos) that
Blackbird's `everyframe` steps through is driven ENTIRELY by fixed table
bytes (see BLACKBIRD.md's per-engine semantics) -- it never depends on
runtime voice state. So each translator constructs a throwaway
`BlackbirdSim`, seeds ONLY the one voice-state field the target program
starts from (`wavepos`/`fxpos`/`zp_filtpos`), and calls `sim.everyframe()`
directly in a loop, WITHOUT going through `real_frame()`'s prepare1/2/3/
execute dispatch at all (those stages only ever touch pendnote/pendfx/
pendins/trtimer -- `everyframe()` never reads them). This sidesteps having
to hand re-derive the intricate 6502 carry/asl/ror semantics documented in
BLACKBIRD.md (bit6/bit7 pulse-row carry trick, the 4 fx blend modes, the
filter's overlapping-3rd-byte jump test) -- the ALREADY-VALIDATED simulator
computes them, we only read off the resulting per-frame $D400-$D418 register
values and re-encode them into the shared engine's OWN row format (SET/ADD/
jump for WAVE+FILTER, an accumulator-delta table for PULSE+FM -- see below).
Since the position walk is state-independent, reading `sim.v[0].wavepos` /
`sim.zp_filtpos` before each `everyframe()` call gives the EXACT internal
position sequence for free (no re-derivation of the jump-offset arithmetic),
which is used for cycle detection (the position space is <=256 states, so a
repeat is guaranteed within 300 steps by the pigeonhole principle).

WAVE and FILTER have a general "jump to an earlier row" primitive ($7f =
relative/absolute jump); the translator uses it once a program's
visited-state cycle is found:
  - WAVE:   emit rows 0..cycle_end-1 + a genuine `$7f` jump row back to
            cycle_start -- loops forever, exact. Since B9 the SAME rows also
            carry the pulse deltas (col1 on a bit6 row), so PULSE is exact
            for any note length too, with no separate table.
  - FILTER: emit SET rows (baseline) + ADD-delta rows (RLE-collapsed holds
            and linear ramps) for 0..cycle_end-1, ending in a genuine `$7f`
            jump back to cycle_start -- loops forever, exact.

PITCH is not translated at all any more (B10). The driver runs lft's own
`everyframe` fx interpolator over lft's own fxtable + freq_lsb/freq_msb
bytes, copied verbatim, so a "program" is just an fx INDEX and the note
enters only as `BASEPITCH = note*4` inside the driver. See the "B10" block
above fx_table_info() for what that deleted (per-(fx,note) FMTAB programs,
the 64-slot clustering, and the FM engine's 1-frame note-trigger lag).

See "Filter" for the SET/ADD row byte encoding (derived from
drivers_src/romuzak/romuzak_driver.asm's fp_set/fp_dec decode logic, run in
reverse -- cited inline at each encoder).

Usage:  py -3 bin/build_blackbird_native_song.py [SID/LFT/Fargo.sid]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))

import build_blackbird_driver_full as B
from blackbird_everyframe_sim import (
    BlackbirdSim, asl as _asl, adc as _adc, ror as _ror, lsr as _lsr,
)
from sidm2.blackbird_parser import (
    locate_blackbird, load_sid, decode_streams, classify_byte,
)
from sidm2.blackbird_driver11 import extract_tempo_pairs
from sidm2.sf2_header_generator import SF2HeaderGenerator
from sidm2 import placeholder_edit_area
from sidm2.galway_driver11_emitter import segment_track, unpack_sequence
from sidm2.galway_to_driver11 import (
    D11Row, SF2_NOTE_MIN, SF2_NOTE_MAX, SF2_GATE_ON, SF2_GATE_OFF,
)
from sidm2.sid_player import FREQ_TABLE_LO, FREQ_TABLE_HI

NFM = 64                 # $c0-$ff command space (index = byte & 0x3f)
# Stage A's user-verified pitch calibration: SF2 note = blackbird note + 9.
# B10 made this load-bearing in the DRIVER too (pr_note has to undo it to
# recover Blackbird's own note index before computing BASEPITCH = note*4),
# so it is a named constant emitted into layout.inc as NOTE_OFS rather than
# a literal 9 sitting in two places that could drift apart.
SF2_NOTE_OFS = 9
CYCLE_SEARCH_FRAMES = 300   # > 256 states -> a repeat is guaranteed (pigeonhole)
TARGET_FM_PULSE_FRAMES = 250  # ~5s @ 50fps; PULSE/FM have no jump primitive
# B9 RETIRED B8's PULSE_CAPTURE_FRAMES (was 1200). B8 had to capture pulse
# OUTPUT over a long window because the accumulator does not repeat when
# wavepos does; B9 stores the DELTA program instead and runs the accumulator
# in the driver, so the capture only ever needs the wavepos cycle itself
# (CYCLE_SEARCH_FRAMES) and the output is exact for any length -- there is no
# capture window to run past any more. See unroll_wave_pulse's B9 block.



# ---------------------------------------------------------------------------
# Blackbird byte stream -> steps, WITH fx tracking (Stage A's steps_for_voice
# drops fx entirely -- this is a parallel/extended version, not an edit of
# sidm2/blackbird_driver11.py, which this task must not touch).
# ---------------------------------------------------------------------------
class BBStep:
    __slots__ = ('kind', 'note', 'instrument', 'fx', 'tie', 'ticks')

    def __init__(self, kind, note, instrument, fx, tie, ticks):
        self.kind = kind
        self.note = note
        self.instrument = instrument
        self.fx = fx
        self.tie = tie
        self.ticks = ticks


def _note_ticks(b):
    return 1 if (b & 1) else 2


def _delay_ticks(b):
    return 16 - (b & 0x0F)


def bb_steps_for_voice(byte_stream):
    """Mirrors blackbird_driver11.steps_for_voice's grouping exactly (see
    its docstring for the tick-duration derivation, ported verbatim as
    _note_ticks/_delay_ticks above), extended to also carry the STICKY fx
    program index (1-based Blackbird index, `b - 0xC8` -- matching
    BlackbirdSim.prepare1's own `result = (tested - 0xc8) & 0xff`, NOT
    blackbird_parser.classify_byte's cosmetic 0-based 'arp' arg, which
    Stage A never used for anything since it discards fx).

    B12: pending_instr/pending_tie must attach to the VERY NEXT event of
    ANY kind (note OR delay), not just the next NOTE. player.s's prepare1/
    2/3 form a SINGLE per-tick chain over the compressed stream: prepare2
    consumes AT MOST one instrument/gate-off/legato byte per tick, and
    prepare3 (SAME tick) then reads whatever byte comes immediately after
    it -- note or delay, doesn't matter, it's still the SAME real tick. So
    an instrument-select is NEVER "several ticks before the next note" on
    hardware; it is always exactly one tick before whatever comes right
    after it in the stream. The old code only cleared pending_instr/
    pending_tie inside the 'note' branch, so a standalone instrument-select
    (or legato byte) immediately followed by a DELAY/rest byte -- a real,
    common pattern, e.g. an instrument change happening while a prior note
    is still held -- silently held its effect pending across every
    subsequent delay/rest tick until whatever note eventually came next,
    sometimes many ticks later, and (worse) a stale pending_tie could then
    wrongly suppress that later, unrelated note's own restart. Traced
    directly against a real decoded byte stream (Fargo voice 1, bytes
    #362-369): a legato byte paired correctly with its adjacent note, but a
    standalone instrument-select at byte #365 (sandwiched between two
    delay/hold bytes) was getting bundled onto a note SEVEN ticks later
    that was itself tied -- exactly the silent-deferral pattern this fixes.
    execute() (player.s:433-500) restarts WAVE/FILTER/ADSR/GATE on EVERY
    tick where v_pendins is a real instrument value, independent of
    note/delay -- see blackbird_driver.asm's matching driver-side fix in
    set_instr_v, which commits that restart immediately instead of
    deferring it to pn_note. Both halves were required together, same as
    B11's fx fix."""
    steps = []
    pending_instr = None
    pending_tie = False
    gate_is_off = False
    had_note_yet = False
    cur_fx = 0                     # sticky, like currfx in the real player

    for b in byte_stream:
        kind = classify_byte(b)
        if kind == 'oob':
            continue
        if kind == 'arp':
            cur_fx = (b - 0xC8) & 0xFF
            continue
        if kind == 'unknown':
            continue
        if kind == 'instrument':
            # BlackbirdSim/execute() treats (b-0x82) as a 1-BASED instrument
            # number and indexes ins_ad/ins_wave/etc with `[y-1]` (see
            # BLACKBIRD.md's relocation-manifest note "ins_ad + -1" -- the
            # template itself is built for 1-based `LDA table-1,Y`
            # addressing). The D11/native driver's instrument command byte
            # ($a0-$bf / pr_setinst here) is instead a DIRECT 0-based table
            # ROW index (`tay; lda INSTR_AD,y`) -- so this module stores the
            # already-decremented 0-based row index throughout, unlike
            # blackbird_driver11.py's steps_for_voice (Stage A), which
            # stores the 1-based value directly as D11Row.instrument. That
            # is an off-by-one in Stage A's instrument selection (harmless
            # there only because every Stage-A instrument shares one flat
            # default wave/AD/SR-driven timbre pattern, so a shifted AD/SR
            # substitution isn't obviously wrong on a casual listen) --
            # NOT reproduced here since Stage B's per-instrument WAVE/
            # PULSE/FILTER programs make a wrong row audibly and
            # measurably wrong. Not fixed in blackbird_driver11.py per this
            # task's explicit scope (that file is not touched).
            pending_instr = min(max(b - 0x83, 0), 31)
            continue
        if kind == 'gate_off':
            gate_is_off = True
            continue
        if kind == 'legato':
            pending_tie = True
            gate_is_off = False
            continue
        if kind == 'note':
            # B13: a note byte immediately following a gate-off does NOT
            # retrigger on real hardware. prepare3 (player.s 167-200) always
            # updates v_pendnote from a note byte's own value regardless of
            # what came before it -- but ALSO: `if vs.pendins == 0:
            # vs.pendins = vs.currins` only fires when pendins is STILL 0,
            # and a gate-off byte just consumed by prepare2 already set
            # pendins=$FE, so this note byte's own tick does NOT clear it.
            # execute() (player.s 447-457) then sees pendins=$FE and does
            # ONLY `v_wavemask,x = $FE` (gate stays off) -- no wavepos/ADSR/
            # filter restart, regardless of the note value that was also
            # read this same tick. Verified directly against a live,
            # hardware-validated BlackbirdSim trace (Glyptodont voice 2,
            # real frames ~10165-10168: $cd[fx] $80[gate_off] $2f[note=23] --
            # wavemask flips to $FE, wavepos never moves). The OLD code here
            # treated ANY note byte as a genuine active-note step, silently
            # discarding gate_is_off (which the 'delay' branch below DOES
            # check) -- so the native driver retriggered a full wave/filter/
            # gate restart where real hardware just goes silent. Emitting a
            # 'rest' step instead (same convention the 'delay' branch already
            # uses for gate_is_off) matches the OBSERVABLE effect exactly:
            # the note value has no audible consequence while gated off, and
            # whatever note/instrument eventually DOES retrigger will supply
            # its own values fresh at that point.
            note = b >> 1
            if gate_is_off:
                steps.append(BBStep('rest', None, pending_instr, cur_fx,
                                     False, _note_ticks(b)))
            else:
                steps.append(BBStep('note', note, pending_instr, cur_fx,
                                     pending_tie, _note_ticks(b)))
            pending_instr = None
            pending_tie = False
            gate_is_off = False
            had_note_yet = True
            continue
        if kind == 'delay':
            ticks = _delay_ticks(b)
            if gate_is_off or not had_note_yet:
                steps.append(BBStep('rest', None, pending_instr, cur_fx, False, ticks))
            else:
                steps.append(BBStep('note', None, pending_instr, cur_fx, False, ticks))
            pending_instr = None
            pending_tie = False    # consumed here so it can't leak onto a
                                    # later, unrelated note -- see docstring
            # B13: gate_is_off must ALSO be consumed here, same reasoning as
            # pending_instr/pending_tie. v_pendins resets to 0 in EVERY
            # execute() call (player.s 497-500) and prepare1/2/3 are all
            # SKIPPED for a voice during a multi-tick delay's own hold
            # (v_trtimer negative) -- so a gate-off's silencing effect
            # genuinely only lasts through the ONE delay/rest event that
            # immediately follows it; once that delay's own countdown
            # expires, the NEXT event gets a fresh prepare2 examination
            # (whose "got_note: reuse currins as pendins" path -- see
            # BlackbirdSim.prepare2 -- automatically RESTARTS the gate for a
            # following untied note, independent of the earlier gate-off).
            # Leaving this unreset was harmless before this session (nothing
            # downstream checked gate_is_off outside the delay branch that
            # already correctly used-and-discarded it per delay), but once
            # the 'note' branch above also started checking it, the stale
            # carry-forward across an unbounded run of delay events
            # over-applied "stays silent" to 14-45% of ALL notes in the
            # song (measured) instead of the rare same-tick gate-off/note
            # pairing this was meant to catch -- verified by rebuilding and
            # seeing Glyptodont regress from 92.0% to 73.2% before this line
            # was added.
            gate_is_off = False
            continue
    return steps


# ---------------------------------------------------------------------------
# B6 (part-splitting): window a per-voice BBStep list to a tick-row range
# [row0, row1) -- ticks map 1:1 to D11 rows (see BLACKBIRD.md's "Tempo-model
# open caveat -- RESOLVED"), so windowing by ROW index needs none of DMC's
# frame-alignment machinery (its `align()` exists because DMC windows by real
# FRAME position under a coarser tick grid -- Blackbird's tick IS the row).
# ---------------------------------------------------------------------------
def window_steps(steps, row0, row1):
    """Slice one voice's full-song BBStep list to [row0, row1) row-ticks.

    STATE CONTINUITY (matching bin/build_mon_native_song.py's build_native_song
    win= convention, read in full before writing this): a note/held-note that's
    still sounding when row0 lands mid-step is RE-ENTERED at row0 rather than
    silently dropped (dropping it would leave the voice silent until its next
    real onset -- exactly the defect DMC's own win= docstring names and fixes).
    Unlike DMC/MoN (whose per-note WAVE/PULSE/FM programs are captured live
    from a siddump trace, so a mid-note capture starting at the boundary's own
    phase is *exact* by construction), Blackbird's programs are STRUCTURAL --
    unroll_wave_pulse/unroll_filter always replay a program from ITS
    OWN row 0 on every genuine note trigger, matching real hardware's own
    pn_note behaviour (there is no "resume mid-cycle" primitive in either the
    real player or the shared native engine). So a re-entered note is forced
    to a genuine trigger (tie=False, explicit instrument+fx+note) rather than
    a tie: tie=True at a part's own row 0 would leave WAVE+FILTER parked at
    whatever `do_init` seeds (see B4 Bug 3 -- tie skips their restart
    entirely), not at the correct instrument's program, which is wrong for
    the note's WHOLE remaining duration, not just briefly. This is a real,
    named residual (not silently absorbed): any part boundary that lands
    inside a sustained note re-triggers that note's WAVE/PULSE/FM programs a
    tick early relative to real hardware, audible as a brief re-attack
    transient at that instant -- see docs/players/BLACKBIRD.md's part-
    splitting section.
    """
    out = []
    pos = 0
    cur_instr = None
    last_note = None
    started = False
    for s in steps:
        ticks = max(1, s.ticks)
        s_end = pos + ticks
        if s.instrument is not None:
            cur_instr = s.instrument
        if s.kind == 'note' and s.note is not None:
            last_note = s.note
        if s_end <= row0:
            pos = s_end
            continue
        if pos >= row1:
            break
        seg_start = max(pos, row0)
        seg_end = min(s_end, row1)
        seg_ticks = seg_end - seg_start
        if seg_ticks <= 0:
            pos = s_end
            if pos >= row1:
                break
            continue
        if not started:
            if s.kind == 'rest':
                out.append(BBStep('rest', None, None, s.fx, False, seg_ticks))
            else:
                note_val = s.note if s.note is not None else last_note
                out.append(BBStep('note', note_val, cur_instr, s.fx, False, seg_ticks))
            started = True
        else:
            instr = s.instrument if seg_start == pos else None
            tie = s.tie if seg_start == pos else False
            out.append(BBStep(s.kind, s.note, instr, s.fx, tie, seg_ticks))
        pos = s_end
        if pos >= row1:
            break
    if not out:
        out = [BBStep('rest', None, None, 0, False, max(1, row1 - row0))]
    return out


# ---------------------------------------------------------------------------
# Generic run-length collapse: [(v0,v0,v0,v1,v1,...)] -> [(v,count<=cap), ...]
# ---------------------------------------------------------------------------
def _rle(values, cap=255):
    segs = []
    i, n = 0, len(values)
    while i < n:
        v = values[i]
        j = i + 1
        while j < n and values[j] == v:
            j += 1
        run = j - i
        while run > cap:
            segs.append((v, cap))
            run -= cap
        segs.append((v, run))
        i = j
    return segs


def _find_cycle(positions):
    """positions[k] = internal engine state BEFORE frame k's step. Returns
    (cycle_start, cycle_end) such that positions[cycle_start] is the first
    position value that repeats, at index cycle_end. Guaranteed to exist
    within len(positions) states by the pigeonhole principle (<=256 states)
    as long as positions is long enough (CYCLE_SEARCH_FRAMES > 256)."""
    seen = {}
    for i, p in enumerate(positions):
        if p in seen:
            return seen[p], i
        seen[p] = i
    return 0, len(positions)       # never repeated in the window (shouldn't happen)


# ---------------------------------------------------------------------------
# B7 (part-boundary priming, docs/players/BLACKBIRD.md's "B7" section):
# capture the FULL-SONG simulator's real per-voice/global engine state at a
# specific real frame (see run_full_song_sim's snapshot_cb wiring below), and
# map a captured absolute WAVE/FILTER table position back to the LOCAL row
# index a translated program (unroll_wave_pulse/unroll_filter, above) would
# be sitting at, for do_init to resume from instead of always cold-starting.
# ---------------------------------------------------------------------------
def _capture_engine_state(sim):
    voices = []
    for x in range(3):
        vs = sim.v[x]
        voices.append(dict(wavepos=vs.wavepos, wavemask=vs.wavemask,
                            currins=vs.currins, currfx=vs.currfx,
                            pendnote=vs.pendnote,
                            fxpos=vs.fxpos,      # B8/B10: fx-program position
                            basepitch=vs.basepitch,  # B10: note*4, the OTHER
                                                      # half of the fx engine's
                                                      # entire runtime state
                            pwidth=vs.pwidth))   # B9: pulse-accumulator phase
    return dict(voices=voices, zp_filtpos=sim.zp_filtpos,
                filt_owner=sim.filt_owner, regs=list(sim.regs))


def _lookup_wave_row(stats, target_pos):
    """positions[k] (see unroll_wave_pulse) is the absolute wavetable
    position BEFORE translated WAVE row k's own frame -- WAVE is always
    exactly 1 row per frame (no RLE), so row index == positions list index,
    with no further lookup needed once a match is found. Returns None if
    target_pos is unreachable from this program's own wave_start (shouldn't
    happen -- the position walk is a deterministic function of fixed table
    bytes, per unroll_wave_pulse's own docstring, so a position genuinely
    visited by the SAME real instrument's real trigger is always reachable)."""
    if not stats:
        return None
    positions = stats.get('positions') or []
    cyc_end = stats.get('prog_len', len(positions))
    for k in range(min(cyc_end, len(positions))):
        if positions[k] == target_pos:
            return k
    return None


def _lookup_filter_row(extra, target_pos):
    """extra['positions'][k] is the absolute filttable position BEFORE
    SOURCE FRAME k's own step; extra['row_frame_start'] maps ranges of
    source frames to the RLE-collapsed translated FILTER row that covers
    them (see unroll_filter). Returns (row_index, frames_already_elapsed_
    into_that_row) or None if target_pos is unreachable (see
    _lookup_wave_row's docstring for why that shouldn't happen)."""
    if not extra:
        return None
    positions = extra['positions']
    rfs = extra['row_frame_start']
    for k, p in enumerate(positions):
        if p == target_pos:
            for r in range(len(rfs) - 1):
                if rfs[r] <= k < rfs[r + 1]:
                    return r, k - rfs[r]
            break
    return None


# ---------------------------------------------------------------------------
# WAVE + PULSE translator (one instrument's ins_wave[i] program)
# ---------------------------------------------------------------------------
_WP_CACHE = {}

# B9: the single ambiguous code in the col1 encoding (see _pulse_col1). An ADD
# whose wavepos-carry-folded delta lands exactly on $80 would be indistinguish-
# able from a SET of 0. Never occurs on either corpus file (measured: 0 of 52
# Fargo / 92 Glyptodont pulse-row x wavemask combinations); asserted rather
# than assumed, so a future file that DID hit it fails loudly instead of
# silently mistranslating one row.
_PW_AMBIGUOUS = 0x80


def _pulse_col1(sim, y_before, wavemask):
    """B9 -- a 1:1 port of lft's own wave/pulse row semantics (player.s lines
    272-317, quoted in docs/players/BLACKBIRD.md's B9 section) into this
    engine's standard 2-column WAVE table.

    Given the wavepos BEFORE a frame, return (is_pulse_row, col1_byte) where
    col1_byte is EXACTLY the byte lft reads from `wavetable+1,y` -- except
    that the ADD path's carry-in (which on real hardware is inherited from the
    preceding `tya; adc #2` wavepos advance, i.e. a function of the HARDWARE
    position y, a quantity the driver's own re-indexed row space does not
    have) is FOLDED into the stored delta at build time. That fold is exact
    because both y and the waveform byte's bit7 are fixed table properties of
    the row, not runtime state.

    Encoding, identical to hardware's:
      bit7 CLEAR -> ACCUMULATE: pwidth += col1
      bit7 SET   -> ABSOLUTE  : pwidth  = (col1 << 1) & $ff   (lft's `asl`)
    """
    y = y_before
    w = sim.wavetable(y)
    if w >= 0xC0:                      # `cmp #$c0; bcs` -> carry set -> +1
        y = (w + y + 1) & 0xFF
        w = sim.wavetable(y)
    d404v = w & wavemask
    shifted, cb7 = _asl(d404v)         # carry out = bit7 of the waveform byte
    if not (shifted & 0x80):           # `bpl nopulse` -- bit6 clear
        return False, 0x00
    _nw, c_from_wp, _ = _adc(y, 2, cb7)   # `tya; adc #2`
    pdelta = sim.wavetable(y + 1)         # `lda wavetable+1,y`
    if pdelta & 0x80:                     # `bmi pwset` -> absolute
        return True, pdelta
    eff = (pdelta + c_from_wp) & 0xFF     # `adc v_pwidth,x`, carry folded in
    if eff == _PW_AMBIGUOUS:
        raise ValueError(
            f"B9 col1 encoding collision at wavepos {y}: ADD delta "
            f"${pdelta:02x} + wavepos-carry {c_from_wp} == $80, which the "
            f"driver would decode as an absolute SET of 0. This never occurs "
            f"on Fargo/Glyptodont; a file that hits it needs a second column "
            f"(or the carry left unfolded) -- see BLACKBIRD.md B9.")
    return True, eff


def unroll_wave_pulse(lay, d, la, ins_restart, ins_restart2, wave_start):
    # Memoized: build_song's fits() grid search calls build_range dozens of
    # times per part, each re-unrolling the SAME instruments from the SAME
    # fixed table bytes. The result is a pure function of wave_start (all
    # other args are fixed for one main() run), so caching is exact, not an
    # approximation -- and it pays for B8's much longer PULSE capture window.
    key = (wave_start, id(d), la)
    hit = _WP_CACHE.get(key)
    if hit is not None:
        return hit
    sim = BlackbirdSim(lay, d, la, [b'', b'', b''], ins_restart, ins_restart2)
    v = sim.v[0]
    v.wavepos = wave_start & 0xFF
    v.wavemask = 0xFF              # gate on (bit6 pulse-row test is mask-invariant
                                    # -- wavemask only ever clears bit0, see BB sim's
                                    # everyframe(): `shifted,_=asl(d404v)`; bit6 of
                                    # d404v is untouched by 0xFE/0xFF masking)
    v.pwidth = 0
    positions, d404s, pulses, col1s = [], [], [], []
    for _ in range(CYCLE_SEARCH_FRAMES):
        positions.append(v.wavepos)
        # B9: resolve THIS frame's pulse op from the pre-frame wavepos, using
        # the same fixed table bytes everyframe() is about to read. Done
        # BEFORE the call so `v.wavepos` is still the pre-frame value.
        col1s.append(_pulse_col1(sim, v.wavepos, v.wavemask))
        sim.everyframe()
        d404s.append(sim.regs[4])
        pulses.append((sim.regs[2], sim.regs[3]))
    cyc_start, cyc_end = _find_cycle(positions)

    # =====================================================================
    # B9: WAVE col0 = waveform, col1 = THE PULSE DELTA -- a 1:1 structural
    # port of lft's own engine (player.s 272-317) rather than a translation
    # of its OUTPUT.
    #
    # WHY (see docs/players/BLACKBIRD.md's B9 section for the full trail):
    # Blackbird's pulse width is an 8-bit ACCUMULATOR fed through the fixed
    # 256-byte `pwprepare` lookup. The DELTAS cycle with the wave program
    # (period 1-10 rows on Glyptodont); the accumulated OUTPUT does not,
    # because each lap drifts the accumulator by a nonzero amount and
    # `pwprepare` is a -16 ramp with wrap discontinuities (index 8 -> 15,
    # 9 -> 254; mirrored about 127/128), i.e. NOT affine. B8 stored the
    # output byte and so had to unroll until the output happened to
    # realign -- which for these instruments never happens inside any
    # capture window (median 1125 PULSETAB rows per Glyptodont instrument,
    # max 1201, to express what Blackbird stores in ONE row). That bloat is
    # what drove Glyptodont's part count and its bundle-cap pressure.
    #
    # The delta belongs in WAVE col1 specifically because that is EXACTLY
    # where lft puts it -- `wavetable` is one interleaved variable-width
    # byte stream where a pulse row is 2 bytes (waveform, then the delta
    # inline) and a non-pulse row is 1 byte, with bit6 of the waveform byte
    # itself as the "this row carries pulse" flag. This engine's WAVE table
    # is 2 columns of 256, one row per frame, so the SAME information lands
    # in col1 of the SAME row -- no new table, no second cursor, and the
    # pulse steps in lockstep with the wave row because it IS the wave row.
    #
    # col1 is genuinely free for Blackbird: this translator has always
    # written 0x00 there (Blackbird wave rows carry no semitone offset --
    # pitch is the separate fx/FM engine), and the only nonzero col1 values
    # ever emitted are jump targets on $7f rows, which wave_step resolves
    # before it can ever be treated as a content row.
    # =====================================================================
    wave_rows = [(d404s[k] & 0xFF, col1s[k][1]) for k in range(cyc_end)]
    wave_rows.append((0x7F, cyc_start))     # relative-to-program-start; the
                                             # builder absolutises it (see
                                             # gen_includes_song, same
                                             # convention as every other
                                             # native driver in this repo)

    # --- SELF-CHECK: replay the DRIVER's own arithmetic over the emitted
    # col1 column and require it to reproduce the validated simulator's
    # $D402/$D403 byte on EVERY frame of the program's unique span. This is
    # what makes B9 exact-by-construction rather than exact-by-hope: if the
    # port were even one carry off, this fires at build time on the first
    # instrument that exercises it, instead of showing up as a few lost
    # percent in a register-trace comparison nobody can attribute.
    acc, cur = 0, 0
    for k in range(cyc_end):
        is_pulse, c1 = col1s[k]
        if is_pulse:
            acc = ((c1 << 1) & 0xFF) if (c1 & 0x80) else ((c1 + acc) & 0xFF)
            cur = sim.pwprepare[acc]
        if cur != (pulses[k][0] & 0xFF) or cur != (pulses[k][1] & 0xFF):
            raise AssertionError(
                f"B9 pulse self-check failed at wave_start={wave_start} "
                f"frame {k}: driver-replay ${cur:02x} vs simulator "
                f"$D402=${pulses[k][0]:02x} $D403=${pulses[k][1]:02x}")

    # PULSE: PULSETAB is DEAD for Blackbird as of B9 -- the pulse engine now
    # lives inside wave_step. Every instrument gets the same bare $7f
    # freeze-only program, which dedups to a single 3-byte PULSETAB entry
    # the driver never reads. Kept (rather than ripped out of the table
    # allocator) so the edit-area address arithmetic is unchanged and this
    # round's numbers isolate the engine change alone.
    pulse_rows = [(0x7F, 0x00, 0x00)]

    # pw_before[k] = the accumulator value BEFORE translated row k runs,
    # starting from 0. Not used for priming (do_init primes PW_ACC from the
    # simulator's own true `v.pwidth` snapshot, which is genuine per-voice
    # runtime state and does not depend on this from-zero replay) -- kept
    # for diagnostics/reporting only.
    pw_before, _a = [], 0
    for k in range(cyc_end):
        pw_before.append(_a)
        is_pulse, c1 = col1s[k]
        if is_pulse:
            _a = ((c1 << 1) & 0xFF) if (c1 & 0x80) else ((c1 + _a) & 0xFF)

    return wave_rows, pulse_rows, dict(
        cycle_start=cyc_start, cycle_len=cyc_end - cyc_start, prog_len=cyc_end,
        positions=positions, pulse_row_frame_start=[0, 0], pulse_flat=True,
        pw_before=pw_before,
        n_pulse_rows=sum(1 for c in col1s[:cyc_end] if c[0]))


# ---------------------------------------------------------------------------
# FILTER translator (one instrument's ins_filt[i] program -- global engine,
# but each flag-$40 instrument restarts it fresh at note-on, so we can
# unroll it per-instrument exactly like WAVE/PULSE).
# ---------------------------------------------------------------------------
def _filter_set_row(mode, cutoff8, res_byte):
    """9Y YY RB set-filter row. Derived by INVERTING romuzak_driver.asm's
    fp_set decode (F_MODE=(byte0>>4&7)<<4; F_CHI=(byte0&0xf)<<4|(byte1>>4);
    F_CLO=byte1<<4; $d417=byte2) with F_CLO forced to 0 (Blackbird's own
    cutoff is a flat 8-bit value with no fractional sub-byte, so there is
    nothing to put in F_CLO's nonzero bits).

    ROUTING BUG FOUND (this session, via the register-trace comparison --
    match rate was stuck at ~43% until this fix): fp_dec's `cmp #$90; bcs
    fp_set` requires byte0's TOP NIBBLE to be >= 9, but fp_set's OWN mode
    extraction (`lsr x4; and #7`) only keeps the LOW 3 bits of that nibble
    -- so byte0's top bit must be forced to 1 (top nibble = 8+mode) for the
    row to actually route to fp_set at all; a first version left bit7
    clear (top nibble = mode, 0-7, always < 9), so EVERY 'SET' row this
    translator emitted was silently decoded as an ADD row instead (0x98 in
    the working romuzak/galway filter-table examples elsewhere in this repo
    IS exactly 0x80 | (1<<4) | ... -- the existing examples already encode
    it correctly; this translator originally didn't). mode=0 has NO valid
    encoding in this row shape (top nibble would need to be 8, still < 9)
    -- clamped up to 1 (documented residual, not expected to matter: mode
    0 means "no SID filter type bit set", audibly close to leaving the
    passband inert)."""
    m = mode & 0x07
    if m == 0:
        m = 1
    b0 = 0x80 | (m << 4) | ((cutoff8 >> 4) & 0x0F)
    b1 = (cutoff8 & 0x0F) << 4
    b2 = res_byte & 0xFF
    return (b0 & 0xFF, b1 & 0xFF, b2)


def _filter_add_row(delta, run):
    """0X XX YY add-to-cutoff row. Inverting fp_dec's decode
    (F_ADHI=(byte0&0xf)<<4|(byte1>>4); F_ADLO=byte1<<4) for F_ADLO=0,
    F_ADHI=delta (an 8-bit signed-as-unsigned per-frame add, matching
    F_CHI's own flat 8-bit resolution -- see module docstring)."""
    delta &= 0xFF
    b0 = (delta >> 4) & 0x0F
    b1 = (delta & 0x0F) << 4
    return (b0, b1, run & 0xFF)


def unroll_filter(lay, d, la, ins_restart, ins_restart2, filt_start):
    sim = BlackbirdSim(lay, d, la, [b'', b'', b''], ins_restart, ins_restart2)
    sim.zp_filtpos = filt_start & 0xFF
    sim.m_cutoff = 0x80             # initroutine: lda #$80; sta m_cutoff
    positions, trace, is_set_step = [], [], []
    for _ in range(CYCLE_SEARCH_FRAMES):
        positions.append(sim.zp_filtpos)
        # Ground truth for THIS source frame's op type, read BEFORE everyframe()
        # mutates state: real player.s's own dispatch (BlackbirdSim.everyframe,
        # "coset: absolute set" vs "add mode") branches on bit7 of the RAW
        # filttable(y+2) byte -- record it directly rather than inferring
        # SET-vs-ADD from the OUTPUT deltas below (see the bug this fixes,
        # named in the comment on the RLE loop).
        is_set_step.append(bool(sim.filttable(sim.zp_filtpos + 2) & 0x80))
        sim.everyframe()
        trace.append((sim.regs[24], sim.regs[23], sim.regs[22]))   # d418,d417,d416
    cyc_start, cyc_end = _find_cycle(positions)
    prefix = trace[:cyc_end]            # the WHOLE first lap, incl. any lead-in
    is_set_prefix = is_set_step[:cyc_end]

    # RLE-collapse into SET (mode/res/cutoff change, OR a genuine hardware SET
    # op) + ADD (same mode/res, per-frame cutoff delta, genuine hardware ADD
    # op) rows, tracking each row's exact starting FRAME index
    # (row_frame_start) so the loop-back target is frame-exact even after
    # collapsing -- a row spanning multiple frames that cyc_start lands inside
    # gets SPLIT so the jump target still lines up on a real frame boundary.
    # (An earlier version approximated this and silently emitted NO loop row
    # at all for the common "position never moves" case -- caught by the
    # register-trace comparison against the simulator, which showed cutoff
    # free-running into garbage after ~250 frames.)
    #
    # REAL BUG FOUND (Glyptodont instrument 16, filt_start=4, this session):
    # this loop used to classify a frame as ADD purely from "cutoff changed by
    # a consistent per-frame delta while (d418,d417) stayed the same" -- with
    # NO way to distinguish, from the OUTPUT alone, a genuine ADD ramp from a
    # composer-authored CHAIN OF INDEPENDENT ABSOLUTE SETS that merely happens
    # to step by a constant amount (a common cutoff-sweep idiom: consecutive
    # `9Y YY RB`-style rows each with a slightly different target, not one
    # `0X XX YY` delta row). Both look byte-identical UNLESS the position
    # loops back onto one of those frames -- a SET is idempotent (repeating it
    # holds steady), an ADD is NOT (repeating it drifts forever). Instrument
    # 16's program self-loops onto exactly this kind of frame (position 10,
    # confirmed via raw filttable dump: bytes $c4/$c3/$c2 at consecutive rows,
    # each independently SET (bit7 of the 3rd byte is set on ALL THREE), not
    # one ramp) -- the old classifier merged the 2nd+3rd frames into an
    # `ADD(delta=-2)` row, and once the self-loop's jump target landed back on
    # it, $D416 drifted downward by 2 every single frame forever (confirmed
    # via a live py65 trace: driver's F_IDX froze at the ADD row while $D416
    # walked 8,6,4,2,0,254,252... never stopping) -- vs. real hardware (and
    # the validated simulator), which holds flat at the steady value forever.
    # Fix: read the ACTUAL per-frame op type from the sim directly
    # (is_set_step, above) instead of inferring it, and never let a SET frame
    # join an ADD run (or vice versa) regardless of how smooth the output
    # looks. A repeated identical SET costs 1 row per source frame (no native
    # "hold" primitive for SET rows, matching real per-row-is-1-frame
    # semantics) -- cheap; every ported file so far has had deep FILTER-table
    # headroom (Glyptodont: 27/256 rows before this fix).
    rows, row_frame_start = [], []
    d418_0, d417_0, d416_0 = prefix[0]
    rows.append(_filter_set_row((d418_0 >> 4) & 0x07, d416_0, d417_0))
    row_frame_start.append(0)
    prev_mode_res = (d418_0, d417_0)
    prev_cutoff = d416_0
    i, n = 1, len(prefix)
    while i < n:
        d418, d417, d416 = prefix[i]
        if is_set_prefix[i] or (d418, d417) != prev_mode_res:
            rows.append(_filter_set_row((d418 >> 4) & 0x07, d416, d417))
            row_frame_start.append(i)
            prev_mode_res = (d418, d417)
            prev_cutoff = d416
            i += 1
            continue
        delta = (d416 - prev_cutoff) & 0xFF
        run = 1
        while i + run < n and not is_set_prefix[i + run]:
            d418b, d417b, d416b = prefix[i + run]
            if (d418b, d417b) != prev_mode_res:
                break
            if ((d416b - prefix[i + run - 1][2]) & 0xFF) != delta:
                break
            run += 1
        rows.append(_filter_add_row(delta, run))
        row_frame_start.append(i)
        prev_cutoff = prefix[i + run - 1][2]
        i += run
    row_frame_start.append(n)              # sentinel: end of the last row's span

    loop_row = 0
    for k in range(len(rows)):
        s, e = row_frame_start[k], row_frame_start[k + 1]
        if s <= cyc_start < e:
            if s == cyc_start:
                loop_row = k
            else:
                b0, b1, _b2 = rows[k]      # multi-frame ADD row -- split at cyc_start
                rows[k] = (b0, b1, cyc_start - s)
                rows.insert(k + 1, (b0, b1, e - cyc_start))
                # B7 (part-boundary priming): keep row_frame_start in sync
                # with the just-inserted split row so a SOURCE-FRAME ->
                # TRANSLATED-ROW lookup (see _lookup_filter_row) still
                # resolves correctly post-split -- row_frame_start was
                # previously left stale here (harmless before B7, since
                # nothing downstream of this point ever re-read it).
                row_frame_start.insert(k + 1, cyc_start)
                loop_row = k + 1
            break
    rows.append((0x7F, 0x00, loop_row))
    # B7: return the position/row-boundary bookkeeping alongside rows so a
    # caller can map a REAL captured zp_filtpos (from the full-song
    # simulator, at an arbitrary part-boundary frame) back to the exact
    # translated FILTER row + in-row frame offset this program would be at,
    # for priming do_init instead of always cold-starting row 0 -- see
    # docs/players/BLACKBIRD.md's "B7" section / _lookup_filter_row.
    extra = dict(positions=list(positions[:cyc_end]), row_frame_start=row_frame_start,
                 rows=list(rows), cyc_start=cyc_start, cyc_end=cyc_end)
    return rows, extra


# ---------------------------------------------------------------------------
# B10: fx/PITCH program translation -- there isn't any.
#
# B9 replaced PULSE's stored recording with lft's own accumulator; B10 does
# the identical move for PITCH, and the consequence is that this file no
# longer TRANSLATES the pitch engine at all. The driver runs lft's
# `everyframe` interpolator (player.s 207-271) over lft's own fxtable and
# freq_lsb/freq_msb bytes, copied verbatim, so all that is left here is:
#
#   * hand the driver the fxtable bytes (emit_fxtab, below),
#   * hand it fx_start (the per-fx-program entry positions) as the $c0-$ff
#     command table, and
#   * ASSERT, frame by frame, that the driver's own arithmetic over the
#     bytes we actually emit reproduces the validated simulator's $D400/1.
#
# What this deletes is the note-dependence. The old unroll_fm() stored a
# per-frame ABSOLUTE FREQUENCY OFFSET sequence, which is note-dependent
# (the frequency table is exponential, so the same arp program is a
# different Hz offset at every pitch) -- so every (fx-program, note) PAIR
# needed its own command slot: 80 for Fargo and 423 for Glyptodont, against
# a 64-slot cap. An fx INDEX is note-independent, so the slot count is just
# the file's own `nfx` (35 / 47), both under the cap, and the greedy
# nearest-merge clustering that used to burn 16 and 359 slots respectively
# is not merely reduced but removed: cluster_bundles is gone.
# ---------------------------------------------------------------------------
FXTAB_LEN = 257          # 256 addressable positions + the one guard byte
                          # fx_step's `FXTAB+1,y` peek can reach at y=$ff


def fx_table_info(lay, d, la):
    """(nfx, fx_start, fxtab_bytes) for this song, read straight out of the
    located tables.

    nfx is the note-INDEPENDENT distinct-fx-program count, derived exactly as
    BlackbirdSim does (filttable immediately follows fx_start[nfx], per the
    memory layout in docs/players/BLACKBIRD.md). fx_start[i-1] is the FXTAB
    position Blackbird's fx program `i` begins at -- lft's `lda fx_start-1,y`
    in execute(); program 0 is "no program", which does NOT reposition the
    running fxpos."""
    nfx = lay.filttable - lay.fx_start
    off = lay.fx_start - la
    fx_start = list(d[off:off + nfx])
    fo = lay.fxtable - la
    fxtab = bytes(d[fo:fo + FXTAB_LEN])
    if len(fxtab) < FXTAB_LEN:
        fxtab = fxtab + bytes(FXTAB_LEN - len(fxtab))
    return nfx, fx_start, fxtab


def _fx_frame(freqblob, fxtab, fxpos, basepitch):
    """Replay ONE frame of the DRIVER's fx_step (blackbird_driver.asm), in
    Python, reading ONLY the bytes this build actually emits -- `fxtab` is
    the emitted FXTAB blob and `freqblob` the emitted FREQBLOB, indexed
    through the driver's own label arithmetic (freq_lsb = FREQBLOB+96 etc).

    That is the point: this is not a paraphrase of the simulator (which
    would make verify_fx_engine a tautology), it is a model of the ASM
    against the EMITTED TABLES. A truncated FXTAB, a wrong FREQBLOB label
    offset, or a blob too short for `freq_lsb+24,y` at y=127 all fail here
    -- with an IndexError or a value mismatch -- instead of costing a few
    unattributable percent in the register trace.

    Returns (new_fxpos, d400, d401)."""
    def L(i):
        return freqblob[FREQ_LSB_REL + i]

    def M(i):
        return freqblob[FREQ_MSB_REL + i]

    row1 = fxtab[fxpos + 1]                  # peek: bit7 => relative jump
    a = row1 if (row1 & 0x80) else 0
    new_fxpos = (fxpos + a + 1) & 0xFF       # `sec; adc FXPOS,x`
    s = fxtab[fxpos]                         # value read from the OLD position
    if s == 0:
        return new_fxpos, 0xFF, 0xFF         # fixedfreq: $ff to BOTH registers
    t, cout, _ = _adc(s, basepitch, 0)       # clc; adc BASEPITCH,x
    a3, c_bit0 = _ror(t, 1 if cout else 0)
    a4, c_bit1 = _lsr(a3)
    y = a4
    if c_bit0 == 0:
        if c_bit1:                           # mode 10: +12/+13, carry-in 1
            lsb, cl, _ = _adc(L(y + 12), L(y + 13), 1)
            msb, _, _ = _adc(M(y + 12), M(y + 13), cl)
        else:                                # mode 00: direct, no add
            lsb, msb = L(y + 24), M(y + 24)
    else:
        if c_bit1:                           # mode 11: +0/+20, carry-in 1
            lsb, cl, _ = _adc(L(y), L(y + 20), 1)
            msb, _, _ = _adc(M(y), M(y + 20), cl)
        else:                                # mode 01: +19/+1, carry-in 0
            lsb, cl, _ = _adc(L(y + 19), L(y + 1), 0)
            msb, _, _ = _adc(M(y + 19), M(y + 1), cl)
    return new_fxpos, lsb & 0xFF, msb & 0xFF


def verify_fx_engine(lay, d, la, ins_restart, ins_restart2, freqblob, fxtab,
                     fx_start, notes, frames=300):
    """B10's exact-by-construction gate (B9's discipline, applied to pitch).

    For EVERY (fx program, note) combination the song can actually produce,
    replay `frames` frames of _fx_frame -- the driver model over the emitted
    tables -- against the validated simulator's own $D400/$D401 for the same
    seeded state, and raise on the first byte that differs.

    Note the asymmetry that makes this worth running: the simulator reads the
    raw SID image through its own absolute addresses and has no length limit,
    while _fx_frame reads the finite blobs this build emits. So the check
    genuinely proves the EMITTED data is sufficient and correctly located,
    which is the part that can be wrong.

    Notes are swept over the full range the sequence column can carry, not
    just the ones this window happens to use, so a part-splitting decision
    can never move the build onto an unverified (fx, note) pair."""
    checked = 0
    for fx in range(0, len(fx_start) + 1):
        start = 0 if fx == 0 else (fx_start[fx - 1] & 0xFF)
        for note in notes:
            sim = BlackbirdSim(lay, d, la, [b'', b'', b''],
                               ins_restart, ins_restart2)
            v = sim.v[0]
            v.fxpos = start
            v.basepitch = (note << 2) & 0xFF
            pos = start
            for f in range(frames):
                pos, dlo, dhi = _fx_frame(freqblob, fxtab, pos,
                                          (note << 2) & 0xFF)
                sim.everyframe()
                if (dlo, dhi) != (sim.regs[0], sim.regs[1]):
                    raise ValueError(
                        f"B10 fx-engine self-check FAILED: fx={fx} "
                        f"note={note} frame={f}: driver model wrote "
                        f"${dlo:02x}/${dhi:02x}, validated simulator wrote "
                        f"${sim.regs[0]:02x}/${sim.regs[1]:02x}")
                if pos != v.fxpos:
                    raise ValueError(
                        f"B10 fx-engine self-check FAILED: fx={fx} "
                        f"note={note} frame={f}: FXPOS diverged "
                        f"({pos} vs simulator {v.fxpos})")
                checked += 1
    return checked




# ---------------------------------------------------------------------------
# Row builder: BBStep list -> D11Row list, with note/instrument/command
# columns. Command changes only emitted on genuine change, matching the
# existing instrument-column convention.
#
# B10: the command column IS Blackbird's own fx-program number now, with no
# lookup table in between -- it used to be a per-(fx, note, instrument)
# bundle index, which is what made the vocabulary explode past the 64-slot
# cap. The identity mapping is asserted safe by build_range (nfx < NFM).
# ---------------------------------------------------------------------------
def steps_to_rows_native(steps):
    """B11: fx-select changes must land on the row they actually occur on, not
    just on the next note. On hardware, prepare1 (player.s:98-100) writes
    v_pendfx DIRECTLY from a fresh $c9-$f8 select byte on ANY row -- note,
    rest, or sustain -- and execute() applies it that SAME tick, independent
    of prepare3's separate note-triggered mirror. bb_steps_for_voice already
    carries the correct sticky `cur_fx` on every step kind (rest/tie included,
    see its docstring); the bug was here: `cur_cmd` used to only update in the
    note branch, so a fx-change that occurred while the voice was resting or
    sustaining was silently dropped from the emitted sequence until whatever
    note came next (measured: 27% of Fargo's fx changes, 7% of Glyptodont's,
    landed on such a row). The driver's own `maybe_fx_commit` (blackbird_
    driver.asm, B11) is the matching runtime-side half of this fix -- it
    commits a fresh command on rest/sustain rows immediately instead of
    waiting for pn_tied's note-triggered commit.

    B12: instrument changes need the SAME treatment, for the SAME reason.
    bb_steps_for_voice (see its docstring) now attaches pending_instr to
    whatever event immediately follows an instrument-select -- note OR
    rest/hold -- since that pairing is always same-tick on hardware. This
    function used to only ever emit `instrument=` inside the real-note
    branch; a change landing on a rest/hold step was silently dropped from
    the emitted sequence, exactly like B11's fx bug. The driver's matching
    fix (set_instr_v in blackbird_driver.asm) commits the WAVE/FILTER/GATE
    restart immediately when the command byte is parsed instead of
    deferring it to pn_note."""
    rows = []
    cur_instr = None
    cur_cmd = None
    for s in steps:
        n = max(1, s.ticks)
        cmd = s.fx & 0x3F        # B10: the fx index IS the command index
        cmdcol = None
        if cmd != cur_cmd:
            cmdcol = cmd
            cur_cmd = cmd
        inst = None
        if s.instrument is not None and s.instrument != cur_instr:
            inst = s.instrument
            cur_instr = s.instrument
        if s.kind == 'rest':
            rows.append(D11Row(note=SF2_GATE_OFF, instrument=inst, command=cmdcol))
            rows.extend(D11Row(note=SF2_GATE_OFF) for _ in range(n - 1))
        elif s.kind == 'note' and s.note is None:
            rows.append(D11Row(note=SF2_GATE_ON, instrument=inst, command=cmdcol))
            rows.extend(D11Row(note=SF2_GATE_ON) for _ in range(n - 1))
        else:
            note = max(SF2_NOTE_MIN, min(s.note + SF2_NOTE_OFS, SF2_NOTE_MAX))
            rows.append(D11Row(note=note, instrument=inst, command=cmdcol,
                                tie=s.tie))
            rows.extend(D11Row(note=SF2_GATE_ON) for _ in range(n - 1))
    if not rows:
        rows = [D11Row(note=SF2_GATE_OFF)]
    return rows


# ---------------------------------------------------------------------------
# B3: row-indexed tempo schedule. Fargo alone has 22 real mid-song tempo/
# groove OOB records (BLACKBIRD.md's tempo section); B2 only modelled the
# FIRST one as a compile-time constant pair. This re-derives the FULL
# schedule, tagged with the exact ROW (tick) index each record takes effect
# at, by re-running the SAME validated simulator used everywhere else in this
# module (bin/blackbird_everyframe_sim.py) as the formula oracle -- not a
# hand re-derivation. Row index = the simulator's own execute()-call count,
# which IS Blackbird's tick grid (one execute() per do_row on the native
# driver side too -- see blackbird_driver.asm's ROW_CNT declaration), so no
# rescaling is needed between "row index here" and "ROW_CNT there".
#
# Uses find_tempo_records() (the RAW (b1,b2) OOB byte pairs, in stream order)
# to seed a THROWAWAY BlackbirdSim's tempo_debug queue, driven by the SAME
# real per-voice decoded streams as every other translator in this module
# (OOB detection timing depends on the actual note content, not just the
# tempo bytes) -- then just watches when the sim's execute() consumes each
# queued record. Immediately after that happens, sim.zp_master holds the
# value just committed for THIS row (the "long"/b1 side) and sim.zp_tempo
# holds the value XORed in for the NEXT row (the "short"/b1^b2 side) --
# see BlackbirdSim.execute()'s own tail (zp_master=zp_tempo THEN
# m_groove_apply() mutates zp_tempo) -- so reading both right after the call
# gives the full alternating pair with no re-derivation of the XOR math.
# ---------------------------------------------------------------------------
TEMPO_SCHED_CAP = 64        # matches the FM/PULSE bundle 64-slot convention;
                             # X-register indexed on the driver side, so this
                             # is also a hard ceiling, not just a style choice.


def extract_tempo_schedule(lay, d, la, ins_restart, ins_restart2, streams,
                            max_rows=20000):
    import blackbird_everyframe_sim as sim_mod
    tempo_records = sim_mod.find_tempo_records(lay, d, la)
    sim = sim_mod.BlackbirdSim(lay, d, la, streams, ins_restart, ins_restart2,
                                tempo_debug=list(tempo_records))
    schedule = []
    prev_len = len(sim.tempo_debug)
    row = 0
    for _ in range(max_rows):
        will_exec = (sim.zp_master == 0)
        sim.real_frame()
        if will_exec:
            row += 1
        if len(sim.tempo_debug) != prev_len:
            long_frames = max(1, min(255, sim.zp_master // 7 + 1))
            short_frames = max(1, min(255, sim.zp_tempo // 7 + 1))
            # 4th field (real frame_no) is reporting-only, for main()'s extended
            # comparison window -- write_tempo_schedule() only consumes the
            # first 3 (the driver only ever sees ROW indices, never real frames).
            schedule.append((row, long_frames, short_frames, sim.frame_no))
            prev_len = len(sim.tempo_debug)
        if not sim.tempo_debug:
            break
    if len(schedule) > TEMPO_SCHED_CAP:
        raise ValueError(
            f"tempo schedule overflow: {len(schedule)} entries > "
            f"{TEMPO_SCHED_CAP} (X-register-indexed table cap)")
    return schedule


def write_tempo_schedule(schedule):
    """tempo_sched_row_{lo,hi}.inc (16-bit row index, LE) + tempo_sched_t1/t2
    .inc (already-converted //7+1 frame counts) -- consumed by do_row's
    schedule-check block in blackbird_driver.asm. Empty schedule -> empty
    (zero .byte lines) files; TEMPO_SCHED_LEN=0 in layout.inc means do_row's
    `cpx #TEMPO_SCHED_LEN; bcs sk_sched` skips before ever indexing them."""
    def hexbytes(vals):
        return ", ".join(f"${v & 0xFF:02x}" for v in vals)

    row_lo = [r & 0xFF for r, _, _, _ in schedule]
    row_hi = [(r >> 8) & 0xFF for r, _, _, _ in schedule]
    t1 = [t for _, t, _, _ in schedule]
    t2 = [t for _, _, t, _ in schedule]
    for name, vals in (("tempo_sched_row_lo.inc", row_lo),
                        ("tempo_sched_row_hi.inc", row_hi),
                        ("tempo_sched_t1.inc", t1),
                        ("tempo_sched_t2.inc", t2)):
        with open(os.path.join(ROOT, "drivers_src", "blackbird", name), "w") as f:
            f.write("; auto-generated (native song) by build_blackbird_native_song.py's "
                     "extract_tempo_schedule()\n")
            if vals:
                f.write("        .byte " + hexbytes(vals) + "\n")
    return len(schedule)


# ---------------------------------------------------------------------------
# B6 (part-splitting): ONE full-song simulator pass, the single source of
# ground truth every part's own build/validation needs -- avoids re-running
# the sim once per part (a part's window is a SLICE of this, not a fresh
# derivation).
# ---------------------------------------------------------------------------
def run_full_song_sim(lay, d, la, ins_restart, ins_restart2, streams, total_rows):
    """(frames, row_frame, schedule, row_state):
      - frames: the full frame-by-frame $D400-$D418 trace from real frame 0,
        same list shape compare()'s sim_frames already produces -- sliceable
        per part instead of re-simulating per part.
      - row_frame[r] = the 0-based index into `frames` at which row r's
        committed state FIRST appears (row 0 = do_init's own state, visible
        from frame index 0) -- lets a part starting at song-row row0 find the
        correct real-frame OFFSET into the ORIGINAL performance to compare
        its own (always frame-0-based) driver trace against.
      - schedule: the full row-indexed tempo/groove history, SAME technique
        and (row, long, short, frame) shape as extract_tempo_schedule (folded
        into this same pass instead of a second sim run -- identical
        row/frame bookkeeping).
      - row_state[r] (B7, part-boundary priming): the REAL per-voice/global
        engine state (see _capture_engine_state) captured right as row r
        begins -- specifically AFTER row r's own note/instrument commit
        (execute(), if this frame is a tick boundary) but BEFORE this SAME
        frame's everyframe() has stepped wave/pulse/fx/filter forward. This
        is exactly the state a part starting at row0=r needs to prime its
        own do_init with so its own frame-0 everyframe() call reproduces the
        SAME output real hardware would show continuing past this point,
        instead of do_init's flat zeroed cold-start defaults (which are only
        genuinely correct at row 0, the song's own true start -- see
        build_range's use of this via BlackbirdSim's snapshot_cb hook).
        row_state[0] is captured from the sim's OWN pristine __init__ state
        (before any real_frame() call), which is BY CONSTRUCTION identical
        to do_init's existing cold-start defaults -- so priming naturally
        no-ops for any part starting at row0==0 (see docs/players/
        BLACKBIRD.md's "B7" section for the verification that confirms this).
    """
    import blackbird_everyframe_sim as sim_mod
    tempo_records = sim_mod.find_tempo_records(lay, d, la)
    snap_holder = {}

    def _snap(s):
        snap_holder['v'] = _capture_engine_state(s)

    sim = sim_mod.BlackbirdSim(lay, d, la, streams, ins_restart, ins_restart2,
                                tempo_debug=list(tempo_records), snapshot_cb=_snap)
    frames, row_frame, schedule = [], [0], []
    row_state = [_capture_engine_state(sim)]
    prev_len = len(sim.tempo_debug)
    row, f = 0, 0
    max_frames = max(20000, total_rows * 12)   # generous: real frames/tick is
                                                # never observed >7 in this corpus
    while row <= total_rows and f < max_frames:
        will_exec = (sim.zp_master == 0)
        frames.append(sim.real_frame())
        if will_exec:
            row += 1
            row_frame.append(f)
            row_state.append(snap_holder['v'])
        if len(sim.tempo_debug) != prev_len:
            long_frames = max(1, min(255, sim.zp_master // 7 + 1))
            short_frames = max(1, min(255, sim.zp_tempo // 7 + 1))
            schedule.append((row, long_frames, short_frames, f))
            prev_len = len(sim.tempo_debug)
        f += 1
    return frames, row_frame, schedule, row_state


def tempo_at_row(schedule, opening_pair, row0):
    """(long,short) tick-frame pair active AT row0 (the last schedule record
    with row<=row0), else the song's own genuine opening pair (row0==0, or
    row0 earlier than the first record)."""
    active = opening_pair
    for r, lf, sf, _f in schedule:
        if r <= row0:
            active = (lf, sf)
        else:
            break
    return active


def window_tempo_schedule(schedule, row0, row1):
    """Row-shift the full-song schedule onto a part's own row-0-relative
    grid, keeping only records strictly inside (row0, row1) -- a record AT
    row0 itself is already folded into the part's opening pair by
    tempo_at_row (re-applying it at the part's own row 0 would be a spurious
    double-apply of the same tempo change)."""
    return [(r - row0, lf, sf, f) for (r, lf, sf, f) in schedule
            if row0 < r < row1]


# ---------------------------------------------------------------------------
# Native edit-area layout writer (mirrors build_romuzak_native_song's
# gen_includes_song, trimmed to the bundles-only path -- Blackbird B1 has no
# drum/SEEK instrument flags, so those branches are dropped).
# ---------------------------------------------------------------------------
def gen_includes_song(segs, ad_sr, wave_programs, filter_programs,
                      filter_flag_of, fx_start, fxtab, default_filter_program,
                      multispeed=1, tempo_sched_len=0,
                      default_wave_program=None, pulse_programs=None):
    gen = SF2HeaderGenerator()
    gen.DRIVER_INIT, gen.DRIVER_PLAY, gen.DRIVER_STOP = B.DRV_INIT, B.DRV_PLAY, B.DRV_STOP
    gen.PLAYER_ADDRESSES = dict(gen.PLAYER_ADDRESSES)
    gen.PLAYER_ADDRESSES["driver_state"] = 0x16D0
    gen.PLAYER_ADDRESSES["tempo_counter"] = 0x16D1
    gen.driver_name = "Blackbird"
    gen.driver_version_major = 17
    gen.driver_version_minor = 0
    gen.driver_code_top = 0x1000
    vstreams = [bytes([0x01]) + bytes([0xA0, 0x01]) * (len(segs[v]) - 1)
                for v in range(3)]
    edit, mdp = placeholder_edit_area.build_placeholder_edit_area(
        B.EDIT_BASE, gen, voice_streams=vstreams)
    edit = bytearray(edit)
    seq0 = mdp['seq00_addr']
    off = 0
    for v in range(3):
        for s, pk in enumerate(segs[v]):
            o = (seq0 + (off + s) * 0x100) - B.EDIT_BASE
            edit[o:o + len(pk)] = pk
        off += len(segs[v])
    io = gen.instr_addr - B.EDIT_BASE
    wo, po, fo = B.relocate_driver_tables(gen, edit)

    # FILTER (col-major 256x3, deduped). Row 0 is ALWAYS Blackbird's own
    # genuine startup walk (zp_filtpos=0 in the real player, never touched
    # by any instrument whose ins_filt==0 -- see the do_init comment in
    # blackbird_driver.asm for why this must be a real translated program,
    # not an arbitrary/unrelated instrument's block) -- written first so it
    # lands at filt_cursor==0 deterministically; FILT_INIT_ROW in layout.inc
    # always reads 0 as a result, kept as an explicit symbol (not a bare
    # #$00 in the asm) so this invariant is visible/checkable, not implicit.
    # B3 BUG FOUND (via Glyptodont's register-trace comparison, whose default
    # program's jump row exposed it -- Fargo's default program happened to be
    # a degenerate always-same-value cycle where the wrong target and the
    # right one produce the SAME steady-state $D416/7/8 bytes, so it never
    # showed up there): this block used `(r + b2)` for the $7f jump row's
    # absolute target instead of `(default_start + b2)` (matching the
    # per-instrument block below, which correctly uses `start + b2` -- see
    # its own comment). default_start is always 0 here (this block runs
    # FIRST, before filt_cursor advances), so the fix is `(default_start +
    # b2)` = `b2` alone -- NOT `r` (the row's own local index), which was
    # being added on top by mistake. For a 2-row program (SET + jump-to-
    # row-0), the old formula computed target=1 (r=1, b2=0) -- equal to the
    # jump row's OWN index -- which fp_read's `cmp tmpf; beq fp_freeze`
    # (blackbird_driver.asm) treats as an intentional self-freeze, so
    # Fargo's identical-shaped default program still froze at the CORRECT
    # steady value by coincidence. Glyptodont's default program is the same
    # 2-row shape too, so this alone wasn't Glyptodont's story either -- but
    # any LONGER default program (more than 2 rows) would have jumped to
    # entirely the wrong row. Fixed for correctness regardless.
    default_start = 0
    filt_cursor, filt_dedup = 0, {}
    fo_ = fo
    for r, (b0, b1, b2) in enumerate(default_filter_program):
        edit[fo_ + 0 * 256 + r] = b0 & 0xFF
        edit[fo_ + 1 * 256 + r] = b1 & 0xFF
        edit[fo_ + 2 * 256 + r] = ((default_start + b2) if (b0 & 0xFF) == 0x7F else b2) & 0xFF
    filt_init_row = 0
    filt_cursor = len(default_filter_program)
    filt_dedup[tuple(default_filter_program)] = 0
    for i in range(min(len(ad_sr), 32)):
        fprog = filter_programs.get(i)
        if fprog:
            fkey = tuple(fprog)
            if fkey in filt_dedup:
                edit[io + 3 * 32 + i] = filt_dedup[fkey] & 0xFF
            else:
                start = filt_cursor
                for r, (b0, b1, b2) in enumerate(fprog):
                    edit[fo + 0 * 256 + start + r] = b0 & 0xFF
                    edit[fo + 1 * 256 + start + r] = b1 & 0xFF
                    edit[fo + 2 * 256 + start + r] = (
                        (start + b2) if (b0 & 0xFF) == 0x7F else b2) & 0xFF
                edit[io + 3 * 32 + i] = start & 0xFF
                filt_dedup[fkey] = start
                filt_cursor += len(fprog)
                if filt_cursor > 256:
                    raise ValueError(f"FILTER overflow: {filt_cursor} rows > 256")

    # WAVE (col-major 256x2, deduped)
    #
    # B8: row 0 is now ALWAYS Blackbird's own genuine `wavepos == 0` startup
    # program -- the exact structural analogue of the FILTER block above, and
    # for the same reason. Real hardware's wave engine runs CONTINUOUSLY from
    # frame 0 on all three voices (everyframe() is unconditional and
    # `vs.wavepos` starts at 0), so before a voice's FIRST note the default
    # program is already stepping and already writing $D404 and (via its
    # bit6 pulse rows) $D402/3. do_init previously pointed VWI/PPTR at
    # whatever program happened to land at table row 0 / bundle 0, which is
    # an unrelated instrument's program -- see the B8 report for the measured
    # consequence on PULSE specifically.
    wave_cursor, wave_dedup = 0, {}
    wave_init_row = 0
    if default_wave_program:
        for r, (c0, c1) in enumerate(default_wave_program):
            edit[wo + 0 * 256 + r] = c0 & 0xFF
            edit[wo + 1 * 256 + r] = ((0 + c1) if c0 == 0x7F else c1) & 0xFF
        wave_cursor = len(default_wave_program)
        wave_dedup[tuple(default_wave_program)] = 0
    for i, (ad, sr) in enumerate(ad_sr[:32]):
        edit[io + 0 * 32 + i] = ad
        edit[io + 1 * 32 + i] = sr
        fb = 0x40 if filter_flag_of.get(i) else 0
        edit[io + 2 * 32 + i] = fb
        wp = wave_programs.get(i) or [(0x41, 0x00), (0x7F, 0)]
        wkey = tuple(wp)
        if wkey in wave_dedup:
            edit[io + 5 * 32 + i] = wave_dedup[wkey] & 0xFF
            continue
        start = wave_cursor
        for r, (c0, c1) in enumerate(wp):
            edit[wo + 0 * 256 + start + r] = c0 & 0xFF
            edit[wo + 1 * 256 + start + r] = ((start + c1) if c0 == 0x7F else c1) & 0xFF
        edit[io + 5 * 32 + i] = start & 0xFF
        wave_dedup[wkey] = start
        wave_cursor += len(wp)
        if wave_cursor > 256:
            raise ValueError(f"WAVE overflow: {wave_cursor} rows > 256")

    # B10: the $c0-$ff command tables. These keep B8/B9's ADDRESSES exactly
    # (so nothing downstream of them moves), but their CONTENT changed
    # meaning entirely: what used to be a per-bundle 16-bit FMTAB pointer
    # pair (IFM_LO/IFM_HI) is now two independent 8-bit tables --
    #   FXSTART[i] = the FXTAB position Blackbird's fx program i starts at,
    #   FXRST[i]   = whether a note-on repositions FXPOS at all (0 for fx 0,
    #                which lft's execute() deliberately leaves running).
    # The index is Blackbird's own fx number, so no per-song mapping table,
    # no clustering, and no note in the key.
    fxstart_addr = gen.filter_addr + 3 * 256
    fxrst_addr = fxstart_addr + NFM
    ipulse_lo_addr = fxrst_addr + NFM
    ipulse_hi_addr = ipulse_lo_addr + NFM
    fxtab_addr = ipulse_hi_addr + NFM

    pdedup, pulsetab_tmp = {}, bytearray()
    pulsetab_addr = fxtab_addr + FXTAB_LEN

    def _emit_pulse(pp):
        pk = tuple(pp)
        if pk not in pdedup:
            pdedup[pk] = pulsetab_addr + len(pulsetab_tmp)
            for c0, c1, c2 in pp:
                pulsetab_tmp.extend(bytes([c0 & 0xFF, c1 & 0xFF,
                                           0 if (c0 & 0xFF) == 0x7F else (c2 & 0xFF)]))
        return pdedup[pk]

    # B8: PULSE programs are now per-INSTRUMENT (see blackbird_driver.asm's
    # set_instr_v / pr_setprog comments), not per-bundle -- so this array is
    # indexed by instrument row, not by the $c0-$ff command index. It keeps
    # its NFM-sized allocation (64 >= 32 instruments) purely so no other
    # table address moves.
    pulse_programs = pulse_programs or {}
    instr_pulse_addr = [None] * 32
    _flat = [(0x7F, 0x00, 0x00)]
    for i in range(min(len(ad_sr), 32)):
        instr_pulse_addr[i] = _emit_pulse(pulse_programs.get(i) or _flat)
    pulsetab = bytes(pulsetab_tmp)
    need = pulsetab_addr + len(pulsetab) - B.EDIT_BASE
    if len(edit) < need:
        edit.extend(bytearray(need - len(edit)))
    for i in range(NFM):
        # fx program i: start position + "does a note reposition it" flag.
        # i == 0 is Blackbird's fx 0 -- no program, no reposition.
        if 1 <= i <= len(fx_start):
            edit[(fxstart_addr - B.EDIT_BASE) + i] = fx_start[i - 1] & 0xFF
            edit[(fxrst_addr - B.EDIT_BASE) + i] = 1
        else:
            edit[(fxstart_addr - B.EDIT_BASE) + i] = 0
            edit[(fxrst_addr - B.EDIT_BASE) + i] = 0
        pa = instr_pulse_addr[i] if i < 32 and instr_pulse_addr[i] is not None             else pulsetab_addr
        edit[(ipulse_lo_addr - B.EDIT_BASE) + i] = pa & 0xFF
        edit[(ipulse_hi_addr - B.EDIT_BASE) + i] = (pa >> 8) & 0xFF
    edit[fxtab_addr - B.EDIT_BASE:fxtab_addr - B.EDIT_BASE + FXTAB_LEN] = fxtab
    edit[pulsetab_addr - B.EDIT_BASE:pulsetab_addr - B.EDIT_BASE + len(pulsetab)] = pulsetab

    with open(os.path.join(ROOT, "drivers_src", "blackbird", "layout.inc"), "w") as f:
        f.write("; auto-generated (native song) by build_blackbird_native_song.py\n")
        for v in range(3):
            f.write(f"SEQ{v}  = ${seq0 + v * 0x100:04x}\n")
            f.write(f"OL{v}   = ${mdp['ol_track1_addr'] + v * mdp['ol_size']:04x}\n")
        f.write(f"SEQPTRLO = ${mdp['seq_ptr_lo_addr']:04x}\n")
        f.write(f"SEQPTRHI = ${mdp['seq_ptr_hi_addr']:04x}\n")
        f.write(f"TEMPO = {B.TEMPO}\n")
        f.write(f"TEMPO2 = {getattr(B, 'TEMPO2', None) or B.TEMPO}\n")
        f.write(f"TEMPO_SCHED_LEN = {tempo_sched_len}\n")   # B3: row-indexed
                                                              # mid-song tempo changes
        f.write(f"INSTR = ${gen.instr_addr:04x}\n")
        f.write(f"WAVE  = ${gen.wave_addr:04x}\n")
        f.write(f"PULSE = ${gen.pulse_addr:04x}\n")
        f.write(f"FILTER = ${gen.filter_addr:04x}\n")
        # B10: FXTAB is Blackbird's own fxtable, verbatim; FXSTART/FXRST are
        # the $c0-$ff command tables (fx index -> start position / reset
        # flag). FMTAB/IFM_LO/IFM_HI are gone with the FM engine.
        f.write(f"FXTAB = ${fxtab_addr:04x}\n")
        f.write(f"FXSTART = ${fxstart_addr:04x}\n")
        f.write(f"FXRST = ${fxrst_addr:04x}\n")
        f.write(f"NOTE_OFS = {SF2_NOTE_OFS}\n")   # Stage A's pitch calibration,
                                                   # emitted from the SAME constant
                                                   # steps_to_rows_native applies
        f.write(f"PULSETAB = ${pulsetab_addr:04x}\n")
        f.write(f"IPULSE_LO = ${ipulse_lo_addr:04x}\n")
        f.write(f"IPULSE_HI = ${ipulse_hi_addr:04x}\n")
        # B8: the SAME two arrays, but instrument-indexed rather than
        # command-indexed (see blackbird_driver.asm's set_instr_v).
        f.write(f"INSTR_PUL_LO = ${ipulse_lo_addr:04x}\n")
        f.write(f"INSTR_PUL_HI = ${ipulse_hi_addr:04x}\n")
        f.write(f"MULTISPEED = {max(1, int(multispeed))}\n")
        f.write(f"FILT_INIT_ROW = {filt_init_row}\n")
        f.write(f"WAVE_INIT_ROW = {wave_init_row}\n")   # B8: default wave program
    return gen, bytes(edit), mdp, seq0, dict(wave_init_row=wave_init_row)


# B10 (was B9's _PWPREPARE_REF): the reference FREQBLOB bytes, captured on
# first emission and cross-checked on every later file. The RE established
# this whole region is baked identically into every v1.2-exact rip (fixed
# template offsets, not relocated, not composer data) -- this ASSERTS that
# per build rather than trusting it, which is the only way the claim stays
# true for file 3..11. B9 asserted it for pwprepare alone; B10 extends the
# same guard to the freq tables it now also embeds.
_FREQBLOB_REF = None

# Fixed template offsets, confirmed against player.s's own declaration order
# (freq_msb -> freq_lsb -> pwprepare) and its "tables overlap with 15 bytes"
# comment: freq_msb is 96 bytes at 817, freq_lsb 111 bytes at 913, pwprepare
# 256 bytes at 1024. 1024 is exactly 817+96+111, so the three are contiguous
# and the blob is a single slice.
FREQBLOB_OFF, FREQBLOB_LEN = 817, 463
FREQ_MSB_REL, FREQ_LSB_REL, PWPREPARE_REL = 0, 96, 207


def write_freqblob(sim, d, po):
    """freqblob.inc -- the contiguous freq_msb/freq_lsb/pwprepare region read
    straight out of THIS file's own loaded play-data template.

    Emitted as ONE blob rather than three tables because fx_step's indexed
    reads deliberately run past each table's nominal extent (see the driver's
    FREQBLOB comment). B9's separate pwprepare.inc is folded in here -- the
    slice at PWPREPARE_REL is asserted below to be byte-identical to what
    BlackbirdSim itself read at offset 1024, so unifying them cannot silently
    change the pulse behaviour B9 verified.

    pwprepare's shape, for the record (measured, kept from B9's note): a
    descending -16 ramp with WRAP discontinuities every ~17 entries, plus
    plateaus, mirrored about 127/128 (`pw[i] == pw[255-i]` for all i; min 8
    at index 126-129, max 254)."""
    global _FREQBLOB_REF
    blob = list(d[po + FREQBLOB_OFF:po + FREQBLOB_OFF + FREQBLOB_LEN])
    if len(blob) != FREQBLOB_LEN:
        raise ValueError(f"freqblob: expected {FREQBLOB_LEN} bytes, got {len(blob)}")
    # B9's own invariant, re-asserted through the new unified path.
    if blob[PWPREPARE_REL:PWPREPARE_REL + 256] != list(sim.pwprepare):
        raise ValueError(
            "freqblob's pwprepare slice differs from the bytes BlackbirdSim "
            "read at template offset 1024 -- the unified blob is NOT a "
            "faithful superset of B9's table.")
    if _FREQBLOB_REF is None:
        _FREQBLOB_REF = blob
    elif blob != _FREQBLOB_REF:
        raise ValueError(
            "freqblob differs between files -- the 'byte-identical across "
            "every v1.2-exact rip' invariant this driver relies on is FALSE "
            "for this file; the region would have to become per-song data.")
    with open(os.path.join(ROOT, "drivers_src", "blackbird", "freqblob.inc"), "w") as f:
        f.write("; B10: Blackbird's contiguous freq_msb + freq_lsb + pwprepare region,\n"
                f"; read verbatim from this song's play-data template at offset "
                f"{FREQBLOB_OFF} ({FREQBLOB_LEN} bytes). Byte-identical across every\n"
                "; v1.2-exact rip (asserted at build time, see write_freqblob).\n"
                f";   +{FREQ_MSB_REL}   freq_msb   (96 bytes)\n"
                f";   +{FREQ_LSB_REL}  freq_lsb  (111 bytes, overlaps freq_msb by 15)\n"
                f";   +{PWPREPARE_REL} pwprepare (256 bytes, indexed by PW_ACC)\n")
        for k in range(0, len(blob), 16):
            f.write("        .byte " + ", ".join(f"${b:02x}" for b in blob[k:k + 16]) + "\n")


def playing_notes(packed):
    out, last = [], 0
    for n in unpack_sequence(packed):
        if SF2_NOTE_MIN <= n <= SF2_NOTE_MAX:
            last = n
        out.append(last)
    return out


def freq_of(note):
    return 0 if note == 0 else (FREQ_TABLE_LO[note - 1] | (FREQ_TABLE_HI[note - 1] << 8))


def _dedup_row_count(progs_dict, preseed=()):
    """Total rows a set of (possibly repeated) programs needs once identical
    CONTENT is deduped -- mirrors gen_includes_song's own wave_dedup/
    filt_dedup dict-keyed-by-tuple behaviour exactly (used by count_only to
    predict the real post-dedup WAVE/FILTER table row usage without doing
    the full byte-layout build)."""
    seen = {tuple(p) for p in preseed}
    total = sum(len(p) for p in preseed)
    for prog in progs_dict.values():
        k = tuple(prog)
        if k not in seen:
            seen.add(k)
            total += len(prog)
    return total


# ---------------------------------------------------------------------------
# B7 (part-boundary priming, docs/players/BLACKBIRD.md's "B7" section):
# resolve the concrete PRIME_* constants do_init needs from (a) the captured
# real engine-state snapshot at this part's row0 (`prime`, from
# run_full_song_sim's row_state) and (b) gen_includes_song's OWN address
# allocation for THIS part's tables (wave/filter program starts per
# instrument, FM/pulse addresses per bundle) -- must run AFTER
# gen_includes_song, not before, since the addresses don't exist yet.
#
# Field-by-field rationale (see the task report for the full derivation):
#   VWI/VGMASK/VBASENOTE   -- looked up via _lookup_wave_row against the
#                              OWNER instrument's own translated WAVE
#                              program (position-walk is state-independent,
#                              per unroll_wave_pulse's own docstring, so the
#                              SAME walk from wave_start deterministically
#                              reaches whatever position the full-song sim
#                              really captured).
#   AD/SR/FLAGS/VIFILT/VWF -- read directly back from the INSTR table
#                              gen_includes_song just wrote for the owner
#                              instrument (exactly what set_instr_v would
#                              load for that instrument -- AD/SR/flags/
#                              filt-start are NEVER touched between a
#                              trigger and the next one, so the owner
#                              instrument's own static table values ARE
#                              the real current register content).
#   PW_ACC / D402           -- B9: the pulse accumulator's raw phase, copied
#                              straight from the snapshot (`v.pwidth`), plus
#                              the raw $D402 byte for the "this instrument's
#                              wave program has no bit6 rows at all" case.
#   F_IDX/F_CNT/F_ADHI      -- looked up via _lookup_filter_row against
#                              whichever program (default, or the owner
#                              instrument identified by filt_owner_instr)
#                              currently governs the GLOBAL filter engine;
#                              F_CLO/F_CHI/F_MODE/$D417 primed from the raw
#                              captured registers directly (the filter's
#                              ADD-mode ramp always continues from whatever
#                              F_CLO/F_CHI already hold -- see fp_apply in
#                              blackbird_driver.asm -- so these must be the
#                              REAL current cutoff, not re-derived from row
#                              content the way a SET row would).
#   FXPOS / BASEPITCH       -- B10: the fx engine's ENTIRE runtime state, two
#                              raw bytes copied verbatim from the snapshot.
#                              No lookup, no reconstruction, no failure mode
#                              (B8's eight-field FM resume had all three).
#                              VIFXS/VIFXR carry the voice's still-pending
#                              $c0-$ff selection across the boundary.
# ---------------------------------------------------------------------------
def _compute_prime_consts(gen, edit, ad_sr, wave_programs, wave_stats_by_instr,
                           filter_extra_by_instr, default_filter_program,
                           default_filter_extra, prime,
                           prime_instr_of_voice,
                           filt_owner_instr, default_wave_program=None,
                           default_wave_stats=None, fx_start_list=None):
    io = gen.instr_addr - B.EDIT_BASE
    ipulse_lo_addr = gen.filter_addr + 3 * 256 + 2 * NFM
    ipulse_hi_addr = ipulse_lo_addr + NFM
    eb = B.EDIT_BASE

    def _row_at(starts, k):
        """Map a SOURCE frame index k to (row_index, frames_already_elapsed
        into that row) given a cumulative row_frame_start list (len =
        nrows+1). Returns None when k lies past the program's unrolled
        extent (caller falls back to the program's own freeze row)."""
        if not starts or k < 0 or k >= starts[-1]:
            return None
        lo, hi = 0, len(starts) - 2
        while lo <= hi:
            mid = (lo + hi) // 2
            if starts[mid] <= k < starts[mid + 1]:
                return mid, k - starts[mid]
            if k < starts[mid]:
                hi = mid - 1
            else:
                lo = mid + 1
        return None

    consts = {}
    # --- B9: PULSE part-boundary priming is now a SINGLE byte per voice.
    #
    # B8 needed seven fields per voice (PPTR_LO/HI, VPC, VPLO, VPHI, VPADL,
    # plus an aux PULSETAB program emitted just to give the cursor a stable
    # address) because the pulse ran on its own independent row cursor whose
    # whole position had to be reconstructed. B9 deleted that engine: pulse
    # is stepped by wave_step off the WAVE row, so the wave priming that
    # already exists (PRIME_VWI, via _lookup_wave_row) positions the pulse
    # program too, for free and by construction.
    #
    # What remains is the one thing that is genuinely per-voice runtime
    # state and NOT recoverable from any table: the 8-bit accumulator
    # itself. The simulator tracks it as `v.pwidth`, and the boundary
    # snapshot (row0+1, per B8's anchor fix) carries its true value at
    # exactly the instant the part begins -- so this is an EXACT resume of
    # the mid-sweep phase, which is the specific thing B8's own punch list
    # named as unfixable under the output-byte encoding ("it cannot
    # reproduce a phase it was never given").
    for v in range(3):
        consts[f'PRIME_PW_ACC{v}'] = (
            (prime['voices'][v].get('pwidth', 0) & 0xFF) if prime is not None else 0)
        # ...and the REGISTER itself, for the "this instrument's wave program
        # has no bit6 rows at all" case -- see blackbird_driver.asm's own
        # PRIME_D402_TAB comment for the measurement that forced this.
        consts[f'PRIME_D402{v}'] = (
            (prime['regs'][2 + 7 * v] & 0xFF) if prime is not None else 0)

    # --- B10: fx/pitch part-boundary priming -- TWO raw bytes per voice.
    #
    # This block used to reconstruct eight FM fields by locating the captured
    # `fxpos` inside a translated per-(fx,note) program's row/frame map and
    # rebuilding the accumulator from its absolute-offset sequence -- and it
    # fell back to FM_ON=0 (a flat, wrong pitch) whenever that lookup missed,
    # which on Glyptodont it regularly did, because clustering had often
    # replaced the resting voice's real program with a merged neighbour's.
    #
    # The driver now runs lft's own algorithm over lft's own tables, so the
    # simulator's state and the driver's state are THE SAME TWO BYTES. There
    # is no mapping to get wrong, no aux program to emit, and no failure mode
    # to degrade into -- `fxpos` and `basepitch` are copied straight across.
    for v in range(3):
        pv = prime['voices'][v] if prime is not None else None
        consts[f'PRIME_FXPOS{v}'] = (pv['fxpos'] & 0xFF) if pv else 0
        consts[f'PRIME_BASEPITCH{v}'] = (pv.get('basepitch', 0) & 0xFF) if pv else 0
        # The voice's still-pending $c0-$ff selection (its sticky currfx),
        # so a note arriving after the boundary repositions to the right
        # program even before the part's own sequence re-emits a command.
        cf = (pv['currfx'] & 0xFF) if pv else 0
        if pv and 1 <= cf <= len(fx_start_list or []):
            consts[f'PRIME_VIFXS{v}'] = fx_start_list[cf - 1] & 0xFF
            consts[f'PRIME_VIFXR{v}'] = 1
        else:
            consts[f'PRIME_VIFXS{v}'] = 0
            consts[f'PRIME_VIFXR{v}'] = 0

    for v in range(3):
        oi = prime_instr_of_voice[v] if prime is not None else None
        if oi is None:
            # No known active instrument for this voice at row0 -- either
            # prime is None (row0==0, the song's true start), or this voice
            # genuinely never triggered a note anywhere earlier in the
            # song.
            #
            # B8: what real hardware is ACTUALLY doing here is NOT "nothing"
            # -- `vs.wavepos` starts at 0 and everyframe() is unconditional,
            # so the wavepos==0 DEFAULT wave program is already running and
            # already writing $D404 (masked by wavemask=$fe, gate off) and
            # $D402/3. The old cold-start values below pointed VWI at
            # whatever program landed at WAVE row 0 and left the pulse
            # engine on bundle 0. gen_includes_song now pins the genuine
            # default program at WAVE row 0 (same convention as
            # FILT_INIT_ROW), so pointing VWI there is now the CORRECT
            # translation, not merely a placeholder. A never-triggered voice
            # at row0>0 additionally resumes it at its real position k (the
            # PULSE side of that is handled by the shared loop above).
            kdef = 0
            if prime is not None and default_wave_stats is not None:
                kk = _lookup_wave_row(default_wave_stats,
                                      prime['voices'][v]['wavepos'])
                kdef = 0 if kk is None else kk
            consts[f'PRIME_VWI{v}'] = kdef & 0xFF
            consts[f'PRIME_VIWAVE{v}'] = 0
            consts[f'PRIME_VGMASK{v}'] = (
                0xFF if (prime is not None and
                         prime['voices'][v]['wavemask'] == 0xFF) else 0xFE)
            consts[f'PRIME_AD{v}'] = 0
            consts[f'PRIME_SR{v}'] = 0
            consts[f'PRIME_FLAGS{v}'] = 0
            consts[f'PRIME_VIFILT{v}'] = 0
            dwp = default_wave_program or [(0x41, 0x00)]
            consts[f'PRIME_VWF{v}'] = dwp[0][0] & 0xFF
            continue

        wave_start_row = edit[io + 5 * 32 + oi]
        stats = wave_stats_by_instr.get(oi)
        pv = prime['voices'][v]
        k = _lookup_wave_row(stats, pv['wavepos'])
        if k is None:
            print(f"    B7 WARNING: priming voice {v}'s WAVE position "
                  f"{pv['wavepos']} not found in instrument {oi}'s program "
                  f"-- falling back to row 0 (residual, see report)")
            k = 0
        consts[f'PRIME_VWI{v}'] = (wave_start_row + k) & 0xFF
        consts[f'PRIME_VIWAVE{v}'] = wave_start_row & 0xFF
        consts[f'PRIME_VGMASK{v}'] = 0xFF if pv['wavemask'] == 0xFF else 0xFE
        consts[f'PRIME_AD{v}'] = edit[io + 0 * 32 + oi]
        consts[f'PRIME_SR{v}'] = edit[io + 1 * 32 + oi]
        consts[f'PRIME_FLAGS{v}'] = edit[io + 2 * 32 + oi]
        consts[f'PRIME_VIFILT{v}'] = edit[io + 3 * 32 + oi]
        wp = wave_programs.get(oi) or [(0x41, 0x00)]
        consts[f'PRIME_VWF{v}'] = wp[0][0] & 0xFF

        # (B9: PRIME_PW_ACC and every PRIME_FM_* field are set by the
        # dedicated accumulator/FM loop ABOVE, which runs for all three
        # voices regardless of which branch this loop takes. B8's seven
        # per-voice pulse-cursor fields are gone entirely -- wave_step
        # positions the pulse program now, so PRIME_VWI does that job.)

    # --- global filter priming (ONE shared SID resource, not per-voice) ---
    if prime is None:
        consts['PRIME_F_IDX'] = 0
        consts['PRIME_F_CNT'] = 0
        consts['PRIME_F_ADHI'] = 0
        consts['PRIME_F_CLO'] = 0
        consts['PRIME_F_CHI'] = 0
        consts['PRIME_F_MODE'] = 0
        consts['PRIME_D417'] = 0
    else:
        fo = prime['filt_owner']
        if fo == 0 or filt_owner_instr is None:
            base_row = 0
            extra = default_filter_extra
        else:
            base_row = edit[io + 3 * 32 + filt_owner_instr]
            extra = filter_extra_by_instr.get(filt_owner_instr) or default_filter_extra
        found = _lookup_filter_row(extra, prime['zp_filtpos'])
        if found is None:
            print(f"    B7 WARNING: priming FILTER position "
                  f"{prime['zp_filtpos']} (owner filt_start={fo}) not found "
                  f"-- falling back to a fresh row-0 reload (residual, see "
                  f"report)")
            r, frames_into = 0, 0
        else:
            r, frames_into = found
        consts['PRIME_F_IDX'] = (base_row + r) & 0xFF
        consts['PRIME_F_CLO'] = prime['regs'][21] & 0xFF
        consts['PRIME_F_CHI'] = prime['regs'][22] & 0xFF
        consts['PRIME_F_MODE'] = prime['regs'][24] & 0xF0
        consts['PRIME_D417'] = prime['regs'][23] & 0xFF
        if frames_into == 0:
            consts['PRIME_F_CNT'] = 0            # force a fresh row-load, like the old default
            consts['PRIME_F_ADHI'] = 0
        else:
            b0, b1, run = extra['rows'][r]
            consts['PRIME_F_CNT'] = max(0, run - frames_into) & 0xFF
            consts['PRIME_F_ADHI'] = (((b0 & 0x0F) << 4) | ((b1 >> 4) & 0x0F)) & 0xFF
    return consts


PRIME_PER_VOICE_FIELDS = ['VWI', 'VIWAVE', 'VGMASK', 'AD', 'SR',
                          'FLAGS', 'VIFILT', 'VWF',
                          # B9: the ONE remaining pulse field. B8's seven
                          # (VIPUL_LO/HI, PULSE, VPC, VPHI, VPADL, PPTR_LO/HI)
                          # all described a separate pulse row-cursor that no
                          # longer exists -- wave_step steps the pulse now.
                          'PW_ACC', 'D402',
                          # B10: fx/pitch resume -- the two RAW state bytes
                          # plus the voice's pending $c0-$ff selection.
                          # Replaces B8's eight reconstructed FM_* fields.
                          'FXPOS', 'BASEPITCH', 'VIFXS', 'VIFXR']
PRIME_GLOBAL_FIELDS = ['PRIME_F_IDX', 'PRIME_F_CNT', 'PRIME_F_ADHI',
                       'PRIME_F_CLO', 'PRIME_F_CHI', 'PRIME_F_MODE', 'PRIME_D417']


def _write_prime_consts(consts):
    """Appends do_init's PRIME_* scalar constants to the SAME layout.inc
    gen_includes_song just wrote (must run after it -- see
    _compute_prime_consts). Deliberately PLAIN `NAME = value` assignments,
    NOT `.byte` table data: layout.inc is `.include`d in blackbird_driver
    .asm BEFORE any `* = ` origin directive has been issued (it precedes
    even INSTR_AD's own derived constants), so any raw bytes emitted at
    that point in the file would land at an undefined/wrong address. The
    actual PRIME_*_TAB byte tables (3 bytes each, referencing these SAME
    scalar constants) live inside blackbird_driver.asm itself instead, in
    the same already-`*=`-positioned "natural gap" region the tempo_sched_*
    tables use (see the do_init comment + the table block right after
    `ollo`/`olhi`)."""
    path = os.path.join(ROOT, "drivers_src", "blackbird", "layout.inc")
    with open(path, "a") as f:
        f.write("; B7: per-part boundary priming (auto-generated, native song) "
                 "-- see build_blackbird_native_song.py's _compute_prime_consts "
                 "/ blackbird_driver.asm's PRIME_*_TAB + do_init\n")
        for field in PRIME_PER_VOICE_FIELDS:
            for v in range(3):
                f.write(f"PRIME_{field}{v} = {consts[f'PRIME_{field}{v}'] & 0xFF}\n")
        for k in PRIME_GLOBAL_FIELDS:
            f.write(f"{k} = {consts[k] & 0xFF}\n")


def build_range(lay, d, la, ins_restart, ins_restart2, steps_per_voice,
                 ad_sr, default_filter_program, default_filter_extra,
                 full_schedule, opening_pair, row_state,
                 row0, row1, count_only=False):
    """B6 (part-splitting): build (or, count_only, just SIZE) the song's
    [row0, row1) tick-row window as a standalone part. Mirrors bin/
    build_mon_native_song.py's build_native_song(..., win=, count_only=)
    shape (read in full before writing this): pass 1 always computes the
    window's own used-instrument/used-bundle vocabulary (scoped to ONLY
    what that window's notes actually reference, via window_steps' boundary-
    continuation -- see its docstring), count_only skips clustering/assemble
    and returns the raw resource counts a fits() check needs; the real build
    goes on to cluster, pack rows, and assemble+wrap a standalone .sf2.

    Per this task's own instruction to verify rather than assume: WAVE
    (171/256) and FILTER (27/256) headroom on the current whole-song
    Glyptodont build is deep enough that windowing (which can only ever
    SHRINK a window's own local table usage vs the whole song) means the
    bundle cap is the only constraint expected to bind in practice -- but
    all of PLAYBOOK.md Sec.3's caps are still checked here defensively
    (instruments/WAVE/FILTER/sequences), not just bundles, so a future
    denser file that DID also blow a table cap would still split correctly
    instead of silently overflowing.

    B7 (part-boundary priming, docs/players/BLACKBIRD.md's "B7" section):
    `row_state[row0]` (from run_full_song_sim, may be None) is the REAL
    engine state a resting/sustaining voice actually holds at this part's
    own start frame -- used below to (a) pull in the "owner" instrument/
    filter-program/FM+pulse bundle that's SILENTLY still active for a
    voice that isn't re-triggering right at row0 (so their real WAVE/
    FILTER/FM/PULSE programs get emitted into this part's own tables even
    though no windowed step names them), and (b) compute do_init's
    PRIME_* priming constants (appended to layout.inc after gen_includes_
    song runs, since they need gen_includes_song's own address allocation
    to resolve into concrete row/table offsets). For row0==0 (a song's
    true start, e.g. Fargo's only part or Glyptodont's part 1),
    row_state[0] is IDENTICAL to the sim's own pristine __init__ state, so
    every "priming addition" below is a no-op and this reduces exactly to
    B6's own behavior (verified explicitly, see the report).
    """
    windowed_steps = [window_steps(steps_per_voice[v], row0, row1) for v in range(3)]

    used_fx = set()          # B10: the whole per-note vocabulary is now
                              # just the set of fx INDICES (note-independent)
    used_instr = set()
    cur_instr_track = [None, None, None]
    for v in range(3):
        for s in windowed_steps[v]:
            if s.kind == 'note' and s.note is not None:
                if s.instrument is not None:
                    cur_instr_track[v] = s.instrument
                instr = cur_instr_track[v] if cur_instr_track[v] is not None else 0
                used_instr.add(instr)
                used_fx.add(s.fx & 0x3F)

    # --- B7: pull in whatever instrument/filter-program/bundle a RESTING
    # voice is silently still holding at row0, so its real WAVE/FILTER/
    # FM/PULSE programs are guaranteed present in this part's own tables
    # for do_init's priming to reference below (a rest never names an
    # instrument in the windowed step stream itself -- see window_steps'
    # own docstring -- so without this addition the owner's program simply
    # wouldn't exist in a part that never happens to re-select it).
    # B8: `row0 + 1`, not `row0`. B7 found and fixed exactly this off-by-one
    # in main()'s COMPARISON anchor (row_state[r]/row_frame[r] reflect the
    # frame during which row r-1's event was committed, so row r's own
    # content lives at index r+1) -- but left the PRIMING snapshot itself on
    # the stale index, so do_init was being seeded with state one full TICK
    # (~5 real frames at these tempos) before the instant it actually
    # represents. For a resting voice that is a real error: its wave/pulse/
    # FM programs have stepped ~5 frames further by the time the part's own
    # frame 0 begins. Verified as one bug with one cause, not two
    # coincidences -- see the B8 report's anchor-sweep table, where
    # row_frame[row0+1] is a strict LOCAL MAXIMUM (+/-1 frame both score
    # worse), which is what a genuine alignment looks like.
    _pi = row0 + 1
    prime = row_state[_pi] if row_state and 0 <= _pi < len(row_state) else None
    prime_instr_of_voice = [None, None, None]
    filt_owner_instr = None
    if prime is not None:
        nins_total = len(ad_sr)
        for v in range(3):
            pv = prime['voices'][v]
            if pv['currins'] > 0:
                oi = pv['currins'] - 1
                if 0 <= oi < nins_total:
                    prime_instr_of_voice[v] = oi
                    used_instr.add(oi)
                    used_fx.add(pv['currfx'] & 0x3F)
        fo = prime['filt_owner']
        if fo != 0:
            for i in range(len(ad_sr)):
                off = (lay.ins_filt - la) + i
                if 0 <= off < len(d) and d[off] == fo:
                    filt_owner_instr = i
                    used_instr.add(i)
                    break

    # --- B8: Blackbird's OWN `wavepos == 0` default wave/pulse program.
    # Structurally identical to default_filter_program (computed once in
    # main() and shared by every part): the real player's wave engine is
    # unconditional from frame 0 with wavepos initialized to 0, so this is
    # what every voice is genuinely running before its first note, and what
    # a never-triggered voice keeps running forever. Song-wide, not window-
    # dependent -- but computed here rather than threaded through
    # build_song's signature since it's a single 300-frame sim call.
    default_wave_program, default_pulse_program, default_wave_stats = \
        unroll_wave_pulse(lay, d, la, ins_restart, ins_restart2, 0)

    # --- per-instrument WAVE/PULSE/FILTER programs (used instruments only) ---
    wave_programs, pulse_of_instr, filter_programs, filter_flag_of = {}, {}, {}, {}
    wave_stats_by_instr, filter_extra_by_instr = {}, {}
    for i in sorted(used_instr):
        wave_start = d[(lay.ins_wave - la) + i] if 0 <= (lay.ins_wave - la) + i < len(d) else 0
        wr, pr, stats = unroll_wave_pulse(lay, d, la, ins_restart, ins_restart2, wave_start)
        wave_programs[i] = wr
        pulse_of_instr[i] = pr
        wave_stats_by_instr[i] = stats
        filt_start = d[(lay.ins_filt - la) + i] if 0 <= (lay.ins_filt - la) + i < len(d) else 0
        if filt_start != 0:
            frows, fextra = unroll_filter(lay, d, la, ins_restart, ins_restart2, filt_start)
            filter_programs[i] = frows
            filter_flag_of[i] = True
            filter_extra_by_instr[i] = fextra

    # --- B10: the fx/pitch "vocabulary" is just the set of fx INDICES this
    #     window uses. There are no per-(fx, note) programs to unroll, no
    #     bundle list, and no clustering: the driver runs lft's own engine
    #     over lft's own fxtable, so an fx index is note-independent and maps
    #     to a $c0-$ff slot as the identity.
    nfx, fx_start_list, fxtab_bytes = fx_table_info(lay, d, la)
    if nfx >= NFM:
        raise ValueError(
            f"nfx={nfx} does not fit the {NFM}-slot $c0-$ff command space. "
            "B10 assumes the identity fx-index -> command-slot mapping; a "
            "file this dense would need a real (note-independent) fx "
            "clustering pass, which does not exist.")
    n_used_fx = len(used_fx)

    if count_only:
        tracks = [steps_to_rows_native(windowed_steps[v]) for v in range(3)]
        nseg = sum(len(segment_track(tracks[v]) or [b'']) for v in range(3))
        # B8: the default wave program now occupies WAVE row 0 (see
        # gen_includes_song), exactly as default_filter_program already did
        # for FILTER -- so fits() must budget for it too, or a window it
        # approves could overflow the real build.
        nw = _dedup_row_count(wave_programs, preseed=[default_wave_program])
        nf = _dedup_row_count(filter_programs, preseed=[default_filter_program])
        return n_used_fx, len(used_instr), nw, nf, nseg

    # B10: n_merged is structurally 0 now -- kept in the returned dict (and
    # printed) so the report still SHOWS that clustering is gone rather than
    # quietly dropping the field that used to carry the loss.
    n_raw_bundles, n_merged = n_used_fx, 0

    tracks = [steps_to_rows_native(windowed_steps[v]) for v in range(3)]
    segs = [segment_track(tracks[v]) or [bytes([0x7F])] for v in range(3)]

    # Tempo: the pair ACTIVE at this part's own row0 (not necessarily the
    # song's opening pair -- a part starting mid-song must seed CUR_TEMPO/
    # CUR_TEMPO2 with whatever was really playing at that instant), plus this
    # window's OWN row-shifted interior schedule (see tempo_at_row/
    # window_tempo_schedule's docstrings -- both derived from ONE full-song
    # sim pass in main(), not re-simulated per part).
    long_f, short_f = tempo_at_row(full_schedule, opening_pair, row0)
    chain = [long_f] if long_f == short_f else [long_f, short_f]
    B.TEMPO = max(1, chain[0])
    B.TEMPO2 = max(1, chain[1]) if len(chain) > 1 else B.TEMPO

    part_schedule = window_tempo_schedule(full_schedule, row0, row1)
    if len(part_schedule) > TEMPO_SCHED_CAP:
        raise ValueError(
            f"part [{row0}:{row1}) tempo schedule overflow: "
            f"{len(part_schedule)} entries > {TEMPO_SCHED_CAP}")
    n_sched = write_tempo_schedule(part_schedule)

    # B10: the whole "resolve the FM program + position to resume at" block
    # that used to live here is GONE. `fxpos`/`basepitch` from the boundary
    # snapshot ARE the driver's state (see _compute_prime_consts), so there
    # is nothing to look up and no aux program to emit.
    gen, edit, mdp, seq0, aux = gen_includes_song(
        segs, ad_sr, wave_programs, filter_programs, filter_flag_of,
        fx_start_list, fxtab_bytes,
        default_filter_program, tempo_sched_len=n_sched,
        default_wave_program=default_wave_program,
        pulse_programs=pulse_of_instr)

    # B7: now that gen_includes_song has finalized every table's real
    # addresses (wave/filter program starts per instrument), resolve the
    # priming constants and append them to the SAME layout.inc
    # gen_includes_song just wrote.
    prime_consts = _compute_prime_consts(
        gen, edit, ad_sr, wave_programs, wave_stats_by_instr,
        filter_extra_by_instr, default_filter_program, default_filter_extra,
        prime, prime_instr_of_voice, filt_owner_instr,
        default_wave_program=default_wave_program,
        default_wave_stats=default_wave_stats,
        fx_start_list=fx_start_list)
    _write_prime_consts(prime_consts)

    prg = B.assemble()
    names = [f"instr {i:02d}" for i in range(len(ad_sr))]
    sf2 = B.wrap(prg, gen, edit, mdp, instr_names=names)

    return dict(prg=prg, edit=edit, sf2=sf2, gen=gen, mdp=mdp, seq0=seq0,
                n_bundles_raw=n_raw_bundles, n_bundles_final=n_used_fx,
                n_merged=n_merged, n_used_instr=len(used_instr),
                tempo_chain=chain, tempo_sched_n=n_sched, row0=row0, row1=row1,
                primed=(prime is not None))


def prune_stale_parts(prefix, nparts):
    """Delete `<prefix>_partNN.sf2` files with NN > nparts -- a rebuild that
    packs into fewer parts than a previous run otherwise leaves old higher-
    numbered parts on disk (same defect/fix as bin/build_mon_native_song.py's
    own prune_stale_parts, ported verbatim)."""
    import glob
    import re
    removed = 0
    for f in glob.glob(f"{prefix}_part*.sf2"):
        mm = re.search(r"_part(\d+)\.sf2$", f)
        if mm and int(mm.group(1)) > nparts:
            os.remove(f)
            removed += 1
    if removed:
        print(f"  pruned {removed} stale part file(s) beyond part{nparts:02d}")


# per-category register breakdown (freq/waveform/pulse/ad-sr/filter), matching
# every prior B-round's report granularity.
REGS_TO_CHECK = list(range(25))   # all of $D400-$D418
CATS = {
    'freq': [0, 1, 7, 8, 14, 15], 'waveform': [4, 11, 18],
    'pulse': [2, 3, 9, 10, 16, 17], 'adsr': [5, 6, 12, 13, 19, 20],
    'filter': [21, 22, 23, 24],
}


REG_NAMES = [
    'v0freqlo', 'v0freqhi', 'v0pwlo', 'v0pwhi', 'v0ctrl', 'v0ad', 'v0sr',
    'v1freqlo', 'v1freqhi', 'v1pwlo', 'v1pwhi', 'v1ctrl', 'v1ad', 'v1sr',
    'v2freqlo', 'v2freqhi', 'v2pwlo', 'v2pwhi', 'v2ctrl', 'v2ad', 'v2sr',
    'fcutlo', 'fcuthi', 'fresfilt', 'modevol',
]


def report_registers(sim_frames, drv_frames, lo, hi, label, only_reg=None, max_examples=3):
    """B12 diagnostic: per-register (not per-category) match%, plus the first
    N mismatching frames' (sim,drv) values for each broken register -- to
    pin down exactly which SID register/voice diverges and what it diverges
    TO, rather than just which category. Gated by BB_DIAG_LO/BB_DIAG_HI.
    only_reg (BB_DIAG_REG, a register index) restricts to one register and
    raises the example cap so a full divergence timeline can be read off,
    not just the first few hits."""
    n = min(hi, len(sim_frames), len(drv_frames)) - lo
    print(f"    {label} per-register [{lo}:{lo+n}) n={n}:")
    regs = [only_reg] if only_reg is not None else REGS_TO_CHECK
    for r in regs:
        match = sum(1 for f in range(lo, lo + n) if sim_frames[f][r] == drv_frames[f][r])
        pct = 100 * match / n if n else 0.0
        marker = "" if pct > 99.9 else "  <-- MISMATCH"
        line = f"      ${0xD400+r:04X} {REG_NAMES[r]:9s}: {pct:5.1f}%{marker}"
        print(line)
        if pct <= 99.9:
            examples = []
            started = False
            for f in range(lo, lo + n):
                if sim_frames[f][r] != drv_frames[f][r]:
                    started = True
                if started:
                    examples.append(f"@{f} sim=${sim_frames[f][r]:02x} drv=${drv_frames[f][r]:02x}")
                if len(examples) >= max_examples:
                    break
            print("        " + " ".join(examples))


def report_binned(sim_frames, drv_frames, bin_size, label):
    """B12 diagnostic: per-bin_size-frame category match%, to find WHERE over
    a long song a residual grows rather than just that it exists (B12's own
    task: Fargo's full-song pulse/adsr numbers are far below their short-
    window numbers, and no prior round has located where the gap opens up).
    Gated by BB_DIAG_BIN (frame count per bin) so it's opt-in, off by default
    -- this is an investigation aid, not part of the normal build report."""
    n = min(len(sim_frames), len(drv_frames))
    print(f"    {label} binned every {bin_size}f ({n} frames total):")
    for lo in range(0, n, bin_size):
        hi = min(lo + bin_size, n)
        bn = hi - lo
        cat_match = {k: 0 for k in CATS}
        for f in range(lo, hi):
            sr, dr = sim_frames[f], drv_frames[f]
            for k, regs in CATS.items():
                cat_match[k] += sum(1 for r in regs if sr[r] == dr[r])
        cats_str = ", ".join(
            f"{k}={100*cat_match[k]/(len(regs)*bn):.1f}%"
            for k, regs in CATS.items())
        print(f"      [{lo:6d}:{hi:6d}) n={bn:5d}: {cats_str}")


def report_window(sim_frames, drv_frames, lo, hi, label):
    n = hi - lo
    if n <= 0 or hi > len(sim_frames) or hi > len(drv_frames):
        return None
    cat_match = {k: 0 for k in CATS}
    cat_total = {k: len(v) * n for k, v in CATS.items()}
    per_frame_match = []
    first_diverge = None
    for f in range(lo, hi):
        sr, dr = sim_frames[f], drv_frames[f]
        n_match = sum(1 for r in REGS_TO_CHECK if sr[r] == dr[r])
        per_frame_match.append(n_match)
        for k, regs in CATS.items():
            cat_match[k] += sum(1 for r in regs if sr[r] == dr[r])
        if n_match < len(REGS_TO_CHECK) and first_diverge is None:
            first_diverge = f
    exact_frames = sum(1 for m in per_frame_match if m == len(REGS_TO_CHECK))
    avg_match = sum(per_frame_match) / (len(REGS_TO_CHECK) * n)
    cats_str = ", ".join(f"{k}={100*cat_match[k]/cat_total[k]:.1f}%" for k in CATS)
    print(f"    {label} [{lo}:{hi}) n={n}: overall={avg_match*100:.1f}%  {cats_str}  "
          f"(exact frames {exact_frames}/{n}, first mismatch @{first_diverge})")
    return dict(exact_frames=exact_frames, avg_match=avg_match,
                first_diverge=first_diverge,
                cats={k: 100 * cat_match[k] / cat_total[k] for k in CATS})


# PLAYBOOK.md Sec.3's per-file caps. CAP_I/CAP_TBL/CAP_SEG mirror bin/
# build_dmc_native_song.py / bin/build_mon_native_song.py's own convention
# directly (instruments/WAVE/FILTER/sequences), but CAP_B is Blackbird-
# specific, NOT copied from DMC/MoN's raw-count-must-be-<=63 (i.e.
# effectively zero-clustering) convention -- checked against real data
# first, per this task's own instruction not to assume: DMC/MoN's parts are
# built to need almost no clustering AT ALL once windowed (that's the whole
# point of splitting for them), but Fargo's EXISTING, previously-accepted
# whole-song native build already clusters 43/107=40.2% of its bundles away
# and was never judged a fidelity problem worth splitting over -- only
# Glyptodont's 359/423=84.9% was. A strict raw<=63 cap (DMC/MoN's own
# number) split Fargo into 2 parts on the first pass here, which is WRONG
# per this task's explicit correctness check ("Fargo must still build as
# exactly 1 part"). CAP_B=2*NFM=128 (>=50% of a window's raw bundles must
# still survive unmerged) is the smallest round threshold that keeps
# Fargo's known-good, already-shipped 40.2% loss on the "don't split" side
# while still triggering a split for Glyptodont's 84.9% -- i.e. "mild"
# clustering (<=50%, PLAYBOOK.md Sec.3's "without heavy clustering") is
# accepted per-part, "heavy" (>50%) forces a split.
#
# B8 (Lever 2) RE-DERIVED THIS EMPIRICALLY rather than by argument, since
# B6 chose 128 under a constraint B7/B8 have since removed (cold-start
# boundaries used to be very lossy, so splitting was expensive; priming
# made it cheap). Measured Glyptodont sweep, frame-count-weighted full-part
# aggregate, everything else identical:
#
#   CAP_B | parts | overall | freq | wf   | pulse | adsr | filter
#   ------+-------+---------+------+------+-------+------+-------
#     128 |   5   |  66.4   | 57.9 | 90.4 | 17.6  | 94.3 | 92.4
#      96 |  10   |  67.3   | 62.2 | 90.5 | 16.8  | 94.6 | 92.5
#      80 |  15   |  67.7   | 63.4 | 90.4 | 17.0  | 94.6 | 92.5
#      64 |  16   |  67.7   | 63.7 | 90.4 | 17.0  | 94.6 | 92.5
#
# The effect is REAL but SMALL and confined almost entirely to freq (the
# only category bundle clustering touches, now that B8 moved PULSE off the
# bundle): +5.8pp freq / +1.3pp overall from 128 -> 64, flat past 80, at
# the cost of 3x the part count. Fargo (the correctness anchor) stays
# exactly 1 part and byte-identical at 128/96/80 -- its raw bundle count is
# 80 after B8's decoupling -- but SPLITS INTO 2 at 64 and regresses hard
# (94.1% -> 77.5%), so 64 is out regardless of Glyptodont's number.
# 96 ships: it keeps Fargo at 1 part, takes ~3/4 of the available freq gain
# (+4.3 of +5.8pp), and needs 10 parts rather than 80's 15 -- and part count
# is a real musical cost the register-trace metric does NOT price in (each
# part is a separate SF2 with a hard cut, no crossfade). 80 is the measured
# fidelity optimum if part count is no object; override via BB_CAP_B.
CAP_B, CAP_I, CAP_TBL, CAP_SEG, STEP = 96, 32, 256, 120, 150
# B8 (Lever 2): CAP_B is sweepable from the environment so the threshold
# can be re-derived from measurements rather than argued about -- see the
# sweep table in docs/players/BLACKBIRD.md's B8 section.
CAP_B = int(os.environ.get('BB_CAP_B') or CAP_B)


def build_song(lay, d, la, ins_restart, ins_restart2, steps_per_voice,
               ad_sr, default_filter_program, default_filter_extra,
               full_schedule, opening_pair, row_state, span, base):
    """Adaptive part-split the song: greedily grow each [row0,row1) window
    (STEP-row probes) as long as build_range(..., count_only=True) still
    fits every cap, cut a part boundary, continue from row1 -- same grid-
    search SHAPE as bin/build_dmc_native_song.py's build_song (STEP is in
    TICK-ROWS here, not real frames: Stage A already established ticks map
    1:1 to D11 rows, so no DMC-style grid-alignment/align() is needed -- a
    row-index window is already tick-exact by construction).

    B7: `row_state`/`default_filter_extra` are threaded into fits()'s own
    count_only probe (not just the real build below) so a part's resource
    budget correctly ACCOUNTS for the extra owner-instrument/bundle/filter-
    program entries B7's priming injects (see build_range's own docstring)
    -- otherwise fits() could approve a window that the real (primed) build
    then overflows. Verified this doesn't change Fargo's own single-part
    decision (row0 is always 0 for every fits() probe Fargo's search makes,
    for which priming is a no-op by construction) -- see the report."""
    def fits(row0, row1):
        nb, ni, nw, nf, ns = build_range(
            lay, d, la, ins_restart, ins_restart2, steps_per_voice,
            ad_sr, default_filter_program, default_filter_extra,
            full_schedule, opening_pair, row_state,
            row0, row1, count_only=True)
        return nb <= CAP_B and ni <= CAP_I and nw <= CAP_TBL and nf <= CAP_TBL and ns <= CAP_SEG

    bounds, row0 = [], 0
    while row0 < span:
        row1 = min(row0 + STEP, span)
        while row1 < span and fits(row0, min(row1 + STEP, span)):
            row1 = min(row1 + STEP, span)
        bounds.append((row0, row1))
        row0 = row1
    return bounds


def main():
    sid = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "SID", "LFT", "Fargo.sid")
    lay = locate_blackbird(sid)
    if lay is None:
        raise SystemExit(f"{sid}: not a located Blackbird v1.2-exact rip")
    d, la, h = load_sid(sid)
    result = decode_streams(d, la, lay.streamstart)
    po = lay.play_base - la
    ins_restart = d[po + 93] - 1
    ins_restart2 = d[po + 512] - 1

    steps_per_voice = [bb_steps_for_voice(result.real(v)) for v in range(3)]
    span = max(sum(max(1, s.ticks) for s in steps_per_voice[v]) for v in range(3))
    base = os.path.splitext(os.path.basename(sid))[0]
    print(f"{os.path.basename(sid)}: nins(located)={lay.nins} span={span} tick-rows "
          f"events={[len(steps_per_voice[v]) for v in range(3)]}")

    # Blackbird's filter position is ONE continuous global state that starts
    # at zp_filtpos=0 (real hardware) and is only ever REPOSITIONED (never
    # gated on/off) by a filt-carrying instrument's note-on -- so EVERY
    # part's driver init position must be this same genuinely translated
    # program (song-wide, not window-dependent -- see blackbird_driver.asm's
    # do_init comment), computed once and shared by all parts.
    default_filter_program, default_filter_extra = unroll_filter(
        lay, d, la, ins_restart, ins_restart2, 0)

    # AD/SR for every located instrument slot -- also song-wide (cheap, real
    # data straight off the located table, no unrolling, same for every part).
    nins = max(1, min(lay.nins, 32))
    ad_sr = []
    for i in range(nins):
        ad = d[(lay.ins_ad - la) + i] if 0 <= (lay.ins_ad - la) + i < len(d) else 0
        sr = d[(lay.ins_sr - la) + i] if 0 <= (lay.ins_sr - la) + i < len(d) else 0
        ad_sr.append((ad, sr))

    # B10: ONE contiguous freq_msb/freq_lsb/pwprepare blob (supersedes B9's
    # separate pwprepare.inc AND the freqtable.inc the deleted FM engine
    # needed) -- song-wide, written once, shared by every part's assemble().
    sim_for_freq = BlackbirdSim(lay, d, la, [b'', b'', b''], ins_restart, ins_restart2)
    write_freqblob(sim_for_freq, d, po)
    freqblob = list(d[po + FREQBLOB_OFF:po + FREQBLOB_OFF + FREQBLOB_LEN])

    # --- B10's exact-by-construction gate (B9's discipline applied to pitch).
    # Replay the DRIVER's own fx arithmetic, over the tables this build
    # actually emits, against the validated simulator's $D400/$D401 -- every
    # frame of every (fx program, note) pair the song can produce. A single
    # wrong carry, a truncated table or a mislocated label fails the BUILD
    # here rather than costing a few unattributable percent downstream.
    nfx_song, fx_start_song, fxtab_song = fx_table_info(lay, d, la)
    notes_song = sorted({s.note for v in range(3) for s in steps_per_voice[v]
                         if s.kind == 'note' and s.note is not None})
    n_checked = verify_fx_engine(lay, d, la, ins_restart, ins_restart2,
                                 freqblob, fxtab_song, fx_start_song,
                                 notes_song)
    print(f"  B10 fx-engine self-check: {n_checked} driver-vs-simulator frame "
          f"comparisons EXACT over {nfx_song + 1} fx program(s) x "
          f"{len(notes_song)} note(s) ($D400/$D401 + FXPOS)")

    # Song's own genuine opening tempo pair (row0==0's fallback -- see
    # extract_tempo_pairs' own off-by-one-corrected //7+1 note in the B2
    # section of docs/players/BLACKBIRD.md).
    pairs = extract_tempo_pairs(d, la, lay.streamstart)
    if pairs:
        a, b = pairs[0]
        opening_pair = (max(1, a // 7 + 1), max(1, b // 7 + 1))
    else:
        opening_pair = (5, 5)   # DEFAULT_TICK_FRAMES fallback, matches Stage A's own default

    # ONE full-song simulator pass -- ground truth for every part's own
    # tempo seeding (tempo_at_row/window_tempo_schedule) AND validation
    # (row_frame maps a part's row0 to the correct real-frame OFFSET into
    # this SAME trace, so each part's own from-frame-0 driver trace is
    # compared against the RIGHT slice of the ORIGINAL performance, not
    # re-derived from scratch per part).
    print("  running one full-song simulator pass (tempo schedule + row/frame map "
          "+ B7 per-row engine-state snapshots)...")
    full_frames, row_frame, full_schedule, row_state = run_full_song_sim(
        lay, d, la, ins_restart, ins_restart2, result.voices, span)
    print(f"  full-song tempo schedule: {len(full_schedule)} row-indexed record(s) "
          f"(first at row {full_schedule[0][0] if full_schedule else '-'}, "
          f"last at row {full_schedule[-1][0] if full_schedule else '-'}); "
          f"{len(full_frames)} real frames simulated")

    bounds = build_song(lay, d, la, ins_restart, ins_restart2, steps_per_voice,
                        ad_sr, default_filter_program, default_filter_extra,
                        full_schedule, opening_pair, row_state, span, base)
    print(f"  packed into {len(bounds)} adaptive part(s) (span {span} tick-rows, "
          f"{STEP}-row probe step, caps: bundles<={CAP_B} instr<={CAP_I} "
          f"wave/filter<={CAP_TBL} seqs<={CAP_SEG})")

    from sidm2.models import SF2DriverInfo
    from sidm2 import sf2_parser

    N_CMP = 200          # matches every prior B-round's own "primary window"
    # B10: env-overridable. B10 collapsed Glyptodont from 10 parts to 1,
    # which silently CHANGES WHAT GETS MEASURED -- 10 parts x ~1425f covered
    # the whole song, one part capped at 3000f covers only its first ~14%.
    # Comparing those two numbers as if they were the same measurement would
    # be meaningless, so the cap is sweepable to put both builds on the same
    # frame coverage. See BLACKBIRD.md's B10 section for both.
    # (Default 3000 = the per-part "full window" cap B3-B5 used; most parts
    # are far shorter end-to-end, so it is usually the WHOLE part.)
    N_FULL_CAP = int(os.environ.get('BB_FULL_CAP') or 3000)

    out_dir = os.path.join(ROOT, "out", "blackbird")
    os.makedirs(out_dir, exist_ok=True)
    stale_unsuffixed = os.path.join(out_dir, f"{base}_native.sf2")
    if os.path.exists(stale_unsuffixed):
        os.remove(stale_unsuffixed)   # superseded by the _partNN convention below

    WEIGHTED = []
    for pi, (row0, row1) in enumerate(bounds, 1):
        br = build_range(lay, d, la, ins_restart, ins_restart2, steps_per_voice,
                         ad_sr, default_filter_program, default_filter_extra,
                         full_schedule, opening_pair, row_state,
                         row0, row1, count_only=False)
        out = os.path.join(out_dir, f"{base}_native_part{pi:02d}.sf2")
        open(out, "wb").write(br['sf2'])
        print(f"\n  part {pi}/{len(bounds)} rows[{row0}:{row1}) ({row1 - row0} rows): "
              f"wrote {out} ({len(br['sf2'])} bytes)")
        print(f"    instr={br['n_used_instr']} bundles {br['n_bundles_raw']}->"
              f"{br['n_bundles_final']} (merged {br['n_merged']}), "
              f"tempo chain {br['tempo_chain']}, {br['tempo_sched_n']} interior "
              f"tempo record(s), B7 primed={br['primed']}")

        di = SF2DriverInfo()
        pla = sf2_parser.parse_sf2_blocks(bytearray(br['sf2']), di)
        print(f"    PARSE: load=${pla:04X} tracks={di.track_count}",
              "OK" if pla == 0x0D7E else "FAIL")

        # --- Real validation: this part's own ASSEMBLED driver trace (always
        # frame-0-based -- a part is a standalone file with no prior state)
        # vs the SAME validated whole-song simulator trace, sliced at this
        # part's own real-frame OFFSET so it's compared against the RIGHT
        # moment of the original performance.
        #
        # B7 FOUND A REAL BUG HERE (pre-existing since B6, not introduced by
        # priming -- but only EXPOSED by it, see the report): row_frame[r]
        # is the frame at which the sim's `row` COUNTER reached r, which
        # happens DURING the real_frame() call that just committed row
        # (r-1)'s note/instrument event -- i.e. full_frames[row_frame[r]]
        # shows row (r-1)'s OWN content, not row r's (verified directly via
        # run_full_song_sim's row_state, whose docstring names the same
        # off-by-one: row_state[r] == the state during window-tick r-1).
        # The driver's OWN frame 0 (do_init + the immediate first do_row
        # call) shows row0's OWN committed content -- so it must be compared
        # against full_frames[row_frame[row0 + 1]], NOT full_frames[
        # row_frame[row0]] (one tick, e.g. ~5 real frames at Glyptodont's
        # tempo, EARLY). Verified empirically before applying (per this
        # task's own "don't accept a hand-wavy explanation" instruction):
        # on Glyptodont part 4 (row0=1200), switching only this anchor moved
        # waveform 40.0%->89.7%, AD/SR 63.9%->91.5%, overall 48.5%->68.3% on
        # the SAME already-built driver binary -- the anchor was silently
        # comparing every part after the first against ~1 tick of STALE
        # (previous-tick) content, which is why waveform/AD/SR looked so
        # badly broken in every B6 report despite the driver's own translated
        # content being largely correct.
        #
        # row0==0 is DELIBERATELY EXEMPTED (kept at the historical
        # row_frame[0]==0 anchor, not row_frame[1]) to satisfy this task's
        # own explicit constraint that Fargo/part-1 must not regress or
        # change its already-verified-correct reported numbers -- row0==0 is
        # a genuine COLD start on both sides (do_init's own defaults exactly
        # equal the sim's own pristine __init__ state), so both anchors
        # start from an identical degenerate all-zero baseline and diverge
        # only by the ALREADY-DOCUMENTED, separately-named "~3-frame
        # startup-pipeline offset" residual either way -- not the same
        # one-full-TICK content mismatch this fix addresses for row0>0.
        # B8: the row0==0 EXEMPTION B7 added is gone -- the anchor is now
        # uniform for every part. B7 kept row0==0 on the historical
        # row_frame[0] anchor purely so Fargo's already-published baseline
        # number wouldn't move, while its own report noted the corrected
        # anchor scored BETTER there too (69.6%->71.6%). That exemption was
        # a reporting-continuity choice, not a correctness one: the driver's
        # frame 0 (do_init + the immediate first do_row) shows row0's OWN
        # committed content on EVERY part, including part 1, and real
        # hardware doesn't commit row 0 until its dispatch has spent 3
        # frames on prepare1/2/3 (row_frame[1] == 3 on both files, measured).
        # Comparing the driver's frame 0 against sim frame 0 was grading a
        # post-commit state against a pre-commit one. Confirmed empirically
        # by sweeping the anchor +/-1 around row_frame[row0+1] on the SAME
        # built binary: it is a strict local maximum (Fargo full-window
        # 81.9 / 82.3 / 81.5 at F0 = 2 / 3 / 4), which a coincidental
        # improvement would not be. Both anchors' numbers are reported in
        # the B8 section of docs/players/BLACKBIRD.md so the change is
        # visible rather than silently folded into the headline.
        # (The pre-B8 anchor was `F0 = row_frame[row0]`; see the comment above
        # for why that was off by one tick, and BLACKBIRD.md's B8 section for
        # both anchors' numbers side by side.)
        if (row0 + 1) < len(row_frame):
            F0 = row_frame[row0 + 1]
        else:
            F0 = row_frame[-1]
        F1 = row_frame[row1] if row1 < len(row_frame) else len(full_frames)
        if row1 > 0 and (row1 + 1) < len(row_frame):
            F1 = row_frame[row1 + 1]
        part_span_frames = max(1, F1 - F0)
        n_want = min(max(N_CMP, part_span_frames), N_FULL_CAP, len(full_frames) - F0)
        drv_frames = B.headless_trace(br['prg'], br['edit'], n_want)
        sim_slice = full_frames[F0:F0 + len(drv_frames)]

        print(f"    REGISTER-TRACE COMPARISON vs the validated simulator "
              f"(sliced at real-frame offset {F0} in the whole-song trace):")
        pr = report_window(sim_slice, drv_frames, 0, min(N_CMP, len(drv_frames)),
                      "primary window (first 200f)")
        if len(drv_frames) > N_CMP:
            fw = report_window(sim_slice, drv_frames, 0, len(drv_frames),
                          f"full-part window ({part_span_frames}f span"
                          f"{', capped' if part_span_frames > N_FULL_CAP else ''})")
            if fw:
                WEIGHTED.append((len(drv_frames), fw))
            # steady-state (post-primary) window: isolates the part's OWN
            # startup transient (do_init's ~3-frame pipeline-fill + the
            # boundary-retrigger residual window_steps' docstring names) from
            # the rest of the part -- same segmenting technique the B1 report
            # already used on the whole-song build ("frames 0-10 vs 10-200")
            # to tell a real startup artifact from a genuine steady-state gap.
            report_window(sim_slice, drv_frames, N_CMP, len(drv_frames),
                          "steady-state (200f:end, excludes this part's own "
                          "startup transient)")
            diag_bin = os.environ.get('BB_DIAG_BIN')
            if diag_bin:
                report_binned(sim_slice, drv_frames, int(diag_bin),
                              f"part {pi} diagnostic")
            diag_lo = os.environ.get('BB_DIAG_LO')
            if diag_lo:
                diag_hi = int(os.environ.get('BB_DIAG_HI') or len(drv_frames))
                diag_reg = os.environ.get('BB_DIAG_REG')
                report_registers(sim_slice, drv_frames, int(diag_lo), diag_hi,
                                  f"part {pi} diagnostic",
                                  only_reg=(int(diag_reg) if diag_reg is not None else None),
                                  max_examples=(60 if diag_reg is not None else 3))

    if WEIGHTED:
        tot = sum(n for n, _ in WEIGHTED)
        agg = {k: sum(w['cats'][k] * n for n, w in WEIGHTED) / tot for k in CATS}
        ov = sum(w['avg_match'] * n for n, w in WEIGHTED) / tot
        print(f"\n  WEIGHTED AVERAGE over {len(WEIGHTED)} part(s), {tot} frames "
              f"(CAP_B={CAP_B}): overall={ov*100:.1f}%  " +
              ", ".join(f"{k}={agg[k]:.1f}%" for k in CATS))
    prune_stale_parts(os.path.join(out_dir, f"{base}_native"), len(bounds))


if __name__ == "__main__":
    main()
