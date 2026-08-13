# Maniacs of Noise (Jeroen Tel) — SID → SF2 support

**Composer:** Jeroen Tel (Maniacs of Noise engine, 1987-89 era)
**Corpus:** `SID/Tel_Jeroen/` (179 `.sid` files)
**Registry key:** none yet — the whole pipeline lives in `bin/` (not wired into `DriverSelector.PLAYER_REGISTRY`)
**Status:** native SF2 driver, **100% byte-exact on freq + waveform + pulse + filter, all 3 voices, full song length** for Hawkeye subtunes 2 & 3; every other covered tune measures **98-100% on all four registers** except Supremacy's accepted ~86-92% structural profile. The 2026-07-05 fixes (filter guard + boundary continuation + `$FB` tie decode) collapsed part counts: Supremacy sub0/sub1/sub2 = 5/**1**/**1** parts, Hawkeye sub0 7, Cybernoid 11, Cybernoid II 13, Myth 8 (see *Part-count reduction*). Current headline figures: `docs/reference/ACCURACY_MATRIX.md` (canonical; verified to match this doc 2026-08-09).

Covered tunes so far: **Hawkeye**, **Cybernoid**, **Cybernoid II**, **Myth**, **Supremacy**. The engine RE transfers — one parser (`sidm2/mon_parser.py`) decodes all of them via per-tune orderlist-model variants.

---

## ⚠️ The `$D418` passband fix landed in the builder; the artifacts kept the bug

