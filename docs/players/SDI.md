# SDI — SID Duzz' It (Geir Tjelta & Glenn Rune Gallefoss)

**Status (2026-08-12):** parser + onset/pitch validation across SIX decoded
variants; Stage A (editable Driver 11) shipping via `bin/sdi_to_sf2.py`;
Stage B native shipping via `bin/build_sdi_native_song.py`, **swept over the
whole flat dir** (`pyscript/sdi_native_sweep.py`). Corpus:
`SID/Gallefoss_Glenn/` (473 files; 441 in the flat dir, 671 songs) +
`SID/Red_kommel_jeroen/` staging.
**343 of 441 files locate → 348 Stage-A SF2s** (343 + 5 verified E extra
subtunes). **324 of those are sweep-validated** — the medians below rest on
those, not on all 343. Current headline figures: `docs/reference/ACCURACY_MATRIX.md`
(canonical; verified to match this doc 2026-08-09).

> **THREE DIFFERENT DENOMINATORS — do not conflate them** (the 2026-07-16 audit
> did, and nearly caused 19 good SF2s to be deleted as "orphans"):
> - **343 locate** — `locate()` returns a layout. This is the *builder's* gate:
>   `convert()` checks `lay is None` and nothing else, so it emits one SF2 per
>   located file. 343 + 5 subtune extras = the 348 on disk, exactly. There are
>   **no orphans**.
> - **324 sweep-validated** — `bin/_sdi_sweep.py` additionally needs usable
>   ground-truth onsets; it drops 19 that locate but cannot be scored (e.g.
>   `Barbers_Adagio_64`, `play=$0000`, 0 real onsets — correctly excluded, so it
>   inflates no median).
> - **671 songs** — subtunes. ~417 remain undecoded.
>
> A **fourth** denominator now exists and belongs to a different pipeline:
> **262 of 441 build natively (Stage B)**, measured by
> `pyscript/sdi_native_sweep.py`. It is not a subset of the 343 — Stage B needs
> drivable onsets, which locate() does not check, and refuses 62 files locate()
> accepts. Never quote 343, 324 and 262 in the same sentence.

**This cycle (2026-07-13):** variant **C walk decoded** (strict median
66.7→86.0), **multi-subtune** support (A/C/E), and the **"sixth layout"
wrapper cracked** — the 69-file `$0FFF` play+4 cluster is variant E behind
an init/play JMP wrapper (+62 files located, E corpus 52→114).

**Ground truth:** the authors' own commented player source — SDI 2.1 n49,
1994 lines, `bin/SIDDuzz/extracted/sdi21-n49.asm` (c1541+petcat from the
user-staged d64s). It is **feature-flag assembly** (`rem@` flags compile
blocks in/out per song), which explains the rip clusters: one source, many
binary shapes ([PATTERNS.md](PATTERNS.md) P6). The rip generations differ
from the source in memory layout, so every table address is extracted from
the rip's own code operands (relocation-safe signatures).

Parser: `sidm2/sdi_parser.py`. Trail: `memory/gallefoss-sdi-player.md`.

---

## `Tanks_3000` passband: the filter drive detector is fed an empty onset list (2026-08-15)

`passband_check --player sdi` reports `Tanks_3000` as **static LP+BP against an
original that alternates LP/LP+BP 12 times** (94.9%, 72 audible frames). It
**survives a rebuild**, so by that tool's own rule the builder is at fault, not
the artifact. Traced to the bottom; recording it because four plausible
explanations were tested and refuted on the way, and each is worth not repeating.

**Refuted, in order:**

1. *An F8 window over-run.* No — the `.span` sidecar says part 1 is **0–32 s** and
   the modulation starts at frame 853 (17 s), so it is genuinely inside the part.
   The check simply doesn't annotate, because a span may only NARROW a window and
   32 s > the 28 s default.
2. *The F9 shape — mode changes without a cutoff jump, so `detect_filter_drives`
   is blind.* No — every one of the 12 changes comes with a **+352** cutoff jump
   (256 → 608), far above `FILT_FAST = 0x40`.
3. *No note-on to hang the drive on.* No — all 8 changes in the window sit
   **exactly** on gate rises of voice 0, which `routed_voice` correctly
   identifies as the routed voice.
4. *The canonical filter key omits the passband.* True, necessary, and **not
   sufficient alone**. `canon_src` keys on `(MoN instrument, _shape_sig)` where
   `_shape_sig` is the cutoff base and initial slope, so two drives whose cutoff
   envelopes match but whose `$D418` modes differ collapse into one program.
   Called standalone on this file, `detect_filter_drives` returns **37 drives →
   2 keys today, 3 with the passband added** (LP+BP ×30, LP ×6 — exactly the lost
   modulation). But a patch adding it was written, built and measured on its own:
   **no change**, because inside the build there are not 37 drives — see the
   cause below. One drive cannot merge with anything.

