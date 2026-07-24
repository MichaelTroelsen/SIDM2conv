# SIDM2 Roadmap — consolidation & optimization before the next players

**Date**: 2026-07-05
**Version**: v3.13.0 era
**Mission**: static code + AI-driven RE that converts **any SID → SF2 at ≥99% fidelity, 100% editable** in stock SID Factory II.
**Companion docs**: [players/PLAYBOOK.md](players/PLAYBOOK.md) (consolidated knowledge) · [reference/ACCURACY_MATRIX.md](reference/ACCURACY_MATRIX.md) (current accuracy) · `whats-next.md` (active frontier)

This roadmap replaces the v3.5.x-era document (preserved in git history). It is organized as: **A. consolidate the tooling** (pay the debt four player ports accumulated), **B. fidelity**, **C. size/part-count**, **D. the road to "any SID"**. Items are ordered by leverage within each track.

---

## A. Tooling consolidation (do this before the next player)

The Stage-A path is already factored right — `sidm2/galway_driver11_emitter.py` is one shared module consumed by Galway, FC, ROMUZAK, and MoN. The Stage-B (native driver) path is not: it grew by copy-paste and now carries ~3,200 redundant lines. Each new player multiplies this debt.

### A1. One native driver source (highest value)
`drivers_src/{galway,romuzak,mon}/*.asm` are three copies of the **same ~1,300-line engine** (the MoN copy is even still named `romuzak_driver.asm` with a `; Galway SF2 driver` header, and has CRLF endings). Per-player deltas are small, feature-shaped, and already assemble-time-selectable in spirit:

- **Action**: merge into one `drivers_src/common/sf2_native_driver.asm` with 64tass `-D` feature flags: `FEAT_DRUM_ROWS`, `FEAT_SEEK_PULSE`, `FEAT_INSTR_PULSE`, `FEAT_WAVE_RLE`, `FEAT_FILTER_ENV`, `FEAT_PULSE16`, `FEAT_DIGI_*` (the digi flags already work this way).
- **Payoff**: a driver bug fixed once fixes all players (the SF2II CMP-carry class of bug currently needs three patches); a new player becomes a flag set + a freqtable, not a fork.
- **Guard**: byte-compare each flag combination's output against the current three drivers before switching (the assemble() state-region and edit-area guards already exist).

