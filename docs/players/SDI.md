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

## `Barbers_Adagio_64` cannot be siddumped -- and it is NOT untraceable (2026-09-01, task `barbers-adagio-64-siddump-rc1`)

The 728-file `$D418` blindness sweep hit exactly one error, and this is it:
`SID/Gallefoss_Glenn/Barbers_Adagio_64.sid`, `RuntimeError, siddump failed
(rc=1)`. Unmeasured is not measured-zero, so the cause is written down here
rather than left as a footnote.

**THE CAUSE IS A BUSY-WAIT ON `$D012`, and siddump has no VIC.** The file is
an RSID declaring `play=$0000`, so siddump takes its interrupt-vector fallback
(`siddump_complete.py:664`) -- `$01 & 7 == 5`, so it reads `$FFFE/$FFFF` and
recovers `$2708`. That much works. What it recovers is not a per-frame play
routine but one link of a **4x multispeed raster-split chain**:

```
$2700  A2 00      LDX #$00
$2702  8E FF 26   STX $26FF        ; split counter := 0
$2705  4C 00 10   JMP $1000        ; <- the REAL init
$2708  48 98 48 8A 48              ; PHA/TYA/PHA/TXA/PHA
$270D  AD FF 26   LDA $26FF
$2710  C9 04      CMP #$04
$2712  D0 0B      BNE $271F        ; not the 4th split yet
$2714  A9 00      LDA #$00
$2716  8D FF 26   STA $26FF
$2719  68 A8 68 AA 68 40           ; restore + RTI  (frame done)
$271F  AE FF 26   LDX $26FF
$2722  BD 51 27   LDA $2751,X      ; raster-line table: $08 $56 $A4 $F2
$2725  CD 12 D0   CMP $D012
$2728  B0 F8      BCS $2722        ; <<-- SPINS until the raster passes
$272A  EE 19 D0   INC $D019
$272D  AE FF 26   LDX $26FF
$2730  BD 55 27   LDA $2755,X
$2733  8D 37 27   STA $2737        ; self-modifies the operand below
$2736  20 03 10   JSR $1003        ; <- the REAL play, called 4x per frame
$2739  EE FF 26   INC $26FF
$273C  4C 0D 27   JMP $270D
$2740  A9 35 85 01                 ; INIT (header): $01 := $35
$2744  A9 27 A2 08 8D FF FF 8E FE FF   ; $FFFE/$FFFF := $2708
$274E  4C 00 27   JMP $2700
```

`$D012` is a constant in siddump's CPU, so `BCS $2722` at `$2728` never falls
through and the `MAX_INSTR` guard fires. The tool is reporting honestly; it
simply cannot drive a raster-timed player.

**TWO PLAUSIBLE CAUSES WERE MEASURED AND BOTH ARE REFUTED.** Neither was
assumed away:

- *"`play=$0000` is untraceable."* No. `SID/Gallefoss_Glenn/` holds **22** RSID
  files with `play=$0000` and **21 of 22 trace fine** under `siddump -t5`
  (rc=0, 240 rows each). Barbers is the sole failure. The vector fallback works.
- *"referencing `$D012` is the tell."* No. **11 of those 21 working files also
  read `$D012`** near their recovered play address and trace fine. Reading it
  is harmless; **branching back on it** is not. The discriminator is the loop at
  `$2728`, not the register.

**AND THE FILE IS NOT BROKEN -- zig64 traces it, at either entry point.** Its
`$1000` is an ordinary 3-byte jump table (`$1000: JMP $261A` init,
`$1003: JMP $17A6` play), which is the usual Gallefoss shape:

```
$ sidm2-sid-trace.exe barbers.prg 200 2740 2708 0    rc=0   3515 CSV rows
$ sidm2-sid-trace.exe barbers.prg 200 1000 1003 0    rc=0   1376 CSV rows
```

zig64 is cycle-accurate, so its `$D012` advances and the wait terminates. The
2.6x row difference is the 4x multispeed: the wrapper calls `$1003` four times
per frame, so tracing at `$2740/$2708` measures the tune as it actually sounds
while `$1000/$1003` measures one call per frame.

**SO THE ANSWER IS THE THIRD OPTION: it needs different init/play arguments,
and siddump has no way to accept them.** `siddump_complete.py` exposes `-a`
(subtune) and nothing for init or play, so there is no invocation of it that
traces this file. The gap is the CLI, not the rip. Scoring Barbers needs either
an init/play override on siddump or the zig64 path, and until one is wired its
`$D418` behaviour stays **unmeasured** -- deliberately, and visibly.

*Do not "fix" this by widening a sweep's exception handling.* The sweep
reporting one hard error out of 728 is the system working.

> **DO NOT CONFLATE THIS 21/22 WITH THE ONE IN CLAUDE.md.** CLAUDE.md's
> RSID-escape-hatch note says the VICE wrapper "traces **21 of SIDM2's 22**".
> That is a different tool over a different population and the numbers coincide
> by accident. The 21/22 above is **siddump** over the **22 RSID `play=$0000`
> files in `SID/Gallefoss_Glenn/` alone**; tree-wide there are **101** such
> files across 13 directories (Hubbard 18, Tel 16, Gray 10, Laxity 7, Galway 5,
> ...), so 22 is not the tree-wide count either. I checked this expecting the
> two populations to be the same set and they are not.

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

### 2026-08-19 correction — `Coming_Soon`/`Lederhosen` are not failures; `Neverending_Story` was a stale artifact, not a defect (task `sdi-passband-failures`)

The **267 of 281** table above is superseded. A fresh full-corpus
`passband_check --player sdi` pass, cross-checked against a rebuild at HEAD
(`runs.jsonl` id `sdi-passband-failures`, head `80fed62`), found three of the
rows above wrong:

- **`Coming_Soon` is 100.0%**, not the 90.9% two sections above — original and
  build both select `off/LP`, routed 85%. The 90.9% figure was stale.
- **`Lederhosen` is not a failure.** It is in the **unexercised** bucket —
  `off` on BOTH sides, measured inside its own part-1 span — not the failed
  bucket the table two sections above put it in.
- **`Neverending_Story`'s 16.3%/UNCONFIRMED reading (further above) was a
  phantom, not the corpus's worst defect.** The 26 files on disk that produced
  that reading are **46.8h old against a corpus median part-01 age of
  21.4h**, predating both the phase-2 rebuild and the `.span` sidecar
  (`PATTERNS.md` F8) the unconfirmed-row guard depends on. Rebuilding the file
  at HEAD does not reproduce a worse score — the builder **refuses to build
  it**: `REFUSING to build: this file cannot be driven by measure_onsets
  (self-IRQ / multispeed)`, at 59/161 emulated onsets vs. trace. It belongs
  with the 62 files the sweep table below already reports refused for that
  same reason — **a refused build, not a filter defect.** Its 26 stale
  artifacts were quarantined this session (moved, not deleted, to job scratch —
  not this repo's working tree — pending a decision on whether the shipped
  corpus should keep them).

