# Handoff — SIDM2 session, 2026-08-21/22

<original_task>
Drive the task-orchestration loop the `mit-setup` plugin provides:
`/whattask` (generate the plan) → `/runqueue --until-blocked` (drain it) →
`/runtask` (one task) → `/runhuman` (interview the blocked ones). The user
drove it with repeated invocations plus **"commit and push"** three times, and
one **"merge, commit, push"** whose merge half turned out to have no target.

No feature was requested. The scope was: work the plan, verify everything,
never commit from inside a runner, and hand the commits to the user.
</original_task>

<work_completed>

## 10 commits, `6a1f9c9..71a7024`, all pushed to origin/master

| sha | what |
|---|---|
| `8c76e23` | `feat(dispatch)` — native_dispatch wired into conversion_pipeline as an **advisory**, not a router |
| `2bdbb71` | `fix(build)` — four faults in the shared native build pipeline |
| `f797fca` | `fix(mattgray)` — mis-located pattern table blamed the walk |
| `a240049` | `docs(mattgray)` — Stage B counts measured off disk |
| `a1e6f9a` | `feat(provenance)` — every artifact stamped with commit + flags |
| `840f0f5` | `fix(dispatch)` — sdi probe claims foreign files; 4 provably refused |
| `4dc817d` | `docs(roadmap)` — A4 no longer claims the module is inert |
| `e245ff5` | `fix(mattgray)` — pattern table was one byte wide; tempo was eating it |
| `280b6cc` | `fix(build)` — last two holes in the set-atomicity contract |
| `71a7024` | `feat(mon)` — open on the original's passband instead of declaring it late |

Suite went 2549 → **2600 passed / 8 skipped / 2 xfailed**. Every commit was
verified with a real run before it landed; several were re-verified after.

## Tasks run (15 records appended to `.claude/tasks/runs.jsonl`, now 100 lines)

**done**: `builder-emits-then-refuses`, `builder-leaves-extra-parts-on-shorter-rebuild`,
`builder-refuses-no-notes-but-not-no-trace`, `dmc-demo-iv-tune5-wave-overflow`,
`plan-touches-under-declared`, `mattgray-claude-md-counts`,
`mattgray-pattern-no-ff-terminator`, `commit-dispatch-wiring`,
`roadmap-a4-inert-claim-stale`, `corpus-provenance-stamp`,
`builder-sysexit-mid-loop-would-commit`, `blackbird-emitter-bypasses-build-atomicity`,
`dmc-open-clear-late-mode`, `common-driver-d418-write-may-ignore-main-vol`

**partial**: `corpus-audit-empty-trace-artifacts`,
`dispatch-confident-answers-uncorroborated`,
`mattgray-locate-declares-one-pattern-on-two-files` (later deduped/closed)

**blocked** (then re-run and closed): `dmc-open-clear-late-mode`

## The substantive engineering

**Set-atomicity for native builds** (`2bdbb71`, `280b6cc`). `DMC_Demo_IV_tune_5`
packed 92 parts, wrote 4, and raised `WAVE overflow: 288 rows > 256` on the 5th —
leaving a 4-part build indistinguishable from a legitimate one. `emit_one` now
stages multi-part artifacts and `prune_stale_parts` commits the set at once.
Follow-ons in the same family:
- `prune_stale_parts` deleted a surplus `.sf2` and left its `.span` — **352
  orphans over 31 DMC songs** (Cant_Stop 96).
- `build_native_song` refused a decode with no notes but not a **trace with no
  frames** — the same failure one layer down. All 108 DMC + Fun_Fun originals
  screened non-empty, so nothing that builds changed.
- The adaptive packer **never probed its base window** — `fits()` is consulted
  only to decide whether to *grow*. That is why tune_5 died: part 5's window was
  never seen, while part 3 (the only one that grew) probed 181 and laid exactly
  181. Fixed in DMC only; **the same shape is measured live in six other builders**.
- `sys.exit(<nonzero>)` raises SystemExit, which never reaches `sys.excepthook`,
  so a mid-loop refusal would have **committed** staged parts.
- Blackbird had its own emitter and gained nothing from any of it; wired to the
  shared machinery rather than given a fourth copy.

