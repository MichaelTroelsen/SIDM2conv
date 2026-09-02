# Handoff — The Four Biggest Issues (2026-09-02, head 3b346a7)

**FOR `/whattask`**: this file replaces the spent 2026-08-24/26 handoff (all of
whose items are closed in `runs.jsonl` except Rubicon, carried at the bottom;
the old text is in git history). Each task below carries the fields a plan
record needs — stable id, model/effort/mode/lane with reasons, `touches` with
modes, `depends_on`, and a runnable `verify` — so the generation pass is
transcription plus the mechanical 5b widening, not re-derivation.

**Why these four**: each was measured this session, not asserted. The evidence
lines cite `runs.jsonl` records by id.

---

## ISSUE 1 — "Guaranteed 100%" (SF2-exported → Driver 11) is unmeasured and its parser is broken

`docs/reference/ACCURACY_MATRIX.md:42` rates this path **100% "Guaranteed"**;
`docs/players/DRIVER11.md:6` justifies it **"by construction"** — an argument,
not a measurement. The parser implementing it (`sidm2/sf2_player_parser.py`)
returned **235 sequences for SF2 II's own 2-sequence file** (orderlists
[623,0,11], events with illegal field values), reading from offset −1145 — and
**zero of 3,060 tests noticed**, because the path has no coverage
(runs.jsonl: `sf2-player-parser-reads-fixed-triples-from-a-variable-length-stream`,
`driver11-injector-writes-a-duration-byte-the-spec-omits`). A refusal guard now
turns the garbage into empty-plus-warning; the docs still say "Guaranteed".

Measure-first, because the fix differs completely by outcome. THREE tasks, a
dependency chain with a human fork in the middle.

### Task: `sf2-exported-100pct-what-does-the-output-actually-use`
- **title**: Trace one real SF2-exported conversion end-to-end: do SF2PlayerParser's sequences reach the output, or are tables copied verbatim?
- **model**: opus (the failure mode is a plausible wrong call-graph reading) · **effort**: high · **mode**: main · **lane**: serial
- **touches**: `r:sidm2/conversion_pipeline.py`, `r:sidm2/sf2_player_parser.py`, `r:sidm2/sf2_writer.py`, `r:sidm2/driver11_section_injectors.py`, `r:SID`, `r:bin`, `rw:out/sf2exported_probe` (a NEW scratch dir for the one probe conversion — do NOT write any existing corpus subtree)
- **depends_on**: []
- **verify**: "Run ONE real conversion through the has_sf2_magic AND driver_type=='driver11' gate (conversion_pipeline.py:441/487). Then answer with a BYTE-REGION DIFF, not a call-graph reading alone: does the emitted .sf2's sequence region equal the input's (tables copied verbatim → 'by construction' may hold DESPITE the broken parser, whose sequences would be decorative), or does it contain material derived from SF2PlayerParser's extraction? Also enumerate every SID in the tree passing the FULL gate — both conditions, not just the 46 two-byte marker matches — and for each record sequences emitted before/after the refusal guard. Done when the table exists (file, gate, seq count, output-diff verdict) and the sequences-reach-output question has a measured yes/no."
- **note for the generator**: this is the task the old `sf2-player-parser-sequence-offset-goes-negative` and `sf2-export-detection-is-a-two-byte-substring-search` records feed into; fold their measured numbers (364/364 negative, 46/1490 marker matches, 4 non-negative all native files) into its verify rather than re-measuring.

### Task: `sf2-exported-100pct-fork-decision`
- **title**: Dead path or live path — delete-and-restamp, or locate-decode-measure?
- **model**: opus · **effort**: high · **mode**: **requires-user** · **lane**: serial
- **touches**: `r:docs/reference/ACCURACY_MATRIX.md`, `r:docs/players/DRIVER11.md`
- **depends_on**: [`sf2-exported-100pct-what-does-the-output-actually-use`]
- **blocked_on**: "A human decision, made against the measurement the dependency produces: (a) if the population is empty or the sequences never reach output — quarantine the extraction path and re-stamp both docs to 'tables preserved by construction; sequence extraction unsupported/unmeasured'; (b) if the path is live — authorise the full repair chain (locate by descriptor, decode the packed grammar, add SequenceEvent.duration LAST, measure round-trip byte-identity, re-stamp with the measured number and n). Either way the word 'Guaranteed' leaves the docs until a measurement exists."