With that phantom row removed, a full re-run reports:

| | |
|---|---:|
| select the original's passband | **271 of 280** |
| unexercised | 8 |
| unconfirmed | 0 |
| failed | **1** — `Bahbar_v` only (no original SID on disk) |

`271 + 8 + 1 = 280`. The **numerator is unchanged at 271** — this is a
corrected denominator, not an improvement: the phantom row was removed, no
build was fixed. Separately, `Arabia` and `Funk_Facet` (97.8%/99.0% above) are
both **100.0%** with the SDI-scoped filter flags now defaulted on
(`bin/build_sdi_native_song.py`, task `filt-flags-scope-to-sdi`) — leaving
`Bahbar_v` (requires a source file not on disk) as the sole remaining failure.

### 2026-08-22 correction — `Bahbar_v`'s "no original to compare against" was wrong (task `bahbar-v`)

The **"`Bahbar_v` (no original SID on disk)"** verdict two sections above was
itself stale. `SID/Gallefoss_Glenn/Bahbar.sid` **does exist on disk**, and its
current build **scores 100.0%** (`passband_check --player sdi --files
Bahbar`) — the premise that no original was available to compare against was
never checked before it was written up. `Bahbar_v` is not a missing rip; it is
a **superseded 11-part build from 17 Aug** (22 files: 11× `.sf2` + 11×
`.sid`, no `.sf2.span` sidecars — predating the `.span` feature every other
current SDI artifact carries), replaced by the **30-part `Bahbar_native`
build from 18 Aug**, under a `_v` naming no other SDI song uses. The two are
not duplicates — 0 of 11 overlapping parts are byte-identical, and the part
split differs.

The 22 stale `out/sdi/Bahbar_v_native_part*.{sf2,sid}` files were **moved (not
deleted)** to `out/sdi/_quarantine/`, matching the `Neverending_Story`
precedent above. A full `passband_check --player sdi` re-run afterward selected
279 representative builds (was 280 — `Bahbar_v`'s part01 build is no longer
one of them) and reported **no FAILED row**: **271 of 279** builds select the
original's passband, 8 unexercised, 0 unconfirmed, 0 failed. The numerator is
unchanged at 271; the last FAILED row is gone because its cause (a phantom
"no original" premise) is gone, not because a build was fixed.

### 2026-08-22 decision — `Short_Deel` stays in the corpus (task `short-deel-quarantine-decision`)

`Short_Deel` (`SID/Gallefoss_Glenn/Short_Deel.sid`, one of the DELTA-variant
/ zero-page-state cluster at line ~240 above) was checked for staleness
alongside `Dream` and `End_94` in `sdi-stale-artifacts-three-more`, the same
sweep that caught `Neverending_Story`. Rebuilding it at HEAD **refuses**,
verbatim: `REFUSING to build: this file cannot be driven by measure_onsets
(self-IRQ / multispeed). Pass --force to probe.` — 153/182 emulated onsets vs.
trace, the identical refusal class as `Neverending_Story`, not a filter
defect. Unlike `Neverending_Story`, Short_Deel's on-disk 6-part `out/sdi`
artifact was **never rewritten** (the build refused before writing anything),
and `passband_check` already files it correctly as **unexercised** (`off/off`
both sides, measured inside its own part-1 span) — it was never inside the
271-pass count and is not one of the failures either.

**Decision: KEEP Short_Deel in the scored corpus, no artifacts changed.** It
stays because it is genuinely **unexercised rather than failing** — the
checker's own honest classification, not a stale or fabricated reading — and
because it is the one piece of on-record evidence that the 85%
`measure_onsets` onset-agreement gate is marginal for the DELTA /
zero-page-state cluster: Short_Deel's own onset agreement is **84.1%**,
a hair under the 85% threshold, in the same cluster whose median strict
fidelity (55.5, see the DELTA row in the corpus sweep table below) is already
the corpus's weakest. Quarantining a song for sitting just below a threshold
would remove that evidence instead of recording it, which is the same reasoning
`sdi-passband-failures`' notes gave for not quarantining `Bahbar_v`. This is
the closed decision — do not re-ask it; if `Short_Deel` is ever rebuilt
successfully (e.g. a `--force`-probed self-IRQ/multispeed fix), re-measure its
onset agreement fresh rather than assuming 84.1% still holds.

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

> ⚠️ **This 262 is stale, and so is the 281 that superseded it.** As of
> 2026-09-11, after the SDI_WF rebuild below finished (`out/sdi` confirmed
> stable, no sweep running), `py -3 pyscript/gen_sf2_index.py` reports **293
> songs / 5114 files** for native SDI Stage B — see the dated note further
> down this page for the raw-glob cross-check (294/5118) and the built/refused/
> errored split (`built 278 of 441`) from the same rebuild. Do not quote 262
> or 281 as current.

## SDI_WF corpus rebuild, 2026-09-11 — and why variant D did NOT improve

**The whole 441-file corpus was rebuilt with the within-frame onset detector
(`SDI_WF`) at its new default and re-swept**: `pyscript/sdi_native_sweep.py -j6`,
111 minutes, `built 278 of 441`. The rebuild is confirmed on the ARTIFACTS, not
on the sweep's own success report — the prior SDI rebuild died in under five
minutes having written zero files, so the check is that **278 `_part01.sf2`
carry today's mtime** (3,815 parts in total) and the part-01 population grew
**286 → 294**.

| variant | voices | median | =100 | <90 | previous (n, median) |
|---|---:|---:|---:|---:|---|
| A | 120 | 99.9 | 31 | 8 | 120, 99.9 |
| B | 81 | 99.9 | 17 | 9 | 75, 99.9 |
| C | 201 | **98.3** | 24 | **19** | 201, 98.1 |
| D | 54 | **99.6** | 24 | **8** | 15, **89.9** |
| DELTA | 21 | 99.9 | 4 | 0 | 21, 99.9 |
| E | 339 | 99.7 | 62 | 17 | 336, 99.7 |
| V | 18 | **97.8** | 0 | 2 | 18, 96.8 |
| **ALL** | **834** | **99.7** | 162 | 63 | 786 |

