# Handoff — SIDM2 session, 2026-08-16

<original_task>
Opened with **"read what next"**, then a `/whattask` → `/runtask` loop the user
drove with **"next"** repeatedly, plus **"push"**, **"commit this"**, and one
pivotal aside: **"i have 24 cores so we should be able to run things in
parallel"**. Two slash commands (`/whattask`, `/runtask`) were authored during
the session and then used to run it.
</original_task>

<work_completed>

**10 commits**, `afd2f63..c30a2fc`, all pushed. Suite ~2,480. 13 tasks closed,
1 partial, recorded in `.claude/tasks/runs.jsonl` (gitignored, 17 records).

## The through-line

The session's stated task was the `$40-$43` marker. Most of its value came from
what parallelising the verification exposed: **four independent races**, and —
worse — **four checks that passed while the thing they guarded was broken.**

| the check | why it passed anyway |
|---|---|
| `SCORES IDENTICAL` over 5 corrupted artifacts | it scores **part 1 only**; every corrupted file was part 2+ |
| a byte-compare of 71 artifacts, clean | the **scorer** was racing, not the builds |
| a serial-vs-parallel baseline | the baseline was built **before the code under test** |
| `207 vs 210 voices` | true, but it measured a **lock race**, not a build difference |

None was a wrong number. Each was a right number answering a question nobody
had asked.

## Commit by commit

| commit | what |
|---|---|
| `afd2f63` `0c3aadc` `ded4270` `b905f97` | (carried from 08-15) DMC timing fixes, corpus rebuild, `Tanks_3000` 94.9 → 100.0 |
| `e731046` | the `$40-$43` collision is per **SONG**, not per player — `Balloon` 123,180 hits, `Depeche_Mode_Songs` **0** |
| `00893cd` | `passband_check`'s offset fit maximised the **rate**, so a shift bought agreement by discarding frames. Now maximises **count**, then completeness |
| `4d44f00` | `_fm_would_collide` — decided per song **before** the emit pass, staged behind `FM_SCALE_AUTO` |
| `4d01910` | parallel corpus builds. **F2 is three shared files, not one.** 3.5 h → 14 min at `-j16` |
| `3ffdadb` | the scorer's probe was ONE shared file — `-j16` scored songs against **other songs' audio** |
| `722bcaf` | audited every sweep for the same shape: **no other sweep races**; one latent case fixed |
| `6ab60f3` | the lock escaped a Windows `PermissionError` and silently lost one song per corpus run |
| `6e5daf9` | the per-song rule **adopted as default**; `no_fm_scale` deleted from all three shims |
| `20c506e` | **PATTERNS F12** — and the old rule was folklore citing the wrong entry |
| `c30a2fc` | every `$D418` figure re-measured rather than adjusted; SDI **258 → 267 of 281** |

## Where the numbers landed

| | |
|---|---|
| DMC raw medians (freq/wf/pul) | **99.5 / 99.9 / 99.9**, audible **100.0 ×3** |
| DMC / SDI / HardTrack passband | **53/74** · **267/281** · **32/33** |
| DMC corpus rebuild | **3.5 h → 14 min** (`-j16`) |
| Hubbard under the new rule | **byte-identical** (predicted in advance, confirmed twice) |

</work_completed>

<attempted_approaches>

## Retracted — three, all mine

1. **"AUTO regresses DMC to 96.3"** and **"the default control is 96.4"** —
   both came from the raced scorer. **The regression never existed.**
2. **"The lock is correct by construction"** — asserted, then falsified by the
   next test. Two more shared files were still open.
3. **"PATTERNS F2 says builders share `layout.inc`"** — F2 says no such thing.
   Inherited from the old handoff and propagated into two commit messages
   before being caught.

## Traps worth carrying

- **A shifting set of differing artifacts means a race. A stable set does
  not** — it means a real difference, or a baseline built with other code.
  That one distinction separated the real races from two false trails.
- **Builds and scoring fail independently.** Compare artifacts *and* scores; a
  byte-compare cannot see a defect in the scorer that reads them.
