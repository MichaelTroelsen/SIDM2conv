<original_task>
Two requests, in sequence:

1. "we have now build severel SID2SF2 for several target players ... we are still
   facing issue with 100% fidelity and some songs need to be splited into severel
   files. Please do a full code review of the whole tool chain and the players and
   come back with a list of suggestions on how to fix fidelity and number of files
   per song or any other improvement and put them into a and MD for sonnet of opus
   to fix."

   Scope agreed via AskUserQuestion: **everything** (core pipeline + all ~15 player
   ports), **code reading only** (no sweeps re-run for the review itself), output to
   **`docs/`**.

2. Then, across many "go on" / "continue" turns: **execute the review's items**,
   with the standing instruction *"it is important that we test so we do not break
   anything."* Waves 1-5 of the review's own execution order were completed.

NOTE: this file previously held the **Matt Gray** handoff (Driller/LN2/Tusker Stage
A, HEAD 9e00576). That work is CLOSED and shipped; its still-open items
(Deliverance, Quedex, LN2/Tusker play-tests) are carried forward below under
"Matt Gray leftovers" so they are not lost.
</original_task>

<work_completed>

## Branch / commits

Branch **`mattgray-driller-stage-a`**, pushed, level with origin. Working tree
**clean**. 21 commits this session, from `e75700d` to **`2c20e26`**.

| commit | item |
|---|---|
| `ee13f6e` | the review doc itself (30 items) |
| `7fcac5f` | review Appendix A (design pre-analyses) + R31-R34 + R5 status correction |
| `cad8542` | R34 - gitignore `.tokensave/` |
| `6d2b6dd` | R28/R31/R33 - Matt Gray matrix row, player count, dual accuracy dicts |
| `7cff00f` | R23 - `probe_once()` crash oracle |
| `22da326` | R5 - Blackbird E3c(a) verify-and-close |
| `33e8e0a` | R6 - Galway/ROMUZAK `cmp #$90` SF2II hazard |
| `b24899e` | R21 - Sound Monitor sweep made reproducible |
| `b37fb47` | R2 - `sidm2/sf2_caps.py` |
| `f411b4b` | R3 - `sidm2/native_build.py` |
| `80a70d2` | R3b - explicit tempo/n_rows params |
| `e668cda` | docs: R2/R3 status + premise corrections |
| `4a133c3` | R1 - driver merge (-1227 lines, byte-identical) |
| `ebe5934` | docs: R1 status + ROADMAP A5 warning |
| `adf4982` | chore: `.claude/settings.local.json` (user asked) |
| `f797e3f` | R13 - Future Composer Stage B |
| `910b9b1` | docs: R16 closed (measured) |
| `dde449e` | R7 - re-diagnosis |
| `25ed1c6` | R20 - measured capacity, Driller 2 files -> 1 |
| `7a813fd` | docs: R20 recorded |
| `2c20e26` | R18 closed / R19 downgraded |

Test suite: **1693 -> 1747 passed**, 7 skipped, 2 xfailed, **0 failures**.

## Deliverable 1 - the review: `docs/CODE_REVIEW_2026-07.md`

34 items (R1-R34) across 5 tracks (Consolidation / Fidelity / Part-count /
Measurement infra / Hygiene), each with `file:line` evidence, fix sketch,
verification recipe, trap notes, and a Sonnet-vs-Opus recommendation. Plus
**Appendix A** with design pre-analyses for R5/R17/R20/R24, a ROADMAP
cross-reference table, and a dependency-aware execution order (waves 1-8).
Linked from `docs/INDEX.md`.

## Deliverable 2 - executed items

