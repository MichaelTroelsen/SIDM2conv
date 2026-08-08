# whats-next — session handoff (2026-08-07 → 08)

<original_task>
The session opened with one question:

> "can we replace SID2WAV with https://github.com/libsidplayfp/libsidplayfp or
> https://github.com/libsidplayfp/libresidfp or https://github.com/libsidplayfp/sidplayfp
> anyway please add links to our knowledge of tools."

So the **original scope was: (a) assess whether sidplayfp can replace SID2WAV.EXE, and
(b) add the three repo links to the tool documentation.** Everything else in this session
was follow-on work the user requested step by step, in this order:

1. Do the replacement for real (not just document it).
2. Commit and push it.
3. Open a PR (#17), check for reviews, check CI.
4. Fix the CI failures, then chase each newly-revealed failure to the bottom.
5. Retire the batch-pyautogui launcher and its stale docs.
6. Merge PR #17, switch to master, pull.
7. Investigate the leftover uncommitted `drivers_src/*.inc` changes; commit the sweep script.
8. Read the sibling **h2g** project's fidelity docs; propose improvements to SIDM2's
   fidelity tooling (SID2SID and WAV2WAV, incl. single-channel comparison).
9. Build the A/B baseline harness (delegated to an Opus subagent).
10. Settle **R17** (are the MoN structural options safe to default?) by widening the gate.
11. Fix the `accuracy.py` scoring defects; then `validate_sid_accuracy.py`; then the
    register pairing; then the whole vacuous-score class.
12. Fix the MoN `$1F`/`$3F` band-pass bug, then the master-volume half.
13. Update docs (project rule 3).

**Note on model:** the user switched the session default to Opus mid-way (after the h2g
analysis). The two heavy subagents were explicitly run on Opus.
</original_task>

<work_completed>

## A. sidplayfp replaces SID2WAV.EXE — the original task (commit `32a0e0c`)

**Assessment answer: yes.** SID2WAV.EXE is a 1997 build; `pyscript/audio_tightness_tool.py`
already documented it hanging indefinitely on newer tunes (lft's Glyptodont — parses the
header, then renders zero samples).

- **Install:** MSYS2 already had prebuilt Windows binaries — no build from source needed:
  `pacman -S mingw-w64-x86_64-sidplayfp` (sidplayfp 2.16.2 / libsidplayfp 2.16.1 /
  libresidfp 1.0.1). Bundled into the repo at `tools/sidplayfp/` — the exe plus its 8
  runtime DLLs (`libgcc_s_seh-1`, `libgcrypt-20`, `libgpg-error-0`, `libiconv-2`,
  `libsidplayfp-6`, `libstdc++-6`, `libusb-1.0`, `libwinpthread-1`), ~6.5 MB total,
  consistent with other tracked `tools/` binaries.
- **New module `sidm2/sidplayfp_wrapper.py`** (`SidplayfpIntegration`), mirroring
  `vsid_wrapper.py`'s shape.
- **CLI mapping** (differs from SID2WAV — this is the gotcha): `-t<secs>` duration,
  `-p16`/`-p32` bit depth (**no 8-bit mode**), `-f<hz>` rate, `-o<n>` subtune,
  `-u<n>` mute voice (repeatable), `-s`/`-m` stereo/mono, `-w<name>` WAV out.
  **Output path is `-w<path>` (attached), and the input file comes LAST** — the inverse
  of SID2WAV's `in.sid out.wav` ordering.
- **Exit code 0 on success** (unlike VICE's `vsid`, which exits 1 on normal termination).
  It also overwrites an existing WAV cleanly.
- **Rewired:** `sidm2/audio_export_wrapper.py` (`force_sid2wav` → `force_sidplayfp`),
  `pyscript/audio_tightness_tool.py` (`--renderer auto|vsid|sidplayfp`; `--voice` now
  forces sidplayfp), `sidm2/wav_comparison.py`, `bin/sf2_to_wav.py`,
  `scripts/convert_all.py`, `scripts/test_roundtrip.py`, `pyscript/conversion_executor.py`,
  `pyscript/complete_pipeline_with_validation.py`, `analyze-file.bat`.
- **VSID remains the preferred primary renderer.** sidplayfp only replaces SID2WAV's role.
  sidplayfp does **not** replace VSID for RSID-with-custom-IRQ files (PLAYBOOK's VICE
  escape hatch) — that needs a full emulated machine, not a player library.
- Links added to `docs/TOOLS_REFERENCE.md` and to the auto-memory `tools.md`.

## B. PR #17 and the CI cascade (commits `2ace9e7`, `72dd1ab`, `1ec22b1`, `9f05787`, `f6a65a1`)

PR #17 opened, **all 27 checks eventually green, MERGED 2026-08-07T19:46:33Z** as `c4fc9ce`.
Five failures, each one only visible after fixing the previous:

1. `actions/upload-artifact@v3` / `download-artifact@v3` → **v4**. GitHub now hard-rejects
   v3 in "Set up job", before any code runs. (`.github/workflows/conversion-cockpit-tests.yml`)
2. **bandit** High + Medium: `os.system(f'start {output_file}')` → `os.startfile()`
   (B605/CWE-78, `pyscript/generate_stinsen_html.py:583`); `tempfile.mktemp()` →
   `mkstemp()` + immediate `unlink()` (B306, `pyscript/test_zig64_audio_gate.py`).
   **The unlink is required** — `scripts/sid_to_sf2.py` refuses to write to a path that
   already exists, and `mkstemp` pre-creates the file where `mktemp` only reserved a name.
3. `Test Summary` downloading an artifact that is never produced (the upload steps write
   files no test creates) → `continue-on-error`.
4. `Test Summary` "Comment on PR" 403 `Resource not accessible by integration` → added
   `permissions: {contents: read, pull-requests: write}` scoped to that job only.
5. `Batch Testing Unit Tests` referencing `pyscript/test_batch_pyautogui.py`, **archived
   2026-04-29 in commit `a3e002f`** (it needed `output/` fixtures archived in the same
   cleanup). Removed the three references from `batch-testing.yml`.

Then (`f6a65a1`) **retired the launcher**: `git mv test-batch-pyautogui.bat` →
`archive/cleanup_2026-08-07/retired_batch_pyautogui/` with a README, and scrubbed it from
9 doc files — `CLAUDE.md`, `README.md` (×3), `docs/CI_CD_SYSTEM.md`,
`docs/FILE_INVENTORY.md`, `docs/guides/BEST_PRACTICES.md`, `docs/guides/FAQ.md` (a whole
Q&A entry), `docs/guides/GETTING_STARTED.md`, `docs/guides/TROUBLESHOOTING_FLOWCHARTS.md`,
`docs/guides/TUTORIALS.md` (**Tutorial 8 removed wholesale, Tutorial 9 renumbered to 8**,
index + quick-reference table updated).

## C. The leftover `.inc` files + `mon_struct_sweep.py` (commit `ffa07b1`)

Pre-existing uncommitted changes were investigated, not blindly committed. All four files
were touched in a ~13-second window on 2026-07-30 — a single build run.
`bin/build_mon_native_song.py:39` writes `drivers_src/mon/freqtable.inc` and `:1809`
copies `romuzak/layout.inc` over `mon/layout.inc` **as a build side effect**. Precedent
`227e6aa` ("revert build-regenerated .inc files committed by mistake") says discard.
Discarded the `.inc`s; committed the genuinely-new `pyscript/mon_struct_sweep.py`.

## D. h2g cross-project analysis (no commit — research)

Sibling repo **github.com/MichaelTroelsen/h2g** (Python port of a Rob Hubbard →
GoatTracker converter, **not on this machine**; fetch via
`gh api repos/MichaelTroelsen/h2g/contents/<path> -q '.content' | base64 -d`).
Read in full: `FIDELITY.md`, `FIDELITY-TOOL-IMPROVEMENTS.md`, `SIDM2-FIDELITY-TESTER.md`,
`SIDM2-HUBBARD-KNOWLEDGE.md`, `AUDIT.md`, `whats-next.md` (headings).

Transferable items identified and **verified against SIDM2's actual code**:

- **Per-frame equality is wrong for a swept register.** `bin/mon_part_fidelity.py` scores
  `pulse%` as per-frame agreement; h2g measured and rejected exactly that ("two players
  sweeping the same duty cycle from different phases share almost no frame values").
  Their replacement: movement *count* for pulse, *travel* (summed frame-to-frame movement)
  for cutoff. **Not yet acted on.**
- **Subtune correspondence matrix.** `Dragons_Lair_Part_II` scores 7% on the diagonal,
  **94% at its true counterpart** — the `.sid`'s own init wrapper renumbers subtunes
  before the player sees them. h2g notes `--search-subtunes` is *structurally* unable to
  find this (it varies their index, holds the original's fixed). **Not acted on.**
- **Window size is a measurement artifact.** `BMX_Kidz` scored 0% for eighteen versions
  purely because 13 s of opening silence exceeded a 10 s window; `I_Ball` reads 43% @10s
  and 94% @30s. Live in SIDM2: `mon_struct_sweep` scored **Hawkeye:3 on a 2-second
  window**. **Not acted on.**
- **Don't shape a detector like your hypothesis** — h2g specced a detector for errors
  "near 2×"; reality was 1.1–1.5×, so it would have matched nothing and its silence read
  as "no problem here."
- **Deliberately NOT ported:** h2g's `--pace`/rate machinery (exists because GoatTracker
  can't express arbitrary tempos; SIDM2's native drivers largely can).

## E. The A/B baseline harness (commit `3a329d2`, built by an Opus subagent)

`sidm2/fidelity_common.py` 262 → 859 lines, **additive only** — no existing function's
behaviour changed. New API:

- `Dimension` / `register_dimension` / `dimension(key)` / `split_key` — a registry where
  each score key declares which SID registers it derives from. `dimension()` **raises** on
  an unregistered key rather than defaulting (a defaulted dimension reads as measured and
  isn't). Built-ins: `freq wf pul adsr cutoff filtctl volmode note onset`.
- `dimensions_present` / `registers_read` / `registers_unread` / `format_coverage` — the
  generated "what this run compared / NOT read by anything" block.
- `output_digest(paths)` — sha1/12 of built artifacts; returns **None** if any path is
  missing (sha1-of-nothing compares equal to itself — the same empty==empty defect that
  let the v3.21.0 zig64 gate certify 64 zero bytes as byte-identical).
- `result_row` / `ab_pair` / `dump_rows` / `load_rows` / `settings_mismatch` /
  `option_drift` / `regressions` / `compare_runs` / `format_run_delta` / `git_label`.
- **The key design call:** `compare_runs` **refuses** on mismatched *measurement* settings
  (duration, subtune) but **allows and surfaces** mismatched *build options* as "the change
  under test" — refusing those would forbid the exact comparison the mode exists for.

`pyscript/mon_struct_sweep.py` ported onto it. **Honest accounting: the file GREW**
139 → 176 lines (code 91 → 99). Its A/B *decision* logic shrank ~11 → ~6 lines; the growth
is new capability (tree label, per-side digests, settings refusal, movement ranking,
blindness report). **The stated acceptance criterion was "if it doesn't shrink, the
abstraction is wrong — go back and redesign."** The agent judged the trade worth it and did
not redesign; this was surfaced to the user as an open judgement call. **A second caller is
the real test and has not happened yet.**

## F. R17 SETTLED (commit `67fa1c6`, Opus subagent)

**Question:** are `MON_ARP_STRUCT` / `MON_PULSE_CANON` / `MON_WAVE_CANON` safe to make the
MoN driver's default? Part count is the prize, fidelity is the gate.

The harness immediately printed that the gate was **blind** to `$D405/$D406`,
`$D415/$D416`, `$D417`, `$D418`. Widened `bin/mon_part_fidelity.py` (columns **appended**,
so the existing `OSC_RE` and any saved baseline still parse) and added
`fidelity_common.siddump_frames_full()` (superset; `siddump_per_frame` is now a projection
of it so the two parsers cannot drift) and `exercised()`.

**Verdict: widening did NOT change the answer.** Across 8 targets the four new dimensions
moved **1 time in 25**, and that move was an *improvement*. 61 → 40 parts, genuinely clean
on 7 of 8. **Supremacy sub1 remains the sole regression and is still purely freq/pulse.**

**The actionable part — isolation on Supremacy sub1:**
| option alone | parts | effect |
|---|---|---|
| `MON_ARP_STRUCT` | 2→1 | **the entire win AND the entire regression** |
| `MON_PULSE_CANON` | 2→2 | **regresses with zero benefit** (hidden behind ARP jointly) |
| `MON_WAVE_CANON` | — | no number moved, but output differs → *not measurably harmful, NOT proven safe* |

**Recommendation stands: not safe as an unconditional default**, and the other two prongs
are not safe by elimination either.

Also surfaced (identical on both builds, unrelated to R17): `volmode` 0.0% on all three
Supremacy subtunes + Cybernoid_II, 82.5% on Hawkeye:0; **Supremacy:0 `adsr` 2.3%/4.5%** on
osc2/osc3.

## G. The vacuous-score class — five broken copies (commits `9b1a0f0`, `2bc8c14`, `05bd7db`, `649e076`)

**Headline: two IDENTICAL register captures scored 50%** on `sidm2/accuracy.py`, the
library behind the user-facing validator. Proven by running the pre-fix code side by side.

Four distinct defects:
1. **Sparse-register desync** — voice lists held only frames where `freq_lo` *and*
   `freq_hi` were co-written, then `zip`-paired by position. Verified: two captures with
   audibly different pitches on 3 of 4 frames scored **100%**.
2. **Fabricated zeros** — `frame.get(0x15, 0)` defaulted a *held* register to 0.
3. **Vacuous zero** — `filter_accuracy` kept its `0.0` initialiser and was weighted 10%,
   so a file was docked ten points for **correctly not using a filter** (Hubbard never
   writes cutoff). Silent *voices* did the same to the voice average — that's the other
   40 points. `HUBBARD.md` records the *mirror* bug (0==0 as "filter 100%"), so both
   directions were live in the repo simultaneously.
4. **register_accuracy paired the i-th WRITE against the i-th write** — wrong twice over:
   positional desync, and the wrong question (what the SID plays is the value a register
   *holds*; how many times it was written is inaudible). Measured: two drivers with
   identical held timelines, one writing twice and the other four times, scored **25%**.

`scripts/validate_sid_accuracy.py` carried a duplicate of 1–3 **plus a fourth unique to
it**: `if cutoff_lo in frame or ...` tested register *values* (0–255) for membership among
the frame's *keys* (0x00–0x18), so filter frames were included whenever a value collided
with a written register index. Now **delegates** to `sidm2.accuracy._timeline/_agreement`.

Audit of `if <total> else 100.0 / else 0.0` across `bin/ sidm2/ pyscript/ scripts/` found
three more: `sidm2/validation.py` (a **fourth complete copy** of the weighted scheme, the
path `convert_all.py` runs per file), `pyscript/trace_comparator.py:341` (`else 100.0` — a
voice silent on **both** sides reported 100%), `scripts/convert_all.py:623`
(`Match rate: 100% (0/0 observed values found)`).

**THE LESSON, learned twice in one day — two guards, not one:**
- `score_pct(ok, tot)` → None when `tot == 0`. *Were there any frames?*
- `exercised(a, b)` → False when both series are the same single constant. *Did those
  frames carry information?*

`score_pct` alone is **not sufficient** because **siddump force-displays every register on
its first row** whether the playroutine wrote it or not. A tune that never filters still
yields a full-length, entirely non-None series of zeroes on both sides → nonzero
denominator → confident 100%. **Measured twice after the "fix" was in:** Commando reported
`Filter Accuracy: 100.00%` in `accuracy.py`, then again through `validation.py`. Both were
caught by **running the tool**, not by the tests.

`exercised` is deliberately two-sided: two *different* constants still score ~0%, so a
permanently-wrong register cannot hide in `n/a`.

## H. MoN `$D418` — both halves (commits `464406a`, `c067b23`)

**Passband (`464406a`).** Not a dropped bit — **the passband was never captured**.
`filter_program_for` worked from `filter_trace`, which returns only `(cutoff11, $D417)`;
`_filt_set_row` hardcoded `$90` (X=1, low-pass) for **every MoN tune ever built**. The
driver was never at fault: `fp_set` has always decoded a 3-bit passband into `F_MODE`.
Row encoding: byte0 = `1XXX YYYY`, bit7 marks SET (driver dispatches on `bmi`, the
CMP-carry-safe test — see memory `sf2ii-cmp-carry-bug`), XXX = passband, YYYY = cutoff hi
nibble. `$90`→LP, `$B0`→LP+BP, `$F0`→LP+BP+HP.

Originals measured over 20 s: Cybernoid_II `$3F` (LP+BP), Hawkeye `$7F`×769 / `$1F`×231
(**switching**), Cybernoid `$1F` (already right), Supremacy `$06`/`$03` (no passband).

**Volume (`c067b23`).** Driver hardcoded `ora #$0f`. Over 60 s: Hawkeye 0/2/3, Cybernoid,
Cybernoid_II = 15; **Supremacy sub0 = 6, sub1 = 8**, sub2 = 15. It is a per-song
**constant**, not a ride — the only other value any target shows is frame 0's pre-init bus
state (all three Supremacy subtunes read 3 there). Added build-time `MAIN_VOL` to
`layout.inc` beside `FILT_MODE`; `master_volume()` takes the **MODAL** value so the frame-0
artefact can't be shipped.

**Verified results:**
| target | `$D418` before | after |
|---|---|---|
| Cybernoid_II | 0.0% | **99.7%** |
| Hawkeye | 82.5% | **99.9%** |
| Supremacy sub0 | 0.0% | **exact** — `$06`×800 vs original `$06`×799, independently verified by packing back to SID and tracing |
| Cybernoid | n/a | n/a — its passband is uniformly 1, so byte-identical rows; **cannot** regress |

`freq`/`wf`/`pulse` stayed 100.0 throughout.

## I. Docs (commit `7ec921a`) — project rule 3

- `docs/players/MON.md` — new `$D418` section; **flags that older "filter 100%" figures
  meant CUTOFF ONLY**.
- `docs/players/PATTERNS.md` **D4 extended** (not duplicated — vacuous acceptance was
  already the entry) with the two-guard rule and the five-broken-copies scale.
- `CLAUDE.md` — fidelity harness added to tools ("route new scorers through it, don't
  write a sixth copy"); MoN row of Known Limitations rewritten to state which registers
  its accuracy claim covers.

## J. Experiment: is sidplayfp `-u` a faithful voice slice? (no commit — findings only)

Motivated by the proposed single-channel comparison. **Answer: no, on many tunes.**

Muting all three voices does **not** produce silence:
| tune | all-3-muted residual RMS | vs its mix |
|---|---|---|
| Commando | 11 | silent ✅ |
| Crazy_Comets | 25 | silent ✅ |
| Sanxion | 227 | ~10% bleeds |
| **I_Ball** | **1960** | **75% of the mix survives** |

**Consequence (this part held up):** per-voice audio comparison is silently invalid where
the residual is large — the same signal appears in all three "isolated" renders, making
them agree for reasons unrelated to the driver.

**⚠ TWO CORRECTIONS, both from `21917ba` (see §K):**
1. **My inferred cause — `$D418` master-volume digi — is FALSIFIED.** Sanxion and I_Ball
   hold the volume nibble at a constant 15 for all 1000 frames, exactly like clean
   Commando. The real causes are per-tune: Arkanoid has a separate sample channel
   (`-g1`: .114 → .004), Sanxion's is filter-path and emulation-dependent
   (`-nf`: .032 → .004). I had flagged this as effect-proven / cause-inferred; the
   inference was wrong.
2. **My "isolated voices don't sum to the mix" measurement was confounded.** Those four
   renders each carried a *random* power-on delay (§K), so the poor correlation was partly
   my own measurement noise. The all-muted residual finding is unaffected — it is an RMS
   magnitude, not an alignment measure.

Scratch scripts (not in repo, under the session scratchpad):
`mute_test.py`, `mute_test2.py`.

## K. CONCURRENT WORK — commit `21917ba` (NOT mine; landed after `7ec921a`)

Authored outside this conversation in the same checkout. Two things, both of which
invalidate parts of the plan above:

**1. sidplayfp renders with a RANDOM power-on delay by default.** Documented only under
`--help-debug`. Every audio render in this repo carried a random shift of up to ~8 ms —
the same order as the millisecond onset deltas `audio_tightness_tool` reports. Three
renders of one file with identical arguments gave onset counts **152/159/156** and
`rms(difference)/rms ≈ 1.2`: two runs of the SAME file differed as much as the signal.
Compared against itself, Commando scored **148/157** matched onsets with 18 spurious
extras. Pinned to `--delay=0` (`power_on_delay=0` default in `sidplayfp_wrapper`, `None`
restores sidplayfp's behaviour) → 156/156/156, ~0.0003, self-comparison exact.
Recorded as **PATTERNS.md F5**: *a comparison tool owes you f(x,x) = perfect, or it is
measuring its own noise.*

**2. `--voice all` sweep shipped** (5 renders per side), with the isolation guard I had
listed as remaining work — but built on better data than I had:
- The residual is a **GRADIENT, not two classes** (0.2% Commando … 68% I_Ball across 12
  tunes) and it **moves with the window** (Cybernoid_II 23.8% @20s, 34.5% @12s). So the
  threshold is reasoned, not read off a histogram: warn at 5%, **REFUSE at 50%** (exit 3,
  `--allow-digi-bleed` overrides) — 50% meaning "the residual carries more energy than the
  voice". `no-signal` is distinguished from `clean` for a silent render.
- Per-voice tightness table + the **registers × audio cross-tab** via a new
  `fidelity_common.per_voice_register_agreement` (uses `score_pct` + `exercised`).
- **First result: Cybernoid_II vs its native MoN build is register-exact on all three
  voices and only 71–85% onset-matched → SYNTHESIS divergence on every voice.**

**This also answers an open question of mine:** `per_voice_register_agreement` is a
**second caller** of the harness, which was the stated test of whether the abstraction
earns its size.

</work_completed>

<work_remaining>

Ordered by value. Nothing here is blocked on anything else unless stated.

## ~~1. Single-channel comparison + digi guard~~ — **DONE in `21917ba`** (not by me)
Shipped as `audio-tightness.bat ... --voice all`, with the isolation guard, the per-voice
table and the registers × audio cross-tab. See §K. **Do not rebuild this.**

**The follow-up it created:** Cybernoid_II vs its native MoN build is **register-exact on
all three voices yet only 71–85% onset-matched** — a synthesis divergence on every voice,
invisible to every register metric in the repo. That is now the most interesting open
thread here, and it is exactly the quadrant the cross-tab was built to expose.

## 2. Supremacy `adsr` 2.3% / 4.5% on osc2/osc3 (newly visible, unexplained)
Identical on both R17 builds, so **not** an R17 regression — a pre-existing envelope gap
the old 3-column gate could not see. Reproduce:
`py -3 bin/mon_part_fidelity.py out/mon/Supremacy_sub0_part01.sf2 0 16`

## 3. Pulse scored as per-frame equality (h2g's measured finding)
`bin/mon_part_fidelity.py:113` scores `pulse%` as per-frame agreement. A phase-offset but
otherwise correct sweep scores near zero. Consider movement-count (pulse) and travel
(cutoff) instead. Bites the approximate players (DMC, Deenen, SDI, Matt Gray), not the
byte-exact ones.

## 4. The other 13 bespoke verify/sweep scripts
`bin/_verify_f4_*.py`, `_verify_f5_*.py`, `_verify_filter_*.py`, `_verify_pulse_source_edit.py`,
`_verify_variant_sources.py`, `_verify_wizax_a_f1.py`, `_verify_zetrex_yp_f1.py`,
`_validate_galway_generalize.py`, `pyscript/blackbird_sweep.py`, `blackbird_crash_probe.py`.
Porting a **second** caller onto the harness is the real test of whether the abstraction
earns its 598 lines (see the open judgement call in §E above).

## 5. Smaller / opportunistic
- `pyscript/accuracy_heatmap_generator.py` — the 5th copy of a weighted scheme. Left alone
  **deliberately**: it computes a genuinely different thing (grid-cell coverage). Re-check
  before assuming it's a bug.
- Subtune correspondence matrix (h2g §7) — SIDM2 does heavy multi-subtune work and
  `CLAUDE.md` already records Driller's `music_init` ignoring the accumulator, the same
  class of wrapper weirdness.
- Minimum-evidence floor for sweep windows (Hawkeye:3 scores on a **2-second** window).
- `CHANGELOG.md` / `STORY.md` / version bump — **not** done, and **not** required unless a
  version bump is intended (CLAUDE.md ties those to version bumps specifically).
</work_remaining>

<attempted_approaches>

## Failed / corrected during the session — do not repeat

- **`git checkout -- drivers_src/` is TOO BROAD.** It silently destroyed the
  `romuzak_driver.asm` change in commit `c067b23`, one commit from shipping a broken
  driver. Only `layout.inc` and `freqtable.inc` in that tree are build-generated;
  **`romuzak_driver.asm` is real source.** Caught because `git status` showed two files
  where three were expected. Revert generated files **by name**.
- **The `-u` mute experiment was mis-designed twice** before it produced a result:
  (1) blamed sample misalignment — cross-correlation showed lags of only 4–39 samples;
  (2) blamed DC offset — removing the mean changed nothing. The decisive test was the
  obvious one: **mute everything and expect silence.** Reach for the direct test first.
- **A test that passes on both old and new code pins nothing.** Every regression test
  written this session was verified to FAIL against the pre-fix code (via
  `git show HEAD:<file>` into a scratch module). One did *not* discriminate and was
  **relabelled in-file as a forward guard** rather than left to read as a defect pin.
- **One test's premise was wrong, not the code**: asserting a constant-held register should
  score 100%. `exercised()` correctly reports `n/a`. The test had to use a timeline that
  *moves*. Recorded in the test docstring so nobody "fixes" it back.
- **`score_pct` alone does not close the vacuous-100 class** — see §G. Cost two passes.
- **Widening `filter_trace` to a 3-tuple was started and reverted**: six sibling builders
  import it (DMC, FC, Hubbard, SDI, Sound Monitor, `_bundle_phase0`). Added a MoN-local
  `passband_trace` instead, and made the shared `traces` tuple accept 2 **or** 3 elements.
- **Three parallel subtasks were requested and declined** (for the revert/commit/R17
  sequence): they were strictly ordered and would have raced on the same git repo — the
  exact concurrency hazard flagged an hour earlier. Did 1–2 inline, delegated only the
  long one.
- **`fidelity.md` / `fidelity-tool-improvements.md` could not be found locally** — three
  independent searches (mine, a forked agent's, and a targeted one) came up empty. They
  live in the **h2g GitHub repo**, uppercase, not on this machine.
- **"use model fable" could not be honoured by a fork** — a forked worker cannot switch its
  own model mid-execution; the parent must set it at spawn time.
- `np.correlate(mode='full')` on 200k samples is far too slow — timed out at 120 s and had
  to be backgrounded.
</attempted_approaches>

<critical_context>

## Environment / invocation
- Repo: `C:\Users\mit\claude\c64server\SIDM2`, branch **master**, in sync with
  `origin/master` (`github.com/MichaelTroelsen/SIDM2conv`).
- Full suite: `py -3 -m pytest pyscript/ -q` → **1834 passed, 7 skipped, 2 xfailed,
  0 failed** (~2.5 min). Baseline at session start was 1810. The 2 warnings are
  pre-existing `PytestReturnNotNoneWarning`s in unrelated files.
- MoN builds: `py -3 bin/build_mon_native_song.py SID/Tel_Jeroen/<Tune>.sid <sub> auto`
  (~2.5 min each; the 8-target sweep is ~40 min).
- Scoring: `py -3 bin/mon_part_fidelity.py out/mon/<Tune>_sub<N>_part01.sf2 <sub> <secs>`

## Hazards that will bite again
- **NEVER run two MoN builds concurrently.** `build_mon_native_song.py:39` writes
  `drivers_src/mon/freqtable.inc` and `:1809` copies `romuzak/layout.inc` over
  `mon/layout.inc` — shared **tracked source**, not temp files. Concurrent builds silently
  corrupt each other's results. This is h2g's "do not share a workdir" lesson in a nastier
  form, and it is why `mon_struct_sweep` can never be parallelised.
- Those `.inc` files come back modified after **every** build. Revert them **by name**
  (precedent `227e6aa`), never with a directory-wide checkout (see attempted_approaches).
- **siddump force-displays every register on its first row.** This is the root of the
  vacuous-100 class and of the frame-0 artefacts in `MAIN_VOL` derivation. Assume any
  register series starts with one frame of pre-init bus state.
- sidplayfp CLI: output is `-w<path>` **attached**, input file **last** — inverse of
  SID2WAV. Exit 0 on success (VICE's `vsid` exits 1 on *normal* termination).
- `scripts/sid_to_sf2.py` **refuses to write to a path that already exists**.
- **sidplayfp's `--delay` defaults to RANDOM** (documented only under `--help-debug`),
  giving every render a random shift of up to ~8 ms. `sidplayfp_wrapper` now pins
  `power_on_delay=0`; pass `None` only if you deliberately want hardware-like
  irreproducibility. Any measurement taken from renders made BEFORE `21917ba`
  (including my `-u` mute-summing experiment) carries this noise.

## Design rules established this session
- **Two guards, always:** `score_pct` (were there frames?) + `exercised` (did they carry
  information?). Route new scorers through `sidm2/fidelity_common.py`; do not write a
  sixth copy of the weighted-accuracy scheme.
- `compare_runs` refuses on mismatched *measurement* settings, surfaces mismatched
  *build options* as the change under test.
- Columns are **appended**, never inserted, so saved baselines and existing regexes
  (`OSC_RE`) keep parsing.
- A shared helper is not widened for one caller (`filter_trace` stayed a 2-tuple).

## Open judgement call (flagged to the user, not resolved)
The `mon_struct_sweep.py` port **grew** the file (139→176) against a stated acceptance
criterion of "if it doesn't shrink, the abstraction is wrong — redesign." The subagent
argued the A/B *decision* logic shrank and the rest is new capability, and did not
redesign. **A second caller is the test** — and `21917ba` supplied one
(`fidelity_common.per_voice_register_agreement`), independently of this question. Judge
the abstraction on that before porting the remaining 13.

## Verified-vs-assumed
- **Verified:** every `$D418` before/after number; the 50%/25%/100% pre-fix scores; the
  `-u` mute residuals; test counts; Cybernoid's structural no-regression guarantee.
- **FALSIFIED (was my inference):** `$D418` digi is NOT the `-u` bleed mechanism —
  refuted in `21917ba`. The effect was real, the cause was wrong; per-tune causes are a
  separate sample channel (Arkanoid) or a filter-path/emulation artifact (Sanxion).
- **NOT verified:** the R17 corpus table (the subagent's, not independently re-run —
  ~40 min); h2g's own corpus figures (their measurements, quoted as theirs).
</critical_context>

<current_state>

## Complete and pushed
Working tree **clean**, `HEAD == origin/master` at **`7ec921a`**.

Session commits, oldest first:
| commit | what |
|---|---|
| `32a0e0c` | sidplayfp replaces SID2WAV.EXE |
| `2ace9e7` | CI artifact-action deprecation + bandit High/Medium |
| `72dd1ab` | Test Summary: artifact that was never produced |
| `1ec22b1` | Test Summary: missing PR-comment permission |
| `9f05787` | Batch Testing: file archived 4 months ago |
| `f6a65a1` | retire the batch-pyautogui launcher + 9 doc files |
| `c4fc9ce` | **PR #17 merged** (squash) |
| `ffa07b1` | add `mon_struct_sweep.py` |
| `3a329d2` | shared A/B baseline harness + dimension registry |
| `67fa1c6` | widen the R17 gate — **R17 settled** |
| `9b1a0f0` | identical captures scored 50% |
| `2bc8c14` | `validate_sid_accuracy` delegates |
| `05bd7db` | `register_accuracy` compared write sequences |
| `649e076` | vacuous-score class closed across 4 more scorers |
| `464406a` | MoN passband (`$1F`/`$3F`) |
| `c067b23` | MoN master volume (`MAIN_VOL`) |
| `7ec921a` | docs (project rule 3) |

**PR #17 MERGED**, 27/27 checks green. Branch `mattgray-driller-stage-a` kept (not deleted).

## Not started
Everything in `<work_remaining>`. Single-channel comparison is **designed with its blocker
resolved** but no code written.

## Temporary / not in the repo
- Scratchpad: h2g doc copies, `mute_test.py`, `mute_test2.py`, rendered WAVs, and
  `old_accuracy.py` / `old2_accuracy.py` (pre-fix modules extracted via `git show` for
  proving tests fail against them). None are needed to continue.
- `out/mon/*.sf2` build artifacts for Cybernoid, Cybernoid_II, Hawkeye, Supremacy sub0
  exist from verification runs.

## Open questions
1. Does the harness abstraction earn its size? A second caller now exists
   (`per_voice_register_agreement`, `21917ba`) — assess it rather than waiting.
2. What causes Supremacy's `adsr` 2.3%/4.5%?
3. ~~Is `$D418` digi the `-u` bleed mechanism?~~ **Answered: no** (`21917ba`). Open
   instead: why is Cybernoid_II register-exact but only 71-85% onset-matched?
4. ~~Threshold for the digi guard.~~ **Chosen in `21917ba`**: warn 5%, refuse 50%, and
   the spread turned out to be a gradient rather than two classes.
</current_state>
