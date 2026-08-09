# HardTrack Composer — SID → SF2 support

**Status: RE stage only.** The module format is decoded, relocation-safe, and
validated against siddump. There is **no converter yet** — no Stage A (Driver 11)
and no Stage B (native driver). Nothing is wired into `DriverSelector`.

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

**Code:** `sidm2/hardtrack_parser.py` · validator `pyscript/hardtrack_validate.py`
· tests `pyscript/test_hardtrack_parser.py` (21).

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
  ...      instrument block: 13 parallel 32-byte tables
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

Instrument byte: `$00` = *keep the current instrument*; otherwise `& $1F` selects
one of 32. That is why the editor writes `$80` for "instrument 0" — a literal `$00`
would mean "no change".

### Tempo

One global divider, self-modified in the play routine, reloaded from an 8-entry
per-subtune speed table. **A song row lands every `speed+1` frames.** Within a
beat the player uses the counter value as a phase selector: `0` = read a row,
`1` = decrement the note duration, anything else = run the synth programs only.

### Instruments — 13 parallel 32-byte tables

Field *k* of instrument *n* is at `instrument_base + k*32 + n`. Confirmed roles:

| # | Role |
|---|---|
| 0 | attack/decay → `$D405` |
| 1 | sustain/release → `$D406` |
| 2 | pulse width: high nibble → `$D403`, low nibble → `$D402` |
| 3 | wave-program start cursor |
| 4 | pulse-program start cursor |
| 5 | **flags** — bit 7 = program drives frequency absolutely, bit 4 = hard restart, bits 0–1 = mode |
| 8 | low nibble + high nibble ×2 → two synth counters |
| 9 | copied to the per-voice parameter block |
| 10, 11 | synth-program parameters |

Fields 6, 7 and 12 are **not yet identified** and are deliberately left unnamed in
`Instrument.raw` rather than guessed at.

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
| **sequencer-pitch** (instrument field 5 bit 7 clear) | 5,846 | **88.39%** |
| **program-driven** (bit 7 set) | 1,074 | **2.61%** |

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

## Next steps

1. **Stage A** — transpile to an editable Driver 11 SF2 through the shared
   `GalwayDriver11Song` + `galway_driver11_emitter` IR. The parser already yields
   what that needs (notes, durations, instruments, per-voice orderlists).
   Watch the caps in [PLAYBOOK.md](PLAYBOOK.md) §3.
2. **Resolve the residual** — instrument the `$63`/`$64` slide commands and
   confirm (or refute) the hypothesis above before quoting a higher number.
3. **Wave/pulse/filter programs** — `$FF`-terminated `[value][delay]` step lists
   with a `$80 <index>` jump; the global filter sweep is a separate song-level
   program whose cursor the player **does not reset in `init`** (it is
   self-modified code, so a ripped file carries the cursor value it was saved
   with). Worth confirming on hardware before relying on it.
4. **Identify instrument fields 6, 7, 12.**
5. **The editor is the strongest lever left** — run `-HARDTRACK 1.PRG` under
   RetroDebugger, build a one-note tune, and diff memory. That resolves the
   remaining fields far faster than more static disassembly.
