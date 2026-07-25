<original_task>
Session began with "read what next" — the established convention meaning: read
this file's previous contents (the prior session's handoff) and continue that
work without being asked.

That handoff set the priority as root-causing why E3f's combo fx command values
crashed SF2II's editor on play, with E3f disabled by default as a hotfix
(`5295165`). Later user instructions, in order: run the crash batches myself;
test follow-mode and play-from-cursor; load the combo build for a manual test;
merge and push; move the sweep and crash probe into `pyscript/` with tests;
then "you decide what to do".
</original_task>

<work_completed>
## Summary

Blackbird/lft is CLOSED OUT and shipped as **v3.22.0**. All work on `master` and PUSHED.

| commit | what |
|---|---|
| `2d65366` | **E3f RE-ENABLED** — the "combo values crash SF2II" premise was FALSIFIED |
| `b0bff86` | **E4** — prepare1's byte allowance is forfeited by prepare2; To_Die_For_II 94.2% → 98.2% |
| `5db109c` | Promoted the sweep + crash oracle into `pyscript/` with 34 tests |
| `5036a30` | Documented the filter lead + refreshed this handoff |
| `d6fff59` | **E5** — the filter row grammar was missing a row type; To_Die_For_II → **100.0**, Revolutions_Delivered → **100.0** |
| `2c41d97` | E5 editor play-test PASSED (4/4) + handoff refresh |
| `486a990` | **E6** — B7 priming vs `window_steps`; Into_the_Unknown → **100.0** |
| (this) | v3.22.0 wrap-up: inventories, CHANGELOG, STORY, version bump, KB card |

**Blackbird corpus 99.18 → 99.963.** Glyptodont 162/162 note-ons by default.
**11 of 16 files at exactly 100.0**; none below 99.8. Full suite **1679 passed** / 7 skipped / 2 xfailed
(was 1645; +34 new, none regressed).

## 1. The E3f crash premise was WRONG (`2d65366`)

The prior session disabled E3f believing combo command values 48-62 crash the
editor, inferred from ONE observation per arm. Falsified by building a
scriptable oracle (`pyscript/blackbird_crash_probe.py`): launch the REAL editor,
F10-load, press F1, screenshot, report survival.

Against the SAME editor that crashed (`Build: Dec 26 2025 21:27:55`):

| build | trials | combo commands EXECUTED | crashes |
|---|---|---|---|
| COMBO (162/162) | 5 x 66s | **120** (values 48 and 50) | **0** |
| SAFE (157/162) | 5 x 66s | 0 | 0 |

All 10 screenshots OCR-verified (right file, SF2II actually foreground,
`Playing time: 1:06`). User ran a follow-play (Ctrl+P) trial too — also clean.

**MY FIRST BATCH WAS INVALID AND CAME BACK CLEAN.** A 6-second window returned
16/16 SURVIVED, but the earliest combo command fires at **8.2s** — it executed
ZERO of the construct under test. Caught by checking row→time against the
build's own 4.52 frames/row. `assert_window_covers()` now makes that raise.

Also falsified by measurement: 128-sequence limit (71 vs 72), `Unpack` heap
overrun (both peak 960 of 1024), packed-block overflow (both cap at 250),
`driver_state.cpp`. `DoPlay()` read end-to-end — nothing in the play path
indexes the Commands table by command value.

E3f is ON by default; **`BB_NO_COMBO=1`** disables.

## 2. E4 — the real To_Die_For_II bug (`b0bff86`)

Blackbird's prepare1/2/3 run in FIXED order per tick. The builder modelled
prepare1's and prepare2's one-byte-per-tick budgets as INDEPENDENT. They are
not: **prepare1's allowance is FORFEITED the moment prepare2 consumes**, because
prepare1 has already run and passed on a different byte.

Voice 1 bytes 651-654 = `$80` `$c9` `$92` `$34`: prepare2 takes `$80`, then
prepare3 eats `$c9` as a 7-tick delay (`$f0|$c9 = $f9`), so note 26 (`$34>>1`)
lands on tick 357 — matching the sim's row-358 note-on exactly. The builder had
it at 364, six ticks late.

Fix: `if arp_pending:` → `if arp_pending or prep2_pending:` (third of three
sibling cases; the other two came from the REPEAT=1 arc).

One missed note-on cost 5.8 points because B9's pulse engine free-runs a DELTA
program with no note-restart — the accumulator stayed de-phased ~1100 frames,
pinning pulse at exactly 66.7% (2 of 3 voices). **With a free-running
accumulator, a transient error is permanent.**

Result: pulse 85.2→100.0, waveform 99.1→100.0, adsr 99.5→100.0, freq 98.8→99.9.
Sweep: 1 improved, 0 regressed, no part moves, **every other file
byte-identical** — the signature of a mechanism fix, not a re-tuning.

## 3. Tooling promoted + tested (`5db109c`)

`pyscript/blackbird_sweep.py` (corpus sweep + `--compare`) and
`pyscript/blackbird_crash_probe.py` (crash oracle + combo schedule analysis),
with 34 tests running in 0.43s — they never build and never launch SF2II
(analysis is pure functions; only `probe_once` touches the GUI, lazily
imported). Both verified end-to-end: `--schedule` reproduces "55 combo
command(s); first at 8.2s (row 91, voice 1)"; `--compare` reproduces the E4 diff.