`464406a` (2026-08-08, *"MoN rebuilt every tune with a low-pass filter, whatever
it selected"*) is where `passband_trace` was written. **131 of the 206 `out/mon`
`.sf2` files, across 16 songs, still predate it.** Checked with
`pyscript/passband_check.py --player mon`, which measures the ARTIFACT rather
than the builder:

**8 of 19 checkable builds select the wrong passband**, five of them at 0.0%
with the filter routed on 100% of frames — `Daring_Dots`, `G_I_Hero`, `Ice_Age`,
`M_A_C_C` and `Myth` all render plain LP where the original selects LP+BP or
LP+HP. `Children_Songs`, `Gaplus` and `Pal_sine_hoener_tune_1` are the
modulating class. `Supremacy` and `Viool_Tello` differ too but route **nothing**
through the filter, so theirs is inaudible and is not counted.

This is the **third** player found this way, after HardTrack (21 of 33 wrong)
and DMC (26 of 57). In each case a session fixed the builder, never regenerated
the output, and the player doc went on quoting the builder. The lesson is not
about the filter: **a fix in a builder is not a fix in the corpus**, and nothing
in this repo measured shipped artifacts until now.

> ⚠️ **Do not blind-rebuild these.** `Myth` is a relocating compilation and needs
> `bin/build_myth_native_song.py`, **not** the generic `build_mon_native_song.py`
> — and `Myth` is one of the eight. MoN songs also carry subtune arguments.
> Coverage is partial for the same reason: only 19 songs expose a
> `_sub0_part01.sf2` for the checker to find.

## The MoN engine (reverse-engineered)

MoN is a two-level **orderlist → pattern** player with a per-frame effects engine:

- **Tempo gate:** the sequencer advances one *tick* every `speed+1` frames (`DEC $9116`, reload from the per-subtune speed byte). Effects (slides, PWM, filter) run **every frame**.
- **Orderlist** (per voice): pattern numbers + parameter bytes — `$80+` = transpose/instrument base (`&$1F`), `$60-$7F` = param, `$40-$5F` = **pattern-repeat counter** (`&$3F`, replay N+1×), `$FE` = **song end** (terminal halt — it rewrites the play entry so later calls RTS), `$FF` = orderlist loop.
- **Pattern bytes** (Hawkeye/Cybernoid dispatch): `$00-$6F` note (+ orderlist transpose), `$70-$7F` wave-program select, `$80-$BF` **sticky duration** (`&$3F` ticks; persists across notes and patterns; a second `$8x-$Bx` adds), `$C0-$DF` instrument prefix (`&$1F` + base), `$E0-$FF` commands (`$Fx` odd = filter value; `$Fx` even = legato note — no re-gate).
- **Instruments:** 8-byte records (Hawkeye `$860C`): PW nibble, waveform/ctrl, AD, SR, effect selector, wave-program pointer, flags.
- **Freq table is SPLIT:** lo bytes and hi bytes are two separate note-indexed tables (Hawkeye `$8337` / `$8396`), *not* interleaved.
- **Filter:** a per-instrument **cutoff envelope** (not a sweep or static table) — a per-voice frame counter reset on note-on indexes a 10-byte threshold/delta table (attack base, 3 signed segment deltas, sustain, 4 thresholds); 4 selectable tables + an unused triangle-LFO mode. Only `$D416` (cutoff hi) is written.
- **Synth engines (Supremacy variant):** pitch arps are compact looping semitone tables (`dur, steps…, $FF loop`), selected by the `$60-$7F` pattern byte and restarted per note; the waveform is a plain attack + steady + release gate envelope (only the steady length varies per note).
- **`$FB` = TIE flag (Supremacy variant):** consumed by the event EPILOGUE ($1335 — note/retrig/slide finalize only, not rests): peek the byte after the event; `$FB` sets `$100A,X`, which (a) suppresses this note's gate-off ($1155) and (b) makes the NEXT note skip the whole instrument/gate restart ($12C5) — a legato pitch change. It consumes NO time. Decoding it as a top-level `$E0+` rest (27 phantom ticks each) desynced Supremacy sub0 V2 from 138.6s.
- **Hard-restart PREAMBLE (Supremacy variant):** EVERY retrigger writes freq `$0000` + wf `$41` for exactly ONE frame before the note proper (base freq + first wave row land the next frame). Trace-verified on all three voices, all instruments. The native driver reproduces it via `NOTE_PREAMBLE` builds: `NPRE,x` set at pr_note; `wave_step`/`fm_step` write `$41`/`$0000` on that frame and FREEZE their state (the preamble is an EXTRA frame — consuming a row there destroys each note's attack row; the uniform 1-frame stream shift is absorbed by alignment). Result: waveform 100% exact, tonal voices 100% exact-freq; only the drum class keeps ~2 boundary frames (its instrument-attack `$FF00` pitch rides one frame late).

### Orderlist-model variants (one parser, `ol_mode` per tune)

| Tune | Load | Model |
|------|------|-------|
| Hawkeye | $7AE0 | `selfmod` — subtune setup self-modifies a 6-byte orderlist-pointer set (fixed high byte) |
| Cybernoid | $AE00 | `selfmod` + a second per-subtune hi-byte table |
| Cybernoid II | $A600 | `stride` — reads the pointer set directly (`LDA olBase,X`, stride 4) |
| Myth | $1D00 | relocating **compilation**: init copies a per-subtune MoN sub-player to $9000/$A400 and runs it there (`play=$0000` self-IRQ wrapper) — parsed via **py65 emulation extraction**, not statically |
| Supremacy | $1000 | `supremacy` — flat compact variant: orderlist ptr table `$16DC`+sub*8+voice*2, notes strictly `<$60`, `$60-$7F` = arp/wave-program selector, additive durations |

All table addresses are located by **relocation-safe code signatures**, never hardcoded.

---

## How MoN is converted

### Stage A — Driver 11 transpile, *editable* (`bin/mon_to_sf2.py`)
Reuses the Galway/ROMUZAK Stage-A IR (`GalwayDriver11Song` + `galway_driver11_emitter`). Notes, order, and timing are **onset-exact** (Hawkeye sub3 28/28, sub2 174/174 vs siddump), instruments carry AD/SR/waveform/PW. Timbre modulation (slides/PWM/filter) is flat — use Stage B for fidelity. Known limit: pitch can sit a note-index calibration off on some tunes (Cybernoid V1 was 2 semitones low) — the native path is pitch-exact.

```
py -3 bin/mon_to_sf2.py SID/Tel_Jeroen/Hawkeye.sid out/Hawkeye.sf2 3
```

### Stage B — native SF2 driver, *byte-exact* (`bin/build_mon_native_song.py`)
The shared trace-driven native pipeline (same engine family as ROMUZAK/Galway; driver source `drivers_src/mon/romuzak_driver.asm`):

- **Per-note (FM, pulse) bundles** via the `$c0-$ff` sequence command channel — each note's command selects an FM slide/arp program + a pulse program captured from the trace. The driver holds base pitch on the trigger frame, so FM programs drop delta[0].
- **Wave programs as instruments** — the gate envelope (`$41→$40` etc.) is a per-note wave program advancing 1 row/frame (RLE'd: col 1 is a frame *count* here, not the base engine's semitone column).
- **Filter** — the cutoff envelope is emitted as SET + ADD rows, restarted per note by a flag-`$40` instrument; drives are detected from note-on-aligned cutoff jumps, restricted to the **$D417-routed voice**, and canonicalized per **(instrument, envelope-shape)** composite key (Myth mixes up/down-ramp shapes across song sections; Hawkeye's shape is fixed per instrument).
- **Myth** goes through `bin/build_myth_native_song.py` — py65 relocate + init + play-per-frame extraction feeding the same `build_native_song` via a MON-compatible shim.

```
MON_ARP_STRUCT=1 py -3 bin/build_mon_native_song.py SID/Tel_Jeroen/Supremacy.sid 2 auto   # auto = adaptive parts
py -3 bin/build_myth_native_song.py 0 auto
```

`MON_ARP_STRUCT=1` enables the **structural path** (looping arp/slide/vibrato FM entries + canonical
wave/pulse programs, each exact- or semitone-guarded per note with trace fallback). It is calibrated
on Supremacy (where it collapses sub1/sub2 to one part each) and is fine for Hawkeye/Cybernoid.
~~**Keep it OFF for Myth**~~ — the measured regression (Myth sub0 part1 osc1 freq 89.1% flag-on
vs 100% flag-off, "the guards admit a wrong substitution on the Myth engine variant") **no longer
reproduces**. Re-measured 2026-07-30 on the identical 20 s window via
`bin/mon_part_fidelity.py out/mon/Myth_sub0_part01.sf2 0 20`, built through Myth's own emulation
shim (`bin/build_myth_native_song.py 0 auto`):

| build | osc1 | osc2 | osc3 |
|---|---|---|---|
| flag-**off** (control) | 100.0 / 100.0 / 100.0 | 100.0 / 100.0 / 100.0 | 100.0 / 100.0 / 100.0 |
| flag-**on** | 100.0 / 100.0 / 100.0 | 100.0 / 100.0 / 100.0 | 100.0 / 100.0 / 100.0 |

…and Myth sub0 drops **8 → 6 parts** flag-on. The intervening guard tightenings fixed it — most
likely the arp guard's `tol` change (the flat `max(4, …)` used to accept *any* arp vacuously on
short notes; see the comment at `build_mon_native_song.py:1472-1476`). Scope of this check: sub0
part01, which is exactly what the original regression named. A full both-ways corpus sweep is
still the prerequisite for making these flags the default.

Load the result via `py -3 pyscript/sf2_open_in_editor.py out/mon/PART.sf2 40` (SF2II's argv-load Heisenbug needs the retry loader). Native play address is `$1003`.

---

## Fidelity status (per tune)

All rows re-measured 2026-07-05 (final sweep) with adaptive (`auto`) windows and all
2026-07-05 fixes in: filter per-drive guard + window residual, boundary-continuation
notes, and the `$FB` tie decode. Structural flag ON except Myth; builds and measurements
strictly sequential — see *lessons*.

| Tune | Subtune | Parts | freq / wf / pulse / filter | Notes |
|------|---------|-------|----------------------------|-------|
| **Hawkeye** | 3 (main theme) | 1 | **100/100/100/100** | byte-exact, full length; GUI-confirmed |
| **Hawkeye** | 2 | 1 | **100/100/100/96.5** | byte-exact; GUI-confirmed |
| **Hawkeye** | 0 (6.4-min theme) | **7** (was 13×30s) | 99.7-100 / 97.8-100 / **100** / 99.1-100 | full 384s; read-watch-verified walk |
| **Cybernoid** | 0 | **11** (was 14) | 98.0-100 / **100** / **100** / 98.3-100 | full 399s; see *SBC bug* below |
| **Cybernoid II** | 0 | **13** (was 20) | 99.5-100 / 99-100 / **100** / 98.5-100 | third orderlist variant |
| **Myth** | 0 (main) | **8** | 98.9-100 / 99.6-100 / **100** / 99.2-100 | emulation-extracted; **flag-off build** |
| **Myth** | 2 | 2 | 100/99-100/100/96 | sub1 is empty (NOP'd in the wrapper) |
| **Supremacy** | 0 | **5** (was 34) | 90-95 / 92.7-99 / 96-100 / **100** | real length ~230s (3846 ticks; $FE halt + $FB ties) |
| **Supremacy** | 1 | **1** (was 24) | 94.4-98 / 93.4-99 / 91.6-98 / **100** | real length 38s ($00 global loop) |
| **Supremacy** | 2 | **1** (was 70) | 93.3-99 / **100** / **100** / **100** | real length 150s; whole song, one editable SF2 |

The 2026-07-06 hard-restart PREAMBLE (see engine notes) dissolved most of Supremacy's
old "structural profile": sub2's waveform + pulse are now 100% EXACT over the full
150s (tonal voices 100% exact-freq); the residual freq gap is the drum class (its
instrument-attack pitch rides one frame late) plus arp-guard-tolerated frames.

### Tel-corpus expansion (2026-07-06) — 15 more tunes build (default subtune, auto)

Corpus survey: `SID/Tel_Jeroen/` = 179 files → MoN/Deenen 72, MoN/FutureComposer 44,
Soundmonitor 39, Rob Hubbard 18, other 6 (player-id.exe). 21 parse with the existing
three orderlist models (the id-groups cut across our models: Supremacy/Myth/Gaplus are
Deenen-tagged yet parse). 2 of those are PSEUDO-parses (Turbo_Outrun,
Thats_the_Way_It_Is_main: garbage speed bytes 255/225 from a mis-located speed table —
now rejected by a frames/tick 1-8 gate instead of "hanging" on a 3280s trace).

| New tune | Parts | min freq/wf/pulse/filter | Class |
|----------|-------|--------------------------|-------|
| Daring_Dots, Pal_sine_hoener_tune_1, Thats_preview, Sample, Viool_Tello, Tomcat | 1-4 | 96.6-100 / 95-100 / 100 / 99-100 | **clean** |
| Hawkeye_Proto_1 | 4 | 100 / 88 / 100 / 99.7 | one wf dip |
| Gaplus | 27 | 87.1 / 100 / 100 / 97.7 | freq quirk |
| M_A_C_C | 7 | 83.3 / 99.8 / 100 / 99.5 | freq quirk |
| Children_Songs / Gaplus_preview / Iets_van_JT | 11/18/10 | 48.7-66.9 freq, wf+pulse ~100 | **freq-quirk class** (unmodeled pitch effect — diagnose like the preamble: boundary dump first) |
| G_I_Hero | 13 | 78 uniform | alignment class |
| Ice_Age | 23 | ~0 | **V0 = 2× V1/V2 ticks** — per-voice loop/overrun, needs this variant's loop semantics |
| Wizzy | 3 | part3 collapses | uneven voices (1024/512/128 ticks) — per-voice `$FF` orderlist LOOP not replayed (one-pass decode; same class as Hawkeye sub2 V1) |

Remaining Tel work = the per-tune quirk classes above + FOUR new engine arcs
(user priority 2026-07-06): **1. Rob Hubbard (18), 2. Soundmonitor (39),
3. MoN/Deenen mainstream (72, Robocop3/Turrican-era)**, plus stray one-offs.

Fidelity is measured with `bin/mon_part_fidelity.py PART SUB SECS OFF0_SECS` (per-frame semitone-freq / waveform / pulse / filter-cutoff, plus `adsr` and the three split filter registers, vs siddump) and `bin/mon_sf2ii_confirm.py` (instrumented real-SF2II capture).

### `$D418` — two defects that hid under "filter 100%" until 2026-08-07

**Read the "filter" percentages above as *cutoff* (`$D415/$D416`) only.** They were
accurate and they were not the whole filter: `$D418` was scored by nothing until
the R17 gate was widened, and it was wrong on three of the eight targets.

- **Passband was never captured.** `filter_program_for` worked from
  `filter_trace`, which returns `(cutoff11, $D417)` — `$D418` was not in it — so
  `_filt_set_row` hardcoded `$90`, i.e. X=1, low-pass, for *every MoN tune ever
  built*. The driver was never at fault: `fp_set` has always decoded a 3-bit
  passband into `F_MODE`; nothing ever handed it anything but low-pass. Measured
  over 20 s: Cybernoid_II wants `$3F` (low+band), Hawkeye alternates `$7F` and
  `$1F`, Cybernoid genuinely is `$1F`, Supremacy uses no passband at all. Fixed
  by `passband_trace` + a per-frame passband threaded into the SET rows; a
  passband *switch* now forces a SET row, since ADD rows only move the cutoff.
- **Master volume was hardcoded** `ora #$0f`. Over 60 s the corpus is
  Hawkeye/Cybernoid/Cybernoid_II 15, **Supremacy sub0 6, sub1 8**, sub2 15 — so
  two subtunes played more than twice as loud as the original. Now a build-time
  constant `MAIN_VOL` in `layout.inc`, taken as the **modal** value because
  siddump's forced row 0 shows the pre-init bus state (all three Supremacy
  subtunes read 3 there) and taking frame 0 would ship the artefact.

| target | `$D418` before | after |
|---|---|---|
| Cybernoid_II | 0.0% | **99.7%** |
| Hawkeye | 82.5% | **99.9%** |
| Supremacy sub0 | 0.0% | **exact** (`$06`, verified by packing back to SID and tracing) |
| Cybernoid | n/a | n/a — its passband is uniformly 1, so the change emits byte-identical rows and *cannot* regress it |

Volume is a per-song **constant** in this corpus, not a ride — a tune that
genuinely rides it will surface as a `volmode` score below 100 rather than as
plausible-looking output.

### Supremacy `adsr` 2.3%/4.5% → 100% — the orderlist instrument base (2026-08-08)

The envelope gap that `$D418` scoring exposed is **closed, and it was a parser
bug, not a driver one.**

`$70-$7F` in a Supremacy orderlist is the **instrument base**, which the parser
skipped as a "modifier — no note effect". The player is explicit:

```
$11F1   CMP #$70 / BCC / AND #$0F / STA $100D,X      ; base = b & $0F
$126D   CLC / ADC $100D,X / AND #$1F / STA $1026,X   ; idx = (select + base) & $1F
        ASL ASL ASL / SEC / SBC $1026,X              ; Y = idx*8 - idx = idx*7
        LDY $1026,X / LDA $1869,Y / STA $104F,X      ; 7-byte record
```

Subtune 0 makes it directly visible because it is a **3-voice canon of one
pattern set**: voice 0's orderlist opens `8C 01 …` (no base) while voices 1 and
2 open `8C **71** …` (base 1). The same `$C1` therefore selects instrument 1
(`41 48 CA`) on voice 0 and instrument **2** (`11 68 CA`) on the other two.
Dropping the base made all three play voice 0's envelope.

The whole residual was **one nibble**: attack 4 vs 6, `$48CA` against `$68CA`,
constant for the entire window. The shape in the report was the tell — a single
contiguous wrong run from each voice's entry (frames 18 and 36, the canon's
6-and-12-tick offsets) to the end, not scattered misses.

| | osc1 | osc2 | osc3 |
|---|---|---|---|
| `adsr` before | n/a | 2.3 | 4.5 |
| `adsr` after | n/a | **100.0** | **100.0** |

`freq`/`wf`/`pulse` are **byte-identical** before and after on part01, and
parts 06 and 09 are unchanged in every column (A/B'd by rebuilding both ways).
Subtunes 1 and 2 also carry base bytes (`$79`, `$7c`, `$7d`, `$7e`) and now
read `adsr` 99.9-100 with their strict freq/pulse residual purely ±1-frame skew
(skew-tolerant 100.0). `ol_mode == "supremacy"` matches **only** Supremacy, so
the blast radius is that one file's three subtunes.

**Why it survived**: the pitch was unaffected, and the wave program overwrites
the waveform byte on the frame after the note-on, so the only column that could
ever have shown it was `$D405/$D406` — which nothing scored until the R17
widening. Same lesson as the hardcoded low-pass below, one register along.
Pinned by `pyscript/test_supremacy_parser.py::test_orderlist_7x_sets_the_instrument_base`
(verified to fail against the pre-fix parser).

**The transferable part is not the fix, it is why it survived.** A hardcoded
low-pass is inaudible in freq/wf/pulse — the only columns the gate scored — so
it shipped for the entire life of the driver and was found within hours of
`$D418` becoming a dimension. See `PATTERNS.md`, *A metric that cannot see a
change*.

---

## The mainstream-Tel "B1-indirect" generation (SID/Tel_Jeroen, 2026-07-18)

`SID/Tel_Jeroen` (179 files, the Robocop3/Turrican-era corpus) is **not** the
Hawkeye/Cyb engine — 125/179 had every table fall out of range under the old
locate. The **B1-indirect bucket** (24 files) is a distinct MoN generation, now
handled in `mon_parser.py` (`ab99032`), gated miss-only so Hawkeye/Cyb are
untouched.

- **`_locate_b1`** (fires only after the B9/BD copy loops miss): olptr via the
  INDIRECT subtune copy `LDY#5; LDA ($zp),Y; STA live,Y`, with `tbl_olptr`/`_hi`
  from the two `BD tab,X; STA $zp(+1)` feeders **anchored backward** from the copy
  loop (a naive file-first `_find` grabs a stray earlier match — verify against the
  disassembly). Split freq tables ~`$60` apart read `TAY; LDA lo,Y; <store>; LDA
  hi,Y` (store `85`/`8D`, not `9D`). Speed = one shared reload byte (`DEC cnt; BPL;
  LDA reload; STA cnt`), read subtune-independent. Requires feeders + freq in-image
  (rejects Hawkeye's stray `A0 05 B1` data run).
- **`_voice_blocks_tel`** (grammar RE'd from the player — orderlist advance `$105F`,
  pattern read `$1093`): ORDERLIST byte bit7 → transpose `&$1F`; byte <`$80` →
  pattern index; `$FF/$FE` end. ROW: length `(ctrl&$1F)+1` ticks; **bit6** →
  gate-off/rest (1 byte, no note); **bit7** → an instrument command byte precedes
  the note; else ctrl+note; note = raw+transpose; `$FF` ends the pattern.

**Status (onset-EXACT via `mon_validate`, 2026-07-18 update — 12/24 EXACT, was 6):**
- **12 EXACT**: the original 6 (05-09-87, Ikari_Union, Lost_in_China, Scout,
  Trying_Out_2_v1, Trying_Out_3) + 5 that turned out to need only the row
  length-mask fix below, not new grammar (Happy_JT, Beginning, Beginning_v2,
  DemoSong, Reggae_Example — see same-day #3) + 1 that needed the column-major
  instrument table fix (Chrome_Met1 — see same-day #4).
- **~2 near-exact (92%/78%)** — Orion_Intro, Trying_Out; single-voice residual,
  not yet diagnosed (didn't get the Alloyrun-style hand-trace this session).
- **Same-day follow-up (3 rounds, all in `_locate_b1_row_variant`, all
  signature-detected so untouched files are provably unaffected)** — 05-09-87/
  Scout/Bantam/etc. share fragments of the same compiled code but never exercise
  these paths in their own song data:
  - **Same-day #1: Alloyrun/Starball.** **orderlist REPEAT** (`$40-$7F`, no bit7): the byte the memory doc flagged as
    "`$43` used as a pattern index → OOR" is not a pattern index at all — it's
    `AND #$40; BEQ; AND #$3F; STA,X reload` (disassembled at Alloyrun `$E127-$E137`,
    **byte-identical in Scout's dispatch**, which stayed EXACT because Scout's data
    never sets bit6). Sets a per-voice counter = `byte&$3F`; the NEXT orderlist
    pattern then replays `(counter+1)` times before the orderlist advances
    (disassembled end-of-pattern check at `$E210-$E22B`).
  - **pattern-index off-by-one** (Alloyrun only): `SEC; SBC #$01` right before the
    `ASL;TAY` table index — this compile's orderlist pattern numbers are 1-based.
  - **CLASSIC row grammar** (Alloyrun + Starball only): these two don't use the
    simple ctrl-byte-length grammar at all — their row dispatch
    (`$E182-$E19A`) is the **same** `$8x`-duration / `$Cx`-instrument /
    `$Ex`-command chain already implemented and Hawkeye/Cybernoid-validated as
    `_pattern()`. Reused verbatim rather than re-derived.
  - **Result**: Alloyrun 1.1%→**61%** (55/90), Starball 1.0%→**76%** (71/93); both
    now have at least one EXACT voice. Zero change to the other 21 bucket files —
    each remaining broken file is its own compiled micro-variant and needs its own
    RE pass, not a shared fix. `Alloyrun_v2` still decodes to 0 events (separate,
    unrelated: the copy-loop/feeder locate itself misses at that file's relocation).
  - **Same-day #2: Bantam's row-ctrl off-by-one.** Bantam's row dispatch is
    structurally identical to Scout's (raw ctrl `AND #$7F` for length, ctrl's bit7
    tests for an instrument-command byte) EXCEPT it does `SEC;SBC#$01` on the ctrl
    byte before BOTH the length mask and the bit7 test (`$80E8-$80F9`) — so its
    instrument-command threshold sits at raw-ctrl≥`$81`, one higher than every
    other compile in the bucket. Detected structurally (`_tel_row_ctrl_off1`: find
    the row-ctrl fetch via the same zp the tbl_pat lookup uses, then check for
    `SEC;SBC#$01` before the first `AND #imm`) so it fires only for files with that
    exact byte sequence. **Bantam 2.7%→73%.**
  - **Same-day #3: the row length mask was never actually `$1F` everywhere.** The
    original grammar RE (05-09-87) read `AND #$1F` for the row-ctrl length field
    and that became the hardcoded Python constant — but disassembling Zynon_Zak
    showed an otherwise byte-identical dispatch masking `AND #$3F` (`$C098`) one
    bit wider. Rather than special-case Zynon_Zak, `_locate_b1_row_variant` now
    reads the **actual mask operand from each file's own code** at the row-ctrl
    site (`_tel_row_len_mask`) and uses it directly — safe by construction: any
    file whose real lengths fit under the old `$1F` decodes identically (the extra
    mask bits are simply unused), so this can only fix files that were silently
    wrapping longer notes, never regress a working one. **5 more files hit
    onset-EXACT this same change**: Happy_JT, Beginning, Beginning_v2, DemoSong,
    Reggae_Example (all real masks were `$3F`/`$7F`, none needed a repeat/off1/
    classic-row quirk — length wrapping was the ENTIRE gap). Plus **Zynon_Zak
    35.6%→84%**, **Orion_Intro 77%→92%**, **Trying_Out 61%→78%**, and Bantam
    ticked up again to **77%** (its `$7F` mask, read for real once `_tel_row_len_mask`
    covers the off1 branch too). **11/24 bucket files are now onset-EXACT** (was
    6). Zero change to Alloyrun/Starball (classic-row grammar bypasses this mask
    entirely) or the untouched broken files (Tel_1, Monitor_Madness_1/2,
    Trying_Out_2, Chrome_Met1 — confirmed unaffected because their own real mask
    already reads `$1F`, matching the old default).
  - **Same-day #4: `_silent_instr` assumed row-major, several compiles are
    column-major.** Investigating Tel_1 (still 24% despite byte-identical
    grammar to 05-09-87) found the SIMPLE grammar's note-append never called
    `_silent_instr` at all (only `_pattern`/`_emit` did), so the "instrument 0 =
    rest slot" convention was silently skipped for every B1-tel file using the
    simple row grammar — added the same check there. Separately, `_silent_instr`
    itself assumed Hawkeye's ROW-MAJOR 8-byte-record layout (`tbl_instr + i*8`);
    disassembling Tel_1 showed a COLUMN-major layout instead — five SEPARATE
    same-length parallel arrays (pulse-lo/hi, waveform, AD, SR), each indexed
    DIRECTLY by instrument number (`field_base + i`, no `*8`), confirmed by
    checking instrument 0 reads all-zero across all five real arrays but garbage
    under the row-major guess. New `_locate_tel_instr_fields` locates the real
    waveform/AD/SR array bases (anchored near the already-trusted AD site, not a
    blind file-first search — two false positives caught mid-session, Orion_Intro
    and Chrome_Met1, where an unrelated nearby `STA $D404` briefly regressed both;
    fixed by REQUIRING the three fields be evenly spaced, `ad-wf == sr-ad`, the
    signature every genuine match showed). Full resweep after the fix: **zero
    regressions, plus a bonus — Chrome_Met1 jumped straight to onset-EXACT**
    (1.5%→100%, it was column-major too and had nothing else wrong). Tel_1 itself
    only partially improved (its instrument-0 padding now correctly suppressed)
    but has a SEPARATE, undiagnosed timing bug past that — not the same file the
    fix was ultimately most valuable for. **12/24 bucket files now onset-EXACT.**
  - **Residual on Alloyrun V1**: raw-byte reconstruction confirms the decode is
    correct (dur=10 note=D#2 matches the pattern bytes exactly) but siddump shows an
    EXTRA onset at tick+1 with the same pitch — an instrument-driven gate blip the
    pattern never encodes, i.e. the **same Stage-B category as the middle tier**,
    not a further grammar gap. See `memory/mainstream-mon-tel.md`.
  - **Same-day #5 (new session): the row's OWN bit5 is a TIE flag, not noise.**
    Tel_1's remaining bug (24%, "extra ~2-tick gap" per the prior handoff) was
    diagnosed via a raw zig64/vsid register trace (`osc1_control` writes), not
    static byte guessing alone: a fast descending run alternated real onsets with
    siddump-BRACKETED (legato) notes every other row, even though every row's
    ctrl/note decode was already correct. Disassembling the "sustain tick"
    handler ($114A-$1166, runs every frame a note is still counting down) found
    `LDA $170E,X (the row's own stored ctrl byte); AND #$20; BNE skip-gate-off`
    — bit5 SET on a row means "don't release the gate at my own last tick",
    which leaves the SID gate held high into the next row, so that row's fresh
    waveform write (same gate value, no falling edge) does NOT retrigger the
    envelope on real hardware even though the pattern data changed to a genuinely
    new note. Implemented as `_tel_row_tie` (`sidm2/mon_parser.py`): detected via
    the `BD ?? ?? 29 20 D0` signature, gated to `row_mask == 0x1F` (files whose
    length mask is wider already consume bit5 as part of the length field, so it
    can't double as a tie flag there — checked empirically too: every
    already-EXACT file carrying this signature never sets bit5 in its own song
    data, so enabling it is a no-op for them). **Tel_1 24%→86%** (122/142); one
    genuine residual remains starting frame464, hand-traced via the SAME register
    trace to a DIFFERENT mechanism — an instrument wave-program/arpeggio effect
    that does its own independent mid-note gate cycling (confirmed: gate toggles
    off only 1 frame after the onset, far too early to be the end-of-note
    mechanism) — real Stage-B territory (unmodelled wave-program engine), not a
    further row-grammar bug. Full 23-file resweep + the 5-check byte-exact gate:
    zero regressions. Monitor_Madness_1/2 and Trying_Out_2 also carry this same
    signature but stayed at ~0-2% — they have a different, more fundamental bug
    the tie fix doesn't reach (see `memory/mainstream-mon-tel.md`).
  - **Same-day #6: `bin/mon_validate.py` itself was miscalibrating these 3
    files, not just the decoder.** Investigating Monitor_Madness_1's near-zero
    score found a raw zig64 register trace (`osc1_control`) showing its INIT
    routine (a raster-IRQ-based init, unlike the simpler call/return init in
    the 12 already-EXACT files) primes a voice's waveform register at frame 0
    with the gate bit already set — `format_voice_column`'s `is_first_frame`
    branch (`pyscript/siddump_complete.py`) unconditionally shows a note for
    ANY wave≥0x10 on the very first displayed row, so that priming write reads
    as a spurious onset a frame or more before the real one. The validator's
    old calibration (median of index-0 deltas across voices) let 2-of-3
    corrupted voices outvote the correct one. Rewrote the calibration as a
    joint brute-force search over a small offset range AND, per voice, whether
    to drop a leading onset (`_artifact_variant`, gated to an exact
    `len(siddump)==len(parser)+1` count match at frame 0) — picking whichever
    combination maximizes total matched onsets, never applied unconditionally.
    **First attempt regressed Cybernoid sub1 V2** (15/15→10/15): its count
    mismatch was a genuine TRAILING wraparound onset, not a frame-0 artifact,
    and unconditional dropping silently broke an already-perfect voice — fixed
    by making the drop a candidate the search evaluates (tie-break: fewer
    drops wins), so a wrong guess can only lose a tie, never regress a working
    voice. **Monitor_Madness_1 2%→75%** (75/106, V1 now EXACT), **Monitor_
    Madness_2 3/146→90/146**, **Trying_Out_2 1/59→41/59** — the latter two hit
    a locally-good but not fully optimal offset (their per-voice count
    mismatches don't reduce to the same clean pattern); full further fix is
    open. Full 23-file resweep + the 5-check byte-exact gate (re-run after the
    Cybernoid regression was caught) + full pytest suite: zero regressions
    everywhere else.

## Cybernoid_II "synthesis divergence" — FALSIFIED 2026-08-08

The registers x audio cross-tab reported Cybernoid_II as register-exact on all
three voices yet only 71-85% onset-matched, and called it SYNTHESIS on every
voice. It is not a driver defect; it is the metric.

**What the registers actually say.** A full siddump diff over 350 frames gives
**6 differing lines total**, all in frames 0-2, all one thing: the driver's
`$D418` filter-mode write lags the original by exactly one frame
(`Off -> Low -> L+B` against `Low -> L+B -> ...`). That single lag is the
entire content of the `$D418` 99.7%. Everything else is byte-identical.

**What the audio gap actually is.** Two things, neither attributable to the
build:

- *Metric noise.* Two `--delay=0` renders of one file are the same signal to
  within `r = 1.0000` and `rms(diff)/rms ~ 0.001`. The full mix does not care
  (38/38 onsets, 100% across all six pairings). A **voice-isolated** render
  does: onset counts 101/88/98 and pairwise match rates 84.2-96.9%, because
  muting two voices leaves a large population of onsets on the detector
  threshold.
- *Phase.* Perturbing the power-on delay on the ORIGINAL ALONE, note data
  untouched, walks the score across the same band. The original and the build
  reach their first play call through different init code (`$a600` vs `$1000`),
  so their oscillators and noise LFSR are at different free-running phases.

`audio_tightness_tool` now measures both per voice (`--repeat-floor`, default 9:
one plain replicate plus 8 phase perturbations) and returns **INCONCLUSIVE**
inside the floor. All three Cybernoid_II voices land there, reproducibly across
runs. See PATTERNS.md **F5b**.

**The one real defect it turned up — fixed 2026-08-08.** `do_play` wrote the
`$D418` volume/mode byte at its TOP, before `filt_prog_step` had run, so it
published the PREVIOUS frame's `F_MODE`. The cutoff never had this bug because
`fp_apply` stores `$D415/$D416` itself — which is exactly why the lag surfaced
on `$D418` alone. The driver now writes it after the multispeed loop, for the
same reason the code already gives at `dp_vib` for running `filt_prog_step`
after `do_row`. `digi_stream` still runs last, so the digi keeps the final word.

Cybernoid_II `$D418` goes 99.7% → **0 of 350 differing frames**. Hawkeye
sub0/sub2/sub3, Cybernoid sub0 and Supremacy sub0 are unchanged; Cybernoid
osc3 freq 95.0 was A/B-confirmed against a pre-change rebuild as pre-existing.
Note that `mon_part_fidelity`'s window excludes the opening frames, so it now
reports this register as `n/a` (constant and identical) rather than 100% — the
defect lived precisely where that harness does not look, which is why it was
only ever visible as the 0.3%.

**Not fixed**: `drivers_src/common/sf2_native_driver.asm:369` (the shared
engine behind ROMUZAK and Galway) has the identical ordering — `sta SID_VOL`
before `jsr filt_prog_step` at :382 — and still hardcodes `ora #$0f` where
MoN's copy takes `MAIN_VOL`. Extending the fix there means rebuilding and
revalidating both corpora.

## Hard-won lessons (encoded in code/tests — do not re-learn)

- **The siddump SBC carry bug (2026-06-30).** Cybernoid's lead sounded wrong "when vibrating" although every register was byte-exact — the *capture* CPU (`sidm2/cpu6502_emulator.py`) had SBC carry stuck set, breaking 16-bit subtraction chains, so siddump computed a too-wide vibrato and the native build faithfully replayed the error. Fix: carry = `temp >= 0`; guarded by `pyscript/test_cpu6502_sbc.py`. Lesson: when trace-replay sounds wrong but the metric says byte-exact, **suspect the capture CPU** — cross-check py65 and VICE.
- **Trace-replay has a cycle-level floor.** A byte-exact per-frame register replay still measures ~0.168 VICE spectral distance vs the original on a high-resonance filtered voice (the resonant filter responds to exact write cycles). Write *order/schedule* reproduction was tested and does **not** close it. The native driver sits ~at this floor (0.189); no procedural port is warranted for this.
- **MoN is single-speed.** The "multispeed" reading was a measurement artifact (three voices' freq writes misattributed to one voice).
- **`$FE` is song end, not pattern-skip** — it halts the whole player; short subtunes must be compared only over the real song length (post-end silence skews percentages).
- **Filter resets must come from note-on-aligned drives**, never a trace-only cutoff-jump threshold (over-detects on normal sweeps and shatters spans).
- **SF2II CMP-carry:** any native-driver dispatch on values >$7F apart must bit-test (`bmi`/`and`), not `cmp` (SF2II's bundled 6510 computes CMP carry from bit7 of A−op).
- **Never run two MoN builds concurrently** — every build regenerates the shared scratch `drivers_src/mon/layout.inc` + `freqtable.inc` (and `drivers_src/romuzak/layout.inc`), so parallel builds assemble each other's tables into garbage SF2s (near-zero fidelity on random parts). Fidelity *measurements* are safe to parallelize since `mon_part_fidelity` derives a unique probe filename per part (2026-07-05; it previously shared one probe and raced too — corrupted-probe signature: freq ~0%, pulse 1-5%, wf 25-45%).
- **Don't trust SID-output "loop detected" probes alone** — Hawkeye sub0's output at 294s matches 120s for >10s because the orderlist *repeats the same entry transposed*, not because the song loops. A py65 **orderlist read-watch** (log reads of the orderlist bytes per frame) settles the real walk; it confirmed the player walks all 110 entries in 4800 ticks, exactly the parser model.
- **Uniform freq=wf=pulse percentages = misalignment, freq-only loss = decode/FM.** Two boundary classes fixed 2026-07-05 in `build_mon_native_song`: (1) notes gated ACROSS a window start were dropped (onset outside window) — a 6s window lost 44% of a voice; now re-entered at t0 as a capture-from-t0 continuation. (2) filter drives are per-note exactness-guarded + each window gets a synthetic residual-envelope restart on its first note — filter went from 30-90% to 98-100% corpus-wide.
- **Instrument 0 is the REST/silent slot (2026-07-18).** Its 8-byte record is all-zero across Hawkeye/Cybernoid/Cybernoid_II/Double_Dragon; a zero SID voice makes no sound, so siddump shows NO onset for it. `_emit` was counting instr-0 events as note onsets — false onsets that, under the validator's monotonic alignment, BLOCK real matches. Fix: `_silent_instr` → `retrig=False` (event kept, timing untouched, SF2 renders it via the same silent instrument). Numerator *rises*: **Cybernoid sub0 41/54→53/53, Double_Dragon sub0 99/123→109/109, Zynon sub0/1/2 →26/115/45 all exact** (Double_Dragon + Zynon were the "partial/rejected" MoN/FC files in the Deenen corpus). Zero regression to the byte-exact Hawkeye/Cyb subtunes. See [DEENEN.md](DEENEN.md).

---

## Part-count reduction — the structural path (EXECUTED 2026-07-05 for Supremacy)

Dense tunes blow three SF2II hard caps **simultaneously** (per SF2 file: 63 command bundles, 32 instruments, 256 wave rows) because the trace-driven build captures **per note**, unrolling the player's compact looping synth tables. The structural rebuild (`MON_ARP_STRUCT=1`) re-compresses them:

- **Swing tempo** (speed byte bit7 — tick periods alternate speed, speed+1), tick-exact frame accumulation, onset_delay=2, prefix-chain retriggers, additive durations, top-level rests, `$FD` 4-byte slides — all py65-tracer-proven (`bin/mon_event_trace.py` = the decode ground truth).
- **Structural FM entries** in the driver: looping semitone arps, slides (rate `7<<(speed-1)` Hz/frame, target-clamped), scaled pitch-proportional vibrato (per-program rounding), each substitution exact- or semitone-guarded per note with trace fallback.
- **Canonical wave/pulse programs** per (instr, wprog) from the longest note, gate-split, with exact unrolled guards.
- **Global song markers**: orderlist `$00` = global loop, `$FE` = global halt (Supremacy branch only — the Hawkeye-family walk was read-watch-verified to match the parser one-pass model; it needs no global cut).

Result: Supremacy sub1 70→**1 part**, sub2 24→**1 part**, sub0 34→**10 parts** (the real lengths emerged from the global markers: 38s / 150s / 234s). Adaptive window packing (`auto`) also collapsed Hawkeye sub0 13→7, Cybernoid 14→10, Myth →7 parts.

**Re-measured 2026-07-30** (R17 flagship check) with all three prongs on
(`MON_ARP_STRUCT=1 MON_PULSE_CANON=1 MON_WAVE_CANON=1`), each compared against the
unrolled build on the **same window** via `bin/mon_part_fidelity.py <part.sf2> <sub> <secs>`:

| file | parts off → on | fidelity, same window | note |
|---|---|---|---|
| Supremacy sub2 | **10 → 1** | identical (94.0/100/100, 100/100/100, 100/100/100, filter 100) | bundles 60→**18**, instr 16→12 |
| Hawkeye sub2 | 1 → 1 | **identical 100.0 on every register** | bundles 59→49, instr 21→17 |
| Cybernoid sub0 | **13 → 11** | identical (99.9/98.9/97.9, filter 100) | part01 38s→48s, bundles 55→**63** = exactly on the cap |

24 parts → 13 with **zero** fidelity change. Note sub2's *baseline* is now 10, not the 24 above —
unrelated fixes moved it. Cybernoid shows the prongs buy headroom the adaptive planner then
spends, so a part-count win is not automatic. Myth sub0 is **not buildable via this CLI** — the
pseudo-parse gate refuses it (`speed byte 255`); it needs the py65 emulation shim.

⚠️ Still opt-in for the reason in *Remaining frontier* #2 below: **flag-on regresses Myth**.
Per-variant guard calibration + a full both-ways corpus sweep are the prerequisites for making
these the default; three files are not a corpus.

Remaining frontier:

1. **Filter window seams** — filter cutoff is the one register still 30-90% on multi-part tunes (restarts at window boundaries); whole-song parts measure filter 100%.
2. **Structural path beyond Supremacy** — ~~flag-on regresses Myth (osc1 89%)~~ **retested 2026-07-30: it does not.** Myth sub0 part1 is 100.0/100.0/100.0 both ways on the same window, and 8→6 parts flag-on. With Supremacy (10→1), Hawkeye sub2 (100.0 preserved) and Cybernoid (13→11) also clean, **no known regression remains** — the outstanding work is a full both-ways corpus sweep, then flipping the default. Two loose guards are worth auditing while doing it: the arp acceptance is semitone-with-tolerance (`:1471-1477`) and the **slide substitution at `:1480-1483` has no exactness guard at all**, unlike the vibrato/canonical paths beside it.
3. **Registry wiring** (roadmap A4) — the whole pipeline still lives in `bin/`.

---

## Key files

| File | Role |
|------|------|
| `sidm2/mon_parser.py` | MoN decoder (orderlists, patterns, instruments, arp programs; `ol_mode` variants) |
| `bin/build_mon_native_song.py` | shared Stage-B native build (bundles, wave/pulse/filter programs, clustering, part windowing) |
| `bin/build_myth_native_song.py` | Myth emulation-extraction shim → same native build |
| `bin/mon_to_sf2.py` | Stage-A Driver-11 transpile |
| `drivers_src/mon/romuzak_driver.asm` | native driver (ROMUZAK/Galway engine copy + MoN wave-RLE `wave_step`) |
| `bin/mon_part_fidelity.py`, `bin/mon_fidelity.py`, `bin/mon_validate.py`, `bin/mon_sf2ii_confirm.py` | fidelity/validation tools |
| `pyscript/test_mon_parser.py`, `test_mon_to_sf2.py`, `test_mon_filter.py`, `test_supremacy_parser.py`, `test_cpu6502_sbc.py` | tests |

Deep memory references: `memory/hawkeye-mon-player-re.md`, `myth-supremacy-mon-re.md`, `cybernoid-mon-orderlist-re.md`, `hawkeye-mon-filter-engine-re.md`.
