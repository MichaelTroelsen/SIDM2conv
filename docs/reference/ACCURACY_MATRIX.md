# SIDM2 Conversion Accuracy Matrix
**Single Source of Truth for Accuracy Data**

**Version**: 3.24.0
**Last Updated**: 2026-08-09
**Figures last re-measured**: v3.22.0 — unchanged in v3.23.0/v3.24.0 for every pre-existing row, and verified rather than assumed. The **HardTrack Composer** row is newly measured in v3.24.0.
Neither release altered a conversion path. v3.23.0: `git diff 3e42a8c..0498d05 -- bin/ drivers_src/
sidm2/ scripts/` touched only measurement/rendering code plus two pure additions to
`scripts/sid_to_sf2.py` and `sidm2/conversion_pipeline.py`, both wholly inside opt-in
`--audio-export-voices` / `config.export_audio_voices` guards, with no deletions or edits to
existing logic. v3.24.0 added `sidm2/hardtrack_parser.py` as a **new file only** — no existing
module was edited, and HardTrack is not wired into `DriverSelector`, so it cannot reach any
conversion path at all. Nothing that produces a number below was modified, so no number below
moved.
**Status**: ✅ Production Reference — refreshed v3.22.0 (Blackbird/lft added), Matt Gray row
added 2026-07-30. **15 ported player families** are now listed (the v3.14.0–v3.20.0 arrivals —
Hubbard, DMC, Sound Monitor, SDI — had been missing since v3.13.0; Matt Gray, RE'd 2026-07-25,
was missing until now). Counting rule: one row per locator/parser family — Myth and Supremacy
are sub-rows under MoN, not separate counts.

> **Provenance:** every row below was **re-measured on 2026-07-16** — Hubbard, DMC, Sound
> Monitor and SDI by an adversarial audit (`.claude/agents/sidm2-fidelity-falsify.md`),
> Kimmel and Deenen against their validators. The audit's finding: **no headline
> percentage was wrong** — SM's 99.23% reproduces to the digit, SDI's medians within 0.2
> on a full 324-file sweep, Balloon's 100×3 exact over 19996 frames. What was wrong was
> the *packaging*: vacuous claims (Hubbard's "filter 100%" — a register the player never
> writes), unstated windows, build counts sitting in an accuracy column, and a lost
> `win`/`strict` label. Those are corrected here.
>
> **Read the caveats in each row, not just the number.** A percentage without its window,
> its n, and whether the metric was fitted is not a measurement.

---

## Quick Reference — wired pipeline (auto driver selection)

| Source Player | Best Driver | Accuracy | Status |
|---------------|-------------|----------|--------|
| **Laxity NewPlayer v21** (native) | Laxity Driver | **99.93–100%** | ⭐⭐⭐⭐⭐ Production (filter 100%, Stinsen-verified) |
| **SF2-exported SID** (incl. SidFactory_II/Laxity) | Driver 11 | **100%** | ⭐⭐⭐⭐⭐ Guaranteed |
| **Martin Galway** (Stage A default) | Driver 11 transpile | notes/timing exact; timbre approximated | ⭐⭐⭐ Editable |
| **NewPlayer 20.G4** | NP20 Driver | **70–90%** | ⭐⭐⭐ Best effort |
| **Unknown Player** | Driver 11 | varies | ⭐⭐ Safe default |

**⚠️** "Laxity" can mean the AUTHOR (SF2-exported → Driver 11) or the PLAYER FORMAT (→ Laxity driver). Check player-id output.

## Quick Reference — native-driver builds (`bin/`, not yet registry-wired)

Per-frame register fidelity (freq / waveform / pulse / filter) measured vs the original SID; "byte-exact" = 100% on every register over the full song.

