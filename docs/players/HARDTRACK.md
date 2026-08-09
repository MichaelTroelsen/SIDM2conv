# HardTrack Composer — SID → SF2 support

**Status: RE + Stage A.** The module format is decoded, relocation-safe, and
validated against siddump; a **Stage A transpile to an editable Driver 11 SF2**
now exists (`bin/hardtrack_to_sf2.py`). No Stage B (native driver), and nothing
is wired into `DriverSelector` — Stage A is a `bin/` tool, not a default path.

**Format:** HardTrack Composer, a native C64 music editor released **1992** under
Elysium by the Polish sceners **Longhair (Miłosz Ignatowski)** — replay routine —
and **Brush**, who co-coded the tool. CSDb release 74928. HVSC tags it
`HardTrack_Composer`; **1,126 tagged files across only 45 composers** in the
DeepSID dump, a concentrated Polish-scene tool rather than a broadly adopted one.

**Editor:** `bin/hardtrack composer/-HARDTRACK 1.PRG` (22 KB, load `$0801`).
It is **crunched** — the player template and the two default text lines
(`PLAYER 1.0 BY LONGHAIR/ELYSIUM!`, `- MUSIC DONE BY YOU! -`) are visible as
literal runs, but the code around them is packed. To read its live memory map you
must run it and dump RAM (RetroDebugger / VICE); a static scan of the PRG will not
give you table addresses.

**Corpus:** `SID/Shogoon/` (tracked) — 150 files, of which **38 are HardTrack**
(the rest are GoatTracker 78, DMC 23, Music_Assembler 3, and singles). Get the
split with `tools/player-id.exe "SID/Shogoon/*.sid"`; do not assume the directory
is single-player.

**Code:** parser `sidm2/hardtrack_parser.py` · Stage A `bin/hardtrack_to_sf2.py`
· validators `pyscript/hardtrack_validate.py` (parser) and
`pyscript/hardtrack_stagea_validate.py` (Stage A) · loss attribution
`pyscript/hardtrack_attribute.py` · tests
`pyscript/test_hardtrack_parser.py` (28) + `pyscript/test_hardtrack_to_sf2.py` (12).

---

## Module layout

Everything is relative to the module's load address; **`$1000` in 31 of 33 clean
files, but `Timsoft_Intro` loads at `$4000` and `Trance` at `$a000`**, so nothing
may be hardcoded.

```
load+$000  JMP init
load+$003  JMP play
load+$006  volume (init writes $0f)
load+$007  per-voice current note      (runtime)
load+$00a  per-voice orderlist ptr lo  (runtime, from the subtune table)
load+$00d  per-voice orderlist ptr hi  (runtime)
load+$010  per-voice pattern ptr lo/hi (runtime)
load+$016  per-voice orderlist index   (runtime)
load+$019  per-voice pattern index     (runtime)
load+$020  64 bytes of display text (2 x 32 chars)
load+$060  init routine
  ...      player code, including the note frequency tables
  ...      per-voice state block
  ...      subtune speed table (8 bytes)
  ...      instrument block: 13 parallel tables of num_instruments bytes
  ...      wave / pulse / filter program tables
  ...      subtune orderlist pointer tables (6 x 8)
  ...      orderlists, patterns, pattern pointer tables
```

**Two shipped player variants**, differing by 5 bytes inside `init`: play sits at
`init+$78` (16 corpus files) or `init+$7d` (17). A third shape appears once
(`Tribute_to_Laxity`, init at load+$061).

### Why every address must be recovered by signature

The player *code* is fixed-layout, but the editor packs song data of varying size
and **patches the absolute operands** — so the same table lives at `$198b` in
`Love_tune_2`, `$1a35` in `Teekkno` and `$17ab` in `Jazzloor`. The parser matches
byte signatures against the player's own code (`_SIG_INIT`, `_SIG_PATPTR`,
`_SIG_FREQ`, `_SIG_INSTR`, `_SIG_ABSFLAG`) and reads the operands out of the
matched instructions. Adding a constant to the load address works for exactly one
file and then lies.

---

## Data formats

### Orderlist (one per voice per subtune)

