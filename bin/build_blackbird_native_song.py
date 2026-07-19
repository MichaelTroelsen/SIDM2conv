"""Stage B1 -- emit a REAL Blackbird (Linus Åkesson / "lft") tune as a
native-Blackbird-driver .sf2.

Follows bin/build_romuzak_native_song.py's shape (per docs/players/
PLAYBOOK.md and this task's brief): decode the song via the already-shipped
sidm2.blackbird_parser (locate + LZ decompression, untouched here), build
the per-voice D11Row track using the SAME tick-is-a-row model
sidm2.blackbird_driver11.py's Stage A already established (re-derived here,
not imported, because Stage A's steps_for_voice() drops the fx/arp byte --
this module needs it to select the per-note FM+pulse command bundle), then
translate Blackbird's own wave/pulse/filter/fx programs into the shared
native driver's WAVE/PULSETAB/FILTER/FMTAB table formats using the
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

FMTAB and PULSETAB (see drivers_src/blackbird/blackbird_driver.asm's
fm_step/pulse_step) have NO general "jump to an earlier row" primitive --
only WAVE and FILTER do ($7f = genuine relative/absolute jump). So once a
program's visited-state cycle is found:
  - WAVE:   emit rows 0..cycle_end-1 + a genuine `$7f` jump row back to
            cycle_start -- loops forever, exact.
  - FILTER: emit SET rows (baseline) + ADD-delta rows (RLE-collapsed holds
            and linear ramps) for 0..cycle_end-1, ending in a genuine `$7f`
            jump back to cycle_start -- loops forever, exact.
  - PULSE:  the visited VALUE sequence (there IS a native "set absolute,
            hold N frames" 8X/XX/YY row) is RLE-collapsed and physically
            REPEATED (not jumped) for target_frames, then frozen ($7f) --
            exact for target_frames, then holds the last value (documented
            residual: only matters for a note sustained longer than
            target_frames, ~5s at 50fps).
  - FMTAB:  fm_step's table is a per-frame ACCUMULATOR delta list (freq =
            vfreq + FM_ACC, FM_ACC += this row's signed offset every frame
            it's active) -- NOT an absolute-value table. So this translator
            converts Blackbird's ABSOLUTE per-frame offset-from-steady
            sequence into a DELTA sequence (delta[k] = offset[k]-offset[k-1],
            offset[-1]=0, matching FM_ACC's own note-on reset to 0) before
            RLE-collapsing (a constant delta run becomes one linear-ramp
            row) and repeat-then-freeze past the cycle, same as PULSE.
            KNOWN 1-FRAME RESIDUAL (architectural, not a translation bug):
            pr_note (the shared driver's note-trigger code, UNCHANGED here)
            always writes the note's flat STEADY frequency on the trigger
            frame itself and only starts applying FM_ACC delta the frame
            AFTER (see blackbird_driver.asm's pn_note comment) -- whereas
            real Blackbird's fx engine evaluates fx-program row 0 on the
            SAME frame as the note-on. So every FM-modulated note is
            shifted exactly 1 real frame late relative to real hardware.
            This is a pre-existing trait of the shared fm_step engine
            (shared by every other player using this driver family, not
            introduced here) -- documented, not silently absorbed.

See "Bundles" below for how FM+PULSE are selected per note (not per
instrument), and "Filter" for the SET/ADD row byte encoding (derived from
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
from blackbird_everyframe_sim import BlackbirdSim
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
CYCLE_SEARCH_FRAMES = 300   # > 256 states -> a repeat is guaranteed (pigeonhole)
TARGET_FM_PULSE_FRAMES = 250  # ~5s @ 50fps; PULSE/FM have no jump primitive


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
    Stage A never used for anything since it discards fx)."""
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
            note = b >> 1
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
                steps.append(BBStep('rest', None, None, cur_fx, False, ticks))
            else:
                steps.append(BBStep('note', None, None, cur_fx, False, ticks))
            continue
    return steps


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
# WAVE + PULSE translator (one instrument's ins_wave[i] program)
# ---------------------------------------------------------------------------
def unroll_wave_pulse(lay, d, la, ins_restart, ins_restart2, wave_start):
    sim = BlackbirdSim(lay, d, la, [b'', b'', b''], ins_restart, ins_restart2)
    v = sim.v[0]
    v.wavepos = wave_start & 0xFF
    v.wavemask = 0xFF              # gate on (bit6 pulse-row test is mask-invariant
                                    # -- wavemask only ever clears bit0, see BB sim's
                                    # everyframe(): `shifted,_=asl(d404v)`; bit6 of
                                    # d404v is untouched by 0xFE/0xFF masking)
    v.pwidth = 0
    positions, d404s, pulses = [], [], []
    for _ in range(CYCLE_SEARCH_FRAMES):
        positions.append(v.wavepos)
        sim.everyframe()
        d404s.append(sim.regs[4])
        pulses.append((sim.regs[2], sim.regs[3]))
    cyc_start, cyc_end = _find_cycle(positions)

    # WAVE: native $7f jump exists -> loop exactly, forever.
    wave_rows = [(d404s[k] & 0xFF, 0x00) for k in range(cyc_end)]
    wave_rows.append((0x7F, cyc_start))     # relative-to-program-start; the
                                             # builder absolutises it (see
                                             # gen_includes_song, same
                                             # convention as every other
                                             # native driver in this repo)

    # PULSE: fm_step/pulse_step have no jump primitive -> physically repeat
    # the cycle to cover TARGET_FM_PULSE_FRAMES, then freeze on the last
    # value (see module docstring's "PULSE" bullet).
    prefix = pulses[:cyc_end]
    cyc = pulses[cyc_start:cyc_end] or prefix or [(0, 0)]
    seq = list(prefix)
    while len(seq) < TARGET_FM_PULSE_FRAMES:
        seq += cyc
    pulse_rows = []
    for val, run in _rle(seq):
        pulse12 = ((val[1] & 0x0F) << 8) | val[0]
        pulse_rows.append((0x80 | ((pulse12 >> 8) & 0x0F), pulse12 & 0xFF, run))
    pulse_rows.append((0x7F, 0x00, 0x00))   # freeze holding the last value

    return wave_rows, pulse_rows, dict(
        cycle_start=cyc_start, cycle_len=cyc_end - cyc_start, prog_len=cyc_end)


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
                loop_row = k + 1
            break
    rows.append((0x7F, 0x00, loop_row))
    return rows