**The actual cause.** `build_native_song` populates `onsets[v]` — the list it
hands `detect_filter_drives` — only from events with `ev.retrig` set. The SDI
shim emits `total=[268, 202, 308]` events per voice and **`retrig=[1, 1, 1]`**.
So the detector receives ONE onset per voice, returns ONE drive (frame 1), and
one canonical program covers the entire song, carrying whichever passband that
first drive had. Everything downstream — detection, anchoring, the SET-row
encoding, the passband trace, which SDI does pass as a 3-tuple — is working on
an input that is empty by construction.

**One cause: the canonical filter key omits the passband.** `canon_src` keys on
`(MoN instrument, _shape_sig)`, and `_shape_sig` is the cutoff base and initial
slope — so drives whose cutoff envelopes match but whose `$D418` modes differ
collapse into one program, and whichever mode the winner carried is applied to
all of them. Adding the passband to the key splits them. Measured on a **serial
2×2** (one build at a time, artifacts deleted first, non-zero exit refused):

| `filter_tie` | passband in key | oChg | dChg | agree | parts | freq+wf |
|---|---|---:|---:|---:|---:|---|
| off | off | 12 | 0 | 94.9 | 69 | 99.9/99.9/99.9 |
| off | **on** | 12 | **12** | **100.0** | 69 | 99.9/99.9/99.9 |
| on | off | 12 | 0 | 94.9 | 69 | 99.9/99.9/99.9 |
| on | **on** | 12 | **12** | **100.0** | 69 | 99.9/99.9/99.9 |

The key change is necessary and **sufficient**, at identical part count and
identical fidelity. Sibling of F9: there a *detector* was blind to a register,
here a *canonicalisation key* was.

