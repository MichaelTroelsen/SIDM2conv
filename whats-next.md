# Session Handoff — 2026-08-24/26

<original_task>
This session continued from a compacted context. The **originating** request was:
port h2g's `abpage.py` into SIDM2 as a blind A/B listening rig, then add the three
features the h2g page had and SIDM2's did not (measures rail, pattern view,
instrument-map link), then stage the whole converted corpus.

That arc was already essentially complete when this segment began. What this
segment actually did, in the order the user asked for it:

1. `/whattask` (unfocused) — produce the full open-task list, not just the abpage subsystem.
2. `/whattask --dry-run` — re-print it.
3. `/runqueue --until-blocked` ×2 — drain the plan.
4. `/whattask` ×2 more — replan after each drain.
5. **"commit and push"** ×2 — land the work.
6. Fix `graphify update`, which had been failing all session.
7. `/claude-code-setup:claude-automation-recommender` — recommend Claude Code automations.
8. **"do 1. do 2."** — build the two recommended hooks.
9. This handoff.

**Standing constraints** (from the `/runtask`, `/runqueue`, `/whattask` command set):
those commands NEVER commit, merge, push, branch, or open a PR. Every git
operation in this session was performed only on the user's explicit instruction.
`whattask.json` is rewritten only by `/whattask`. `runs.jsonl` is append-only,
one JSON line per attempted task, written with a single `>>` — never
read-and-write-back. `serial.lock` updates go through the `.claude/tasks/serial.lock.d`
mutex. An undeclared `touches` path is a STOP, never a self-granted widen.
</original_task>

<work_completed>

## 1. Six commits, all pushed to `origin/master`

| SHA | Commit |
|---|---|
| `d4dbc47` | `feat(listen): gapless blind A/B listening pages` — the whole abpage arc |
| `fd0345e` | `chore: gitignore graphify-out/` — 37 MB of rebuildable cache |
| `cfa3ab5` | `chore(tasks): record 5 runqueue cycles -- one done, four partial` |
| `6df328f` | `chore(sid): add the LukHash corpus -- 13 files, a player family new to SIDM2` |
| `33b7540` | `docs: session handoff -- the abpage arc and the Rubicon question` |
| `470ec69` | `feat(hooks): enforce the root-folder rule, warn on missing test files` |

Range pushed: `5a6f7e6..470ec69`. Working tree clean at time of writing.

## 2. TWO REAL BUGS found by running the FULL suite before committing

Both were **invisible in isolation** — this is the important part. `pytest pyscript/test_abpage.py`
alone gave 102 passed; the full suite gave **27 failures**.

**(a) `row_schedule()` leaked `logging.disable(logging.CRITICAL)` process-wide.**
`pyscript/abpage.py` silenced the SF2 parser's stderr narration and never restored it.
That switch is global, so any program importing `abpage` lost logging permanently.
It broke **27 tests across three unrelated files** — `test_stage7_emissions.py`,
`test_sf2_diagnostics.py`, `test_sf2_logger_unit.py` — every one of them asserting
against a log that had silently become `''`.
FIX: scoped to the parse, saved/restored via `logging.root.manager.disable`, restored
in a `finally` that covers the early returns. **Three regression tests added.**

**(b) The staging tests' renderer stub was bypassed in a full-suite run.**
`_stage_with` in `pyscript/test_abpage.py` stubbed via
`monkeypatch.setitem(sys.modules, "pyscript.audio_tightness_tool", fake)`. But
`abpage.stage()` does `from pyscript import audio_tightness_tool as att` (line 122),
which reads the **attribute** off the already-imported `pyscript` package object and
never consults `sys.modules`. In isolation nothing had imported that submodule, so the
stub won. In a full run `test_audio_tightness_renderer.py:17` imports it first, the
attribute exists, the stub is bypassed, and three tests invoked the **real VSID
renderer** and died on "VSID produced no audio".
FIX: `monkeypatch.setattr(_pyscript_pkg, "audio_tightness_tool", fake, raising=False)`
alongside the `setitem`.

**How they were pinned as mine rather than pre-existing:** ran the full suite with my
two test files `--ignore`d → **2602 passed, zero failures**. Final state after both
fixes: **2707 passed, 8 skipped, 2 xfailed**.

## 3. Five `/runqueue` cycles (2 runs of `--until-blocked`)

