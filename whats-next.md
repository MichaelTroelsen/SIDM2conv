<original_task>
The user typed `read what next.`, then drove an autonomous task-queue session with
`/loop /runtask` (dynamic mode, self-paced ~20 min ticks). There was no feature
request; the standing instruction was to keep draining the plan in
`.claude/tasks/whattask.json`, cycle after cycle, with the mit-setup plugin's
gates enforced.

Explicit user messages, in order:
1. `read what next.` — read the previous session's handoff.
2. `/mit-setup:whattask` — regenerate the plan.
3. `/loop /runtask` × many — run task cycles. No interval given, so DYNAMIC mode:
   self-paced, one task per tick, `ScheduleWakeup` re-armed at the end of each.
4. `commit and push` — land the accumulated work.
5. `/subtask model fabel do a /code-review` then `keep looping`.
6. `cont` — continue after a usage-limit pause.
7. This handoff.

BINDING CONSTRAINTS from the command set, honoured throughout:
- `/runtask`, `/runqueue`, `/whattask` NEVER commit, merge, push, branch or open
  a PR. The only git write operations happened on the user's explicit
  `commit and push`.
- "AN UNDECLARED PATH IS A STOP, NEVER A GRANT" — `touches` is the complete list
  of paths a task may WRITE.
- `runs.jsonl` is append-only, ONE line per attempted task, single `>>`; never
  read-and-write-back.
- `whattask.json` is rewritten ONLY by `/whattask`.
- `serial.lock` updates go through the `.claude/tasks/serial.lock.d` mutex,
  written via `.tmp` + `os.replace`, released on the failure path too.
</original_task>

<work_completed>

## Commits landed and pushed

`21d3b48..a5cdb0d` — TEN commits, pushed to `origin/master`. Direct-to-master,
matching this repo's established practice (the previous session's `commit and
push` rounds also went straight to master).

| sha | what |
|---|---|
| `6929c22` | `fix(sf2)` — SF2-export detection by structure, not a 2-byte substring |
| `8591f95` | `fix(viewer)` — refuse a decode that cannot fit in its own file |
| `1ff6035` | `fix(listen)` — degenerate wins over truncated |
| `33c1eda` | `fix(logging)` — cp1252 message loss + the `propagate` leak |
| `b1f11fb` | `feat(siddump)` — `--init`/`--play` overrides |
| `f7bf56e` | `fix(sweeps)` — kill-safety for three serial sweeps |
| `27458f5` | `feat(dispatch)` — zero-collision guard instead of arbitration |
| `43dc80b` | `docs` — Driver 11 extractor inert; MATTGRAY.md self-contradiction |
| `30e4574` | `chore(tests)` — track `pytest.ini` |
| `5ecf299` + `a5cdb0d` | prior session's handoff (marked stale) + 18 run records |

## Task cycles (runs.jsonl records 196-215, 20 records, 14 done / 5 partial / 1 superseded)

**`sf2-export-detection-is-a-two-byte-substring-search` — partial then DONE.**
`has_sf2_magic = b'\x37\x13' in c64_data` scans 8KB+ for two bytes. It fires on
**46 of 1,524** tree SIDs at offsets like 809 / 2198 / 11112, and NOT ONE at
offset 0. An SF2 file is `[load_lo, load_hi, $37, $13, <blocks>]`, so after
SIDParser strips the load address the marker sits at C64-data offset 0 and the
first block descriptor at offset 2 — verified via an `sf2_to_sid` round trip of
the TRACKED `bin/music/Driver 11 Test - Arpeggio.sf2`. Shipped
`has_sf2_structure()`: marker@0 + first block is `BLOCK_DESCRIPTOR` + in-bounds
size. **422 of 422** `.sf2` satisfy it; **0 of 46** false positives survive.
**THE OBVIOUS STRENGTHENING IS REFUTED**: walking the chain to `BLOCK_END`
REJECTS a genuine export — a real chain degenerates into `id=$00 size=0` filler
and never reaches `$FF`. A test pins that refutation. New
`pyscript/test_conversion_pipeline.py` (9 tests).