**READ VARIANT D CORRECTLY — its 89.9 → 99.6 is NOT nine points of improvement.**
Its `<90` count is **unchanged at 8**. It was *8 of 15*; it is now *8 of 54*.
The same eight broken voices are still broken; **39 additional voices entered the
variant, all above 90, and diluted them**. Nothing was fixed in D — the
population grew. Quoting "D improved from 89.9 to 99.6" would be the exact
error the denominator rule exists to prevent, and the previous table's own
warning ("D is 5 files; treat its median as a sample") is what made the growth
visible.

**WHERE THE COMPARISON *IS* LIKE-FOR-LIKE, it is a real but small gain.** Four
variants have an unchanged `n`, so their numbers are directly comparable:
A (n=120) flat at 99.9 with one more voice at exactly 100; **C (n=201) 98.1 →
98.3 with `<90` falling 21 → 19**, i.e. two voices genuinely recovered;
DELTA (n=21) unchanged; **V (n=18) 96.8 → 97.8**. B, D and E all grew, so their
medians are not comparable against the earlier figures at all.

**THE 115 ERRORS ARE NOT 115 DEFECTS**, and the split matters more than the
total: **99** are `not an SDI play+3 rip (signatures missing)` — files that are
not SDI at all and never could build; **14** are `WAVE overflow: N rows > 256`,
a real builder ceiling (257–323 rows against a 256 cap), the same class as
Hubbard's 128-sequence cap; **2** are `timeout after 1800s` (`End_94`,
`Rectum`); and **1** (`Barbers_Adagio_64`) recorded a table border `+-------+`
as its error string, which is the error-scraper defect already on record rather
than a build failure.

**THE TWO TIMEOUTS ARE A MEASUREMENT GAP, NOT A RESULT.** `End_94` and `Rectum`
are the two longest decoded files in the corpus (the `span-desc` schedule runs
them first, at 120,097 and 120,004 frames), so the per-file 1800s cap excludes
precisely the heaviest material from every figure above. Raising the cap for
those two is what would close it; until then the corpus median is over a corpus
that is missing its two largest members.

**48 refused**, all with the same reason: `this file cannot be driven by
measure_onsets (self-IRQ / multispeed)`. Those stay in the scored denominator by
decision — they are the evidence that `measure_onsets` under-detects, and
quarantining them would delete the reason the onset fix exists.

### Why the gate refuses these 48 — the NAMED mechanism, and the two files that are already in anyway

The refusal reason string names two things at once ("self-IRQ / multispeed"),
but the mechanism the gate is built to catch, and the one this corpus's whole
onset-fix history traces back to, is **legato collapse in
`measure_onsets`'s gate-rise detection** (`sidm2/dmc_parser.py:378`, the
onset-agreement gate itself lives in `bin/build_sdi_native_song.py:590-615`).
`measure_onsets` finds a note onset by scanning for a `$D404` gate bit
0→1 rise in the **end-of-frame register state**. A player that retriggers a
note by writing gate OFF then ON **inside one play call** never leaves that
state visible — the frame reads 1→1 both before and after — so the
state-based scan records nothing, the note appears to glide under one held
gate (legato), the envelope never re-attacks in the model, and the onset
count comes back far under siddump's own count for the same voice while every
per-frame register metric still reads 100%. That is a **detector blind spot,
not a property of the music**, which is exactly why these files are evidence
for the fix rather than noise to remove.

The evidence is a real emulated-vs-real onset count, measured per file on the
voice carrying the notes, and it is what motivated shipping the within-frame
detector (`SDI_WF`, default since 2026-09-10) in the first place
(`sidm2/dmc_parser.py:393-407`, `bin/build_sdi_native_song.py:578-590`, first
700 emulated frames vs. a siddump reference truncated to the same window):

| file | state-based onsets | within-frame onsets | siddump reference | reading |
|---|---:|---:|---:|---|
| `Sveitser_Ost` | 1 | 67 | 67 | exact — legato collapse, fixed by `SDI_WF` |
| `Jessie_Jazz` | 1 | 70 | 70 | exact — legato collapse, fixed by `SDI_WF` |
| `Twin_Peaks` | 1 | 59 | 59 | exact — legato collapse, fixed by `SDI_WF` |
| `Psycho_II` | 4 | 66 | 66 | exact — legato collapse, fixed by `SDI_WF` |
| `Lame` | 23 | 24 | 25 | control, +1 — not a legato case |
| `Culture_Mix_1` | 47 | 47 | 47 | **control, unmoved** — already agreed, proves `SDI_WF` doesn't over-detect |
| `Neverending_Story` | 15 | 15 | 117 | **unchanged in both modes** — self-IRQ, not legato; no py65 replay drives it |

Four of those five originally-under-detecting files are exactly the legato
case and `SDI_WF` closed them — they build today. `Neverending_Story` is the
one file on this list that is genuinely the *other* half of the reason
string: a self-IRQ player that no py65-based replay (state-based or
within-frame) can drive at all, so its 15-vs-117 gap is untouched by the
fix, and `bin/build_sdi_native_song.py`'s own refusal message
(`REFUSING to build: this file cannot be driven by measure_onsets (self-IRQ /
multispeed)`, verbatim, 59/161 emulated onsets vs. trace when last probed —
see the "phantom" note earlier on this page) is honest about that. The
**48 refused in the 2026-09-11 SDI_WF rebuild are today's residual
population after that fix**: the legato-class files it could reach are gone
from the refused count, and what's left files under the same one reason
string because the gate does not yet distinguish "self-IRQ, unreachable by
either detector mode" from "still under-detecting for some other cause" —
which is itself further evidence that the gate, not just the pre-`SDI_WF`
detector, is where the next fix belongs. That is the case for the standing
decision above: shrinking or quarantining the 48 would erase the very
population this reasoning is built on.

