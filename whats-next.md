<original_task>
"Please continue the SID2SID and WAV2WAV comparison tools. We need to find a way for you to
listen."

Scope as clarified by the user in the first turn (via AskUserQuestion):

1. **Tool scope**: extend `pyscript/audio_tightness_tool.py` to accept `.sid` or `.wav` inputs
   interchangeably — NOT two new separate scripts.
2. **"A way for you to listen"**: BOTH numeric features as text AND spectrograms as a backup for
   ambiguous cases.

Everything after that (the five improvement items, CLAP, the calibration, the CLAUDE.md
compression, the version bump) grew out of this and was individually requested by the user.
</original_task>

<work_completed>

## Final state: 16 commits this session, all pushed. HEAD = `fe9846b`, `origin/master` in sync
(0 ahead / 0 behind), working tree clean. Tests: ~1,900 → **2,075 collected / 2,065 passing**.
Version bumped 3.22.0 → **3.23.0** (2026-08-09).

### Commits (oldest → newest), all on `master`, all pushed
| SHA | Subject |
|---|---|
| `acf5faf` | feat: whole-file audio feature report + spectrogram in audio_tightness_tool |
| `10c74ef` | docs: VSID vs sidplayfp renderer comparison, parameter audit, pipeline assessment |
| `de21355` | feat: per-voice WAV stem export via sidplayfp |
| `8475807` | feat: CLAP audio-embedding bridge, isolated from the project's numpy |
| `558d15f` | docs: CLAP fails its validation gate on SID material; listening-tool assessment |
| `63563c3` | fix: pin VSID's sample rate to 44100 Hz to match sidplayfp |
| `9e80b9f` | feat: pitch-class chroma and section-aware windowed features |
| `5e2f836` | feat: calibrate the listening metrics against the one recorded human verdict |
| `ebc8983` | feat: opt-in mel-scale band spacing for the audio feature summary |
| `b754a0c` | feat: A-weighted loudness alongside raw dBFS in the feature summary |
| `b2eb6c3` | calibration: measure improvements #1 and #2 against the B13 case |
| `13319da` | fix: sparse metrics scored infinitely in the windowed outlier search |
| `e10ecc9` | release: v3.23.0 — audio-domain listening tooling, calibrated |
| `e6cceba` | docs: correct the audio-tightness guide's framing, index the listening tooling |
| `c09fd9c` | docs: compress CLAUDE.md's Known Limitations, audit-gated |
| `fe9846b` | docs: re-stamp ACCURACY_MATRIX.md to v3.23.0, and stop the stamp duplicating |

The push `69c806f..fe9846b` carried 32 commits — 16 from this session plus 16 pre-existing local
commits (the Hubbard/MoN `$D418` arc) that had never been pushed.

---

## 1. The original ask — "a way to listen"

**FINDING FIRST**: SID2SID and WAV2WAV **already worked**. `audio_tightness_tool.py`'s
`resolve_input()` already accepted `.sid`/`.sf2`/`.wav` on either side. No code change was needed
there; this was verified, documented, and NOT re-implemented.

**NEW: `sidm2/audio_listen.py`** (43,639 bytes at HEAD). numpy + Pillow only — deliberately no
matplotlib/librosa/scipy, matching `audio_tightness.py`'s style and this project's installed set.
Contents:
- `extract_features()` → `AudioFeatures` (duration, rms_db_mean/max, silence_frac,
  centroid_hz_mean/std, rolloff85_hz_mean, zcr_mean, flatness_mean, **rms_dba_mean/max**,
  **chroma** 12-vector, band_scale)
- `format_feature_report()` — side-by-side orig/driver + deltas, as text for Claude
- `render_comparison_spectrogram()` — 3-panel PNG (original / driver / dB-diff), hand-rolled
  inferno + diverging colormaps, viewable with the Read tool