### Task: `sf2-player-parser-locate-then-decode-then-duration`
- **title**: The live-path repair: locate the sequence region by descriptor, decode the packed grammar, only then add SequenceEvent.duration
- **model**: opus · **effort**: xhigh (two confident wrong answers already shipped on this thread) · **mode**: main · **lane**: serial
- **touches**: `rw:sidm2/sf2_player_parser.py`, `rw:pyscript/test_sf2_player_parser.py`, `rw:sidm2/models.py`, `rw:pyscript/test_models.py` (create), `r:pyscript/sf2_viewer_core.py`, `r:bin`, `r:SF2`
- **depends_on**: [`sf2-exported-100pct-fork-decision`]
- **verify**: "ONLY if the fork chose (b). Order is binding: (1) locate WITHOUT the $0903 constant — sf2_viewer_core's descriptor walk is the working reference but lives in pyscript/, so extract the shared part into sidm2/ the way process_group.py was (runs.jsonl: sweep-kill-safety-wants-a-shared-module is the precedent), never import pyscript from sidm2; (2) decode with the packed grammar pinned in test_driver11_section_injectors.py against bin/music/Driver 11 Test - Arpeggio.sf2 — that file parses to exactly 2 sequences, 16 rows in the second, with two duration-1 rows from the $81 bytes, and any decoder not reproducing that is wrong; (3) ONLY THEN widen SequenceEvent (~53 importers — append duration with a default so positional construction survives). Done when the reference file round-trips byte-identically through parse→inject and the full suite passes."

---

## ISSUE 2 — The suite is not green under random ordering, so no pass count is quotable

Six tests in `pyscript/test_stage7_emissions.py` fail under `pytest-randomly`
with a **varying subset per run** — PATTERNS.md F12's signature for
shared-state order dependence. Every number this repo quotes ("3064 passed")
silently depends on `-p no:randomly`
(runs.jsonl: `unbounded-laxity-fallback-readers-emit-13k-entry-sequences`,
which measured the varying-subset tell across two runs).

### Task: `test-stage7-emissions-order-dependent-logging-flake`
(already in the plan — carry it forward, but SHARPEN the verify)
- **model**: opus · **effort**: high · **mode**: main · **lane**: serial
- **touches**: `rw:pyscript/test_stage7_emissions.py`, `r:sidm2/logging_config.py`, plus `rw:` whichever module the leak is found in — the generator should note the touches may need a /whattask widening once the culprit is named
- **verify**: "Reproduce under THREE fixed seeds (-p randomly --randomly-seed=N) recording which subset fails per seed; find the escaping global (prime suspect: logging state — this same file was hit by a logging.disable leak before); fix AT THE SOURCE. A reset fixture that makes the tests pass while the leak persists is the named FAILURE mode, not the fix — the check is that the full suite is green under 3 different random seeds WITHOUT -p no:randomly, and that the culprit global is named in the record."
- **ordering**: do this BEFORE quoting any milestone number from Issues 1 or 3.

---

## ISSUE 3 — Laxity 99.93% is a target wearing a measurement's clothes

CLAUDE.md's own row admits it: the only measurement on record is **n=2**
(2025-12-28) and **its script is no longer in the tree**. The locate defect
that fed this path is now fixed (14→3 refusals, runs.jsonl:
`laxity-parser-reads-runtime-pointers-as-the-sequence-table`), so re-measuring
is meaningful for the first time.

### Task: `laxity-9993-remeasure-with-a-tracked-script`
- **title**: Re-measure native-Laxity frame accuracy with a script that cannot vanish
- **model**: sonnet (the harness exists; this is a sweep) · **effort**: medium · **mode**: main (multi-minute corpus conversions) · **lane**: serial
- **touches**: `rw:pyscript/laxity_accuracy_sweep.py` (create), `rw:pyscript/test_laxity_accuracy_sweep.py` (create), `r:SID`, `rw:out/laxity_sweep` (new scratch subtree for its conversions), `rw:docs/players/LAXITY.md`
- **depends_on**: []
- **verify**: "A TRACKED sweep script — the original vanished, which is why the figure is unquotable — measuring per-file frame accuracy over every SID the fixed locate handles, routed through fidelity_common (score_pct / exercised / underpowered, so a vacuous 100 cannot recur), printing per-file % WITH n. Done when LAXITY.md carries the measured distribution (not just a mean), the file list, and the run date. Re-stamping CLAUDE.md's row and ACCURACY_MATRIX.md is a FOLLOW-UP task gated on a human reading the result, not part of this one."