- **Change one variable.** Three of the four false trails were two-variable
  comparisons: serial+no-isolate vs parallel+isolate, batch vs alone, and old
  code vs new.
- **A stale artifact's mtime gives it away** where its filename does not — a
  "failed" smoke test was a file from the previous day.
- **Windows**: a lock file pending deletion answers `O_CREAT|O_EXCL` with
  `ERROR_ACCESS_DENIED`, not "exists". Catch both.
- **For HardTrack, `audible` is the STRICTER column** — opposite to DMC, whose
  raw is depressed by rest frames. Do not read the two the same way.
- **A subagent's silence is not evidence its work is absent.** One returned
  "I'll wait for the background build" after 112k tokens; the work was in the
  tree. Check the tree.

</attempted_approaches>

<critical_context>

- **Corpus builders may now run CONCURRENTLY.** `--jobs N` (DMC sweep only so
  far) takes a cross-process lock; see `PATTERNS.md` **F12** for the four
  shared surfaces and why isolation was rejected in favour of a lock.
- **`.claude/tasks/`** holds the plan (`whattask.json`) and the append-only run
  log (`runs.jsonl`). **Both are gitignored** — every finding above that is not
  in a commit message lives only there.
- `/whattask` regenerates the plan and folds the run log back in; `/runtask`
  runs ONE task with its dependency/mode/lane gates enforced. Outcomes are
  `done | partial | failed | inconclusive | blocked` — `partial` means resume,
  not restart.
- Rebuild scripts: `pyscript/dmc_native_sweep.py --build -j16`,
  `pyscript/hardtrack_native_rebuild.py` (still serial, ~19 min),
  `bin/build_sdi_native_song.py`.

</critical_context>

<current_state>

Suite ~2,480, version **3.27.0 unchanged — 69 commits behind a stamp**.

**Open work, ranked:**

1. **`release-3-28`.** *Requires user.* 69 commits since v3.27.0.
   `pyscript/test_version_stamps_agree.py` makes the mechanics safe once you
   decide.
2. **`sdi-filter-between-note-automation`.** *Opus, main, PARTIAL — resume.*
   Mechanism is measured, not hypothesised: `detect_filter_drives:756` credits
   an attack to an onset only when `-1 <= (f - onset) <= 4`. `Arabia`'s attack
   at frame 688 sits in a **71-frame gap** between onsets 637 and 708 and is
   dropped; `Funk_Facet`'s is 1 frame out and merely late. Fix needs **no
   driver change** — widen the upper bound so the attack maps to the preceding
   onset, and `filter_program_for`'s capture supplies the hold. ⚠️ Shared by
   **six players**; verify against BOTH files and watch for attacks credited to
   the wrong note.
3. **`dmc-part-split-nondeterministic`.** *Opus.* 5 of 88 songs take different
   part splits between runs, in **both directions**, pre-existing. Aggregate
   stats are stable but the corpus is **not reproducible at the artifact
   level** — which limits every byte-compare gate, including this session's.
4. **`hardtrack-rebuild-jobs`** — still serial at ~19 min; the DMC sweep is a
   working template. *Sonnet, subtask.*
5. **`dmc-driver-init-passband-default`** (no `$D418` at INIT; `Soap_Theme`'s
   19 frames), **`hardtrack-voice1-early-noteon`** (needs RetroDebugger),
   **`sweep-no-progress-at-j`** (a `-j16` run prints nothing for 14 min).

**Blocked on the user:** `bahbar-v` (no original SID — the tool agrees),
`roadmap-e1-vice-voice-mute` (your siddetector WinVICE toolchain),
`roadmap-e2-oscilloscope` (ffmpeg not installed).

**Closed this session:** the `$40-$43` arc end to end, four passband
diagnoses (`Soap_Theme`, `Arabia`, `Funk_Facet`, `Fun_Factory` — all now with
named causes), the DMC content re-derivation, the 21 unexercised windows, the
sweep-probe audit, and the offset-fit defect underneath all of it.

</current_state>
