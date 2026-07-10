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

## Phase 0 findings (measured) — the decomposition is player-dependent

| Player (song, window) | distinct FM | distinct pulse | (FM,pulse) pairs | driver of the explosion |
|---|---|---|---|---|
| **DMC** (Shape, 30 s) | 88 (diverse) | 70 (diverse) | 116 | both axes — unique per-note arp + PWM |
| **Hubbard** (Commando, 14 s) | **24 (structural, flat)** | 50 (grows) | 68 | **pulse** — FM is reused |

The decompose (`BUNDLE_DECOMPOSE=1`) shows Hubbard's FM shapes are structural (24, flat as the
window grows) while pulse diversity drives the split; DMC is diverse in *both*. So:
- **DMC** — clustering (Phase 1) is a **dud** (proven); decoupling (Phase 2) is modest (~25 %).
- **Hubbard / MoN** — decoupling (Phase 2) is **transformative**: move pulse off the command
  channel and the bundle channel needs only ~24 FM slots (< 63) → **Commando's 45 parts could
  collapse toward 1**. This is the big lever for the "all songs like Hubbard" corpus.

**Revised priority: Phase 2 first** (decouple pulse — huge for Hubbard/MoN, modest for DMC),
then Phase 3 (structural FM) for any residual FM-driven splits. Phase 1 is shelved (no lossless
win where FM/pulse are both diverse).

## Plan (phased, lowest-risk first)

### Phase 0 — decompose the bundles *(quick, do first)*
For a few high-bundle windows, count **distinct FM shapes** vs **distinct pulse shapes** vs
the **(FM, pulse) pairs** actually used. This sizes every phase below: if a window has e.g.
30 FM shapes × 8 pulse shapes but 64 pairs, decoupling turns 64 → ~38; if it's 60 FM shapes,
the win is in FM structuralisation instead. Deliverable: a per-song FM/pulse/pair histogram.

### Phase 1 — more aggressive near-lossless clustering *(low risk, fast)*
The greedy bundle-merge already exists (`bgate` = "inaudible" merges: same pulse, FM within
`BUNDLE_TOL`). `BUNDLE_TOL` was `0` (off) and is now env-configurable
(`BUNDLE_TOL=<n> py -3 …`); a decompose probe is env-gated (`BUNDLE_DECOMPOSE=1`).

**RESULT (measured 2026-07-09) — Phase 1 is a DUD for DMC.** Decompose of a 30 s Shape
window: **116 (FM,pulse) pairs, 88 distinct FM, 70 distinct pulse** — genuinely diverse in
*both* axes (DMC captures a unique per-note wavetable arp *and* per-note PWM). Part counts by
`BUNDLE_TOL`: Shape 38→37, Namnam 28→26, Billie_Jean 15→14 — and only at *absurd*
tolerances (1000–3000, audibly lossy); at inaudible tolerances (≤300) the reduction is **0**.
The same-pulse-merge premise barely applies because the pulse programs are too varied. So for
DMC, lossless clustering **cannot** reduce parts — the explosion is architectural. *(Still
worth checking on Hubbard/MoN, whose FM is often structural and pulse per-instrument, so
same-pulse near-FM merges should apply far more — TODO.)*

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
**Sizing (from Phase 0):** decoupling DMC's 116 pairs → 88 FM (the FM channel) + 70 pulse
(to the 256-row pulse table) → the split cap becomes FM=63 instead of pairs=63, so a 30 s
window that held 116 pairs holds ~88 FM → parts shrink ~`116/88 ≈ 25 %`, and pulse never
forces a split again. Modest for DMC (FM diversity dominates), larger where pulse drives the
count. **This is DMC's only lossless lever short of Phase 4.**

**SHIPPED for Hubbard (2026-07-09) — a huge, lossless win.** The mechanism already existed
(the per-instrument pulse **canonical**, `pp = cp`, "the whole-song bundle-collapse trade")
but was gated behind `ARP_STRUCT` (which also mangles FM). Surgically un-gated via a
`pulse_canon` shim flag (+ `MON_PULSE_CANON=1`), enabled by default on the Hubbard shim
(gated to `hard_restart`; V2/Delta's freerun path and all other players are untouched). The
ROM pulse free-runs per instrument, so per-note captures differ only in inaudible phase →
collapsing them to one canonical per instrument is lossless. Measured: **Commando 45 → 4
parts, Monty 22 → 4 parts, both at 100/100/100 + filter 100 %** (distinct_pulse 50 → 4–6,
pairs 68 → ~25, now tracking distinct-FM). Delta (V2) unchanged (3 parts, freerun path). 37
tests green.

**MoN (tested `MON_PULSE_CANON=1`) — a smaller, lossless win.** MoN modules are
`hard_restart=0`, so only the *strictly-lossless* variant fires (`pp = cp` when the unrolled
pulse is identical), not Hubbard's phase-tolerant one. Still, its pulse is per-instrument
enough that distinct_pulse collapses (Cybernoid_II sub0: ~50 → 4–6, **20 → 13 parts**, pulse
100 %), and the **byte-exact crown jewel is safe** — Hawkeye sub2 is byte-identical before/after
(both osc1 97.5 / osc2·3 100 over a 60 s window; a measurement-window artifact, unchanged by
the flag). The win is smaller because once pulse collapses, MoN's splits are bound by the
*other* caps (wave/filter/memory), not bundles.

**Verdict after the crown-jewel check: NOT default-safe for MoN — kept opt-in.** Cybernoid is
clean, but **Supremacy sub1 breaks** with `pulse_canon`: it drops 23 → 2 parts but part01
falls to ~93 % and **part02 collapses (freq 7–18 %, pulse ~0)**. Once pulse collapses the
adaptive splitter over-grows the windows, and Supremacy's structural-arc / boundary-continuation
/ per-drive-filter pulse handling doesn't survive that (unlike Hubbard's `hp_engine`, which is
byte-exact by construction). So MoN keeps `MON_PULSE_CANON=1` **opt-in only**; defaulting it on
would regress the byte-exact crown jewel. A safe MoN default would need the splitter to still
cap window growth by the *raw* (pre-canonical) bundle count, or a per-tune guard — future work.