### Wave 1 (all shipped)
- **R34** working-tree triage. `tools/Bobix.asm` + `tools/Disc-o-very.asm` were
  orphaned SIDdecompiler output -> moved to `archive/experiments/` (which is
  gitignored - the repo's own scratch-parking convention). `.gitignore` +=
  `.tokensave/`.
- **R28/R33** `docs/reference/ACCURACY_MATRIX.md`: added the **missing Matt Gray
  row**; fixed the stale "all 12 ported players" header (15 families; counting rule
  now stated).
- **R31** `sidm2/driver_selector.py`: `EXPECTED_ACCURACY` duplicated three of
  `PLAYER_REGISTRY`'s accuracy strings -> laxity/np20/galway now derive from the
  registry. `driver11_sf2`/`driver11_default` stay literal (no registry equivalent).
- **R23** `pyscript/blackbird_crash_probe.py` + `pyscript/sf2_open_in_editor.py`:
  the crash oracle reported a **user-closed window as CRASHED**. Root cause:
  `_spawn_detached` returned a bare pid, and Windows drops an exited process from
  the table, so its exit code was unrecoverable. Now returns the **Popen object**
  (CPython keeps its handle regardless of DETACHED_PROCESS) and classifies via a new
  pure `classify_termination(exit_code)`: `None`->SURVIVED, `0`->**CLOSED**,
  else->CRASHED. CLOSED is excluded from `tally()`'s crash-rate denominator. Added
  opt-in periodic screenshots (`shot_interval`, off by default).
- **R21** `pyscript/soundmonitor_sweep.py` + `pyscript/test_soundmonitor_sweep.py`
  (NEW, 14 tests). The 99.23% SM headline came from **untracked**
  `bin/_opt_sweep_corpus.py`, which parsed a log only produced by a second untracked
  script. New sweep is self-contained (builds all 11 songs itself, parses part
  windows from each build's own live stdout). **Ran it: 99.252% over all 27/27
  parts** - reproducing SOUNDMONITOR.md's own predicted "restoring Dance part01
  gives 99.25%".
- **R5** Blackbird E3c(a): **status corrected, not fixed**. ROADMAP called it the
  "highest remaining audible payoff"; the code shows **E3f already closed it**
  (`build_blackbird_native_song.py:3025-3081` allocates combo fx indices; every
  corpus file fits, worst 25/26 spare). Re-ran the sweep: ADSR **100.0** on
  Glyptodont+Fargo. Shipped the real residuals: `combo_dropped_*` now surfaced in
  `blackbird_sweep.py`'s JSON, and the previously-silent `min_tempo_song < 3`
  no-arming guard now prints. Builder edit verified a byte-identical no-op.
- **R29** full suite re-run (had not been run since `eae7325`).
- **R6** `drivers_src/{galway,romuzak}` `fp_dec`: `cmp #$90` -> `cmp #$80`. SF2II's
  CMP carry is wrong for |A-op|>127, so **every filter ADD row executed as a SET row
  in the real editor** while every offline emulator read clean. Verified by
  **git-stash A/B: exactly ONE byte differs** (the cmp operand, `$90`->`$80` at
  offset `$4a7`). Emptied `KNOWN_UNFIXED` in
  `pyscript/test_sf2ii_emulator_hazards.py`. MoN's copy already used `bmi` (immune);
  Blackbird fixed in B24.

### Wave 2 - consolidation (all shipped, all byte-verified)
- **R2** `sidm2/sf2_caps.py` (NEW). `CAP_B,CAP_I,CAP_TBL,CAP_SEG,STEP = 63,32,256,
  120,100` was re-declared identically in **6** builders; `ST_FIRST,ST_LAST =
  0x16cc,0x1702` in **3** driver_full assemblers. All 9 import now. Blackbird keeps
  its deliberate `CAP_B=96` **and `STEP=150`** override (the STEP part was not in the
  review). A/B: **all 7 native builders byte-identical**.
- **R3** `sidm2/native_build.py` (NEW) + `pyscript/test_native_build.py` (13 tests).
  **Corrected the review's premise**: `gen_includes_song` is NOT a "~180-line
  identical skeleton" - the three signatures take genuinely different data and their
  middles lay out per-player tables. What IS shared: a **22-line byte-identical
  prologue** (-> `make_native_gen` + `lay_out_sequences`) and the
  relative->absolute jump-target fixup, **one expression hand-copied 5 times** and
  the site of a real shipped bug (Blackbird's "B3 BUG FOUND": `(r + b2)` instead of
  `(start + b2)`) -> `program_jump_col`. Deliberately NOT converted after reading
  each site: Galway's filter block uses the row index **on purpose** (freeze-
  terminated programs, a third semantic) and the pulse tables use a fourth rule
  (jump -> 0). A/B: Galway/ROMUZAK/MoN/Blackbird byte-identical.
- **R3b** the mutable-global hazard. `build_galway_trace_song` set `B.TEMPO` on the
  *driver_full* module so `build_galway_native_song` (a **third** module) could read
  it back; `headless_audio` read `TEMPO`/`N_ROWS` from its own scope after callers
  mutated them. Now explicit `tempo=`/`n_rows=` params with a `None`->old-global
  fallback (so untouched consumers are unaffected). Removed a genuinely dead line
  (`B.TEST_INSTR = instrs`). A/B: 4 players byte-identical.
- **R1** driver merge. `drivers_src/common/sf2_native_driver.asm` (NEW) is the
  shared engine; `galway/`+`romuzak/` are 23-line feature-selection shims
  (`FEAT_DRUM_ROWS`, `FEAT_SEEK_PULSE`, `FEAT_INSTR_PULSE`). **Net -1227 lines.**
  Gate met: **assembled machine code byte-identical for both players** (`.prg` and
  wrapped `.sf2`), plus 4 players' real songs byte-identical and the full 40-tune
  Galway corpus 40/40.
  **Overturned A1's 3-way proposal by measurement**: galway<->romuzak is **4 hunks =
  3 clean feature blocks**; mon<->romuzak is **51 scattered hunks**; blackbird ~1962
  diff lines. 51 interleaved `.if`s would cost more than the duplication saves.
  Evidence it's the right split: this session's own R6 fix had to touch galway AND
  romuzak, and **neither** mon (already `bmi`) nor blackbird (fixed in B24).

### Wave 3
- **R13 Future Composer Stage B** - `bin/build_fc_native_song.py` (NEW) +
  `pyscript/test_fc_native_song.py` (17 tests). FC was the last ported player with
  no native driver, chosen as the test that R1-R3 generalizes. **It added no new
  driver and no new engine code**: a MON-compatible `FCShim` feeds the shared
  trace-driven `build_native_song`, and it consumes R2's `sf2_caps`.
  **Result: 14 of 15 corpus voices at exactly 100.0% audible per-frame pitch over
  FULL song length** (5 rips, per-voice n 346-2253). Note placement independently
  **frame-exact** (decode onsets == trace gate-rises, delay +0). Sole residual
  Triangle_Intro v1 **83.6%**/633fr.
  FC is **decode-driven** (not onset-aligned like SDI/DMC) because its parser is
  validated byte-exact - and gate-rise re-derivation would discard the rests, the
  whole reason to build FC natively.
  **Bonus**: Stage B removes Stage A's headline defect (SF2II Driver 11 cannot gate
  a long silent intro; that drove an abandoned Driver-15 investigation).

