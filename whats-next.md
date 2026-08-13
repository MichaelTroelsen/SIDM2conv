# Handoff — SIDM2 session, 2026-08-12/13

<original_task>
Opened with **"read what next"** on the previous session's handoff, then
**"do the task on the list"** and repeated **"continue"**. No pre-set scope; the
user drove item by item and asked once for a task listing with model and
subtask/main labels.

The list came from the previous handoff's `work_remaining`, and then grew from
what the work uncovered. One `/subtask` fork was launched (SDI passband fix) and
stopped by the user after it had applied the edit correctly.
</original_task>

<work_completed>

**22 commits**, `c1c85cb..13ce999`, all on `master`, **NONE PUSHED**.
Working tree clean apart from this file. Suite at HEAD: **2431 passed,
8 skipped, 2 xfailed, 0 failures** (~235 s).

## 1. The SDI corpus sweep was measuring nothing — `fe4375d`, `5b0caf4`

The previous session left a 441-file sweep running. It had printed
`built 161 refused 38 errored 242 of 441`. **That was a 274-file A–O sample.**
From file #275 onward every child returned rc `3221225794`
(`STATUS_DLL_INIT_FAILED`) with no output — ~5 h in, the parent could no longer
spawn processes — and the sweep recorded all 167 in the same `errored` column as
real per-file failures. Three of them build cleanly on a fresh invocation, so
167 "results" were fabrications.

Re-ran the tail in chunks of 20 (each a fresh process tree; the exhaustion is
cumulative in one parent). **Full corpus: 262 built, 62 refused, 117 errored.**
Per-variant medians A 99.9 / B 99.9 / C 98.1 / D **95.9** / DELTA 99.9 / E 99.7 /
V 96.8 over 786 voices. **Variant D is 7 of its own 15 voices below 90** and is
5 files — its median is a sample, not a verdict.

The sweep now quarantines those return codes as `unmeasured`, aborts after
`--infra-abort` consecutive ones (default 3), and prints a resume command.

## 2. `n` wired into the SDI builder — and it is weaker than it looks — `94ed09b`

`fmt_pct(p, n=…)` now carries frame counts. **But the `n` is the SONG LENGTH,
identical on all three voices** (Kirby 2144×3, Delta 7770×3), because
`measure_parts` skips a frame only when *both* sides have freq 0 and siddump
holds a voice's freq through its rests. It answers "was the song long enough",
not "did this voice carry information". The marker never fires on this corpus
(smallest n = 802).

## 3. The launch classifier moved into the shared harness — `e947da4`

`fidelity_common.launch_failure()`. `soundmonitor_sweep` and `blackbird_sweep`
had the identical shape and now route through it. A child that produced OUTPUT
is never classified, however it exited.

## 4. THE BIG ONE: a fix in a builder is not a fix in the corpus

`PATTERNS.md` **F7** (`2affa06`) is the durable write-up. Found on **four**
players; `pyscript/passband_check.py` (`614c298`) measures the ARTIFACT.

| player | cause | before | after |
|---|---|---|---|
| HardTrack | stale artifacts (31 of 33 predate `cffc51e`) | 2 by construction | **24/33** |
| DMC | stale artifacts (968 of 984 `.sf2`) | 31/57 | **55/57**, then 50/74 after the corpus grew |
| MoN | 7 stale + **`Myth` a builder gap** | 9/19 | **17/19** |
| SDI | **builder never passed a passband at all** | 15 of 30 sampled fail | fixed, **corpus NOT rebuilt** |

- **Why it hid**: every per-player fidelity scorer is structurally blind to
  `$D418`. `Balloon` re-measures **byte-identical** before and after its fix.
- **`Myth`** needed its own builder (`<SUB> <warg>`, no path) — and *still* came
  back 0.0%, because that builder had the same gap. It could not take the others'
  fix: its `frames`/`ftr` come from a py65 `capture()`, so `$D418` is recorded
  there instead, on the same clock. 0.0% → **100.0%**.
- **SDI's V path is deliberately still a 2-tuple** — py65 `v_traces` records no
  `$D418`.

## 5. The passband is a CORRECTNESS fix, not the brightness fix — `db22818`, `6a36062`

