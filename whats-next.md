# Handoff — SIDM2 session, 2026-08-12/14

<original_task>
Opened with **"read what next"** on the previous handoff, then **"do the task on
the list"** and repeated **"continue"**. No pre-set scope. The user asked once
for a task listing with model and subtask/main labels, launched one `/subtask`
fork (SDI passband fix) and stopped it after it had applied the edit correctly,
and twice said **"push"**.
</original_task>

<work_completed>

**31 commits**, `c1c85cb..2b18197`, all pushed to `origin/master`. Tree clean.
Suite at HEAD: **2436 passed, 8 skipped, 2 xfailed, 0 failures**.

## The finding: a fix in a BUILDER is not a fix in the CORPUS

`PATTERNS.md` **F7** is the durable write-up. Four players had shipped artifacts
contradicting their own documentation, and nothing noticed because **every
fidelity scorer in this repo is structurally blind to `$D418`** —
`Balloon` re-measures byte-identical before and after its fix.

`pyscript/passband_check.py` measures the ARTIFACT. Final state:

| player | cause | result |
|---|---|---|
| Blackbird | none — was never broken | **16/16**, via its simulator |
| MoN | 7 stale artifacts + **`Myth` a builder gap** | **17/19** (2 unexercised) |
| HardTrack | 31 of 33 artifacts predated `cffc51e` | **25/33**; all 9 residuals explained, none a wrong passband |
| DMC | 968 of 984 `.sf2` predated it | **50/74**; 2 genuine defects |
| SDI | **builder never passed a passband at all** | fixed + corpus rebuilt → **237/281** |

Two builder gaps, both invisible to every existing scorer: **SDI** (never passed
a 3-tuple) and **`Myth`** (its own builder, py65 `capture()`, fixed on the same
clock as `ftr`).

## Other work

- **The SDI Stage B sweep was measuring nothing.** The previous session's run
  printed `built 161 … of 441`; it was a **274-file A–O sample** — 167 files
  returned `STATUS_DLL_INIT_FAILED` and were recorded as per-file failures. Full
  corpus after the chunked re-run: **262 built**, medians A/B/DELTA 99.9, E 99.7,
  C 98.1, **D 95.9 (7 of its own 15 voices below 90)**, V 96.8.
- **`pyscript/dmc_native_sweep.py`** replaces untracked `bin/_dmc_fidelity.py`,
  reproduces `Balloon` exactly, and **refuses to score without an asserted
  window**. First DMC corpus figure: **72 of 88**, freq median 94.7 / wf 100.0 /
  pulse 100.0 over 216 voices, 87 voices below 90, 9 songs under the 250-frame
  floor.
- **`fidelity_common.launch_failure()`** — shared by all three sweeps.
- **`HT_NO_PASSBAND=1`** — lets the passband be A/B'd against today's builder.
- **The passband fix is CORRECTNESS, not audio.** 8-tune A/B: centroid closer on
  4/8, rolloff **worse** (2/8), only A-weighted level consistent (7/8).
- **The HardTrack brightness gap is ONE FILE.** Across 9 tunes measured inside
  their own part-1 spans, our render is darker on **2** and brighter on **7**
  (to +172 Hz). No corpus-wide deficit exists to close.

</work_completed>

<attempted_approaches>

## Read this first: the same error, five times, in three tools

**Comparing a build's part 1 against a window longer than the part.** Past its
end our part LOOPS against the original's continuing music, and the difference
scores as a defect.

1. `dmc_native_sweep` scored part 1 against a fixed 20 s window. DMC parts are
   2–20 s; `Cant_Stop` read 34.8/86.0/91.5 — the window, across 53 of 57 songs.
2. I then claimed a guessed window only *deflates*. **Wrong** — spans run
   6.9 s–399.9 s, so a short window **flatters**: `Blobby`'s 20 s reported 97.9%
   on a voice whose real 67.9 s part scores 59.5%.
3. `passband_check` had the identical bug. I published **"9 HardTrack
   mode-TIMING failures"** and retracted it: at true spans `Something_to_Eat`
   68.7→**100.0** (31 changes vs 31, not 88 vs 87), `Illmatic_end` 71.1→**100.0**,
   `Domino_Dancing` 99.0→**100.0**.