A byte stream. Pointers come from six 8-entry tables (lo/hi × 3 voices) indexed by
subtune; `init` does `AND #$07`, so **8 subtunes maximum**.

| Byte | Meaning |
|---|---|
| `$00–$7F` | play this pattern |
| `$80–$FC` | set transpose = `value & $7F`, then the **next** byte is the pattern |
| `$FD n` | jump: set the orderlist index to `n` (the song loop point) |
| `$FE` | halt this voice |
| `$FF` | restart the orderlist from index 0 |

Transpose is applied as `(note + transpose) & $7F`, i.e. **signed mod 128**:
`$F4` → `$74` → −12 semitones (an octave down), `$82` → +2.

### Pattern

A byte stream, **not** a fixed-width row grid. Notes carry an instrument byte;
duration is a separate rest command, so a "row" is one event, not one frame.

| Byte | Meaning |
|---|---|
| `$FF` | end of pattern → fetch the next orderlist entry |
| `$67 n` | rest for `n` rows (this is how note length is expressed) |
| `$63 a` / `$64 a` | slide / portamento, one argument byte |
| `$60` / `$61` / `$62` | tie / gate-off / reset — each still consumes an instrument byte |
| other | **note** (`& $7F`, index into the 96-entry frequency table) followed by an instrument byte |

Instrument byte: `$00` = *keep the current instrument*; **`$6F` = LEGATO**;
otherwise `& $1F` selects one of 32. That is why the editor writes `$80` for
"instrument 0" — a literal `$00` would mean "no change".

**`$6F` is not a synonym for `$00`.** Both keep the current instrument, but `$6F`
additionally sets `$16CB`, which makes the note-on path **skip the instrument
reload** — so the pitch changes while the wave and pulse programs keep running
from where they were, instead of restarting their attack. It carries **24.7% of
all note events** in this corpus (4,353 of 17,628, in all 31 decodable files), so
it is a core feature, not an edge case. Stage A reproduces it with a duplicate
instrument slot (see below).

### Tempo

One global divider, self-modified in the play routine, reloaded from an 8-entry
per-subtune speed table. **A song row lands every `speed+1` frames.** Within a
beat the player uses the counter value as a phase selector: `0` = read a row,
`1` = decrement the note duration, anything else = run the synth programs only.

### Instruments — 13 parallel tables

Field *k* of instrument *n* is at `instrument_base + k*num_instruments + n`.

⚠️ **`num_instruments` is per-file, not a constant 32.** It ranges 3–32 across
this corpus (`If_I_Was_a_Rich_Man` stores 3, `Jazzloor` 9, `Love_tune_2` 32).
The first cut of this parser hardcoded 32 and therefore read every field but the
first from the wrong address on 17 of 33 files — while still returning entirely
plausible-looking bytes. The count is now derived **two independent ways** and
required to agree: `(flag_table − base) / 5` and `(wave_table − base) / 13`. They
agree on 32 of 33 files; `Tribute_to_Laxity` (the odd third variant) does not, and
is flagged via `instrument_count_verified == False` rather than silently trusted.

| # | Role |
|---|---|
| 0 | attack/decay → `$D405` |
| 1 | sustain/release → `$D406` |
| 2 | pulse width: high nibble → `$D403`, low nibble → `$D402` |
| 3 | **pulse-sweep** program start cursor |
| 4 | **waveform/arpeggio** program start cursor |
| 5 | **flags** — bit 7 = program drives frequency absolutely, bit 4 = hard restart, bits 0–1 = mode |
| 8 | low nibble + high nibble ×2 → two synth counters |
| 9 | copied to the per-voice parameter block |
| 10, 11 | synth-program parameters |

Fields 6, 7 and 12 are **not yet identified** and are deliberately left unnamed in
`Instrument.raw` rather than guessed at.

Fields 3 and 4 were **swapped** in the first cut. Note the test that found it: a
plausibility check ("do these bytes look like SID control values?") scored *both*
readings at ~91.6% and so proved nothing. What settled it was reading the
consumers — field 3 feeds the cursor stepping the pulse table, field 4 the one
stepping the waveform table.

### Synth programs

Two `$FF`-terminated step lists per instrument, both with a `$FF <index>` jump:

- **Waveform/arpeggio** — a pair of parallel tables walked by one cursor. The
  first supplies the `$D404` control byte; the second is an arpeggio offset added
  to the current note, *or* the absolute frequency high byte when the
  instrument's bit 7 is set. This is the mechanism behind the "program-driven"
  column in the fidelity table.
- **Pulse sweep** — `[value][frames]` pairs where `value & $FE` is the step
  magnitude and **bit 0 is the direction** (0 = up, 1 = down), applied to
  `$D402/$D403` each frame. A decoder that ignores bit 0 sweeps every instrument
  upward.

The **global filter sweep** is a third, song-level program (`[cutoff][delay]`
with a `$80 <index>` jump) writing `$D416`. Its cursor lives in self-modified
code and **`init` does not reset it**, so a ripped file carries whatever value it
was saved with — confirm on hardware before relying on it.

### Frequency table

Two 96-byte tables (lo, hi) inside the player code. Entry 0 is **C-0** (`$0116`);
the table octave-doubles exactly, which is what
`test_freq_table_doubles_every_octave` pins.

---

## Fidelity

Measured with `py -3 pyscript/hardtrack_validate.py SID/Shogoon/*.sid -t 20`.
A modelled note-on counts as correct when the player's **own** frequency-table
value for that note actually reaches `$D400/$D401` within 8 frames — a byte-exact
register comparison, not a note-name match. (Note names are useless here: the
instruments open with a one-frame attack transient, so siddump's "onset" row
reports something like `E-6` for every note regardless of pitch. Matching on that
column scores a *correct* model at 0%.)

**Two columns, quoted separately and never averaged:**

| | notes | match |
|---|---|---|
| **sequencer-pitch** (instrument field 5 bit 7 clear) | 5,784 | **88.73%** |
| **program-driven** (bit 7 set) | 1,062 | **2.64%** |

The split is not a convenience — it is the measurement. Bit 7 means the
instrument's wave program writes `$D400/$D401` itself, so the sequencer note never
reaches the register and *cannot* match. Pooling the two columns would report the
unimplemented synth engine as a parser error, and the pooled number would move
whenever a tune's drum/melody mix changed.

**8 of 33 files decode at exactly 100.0%**: `Domagareflexow`,
`If_I_Was_a_Rich_Man`, `Love_tune_2`, `Ritual_II_tune_1`, `Sling`,
`Something_to_Eat`, `Tribute_to_Laxity`, and `Zakplus`/`Shogoon-Rave` at ≥99%.

### Evidence that the residual is not drift

Match rate by 100-frame bucket across all files, sequencer-pitch notes only:

```
frames    0- 99  87.48%      frames  500-599  88.91%
frames  100-199  88.28%      frames  600-699  90.15%
frames  200-299  88.10%      frames  700-799  88.27%
frames  300-399  88.54%      frames  800-899  89.31%
frames  400-499  87.68%      frames  900-999  87.06%
```

**Flat.** The orderlist/pattern walk stays locked to the player for 1,000 frames
across 33 files — there is no accumulating desync. The low-scoring files
(`For_Astoria_6` 60.6%, `Jazz_and_Weird_Tekno` 61.5%, `Walk_to_Soul` 63.5%) are
already low in their *first* bucket, so it is a property of those tunes' notes,
not of elapsed time. The residual was also tested against instrument flag bits
0–1 (mode), 4, 5 and 6 — none of them partitions it (mode 0 = 86.96%,
mode 2 = 88.67%), so it is **not** a second override flag. The leading remaining
candidate is the slide/portamento commands `$63`/`$64` plus wave-program pitch
modulation moving the register off the exact table value; that is untested and
stated here as a hypothesis, not a finding.

---

## Refusals — 5 of the 38 corpus files

`HardTrackModule` raises `HardTrackError` rather than decoding something wrong:

| File | Why |
|---|---|
| `Eternal`, `Fruitmania`, `Miecze_Valdgira_2` | 2 player instances in the file |
| `Zone_of_Darkness` | 3 player instances |
| `Commercial_Fake` | PSID init `$2f01` ≠ module entry `$1000` |

