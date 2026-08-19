# Handoff — SIDM2 session, 2026-08-17/18

<original_task>
Continued the `/whattask` → `/runtask` loop. The user drove it with **"next"**
repeatedly, plus **"push and commit"**, **"do 1"**, **"run phase 2 again"**,
**"delete them once verified"**, and — five times — **"can we work on something
else while it's running"**, which shaped the whole session: every task had to be
chosen for whether it could run *beside* a live corpus rebuild.
</original_task>

<work_completed>

**10 commits**, `76c0132..b3d5a40`, all pushed. Suite **2,482 passed**.
`.claude/tasks/runs.jsonl` holds **37 records / 27 distinct ids** — 23 done,
3 partial, 1 inconclusive (gitignored; see *Blocked on you*).

## The through-line: five things were measured and four of them were refuted

This session produced almost no new fidelity. What it produced is a list of
claims that turned out not to survive contact with a measurement — **two of
them my own, written earlier the same day.**

| claim | verdict |
|---|---|
| `DMC_Demo_IV_tune_5`'s 98.0%/10-audible/3-mode-change | **not reproducible at any window**, and its three components are mutually exclusive |
| DMC's 31-timing / 18-content split | **superseded** — 12 / 7 / 22 on the current corpus |
| Myth sub0 part-1 filter 77% | **does not reproduce** — cutoff is 100.0% over n=1000 |
| `Altered_States` 47-frame "startup latency" | **not a latency** — the original declares its passband before it routes |
| A4: route on `player-id` strings | **refuted** — verdicts are many-to-many with the builders |
| A4 redesign: route on each parser's own locate *(mine, same day)* | **also refuted** — `dmc` and `mon` accept all 48 files |
| "every build opens on `$D418` off" *(mine, same day)* | **refuted** — 2 of 33, not 33 of 33 |

## Numbers that moved

| | |
|---|---|
| SDI passband, **control** (rebuilt at HEAD, flags OFF) | **268/281** — above the 267 baseline |
| DMC tolerance split | TIMING **12** / PARTIAL **7** / CONTENT **22** |
| Myth sub0 part 1 cutoff | **100.0%** over n=1000, 832 changes, 97 distinct values |
| `out/dmc` artifacts | 1241 → **1075** (332 stale files removed) |
| SDI sweep | gained `--jobs`; ~11 h → ~1 h |

</work_completed>

<attempted_approaches>

## Traps worth carrying

- **A "killed" background job is not dead.** Twice the notification fired and
  the driver tree kept running — once completing phase 1 and walking into
  phase 2 with the flags ON while a replacement run built the flags-OFF control
  into the same `out/sdi`. Both runs were void. **Check the process list, never
  the notification.** A PID file and an EXIT/TERM trap did *not* prevent it.
- **A green check written in the same command that runs it is not a check.** I
  composed a run record claiming `test_player_index.py passes` and ran the test
  in the same shell call; it failed (1 of 11). Run first, then write.
- **A probe bug must not be catchable as a verdict.** `is_soundmonitor(data,
  la, h)` called with two arguments raised `TypeError`, a broad `except
  Exception` recorded it as "not a Sound Monitor rip", and the family silently
  rejected its own corpus while the run looked clean.
- **Editing a script a running `bash` is executing** can resume mid-line — bash
  reads by byte offset. I did it once and reverted to byte-identical content.
  Same rule as PATTERNS F2 for Python modules a live build imports.
- **A second scorer must reproduce the first at zero tolerance**, or it is a
  different scorer. A raw-equality `freq` comparison scored `Roadblaster` v2 at
  58.2 where the sweep says 96.9 — `score_pair` compares freq by **semitone**.
- **Sample spread across a corpus, not the first N.** One file per directory
  gave a clean-looking player-id map; sampling evenly exposed the collisions
  that refuted A4. `Tel_Jeroen`'s first file alphabetically reports
  `Rob_Hubbard`.
- **Vacuous 100%s hide in filter columns.** Myth's `$D417` and `$D418` both
  read 100.0% and both are constant on *both* sides — `exercised()` False.
  Only the cutoff row was evidence.
- **A refused build can still emit.** `DMC_Demo_IV_tune_5`'s stale artifacts
  were 0.1 h old — the verification build had just rewritten them before
  failing at a later part. Deleting stale output buys exactly one clean run.
- **Oversubscribing the host is a real failure mode.** Running a 2,482-test
  suite, a py65 capture and a 66-run siddump sweep beside a `-j16` build caused
  3 process-launch failures and aborted phase 2 at 264/441. The `--infra-abort`
  guard behaved correctly; the operator did not.

</attempted_approaches>

<critical_context>

- **The runner's lane gate is now a RESOURCE gate.** `lane` is a hint;
  contention is computed from `touches`, tagged `r:` / `rw:`. Readers conflict
  with writers, a tool's scratch file is a write you did not author,
  `serial.lock` is a JSON **array** keyed on paths, and the gate also checks
  `out/.mon_build.lock` and mtimes for writers that never registered.
  `~/.claude/lib/runtask_gate_check.py` and `whattask_lane_check.py` implement
  the rules and were run against live state.
- **`/whattask` now DERIVES the lane** from `touches` instead of asserting it,
  with a floor: anything `needs_main` for a stateful singleton is serial.
- Rebuild scripts: `pyscript/dmc_native_sweep.py --build -j16`,
  `pyscript/sdi_native_sweep.py -j8`, `pyscript/hardtrack_native_rebuild.py`
  (still serial). New: `pyscript/dmc_tolerance_sweep.py` (PATTERNS D10),
  `sidm2/native_dispatch.py` (**inert** — nothing imports it).

</critical_context>

<current_state>

Version **3.27.0 unchanged — 80 commits behind a stamp.**

## In flight

**`sdi-filter-between-note-automation`**, phase 2 of 2, holding the serial lock.
Phase 1 (control, flags OFF) is **done and must not be redone**: 268/281,
254 built / 62 refused / 125 errored, 3,111 parts — in `sdi_ctl.json` and
`parts_ctl.json`. Phase 2 is a rerun at `-j8` after the first attempt aborted.
⚠️ The 1b snapshot **failed silently-ish** (`robocopy rc=16`, 0 files), so the
control corpus on disk is gone and only its JSON survives.

## Open, ranked

1. **`filt-flags-adopt-as-default`** — blocked on the above. Watch **part
   counts**, not just fidelity: `FILT_EXACT_PB` is strictly stricter.
2. **`builder-emits-then-refuses`** — a refused build leaves partial artifacts,
   so stale output regenerates itself. The durable fix behind the cleanup.
3. **`dispatch-rank-by-evidence`** — A4's third shape: rank by evidence
   strength, never boolean accept. Do **not** re-try either refuted premise.
4. **`dmc-init-passband-claim-unmeasured`** — settle DMC's "every build opens
   on off" the way HardTrack's twin was settled. `dmc-driver-init-passband-default`
   now depends on it.
5. `dmc-part-split-nondeterministic`, `dmc-two-voices-disagree-with-sweep`
   (208 of 210 voices agree; the 2 that don't are signal),
   `mon-artifacts-lack-span-sidecar`, `hardtrack-rebuild-jobs`.

## Blocked on you

`release-3-28` (80 commits) · `runs-log-not-durable` (**37 records exist only on
this machine**) · `bahbar-v` (no original SID) · `roadmap-e1` (your WinVICE
toolchain) · `roadmap-e2` (ffmpeg).

</current_state>