| Source Player | Entry point | Fidelity | Status |
|---------------|-------------|----------|--------|
| **Martin Galway** (40-tune corpus) | `bin/build_galway_trace_song.py`, corpus `bin/build_galway_corpus.py` | ~100% on every register for validated tunes; **30/40 objectively clean in real SF2II** (≥95% freq, ≥90% pulse), 40/40 build | ✅ [GALWAY.md](../players/GALWAY.md) |
| **Maniacs of Noise / Jeroen Tel** — Hawkeye | `bin/build_mon_native_song.py` | **100% byte-exact** (freq+wf+pulse+filter, 3 voices, full length) subtunes 2 & 3; sub0 windowed **8** adaptive parts (13 only in fixed-30s mode) with filter **99.92%** — re-measured 2026-07-30 over the full 384s, cutoff **and** ctrl/res/routing, n=19168, 5 of 8 parts exactly 100.0%. **This supersedes the long-standing "filter ~75% seams" figure, which was stale by ~300x**: the residual is 16 frames total, all in the first 4-8 frames of 3 parts (the driver's cold start before its first filter write), and since parts are separate files a user opens individually that is an ~80ms settle at a file's opening, not an audible mid-song seam | ✅ [MON.md](../players/MON.md) |
| — Cybernoid / Cybernoid II | same | ~95-100 / ~99-100 / ~100 / ~99 per register (11-20 parts) | ✅ |
| — Myth (sub0, sub2) | `bin/build_myth_native_song.py` | freq/wf/pulse ~100%, filter ~90-96% | ✅ (emulation-extracted) |
| — Supremacy (3 subtunes) | `bin/build_mon_native_song.py` | freq 96-99, wf/pulse ~99.8-100, filter 100 (24-70 parts — part-count frontier) | ✅ |
| **ROMUZAK V6.3** (2 tunes) | `bin/build_romuzak_native_song.py` | note/orderlist-exact + byte-exact wf/pulse/AD-SR (~98-100%) | ✅ [ROMUZAK.md](../players/ROMUZAK.md) |
| **Rob Hubbard V1** — Monty, Commando, Zoids, Last V8 | `bin/build_hubbard_native_song.py`, corpus `bin/hubbard_build_all.py` | **pulse 100%** (all voices, all 4 tunes, n=386–996/voice — a *modelled* engine, `hp_engine=1`, measured against the original's real output: the strongest number here). freq **99.3–100** (not 100: Commando osc2 99.3). **Filter: not exercised** — Hubbard never writes cutoff/resonance, so the old "filter 100%" was `0==0` for 1000 frames and meant nothing. 12 V1 tunes + subsongs built. Measured on part01 of each; later parts not re-measurable without a rebuild. | ✅ [HUBBARD.md](../players/HUBBARD.md) |
| **Rob Hubbard V2** (Delta class) | same | Delta theme freq **100%**, wf **85–97%** — same 996-frame window, and the wf residual is entirely **±1-frame skew** (skew-tolerant reads 100/100/100), i.e. the doc quotes the *pessimistic* figure. **Pulse 100% is captured, not modelled** (`hp_engine=0` for Delta: the SF2 replays a pulse stream captured from the original's trace — a round-trip result, not engine understanding). **Filter: not exercised** (see V1). 6 split-songs + Delta + 7 swallow built. | 🚧 [HUBBARD.md](../players/HUBBARD.md) — swallow-class state-region relocation + spin-class + note-format laggards open |
| **DMC (Demo Music Creator)** — Johannes Bjerregaard | `bin/build_dmc_native_song.py`, corpus `bin/dmc_build_all.py` | **Balloon**: 77 parts → **ONE 400s SF2**, wf/pulse **100×3 over the full 400s** (n=19996/voice, 0 skips, 28/30/2 distinct pulse values — the best-evidenced number in this table). Its freq is **80.6/100/97.7** — the weakest DMC figure, previously omitted. **Rockbuster** freq/wf/pulse ~97/100/100 (mean freq 97.6) — but that is **part 1 of 16, first ~20s**; parts 2–16 have no measurement (the tool always compares from frame 0). **Every DMC % is window-dependent and the window is a free parameter** — Thunder_Force part01 reads 100/89/95 at 6s and 44/38/39 at 20s. Quote a window or the number is meaningless. | 🚧 [DMC.md](../players/DMC.md) — bundle-bound files keep high part counts; "56/88 onset-eligible" and "all build" are a **mode-selection count** and a **build count**, not accuracy (an ELIGIBLE file can still score badly: Twilight_Beyond is eligible at 99% onset-agree yet part01 reads 39/39/54) |
| **Sound Monitor (Musicmaster)** — Hülsbeck | `bin/build_soundmonitor_native_song.py` (Stage A: `bin/soundmonitor_to_sf2.py`) | corpus strict sweep **99.25% freq+wf** over **all 27 of 27 parts / 11 songs** (`pyscript/soundmonitor_sweep.py`, re-derived 2026-07-30 — supersedes the prior 99.23%/26-parts figure, same metric, now including the previously-missing `Dance_at_Night_remix part01`). Postdates the v3.17.0 desync fix. freq+wf is the best 2 of 4 register groups — **pulse 96.67 / filter 97.33** corpus-wide ✻ (doc-carried from the 2026-07-16 audit; the new sweep's JSON has the per-part data but no corpus-wide pulse/filter aggregator yet). **Fuck_Off** part01 (242s) is 100.0 on every register; **Dance: only parts 03 and 04** reach 100.0 everywhere (part02 v2 pulse 93.1, part05 filter 98.5, part06 v1 freq 96.9). 11 songs / 27 parts built. | ✅ [SOUNDMONITOR.md](../players/SOUNDMONITOR.md) — **reproducible from a fresh clone** (R21): `pyscript/soundmonitor_sweep.py` is tracked, self-contained (builds all 11 songs itself, no external log dependency), and asserted by `pyscript/test_soundmonitor_sweep.py` (14 tests) |
| **SID Duzz' It (SDI)** — Gallefoss/Tjelta | `bin/sdi_to_sf2.py` | Stage A medians, **strict** (pitch-exact) unless marked: A 98.3, D 100, C 86.0, B 74.8, E 50.8, **DELTA win 89.8 / strict 55.5**, V 21.8. n per variant: A 50, B 43, C 80, D 18, E 118, DELTA 8, V 6. **Only A and D are unfitted**; C/E/DELTA/V pick a timing model best-of-N against the reference (see SDI.md). **343 locate → 348 SF2s** (343 + 5 subtune extras); **324 sweep-validated** — the medians rest on those. "0 failures" = emitted without error, **not** a fidelity statement: 274/324 ship with some default instrument data. | 🚧 [SDI.md](../players/SDI.md) — native Stage B TODO |
| **Blackbird / lft** (16-file v1.2-exact corpus) | `bin/build_blackbird_native_song.py` | Corpus **mean 99.96** overall, **11 of 16 at exactly 100.0**, none below 99.8. The 16 files are **every LFT rip the locator supports** (16 of 61 present; 45 are variants `locate_blackbird` cannot locate at all) -- a coverage limit, not a curated sample. Note the denominator differs from every other row here: this is measured **against the validated Python simulator** (`bin/blackbird_everyframe_sim.py`), not directly against the original SID — the simulator is itself trace-validated, but that is one inference step further out. Glyptodont **162/162 note-ons** (0 missing, 0 spurious), hard-restart arming **100% on every file**. `To_Die_For_II` reached **100.0** in one session (94.2 -> 98.2 via E4 -> 100.0 via E5), with `Revolutions_Delivered` **99.0 -> 100.0** (E5) and `Into_the_Unknown` **98.1 -> 100.0** (E6). The five files still short of 100.0 (Glyptodont 99.8; Fargo, Dithered_Island, Euclid_Was_Here, Fugue 99.9) are small freq artifacts, not structural defects. | ✅ [BLACKBIRD.md](../players/BLACKBIRD.md) — **not wired into `DriverSelector`**. Corpus sweep is tracked and tested — `pyscript/blackbird_sweep.py` (+ `blackbird_crash_probe.py`, 34 tests in `test_blackbird_sweep.py` / `test_blackbird_crash_probe.py`): **reproducible from a fresh clone**, and the mean quoted here is asserted by a test. Regenerate with `py -3 pyscript/blackbird_sweep.py <label>`, diff with `--compare`. E3f combo fx values were disabled for a day on an SF2II-crash report that was later **falsified** by a 10-trial screenshot-verified editor play batch (`BB_NO_COMBO=1` disables); the crash originally reported by the user remains **unexplained** |
| **Future Composer** ($1800 V1.0, 5-rip corpus) | Stage B `bin/build_fc_native_song.py`; Stage A `bin/fc_to_sf2.py` | **Stage B (2026-07-30): 14 of 15 corpus voices at exactly 100.0% audible per-frame pitch over FULL song length** (audible = the original's gate on; per-voice n 346–2253). Sole residual: Triangle_Intro v1 (the lead) **83.6%** over 633 frames — 100.0% for its first 30 s, diverging later. Note placement is independently **frame-exact** (decode onsets == trace gate-rises, delay +0). ⚠️ The builder also prints a **raw** column that runs 58–100% and **understates**: an FC rest is note ≥ 96, so the original parks a near-zero `$0002` in `$D400` **gate-off** while this build emits a true rest — an inaudible mismatch (Triangle_2_years, which has zero rests, has raw ≈ audible). Read both columns with their n. Stage A remains note-accurate on 25/27 voices but **cannot gate a long silent intro** under SF2II's Driver 11; Stage B has no such limit. | ✅ [FUTURECOMPOSER.md](../players/FUTURECOMPOSER.md) — Stage B adds **no new driver** (MON-compatible shim → the shared trace-driven engine), which is why it was chosen as the test that the R1–R3 consolidation generalises; `bin/`, not registry-wired |
| **Jeroen Kimmel** (Hubbard-derived, 4 tunes / 9 SF2s) | `bin/kimmel_to_sf2.py` | Stage A: **11/12 voice-medians exact 100%** (frame-pitch, not gate-onset — see doc); arp/PWM/freq-slide(T0)/drum driver-verified byte-exact | ✅ [KIMMEL.md](../players/KIMMEL.md) |
| **Charles Deenen** (MoN/Deenen replay, 40-file corpus) | `bin/deenen_to_sf2.py`, `bin/deenen_sm_build.py` | Stage A: 7 clean wins (5 at exactly 100/100 onset+pitch, Constant_Runner 100/97.7, Astro 77.4/91.5; 10/19 located) + 8 freebies at 100%; per-voice/per-time audio validator (`bin/deenen_sf2_validate.py`); implausible decodes REFUSED | 🚧 [DEENEN.md](../players/DEENEN.md) |
| **HardTrack Composer** (Longhair/Brush, Elysium 1992) — 38-file Shogoon corpus | **RE stage only** — `sidm2/hardtrack_parser.py`, validator `pyscript/hardtrack_validate.py`. No converter: no Stage A, no Stage B, not wired | Sequencer decode vs siddump, **byte-exact frequency-register** comparison (`-t 20`): **88.39%** (5167/5846) on notes whose instrument lets the sequencer own the pitch, and **2.61%** (28/1074) on notes whose instrument sets `$D400/$D401` from its own wave program (field-5 bit 7). **Quote the two columns separately — never average them**: the second is the unimplemented synth engine, not a decode error, and a pooled figure would drift with a tune's drum/melody mix. **8 of 33 decodable files at exactly 100.0%**. The residual is **not drift** — match rate is flat (87.1-90.2%) across all ten 100-frame buckets, and the weak files are already weak in bucket 0; instrument flag bits 0-1/4/5/6 were each tested and none partitions it. 5 of the 38 files are **refused** (wrapped/multi-instance rips), not silently mis-decoded | 🚧 [HARDTRACK.md](../players/HARDTRACK.md) — 21 tests in `pyscript/test_hardtrack_parser.py`; corpus `SID/Shogoon/` and the editor `bin/hardtrack composer/` are tracked, so the tests run from a fresh clone. Corpus is mixed-player: only 38 of its 150 files are HardTrack |
| **Matt Gray** (own from-scratch engine, 18 tunes: Driller, Last Ninja 2 ×13 subtunes, Tusker ×4 subtunes) | `bin/mattgray_to_sf2.py` | Stage A only: sequencer **onset 100% / pitch 100%** on all 18 tunes — but **scoped to plain (non-modulated) instruments only**. Stage A knowingly omits the slide/arp/PWM/drum engine, so timbre is **not claimed** and the audio will not sound like the originals; that is a Stage B claim, not yet started. Driller round-trips 6000/6000 sequence rows byte-exact and is SF2II play-tested: its **whole 11:05 song is ONE file** (R20) and that single module is **3/3 SURVIVED over a 700 s window**, editor clock **11:41** = full song + loop, with the old 2-part build as an interleaved control (Deliverance/Quedex locate still blocked). | 🚧 [MATTGRAY.md](../players/MATTGRAY.md) — not wired into `DriverSelector` |

## Editor-view clusters (inside the Laxity path)

Audio is 100% (embedded binary); these rows describe **editor** fidelity — see [CLUSTERS.md](../players/CLUSTERS.md).

| Cluster | Editor status |
|---------|---------------|
| Stinsen / Beast / Angular (NP21 variants) | F1-F5 wired, edits propagate, zig64-verified |
| DRAX (4 files) | instrument table resolved; full wiring pending |
| Vibrants 2000 A.D. (2 files) | F1 populated (notes + per-pattern transpose) |
| Wizax-A / Zetrex-YP / V20 umbrella | detection + audio recovery; editor view deferred |

## Anti-matrix (known-bad pairings — do not use)

| Source → Driver | Accuracy | Instead |
|-----------------|----------|---------|
| Native Laxity NP21 → Driver 11 | 1–8% | Laxity driver |
| MoN → Stage-A Driver 11 for *sound* | notes exact, timbre flat | native build (`bin/build_mon_native_song.py`) |

---

## Understanding the metrics

- **Frame accuracy** (wired pipeline): % of frames whose SID register writes match the original byte-for-byte.
- **Per-register fidelity** (native builds): per-frame match rate per register class — freq (semitone-based), waveform, pulse, AD/SR, filter cutoff — per voice, over the real song length (post-`$FE` silence excluded).
- **Byte-exact**: 100% on every tracked register for every frame of the song. The project's crown-jewel standard (MoN Hawkeye sub2/3 achieve it).
- **Objective SF2II validation**: the instrumented editor's *actual* playback captured and diffed (`bin/sf2ii_vs_real.py`) — the truth-teller; headless metrics historically overstate (Galway "37 faithful" → 30/40 objective).

Measurement tools ladder: onset validators (`*_validate.py`) → per-frame fidelity (`mon_part_fidelity.py`, `romuzak_native_validate.py`) → real-SF2II capture (`sf2ii_vs_real.py`) → VICE audio A/B (`listen_compare.py`). See [PLAYBOOK.md §4](../players/PLAYBOOK.md).

---

## History

Pre-v3.13 versions of this file covered only Laxity/Driver11/NP20/Hubbard; the v3.1.1 edition (2026-01-02) is preserved in git history. Per-version accuracy narrative: `CHANGELOG.md` / `STORY.md`.