**Corpus-policy wrinkle — the 48 are not the only files failing this gate,
and the policy is not uniform.** `Banana` and `Psycho` fail today's
onset-drivability gate exactly like the 48 above (`Psycho` was itself one of
the four the `SDI_WF` table's precursor measurement was run against, as
`Psycho_II`'s sibling file), yet unlike the 48 they are **not sitting in
"refused" with zero artifacts** — they already shipped, from an earlier build
predating today's 85%-agreement gate: `out/sdi/Banana_native_part01.{sf2,sf2.prov,sf2.span,sid}`
(4 files, 1 part) and `out/sdi/Psycho_native_part{01,02}.{sf2,sf2.prov,sf2.span,sid}`
(8 files, 2 parts) — **12 files on disk between the two songs**, confirmed by
directory listing on 2026-09-11, not the "24" figure floated in an earlier
pass at this question; that earlier figure is not reproducible from what is
on disk and should not be repeated. The point stands regardless of the exact
count: those artifacts are not being rebuilt or re-verified by the current
sweep (both songs are D-variant and appear in the 13-file "no artifact
before or after" list a few sections up for the *loop-guard* fix, which is a
different fix than `SDI_WF` — they never got as far as a fresh onset
measurement under the current gate). **Decision, so it is not re-asked: the
existing `Banana`/`Psycho` artifacts stay on disk, untouched and unscored by
the current gate**, exactly as `Short_Deel` and `Bahbar_v` were kept above —
this repo's policy has consistently been to keep what already shipped rather
than delete evidence, not to hold every song to the gate version active on
the day it happens to be re-swept. What the policy explicitly does **not**
do is claim those 12 files pass today's 85% gate — they don't, and no
sweep should report them as passing without re-running the onset check
under `SDI_WF` first.

---

| variant | voices | median | =100 | <90 |
|---|---:|---:|---:|---:|
| A | 120 | 99.9 | 30 | 8 |
| B | 75 | 99.9 | 16 | 10 |
| C | 201 | 98.1 | 21 | 21 |
| D | 15 | **89.9** | 4 | **8 of 15** |
| DELTA | 21 | 99.9 | 4 | 0 |
| E | 336 | 99.7 | 59 | 17 |
| V | 18 | 96.8 | 0 | 2 |

**102 of the 262 have all three voices ≥99** (was 103 before the D rescore:
`Culture_Mix_1` dropped out, its old 99.7 voice-0 read was itself stale —
see below); **11 are 100/100/100.**

Read these with three conditions attached:

- **A median is not a pass rate.** 66 of 786 voices are below 90, and they are
  not spread evenly: **variant D is 8 of its 15**, the only variant where a
  broken voice is the common case. D is 5 files; treat its median as a sample,
  not a verdict. **Rescored 2026-08-20 against the post-walk-fix builds**
  (`6aa2162`), each file measured over its own part-1 `.sf2.span` window, not
  the stale ~2401s window the pre-fix figures below used:
  `Onkie_Donkie` 70.5/100.0/83.7 (n=6800, span 0–136s, part 1 of 2),
  `Lame` 50.9/88.0/99.9 (n=3550, span 0–71s),
  `Culture_Mix_1` 94.2/100.0/100.0 (n=6600, span 0–132s),
  `Culture_Mix_2` 54.1/92.3/100.0 (n=5000, span 0–100s, part 1 of 2),
  `Dream` 74.3/87.6/89.9 (n=6200, span 0–124s). No `n` is underpowered
  (all ≫250, the 5s-PAL floor). Scored via `build_sdi_native_song._fidelity`
  against the on-disk part01 `.sf2` — a score-only read, no rebuild. The
  RETIRED pre-fix figures were `Onkie_Donkie` 47.7/77.2/71.1, `Lame`
  55.3/86.1/99.3, `Culture_Mix_2` 56.3/99.6/99.9, `Culture_Mix_1` 99.7/100/100
  (measured against builds windowed to the old ~2401s tick-cap ceiling) — do
  not quote them, they no longer describe anything on disk.
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

### Variant-D walk was bounded by the tick cap, not the song (fixed 2026-08-20, `6aa2162`)

A D track ends in `$ff` (loop), not `$fe` — true on all three voices of all 18
D-variant files, with `$fe` appearing nowhere — so no voice ever stopped on
its own and the walk ran to the 40,000-tick ceiling, which every caller then
read back as the song length. `sidm2/sdi_parser.py` now bounds each voice to
its own longest repeating pass (`pyscript/test_sdi_d_loop_guard.py` pins the
mechanism); see the commit for the rejected alternatives (first-`$ff` stop,
LCM-of-voices) and the siddump-repeat-period validation.

Re-measured directly against `out/sdi` (part + `.sf2.span` files on disk,
2026-08-20): of the 18 D-variant files, **5 build** (unchanged by this fix —
same 5 built before and after). The other **13 have no artifact at all,
before or after** — `Another_Day_in_Paradize`, `Banana`,
`Happy_Birthday_Tg-Acme`, `Holy_Josh`, `Jessie_Jazz`, `Max_Mix_1`,
`Mini_Poelse`, `Mummy`, `Psycho`, `Psycho_II`, `Space_Suit`, `Sveitser_Ost`
and `Twin_Peaks` — because they hit the Stage-B onset-drivability gate
(`measure_onsets` below 85%, "self-IRQ/multispeed"), which the loop guard
does not touch. That is a refusal, not a regression.

| file | parts on disk | window on disk (`.sf2.span`) |
|---|---:|---|
| `Culture_Mix_1` | **1** | 0–132s |
| `Culture_Mix_2` | **2** | 0–100s, 100–101s |
| `Dream` | **1** | 0–124s |
| `Onkie_Donkie` | **2** | 0–136s, 136–262s |
| `Lame` | **1** | 0–71s |

Before the fix all five reported windows near the old ~2401s tick-cap
ceiling (the commit message independently confirms `Lame`: 31 parts → 1,
~2405s trace → ~75s). **Rescored 2026-08-20** (task
`sdi-d-voices-rescore-post-walkfix`) directly against these on-disk part01
`.sf2`s, each over its own span above — see the updated figures two
subsections up. The corpus sweep this note used to say was needed was not:
`build_sdi_native_song._fidelity` reads an already-built `.sf2` and rewraps
it as a PSID probe, so scoring these 5 files cost two `siddump` runs each,
not a rebuild.

### 2026-08-20 — the "262 of 441 build" headline is stale; the rebuild meant to explain it did not run (task `sdi-part-counts-stale-after-d-rebuild`)

A full corpus re-sweep (`pyscript/sdi_native_sweep.py --jobs 8 --schedule
span-desc`, PID 114492, launched 2026-08-20T14:54:14Z) was meant to refresh
the built/refused/errored counts and explain the 262-vs-282 delta a4d47e4 had
already spotted but deliberately left unwritten. **It did not run to
completion.** Verified directly, not from a notification:

- The log holds only its 3 startup lines (schedule + `-j8` banners) and zero
  `N/441 done` lines.
- The main process is **absent from the process list**
  (`Get-CimInstance Win32_Process | Where CommandLine -match 'sdi_native_sweep'`
  returns nothing), though it was confirmed alive at T+4.5min in the prior
  session's own check.
- **Zero files in `out/sdi` are newer than the sweep's own recorded start
  timestamp.**
- No `wrote <json>` line, no `ABORTING` line, no summary line of any kind.

So `out/sdi` is **not** a freshly rebuilt corpus — it is exactly the state
a4d47e4 already measured, and the built/refused/errored breakdown that would
explain the delta below still does not exist.

**Re-derived directly from disk today** (`find out/sdi -iname "*.sf2"`):

| | count |
|---|---:|
| `.sf2` files | 5,048 raw → **5,039** excluding a stray scratch probe |
| `.sf2.span` files | 4,956 |
| distinct songs with ≥1 artifact | 282 raw → **281** excluding the same probe |

The raw glob catches `out/sdi/_diag*` (`_diag.sf2` +
`_diag_native_part01..08.sf2`, 9 files, mtime 2026-08-17 18:55) — a leftover
single-file scratch probe, not one of the 441 corpus songs. **Not removed
here** (this task is read-only on `out/sdi`); whoever next has write access
should delete it.

**281 built songs is the honest current figure — not 262 (the headline two
sections below), and not the 282 a4d47e4's commit message reported** (that
count didn't exclude the probe). The gap between 281 and 262 **predates this
task, is unchanged by it, and remains unreconciled** — a completed sweep is
still needed to produce a fresh built/refused/errored breakdown; this
session's attempt did not produce one.

**The `End_94`/`GT_Groove` anomaly a4d47e4 flagged is confirmed still
present, unchanged, on disk today:**

| song | native parts | vs. corpus median (6, p75=13) |
|---|---:|---|
| `End_94` | **1,190** | ~200x |
| `GT_Groove` | **402** | ~67x |
| `L-Forza_long_edit` | 174 | ~29x |
| `Stort_Plaster` | 137 | ~23x |
| `L-Forza_Remix` | 127 | ~21x |

Median part count across all 281 songs is 6 (p25=3, p75=13, max=1,190). These
five sit far outside that distribution. `git show 6aa2162` (the variant-D
walk fix) touches only D-decode code and none of these five are variant D, so
this is confirmed a **separate, still-unexplained defect** — not a side
effect of the walk fix, and not something this task's failed rebuild attempt
could confirm or refute either way.

> ⚠️ **The 281/262 figures above are now stale — re-derived 2026-09-11, after
> the SDI_WF rebuild (see the dated section below) finished and the tree was
> confirmed stable.** `py -3 pyscript/gen_sf2_index.py` (which walks `out/sdi`
> the same way this page's counts always have) now reports **293 songs / 5114
> files** for native SDI Stage B. A raw glob against `out/sdi` on the same day
> counted `*_part01.sf2` = **294** and all `*.sf2` = **5118** — 1 song / 4
> files more than the index script's figure; the `_diag*` scratch probe noted
> above is no longer present on disk, so it does not explain the gap, and it
> is not reconciled here. Do not quote 281 or 262 without this note. The
> part-01 population's growth **286 → 294** across the rebuild is corroborated
> independently in the dated section below.

**Variant-D table below re-verified against disk today, unchanged** (as
expected — nothing rebuilt): `Culture_Mix_1` 1 part, `Culture_Mix_2` 2,
`Dream` 1, `Onkie_Donkie` 2, `Lame` 1 — exactly matches a4d47e4. No drift,
confirming the corpus genuinely did not move.

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

## The ten "collapsed" tail parts are TWO causes, not ten defects (2026-09-05)

A corpus bundle audit flagged ten SDI artifacts: `Neurotica_short_native_part06`
and `_part07` at **0 bundles** (part06 carrying one note), and
`Noice_native_part15` through `_part22` at **4 bundles** each. Eight consecutive
tail parts at one value is a shared cause, and it turned out to be two shared
causes — neither of them a per-part defect, and neither of them a packer bug.

### Neurotica_short 06/07 — stale orphans a broken prune never removed

The two artifacts are **byte-identical** (md5 `5d4700da`, 13,612 bytes each) and
dated **2026-08-17**, while parts 01–04 are from **2026-08-18** and carry `.span`
sidecars that 05–07 lack. Part 04's span ends at 68 s and the song decodes to
66 s, so the current build is **four** parts. Parts 05–07 are the tail of a
superseded build — the same shape as the DMC `Rockbuster` orphan.

**`prune_stale_parts` cannot see them, and the reason is a prefix.** It globs
`{prefix}_part*.sf2`, `bin/build_sdi_native_song.py:366` passes
`out/sdi/{base}`, and the emitter writes `{base}_native_part{NN}.sf2`. So the
glob is `out/sdi/Neurotica_short_part*.sf2`, which matches nothing.
`bin/build_blackbird_native_song.py:3295` passes `f"{base}_native"` and is
correct; SDI is the copy that dropped the infix. **SDI's prune has always been a
no-op.**

Measured two independent ways, which agree:

| test | orphan parts | songs |
|---|---|---|
| `.sf2` with no `.span` sidecar | 72 | 10 |
| part mtime older than its own `part01` | 63 | 9 |

Largest: `Bahbar` 19, `Moi_Funk` 13, `Survival` 12, `Delta_Slow` 8,
`Tranedans` 4, `Neurotica_short` 3. All the no-span ones date to 2026-08-17.
The two tests differ only at the edges (`Velomatrix` part07 carries a `.span`
but is old; `_d` shows only in the first), so **neither test alone is the
population** — a post-`.span` orphan would carry a `.span` and be invisible to
the first.

Not fixed here: the fix site is the builder, and the task that found this
declares only this document as writable.

### Noice 15–22 — real parts of a decode that runs away

These eight are **not** orphans: they carry `.span` sidecars and share the
current build's timestamp. They are also not small windows — parts 01–13 span
2–4 s each, and parts 14–21 span **290–292 s each**. Four bundles across 292
seconds is correct compression, not a collapse; `BUNDLE_FLOOR = 5` is a
per-artifact constant with no notion of how much music the artifact covers.

What is wrong is upstream. `Noice` decodes to **116,578 events over 2400 s**,
and bucketed by minute the count sits at **3000 events per minute** from minute
two onward — that is 50 events per second at 50 Hz, i.e. **one decoded event on
every frame**. The song's real content is the first ~2 minutes (769 rising to
1889, then saturation). The 2401 s "song" is the decoder never terminating.

**Corpus-wide this is rare and specific — 3 files of 343:**

| file | variant | decoded span | minutes at ≥1 event/frame |
|---|---|---|---|
| End_94 | B | 2400 s | 36 of 40 |
| Noice | B | 2400 s | 37 of 40 |
| GT_Groove | B | 1600 s | 24 of 27 |

Every other file is clean, including 40 of the 43 variant-B files — so this is
**not** a variant-B decode property. `Stort_Plaster` (E, 5,044 events / 586 s),
`Kirby`, `2_Young_2_Die` and `Arabia` all show a normal density.

### This corrects an earlier verdict on this page's neighbours

`runs.jsonl:sdi-end94-gtgroove-part-count-anomaly` measured that End_94 and
GT_Groove split at the `CAP_B = 63` command-bundle cap — one `STEP` of End_94
costs 36–52 bundles, two cost 65–118 — and concluded the packer was working
correctly against dense music, leaving open "why is End_94's bundle density
double the corpus norm". **This is the answer, and it changes the verdict.**
The measurements stand; the density is not a property of the music. All three
CAP_B-saturated songs are exactly the three whose decode runs away, and a
decoder emitting an event every frame is what makes each 2 s window cost 36–52
bundles. The 1190 parts are still not a packer defect — they are downstream of a
decode that does not stop.

## Passband rescore on the current disk: 271/279, and ZERO failures (2026-09-05)

The published figure — **267 of 281**, with 7 unexercised, 2 unconfirmed and
**5 failed** — predated the stale-artifact rebuild. Re-run against the disk as
it stands (`py -3 pyscript/passband_check.py --player sdi -j8`, 3m00s):

```
coverage: 5027 .sf2 in out/sdi -> 279 representative build(s) selected
271/279 builds select the original's passband (or route nothing through the
        filter, where it cannot be heard)
  8 NOT COUNTED EITHER WAY (original never routes a voice in this window):
    Another_Beginning, Beginning, Beverly_Kraven, Holy_Daze,
    Invention_1, Kururin, Lederhosen, Short_Deel
exit 0
```

**The five failures and the two unconfirmed rows are gone: `grep -icE
"FAILED|UNCONFIRMED"` over the full output returns 0, and the tool exits 0.**
`Short_Deel` — kept in the scored corpus by decision — is now one of the eight
unexercised. That is **not a win either**: the checker prints `(filter never
exercised in this window -- NOT a pass)` against it, so it is neither in the 271
nor a failure.

Six rows still score below 100 % frame agreement and every one is classified as
passing with its reason printed, which is the checker working rather than a
softened gate:

| file | agree | why it passes |
|---|---|---|
| Aerodynamic | 99.5 | 1 frame, 99 % routed |
| Techno_Rave | 99.9 | 2 changes both sides |
| Trapped | 99.1 | 1 driver-side change, 100 % routed |
| Flames | 97.5 | no voice routed — passband inaudible |
| Trooper | 97.5 | no voice routed — passband inaudible |
| What_Is_Love | 94.5 | all 11 mismatches on frames the original does not route |

### Two caveats that belong beside the number

**The denominator moved 281 → 279 and only part of that is explained here.**
`out/sdi` holds 280 `_native_part01.sf2` artifacts; the checker scores 279. The
one it drops is **`_d`**, a base with no `SID/Gallefoss_Glenn/_d.sid` behind it
at all — correctly excluded, and junk in the corpus (it also carries 4 orphan
parts). Which two songs the earlier 281 counted cannot be recovered without
that run's file list, so **do not read 281 → 279 as "two songs lost"**; read it
as two different selections whose overlap was not recorded.

**The corpus is essentially unstamped, so this is not provenance-confirmed.**
The run reports `2 at ff52cb4 (dirty); 1 at 57f6ca3 (dirty); 1 at 7e67c33
(dirty); 275 UNSTAMPED (built before provenance existed)`. The claim "the
figures now postdate the stale-artifact rebuild" rests on the failure count
being zero, **not** on any artifact being able to say which commit built it.

The probe `.sid` files the tool writes beside each artifact are cleaned up by
the tool itself: `out/sdi` is 15,397 entries before and after, with 0
`_passband_probe_*.sid` left behind.

---

## `End_94` and `Rectum` build fine — the 1800 s cap was the only thing stopping them, and the medians do NOT move (2026-09-11, task `sdi-two-longest-files-timeout-at-1800s`)

The 2026-09-11 corpus sweep recorded `timeout after 1800s` for exactly two files,
and they are the corpus's two LONGEST decoded songs (`End_94` 120,097 frames,
`Rectum` 120,004 — the `span-desc` schedule runs them first). That made the
exclusion **biased rather than random**: every per-variant median above was over a
corpus missing its two heaviest members.