### Task: `laxity-9993-restamp-docs`
- **model**: sonnet · **effort**: low · **mode**: **requires-user** · **lane**: serial
- **touches**: `rw:CLAUDE.md`, `rw:docs/reference/ACCURACY_MATRIX.md`, `rw:docs/players/LAXITY.md`
- **depends_on**: [`laxity-9993-remeasure-with-a-tracked-script`]
- **blocked_on**: "The human reads the measured distribution and decides what the headline row should say — the number may come back below 99.93, and how to present that is not a runner's call."

---

## ISSUE 4 — The plan itself keeps instructing runners to be wrong

The Driver-11 format question **flipped three times** because carried-over
verify strings asserted refuted premises ("ESTABLISHED, DO NOT RE-DERIVE"),
and the hygiene task covering this was closed once and **recurred twice the
next session** (runs.jsonl: `plan-verify-strings-not-reconciled-against-commits`,
reopened). Manual passes have failed; the fix must be mechanical.

### Task: `plan-verify-strings-not-reconciled-against-commits`
(already in the plan, REOPENED — carry forward unchanged)

### Task: `whattask-generation-cross-checks-refutations-mechanically`
- **title**: Make /whattask flag, not copy, a carried-over verify whose id has a refutation in runs.jsonl
- **model**: opus · **effort**: high · **mode**: main · **lane**: serial
- **touches**: the mit-setup marketplace plugin's whattask command file (OUTSIDE this repo — the generator must name the real path and note the 1.9.4-bump precedent from decisions.jsonl: editing the cache is invisible to the marketplace)
- **depends_on**: [`plan-verify-strings-not-reconciled-against-commits`]
- **verify**: "The generation step, for every carried-over task, scans that id's runs.jsonl records for retraction language (RETRACT/REFUTE/premise-refuted/FALSIFIED) and flags the verify for rewrite instead of copying it. Done when the rule text is in the MARKETPLACE copy with a version bump, and a dry test against this session's log flags the two known cases (the parser task's ESTABLISHED clause; the audit task's notes:bundles ratio)."

### Task: `runs-jsonl-opened-entries-must-be-slugs`
- **title**: Four absolute file paths got into `opened` arrays as "task ids"
- **model**: sonnet · **effort**: low · **mode**: subtask · **lane**: parallel (touches nothing another task writes)
- **touches**: the runtask/runqueue command files in the same marketplace plugin (outside this repo; same path note as above)
- **verify**: "The record-writing step validates every `opened` entry as a kebab-case slug and refuses a path or URL with a message naming the offending entry. The four path entries from this session's log are the test case."

### Standing rule for the generator (not a task): pin contested facts to
**tracked files, not prose**. The three tests in
`pyscript/test_driver11_section_injectors.py` against SF2II's own bytes are
what finally ended the Driver-11 flipping; a verify that can cite a byte at an
offset in a tracked file beats one that cites a records entry.

---

## Ordering summary

```
now, independent:  sf2-exported-100pct-what-does-the-output-actually-use   (1a)
                   test-stage7-emissions-order-dependent-logging-flake      (2)
                   laxity-9993-remeasure-with-a-tracked-script              (3a)
                   plan-verify-strings-not-reconciled-against-commits       (4a)
gated on human:    sf2-exported-100pct-fork-decision        <- 1a
                   laxity-9993-restamp-docs                 <- 3a
gated on those:    sf2-player-parser-locate-then-decode-then-duration  <- fork(b) only
                   whattask-generation-cross-checks-refutations        <- 4a
```

Do **2** before quoting any milestone number from 1 or 3. Nothing here runs
parallel with a timing measurement; none exists in this set.

---

## Carried forward unchanged: Rubicon (still awaiting the user's choice)

`rubicon-locate-fallback-or-re` — two options presented, never answered:
harden `mon_parser._locate()`'s silent `0x83FC` fallback into an honest
refusal (first sweeping the corpus for files that depend on the fallback by
accident), or RE Rubicon's actual engine variant (load `$3F00`, init `$3F50`,
play `$3F64`, matching none of the four locate branches; needs a py65 INIT
trace). Both siblings (`Rubicon_Load_1/2`) hit the identical fallback and any
fix must be re-checked against all three. Detail: the 2026-08-24 handoff in
git history, and `memory/mainstream-mon-tel.md` (auto-memory, not in tree).