These are wrapper/multi-module rips (their PSID init/play do not point at a
module entry). Before the refusal existed the parser happily decoded instance 0
and the simulator ran away, emitting a note on **every frame of every voice** —
2,997 phantom onsets scored against the wrong song. A decoder that cannot tell
which module it is looking at must say so; see PATTERNS.md and the DEENEN
"builder refuses implausible decodes" precedent.

---

## Stage A — editable Driver 11 SF2

```
py -3 bin/hardtrack_to_sf2.py SID/Shogoon/Love_tune_2.sid       # -> out/hardtrack/
py -3 pyscript/hardtrack_stagea_validate.py "SID/Shogoon/*.sid" -t 20
```

### What transfers exactly

- **Notes and timing.** A HardTrack row lands every `speed+1` frames, a Driver 11
  row plays `tempo+1`, so `tempo = speed` and one row maps to one row.
- **The waveform/arpeggio program**, transliterated 1:1. Both formats are a
  2-column table with a jump row, and — crucially — both use the same rule in
  column 1: `$00–$7F` is a relative semitone, `$80+` an absolute note. So the
  whole table is copied with row indices preserved and each instrument keeps its
  own cursor as `wave_idx`; internal jumps stay valid with no remapping.
- **Per-instrument AD/SR and the starting pulse width.**

### What does not (all logged by the builder, never silent)

- **Pulse sweep** — HardTrack sweeps the width every frame; Driver 11's pulse
  table is set-and-hold, so swept leads sound static. Stage B material.
- **Slide/portamento** (`$63`/`$64`) become sustain rows.
- **The global filter sweep** is not ported.
- **Orderlist transpose is materialised, not expressed.** Driver 11 *does* have
  an `$A0+transpose` orderlist command, but the shared emitter writes transpose 0
  unconditionally and changing it would touch a path eight other players depend
  on. A pattern used at two transposes becomes two sequences with pre-transposed
  notes: correct, just more sequences than necessary.
- **The loop point** — `$FD n` loops to orderlist index *n*; a Driver 11
  orderlist only loops to its start, so a song with an intro replays it.

### Fidelity

Same byte-exact frequency-register metric as the parser validator, over
sequencer-pitch notes only, 20 s:

| | notes | match |
|---|---|---|
| **Stage A** (Driver 11 render) | 5,784 | **91.34%** (`--lag 1`: **92.08%**) |
| parser decode (original SID) | 5,784 | 88.73% |

**Stage A scoring *above* the parser is a measurement artifact, not an
improvement — do not read it as one.** Where the original's wave program bends a
note's pitch away from the exact table value, the original *misses* the metric
while Stage A — which does not port that modulation — plays the note plainly and
*hits* it. Stage A wins those notes by being simpler, not better. The comparison
is only meaningful in the losing direction: where Stage A scores **below** the
parser, the transpile genuinely lost something.

By that reading: **6 of the 8 files the parser decodes at 100.0% are Stage A
100.0% too** (`Domagareflexow`, `If_I_Was_a_Rich_Man`, `Love_tune_2`,
`Ritual_II_tune_1`, `Sling`, `Tribute_to_Laxity`). `Something_to_Eat` loses one
note of 454. The real losses are `Zakplus` (99.0 → 87.6) and `Hopscotch`
(72.2 → 56.8).

### The Stage A losses — attributed

Measured over the notes the **parser itself resolves** (5,132), with the known
Driver 11 startup frame corrected, Stage A loses **16 notes — it retains
99.69%**. That is the informative number: the 91.34% / 92.08% figures are diluted
by notes the parser never resolved either, which Stage A cannot be blamed for.

Two rounds of work got there:

**1. `$6F` legato — fixed.** `$6F` had been treated as a synonym for `$00` and
accounted for **58.1% of all Stage A losses** (25 of 43; a 6.8× enrichment over
plain notes). A `$6F` note now selects a **duplicate instrument slot whose
`wave_idx` points at the step the wave program SETTLES on** rather than at its
attack — the `$FF` jump target, or the last real step before `$FE`
(`settled_cursor()`). Driver 11 always restarts a wave program on note-on and
**cannot express a tie at all** (its `$90-$9F` tie durations desync the runtime
driver; `test_no_tie_bytes_emitted` locks them out), so a second instrument is the
only route to "new pitch, no re-attack" through the real driver. The variant
copies AD/SR/flags/pulse verbatim and differs in `wave_idx` alone.
Result: `$6F` losses **25 → 0** (of 864), plain-note losses **unchanged** — that
invariance is the regression check. (An intermediate writeup said "25 → 3"; the
three were `Jazzloor`, `Something_to_Eat` and `Trance` notes at frames 996-997,
removed as boundary artifacts by the next fix. The legato fix is complete.)

**2. A measurement bug — fixed.** Five of the remaining "losses" were notes at
frames 996-997 whose 9-frame match window ran past the end of a 1,000-frame
trace: every frame in the window was missing, so they scored as misses for
reasons unrelated to the conversion. Both validators now drop notes whose window
does not fit, using a `max(lag, 1)` margin so a `--lag 0` and a `--lag 1` run
score the **same** note set and stay comparable.

### The 16 that remain — both groups explained

**11 of the 16 are two instruments failing completely**, and they fail for two
different reasons. Both are cases where Driver 11 simply cannot express what
HardTrack does.

| file | voice | instr | lost | cause |
|---|---|---|---|---|
| `Ritual_II_tune_2` | 2 | 13 | 6 / 6 | program returns to base only past the window |
| `Walk_to_Soul` | 1 | 3 | 5 / 5 | `$62` freezes the wave stepper |

**`Walk_to_Soul` — the `$62` freeze.** `$62` sets `$16D4`, which makes the player
**skip the wave stepper from then on**, so the frequency stops being updated and
holds whatever was last written. Its note 21 is followed by `$62` on the very
next row, freezing the program before it can ramp away — so the base note,
written at note-on, survives. Stage A has no freeze, runs the instrument's full
descending ramp and settles at note+4.

Measured exactly: notes immediately followed by `$62` lose **7.35% (5/68)**
against **0.26% (11/4,200)** for plain notes — a **28× enrichment**, and the 5
are precisely `Walk_to_Soul`'s. `$62` alone is not sufficient (63 of the 68 are
kept) — it costs a note only when the instrument's program would otherwise wander
far from the base pitch.

> **Correction.** An earlier pass reported this explanation as "tested and
> refuted". That verdict was wrong: it came from a tagger that mapped onsets onto
> pattern events with a cursor heuristic, which mis-aligned on this very file.
> Recording the pattern byte-index at note time made the test exact and reversed
> the result. Noted because the wrong verdict was published in the accuracy
> matrix for two commits.

**`Ritual_II_tune_2` — a long ramp.** Here the decode is provably right: an
independent search over every cursor in the wave table found that the
instrument's own field-4 cursor explains the observed output **9 of 9 steps**
(`[79, 58, 58, 54, 54, 51, 51, 44, 44]`). The program does return to the base
note — but only at its very end, around +16 frames, outside the 9-frame window.
The original still scores because it plays the base note at **+0..+2**: HardTrack
writes the bare note frequency at note-on and the wave program overwrites it from
the next frame, whereas Driver 11 applies wave row 0 immediately and never has
that sample.

That note-on write is real, but it is **not on its own a predictor of loss**:
44% of lost notes had an early (d≤2) original hit against 25% of kept notes — an
enrichment, not a separation, since 1,281 kept notes also hit early. It is a
contributing factor, not the mechanism.

The remaining 5 losses are scattered singles (`Altered_States_Tune_2` ×2,
`Love_tune_3` ×2, `For_Astoria_6` ×1) on instruments that otherwise score fine.

**Neither group is fixable in Stage A.** Driver 11 has no equivalent of `$62`'s
stepper freeze, and no way to sound the base pitch before the wave program takes
over. Both are Stage B (native driver) material. 16 notes is 0.31% of the
parser-resolved corpus.

### Where the +1 frame comes from — found

`$16CC` in the shipped Driver 11 template (`G5/examples/Driver 11 Test -
Arpeggio.sf2`) is **`$40`**, and the play routine opens:

```
1006: lda #$00
1008: bit $16cc      ; $40 -> bit 6 set
100b: bmi $1051      ; not taken
100d: bvs $1047      ; TAKEN -> state-init path, clears $16CD..$1740
```

So Driver 11 spends its **first play call initialising its own state** instead of
playing a row, and every render starts one frame behind the original.

It comes from the **template**, not from this builder — the emitted file is
byte-identical to the template across `$16CC-$1702` (15 non-zero bytes, same
values). It therefore applies to **every Driver 11 Stage A build in this repo**,
not just HardTrack. Three other explanations were tested and refuted along the
way: the PSID wrapper's play address (`$1006` is right; forcing `$1003` gives
total silence), the instrument hard-restart flag (`$80`/`$00`/`$40` give
identical offset histograms), and the builder's own row layout.

The shift is **constant, not drift** — median `+1` in every third of the song
(68.6% / 71.5% / 66.8% of notes at exactly +1). A uniform 20 ms offset of the
whole song is **not a fidelity defect**; it only ever broke the measurement.

`pyscript/hardtrack_stagea_validate.py --lag 1` removes exactly that known phase.
Doing so is decisive for the two files previously called losses:

| file | Stage A | `--lag 1` | parser |
|---|---|---|---|
| `Zakplus` | 87.6% | **99.0%** | 99.0% |
| `Hopscotch` | 56.8% | **72.2%** | 72.2% |
| `Love_tune_3` | 93.4% | 93.4% | 99.2% |
| `Walk_to_Soul` | 57.6% | 57.6% | 63.5% |

`Zakplus` and `Hopscotch` land **exactly** on the parser's own score — those two
were never losses, only the phase. `Love_tune_3` (−5.8) and `Walk_to_Soul` (−5.9)
do not move, so **they are the genuine Stage A losses and remain unexplained**.

Corpus-wide the correction is worth **+0.74 pp** (91.34% → 92.08%), because
most notes already land inside an 8-frame window.

### Window sensitivity — quote the window with the number

The match window is not a free parameter, and it has **no plateau**. (Measured
**before** the trace-boundary guard and the `$6F` fix, on the note set of the
time — kept internally consistent rather than half-updated. Both guards shift
every row up slightly; neither changes the shape, which is the point.)

| window (frames) | parser | Stage A |
|---|---|---|
| 4 | 81.06% | 37.05% |
| 6 | 86.62% | 88.52% |
| **8** (reported) | **88.39%** | **90.64%** |
| 9 | 89.22% | 91.50% |
| 12 | 91.98% | 94.85% |
| 24 | 93.17% | 95.79% |

Both figures keep climbing, so no window is "the right one" and widening one to
make a number look better would be laundering. The reported 8 is kept because it
is what the parser was measured at; a fair reading is that Stage A's residual is
**dominated by the known +1 lag**, and allowing exactly that one frame puts it at
91.50%.

Two measurement traps this build walked into, both worth remembering:

1. The Driver 11 note byte is the **semitone index itself**, not `index + 1` as
   the shared IR's own comment suggests. Emitting `index + 1` put every note
   exactly one semitone sharp — audible as a wrong key, and invisible to any
   check that only asks "did a note play?".
2. `pyscript/sf2_to_text_exporter.py` reports "invalid sequence address $0000"
   and prints all three orderlists as sequence 00 for these files. The **emitted
   file is correct** (checked by reading the orderlist bytes back through
   `sf2_parser`); the exporter is what is wrong. Do not debug the builder from
   its output.

---

## Next steps

1. **Resolve the parser residual** — instrument the `$63`/`$64` slide commands and
   confirm (or refute) the hypothesis above before quoting a higher number.
3. **Wave/pulse programs are decoded** (`wave_program()`, `pulse_program()`) but
   not yet *modelled* in `simulate()` — doing so is what would let the fidelity
   score cover the program-driven column at all.
4. **Identify instrument fields 6, 7, 12**, and confirm the global filter
   sweep's un-reset cursor on hardware.
5. **The editor is the strongest lever left** — run `-HARDTRACK 1.PRG` under
   RetroDebugger, build a one-note tune, and diff memory. That resolves the
   remaining fields far faster than more static disassembly.