### Wave 4 - both resolved by measurement, no fidelity code written
- **R16 filter seams - CLOSED, premise stale by ~300x.** Claim was "~25% cost,
  Hawkeye sub0 filter ~75%". **Measured 99.92%** (cutoff AND ctrl/res/routing, full
  384s, n=19168, 5 of 8 parts exactly 100.0). Cause: `build_mon_native_song`'s
  **"WINDOW-START residual filter"** block already implements R16's own fix sketch;
  nobody re-measured. Real residual pinned: **16 frames of 19168 (0.08%)**, the
  first 4-8 frames of 3 parts (driver cold start). Not worth fixing - parts are
  **separate files a user opens individually**, so it's an ~80ms settle at a file's
  opening, not a mid-song seam. ("13 parts" was the fixed-30s count; adaptive is 8.)
- **R7 Galway pulse-PWM - RE-DIAGNOSED, tune list wrong in BOTH directions.**
  Measured distinct per-frame pulse values (orig->built), each tune at **its own
  build subtune**, best-delay searched, Rambo as a validated 100/100/100 control:

  | tune | verdict |
  |---|---|
  | Commando_High-Score | **not defective** (106->106, 99.8-100%) - already fixed |
  | Highlander | v1 only, **317->317 distinct, wrong values** - a different defect |
  | Match_Day | **v2 only** (53->10, 25.4%) |
  | Street_Hawk | **confirmed** (92->25, all 3 voices) |
  | **Wizball** | **worst in corpus** (1092->430) - **never listed in R7** |

  Three hypotheses **eliminated by measurement**: `PULSE_ROW_CAP` trim never fires;
  `PULSE_TABLE_ROWS`(2048) not hit; `pq` quantization stays 1. Real signal is
  upstream - Street_Hawk builds **1 instrument / 1 bundle / 3 pulse rows for 129
  notes** vs Highlander's 634, so the encoder faithfully encodes input that already
  lost the sweep. Shipped a strict no-op (byte-verified): the `PULSE_ROW_CAP` trim
  now announces itself + `GALWAY_PULSE_ROW_CAP` override (it was silently lossy).