# ---------------------------------------------------------------------------
# FMTAB translator: (fx program row, note) -> DELTA-per-frame accumulator
# rows (see module docstring's "FMTAB" bullet for why this is delta, not
# absolute value, unlike WAVE/PULSE/FILTER).
# ---------------------------------------------------------------------------
def unroll_fm(lay, d, la, ins_restart, ins_restart2, fx_row, note):
    sim = BlackbirdSim(lay, d, la, [b'', b'', b''], ins_restart, ins_restart2)
    v = sim.v[0]
    v.fxpos = fx_row & 0xFF
    v.basepitch = (note << 2) & 0xFF
    positions, freqs = [], []
    for _ in range(CYCLE_SEARCH_FRAMES):
        positions.append(v.fxpos)
        sim.everyframe()
        freqs.append(sim.regs[0] | (sim.regs[1] << 8))
    cyc_start, cyc_end = _find_cycle(positions)
    steady = sim.freq_lsb(note + 24) | (sim.freq_msb(note + 24) << 8)
    offsets = [(f - steady) & 0xFFFF for f in freqs[:cyc_end]]

    cyc = offsets[cyc_start:cyc_end] or offsets or [0]
    seq = list(offsets)
    while len(seq) < TARGET_FM_PULSE_FRAMES:
        seq += cyc
    seq = seq[:max(TARGET_FM_PULSE_FRAMES, len(offsets))]

    deltas = []
    prev = 0
    for off in seq:
        deltas.append((off - prev) & 0xFFFF)
        prev = off

    rows = []
    for val, run in _rle(deltas):
        rows.append((val & 0xFF, (val >> 8) & 0xFF, run))
    rows.append((0x00, 0x00, 0x00))         # freeze: FM_ACC holds at its last value
    return rows, offsets == [0] * len(offsets)