**Re-run with the cap raised to 7200 s — both BUILD.** No code changed; only
`--timeout`.

| file | variant | voice medians | parts |
|---|---|---|---:|
| `End_94` | B | 100.0 / 99.8 / 99.8 | **1192** |
| `Rectum` | A | 97.9 / 100.0 / 100.0 | 72 |

`built 2 refused 0 errored 0`. So **they are not a structural ceiling** — the only
thing excluding them was a per-file wall-clock limit, and both finish inside 7200 s.
The pair took **60.6 min** together; each necessarily exceeds 1800 s, since both hit
that cap in the full sweep.

### And the answer to the question the bias raised: nothing moves

| variant | without the two | with them |
|---|---|---|
| A | n=120 med 99.9 | n=123 med **99.9** |
| B | n=81 med 99.9 | n=84 med **99.9** |
| C / D / DELTA / E / V | unchanged | unchanged |
| **ALL** | n=834 med **99.70** | n=840 med **99.70** |
| voices below 90 | 63 | **63** |

Six voices enter and **not one figure changes** — not a variant median, not the
corpus median, not the below-90 count. The two largest songs in the corpus score
in line with it.

**That is a real negative result, not a non-finding.** The concern was legitimate:
a biased exclusion CAN move a median, and nothing about "these are the two longest
files" told us which way. It had to be measured. Having been measured, every
per-variant figure recorded at `e044bf1` stands as written, and the 278-built
denominator is the one to quote — now with the two timeouts accounted for rather
than silently absent.