Tests encode the FAILURE modes: too-short play window raises, empty schedule is
an error not a pass, crash-rate is over trials that actually PLAYED, a failed
build parses to `None` not 0%, part moves are reported separately from
regressions, the recorded mean 99.669 is asserted.

The doc rows in `CLAUDE.md` / `ACCURACY_MATRIX.md` no longer say "not
reproducible from a fresh clone" — that stopped being true.

## 4. E5 — the filter row grammar was missing a row type (`d6fff59`)

Hardware writes `$D418` AND `$D417` EVERY frame from `filttable[y]`/`[y+1]`,
independently of whether that frame's cutoff op is SET or ADD. The native
grammar had only SET (`[$80,$FF]`: mode+res+absolute cutoff) and ADD
(`[$00,$0F]`: cutoff delta, byte2 = RUN COUNT) — nothing could say **"set
mode+res, leave cutoff alone"**. So a program whose row 0 is an ADD-cutoff
record inherited the previous filter owner's passband/resonance.

To_Die_For_II instrument 6 (`ins_filt[6]=26`) is that shape: raw `filttable` at
`$1566` position 26 = `$2f $f1 $00 $ff` (band-pass, res `$f0`+routing, cutoff
ADD of 0, advance `$ff` → `+0`, holds forever). The driver held `$D417=$00` /
`$D418=$0f` from frame ~1648 to the end — it never ENABLED the filter.

Fix: a third row type `1M DD RB` in the dead `[$10,$1F]` space
(`_filter_modeadd_row` + `fp_modeadd`). Does NOT contradict B21 — the cutoff
stays a delta on the inherited value; B21 governs cutoff, E5 governs mode/res.

**Dispatch is a BIT TEST (`and #$10 / bne`), never `cmp #$10`**: byte0 reaches
`$FF` there and SF2II's CMP is only correct for `|A−op| ≤ 127` (the E3d hazard
class, shipped twice before in this repo).

Result: To_Die_For_II **98.2 → 100.0** (filter 88.9 → 99.9), Revolutions_Delivered
**99.0 → 100.0**; corpus 99.669 → 99.844; 0 regressed, no part moves, no size
changes. 13 filter programs across 5 files use the new row type — and 3 of those
files were ALREADY 100.0 and stayed there, so the changed path is exercised
where there was nothing to gain.

**Editor play-tested: 4/4 survived**, playback 0:52–1:12, past the ~33s filter
events. (Title-bar OCR failed on 3 of 4 shots because the terminal overlapped
SF2II; survival is process-liveness, and the editor panel underneath shows the
timer running and the row cursor advancing — verified by direct inspection.)
</work_completed>

<work_remaining>
## 1. ~~To_Die_For_II's filter~~ — SOLVED by E5 (`d6fff59`), now 100.0

Kept only as a pointer: the grammar fix is documented in
`docs/players/BLACKBIRD.md`'s E5 section. Hardware rewrites `$D418`/`$D417`
EVERY frame regardless of whether that frame's cutoff op is SET or ADD, and the
native row grammar had no way to say "set mode+res, leave cutoff alone" — so an
ADD row0 inherited the previous filter owner's passband/resonance. Fixed with a
third row type `1M DD RB` in the dead `[$10,$1F]` space. **Editor play-tested,
4/4 survived.** My first diagnosis ("`unroll_filter` misreads the table") was
wrong; reading the CONSUMER (`fp_dec`/`fp_set`) is what corrected it.

## 2. ~~Into_the_Unknown~~ — SOLVED by E6 (`486a990`), now 100.0