⚠️ **A previous version of this section claimed TWO causes in series and was
wrong.** It said SDI's shim starves the filter-drive detector — `retrig = not
tie`, so a legato voice contributes one onset — and that `filter_tie=1` was the
other half. The starvation is real *in a single-window build* (onsets `[1,1,1]`
→ 1 drive → 1 program, instrumented), but the production path is **adaptive**,
and per-part classification yields drives regardless; `filter_tie` changes
nothing measurable. It was reverted rather than shipped: it would have altered
behaviour across 441 SDI files for no benefit.

**How the wrong claim was reached, because the process failure is the lesson.**
The evidence was assembled across interleaved builds instead of one controlled
run, and three separate defects in the scratch harness each produced a confident
wrong number:
  * it kept only `agree` and `routed` from `passband_check`, discarding
    `oChg`/`dChg` — so a window in which NEITHER side modulates read as a
    perfect 100.0 (`Kirby` did exactly this);
  * it scored the artifact left behind by a **failed** build, attributing the
    previous config's result to the new one;
  * the failure that exposed it was two builders racing on
    `drivers_src/mon/layout.inc` — **PATTERNS F2**, violated twice, both times
    because a momentary `tasklist` process count was trusted over the job list.
`passband_check` already prints the columns that expose all of this and
annotates "filter never exercised in this window — NOT a pass". Scraping its
rendered text threw the guard away. Consume the structured result, run one build
at a time, and delete artifacts before a config A/B.

**Status**: shipped as the passband-in-key change in `build_mon_native_song.py`
(`FILT_KEY_PB=0` restores the old key). `Arabia` (**97.8%**, re-measured
post-`00893cd` offset-fit fix — was previously published as 98.2%) and
`Funk_Facet` (99.0%) survive a rebuild unchanged and are separate, smaller
defects: **one mechanism at two severities** — gate-anchored filter dispatch
drops a `$D418` write that arrives between note-ons. `Arabia`'s write is 20
frames pre-onset and lost outright (7 audible mismatched frames); `Funk_Facet`'s
is 1 frame pre-onset and arrives late (12 audible mismatched frames).


## The variants (one editor, six binary generations)

| Variant | Class file | Header | Track ptr shape | Seq row shape |
|---------|-----------|--------|-----------------|---------------|
| **A** | 30seconds | `play=init+3`, 2-JMP | 8-byte init-copy block | prefix* + terminal (dur/sound prefixes) |
| **B** | Airwalk | `play=init+3` | per-voice ptr arrays | dur `$80-$bf`, instr `$c0-$df`, arp `$e0+` |
| **C** | Bahbar | `play=init+3` | subtune 8-byte records | SOUND `$60-$7f`, DUR `$80-$bf`, CHORD `$c0-$fc` |
| **D** | Another_Day | `play=init+3` | (seq#, hdr) pairs; hdr = transpose/repeat | note + dur-flag byte (+2 for filter/glide) |
| **E** | 2_Young_2_Die | **`play=init+4`** (v2.1-source gen) | tp → tl/th arrays (ghost 4th channel!) | [ONE cmd][dur][note, bit7 = TIE] |
| **V** | Oh_Boy_VE-2x | **`play=$0000`** (wrapper, 2x/4x) | per-voice arrays, $40-byte state blocks | fixed 3-byte rows [note, fx, next-dur] |

Sixth unlocated layout: Acid_Jazz (`play=$1B36`, absolute state arrays) — open.

## The pitch-carrier ports (the strict-score campaign)

SDI melodies move via **pitch-carrying instruments** ([PATTERNS.md](PATTERNS.md)
P1) — sequences can hold a constant note while the wfprg carries the music.
Each variant hides the pitch differently; porting it was the whole
windowed→strict gap:

- **A**: wfprg **row 1** arg (row 0 = the `($01,0)` test row); drums (wf
  bit7) carry the ABSOLUTE semitone. Result: **windowed == strict** (98.6
  corpus median) — the pitch model is exact.
- **D**: the walk's **resting row** (3-byte rows `[wf, pitch, extra]`;
  ctrl `$FE` stops parked on the last row, `$FF` loops; pitch bit7 =
  absolute). 12 D files went to **100.0 strict** in one change (Another_Day
  81→100, Banana 69→100, Culture_Mix 62→100).
- **E**: wfprg **row 0**, applied ON the note-on frame by the
  set-instrument tail (byte-verified at 2_Young `$EE1F`); ties skip it.
  Plus `$c0-$ef` arp records **redirect the sound** (`ad+1` byte). Note
  formula (dis-verified): `note + conduct($E943) + transpose`. Timing
  calibrated per file by strict agreement.
- **V**: instrument **octave nibble** (+12·(oct−1)) + per-note instrument
  in the row's fx byte (`&$E0==0`).
- **C**: RESOLVED (2026-07-13) — the wfprg walk is a py65-verified
  frame-paced program: 11-byte instrument records (stride from the
  `ASL x3 + ADC x3` sound-set tail), walk start = record byte +2, ONE row
  per frame, `wf ≥ $90` = jump BACK `(wf−$90)` rows and execute that row
  (`$91` = 1-row park, `$93` = 3-row chord arp). Two per-file restart
  models ('onset'/'steady' free-running loop) selected by strict agreement;
  drum **rolls** (a `$09` TEST+GATE row re-executed each loop) expand into
  synthetic re-gate notes. The earlier "regressed Bahbar" gate was a
  dormant **stride bug** (`instr % 1`), not walk phase. **C strict median
  66.7 → 86.0** (55/80 files ≥ 80 strict, was 26).

## Variant V — the wrapper class (was "multispeed D", was 0.0)

The six `*_VE-2x/-4x` files are `play=$0000` rips: a raster wrapper installs
its own IRQ, drives a 3-JMP module (init/play/fast) 2 or 4 times per frame,
and the module's seq-row read is **byte-identical to D's track read** — a
false-locate trap that scored 0.0 on both metrics twice
([PATTERNS.md](PATTERNS.md) D2). V dispatches BEFORE D in `locate()`.
Tracker engine: `$40`-byte per-voice state blocks (`$0400/$0440/$0480`),
per-seq **length-in-ticks** table (the track advances on expiry,
independent of the row stream), rows always 1 tick, `$60` = blank row,
`$5F` = gate off. Everything locates in-file; only the `$0400` state is
runtime. The `$Cx` global-tempo fx is recorded but not emulated (a flat
calibrated clock beats the naive tick→call map).

## Validation method

`bin/_sdi_sweep.py` (scratch): dual-metric corpus sweep — **windowed**
(0..+37 semis, arp-tolerant) and **STRICT** (semitone delta == 0) onset+pitch
agreement vs siddump, 12 s windows, samples at `fr+{0,2,3,5}`. The
windowed−strict gap is the pitch-carrier signal; report both, always
([PATTERNS.md](PATTERNS.md) D4). E and V select their timing model per file
by strict agreement (D5).

## Open items

- **E conduct program**: decoded (the ghost 4th channel writes a global
  pitch base `$E943` real voices offset from) and shipped as zero-delta-safe
  infrastructure; the ghost timeline for the **wrapper** nch=4 generation
  is not yet wired (Afterburner 80/40, Ambient 78/18).
- **E `$Cx` track-delay = TRAILING** (FIXED 2026-07-13): the player
  (`$EE8F`) stores `b&$3f` to the per-voice delay cell `$e910,X`; the gate
  (`$EE50`) pays it only AFTER the seq it was read with, before advancing to
  the NEXT track entry — a trailing hold, not a leading pre-seq delay. Our
  decoder had added it before the following seq (the +3-tick/+6-frame drift).
  Emulation-verified (`bin/_sdi_e_gatewatch.py` gate rises +
  `_sdi_e_trackwatch.py` armed-but-unpaid delay). Corpus: E strict median
  47.5 → **50.8**, windowed 70.7 → 75.0, 43 files up (JS_Beta +24, Moi_Funk
  +21, Evil_Within +16, Sweeper +15, Xard +6) vs 10 tiny regressions on
  already-broken files (windowed still up there). Lock:
  `TestSDIVariantETrackDelay`.
- E laggards: **Arabia** (nch=4 ghost/conductor file) — grammar, pitch, base
  timing AND the trailing-delay all dis/emu-verified; its residual is now the
  unwired **wrapper conduct/ghost timeline** (pitch), not the track-delay.
  Glide-heavy files still park strict in slides.
- **C niche**: Everytime (noise twins), Ninja_IV (gateless test-click
  percussion — a metric disagreement), Tanks_3000 (dormant-copy image; its
  live `$1000` player is an unrecognized variant), Magic_Moment glides.
- V residual: its own wfprg walk (drum absolutes, detunes), tempo commands.
- **Multi-subtune**: A/C/E supported; B indexes subtunes differently
  (unsupported); Tanks_3000's 12 subtunes need its live player first;
  ~417 of 671 songs still undecoded (single-subtune-per-file default).
- **Variant DELTA (8 files, DONE 2026-07-13)**: the play+3 JMP-wrapped,
  self-mod-dispatch E-family cluster. TWO state layouts, SAME grammar:
  ZERO-PAGE state (Commando/Delta/Delta_Slow/DMC_Demo_remake/Short_Deel) and
  PAGE-$03 state (Invention_1/Lightforce/Neurotica_short). Track grammar =
  E's exactly (incl. the trailing $Cx delay); tables relocation-located by
  signature (zp B4 / abs BC forms); SEQ row = [sound $80-$bf & $3f][dur
  $60-$7f & $1f, persists][note <$5f + transpose], $00 = seq END. RE'd +
  emulation-verified (bin/_sdi_delta_seqwatch.py / _sdi_e_gatewatch.py).
  Medians windowed 89.8 / strict 55.5 (Invention_1 98.7/98.7, Delta_Slow
  100/83, Neurotica 100/83). GUARD: the abs (BC) form shares the ptr-load
  shape with variant B and with 9 unrelated engines, so the entry REQUIRES
  the Delta play-dispatch sig `C9 02 F0 ?? C9 01 F0` (CMP #$02 track /
  CMP #$01 seq) — present in all 8 genuine, none of the 9 false-positives.
  Base note only (the wfprg arg walk arps the pitch — Stage B, like E).
  Lock: TestSDIVariantDelta.
- **Coverage**: the 32 locate-NONE play+3 files are ALL SDI-family (player-id:
  GRG/Geir_Tjelta/SIDDuzz'It — NOT foreign DMC/Hubbard rips) behind init/play
  JMP wrappers, in sub-variant clusters. DELTA-class (8) fully cracked (zp +
  page-$03). E single-store-init gen (+4: L-Forza_Remix/L-Forza_long_edit
  95.4/95.4, Leon_Latex 64/30, Club_69 42/20) routed to the E decoder via a
  fallback tl/th sig (init copies each ptr byte once vs twice). Remaining NONE
  is a HETEROGENEOUS long tail (structural map 2026-07-13): ~22 play+4
  (E-family init/table variants, e.g. Pepita = another tl/th shape), 10 D-seq
  + 7 E-seq play+3 hybrids, ~40 one-off covers/foreign/digi at weird play-init
  offsets. Clusters: [LDX LDA STA STA] (Mountain_March/
  Prehistoric_Tale/Title_Needed), [TAX LDA STA LDA] wrapper (Commando_Arcade/
  Hysteria_Pimped), + the 9 abs-form false-positives the dispatch guard
  correctly excludes (Crystal_Gazer/Doors_of_Perception/... = other engines).
  ~73 more locate-NONE with other play-init offsets.
- **Stage B native** — SHIPPED (`bin/build_sdi_native_song.py`) and now swept
  over the whole flat dir: **262 of 441 build, 786 scored voices**, tracked and
  reproducible from a fresh clone via `pyscript/sdi_native_sweep.py`. See below.

## Stage B native — the pitch-ceiling lift (`bin/build_sdi_native_song.py`)

The Stage-A strict ceiling (~50 on E/DELTA/V) is the per-frame **wfprg arpeggio**
a static decoder can't model. Stage B captures it: a trace-driven shim into
`build_mon_native_song` (the DMC/Sound-Monitor pattern) places notes at emulated
`$D404` gate-rises (`measure_onsets`), takes base pitch from the trace, and the
engine reproduces every per-frame freq/waveform/pulse/filter byte-exact.

First cut (onset-aligned, single window, inline phase-aligned freq+wf fidelity —
never emits blind). Proven on two variant-E files:

| file | Stage A strict | Stage B (per-frame freq+wf, v0/v1/v2) |
|------|---------------|----------------------------------------|
| 2_Young_2_Die | ~67 | **98.4 / 85.3 / 99.9** |
| Tranedans | **13.4** | **88.7 / 91.9 / 99.3** |

v1 residuals are the known drum/hat re-gate capture class.

**Ground through to ~100% (2026-07-18).** Fixes, each a general lever:
- **adaptive part-splitting** (`auto` splits the whole song, no cap force-merge);
- **DELTA/E legato voices** take their tie-boundary schedule from the trace's own
  pitch-change frames (drift-free ties);
- **tighter legato criterion** — fast arp voices that re-gate regularly stay on
  the gate-rise path (Moi_Funk v1 37→83);
- **leading rest** for late-entering voices (they were shifted early by their
  whole start offset — Bahbar v2 played 769f early; broad lift to 98-100%);
- **last-note sustain** — hold the final note while the voice stays active
  (Neurotica_short 54/59/62 → 99.9/99.6/99.9; the "deep-song drift" was a
  truncated sustained tail);
- **noise-aware metric** — a noise frame is scored on its waveform, not a
  meaningless pitch (2_Young v1 85→100);
- the **C-class `$D404=$08` TEST gate is a non-issue** (the capture sidesteps it);
- **variant V / self-IRQ (`play=$0000`) driven directly** — siddump/measure_onsets
  choke on it, so the module (init/play/fast at base/+3/+6, located via the
  wrapper's `JSR base; CLI`) is driven via py65 at `v_mult` play-calls/frame; that
  py65 trace is the ground truth, and the emitted SF2 is validated against it.
  **All 6 V files build** (Different_Reality 99.1/99.4/99.1, Oh_Boy 99.7/99.7/80.3,
  Implocation 97/99.8/96, …).

**All six variants (A/B/C/D/E/V) now have Stage B.** Most E/DELTA/C/V voices are
**98-100%** (2_Young 100/100/100, Delta_Slow 100/100/100, Neurotica 99.9/99.6/99.9,
Moi_Funk 99.9/99.9/98.6, Kirby ~99.7). The lone residual is a **fast per-frame arp
voice class** (Bahbar v1/v2 ~92.7/90.4, Filthy_Hit v0 76) — genuinely tonal, the
honest FM-capture ceiling (lifting it needs shared-MoN-engine FM work).

### ⚠️ The `$D418` passband was never captured (fixed 2026-08-13)

`HARDTRACK.md`'s cross-builder audit recorded **"SDI: low 100% — default was
right by luck"**. That verdict came from one file. Across a 30-file sample,
**15 fail**: the originals select **BP, LP+BP, LP+HP and LP+BP+HP**, and
modulate up to 10 times, while every build rendered plain low-pass with the
filter **routed on 100% of frames**.

Unlike MoN, HardTrack and DMC this was **not a stale artifact** —
`build_sdi_native_song.py` never passed a passband at all, so `_filt_set_row`
defaulted to low-pass and no rebuild of the old corpus would have helped.
Fixed by handing `build_native_song` the 3-tuple it expects. Verified across
every failure class, all **0.0% → 100.0%** with the music unchanged:

| file | original selects | before | after |
|---|---|---|---|
| `Ambient` | LP+BP | 0.0% | **100.0%** |
| `Acid_Jazz` | LP+BP+HP | 0.0% | **100.0%** |
| `Airwalk_II` | BP | 0.0% | **100.0%** |
| `Alone_in_Space` | LP/LP+BP, 10 changes | 34.0% | **100.0%** (10 of 10 matched) |

> ⚠️ **The V-wrapper path is deliberately still a 2-tuple.** Variant V is
> driven through py65 and `v_traces` does not record `$D418` at all, so there is
> no passband to pass. Those 6 builds keep the low-pass default; capturing it
> means extending the py65 tracer. `pyscript/passband_check.py --player sdi`
> reports them if their originals select otherwise — a stated gap beats a
> 3-tuple of the wrong thing.

**Corpus rebuilt and re-checked (2026-08-13/14, 441 files, 23 chunks):**

| | |
|---|---:|
| select the original's passband | **237 of 281** |
| unexercised (original never routes and never selects one) | 7 |
| unconfirmed (multi-part, window may over-run part 1) | 33 |
| failed | **5** |

Before the fix a 30-file sample was 12 pass / 15 fail. Build outcomes are
unchanged by the fix — **261 built / 62 refused / 118 errored** against
262/62/117 before, and per-variant fidelity medians move only where one variant-D
file stopped building (A 99.9, B 99.9, C 98.1, D 96.3, DELTA 99.9, E 99.7,
V 96.8). That is the expected result: `$D418` is in none of the freq+wf columns,
so a build-rate change would have meant something was broken.

⚠️ **Three of the five failures are `*_VE-4x` files — the V path, exactly as
predicted.** `Different_Reality_VE-4x`, `Underwear_VE-4x` and
`Implocation_VE-4x` each differ by **12 audible frames** at 98.6% (an `off →
LP` startup difference); `Filthy_Hit_VE-4x` is the real one at **0.0% with 1,387
audible frames**, selecting BP where we write LP. That is the documented cost of
leaving `v_traces` alone, and it is now measured rather than assumed. The other
two failures are `Coming_Soon` (90.9%) and `Lederhosen`, plus `Bahbar_v` which
has no original to compare against.

### RESOLVED 2026-08-14 — and only half of it was the builder

`v_traces` now records `$D418` on the same clock as `cut` and `$D417`, and the V
path hands `build_native_song` a 3-tuple like every other path. It also **prints
the passband runs it captured**: the V rip is the one family where siddump
cannot drive the player, so that list is the only reference there is, and
comparing a build against a reference nobody printed is how three confident
wrong Blackbird readings happened (`PATTERNS.md` F7).

With the capture in, `Filthy_Hit_VE-4x` moved 0.0% → **25.8%** and stayed a
failure. Dumping both sequences rather than believing either one:

| reference | first 400 frames |
|---|---|
| py65 at `mult=1` | `off x6, BP x384, LP x10` |
| **py65 at `mult=4`** (the tune's real rate) | `off x1, BP x96, LP x303` |
| siddump | `off x25, BP x375` |

**siddump cannot adjudicate a V rip.** The wrapper declares `play=$0000` and
installs its own IRQ at `v_mult` calls per frame; siddump calls the player
**once** per frame. On a tune that alternates its passband *within* the frame
that is not a rounding difference — 375 of 400 frames BP against 303 of 400
ending on LP — and the mult=1 run reproducing siddump is what identifies the
call rate as the whole of the disagreement.

So `passband_check` gained what Blackbird already had: a reference that drives
the tune. `ref: "sdi_v"` is per **FILE**, not per player — `sdi_v_reference`
returns `None` for the five non-V variants so they keep siddump, because
swapping their reference would have changed 276 rows to fix 5.

| file | before | after, at its own part-1 span |
|---|---:|---:|
| `Filthy_Hit_VE-4x` | 0.0% (1,387 audible) | **100.0%**, routed 100% |
| `Different_Reality_VE-4x` | 98.6% | **100.0%** |
| `Underwear_VE-4x` | 98.6% | **100.0%** |
| `Implocation_VE-4x` | 98.6% | **100.0%** |
| `Pultost_VE-4x` | — | **100.0%** |

Corpus: **237 → 241 of 281**, failures 5 → 3 (`Bahbar_v` has no original,
`Coming_Soon` 90.9%, `Lederhosen`). The other 276 rows are unchanged, which is
the point of the per-file reference. Pinned by
`pyscript/test_passband_check.py`.

### The unconfirmed rows are resolved — 29 → 0 (2026-08-14)

They never needed a human to assert 29 windows: the builder had computed each
one and printed it. `emit_one` now writes a `.span` sidecar beside every part and
`passband_check` narrows each file to its own part 1 (`PATTERNS.md` F8;
`part_span`/`window_for` in `fidelity_common`).

**241 → 258 of 281**, with 27 rows measured over a derived window. Failures went
**3 → 7**, and that is the mechanism working rather than a regression: over-run
can only MANUFACTURE disagreement, never conceal it, so resolving a window turns
unknowns into passes *and* exposes the genuine defects the noise was covering.

> **`Juba-Jazz` FIXED 2026-08-15 — 52.8% → 100.0%.** Its filter is switched on
> by `$D417` routing `00 → $f4` + `$D418` LP+BP on one note-on, with the **cutoff
> held at 0 for the entire song**. `detect_filter_drives` keys on cutoff jumps,
> so it credited nothing, no filter program was attached, and the build never
> left low-pass. A second, strictly additive pass now credits a filter ENABLE
> that the cutoff pass missed (`PATTERNS.md` F9). Verified on the neighbours:
> HardTrack 31/33 byte-identical and the other 2 identical on passband and
> fidelity; 12 sampled passing SDI files still pass.

| newly established | part 1 | verdict |
|---|---:|---|
| `Juba-Jazz` | 72 s | **52.8%**, 661 audible frames — real |
| `Tanks_3000` | 32 s | **94.9%**, static where the original modulates 12x, 72 audible — real |
| `Funk_Facet` | 24 s | **99.0%**, 12 audible frames — real, marginal |
| `Arabia` | 18 s | **98.2%** — real |
| `Finish_Line` | 22 s | **100.0%** (44 changes on both sides) |
| `Homebrew` | 14 s | **100.0%** (42 changes both sides) |

⚠️ **`Juba-Jazz` and `Tanks_3000` were never at risk of over-run at all** — their
part 1 is LONGER than the 28 s window, so nothing could loop inside it. The old
rule "multi-part ⇒ unconfirmed" was over-cautious in one direction and blind in
the other; the sidecar replaces a proxy with the actual question.

The old text: *the 33 unconfirmed are multi-part files whose part 1 may end
inside the 28 s window; resolving them needs a per-file asserted `--seconds`.* Their mode SETS and
change counts now track the originals closely (`Finish_Line` 56 vs 56,
`Curse` 87 vs 84, `Homebrew` 85 vs 84), where before the fix every one of them
was a flat `LP` with 0 changes.

### Current corpus figure: 267 of 281 (re-measured after `00893cd`)

The **258 of 281** figure above predates a fix to `passband_check.py` itself
(`00893cd`): its alignment fit used to maximise the match RATE rather than the
match COUNT, and because the scorer trims the tail, a shift could shrink the
denominator without repairing a single frame — inflating a percentage and
reporting a meaningless offset. `py -3 pyscript/passband_check.py --player sdi`
run fresh against the current corpus now reports:

| | |
|---|---:|
| select the original's passband | **267 of 281** |
| unexercised (original never routes and never selects one) | 7 |
| unconfirmed (multi-part, window may over-run part 1) | **2** |
| failed | **5** |

`267 + 7 + 2 + 5 = 281`. Two things moved since 258:

- **`Tanks_3000` and `Juba-Jazz`**, both failures in the 258-count, are now
  fixed (see above and the canonical-filter-key section at the top of this
  document) — that alone accounts for 258 → 260.
- The remaining 258 → 267 move (net +7, offset by 2 files that are now
  UNCONFIRMED where they previously read as resolved) is the `00893cd` fit
  correction changing which frames the tool counts as compared, not a rebuild.

⚠️ **Two files are UNCONFIRMED again, and were not before**: `Neverending_Story`
(16.3%, 13 parts) and `Solar_Plexus` (98.7%, 6 parts) — the corrected fit no
longer silently absorbs their over-run, so the F8 per-file `.span` window does
not resolve them cleanly. Re-run with an explicit per-file `--seconds` before
treating either as a pass or a fail.

**Failed (5, unchanged in membership from the cross-check, values re-measured
today):** `Arabia` 97.8% (see the canonical-filter-key section above —
previously published as 98.2%), `Bahbar_v` (no original to compare against),
`Coming_Soon` 90.9%, `Funk_Facet` 99.0%, `Lederhosen` (static where the
original changes twice).

### The corpus sweep (`pyscript/sdi_native_sweep.py`, 2026-08-12)

The figures above came from `bin/_sdi_stageb_sweep.py` — **untracked**
(`.gitignore` excludes `bin/_*.py`) and a hand-picked **15-file sample across 3
of the 6 variants**. The tracked sweep replaces it: it derives its corpus from
`SID/Gallefoss_Glenn/` rather than naming one, invokes the builder per file, and
**records refusals with their reason instead of dropping them**. This is also the
shipping path this section used to list as open — the builder was standalone,
one file at a time.

**All 441 files in the flat dir, no sample:**

| | files | |
|---|---:|---|
| **built** | **262** | 786 scored voices |
| refused | 62 | all one reason: `cannot be driven by measure_onsets (self-IRQ / multispeed)` |
| errored | 117 | 98 `not an SDI play+3 rip`, 16 `WAVE overflow (>256 rows)`, 2 timeout, 1 `IndexError` |

| variant | voices | median | =100 | <90 |
|---|---:|---:|---:|---:|
| A | 120 | 99.9 | 30 | 8 |
| B | 75 | 99.9 | 16 | 10 |
| C | 201 | 98.1 | 21 | 21 |
| D | 15 | **95.9** | 2 | **7 of 15** |
| DELTA | 21 | 99.9 | 4 | 0 |
| E | 336 | 99.7 | 59 | 17 |
| V | 18 | 96.8 | 0 | 2 |

**103 of the 262 have all three voices ≥99; 11 are 100/100/100.**

Read these with three conditions attached:

- **A median is not a pass rate.** 65 of 786 voices are below 90, and they are
  not spread evenly: **variant D is 7 of its 15**, the only variant where a
  broken voice is the common case (`Onkie_Donkie` 47.7/77.2/71.1, `Lame`
  55.3/86.1/99.3, `Culture_Mix_2` 56.3/99.6/99.9 — yet `Culture_Mix_1` is
  99.7/100/100). D is 5 files; treat its median as a sample, not a verdict.
- **The `n` is the SONG LENGTH, not per-voice information.** The builder now
  prints `voice N: X%  (n=…)` and routes through `fmt_pct(p, n=…)`, so a thin
  comparison gets the `!` marker — but the count is **identical across all three
  voices on every file measured** (Kirby 2144/2144/2144, Delta 7770×3,
  Eurovision 802×3), because `measure_parts` skips a frame only when **both**
  sides have freq 0 and siddump holds a voice's last written frequency through
  its rests. After a voice's first note its freq is essentially never 0 again.
  So this `n` answers *"was the song long enough?"* and **not** *"did THIS voice
  carry enough information?"* — a voice that plays one note and falls silent
  scores over the same `n` as one that plays throughout, and the second question
  is the one a per-voice percentage actually needs. Still open.
- **The marker does not fire on this corpus.** The ten smallest built files by
  SID size run `n` = 802–7770, all far above the 250-frame (5 s PAL) floor.
  The guard is wired in and inert here; it is insurance for a short rip, not a
  filter that removed anything from the table above.
- **`errored` ≠ unsupported.** `WAVE overflow: N rows > 256` (16 files, seen at
  259–305 rows) is a **builder cap**, not a property of the music — the same
  class of ceiling as Hubbard's 128-sequence cap.

> **A sweep that stops being able to launch a process has stopped measuring.**
> The first full-corpus run returned rc `3221225794` (`STATUS_DLL_INIT_FAILED`)
> for every file from #275 of 441 onward — ~5 h in, the parent could no longer
> spawn a child — and **did not stop**. It counted all 167 as `errored`
> alongside the real classes and printed `built 161 refused 38 errored 242 of
> 441`, whose per-variant medians were in fact an alphabetical **A–O sample**.
> Three of those files build cleanly on a fresh invocation, so 167 "results"
> were fabrications. The sweep now quarantines those return codes as
> `unmeasured`, aborts after `--infra-abort` consecutive ones (default 3), and
> prints the resume command; the table above is the merge of the valid 274-file
> portion with a chunked re-run of the other 167. Pinned by
> `pyscript/test_sdi_sweep_launch_guard.py`.

## Stage A

`bin/sdi_to_sf2.py [--subtune N] [--c-steady]` → `out/sdi_sf2/`: 1 SDI tick
= 1 Driver-11 row, pitch resolved through the song's own freq table to the
PAL semitone grid, AD/SR from the located instrument tables (A/B; defaults
logged for C/D/E/V), ties re-gate (runtime Driver 11 cannot parse tie bytes
— the Sound Monitor lesson). `--subtune N` converts a specific subtune
(A/C/E; a guard skips subtunes that duplicate subtune 0). **348 SF2s**
(0 conversion failures on located files).

> **"0 failures" is not a fidelity statement** — it means "emitted without
> raising". `convert()` ships an SF2 whenever `locate()` succeeds, printing
> `WARN: N instruments use DEFAULT timbre/ADSR`. **274 of 324 (85%) carry some
> default instrument data**: flags missing in all 274, ADSR in 173, wfprg in 75.
> Most shipped SDI SF2s are PARTIAL, and the builder says so per file.

### Part splitting (fixed 2026-07-30) — 13 files were silently missing music

Driver 11's sequence pointer table holds exactly **128** entries. Stage A emitted
**one** module per song regardless, and `galway_driver11_emitter` truncated the
excess — **silently** until 2026-07-30, dropping the over-cap sequences *and*
every orderlist entry referencing them, so a voice lost arbitrary chunks of its
structure while the file still parsed, loaded and played. The builder's own log
had been printing the discrepancy all along (`sequences=171` while 128 were
emitted); nothing compared the two.

| file | was dropping | now | | file | was dropping | now |
|---|---|---|---|---|---|---|
| `Psycho` | **101** | 3 parts | | `L-Forza_long_edit` | 28 | 2 parts |
| `Happy_Birthday_Tg-Acme` | **100** | 3 parts | | `Sveitser_Ost` | 27 | 2 parts |
| `Tanks_3000` | 86 | 2 parts | | `Onkie_Donkie` | 12 | 2 parts |
| `Jessie_Jazz` | 76 | 2 parts | | `Holy_Josh` | 7 | 2 parts |
| `Psycho_II` | 50 | 2 parts | | `Lame` | 5 | 2 parts |
| `Another_Day_in_Paradize` | 43 | 2 parts | | `Culture_Mix_2` | 43 | 2 parts |
| `Mini_Poelse` | 31 | 2 parts | | | | |

`convert()` now plans parts with `sidm2.d11_windowing.plan_row_windows`. SDI
packs a per-voice **row grid** (`build_rows`) before `segment_track`, so cutting
at a row index is aligned across voices by construction — all three share the
grid. Windows grow by doubling then binary-search the edge, and count what a
window **needs** (post-dedup) rather than reading a count back out of an emitted
file, which cannot detect overflow because the emitter truncates.

Naming: a song that fits keeps its original filename; a split song becomes
`NAME_part01.sf2`, `NAME_part02.sf2`, … and the superseded single file is
**deleted** (leaving the truncated one beside the parts invites opening it).

**Verified**: full-corpus A/B against the pre-fix builder — **330 byte-identical,
0 unexpected diffs**, exactly the 13 known-broken songs newly split (28 parts
replacing 13 files, so 343 songs now emit 358 files). Re-running
`pyscript/sf2_truncation_sweep.py sdi` reports **0 lose music** (was 13).