**`sf2-exported-fixture-pins-the-substring-defect` — done.**
`TestSF2ExportedPath::test_analyze_sf2_exported_sid` built its fixture as
`b'\x00'*100 + b'\x37\x13' + b'\x00'*922` — the marker at offset 100, the exact
chance-collision shape — and asserted `SF2PlayerParser` is used. It passed only
because the check was a substring search. **The only test covering that path was
asserting the defect.** Now a real SF2 image.

**`out-sf2exported-probe-breaks-player-index` — done.** The directory held **12**
files, not the 6 the handoff estimated: three `.sf2` PAIRS (`_g`/`_n`/`_noguard`)
from the guard A/B. All three pairs are **byte-identical** (md5 `aa614aa0…`,
`7e66aba5…`, `febf2666…`), so they were EVIDENCE. **Moved to the scratchpad, not
deleted**; md5s recorded in the run log.

**`test-stage7-emissions-order-dependent-logging-flake` — done.** Root cause:
`sidm2/logging_config.py:311` sets `logger.propagate = False` inside
`setup_logging()` and never restores it; `scripts/test_logging_system.py` calls
it ~17 times, so the first to run detaches the `sidm2` logger from root for the
session, and `test_stage7_emissions` (which captures on the ROOT logger) then
sees `''`. Fixed with an autouse fixture in the TEST, not in `logging_config`
(propagate=False is correct for a configured app logger; graphify puts 789 nodes
at depth 2 behind that module). `TestZZPropagateIsRestoredBetweenTests` sorts
last so it fails DETERMINISTICALLY under `-p no:randomly`.

**`logging-warning-crashes-on-a-non-ascii-glyph` — done.** It does NOT crash —
that is why nobody noticed. Under `PYTHONIOENCODING=cp1252` the handler raises
`UnicodeEncodeError`, logging swallows it, **the message is discarded** and a
traceback goes to stderr. Fixed at the STREAM with
`errors='backslashreplace'` (not `'replace'`, so which glyph it was stays
recoverable). Pinned with a real `io.TextIOWrapper(encoding='cp1252')`, no env
var, so it reproduces on any platform.

**`other-sweeps-have-no-kill-safety` — done. THE TASK'S PREMISE WAS REFUTED.**
The verify said the orphan behaviour follows from `ThreadPoolExecutor +
subprocess.run` and "a sweep that runs serially needs nothing". None of the four
targets uses a pool. A serial stand-in was hard-killed mid-child: **unguarded →
child SURVIVED and wrote its artifact; guarded → 0 survivors.** The pool
multiplies orphans; it is not the mechanism. Guarded `blackbird_sweep`,
`hardtrack_native_rebuild`, `soundmonitor_sweep`; `instrument_map_sweep` spawns
nothing and is genuinely exempt. New `pyscript/test_hardtrack_native_rebuild.py`.

**`pytest-ini-is-gitignored-so-its-addopts-do-not-travel` — done.** Demonstrated
against a REAL clone (`.git` is 48M): this tree collects 3,106 clean; the clone
collects 3,167 **with 10 collection ERRORS and "Interrupted"** — it cannot run
the suite at all. Eight are `archive/`; **two are LIVE tests**
(`test_audio_export_wrapper.py`, `test_sf2_player_parser.py`) because `archive/`
carries same-named copies that shadow them on basename. Decision: TRACK
`pytest.ini` (highest precedence; addopts moved to `pyproject.toml` would travel
and then lose to a stale local `pytest.ini`).

**`siddump-needs-an-init-play-override` — done.** `Barbers_Adagio_64` declares
`play=$0000`; the vector fallback recovers `$2708`, one link of a 4x multispeed
raster-split chain that busy-waits on `$D012`. Default exits **1**; with
`--init 0x1000 --play 0x1003` it exits **0** with a 109-line dump. **`--play` had
to beat the FALLBACK, not just the header** — its header play IS `$0000`.

**`abpage-row-schedule-flags-empty-tracks-as-truncated` — done.** Two writes ran
in SEQUENCE at the end of the per-track loop: the degenerate check empties
`rows`, then `if cut: truncated.append(tno)` fired anyway. Fix is
degenerate-wins (`cut = False` in the same block). Corpus sweep at cap 2048 over
411 files: **0** tracks in both lists, **0** truncated flags on empty tracks, one
honest truncation (`hawkeye_subtune_0`, `[2048, 0, 133]`).

