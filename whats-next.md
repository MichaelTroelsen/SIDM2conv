<original_task>
Session opened with: "load fargo and start tracing" — load `SID/LFT/Fargo.sid`
(a Blackbird/lft-player SID file) into the RetroDebugger MCP tool set and begin
live 6502 tracing. This grew, by the user's own continued direction across
several sessions ("please do Glyptodont", "keep pushing on the decompression
bug", "move forward", "can you do a lft song into SF2", "continue the work
from B10", etc.), into a full reverse-engineering + native-driver-porting
effort for the **Blackbird player** (Linus Åkesson / "lft") — a player family
that had only "recon, locate solved, decompression open" status before this
arc began (per `docs/players/BLACKBIRD.md`'s original opening line).

**This file was stale as of 2026-07-20**: it previously only covered through
Stage A (commit `dfb8241`) and said "Stage B: NOT STARTED". In fact Stage B
(the native 6502 driver) has since shipped rounds B1 through B10 in
subsequent sessions the same day. This rewrite brings it current. The
authoritative, most-detailed source is always `docs/players/BLACKBIRD.md` —
read that first if resuming; this file is a compressed handoff, not a
replacement.
</original_task>

<work_completed>
## 1-7. Everything through Stage A — see `docs/players/BLACKBIRD.md` for detail

Briefly, all shipped/committed/verified in earlier sessions (commits
`095f59d`..`dfb8241`), and still true/current:
- **Decompression fully solved**: the interleaved 3-voice compressed stream's
  true bug was stream-terminator handling (`zp_inptr` freezes permanently at
  the real end-of-stream byte; every voice re-reads the same frozen byte
  forever, appending grammar-safe `$C0` filler). Verified against 2 live
  RetroDebugger CPU traces (committed fixtures:
  `SID/blackbird_fargo_trace_4199_5371.json`,
  `SID/blackbird_glyptodont_trace_4248_5026.json`) via a strict unique-
  contiguous-match check, plus a clean 11-file v1.2-exact-bucket sweep.
- **Tempo/groove model solved**: self-modifying XOR alternation between two
  `zp_tempo` values, `frames_per_cycle = tempo_byte // 7 + 1` (the `+1` was
  MISSING in the originally-documented formula and in
  `estimate_tempo_chain()` — found and fixed for the **native driver** during
  B2, see below; **Stage A's own `estimate_tempo_chain()` in
  `sidm2/blackbird_driver11.py` still has the un-fixed off-by-one** — a small
  standing gap, not touched by any B-round since B-rounds work on the native
  driver's own separate table-extraction path).
- **`sidm2/blackbird_parser.py`** (locate/decompress/grammar-classify) and
  **`pyscript/test_blackbird_parser.py`** (9 tests/27 subtests) — production,
  shipped, all passing.
- **`sidm2/blackbird_driver11.py`** — Stage A (Driver 11 transpile): notes/
  timing/pitch correct (user-audio-confirmed via `sf2_open_in_editor.py`),
  timbre deliberately flat (default instruments) per the Stage-A ceiling.
- **`docs/guides/RETRODEBUGGER_GUIDE.md`** — full MCP tool reference,
  including the `.sf2`-won't-`retro_load` gotcha (use `.prg` rename) and the
  "SYS via raw jump doesn't start playback" caveat.
- **`docs/SID_TO_SF2_CONVERSIONS.md`** + `pyscript/gen_conversion_index.py` —
  maintained conversion index, separate side task, still current (regenerate
  after any future conversion).
- Memory: `memory/blackbird-lft-player.md` has the full granular trail;
  `MEMORY.md` stays compacted.

## 8. Stage B — native 6502 driver, B1 through B10 shipped

Per `docs/players/PLAYBOOK.md`'s ladder, Stage B means a from-scratch fork of
the shared native-driver engine (same base as ROMUZAK/MoN/Galway) targeting
real per-frame byte-exact register output, not Stage A's flat defaults. This
is now real and building for 2 files. **Key files**:
- `drivers_src/blackbird/blackbird_driver.asm` — the forked 6502 driver
  (started from `romuzak_driver.asm`; DIGI engine stripped)
- `bin/blackbird_everyframe_sim.py` — the validated Python simulator of
  `player.s`'s `everyframe`/`execute`/`prepare1-3` pipeline; this is the
  **formula oracle** every table translator calls into rather than
  hand-rederiving 6502 carry/asl/ror bit tricks
- `bin/build_blackbird_native_song.py` — the translator (decoded event
  stream + simulator → driver tables) and `bin/build_blackbird_driver_full.py`
  — assemble/wrap harness
- Output: `out/blackbird/Fargo_native_part01.sf2`,
  `out/blackbird/Glyptodont_native_part01.sf2` (both single-part as of B10)

**The synth engine itself was RE'd and validated 100% byte-exact FIRST**
(before any driver code was written): a from-scratch Python simulator
reproduces 14,673/14,673 (Fargo) and 18,332/18,332 (Glyptodont) real
$D400-$D418 writes in exact order/value over 1200 real frames each, checked
against real hardware via the `vsid-trace.js` escape hatch (zig64 reports 0
writes for Blackbird — a separate, still-open, still-undiagnosed gap, see
Work Remaining). This simulator is what B1-B10 all built on top of.

**Round-by-round summary** (full detail, bug-by-bug, in
`docs/players/BLACKBIRD.md` — search for "## B1" through "## B10 shipped"):

| Round | What it did | Fargo overall | Glyptodont overall |
|---|---|---|---|
| B1 | First native driver + translator, FM as absolute-offset table | 55.1% (200f) | — |
| B2 | Fixed real tempo alternation (`//7 + 1` bug found) | 59.9% (200f) | — |
| B3/B4 | Full mid-song tempo schedule (22 records, not just first pair); 4 real bugs fixed | ~70% | ~54% |
| B5-B7 | 3 more pulse/filter bugs; adaptive part-splitting; part-boundary state priming | — | multi-part |
| B8 | PULSE decoupled from the FM bundle (hardware ties it to the INSTRUMENT, not FM); 4 more bugs | **94.1%** (3000f) | — |
| B9 | Pulse-width ACCUMULATOR ported into the driver (lft's own structure, not a recorded table) | — | **82.7%** (10 parts) |
| **B10** | fx/pitch interpolator ported into the driver (lft's own 4-mode table lookup, note-independent) | **94.9%** (3000f) / **78.8%** (20,550f whole song) | **91.4%** (1 part, whole song, 20,223f) — **10 parts → 1** |

**B10 is the most recent shipped round** (commit `37b21f7`). It deleted the
old `fm_step` accumulator entirely (a *recording* of absolute frequency
offsets, which was note-dependent and needed one command slot per
`(fx-program, note)` pair — 423 slots for Glyptodont, 85% of which had to be
lossy-clustered to fit the 64-slot cap) and replaced it with `fx_step`, a
direct port of lft's real interpolator running over the real
`freq_lsb`/`freq_msb` tables. This made the command column **note-independent**
(just Blackbird's own fx-program index — Fargo 32 slots of nfx=35, Glyptodont
47 slots of nfx=47, **zero clustering needed on either file now**), which is
also why Glyptodont's part count collapsed from 10 to 1 (the old per-note
clustering was fragmenting it into 64-slot-limited chunks; removing the need
for clustering removed the fragmentation). It also eliminated the 1-frame
note-trigger pitch lag by construction (no accumulator to prime) — verified
via a ±2-frame sweep showing shift-0 as a strict local maximum on all 3
Fargo voices.

**B11 shipped in THIS session** (2026-07-20, right after this file was
written): fixed B10's own named dominant residual, "fx changes on rest/
sustain rows deferred to next note onset" (27% of Fargo's fx changes, 7% of
Glyptodont's, were landing on non-note rows and getting silently dropped/
deferred). Root cause verified directly against `player.s`: `prepare1`
writes `v_pendfx` DIRECTLY on any row with a fresh select byte, and
`execute()` applies+clears it unconditionally every tick — independent of
`prepare3`'s separate note-only mirror (which the driver's pre-existing
`pn_tied` already modeled correctly). TWO fixes were needed together (a
driver-side commit AND a translator-side row-emission fix — fixing only one
would have been a no-op): `drivers_src/blackbird/blackbird_driver.asm` (new
`fxflag` + `maybe_fx_commit`) and `bin/build_blackbird_native_song.py`'s
`steps_to_rows_native` (the fx-change check was only inside the note branch).
Full detail: `docs/players/BLACKBIRD.md`'s "B11 shipped" section,
`memory/blackbird-stage-b-native.md`.

**B12 shipped SAME session, right after B11** (2026-07-20): targeted B11's
own named next residual, Fargo's weak full-song pulse/adsr. Added a
permanent diagnostic harness to the build script (`BB_DIAG_BIN`/`BB_DIAG_LO`/
`BB_DIAG_HI`/`BB_DIAG_REG` env vars) and used it to discover "weak
pulse/adsr" was actually TWO unrelated bugs: (1) **voice 2 has a full,
PERMANENT instrument-state desync starting ~frame 8000** in Fargo — root
cause NOT found, needs a fresh live trace, this is now THE dominant open
issue; (2) voice 1's pulse was phase-shifted by exactly 1 real frame — this
one WAS root-caused (against `player.s`'s `prepare2`/`prepare3`/`execute()`
directly) and fixed: a standalone instrument-select byte with no note nearby
was silently deferred (or, if the eventual note was tied, dropped outright)
because the native driver only restarted WAVE/FILTER/ADSR/GATE at
note-trigger time (`pn_note`), not immediately like real hardware's
`execute()` does. Same two-halves pattern as B11: driver fix in
`set_instr_v` (GATE+FILTER now restart immediately) plus a translator fix in
`bb_steps_for_voice` (pending instrument/tie state no longer leaks across
multiple intervening rest/hold rows onto an unrelated later note). One
finding was EMPIRICAL, not fully explained: also restarting the wave-row
cursor (VWI) immediately — which is what `player.s`'s literal source
suggests is needed — fixed the same bug but REGRESSED pulse; leaving VWI out
(still only reset by `pn_note`) was measurably better on every count. Full
detail + the open question: `docs/players/BLACKBIRD.md`'s "B12" section.

**Honest current fidelity, post-B12** (whole-song, matched-frame-coverage —
see `docs/players/BLACKBIRD.md`'s B12 section for full per-category tables):
- **Fargo** (20,550 frames, 1 part): overall 79.5%, **freq 100.0% (exact)**,
  waveform 77.0%, **pulse 51.6%, adsr 74.7%** (both still weak — dominated by
  voice 2's unexplained desync from ~frame 8000 onward; a 3000-frame window
  flatters both to ~90/98 — always quote the window).
- **Glyptodont** (20,223 frames, 1 part): overall 92.0%, freq 99.7%, waveform
  93.5%, pulse 77.7%, adsr 96.2%, filter 94.7%.

**Verification discipline established across all B-rounds** (worth
preserving as a pattern): every round's translator change is checked against
`bin/blackbird_everyframe_sim.py` (the independently-validated oracle), not
against "does it sound plausible" — e.g. B10 shipped with `verify_fx_engine()`,
which replays the driver's own emitted tables through the same arithmetic
the simulator uses, for EVERY frame of EVERY (fx-program, note) pair the
build can produce (302,400 comparisons for Fargo, 705,600 for Glyptodont),
run on every build, with negative controls confirming the gate has teeth
(a deliberately-corrupted table fails; a deliberately-truncated one throws).
This "exact-by-construction gate, checked on every build, with a negative
control" pattern is the standard to match for any future B-round.
</work_completed>

<work_remaining>
## The honest B12 punch list (start here for the next round)

1. **DONE (B11, this session)**: fx changes on a rest or tie used to be
   deferred to the next note onset. Fixed in both the driver and the
   translator — see the B11 summary above. Fargo freq is now exact (100.0%).
2. **DONE, PARTIALLY (B12, this session)**: Fargo's full-song pulse/adsr
   weakness turned out to be two unrelated bugs. Fixed: a standalone
   instrument-select with no note nearby was silently deferred/dropped
   (same pattern as B11's fx bug). NOT fixed, and now the biggest open
   item: **voice 2 in Fargo has a full, permanent instrument-state desync
   starting ~frame 8000** (ctrl/AD/SR/pulse all wrong, flatlines at a
   constant wrong value for the rest of the song). This needs a fresh LIVE
   hardware trace targeted at that specific region — B12's own
   `BB_DIAG_LO`/`BB_DIAG_HI`/`BB_DIAG_REG` env vars (in
   `bin/build_blackbird_native_song.py`) are the tool to localize the exact
   triggering frame/event first, the same way B12's own bug was found.
   Also unexplained: why leaving VWI's restart OUT of `set_instr_v` measures
   better than including it, even though `player.s`'s literal source reads
   as if it's needed there — worth revisiting with a live trace too.
3. **The FXTAB `+1` guard byte is unexercised** by either file (confirmed via
   B10's own negative-control table) — defensive only, not a gap to close.
4. **`CAP_B` is retained but now inert** post-B10 (clustering no longer binds
   on either file); if a future file has `nfx >= 64` the build correctly
   RAISES rather than silently clustering, but there's no note-independent
   fx-clustering pass built for that case if one is ever needed.
5. **Only Fargo + Glyptodont have been built natively.** The other 9
   v1.2-exact-bucket files (Dishwasher_Groove, Dithered_Island, Elvendance,
   Euclid_Was_Here, Into_the_Unknown, Maple_Leaf_Rag,
   Revolutions_Delivered, Thus_Spoke_the_PC_Speaker, Toy_Rocket) are
   untried on the native driver (Stage A covers all 11, native driver only 2).
6. **Not wired into `DriverSelector`** — deliberate, fidelity not yet judged
   sufficient vs. other players' native drivers.
7. **The native driver's audio has never been listened to** — only Stage A's
   coarser output has been ear-confirmed (the "notes correct, timbre flat"
   finding). Should use `pyscript/sf2_open_in_editor.py` per the established
   convention (RetroDebugger cannot reliably load/run `.sf2` files — see the
   RetroDebugger guide's gotchas section).

## Older, still-open items not superseded by B-work

- **zig64 reports 0 SID writes for Blackbird files** despite them being
  normal well-formed PSIDs that play fine under RetroDebugger/VICE — still
  never diagnosed WHY (the `vsid-trace.js` escape hatch is the working
  substitute and is what all B-round validation uses instead). A gap in a
  shared project tool, not Blackbird-specific — fixing it would help future
  work on any player, not just this one.
- **Near-v1.2 variant buckets (~16 files) are not supported at all** —
  `locate_blackbird()` correctly returns `None` for them (regression-tested),
  but no work exists to locate/support them. Would need an alternate
  relocation-manifest template from an older birdcruncher release (only
  v1.2's template is bundled in this repo), or hand disassembly RE.
- **7 "much-older/uncertain" files** — diverge almost from byte 3, not
  investigated, possibly pre-1.0 or a different engine entirely.
- **Stage A's `estimate_tempo_chain()` off-by-one is still unfixed** (see
  "1-7" above — the native driver bypasses it with its own corrected
  extraction, but Stage A's own output for OTHER files still uses the wrong
  formula). Small, well-scoped, independent of the B-round work.
- **Instrument-index clamping (48→32) downstream correctness** was never
  audited against actual note references in a file that uses instrument
  index 32-34 — worth a quick check if a future file's Stage A output sounds
  wrong in specific sections.
</work_remaining>

<critical_context>
## Key file locations (git repo, all committed as of `37b21f7`)
- `docs/players/BLACKBIRD.md` — **the authoritative, most detailed doc, read
  this FIRST**; has exact source-line citations, byte-level arithmetic, and a
  "What's genuinely proven vs. still open" summary kept current after every
  round (currently ends after B10).
- `sidm2/blackbird_parser.py` — locate + decompression (production)
- `sidm2/blackbird_driver11.py` — Stage A IR-mapping (production, has the
  known un-fixed tempo-chain off-by-one noted above)
- `pyscript/test_blackbird_parser.py` — Stage-A-era test suite (9/27 subtests)
- `drivers_src/blackbird/blackbird_driver.asm` — the native Stage B driver
  (forked from `romuzak_driver.asm`)
- `bin/blackbird_everyframe_sim.py` — the validated engine simulator, the
  formula oracle every table translator uses
- `bin/build_blackbird_native_song.py` — the native-driver table translator
- `bin/build_blackbird_driver_full.py` — assemble/wrap harness (this is
  almost certainly the entry point to invoke for a B11 rebuild)
- `out/blackbird/Fargo_native_part01.sf2`,
  `out/blackbird/Glyptodont_native_part01.sf2` — current native build output
  (regeneratable via the build script, check if these are committed or
  build artifacts before assuming they're current post-B10)
- `SID/blackbird_fargo_trace_4199_5371.json`,
  `SID/blackbird_glyptodont_trace_4248_5026.json` — committed live-CPU
  ground-truth fixtures (decompression-era, still used by the test suite)

## Non-obvious facts worth remembering (still true, carried from earlier sessions)
- `zp_base=$E0`, `unpackvoice=$1259`, `zp_inptr=$E2/$E3` identical across all
  v1.2-exact-bucket files.
- Real tempo formula is `tempo_byte // 7 + 1` (the `+1` matters — B2 found
  this the hard way; Stage A's `estimate_tempo_chain()` still lacks it).
- `freq_msb`/`freq_lsb` live at fixed template offsets 817/(817+96); as of
  B10 these plus `pwprepare` (offset 1024) are emitted as ONE contiguous
  463-byte blob (`FREQBLOB`) because 16-bit-indexed reads legitimately run
  past each table's nominal extent into the next one — don't re-truncate
  this if touching the blob again.
- `retro_load` cannot load `.sf2` directly — rename to `.prg` first; even
  then, a raw `retro_cpu_jump` to the SYS entry doesn't reliably start
  playback (BASIC's real `SYS` command does setup a raw jump skips) — use
  `pyscript/sf2_open_in_editor.py` for real audio verification instead.
- `retro_reset` is confirmed non-functional (twice) — don't rely on it.
- Always zero `$D400-$D418` via `retro_memory_write` before ending a turn
  that loaded/played anything audible in RetroDebugger.
- User's standing preference (`feedback-accuracy-over-speed.md` in memory):
  max accuracy over speed, verify agent claims independently rather than
  trusting reports at face value, quote the measurement window explicitly
  whenever citing a fidelity percentage (short windows have repeatedly been
  shown to flatter real numbers — e.g. Fargo pulse 90.8% @3000f vs 52.0%
  whole-song).

## Where the previous session's ephemeral/scratch files were (likely stale/gone)
Earlier Stage-A scratch builds and B1-era simulator/comparison scripts lived
in per-session scratchpad directories under
`C:\Users\mit\AppData\Local\Temp\claude\C--Users-mit-claude-c64server-SIDM2\`
— these are NOT committed and a fresh session will not have them. By B10,
the simulator (`bin/blackbird_everyframe_sim.py`) and translator
(`bin/build_blackbird_native_song.py`) were promoted into the real repo, so
this matters much less than it used to — check `bin/` and
`drivers_src/blackbird/` first before assuming anything needs regenerating
from scratch.
</critical_context>

<current_state>
## Deliverables status (as of 2026-07-20, B11 committed / B12+B13 shipped THIS session, neither committed yet)
- Decompression, tempo model, `blackbird_parser.py`, Stage A
  (`blackbird_driver11.py`): **COMPLETE**, committed, tested, user-audio-verified.
- `docs/guides/RETRODEBUGGER_GUIDE.md`, `docs/SID_TO_SF2_CONVERSIONS.md`:
  **COMPLETE**, committed.
- **Stage B native driver: IN PROGRESS, B1 through B13 shipped.** Fargo
  79.2% (freq 99.7%) / **Glyptodont 97.6%** (freq 99.5%, pulse 99.7%)
  overall register match, whole-song, both single-part SF2s. Not yet
  audio-listened, not wired into `DriverSelector` (deliberate).
- **B11 is committed** (`83af9b3`). **B12 AND B13 are UNCOMMITTED** — see
  "What's committed vs. not" below.
- **B13, this session**: what started as a Glyptodont-focused recon (a real
  VICE live hardware trace through frame 10300, plus live `py65` single-step
  CPU tracing) initially mis-attributed the residual to a driver-side "wave
  restart" bug — that framing was WRONG, caught by pushing one step further
  (instrumenting the continuous simulator's own internal state, not just
  final register output). The TRUE root cause: `bb_steps_for_voice`
  (the translator, `bin/build_blackbird_native_song.py`) ignored its own
  `gate_is_off` flag whenever the very next byte was a NOTE rather than a
  delay — so `[gate_off][note]` (a real, if uncommon, Blackbird grammar
  pattern meaning "voice goes silent, note value discarded, no restart")
  was wrongly emitted as a genuine active-note restart. First fix attempt
  regressed Glyptodont 92.0%→73.2% (way too broad), which caught a SECOND,
  companion bug: the 'delay' branch never RESET `gate_is_off` after using
  it, so it rode across unbounded runs of delay events instead of only the
  one event immediately following the gate-off. Both branches now correctly
  consume-and-reset the flag. **Result: Glyptodont 92.0%→97.6%, pulse
  77.7%→99.7%.** Fargo is essentially unchanged (79.5%→79.2%), confirming
  its OWN separate voice-2 desync (open since B12, ~frame 8000 onward) is a
  genuinely DIFFERENT bug — NOT fixed by this round. Full trail:
  `docs/players/BLACKBIRD.md`'s "B13 shipped" section (keep reading past
  "Finding 2" — that mid-investigation framing was superseded further down
  the same section, left in as honest history, not the final answer).
- **B13 also found a bonus, unrelated bug**: the simulator itself
  (`bin/blackbird_everyframe_sim.py`, previously validated only over the
  first 1200 frames of each song) diverges from real hardware on Glyptodont
  voices 0/1/filter in this same later region. Not investigated further —
  flagged so a future round doesn't keep blindly trusting it past frame
  ~1200 without a fresh check.

## What's committed vs. not
Everything under `work_completed` items 1-8 through B11 is committed to
`origin/master` (B11 = commit `83af9b3`). **B12 AND B13's changes are NOT
yet committed**: `drivers_src/blackbird/blackbird_driver.asm` (B12's
`set_instr_v` GATE+FILTER restart), `bin/build_blackbird_native_song.py`
(B12's pending-instrument/tie fix + `BB_DIAG_*` diagnostic functions; B13's
`bb_steps_for_voice` gate_is_off fix, both branches), `docs/players/BLACKBIRD.md`
(new B12 AND B13 sections), this file, and the memory files
(`memory/blackbird-stage-b-native.md`, `memory/MEMORY.md`). B13's own `py65`
single-step scripts and the VICE trace JSON are scratch-only (session
scratchpad, NOT committed, NOT regenerable without re-running `node
scripts/dev/vsid-trace.js` from the separate `sid-reference-project` repo —
see B13's writeup for the exact command). The rebuilt
`out/blackbird/Fargo_native_part01.sf2` / `Glyptodont_native_part01.sf2` are
build artifacts (regenerate via `bin/build_blackbird_native_song.py`, not
meant to be committed). Run `git status` to see the exact uncommitted diff.

## Immediate action if resuming
1. Check `git status` / `git log` first — if B12/B13 are already committed,
   skip to step 3. If not, review the diff and decide whether to commit it
   (the user hasn't been asked yet this time — B11 was committed only
   after an explicit "yes").
2. Read `docs/players/BLACKBIRD.md`'s "B12" AND "B13 shipped" sections, plus
   "What's genuinely proven vs. still open" tail, in full.
3. For the next round: **Fargo's own voice-2 desync (open since B12,
   permanent from ~frame 8000) is the clear next target** — confirmed a
   DIFFERENT bug from B13's Glyptodont fix, still fully unexplained. Attack
   it with the SAME method that cracked B13: (a) use `BB_DIAG_BIN=2000
   python bin/build_blackbird_native_song.py SID/LFT/Fargo.sid` (with
   `BB_FULL_CAP=20550`) to re-confirm the flatline window and narrow the
   exact onset frame with `BB_DIAG_LO`/`BB_DIAG_HI`/`BB_DIAG_REG`; (b) do
   NOT stop at a driver-side register-output diff — instrument
   `run_full_song_sim`'s CONTINUOUS simulation to dump internal per-voice
   state (`vs.wavepos`/`vs.wavemask`/`vs.pendins`/`sim.v[x].rpos`, the raw
   byte cursor) frame-by-frame around the onset, the way B13's second half
   did — this is what caught B13's real bug after an initial wrong
   diagnosis; (c) correlate the exact onset frame against the raw decoded
   byte stream (`result.real(voice)` + `classify_byte`), not just the
   higher-level `steps_per_voice`/`row_frame` abstractions, since B13 also
   showed those can misdirect (the row-frame correlation was off by one row
   at first). A `[gate_off]`-adjacent pattern is a reasonable first
   hypothesis given B13's own finding, but verify against the actual byte
   stream rather than assuming — B13's own first two hypotheses (an
   instrument restart, then a wave-engine carry-folding mismatch) were both
   wrong before the real cause turned up.
</current_state>