# ---------------------------------------------------------------------------
# Bundle clustering: Fargo's FM offsets turn out to be genuinely note-
# dependent (empirically verified this session -- arpeggio deltas are
# nonlinear across the frequency table, so the SAME fx program gives
# different absolute Hz offsets for different notes; see this module's
# report for the measured example), so a per-(fx,note) bundle is required
# for correctness, not merely a safety fallback -- and Fargo alone produces
# more than the 64-slot $c0-$ff command cap. Per docs/players/PLAYBOOK.md's
# technique catalog ("greedy nearest-merge clustering... first proven on
# Galway's Rambo port"), merge the closest pairs (count-weighted L1 distance
# over a short reconstructed-trajectory signature) until the cap is met,
# rather than the much lossier "alias everything past the cap to bundle 0"
# fallback.
# ---------------------------------------------------------------------------
def _bundle_signature(fp, pp, n_fm=40, n_pulse=8):
    """A short, comparable numeric fingerprint for one (fm_prog, pulse_prog)
    bundle: the first n_fm frames of its RECONSTRUCTED absolute FM offset
    trajectory (undoing the delta/RLE encoding _rle+unroll_fm produced) plus
    the first n_pulse pulse values -- close signatures sound close."""
    offs = []
    acc = 0
    for lo, hi, dur in fp:
        delta = lo | (hi << 8)
        if delta >= 0x8000:
            delta -= 0x10000
        cnt = max(1, dur) if dur else (n_fm - len(offs))
        for _ in range(cnt):
            if len(offs) >= n_fm:
                break
            acc += delta
            offs.append(acc)
        if len(offs) >= n_fm:
            break
    while len(offs) < n_fm:
        offs.append(offs[-1] if offs else 0)
    pulses = []
    for b0, b1, b2 in pp:
        if (b0 & 0xFF) == 0x7F:
            break
        pulses.append(((b0 & 0x0F) << 8) | b1)
        if len(pulses) >= n_pulse:
            break
    while len(pulses) < n_pulse:
        pulses.append(pulses[-1] if pulses else 0)
    return offs + pulses


def cluster_bundles(bundle_list, target, counts=None):
    """bundle_list: [(fm_prog, pulse_prog), ...], already content-deduped
    (no two entries identical). Returns (new_bundle_list, remap) where
    remap[old_index] = new_index, len(new_bundle_list) <= target.

    counts[i] = how many real note-ONSET EVENTS (not just distinct
    (fx,note,instr) keys) actually play bundle_list[i] -- callers must supply
    real per-bundle onset tallies. Defaults to uniform (all 1) if omitted,
    reproducing the old unweighted behaviour exactly.

    COUNT-WEIGHTED merge, per docs/players/PLAYBOOK.md's technique catalog
    ("greedy nearest-merge clustering... count-weighted FM-contour L1... first
    proven on Rambo/Galway v3.12", see bin/build_galway_trace_song.py's own
    cluster_bundles for the reference implementation) -- NOT previously
    applied here. The old version picked the globally nearest PAIR by raw L1
    distance alone, so two bundles that happen to be numerically close but
    are each played by MANY notes could get merged just as readily as two
    bundles nobody would ever hear merged -- there was no bias toward
    sacrificing rarely-heard bundles first. Fixed by weighting the merge cost
    by min(weight_i, weight_j) (Galway's own `cost = fd * min(cnt[i],
    cnt[j])`), so a merge affecting fewer onset events is always preferred at
    equal or lesser distance, and the SURVIVING representative of a merged
    group is now the group's OWN most-played original member (not just
    whichever bundle index happened to start the group first) -- so the
    program that plays for a merged group is the one that sounds right for
    the majority of the notes using it."""
    n = len(bundle_list)
    if counts is None:
        counts = [1] * n
    if n <= target:
        return list(bundle_list), list(range(n))
    sigs = [list(map(float, _bundle_signature(fp, pp))) for fp, pp in bundle_list]
    groups = [[i] for i in range(n)]
    reps = [list(s) for s in sigs]
    weights = [max(1, counts[i]) for i in range(n)]

    def l1(a, b):
        return sum(abs(x - y) for x, y in zip(a, b))

    while len(groups) > target:
        best = None
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                dd = l1(reps[i], reps[j])
                cost = dd * min(weights[i], weights[j])
                if best is None or cost < best[0]:
                    best = (cost, i, j)
        _, i, j = best
        wi, wj = weights[i], weights[j]
        reps[i] = [(reps[i][k] * wi + reps[j][k] * wj) / (wi + wj)
                   for k in range(len(reps[i]))]
        weights[i] = wi + wj
        groups[i].extend(groups[j])
        del groups[j]; del reps[j]; del weights[j]

    remap = [0] * n
    new_bundles = []
    for gi, grp in enumerate(groups):
        # keep the group's OWN most-played member's real program (not an
        # average, and not just whichever merge happened to add first) --
        # the surviving sound should match what most of the group's onsets
        # actually expect to hear.
        rep_orig = max(grp, key=lambda k: counts[k])
        new_bundles.append(bundle_list[rep_orig])
        for oi in grp:
            remap[oi] = gi
    return new_bundles, remap