### Wave 5 - part-count
- **R20 memory-wall audit - SHIPPED, Driller 2 files -> 1.** `MAX_PART_FRAMES =
  24_000` was splitting at ~40% of real capacity, justified by a "~27,650 play-calls
  ~= 9.2 min" ceiling that is **not in the git history and does not follow from the
  format** (nothing in a Driver 11 file grows with TIME; all tables fixed-size,
  sequence region a fixed 128 x 256-byte slots -> capacity is event **density**).
  Measured: Driller's whole 8320-row/665.6s song is **ONE valid module**, 57/128
  slots, top **$61CF** vs `$D000` (~28KB unused). `convert()` now **probes**: emit
  the candidate range for real, check the two binding limits (<=128 sequences, top <
  `$D000`), grow by doubling, binary-search the edge. Verified: one-part Driller
  walks its orderlists to **[8320,8320,8320]** rows/voice, **zero** cap violations,
  row total == old two parts summed; already-1-part songs **byte-identical** (LN2
  sub2, Tusker sub2). Figure **retracted** in PLAYBOOK's caps table. 2 regression
  tests added.
- **R18 wave-RLE - CLOSED, NO CANDIDATE.** Instrumented the windowing probe on FC's
  5-part `Is_There_a_Difference` to report *why* each cut fires: **bundles bind
  every single cut** (64/66/67/64 vs the 63 cap) while **WAVE sits at 40-61 of 256
  (16-24%)**. RLE would relieve a cap with ~200 rows of headroom -> zero part
  reduction. MoN's Cybernoid 18->11 win was real only because that tune is
  wave-row-bound (and RLE is already applied there).
- **R19 cross-part dedup - DOWNGRADED to P3.** By its own statement it does not
  reduce part count, and its "stabilizes seams" half died with R16 (99.92%).
- **Recorded**: the lossless part-count lever is the **bundle** cap -> confirms
  **R17 (Stage C structural RE)** as the flagship and explains why. A **lossy** dial
  also already exists and is quantified: the probe requires the PRE-cluster raw
  bundle count to fit 63 (no clustering permitted); raising `CAP_B` clusters the
  excess - Blackbird measured **16 parts at CAP_B=64 vs 5 at 128 for ~5.8pp freq**.
  Kept opt-in per player, never a default (standing lossless-only rule).

## Documentation corrected (a major output in its own right)