**Provenance** (`a1e6f9a`). Every artifact now carries a `.prov` naming the
commit, dirty state, builder and env flags in force. The flag set is **scanned
from source** (73 vars across `bin/` and `sidm2/`), not hand-listed.
`passband_check` prints a census before any number and shouts on mixed or dirty
stamps. `build_provenance()` / `provenance_census()` live in `fidelity_common.py`
beside `part_span`, carrying the same `.sid`-vs-`.sf2` keying subtlety.

**Dispatch** (`8c76e23`, `840f0f5`). `native_dispatch` routes advisorily: over
734 files there are zero signature collisions but **~26 confident answers are
uncorroborated** by player-id, so wiring it as a router would have shipped wrong
SF2s silently. The `sdi` probe claims 20 foreign Shogoon files with **zero
shipped builds**; 4 are provably refused via a voice-count-shape check (0 false
positives on 160 real rips).

**Matt Gray locate** (`e245ff5`). Four-link chain: `n_patterns = pat_hi - pat_lo`
and locate took the *first* adjacent site pair — one byte wide — declaring a
one-pattern song against tracks referencing 22/23. Widest-pair finds the real
tables (`$16a6`/22, `$268f`/23); all 9 working files keep theirs. Then tempo had
to stop claiming the pattern table; then **no free site remains for tempo at
all**. Probe/decode corrected **13/55 → 11/55**.

**Init passband** (`71a7024`). MoN driver zeroed `F_MODE` at init, so every build
opened with `$D418` mode bits OFF. Nine DMC builds opened `off/`, eight audibly
routed. Opt-in `INIT_PASSBAND=1`; all nine go **98.5–99.9% → 100.0%** with
`dChg=0`, measured with `compare()`'s offsets forced to `[0]`.

## Interview (`/runhuman`) — 8 of 9 blockers resolved

`requires-user` went **9 → 1**. Answers are in `.claude/tasks/decisions.jsonl`
(9 lines) and patched into 9 plan records. See `<current_state>`.

Two questions changed shape *before* being asked, which is what the research is
for:
- **`bahbar-v`** was recorded "no original SID". Wrong. `Bahbar.sid` exists and
  scores 100.0%; `Bahbar_v` is a superseded 11-part build (17 Aug) replaced by
  the 30-part `Bahbar_native` (18 Aug), under a `_v` naming **no other song in
  281 uses**. 0 of 11 overlapping parts byte-identical.
- **`roadmap-e1`** wanted VICE patched for per-voice muting. `sidplayfp_wrapper.py`
  **already does it** (`-u<voice>`, exposed as `--audio-export-voices`); its own
  docstring says it replaced SID2WAV as "the voice-isolating renderer". And
  `C:/winvice` holds binaries with no `.c`. That also dissolved half of E2.
</work_completed>

<work_remaining>

## Immediately runnable — the 4 delegable subtasks (all carry a `decision`)

The plan had **zero** delegable tasks for several drains; the interview created
four. All are small, none touches a corpus, so `/runqueue` can finally fan out.

1. **`bahbar-v`** — MOVE (not delete) the 22 `out/sdi/Bahbar_v_native_*` files
   to a quarantine dir. Verify: `passband_check --player sdi` reports no FAILED row.
2. **`short-deel-quarantine-decision`** — no corpus change; write the decision
   into `docs/players/SDI.md` (stays because it is *unexercised*, not failing,
   and is the evidence the 85% onset gate is marginal for the DELTA cluster).
3. **`roadmap-e1-vice-voice-mute`** — rewrite ROADMAP E1 as superseded, naming
   sidplayfp's `-u<voice>` / `--audio-export-voices`. **Keep** the caveat that
   muting is not clean isolation on every tune. Note E2 no longer depends on E1.
4. **`whattask-rule-not-live-in-plugin-cache`** — bump the marketplace
   `plugin.json` 1.9.3 → 1.9.4 so the cache refreshes.

## Main-lane, unblocked by the interview

5. **`release-3-28`** — 114 commits since the 3.27.0 stamp. Bump
   `sidm2/__init__.py` + README, CLAUDE.md, ACCURACY_MATRIX.md, STORY.md +
   CHANGELOG heading. `test_version_stamps_agree.py` pins all five.
6. **`pr5-v3-5-7-decide`** — apply the branch's 5 files, run the suite,
   **re-measure**. The 87%→92% claim is 114 commits stale. **The merge is the
   human's**; the runner must not perform it.