# ---------------------------------------------------------------------------
# Row builder: BBStep list -> D11Row list, with note/instrument/command
# (bundle index) columns. Command changes only emitted on genuine change,
# matching the existing instrument-column convention.
# ---------------------------------------------------------------------------
def steps_to_rows_native(steps, bundle_of):
    """bundle_of: dict[(fx, note, instrument)] -> command index (0-63)."""
    rows = []
    cur_instr = None
    cur_cmd = None
    for s in steps:
        n = max(1, s.ticks)
        if s.kind == 'rest':
            rows.extend(D11Row(note=SF2_GATE_OFF) for _ in range(n))
        elif s.kind == 'note' and s.note is None:
            rows.extend(D11Row(note=SF2_GATE_ON) for _ in range(n))
        else:
            note = max(SF2_NOTE_MIN, min(s.note + 9, SF2_NOTE_MAX))
            inst = None
            if s.instrument is not None and s.instrument != cur_instr:
                inst = s.instrument
                cur_instr = s.instrument
            key = (s.fx, s.note, cur_instr if cur_instr is not None else 0)
            cmd = bundle_of.get(key, 0)
            cmdcol = None
            if cmd != cur_cmd:
                cmdcol = cmd
                cur_cmd = cmd
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
# Native edit-area layout writer (mirrors build_romuzak_native_song's
# gen_includes_song, trimmed to the bundles-only path -- Blackbird B1 has no
# drum/SEEK instrument flags, so those branches are dropped).
# ---------------------------------------------------------------------------
def gen_includes_song(segs, ad_sr, wave_programs, filter_programs,
                      filter_flag_of, bundles, default_filter_program,
                      multispeed=1, tempo_sched_len=0):
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
    wave_cursor, wave_dedup = 0, {}
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

    # FM + PULSE bundles (per-note command $c0-$ff -> (FM prog, pulse prog))
    ifmlo_addr = gen.filter_addr + 3 * 256
    ifmhi_addr = ifmlo_addr + NFM
    ipulse_lo_addr = ifmhi_addr + NFM
    ipulse_hi_addr = ipulse_lo_addr + NFM
    fmtab_addr = ipulse_hi_addr + NFM

    fmdedup, fmtab = {}, bytearray()
    pdedup, pulsetab_tmp = {}, bytearray()
    fm_addr_of, p_addr_of = [], []
    for fp, pp in bundles[:NFM]:
        fk = tuple(fp)
        if fk not in fmdedup:
            fmdedup[fk] = fmtab_addr + len(fmtab)
            for e0, e1, e2 in fp:
                fmtab += bytes([e0 & 0xFF, e1 & 0xFF, e2 & 0xFF])
        fm_addr_of.append(fmdedup[fk])
    pulsetab_addr = fmtab_addr + len(fmtab)
    for fp, pp in bundles[:NFM]:
        pk = tuple(pp)
        if pk not in pdedup:
            pdedup[pk] = pulsetab_addr + len(pulsetab_tmp)
            for c0, c1, c2 in pp:
                pulsetab_tmp += bytes([c0 & 0xFF, c1 & 0xFF,
                                       0 if (c0 & 0xFF) == 0x7F else (c2 & 0xFF)])
        p_addr_of.append(pdedup[pk])
    fmtab, pulsetab = bytes(fmtab), bytes(pulsetab_tmp)
    need = pulsetab_addr + len(pulsetab) - B.EDIT_BASE
    if len(edit) < need:
        edit.extend(bytearray(need - len(edit)))
    for i in range(NFM):
        fa = fm_addr_of[i] if i < len(fm_addr_of) else fmtab_addr
        pa = p_addr_of[i] if i < len(p_addr_of) else (p_addr_of[0] if p_addr_of else pulsetab_addr)
        edit[(ifmlo_addr - B.EDIT_BASE) + i] = fa & 0xFF
        edit[(ifmhi_addr - B.EDIT_BASE) + i] = (fa >> 8) & 0xFF
        edit[(ipulse_lo_addr - B.EDIT_BASE) + i] = pa & 0xFF
        edit[(ipulse_hi_addr - B.EDIT_BASE) + i] = (pa >> 8) & 0xFF
    edit[fmtab_addr - B.EDIT_BASE:fmtab_addr - B.EDIT_BASE + len(fmtab)] = fmtab
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
        f.write(f"FMTAB = ${fmtab_addr:04x}\n")
        f.write(f"PULSETAB = ${pulsetab_addr:04x}\n")
        f.write(f"IFM_LO = ${ifmlo_addr:04x}\n")
        f.write(f"IFM_HI = ${ifmhi_addr:04x}\n")
        f.write(f"IPULSE_LO = ${ipulse_lo_addr:04x}\n")
        f.write(f"IPULSE_HI = ${ipulse_hi_addr:04x}\n")
        f.write(f"MULTISPEED = {max(1, int(multispeed))}\n")
        f.write(f"FILT_INIT_ROW = {filt_init_row}\n")
    return gen, bytes(edit), mdp, seq0