Several roadmap/matrix claims were measured **false or stale** and fixed in place:
1. ROADMAP's "E3c(a) 40 retriggers open" - already closed by E3f (R5).
2. ROADMAP C4 / matrix "filter ~75% at seams" - **99.92%** (R16).
3. ROADMAP B2 / R7's flat-pulse tune list - wrong both ways (R7).
4. PLAYBOOK's "~27,650 play-calls" ceiling - **retracted as underivable** (R20).
5. ROADMAP A1's 3-way driver merge - right for the pair, wrong for MoN (R1).
6. **ROADMAP A5's "fix the MoN driver file name" would BREAK the build** -
   `build_mon_native_song.py:1763` does `B.GAL = MON_DIR` and `assemble()` hardcodes
   `<GAL>/romuzak_driver.asm`, so the name is **load-bearing** (R1).
7. "MoN has CRLF endings" reads as an anomaly - **all four** `.asm` are CRLF (R1).
8. R3/A2's "~180-line identical skeleton" - measured wrong (R3).
9. ACCURACY_MATRIX "all 12 ported players" - 15 (R33); missing Matt Gray row (R28).
</work_completed>

<work_remaining>

## Wave 6 - R17: Stage C structural synth-table RE (the flagship, Opus, L)

**Now confirmed as THE part-count lever** by R18's measurement (bundles bind every
cut). Design already written in the review's **Appendix A section D-R17**; read it
first. Key points:
- **Stage B is Stage C's oracle**: the existing unrolled build is byte-exact, so
  emit both and compare full per-frame register streams. Any mismatch = the
  structural model is wrong. No listening, no thresholds.
- Therefore roll out **per-instrument hybrid**: instruments whose structural
  programs verify byte-identical use the compact form, others keep unrolled. The
  corpus can never regress; coverage is a ratchet.
- Three designed-against mismatch classes: loop grammar (attack + steady-loop
  split), tick phase (use RLE frame counts, never resample - resampling is lossy),
  note-relative arps (SF2 wave col1 semitone column; never bake absolute notes).
- **Measure first**: count distinct (FM-program, rate) pairs. If slides take their
  rate from the pattern stream, pairs may still exceed 63 and the win comes from
  wave/instrument collapse instead. One-day script on already-parsed data.
- Targets: Supremacy sub2 (70 parts, engines cracked) then Myth sub0, then evaluate
  DMC/SDI bundle-bound files.
- Success order: byte-exact preserved -> THEN part count. A part-count win with any
  register diff is a failure (lossless-only rule).

## Remaining review items (see `docs/CODE_REVIEW_2026-07.md` for full detail)