8-tune A/B via `HT_NO_PASSBAND=1` (both arms from today's builder):

    centroid   mean  +3.95 Hz   closer on 4/8
    rolloff    mean -32.54 Hz   closer on 2/8   <-- worse
    level dBA  mean  +0.41      closer on 7/8   <-- only consistent gain

**"Missing passband reads as darker" is REFUTED** — on 6 of 8 our low-pass-only
render was *brighter*. Confound checked, not assumed: the two no-passband arms'
register traces are identical across all 1400 frames.

## 6. The DMC corpus figure — `890a961`, `1ca6665`

`pyscript/dmc_native_sweep.py` replaces untracked `bin/_dmc_fidelity.py` and
reproduces `Balloon` exactly (`f 80.6/100.0/97.7`, n=19996). First corpus figure:
**72 of 88 scored**, 14 refused, 2 errored; medians **freq 94.7 / wf 100.0 /
pulse 100.0** over 216 voices, **87 of 216 freq voices below 90**, and 9 songs
under the 250-frame floor.

## 7. The brightness gap re-scoped — `13ce999`

Across 9 tunes, each measured **inside its own part-1 span**, our render is
darker on **2** and brighter on **7** (to +172 Hz). There is no corpus-wide
deficit. ~half the gap remains on `Love_tune_2` alone.

</work_completed>

<attempted_approaches>

## Things I got wrong, in order — read this section first

**The same window error four times, in three tools.** This is the through-line
of the session.

1. `dmc_native_sweep` scored part 1 against a fixed 20 s window. DMC parts are
   2–20 s, so `Cant_Stop` (114 parts) read 34.8/86.0/91.5 — measuring the window,
   across 53 of 57 songs.
2. I then claimed a guessed window only *deflates*. **Wrong**: part-1 spans run
   6.9 s–399.9 s, so a short window **flatters** — `Blobby`'s 20 s reported
   97.9% on a voice whose real 67.9 s part scores 59.5%.
3. `passband_check` had the identical bug. I published "9 HardTrack mode-TIMING
   failures" and **retracted it** (`4bfa96c`): part 1s are 6–12 s, and at their
   true spans `Something_to_Eat` 68.7→**100.0** (31 changes vs 31, not 88 vs 87),
   `Illmatic_end` 71.1→**100.0**, `Takisobie` 57.2→99.8, `Fun_Factory` 69.5→99.0.
   `Domino_Dancing` 99.0→**100.0** likewise.
4. Then the **audio** measurements for §7 — caught before publishing only
   because #3 had just happened.

**Over-running can only MANUFACTURE disagreement, never hide it.** So every
"N of M correct" figure survives; only failures were downgraded. Multi-part
failures now report UNCONFIRMED unless `--seconds` is asserted.

**Three more wrong readings, all mine:**

- **"16/16 Blackbird pass"**, then "16 originals never route a voice", then "our
  builds route the filter 56–100% where the original routes 0%" — a real-looking
  audible defect. **All against silence**: `SID/LFT/*.sid` produce NO trace under
  siddump (0 frames with freq or waveform, `$D418`=0). An all-zero trace is
  byte-identical to "never filters" and to "undriveable". Fixed with
  `has_evidence()` (`f637802`) — a rule this repo already had
  (`zig64-gate-false-pass`).
- **Three DMC files reported as failures three times** before I checked
  `$D417`: they route NOTHING, so the passband selects among silent outputs —
  true statement, nil severity (`c3c4240`).
- **A "static vs modulating" rule that fired regardless of score**, condemning
  three files at 100.0% whose originals' only "change" is the initial
  `off → mode` transition.

**Dead ends worth not repeating:**

- `Cant_Stop`'s part 1 is 17.9 s, not the ~5 s I assumed from its 114 parts.
  **Part counts do not imply equal durations** — the later parts are the short ones.
- My loop-detector for inferring part spans false-positived on `Balloon`
  (reported a loop at 120 frames in a genuine 400 s part). Scrapped.
- **Heredoc backslash trap, hit 3×**: `python - <<'PY'` eats one backslash level,
  so `\\n` in a search string becomes a real newline and `f"\\n…"` in inserted
  code becomes an unterminated f-string. **Write patch scripts with the Write
  tool** when they contain backslashes.

</attempted_approaches>

<critical_context>

- **`passband_check.py --player {hardtrack,dmc,mon,sdi,fc,blackbird}`** is the
  new artifact-level check. It compares `$D418` bits 4-6 ONLY (low nibble is
  volume), fits the boot offset over `range(-4, 9)` and reports it, and refuses
  three ways: no reference trace, filter never exercised, multi-part failure
  without an asserted window.
- **Routing matters as much as mode**: `$D417`'s low nibble picks which voices
  enter the filter. A passband mismatch where nothing is routed is inaudible.
- **`whats-next.md` was left modified-uncommitted by the previous session too** —
  it is not tracked as clean; this file replaces that content.
- Environment unchanged: Windows, `py -3` (3.14), `pytest-timeout` NOT installed.
  Scratchpad holds every patch/probe script from this session.

</critical_context>

<current_state>

HEAD `13ce999`, branch `master`, **22 commits unpushed**, tree clean but for
this file. Suite 2431 passed.

| task | state |
|---|---|
| #15 SDI corpus rebuild + full check (281) | **PENDING** — builder fixed, 262 songs still carry the low-pass default. *Sonnet, subtask.* |
| #16 HardTrack brightness gap | **RE-SCOPED, not closed.** Next real step: HRC per-note lookahead, then A/B the audio. *Opus, main.* |
| #18 Blackbird passband unmeasurable | **PENDING** — needs the simulator or VICE wrapper as reference. *Opus, main.* |
| #19 this handoff | done |

**Also open, unfiled:** `French_Frites` is a confirmed real passband failure
(49.6% at its true 39 s span, holding LP+BP+HP while the original moves through
HP and BP+HP). `DMC_Demo_IV_tune_5` reads 98.0% at 10 s and its 3 mode changes
all occur with the **cutoff unchanged** — the one mechanism with support: a
passband is only expressible where the builder emits a filter row, so a
mode-only change has nowhere to go. `Zoom`, which passes at 100%, changes mode
only where the cutoff also moves. **That hypothesis is untested beyond 3 files.**

</current_state>