### A2. Shared native-build library (`sidm2/native_build/`)
- `gen_includes_song` is the top copy-paste hotspot (~180-line identical skeleton in the Galway and ROMUZAK builders; MoN imports ROMUZAK's). Extract: header/Block-2 state pinning, vstream orderlists, sequence-slot writes, wave-program dedup, FM/PULSE row-major layout with 16-bit pointers, `layout.inc` writer — with per-player hooks for instrument flags and extra tables.
- `build_galway_driver_full.py` vs `build_romuzak_driver_full.py`: 353 lines, **12 differ** (all name substitutions). Parameterize (`player=`), delete one.
- The adaptive-window `fits()` loop (caps probe → window split) is duplicated between the MoN and Myth mains → shared `pack_adaptive_windows()`.
- Move the SF2II cap constants (63 bundles / 32 instruments / 256 rows / 120 sequences / 960 events / $D000 wall) into **one** `sidm2/sf2_caps.py` consumed everywhere they are currently re-declared.

### A3. Shared fidelity library (`sidm2/fidelity_common.py`) — ✅ DONE 2026-07-05
~250-300 copy-pasted lines across 6 validators, including a **real latent bug**: the semitone converter `_semi()` existed 3× with *drifting reference frequencies* (`0x1168` vs `0x1167` vs inline log2). Extracted: PSID wrapping (×4), semitone conversion (canonicalized on `SEMI_REF=0x1167` = PAL C-4), siddump table parsers (×4 → `siddump_per_frame` / `siddump_note_onsets` / `siddump_filter_trace`), zig64 fill-forward serializer (×2), gated best-offset matcher (×2). Verified by byte-diffing every validator's output against pre-refactor baselines (all identical, including mon_fidelity across the reference change) + 13 unit tests (`pyscript/test_fidelity_common.py`).

### A4. Wire the `bin/` players into the default pipeline
ROMUZAK, MoN, and FC are absent from `PLAYER_REGISTRY`; Galway-native is `bin/`-only. Add registry entries + converters so `sid-to-sf2.bat` auto-routes them (native builds behind a `--native` flag or as the default where byte-exact). This is the difference between "we have the tech" and "the tool converts it".

### A5. Repo hygiene
- `bin/` holds ~2,200 `_`-prefixed scratch files (one-shot probes + intermediate `.sf2`/`.txt`). Archive per the archive-before-explain protocol; keep the ~48 production scripts. Add a `bin/README.md` naming the production entry points per player.
- Fix the MoN driver file name (`romuzak_driver.asm` → after A1, moot) and CRLF.
- Untracked strays from `git status` (`the`, `bin/_mon_load.*`, tool dirs) — triage into .gitignore or archive.

**Estimated payoff of A1-A3**: ~3,200 duplicated lines → ~1,600 shared; next player's Stage B drops from days-weeks toward days.

---

## B. Fidelity improvements

### B1. MoN structural rebuild (active frontier — `whats-next.md`)
The bounded, de-risked sequence: **(1) note-timing reconciliation** (parser durations vs real note lengths, ~9-frame drift — the current blocker), (2) re-apply the proven FM semitone+loop arp wiring, (3) wave `[attack][steady+loop]` programs, (4) pulse. Byte-exact by construction (the programs come from the player's own tables) — this is both a fidelity and a size item (see C1).

### B2. Galway residual 10/40
The one **shared** gap: pulse-width *modulation* not extracted for Commando / Street_Hawk / Match_Day / Highlander (real PW sweeps, build emits flat) → emit `0X`-add pulse rows. The rest are distinct per-tune issues (fast-pitch detail, coarse tempo, slide, freq-0 rests) — take them opportunistically after A3 makes measurement cheap.

### B3. Make the objective metric universal
`sf2ii_vs_real.py` (instrumented real SF2II capture) is Galway-only today, yet it is the metric that exposed the "37 faithful → 30/40" overstatement. After A3, generalize it player-agnostically and gate every player's "done" claim on it, not on headless numbers.

### B4. Future Composer Stage B
FC is the only ported player without a native driver (Stage A only, $1800 variant = 5/20 files). After A1/A2 this becomes the cheapest Stage B yet — and the first test that the consolidated pipeline actually generalizes.

### B5. Known small residuals (tracked, low priority)
Myth sub0 part-1 filter 77% (rapid multi-section opening; other parts 90-98%, ear-confirmed fine) · MoN $00-silent-note freq offset (inaudible) · ROMUZAK drum octave ~13% osc3 gap (needs drum-engine disasm) · trace-replay cycle floor (~0.17 spectral on resonant leads — **fundamental, do not chase**).

---

## C. Size / part-count optimization (lossless only — user standing rule)

### C1. Structural synth-table RE (the only proven lossless path)
Quantified conclusion from Supremacy: dense tunes blow bundles+instruments+wave-rows **simultaneously**; no trace-based method compresses the player's unrolled looping tables. The structural path (extract the player's own compact arp/wave tables + selectors, emit them as looping SF2 programs) collapses 87 instruments → ~5 and 178 bundles → ~16 arp programs, byte-exact from ROM. Supremacy's engines are cracked; the arp parser is committed. Target: Supremacy sub2 70 parts → single digits; Myth sub0 7 → ~1-2. **This is the flagship size work and it equals B1.**

### C2. Port the wave-RLE win
MoN's RLE wave rows (col1 = frame count) cut Cybernoid 18 → 11 parts, proven byte-identical. After A1 it's a feature flag — evaluate it for any wave-row-bound tune on other players.

### C3. Program dedup across parts
Windowed parts currently rebuild programs per window; identical programs recur across parts. Cross-part canonicalization won't reduce the *count* of parts (caps are per file) but shrinks each file and stabilizes seams (filter-seam residuals are window-boundary artifacts).

### C4. Filter seams at window boundaries
Part-boundary filter restarts cost ~25% filter fidelity on windowed tunes (Hawkeye sub0). Carry the filter engine state (envelope phase) across the window cut when emitting part N+1's first program.

---

## D. The road to "any SID → 99% / 100% editable"

### D1. A player-agnostic trace-first fallback
The deepest lever the four ports revealed: `build_native_song` already accepts external traces (Myth's shim proved it — a MON-compatible shim + py65 frames, no static parser). Generalize into a **universal trace-driven converter**: any SID → siddump/zig64 trace → gate/legato note extraction (Galway's extractor is already player-agnostic) → native driver build. Expected: ~95-100% per-register fidelity, editable notes/instruments, multiple parts, for *players we have never RE'd*. Ship it as the "unknown player" fallback above Driver 11. Parsers/structural RE then become fidelity+compactness *upgrades* per player, not prerequisites.

### D2. Generic signature-scanning framework
Every player port hand-rolls relocation-safe byte signatures with wildcards + operand extraction. Factor a small engine (pattern DSL, self-modified-pointer resolution, per-file confirmation reports) so new-player table location is declarative. The DRAX/2000AD/V20 detectors would collapse into data.

### D3. Rob Hubbard (95 tunes — the next big corpus)
Galway-shaped (per-channel bytecode interpreter, no flat tables). With D1, Hubbard gets a trace-native path almost for free; the RE effort then goes into the editor-fidelity upgrade. Kick off only after A1-A3 land.

### D4. Codify the AI-RE toolkit
The scratch tools that cracked every engine — disassembler with emulation write-PC probes (`_mon_disasm.py` pattern), freq-lookup interceptors, filter/state tracers, lockstep CPU diff (`_mon_cpu_diff.py`, which found the SBC bug) — get recreated each session. Promote the stable core to `bin/re_toolkit/` with a short guide, so each new player starts from tools, not from scratch.

---

## E. Audio-domain verification (added 2026-07-24)

Every fidelity number in this repo is a **register-write** match. That is the
right primary metric, but it is provably not sufficient: the Blackbird B25
round shipped a verified, register-exact improvement (97.5% overall) that did
**not** fix the audible problem a listening pass reported. `audio-tightness.bat`
(`docs/guides/AUDIO_TIGHTNESS_GUIDE.md`) is the first tool in this track —
onset timing + attack shape, with a systematic-offset/jitter split and an
alignment timeline. The items below are what it still needs.

### E1. Patch VICE for per-voice muting (unblocks everything else here)
`vsid -help` confirms **VICE exposes no voice-mute option** (only engine/model/
sampling). SID2WAV has `-m<num>` but is a 1997 build that **hangs outright on
some newer tunes** — lft's `Glyptodont.sid` renders zero samples under it while
VSID handles it fine. So today: the files most worth analyzing are exactly the
ones that cannot be voice-isolated.

- **Action**: add a voice-mute resource/CLI option to the local WinVICE build
  (reSID exposes per-voice output internally; the mute can be applied at the
  `sid_engine` write layer or as a reSID `voice.envelope` gate). The user has
  **already patched WinVICE in the `siddetector` project** — reuse that same
  build/toolchain rather than starting a fresh fork.
- **Payoff**: per-voice isolation on *every* file, from one renderer, which
  unblocks E2 and removes the tool's current SID2WAV dependency entirely.
- **Guard**: cross-check a patched-VICE per-voice render against SID2WAV's
  `-m` output on a file both can handle (e.g. `SID/Angular.sid`) before
  trusting it — same "two independent tools must agree" discipline the
  zig64/vsid trace cross-validation already uses.

### E2. SidWiz-class oscilloscope video in the tool stack
Per-channel oscilloscope video (original vs driver, one lane per SID voice) is
the fastest way for a human to *see* a timing/shape difference, and it is
shareable. Two mature options: **[SidWizPlus](https://github.com/maxim-zhao/SidWizPlus)**
(C#/.NET — `dotnet` is already installed here; began life as "SidWiz") and
**[Corrscope](https://github.com/corrscope/corrscope)** (Python, pip-installable,
correlation-based triggering that holds complex waves steady).

- **Blocked on**: E1 for per-voice tracks on VSID-only files, and **ffmpeg**,
  which is not currently installed (both tools need it to encode video).
- **Action**: wrap whichever is chosen behind a `bin/` or `pyscript/` entry
  point that takes the per-voice WAVs the tightness tool already renders and
  emits a comparison video; do not vendor the tool, shell out to it.
- **Note**: Corrscope is the lower-friction integration (same language, pip
  install, headless render); SidWizPlus has the richer per-channel styling.

### E3. Glyptodont's "+2.5-frame offset" — ✅ RESOLVED 2026-07-24: it was not real
The tool reported a **+50.0 ms (+2.50 PAL frame)** whole-render offset against
the B25 native build, with 60.7% of onsets "loose". Both numbers were
measurement artifacts. What actually happened, in the order it was ruled out:

- **Not tempo drift**: inter-onset-interval ratio driver/original = **1.00000**
  (median IOI 90.0 ms on both sides).
- **Not a render start-point shift**: first-onset difference was only +10 ms
  (0.5 frames), and per-quarter medians bounced (+80/+40/+75/+20 ms) rather
  than holding constant or trending — a linear fit removed almost none of the
  spread (std 55.3 → 54.7 ms).
- **The actual cause**: the default alignment tolerance was **150 ms while the
  median IOI is 90 ms**. A greedy matcher with a window wider than the note
  spacing can pair an onset with its *neighbour*, and that mispairing
  preserves time order, so `count_alignment_crossings()` reported zero. A
  tolerance sweep collapsed the "offset" monotonically to **exactly 0.0 ms at
  ≤70 ms** (150→+50, 120→+30, 90→+10, ≤70→0), with median |jitter| falling
  50 ms → 10 ms (the detector's own hop resolution).

**Fix shipped**: the tolerance now defaults to half the original's own median
IOI (`safe_tolerance_ms`, clamped to 20-150 ms), the report prints the IOI and
warns when a tolerance approaches or exceeds it, and a regression test pins
the failure mode.

**The corrected Glyptodont reading — the timing was never the problem:**
offset **+0.00 frames**, median jitter **0.0 ms**, only **7.4%** loose
(was 60.7%). The matched onsets are essentially perfectly timed.

### E3b. The real Glyptodont discrepancy: onset presence, not onset timing
With alignment fixed, what remains is **122/195 matched (62.6%), 73 missing
(37.4%), 55 extra (31.1%)**. The driver is not mistiming drum hits — it is
**dropping and adding them**. That is a far better lead for the original
"drums don't sound tight" report than any timing number, and it is
un-investigated. First question to settle: how much of it is genuine
note-level divergence versus onset-detector sensitivity differing between two
renders with different amplitude/spectral character (195 vs 177 detected
onsets before any matching). Cross-check a sample against the register trace,
where a dropped note is unambiguous.

### E4. Calibrate the remaining detector defaults
`--loose-threshold-ms 40` and the detector params (hop/window/bands/freq
range) are still **provisional guesses**, not tuned against a corpus.
(`--onset-tolerance-ms` is no longer in this list — E3 made it adaptive.)
Calibrate against files with known-good and known-bad timing so "loose" means
something reproducible across files.

---

## Suggested execution order

| # | Item | Track | Size |
|---|------|-------|------|
| 1 | Fidelity common lib + fix `_semi` drift | A3 | S |
| 2 | MoN structural rebuild step 1 (note timing) → 2-4 | B1/C1 | M — **already scoped in whats-next.md** |
| 3 | Unify native driver (feature flags) | A1 | M |
| 4 | Shared native-build library + caps module | A2 | M |
| 5 | Universal trace-first fallback (D1) — the mission's biggest step | D1 | M-L |
| 6 | Wire bin/ players into the registry | A4 | S-M |
| 7 | FC Stage B (validates the consolidation) | B4 | M |
| 8 | Galway pulse-PWM residuals; universal objective metric | B2/B3 | S-M |
| 9 | bin/ archive sweep + re-toolkit | A5/D4 | S |
| 10 | Hubbard kickoff | D3 | L |
| ~~11~~ | ~~Explain Glyptodont's +2.5-frame offset~~ | E3 | ✅ **DONE 2026-07-24** — artifact, not real |
| 11 | Glyptodont's 73 missing / 55 extra onsets (the real lead) | E3b | M |
| 12 | Patch WinVICE for per-voice mute (reuse `siddetector` build) | E1 | M |
| 13 | SidWiz/Corrscope video in the tool stack (needs E1 + ffmpeg) | E2 | M |
| 14 | Calibrate remaining tightness detector defaults | E4 | S-M |

**Standing constraints**: accuracy/byte-exactness over speed and file count; never ship lossy output silently; every "done" claim backed by the objective real-SF2II metric and, finally, the user's ears — the E track exists because that last check caught something the register metric could not.
