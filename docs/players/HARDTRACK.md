# HardTrack Composer — SID → SF2 support

**Status: RE + Stage A + Stage B.** The module format is decoded,
relocation-safe, and validated against siddump; a **Stage A transpile to an
editable Driver 11 SF2** exists (`bin/hardtrack_to_sf2.py`), and a **Stage B
native build** (`bin/build_hardtrack_native_song.py`) replays the synth engine
from a per-frame capture instead of modelling it. Nothing is wired into
`DriverSelector` — both are `bin/` tools, not a default path.

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

**Code:** parser `sidm2/hardtrack_parser.py` · synth engine
`sidm2/hardtrack_synth.py` · Stage A `bin/hardtrack_to_sf2.py`
· validators `pyscript/hardtrack_validate.py` (parser, onset),
`pyscript/hardtrack_synth_validate.py` (registers, per-frame) and
`pyscript/hardtrack_stagea_validate.py` (Stage A) · loss attribution
`pyscript/hardtrack_attribute.py` · tests
`pyscript/test_hardtrack_parser.py` (28) + `pyscript/test_hardtrack_to_sf2.py` (12)
+ `pyscript/test_hardtrack_synth.py` (22).

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
| `$63 a` / `$64 a` | slide **up** / slide **down** by `a` per frame, one argument byte. Not a portamento — there is no target pitch; the ramp ends only at the next note-on on that voice (33/33) |
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
| 5 | **flags** — bit 7 = program drives frequency absolutely, bit 4 = *on a repeated note, skip the filter re-arm* (**not** a hard restart — it reaches nothing else; the parser property was renamed `hard_restart` → `skip_filter_rearm` in v3.25.0), bits 0–1 = mode. Bits 2, 5, 6 are never read: the player masks field 5 with only `$03`/`$10`/`$80`, in 33/33 |
| 6 | filter program start cursor (self-modified into `$158f`) |
| 7 | **initial filter cutoff** (self-modified into `$15b2`, the base the program's per-frame delta accumulates onto → `$D416`). Not the resonance — that is field 12's high nibble |
| 8 | **vibrato**: low nibble = frames per direction, high nibble ×2 = onset delay |
| 9 | **vibrato depth** (added to / subtracted from the frequency low byte) |
| 10 | vibrato depth **increment** per half-cycle |
| 11 | vibrato depth **limit** — once reached, the depth stops growing |
| 12 | **filter setup**: high nibble = **resonance** → `$D417` bits 7–4, low nibble ×16 = mode → `$D418` bits 7–4, and a non-zero value also sets this voice's `$D417` enable bit. `$00` = this instrument is not routed through the filter at all |

Fields 6, 7 and 12 were unidentified for the whole of the decode arc and are now
read off their consumers at `$13b3`, `$13b9` and `$138f`: all three are the
**filter**, which is why nothing that measured `$D400`–`$D404` could see them.
Fields 8–11 are the vibrato engine (`$14df`–`$1530`), not generic "synth
parameters" — the depth *ramps* toward field 11 in steps of field 10, which is
what gives HardTrack's vibrato its delayed swell.

Fields 3 and 4 were **swapped** in the first cut. Note the test that found it: a
plausibility check ("do these bytes look like SID control values?") scored *both*
readings at ~91.6% and so proved nothing. What settled it was reading the
consumers — field 3 feeds the cursor stepping the pulse table, field 4 the one
stepping the waveform table.

### Synth programs

Two `$FF`-terminated step lists per instrument, both with a `$FF <index>` jump:

- **Waveform/arpeggio** — a pair of parallel tables walked by one cursor, one
  step per frame. The first supplies the `$D404` control byte; `$FF` jumps (the
  target is in the second column) and **`$FE` stops the stepper**. The second
  column has three readings and the branch order at `$1474`–`$1497` decides
  which: with the instrument's bit 7 set it is written **straight into `$D401`**
  with `$D400` cleared (the "program-driven" column); otherwise `$80+` is an
  **absolute note index** (`& $7F`) and anything below is a **relative semitone**
  added to the sounding note. Masking that column with `$7F` destroys the
  absolute encoding.
- **Pulse sweep** — `[value][frames]` pairs where `value & $FE` is the step
  magnitude and **bit 0 is the direction** (0 = up, 1 = down), applied to
  `$D402/$D403` each frame. A decoder that ignores bit 0 sweeps every instrument
  upward.

⚠️ **A running waveform program suppresses vibrato and slides entirely.** The
stepper at `$1454` ends in `JMP $1553` — straight to the register write, jumping
over the slide/vibrato block at `$14a5`. So `$63`/`$64` and the field-8–11
vibrato only reach the frequency once the wave program has stopped itself with
`$FE` or been frozen by the pattern's `$62`. This is a property of the player,
and it is why the wave program's arpeggio offset — not the sequencer note — is
what the frequency register actually shows for most of a note's life.

### The filter sweep — global, and modelled

A third program (`[delta][delay]` pairs with a `$80 <index>` jump) writing
`$D416`. It is **global, not per-voice**, and that is structural rather than
incidental: the engine sits *past* the `dex / bmi` at `$1583` that ends the
voice loop, so it runs **once per frame after all three voices**. Its cursor,
cutoff accumulator, delta and `$D418` mode nibble all live in **self-modified
operands**, which is why an operand scan for a table address never named them —
the addresses being written are inside the code.

Instrument fields 6, 7 and 12 only *seed* it, at note-on (`$137d`): f6 the
program cursor, f7 the initial cutoff, f12 `(resonance << 4) | mode`. `init`
resets none of it, so a ripped file starts from whatever the editor saved —
and that matters: `Love_tune_2` opens on cutoff `$1a` stepping `$40` a frame,
and siddump's very first row reads `$5a`, which is reachable only from the
saved pair.

Three details are easy to get wrong, and each was checked by breaking it on
purpose and watching the corpus score fall (see *Negative controls* below):

- **The accumulator is 8-bit and wraps.** `CLC / ADC` with no clamp:
  `Love_tune_2` runs `$1a → $5a → $9a → $da → $1a`, audibly a sawtooth.
  Clamping instead scores **24.75%**.
- **`f12 == 0` does not skip the re-arm — it CLEARS this voice's routing bit**
  (`$13cb`, `AND $16da,x`). An instrument with no filter actively switches its
  voice *out*. Reading it as a no-op scores `$D417` at **48.28%**.
- **`$D415` is never written**, in none of the 33 decodable modules, so the
  cutoff is the 8-bit `$D416` alone.

The un-reset cursor is therefore **no longer an open hardware question** — it is
modelled, and the model is byte-exact against the real playroutine.

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

→ **That hypothesis is now confirmed** — see the next section. Modelling the
wave program removes essentially the whole residual, and the mechanism is the
one guessed at here: the arpeggio column, not the sequencer note, is what the
frequency register holds for most of a note's life.

---

## Register-level fidelity — the synth engine modelled

`py -3 pyscript/hardtrack_synth_validate.py "SID/Shogoon/*.sid" -t 20`

The onset measurement above asks "did the sequencer's note reach `$D400/$D401`
within 8 frames". `sidm2/hardtrack_synth.py` asks the question one level down:
**predict the SID register file every frame and compare it byte for byte**. That
removes both weaknesses at once — there is no settle window to quote, and the
program-driven instruments are scored on what they actually write instead of on
a sequencer pitch that never gets there.

`simulate_registers()` is a transcription of the play routine, not a model of
it: the three-frame note-on pipeline, the waveform/arpeggio stepper, the
pulse-width sweep, the vibrato engine, `$63`/`$64` and the `$62` freeze. Every
branch is annotated with the address it came from so it can be diffed against a
disassembly. The filter is modelled too, as of v3.25.0 — see below; it is
scored over frames rather than voice-frames, because there is one of it.

**20 s, all 33 decodable files, 97,806 voice-frames:**

| | frames | byte-exact |
|---|---|---|
| **frequency** `$D400/$D401` — layout-seeded files (18) | 53,569 | **100.00%** |
| &nbsp;&nbsp;• sequencer-pitch instruments | 47,440 | **99.97%** |
| &nbsp;&nbsp;• **program-driven** instruments (bit 7) | 6,129 | **100.00%** |
| **waveform** `$D404` — seeded | 53,569 | **100.00%** |
| **pulse width** `$D402/$D403` — seeded | 53,569 | **100.00%** |
| frequency — second-build files (15) | 44,237 | 99.96% |
| waveform — second build | 44,237 | **100.00%** |

**16 of the 18 seeded files are exactly 100.0% on all three registers.** The
program-driven column moved from **2.64% to 100.00%** — it was never a fidelity
figure, it was the score for predicting the wrong thing.

### The filter registers (v3.25.0)

Scored over **frames**, not voice-frames, because the engine is global. Same
20 s window, same 33 files:

| | frames | byte-exact | files scoring n/a |
|---|---|---|---|
| **cutoff** `$D416` | 32,967 | **100.00%** | 0 |
| **resonance + routing** `$D417` | 32,967 | **100.00%** | 0 |
| **mode + volume** `$D418` (bits 0–6) | 9,990 | **100.00%** | **23 of 33** |

Three things this table is saying, none of which is "the filter is 100%":

- **`$D418` is only exercised by 10 of the 33 files.** The other 23 hold one
  constant on both sides for the whole window, so `exercised()` withholds them
  rather than letting `0 == 0` report a confident 100%. Quote the file count
  beside that column or it reads as three times the evidence it is.
  `docs/players/HUBBARD.md` had to retract a published "filter 100%" for
  exactly this shape.
- **`$D415` is excluded because it does not exist here**, not because it was
  hard. Zero stores corpus-wide; siddump's `FCut` is `(D415 & 7) | (D416 << 3)`
  so `>> 3` recovers `$D416` exactly.
- **`$D418` bit 7 is not visible to siddump**, which prints only
  `(D418 >> 4) & 7`. f12 low nibbles of `9` and `14` do set it (voice 3 off), so
  that one bit is modelled but unverified. The comparison masks to bits 0–6.

The filter scores 100% on the **unseeded** build too, which the frequency
column does not. That is not luck: the filter's state lives in self-modified
code operands recovered by signature, not in the per-voice variable block, so
the second player build's different allocation never touches it.

### The second build has a bug, and the model reproduces it

Chasing `Shogoon-Rave` — the worst second-build file at 96.5% — found a defect
in the **player**, not the model. Its `$62` (CMD_RESET) handler:

```
112F  LDA #$00
1131  STA $165a,x     ; waveform := 0
1134  LDY $16a0,x     ; Y := this voice's SID slot ...
1137  9D 06 D4        ; STA $D406,X   <-- ... and then never uses it
```

`$9D` is `STA abs,X`; the code plainly means `$99`, `STA abs,Y`. The `ldy` on
the line before is loaded and discarded. So zero lands at `$D406 + x`:

| x | address | what it actually hits |
|---|---|---|
| 0 | `$D406` | voice 0 sustain/release — right, by accident |
| 1 | `$D407` | **voice 1 frequency LOW** |
| 2 | `$D408` | **voice 1 frequency HIGH** |

A `$62` on voice 1 or 2 silently zeroes part of *voice 1's* pitch. It survives
only until voice 1 next writes its own registers, which is why it surfaces on
exactly the frames where voice 1 takes the note-change early return and writes
nothing but `$D404`/`$D406` — 3-frame runs, every 20 frames.

It was found by tracing the real playroutine under py65 and asking which PC
wrote the register: every other frequency write came from `$152f`, that one came
from `$1137`. Static reading had produced three wrong guesses first (vibrato
depth, the seed, the wave-program cursor), all of which fitted the data until
the PC did not.

**`STA $D4xx,X` occurs in exactly two places corpus-wide**: `init`'s legitimate
`$D400-$D41C` clear loop, and this. And the 15 files carrying it are *precisely*
the 15 second-build files — the bug is part of what makes it a second build.

Reproduced, not corrected: the model exists to predict what the SID is fed.
Voice 1 of `Shogoon-Rave` went **43 misses → 1**, and the second-build
population **99.68% → 99.81%**.

### The out-of-range arp read — diagnosed, then FIXED

A wave program's arpeggio offset can push the note index **past the end of the
96-entry frequency table**. `Shogoon-Rave` instrument 4 steps `arp $33` on note
54 → index 105, and the tables sit directly in front of the player's own
variable block, so `freq_hi_table + 105` = `$1651` — voice 0's `freq_lo`
**variable**. The real player reads **live RAM** there; an image-based model
reads the frozen byte the editor saved.

This was first recorded as needing "a real memory array" and left alone. That
was an over-estimate: the model does not need general memory, only the addresses
it can already **name**. `_var_addr_map` inverts the two seed sources into
`{address: (attribute, voice)}` and the frequency-table read consults it **only
when the index exceeds the table**; everything else falls through to the image
exactly as before.

| population | before | after |
|---|---|---|
| layout-seeded (43 variables mapped) | 99.98% — 13 misses | **100.00% — 0** |
| second build (5 variables mapped) | 99.81% — 84 misses | **99.89% — 47** |

**The split is the evidence.** The fully-mapped population goes to *exactly*
100.00% while the partially-mapped one keeps a proportional remainder — which is
what the mechanism predicts and coincidence does not.

### The 47 were mostly ONE variable seeded from a constant (v3.25.0) — 47 → 18

Those 47 were assumed to be "the variables the second build's layout does not
expose". Measured, they were not a broad seeding gap at all: **every one of the
15 second-build files lost exactly 3 frames** (Griffin_Score 5), all on **frame
3, one per voice** — the last note-on pipeline frame, where the register still
carries the power-on value from the module image.

`vib_depth` is in **no** layout on either build, so it was the last variable
still placed by a constant, `load + $1C` — the pattern this player breaks by
construction. The bytes there were literally the error: `Shogoon-Rave` holds
`$42 $23 $0b` at `$101c` and its three voices were wrong by exactly
**+66 / +35 / +11**. The fake depth is applied as a downward vibrato during the
pipeline frames. It never showed on the first build because *that* build's other
vibrato state is seeded and blocks the vibrato before the first note — the
constant was wrong on 15 files and masked on the other 18.

Recovered from the leg that reads it instead (`HardTrackModule.vibrato_var_addrs`).
The player computes both pitch modulations identically —

```
BD lo lo      LDA freq_lo,X
18 / 38       CLC / SEC
7D/FD aa aa   ADC/SBC <amount>,X
```

— and there are exactly **four** such legs forming two pairs that share one
operand each: the SLIDE pair first (the routine tests `slide_cmd` before falling
through), then the VIBRATO pair. That shape holds on **33/33** decodable files
and is self-checking, which is what separates it from a byte pattern that merely
looks right. It resolves to `$101c` on all 18 first-build files — *the old
constant, so they are unchanged* — and to `$16bb` (`$46bb`/`$a6bb` relocated,
`$16ef` on `Tribute_to_Laxity`'s third shape) on the other 15.

| population | before | after |
|---|---|---|
| layout-seeded (18 files) | 100.00% — 0 misses | **100.00% — 0** |
| second build (15 files) | 99.89% — 47 misses | **99.96% — 18** |

`Trance`, `Tribute_to_Laxity` and `What_Can_I_Say_Crap` are now exactly 100.00%.
Pinned by `test_vib_depth_comes_from_its_consumer_not_a_constant`.

⚠️ **An open lead, deliberately not closed by picking the better number.** On
the second build *alone*, seeding **nothing** scores better than seeding the
correct address — 10 misses against 18 — so the saved byte at `$16bb` is not
quite that variable's power-on value. The address is not in doubt (unique
33/33); the byte is. Corpus-wide the recovered address is still both the best
and the principled option:

| seeding | build-1 misses | build-2 misses | total |
|---|---|---|---|
| old constant `load + $1C` | 0 | 47 | **47** |
| nothing | 13 | 10 | 23 |
| **recovered operand** | **0** | 18 | **18** |

Taking the seed that scored best on one population is exactly how the constant
being replaced got here, so the 8-frame difference stays recorded rather than
fitted. A clue for whoever picks it up: `$16bb` sits at **+109 from `freq_hi`**,
which is the block offset of `vib_dir` on the first build — so the second
build's variable ORDER may differ, and the leg may be reading a slot this model
names something else.

### Negative controls

A uniform 100.00% across 33 files is the shape this project has twice been
wrong about, so each assumption was broken on purpose to check the measurement
can still see it. Corpus-wide, 6 s window:

| deliberately broken | `$D416` | `$D417` |
|---|---|---|
| *(unmodified)* | **100.00%** | **100.00%** |
| cutoff clamped at 255 instead of wrapping | 24.75% | 100.00% |
| filter program never steps (delta frozen) | 23.90% | 100.00% |
| `f12 == 0` skips instead of clearing routing | 100.00% | 48.28% |
| fields 6 and 7 swapped | 28.34% | 100.00% |
| **field-5 bit 4 gate ignored** | **100.00%** | **100.00%** |

The last row is a real negative result and is recorded as one. Ignoring the
bit-4 gate entirely changes **nothing measurable**, because only **21
instruments** in the corpus set the bit and just **one** of those has a filter
to re-arm. The reading in the field table above comes from the bit's only
consumer in the disassembly; this corpus can neither confirm nor refute it, and
`test_field5_bit4_is_not_exercised_by_this_corpus` pins the two counts so the
claim can be upgraded if a file ever exercises it. The f6/f7 row is worth
noting separately: the swap costs 71 points, so the field identities are now
confirmed by the metric independently of how they were read off the code.

### Why the two populations are never pooled

They are now labelled by **seed source** rather than by a yes/no: `layout+sig`
(all 43 per-voice variables placed from the `_RAM` allocation) and `signature`
(the 5 recovered from their consumers, the other 38 starting at zero). Three
states, because collapsing them to a boolean hides the one that matters — and
because "unseeded" is simply no longer true of the second build.

The player's per-voice variables live **inside the loaded module image**, so
their power-on values are the bytes the editor saved there — the player's live
state at export — not zero. Assuming zero makes the first note of every voice
take the wrong branch at `$11bf`/`$12e2`, which spends one extra vibrato tick and
leaves that voice a frame out of phase **until the next note-on resyncs it**.
That single frame was the whole of the startup residual.

`ram_layout_base()` recovers the block by signature and **verifies it against
three independent anchors** (the abs-flag store's destination plus both stepper
cursors) before seeding anything. It succeeds on 18 files. The other 15 are the
second shipped player build, whose variable allocation genuinely differs —
everything past the abs-flag sits 3 bytes lower and `vib_depth`/`pending_note`
swap between the voice block and the module header, so it is a different
allocation, not an offset. Those run unseeded, are correct from their first
note-on onward, and are reported as a **separate line** rather than averaged in.

### What is left

12 frames on `Teekkno` and 1 on `Domagareflexow` — 0.02% of the seeded set, in
four 3-frame clusters where the frequency *high* byte is wrong and the low byte
is right. Unexplained; recorded rather than rationalised.

### Alignment was measured, not fitted

Offset 0 against siddump is a sharp peak, not a plateau: frequency scores
**100.0%** at offset 0 and 50.1% / 51.7% at ∓1 frame. `test_siddump_frame_
alignment_is_zero_not_fitted` pins that, so the alignment can never be quietly
tuned to flatter a future change.

### A parser bug this found

`pulse_table` was read from signature **+6** — the `lda ABS,y` *opcode* byte, not
its operand. It pointed outside the module on every file in the corpus, so
`pulse_program()` returned a full-length series of zeroes, which reads exactly
like a valid program that holds the pulse width still. Nothing caught it because
nothing scored `$D402/$D403` until now; with `+7` the pulse register goes from
**8.7% to 100.0%** on `Zakplus`. `test_pulse_table_lands_inside_the_module`
now asserts the table is in range for every decodable file.

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
- **Slide up/down** (`$63`/`$64`) become sustain rows.
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

Driver 11's entry points are a **command protocol** over the byte at `$16CC`, and
the per-frame tick at `$1006` dispatches on it. `init` at `$1000` leaves the
command at **`$00`**, which means *state not initialised*:

```
1000: sta $16cd      ; init: store subtune...
1003: lda #$00
1005: sta $16cc      ; ...and set command $00
...
1006: lda #$00       ; the per-frame TICK
1008: bit $16cc
100b: bmi $1051      ; $80 -> play one row  (the steady state)
100d: bvs $1047      ; $40 -> STOP: gate off $D404/$D40B/$D412, rts
100f: ...            ; $00 -> clear $16CD-$1740, seed, set command $80, rts
                     ;        -- and play NO row this call
```

So Driver 11 spends its **first play call initialising its own state** instead of
playing a row, and every render starts one frame behind the original.

It comes from **Driver 11**, not from this builder, so it applies to **every
Driver 11 Stage A build in this repo**, not just HardTrack. Three other
explanations were tested and refuted along the way: the PSID wrapper's play
address (`$1006` is right; forcing `$1003` gives total silence — because `$1003`
is the *stop* entry), the instrument hard-restart flag (`$80`/`$00`/`$40` give
identical offset histograms), and the builder's own row layout.

> ⚠️ **Corrected 2026-08-09.** This section previously said the cause was the
> template shipping `$16CC = $40`, with `BVS $1047` taking a "state-init path".
> The byte **is** `$40` in the file at rest, but `init` overwrites it with `$00`
> before the first tick ever runs, and `$1047` is the **stop** path, not init.
> The measured effect — one silent first frame — was right; the mechanism was read
> off the binary at rest instead of from a run. Now pinned by
> `pyscript/test_driver11_startup_frame.py` and documented canonically in
> [DRIVER11.md](DRIVER11.md); the trap itself is PATTERNS.md **F6**.

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

## Stage B — native driver (trace-driven)

```
py -3 bin/build_hardtrack_native_song.py SID/Shogoon/Love_tune_2.sid   # -> out/hardtrack_native/
py -3 pyscript/hardtrack_native_sweep.py -t 60                         # corpus sweep
```

Stage B adds **no new driver**. A MON-compatible shim (`HardTrackShim`) feeds
`bin/build_mon_native_song.build_native_song` — the same trace-driven engine
behind Hawkeye / Hubbard / DMC / Sound Monitor / SDI / Future Composer — and
`emit_one` assembles MoN's driver. This is the cheapest shape of Stage B in the
project and the second time it has been reused for a new player (FC was the
first), which is the point: the expensive part of Stage B is meant to be
written once.

**Only the sequencer crosses the shim boundary**: notes, tick durations,
instrument indices, all from `hardtrack_parser.voice_events()`. Every timbre
decision — waveform steps, pulse width, pitch modulation, filter cutoff — comes
from a **per-note capture of the original's own siddump output**. Nothing here
re-implements HardTrack's synth engine; it replays it. That is what dissolves
the entire Stage A loss list at once: `$62`'s stepper freeze, the note-on base
frequency, the pulse sweep, `$63`/`$64` slide/portamento, the global filter
sweep and the program-driven (field-5 bit 7) column are all just frames in the
capture.

> This is **captured, not modelled** — the PLAYBOOK distinction. It is exact for
> the window it was captured over and it is *not* a compact re-encoding of the
> player's tables, which is why a dense tune windows into many parts. Now that
> `hardtrack_synth.simulate_registers()` predicts those registers, a Stage C
> structural build that emits HardTrack's own looping programs instead of
> unrolled captures is a real option; Stage B does not attempt it.

### The three sequencer facts the shim depends on

1. **A row lands every `speed+1` frames, and rows tile the timeline.** Each
   voice's event list must be contiguous from tick 0 — `voice_events` inserts a
   leading rest for a voice whose pattern opens with `$67`, and gives the last
   event the rest of the window. `build_native_song` places event *k* at tick
   `sum(dur[:k])`, so a gap slides everything after it earlier for the whole
   song. Measured before the fix: Love_tune_2's voices 1 and 2 played 10 and 20
   frames early from the first bar.
2. **`$61` gate-off is folded into the preceding note, not emitted as a rest.**
   HardTrack keeps stepping the wave program after the gate clears, so a voice
   goes on **arpeggiating through its release** (Love_tune_2 voice 1: 150 frames
   per phrase at `wf $40`, gate off). A rest idles the driver's voice and throws
   that tail away; leaving it inside the preceding note's capture window replays
   it verbatim, because the gate bit is just another `$D404` byte there. Only a
   gate-off with nothing before it is a real rest.
3. **The note-on is a 2-frame pipeline.** A row dispatched on frame *G* leaves
   the previous note's frequency in `$D400` on *G* and *G+1*; the gate rises on
   *G+2*. For a re-triggered note `snap_gate` finds that rise by itself, so the
   offset is a no-op — but a note the part window **re-enters mid-flight** has
   no gate rise to snap to, and without the offset it replays its capture two
   frames early for its entire length (again Love_tune_2 voice 1: a 200-frame
   arpeggio wrong on every frame, while its waveform stayed byte-exact). The
   offset was swept, not assumed: `HT_PIPE=2` beats 0 and 3 on fidelity **and**
   drops the part count 8 → 6, which a fitted parameter would not do.

### `$6F` legato needs no mechanism here

Stage A had to invent a duplicate instrument slot for it (Driver 11 restarts a
wave program on every note and cannot express a tie at all). Stage B treats a
`$6F` note as an ordinary note-on: the driver does restart a wave program, but
the program it restarts is *this note's own capture*, which already begins
wherever the original's program had got to. The feature disappears into the
method.

### One shared-engine change

`build_mon_native_song` gained `_fm_scale_ok(m)` and the shim flag
`no_fm_scale`. The driver marks a SCALED (pitch-proportional vibrato) FM entry
by a `$40`–`$43` offset **high byte**, so a song whose real Hz deltas reach that
range cannot have the marker enabled. Hubbard's drum dives hit this first, which
is why `hard_restart` implied it — but HardTrack needs the opt-out *without*
Hubbard's kill-ADSR engine, so the two are now separate flags. Symptom worth
recognising: Love_tune_2's voice-2 drum has a `$4300` delta, and with the marker
on that one entry was dropped, freezing the note at the wrong absolute frequency
for its whole tail **while its waveform stayed byte-exact** — a defect no
waveform metric can see. Every other shim leaves `no_fm_scale` unset and is
byte-unaffected (MoN/arp/filter/wave-struct tests: 20 passed).

### Fidelity

Per-frame frequency (nearest semitone) against the original, over every part,
with the builder's own best-delay alignment. `Love_tune_2`, the full 117 s song,
6 parts:

| voice | raw (n) | audible, gate-on (n) | misses on the driver's note-on frame |
|---|---|---|---|
| 0 | 92.8% (5841) | 88.2% (3546) | 419 of 421 — **418 under the SID TEST bit** |
| 1 | 92.9% (5841) | 77.3% (1765) | 400 of 400 — 400 under the TEST bit |
| 2 | 95.1% (5841) | 91.5% (3117) | 265 of 285 — 265 under the TEST bit |

**Read the third column before the first two.** The driver holds the note's base
pitch on its trigger frame; HardTrack still has the *previous* note's frequency
there (fact 3 above). That frame can never match, and it is not a conversion
error — it is one frame per note, and the builder counts how many of them carry
the SID **TEST** bit, which resets the oscillator and makes the frame silent.
Essentially all of them do. Net of that structural frame, Love_tune_2 loses
**2 / 12 / 20 frames out of 5,841 per voice** — 99.97 / 99.79 / 99.66%.

The count is **reported, never excluded**: dropping frames chosen by a rule that
correlates with mismatch is how a metric launders itself. Both numbers are
printed side by side for exactly that reason, and the sweep prints a third
(`net`) with its own denominator.

### Corpus sweep

`py -3 pyscript/hardtrack_native_sweep.py -t 60` — **all 33 decodable files
build**, 195 parts in total, 60 s window each (quote the window; a 60 s slice of
a 117 s song is not the song).

| | |
|---|---|
| raw (all frames with a frequency either side) | **91.04%** (n = 277,392) |
| audible (original's gate on) | **88.25%** (n = 157,356) |
| misses | 24,840 — of which **15,575 are the driver's note-on frame** (15,203 of those under the SID TEST bit) |
| net of that structural frame | **9,265 of 277,392 = 3.34%**, i.e. **96.66%** |

Per file, by net-miss rate: **3 at exactly zero** (`Muza_Do_Dema`,
`Something_to_Eat`, `Teekkno`), **15 of 33 below 0.5%**, **22 of 33 below 2%**.

The tail is real and is **not** explained yet:

| file | net miss | note |
|---|---|---|
| `Fun_Factory` | 27.96% | 12 parts — the worst in the corpus |
| `Tribute_to_Laxity` | 16.40% | the odd third player variant; `instrument_count_verified == False`, so its instrument stride is not confirmed |
| `Griffin_Score` | 15.95% | 20 parts, by far the densest capture |
| `Illmatic_end` | 8.42% | |
| `What_Can_I_Say_Crap` | 6.81% | |

Three of the five are also the highest part counts, which is the obvious lead —
a dense capture is exactly where a canonical-program substitution has the most
chances to be accepted wrongly — but that is a **hypothesis, not a finding**,
and it has not been tested.

**Refusals: 6, not 5.** `HardTrackModule` refuses `Eternal`, `Fruitmania`,
`Miecze_Valdgira_2`, `Zone_of_Darkness` (multi-instance), `Commercial_Fake`
(PSID init `$2f01` ≠ entry `$1000`) and — newly visible because the sweep
enumerates by signature rather than by player-id — **`Dune_Cover`** (init
`$4000` ≠ entry `$0900`). `player-id` calls that file `Comer/Digi`, so the
"38 HardTrack files" count above is unchanged; the signature scan simply finds
one extra candidate and then correctly declines it.

⚠️ The sweep first reported **"117 refused"** because non-HardTrack files raise
the same exception type ("no init signature found") as a genuine refusal. The
directory is mixed-player, so that counted 112 GoatTracker/DMC files as
HardTrack failures. A refusal count is only meaningful against the right
denominator — fixed by distinguishing "not this player" from "this player,
refused".


### What Stage B does not do

- **It is not editable in the Stage A sense.** The captured programs are
  unrolled per note, so the SF2 opens and plays but its wave/pulse tables are a
  transcription, not the composer's tables. Stage A remains the editable route.
- **It windows.** Song length is bounded by the SF2II caps (`sidm2/sf2_caps.py`),
  and a dense tune becomes many parts; part count is a **density** measure, not
  an accuracy one.
- **Rung 3 has now been run and PASSES** — see *Rung 3* below. SF2II plays our
  Stage B SF2 identically to our own render.
- **`DriverSelector` is untouched**, deliberately, exactly as for Stage A.

---

## Rung 3: the instrumented SF2II capture (v3.25.0) — **PASSED**

`bin/sf2ii_vs_real.py` runs a patched SF2II (`bin/SIDFactoryII_dbg.exe`) that
dumps its SID registers every frame, so this measures what the **editor's own
driver actually plays**.

### The question rung 3 exists to answer, answered directly

Our `.sid` wrapper and the `.sf2` carry the same Stage B driver and data, so the
decisive test is whether the editor executes them the same way. Capturing SF2II
and comparing it against **our own wrapper's render** rather than against the
original:

| voice | freq | waveform | pulse | n |
|---|---|---|---|---|
| 0 | **100.0%** | **100.0%** | **100.0%** | 294 |
| 1 | **100.0%** | **100.0%** | **100.0%** | 286 |
| 2 | **100.0%** | **100.0%** | **100.0%** | 82 |

At offset 0, exactly. **SF2II plays our Stage B SF2 identically to our own
render.** There is no SF2II-only hazard in these builds, which is precisely what
rung 3 was there to establish.

Reproduce it with `pyscript/sf2ii_vs_wrapper.py` (v3.25.0), which is this
comparison rather than the editor-vs-original one:

```
py -3 pyscript/sf2ii_vs_wrapper.py out/hardtrack_native/Love_tune_2_part01.sf2                                    out/hardtrack_native/Love_tune_2_part01.sid 18
```

It lived in a scratch file until now, which is why the two retractions below
were possible at all -- the only thing in the repo was `sf2ii_vs_real.py`, and
that answers a different question.

### ⚠️ Two retracted readings, both from the same tool

This section previously said rung 3 was *inconclusive* (tool unreliable), then
that Stage B *failed* it. Both are wrong and both came from
`bin/sf2ii_vs_real.py` rather than from the build:

1. **"The tool is unreliable"** — the control was `out/Cybernoid_II.sf2`, a
   Driver 11 Stage A build, not the native Stage B build the byte-exact claim
   refers to. The native build (`out/mon/`) scores **100% on every register of
   every voice** (890/890, 863/863, 114/114), so the tool is sound.
2. **"Stage B fails rung 3"** — the tool's `Love_tune_2` figures (freq
   66/21/61%) are an alignment artifact. The same wrapper-vs-original
   comparison, same 20 s window, same gating, same 1-semitone tolerance, done
   per voice:

   | voice | at offset 0 | at shift −3 | tool reported |
   |---|---|---|---|
   | 0 | 23.6% | **91.2%** | 66% |
   | 1 | 13.8% | **93.4%** | 21% |
   | 2 | 4.3% | **64.1%** | 61% |

   Every tool figure sits between the misaligned and the correctly-aligned
   value. It scored a compromise offset, not the build.

**The standing lesson, for the third time in this cycle**: a per-register or
per-voice best-offset is meaningful only against the render's *global* offset,
and this render sits at −3 (`measure_voices` uses a best-delay alignment for
exactly this reason). The retracted filter fix above failed the same way.

### The tool is FIXED (v3.25.0) — and the diagnosis above was wrong

This section previously blamed the compromise on *one global offset where the
voices need different alignments*, and recommended a per-voice search. **That
was the wrong reading, and implementing it made things worse** (it picked
offsets 5 / 317 / 147 for three voices that in fact share −3, because a
repetitive tune has many spurious alignment peaks). The offset is genuinely
global — it is one startup delay. Two real defects, both now fixed in
`bin/sf2ii_vs_real.py`:

1. **The search range was `range(0, 400)` — it could not express a negative
   offset at all.** Our render *leads* the original by 3 frames, so the true
   answer was never in the search space. The tool reported the offset-0 value as
   though it were the build's fidelity.
2. **It ranked offsets by raw hit count, not match rate.** Hits are confounded
   by how many captured frames an offset leaves inside the trace window: offset
   157 beat −3 on hits (208+43+52) purely by comparing more frames, at a far
   worse rate (67/14/62%). Coverage is now a fairness *filter* — an offset that
   can only compare half the frames is a smaller experiment, not a better
   alignment — and rate is maximised within it.

Re-measured with the fix, `Love_tune_2` part 1 vs the original, 20 s:

| | offset | freq | waveform | pulse | AD/SR |
|---|---|---|---|---|---|
| osc1 | −3 | 91% (353/387) | **100%** | **100%** | **100%** |
| osc2 | −3 | 93% (354/379) | **100%** | 98% | **100%** |
| osc3 | −3 | 64% (59/92) | **100%** | **100%** | **100%** |
| filter | −3 | cutoff **100%** (359/359) | | route **100%** | |

The tool now finds −3 by itself and reproduces the hand-derived 91.2/93.4/64.1
above. Waveform and AD/SR read 100% on all three voices where the bogus offset
had shown 79/86/57. **Control**: MoN native `out/mon/Cybernoid_II_sub0_part01.sf2`
still resolves to offset 0 with every per-metric figure byte-identical to the
pre-fix run (984/987, 945/948, 126/126, cutoff 1000/1002) — the fix is a no-op
where the old search was already right. Galway and MoN use the same tool.

---

## Rung 4's residual brightness gap: two leads FALSIFIED, one unprovable here

"About half the brightness gap is still open" with ADSR named as the best
candidate. Re-measured at the render's real −3 alignment over `Love_tune_2`
part 1 (28 s, 1,396 frames), the picture is much narrower than that.

**Baseline reproduces exactly**: centroid **−51.4 Hz**, rolloff −169.6 Hz,
level −0.4 dBA — the documented post-passband figures.

### Every register difference, and whether it can be heard

| register | mismatching frames | audible? |
|---|---|---|
| cutoff `$D416` | 418 | **none** — 0 of 757 filter-routed frames differ; all 418 are on frames where `$D417`'s routing nibble is 0, i.e. the filter is out of circuit |
| frequency | 206 | **none** — all 206 carry the SID **TEST** bit or have the gate off |
| SR `$D406` | 336 | the only substantial one; every frame is gate-off (release tails) |
| AD `$D405` | 28 | negligible |
| waveform | 4 | negligible |

⚠️ **The "cutoff 94.6%" figure quoted above does not describe an audible
defect.** Restricted to the frames where the original actually routes a voice
through the filter, the cutoff is **100.0% byte-exact (757/757)**. That lead is
retired: it was measured over all frames, and the filter is not in circuit for
most of them.

Frequency is likewise exonerated for this purpose — its residual is entirely the
known structural note-on frame, which carries TEST and is silent.

### The SR-tail hypothesis is NOT supported by the energy measurement

If the gap were our release tails ringing where HardTrack cuts them dead, our
render would be **louder** than the original near those frames, and locally so.
Rendered both with sidplayfp and measured per-frame RMS:

| frames | level delta (ours − original) |
|---|---|
| 1–8 frames after an SR mismatch | **−0.84 dB** |
| all other frames | −1.17 dB |
| whole render | −1.08 dB |

Our render is **uniformly quieter**, by about the same amount everywhere. Extra
ringing tails predict the opposite sign and a local effect; neither appears.

⚠️ **This is not a clean falsification, and the reason is worth recording**:
`Love_tune_2` has an SR mismatch at every note-on across three voices, so 1,055
of 1,400 frames sit within 8 frames of one and only **3 frames** are clear of
all of them. There is no within-render control on this material, so the contrast
above is between "very near a mismatch" and "slightly less near". A tune with
sparser note-ons would give a real control.

**What would settle it**: build the `HRC` per-note lookahead (see the SR-only
row section below for why a row type cannot) and A/B the audio directly. That
remains the only decisive experiment — but it is now a **less** promising one
than the doc previously implied, because the register that was supposed to be
the cause does not move the energy in the predicted direction.

> **RUN, 2026-08-14.** The lookahead is built (`SR_PREKILL`, now ON by default)
> and the prediction above held: it fixes the registers (2,966 → 728 mismatching
> frames over nine tunes once gated on instrument mode) and makes `Love_tune_2`
> *darker*, not brighter. See the two sections below.

---

## The ADSR residual: an SR-only row was BUILT and REVERTED (v3.25.0)

ADSR is the weakest register in the audible window (88–94%). The residual was
recorded as "systematic — HardTrack's pre-note-on SR-zeroing on frames that
precede the capture window", with the fix given as an **SR-only `$7D` variant**
and its audible value marked unproven. The mechanism is confirmed, the fix as
specified does not work, and the reason is structural rather than a detail.

### What was confirmed

Measured on `Love_tune_2`, 996 frames per voice at the render's −3 alignment:

| | voice 0 | voice 1 | voice 2 |
|---|---|---|---|
| AD `$D405` differs | **0** | 9 | 19 |
| SR `$D406` differs | 68 | 67 | 107 |
| dominant mismatch | `ours=$3a → orig=$00` | same | same |

So `hard_restart = 1` really is the wrong fix — the `$7D` row zeroes AD as well,
and AD is already essentially right. Two further facts, both measured:

- **Every** SR-mismatch frame has the original's gate **OFF** — 68/68, 67/67,
  107/107. The difference can only ever affect a *release tail*, never a
  sounding note's attack or body.
- The original writes `SR=$00` on frames ≡ 1 (mod 5) with `frames_per_tick = 5`,
  i.e. at **row dispatch**, `onset_delay − 1` frames before the note reaches the
  SID, staggered per voice. 68 ≈ 2 × 35 note-ons: **exactly two frames per
  note**. (An intermediate reading called this "periodic, not pre-note-on" and
  was wrong — the periodicity *is* the note cadence.)

This is the classic hard restart, and it is the same mechanism that turned out
to be genuinely audible on Blackbird (the "drums aren't tight" root cause was a
pre-restart SR/gate blip), so "audible value unproven" is weaker than it looks.

### What was built, and why it was reverted

A `$7C` **SR-only kill row** — `lda #$00 / sta SID+6,y`, leaving AD, the gate and
the waveform alone — gated behind a new `SR_KILL` driver flag and a shim flag
`sr_restart`, emitted one row before each note in the manner of `_hr_rows`.

It assembles, builds all six parts, and **changes nothing**: SR mismatches stay
at exactly 68/67/107 and frequency is unchanged at 92.8/92.9/95.1.

The reason is structural. Stage B **folds gate-offs into the preceding note** (a
deliberate decision documented above — emitting a rest there idles the voice and
throws away the arpeggiated release tail), so the whole song contains just **90
rest rows out of 30,477**, of which only **30** precede a note. The original
zeroes SR before *every* note — 112 note-ons in 20 s alone. Notes are
back-to-back, and converting a note row to `$7C` would delete music, which the
emitter correctly refuses.

**A row type cannot express this.** The write has to land between row dispatch
and note-on, which in this driver is not a row boundary at all — it needs a
per-note lookahead. The driver already has the shape of one: `HRC`, the
HARD_RESTART re-arm countdown, whose own comment records that the "1-frame-early
HRC write was the dump diff's adsr residual" and that it is deliberately left at
0. That is where a correct fix would go, and it is a materially bigger change
than a new row — in a driver shared by seven players, for an effect bounded to
release tails on gate-off frames.

Reverted; the driver and both builders are byte-identical to before, and the
rebuilt part 1 reproduces 92.8/92.9/95.1 exactly.

---

## The per-note lookahead was BUILT, and it is NOT the brightness fix (2026-08-14)

The experiment above ("build the `HRC` per-note lookahead and A/B the audio
directly — that remains the only decisive experiment") has been run. It is
`SR_PREKILL` in `drivers_src/mon/romuzak_driver.asm`, it ships **off**, and
`HT_SR_PREKILL=2` turns it on per build. Reproduce the whole A/B with
`py -3 pyscript/hardtrack_sr_prekill_ab.py` — tracked, so unlike the DMC
figures it is not quoting a script that was never in the repo.

**The width is measured, not guessed.** Every `SR=$00` run in the originals is
*exactly two frames*: 159 runs on `Love_tune_2`, 378 on `Muminki_Rooooolz`, 328
on `Something_to_Eat`, 142 on `Muza_Do_Dema`, 23 on `Teekkno`. Nothing else.

It fires on the frame `zp_tcnt == SR_PREKILL` for a voice whose `vhold` is 0 —
one that FETCHES at the next row tick, the same predicate the SEEK pulse hold
already uses — and `sr_rearm` restores the instrument AD/SR on the fetch itself.
No row is spent, which is the whole point: the write lands between two row
boundaries, where Stage B has none to give.

### What it does to the registers

| file | window | SR mismatching frames, off → on |
|---|---:|---:|
| `Muminki_Rooooolz` | 28 s | 750 → **0** |
| `Something_to_Eat` | 10 s | 234 → **0** |
| `Ritual_II_tune_2` | 10 s | 125 → **3** |
| `Takisobie` | 12 s | 166 → **14** |
| `Rune-T_Noter` | 14 s | 235 → **21** |
| `Love_tune_2` | 28 s | 338 → **68** |
| `Walk_to_Soul` | 10 s | 299 → **83** |
| `Muza_Do_Dema` | 28 s | 777 → **513** |
| `Teekkno` | 28 s | 42 → **468** ⚠ |
| **total** | | **2,966 → 1,170** |

Summed over three voices at the render's −3 alignment. On `Love_tune_2` the
per-voice figure is 92/98/148 → 2/8/58, and **every** survivor is the reverse
direction (we zero where the player does not), so the defect the doc named is
gone rather than reduced.

### What it does to the audio — and this is the answer

Mean |centroid error| **67.2 → 52.7 Hz**, mean |rolloff error| **182.9 → 136.2
Hz** across the nine tunes. Closer to the original on **5 of 9**, further on 4.

**But it makes `Love_tune_2` worse: centroid −57.9 → −101.4 Hz, rolloff −160.7
→ −255.1.** That is the one file the brightness gap was ever about, so the
answer to the filed question is **no** — the lookahead is a correctness fix that
happens to help the corpus, not the fix for the residual it was proposed for.

The SR-tail hypothesis is nevertheless confirmed *in direction* and shown to
**overshoot**. Per-frame RMS on `Love_tune_2`, binned by the ORIGINAL's own level:

| the original's level | frames | off, ours − orig | on, ours − orig |
|---|---:|---:|---:|
| −35..−28 dBFS (tails, quiet passages) | 295 | **+1.26 dB** | **−0.48 dB** |
| −28..0 dBFS (the music) | 1,099 | −1.87 dB | −2.19 dB |

We really were ringing too loud where the player cuts the tail dead, and the fix
more than halves that error. It costs 0.32 dB on the loud frames to buy it, and
on this tune that trade reads as *darker*, not *tighter*.

### `Teekkno` refutes "every note" — and mode 2 IS the selector

Keyed by the AD/SR pair written on each note-on, over part 1:

| file | note-ons | preceded by an `SR=$00` restart |
|---|---:|---:|
| `Love_tune_2` | 159 | **159 (100%)** |
| `Muminki_Rooooolz` | 378 | **378 (100%)** |
| `Teekkno` | 245 | **23 (9%)** |

So the restart is a **per-instrument** property, not a per-note or per-song one,
and `Teekkno` is the file that discriminates: its ADSR `$0ffc` restarts on 1 of
222 note-ons while `$099d`/`$099e`/`$cccc` restart on 9/10, 7/7 and 4/4. Firing
unconditionally is what costs `Teekkno` 42 → 468 and flips its centroid sign.

Two candidate selectors were **ruled out** on the way:

- **Instrument field 5 bit 4.** The player reads field 5 exactly three times per
  module with masks `$03`, `$10` and `$80` in 33 of 33, and `$10`'s only consumer
  is the filter re-arm guard (disassembled above under `skip_filter_rearm`).
- **Gate state.** The two pre-note frames are gate-off in every case measured, on
  the file that restarts and the file that does not alike.

The answer was the third mask, `$03` — see the next section.

### Two traps, both invisible to the register comparison

1. **`sr_pre` must be gated on the voice being SILENT.** `SR=$00` zeroes
   *sustain* as well as release; the envelope falls to zero and only a gate RISE
   re-attacks it, so one mistimed kill silences the rest of a held note **while
   every later register still reads correct**. Four such frames on `Love_tune_2`
   cost **−24 dB** across 27.1–28.0 s. The SR diff saw 4 frames; the audio saw a
   hole. Never ship this measured only in the register domain.
2. **The gate cannot be recomputed from `WAVE[VWI]`.** `wave_step` INCs `VWI` on
   the frame a row's count expires — which is exactly the pre-fetch frame
   `sr_pre` runs on, so the recomputed byte is the *next* row's, and the first
   attempt at the guard blocked 100% of the kills instead of 4 of 244. The driver
   now stashes the `$D404` byte it actually wrote in `VGCUR`.

### Safety

Verified byte-identical with the flag off: `Monty_on_the_Run` (Hubbard,
`HARD_RESTART=1`), `Final_Luv` (Sound Monitor, `HARD_RESTART=0`), MoN's
`Cybernoid_II`, and `Love_tune_2` itself.
`pyscript/test_hardtrack_sr_prekill.py` pins that every byte of the feature sits
inside a `.if SR_PREKILL` block, that the kill touches `$D406` and never `$D405`,
and that both gates precede the store.

---

## The selector is instrument mode 2, and the fix is ON by default (2026-08-14)

The section above left one thing open — *which* instruments get the restart —
and answered it wrongly by omission, because firing on every note is what cost
`Teekkno` 42 → 468. The selector is **instrument field 5 bits 0–1 == 2**, the
`mode` the parser had named and never explained.

Both of the player's `LDA #$00 / STA $D406,y` sites are guarded by the PREVIOUS
frame's mode, held per voice:

```
$11ca  lda F5,y / and #$03 / pha      ; this instrument's mode
$11d0  lda mode,x / sta prevmode,x    ; shift: prev <- cur, once per frame
$11d7  pla / sta mode,x
$11da  lda prevmode,x / cmp #$02
$11df  beq $11e9                      ; -> lda #$00 / sta $D406,y + gate off
$11e1  lda #$fe / sta gmask,x         ; else a PLAIN gate-off

$12da  lda legato,x / bne skip        ; the note-FETCH path: the same kill,
$12e2  lda prevmode,x / bne $12ea     ;   on a non-legato fetch
```

Three things follow, and each one had to be got right:

- **It belongs to the note that is ENDING**, not the one starting. Keyed on the
  starting note the rule scores 4 of 6 ADSR keys on `Teekkno`; keyed on the
  ending note it scores **242 of 242**.
- **The corpus carries only modes 0 and 2** (134 and 792 instruments across 38
  files), so the fetch site's `bne` is the same test as the note-end site's
  `cmp #$02`.
- **It is not `skip_filter_rearm`.** Bit 4 suppresses a filter re-arm and reaches
  nothing else — that reading stands. The real hard restart was in the two bits
  next to it, which is why field 5's three masks (`$03`, `$10`, `$80`) were the
  right inventory and the wrong conclusion.

Measured against the players' own output, keyed on the ending note:

| file | note-ons | predicted correctly | false positives |
|---|---:|---:|---:|
| `Teekkno` | 242 | **242 (100%)** | 0 |
| `Love_tune_2` | 158 | **158 (100%)** | 0 |
| `Muminki_Rooooolz` | 375 | **375 (100%)** | 0 |
| `Walk_to_Soul` | 340 | 331 (97.4%) | 0 |
| `Muza_Do_Dema` | 145 | 139 (95.9%) | 0 |

**Zero false positives in 1,260 note-ons.** The residual on the last two is
one-directional — restarts the rule does not predict, never restarts it invents
— and the ADSR-pair proxy used to attribute an instrument is itself part of it.

### Wiring

`Instrument.ends_with_hard_restart` → the shim's `sr_restart` → instrument col2
bit **`$04`** → `sr_pre` tests `VIFLAGS,x`. `VIFLAGS` still holds the ending
note's instrument at that moment, because the next fetch has not run `set_instr`
yet — the same reason the write has no row to live on. The emitter masks `$04`
out unless `SR_PREKILL` is set, so a build without the feature is byte-identical
whatever a shim asks for.

### What it does, gated

| | unconditional | mode-2 gated |
|---|---:|---:|
| SR mismatching frames, the 9 tunes | 2,966 → 1,170 | 2,966 → **728** |
| `Teekkno`, the discriminating file | 42 → **468** | 42 → **26** |
| mean \|centroid error\| | 52.7 Hz | **51.4 Hz** |
| mean \|rolloff error\| | 136.2 Hz | **132.6 Hz** |

`Love_tune_2` still reads darker (−56.6 → −102.7 Hz centroid) and that is still
the honest cost: the fix makes the envelope right and spends brightness doing it.
Its release-tail level error is more than halved in exchange (+1.26 → −0.42 dB
on the frames where the original sits at −35..−28 dBFS).

### The whole corpus, and the rebuild

Registers only (`--all --no-audio`), each file over the part-1 span its own build
reports — 33 files, three chunks:

| chunk | files | SR mismatching frames, off → on |
|---|---:|---:|
| 1 | 8 | 3,351 → 363 |
| 2 | 11 | 4,439 → 794 |
| 3 | 14 | 4,607 → 637 |
| **all** | **33** | **12,397 → 1,794**, WORSE on **0** |

Not one file regresses, which is what turned this from an experiment into a
default. The Stage B fidelity sweep is **byte-identical** off vs on — raw 91.04%,
audible 88.25%, 9,265 net misses either way — because the fix does not touch
frequency; it is a safety check, not a win, and reading it as one would be the
`0 == 0` mistake `fidelity_common` exists to prevent.

**Shipped ON** (`HT_SR_PREKILL=0` disables, which is how the A/B is taken), and
the corpus was rebuilt with it: `py -3 pyscript/hardtrack_native_rebuild.py`
clears `out/hardtrack_native/` and rebuilds all **33 of 33** at the default
window, 313 parts. `passband_check --player hardtrack` still reads **25/33** with
the same 8 UNCONFIRMED multi-part files, so nothing there moved.

*A fix in the builder is not a fix in the corpus* (`PATTERNS.md` F7) — that is
why the rebuild is a tracked script and not a sentence in a commit message.

---


## Rung 4: the first listening pass (v3.25.0)

Every fidelity number in this document above is **headless**. PLAYBOOK §4 rung 4
had never been run on this player, and in this repo headless has overstated
before — Galway's "37 faithful" became 30/40 under an objective metric. So:
`Love_tune_2` part 1 (0–28 s), original vs the Stage B render.

**The control first.** Original vs itself scores **exactly 0.0 on every
feature** — the render is deterministic — so any non-zero delta below is real
signal rather than render noise.

| | original | Stage B | delta |
|---|---|---|---|
| RMS level (A-weighted) | −29.2 dBA | −28.5 dBA | **+0.7 dBA** |
| spectral centroid | 1994.0 Hz | 1894.7 Hz | **−99.3 Hz** |
| rolloff (85%) | 4478.0 Hz | 4197.9 Hz | **−280.1 Hz** |
| spectral flatness | 0.494 | 0.479 | −0.015 |
| dominant pitch class | A 0.18, B 0.14 | A 0.16, D♯ 0.16 | **+0.023 D♯, −0.022 A** |

Mix onsets: **225 of 308 matched**, offset +10 ms, jitter 50 ms.

**The spectrogram shows no gross defect.** Both panels carry the same harmonic
banding, the same rhythmic vertical structure and the same section boundary; the
diff panel is mostly neutral with fine vertical striping, which is the signature
of small time-alignment jitter rather than wrong or missing notes — consistent
with the one-frame-per-note structural offset already documented above.

So the honest verdict is **close but measurably not identical**: the Stage B
render is slightly darker (centroid −99 Hz, rolloff −280 Hz) and carries a small
pitch-class shift toward D♯. Not a pass, not a failure — a baseline.

**And following that "darker" reading found a real defect.** See below; it
accounts for about half of it.

### The defect rung 4 found: the passband was never captured

The brightness loss was **not uniform** — windowed at 4 s it is flat for 12 s and
then steps (centroid +1/−12/+0, then −128/−257/−152/−168). Worth noting that
`--windowed`'s worst-window search **did not flag it**: it removes each metric's
median and ranks the spread, so a *step* reads as spread rather than as an
outlier. Read the per-window table, not just the verdict line.

Comparing the two renders register by register found the cause immediately, and
it was not subtle: the **filter passband matched on 0.0% of frames.** The
original selects low+band (`$D418` mode 3) on 100% of frames; the Stage B render
wrote low-pass on 100% of them.

The cause is a missing argument. `build_native_song` takes its traces as a
tuple, and the **third element is the `$D418` passband**; without it
`_filt_set_row` defaults to `passband=1`, low-pass. The HardTrack builder passed
a 2-tuple.

This is a **known bug class that HardTrack was simply missed by** — the fix has
existed since the MoN work, and `passband_trace`'s own docstring names it:

> *"This was never captured, so `_filt_set_row` hardcoded low-pass and every MoN
> tune was rebuilt with a low-pass whatever it actually selected. Inaudible in
> the freq/wf/pulse columns, so it survived until `$D418` became a scored
> dimension."* — with `Cybernoid_II $D418 = $3F (low+band), we wrote $1F`.

"Inaudible in the freq/wf/pulse columns" is exactly why it survived here too:
**this builder's own fidelity report scores frequency and nothing else**, so no
headless number in this document could ever have moved. Fixed:

| | before | after |
|---|---|---|
| `$D418` passband match | **0.0%** | **100.0%** |
| RMS level (A-weighted) | +0.7 dBA | −0.4 dBA |
| spectral centroid | −99.3 Hz | **−51.4 Hz** |
| rolloff (85%) | −280.1 Hz | **−169.6 Hz** |
| spectral flatness | −0.015 | −0.003 |

Frequency fidelity, part count and part sizes are all unchanged, as they must be.

**The same gap was then checked across every native builder**, and measured
rather than assumed — an absent call is only a defect if that player's originals
actually select a non-low-pass passband:

| builder | passband its original selects | verdict |
|---|---|---|
| HardTrack | low+band 100% | **was wrong — fixed** |
| DMC (`Rockbuster`) | low+band 100% | **was wrong — fixed** |
| Future Composer | low 100% | default was right by luck — **confirmed 5/5, 2026-08-13** |
| SDI | **BP / LP+BP / LP+HP / LP+BP+HP, and modulating** | ⚠️ **this row was WRONG** — it was one file. 15 of a 30-file sample fail; builder fixed 2026-08-13, corpus not yet rebuilt |
| MoN | low+band, band+high, modulating | **was wrong — fixed** (`464406a`), and 131 of 206 artifacts kept the bug until 2026-08-13 |
| Blackbird | LP / BP / LP+BP, modulating | **correct, 16/16** — but only measurable against its simulator; siddump cannot drive an LFT rip |
| Hubbard | none 100% | no passband to get wrong |
| Sound Monitor | none 100% | no passband to get wrong |

⚠️ **This table checked each builder's CODE, and per player it checked ONE
FILE.** Both limits cost something: the code check missed that 31 of 33
HardTrack, 968 of 984 DMC and 131 of 206 MoN shipped artifacts predated their
fix, and the one-file sampling recorded SDI as fine when half its corpus is not.
See `PATTERNS.md` F7.

DMC's fix was verified by byte-diffing the emitted SF2 against a build with the
change reverted: **exactly 8 bytes differ, all filter SET rows, every one
`low → low+band` with its cutoff nibble untouched.**

### ⚠️ The fix was in the BUILDER. The files on disk were not rebuilt.

Everything above is true of `build_hardtrack_native_song.py` and was false of
almost every artifact it had produced, for two days, while this document quoted
the builder. `pyscript/passband_check.py` measures the **artifact**; run against
the 33 shipped builds on 2026-08-12 it found 21 rendering the wrong passband.

The accurate statement is stronger than "21 were stale":

> **31 of 33 artifacts came from the PRE-FIX code, which wrote low-pass
> unconditionally.** That is observable on the 21 whose originals select
> anything other than plain LP; on the other 10 the hardcoded default happens to
> be the right answer. Only `Love_tune_2` and `Zakplus` — both rebuilt after
> `cffc51e` — were correct by construction.

So the defect rate in builder *output* was 100% until the fix, and a naive audit
scoring 12/33 "correct" would have been reading coincidence as evidence.

After rebuilding all 33:

| | passing | note |
|---|---|---|
| before | **2** by construction (12 by the check) | 10 correct only because their original is LP-only |
| after | **24 of 33** | all 10 static-wrong files → 100.0% |

⚠️ **The "9 remaining failures" reported here on 2026-08-13 are RETRACTED.**
They were an artifact of the checking window, not defects. `passband_check`
compared part 1 against a fixed 28 s for every file; HardTrack part 1s are
**6-12 s**, and past its end our part **loops**, so the comparison ran our
restarted part against the original's continuing music. Re-checked at each
file's true part-1 span, read off the builder:

| file | at fixed 28 s | true part 1 | at its true span |
|---|---|---|---|
| `Something_to_Eat` | 68.7% | 10 s | **100.0%** (31 mode changes vs 31) |
| `Illmatic_end` | 71.1% | 6 s | **100.0%** (8 vs 8) |
| `Takisobie` | 57.2% | 12 s | **99.8%** |
| `Fun_Factory` | 69.5% | 6 s | **99.0%** |

`Something_to_Eat` was the headline example — "88 mode changes against the
original's 87". At its real span it is **31 against 31**; the extra changes were
our own loop. The claim that the residual is mode *timing* rests on nothing.
Fitted offsets do land on −3, matching this document's render offset, and that
part still holds.

**All 9 have since been checked at their true spans, and none is a wrong
passband:**

| file | part 1 | at fixed 28 s | at its true span |
|---|---:|---:|---:|
| `Something_to_Eat` | 10 s | 68.7% | **100.0%** (31 changes vs 31) |
| `Illmatic_end` | 6 s | 71.1% | **100.0%** (8 vs 8) |
| `Domagareflexow` | 26 s | 96.3% | **100.0%** (8 vs 8) |
| `Ritual_II_tune_2` | 10 s | 71.2% | **100.0%** (35 vs 34) |
| `Hopscotch` | 20 s | 88.8% | **99.9%** (4 vs 4) |
| `Rune-T_Noter` | 14 s | 80.2% | **99.9%** (13 vs 14) |
| `Takisobie` | 12 s | 57.2% | **99.8%** |
| `Fun_Factory` | 6 s | 69.5% | **99.0%** (12 vs 12) |
| `Altered_States_Tune_2` | 12 s | 97.2% | **93.4%** — see below |

**`Altered_States_Tune_2` has nothing audible left in it either.** The original
holds `$D417 = 0` for its first 50 frames — **feeding no voice to the filter**
— while selecting LP; our build reads `off` across exactly that stretch and
agrees from the moment a voice is actually routed. **All 47 mismatched frames of
599 are unrouted frames: zero audible mismatches.**

The tool hid this by reporting the routed fraction **globally** (80% for this
file), which answers "does this tune use the filter at all" when the question is
"does it use the filter *where we disagree*". `passband_check` now counts
mismatches on routed frames only and prints them as `80%/0a`. The unrouted rule
already existed — it was running over the wrong frames, which is why it caught
three all-unrouted DMC files and missed this one.

The underlying difference is still a STARTUP LATENCY, not a mode error: The original selects LP from frame 0; our
build reads `off` until **frame 47** (0.94 s) and LP thereafter. All **47 of its
599 mismatched frames are that opening gap** — the filter program's first SET
row simply lands late, and the checker's unusual +8 fitted offset (every other
file sits at −3) was the fit trying to absorb it. Nothing after frame 47
disagrees.

So the passband on this player is **correct on all 33 builds**; what remains is
under a second of missing filter state at the start of one file.

`passband_check` reports a multi-part failure as **UNCONFIRMED** unless
`--seconds` is asserted, because over-running can only manufacture disagreement
— which also means the **passes are unaffected**: a file that matched across a
too-long window matched everywhere it was compared.

All 9 route the filter on 59-100% of frames, so none of them was the inaudible
class DMC turned out to have — but that was never the reason they failed. `passband_check.py` reports the routed
fraction because `$D418`'s mode bits choose which filter OUTPUT is summed while
`$D417`'s low nibble chooses which voices are fed IN — a passband mismatch on a
tune that routes nothing cannot be heard, and three DMC files were counted as
failures three times before that was noticed. It does not excuse anything here:

| | agree | routed |
|---|---:|---:|
| `Something_to_Eat` | 68.7% | 100% |
| `Illmatic_end` | 71.1% | 95% |
| `Domagareflexow` | 96.3% | 99% |
| `Fun_Factory` | 69.5% | 84% |
| `Ritual_II_tune_2` | 71.2% | 84% |
| `Rune-T_Noter` | 80.2% | 83% |
| `Altered_States_Tune_2` | 97.2% | 75% |
| `Hopscotch` | 88.8% | 72% |
| `Takisobie` | 57.2% | 59% |

`out/dmc/` was NOT rebuilt — 968 of its 984 `.sf2` predate `cffc51e`, and
`passband_check.py --player dmc` exists to size that before anyone commits to a
57-song rebuild.

### ⚠️ Fixing the passband did NOT close the brightness gap

The rung-4 pass attributed a brightness deficit to the missing passband:
"consistently darker", centroid −99.3 → −51.4 Hz, rolloff −280.1 → −169.6 Hz.
**That was measured on one file, and it does not generalise.**

Measured across 8 tunes with `HT_NO_PASSBAND=1` — the pre-fix 2-tuple
reproduced deliberately, so both arms come from the same builder and the only
difference is the passband:

| | mean |Δ| reduction | closer with passband on | no-passband arm *darker* |
|---|---|---|---|
| spectral centroid | +3.95 Hz | 4/8 | **2/8** |
| rolloff (85%) | **−32.54 Hz** | 2/8 | **1/8** |
| RMS level (A-weighted) | +0.41 dBA | **7/8** | 0/8 |
| spectral flatness | −0.00 | 2/8 | 3/8 |

Two claims die here. **"Missing passband reads as darker" is refuted** — on 6 of
8 files the low-pass-only render was *brighter* than the original. And **the fix
does not move brightness toward the original**: centroid is a coin flip and
rolloff gets *worse* on 6 of 8. The only consistent gain is A-weighted level.

Among the four files that reached 100.0% register agreement, one improved
sharply (`Teekkno`, centroid −136.8 → −45.7, rolloff −330.7 → −154.6), one did
not move at all (`Walk_to_Soul`, +86.6 → +87.2 despite going 0% → 100%), and two
got **worse** (`Muminki_Rooooolz`, centroid +77.1 → +172.5).

**The A/B is confound-free, and that was checked rather than assumed.** The
worry was that "before" artifacts dated from 2026-08-09 and "after" from today,
folding three days of builder changes into the deltas. Re-built with
`HT_NO_PASSBAND=1` against today's code, the register traces of the two
no-passband arms are **identical across all 1400 frames** on every file tested —
including three whose SF2s differ in bytes, where the differences sit in data the
player never reaches. The only output-affecting HardTrack builder change since
2026-08-09 *is* the passband.

So the passband fix stands on **correctness** — the register is now right where
it was provably wrong — and not on any audio claim. The brightness gap is
unchanged, and it now has one fewer candidate mechanism.

### Per-voice isolation: run at a real floor, and the cross-voice lead is DEAD

Per-voice isolation is what localised the equivalent Matt Gray audio gap. Run on
`Love_tune_2` part 1 (28 s, `--voice all`) it returns **SYNTHESIS** on voices 1
and 2 — audio 73% and 67% against floors of 89% and 95%, registers 96-100%
byte-exact.

The first run of this used `--repeat-floor 1`, which prints `p=0.50 by rank
alone` — no power at all, the exact trap `PATTERNS.md` F5b and `MON.md` record,
where a "register-exact but SYNTHESIS on every voice" reading on Maniacs of
Noise was **falsified** as metric noise. Re-run at `--repeat-floor 3` it is
`p=0.25`. Better, still below any conventional bar, and the isolation guard
**warns on our side**, so the tool's own words apply: "usable but partly
correlated across voices". Voice 3 reads SEQUENCER, not SYNTHESIS — its
registers diverge too (freq 94.1%).

**The cross-voice asymmetry that came out of the first run does NOT survive a
second tune.** The claim was that the original's voices are uncorrelated once
isolated while ours are not:

| inter-voice correlation of the "isolated" renders | orig r(1-2)/(1-3)/(2-3) | ours |
|---|---|---|
| `Love_tune_2` | +0.01 / +0.03 / −0.01 `[clean]` | +0.14 / +0.17 / +0.13 `[warn]` |
| `Jazzloor` | +0.05 / +0.12 / +0.10 `[warn]` | +0.09 / +0.17 / +0.10 `[warn]` |
| `Hopscotch` | +0.07 / +0.04 / +0.11 `[warn]` | +0.69 / +0.77 / +0.72 `[refuse]` |

On `Jazzloor` the original bleeds essentially as much as we do. So "our renders
bleed" is **not** a general property — it was a `Love_tune_2` fact. What holds
across all three is only the weaker statement that ours is never *better* and is
sometimes far worse. `Hopscotch`'s `[refuse]` at 56-80% shared energy is
unexplained and **is not the passband**: that file's `$D418` is static on our
side, so it cannot be driving an all-muted residual. One untested confound
remains — `residual/mix` is a ratio, so a quieter mix inflates it, and absolute
levels were not checked.

### The brightness gap is ONE FILE, and the corpus goes the other way

After the passband fix the windowed step on `Love_tune_2` is roughly halved but
still there (centroid −65/−146/−74 from 12 s on). **That is a `Love_tune_2`
fact and it does not generalise.** Measured across 9 tunes on 2026-08-13, each
over a window inside its own part-1 span:

| file | window | centroid Δ | rolloff Δ |
|---|---:|---:|---:|
| `Muminki_Rooooolz` | 28 s | **+172.5** | +500.7 |
| `Ritual_II_tune_2` | 10 s | **+170.9** | +412.9 |
| `Rune-T_Noter` | 14 s | +32.8 | +42.0 |
| `Muza_Do_Dema` | 28 s | +28.9 | +64.4 |
| `Takisobie` | 12 s | +18.7 | +100.8 |
| `Walk_to_Soul` | 10 s | +11.7 | +140.8 |
| `Something_to_Eat` | 10 s | +4.5 | +183.0 |
| `Teekkno` | 28 s | −45.7 | −154.6 |
| `Love_tune_2` | 28 s | **−51.4** | −169.6 |

**Our render is darker on 2 of 9 and brighter on 7**, rolloff splitting the same
way. (The SR pre-kill section above re-measures this same nine-file table with
the lookahead on: it pulls the seven bright files toward the original and pushes
the two dark ones further away, which is the same asymmetry seen from the other
side.) So "the render is consistently darker, close the gap" is the wrong frame:
there is a per-file spectral difference in both directions and no corpus-wide
deficit to close. A mechanism proposed for a *darkness* gap has to explain
`Muminki_Rooooolz` at **+172 Hz** as well.

> ⚠️ **Every window here sits inside its file's part 1**, and that was nearly
> got wrong a fourth time in one session. Five of these files have 10-14 s part
> 1s and the first pass measured all nine over 28 s, past which our part loops
> against the original's continuing music. The five moved substantially
> (`Ritual_II_tune_2` +280.4 → +170.9, `Walk_to_Soul` +87.2 → +11.7,
> `Takisobie` +84.8 → +18.7) though none changed sign. Quote a HardTrack audio
> figure only with the part-1 span it was taken inside.

Two things are already ruled out:

- **The waveform is not the cause.** Its mismatch pairs are *symmetric* —
  `$40→$09` ×22 alongside `$09→$40` ×22, `$13→$12` ×40 alongside `$12→$13` ×38.
  Equal counts in both directions is a phase offset, not wrong content.
- **The filter is not routed in for the first 12 s** (`$D417` routing bits read
  0.00, then 0.79 → 1.00). That is why the cutoff being wrong by +115 over
  0–12 s is inaudible, and why the step exists at all: the filter comes into
  circuit at 12 s.

### ⚠️ A filter-alignment "fix" that was RETRACTED

Worth recording, because the mistake is a general one and it was caught only by
a second measurement.

Over the 800 frames where the filter is routed in, the cutoff matched **0 of
800** at shift 0, and **757 of 800 (94.6%) at a whole-track shift of −3**. That
reads as "the sweep is correct but 3 frames early", and `onset_delay` for this
player is exactly 3, which made it look conclusive. A `filter_capture_shift` was
added, and it did move the cutoff to 88.6% exact **at shift 0**.

**It was wrong.** The whole part render is uniformly **−3 frames** against the
original — that is why `measure_voices` uses a best-delay alignment in the first
place. Measured the same way, all three voices' frequency also peaks at −3
(96.1% / 95.7% / 77.1% within 50 cents, against 26.5% / 4.7% / 2.4% at shift 0).
So the cutoff's −3 was **already consistent with the rest of the render**, and
"fixing" it to 0 moved the filter 3 frames out of step with the voices.

The tell was there and was missed: the change produced a large register gain and
**no audible change whatsoever**. That should have prompted the check it
eventually got.

**The lesson: never align one register in isolation.** A per-register best-shift
is only meaningful against the render's *global* offset. `HARDTRACK.md` already
carries the sibling rule for the model —
`test_siddump_frame_alignment_is_zero_not_fitted` exists because offset 0 must
be a sharp peak — and the same discipline applies to the render.

Reverted; the shared `build_native_song` is untouched again.

### The register table, measured at the render's actual offset

Every per-register figure earlier in this section was taken at shift 0 and is
therefore **wrong**. Re-measured at the render's real −3 offset, `Love_tune_2`
part 1:

| | 0–12 s (filter not routed) | 12–28 s (filter routed in) |
|---|---|---|
| waveform `$D404` | 100.0 / 99.7 / 99.7% | **100.0 / 100.0 / 99.8%** |
| pulse `$D402/3` | 100.0 / 100.0 / 100.0% | **100.0 / 100.0 / 100.0%** |
| frequency | 96.3 / 95.1 / 93.5% | 96.9 / 96.6 / 91.6% |
| ADSR `$D405/6` | 93.0 / 92.3 / 90.6% | **93.8 / 93.2 / 88.2%** |
| cutoff `$D416` | 37.2% *(inaudible — not routed)* | **94.6%** |
| `$D417` / passband / volume | 100% / 100% / 100% | **100% / 100% / 100%** |

This is a much better result than the shift-0 numbers implied, and it retires
the "waveform divergence" lead entirely: at the correct alignment the waveform
is essentially exact, and the symmetric mismatch pairs were the offset itself.

### Next lead: the pre-note-on SR zeroing is not reproduced

With waveform, pulse, `$D417`, passband and volume all at 100%, **ADSR is now
the weakest register in the audible window** (88–94%), and its residual is
systematic rather than phase:

```
orig $0800 -> driver $088C   x42        AD matches, SR does not
orig $0100 -> driver $013A   x84
orig $0000 -> driver $00AA   x40
```

The high byte (AD) always agrees; the original writes **SR = `$00`** where the
driver writes the instrument's real SR. That is HardTrack zeroing sustain/release
on the frames *before* a note-on — the classic hard restart, emitted by the
`check_note` early return (`$11e9`: `lda #$00 / sta $d406,y`) and by `$12ea`.

Those frames sit **before** the note-on, so they precede the per-note capture
window and the driver never sees them. Note that the shim currently sets
`hard_restart = 0` on the stated grounds that "HardTrack's field-5 bit 4 is its
OWN hard restart, already in the capture" — that is true of bit 4 and **not** of
this path, which is a different mechanism.

#### `hard_restart = 1` is provably the WRONG fix

The shim's comment warns that `B.HARD_RESTART` is the *Hubbard kill-ADSR engine*
and "would add a behaviour this player does not have". That is now measured
rather than taken on trust, and it is exactly right:

- the driver's `$7D` hard-restart row does **gate off + AD/SR = 0**
  (`_hr_rows`: *"the `$7D` hard-restart row (driver: gate off + AD/SR=0)"*);
- HardTrack's `$11e9` writes **`$D406` only** — `$D405` is never touched.

Over all 1,397 frames of part 1, at the render's real offset:

| voice | AD differs | SR differs | of SR misses, "orig SR=0, driver ≠ 0" |
|---|---|---|---|
| 0 | **0** (0.00%) | 92 (6.6%) | **100%** |
| 1 | 10 (0.72%) | 98 (7.0%) | 92% |
| 2 | 20 (1.43%) | 148 (10.6%) | 88% |

**AD already matches on 98.6–100% of frames.** Enabling the driver's hard
restart would zero AD as well and *introduce* errors into the one half of the
register that is currently right, in order to fix the other half. A correct fix
needs an **SR-only** variant of the `$7D` row — an asm change in
`drivers_src/mon/`, in a driver shared by seven players — and its audible value
is **unproven**: the cutoff-alignment episode above is a fresh example of a large
register gain buying nothing audible. Scoped and left open rather than guessed
at.

### ⚠️ Why the per-voice verdicts here are NOT quotable

The per-voice sweep returns SYNTHESIS on voices 1 and 2 and SEQUENCER on voice 3,
all below their measured repeatability floors (audio 73/67/47 vs floors
90/96/95). **Do not quote that as a finding.** Two reasons, both from this
repo's own history:

1. **The driver render fails the voice-isolation guard.** Muting the other two
   voices leaves 8.6/9.1/13.2% shared energy on the Stage B side, against
   1.5/2.1/2.7% on the original — so those per-voice numbers are partly the same
   signal measured three times. `audio-tightness` prints `[WARN]` for exactly
   this and says the deltas are "usable but partly correlated".
2. **"Register-exact but SYNTHESIS on every voice" is a reading that has already
   been FALSIFIED once in this repo** — on MoN, where it turned out to be metric
   noise (`PATTERNS.md` F5b). The tool itself scores the rank test at **p = 0.25
   by chance** over 3 self-comparisons, which is not significance.

Per `docs/AUDIO_LISTENING_CALIBRATION.md`, onset match has **ordinal sensitivity
but no absolute gate**: a 99.8%-register-exact build scored 64.7% against an
85–91% original-vs-itself floor. Use these numbers against a *baseline build*,
never as pass/fail.

---

## Next steps

1. ~~**Resolve the parser residual**~~ — done: the wave program's arpeggio column
   owns the frequency register, and modelling it removes the residual.
   See *Register-level fidelity*. Reproduce the attribution with
   `pyscript/hardtrack_residual.py`: of 5,784 sequencer-pitch notes, 652 (11.27%)
   lose, and **630 of them are predicted frame-exactly** by the instrument's own
   arp program at a constant 3-frame note-on delay — while the same model also
   holds on 97.7% of the *kept* notes, which a model fitted to the losses would
   not. For **344 of the 652 the bare table value is never written at all**, even
   within 33 frames: the metric asks for something the player never does. 22
   notes (0.38%) are unexplained and recorded as such; 21 carry `$6F`, but the
   obvious cursor-continuation mechanism was tested and **falsified** (it
   explains 2).
3. ~~**Model the wave/pulse programs**~~ — done: `sidm2/hardtrack_synth.py`.
   The program-driven column went 2.64% → 100.00%.
4. ~~**Identify instrument fields 6, 7, 12**~~ — done, and reached
   independently by three passes: all three are the filter (program cursor /
   **initial cutoff** / resonance+mode+routing). Fields 8–11 are the vibrato
   engine. Detail: `docs/players/HARDTRACK_FILTER_AND_SLIDE.md`.
4a. ~~**Model the filter**~~ — done in v3.25.0, and with it the un-reset cursor
   question: `$D416`/`$D417` are byte-exact on 32,967 frames across all 33
   files, `$D418` on the 10 files that exercise it. `simulate_registers()` now
   leaves **no register group unpredicted**. The one thing still unverified is
   `$D418` bit 7 (siddump cannot see it) and the field-5 bit-4 re-arm gate,
   which this corpus does not exercise — see *Negative controls*.
4b. ~~**Map the second player build's variable block**~~ — done differently, and
   the answer reframed the item. A second `_RAM` table was the wrong shape: that
   build lays out its **code** differently too (`$11bf` is mid-instruction
   there), so no positional table can follow it, and a third would be needed for
   `Tribute_to_Laxity`. Instead the variables that matter are recovered from
   **their own consumers** (`HardTrackModule.voice_var_addrs`), which works on
   every build because it assumes no allocation at all.
   **Which variables matter was measured, not guessed**: ablating each seeded
   variable in turn on the 18 build-1 files shows the whole startup transient is
   `mode` (**1.67 points on its own**), then `freq_hi`/`freq_lo` (~0.2 each),
   then a vibrato tail. Five signatures cover all of them, and on build-1 files
   the addresses they yield agree with the `_RAM` layout on **18 of 18** — two
   recoveries sharing no inputs. Second-build frequency **99.15% → 99.68%**.
   ⚠️ **What is left there is NOT a seeding gap.** Restricting build 1 to the
   same five variables costs it only **0.03 points** (99.976% → 99.946%), so the
   other 38 cannot explain the rest. Following that lead found the real cause —
   see below.
5. ~~**The editor is the strongest lever left**~~ — **spent, and it was not.**
   `-HARDTRACK 1.PRG` was run under RetroDebugger and it boots (two-stage
   self-relocator: Polish banner → a `$0340` trampoline → shift `$0900-$FFFF`
   down to `$0801` → a second stub relocating a decruncher to `$0100`). But its
   main screen is unlabelled hex whose only words are `SPEED`, `SONG`, `OCT` and
   the title, and F1/F7 do not switch views — so it yields **no field names**.
   Every field identity in the table above came from the player's consumers
   instead. A "build a one-note tune and diff memory" pass could still work, but
   it is a slower route to answers that are already settled, not a shortcut.
   Gotcha if anyone does retry it: `retro_load` does **not** clear RAM and still
   reports `"loaded"`, so without a preceding `retro_reset` you debug the
   previous session's program. Compare a few bytes at the load address against
   the file before believing a load happened.
6. **Stage C: emit HardTrack's own programs instead of unrolled captures.**
   ⛔ **The FM prong of this was implemented and REVERTED in v3.25.0** — the
   8-program collapse is real and so is the 6 → 4 part win, but only at a
   7–19 point frequency cost; guarded losslessly it accepts 1.7% and buys
   nothing. See the boxed result below before restarting it.
   Stage B's part count is pure capture density, and `hardtrack_synth`'s
   register model now predicts what those captures contain. Emitting the
   player's looping wave/pulse programs directly is the lossless way to collapse
   parts — the same "structural, not trace" step MoN's Supremacy work names.

   **Scoped by measurement (v3.25.0).** Which cap actually forces the split, for
   `Love_tune_2` growing the window from frame 0:

   | window | bundles /63 | instr /32 | wave /256 | filter /256 | seq /120 |
   |---|---|---|---|---|---|
   | 0–1400 | 48 | 24 | 88 | 123 | 4 |
   | 0–1700 | **79 ✗** | 30 | 104 | 129 | 6 |
   | 0–2400 | **98 ✗** | **33 ✗** | 109 | 129 | 9 |
   | 0–5865 | **262 ✗** | **54 ✗** | 165 | 161 | 19 |

   **Bundles bind first**, instruments second; the wave, filter and sequence
   tables never come close and are not the lever. A bundle is an (FM, pulse)
   pair in the `$c0-$ff` command channel, so Stage C has to collapse *that*.

   ⚠️ **The two existing opt-in prongs do nothing here, and this was measured
   before assuming otherwise.** `MON_PULSE_CANON=1` and `MON_WAVE_CANON=1` leave
   the part count at 6 and every fidelity figure byte-identical. The reason is in
   `PULSE_CANON`'s own gate: for a shim without `hard_restart` it substitutes the
   per-instrument canonical only when `_pulse_unroll` makes it *identical* over
   the compare window — a strictly lossless condition that HardTrack's
   genuinely-per-note pulse sweeps rarely satisfy. There is nothing to collapse
   losslessly on the pulse side.

   So the lever is the **FM side**, and `BUNDLE_DECOMPOSE=1` prices it. A bundle
   is an (FM, pulse) pair, and the pair count tracks the FM side almost exactly:

   | window | pairs | distinct FM | distinct pulse |
   |---|---|---|---|
   | 0–1400 | 48 | 45 | 28 |
   | 0–1700 | **79** | **71** | 34 |
   | 0–2400 | 98 | 80 | 43 |

   **Why every existing lever fails, measured not assumed.** `MON_PULSE_CANON`
   and `MON_WAVE_CANON` target the wrong side and change nothing (above).
   `BUNDLE_TOL`, which merges bundles whose pitch contours differ by less than
   a tolerance, was swept **0, 2, 4, 8, 16, 32** and the effective count stayed
   at **79 at every setting**. Those 71 FM programs are not near-duplicates —
   they are genuinely distinct *in Hz space*, because a per-note Hz-delta unroll
   of the same arpeggio at a different base pitch is a different byte sequence.

   Which is precisely what a structural representation fixes. Over the same
   window, 286 note events use **10 distinct instruments** and only **8 distinct
   arp programs** once read as pitch-independent semitones from the wave
   program's arp column:

   | FM representation | distinct programs |
   |---|---|
   | per-note Hz-delta unrolls (today) | **71** |
   | structural semitone arp (Stage C) | **8** |

   A ~9× collapse on exactly the axis that binds — that is the prize, and it is
   the shape `arp_fm_program` already emits for MoN under `ARP_STRUCT`.

   ⚠️ **8 is the FM side alone, not the resulting bundle count.** Pairs are
   (FM, pulse) and the pulse side stays at 34, so the post-change count lands
   somewhere between 34 and 8×34 depending on how they pair up — likely
   pulse-dominated, comfortably under the 63 cap, but only the implementation
   settles it. `ARP_STRUCT` is also still env-gated for MoN pending its sibling
   prongs ("all three caps must drop for the part count to fall"), so this
   remains a project across a builder shared by seven players, not a flag flip.

   ### ⛔ IMPLEMENTED AND REVERTED (v3.25.0) — the prize is real, the trade is not

   The prong above was built and measured end to end, and it **does not pay**.
   Not reverted for difficulty: it works, and the collapse is exactly as
   predicted. It was reverted because the collapse is only available at a price
   this player's Stage B may not pay.

   The structural program was emitted from the wave program's arp column with
   semantics taken from `hardtrack_synth`'s `$1454` stepper (**not** from the
   table bytes — three readings taken from the bytes were all wrong: `$FE` is a
   stepper **FREEZE**, not a jump; `$FF` is the jump, target in the arp column;
   and an arp byte with bit 7 set is an **absolute note**, which is how every
   program in `Love_tune_2` opens — `$81`/`$cc`, a one-frame noise burst at note
   76). Emitted that way, **1,028 of 1,327 note events collapse to exactly 8
   distinct programs**, confirming the table above from the builder rather than
   from a static count.

   | build | parts | freq raw (v0/v1/v2) | audible |
   |---|---|---|---|
   | baseline (capture) | 6 | 92.8 / 92.9 / 95.1 | 88.2 / 77.3 / 91.5 |
   | structural, existing `tol` guard | **4** | **84.7 / 85.8 / 88.1** | 78.8 / 58.5 / 82.0 |
   | structural, exact guard (`tol = 0`) | 6 | 92.8 / 92.9 / 95.1 | 88.2 / 77.3 / 91.5 |

   The middle row is the whole finding. The part-count win is genuine — 6 → 4,
   with the binding cap moving off bundles onto instruments (32/32 in part 2) —
   but it costs **7–8 points of raw frequency and up to 19 of audible**, and
   per-voice misses roughly double (421 → 897, 412 → 832, 285 → 695). Those
   extra misses are **not** on the driver's note-on frame, so they are not the
   known unavoidable one; they are real. Two note-on phasings were tried (the
   absolute prologue held as base, and dropped) and both regress — **the phase
   is not the cost**, the substitution is.

   Guarded losslessly the trade disappears in the other direction: with
   `tol = 0` the fidelity is baseline to the frame, and the part count is
   **still 6**, because only **148 of 8,526** candidate substitutions survive
   the exact guard (**1.7%**). HardTrack's captured pitch almost never follows
   the pure table arp, since vibrato, `$63`/`$64` slides and detune ride on
   essentially every note — **which is the reason Stage B captures the synth
   engine instead of modelling it in the first place.** The prong asks this
   builder to go back to modelling the one dimension it deliberately stopped
   modelling.

   What would have to change first, for anyone picking this up: the structural
   arp needs to compose with the per-note modulation rather than replace it (a
   semitone arp *plus* the captured residual), because the residual is not
   noise — it is most of the pitch signal. The 8-program collapse is available
   the moment that exists. Until then a `tol`-guarded substitution is a
   fidelity regression wearing a part-count win.
7. **Rung 3 only now** (PLAYBOOK §4): an instrumented SF2II capture. ~~The
   listening pass~~ was run in v3.25.0 — see *Rung 4* above; it found no gross
   defect and a small real brightness/pitch-class difference, and is recorded as
   a baseline rather than a verdict. Rung 3 still needs the editor GUI.