Wave 7: **R4** (wire the 11 `bin/`-only players into `PLAYER_REGISTRY`),
**R24** (universal trace-first fallback - Appendix A D-R24 has the architecture).
Wave 8: **R8-R12** per-player residuals, **R14** (DMC standard window), **R15**
(name Laxity's 0.07%), **R22** (universalize `sf2ii_vs_real.py`), **R25** (audio
track), **R26** (signature framework), **R27** (bin/ archive), **R30** (broad-except
audit), **R32** (compress CLAUDE.md's Known Limitations - it is loaded every session).

## Immediate follow-ups created by this session's work

1. ~~**Play-test the one-part Driller in real SF2II.**~~ ✅ **DONE 2026-07-30
   (`aed30fe`): 3/3 SURVIVED over 700s, editor clock 11:41 = whole song + loop**,
   against the 2-part build as an interleaved control. One-file Driller is
   shipped. Three bugs were found on the way and fixed in `4b3d2da`:
   - **R20a** the part-probe's slot check was **tautological** (`used <=
     SEQ_SLOTS` with `used` summed over `range(SEQ_SLOTS)`), and the emitter
     dropped over-cap sequences **silently**, its `break` leaving the voice loop
     so later voices went completely silent. Driller unaffected (57<=128).
   - **R23 second pass**: the oracle never checked a trial *began* (idle editor
     at 0:00 read as SURVIVED) → now gated on SF2II's "Playing time" advancing,
     new `NOPLAY` verdict; screenshots were screen-**region** grabs that captured
     whatever covered the editor → now `PrintWindow`.
   - **`pyscript/conftest.py` killed every SIDFactoryII on the machine** at the
     end of *any* pytest session → faked a **100% crash rate on both arms**
     (uniform exit code 15 was the tell). **Never run pytest during a play-test**
     — now scoped to the session's own editors, but keep the rule.
   NB `EDITOR` is **cwd-relative** (`sf2_load_test.py:30`): run the probe from
   the **repo root**; the harness itself spawns the editor with cwd=`bin/`.
2. **R7 continued**: the real work is upstream of `faithful_pulse_program` - inspect
   how `song.pulse[v]` is captured and how gate-regions are segmented in
   `bin/build_galway_trace_song.py` (`note.tie -> EMPTY_PUL` at ~:645 means one
   program serves a whole legato region; a tune-spanning region explains
   Street_Hawk's 1 bundle). Verify with the R7 distinct-count table (counts are
   alignment-independent; match% is not).
3. **R13 residual**: localize Triangle_Intro v1's 83.6%. **Use the `t0` bounds
   `build_song` already computes** - a brute-force `t0` search over the original
   produces nonsense (see attempted approaches).
4. **Myth sub0 part1 filter 77%** (ROADMAP B5) is still **unverified** - do not
   assume it followed R16. Needs the py65 **emulation** trace; shapes differ
   (`(cutoff, ctrl)` tuples vs `per_frame`'s int `fcut`).
5. **R3 residual**: the globals-as-parameters pattern persists in
   `build_romuzak_native_song` (`B.TEMPO`/`B.N_ROWS`), `build_mon_native_song`
   (`B.TEMPO`/`B.TEMPO2`/`B.TEMPO_SWALLOW`/`B.TEMPO_SCHED`) and
   `build_blackbird_native_song` (`B.TEMPO`/`B.TEMPO2`) - **4 more channel
   variables**, all working via the `None` fallback. Converting them is the
   prerequisite for actually MERGING the two 353-line driver_full files.
6. **FC follow-ups**: `FCShim._voice_blocks` returns one flat block; `fc_parser`
   exposes real `voice_blocks` (51/41/51 on Triangle_Intro) which would let repeated
   blocks share sequences (part-count optimisation). Native `.prg` FC modules in
   `out/fc_native/` are not buildable yet (siddump needs a PSID wrap).

## Matt Gray leftovers (carried forward from the previous handoff)

- **Deliverance** (1990, a THIRD generation): `_scan_for_shim()` finds the shim, but
  `locate()`'s "6 consecutive `LDA abs,y` stepping by 2" no longer holds. Steps in
  the old handoff (git history of this file at `9e00576`).
- **Quedex** (1987, FOURTH generation): no `ldx #$00/$07/$0e` + `jsr` triple exists;
  needs a second entry-point strategy, not just a new `locate()` branch.
- **LN2 subtunes 5 and 6** have unusable sample sizes (n=19 and n=1) - their "100%"
  is not evidence.
- **Stage A for LN2/Tusker was never play-tested** in SF2II.
- The other ~50 HVSC `Gray_Matt` files are untouched/unclassified.
</work_remaining>

<attempted_approaches>

## Failures and dead ends - do not repeat

**Brute-force `t0` alignment search when the real bounds are known.** Twice.
Trying to localize Triangle_Intro v1's residual (R13) and again on Myth, I searched
for the best `t0` over the original instead of using the `t0` values `build_song`
already computes. It "found" a 15-frame window and produced 25.1%/6.7%/77.8%
garbage. **Discarded rather than reported.** Always use the known bounds.

**Comparing two differently-shaped filter traces (R16/Myth).** `per_frame(...)[1]`
is an int `fcut`; `siddump_filter_trace` returns `(cutoff, ctrl)` tuples. Comparing
them returned a meaningless **0.0%**. Discarded. Compare like with like.

**Measuring a build's original at the wrong subtune (R7).** `build_galway_corpus`
builds Wizball at **subtune 3**; I measured the original at subtune 0 and got a
spurious 0.0%. Always read the builder's own subtune (`SUBTUNE` overrides +
PSID `start_song-1`).

