# SDI — SID Duzz' It (Geir Tjelta & Glenn Rune Gallefoss)

**Status (2026-07-12):** parser + onset/pitch validation across SIX decoded
variants; Stage A (editable Driver 11) shipping via `bin/sdi_to_sf2.py`;
Stage B native = next arc. Corpus: `SID/Gallefoss_Glenn/` (~350 files) +
`SID/Red_kommel_jeroen/` staging.

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
  Plus `$c0-$ef` arp records **redirect the sound** (`ad+1` byte). Timing
  calibrated per file by strict agreement (Kirby 16.5→71.0 from calibration
  alone — the conduct program is still unresolved).
- **V**: instrument **octave nibble** (+12·(oct−1)) + per-note instrument
  in the row's fx byte (`&$E0==0`).
- **C**: the wfprg walk is fully located (wf/arg/start columns) but the
  onset application **regressed Bahbar** 94.3→81.4 while helping the
  Banana_Man class — the walk phase differs per sub-class, so it is GATED
  OFF pending emulation. C stands on seq notes (Bahbar 94.3 strict).

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

- **C walk phase** (Bahbar vs Banana_Man sub-classes) — needs emulation of
  the first walk step's timing vs note-on.
- **E conduct program** (the dual row condition) — per-file calibration
  sidesteps it for validation; Stage B sidesteps it via `measure_onsets`.
- E laggards: glide-heavy files (strict parks in slides), Evil_Within
  (voice-mapping collapses: all 3 voices decode the same track),
  Arabia (row grammar misparse).
- D pocket: `$FF` track-loop under-decode (Space_Suit/Sveitser_Ost/Lame —
  fix queued), Holy_Josh/Max_Mix cause unknown.
- V residual: its own wfprg walk (drum absolutes, detunes), tempo commands.
- Acid_Jazz layout; 38 locate-NONE `play=init+3` files (likely non-SDI
  covers); the `play=init+4` cluster beyond the located E files.
- **Stage B native** via the shared MoN engine (step-grid; note: C-class
  note-on writes `$D404 = $08` TEST bit — mind the gate model).

## Stage A

`bin/sdi_to_sf2.py` → `out/sdi_sf2/`: 1 SDI tick = 1 Driver-11 row, pitch
resolved through the song's own freq table to the PAL semitone grid, AD/SR
from the located instrument tables (A/B; defaults logged for C/D/E/V), ties
re-gate (runtime Driver 11 cannot parse tie bytes — the Sound Monitor
lesson).