### Two things this leaves behind

- **`End_94` emits 1192 parts**, far the largest in the corpus (next is
  `GT_Groove` at 405). Whether an SF2 of that part count is usable in SF2II at all
  is a separate open question, already on the backlog.
- **The sweep records no per-file wall-clock.** Its JSON carries `n`,
  `onset_agree`, `parts`, `rc`, `refused`, `v_wrapper`, `variant`, `voices` — and
  no duration, so "quote each file's own wall-clock" cannot be satisfied from the
  run. Only the pair's 60.6 min is available. That gap is already a known backlog
  item; it is why a timeout this close to the limit could not be sized in advance.

---

## Passband after the SDI_WF rebuild: 277 of 293, and EIGHT NEW FAILURES that are the builder's (2026-09-11, task `sdi-passband-failures`)

**Every passband figure above this line predates the 2026-09-11 corpus rebuild and
is superseded.** `out/sdi` was rebuilt wholesale at `e044bf1` (278 of 441 built),
so a row scored against a pre-rebuild artifact says nothing about what ships now.
Re-run: `py -3 pyscript/passband_check.py --player sdi -j 4`.

| | before (2026-08-22) | after the rebuild |
|---|---:|---:|
| select the original's passband | 271 of 279 | **277 of 293** |
| unexercised (not counted either way) | 8 | 8 |
| **FAILED** | **0** | **8** |