**Realizing the win — corpus rebuild results (2026-07-10).** V1 collapsed as predicted:
Monty 22→4, Commando 45→4, Chimera 76→12, Zoids→4, Thing_on_a_Spring 33→4, Gremlins s6
35→1, Hunter_Patrol 25→8; Delta (V2 freerun) 221→165. **BUT the V2 swallow class explodes
under its first real `auto` build**: Shockway_Rider 638 parts, Auf_Wiedersehen 274,
Star_Paws 188, Saboteur_II 112 (the old inventory's "1 file" entries for these were stale
manual whole-song artifacts, not comparable). `pulse_canon` is not the cause (it can only
reduce bundle counts).

**Swallow-explosion root cause (measured 2026-07-10): a V2 track over-decode, not caps.**
Healthy files decode all three voices to EQUAL one-pass lengths (Monty 350/350/350 s,
Delta 545×3, Commando 236×3 — synced tracks). The exploders are wildly unequal: Shockway
261/868/**3210 s**, Star_Paws 43/512/1658 s, Saboteur_II 398/848/2773 s, Auf_W
364/825/1900 s. One voice's track decodes ~10× too long (a V2 repeat-count / track
mis-decode), `decode_song`'s loop expansion then unrolls the other voices to match → a
4013 s span → 638 parts *of repeats*. The windows are normal (~6 s); the SPAN is wrong.

**FIXED (2026-07-10, ROM-verified):** the exploders' tracks use **bit7 TRANSPOSE
commands** the parser decoded as pattern numbers 128+ (garbage patterns → the 10×-long
voice). Three encodings found in the players' own code: one-byte `$80|semis` (Shockway
`$ED99`, Star_Paws; Saboteur_II adds a `$FE` check) and two-byte `$80 nn`
(Auf_Wiedersehen `$E49D`). Parser now detects the idiom (`lay.trk_transpose`,
signature-gated — V1 files untouched), skips/records the transpose in `track_patterns`,
and applies it to note pitches in `decode_song`. One-pass voice lengths now near-equal
(Saboteur 193×3 exactly). **Shockway rebuilds 638 → 21 parts** (span 4013→419 s). The
builder also gained the span-sanity guard (>2.5× median = suspect mis-decode warning).
**Follow-on front:** this class's *fidelity* is still poor (Shockway part01 freq 62–85,
pulse ~0 — the swallow freerun pulse model doesn't fit the transposed-track generation);
it was garbage-decoded entirely before, so this is the first honest baseline, not a
regression.

**Transposed-class pulse experiment (2026-07-10, `HUBBARD_FORCE_HP=1`):** forcing the V1
HP pulse engine (the class is V1-notes + swallow) gives **osc2 93.8 / 99.8 / pulse
0→100** and improves osc1 freq/wf (70.7/92.0) — but regresses osc3 wf (96→70, a periodic
10-frame wave cycle desync) and osc1/osc3 pulse stay ~0–6. So the class has **mixed
instrument semantics** (some records V1-HP, some not) — it needs its own instrument-record
RE before the default flips. Env experiment kept; default unchanged (freerun).

**Analyser upgrades round 2 (`bin/mon_part_fidelity.py`):** (3) **mismatch-cluster
report** — registers under 99.5 % list their residual as frame-runs (top 3), separating a
wrong program (one long run) from timing jitter (scattered 1-frame runs). It immediately
localized Supremacy sub1 osc2's whole 6 % wf residual to **3 runs** and diagnosed it: the
original writes **wf `$00`** (waveform off) during long rests while the native driver
holds the instrument waveform with gate clear — a driver-level rest representation gap,
now a concrete identified fix. (4) **part-loop auto-cap** — a windowed part loops back to
its start when its content ends; measuring past that fabricated a phantom 148-frame tail
residual (Shockway part01 = 22 s, measured at 25 s). The analyser now detects the probe's
self-loop by a 40-frame all-voice freq self-similarity scan and caps the window there. Also: Deep_Strike s0 FAILs mid-build with a WAVE-overflow crash
in `gen_includes_song` (count-vs-emit divergence — the adaptive `fits()` passed but emit
overflowed; 25 partial parts on disk). Devils_Galop/I_Ball/Wiz still spin-class timeouts.

**Fidelity-analyser upgrade (2026-07-10, `bin/mon_part_fidelity.py`)** — chasing the last
1–2 %: (1) **per-voice delay refinement** (±2 frames per voice on top of the shared engine
delay — the original staggers per-voice register writes; one global delay cost a phantom
~1–2 % on the offset voice); (2) **residual classification** — each mismatch is checked
against the original's ±1-frame neighbours: a match there = 1-frame **transition skew**
(inaudible register-write phase), reported as a separate *skew-tolerant* score; whatever
remains is REAL residual worth chasing. First results: Commando osc2's 0.7 % is *content*,
not skew (worth investigating); the MoN pulse-canon Supremacy cost is confirmed real
(osc3 pulse 99.9→94.2 / 100→83.7, non-skew). It also exposed that the earlier "part02
collapses to 7–18 %" claim was a **measurement artifact** (wrong window offset — the
pulse-canon build shifted part boundaries from 0-32/32-38 to 0-28/28-38); the corrected
verdict: pulse_canon on Supremacy costs a real but modest ~6–16 % osc3 pulse, so the
MoN opt-in (not default) decision stands.

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
