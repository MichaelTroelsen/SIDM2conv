<original_task>
The user drove an autonomous task-queue session on the SIDM2 repo using a custom
plugin command set (`mit-setup:whattask`, `runtask`, `runqueue`) plus `/loop`.
There was no single feature request; the standing instruction was to work the
task plan, cycle after cycle, with the plugin's gates enforced.

Explicit user requests, in order:
1. `/loop 5 /runtask next`, then `/loop 3`, `/loop 10` (repeated) — run task-queue
   cycles. `N` with no unit suffix is read as **N iterations, not N minutes**;
   this reading was stated early and never contradicted.
2. "commit and push" (x3) — land accumulated work.
3. "wait for the agent then commit those two".
4. "what is the biggest issues or task that needs to be fixed?"
5. "please make a plan for solving the biggest issues."
6. "please do a make a plan that can be handed over to /whattask" — which
   produced the four-issues handover that this file is now REPLACING.
7. `/mit-setup:runqueue` — dual-lane orchestration.
8. `/mit-setup:whattask` (x2) — regenerate the plan.
9. "what is status on the big task" — status of the four-issues plan.
10. This handoff.

BINDING CONSTRAINTS from the command set, honoured throughout:
- `/runtask`, `/runqueue`, `/whattask` NEVER commit, merge, push, branch or open
  a PR. Every git operation in this session happened only on the user's explicit
  instruction.
- "AN UNDECLARED PATH IS A STOP, NEVER A GRANT" — `touches` is the complete list
  of paths a task may WRITE.
- `runs.jsonl` is append-only, ONE line per attempted task, written with a
  single `>>`; never read-and-write-back.
- `whattask.json` is rewritten ONLY by `/whattask`.
- `serial.lock` updates go through the `.claude/tasks/serial.lock.d` mutex,
  written via `.tmp` + `os.replace`, released on the failure path too.
</original_task>

<work_completed>

## Commits landed and pushed (all on master, origin/master in sync)

`3b346a7..21d3b48` — five commits, pushed:

| sha | what |
|---|---|
| `b8e32f6` | `feat(laxity)` — tracked accuracy sweep + LAXITY.md result |
| `edd3fc7` | `fix(sf2)` — sf2_player_parser offset refusal + Driver-11 ground-truth tests |
| `03ccce9` | `fix(listen)` — abpage row cap dropped |
| `0ec3494` | `docs` — empty-trace scope, FC n=0, PATTERNS F13 |
| `21d3b48` | `docs(handoff)` — the four-issues plan (THIS FILE, now superseded) + 15 run records |

An earlier push in the same session landed `23a0740..3b346a7` (process_group
extraction, sys.path fix, abpage decode + row cap, run records).

## Task cycles completed (each recorded in `.claude/tasks/runs.jsonl`, now 195 records)

**`sweep-kill-safety-wants-a-shared-module` — done.** Extracted
`bind_children_to_this_process` into new `pyscript/process_group.py`; both
`sdi_native_sweep.py` and `dmc_native_sweep.py` import it. THE MOVE FOUND A BUG:
the old idempotence test asserted only that `_JOB_HANDLE[0]` is truthy after a
second call. It is — but it is a DIFFERENT handle (measured 604 -> 636): the
second call created a second job and leaked the first. Guarded with an early
`if _JOB_HANDLE[0]: return True`; the new assertion is handle EQUALITY.
Two of the three pins that had to survive the move would have died on the move
alone regardless of where they pointed — they sliced the body at "the next
`def `", and the helper is now the LAST def in its module.
Created `pyscript/test_process_group.py` (6 tests) pinning what only a shared
module can get wrong: an isolated-interpreter import (`-I`, only `pyscript/` on
the path, because in-process the check is vacuous — pytest already has rootdir
on `sys.path`), and a cycle check over parsed AST import nodes (a text grep hits
the docstring, which names both sweeps on purpose).

