<original_task>
This conversation began with the user asking to "read what's next" (i.e.,
read the repo's own `whats-next.md` handoff file from a PRIOR session) to
resume the Blackbird (Linus Åkesson / "lft") player reverse-engineering
arc. That prior handoff was itself stale (it stopped after Stage A,
commit `dfb8241`, while `git log` already showed Stage B rounds B1-B10 had
shipped in between). The user's own directions across THIS conversation,
each building on the last, were: "yes" (update whats-next.md AND continue
the work), "continue", "Glyptodont are still not 100% fidelity", "I want
you to do the full live trace", "write up first. then push", "keep
pushing", "commit and push fargo. maybee time for more lft songs", and
finally this `/whats-next` invocation to produce a fresh, precise handoff
for continuing in a new context. The throughline across all of it: keep
advancing the Blackbird Stage B native 6502 driver's fidelity and
coverage, verifying rigorously (live hardware traces, not just simulator
comparisons) rather than accepting plausible-looking fixes.
</original_task>

<work_completed>
## Session arc summary: Stage B rounds B11 through B15, all shipped, all committed and pushed to `origin/master`

Starting HEAD was `37b21f7` (B10). Ending HEAD is `7de46b7` (B15). Three
commits were made this session, all pushed:
- `d946701` — "Blackbird Stage B12+B13" (B11 had already been committed as
  `83af9b3` in an EARLIER session, before this conversation's own B12-B15
  work began — B11 was reviewed and pushed at the very start of this
  conversation after the user said "yes").
- `0896f05` — "Blackbird Stage B14: fix instrument-index overflow
  (35>32 slots) -- Fargo 79.2%->92.7%"
- `7de46b7` — "Blackbird Stage B15: extend native driver coverage to all
  11 v1.2-exact-bucket files"

### 1. whats-next.md refresh + B11 review/commit (start of conversation)

Read the OLD, stale `whats-next.md` (which stopped at Stage A) and
`git log`, discovered B1-B10 had already shipped in prior sessions.
Rewrote `whats-next.md` from scratch to reflect the true state (B10 done),
then began investigating B11 (a punch-list item B10's own writeup had
already scoped: "fx changes on a rest or tie are deferred to the next
note onset"). Root-caused and fixed it directly against `player.s`:
`prepare1` writes `v_pendfx` immediately on ANY row with a fresh
`$c9-$f8` select byte, and `execute()` applies+clears it unconditionally
every tick — independent of `prepare3`'s separate note-only mirror. Fixed
in TWO places (driver `drivers_src/blackbird/blackbird_driver.asm`'s new
`fxflag`/`maybe_fx_commit`, and translator
`bin/build_blackbird_native_song.py`'s `steps_to_rows_native` row-emission
logic). Result: Fargo freq 97.4%→**100.0% (exact)**, overall 78.8%→79.4%;
Glyptodont freq 97.1%→99.7%, overall 91.4%→92.0%. Documented in
`docs/players/BLACKBIRD.md`'s "B11 shipped" section. User then explicitly
said "yes" to committing — committed as `83af9b3` and pushed (this was
actually still within an earlier phase; by the time the CURRENT
conversation's visible history starts in full, B11 was already landed and
the user was reviewing/continuing from there).

### 2. B12 shipped: instrument-select restart timing

User said "continue". Investigated Fargo's own full-song pulse (52.0%)
and adsr (74.0%) weakness (B11's own named next residual). Added a
PERMANENT diagnostic harness to `bin/build_blackbird_native_song.py`:
`report_binned`/`report_registers` functions gated by new env vars
`BB_DIAG_BIN`/`BB_DIAG_LO`/`BB_DIAG_HI`/`BB_DIAG_REG` — these are now a
standing part of the build script, not removed after use. Used them to
discover the "weak pulse/adsr" symptom was actually TWO separate bugs:
(1) **fixed this round**: a standalone instrument-select byte with no
note nearby was silently deferred (or, if the eventual note was tied,
dropped outright) by the native driver, because `player.s`'s `execute()`
restarts WAVE/FILTER/ADSR/GATE on EVERY tick a real instrument-select is
consumed, independent of note-triggering, but the driver only restarted
at note-trigger time (`pn_note`). Fixed in `set_instr_v` (immediate
GATE+FILTER restart — ADSR was already immediate) and
`bb_steps_for_voice`/`steps_to_rows_native` (pending instrument/tie state
no longer leaks across intervening rest/hold rows onto an unrelated later
note — same "commit on the very next event, not an arbitrary later one"
principle B11 already established for fx). **Empirically found, not fully
explained**: also restarting the wave-row cursor (VWI) immediately in
`set_instr_v` — which is what `player.s`'s literal source suggested was
needed — measurably REGRESSED pulse (52.0%→50.0%, worse than doing
nothing); leaving VWI restart OUT (still only reset by `pn_note`) was
strictly better on every metric (52.0%→51.6%). Shipped without fully
understanding this asymmetry — flagged as an open question. (2) **left
open**: voice 2 in Fargo has a full, permanent instrument-state desync
starting ~frame 8000 — root cause NOT found this round, this is what
LATER became the B14 investigation (see below). Result:
**Fargo 79.4%→79.5%, Glyptodont ADSR 96.1%→96.2%**. Committed together
with B13 as `d946701`.

### 3. B13 shipped: Glyptodont's gate-off-before-note bug (via a real live hardware trace)

User said "Glyptodont are still not 100% fidelity" (a direct, factual
observation). Investigated using the B12 diagnostic tools and found a
DIFFERENT shape of residual than Fargo's: waveform/AD-SR/filter actually
reach exact 100.0% for the back half of Glyptodont's song — the real
problem was narrow, concentrated almost entirely in voice 2's pulse,
permanently wrong from ~frame 10165 onward. User then explicitly said
"I want you to do the full live trace" — this triggered a genuinely new
tier of investigation:

- Ran `node scripts/dev/vsid-trace.js` (from the SEPARATE
  `C:\Users\mit\claude\sid-reference-project` repo — a VICE-based real
  hardware SID register-write tracer, NOT part of SIDM2 itself) to
  capture a REAL emulated-hardware trace of Glyptodont through frame
  10300 (`--frames 10300 --json --changed-only`), run in the background
  (~3-4 minutes of real emulated playback). This was to check whether
  `bin/blackbird_everyframe_sim.py` (the Python simulator EVERY prior
  B-round trusted as ground truth) was STILL correct that deep into the
  song — it had only ever been validated over each song's first 1200
  frames.
- Wrote scratch comparison scripts (session-scratchpad-only, NOT
  committed) to reconstruct full per-frame register snapshots from the
  vsid write-event JSON and align them against the simulator's own trace
  (found the correct frame offset via a sweep, confirmed unambiguous).
- **Finding 1**: the simulator IS still correct for Glyptodont's voice 2
  in this exact window (100% match vs real hardware) — so the residual is
  a genuine bug, not stale simulator ground truth.
- **Finding 2 (later superseded, kept in the doc as honest history)**:
  used `py65` (pure-Python 6502 emulator, already used internally by
  `headless_trace`) to single-step the driver's own execution frame by
  frame, cross-referenced against a 64tass `--labels` dump to resolve PCs
  to source labels. This INITIALLY (wrongly) diagnosed a "wave-program
  restart" bug (found a genuine `pn_note` restart write at the exact
  frame the residual begins) — this framing was WRONG.
- **The actual root cause** (found by pushing one step further, per the
  user's explicit instruction): instrumented the CONTINUOUS simulator's
  own internal per-voice state (`vs.wavepos`/`vs.wavemask`/`vs.pendins`,
  and the raw byte-stream cursor `sim.v[x].rpos`) frame-by-frame, not just
  final register OUTPUT. This showed `wavepos` NEVER CHANGES around this
  window — there is no restart on real hardware at all. What actually
  happens: `vs.pendins` becomes `$FE` (the gate-off sentinel) and
  `vs.wavemask` flips to `$FE` — a GATE-OFF event. Tracking the raw byte
  cursor nailed the exact sequence, one byte per real frame, which ALSO
  corrected an earlier working assumption in this investigation: real
  hardware's dispatch is `prepare1`→`prepare2`→`prepare3`→`execute`, each
  getting its OWN SEPARATE real frame (confirmed directly in
  `blackbird_everyframe_sim.py`'s `real_frame()`), not all four stages
  within one frame as first assumed.
- **The actual bug**: `bb_steps_for_voice` (the translator, in
  `bin/build_blackbird_native_song.py`) sets `gate_is_off = True` on a
  gate-off byte but only ever CHECKED that flag in the `'delay'` branch —
  the `'note'` branch ignored it entirely, so `[gate_off][note]` (a real,
  if uncommon, Blackbird grammar pattern meaning "voice goes silent, note
  value discarded, no restart") was wrongly emitted as a genuine active
  note.
- **First fix attempt regressed Glyptodont 92.0%→73.2%** (freq alone to
  71.3%) — way too large for the one row this was meant to fix. Counting
  `[gate_off]→[note]` pairs across the whole song found why: **14-45% of
  every voice's notes** matched the naive pattern, not the rare handful
  expected.
- **Root cause of the regression**: the `'delay'` branch ALSO never reset
  `gate_is_off` after using it — a PRE-EXISTING bug, harmless until the
  note-branch fix started checking the flag too. On real hardware,
  `v_pendins` resets every `execute()` call and a delay's own hold skips
  `prepare1/2/3` entirely (`v_trtimer` negative), so gate-off's silencing
  effect only ever covers ONE event; once a delay's own countdown
  expires, `prepare2` gets a fresh chance to run, and for a note byte its
  own "got_note: reuse currins as pendins" path automatically restarts
  the gate, independent of any earlier gate-off several delay-ticks back.
  Fixed by resetting `gate_is_off = False` in BOTH branches (same
  one-event-only consumption discipline B11/B12 already used for
  `pending_instr`/`pending_tie`).
- **Result: Glyptodont 92.0%→97.6%, pulse 77.7%→99.7%**, waveform
  93.5%→95.5%, filter 94.7%→95.2%, freq essentially flat (99.7%→99.5%).
  **Fargo essentially unchanged** (79.5%→79.2%), confirming Fargo's own
  voice-2 desync (open since B12) is a genuinely DIFFERENT bug.
- **Bonus, unrelated finding**: the SAME live trace showed the simulator
  itself (previously validated only over each song's first 1200 frames)
  diverges from real hardware on Glyptodont voices 0/1/filter in this
  same later region — a genuine, previously-unknown simulator bug,
  flagged but NOT investigated or fixed.
- Full trail documented in `docs/players/BLACKBIRD.md`'s "B13 shipped"
  section, which DELIBERATELY keeps the mid-investigation wrong "Finding
  2" framing visible (with an explicit note that it's superseded further
  down the same section) as honest history rather than scrubbing it.
- **Mid-turn side task**: user asked "load Glyptodont into sf2" —
  launched `py -3 pyscript/sf2_open_in_editor.py
  out/blackbird/Glyptodont_native_part01.sf2`, succeeded on attempt 3 of
  its known ~73%-per-attempt flaky retry loop (PID 42236). This was the
  FIRST-EVER audio listen of the Blackbird NATIVE driver's output (Stage
  A's coarser output was the only thing ear-tested before this session).
  User later reported (also mid-turn, while B14 tracing was in progress):
  **"Glyptodont sounds really close. something with the perc or drums.
  very close."** This tracks the numbers: waveform (95.5%) and filter
  (95.2%) are the two categories still short of 100% post-B13, and
  percussion/noise sounds lean hardest on exactly those.

### 4. B14 shipped: Fargo's real root cause (a genuine format-limit overflow)

User said "keep pushing" (continuing onto Fargo's own still-open
residual). Applied the EXACT same method that cracked B13:

- Relocated the exact onset frame with `BB_DIAG_BIN`/`BB_DIAG_LO`/
  `BB_DIAG_HI` in the CURRENT (post-B13) build — confirmed the SAME
  "permanent full desync from ~frame 8000" shape B12 first measured.
- Instrumented `BlackbirdSim`'s own internal per-voice state
  (`wavepos`/`wavemask`/`pendins`/`currins`) AND the raw byte cursor
  around the onset (~real-frame 7945).
- Found a GENUINE instrument-select event (raw byte `$a4`) restarting
  correctly in the simulator with `currins=$22` (34 decimal, a real,
  distinct instrument).
- Compared this against `bb_steps_for_voice`'s OWN computation for the
  SAME raw byte: `pending_instr = min(max(b - 0x83, 0), 31)` — a DIRECT
  CLAMP to 31, not a remap. Confirmed by direct count: Fargo genuinely
  uses **35 distinct raw instrument indices** across the whole song
  (0-34), matching `nins=35` as located — NOT 28 or some smaller "actually
  used" subset as an earlier build-log line ("instr=28 bundles") had
  misleadingly suggested (that number referred to something else).
  Indices 32/33/34 all silently aliased onto slot 31.
- This was NOT merely a wrong command byte: `build_range` used the SAME
  clamped index to read the RAW source `ins_wave`/`ins_ad`/`ins_filt`
  tables DIRECTLY (`d[(lay.ins_wave - la) + i]` etc.), so a note using
  real instrument 33 played instrument 31's ACTUAL wave/ADSR/filter
  program instead. Once an untied note relying on the "sticky repeat
  current instrument" mechanism followed (very common — most untied
  notes don't carry their own fresh instrument-select), the wrong
  substitution PERSISTED for the rest of the voice's notes — exactly
  matching the "permanent from this point" shape.
- **Why `fits()`'s own resource check never caught this**, despite
  `CAP_I=32` already existing SPECIFICALLY to trigger B6's adaptive
  part-splitting for exactly this class of overflow (the SAME mechanism
  that already handles Glyptodont's own bundle-count limit): the
  `used_instr` set (feeding the `ni <= CAP_I` check) was built from the
  ALREADY-CLAMPED `s.instrument` values, which can never exceed 32 by
  construction — the check was measuring a quantity mathematically
  incapable of ever reporting an overflow, regardless of the song's true
  distinct instrument count.
- **A second, compounding bug found while fixing this**: `used_instr`
  (and `used_fx`) were only scanned from `kind == 'note'` steps — but
  B11/B12 already made `steps_to_rows_native` emit fx/instrument commands
  on rest/hold rows too (a command doesn't need a note to apply). A
  standalone instrument-select landing on a rest/hold row was invisible
  to the resource count, causing a `KeyError` in the new remap the moment
  clamping stopped silently absorbing the gap (this surfaced as an actual
  crash during testing, caught and fixed before shipping).
- **The fix** — three coordinated changes in
  `bin/build_blackbird_native_song.py`:
  1. `bb_steps_for_voice` no longer clamps — passes through the true raw
     instrument index (`max(b - 0x83, 0)`, no upper bound). See its own
     extensive B14 docstring comment at the site of the change (~line
     203 area, search for "B14: NOT clamped to 31").
  2. `build_range` builds a genuine per-part DENSE remap
     (`instr_remap = {raw: slot for slot, raw in enumerate(sorted(used_instr))}`)
     and uses it everywhere a raw index used to be a direct table key:
     `wave_programs`/`pulse_of_instr`/`filter_programs`/`filter_flag_of`/
     `wave_stats_by_instr`/`filter_extra_by_instr` (now keyed by slot, not
     raw index), `prime_instr_of_voice`/`filt_owner_instr` (B7 priming's
     own instrument references, remapped via `instr_remap.get(...)`), and
     `windowed_steps`' own `s.instrument` field (via a NEW helper function
     `_remap_step_instrument(s, instr_remap)`, defined right after the
     `BBStep` class, producing remapped `BBStep` copies — applied only
     when `not count_only`, to avoid wasted work during `fits()`'s grid
     search). Also builds a part-scoped `part_ad_sr` list (index == driver
     slot) instead of passing the full song-wide `ad_sr` into
     `gen_includes_song`/`_compute_prime_consts`. A part genuinely needing
     more than 32 distinct instruments now raises loudly on a REAL build
     (`if not count_only and len(instr_remap) > CAP_I: raise ValueError`)
     — guarded so it does NOT fire during `fits()`'s own `count_only`
     probe calls (which must see an ordinary "doesn't fit" signal via the
     returned count, not an exception, or the adaptive-splitting search
     itself would crash instead of shrinking the window).
  3. The `used_instr`/`used_fx` counting loop (near the top of
     `build_range`) now scans EVERY step regardless of `kind`, not just
     `kind == 'note'` steps.
  4. `main()`'s song-wide `ad_sr` extraction (`nins = max(1, lay.nins)`,
     was `min(lay.nins, 32)`) is no longer capped at 32 — that used to
     truncate `lay.nins > 32` files before `build_range`'s own per-part
     remap ever got a chance to select which instruments fit a given
     part's own budget.
- For Glyptodont (31 raw instruments, already under the cap), this remap
  is a no-op — `instr_remap[i] == i` for every `i`.
- **Result**: Fargo now genuinely needs 2 parts (B6's adaptive splitting
  correctly firing for Fargo for the FIRST TIME, not a bug — resolved
  once split). **Fargo 79.2%→92.7%** (freq 99.6%, waveform 98.1%, adsr
  99.6%, filter 100.0%; pulse 71.1%, up hugely from 50.3% but now the
  weakest category, NOT further investigated this round). Fargo now ships
  as 2 separate SF2 files (`Fargo_native_part01.sf2`/`_part02.sf2`), not
  1. **Glyptodont byte-identical to B13, 97.6%** (confirmed no
  regression; `instr` count in the build log moved 31→32, purely from the
  used_instr/used_fx under-counting fix now correctly including a
  rest/hold-row reference that was always there, not a behavior change).
- B10's `verify_fx_engine` self-check still passes at full count on both
  files. `pyscript/test_blackbird_parser.py`'s full 9/27 subtests still
  pass.
- Documented in `docs/players/BLACKBIRD.md`'s "B14 shipped" section.
  Committed as `0896f05` and pushed.

### 5. B15 shipped: extend native driver to the full 11-file corpus

User said "commit and push fargo. maybee time for more lft songs" — read
as (a) commit+push the pending work, (b) continue pushing on Fargo [done
as B14 above], (c) consider extending to more LFT songs. After B14
landed, ran the OTHER 9 v1.2-exact-bucket files (previously only
located/Stage-A-covered, never built through the native Stage-B pipeline)
through `bin/build_blackbird_native_song.py` cold, with
`BB_FULL_CAP=999999` to force whole-song comparison:

| File | Overall | Freq | Waveform | Pulse | ADSR | Filter | Parts |
|---|---|---|---|---|---|---|---|
| Thus_Spoke_the_PC_Speaker | 98.9% | 100.0% | 96.6% | 100.0% | 97.2% | 100.0% | 1 |
| Maple_Leaf_Rag | 98.8% | 100.0% | 96.0% | 100.0% | 97.0% | 100.0% | 1 |
| Euclid_Was_Here | 98.3% | 99.9% | 93.7% | 100.0% | 96.2% | 100.0% | 1 |
| Dishwasher_Groove | 97.5% | 99.4% | 97.3% | 100.0% | 95.8% | 93.8% | 1 |
| Fargo (B14) | 92.7% | 99.6% | 98.1% | 71.1% | 99.6% | 100.0% | 2 |
| Glyptodont (B13) | 97.6% | 99.5% | 95.5% | 99.7% | 96.2% | 95.2% | 1 |
| Elvendance | 95.3% | 99.2% | 95.8% | 100.0% | 97.4% | 79.1% | 1 |
| Into_the_Unknown | 95.4% | 99.9% | 96.1% | 89.2% | 97.9% | 93.5% | 3 |
| Toy_Rocket | 95.1% | 99.4% | 93.9% | 87.5% | 95.7% | 99.8% | 1 |
| Dithered_Island | 92.7% | 99.9% | 95.7% | 75.3% | 96.5% | 99.8% | 2 |
| Revolutions_Delivered | 91.4% | 99.6% | 77.7% | 92.9% | 95.6% | 81.1% | 1 |

All 9 new files built successfully on the FIRST try, no crashes, no
exceptions, every B10 `verify_fx_engine` self-check passing at full
count. Multi-part splitting (B6's adaptive mechanism, now correctly
triggered by B14's true instrument-count fix) fired automatically for 2
of the 9 new files (Dithered_Island: 2 parts, Into_the_Unknown: 3 parts)
with no manual intervention. **All 11 v1.2-exact-bucket files now have a
working native Stage-B build**, ranging 91.4%-98.9% overall (mean ~95%).

This was a coverage extension, NOT a fix — no code was changed for B15,
only the existing (now more robust) pipeline was run against more inputs.
Explicitly documented as a BASELINE, not a claim of per-file
understanding: none of the 9 new files have been individually
root-caused via live-trace investigation the way Fargo/Glyptodont were,
and none have been audio-listened.

Documented in `docs/players/BLACKBIRD.md`'s new "B15 shipped" section.
ALSO used this pass to refresh the doc's badly-stale TOP-OF-FILE status
summary (lines 1-46), which had not been touched since roughly the
B4-B7 era months earlier and still quoted B4-era fidelity numbers
(Fargo 69.6%, Glyptodont 53.5%) as if current — rewrote it to reflect the
true current B15 state.

Rebuilt Fargo one more time after the corpus sweep specifically to
restore `drivers_src/blackbird/layout.inc` and the 4
`tempo_sched_*.inc` files to a representative committed state (these are
build-artifact `.inc` files that get regenerated by whichever file was
built LAST — the corpus sweep's last file was Toy_Rocket, which would
have left a misleading/arbitrary state; prior B-round commits have always
committed these reflecting Fargo or Glyptodont, so this matches
established practice). Committed as `7de46b7` (includes
`docs/players/BLACKBIRD.md`, `whats-next.md`, and the 5 regenerated
`.inc` files) and pushed.

## Memory files updated throughout (all in `C:\Users\mit\.claude\projects\C--Users-mit-claude-c64server-SIDM2\memory\`, OUTSIDE the git repo)
- `memory/blackbird-stage-b-native.md` — extended substantially across
  B11 through B15, now the primary durable record of this whole arc's
  granular findings (root causes, exact fix descriptions, all numbers).
  Its own frontmatter `description` field was kept current after each
  round.
- `memory/blackbird-lft-player.md` — NOT touched this session (already
  near its own size limit from a prior session; explicitly left as
  "stops at Stage A" with a forward pointer to
  `blackbird-stage-b-native.md`, which is where all NEW findings go).
- `memory/MEMORY.md` — the compacted index; its Blackbird-related lines
  (both the "New-player priority" line and the dedicated Blackbird
  Stage B line) were updated after every round to reflect current state.
  NOTE: at the very end of this conversation, a system reminder indicated
  `MEMORY.md` was ALSO modified externally (by the user or a linter) —
  specifically an update to the `sf2ii-pyautogui-heisenbug.md` index line
  (unrelated to Blackbird, noting SF2II now "crashes on EVERY launch" as
  of 2026-07-20). That external edit should be preserved, not reverted —
  it was not made by this session's own work and is orthogonal to the
  Blackbird arc.
</work_completed>

<work_remaining>
## Immediate priorities, in the order this session's own final whats-next.md update (now superseded by this document) recommended

1. **Fargo's own pulse residual (71.1%)** — the weakest category on
   either of the two individually-investigated files, NOT yet chased
   down. This is the clearest, most well-precedented next step: apply
   the EXACT method that cracked both B13 and B14:
   a. Use `BB_DIAG_BIN=2000 python bin/build_blackbird_native_song.py
      SID/LFT/Fargo.sid` (with `BB_FULL_CAP=20550`) to re-locate the
      residual region in the CURRENT 2-part build (the part boundary at
      row 1200 may have shifted where any given issue now falls
      relative to earlier per-part investigations).
   b. Narrow the exact onset frame with `BB_DIAG_LO`/`BB_DIAG_HI`/
      `BB_DIAG_REG` (these env vars are permanent, already in
      `bin/build_blackbird_native_song.py`, added in B12).
   c. Do NOT stop at a driver-vs-simulator register-output diff — that
      alone produced a WRONG diagnosis in B13 (a plausible-looking "wave
      restart" bug that turned out to be a "gate-off" event once pushed
      further) and would likely have produced an incomplete one in B14
      too. Instrument `BlackbirdSim`'s own internal per-voice state
      (`vs.wavepos`/`vs.wavemask`/`vs.pendins`/`vs.currins`, and the raw
      byte-stream cursor `sim.v[x].rpos`) frame-by-frame around the
      onset, via a small standalone script that imports
      `bin/build_blackbird_native_song.py`'s and
      `bin/blackbird_everyframe_sim.py`'s internals directly (see
      "Critical Context" below for the exact reusable script pattern
      developed this session).
   d. Correlate the exact onset frame against the RAW decoded byte
      stream (`result.real(voice)` + `sidm2.blackbird_parser.classify_byte`),
      NOT just the higher-level `steps_per_voice`/`row_frame`
      abstractions — B13's own investigation found the row-frame
      correlation was off by exactly one row on the first attempt
      (predicted row 2034, the real trigger was row 2033), only caught
      by cross-checking against the true raw-byte-cursor trace.
   e. Given B14's precedent (a genuine 35>32 format-limit overflow), it
      is worth explicitly checking whether Fargo's pulse residual is
      ALSO an instrument/table-overflow class of issue specific to
      PULSE data specifically (e.g. does any per-instrument PULSE
      program exceed some other undiscovered cap?) before assuming it's
      a NEW, unrelated bug — but do not assume this without verifying
      against the actual trace; B13 and B14 turned out to be genuinely
      different bug classes despite superficial similarity (both
      voice-2, both pulse-shaped).

2. **Root-cause individual residuals in the 9 newly-built (B15) files**
   — none of these have had ANY live-trace investigation, only a cold
   build. Worth investigating in roughly this priority order (worst
   fidelity / most room for improvement first):
   - `Revolutions_Delivered`: waveform 77.7%, filter 81.1% — the two
     worst individual category scores in the WHOLE 11-file corpus.
   - `Elvendance`: filter 79.1% — otherwise a strong file (pulse 100%,
     freq 99.2%), filter is an isolated weak spot worth a targeted look.
   - `Dithered_Island` / `Into_the_Unknown`: both needed multi-part
     splitting (2 and 3 parts respectively) and both show meaningfully
     weak pulse (75.3%, 89.2%) — worth checking whether their
     part-boundary transitions specifically are the issue (see item 4
     below, which flags this exact class of concern for Fargo's own
     part 2).

3. **The B13-recon bonus finding**: the simulator itself
   (`bin/blackbird_everyframe_sim.py`) diverges from real hardware on
   Glyptodont voices 0/1/filter past frame ~1200 (the point beyond which
   it was never originally validated). This is UNRELATED to any of the
   translator/driver bugs fixed in B11-B14 and remains completely
   uninvestigated. Matters because EVERY fidelity percentage quoted
   throughout this whole B-round history implicitly trusts the simulator
   as ground truth — if it's wrong elsewhere too, some historical
   "driver bug" diagnoses could theoretically be simulator artifacts
   instead (though B13's own direct real-hardware cross-check did
   specifically confirm the simulator WAS correct for the ONE case that
   mattered there, voice 2). A dedicated live-trace investigation of
   voices 0/1/filter specifically (matching B13's own vsid-trace.js
   methodology) would be the way to properly resolve this.

4. **Fargo's part 2 shows a rough startup** (primary-200f window only
   93.0% overall, freq only 92.3%, in the B14 post-split build) — likely
   the SAME class of part-boundary priming edge case B7/B8 chased for
   Glyptodont's own multi-part era (before B10 collapsed it back to 1
   part), but NOT re-investigated this session since B10 had already
   solved it for Glyptodont and this is the FIRST time Fargo itself has
   ever been multi-part. Worth checking whether B7/B8's existing priming
   fixes (`_compute_prime_consts`, `PRIME_*` fields in
   `blackbird_driver.asm`) are being correctly exercised for Fargo's
   OWN part 2 boundary specifically, or whether there's a NEW edge case.

5. **Extend audio listening beyond Glyptodont's pre-B14 build** — nobody
   has heard Fargo (pre- or post-B14) or ANY of the 9 new B15 files yet.
   Given real audio listening is now a proven, working path
   (`pyscript/sf2_open_in_editor.py`, ~73% per-attempt success, just
   retry) and has ALREADY surfaced one concrete, numerically-consistent
   lead (Glyptodont's "perc/drums" feedback pointing at waveform/filter),
   listening to a few more files — especially Fargo post-B14, and maybe
   the two multi-part files (Dithered_Island, Into_the_Unknown) — could
   surface similarly concrete leads before investing in more live-trace
   digging blind.

6. **Not started / explicitly out of scope, unchanged from before this
   session**: the ~16 near-v1.2-variant Blackbird files (older
   birdcruncher tool versions, 5 at "variant A", 1 at "variant A'", 10 at
   "variant B" per `docs/players/BLACKBIRD.md`'s corpus-scope table) —
   `locate_blackbird()` correctly rejects them, no alternate relocation
   template exists in the repo to support them. The ~7 "much-older/
   uncertain" files (diverge almost from byte 3) — not investigated at
   all. Wiring ANY of the 11 v1.2-exact-bucket files into
   `DriverSelector`/`conversion_pipeline` — deliberately still out of
   scope; the project's own convention treats "notes/timing right,
   timbre not yet fully verified" as not-yet-production-ready, and none
   of these files (except Glyptodont, partially) have been audio-verified.
</work_remaining>

<attempted_approaches>
## Wrong turns this session, all caught and corrected before shipping — useful to know so they aren't repeated

### B13: "wave-program restart" — a plausible-looking WRONG diagnosis, caught by pushing one level deeper
Live `py65` single-stepping of the driver found a genuine `pn_note`
restart write (`VWI,x = $44`) at the EXACT frame Glyptodont's pulse
residual begins, and the driver's own captured WAVE table was internally
self-consistent with the 2-frame "settle" behavior this restart produced.
This LOOKED like a complete, verified diagnosis (real CPU trace, matching
table, exact frame correlation) — but was wrong. Only caught by
explicitly instrumenting the CONTINUOUS simulator's OWN internal state
(not just comparing final register OUTPUT against the driver), which
showed real hardware shows NO restart at all there — it's a gate-off
event. **Lesson, stated explicitly in this session and worth repeating
for Fargo's own pulse investigation**: a register-output diff, even a
very precise one anchored to an exact frame via live CPU tracing, can
still support a plausible-but-wrong causal story. Only comparing INTERNAL
STATE against a trusted independent source (here: the simulator's own
internals, cross-validated against real hardware) actually distinguishes
"a restart legitimately happened and produced this pattern" from "no
restart happened, something else entirely produced a similar-looking
pattern."

### B13: row/tick correlation was off by one row on the first pass
Using `row_frame` (the GLOBAL row-index-to-real-frame mapping from
`run_full_song_sim`) to find "which row is active at frame 10168" first
implicated row 2034 (part of a run of tied notes). The REAL trigger,
found once the byte-cursor trace was cross-checked, was row 2033 (a
distinct, untied note with its own fresh fx-select). The row_frame-based
correlation technique is still useful for a FIRST approximation, but this
session's experience shows it should always be cross-checked against the
raw byte-cursor trace (`sim.v[x].rpos`) before treating "which row" as
settled, especially when the specific row's CONTENT (tie status,
instrument reference) matters to the diagnosis.

### B13: first fix attempt (checking `gate_is_off` in the note branch alone) massively over-applied
Rebuilding immediately after adding the note-branch check regressed
Glyptodont from 92.0% to 73.2% — the fix was CORRECT in principle but
incomplete: a companion bug (the delay branch never resetting
`gate_is_off`) meant the flag rode across unbounded runs of delay events
instead of covering only the one event immediately after a gate-off.
**Lesson**: after ANY fix to a "consume this flag/pending value" pattern,
verify empirically how OFTEN the fixed condition now fires (a quick
standalone count script, as used here) before trusting a full rebuild's
result — a naive count immediately revealed 14-45% of notes matched the
over-broad pattern, which is what led to finding the real, second bug
before wasting a full rebuild-and-diff cycle chasing a symptom.

### B14: same-class instinct check — was NOT the same bug as B13, despite similar shape
Given B13's fix (gate-off handling) was fresh, it was tempting to assume
Fargo's own voice-2 desync was the SAME root cause. It was explicitly
checked (rebuilt Fargo after B13 landed, confirmed 79.5%→79.2%, i.e.
essentially unchanged) BEFORE assuming B13's fix would also cover Fargo —
this confirmed they are genuinely different bugs. This check is
documented as a deliberate verification step, not an oversight.

### B14: initial `KeyError` from an incomplete first implementation of the remap
The first version of the `instr_remap` fix crashed with `KeyError: 8`
when rebuilding Fargo, because `used_instr` (built from a loop that only
scanned `kind == 'note'` steps) didn't include an instrument reference
that landed on a rest/hold row (a reference `_remap_step_instrument` then
tried to look up and failed to find). This is DOCUMENTED as a genuine
implementation bug caught by testing, not a design flaw — the underlying
remap approach was correct, but the resource-counting loop needed the
same fix. Fixed by scanning every step regardless of kind (see Work
Completed item 4, fix #3).

### B14: `raise` guard needed careful placement relative to `count_only`
The `instr_remap` overflow-safety check (`if len(instr_remap) > CAP_I:
raise`) was FIRST written without a `count_only` guard, which would have
crashed `fits()`'s own probe calls (used by B6's adaptive part-splitting
search to test candidate windows) instead of letting them return an
ordinary "doesn't fit, try a smaller window" signal. Caught by reasoning
through the call graph before it was ever run against real data (not
caught by a crash) — the guard `if not count_only and len(instr_remap) >
CAP_I: raise` was the corrected version shipped.

### None of B11/B12's approaches were themselves wrong turns — they were both scoped, targeted fixes that worked on the first real attempt (unlike B13/B14, which each involved at least one significant false start). Worth noting only because it shows the "false start" pattern in B13/B14 correlates with going deeper into genuinely novel territory (live hardware tracing, internal-state instrumentation) rather than being a general feature of this codebase's difficulty.
</attempted_approaches>

<critical_context>
## Architecture facts discovered/confirmed this session, likely to matter for ANY future Blackbird investigation

- **The true per-frame dispatch, confirmed directly in
  `blackbird_everyframe_sim.py`'s `real_frame()`**: `zp_master` counts
  down by 7 each real frame. While it's still ≥21 (3×7), NOTHING
  prepare-related happens that frame (`everyframe()` still runs). Once it
  drops below 21, exactly ONE prepare stage runs per frame, cycling
  `preparejmp` 1→2→3 (`prepare1` on one frame, `prepare2` on the NEXT
  frame, `prepare3` on the frame after that). When `zp_master` hits
  EXACTLY 0, `execute()` runs. So a full tick-cycle (one "row" of the
  native driver's own sequence) spans `tempo_byte // 7 + 1` REAL FRAMES,
  and prepare1/prepare2/prepare3/execute are SPREAD ACROSS the LAST 3-4
  of those frames, ONE STAGE PER FRAME — NOT all four stages within a
  single frame, which was this session's own (and possibly prior
  sessions') working assumption until directly falsified by a live
  frame-by-frame trace during the B13 investigation. This matters for any
  future timing-sensitive investigation: "what happens on frame N" for a
  given tick depends on WHICH prepare stage is due that specific frame,
  not "everything for this row."
- **`prepare2`'s "got_note: reuse currins as pendins" mechanism**
  (`player.s` — `if b < 0x80: _pr2_noteback(x, vs.currins)`) fires
  WHENEVER `prepare2` examines a position whose CURRENT byte is a note
  (bit7 clear), even peeking ahead of what `prepare3` will itself later
  consume on the SAME tick. This is what makes EVERY untied note
  (whether or not it carries its own fresh instrument-select byte)
  restart using the STICKY current instrument — a real, load-bearing
  mechanism, not a fallback edge case.
- **`v_pendins` (and `v_pendfx`) reset to 0 in EVERY `execute()` call**,
  unconditionally, regardless of what happened that tick. Nothing about
  "gate off" or "fx select" persists across MULTIPLE ticks by itself —
  what LOOKS like persistence (e.g. a voice staying silent through a long
  delay) is actually `v_wavemask` (a genuinely separate, persistent
  per-voice state byte) staying at whatever it was last explicitly set
  to, NOT `v_pendins` itself carrying forward. Any future investigation
  of "why does this state seem to persist" should check which SPECIFIC
  state variable is actually persistent (wavemask, wavepos, pwidth,
  currins/currfx) versus which are per-tick pending flags that always
  reset (pendins, pendfx, pendnote).
- **`bb_steps_for_voice`'s general pattern, now applied consistently to
  fx (B11), instrument+tie (B12), and gate-off (B13)**: any "pending"
  state set by a prefix-classified byte (arp/instrument/gate_off/legato)
  must be consumed by (attached to, and then CLEARED by) the very NEXT
  classified event of ANY kind (note OR delay) — never held across
  multiple subsequent events. Every bug found and fixed in B11-B13 was a
  variant of this SAME principle being violated somewhere (either not
  checked at all, as in B11/B12/B13's first bugs, or checked-but-not-
  reset, as in B13's second, companion bug). **If investigating Fargo's
  pulse residual or any of the 9 new B15 files' residuals, checking
  whether this SAME class of bug exists somewhere else in
  `bb_steps_for_voice` (there are still other classified byte kinds —
  'arp'/'oob' — whose consumption discipline was not specifically
  re-audited this session) would be a reasonable first hypothesis before
  assuming a wholly new bug class.**
- **The `vsid-trace.js` live-hardware-trace tool** lives in a SEPARATE
  repo (`C:\Users\mit\claude\sid-reference-project`), NOT in SIDM2 itself.
  Usage: `node scripts/dev/vsid-trace.js <file.sid> --frames N --json
  --changed-only [--out <path>]`. It wraps VICE's `vsid` in
  `-sounddev dump` mode. Real playback time (not instant) — a 10300-frame
  trace took several minutes and was run via the Bash tool's
  `run_in_background: true` option, with the result picked up via the
  automatic task-completion notification rather than polling. The output
  JSON's `frames` array only includes frames THAT HAD WRITES (a sparse
  representation) — reconstructing a full per-frame 25-register snapshot
  requires accumulating writes cumulatively starting from an all-`$00`
  reset state (matching `sidm2-sid-trace.exe`'s own convention). Finding
  the correct frame ALIGNMENT between this trace and the simulator's own
  frame-0 convention required a small offset sweep (checked ±10 frames)
  — this offset (found to be exactly 0 for Glyptodont) should be
  re-verified, not assumed, for ANY new file this tool is used against.
- **The reusable script pattern developed this session** for internal-
  state instrumentation (used successfully for both B13 and B14): a
  small standalone Python script (written to the session scratchpad, NOT
  committed) that does:
  ```python
  import sys, os
  sys.path.insert(0, os.path.join(os.getcwd(), 'bin'))
  sys.path.insert(0, os.getcwd())
  import build_blackbird_native_song as B
  import blackbird_everyframe_sim as SM
  from sidm2.blackbird_parser import locate_blackbird, decode_streams, classify_byte

  sid = "SID/LFT/<File>.sid"
  lay = locate_blackbird(sid)
  d, la, h = B.load_sid(sid)
  result = decode_streams(d, la, lay.streamstart)
  po = lay.play_base - la
  ins_restart = d[po+93]-1
  ins_restart2 = d[po+512]-1

  tempo_records = SM.find_tempo_records(lay, d, la)
  sim = SM.BlackbirdSim(lay, d, la, result.voices, ins_restart, ins_restart2,
                         tempo_debug=list(tempo_records))
  log = []
  for f in range(N_FRAMES):
      regs = sim.real_frame()
      vs = sim.v[VOICE_INDEX]
      log.append(dict(frame=f, rpos=vs.rpos, wavepos=vs.wavepos,
                       wavemask=vs.wavemask, pendins=vs.pendins,
                       currins=vs.currins, reg=regs[REGISTER_INDEX]))
  # then inspect log[LO:HI] directly, and cross-reference raw bytes via
  # result.real(VOICE_INDEX)[rpos_before:rpos_after] + classify_byte(b)
  ```
  IMPORTANT gotcha hit twice this session: `import build_blackbird_native_song
  as B` shadows the module-level name `B` that `build_blackbird_native_song.py`
  ITSELF uses internally to mean `build_blackbird_driver_full` (its own
  `import build_blackbird_driver_full as B` at the top of that file) — so
  inside a scratch script, calling something like `B.headless_trace(...)`
  will FAIL with `AttributeError` unless you import
  `build_blackbird_driver_full` under a DIFFERENT alias (e.g. `BF`) in the
  scratch script and call `BF.headless_trace(...)` instead. This tripped
  the investigation once and is worth remembering for any future
  scratch-script instrumentation.
  Also: `run_full_song_sim`'s OWN internal `BlackbirdSim` instance is
  SEPARATE from one you construct fresh in a scratch script — they will
  independently reproduce the SAME simulation deterministically (no
  randomness, confirmed), so re-constructing a fresh `BlackbirdSim` in a
  scratch script to get frame-by-frame internal access (rather than
  trying to hook into `run_full_song_sim`'s own instance) is the correct,
  simple approach, and was what worked both times.
- **`headless_trace`** (in `build_blackbird_driver_full.py`, aliased as
  `BF` per above) is a PURE PYTHON 6502 emulator (`py65`) — it runs the
  DRIVER's own assembled code deterministically with NO real hardware
  IRQ timing at all (just a simple `call(0x1003)` loop for `do_play`).
  This was important evidence in the B13 investigation: because
  `headless_trace` ALREADY reproduced the exact same bug pattern the real
  VICE hardware trace showed, this RULED OUT any "real hardware IRQ
  timing/cycle overrun" theory — the bug had to be a pure, deterministic
  LOGIC bug in the driver's own 6502 code (or, as it turned out, in the
  TRANSLATOR that builds that code's data tables), not a timing race.
- **`build_range`'s `count_only=True` mode** (used by `fits()` during
  B6's adaptive part-splitting grid search) must NEVER be allowed to
  raise an exception for a condition that simply means "this window
  doesn't fit" — it must always return a value that `fits()` can check
  against a cap. Any FUTURE new resource-check added to `build_range`
  (following B14's own `instr_remap` precedent) needs the same
  `if not count_only:` guard pattern before any `raise`.
- **User's own working style, confirmed again this session**: values
  real hardware verification over ANY amount of static code reading or
  simulator-only comparison ("I want you to do the full live trace" was
  an explicit, direct instruction, not a suggestion); is comfortable with
  long, deep technical investigations and wants them PUSHED further
  rather than stopped at a plausible-but-unverified answer ("keep
  pushing" said TWICE this session, each time after a result that could
  have been treated as "good enough"); appreciates being told about
  wrong turns rather than having them silently hidden (this session's
  `docs/players/BLACKBIRD.md` explicitly preserves the B13 "Finding 2"
  wrong diagnosis with a note explaining it was superseded, rather than
  rewriting history) — continue this pattern; gives short, information-
  dense directives ("commit and push fargo. maybee time for more lft
  songs" packed THREE distinct instructions into one line) and expects
  them to be correctly parsed and acted on without needing clarification
  for reasonably-inferrable intent, though `AskUserQuestion` has been
  used successfully in EARLIER sessions of this same arc for genuinely
  ambiguous single-word instructions (not needed this session — nothing
  was ambiguous enough to warrant it).
</critical_context>

<current_state>
## Deliverables status
- **B11 through B15 are ALL shipped, committed, and PUSHED to
  `origin/master`.** Current HEAD: `7de46b7`. No Blackbird-related
  uncommitted changes remain except the pre-existing, unrelated
  `.claude/settings.local.json` (intentionally left alone all session,
  matching established practice).
- **All 11 v1.2-exact-bucket Blackbird files now have a working native
  Stage-B SF2 build**, ranging 91.4%-98.9% overall whole-song register
  match against the validated simulator (mean ~95%).
  `out/blackbird/*.sf2` contains all of them as build artifacts
  (NOT committed — regenerate via `bin/build_blackbird_native_song.py
  SID/LFT/<File>.sid`, with `BB_FULL_CAP=<large number>` if a whole-song
  comparison is wanted rather than the default 3000-frame window).
- **Only Fargo and Glyptodont have been individually root-caused** via
  deep live-trace investigation (B13 for Glyptodont, B14 for Fargo). The
  other 9 files newly covered by B15 are an UNINVESTIGATED baseline.
- **Only Glyptodont has been audio-listened**, and only its PRE-B14 build
  (B14 doesn't affect Glyptodont at all, so this listen remains valid/
  current — Glyptodont was not rebuilt or changed by B14/B15). User
  feedback: "sounds really close. something with the perc or drums. very
  close." No other file, including Fargo, has been audio-verified at all.
- **NOT wired into `DriverSelector`/`conversion_pipeline`** — deliberate,
  for all 11 files, unchanged this session.
- Documentation is CURRENT and believed accurate as of this handoff:
  `docs/players/BLACKBIRD.md` (top-of-file status summary refreshed in
  B15; "B11 shipped" through "B15 shipped" sections all present and, per
  spot-checks during this session, internally consistent with each
  other); `memory/blackbird-stage-b-native.md` (external to the git repo,
  at `C:\Users\mit\.claude\projects\C--Users-mit-claude-c64server-SIDM2\memory\`,
  extended through B15, frontmatter description current);
  `memory/MEMORY.md` (index lines for Blackbird current through B15; ALSO
  has an unrelated external edit from outside this session — an SF2II
  crash-frequency note — that should be left as-is, not reverted).
- This `whats-next.md` file itself: being freshly rewritten AS this
  response, superseding the version that existed at the start of THIS
  `/whats-next` invocation (which was itself this session's own earlier,
  now-outdated self-maintained version — the content above supersedes it
  entirely and is the authoritative handoff going forward).

## Open questions / pending decisions (for the user, not yet answered)
- Whether to prioritize (a) Fargo's own pulse residual (71.1%, a known
  weak spot on an already-investigated file) versus (b) starting fresh
  investigation on one of the 9 newly-built B15 files (all completely
  uninvestigated) versus (c) the unrelated B13-recon simulator-accuracy
  bonus finding (voices 0/1/filter past frame ~1200) versus (d) more
  audio listening across more files before further live-trace digging.
  This handoff's own "Work Remaining" section orders these as a
  RECOMMENDATION (pulse residual first, matching the most direct
  continuation of this session's own momentum and tooling), not a
  decision already made by the user.
- Whether/when to consider wiring any Blackbird file into
  `DriverSelector` — explicitly NOT decided, and the project's own stated
  convention (production-readiness requires audio verification, which
  only Glyptodont has partially received) suggests this is premature
  regardless, but has not been explicitly discussed with the user this
  session.
</current_state>