**Assuming the cap named in the docs is the binding one (R18).** Wave rows were
assumed to be the part-count constraint; measurement showed bundles bind every cut
and WAVE sits at 16-24%. Measure which cap binds before relieving one.

**`PULSE_ROW_CAP` as the R7 root cause.** Plausible (its own comment admits it is
an arbitrary safety margin, and its trim loop is lossy) but **the trim never fires**
on any affected tune. Instrumented and disproved in one run. Same for
`PULSE_TABLE_ROWS` and `pq`.

**Trusting the review's own premises.** Of the items executed in waves 4-5, **three
of five had a false or stale premise** (R16 stale ~300x, R7's tune list wrong both
ways, R18 no candidate). The review was in places repeating stale documentation.
**Measure before fixing** - it was consistently more valuable than the fixes.

**Naive `gen_includes_song` unification (R3).** Considered and rejected after
measuring: three genuinely different signatures + per-player table layout. Forcing
one signature would need a dozen mutually-exclusive flags.

**Merging MoN/Blackbird drivers (R1).** Rejected on measurement: 51 hunks and ~1962
diff lines respectively. `.if`-maze cost exceeds the duplication saved.

**A bash heredoc containing apostrophes inside `$(cat <<'EOF')`** broke parsing
once; used `git commit -F <file>` from the scratchpad instead.
</attempted_approaches>

<critical_context>

## Verification discipline that worked (reuse it)

- **git-stash A/B + byte-diff** is the strongest available gate and was used for
  every refactor: stash the **complete** changeset (including new files and
  transitive import deps), rebuild, byte-compare. R1 achieved **byte-identical
  assembled machine code**, which proves behavior preservation outright.
- **`drivers_src/*/{layout,freqtable,tempo_sched_*}.inc` are regenerated by every
  build** - `git checkout --` them before staging. This bit nearly every run.