**`abpage-row-schedule-truncates-two-voices-at-512-rows` — done (delegated).**
Cap 512 -> 2048. Angular `[512,512,481]` truncated `[0,1]` -> `[564,744,481]`
truncated `[]`. Payload 9,651 -> 11,639 bytes (20.6%). I re-ran every number and
one did NOT hold: the agent justified 2048 as ">2.7x headroom over Angular's
longest voice (744)" — measured on ONE file. Over all 411 readable `.sf2`:
Chain_Reaction 1664, Unboxed_Ending 1408, Cybernoid_II 1216, and
`out/hawkeye_subtune_0.sf2` at EXACTLY 2048. Corrected the comment with the
sweep. Opened `abpage-row-schedule-cap-still-truncates-four-files-at-2048` and
`abpage-row-schedule-flags-empty-tracks-as-truncated`.

**`barbers-adagio-64-siddump-rc1` — done.** Cause written into
`docs/players/SDI.md`. `SID/Gallefoss_Glenn/Barbers_Adagio_64.sid` is an RSID
with `play=$0000`; siddump's vector fallback recovers `$2708`, which is not a
per-frame play routine but one link of a **4x multispeed raster-split chain**:

    $2722  BD 51 27   LDA $2751,X      ; raster table $08 $56 $A4 $F2
    $2725  CD 12 D0   CMP $D012
    $2728  B0 F8      BCS $2722        <<-- busy-wait; $D012 is CONSTANT in siddump
    $2736  20 03 10   JSR $1003        ; the real play, 4x per frame
    $2705  4C 00 10   JMP $1000        ; the real init

THREE hypotheses measured and REFUTED: (a) "play=$0000 is untraceable" — 21 of
the 22 RSID `play=0` files in that directory trace fine (rc=0, 240 rows);
(b) "reading `$D012` is the tell" — 11 of those 21 also read it near their
recovered play address and trace fine, so BRANCHING BACK is the discriminator;
(c) "the handler's RTI unbalances the stack" — `cpu6502_emulator.py:599` halts
correctly at `sp==0xFF`. zig64 traces the file at rc=0 from either entry
(`$2740/$2708` 3515 rows; `$1000/$1003` 1376 — the 2.6x is the 4x multispeed).
So it needs different init/play args and siddump exposes only `-a`. A blockquote
warns against conflating this 21/22 with CLAUDE.md's vsid "21 of SIDM2's 22" —
different tool, different population; **101** RSID `play=$0000` files exist
tree-wide across 13 directories.

