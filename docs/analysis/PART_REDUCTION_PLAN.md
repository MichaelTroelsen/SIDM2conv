# Reducing SF2 parts per song — analysis & plan

**Goal:** cut the number of SF2 files a long song is split into. Applies to **every native
player** (Galway, MoN, Hubbard, ROMUZAK, DMC — they share `bin/build_mon_native_song.py`).

## Why songs split (measured, 2026-07-09)

The adaptive builder grows a window until an SF2II cap is exceeded, then starts a new part.
Instrumenting the split points (`bin/_dmc_split_analysis.py`) across the worst offenders:

| song | binding cap at each split |
|---|---|
| Shape (38 parts) | bundles 5/5 |
| Namnam_Special (28) | bundles 5/5 |
| Billie_Jean (15) | bundles 5/5 |
| MSI_Demo (36) | bundles 4/5 (instruments once) |

**~95 % of splits are forced by the bundle cap.** Typical counts at a split: `bundles 64–78 /
63`, while `wave 65–127 / 256`, `filter 0–67 / 256`, `instr 13–31 / 32`, `seq 3–6 / 120`.

### Root cause

A **bundle** = one per-note **(FM slide/arp + pulse-width envelope)** pair, selected by a
sequence **command byte in `$c0-$ff` → only 64 slots**. SF2II allows one command index per
sequence row, so FM and pulse are *coupled* into a single index. A long song needs a new part
every ~64 distinct **(FM, pulse) combinations** — even though the wave/pulse/filter *tables*
(256 rows) and the instrument list (32) still have headroom. The bundle channel is the
bottleneck; nothing else is close.

## Plan (phased, lowest-risk first)

### Phase 0 — decompose the bundles *(quick, do first)*
For a few high-bundle windows, count **distinct FM shapes** vs **distinct pulse shapes** vs
the **(FM, pulse) pairs** actually used. This sizes every phase below: if a window has e.g.
30 FM shapes × 8 pulse shapes but 64 pairs, decoupling turns 64 → ~38; if it's 60 FM shapes,
the win is in FM structuralisation instead. Deliverable: a per-song FM/pulse/pair histogram.

### Phase 1 — more aggressive near-lossless clustering *(low risk, fast)*
The greedy bundle-merge already exists (`cluster_bundles` + `bgate` = "inaudible" merges:
same pulse, FM within a hard distance). Widen the tolerance a notch and merge the two
*most-similar* bundles until ≤63 — the loss lands on the fewest, least-audible notes (a tie's
empty pulse, a saw note's don't-care PWM). Every extra merge that fits a window is one fewer
part. Measure fidelity before/after per player; keep only merges under a loss threshold.

### Phase 2 — decouple pulse from the bundle *(high impact, medium risk)*
The structural fix. Move the pulse component **out** of the command byte so the bundle carries
**FM only**, collapsing `(FM × pulse)` → `(FM) + (pulse)`. Two routes, pick per player:
- **Free-running per-instrument pulse** — the `freerun_pulse` path already exists (used by
  V2/Delta). Where a voice's PWM is per-*instrument* (not re-shaped every note), emit it as one
  free-running pulse program per instrument and drop pulse from the bundle. Command = FM only.
- **Pulse in the instrument record** — fold the pulse-program index into the `$a0-$bf`
  instrument (32 slots), leaving the command byte for FM. Watch the instrument cap doesn't
  become the new bottleneck (it's at ~31/32 for a few songs).

Expected: for pulse-diverse songs the bundle count roughly halves → parts roughly halve.

### Phase 3 — structural FM for arp/vibrato players *(Hubbard / MoN)*
Where the FM is *structural* (looping arps, pitch-proportional vibrato), emit one
pitch-independent looping program per shape instead of a per-note Hz-delta capture — many
notes then share one FM slot. `ARP_STRUCT` + `arp_fm_program` + `_vibrato_program` already
exist behind a flag; the guarded-substitution machinery is there. (Not for DMC: its arps are
off-PAL, so Hz-delta is strictly more exact — proven dead end.)

### Phase 4 — widen the ceiling *(deep, optional)*
A driver change to address more than 64 bundles (a two-byte command, or a second command
dimension). Biggest structural change; only if Phases 1–3 don't get parts low enough.

## Recommended order
**Phase 0** (size the win) → **Phase 1** (quick clustering win, all players) → **Phase 2**
(the structural halving). Phase 3 for Hubbard/MoN specifically. Validate each phase with
per-voice fidelity (no silent regressions) and the `dmc_build_all` / `hubbard_build_all` /
galway corpus runners, then refresh `docs/SF2.md` via `pyscript/gen_sf2_index.py`.

## Success metric
Parts per song, corpus-wide (from `docs/SF2.md`), at equal-or-better measured fidelity. Today:
DMC 236 files / 32 songs, MoN 289 / 25, Hubbard 846 / 73. Target: materially fewer parts on
the long songs (Shape 38, MSI_Demo 36, Hubbard multi-part songs) with no fidelity loss.
