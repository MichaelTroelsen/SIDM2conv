<original_task>
The session opened with "read what next", i.e. read this file. The version it found was itself
stale (written at HEAD `dee93ba`, claiming "Stage B not started" when Stage B had shipped), so the
first act was to report that and re-derive state from `docs/players/HARDTRACK.md`.

Everything after came from the user repeatedly saying "cont"/"continue" plus four explicit asks:

1. "read what next"            -> report state; the handoff was 10 commits stale.
2. "push and commit"           -> the filter-engine work.
3. `/subtask` "update whats-next.md"
4. "rung 3"                    -> run PLAYBOOK §4 rung 3.
5. "do 1."                     -> diagnose the (apparent) SF2II discrepancy.

All work is HardTrack Composer except two SF2-viewer bug fixes found while using its output.
</original_task>

<work_completed>

## HEAD `848972e`, v3.25.0, tree clean, `origin/master` in sync. Tests 2,297 pass / 8 skip / 2 xfail.

### The engine work (shipped)
- **The filter is modelled.** It is GLOBAL, not per-voice: the engine sits past the `dex / bmi` at
  `$1583` that ends the voice loop, so it runs once per frame AFTER all three voices, and its
  cursor/accumulator/delta/mode live in self-modified operands. Byte-exact vs siddump: `$D416` and
  `$D417` **100% on 32,967 frames**, `$D418` 100% on 9,990 — but `$D418` is exercised by only
  **10 of 33 files**, the rest withheld by `exercised()`. `$D415` is never written (0 stores).
- **Five negative controls**, four of which break the score (wrap 24.75%, stepper 23.90%, f6/f7
  swap 28.34%, `f12==0` routing-clear 48.28%). The fifth — the field-5 bit-4 re-arm gate — moves
  NOTHING, recorded as a negative result: only 21 instruments set it, one has a filter to re-arm.
- **A player bug reproduced**: the second build's `$62` handler is `STA $D406,X` where it means
  `,Y`, so a `$62` on voice 1/2 zeroes part of VOICE 1's frequency. Exactly the 15 second-build
  files carry it. `Shogoon-Rave` voice 1: 43 misses -> 1. Found with py65 by logging which PC
  wrote the register, after three static readings fitted the data and were all wrong.
- **Second build seeded per-variable** from each variable's own consumer (`voice_var_addrs`) --
  a positional table cannot follow that build because its CODE differs too. Ablation priced the
  transient: `mode` alone is 1.67 points.
- **Out-of-range arp reads resolve to live variables** (`_var_addr_map`). An arp offset can push
  the note index past the 96-entry table into the player's own variables; the real player reads
  live RAM, the model read the frozen image. **Layout-seeded population now EXACTLY 100.00% on
  frequency (0 of 53,569)**; second build 99.89%. The split is the evidence.
- `Instrument.hard_restart` renamed **`skip_filter_rearm`** (it gates the filter re-arm, nothing
  else; zero callers).

### Audio / editor evidence (both rungs now run)
- **Rung 4 (listening pass)** run for the first time. It found a real defect no headless metric
  could: the **`$D418` passband was never captured**, so every render was low-pass while
  `Love_tune_2` is low+band 100% of frames. Fixed; centroid -99.3 -> -51.4 Hz. **DMC had the
  identical gap and is also fixed** (verified by byte-diffing the SF2: exactly 8 bytes, all filter
  SET rows, `low -> low+band`). FC/SDI were right by luck; Hubbard/SoundMonitor have no passband.
- **Rung 3 (instrumented SF2II) PASSES.** SF2II plays our Stage B SF2 **identically to our own
  render** — 100% freq/waveform/pulse on all three voices at offset 0. No SF2II-only hazard.

### Two SF2-viewer bugs, both "a Laxity constant applied to every driver"
- `_detect_laxity_driver()` tested `load_address == 0x0D7E`, which is the SF2 CONTAINER address --
  identical for every driver -- so it returned True for EVERY file. Now tests the driver NAME.
  Needed `_normalize_driver_name` because the name ships in two encodings (screen-code and ASCII);
  the first attempt regressed genuine Laxity files. 17/17 correct.
- Driver 11 orderlists were read from the hardcoded LAXITY file offset `$1766`, landing on zeros,
  so every position exported as `A000`. Real address is the Music Data block's word at offset 12.
  Verified by an invariant the broken read cannot satisfy: sequences are numbered 0..N with no
  gaps, so a correct orderlist references exactly max+1 distinct sequences.

</work_completed>

<work_remaining>

1. **Stage C's FM prong** — the biggest structural win, now PRICED. Bundles bind first (79 > 63 at
   window 1700), instruments second; wave/filter/seq tables never come close. A bundle is an
   (FM, pulse) pair and the pair count tracks FM almost exactly. **FM collapses 71 -> 8** when read
   as pitch-independent semitones from the wave program's arp column instead of per-note Hz-delta
   unrolls. Every cheaper lever is ruled out BY MEASUREMENT: `MON_PULSE_CANON` and `MON_WAVE_CANON`
   change nothing, and `BUNDLE_TOL` swept 0/2/4/8/16/32 stays at 79 — those 71 programs are
   genuinely distinct in Hz space, which is exactly what a structural form fixes.
   ⚠️ 8 is the FM side alone; pulse stays at 34, so the resulting bundle count needs the
   implementation to settle. Touches a builder shared by SEVEN players.