| Task | Lane | Model/Effort | Outcome |
|---|---|---|---|
| `sdi-accuracy-matrix-d-figure-stale` | delegated | sonnet/low | **done** |
| `laxity-decode-is-two-stage-and-the-viewer-runs-one` | main | opus/xhigh | partial |
| `detect-filter-drives-blind-to-mode-only-changes` | main | opus/high | partial |
| `editor-ground-truth-is-the-converted-sf2-not-the-original` | main | opus/high | **done** |
| `laxity-parser-reads-runtime-pointers-as-the-sequence-table` | main | opus/xhigh | partial |

`runs.jsonl` grew from 125 → **130 records**, none torn, each appended with a single `>>`.
Locks claimed and released under the mutex on every cycle; `serial.lock` is `[]` and
`serial.lock.d` is gone.

### THE BIG TECHNICAL FINDINGS

**Laxity / Angular — the ground-truth question is CLOSED, and it overturned two prior cycles.**
- `SID/Angular.sid` and `SF2/Angular.sf2` are **byte-identical across the entire music
  region: 978 of 978 bytes over `$1AF2–$1EC3`**, at the same C64 addresses. So the SID
  Factory II view of the *converted* file IS a valid oracle for decoding the *original*,
  and cycles 1–5's negative results are **wrong, not uninterpretable**.
- **Cycle 3's "SF2/Angular.sf2 wraps the native NP21 player" is FALSE.** Not even 32
  bytes of the original's player appear in the SF2; `$1000-$10FF` differs outright.
  `SF2/Angular.txt` records the build: SIDM2 **v2.8.0**, 2026-06-09,
  `Selected Driver: LAXITY (sf2driver_laxity_00.prg)`, a manual `--driver laxity`
  override. The SF2 embeds a DIFFERENT player binary that is address-compatible with
  NP21's data layout. The `@X-PLAYER BY LAXITY.MUSIC BY DRAX-` string sits at SF2 offset
  675 but at `$101F` in the original — carried as metadata, not shared code.
- **The `$1B1C`/`$1B2A` split lo/hi table is NOT ruled out** — cycles 3 and 5 both
  rejected it on a bad decode. The region partitions **exactly, zero bytes unexplained**:
  `$1AF2` + 3×14 orderlists = `$1B1C`; + 14 lo + 14 hi = `$1B38` = table entry 0; entries
  `$1B38 $1B3B $1B8F $1BE5 $1C30 $1C6C $1CBD $1D0E $1D46 $1D9A $1DF0 $1E26 $1E58 $1E8B`,
  all ascending, last ending at `$1EC3`. The table is byte-identical in both files.
- **The discriminator is CLOSED**: `scripts/convert_all.py:284` uses `LaxityParser`'s raw
  sequences ONLY for command analysis; line 289 separately calls
  `LaxityPlayerAnalyzer(...).extract_music_data()`, which runs BOTH stages
  (`laxity_analyzer.py:634-640`). So the 99.93–100% figure comes from the two-stage path.
  **`LaxityParser` is half an API, not broken.**
- **BUT the locate is broken far more widely than one file.** `laxity_parser.py:99-117`
  reads `ch_seq_ptr` at `load+$0A1C`/`load+$0A1F` — the playroutine's **RUNTIME
  current-sequence pointer**. On Angular that yields `$0334/$0341/$0336`, all **below the
  `$1000` load address**, accepted by the check at line 125:
  `if seq_addr > 0 and seq_addr < 0x10000`. The three extracted blobs are 232/230/219
  bytes and blob 1 begins at blob 0's offset **+2** — overlapping windows of one code
  region, not three sequences.
- **Measured across the corpus** (a locate counts as good only when all three pointers
  land inside the loaded image AND are distinct):
  - `$099F` works on **2/17** (Angular, Omniphunk)
  - `$0A1C` works on **1/17** (Stinsens_Last_Night_of_89)
  - **14/17 are served by NEITHER**
  `laxity_parser.py:18` already carries the epitaph: *"Old value 0x099F was wrong for
  Stinsen (pointed into filter speed table)."* A constant swap trades two files for one.
- Stage-two grammar, read from `LaxitySequenceParser.parse_sequence`:
  `$00-$7E` note | `$7F` END | `$80-$9F` DURATION `((b & $1F)+1` frames) |
  `$A0-$BF` INSTRUMENT | `$C0-$FF` command INDEX into the command table.
