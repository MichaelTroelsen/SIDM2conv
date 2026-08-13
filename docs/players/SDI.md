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

**The corpus was NOT rebuilt.** 262 songs is hours, and every one of them still
carries the low-pass default until it is. See `PATTERNS.md` F7.

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