B7 added a resume-mid-cycle primitive and `window_steps` never learned it existed: a
mid-note part boundary re-triggered the wave program, discarding the primed pulse phase.
Two-frame stall -> permanent 2-step lag (B9's accumulator free-runs). Fixed by emitting a
tie when the boundary lands INSIDE a step. Found only by a py65 trace of the assembled
driver, after three data-side hypotheses came back clean.

## 3. `DriverSelector` — NOT a defect, do not "fix" unasked.
Every native-driver player here is `bin/`-only (Galway, MoN, Hubbard, DMC, Sound Monitor,
SDI, ROMUZAK). Blackbird matches the established pattern.

## 3b. THE BIG ONE: 45 of 61 LFT rips do not locate.
The "16-file v1.2-exact corpus" is not a curated sample — it is **every rip
`locate_blackbird` supports**. The other 45 files in `SID/LFT/` fail location outright.
Extending variant coverage is a fresh multi-session RE arc and deserves its own go/no-go
decision; it is NOT a wrap-up task.

## 4. Galway / ROMUZAK `fp_dec` — SF2II executes filter ADD rows as SET rows.
`drivers_src/galway/galway_driver.asm:535`, `romuzak_driver.asm:564`:
`cmp #$90; bcs fp_set` with no high-bit guard. Widen to `cmp #$80` (B24 form)
ONLY after confirming each player's `fp_set` mode extraction handles a
top-nibble-8 byte0, then re-verify each corpus. Allowlisted in
`pyscript/test_sf2ii_emulator_hazards.py::KNOWN_UNFIXED`.

## 5. The user's ORIGINAL SF2II crash remains UNEXPLAINED.
Established: loading a combo build and pressing play — with or without follow
mode — does not reproduce it. NOT established: that no editor state can. If it
recurs, `BB_NO_COMBO=1` is the immediate out, and the recurrence would be the
most informative datum available. Value 49 was never executed in-window (only
48 and 50); structurally identical, but not directly exercised.

## 6. E1/E2 roadmap (user-requested earlier, not started)
E1 WinVICE per-voice mute; E2 SidWiz/Corrscope video (blocked on E1 + ffmpeg).
</work_remaining>

<critical_context>
## Verification discipline that actually caught things this session

- **Check the measurement window covers the effect.** The 6s-vs-8.2s near-miss
  is the single most important lesson here. An all-green result measured outside
  the window where the effect lives is not evidence of absence.
- **Beware vacuous matches.** `$D415`/`$D416` at "100%" while both are `$0000`
  means nothing. Assert the evidence is non-trivial before quoting it.
- **Derive rules from working code, not from the discrepancy.** Three tick
  accountings disagreed (sim 358, builder 364, naive re-walk 350) and the naive
  walk was wrong the SAME way the builder was. Reading `prepare1/2/3` and
  `trtimer`'s wrap arithmetic found it — and confirmed `_note_ticks`/
  `_delay_ticks` were correct and never the bug.
- **Byte-identical elsewhere** is the signature of a genuine mechanism fix; a
  re-tuning perturbs many files and nets positive.
- **Part counts are part of the result.** A moved count shifts the measurement
  window and makes the numbers incomparable (the B10 trap). `EXPECTED_PARTS`
  now pins Fargo 2 / Dithered_Island 2 / Into_the_Unknown 3.
- **Read the CONSUMER, not just the producer.** E5's first diagnosis
  ("`unroll_filter` misreads the table") was plausible, wrong, and got committed
  to the docs as an open lead before being checked. Reading `fp_dec`/`fp_set` in
  the DRIVER showed the ADD path never touches `F_MODE`/`$d417` at all — a
  missing capability, not a parsing error.
- **A register pinned at exactly 66.7% / 33.3%** is a whole-voice failure, not
  scattered error. If it's pulse, suspect accumulator phase and look for a
  timing event EARLIER than where the plateau starts.

## Build/verify discipline (load-bearing every round)

- `drivers_src/blackbird/*.inc` are TRACKED but purely generated —
  `git checkout -- drivers_src/blackbird/` before every commit.
- `py -3 pyscript/blackbird_sweep.py <label>` builds all 16 → JSON;
  `--compare a.json b.json` diffs (exit 1 on regression or part move).
- `bin/build_blackbird_native_song.py SID/LFT/<name>.sid` builds one file.
  `BB_DIAG_BIN=N` / `BB_DIAG_LO` / `BB_DIAG_HI` / `BB_DIAG_REG` are the
  binned + per-register diagnostics that located both bugs this session.
- `BB_NO_COMBO=1` disables E3f combo arming.
- `py -3 pyscript/sf2_open_in_editor.py <file.sf2>` loads into real SF2II —
  MUST run from repo root. Flaky; retries.
- **GUI automation steals focus and its keystrokes land in whatever is
  foreground.** It disrupted the user's session this time. Do not run batches
  while they are at the machine; ask first.
- Full suite: `py -3 -m pytest pyscript/ -q` (~4 min), baseline **1679 passed /
  7 skipped / 2 xfailed**.

## To_Die_For_II specifics
TEMPO=4 (4.006 frames/row), span 643 tick-rows, 2576 frames, 1 part, 14
instruments, `ins_restart=7`, `ins_restart2=5`, nins=20, filttable `$1566`.
</critical_context>

<current_state>
## Repository
- Branch `master`, HEAD `d6fff59`+, fully pushed (`git log origin/master..master`
  empty). Branch `e3f-reenable-crash-falsified` is now redundant with master and
  can be deleted.
- Uncommitted: `.claude/settings.local.json` (pre-existing), this file, and the
  BLACKBIRD.md "OPEN LEAD" section written at the end of the session.
- Untracked `scratchpad/`: superseded copies of the promoted tools, the batch
  drivers, the To_Die_For_II probes (`tdf2_probe.py`, `tdf2_filter.py`), sweep
  JSONs and screenshots. Safe to delete; the tracked `pyscript/` copies are
  canonical.

## Corpus (on disk, E3f ON + E4)
mean **99.844**, 10 files at exactly 100.0, Glyptodont 162/162 (26930 bytes),
To_Die_For_II **100.0**, Revolutions_Delivered **100.0**, Into_the_Unknown 98.1. Part counts Fargo 2,
Dithered_Island 2, Into_the_Unknown 3, rest 1.

## SF2II
One instance may still be open from the manual follow-play test (loaded
`scratchpad/Glyptodont_COMBO.sf2`). Harmless; close it.
</current_state>