- Orderlists confirmed against the editor for the first time: `$199F` → `$1AF2/$1B00/$1B0E`,
  13 bytes + `$FF` each, first sequence per voice = **01 / 02 / 05** = the editor's
  a000/a001/a002.
- `tools/player-id.exe SID/Angular.sid` → **`Laxity_NewPlayer_V21`**. "Unsupported variant"
  is dead.

**`detect_filter_drives` — premise corrected.**
- It is at `bin/build_mon_native_song.py:888`, NOT the SDI builder. `bin/build_sdi_native_song.py:36`
  does `import build_mon_native_song as BM` and line 38 says *"detect_filter_drives and
  _filt_exact are shared"*. The task's `touches` named only the SDI builder → the cycle
  correctly refused to widen itself.
- The passband-ENABLE case is **already fixed** (second pass, lines 953-965, the
  Juba-Jazz / PATTERNS F9 fix) — narrow by design: only `$D417` none→some.
- The **real remaining blindness is by SIGNATURE**: `detect_filter_drives(ftr, ...)` cannot
  see `$D418` at all. `fidelity_common.siddump_filter_trace` returns **2-tuples** —
  Funk_Facet row 100 is `(928, 241)` = (cutoff, `$D417`). The passband travels separately
  as `pbtr` and only ever reaches `filter_program_for`. Fixing it means threading `pbtr`
  in and updating every caller across MoN, DMC, SDI, FC, Myth.
- **Funk_Facet frame 108 is NOT an instance of it.** `$D417` is constant `$F1` across
  frames 100-119. Cutoff holds 256 for 104-108 then rises **+80/frame** from 109;
  `FILT_FAST` is `0x40` = 64, so 80 CLEARS it and the attack **IS** detected — then
  dropped because `cand` needs a note-on in `[105,110]` (`FILT_LEAD=4`) and there is none.
  That is a missing **ANCHOR**, and belongs to `sdi-funk-facet-pre-onset-anchor`.

## 4. `graphify update` — root cause found and fixed

It had failed **all session** with `error: path not found: \c\Users\mit\claude\c64server\sidm2`.
- Cause: `graphify-out/.graphify_root` (read at graphify `cli.py:2179`) held the Git Bash
  path `/c/Users/mit/claude/c64server/sidm2`. Windows `Path()` parses that as
  `\c\Users\...`, a drive-relative path that does not exist.
- Fix: rewrote it with the native path. `graphify update` now completes — re-extracted
  364 files, **20,441 nodes / 32,016 edges**, at HEAD.
- This unblocked `/whattask` step 5b's dependency cross-check, unavailable since 2026-08-22.

**CRITICAL CAVEAT, measured:** `graphify path` and `graphify query` **return confident
false negatives on this repo.** The `bin_build_sdi_native_song -> bin_build_mon_native_song`
import edge **IS** in `graph.json` links (1 edge), yet:
- `graphify path "bin/build_sdi_native_song.py" "bin/build_mon_native_song.py"` → "No directed path found"
- with `--undirected` → "No path found"
- with the **correct** underscore node ids → "No directed path found"

It answers "no path" rather than "node not found" — the silent fuzzy-match failure.
`graphify query "what depends on bin/build_mon_native_song.py"` returned
`ROMUZAK_SF2_DRIVER_PLAN.md` and `build_galway_digi_songs.py`, neither a dependent.

**The working method:** read `graphify-out/graph.json` `links` directly, map node ids via
their `src` field, treat a cross-file edge as a *prompt to look*, then confirm with
`grep -rlE 'import X|from ... import X'` before widening any `touches`. Edges on this
corpus carry **no `kind`**, so they cannot separate an import from a doc co-mention:
50 of 58 tasks showed "neighbours" that were mostly noise.

Saved to auto-memory as `graphify-on-every-task.md` (user instruction: use graphify on
**all** tasks).

## 5. The graphify cross-check, run on every task for the first time

Grep-confirmed widenings applied to the plan:

| Module | Was missing from `touches` |
|---|---|
| `sidm2/laxity_parser.py` | `sf2_viewer_core.py`, `scripts/test_converter.py`, `scripts/test_laxity_driver.py` |
| `pyscript/sf2_viewer_core.py` | its **4** importers: `abpage`, `sf2_html_exporter`, `sf2_to_text_exporter`, `sf2_viewer_gui` |
| `sidm2/sf2_editor_automation.py` | **5** test files, none previously declared |
| `pyscript/sdi_native_sweep.py` | 2 sweep tests |
| `sidm2/fidelity_common.py` | 6 scorers |
| `pyscript/abpage.py` | `test_abpage_chips.py` |

Plus **13** builders/tools with no test file, each now naming the one its task must CREATE.

## 6. Two plan bugs fixed rather than carried as tasks

- `detect-filter-drives-blind-to-mode-only-changes` now declares
  `rw:bin/build_mon_native_song.py` (where the function actually lives) and its verify
  records the corrected premise.
- The Laxity work is now a real chain:
  `editor-ground-truth-…` (done) → `laxity-parser-reads-runtime-pointers-…` →
  `laxity-decode-is-two-stage-…` → `sf2-viewer-core-sequence-overread` /
  `abpage-pattern-follow-correct-on-all-songs` → `abpage-flagship-corpus-stage`.

## 7. Two Claude Code hooks built (`470ec69`) — the repo's first

Analysis found **zero hooks configured**, no `.claude/settings.json` (only `.local`),
1 subagent, 4 MCP servers, 87 permissions, 5 CI workflows.

- **`.claude/hooks/block_root_py.py`** — PreToolUse(`Write|Edit`), **BLOCKS** a `.py`
  written to the repo root (CLAUDE.md Critical Rule #1, previously enforced only by the
  manual `cleanup.bat --scan`). Narrow by design: repo ROOT only.
- **`.claude/hooks/warn_missing_test.py`** — PostToolUse(`Write|Edit`), **WARNS** when an
  edited source has no `pyscript/test_<name>.py`. Warns, never blocks.
- **`.claude/settings.json`** — new, project scope (trackable), wires both via
  `$CLAUDE_PROJECT_DIR`.

Six pipe-tests before wiring, **including the three that must stay SILENT**
(`pyscript/*.py`, `CLAUDE.md`, a file that already has a test, a test file itself).
**Hook 1 is verified live** — it blocked an attempted write of `hook_probe.py` to the root
and no file was created.

## 8. `/whattask` passes: 55 → 58 → 59 → 60 tasks

- Restored a 39-task backlog from a scratchpad backup that focused passes had shelved.
- Found **24 ids opened by run records that had never reached a plan**; 21 planned, 5 deduped.
- **Caught a real miss of my own**: an earlier pass built from the backlog and run log
  without reconciling `whats-next.md`, and dropped the LIVE Rubicon question. Now tracked
  as `rubicon-locate-fallback-or-re`.
- `SID/LukHash/` (13 new files) identified: **12 are `Hermit/SidWizard_V1.x`, 1 `Mssiah`** —
  a player family with no entry in `DriverSelector.PLAYER_REGISTRY` and no `docs/players/` card.

</work_completed>

<work_remaining>

## THE ONE THING BLOCKED ONLY ON YOU

### Rubicon investigation — awaiting user's choice (UNCHANGED, still unanswered)

Two options were presented, response not yet received:

1. **Harden `mon_parser._locate()`'s fallback** (bounded, mechanical): change
   `sidm2/mon_parser.py:188-189`
   (`else: self.tbl_olptr, self.olset_hi = 0x83FC, 0x7B`) to raise or return a
   clear "not located" signal instead of a silent hardcoded guess, matching
   this repo's own "fail honestly" convention (`fidelity_common.py`'s
   `run_siddump`, `SDIModule.__init__`'s `raise ValueError` are the pattern to
   follow). **Must first check** whether any currently-"working" MoN
   conversion actually depends on this fallback path succeeding by accident —
   grep/sweep the whole corpus for files whose `ol_mode` resolves to
   `"selfmod"` via this exact fallback (not a real `cp` match) before changing
   it, or a silent regression is possible.