- `chroma_vector()`, `chroma_shift_description()`, `dominant_pitch_classes()` (#5)
- `extract_features_windowed()`, `worst_window()`, `format_windowed_diff_report()`,
  `WindowOutlier`, `_robust_spread()`, `_metric_scale()` (#4)
- `a_weight_db()`, `a_weighting_correction_db()` (#2)
- `hz_to_mel`/`mel_to_hz`/`band_edges`/`band_centers`/`undersampled_bands` live in
  `sidm2/audio_tightness.py` (#1); `band_energies(scale=)`, `_logmel(scale=)`

**CLI flags added** to `pyscript/audio_tightness_tool.py`: `--spectrogram [PATH]`, `--no-listen`,
`--windowed [SECONDS]`, `--band-scale {linear,mel}`.

## 2. Per-voice WAV stem export (`de21355`)
- `AudioExportIntegration.export_voice_stems()` + `VOICE_MUTE_MAP` in
  `sidm2/audio_export_wrapper.py` — writes `<name>_voice1/2/3.wav` beside the mix.
- Forces sidplayfp (VSID has **no** per-voice mute at all), pins `power_on_delay=0` for
  reproducibility, warns that muting is not clean isolation (digi-bleed worst case 58.7%).
- Wired to `--audio-export-voices` (`scripts/sid_to_sf2.py`) and `config.export_audio_voices`
  (`sidm2/conversion_pipeline.py`).
- `pyscript/test_audio_export_wrapper.py` — 11 tests, sidplayfp mocked (no binary needed).

## 3. VSID/sidplayfp comparison + sample-rate fix
- `docs/VSID_VS_SIDPLAYFP_COMPARISON.md`: 6 songs × 2 renderers, run at **20 s and 60 s**.
- **Finding 2 was self-corrected**: a "-10.0 ms offset, zero scatter" at 20 s read **0.0 ms** at
  60 s. Both are adjacent bins of the detector's 10 ms hop; the true offset is sub-resolution.
  The doc retracts the original explanation.
- `63563c3` pins VSID to `-soundrate 44100`; `VSIDIntegration.export_to_wav()`'s `frequency`
  param was **accepted and silently ignored** — now actually passed.

## 4. CLAP audio embeddings — BUILT, VALIDATED, REJECTED, UNINSTALLED
- `sidm2/audio_embed.py` (8,867 b) — subprocess bridge, numpy-only, never imports torch.
- `pyscript/clap_worker.py` — venv-side; **duplicates real fd 1 and points fd 1 at stderr** before
  loading anything (the checkpoint loader prints hundreds of lines from native code that would
  desync the JSON protocol). This was load-bearing, not defensive — verified in practice.
- `pyscript/install_clap.py`, `pyscript/clap_validate.py`, `pyscript/test_audio_embed.py` (19
  tests, worker faked — run without torch).
- **Validation result (the reason it was rejected)**: separation = `min(same-tune) − max(cross-tune)`
  - 4 tunes / 20 s → **−0.053** FAIL
  - 4 tunes / 60 s → **+0.006** PASS (meaningless margin)
  - **9 tunes / 60 s → −0.413 FAIL, decisively**
  Different compositions score up to **0.947** while a same-tune pair falls to **0.534**.
- Recorded in `docs/CLAP_EMBEDDING_NEGATIVE_RESULT.md`.
- **`tools/clap_venv` UNINSTALLED at the user's request** (3.2 GB reclaimed). The bridge code and
  docs are kept; `pyscript/install_clap.py --uninstall` / re-run reinstalls.

## 5. The five improvements (all from `docs/AUDIO_LISTENING_IMPROVEMENT_PLANS.md`)
| # | Item | Commit | Tests | Verdict vs the B13 case |
|---|---|---|---|---|
| 1 | Mel-scale bands (opt-in) | `ebc8983` | 42 | **Unproven** — 2 of 3 metrics improve, margins too small for n=1 |
| 2 | A-weighting | `b754a0c` | 22 | **Clear win** — separation 0.294 → 1.585 (5.4×) |
| 3 | Calibration manifest | `5e2f836`,`b2eb6c3` | 14 | *is* the evidence |
| 4 | Windowed features | `9e80b9f` | 31 | Works **only with `silence_frac` excluded** |
| 5 | Chroma | `9e80b9f` | 23 | **Correct null** — percussive defect, no pitch shift, none reported |

## 6. The calibration (`5e2f836`, `b2eb6c3`) — the most important deliverable
Rebuilt the **exact B13 artifacts** via a throwaway `git worktree` at commit **`d946701`**
("Blackbird Stage B12+B13"), the build a human listened to and called *"something with the perc or
drums"*. Built Glyptodont there and at HEAD.

| comparison | onset match |
|---|---:|
| original vs **itself**, phase-perturbed — the floor | **85.4–91.3 %** |
| original vs HEAD build (99.8 % register, 162/162 note-ons) | **64.7 %** |
| original vs B13 build (the one that sounded wrong) | **56.9 %** |

**Conclusion: ordinal sensitivity, NO usable absolute gate.** A near-perfect build scores 20+
points below what the original scores against itself, so any threshold flagging B13 condemns the
good build too. The deficit is systematic (SID render vs native-driver SF2 render), not a defect.

Feature separations (`|Δbad| − |Δgood|`, positive = informative):
`rms_dba +1.585`, `rms_dbfs +0.294`, `flatness_mel +0.022`, `flatness_linear +0.019`,
`centroid_mel −17.408`, `centroid_linear −18.613`, `rolloff_mel −77.106`, `rolloff_linear −75.441`.
Negative centroid/rolloff = **confound**, not anti-information: the good build has more content
(32 instruments vs 31, 26.9 KB vs 20.8 KB), so more song plays and the whole-file average shifts.

Artifacts: `pyscript/calibration_cases.json` (9,384 b, append-only, findings self-tested),
`pyscript/test_audio_listen_calibration.py`, `docs/AUDIO_LISTENING_CALIBRATION.md`.

## 7. Bugs found and fixed (all by running against real material, none by review)
1. **`worst_window()` returned `inf`** (`13319da`) — `silence_frac` is 0 in 7/12 windows → median 0
   → `_metric_scale()` returned 0 → divide-by-zero. It won every ranking and flagged good and bad
   builds identically. Fixed: sparse metrics fall back to the mean.
2. **`UnicodeDecodeError` in BOTH render wrappers** (`5e2f836`) — strict cp1252 decoding of
   subprocess output raised inside subprocess's **reader thread**, uncatchable by the surrounding
   try/except. Fixed with `errors='replace'`.
3. **VSID sample rate** (`63563c3`), see §3.
4. **pyflakes regression I introduced** in `acf5faf` — `-> "Image.Image"` annotations with `Image`
   imported only inside function bodies. Fixed with a `TYPE_CHECKING` import. I had run only the
   audio subset instead of the full suite; the project rule exists for exactly this.

## 8. Documentation
New: `docs/AUDIO_LISTENING_CALIBRATION.md`, `docs/AUDIO_LISTENING_CAPABILITY_ASSESSMENT.md`,
`docs/AUDIO_LISTENING_IMPROVEMENT_PLANS.md`, `docs/CLAP_EMBEDDING_NEGATIVE_RESULT.md`,
`docs/VSID_VS_SIDPLAYFP_COMPARISON.md`, `DOC-AUDIT.md`.
Updated: `CHANGELOG.md` (3.23.0), `STORY.md`, `sidm2/__init__.py`, `CLAUDE.md`,
`docs/guides/AUDIO_TIGHTNESS_GUIDE.md`, `docs/reference/ACCURACY_MATRIX.md`, `audio-tightness.bat`.

## 9. CLAUDE.md compression, audit-gated (`c09fd9c`, `fe9846b`)
Ran the **audit-docs skill** first (`DOC-AUDIT.md`) rather than trimming on impression.
- **P1**: Known Limitations is a THIRD copy — **15/15 players** appear in both CLAUDE.md and
  `ACCURACY_MATRIX.md` (which CLAUDE.md itself calls "accuracy source of truth"), and each has a
  `docs/players/` doc. The copies **had drifted** (matrix v3.22.0 vs shipped 3.23.0).
- All 3 named caveats verified to **survive in the player docs in stronger form** (MON.md has a
  dedicated `$D418` heading; DMC.md has "ELIGIBLE IS NOT AN ACCURACY FIGURE" and "EVERY DMC
  PERCENTAGE IS WINDOW-DEPENDENT" as bolded standalone statements).
- Compressed rows 12,546 → 5,973 b (**−52 %**); **17/17 caveats verified present after the edit**.
- CLAUDE.md overall **31,842 → 25,201 b (−21 %, ~1,660 tokens/session)**.
- Version-bump checklist now names `ACCURACY_MATRIX.md` (fixing the cause, not the symptom).
- Footer now states bytes/tokens, not lines — the file drifted to 32 KB *while inside* its ~215-line
  budget because prose migrated into table cells.
- `fe9846b` re-stamped the matrix to 3.23.0 **after verifying no conversion path changed**, and
  **removed** the duplicate version from CLAUDE.md's pointer rather than updating it.
</work_completed>

<work_remaining>

### A. Open items

1. **`worst_window()`'s silence_frac swamping — FIXED 2026-08-09.** Root cause: the confound
   (driver never reproduces the original's startup silence) is **one-directional** — delta
   (driver − orig) is negative in nearly every window regardless of build quality. Fix:
   `_only_more_silent()` in `sidm2/audio_listen.py` clips that direction to 0 before ranking,
   rather than dropping the metric outright, so a driver that genuinely goes silent mid-song (the
   *opposite* direction) is still caught. Verified **live**, not just synthetically: rebuilt the
   real B13 bad SF2 in a throwaway `git worktree` at `d946701` and re-ran against HEAD's good
   build, both vs the real 60s sidplayfp render of `SID/LFT/Glyptodont.sid`. Silence's score is now
   **0.0 for both builds** (fully defanged); the ranking separates cleanly — bad = centroid
   +150.0 Hz @15.0s (score 2.58), good = RMS +4.35 dB @0.0s (score 2.22) — matching the shape the
   prior "excluding silence_frac" workaround predicted. `pyscript/calibration_cases.json`'s
   `windowed` block and `sidm2/audio_listen.py`'s comment above `_WINDOW_METRICS` updated with the
   live numbers. 5 new tests in `pyscript/test_audio_listen_windowed.py`
   (`TestSilenceFracOnlyFlagsGoingMoreSilent`), full suite 2065→**2069 passing**, zero regressions.
   **Residual, unmeasured**: the two scoring branches (sigma vs flat-baseline) still are not
   range-comparable in general — that was never shown to matter for any metric other than
   silence_frac's confound, which is now handled at the source, so it was not chased further.

2. **A second calibration case was added — DONE 2026-08-09.**
   `blackbird-glyptodont-e3e-drums-not-tight`: same tune as B13 but a deliberately DIFFERENT,
   near-isolated commit range (`ef3263b` B25 → `12c7da5` E3e), chosen because the human verdict
   ("sounds really good, [but] something not right with the drums... might be filters") was
   recorded *after* B25 shipped a register-accuracy improvement (97.1%→97.5%) that did **not**
   resolve the complaint — a real instance of the registers-vs-audio gap this tooling exists to
   catch, not a hypothetical one. Measured independently end-to-end (own repeatability-floor
   script, own worst_window rerun) rather than reusing B13's numbers. **Result: every finding
   replicates** — orders correctly (56.8<65.2), no usable absolute gate (floor 84.3–99.8%),
   `rms_dba_aweighted` is again the best feature (3.0× vs 1.5×), mel improves the same 2-of-3
   metrics, centroid/rolloff show the same negative-separation completeness confound, chroma is
   again a correct null, and `worst_window()`'s post-fix ranking lands on the *same* window indices*
   (bad=centroid @15.0s window 3, good=RMS @0.0s window 0) as B13 despite being a wholly different
   defect — independent evidence the silence_frac fix (item A1) generalizes rather than being
   fitted to one tune. First attempt (Cybernoid/MoN, the SBC-carry-bug case) was **abandoned**
   this turn on a false lead (see the correction below — **there was no real gap**, it was my own
   CLI mistake) and not retried; a genuine third case from the SBC-carry-bug defect is still
   possible later if wanted. 14/14 manifest consistency checks passed on first write — every
   hand-computed finding number was correct.

   **CORRECTION (2026-08-09, later turn)**: the "MoN-family sidplayfp silent-after-1s" finding
   below was **WRONG — not a project bug**. I had reused `mon_sf2_validate.py`'s
   `--driver-play 0x1006`, which is that script's OWN one-off ad-hoc Stage-A probe address
   (`GalwayDriver11Song`/`galway_driver11_emitter`), not the address the real native driver
   `bin/build_mon_native_song.py` actually produces. That driver reuses the ROMUZAK template
   (`bin/build_romuzak_driver_full.py`: `DRV_INIT=0x1000, DRV_PLAY=0x1003, DRV_STOP=0x1006`) — the
   same convention as Blackbird. I was calling the **stop** routine every frame instead of
   **play**, which explains the ~1s-then-silence shape exactly (SID muted by the stop routine, not
   a crash). Re-rendered with `--driver-play 0x1003`: full, continuous, normal-sounding audio for
   the whole 10s test (RMS steady ~0.08-0.15 throughout, vs decaying to 0.0 at 1s). **MoN-family
   SF2s render fine via sidplayfp; there is no pipeline gap.** The "NEW GAP FOUND" row in the
   deliverable-status table below and the corresponding open question are both stale as of this
   correction.

3. **`docs/players/` still duplicates the accuracy figures.** Only CLAUDE.md's copy was compressed.
   `ACCURACY_MATRIX.md` + 21 player docs still both carry them. The duplication root cause is
   reduced, not eliminated.

4. **Python Tools section of CLAUDE.md deliberately NOT trimmed** (~7.2 KB). I reversed my own
   recommendation after reading it: it is anti-footgun operational guidance ("do not write a new
   one", "check the exit code, don't just parse stderr", "a too-short window looks identical to a
   broken trace", "vsid exits 1 on normal termination"), not duplicated narrative. **Do not trim
   it without reading it first.**

### B. Never verified (would need the project's own agent)
5. **Every accuracy percentage in CLAUDE.md / ACCURACY_MATRIX.md is UNVERIFIED by this session.**
   The audit routed them to `.claude/agents/sidm2-fidelity-falsify.md` per the workflow's step 3b.
   They are neither confirmed nor disconfirmed. If they matter, run that agent.

6. **Sensitivity to a synthesis defect was never directly measured.** The CLAP rejection and the
   calibration both tested cross-tune discrimination and same-tune-different-phase. Nobody measured
   whether the tooling detects a subtle envelope/synthesis error within one tune. The inference is
   *a fortiori* (if it can't separate Commando from Angular it can't catch a subtle defect), which
   is reasoning, not measurement. The docs say so.

### C. Suggested next steps, in order
1. ~~Decide the `silence_frac` question (A1)~~ — **DONE 2026-08-09**, see item A1 above.
2. ~~Add a second calibration case (A2)~~ — **DONE 2026-08-09**, see item A2 above.
3. Consider whether `docs/players/` or `ACCURACY_MATRIX.md` should be the single home (A3).
</work_remaining>

<attempted_approaches>

### Failed / rejected, with reasons — DO NOT REPEAT
1. **CLAP audio embeddings.** Fully built, then rejected on measurement. Failure mode: longer
   renders made discrimination **worse** (cross-tune median 0.616 → 0.767) — a general-audio model
   collapsing toward a genre centroid. All C64 SID sounds like "C64 SID" to it. **The user's
   intuition that "simple songs should be easy" is inverted**: simple + homogeneous means *less*
   between-class variance, so discrimination is harder, not easier. Re-testing needs a
   domain-specific or fine-tuned checkpoint, and `clap_validate.py` already generates the training
   signal (same-tune = positive, cross-tune = negative).
2. **A 4-tune/60 s CLAP PASS at +0.006 was a small-sample artifact** — widening to 9 tunes inverted
   it to −0.413. **Any future re-test must vary the CORPUS, not just the render length.**
3. **`numpy<2.0` in the main environment** — never attempted; laion-clap pins it against this
   project's 2.5.1 and would force a project-wide downgrade.
4. **Python 3.14 for the CLAP venv** — FAILED. numpy 1.x has no wheels above **cp312**; pip built
   from source and it died on import in numpy's own `getlimits` ("cannot convert longdouble
   infinity to integer"). The installer now auto-detects ≤3.12 and refuses newer with that reason.
5. **`venv.EnvBuilder`** — wrong tool: it clones the *running* interpreter (3.14). The installer
   shells out to `<base_python> -m venv` instead.
6. **Three laion-clap packaging bugs**: `torch`, `torchvision`, `torchaudio` are all imported at
   module scope and **none are declared** as dependencies. Each surfaced one at a time. `timm` and
   `open_clip` are also imported but sit behind guarded try-blocks (not needed).
7. **Exact-substring matching to test caveat survival** — FAILED, produced false "missing" verdicts
   on caveats I had already read in the player docs. The docs paraphrase. Semantic survival cannot
   be checked mechanically; this is why the compression **kept all caveats inline** instead.
8. **Naive path-existence check on CLAUDE.md** — FAILED, reported 18 dead references; all 15 real
   files resolved repo-wide. The check assumed root-relative paths; docs cite bare basenames.
9. **`rg` via Python `subprocess`** — `FileNotFoundError` in this environment. Use the Grep tool or
   in-process Python search.
10. **Piping an installer through `| tail`** — masked the real exit code (`tail`'s 0), making a
    failed install look successful. Cost one wasted round trip.

### Considered but not pursued
- **Pretrained alternatives to CLAP**: `panns-inference` (drags in librosa/matplotlib — the exact
  deps `audio_listen.py` avoids), `torchvggish` (PyPI last released 2022, undeclared deps),
  `openl3` (needs TensorFlow *in addition to* torch).
- **A human-in-the-loop calibration workflow** — offered as the cheapest option; user chose CLAP
  first, then the calibration was built anyway as improvement #3.
</attempted_approaches>

<critical_context>

### The single most important finding
**The tooling does NOT replace human listening, and this is now measured rather than asserted.**
Ordinal sensitivity, no absolute gate. Quote any onset number **against a baseline build or the
repeatability floor, never alone**, and **measure the floor per tune** (85–91 % is Glyptodont's, not
a constant). `docs/guides/AUDIO_TIGHTNESS_GUIDE.md` previously implied the tool caught the B13
defect class; that is corrected at the top of the section making the claim.

### The recurring pattern — the most transferable lesson
**Four of the five planned improvements would have shipped a *confidently wrong* number that their
own unit test passed:**
| # | Plan's approach | Would have shipped |
|---|---|---|
| 1 | linear band spacing | 100 Hz vs 200 Hz (a full octave) both peak in band 0; CLI prints **−0.0 Hz** for a doubling |
| 2 | band-centre A-weight lookup | **+12.8 dB** error at 55 Hz — and the plan's own 60 Hz test still passed |
| 4 | std-based z-score | one outlier among n identical values caps z at n/√(n−1) = **2.5** vs a 3.0 threshold → "no section stands out" |
| 5 | 40 ms chroma window | 55 Hz bass classified **G instead of A**, +0.385 margin |
Plus the `inf` bug (#4) and CLAP's 4-tune false PASS. **Every one is a confident null or a
confident wrong answer, not a noisy one** — the shape that gets believed. None were caught by
review; all fell out of running against real material and checking against an external reference
(published IEC table, a known pitch, the z-score's arithmetic ceiling, a wider corpus).
**Corollary: a check returning "nothing here" deserves the same scrutiny as a surprising finding.**

### Environment / setup gotchas
- **Python 3.14.6** is the project interpreter; **3.12 also installed** (`py -3.12`) and is what the
  CLAP venv needs.
- **Windows console is cp1252** — printing `→`/`✅` from Python raises `UnicodeEncodeError`. Use
  `PYTHONIOENCODING=utf-8`.
- **`rg` is not directly invocable** via subprocess; the Grep tool works.
- **`git stash` is unsafe here** — a fork ran `git stash push` on a path with no changes (so no
  stash was created), then `git stash pop` took a **pre-existing unrelated stash** (SDI Stage B),
  applying 4 foreign files. Recovered; verified intact. **Always check `git stash list` first.**
- **`stash@{0}` = "SDI Stage B: leading rest for late-entering voices"** — PRE-EXISTING, predates
  this session, deliberately untouched. Do not pop it blindly.
- **Blackbird native driver**: `--driver-init 0x1000 --driver-play 0x1003` (from
  `bin/build_blackbird_driver_full.py`'s `DRV_INIT`/`DRV_PLAY`). Required — the SF2 has no Block 2
  header and the Driver-11 default guess is wrong.
- **Building a player writes `drivers_src/<player>/*.inc`** — per-song generated artifacts that are
  tracked. My Glyptodont build dirtied `drivers_src/blackbird/*.inc`; I reverted them. **Check
  `git status` after any build.**
- **sidplayfp's `--delay` defaults to RANDOM**; this project pins `power_on_delay=0` for
  reproducibility. VSID has **no** equivalent knob.
- **CLAP wants 48 kHz**; the filelist API loads/resamples itself, so 44.1 kHz renders are fine.

### Measurement discipline this codebase enforces (and why)
- `sidm2/fidelity_common.py` — **do not write a new scorer**. `score_pct` returns `None` (never
  100.0/0.0) when `tot == 0`; `exercised()` catches the case where siddump force-displays every
  register on its first row, so a never-filtered tune scores a confident 100 %. Five separate
  copies of the same scheme existed, each independently broken; one scored **two identical captures
  at 50 %**.
- The **repeatability floor** pattern (`measure_repeatability_floor`) is the template used for both
  the CLAP gate and the calibration: *a metric is evidence only when it beats what the same input
  scores against itself.*
- `.claude/agents/sidm2-fidelity-falsify.md` exists and **owns accuracy claims**. Don't adjudicate
  them with weaker tools.

### Decisions and trade-offs
- **CLAP bridge kept, venv uninstalled** — inert when unused, 19 torch-free tests, so a future
  re-test is just `install_clap.py` + `clap_validate.py`.
- **Known Limitations compressed, Python Tools not** — the first is duplicated narrative, the second
  is anti-footgun guidance whose value depends on being read inline.
- **CLAUDE.md's version pointer to the matrix was DELETED, not updated** — updating it would have
  recreated the duplication that caused the drift.
- **Chroma's floor is C1 (32.7 Hz), not the planned C2** — SID bass runs to 55 Hz and a C2 floor
  would discard the register the 200 ms window exists to resolve.
- **`rms_dba_*` deliberately excluded from `_WINDOW_METRICS`** — dBA and dBFS are near-duplicates
  there and would give level two chances to win the max-normalized ranking.
</critical_context>

<current_state>

### Nothing is in-flight. Commit pending at the time of this edit (about to be made).
- Previous snapshot: HEAD `fe9846b`, 2,065 passing. **Since then (2026-08-09, this turn)**:
  1. Fixed `worst_window()`'s silence_frac swamping (item A1, commit `11a64ec`).
  2. Added a second calibration case (item A2, commit pending) — `blackbird-glyptodont-e3e-
     drums-not-tight`, which independently replicated every finding from the B13 case.
  Tests now **2,069 passing** (net +4 from A1; A2 added no code, only a JSON manifest entry), 8
  skipped, 2 xfailed, 0 failures.
- Working tree kept clean throughout: TWO throwaway `git worktree` builds this turn (Blackbird at
  `ef3263b`/`12c7da5` for A2, plus one abandoned Cybernoid/MoN attempt at `d946701`-era commit)
  dirtied tracked generated files (`drivers_src/blackbird/*.inc`, `drivers_src/mon/*.inc`,
  `drivers_src/romuzak/layout.inc`) — all reverted via `git checkout --`, confirmed via
  `git status` before each commit. All throwaway worktrees removed after use.
- **Version 3.23.0** consistent across all four canonical places: `sidm2/__init__.py`,
  `CHANGELOG.md`, `CLAUDE.md` header, `docs/reference/ACCURACY_MATRIX.md`. Not bumped for either
  A1 or A2 (both are within the already-shipped listening tooling, not new features).
- **`tools/clap_venv` does NOT exist** (uninstalled). `clap_validate.py` degrades to a clear
  actionable error; its 19 tests still pass.
- **`stash@{0}`** (SDI Stage B) is intact and untouched — pre-existing, not mine.
- **RETRACTED (2026-08-09, later turn): there was no MoN-audio-rendering gap.** The prior finding
  ("MoN-family SF2s render ~1s then go silent under sidplayfp") was **my own CLI mistake**, not a
  project bug — see the correction under item A2 above for the root cause
  (`--driver-play 0x1006`, the wrong script's constant, calls the driver's STOP routine every
  frame instead of PLAY at `0x1003`). Re-verified with the correct address: full, normal, ~10s of
  continuous audio, no silence. Nothing to fix, no gap to track.

### Deliverable status
| Item | Status |
|---|---|
| "A way to listen" (features + spectrograms + chroma + windows) | **COMPLETE, shipped** |
| SID2SID / WAV2WAV | **COMPLETE** — already worked, verified + documented |
| Per-voice stem export | **COMPLETE**, wired to CLI + pipeline config |
| Improvements #1–#5 | **COMPLETE**, all committed and tested |
| Calibration against a human verdict | **COMPLETE, 2 cases**, second REPLICATES the first independently |
| CLAP | **REJECTED on measurement**, code kept, venv removed |
| v3.23.0 release (CHANGELOG/STORY/version) | **COMPLETE** |
| CLAUDE.md compression | **COMPLETE** (−21 %), audit in `DOC-AUDIT.md` |
| `worst_window()` silence_frac limitation | **FIXED 2026-08-09**, verified live against 2 independent cases |
| MoN/Cybernoid audio-domain rendering | **RETRACTED — no gap, was my CLI mistake** (see above) |
| Accuracy percentages verified | **NOT DONE — out of scope, routed to the falsify agent** |

### Open questions for the user
1. Should `ACCURACY_MATRIX.md` or `docs/players/` be the single home for accuracy figures? Two
   copies remain.
2. Now that MoN-family audio rendering is confirmed to work (`--driver-play 0x1003`), is a THIRD
   calibration case worth building from the original Cybernoid SBC-carry-bug defect ("Cybernoid's
   lead sounds wrong when vibrating", commit `699c878`)? Nothing blocks it now.
</current_state>