**`unbounded-laxity-fallback-readers-emit-13k-entry-sequences` — done.** Bound is
an IMPOSSIBILITY, not a threshold: every packed entry costs ≥1 byte, so entries
cannot outnumber the file's bytes. Over 47 files exactly ONE breaches it
(`_test_commando`, 24,696 entries in 22,705 bytes); next largest legitimate
decode uses **13%** of its bound. **The check is on the TOTAL** — commando's two
bodies each fit and only their sum does not. **47 of 47 still decode**; the
refusal falls THROUGH. Recorded on `sequence_refusals`.

**`laxity-heuristic-decodes-need-provenance-marking` — done.**
`SF2Parser.sequence_provenance = {reader, structural}` set at all seven dispatch
return sites; `structural=True` reserved for `_parse_laxity_real_sequences`.
Re-measured split: **22 structural / 25 heuristic** over 47 (task said 21/24 over
45). `row_schedule` carries it verbatim into the `patterns.json` sidecar;
`patterns_card` renders a banner naming the reader. Mutations at BOTH layers fail
in DIFFERENT tests.

**`mattgray-probe-count-has-three-disagreeing-figures` — done. THE WRONG NUMBER
WAS MINE.** Docs say 11/55; measured 11/55. The "12" was my own `rglob` bucketed
by path prefix — the twelfth is `SID/Gray_Matt/Worktunes/2001_Theme.sid`, a
SUBDIRECTORY file. 11 and 12 are both right at their own denominators. A REAL
defect was there though: `MATTGRAY.md` line 46 and line 49 contradicted each
other seven lines apart; line 49's parenthetical was stale. Fixed.

**`abpage-flagship-render-cost-estimate-is-optimistic` — done. TITLE IS
BACKWARDS.** A 20s render is **1.15s (n=3)**, not 7.5s → ~38 min per 100 songs,
not ~5h. **CAVEAT KEPT**: I measured the BARE RENDER; if the original 7.5s was
the whole `stage` step, ~6.3s of non-render work is outside my measurement.
Size: ~8 GB **confirmed** for stereo+voices, but only Angular is that
configuration — the other 10 staged songs are 30s MONO, NO voices at 5.3 MB.

**`what-supplies-the-emitted-sequences-on-the-misrouted-path` — done.** The
inherited A/B could not answer its own question (guard-present vs guard-removed
are the SAME branch). Switched the BRANCH instead: misrouted vs correct give
**byte-identical** output (17,957 / 52,658 / 52,214), yet the branches hand
downstream **sequences 0 vs 3, instruments 0 vs 8**. So `ExtractedData.sequences`
and `.instruments` never reach the writer — **the extraction stage is decorative
on this path**, and "100% by construction" is not evidenced by it.

**`cybernoid-ii-sub0-native-passband-mismatch` — partial.** The PREVIOUS cycle's
premise is FALSE: `traces` is a CACHE, not a feature gate — `build_native_song`'s
`if traces is not None:` has an ELSE (2 lines 1603-1609) computing `pbtr`
identically. The real gate is the OPT-IN env var `INIT_PASSBAND` at 1626.
Setting it emits `INIT_FMODE = $10` and moves `ours` from `off/LP+BP` to
`LP/LP+BP` — the leading `off` is GONE — while the score stays **84.6%**. So the
init value is right and the FIRST FILTER ROW IS LATE: a second, distinct defect.
Everything reverted byte-for-byte (md5 verified).

**`dispatch-cross-family-arbitration-for-contested-files` — partial.** **ZERO
collisions** over 1,524 files (1,248 sig=0, 276 sig=1, 0 sig>1). Counts validate
against the module's own pinned figures. `hardtrack` ∩ `sdi` on Shogoon = **0**.
So a rule would be fitted to zero examples. Shipped the guard instead, with an
explicit VACUOUS-PASS floor (probes claiming nothing also produce zero
collisions).