2. **RE Rubicon's actual engine variant**: real 6502 work. Load address
   `$3F00` (init `$3F50`, play `$3F64`) doesn't match any of the four known
   locate branches (`selfmod` B9-copy, `stride` BD-copy, `_locate_b1`
   B1-indirect/mainstream-Tel, `_locate_supremacy`). Likely one of the ~85
   still-unhandled files in the mainstream MoN/Tel_Jeroen bucket (see
   `memory/mainstream-mon-tel.md`, auto-memory, not in this repo's tree — ask
   the assistant to recall it). Needs a py65 INIT trace of Rubicon's actual
   code (same technique used throughout this repo's MoN RE arc) to find its
   real orderlist-copy signature and add a 5th `_locate()` branch.

Neither has been started as code. Both `Rubicon.sid`'s sibling files
(`Rubicon_Load_1.sid`, `Rubicon_Load_2.sid`) hit the identical fallback
(same `tbl_olptr=0x83fc`) — whatever fix lands should be re-checked against
all three.

## THE TASK PLAN

**`.claude/tasks/whattask.json` — 60 tasks, 15 closed, 46 ready, head `470ec69`.**
It is **gitignored** (only `runs.jsonl` is tracked under `.claude/tasks/`), so it does not
travel. Read it, don't read this file, for the task list.

**Zero delegable ready tasks.** 45 of 46 ready are `serial`; the only `parallel` one is
`sidwizard-lukhash-unsupported-player`. `/runqueue` runs single-file until something
unblocks. That is real arithmetic, not a labelling artifact — almost every task writes a
corpus subtree or the shared MoN/ROMUZAK driver.

### Highest-value chain (Laxity), in strict order

1. **`which-files-back-the-laxity-99-93-figure`** (sonnet/medium) — cheap and it GATES the
   rest. CLAUDE.md rates native Laxity NP21 at 99.93–100%, yet the locate feeding that path
   fails on 14 of 17 `SID/*.sid`. Read `docs/players/LAXITY.md` and
   `docs/reference/ACCURACY_MATRIX.md` for the named corpus and check whether those files
   are among the ones whose locate succeeds. **Both outcomes are publishable**: if the
   figure rests on 2–3 files, re-stamp the docs with the real denominator; if broader,
   accuracy survives a broken locate and fixing it is safe.
2. **`laxity-locate-fails-on-14-of-17-files-silently`** (opus/high) — the **minimum fix is a
   REFUSAL, not a locate**: reject a pointer outside `[load, load+len)`. That turns 14 silent
   wrong answers into 14 honest failures. Do it FIRST and separately, then measure how many
   files stop converting. `pyscript/test_laxity_parser.py` **does not exist** — create it and
   pin the `$0334`-below-load case.
3. **`laxity-parser-reads-runtime-pointers-as-the-sequence-table`** (opus/xhigh) — the real
   locate. **Do NOT swap the constant** (see Attempted Approaches). It needs a
   **signature-based locate**, the lesson CLAUDE.md already records for HardTrack's
   `vib_depth`. The searchable shape is in Work Completed §3.
4. `laxity-decode-is-two-stage-and-the-viewer-runs-one` → `sf2-viewer-core-sequence-overread`
   and `abpage-pattern-follow-correct-on-all-songs` → `abpage-flagship-corpus-stage`
   (the ~5 h / ~8 GB staging the user authorised: **~100 songs, 60 s, WITH voices** —
   `decisions.jsonl:abpage-scope-and-feature-order`, BINDING).

### Other ready work worth naming

- **`detect-filter-drives-blind-to-mode-only-changes`** (opus/xhigh) — now correctly scoped.
  Needs a file that genuinely changes `$D418` with routing already on; Funk_Facet is not one.
- **`ninety-four-sources-have-no-test-file`** (sonnet/medium) — **94 of 162** files under
  `sidm2/` (74) and `bin/build_*` (20) have no test. This is a **triage** task, not a
  test-writing sweep, plus the hook-scope decision below.
- **`whattask-touches-named-a-writer-as-the-parser`** — 2 of 3 parts done. What remains is
  **durability**: the `.graphify_root` repair is in gitignored `graphify-out/`, so it does
  not travel and re-breaks if a full `graphify extract /c/...` runs from Git Bash.
- **`sidwizard-lukhash-unsupported-player`** (opus/medium, the only parallel task) — check
  `mcp__tdz-c64-knowledge` for an existing SidWizard card BEFORE any RE; it is Hermit's
  documented modern tracker with public sources.

### A decision the hooks left open

Hook 2 fires on any edit to the 94 untested sources, so on the native builders it will fire
often. A warning that always fires is one people learn to ignore. Options: leave it
(accurate, noisy), narrow `WATCHED` in `.claude/hooks/warn_missing_test.py` to `sidm2/` only
(drops 20 of 94), or treat the 94 as a debt list to work down.

### Still `requires-user` besides Rubicon

- `roadmap-e2-oscilloscope` — ffmpeg still not on PATH (agreed to install, not yet present).
- `analysis-docs-are-gitignored` — should `*_ANALYSIS.md` exempt `docs/`?
  Note `.gitignore:248` taught this repo that git never walks into a directory excluded by a
  trailing-slash pattern, so a negation inside it is silently inert — verify with
  `git check-ignore -v`, not by reading the pattern.

### PR #5

Decided: **merge then re-measure**. The runner cannot merge. Its 87%→92% figure is 114
commits stale and **must not be quoted unmeasured**.

</work_remaining>

<attempted_approaches>

## Laxity — approaches RULED OUT across six cycles. Do not re-derive any of these.

- **(a)** Block 5's `sequence_index_address`/`sequence_data_address` — garbage on this file
  (`$1ECB` is `$CB` filler, `$041E` is below the `$0D7E` load). CYCLE 1.
- **(b)** Block 2 (Driver Common) — runtime state addresses only. CYCLE 1.
- **(c)** `sf2_packer` `driver_top + 0x0903` — a Driver 11 constant. CYCLE 1.
- **(d)** ANY contiguous absolute little-endian pointer table — exhaustive 64K search for
  `$24CB` returned **0 hits**. CYCLE 2.
- **(e)** "Reject false positives and the scanner numbering aligns" — WITHDRAWN; the scanner
  never finds the sparse sequences 00/01 at all. CYCLE 2.
- **(f)** Split lo/hi table at `$1B1C`/`$1B2A` — rejected in cycle 3 on a bad decode, and
  **I re-rejected it in cycle 5** after re-decoding with the real `LaxitySequenceParser` and
  the real 64-entry command table, which gave byte-identically the same wrong music.
  **BOTH REJECTIONS ARE NOW SUSPECT** — cycle 6's 978/978 byte-identity proves the table
  partitions the music region exactly. The *decoder* is the likely fault, not the locate.
  Treat (f) as REOPENED.
- **(g)** Forcing `_parse_laxity_sequences()` — reaches the branch, yields one sequence of
  zeros. CYCLE 4.
- **(h)** Running BOTH stages via `LaxityPlayerAnalyzer` — returns 3 sequences of
  **846/843/795 events** with its own validator printing "Sequence 0 too long (846 events)".
  Stage two runs fine; it is fed garbage. CYCLE 5.
- **(i)** **Swapping the constant `$0A1C` → `$099F`** — measured and refuted. 2/17 vs 1/17,
  with 14/17 served by neither. `laxity_parser.py:18` already records that `$099F` was tried
  and rejected for Stinsen. A swap trades two files for one. CYCLE 6.

## Two hypotheses of my own, refuted this session

- **"Funk_Facet frame 108 is a mode-only change"** — no. `$D417` is constant `$F1`, and
  `$D418` is not an input to the detector at all.
- **"The frame-109 attack rises too slowly for `FILT_FAST`"** — no. +80 clears the 64
  threshold comfortably; the attack IS detected and then dropped for want of an anchor.

## Testing-apparatus failures worth remembering

- `pyscript/abpage_scroll_harness.js` passed **three times on a visibly broken page** before
  being fixed to mirror the real DOM.
- `pytest pyscript/test_abpage.py` alone gives 102 passed while the full suite gives 27
  failures — **isolation is not evidence**. `pytest-randomly 4.1.0` is now installed, which
  is what would have caught this at introduction.
- I twice told the user a working graphify would have caught the wrong `touches`, then
  measured it and found `graphify path` reports "no path" for an edge that IS in the links.
  The data was there; the CLI does not surface it.

## Dead ends not pursued

- Adding `context7` or other MCP servers — this repo already runs tokensave, retrodebugger,
  c64bridge and tdz-c64-knowledge, and its real references are disassemblies, not JS docs.
- Generating 94 test files mechanically — rejected as ceremony; the task is triage.

</attempted_approaches>

<critical_context>

## Numbers that must be quoted with their conditions

- **99.93–100% native Laxity** is now in tension with a locate that fails on 14/17 files.
  Do not repeat the figure until `which-files-back-the-laxity-99-93-figure` answers.
- **PR #5's 87%→92%** is 114 commits stale. Never quote unmeasured.
- **SDI D-variant is 89.9 / "8 of 15"**, not the retracted 95.9 / "7 of 15". Both surviving
  mentions of the old pair (CLAUDE.md:175, ACCURACY_MATRIX.md:63) are **explicitly labelled
  retractions and must be left alone** — verified this session, nothing was stale.

## Environment gotchas hit this session

- **The Bash tool is Git Bash, not PowerShell.** PowerShell here-strings (`@'...'@`) are a
  parse error. Use a message file + `git commit -F`, which is what worked.
- **`jq` is NOT installed.** Validate JSON with Python.
- Heredocs choke on backslashes in Python string literals — write the script to a file
  instead (that is why the scratchpad has `genplan*.py`, `rec_*.py`, `xcheck*.py`).
- `graphify-out/` is **37 MB** and now gitignored (`fd0345e`).
- The repo pushes **directly to `master`** (`MichaelTroelsen/SIDM2conv`); that is its
  established convention and the user asked for commit+push twice.

## Repo conventions that bit or nearly bit

- `pyscript/test_version_stamps_agree.py` pins version, build date and the CHANGELOG heading
  across five files — but **NOT** CLAUDE.md's own `**Size**:` stamp. Verified by hand this
  session: 40,456 bytes = 39.5 KB, matching. A test for it is still missing.
- CLAUDE.md is measured in **bytes**, not lines, and is loaded into every session.
- `out/.mon_build.lock` is the external lock; the `hazards` array names the shared
  MoN/ROMUZAK driver files. Checked absent before every cycle.
- `passband_check` writes a scratch probe `.sid` beside each artifact — declare it in
  `touches` even for a "read-only" task.

## Files created this session (all committed)

`pyscript/abpage.py`, `abpage_chips.py`, `test_abpage.py`, `test_abpage_chips.py`,
`abpage_browser_probe.py`, `abpage_scroll_harness.js`, `ab-listen.bat`,
`docs/plans/ABPAGE_PORT_PLAN.md`, `.claude/hooks/block_root_py.py`,
`.claude/hooks/warn_missing_test.py`, `.claude/settings.json`, `SID/LukHash/` (13 files).

## Auto-memory written (outside the repo, will NOT travel)

`~/.claude/projects/C--Users-mit-claude-c64server-sidm2/memory/graphify-on-every-task.md`
— the user's standing instruction plus the CLI-false-negative caveat and the root fix.
Indexed in `MEMORY.md`.

</critical_context>

<current_state>

- **HEAD `470ec69`, working tree CLEAN, everything pushed to `origin/master`.**
- **Test suite: 2707 passed, 8 skipped, 2 xfailed.** `pytest-randomly 4.1.0` active.
- `.claude/tasks/whattask.json`: **60 tasks, 15 closed, 46 ready**, head `470ec69`. Gitignored.
- `.claude/tasks/runs.jsonl`: **130 records**, none torn. Tracked and committed.
- `serial.lock` is `[]`; the `serial.lock.d` mutex directory does not exist. No cycle in flight.
- `graphify update` **works** — 20,441 nodes / 32,016 edges at HEAD. The repair is local-only.
- Both hooks are **live**. Hook 1 verified by blocking a real write; hook 2 is loaded and
  pipe-verified but was not triggered live (that would have meant editing a builder for a demo).
- Nothing is half-applied. No temporary workarounds are in place. The one scratch artifact,
  `graphify-out/.graphify_root.bak`, was deleted after the fix was confirmed.

**Open questions, in priority order:**
1. Rubicon — harden the fallback, or RE the variant? (asked repeatedly, never answered)
2. Hook 2's scope — leave, narrow to `sidm2/`, or work the 94 down?
3. `*_ANALYSIS.md` — exempt `docs/`?
4. ffmpeg on PATH (unblocks `roadmap-e2-oscilloscope`).

**Recommended next action:** answer Rubicon. It has now survived four planning passes
unanswered, it is the only item stalled purely on a human rather than on other work, and
both of its branches are otherwise ready to run.

</current_state>