- Native builds are launched from repo root; SF2II must launch with **cwd=bin/**.
- 64tass path: `C:\Users\mit\Downloads\64tass-1.60\64tass-1.60.3243\64tass.exe`.

## Non-obvious mechanics discovered

- **64tass resolves a nested `.include` relative to the INCLUDING file**, not cwd -
  tested empirically. Hence `-I <player_dir>` in both `assemble()` calls after R1.
  Without it the build fails loudly (it cannot silently pick a wrong file).
- **`emit_one` does `B.GAL = MON_DIR`** (`build_mon_native_song.py:1763`), so every
  shim-based Stage B assembles **MoN's** driver. That is why FC's Stage B needed no
  new driver - and why MoN's "misnamed" `romuzak_driver.asm` is **load-bearing**.
- **`SF2HeaderGenerator.PLAYER_ADDRESSES` is a CLASS attribute** - mutating it in
  place leaks across every song built in one process. `make_native_gen` copies it;
  a test pins this.
- **FC rests park a near-zero `$0002` in `$D400` with the gate OFF** (note >= 96
  reads past the 96-entry freq table). A build emitting a true rest "mismatches" on
  an inaudible register - Triangle_Intro v1 reads **57.8% raw vs 100.0% audible**.
  `Triangle_2_years` (zero rests) is the control: raw ~= audible. **Any player whose
  rests leave a non-zero freq register shows this false penalty.**
- **FC's `FCInstrument` field names follow the V4.1 manual, which is WRONG for
  V1.0**: byte `[5]` (named `vibrato`) holds the arp offsets; the field named `arp`
  (byte `[6]`) is the pulse-sweep ctrl and is unused. Confirmed against Stage A.
- **FC has two independent `+1`s**: `frames_per_tick = speed+1` and
  `ticks = dur+1`. Both are load-bearing; tests pin them.
- **Blackbird's `min_tempo_song < 3` guard disables hard-restart arming for the
  WHOLE song** - previously silent, now printed.

## Standing rules honored

- Accuracy/byte-exactness over speed, cost and file count; **never ship lossy output
  silently** (this is why the `PULSE_ROW_CAP` trim now announces itself, and why the
  `CAP_B` part-count dial stays opt-in).
- Never claim a percentage without its **window and n**; an empty comparison is "no
  test ran", not 100% (`score_pct` returns None).
- Root-clean rule: no `.py` in repo root; all Python in `pyscript/` or `bin/`.

## Environment

- Corpora: `SID/Fun_Fun/` (FC, Sound Monitor, ROMUZAK), `SID/Galway_Martin/` (40),
  `SID/LFT/` (Blackbird), `SID/Tel_Jeroen/` (MoN), `SID/Gallefoss_Glenn/` (SDI),
  HVSC Matt Gray at
  `C:\Users\mit\Downloads\HVSC_85-all-of-them\C64Music\MUSICIANS\G\Gray_Matt`.
- `/tmp` does not exist; use the session scratchpad.
- Bash tool caps at 10 min - long corpus runs need `run_in_background`.
- The tokensave hook blocks grep on symbol-like patterns; `export
  TOKENSAVE_DISABLE_GREP_HOOK=1` to override for one call.
</critical_context>

<current_state>

## Status

- Branch **`mattgray-driller-stage-a`**, HEAD **`2c20e26`**, **pushed**, level with
  origin. Working tree **clean** (only regenerated `.inc` artifacts appear
  transiently after builds - always `git checkout --` them).
- Full suite: **1747 passed, 7 skipped, 2 xfailed, 0 failures**.
- No PR opened.

## Deliverables

| item | status |
|---|---|
| `docs/CODE_REVIEW_2026-07.md` (34 items + Appendix A) | **complete**, kept updated as items closed |
| Wave 1 (R34, R28/R31/R33, R23, R21, R5, R29, R6) | **complete** |
| Wave 2 (R2, R3, R3b, R1) | **complete**, all byte-verified |
| Wave 3 (R13 FC Stage B) | **complete** (14/15 voices 100% audible) |
| Wave 4 (R16, R7) | **R16 closed by measurement; R7 re-diagnosed, fix NOT written** |
| Wave 5 (R20, R18, R19) | **R20 shipped (Driller 2->1 file); R18 closed; R19 downgraded** |
| Wave 6+ (R17 flagship, R4, R24, R8-R12, R14-R15, R22, R25-R27, R30, R32) | **not started** |

## New files this session

`sidm2/sf2_caps.py`, `sidm2/native_build.py`,
`drivers_src/common/sf2_native_driver.asm`, `bin/build_fc_native_song.py`,
`pyscript/soundmonitor_sweep.py`, `pyscript/test_soundmonitor_sweep.py`,
`pyscript/test_native_build.py`, `pyscript/test_fc_native_song.py`,
`docs/CODE_REVIEW_2026-07.md`.

## Open questions / pending decisions

1. ~~One-part Driller is not SF2II play-tested~~ ✅ **RESOLVED 2026-07-30** —
   3/3 SURVIVED, full duration, clock 11:41 (see work_remaining #1).
2. **R7's fix is not written** - only the diagnosis. Deliberate: the remaining work
   is genuine RE on Galway's pulse capture for 2 tunes.
3. **Myth sub0 filter 77%** unverified (harness shape mismatch).
4. Whether to spend the **lossy `CAP_B` dial** on any player (3.2x fewer parts for
   ~5.8pp freq). Currently opt-in only; needs a user decision, not a default.
5. `.claude/settings.local.json` was committed this session at the user's explicit
   request (`adf4982`) after being deliberately unstaged for many sessions.
</current_state>