`277 + 8 + 8 = 293`. **Do not read 271 → 277 as an improvement**: the denominator
grew by 14 at the same time, which is the whole reason the previous section's
"numerator is unchanged at 271" warning existed. The figure that actually moved,
and the one worth acting on, is **FAILED going from 0 to 8**.

### The 8 failures are the BUILDER's, by passband_check's own rule

`Commies` 98.9 · `Curse` 98.7 · `Eastbottom` 98.5 · `Everytime` 98.1 ·
`Funk_Facet` 98.9 · `Painful` 98.9 · `Virtual` 99.0 · `Zoophyte` 98.8

All eight are **marginal** — 98.1–99.0% against a 99.0 `--min` — so none is a
collapsed filter; they are near-misses. But the tool prints *"rebuild these
first; if it survives a rebuild the builder is at fault, not the artifact"*, and
**that rebuild has already happened**: all eight artifacts carry 2026-09-11
mtimes (08:10–08:54), built by the sweep itself. So the escape hatch is spent and
the attribution falls to the builder.

`Funk_Facet` is the sharpest single case, because this page already recorded it at
**100.0%** once the SDI-scoped filter flags were defaulted on. It now reads 98.9%.
One file, same flags, before-and-after a rebuild — that is the cleanest evidence
that the rebuild is what moved these rows.

**What is NOT established, and must not be asserted:** *why*. `SDI_WF` changed
onset detection, which changes note placement, which changes the frames a filter
program is compared over — a plausible route from the rebuild to a passband
near-miss, and no more than plausible. **The settling measurement** is to rebuild
one of the eight with `SDI_WF=0` and re-score it: if it returns above 99.0%, the
onset change is the cause; if it does not, the cause is elsewhere in the rebuild
and the flag is exonerated. That is one file and one re-score, not a corpus pass.
`Virtual` and `Zoophyte` additionally print `<== mode mismatch` with 28/28 and
33/33 mismatching frames, so they may be a second, distinct defect rather than the
same near-miss — check them separately.

### The 8 unexercised ARE a real ceiling, and two of them explain themselves

`Another_Beginning` · `Beginning` · `Beverly_Kraven` · `Holy_Daze` ·
`Invention_1` · `Kururin` · `Lederhosen` · `Short_Deel`

These cannot be improved by building: the original never routes a voice through
the filter and never selects a passband inside the window, so **there is nothing
to reproduce**. The tool's own suggestion to widen `--seconds` would cross a part
boundary, which is the over-run the `.span` guard exists to prevent — widening
MANUFACTURES disagreement rather than revealing filter behaviour. They are
correctly *not counted either way* rather than scored as failures.

Six of the eight carry 2026-09-11 mtimes. The two that do not are the interesting
ones, and both are explained elsewhere on this page rather than being anomalies:

- **`Lederhosen` (2026-08-18)** is one of the **14 WAVE-overflow files** — the
  rebuild *refused* it (`ValueError: WAVE overflow: 264 rows > 256`), so it still
  carries its August artifact. Its passband row and its build refusal are the same
  fact seen from two directions.
- **`Short_Deel` (2026-08-17)** sits at 84.1% onset agreement against an 85% gate,
  and a recorded decision keeps it in the corpus precisely because it is
  *unexercised* rather than failing.

**So the ceiling question splits.** The 8 unexercised are a genuine, measured
ceiling with current inputs and should stop being re-litigated. The 8 failures are
not a ceiling at all — they are a regression the rebuild introduced, and they are
the actionable half.

---

## The 256-row WAVE ceiling is the NATIVE DRIVER's, and the 14 files it blocks are UNBUILT, not unbuildable (2026-09-11, task `sdi-wave-overflow-256-row-ceiling`)

14 of the 441 files in `SID/Gallefoss_Glenn` (`ls SID/Gallefoss_Glenn/*.sid | wc -l`
-> 441) die with `ValueError: WAVE overflow: N rows > 256`, N 257-323. **Diagnosis
only** -- the builder and parser were read-only for this task, and the answer below
implies a change to code nine builders share, so nothing was changed.

### Reproduction, and where the raise actually lives

```
py -3 bin/build_sdi_native_song.py SID/Gallefoss_Glenn/Sugarhill.sid
  part 1/270 (0-80s) ... part 6/270 (132-132s) SDI Stage B: ...
  File "bin/build_sdi_native_song.py", line 411, in build_song   BM.emit_one(...)
  File "bin/build_mon_native_song.py",  line 2662, in emit_one   RN.gen_includes_song(...)
  File "bin/build_romuzak_native_song.py", line 184, in gen_includes_song
ValueError: WAVE overflow: 323 rows > 256
  build refused: discarded 6 staged part(s), disk unchanged
```

The raise is **not in the SDI builder**. `build_sdi_native_song` imports
`build_mon_native_song as BM`, which imports `build_romuzak_native_song as RN`,
and `RN.gen_includes_song` is what lays the wave table -- so this defect is
reached identically by every builder on that chain. Sugarhill reproduces the
worst N in the list (323). All 14 names resolve to real files (checked
individually). Two of the 14 were **re-derived** rather than trusted:
`Sugarhill` -> `323 rows > 256` and `Rough_Boy` -> `265 rows > 256`, both by
running the builder above. The remaining 12 N values are carried from the sweep's
error map, **not** re-measured here — each run costs ~20 minutes of emulated
tracing, so a 14-file re-derivation is a batch job, not an inline check.

### WHOSE CEILING: the native driver's, and it is architectural

**Not the SF2 format.** The table descriptor's row count is a **16-bit** field --
`sidm2/sf2_header_generator.py:121`, `data.extend(struct.pack("<H", self.rows))`.
The format can declare 65535 rows. `docs/reference/SF2_FORMAT_SPEC.md:79` does
list `| Wave | $0B03 | 256 | 128 entries x 2 bytes |`, but that is **Driver 11's**
own fixed block (256 *bytes*, 128 rows) -- a different and smaller number that
says nothing about the native driver's relocated tables, which are declared
`rows=256, columns=2` at `sf2_header_generator.py:391`.

**The native driver, `drivers_src/common/sf2_native_driver.asm`.** The row index
is an 8-bit quantity in four independent places:

| line | code | what it fixes |
|---|---|---|
| 134 | `VWI = $1800 ; per-voice current wave-program row (3)` | 3 bytes = **one byte per voice** -- the running row counter |
| 136 | `VIWAVE = $1806 ; per-voice instrument wave-program start row (3)` | 1 byte per voice |
| 421 | `lda WAVE,y` | the row lives in **Y**, an 8-bit register |
| 424 | `lda WAVE+256,y` | the column stride **256 is a hard-coded assembly constant** |
| 424-425 | `lda WAVE+256,y` / `tay` | the `$7F` jump target is **one byte** |
| ~470 | `ldy ws_row` / `iny` / `tya` / `sta VWI,x` | the advance wraps at 256 |

Row 256 is therefore not addressable, and the byte where row 256 of column 0
would sit **is** row 0 of column 1. Lifting the cap is not a constant bump: it
needs 16-bit indexing inside the per-frame `wave_step` loop, plus wider
`VWI`/`VIWAVE`/`INSTR_WAVE`/jump-target fields.

**The builder only mirrors it.** `sidm2/sf2_caps.py`: `CAP_TBL = 256  # WAVE /
FILTER table rows (each)`. `bin/build_romuzak_driver_full.py:81-86`:
`gen.wave_columns = 2` then `gen.pulse_addr = gen.wave_addr + 2 * 256`. The
generated `drivers_src/romuzak/layout.inc` confirms the geometry arithmetically:
`WAVE = $3800`, `PULSE = $3a00` -- exactly `$200` = 2 columns x 256 rows, with no
slack. So `CAP_TBL` is a faithful restatement of the driver, **not** a packing
choice someone picked.

This is the same shape as the Hubbard precedent and was established the same way
-- `docs/players/HUBBARD.md:308`, "it needs **153** sequences, Driver 11's pointer
table holds **128**" -- the cap is read out of the consuming driver's own table,
and the verdict stays "not fixed / open" rather than "impossible".

### HARD CAP OR PER-PART? Per part -- but splitting is already EXHAUSTED

Each emitted part gets its own wave table, so the 256 is per-part and
`build_song`'s `fits()` probe already tests `nw <= CAP_TBL`
(`bin/build_sdi_native_song.py:371`). Instrumenting that loop read-only
(replicating the bounds walk and comparing the `count_only` probe against the
real layout) gives, for Sugarhill:

```
PROBE floor=1 bounds=270
part  1 win=0-4000    shrunk=0 probe nw=110 fits=True  REAL_wave_rows=110
part  2 win=4000-6100 shrunk=0 probe nw=132 fits=True  REAL_wave_rows=132
part  3 win=6100-6600 shrunk=0 probe nw=159 fits=True  REAL_wave_rows=159
part  4 win=6600-6625 shrunk=2 probe nw= 91 fits=True  REAL_wave_rows= 91
part  5 win=6625-6637 shrunk=3 probe nw= 85 fits=True  REAL_wave_rows= 85
part  6 win=6637-6649 shrunk=3 probe nw= 81 fits=True  REAL_wave_rows= 81
part  7 win=6649-6650 shrunk=6 probe nw=323 fits=False REAL_wave_rows=323
```

Two things settle the question. First, **part 7's window is ONE FRAME** -- it
shrank 6x to the `_floor`, still did not fit, and was emitted anyway via the
documented floor escape ("a window that still will not fit at one row is emitted
as before rather than looping forever", `build_sdi_native_song.py:396-404`). There
is no narrower window, so **no split can fix this**: a per-note wave program's
length is set by the note's `dur_f`, not by the part window. Second, probe and
layout **agree exactly** (323 == 323), so this is *not* the DMC
probe-disagrees-with-layout class (`2bdbb71`) that the floor escape was written
for -- the packer is being told the truth and has nothing left to do with it.

### WHY 323: one instrument spends the entire table on a 3-row loop

Part 7's three instruments need **2 / 65 / 256** rows. One instrument alone fills
the table. Dumping that 256-row program:

```
instr 2: 256 rows
  distinct consecutive runs = 256   (RLE can collapse nothing)
  distinct row values = 8 -> [(9,1),(20,1),(64,1),(64,2),(65,1),(127,254),(128,1),(129,1)]
  first 12 rows: (9,1) (129,1) (65,1) (64,2) (20,1) (128,1) (64,1) (20,1) (128,1) (64,1) (20,1) (128,1)
  last   6 rows: (20,1) (128,1) (64,1) (20,1) (128,1) (127,254)
  body rows 251, exact period of body = 3
```

Rows 4-254 are an **exact period-3 cycle** `($14,1) ($80,1) ($40,1)` -- the
per-frame WFPRG arpeggio this page already names as SDI's signature. The driver's
`$7F` row is a **jump to a row** (`lda WAVE+256,y` / `tay`, line 424), so that
content is expressible in **8 rows**: 4 attack rows, the 3-row cycle, and one
`$7F` jumping back to the cycle start. The builder spends **256** -- a 32x
over-spend -- because `_rle_wave_impl` (`bin/build_mon_native_song.py:1103-1117`)
collapses only *consecutive identical* frames and then appends a single `$7F` that
loops to the **last run**, never to a repeating cycle. Compounding it, the
per-note capture clamp is `min(dur_f, 256)` (`:1133`, and the same clamp at
`:1504`) -- the clamp on ONE note equals the budget for the WHOLE table, so a
single note is allowed to consume all of it. That clamp was raised from
`WAVE_CAP=96` to 256 for MoN reasons, where RLE genuinely compresses; on SDI's
every-frame arpeggios it compresses nothing.

### VERDICT: merely unbuilt

**The 14 are not permanently unbuildable, and their music does not need more than
256 rows.** The ceiling is the driver's and is real, but on the measured file the
overflowing part carries ~8 rows of information in 256 rows. The blocker is the
builder's wave packing, not the driver's table and not the SF2 format.

**Deliberately NOT fixed here.** `_rle_wave_impl` and `_wave_prog_for` live in
`bin/build_mon_native_song.py` and are reached by nine builders through
`RN.gen_includes_song`; a cycle-aware wave RLE would re-pack every corpus that
routes through it. That is a re-plan, not a widening of this task.

### What is NOT established, and the measurement that would settle it

The per-instrument mechanism above is measured on **one** file (Sugarhill, variant
C). `Rough_Boy` is confirmed to overflow (265) but its row breakdown was not
dumped, and the other 12 are taken from the sweep's error map by name.
The settling measurement is cheap and mechanical: for each of the 14, run the
builder, and on the overflowing part dump the per-instrument row counts plus each
long program's exact body period (the two read-only probes used above). If every
one shows a single instrument at or near 256 rows whose body has a short exact
period, then one cycle-aware RLE clears all 14 and the "unbuilt" verdict holds
corpus-wide. If any file instead shows genuinely incompressible content summing
past 256 across several instruments, that file -- and only that file -- is a real
driver-ceiling case and needs the 16-bit-index driver change.