7. **`stale-worktree-decision`** — `git worktree remove` × 12, reclaim 854 MB.
8. **`runs-log-not-durable`** — negate `.gitignore:248` for `runs.jsonl` only;
   `whattask.json`, `interview.json`, `serial.lock`, the pid file stay ignored.

## The largest open engineering item

9. **`packer-base-window-never-probed-in-six-builders`** — measured absent at
   `build_mon:2563`, `build_sdi:289`, `build_hardtrack:260`, `build_fc:162`,
   `build_soundmonitor:390`, `build_mattgray:318`. `needs_main`; its verify
   rebuilds six corpora to prove byte-identity.
10. **`galway-microprose-soccer-renders-a-quarter-loud`** — confirmed defect,
    fix site named, objection already disposed of. Edits
    `drivers_src/common/sf2_native_driver.asm:393`.
11. **`dmc-driver-init-passband-default`** — the adopt A/B for `INIT_PASSBAND`.
    ~200 builds over DMC + HardTrack. `needs_main` (corrected this session).
    **Score with `offsets=[0]`** or the fitted shift masks the defect under test.
12. **`mattgray-tempo-table-unlocatable-on-two-files`** — needs the play routine
    disassembled, **not another heuristic**. Two wrong tempos already measured
    and rejected (129 from `instr_a0`, 21/37 from the arpeggio pointers).

## Still blocked on you

13. **`roadmap-e2-oscilloscope`** — you agreed to install ffmpeg; it is not on
    PATH. Flips to main once `ffmpeg -version` succeeds. Stems half is solved.
</work_remaining>

<attempted_approaches>

## Vacuous checks that reported success — the recurring failure of this session

**A byte-comparison after a crash always says "identical".** Three times a
"BYTE-IDENTICAL: True" was produced by a build that never ran:
1. An escaped-newline error left `build_mon_native_song.py` with an unterminated
   string → crashed at import → artifacts untouched.
2. 64tass has no `defined()`, so `.if !defined(INIT_FMODE)` failed to assemble →
   ASSEMBLE FAILED → artifacts untouched.
3. Same class earlier in the corpus-audit work.
**Only `exit=0` makes a byte comparison evidence.** Check it first, every time.

**A span-vs-trace-length audit that measured its own argument.** Comparing each
one-part artifact's span against `F.per_frame(orig, ['-t', span+15])` produced
"56 of 61 suspicious" — every row reading exactly `15.0s UNCOVERED`, i.e. the
`-t` value. siddump returns the duration *requested*. All 56 flags withdrawn.
The method is structurally dead too: for a one-part adaptive build the span **is**
the decode's song length, so checking it against the decode is circular.

**A test that could not fail.** The Blackbird staging test asserted only that
the staging lines *exist in the source*; it passed against `if False:` wrapped
around them. A source scan matches unreachable code. Now pins the branch.

**Two injection-harness errors.**
- `runpy.run_path` **re-executes** the module, so patching the already-imported
  copy has no effect — the injection must target something the re-executed
  module *imports*.
- Catching the injected exception in the probe means it never reaches
  `sys.excepthook`, so `_UNWOUND` stays False and atexit **commits**. Run the
  failure as a subprocess with the exception unhandled.

**Three refuted corroboration designs for the dispatcher** (do not re-derive):
1. Promote a construct-only family on a reliable player-id verdict — precision
   fell 75.0 → 71.4.
2. Demote on a contradicting player-id verdict — the needed verdict (`DMC`) is
   not in `RELIABLE_PLAYER_IDS`, which was itself built from measurement.
3. Decode plausibility — the SDI decoder walks garbage happily; false accepts
   produce **more** notes than real rips (median 1471).
What worked was **shape**: 0 of 160 real rips have three voice counts within 2%
of each other; 4 of the 20 false accepts do.