def write_freqtable(sim):
    """freqtable.inc indexed by SF2 note byte, using Blackbird's OWN
    steady freq_lsb/freq_msb table (validated byte-exact -- see
    blackbird_driver11.py's "Pitch" docstring section for the SF2 note =
    blackbird_note_idx + 9 calibration this reuses), PAL fallback outside
    the calibrated range."""
    words = [0] * 0x70
    for note_idx in range(0, 64):
        sf2note = note_idx + 9
        if sf2note > 0x6F:
            continue
        words[sf2note] = sim.freq_lsb(note_idx + 24) | (sim.freq_msb(note_idx + 24) << 8)
    for i in range(1, 0x70):
        if words[i] == 0:
            s = min(i - 1, 95)
            words[i] = FREQ_TABLE_LO[s] | (FREQ_TABLE_HI[s] << 8)
    with open(os.path.join(ROOT, "drivers_src", "blackbird", "freqtable.inc"), "w") as f:
        f.write("; Blackbird steady freq_lsb/freq_msb table (byte-exact), SF2 note = "
                "blackbird_note_idx + 9\n")
        for k in range(0, len(words), 8):
            f.write("        .word " + ", ".join(f"${w:04x}" for w in words[k:k + 8]) + "\n")


def playing_notes(packed):
    out, last = [], 0
    for n in unpack_sequence(packed):
        if SF2_NOTE_MIN <= n <= SF2_NOTE_MAX:
            last = n
        out.append(last)
    return out