2. **`sf2ii_vs_real.py` needs a PER-VOICE offset.** It picks one global offset by maximising the
   SUMMED frequency match, which is a compromise when voices need different alignments — that is
   what produced two retracted conclusions this cycle. Galway and MoN use the same tool.
3. **SR-only `$7D` row.** ADSR is the weakest register in the audible window (88-94%) and the
   residual is systematic: AD always agrees while the original writes SR = `$00` (HardTrack's
   pre-note-on hard restart, on frames that PRECEDE the capture window). ⚠️ `hard_restart = 1` is
   PROVABLY wrong — the driver's `$7D` row zeroes AD too and AD differs on 0/10/20 of 1,397 frames.
   A correct fix is asm in the shared driver; audible value unproven.
4. **Second build's remaining 47 frames** — needs more of its variable layout mapped.
5. **Laxity's orderlist address** in `sf2_viewer_core` — the hardcoded `$1766` does not survive
   inspection for Laxity either (the block word disagrees on all five files tested), but Laxity has
   its own working parse path and choosing needs Laxity ground truth. Scope pinned by a test.
6. About half the rung-4 brightness gap is unexplained; ADSR/SR is the best candidate (item 3).

</work_remaining>

<attempted_approaches>

### ⚠️ THREE wrong conclusions this cycle, ALL from alignment
This is the single most important thing to carry forward.

1. **A filter-capture "fix" — REVERTED (`0ed5986`).** The cutoff matched 0/800 at shift 0 and
   757/800 at -3, and `onset_delay` is exactly 3, so it looked settled. But the WHOLE part render
   sits at -3 — all three voices' frequency also peaks there (96.1/95.7/77.1% vs 26.5/4.7/2.4% at
   0). The cutoff's -3 was already correct; "fixing" it to 0 desynced the filter from the voices.
   **The tell was present and ignored**: a large register gain with zero audible change.
2. **"rung 3 is inconclusive, the tool is unreliable" — RETRACTED.** The control was
   `out/Cybernoid_II.sf2`, a Driver 11 Stage A build, not the native Stage B build the byte-exact
   claim refers to. The native build (`out/mon/`, from `build_mon_native_song.py`) scores 100% on
   every register of every voice.
3. **"Stage B fails rung 3" — RETRACTED.** An artifact of the tool's single global offset. Done per
   voice, the same comparison gives 91.2/93.4/64.1% at shift -3 against the tool's 66/21/61%.

**The rule**: a per-register or per-voice best-offset means nothing without the render's GLOBAL
offset. `measure_voices` uses a best-delay alignment for exactly this reason.

### Other measurement traps hit
- An "equal track lengths" invariant in a new test failed on Hopscotch (44/48/48) — voices loop at
  different points. The invariant was wrong, not the code. Replaced with sequence contiguity.
- A `BUNDLE_TOL` sweep used the wrong env name and silently ran tol=0 six times; the
  `effective@tolN` label in the output is what caught it.
- A test harness used `startswith('SF2/')` where Windows `glob` returns `SF2\` — reported 8 false
  failures against correct code.

### Doc drift, caught by an audit
CLAUDE.md and ACCURACY_MATRIX still carried a RETIRED lead ("the waveform match falling 86% ->
70-79%") four commits after the correction landed in HARDTRACK.md. Also two "runs all" test counts
where only one had been maintained. Every headline figure was re-run and reproduces exactly,
including the derived ones (32,967 = 17,982 + 14,985; 97 = 13 + 84).

</attempted_approaches>

<critical_context>

- **Two fidelity columns, never averaged**; always quote the match window (it has NO plateau).
- **Stage A > parser is an ARTIFACT** — quote retention (99.69%), not the diluted 91.34%.
- **`$D418`'s 100% rests on 10 files of 33** — quote the file count, or it reads as 3x the evidence.
- **The render sits at -3.** Any per-register alignment must be judged against that.
- **The filter is GLOBAL** — do not model it per-voice.
- `SID/Shogoon/` is mixed-player: 38 of 150 files.
- Stage B accuracy figures are true of our render AND of the editor (rung 3 confirmed both).
- Native MoN builds live in `out/mon/`; `out/<name>.sf2` is the Driver 11 Stage A build. Using the
  wrong one as a control produced retraction #2.
- `bin/SIDFactoryII_dbg.exe` is the patched editor that dumps `SIDFR <frame> r0..r24` per frame.
- Build-generated `drivers_src/{mon,romuzak}/*.inc` get dirtied by any native build; `git checkout`
  them (`bin/_sm_build_all.py` does the same).

</critical_context>

<current_state>

| item | status |
|---|---|
| RE (format, all 13 fields, filter, vibrato, slides) | **complete** |
| `sidm2/hardtrack_parser.py` / `hardtrack_synth.py` | **complete** — every register group predicted |
| Register fidelity, layout-seeded population | **frequency EXACTLY 100.00%** (0 of 53,569) |
| Stage A (`bin/hardtrack_to_sf2.py`) | complete, 99.69% retention |
| Stage B (`bin/build_hardtrack_native_song.py`) | complete, 33/33 build |
| PLAYBOOK §4 rung 3 (SF2II capture) | **PASSED** |
| PLAYBOOK §4 rung 4 (listening pass) | **run**; found + fixed the passband defect |
| Stage C | **not started**, priced at 71 -> 8 FM programs |
| `DriverSelector` wiring | not done, deliberately — both stages are `bin/` tools |
| tests | 121 HardTrack + 4 SF2-viewer; suite 2,297 |

</current_state>
