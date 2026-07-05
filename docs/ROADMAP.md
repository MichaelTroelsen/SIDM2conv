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

### A3. Shared fidelity library (`sidm2/fidelity_common.py`)
~250-300 copy-pasted lines across 6 validators, including a **real latent bug**: the semitone converter `_semi()` exists 3× with *drifting reference frequencies* (`0x1168` vs `0x1167` vs inline log2). Extract: PSID wrapping (×4), semitone conversion (×3, pick one reference), siddump table parser (×4), zig64 CSV fill-forward serializer (×2), gated best-offset matcher + histogram (×2). Then every player's validator is a thin config over one measured core — and the measurement ladder (onset → per-frame → real-SF2II → audio) becomes uniform.

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

**Standing constraints**: accuracy/byte-exactness over speed and file count; never ship lossy output silently; every "done" claim backed by the objective real-SF2II metric and, finally, the user's ears.