4. Then the **audio** measurements for the brightness re-scope — caught before
   publishing only because #3 had just happened.
5. And it made the "mode change needs a filter row" hypothesis look *better*
   than it was: I checked its counterexample at 28 s and saw 1 mode change where
   its true 39 s span has 2.

**Over-running can only MANUFACTURE disagreement, never hide it.** So every
"N of M correct" figure survives; only failures were downgraded. Multi-part
failures now report UNCONFIRMED unless `--seconds` is asserted.

## Four more wrong readings, all mine

- **Three confident Blackbird conclusions drawn against silence** — "16/16
  pass", then "16 originals never route a voice", then "our builds route the
  filter 56–100% where the original routes 0%", which reads as a real audible
  defect. `SID/LFT/*.sid` produce NO trace under siddump. Fixed with
  `has_evidence()`; the reference is now the simulator.
- **Three DMC files called failures three times** before I checked `$D417`:
  they route nothing, so the passband selects among silent outputs.
- **A severity rule running over the wrong frames.** The unrouted check was
  GLOBAL, so it caught all-unrouted files and missed every partial case —
  `Altered_States_Tune_2`'s 47 mismatches are *all* unrouted.
- **A "static vs modulating" rule that fired regardless of score**, condemning
  three files at 100.0%.

## Dead ends

- `Cant_Stop`'s part 1 is 17.9 s, not the ~5 s I assumed from its 114 parts.
  **Part counts do not imply equal durations.**
- A loop-detector for inferring part spans false-positived on `Balloon`.
- **Heredoc backslash trap, 4×**: `python - <<'PY'` eats one backslash level.
  **Write patch scripts with the Write tool** when they contain backslashes.

</attempted_approaches>

<critical_context>

- **`passband_check.py --player {hardtrack,dmc,mon,sdi,fc,blackbird}`** compares
  `$D418` bits 4-6 only (low nibble is volume), fits the boot offset over
  `range(-4, 9)`, and refuses four ways: no reference trace, filter never
  exercised, all-mismatches-unrouted, multi-part failure without an asserted
  window. `ref: "sim"` selects a simulator reference per player.
- **Routing matters as much as mode**, and on the MISMATCHING frames:
  `$D417`'s low nibble picks which voices enter the filter.
- **The cross-builder audit in HARDTRACK.md checked CODE and sampled ONE FILE
  per player.** Both limits cost something — it is why SDI shipped a
  low-pass-only corpus. Corrected there and in `ACCURACY_MATRIX.md`.
- Environment: Windows, `py -3` (3.14), `pytest-timeout` NOT installed. Chunk
  long corpus runs (~20 files) — a single parent died at ~275 files.

</critical_context>

<current_state>

HEAD `2b18197`, `master`, pushed, tree clean, suite 2436.

| task | state |
|---|---|
| #16 HardTrack brightness gap | **RE-SCOPED, open.** No corpus-wide deficit; ~half remains on `Love_tune_2` alone. Decisive experiment unattempted: build the **HRC per-note lookahead**, then A/B the audio. ADSR 88–94% is the named candidate; `hard_restart=1` is provably wrong. *Opus, main.* |

**Open, unfiled:**

- **`Filthy_Hit_VE-4x`** — 0.0%, 1,387 audible frames. The V path's py65
  `v_traces` records no `$D418`; extending it would close the last real SDI
  passband gap. The other 3 V files differ by only 12 frames each.
- **33 SDI files UNCONFIRMED** — need a per-file asserted `--seconds`.
- **`French_Frites`** decodes badly generally (freq 24.1/34.4/26.3) — a DMC
  decode question, not a filter one. Belongs with the corpus tail: **87 of 216**
  frequency voices below 90.
- **`Altered_States_Tune_2`'s 47-frame first-filter-row latency** — inaudible,
  unexplained.
- A **startup-latency generalisation** was attempted and **discarded as
  under-controlled** (compared at offset 0 with a flat window). Redo it with
  per-file spans and fitted offsets or not at all.

</current_state>