**`empty-trace-audit-needs-bundle-diversity-not-span` — done.** Added
`bundle_diversity()` / `bundle_collapse()` / `BUNDLE_FLOOR = 5` to
`sidm2/fidelity_common.py`, plus 4 tests in `pyscript/test_fidelity_common.py`.
Calibrated against a REAL built control: ran the DMC builder on a copy of
`Balloon.sid` with the trace stubbed to a constant, producing
`out/dmc/EMPTYTRACE_CONTROL_part01.sf2`. Its own log line is the shipped
defect's signature: `part 1/1 (0-400s): instr=5 bundles=7 ... packed into 1
adaptive parts`. Balloon 24 bundles / 6732 notes; control 2 / 424. Corpus floor
over 63 one-part artifacts: min 10, median 33, max 70; nothing real <= 5.
**THE PRESCRIBED RATIO IS REFUTED**: notes:bundles ranks the control as
HEALTHIER than the certified build (Balloon 280.5 vs control 212.0), because the
ratio is dominated by song length, which a dead trace does not change. A test
pins the misranking. I also committed the exact bug the task exists to prevent
and my own test caught it: `SF2Parser` reports a missing file by PRINTING, so a
nonexistent path scored `bundles=0` and `bundle_collapse()` returned True.
Now returns None.

**`corpus-audit-empty-trace-artifacts` — done.** 77 one-part artifacts across
all 7 corpora, 77 measured, 0 unmeasurable, exactly ONE flagged — the planted
control. Per corpus (n/min/med/max): blackbird 13/9/36/62, dmc 10/2/24/47,
fc 0, hardtrack_native 1/63/63/63, mon 5/15/17/61, sdi 42/10/36/70,
soundmonitor 6/14/18/31. Lowest REAL build is blackbird `Euclid_Was_Here` at 9.
I INCLUDED `out/blackbird`, which the previous cycle excluded: its reasons
(no `.span`, siddump cannot drive an LFT rip) are about TRACE checks, and
`bundle_diversity` reads the artifact's own tables via `SF2Parser`.

**`driver11-injector-writes-a-duration-byte-the-spec-omits` — done.** Settled
against SF2II's OWN bundled file, `bin/music/Driver 11 Test - Arpeggio.sf2`
(driver string "DRIVER 11.00 - THE STANDARD", load `$0D7E`, TRACKED in git). At
raw offset `0x19AE` (addr `$272A`):

    C1 A0 80 30 30 00 C2 81 30 30 C3 80 2E 00 2E 2E 00 C4 2E 00 81 2E 7F

`unpack_sequence` parses it into 16 coherent rows terminating on `$7F`, with TWO
duration-1 rows from the `$81` bytes. Read as fixed triples: **0 of 7** groups
have a legal instrument byte. So the on-disk Driver 11 stream IS the packed
variable-length grammar and DOES carry durations; the spec's "three columns" is
the editor view; `inject_sequences`' shape is right and `DEFAULT_DURATION = 0x80`
is the flattening. **THIS RETRACTS MY OWN EARLIER RETRACTION** — I had recorded
"two formats, so the fixed triples are correct for Driver 11", which is false; I
over-read `unpack_sequence`'s docstring scope ("Laxity compatible") as a format
boundary. The `78d7ef2` comment was right on every clause. 3 tests pin it.
Also explains the negative offset: this file loads at `$0D7E` and its sequences
sit near `$272A`, so `SEQ=0x0903` is simply not where sequences are.

**`sf2-player-parser-reads-fixed-triples-from-a-variable-length-stream` —
partial.** Added a refusal to `sidm2/sf2_player_parser.py` (+42 lines,
additive): `sequence_offset = 0x0903 - load_addr + 2` is negative for 364/364
`out/*.sf2`, 42/46 marker SIDs, and the editor's own file, and a negative index
reads the file TAIL without raising. On SF2II's 2-sequence file it returned
**235 sequences**, orderlists `[623, 0, 11]`, events like `instrument=$01
command=$FF`. Now raises `InvalidInputError` naming the constant and the load
address; the caller already wraps it and keeps empty sequences, so it degrades
to "no sequences plus a warning". Created `pyscript/test_sf2_player_parser.py`
(4 tests). Mutation-checked: removing the guard turns 3 red while "a load
address BELOW $0903 still parses" stays GREEN. **Zero of 3,060 existing tests
broke — direct evidence the path is untested, not merely wrong.**

**`sf2-exported-100pct-what-does-the-output-actually-use` — done.** THE BIG
FINDING. 46 SIDs carry the `$1337` marker; 37 pass the full
`conversion_pipeline.py:444` gate (`has_sf2_magic AND driver_type ==
'driver11'`); **ALL 37 got driver11 from the FALLBACK DEFAULT** — every reason
string is "Standard SF2 driver for maximum compatibility" — and **ZERO were
positively identified as SF2 exports**. They are native rips: Hubbard 14,
Bjerregaard 5, Gray 3, Shogoon 3, Gallefoss 3, Tel 2. Converting
`SID/Hubbard_Rob/Commodore_64_Music_Examples.sid` logs verbatim "Using SF2
player parser (driver: driver11, SF2-exported file)" on a native Hubbard rip.
AND the parser's sequences never reach the output: converting with the refusal
guard PRESENT vs REMOVED gives BYTE-IDENTICAL `.sf2` on three files (17,957 /
25,566 / 19,542 bytes). So `DRIVER11.md:6`'s "by construction" premise is FALSE
for every file that takes this route, and `ACCURACY_MATRIX.md:42`'s
"Guaranteed 100%" rests on nothing measured.

**`laxity-9993-remeasure-with-a-tracked-script` — done.** Created TRACKED
`pyscript/laxity_accuracy_sweep.py` + `pyscript/test_laxity_accuracy_sweep.py`
(6 tests). Result over 17 of 17 files, 0 errors, 0 unmeasurable: frame accuracy
min **98.73%** (`Unboxed_Ending_8580`), median **100.00%**, max **100.00%** —
and **16 of 17 at exactly 100.00% on BOTH columns** (per-frame mean AND exact
frame-for-frame identity, 1500/1500). Same round trip the retired n=2 figure
used. Population from `DriverSelector`, not a hand list. Three refusals,
mutation-checked. Wrote the result plus three quoting conditions into
`docs/players/LAXITY.md`. FOUND A SILENT WRITE: `validate_sid_accuracy.py` drops
`validation_<stem>_<ts>.html` into the CURRENT directory without `--output`; it
is gitignored (`.gitignore:200`) so `git status` never shows it. Two landed in
the repo root; deleted, and a test now pins the flag.

**`/runqueue` cycle — 3 tasks, all done.** Fanned out 2 delegable doc tasks via
Workflow (`opts.effort` = `low` from the plan, the ONE path that can enforce
effort) while running one main task here:
- `fc-corpus-has-no-one-part-artifacts-to-screen` — out/fc: 19 sf2, 5 part01,
  **0** without part02, re-verified by me; scope limit written into
  `docs/players/FUTURECOMPOSER.md:329`.
- `mutation-checks-need-a-pycache-clear` — `docs/players/PATTERNS.md` F13 at
  line 676, both failure directions.
- `empty-trace-screen-does-not-cover-multi-part-artifacts` — 446 songs, 77
  one-part, **369 multi-part (83%)** outside scope, 8,301 `.sf2` total. BUT a
  dead trace CANNOT produce a multi-part build: `fits()` grows a part while
  every count is under its cap, so no trace data => window grows to span => ONE
  part. Multi-part output is itself evidence the trace overflowed a cap. AND the
  floor does not transfer: 60 of 6,692 parts sampled, bundle min **6**, median
  34 — a one-bundle margin vs four for whole songs. Written into `DMC.md:806`.

**`abpage-row-schedule-cap-still-truncates-four-files-at-2048` — done
(delegated).** Cap DROPPED: `max_rows: int | None = None`, truncation gated on
it. hawkeye `[2048,0,133]` truncated `[0]` -> `[2495,0,133]` truncated `[]` (447
rows were being cut). **Cost is flat**: largest payload 22,732 bytes (Sanxion)
at cap 2048 AND fully uncapped — removing the ceiling costs nothing corpus-wide,
which is why raising to a third number was wrong (512 -> 2048 -> still
truncating). Over-read guard intact: `_test_commando` still `[0,0,0]` with 3
over-read records on the NO-CAP path. 92 tests pass. Reverting turns 2 red while
the guard test correctly stays GREEN.

**`cybernoid-ii-sub0-native-passband-mismatch` — partial.** `passband_check
--player mon` reports `Cybernoid_II_sub0_native (84.6%)`: original `LP+BP`
oChg=0, ours `off/LP+BP` dChg=1, off=0 — a leading `off` run over ~15.4% of
frames, not lateness, not modulation. NOT a stale artifact: I rebuilt it (the
tool's own prescribed first step) and the score did not move. I FOUND A REAL
OMISSION THAT IS NOT THE CAUSE: `traces` was computed ONLY inside
`if adaptive or winsec > 0:` (`bin/build_mon_native_song.py:2656/2666`), so the
single-file path at 2708 called `build_native_song` with NO traces — not even in
scope — and that function gates its whole trace path, INCLUDING
`pbtr = traces[2]` (the `$D418` passband), on `if traces is not None`
(1597/1602). I hoisted it, rebuilt, and **the score was unchanged at 84.6%** —
hypothesis refuted. Hawkeye_sub2_native and Hawkeye_sub3_native pass by
COINCIDENCE (their originals select a constant `LP`). Rebuilding also printed
"464 of 527 bundles FORCE-MERGED ... freq/pulse programs WILL be wrong ... Use
adaptive windows", so that artifact is known-bad anyway and its windowed sibling
already scores 100.0%. **I REVERTED both the builder change and the artifact
byte-for-byte** rather than commit an unverified builder change.

**`plan-verify-strings-not-reconciled-against-commits` — blocked.** Its only
writable path is `rw:.claude/tasks/whattask.json`, which `/runtask` is forbidden
to write. Unrunnable by construction — and it is the
`plan-task-declared-a-path-runtask-may-not-write` class REPRODUCED by the
`/whattask` pass that had that very task in its closed list.

## `/whattask` regenerations

Two full passes. The later wrote **71 tasks / 86 closed / 59 ready**, head
`3b346a7`, folding in the four-issues handover. `graphify update` ran BEFORE the
touches cross-check both times (20,687 nodes / 32,388 edges). Closed 9 in the
second pass, including `driver11-injector-comment-conflates-laxity-and-driver11-
formats` as REFUTED (the comment is correct).
Found: **4 `opened` entries were absolute file paths, not task ids** — excluded;
and 94 opened ids were missing from the plan before the first regeneration.

## The four-issues plan (was the content of this file at 21d3b48)

Issue 1 the unmeasured "Guaranteed 100%"; Issue 2 the pytest-randomly flake;
Issue 3 the Laxity 99.93%; Issue 4 plan hygiene. Delivered as 9 tasks in
plan-record shape. **Issues 1 and 3 are now measured out; both wait on the
user.** Issue 4 is structurally blocked. Issue 2 is IN FLIGHT (below).

</work_completed>

<work_remaining>

## IN FLIGHT RIGHT NOW — finish this first

**`test-stage7-emissions-order-dependent-logging-flake`** is HELD in
`.claude/tasks/serial.lock` (pid 4327, which is a dead transient Bash shell —
see gotchas) and has NOT been recorded. Its cycle is incomplete.

State of the diagnosis:
1. **Flake REPRODUCED.** `python -m pytest pyscript/ scripts/ -q -p randomly
   --randomly-seed=1` gives **7 failed, 3066 passed** — six in
   `test_stage7_emissions.py`, every one `AssertionError: '...' not found in ''`
   (the empty-log signature), plus the known `test_player_index.py` failure from
   `out/sf2exported_probe`.
2. **The file alone PASSES** under seeds 1, 2 and 3 (13 passed each). So the
   leak is CROSS-FILE.
3. **Mechanism PROVEN by decisive experiment.** `sidm2/logging_config.py:311`
   does `logger.propagate = False` on the `sidm2` package logger inside
   `setup_logging()`, and never restores it. Demonstrated directly: attach a
   handler to the ROOT logger, log via `sidm2.demo` -> captured; call
   `setup_logging()`; log again -> captured `''` while the record goes to
   setup_logging's own handler. `test_stage7_emissions`'s capture helper (lines
   ~45-62) attaches its handler to `logging.getLogger()` — root — so once
   propagate is False it can never see `sidm2.*` records again.
4. **The TRIGGER is NOT yet identified.** `setup_logging` is called only from
   CLI entry points (`pyscript/accuracy_heatmap_tool.py:97`,
   `pyscript/audio_tightness_tool.py:851`, `scripts/convert_all.py` via
   `configure_from_args`), and no test appears to reach any of them (the
   `unittest.main()` hits in test files are the test runner, not the tool).

**A run is in flight to name the trigger.** Background id `bmpf1d7qz`, monitor
`btgx5n26l`. It runs the full suite under seed 1 with a pytest plugin loaded
from OUTSIDE the repo:
`PYTHONPATH=<scratchpad> python -m pytest pyscript/ scripts/ -q -p randomly
--randomly-seed=1 -p propwatch`, output to `<scratchpad>/seed1_watch.txt`.
The plugin is `<scratchpad>/propwatch.py`; it hooks
`pytest_runtest_teardown` and prints
`*** PROPAGATE FLIPPED TO FALSE DURING: <nodeid>` the first time
`logging.getLogger('sidm2').propagate is False`, plus the handler list and
`logging.root.manager.disable`. **Read that output first** — it names the
culprit test and completes the diagnosis.

Then:
- Record the cycle in `runs.jsonl` (one line, single `>>`). Likely `partial`:
  the fix at source needs `rw:sidm2/logging_config.py`, which this task holds
  only as `r:`. The task's own verify says *"touches may need a /whattask
  widening once the culprit module is identified; stop and report rather than
  widening mid-run."*
- Release the lock record under the mutex.

## Then, in priority order

1. **Issue 1 fork — USER DECISION, `sf2-exported-100pct-fork-decision`.**
   Measurement is complete (37 files, all fallback-default, sequences
   discarded). Options: **(a)** quarantine the sequence-extraction path and
   re-stamp `ACCURACY_MATRIX.md:42` + `DRIVER11.md:6` to "tables preserved by
   construction; sequence extraction unsupported/unmeasured"; **(b)** authorise
   the repair chain in `sf2-player-parser-locate-then-decode-then-duration`.
   Either way "Guaranteed" should leave the docs. (a) is recommended.
2. **Issue 3 restamp — USER DECISION, `laxity-9993-restamp-docs`.** The number
   came back ABOVE target; the presentation is the human's call. The 30-second
   window caveat must travel with it.
3. **Clear `out/sf2exported_probe`** — 6 gitignored probe `.sf2` I created in
   the SF2-export investigation break `test_player_index.py::
   test_every_built_directory_is_classified`. `rm -rf out/sf2exported_probe`
   fixes it, or an `IGNORED` entry in `player_index.py`. It is outside every
   current task's `touches`, which is why it is still there. **The suite is red
   on exactly this one test for this one reason.**
4. **Issue 4 re-scope.** `plan-verify-strings-not-reconciled-against-commits`
   must become whattask-only (or write somewhere a runner may write). Its
   structural half, `whattask-generation-cross-checks-refutations-mechanically`,
   plus `runs-jsonl-opened-entries-must-be-slugs`, both describe edits to the
   mit-setup MARKETPLACE plugin (outside this repo) while declaring only `r:`
   paths inside it — see `plan-tasks-editing-the-plugin-declare-no-writable-path`.
5. **`bin/build_mon_native_song.py:2708` still lacks `traces=`.** Real omission,
   NOT the cause of the 84.6%, deliberately reverted. Tracked as
   `mon-single-file-path-builds-without-a-passband-trace`. Fixing it needs a
   verification plan for freq/pulse/filter, not just the passband.
6. **The MoN 84.6% remains open.** Next step: find what emits the leading `off`.
   Likeliest the driver's own init not writing `$D418` mode bits until its first
   filter row — the SAME mechanism as the existing
   `dmc-driver-init-passband-default`. These two should probably be MERGED. Note
   `docs/players/MON.md` is not in that task's `touches`, so the 22/27
   restatement has nowhere to land (`mon-md-not-in-touches-so-2227-cannot-be-
   restated`).
7. **`/whattask` is behind again** — the plan's head is `3b346a7` while HEAD is
   `21d3b48`, and ~15 new `opened` ids exist only in `runs.jsonl`.

</work_remaining>

<attempted_approaches>

## Refuted hypotheses (do NOT re-try these)

- **"Driver 11 and Laxity are two formats, so `sf2_player_parser`'s fixed
  triples are correct for Driver 11."** MY OWN earlier retraction, and it is
  FALSE. Disproved on SF2II's own file: 0 of 7 triples carry a legal instrument
  byte. I had over-read `unpack_sequence`'s docstring scope as a format
  boundary. The question has now flipped THREE times in the records, which is
  why the answer is pinned to bytes at an offset in a TRACKED file rather than
  to prose.
- **"The missing `traces=` on the MoN single-file path causes the 84.6%
  passband failure."** Refuted by its own test: hoisting the trace and rebuilding
  changed the artifact bytes and left the score at exactly 84.6%.
- **"`Cybernoid_II_sub0_native` is a stale pre-fix artifact."** Refuted by
  rebuilding it — the score survived. Its Aug-8 date is a red herring.
- **"`play=$0000` makes Barbers_Adagio_64 untraceable."** Refuted: 21 of 22
  sibling RSID `play=0` files trace fine.
- **"Reading `$D012` is the tell for the siddump hang."** Refuted: 11 of those
  21 working files also read it. BRANCHING BACK on it is the discriminator.
- **"The Barbers handler's `RTI` unbalances siddump's stack."** Refuted:
  `cpu6502_emulator.py:599` returns False at `sp==0xFF`, and its 3 pushes are
  matched by 3 pulls.
- **"The notes:bundles ratio flags an empty-trace collapse."** Refuted: it ranks
  a certified build BELOW a known-bad control (280.5 vs 212.0).
- **"The `_native` naming is retired, so `Cybernoid_II_sub0_native` is an
  orphan of an old convention."** Checked and false — `bin/build_mon_native_
  song.py:2710` still emits it; it is the non-windowed branch.
- **"Extending the empty-trace screen to all 6,692 parts is the obvious next
  step."** Measured against: parts legitimately carry as few as 6 bundles
  against a floor of 5.

## Delegation failures and how they were handled

- **A subagent returned NO record twice.** The abpage cap task's agent used
  `Path.rglob('*.sf2')` under `SF2/` and `out/`, sweeping **8,753** nested build
  files instead of the intended 411 top-level ones. It ran 10+ minutes, then
  stopped holding for a background sweep that was already moot, returning prose
  instead of the JSON record — twice, ~161k tokens. Fixed by resuming it via
  `SendMessage` with an explicit instruction to work FOREGROUND-ONLY from what
  it already had. Non-recursive `.glob` reproduced exactly 411 files and the
  docstring's prior numbers, cross-validating the measurement.
- **Agents put FILE PATHS in `opened` arrays** (5th and 6th sightings). Stripped
  rather than recorded.

## Tooling traps hit

- **Same-length mutation + stale pytest bytecode.** Swapping `0x19AE`->`0x19AF`
  or `0xC1`->`0xA1` leaves the assertion-rewrite `.pyc` valid (Python checks
  mtime AND size), so tests still fail after a correct restore. Cost three
  commands. Now `PATTERNS.md` F13.
- **A mutation patch that never applied.** Single-quoted Python against
  double-quoted source matched nothing; the suite passed, which looks exactly
  like a test failing to catch its mutation and CERTIFIES it. Always assert the
  anchor is unique before mutating.
- **`--json` vs `--comparison-json`** on `validate_sid_accuracy.py`: `--json`
  writes the two raw captures (~1.3 MB each), not the comparison. The first
  sweep reported every row as an error because of it.
- **Piping a background run through `grep | tail`** produced a 59-byte binary
  file and no usable result — indistinguishable from "no failures". Re-ran
  writing plain output to a file instead. Output files also contain NULs;
  `tr -d '\000'` before grepping.
- **`-I` implies `-E`**, so `PYTHONPATH` is ignored; the path had to go in the
  `-c` source for the isolated-import test.

</attempted_approaches>

<critical_context>

## Repo conventions that bit

- **`out/` is the CORPUS tree, not scratch.** `pyscript/test_player_index.py::
  test_every_built_directory_is_classified` asserts every `out/` directory
  holding `.sf2` files is classified in `player_index.py`. Two of my own cycles
  tripped it. The Laxity sweep was fixed at source: results (`sweep.json`) stay
  under `out/laxity_sweep`, disposable intermediates go to
  `tempfile.gettempdir()`.
- **The suite is NOT green without `-p no:randomly`.** Baseline with the flag:
  3,069-3,073 passed, 0 failed apart from the `sf2exported_probe` issue. Under
  `-p randomly --randomly-seed=1`: 7 failed.
- **A cycle that writes a NEW `out/` subtree must run the full suite before
  claiming done.** I recorded `sf2-exported-100pct-...` as done without doing
  so and left the suite red; it surfaced two cycles later.

## The lock protocol's live unsoundness

Every holder record this session carries the pid of a **transient Bash shell**
(`$$` in a one-shot command), which is dead by the time anything reads it. The
mutex protocol says to reap records whose pid is not running — which would free
paths an agent is actively editing. This happened concretely: the abpage record
carried pid 1479 (dead) while its agent was mid-edit on both declared files. **I
declined to reap it and said so.** Tracked as
`runtask-lock-records-a-transient-shell-pid`.

Related: a held `r:out` (whole-tree read) refused **35** otherwise-ready tasks in
the `/runqueue` cycle — every `rw:out/<player>` corpus task. It should have been
`r:out/<subtree>`. Tracked as
`plan-r-out-whole-tree-read-serialises-35-tasks`.

## Ground truth worth knowing

- `bin/music/Driver 11 Test - Arpeggio.sf2` is SF2II's own bundled file and is
  TRACKED in git — so tests against it are portable. Contrast
  `out/dmc/EMPTYTRACE_CONTROL_part01.sf2`, the bundle-diversity control, which
  is GITIGNORED under `out/`: the two tests referencing it **SKIP** on any other
  machine. Deleting it silently weakens them.
- Any future re-run of the empty-trace corpus audit that does NOT flag exactly
  one file should be treated as a BROKEN SCREEN, not a clean corpus — the
  control is the only thing making the result falsifiable.
- `passband_check --player mon` prints "rebuild these first; if it survives a
  rebuild the builder is at fault, not the artifact". That rebuild has now been
  done for Cybernoid_II; do not redo it.
- `sidm2/models.py` has ~53 importers including every native builder; widening
  `SequenceEvent` is not a small change.
- `sidm2/fidelity_common.py` has ~90 importers.
- `abpage.row_schedule` calls `logging.disable()` — process-wide — but its
  restore correctly covers all three early returns via `finally`, and two guard
  tests pin it. It is NOT the current leaker.

## Environment

Windows 11, Git Bash + PowerShell, Python 3.14.7, pytest 9.1.1 with
`pytest-randomly` installed. `pytest-timeout` is NOT installed (`--timeout=`
silently makes the run a usage error, which piping through `tail` masks as exit
0). `ffmpeg` is NOT on PATH (re-checked this session). MCP server
`sidm2-siddump` failed to connect all session; `tokensave` and `graphify` work.

</critical_context>

<current_state>

## Git

- HEAD = **`21d3b48`**, `origin/master` in sync, 5 commits pushed this session
  (plus 4 earlier at `3b346a7`).
- Working tree: **`M .claude/tasks/runs.jsonl` ONLY.** Everything else is
  committed. `bin/build_mon_native_song.py` and
  `out/mon/Cybernoid_II_sub0_native.sf2` were deliberately reverted
  byte-for-byte.

## Locks

`.claude/tasks/serial.lock` holds ONE record:
`test-stage7-emissions-order-dependent-logging-flake` (pid 4327 — dead
transient shell; do NOT reap mechanically, see gotchas). Its cycle is
**in flight and unrecorded**.

## Run log

`.claude/tasks/runs.jsonl` — **195 records**, tracked in git, 1 line uncommitted
(the Cybernoid `partial`).

## Plan

`.claude/tasks/whattask.json` — 71 tasks, 86 closed, head `3b346a7`
(**5 commits stale**). 8 `requires-user`. Readiness must be recomputed from
`runs.jsonl`, not read off the file.

## Suite

Red on exactly one test — `test_player_index.py::
test_every_built_directory_is_classified`, caused solely by
`out/sf2exported_probe` (6 gitignored probe `.sf2`). Everything else passes with
`-p no:randomly`. Under a random seed, 6 additional `test_stage7_emissions`
failures — the flake under investigation.

## Open questions for the user

1. **Issue 1 fork**: quarantine-and-restamp (a), or authorise the repair (b)?
2. **Issue 3 restamp**: how to present 16/17-at-100.00% in `CLAUDE.md` and
   `ACCURACY_MATRIX.md`?
3. **May I `rm -rf out/sf2exported_probe`** to green the suite?

## Immediate next action

Read `<scratchpad>/seed1_watch.txt` (background `bmpf1d7qz`, monitor
`btgx5n26l`) for the `*** PROPAGATE FLIPPED TO FALSE DURING: <nodeid>` line.
That names the culprit test and completes the flake diagnosis. Then record the
cycle and release the lock.

</current_state>