**Two tempo values measured and rejected** for Pogo/Warriors: 129 (read out of
`instr_a0`) and 21/37 (the arpeggio pointer table's high byte). Either would put
every note at the wrong time while the decode still looked fine.

**Nearly named the wrong driver file.** `drivers_src/romuzak/romuzak_driver.asm`
has no `$D418` handling and the common driver does — but the romuzak one is a
shim that `.include`s the common body, while MoN/DMC repoint the assembler at
`drivers_src/mon` and assemble their **own unmerged copy**. Checking which file
is actually assembled changed the answer.

## Lock-protocol defect found and fixed

Claiming two lanes in two separate python processes recorded a pid that died
immediately, so the next claim's orphan-reap correctly dropped the first record.
**The reap rule is right**; recording a short-lived pid is wrong. Now claims both
lanes in one write against a session pid persisted in
`.claude/tasks/.runqueue_session_pid` — and that pid must be a **live long-lived
process** (`claude.exe`, found by walking the parent chain), not the helper's.
</attempted_approaches>

<critical_context>

## Non-obvious mechanics

- **`emit_one` is shared by EIGHT players** — DMC, MoN, Sound Monitor, FC,
  HardTrack, SDI, Hubbard, Matt Gray. Any unconditional change there moves every
  corpus at once. This is why `INIT_PASSBAND` is opt-in.
- **The 4-byte problem**: emitting `lda #$00 / sta F_MODE` unconditionally adds 4
  bytes and shifts every address after it, moving all eight players' artifacts
  even at a zero value. Hence: always emit the constant (64tass needs the symbol
  to test it), guard the instructions with `.if INIT_FMODE != 0`.
- **`compare()`'s fitted offset masks late-declaration defects.** At default
  `OFFSETS` the nine DMC builds all read 100.0. Force `offsets=[0]` to see them.
- **`passband_check` writes a scratch probe** (`out/dmc/_passband_probe.sid`) —
  declare it in `touches` even for a read-only task.
- **Blackbird writes no `.span` at all**, so its prune's span glob is dead code,
  not a live bug. Its corpus is scored against the **simulator**; siddump cannot
  drive an LFT rip.
- **`core.autocrlf=true`**: writing files through Python text mode converts LF→CRLF
  and inflates them on disk (CLAUDE.md +231 bytes). Git normalises on staging so
  the diff is clean, but CLAUDE.md is measured in **bytes** because it loads every
  session — convert back to LF.

## Process rules that were earned the hard way

- **An undeclared path is a STOP, not a grant.** `dmc-open-clear-late-mode` was
  recorded `blocked` for this and re-run after `/whattask` corrected `touches`.
  That is the intended cycle, not a failure.
- **The runners never commit, merge, or push.** Every commit this session was
  the user's explicit instruction.
- **`/whattask` must fold forward the previous plan's `closed` array**, not just
  `runs.jsonl` — without it, 15 already-closed ids resurrect each pass.
- **The step-5b touches rules are NOT live.** They exist only in the marketplace
  copy; all 11 cached plugin versions lack them, and four `/whattask` runs
  executed the old text. Applied by hand each pass. Task #4 above fixes this.

## Corpus hygiene

- `out/dmc` was left **coherent**: measuring the passband fix required building 9
  songs with `INIT_PASSBAND=1`, which stamped them; all 9 were rebuilt at defaults
  afterwards. Census reads 12 at `280b6cc` with no flags, 62 UNSTAMPED.
- Existing artifacts stay UNSTAMPED deliberately — backfilling a `.prov` would
  invent the fact the sidecar exists to record.
</critical_context>

<current_state>

**HEAD `71a7024`, working tree clean, master in sync with origin (0/0).**
Suite green at **2600 passed / 8 skipped / 2 xfailed**. Nothing uncommitted.

**Plan**: `.claude/tasks/whattask.json` at `71a7024`, **41 tasks, 43 closed**.
Modes after the interview: **4 subtask / 36 main / 1 requires-user**.

**Run log**: `.claude/tasks/runs.jsonl`, 100 records. **Still gitignored** —
task #8 above changes that. It is the only evidence behind ~12 commit messages
and exists on this machine only.

**Decisions**: `.claude/tasks/decisions.jsonl`, 9 lines, 8 resolved. This file
**outranks the plan** and survives regeneration — `/whattask` step 2c reads it,
so none of these questions should ever be asked again.

**Research cache**: `.claude/tasks/interview.json`, 9 blockers, questions only.
Safe to delete; costs only the re-research.

**Open question, none.** Everything asked was answered except ffmpeg, which is
an action on your side rather than a decision.

**Recommended next**: `/runqueue` — the four delegable subtasks can fan out
while a main task runs beside them, which has not been possible for several
drains. If you would rather clear the ledger first, `release-3-28` and
`stale-worktree-decision` are both authorised and independent.
</current_state>