**`gate-treats-the-driver11-fallback-as-an-sf2-identification` — partial. PREMISE
INVERTED.** After the detector fix `has_sf2_structure` is True for **0 of 1,524**
tree files, so the driver clause can no longer cause a false positive — only a
MISS. Demonstrated: a genuine SF2 export (round trip of SF2II's own DRIVER 11
test file) is called `SidFactory_II/Laxity` by player-id and routes to the
**laxity** driver, so `is_sf2_exported` is False. **`driver_selector.py:67` and
CLAUDE.md directly contradict each other on that string**, which CLAUDE.md marks
Critical. Cleanup deliberately NOT applied while `sf2_player_parser` still
misreads the packed grammar.

**`dmc-dreaming2-v3` — partial. IT IS ONE BIT.** On all 75 audible frames the
original writes `$51` and ours writes `$50` — same pulse nibble, **only the gate
differs**. Our v3 has **zero** gate-on frames in 500, against 449/89 for voices
1/2. `decode_song` yields **1,527** v3 events, MORE than either other voice, so
the loss is strictly downstream of decode. "audible 0.0% wf" does NOT mean
silent.

**`three-sf2-payloads-decode-differently-from-their-own-sid` — partial. THREE
DIFFERENT PROBLEMS.** Stinsens does NOT "return nothing" — 1,762 entries from the
heuristic; its locate finds **ZERO** candidates (Angular/Blue/Dreamy each find
1). Relaxing `ptrs[0] == tbl + 2*count` finds `tbl=$1A22, N=39, shift=+97`, six
bytes from the `$1A1C` the task names, one body decoding to exactly 53 (one of
the SID's three sizes) — but that relaxation takes candidates **0 → 881**. Blue
locates cleanly; 545 vs 567 is a SHAPE difference (22 sequences vs 1), not a
defect. Dreamy's "1806 vs 169" no longer reproduces — 207 vs 379 today, an
under-read.

## `/whattask` regeneration (one pass, tick 5)

Rewrote the plan at head `21d3b48`: **81 tasks, 146 closed, 59 ready**. Graph
refreshed first (`graphify update` → 20,754 nodes / 32,506 edges).

**THE BIG FIND: 53 task ids had been run to `done` and never recorded in
`plan.closed` by any previous pass** — invisible as completed work, present only
in `runs.jsonl`. `closed` jumped 88 → 146.

Also: closed `mon-single-file-path-builds-without-a-passband-trace` as a REFUTED
premise; re-opened `sf2-player-parser-reads-fixed-triples-…` which a previous
pass had closed on a `partial`; widened `touches` on
`cybernoid-ii-sub0-native-passband-mismatch` (+`rw:docs/players/MON.md`) and
`test-stage7-emissions-…` (+`rw:scripts/test_logging_system.py` — **without which
that fix was unreachable**); stripped 4 more path-shaped `opened` entries (7th
sighting).

</work_completed>

<work_remaining>

## Uncommitted right now — four files, one task

`laxity-heuristic-decodes-need-provenance-marking` (record 214, `done`) landed
AFTER the push. 135 insertions across:
- `pyscript/sf2_viewer_core.py` (+25) — `sequence_provenance` field, `_mark_provenance`, 7 call sites
- `pyscript/abpage.py` (+24) — `provenance` in `row_schedule`'s dict, banner in `patterns_card`
- `pyscript/test_sf2_viewer_core.py` (+42) — 2 tests
- `pyscript/test_abpage.py` (+42) — 3 tests

Plus `.claude/tasks/runs.jsonl` (+2 records, 214 and 215).

Verified: **3,114 passed / 0 failed** under `--randomly-seed=1`. Both mutation
directions caught. **Commit and push when ready** — this is the only outstanding
deliverable state.

## Then, in priority order

1. **`/whattask` is 12 orphan ids behind.** The plan head is `21d3b48` while HEAD
   is `a5cdb0d`, and these exist only in `runs.jsonl`:
   `mon-single-file-traces-premise-is-false-close-it`,
   `patterns-f13-should-prefer-line-range-patching-over-string-anchors`,
   `claude-md-and-driver-selector-disagree-on-sidfactory-ii-laxity`,
   `mattgray-test-docstring-names-five-unbuilt-songs-but-there-are-three`,
   `root-conftest-should-ignore-archive-independently-of-pytest-ini`,
   `siddump-tests-are-split-across-two-differently-named-files`,
   `dmc-tasks-declare-the-mon-builder-but-dmc-songs-use-build-dmc-native-song`,
   `logging-file-handler-encoding-unmeasured`,
   `driver11-doc-task-patched-a-read-only-path-touches-needs-rw`,
   `staged-pattern-sidecars-predate-provenance-and-show-no-banner`,
   `laxity-locate-requires-bodies-immediately-after-the-table`,
   `blue-sf2-vs-sid-is-a-shape-difference-not-a-defect`.
   `mon-single-file-traces-premise-is-false-close-it` should be CLOSED, not run.

2. **USER DECISIONS (14 `requires-user` tasks; these four are live):**
   - **`sf2-exported-100pct-fork-decision`** — now has decisive new evidence: the
     extraction stage is INERT on that path (sequences 0 vs 3 changes no output
     byte). Options: (a) quarantine the sequence path and restate
     `ACCURACY_MATRIX.md:42` + `DRIVER11.md:6`; (b) authorise
     `sf2-player-parser-locate-then-decode-then-duration`. (a) recommended.
   - **`claude-md-and-driver-selector-disagree-on-sidfactory-ii-laxity`** (not yet
     in the plan) — `driver_selector.py:67` maps that string to LAXITY;
     CLAUDE.md says Driver11 and marks it **Critical**. One is wrong. Needs both
     paths writable plus a measurement of what such a file contains.
   - **`laxity-9993-restamp-docs`** — the number came back ABOVE target
     (16/17 at exactly 100.00%); presentation is the human's call. The 30-second
     window caveat must travel with it.
   - **DMC/HardTrack/MoN passband A/B** (`dmc-driver-init-passband-default`) —
     deferred FOUR times this session, deliberately. It rebuilds `out/dmc`
     (991 parts) and `out/hardtrack_native` (313) IN PLACE at two settings —
     hours, and an interrupted tick leaves them half-rebuilt. **Needs a green
     light.** Now corroborated on a SECOND family (MoN shows the same
     `off/LP+BP → LP/LP+BP` move), so MoN belongs in the A/B too.

3. **Re-run `/code-review` over `21d3b48..HEAD`.** The `@code-review` fork FAILED
   (session rate limit) AND had scoped itself to `git diff HEAD~1` — just the
   runs.jsonl append — so it would not have reviewed the ten commits anyway.

4. **`mon-first-filter-row-is-late-not-the-init-value`** — depends on the DMC
   passband decision. The init value is proven right; what remains is why the
   first filter-program row is late. `romuzak_driver.asm:469` documents the
   steady-state version of the same lag.

5. **`dmc-dreaming2-v3` needs `bin/build_dmc_native_song.py`** in `touches` — it
   declares `bin/build_mon_native_song.py` instead, and Dreaming_2 is built by
   the DMC builder. Diagnosis is complete; only the fix is blocked.

6. **`laxity-locate-requires-bodies-immediately-after-the-table`** — Stinsens'
   locate needs a candidate to EXIST, not disambiguation. Any shift relaxation
   must add a second discriminator (0 → 881 candidates otherwise) and must
   re-verify the 22 structural files are unmoved.

</work_remaining>

<attempted_approaches>

## Refuted hypotheses (do NOT re-try)

- **"Strengthen the SF2 detector by walking the block chain to `BLOCK_END`."**
  Written, measured, REFUTED: it rejects a genuine export. A real chain
  degenerates into `id=$00 size=0` filler and runs off the end without reaching
  `$FF`. A test pins this so it is not re-added.
- **"The MoN single-file path builds without a passband trace."** FALSE — the
  `if traces is not None:` branch has an ELSE computing `pbtr` identically.
  `traces` is a CACHE for windowed builds. The previous session's hoist was a
  functional no-op, which is exactly why its score did not move.
- **"A serial sweep needs no kill-safety."** The task's own verify said this.
  Refuted by experiment: an unguarded serial parent's child SURVIVED a hard kill
  and wrote its artifact.
- **"The Matt Gray probe count has three disagreeing figures."** Two of the three
  were fine; the third was MY OWN `rglob`-bucketed-by-prefix artifact.
- **"Stinsens' SF2 returns nothing."** It returns 1,762 entries from the
  heuristic. The "returns nothing" phrasing is stale and will send the next
  attempt hunting an empty-result bug that does not exist.
- **"Dreamy over-reads 1806 vs 169."** No longer reproduces: 207 vs 379 today,
  an UNDER-read.
- **"Blue is a decode defect."** It locates cleanly; 545 vs 567 is a SHAPE
  difference (22 sequences vs 1). The verify's "same shape" bar is unreachable.
- **"`audible 0.0% wf` means a silent voice."** It means never byte-EQUAL. The
  waveform nibble is correct; only the gate bit differs.
- **"The render-cost estimate was optimistic."** Backwards — pessimistic ~6.5x on
  time, correct on size.
- **Arbitration between dispatch families.** No instance exists: 0 collisions in
  1,524 files. Eleven designs were already refuted in the module docstring; a
  twelfth fitted to zero examples is not an improvement.

## Tooling traps hit this session

- **A MUTATION THAT NEVER APPLIED, TWICE IN A ROW.** Heredoc backslash escaping
  did not survive into the Python source, the anchor matched 0 occurrences, and
  **the suite then PASSED** — which reads exactly like "the test does not catch
  its mutation" and would have CERTIFIED the code. Only `assert count == 1`
  caught it. This is `PATTERNS.md` F13 recurring. **Reliable form: patch by
  verified LINE RANGE, assert the block's first/last lines, assert the marker
  string is present afterwards.** Opened as
  `patterns-f13-should-prefer-line-range-patching-over-string-anchors`.
- **A MUTATION BACKUP TAKEN FROM THE WRONG POINT.** Restoring `blackbird_sweep.py`
  from its PRE-EDIT backup after a mutation also reverted the feature. Take the
  mutation backup from the ALREADY-EDITED file.
- **TESTS THAT PASSED AGAINST A STUB.** `hasattr(module, 'helper')` plus "output
  mentions kill-safety" both passed against `lambda: False` — the NOT-ESTABLISHED
  branch contains the same string the test grepped for. **18 passed under the
  mutation.** The assertion with teeth is IDENTITY against the shared module.
- **A SILENTLY SKIPPED TEST.** Three parametrised cases pointed at `SF2/<name>.sf2`
  when the files are under `out/`; the run reported "94 passed, 3 skipped" and
  looked fine. A skipif that fires is indistinguishable from a pass in a summary
  line — check what the skips ARE.
- **A PARSER'S OWN READ-BACK LYING.** `sf2_viewer_core` reported 71,236 entries in
  a 17,957-byte file. Arithmetically impossible; nearly used as evidence. That
  incident is what decided the impossibility guard.
- **Bash tool heredocs** mangle backslashes in some cases — use the Write tool for
  scripts containing escapes.
- **`VAR=val py -3 -c ...` trailing assignments do not reach Python** in this
  shell; use `export VAR=...` first.
- **Piping a long background run through `| tail`** buffers everything until exit —
  nothing is visible mid-run.
- The **classifier was briefly unavailable** (`claude-sonnet-5` overloaded), which
  blocks Bash and MCP but NOT Read/Grep/Glob.

</attempted_approaches>

<critical_context>

## The lock protocol as actually operated

`.claude/tasks/serial.lock.d` mutex, `.tmp` + `os.replace`, released on the
failure path. The helper used all session is
`<scratchpad>/lockmgr.py` (session-local; recreate it from the protocol in
`**/mit-setup/LOCKING.md` if needed).

**One orphan was reaped**, at tick 1: `test-stage7-emissions-…`, pid 4327, host
match, pid not running. **It was safe THAT time and would not have been earlier**
— the previous session declined to reap the same class because an agent was
mid-edit. I verified both its declared files were CLEAN in git before reaping.
Tracked as `runtask-lock-records-a-transient-shell-pid`.

## Repo conventions that bit

- **`out/` is the CORPUS tree, not scratch.** `test_player_index.py` asserts every
  `out/` dir holding `.sf2` is classified. Investigation artifacts do not belong
  there — that is the correct fix, not an `IGNORED` entry.
- **`out/` and `drivers_src/mon/*.inc` are gitignored**, so builder side effects
  are invisible to `git status`. Verify by md5, not by `git diff`.
- **`*_ANALYSIS.md` is gitignored** (`.gitignore:91`) — writing there adds zero
  review burden.
- **A corpus rebuild does not reproduce shipped bytes**: a stock rebuild of
  `Cybernoid_II_sub0_native` gives `9c1fb374…` against the shipped `42de0fdd…`.
  One sample cannot separate nondeterminism from a stale artifact.
- **`passband_check` writes `out/<player>/_passband_probe_<stem>.sid`** — a scratch
  write that no verify string names. Declare it or do not run the tool.
- **The suite is now green under a RANDOM seed.** The long-standing "NOT green
  without `-p no:randomly`" caveat was one leaked global and is obsolete. Any doc
  still saying otherwise is stale.

## Measurement discipline that paid off repeatedly

Every task this session that had a stated premise was measured BEFORE acting, and
**five premises turned out wrong** (serial-needs-nothing, mattgray's three
figures, Stinsens returns-nothing, Dreamy's over-read, the render estimate's
direction). Where a fix was shipped, a mutation was run in BOTH directions and
the failures checked to be DISTINGUISHABLE — twice that caught tests with no
teeth.

## Environment

Windows 11, Git Bash + PowerShell, Python 3.14.7, pytest 9.1.1 with
`pytest-randomly`. `pytest-timeout` NOT installed. `ffmpeg` NOT on PATH
(re-checked). MCP `sidm2-siddump` failed to connect all session; `tokensave` and
`graphify` work. Scratchpad:
`C:\Users\mit\AppData\Local\Temp\claude\C--Users-mit-claude-c64server-sidm2\deac50e5-…\scratchpad`.

</critical_context>

<current_state>

## Git

- HEAD = **`a5cdb0d`**, `origin/master` **in sync**. Ten commits pushed this
  session (`21d3b48..a5cdb0d`).
- Working tree: **five files modified, all from ONE completed task** (record 214,
  `laxity-heuristic-decodes-need-provenance-marking`) plus the two run records:
  `pyscript/sf2_viewer_core.py`, `pyscript/abpage.py`,
  `pyscript/test_sf2_viewer_core.py`, `pyscript/test_abpage.py`,
  `.claude/tasks/runs.jsonl`. 135 insertions, 0 deletions.

## Locks

`.claude/tasks/serial.lock` is `[]` — **no holder**. Every task this session
claimed and released cleanly.

## Run log

`.claude/tasks/runs.jsonl` — **215 records**, tracked in git, **2 uncommitted**
(214 and 215).

## Plan

`.claude/tasks/whattask.json` — 81 tasks, 146 closed, **48 ready**, 14
`requires-user`. Head `21d3b48`, now **1 commit + 12 orphan ids stale**.
Readiness must be recomputed from `runs.jsonl`, never read off the file.

## Suite

**3,114 passed, 21 skipped, 2 xfailed, 0 FAILED** under
`py -3 -m pytest pyscript/ scripts/ -q -p randomly --randomly-seed=1`.
Green under both a fixed and a random seed — for the first time.

## Loop

A `ScheduleWakeup` was armed for the next `/loop /runtask` tick. The user's last
loop instruction was `keep looping`; they have not asked to stop.

## Open questions for the user

1. **Commit and push the four provenance files?** (the only uncommitted work)
2. **Issue 1 fork** — quarantine-and-restamp (recommended) or authorise the
   parser repair? Now backed by "the extraction stage is inert on this path".
3. **`SidFactory_II/Laxity`** — is `driver_selector.py` right or is CLAUDE.md?
4. **Green light for the DMC/HardTrack/MoN passband A/B?** (hours, in-place)
5. **Re-run `/code-review` over `21d3b48..HEAD`?** The fork failed on a rate
   limit and was mis-scoped.

</current_state>
