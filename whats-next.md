<original_task>
Continuation session picking up from the prior handoff (`69c806f`, "whats-next:
session handoff (sidplayfp, the fidelity harness, R17, $D418)"). No new feature
was requested; the ask was open-ended — "what next" — and the session worked
through that prior handoff's ranked `<work_remaining>` list item by item, in
the order the assistant proposed and the user confirmed at each step:

  1. Cybernoid_II's "register-exact yet only 71-85% onset-matched" finding
     (originally read as a synthesis divergence, the most interesting open
     thread in the prior handoff).
  2. Supremacy `adsr` 2.3%/4.5% on osc2/osc3.
  3. Pulse scored as per-frame equality (h2g's measured finding).
  4. (new, raised mid-session) The shared native-driver engine carrying the
     same `$D418` bug just fixed in MoN's own copy.
  5. (new, raised mid-session) Two scorer judgement calls flagged for the user.
  6. (new, raised mid-session) Re-reading existing per-voice audio claims
     against the new repeatability floor.
  7. (new, raised mid-session) Hygiene: a suspected masking-order bug in
     `mon_parser.py`, plus this handoff doc's own staleness.

At the very end of the session the user said "go on" with no further
specifics; the assistant used that latitude to (a) regenerate this handoff
doc via the `taches-cc-resources:whats-next` skill (this document) and
(b) had begun scoping — but not yet executing — the next unblocked item
(wiring per-tune `MAIN_VOL` into ROMUZAK/Galway's own builders). See
`<work_remaining>` #1.
</original_task>

<work_completed>

## 1. Cybernoid_II "synthesis divergence" — investigated, then FALSIFIED, then the tool itself was fixed

**Sub-session A** (forked subagent "yes, start with Cybernoid_II"): reproduced
the prior handoff's finding (registers 100/100/100, audio 71-85%, tool printed
SYNTHESIS on all three voices), then falsified it. Full siddump diff over 350
frames showed only 6 differing lines, all in frames 0-2, all one root cause
(see item 2 below). Perturbing `sidplayfp --delay` on the ORIGINAL ALONE (note
data untouched) reproduced the same 71-85% band purely from free-running SID
phase. Concluded (at the time) that phase alone explained it.

**The assistant's own follow-up investigation went one level deeper** and
found the sub-agent's causal story was still incomplete. Directly measured:

- Three `sidplayfp --delay=0` renders of ONE file are the same signal to
  within `r = 1.0000`, `rms(diff)/rms ~ 0.001` (verified via cross-correlation
  in a scratch script, not assumed).
- On the FULL MIX the onset detector is unmoved by that dither: 38/38 onsets,
  100% match across all six pairings of three renders.
- On a VOICE-ISOLATED render (`-u1 -u2` etc.) the SAME inaudible dither moves
  the onset count 101/88/98 and the pairwise match rate across **84.2-96.9%**
  — muting two voices leaves a large population of onsets sitting on the
  detector's threshold edge. This is METRIC NOISE, not phase, and it was
  previously unmeasured by anything in the repo.

**Shipped in commit `72fb2ae`** ("fidelity: the cross-tab called SYNTHESIS on
noise it had never measured"): `pyscript/audio_tightness_tool.py` gained:
- `REPEAT_FLOOR_SAMPLES = 9` (raised from an initial, too-weak default of 3 —
  the false-positive rate of "worse than every self-sample" is a rank-test
  `1/(N+1)`; 3 gives 25%, 9 gives 10%).
- `repeat_floor_delays(n)` — deterministic delays, the FIRST always 0 (a plain
  replicate, isolating metric noise), the rest even divisions of one PAL frame
  (`PAL_CYCLES_PER_FRAME = PAL_CYCLES_PER_SEC // 50`), so runs are reproducible.
- `measure_repeatability_floor()` — renders the ORIGINAL N extra times per
  voice and runs the same onset comparison the driver rows use.
- `floor_of(samples)` / `effective_floor(samples)` — the floor is a MINIMUM
  over noisy point estimates, so it is widened by the measured replicate
  shortfall (`1 - min(replicate)`) before being compared against. This was
  added after observing the verdict FLIP between two consecutive identical
  runs (voice 3: 85% vs a 77% floor on run 1, 70% vs a 71% floor on run 2) —
  the margin can only ever decline to claim a defect, never invent one
  (pinned by `test_widening_only_ever_declines_to_claim_a_defect`).
- `diagnose()` gained a fourth CLI-visible outcome, `INCONCLUSIVE`, for the
  case `reg_ok and audio inside the widened floor`.
- New CLI flag `--repeat-floor N` (default 9; `0` disables and reverts to the
  old unconditional SYNTHESIS text, which now says explicitly that it is
  uncalibrated).
- New test file `pyscript/test_audio_tightness_repeat_floor.py` (27 tests,
  all verified to FAIL against the pre-fix `diagnose()` loaded standalone via
  `git show HEAD:...`).
- `docs/players/PATTERNS.md` gained entry **F5b**: "`f(x, x)` is necessary
  but NOT sufficient — re-render, then compare." Comparing a WAV against the
  SAME WAV (the usual F5 check) is exact by construction and proves nothing
  about the pipeline; the real test is `f(x, x')` where `x'` is RE-rendered.
- `docs/players/MON.md` gained a "Cybernoid_II synthesis divergence —
  FALSIFIED" section with the full numeric story.
- `CLAUDE.md`'s MoN row updated with the falsification + the fix pointer.

Full suite after this commit: 1887 passed, 7 skipped, 2 xfailed.

**Re-running the sweep after this fix** (`audio-tightness.bat
SID/Tel_Jeroen/Cybernoid_II.sid out/mon/Cybernoid_II_sub0_part01.sf2
--driver-init 0x1000 --driver-play 0x1003 --voice all --seconds 12 --no-html`)
now returns INCONCLUSIVE on all three voices, reproducibly across repeated
runs (unlike the pre-floor tool, which flipped its own verdict run to run).

## 2. The one real defect the falsification surfaced: MoN's `$D418` one-frame lag

While diagnosing Cybernoid_II, the 6 differing siddump lines (frames 0-2) were
traced to a single root cause: `do_play` in
`drivers_src/mon/romuzak_driver.asm` wrote the `$D418` volume/mode byte at the
TOP of the frame, before `filt_prog_step` (called later, after `do_row`) had
produced that frame's `F_MODE`. So every `$D418` write carried the PREVIOUS
frame's passband. The cutoff (`$D415/$D416`) never had this bug because
`fp_apply` (inside `filt_prog_step`) stores those registers itself — which is
exactly why the lag only ever showed up on `$D418`. Cybernoid_II's original
opens `$1F, $3F, $3F...` (vol 15 + low-pass, then +bandpass); the pre-fix
driver emitted `$0F, $1F, $3F...`.

**Shipped in commit `7bb89d7`** ("fix: MoN's $D418 published the PREVIOUS
frame's passband"): moved the `SID_VOL` write (and the `DIGI_SPIKE`-guarded
block around it) from the top of `do_play` to just after the multispeed loop,
after `filt_prog_step`/`pulse_step`/`wave_step`/`fm_step` have all run — the
same ordering rationale the code already documented at `dp_vib` for why
`filt_prog_step` runs after `do_row` ("else the cutoff/pulse sweep lags one
frame"). `digi_stream` still runs last, so digi keeps the final word on
`$D418`; `DIGI_SPIKE` is off for every MoN build regardless.

Verified by full rebuild + re-measurement, not by inspection:
| tune | before | after |
|---|---|---|
| Cybernoid_II `$D418` | 99.7% | **0 of 350 differing frames** |
| Hawkeye sub0/sub2/sub3 | — | unchanged (100/100/100, cutoff 100) |
| Cybernoid sub0 | — | unchanged (osc3 freq 95.0% — see below) |
| Supremacy sub0 | — | unchanged |

Two things double-checked rather than assumed:
- **Cybernoid osc3 freq 95.0% is PRE-EXISTING**, not caused by this change —
  confirmed by rebuilding Cybernoid against HEAD's (pre-fix) driver and
  re-measuring: identical 95.0%.
- **Hawkeye sub3 first read 75.5% cutoff** because it was measured over a
  16-second window when the part is only ~2 seconds long — the exact
  "phantom tail past the loop point" trap `mon_part_fidelity.py`'s own
  comments warn about. Re-measured at the correct 2-second window: 100/100/100,
  cutoff 100.

**Also fixed docs**: `mon_part_fidelity.py` now reports Cybernoid_II's
`$D418` as `n/a` (constant + identical) rather than `100%`, because its
measurement window excludes the opening frames where the (now-fixed) defect
lived — worth remembering: this register was wrong exactly where the harness
does not look, which is why it only ever showed up as "0.3%" via the
different, wider-windowed `--voice all` sweep.

Full suite after this commit: 1887 passed, 7 skipped, 2 xfailed.
Build-regenerated `.inc` files (`drivers_src/mon/freqtable.inc`,
`drivers_src/mon/layout.inc`, `drivers_src/romuzak/layout.inc`) were reverted
BY NAME after every rebuild in this session, never via a tree-wide checkout
(a prior-session incident, recorded in the prior handoff, destroyed a real
source change that way).

## 3. Myth build failure — investigated, found to be user/invocation error, not a defect

Running the generic `bin/build_mon_native_song.py SID/Tel_Jeroen/Myth.sid 0
auto` refused with "implausible speed byte 255... Refusing to build." Traced
to: Myth is a RELOCATING COMPILATION (init copies a per-subtune sub-player to
`$9000/$A400` and runs it there behind a `play=$0000` self-IRQ wrapper), so it
requires `bin/build_myth_native_song.py` (py65 relocate + init + per-frame
extraction), NOT the generic MoN builder — `docs/players/MON.md:55` already
documented this, but `CLAUDE.md`'s accuracy table did not, which is where the
wrong command got picked.

Confirmed NOT a regression: the pre-`0ef5fab` parser refuses the generic
build identically. Rebuilt through the correct builder
(`py -3 bin/build_myth_native_song.py 0 auto`) on the current (post-`7bb89d7`)
driver: 8 adaptive parts as previously documented, part01 measures
**100/100/100 on all three voices, cutoff 100.0% (n=673)**.

**Shipped in commit `de82511`** ("docs: name Myth's builder where the wrong
one gets reached for"): `CLAUDE.md`'s MoN accuracy-table row now names the
correct builder explicitly.

## 4. Four items dispatched to parallel forks ("do 1" / "do 2" / "do 3" / "do 4"), then a working-tree collision reconciled

The user forked four subtasks to run concurrently against the SAME working
directory (`/subtask do 1..4`). All four completed correctly on their own
terms, but one fork's `git add -A` swept up the OTHER THREE forks'
still-uncommitted, in-progress edits into its own commit (`5a3ee7e`), whose
message described only its own (docs) change. A second commit
(`badacb7`, a regression test) also landed separately, split from its own
source-file fix which had already been swept into `5a3ee7e`.

**Fork "do 1" — extend the `$D418` fix to the shared engine.**
`drivers_src/common/sf2_native_driver.asm` (the engine shared by ROMUZAK and
Galway, per `drivers_src/romuzak/romuzak_driver.asm`'s and
`drivers_src/galway/galway_driver.asm`'s own header comments — both are thin
feature-selection stubs over this one file) had the IDENTICAL bug: `sta
SID_VOL` before `jsr filt_prog_step`. Applied the same reordering. Validated:
Galway (`Wizball`) rebuilds clean, `SONG AUDIO OK`, unchanged. ROMUZAK
(`Delirious_9_tune_1`, `Road_of_Excess_end`) both still read `AUDIO MISMATCH`
— confirmed PRE-EXISTING via `git stash` A/B against the prior driver
(identical mismatch before this change; root cause not investigated, out of
scope for this fork). Also noted: the engine still hardcodes `ora #$0f` where
MoN's own copy (already) takes `MAIN_VOL` — NOT fixed by this fork, flagged as
separate, larger plumbing work. **See `<work_remaining>` #1 — the assistant
began scoping this at the very end of the session (see `<critical_context>`
for what was found).**

**Fork "do 2" — the best-lag readout (one of two scorer decisions flagged
after `65e85ac`).** Added a DIAGNOSTIC-ONLY best-lag search (±8 frames,
`_lag_pct`) to `bin/mon_part_fidelity.py`, printed beside the existing
shape-agreement line only when it beats the strict score by >5 percentage
points. Deliberately never touches `ok`/`tot`/`pct` — no published corpus
number moves. Verified against the motivating case: Hubbard `5_Title_Tunes`
osc3 now prints `pul best lag: -3 frames beyond vdly -> 90.5%` beside its
unchanged strict `4.5%`. Confirmed silent (no new output) on
Hawkeye/Cybernoid_II/Myth's byte-exact parts. The SECOND scorer decision from
that pair — realigning `vdly` itself independently per-register rather than
just reading out a diagnostic — was explicitly declined by this fork: it
would move every published freq/wf/pul percentage in the corpus and needs the
user's sign-off first. **Still undecided — see `<work_remaining>` #2.**

**Fork "do 3" — re-read existing per-voice audio claims against the new
repeatability floor.** Found and fixed the only stale claim:
`docs/guides/AUDIO_TIGHTNESS_GUIDE.md` §3 carried the PRE-floor Cybernoid_II
cross-tab example verbatim (85/71/75% audio, unconditional "SYNTHESIS" on all
three voices, no repeat/floor columns — didn't even match the current tool's
output format). Confirmed via `git log -S "voice all"` on tracked docs that
this is the ONLY doc that ever used this tool's `--voice all` sweep output —
Deenen/DMC/etc. per-voice claims go through their own bespoke validators
(`bin/deenen_sf2_validate.py` and siblings), unaffected. Regenerated the
example against the current build + current tool: all three voices now read
INCONCLUSIVE. Rewrote the surrounding partition-outcome table to add
INCONCLUSIVE and the `--repeat-floor 0` escape hatch.

**Fork "do 4" — the masking-order hygiene item + `whats-next.md` staleness.**
Left `whats-next.md` alone (correctly — concurrent forks were rewriting the
exact ground it covers; editing it mid-flight would have gone stale
immediately. This regeneration, right now, is the deferred follow-through).
Disassembled BOTH suspected sites in `sidm2/mon_parser.py` before touching
anything (per project rule: verify against source, not inference) and found
the earlier claim (from a PRIOR session's `do 3` fork, notified mid-session
here) was HALF WRONG:
- **Line 855** (Hawkeye's general `$Cx` dispatch): disassembled Hawkeye at
  `$7CBA-$7CCA` — `AND #$1F` then `ADC`, no final mask. Already correct.
  Left unchanged.
- **Line 939/947** (`_pattern_supremacy`, Supremacy's OWN pattern processor,
  not shared code): disassembled Supremacy at `$1263-$126D` — `CMP #$C0/BCC`,
  then `CLC/ADC $100D,X/AND #$1F` — the mask is AFTER the add. The parser had
  it backwards. Fixed.
Rebuilt Supremacy sub0 before/after: byte-identical fidelity numbers,
confirming this is unexercised by the current corpus (max instrument+base
stays under 31 there) — correctness for future/other files, not a fix to any
shipped output. New test drives the real `_pattern_supremacy` dispatcher
through a synthetic byte stream (not just the arithmetic in isolation),
verified to fail against the pre-fix code.

**Reconciling the working-tree collision.** All four forks reported clean
completion with a clean working tree (`git status --short` empty). Verified
via `git show --stat 5a3ee7e` that it touched 4 unrelated files
(`bin/mon_part_fidelity.py`, `docs/guides/AUDIO_TIGHTNESS_GUIDE.md`,
`drivers_src/common/sf2_native_driver.asm`, `sidm2/mon_parser.py`) under a
docs-only message, and `badacb7` held only the split-off test file. Recorded
SHA-256 hashes of all 5 affected files BEFORE touching history, ran
`git reset --mixed de82511` (moves HEAD + index back to the commit before
`5a3ee7e`, leaves the WORKING TREE untouched — purely a bookkeeping
operation, no content at risk), re-verified all 5 file hashes were BYTE-
IDENTICAL after the reset, then re-committed in four properly-scoped, properly
-attributed commits:
- `7b1006a` — shared-engine `$D418` fix (do 1's content)
- `b3a67ea` — best-lag diagnostic readout (do 2's content)
- `3eb8ce2` — Supremacy masking fix + its own test, combined (do 4's content,
  merging what had been split across `5a3ee7e` and `badacb7`)
- `f705c4a` — the audio-tightness guide update (do 3's content)
Final verification: all 5 file hashes re-checked byte-identical to the
pre-split state, and the FULL SUITE re-run once more on the final assembled
tree: **1888 passed** (up one — the new masking-order test — from the 1887
seen after `72fb2ae`/`7bb89d7`), 7 skipped, 2 xfailed.

## Summary of commits this session (chronological, all present at HEAD)
```
0ef5fab  fix: Supremacy's orderlist instrument-base byte was skipped as an inert modifier
65e85ac  fidelity: a swept register's pulse% was measuring phase, not the engine
72fb2ae  fidelity: the cross-tab called SYNTHESIS on noise it had never measured
7bb89d7  fix: MoN's $D418 published the PREVIOUS frame's passband
de82511  docs: name Myth's builder where the wrong one gets reached for
7b1006a  fix: extend the $D418 frame-lag fix to the shared native driver engine
b3a67ea  diag: best-lag readout for mon_part_fidelity's pulse column
3eb8ce2  fix: Supremacy's pattern processor masked before adding the instrument base
f705c4a  docs: the audio-tightness guide's worked example still said SYNTHESIS
```
`HEAD` = `f705c4a6da3425a6be3db0bdbdb98b9af750a9ef`. Working tree clean.
No pushes to origin performed or requested this session.

Note: `0ef5fab` (the Supremacy orderlist fix) landed via a fork BEFORE the
narrative above starts, concurrently with the assistant's own Cybernoid_II
investigation — the assistant verified it independently (instruction
sequences at `$11EB`/`$1267` confirmed against the binary, residual arithmetic
cross-checked: 18/796 + 36/796 frames = exactly the previously-reported
2.26%/4.52%) rather than duplicating it. Two caveats from that verification
carried forward and NOT yet acted on: (a) the resulting "adsr 100%" is thin —
one constant envelope value per voice, not release/gate-off/second-instrument
coverage; (b) a LATENT (currently unexercised) masking-order bug was
suspected at the time in `mon_parser.py:855`/`:939` — this is exactly what
"do 4" above investigated and found to be real only at line 939, not 855.
</work_completed>

<work_remaining>

## ~~1. MAIN_VOL plumbing for ROMUZAK/Galway~~ — INVESTIGATED, CLOSED as not needed (2026-08-08)

Flagged by "do 1" as separate, larger work; the assistant began investigating
this at the very end of the session (last action before invoking the
`whats-next` skill) and found the following, which should save the next
session re-discovery time:

- The shared write-layout function (`bin/build_romuzak_native_song.py`
  around line 260-300) ALREADY emits `MAIN_VOL = {getattr(B, 'MAIN_VOL',
  0x0f)}` into whatever `layout.inc` it writes — this capability is generic
  and already exists, added as part of the earlier MoN master-volume fix
  (`c067b23`, from the PRIOR session).
- `bin/build_mon_native_song.py:1888` sets `B.MAIN_VOL =
  getattr(m, "main_vol", 0x0F) & 0x0F` (computed per-tune via
  `master_volume(sid, sub)`, defined at `bin/build_mon_native_song.py:414`)
  BEFORE the shared writer runs — this is how MoN gets a correct per-tune
  value. `B` there is an imported alias for the ROMUZAK builder module,
  confirmed by the fact that MoN's builder then does
  `shutil.copyfile(ROM_DIR/layout.inc, MON_DIR/layout.inc)` at line 1899 —
  i.e. it runs the ROMUZAK writer with MoN's own volume value patched in,
  then copies the RESULT into MoN's own directory. This is WHY building a
  MoN tune leaves `drivers_src/romuzak/layout.inc` dirty as a side effect
  (see the recurring "revert build-generated .inc files by name" note above)
  — it gets clobbered with MoN-flavored content and must be reverted.
- **The committed baseline `drivers_src/romuzak/layout.inc` and
  `drivers_src/galway/layout.inc` have NO `MAIN_VOL` line at all** (verified
  by `cat`, both files, this session) — meaning ROMUZAK's and Galway's OWN
  builders (`bin/build_romuzak_native_song.py` run directly to build an
  actual ROMUZAK tune; `bin/build_galway_native_song.py`) have never been
  re-run since that MAIN_VOL capability was added, so the committed files
  are STALE, not fundamentally incapable.
- Critically: **`bin/build_romuzak_native_song.py` never sets `B.MAIN_VOL`
  itself** when building a ROMUZAK tune directly (no equivalent of
  `master_volume()` was found for the ROMUZAK/Galway SID formats in this
  session's search) — so even a fresh rebuild would fall through to the
  hardcoded `0x0f` default every time, UNLESS a per-tune volume-extraction
  function is written for those formats first.
- **This is genuinely unscoped RE work, not a mechanical wire-up**: it
  requires understanding whether ROMUZAK's and Galway's native SID formats
  even encode a variable master-volume nibble the way MoN's Tel-engine does
  (unconfirmed either way this session), and if so, where/how to read it —
  analogous to how `master_volume()` reads MoN's. This should NOT be
  attempted under a vague "continue" instruction without either (a) explicit
  user sign-off to spend RE effort on it, or (b) first doing a bounded
  investigation (does either engine's disassembly show a `$D418`-nibble
  write driven by tune data, the way Supremacy's did?) and reporting back
  before writing any code.
- Galway's existing Wizball test already passes (`SONG AUDIO OK`) at the
  hardcoded `$0f` — some evidence this may not be a live bug for at least
  that file, though it says nothing about the rest of either corpus.

**Investigated via siddump trace (not disassembly -- faster and sufficient):**
traced `$D418` across the full window in 2 ROMUZAK originals
(`Delirious_9_tune_1`, `Road_of_Excess_end`, 600 frames each) and 4 Galway
originals (`Wizball`, `Arkanoid`, `Comic_Bakery`, `Athena`, 600 frames each).
**The register is never written at all in any of the six files** -- frame 0's
displayed `F` is siddump's synthetic pre-init bus value (documented in
`fidelity_common.py`'s `siddump_frames_full` docstring), not a genuine write;
every subsequent frame reads `.` (never written), for the entire trace.

**Conclusion: there is no per-tune master volume to extract for either
engine, because neither original ever touches `$D418`.** This is a different
situation from MoN's (which genuinely varied volume per-tune and had it
wrong) -- the shared engine's hardcoded `ora #$0f` is INERT, not incorrect,
for every file checked. Consistent with `do 1`'s finding that Galway's
existing `Wizball` test already passes unchanged at the hardcoded value.

**Closed as not needed.** Documented as a negative result in
`docs/players/ROMUZAK.md` and `docs/players/GALWAY.md` (new sections, both
dated 2026-08-08) and in `CLAUDE.md`'s MoN row, specifically so this isn't
re-investigated from scratch later. Should NOT be revisited unless a
SPECIFIC file is found whose original genuinely writes a non-default
`$D418` value -- none has been found in the 6 files sampled here (2 of 2
ROMUZAK test files, 4 of 40 Galway corpus files).

## ~~2. Realign `vdly` independently per-register~~ — SCOPED, DECLINED, redirected (2026-08-08)

Swept 85 first-parts (78 Hubbard + 7 MoN-family) through the shipped best-lag
diagnostic (`b3a67ea`) to get real numbers before deciding. 255 voice-rows
total; 65 (25%) read strict pulse% < 99.5%. Of those, only 21 improve when
best-lag-searched (not 19 — the first pass under-counted by using `re.search`
instead of `re.finditer`, missing extra best-lag lines on files with more
than one bad voice), and of THOSE only ~5 land near 100% — the realignment's
real win is roughly 5 of 255 rows (2%), with another ~16 improving partially
but still showing real residual afterward. **User declined the realignment**
given that shape: not worth moving every published freq/wf/pul% in the
corpus for a ~2% win. `vdly` stays per-voice; the best-lag readout stays
diagnostic-only. Do not re-litigate this without new data.

**Redirected to the bigger population instead**: the 44 non-lag-explained
voice-rows (three-quarters of the residual). Investigated ~18 distinct files
by rebuilding each FRESH and re-measuring against the original sweep number:
- **5 were STALE artifacts**, not real bugs — `Commando_song16` (the on-disk
  part was a mis-decode; a fresh rebuild now REFUSES outright, "span 1134s
  exceeds 900s"), `Last_V8_song11`, `Deep_Strike_song0`,
  `Auf_Wiedersehen_Monty_song0` (marginal), `Saboteur_II_song0` (74.7%/34.1%
  → 99.6%/99.6%). A/B-verified this session's own `7bb89d7` was NOT the
  cause of the Saboteur_II change (rebuilt against the PRE-fix driver too,
  got the same 99.6%) — this is ordinary corpus staleness, `out/` being
  `.gitignore`d means nothing enforces it staying in sync with the builder.
- **13 reproduced their exact original numbers** — real, open pulse-engine
  content divergences, not measurement artifacts: `5_Title_Tunes_song1`,
  `Chimera_song0`/`song1`, `Commando_song2`, `Gremlins_song0`/`2`/`3`/`4`/`6`,
  `Star_Paws_song0`, `Action_Biker_song0`, `Delta_song0`,
  `Geoff_Capes_Strongman_Challenge_song3`, `One_Man_and_his_Droid_song0`,
  `Zoids_song2`.
Recorded in `docs/players/HUBBARD.md`'s "Fidelity gotchas" section (new
bullet, 2026-08-08) with the full file list, so the staleness class doesn't
get re-investigated from scratch and the real-bug list is available for
whoever picks this up. **Did not attempt to fix any of the 13** — that is
open-ended, per-tune RE work (matches HUBBARD.md's own documented open
classes: V1 modelled/V2 captured-not-modelled pulse gaps, spin/swallow/
format-laggard classes), not a bounded continuation. `Commando_song2` is
flagged as the cleanest lead if this is picked back up: all three voices
read EXACTLY 14.3% pulse — a suspiciously uniform number across independent
voices, more consistent with one systematic cause than three separate
per-voice bugs.

## 3. `whats-next.md` staleness — RESOLVED by this very document

Was flagged repeatedly through the session (by the assistant's own status
updates and independently by "do 4") as increasingly stale. This regenerated
document supersedes it. No further action needed on this item specifically.

## 4. Nothing else outstanding from the pre-session backlog

Every other item from the PRIOR session's handoff (`69c806f`) — the
single-channel comparison + digi guard, the Supremacy adsr gap, the pulse
per-frame-equality metric issue, the sweep-across-13-bespoke-scripts item,
and the smaller/opportunistic items list — was either already resolved before
this session started, or resolved during it (see `<work_completed>`). The
13-bespoke-scripts item (`bin/_verify_f4_*.py` etc., "porting a second caller
onto the harness") remains theoretically open but was explicitly deprioritized
in the prior handoff's own ranking and was not touched this session; not
re-flagged as urgent.
</work_remaining>

<attempted_approaches>

## Failed / corrected during THIS session — do not repeat

- **First floor implementation used too few samples.** `PHASE_FLOOR_SAMPLES =
  3` (the initial constant name/value) made "worse than every self-sample" a
  rank test with a 25% false-positive rate — caught by literally observing a
  clean voice (Cybernoid_II voice 3) get called SYNTHESIS on one run at 3
  samples. Raised to 9 (10% false-positive rate) and the constant renamed
  `REPEAT_FLOOR_SAMPLES` once the naming below was also corrected.
- **First floor implementation conflated phase with metric noise and was
  mis-named `phase_floor` throughout.** Calibrating with ONLY phase-perturbed
  delays (no delay=0 replicate) mislabeled the actual dominant cause on
  isolated-voice renders, which is largely dither-triggered detector-
  threshold noise, not phase. Caught by directly measuring three delay=0
  renders of the SAME file pairwise and finding an 84-97% match band with NO
  phase perturbation involved at all. Renamed every symbol (`phase_floor_*` →
  `repeat_floor_*`, `measure_phase_floor` → `measure_repeatability_floor`,
  `phase_samples` → `floor_samples`, the CLI flag `--phase-floor` →
  `--repeat-floor`) and restructured the return shape from a flat list to
  `{'replicate': [...], 'phase': [...]}` so the two causes stay
  distinguishable in the diagnosis text.
- **A raw floor (unwidened minimum) let the verdict flip between two
  consecutive, IDENTICAL runs of the same command** — voice 3 read 85%
  against a 77% floor on one run, then 70% against a 71% floor on the next.
  Caught by literally running the same command twice in a row and diffing the
  output, not by reasoning about it in the abstract. Fixed by
  `effective_floor()`, which widens the floor by the measured replicate
  shortfall (`1 - min(replicate)`) — pinned by a test asserting this widening
  can only ever DECLINE to call something SYNTHESIS, never manufacture a
  positive.
- **`git add -A` inside a fork sharing a working directory with three other
  concurrently-running forks swept up their uncommitted edits.** This is a
  structural hazard of the `/subtask` fork mechanism when multiple forks
  target the same repo checkout simultaneously, not a mistake specific to any
  one fork's logic — every fork that noticed it (do 1, do 2, do 4) correctly
  declined to unwind it themselves ("out of scope and risky on a branch other
  forks are actively working in") and left it for the parent conversation to
  reconcile once all forks had reported. The parent reconciled it via
  `git reset --mixed` (not `--hard`) specifically because that command
  provably cannot lose working-tree content — verified with SHA-256 hashes
  before and after. **If running multiple `/subtask` forks against the same
  repo again, prefer `git add <specific files>` over `git add -A` inside any
  fork that commits, or expect this exact collision.**
- **The masking-order "bug" flagged by a prior fork ("do 3", from a session
  before this transcript) was partially wrong** — it claimed BOTH
  `mon_parser.py:855` and `:939` needed the same fix. Disassembly (this
  session, "do 4") showed line 855 was already correct; only line 939 (a
  DIFFERENT, tune-specific code path, not shared with 855) actually had the
  bug. Lesson reaffirmed: a claim inferred from naming-pattern similarity
  between two call sites is not the same as verifying each site against its
  own disassembly — the project's own stated rule ("verify against source,
  not inference") caught this before it caused a wrong fix.
- **Investigating the Myth build failure by assuming it was a regression**
  would have been the wrong instinct — it was in fact investigated properly
  (A/B against the pre-`0ef5fab` parser, confirmed identical refusal) before
  concluding it was pre-existing, and ONLY THEN was the real cause (wrong
  builder invoked) found. Worth noting as a pattern: an unexpected build
  failure right after a same-session fix is NOT automatically caused by that
  fix — check both directions before assuming either.

## Approaches considered but not pursued

- Attempting to fix the ROMUZAK/Galway `MAIN_VOL` hardcode blind (without
  first confirming whether either engine's original ever varies its master
  volume) was considered and explicitly rejected — see `<work_remaining>` #1.
  Writing plumbing for a value that never varies in practice would be
  unearned complexity.
- Rewriting `5a3ee7e`/`badacb7` via `git rebase -i` or `commit --amend` was
  considered and rejected in favor of `git reset --mixed` + fresh commits —
  simpler, provably non-destructive (leaves the working tree untouched, only
  moves the HEAD/index pointer), and avoids the interactive-rebase tooling
  this environment cannot use anyway (Claude Code's git safety rules
  prohibit `-i` flags).
</attempted_approaches>

<critical_context>

## Environment / invocation notes carried over from the prior session, reconfirmed still true

- `py -3 bin/build_mon_native_song.py <sid> <sub> [auto|N|absent]` — the
  generic MoN native-driver builder. `auto` = adaptive max-size windows
  (fewest files, no clustering loss); a bare number = fixed N-second windows;
  absent = whole song in one file (usually too big).
- `py -3 bin/build_myth_native_song.py [sub] [seconds|auto]` — Myth's OWN
  builder (py65 emulation extraction), REQUIRED for Myth specifically. Do not
  use the generic builder on Myth; see `<work_completed>` item 3.
- `py -3 bin/mon_part_fidelity.py <part.sf2> <sub> <window_seconds>
  [start_second]` — per-part fidelity scorer. **The window_seconds argument
  matters**: a part only covers its own span before the driver LOOPS it from
  the start; measuring past that boundary compares the replayed beginning
  against later song content and fabricates a phantom residual (this bit the
  session directly on Hawkeye sub3: 75.5% at a wrong 16s window vs 100% at
  the correct 2s window).
- `audio-tightness.bat orig.sid conv.sf2 --driver-init 0x1000 --driver-play
  0x1003 --voice all --seconds N --no-html` — the per-voice sweep +
  repeatability floor + registers×audio cross-tab, now with the
  `--repeat-floor N` flag (default 9) documented above.
- Build-regenerated files (`drivers_src/mon/freqtable.inc`,
  `drivers_src/mon/layout.inc`, `drivers_src/romuzak/layout.inc`) get dirtied
  as a SIDE EFFECT of building ANY MoN tune (see `<work_remaining>` #1 for
  why `romuzak/layout.inc` specifically gets touched). Revert these BY NAME
  after every rebuild-for-measurement — `git checkout -- drivers_src/` (the
  whole tree) destroyed a real source change in a PRIOR session and must
  never be used.
- `sha256sum <file>` (Git Bash, available in this environment) is the
  reliable way to verify file content is unchanged across a git history
  operation — used twice this session to validate the `git reset --mixed`
  reconciliation was lossless.

## Design rules established or reinforced this session

- **A comparison tool owes you `f(x, x')`, not just `f(x, x)`.** Comparing a
  rendered file against itself is exact by construction and proves nothing
  about the render pipeline. The real test re-renders and compares — see
  PATTERNS.md F5b, shipped this session.
- **A floor built from a small sample count needs its false-positive rate
  stated, not just its raw value.** "Worse than every self-sample" is a rank
  test; N=3 is not a serious claim, N=9 (10%) is the floor used here, higher
  is better for anything meant to be published.
- **A floor is a minimum over noisy estimates and must be widened by the
  measured noise, not trusted as a hard threshold** — otherwise the same
  command run twice can disagree with itself.
- **When multiple forks share one working directory, `git add -A` inside any
  committing fork is a hazard**, not a convenience — it will capture any
  other fork's in-progress, unrelated edits. Prefer explicit file lists.
- **Splitting a mis-attributed commit is a `git reset --mixed` + selective
  `git add` + fresh commits operation, not a rebase.** This preserves
  working-tree content provably (hash-verifiable) and needs no interactive
  tooling.
- **A build failure immediately following a same-session change is not
  automatically that change's fault** — check both directions (does the
  PRE-change code fail identically?) before concluding either way.

## Assumptions made that may need validation in a future session

- That ROMUZAK's and Galway's original engines either DO or DO NOT encode a
  variable master volume analogous to MoN's — genuinely unconfirmed, see
  `<work_remaining>` #1. Do not assume either answer; investigate first.
- That the `--repeat-floor` default of 9 (10% false-positive rate) is an
  acceptable tradeoff for routine use vs. a higher N for anything meant to be
  quoted in a fidelity claim intended for publication — this was the
  assistant's judgement call, not something the user was asked to confirm
  explicitly. If a Cybernoid_II-class number is ever going to be cited as a
  headline fidelity figure, consider re-running with a higher `--repeat-floor`
  first.
- That no other doc besides `AUDIO_TIGHTNESS_GUIDE.md` carries a stale
  `--voice all` example — checked via `git log -S "voice all"` on TRACKED
  docs only this session; an untracked or newly-added doc since could still
  carry one.

## References

- `docs/players/PATTERNS.md` — entries F5 (pre-existing) and F5b (new this
  session) are directly relevant to any future fidelity-tool work.
- `docs/players/MON.md` — the Cybernoid_II section (new this session) and
  the Myth builder note (`line 55`, pre-existing, now cross-referenced from
  `CLAUDE.md`).
- `docs/guides/AUDIO_TIGHTNESS_GUIDE.md` — regenerated worked example, §3.
- `CLAUDE.md`'s MoN row in the Known Limitations table — updated twice this
  session (the `$D418` fix, the Myth builder note); this is the first place
  to check before assuming a claim about MoN fidelity is current.
</critical_context>

<current_state>

## Complete and committed

`HEAD` = `f705c4a6da3425a6be3db0bdbdb98b9af750a9ef`. Working tree clean, no
uncommitted changes, nothing staged. Nine commits landed this session (see
the chronological list in `<work_completed>`), all local — nothing pushed to
`origin` this session, and nothing was requested to be pushed.

Full test suite as of the final commit: **1888 passed, 7 skipped, 2 xfailed**
(`py -3 -m pytest pyscript/ -q`).

## In progress / not started

- `<work_remaining>` #1 (ROMUZAK/Galway `MAIN_VOL` plumbing): investigation
  begun (the mechanism was traced and understood, see
  `<critical_context>`/`<work_remaining>` #1 in detail) but ZERO code written
  for this item. This was the very last thing the assistant was doing before
  this handoff document was generated, in response to the user's unscoped
  "go on" — a deliberate stop-and-scope-first decision rather than writing
  speculative RE code under a vague instruction.
- `<work_remaining>` #2 (per-register `vdly` realignment): explicitly
  blocked on a user decision, not started, not scoped further than what two
  independent forks already reported.

## Temporary / not in the repo

- Various scratch scripts and file copies used for A/B verification this
  session (e.g. a copy of the pre-`0ef5fab` parser for the Myth regression
  check, a copy of the driver source for the Cybernoid rebuild A/B, raw WAV
  renders used for the metric-noise cross-correlation measurement) were
  written under the session scratchpad directory
  (`C:\Users\mit\AppData\Local\Temp\claude\...\scratchpad`) and/or `out/`.
  None are required to continue; they were reproducibility aids, not
  deliverables.
- `out/mon/*.sf2` build artifacts for Hawkeye, Cybernoid, Cybernoid_II, Myth,
  Supremacy exist from this session's verification rebuilds, all built
  against the current (post-`7bb89d7`) driver — these are current, not stale,
  as of `HEAD`.

## Open questions (for the user, not for a future session to guess at)

1. Is the ROMUZAK/Galway `$D418` master-volume hardcode ( `<work_remaining>`
   #1) worth a bounded RE investigation, or should it stay as-is until/unless
   a specific file is found to need it?
2. Should `mon_part_fidelity.py`'s per-voice delay refinement (`vdly`) be
   made per-register (`<work_remaining>` #2)? This moves published corpus
   numbers project-wide and needs an explicit yes.
3. Is `--repeat-floor 9` (10% false-positive rate) an acceptable default, or
   should headline fidelity claims re-run at a higher N before being quoted?
</current_state>