def freq_of(note):
    return 0 if note == 0 else (FREQ_TABLE_LO[note - 1] | (FREQ_TABLE_HI[note - 1] << 8))


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

    # Which (fx, note, instrument) triples are actually used as note onsets?
    # key_counts tallies real onset EVENTS (not just distinct keys) -- used
    # below to weight bundle clustering toward sacrificing rarely-heard
    # bundles first (see cluster_bundles's docstring).
    used_keys = set()
    used_instr = set()
    key_counts = {}
    cur_instr_track = [None, None, None]
    for v in range(3):
        for s in steps_per_voice[v]:
            if s.kind == 'note' and s.note is not None:
                if s.instrument is not None:
                    cur_instr_track[v] = s.instrument
                instr = cur_instr_track[v] if cur_instr_track[v] is not None else 0
                used_instr.add(instr)
                key = (s.fx, s.note, instr)
                used_keys.add(key)
                key_counts[key] = key_counts.get(key, 0) + 1

    print(f"{os.path.basename(sid)}: nins(located)={lay.nins} used_instr={sorted(used_instr)} "
          f"distinct (fx,note,instr) onsets={len(used_keys)}")

    # --- per-instrument WAVE/PULSE/FILTER programs (used instruments only) ---
    wave_programs, pulse_of_instr, filter_programs, filter_flag_of = {}, {}, {}, {}
    wave_stats = {}
    for i in sorted(used_instr):
        wave_start = d[(lay.ins_wave - la) + i] if 0 <= (lay.ins_wave - la) + i < len(d) else 0
        wr, pr, stats = unroll_wave_pulse(lay, d, la, ins_restart, ins_restart2, wave_start)
        wave_programs[i] = wr
        pulse_of_instr[i] = pr
        wave_stats[i] = stats
        filt_start = d[(lay.ins_filt - la) + i] if 0 <= (lay.ins_filt - la) + i < len(d) else 0
        if filt_start != 0:
            filter_programs[i] = unroll_filter(lay, d, la, ins_restart, ins_restart2, filt_start)
            filter_flag_of[i] = True

    # Blackbird's filter position is ONE continuous global state that starts
    # at zp_filtpos=0 (real hardware) and is only ever REPOSITIONED (never
    # gated on/off) by a filt-carrying instrument's note-on -- so the
    # driver's own init position must be a genuinely translated program
    # too, not an arbitrary instrument's block placed at row 0 by
    # allocation coincidence (see blackbird_driver.asm's do_init comment).
    default_filter_program = unroll_filter(lay, d, la, ins_restart, ins_restart2, 0)

    # --- per (fx, note) FM programs, bundled with that onset's instrument's
    #     pulse program (command index selects BOTH, per pr_setprog) ---
    fm_of_fxnote = {}
    fm_flat_count = 0
    bundle_list = []            # [(fm_prog, pulse_prog), ...] -- content-deduped, UNCAPPED
    bundle_content_idx = {}     # (tuple(fm), tuple(pulse)) -> raw index into bundle_list
    bundle_counts = []          # bundle_counts[i] = total real onset EVENTS using bundle i
    raw_bundle_of = {}          # (fx, note, instr) -> raw index into bundle_list
    for (fx, note, instr) in sorted(used_keys):
        fxn_key = (fx, note)
        if fxn_key not in fm_of_fxnote:
            fx_row = 0
            if fx != 0:
                nfx = lay.filttable - lay.fx_start
                if 1 <= fx <= nfx:
                    fx_row = d[(lay.fx_start - la) + (fx - 1)]
            fm_rows, is_flat = unroll_fm(lay, d, la, ins_restart, ins_restart2, fx_row, note)
            fm_of_fxnote[fxn_key] = fm_rows
            fm_flat_count += 1 if is_flat else 0
        fm_prog = fm_of_fxnote[fxn_key]
        pulse_prog = pulse_of_instr.get(instr) or [(0x88, 0x00, 1), (0x7F, 0, 0)]
        bkey = (tuple(fm_prog), tuple(pulse_prog))
        if bkey not in bundle_content_idx:
            bundle_content_idx[bkey] = len(bundle_list)
            bundle_list.append((fm_prog, pulse_prog))
            bundle_counts.append(0)
        idx = bundle_content_idx[bkey]
        bundle_counts[idx] += key_counts.get((fx, note, instr), 1)
        raw_bundle_of[(fx, note, instr)] = idx

    print(f"  {len(fm_of_fxnote)} distinct (fx,note) FM programs "
          f"({fm_flat_count} flat/no-modulation), {len(bundle_list)} distinct bundles "
          f"(content-deduped, before the {NFM}-slot cap), "
          f"{len(filter_programs)} instruments with a filter program")

    # $c0-$ff gives 64 command slots; Fargo alone can exceed that (see module
    # docstring's clustering note) -- greedy-nearest-merge down to the cap
    # rather than aliasing overflow bundles onto an unrelated one. Weighted by
    # real onset-event counts (bundle_counts) so rarely-heard bundles are
    # sacrificed before frequently-played ones (see cluster_bundles's
    # docstring for why this wasn't already happening).
    bundle_list, remap = cluster_bundles(bundle_list, NFM, counts=bundle_counts)
    bundle_of = {k: remap[v] for k, v in raw_bundle_of.items()}
    if len(remap) != len(set(remap)) or max(remap, default=0) >= NFM:
        pass  # remap always <= NFM by construction; sanity note only
    n_merged = len(raw_bundle_of and set(raw_bundle_of.values())) - len(bundle_list)
    print(f"  bundles after clustering: {len(bundle_list)} "
          f"(merged {max(0, n_merged)} pairs to fit the {NFM}-slot command space)"
          if n_merged > 0 else f"  bundles: {len(bundle_list)} (within the {NFM}-slot cap, no clustering needed)")

    # --- D11Row tracks ---
    tracks = [steps_to_rows_native(steps_per_voice[v], bundle_of) for v in range(3)]
    segs = [segment_track(tracks[v]) or [bytes([0x7F])] for v in range(3)]

    # --- AD/SR for every located instrument slot (cheap, real data, no
    #     unrolling needed) ---
    nins = max(1, min(lay.nins, 32))
    ad_sr = []
    for i in range(nins):
        ad = d[(lay.ins_ad - la) + i] if 0 <= (lay.ins_ad - la) + i < len(d) else 0
        sr = d[(lay.ins_sr - la) + i] if 0 <= (lay.ins_sr - la) + i < len(d) else 0
        ad_sr.append((ad, sr))

    # B2: model the song's FIRST tempo/groove pair as a real 2-value swing
    # (TEMPO=long, TEMPO2=short), via the driver's SWTOG toggle (ported from
    # drivers_src/mon). Fargo's other ~20 mid-song tempo-change records are a
    # documented B3 gap, not modelled here.
    #
    # NOT using sidm2.blackbird_driver11.estimate_tempo_chain() here -- built
    # and cross-checked this pass against the validated simulator's own
    # real_frame() row-boundary timing (dumped zp_master at each do_row-
    # equivalent commit over 200 real frames) and found a real off-by-one:
    # the dispatch loop's `cpx #3*7` 3-slot prepare reservation means real
    # frames/tick = tempo_byte // 7 + 1, NOT tempo_byte // 7 -- confirmed
    # empirically (committed zp_master=35 -> next tick 6 real frames later,
    # =28 -> 5 frames later, exactly matching //7+1, not //7). This is the
    # same "+1 footnote" BLACKBIRD.md's Stage-B section already flagged as
    # unresolved; `estimate_tempo_chain()` (and therefore Stage A's tempo,
    # and this driver's FIRST build of B2) is off by one frame per row as a
    # result -- Stage A itself is NOT fixed here (out of this task's scope,
    # and its output was already user-audio-confirmed acceptable at Stage A's
    # coarser fidelity bar), but the native driver uses the corrected values
    # directly via extract_tempo_pairs() (raw bytes, pre-division) instead of
    # propagating the same bug forward.
    pairs = extract_tempo_pairs(d, la, lay.streamstart)
    if pairs:
        a, b = pairs[0]
        chain = [max(1, a // 7 + 1), max(1, b // 7 + 1)]
        if chain[0] == chain[1]:
            chain = [chain[0]]
    else:
        chain = [5]  # DEFAULT_TICK_FRAMES fallback, matches Stage A's own default
    B.TEMPO = max(1, chain[0])
    B.TEMPO2 = max(1, chain[1]) if len(chain) > 1 else B.TEMPO
    print(f"  tempo chain (corrected, //7+1) = {chain}; do_init seeds "
          f"CUR_TEMPO={B.TEMPO}/CUR_TEMPO2={B.TEMPO2} (song-opening pair)")

    # B3: the FULL row-indexed mid-song tempo schedule (see extract_tempo_
    # schedule()'s docstring above) -- do_row applies each entry the instant
    # its ROW_CNT is reached, exactly where real hardware's own OOB record
    # would have landed. Driven by the SAME real decoded streams as every
    # other translator in this module (checked FIRST, per this task's own
    # instructions, whether this would even move the existing 200-frame
    # comparison window's number -- it doesn't, the first tempo pair holds
    # the whole window; the drift only shows up past ~1895 frames, see the
    # extended-window report below).
    tempo_schedule = extract_tempo_schedule(
        lay, d, la, ins_restart, ins_restart2, result.voices)
    n_sched = write_tempo_schedule(tempo_schedule)
    print(f"  tempo schedule: {n_sched} row-indexed mid-song tempo/groove "
          f"records (first at row {tempo_schedule[0][0] if tempo_schedule else '-'}, "
          f"last at row {tempo_schedule[-1][0] if tempo_schedule else '-'})")

    gen, edit, mdp, seq0 = gen_includes_song(
        segs, ad_sr, wave_programs, filter_programs, filter_flag_of, bundle_list,
        default_filter_program, tempo_sched_len=n_sched)

    # freqtable.inc from the SAME sim class (pure table reads, no state needed)
    sim_for_freq = BlackbirdSim(lay, d, la, [b'', b'', b''], ins_restart, ins_restart2)
    write_freqtable(sim_for_freq)

    prg = B.assemble()
    names = [f"instr {i:02d}" for i in range(len(ad_sr))]
    sf2 = B.wrap(prg, gen, edit, mdp, instr_names=names)
    out = os.path.join(ROOT, "out", "blackbird",
                       os.path.splitext(os.path.basename(sid))[0] + "_native.sf2")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "wb").write(sf2)
    print(f"wrote {out} ({len(sf2)} bytes); tables top ~${gen.filter_addr:04X}")

    from sidm2.models import SF2DriverInfo
    from sidm2 import sf2_parser
    di = SF2DriverInfo()
    pla = sf2_parser.parse_sf2_blocks(bytearray(sf2), di)
    print(f"PARSE: load=${pla:04X} tracks={di.track_count}",
          "OK" if pla == 0x0D7E else "FAIL")

    # --- Coarse sanity check: does SOMETHING recognisable play? Only a loose
    # gate -- Blackbird has genuine per-frame FM/arpeggio (unlike ROMUZAK's
    # near-static pitch this harness's tolerance was designed for), so a
    # snapshot several frames into a tick can legitimately sit far from the
    # flat note frequency. The real validation is the register-trace
    # comparison against the simulator below (task's "most important" check).
    exp = [playing_notes(segs[v][0]) for v in range(3)]
    B.N_ROWS = 12
    rows = B.headless_audio(prg, edit)
    nonzero = sum(1 for r in rows for v in range(3) if r[v] != 0)
    print(f"  coarse sanity: {nonzero}/{3*len(rows)} voice-rows produced a nonzero "
          f"frequency (informational only, see the register-trace comparison below "
          f"for the real fidelity measurement)")

    # --- Real validation: compare the ASSEMBLED driver's actual per-frame
    # $D400-$D418 register trace against the VALIDATED SIMULATOR's own trace
    # for the SAME file, driven by the SAME real decoded note stream (not a
    # synthetic one) -- task's point (c), "most important". B3: the driver
    # now applies the FULL row-indexed tempo schedule (not just the first
    # pair) -- see extract_tempo_schedule() above. Drift can still accumulate
    # from the shared engine's inherent 1-frame FM lag on note trigger
    # (architectural, not a bug) and the other named B1/B2 residuals below.
    import blackbird_everyframe_sim as sim_mod
    N_CMP = 200   # kept identical to B1/B2's own window for direct comparability
    tempo_records = sim_mod.find_tempo_records(lay, d, la)

    def compare(n_frames):
        real_sim = sim_mod.BlackbirdSim(lay, d, la, result.voices, ins_restart,
                                        ins_restart2, tempo_debug=list(tempo_records))
        sim_frames = [real_sim.real_frame() for _ in range(n_frames)]
        drv_frames = B.headless_trace(prg, edit, n_frames)
        return sim_frames, drv_frames

    REGS_TO_CHECK = list(range(25))   # all of $D400-$D418
    # per-category breakdown (freq/waveform/pulse/ad-sr/filter), matching the
    # granularity of the original B1 build report -- helps tell WHICH engine
    # a tempo/translation change actually moved, not just the blended total.
    CATS = {
        'freq': [0, 1, 7, 8, 14, 15], 'waveform': [4, 11, 18],
        'pulse': [2, 3, 9, 10, 16, 17], 'adsr': [5, 6, 12, 13, 19, 20],
        'filter': [21, 22, 23, 24],
    }

    def report_window(sim_frames, drv_frames, lo, hi, label):
        n = hi - lo
        if n <= 0 or hi > len(sim_frames):
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
        print(f"  {label} [{lo}:{hi}) n={n}: overall={avg_match*100:.1f}%  {cats_str}  "
              f"(exact frames {exact_frames}/{n}, first mismatch @{first_diverge})")
        return dict(exact_frames=exact_frames, avg_match=avg_match,
                    first_diverge=first_diverge)

    sim_frames, drv_frames = compare(N_CMP)
    print(f"\n  REGISTER-TRACE COMPARISON vs validated simulator ({N_CMP} frames, "
          f"{len(REGS_TO_CHECK)} registers = {len(REGS_TO_CHECK)*N_CMP} cells):")
    primary = report_window(sim_frames, drv_frames, 0, N_CMP, "primary window")
    print("    first 10 frames (sim vs driver, $D400/1 freq v0, $D404 wave v0, "
          "$D416 cutoff):")
    for f in range(min(10, N_CMP)):
        sr, dr = sim_frames[f], drv_frames[f]
        sfreq = sr[0] | (sr[1] << 8)
        dfreq = dr[0] | (dr[1] << 8)
        print(f"      f{f:3d}: sim freq0=${sfreq:04X} wf0=${sr[4]:02X} cut=${sr[22]:02X}"
              f"   drv freq0=${dfreq:04X} wf0=${dr[4]:02X} cut=${dr[22]:02X}"
              f"   {'MATCH' if sr==dr else 'diff'}")

    # --- B3: EXTENDED-window comparison, specifically crossing a real
    # mid-song tempo-change boundary, so the schedule mechanism's effect is
    # actually measurable (task's instruction: check this before/instead of
    # just trusting the 200-frame number, which per this task's own recon
    # never crosses a boundary in the first place -- Fargo's first mid-song
    # change lands at real frame ~1895, Glyptodont's second/last at ~11738).
    ext_result = None
    if len(tempo_schedule) > 1:
        boundary_frame = tempo_schedule[1][3]
        ext_cmp = min(3000, boundary_frame + 500)
        if ext_cmp > boundary_frame:
            print(f"\n  EXTENDED-WINDOW COMPARISON (crosses the real mid-song tempo "
                  f"change at frame {boundary_frame}, row {tempo_schedule[1][0]}):")
            esim, edrv = compare(ext_cmp)
            report_window(esim, edrv, 0, min(N_CMP, ext_cmp), "pre-change (0-200)")
            report_window(esim, edrv, N_CMP, boundary_frame, "pre-change (200-boundary)")
            ext_result = report_window(esim, edrv, boundary_frame, ext_cmp, "POST-CHANGE")
            report_window(esim, edrv, 0, ext_cmp, "full extended window")
        else:
            print(f"\n  (mid-song tempo change at frame {boundary_frame} is beyond the "
                  f"{3000}-frame extended-comparison cap -- not exercised this pass)")
    else:
        print(f"\n  (only {len(tempo_schedule)} tempo record(s) found -- no mid-song "
              f"change to cross, extended-window comparison skipped)")

    return dict(lay=lay, d=d, la=la, ins_restart=ins_restart, ins_restart2=ins_restart2,
                prg=prg, edit=edit, sf2=sf2, tempo=B.TEMPO,
                exact_frames=primary['exact_frames'], avg_match=primary['avg_match'],
                first_diverge=primary['first_diverge'], ext_result=ext_result)


if __name__ == "__main__":
    main()
