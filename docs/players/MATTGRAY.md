# Matt Gray — player RE + Stage A

**Status:** RE complete and Stage A shipped **for the Driller build only**.
Native Stage B: TODO. Not wired into `DriverSelector`.

Matt Gray wrote his own driver from scratch — it is **not** derived from
Hubbard or Galway — and refined it per game. Treat the map below as *one
confirmed build*, not a canonical layout for all 55 of his HVSC files.

---

## Why Driller first

Driller is #4 by remix count among his tunes, not #1, but it is the only build
with an **independently corroborated** memory map: the Codebase64 rough
disassembly's `init $15e0` / `play $0e46` match the HVSC PSID header exactly.
It also has only 2 subtunes against Last Ninja 2's 13.

Popularity ranking (Remix.Kwed.Org remix counts, all 4 result pages
aggregated): Last_Ninja_2 121, Tusker 15, Deliverance 9, Driller 8, Quedex 5 —
178 remixes over 13 tunes. Last Ninja 2 alone is 68% of his RKO output.
Corroboration: HVSC Top 100 lists only Last Ninja 2 (#12) and Driller (#54);
the 1997 sidmusic.org chart lists Last Ninja 2 (7 votes), Driller (4),
Quedex (2). **Tusker and Deliverance rest on the remix count alone.**

---

## Engine model (Driller build, load $0900 / init $15e0 / play $0e46)

`music_play` is a thin shim calling one shared `play_voice` three times with
X = `$00/$07/$0e`, so every per-voice state array has **stride 7**.

### Pattern byte dispatch (`read_note_or_ctrl`, $09e0)

| Byte | Meaning |
|------|---------|
| `>= $fd` | set duration; next byte is the value. **Sticky** — applies to all following notes until changed |
| `$fc nn` | slide/portamento type 2, rate `nn` |
| `$fb nn` | slide/portamento type 1, rate `nn` |
| `$fa nn` | set instrument `nn` (the driver multiplies by 8 for the record offset) |
| `$00` | **rest / note-off** — the driver restores the previous note and ANDs the gate bit out |
| `$01-$f9` | note; index into the 96-entry freq table |
| `$ff` | end of pattern (consumed *after* a note, not in this dispatch) |

A `$fb`/`$fc` slide applies **only to the note that immediately follows it**:
the driver zeroes the effect slot at the top of every fetch (`L09b6`).

### Track (orderlist) bytes

`$ff` restart this voice's track at 0 · `$fe` stop the tune · else pattern number.

### Instruments — TWO parallel 8-byte tables

Not one 8-byte record: the driver reads `instr_A0` ($0ea5) **and** `instr_A1`
($0f55) for the same instrument index, so an instrument is 16 bytes split
across two tables.

| A0 | Use | A1 | Use |
|----|-----|----|-----|
| 0 | pulse: hi nibble → `$d402`, lo nibble → `$d403` | 0 | automatic slide rate (nonzero = enabled) |
| 1 | sustained waveform (ANDed with the gate mask) → `$d404` | 1 | slide step reload period |
| 2 | AD → `$d405` | 2 | waveform for the two-frame swap / drum path |
| 3 | SR → `$d406` | 3 | rate used when A1[4] auto-starts an effect |
| 4 | per-frame pulse-width delta (0 = no PWM) | 4 | nonzero auto-starts a slide effect on every note |
| 5 | arpeggio: lo nibble = table index, hi nibble = length | 5 | drum/effect repeat length |
| 6 | attack-frame waveform | 6-7 | unused in this build |
| 7 | flags: bit0 drum path, bit1 pulse reset, bit2 two-frame swap | | |

### Tempo

`tempo_ctr` counts down once per frame and reloads with `tempo` when it goes
negative, so **a row tick happens once every (tempo + 1) frames**. On a tick
each voice decrements its own duration counter and fetches the next event when
that counter goes negative. A duration byte D holds a note for **D + 1 ticks**.

Driller: `tempo = 3` → 4 frames/row. Verified empirically — the opening
duration of `$3f` gives onsets on frames 1, 257, 513, 769… (64 ticks × 4).

---

## Locating the tables

Every address is recovered by **backward dataflow from the code operands**,
never from absolute addresses, so the parser survives relocation. Each site is
an `LDA abs,y` (opcode `$b9`) at a fixed offset from `play_voice`, and
`play_voice` itself is read from the `JSR` operand inside the `music_play`
shim. `MattGrayParser.verify()` asserts the opcode at all 14 sites and raises
rather than guessing on an unsupported variant.

Table sizes come from adjacency: `pattern_hibytes - pattern_lobytes` = pattern
count, `instr_A1 - instr_A0` / 8 = instrument count, and the tune count from
the track-pointer lo/hi tables.

---

## Fidelity — Driller, 12,000 frames (240 s)

Measured by `bin/mattgray_validate.py` against `siddump_complete.py`.

| Bucket | n | onset | pitch |
|--------|---|-------|-------|
| **Plain instruments (headline)** | **1513** | **100.00%** | **100.00%** |
| Pitch-modulated (informational) | 468 | 100.00% | 65.38% vs base |

**Read the split carefully.** A "plain" instrument is one with no arpeggio
(A0[5]), no drum path (A0[7] bit0), no automatic slide (A1[0]/A1[4]) *and* no
`$fb`/`$fc` slide attached to that note. On a pitch-modulated instrument the
player rewrites `$d400` **every frame**, so an onset there matches whatever the
parser predicts — that bucket **cannot falsify the timing model** and is
reported separately rather than claimed. Its base-pitch mismatch is the synth
side (Stage B), not a sequencer error.

Two measurement traps hit during this work, both worth remembering:

1. **siddump's default display hides real writes.** It prints `....` when a
   register's *value* did not change, so Driller's `42 3b 3b 42 3b 3b` pattern
   (a note re-triggered at the same pitch) looked like 30 parser misses that
   were not misses. `bin/mattgray_validate.py` passes `-w`/`--written`
   (write-hook precision) for exactly this reason — do not remove it.
2. **The first "pitch miss" was the parser being right.** Pattern 5 is
   `fa 0e fd 3f 2f 2b 2e fc 20 2a ff`; note `$2a` was off by exactly `+$20`,
   the `$fc` slide rate. Slides come from the *pattern stream* as well as the
   instrument, so the modulated/plain classification is per-note, not
   per-instrument.

---

## Stage A

`bin/mattgray_to_sf2.py` transpiles onto a stock **Driver 11** SF2 via the
shared `galway_driver11_emitter`.

Carried over exactly: notes, note order, durations, tempo, and per-instrument
ADSR / waveform / pulse setup. **Not modelled (Stage B):** pitch slides,
arpeggios, pulse-width sweep, the drum path. Those instruments still sound,
they just hold a static timbre.

Driller loops at **8320 rows = 33,280 frames = 665.6 s**, all three voices
wrapping on the same tick despite different track lengths (117/82/109 entries)
— a good internal-consistency check. That exceeds the SF2II memory wall
(~27,650 play-calls), so the converter **splits into parts** rather than
truncating silently:

```
py -3 bin/mattgray_to_sf2.py <file.sid> out/Driller_stageA.sf2
  -> Driller_stageA_part01.sf2  rows 0-6000     4113 note rows
  -> Driller_stageA_part02.sf2  rows 6000-8320  1390 note rows
```

Verified structurally: the packed sequences unpack back to the row grid
byte-exactly (6000/6000 rows per voice, 0 mismatches), 41 sequences against the
120 cap, none over SF2II's 960-event `Unpack` limit.

### Editor play-test (real SID Factory II)

Run with `pyscript/blackbird_crash_probe.py`'s `probe_once()` — despite the
name, that function is player-agnostic (only its combo-schedule analysis is
Blackbird-specific). It loads the file in the stock editor, presses F1, and
screenshots the editor's own **"Playing time"** readout as proof the play
actually happened; a probe that silently failed to deliver F1 would otherwise
also report SURVIVED.

| Trial set | Window | Coverage | Result |
|-----------|--------|----------|--------|
| part01 × 3 | 45 s | ~9% of 480 s | 3/3 SURVIVED |
| part02 × 3 | 45 s | ~24% of 186 s | 3/3 SURVIVED |
| part02 × 1 | 195 s | **100%** of 186 s | SURVIVED |
| part01 × 1 | 492 s | **100%** of 480 s | user-confirmed playing (see below) |

The scripted 492 s part01 trial returned `CRASHED`, and that verdict is **void**:
`probe_once()` decides by checking whether the process is still alive after the
window, so a human closing the editor is indistinguishable from a crash — and
that is what happened. No proof-of-play screenshot was written, which is the
same signature either way. The user instead confirmed part01 directly, watching
it play through **twice** in the editor without incident.

**Probe limitation worth fixing** (it affects the Blackbird play-tests too,
same oracle): "process absent" is treated as "crashed" unconditionally, so any
long-window trial is silently corrupted if someone touches the window. Recording
the process *exit code* would separate a clean close from a crash; screenshotting
periodically during the window rather than only at the end would also leave a
partial timeline behind.

Screenshots confirm the module loads as **Driver 11.00**, tempo `03`, all 22
instruments present, and — in part 2 — real decoded music on all three tracks
(`F#2 / A#3 / C#2`, `G-5 / G#5 / A-5`, `F#1 / D#1 / E-1`) with the primed
instrument selects (`a000 / a006 / a00b`) on row 0, which is the mid-song
window-start handling working as intended. Part 1's visible rows show voices 1
and 2 sustaining (`+++`) through the intro drone while voice 3 carries the
line — exactly what the 64-tick opening durations predict.

**What this does and does not establish.** It establishes that both parts load
and play to completion in the real editor without crashing, which is the one
hazard class no offline tool in this repo can see. It does **not** establish
that they *sound* like the original — that needs an ear on an A/B, and the
Stage A output is knowingly missing the slide/arp/PWM/drum engine, so it will
not match. Timbre fidelity is a Stage B claim, not this one.

HVSC songlengths list Driller at 8:41 / 10:21 against the measured 11:05 loop.
The order of magnitude agrees; the exact loop point does not, and HVSC's
per-subtune split is itself suspect here (see below).

---

---

## Last Ninja 2 — SOLVED (12 of 13 subtunes, 100% / 100%)

LN2 is a **relocating compilation**. `play=$4002` is all zeros in the file
because `init $3f40` copies the selected subtune's self-contained player+data
blob to `$4000` first. Thirteen blobs, confirmed by thirteen separate
`(C)1988 MATT GRAY` strings. The copy loop is fully decoded
(`relocating_subtunes()`): source lo/hi at `$3f80`/`$3f8d`, tail at `$3f9a`,
pages at `$3fa7`, length = `pages·256 + tail`.

Once relocated it **is** the same engine: `$4002` is the byte-identical
`music_play` shim and `play_voice $4012` opens with Driller's exact prologue.
Beyond that the 1988 build shares only **one byte** with Driller, so fixed
offsets don't transfer and `locate()` finds the tables by signature instead.

### The format difference that mattered

Locating the tables was **not** enough. The first decode scored 11-22% pitch
while producing entirely sensible pattern, instrument and note counts — nothing
announced itself as broken. The cause was the duration encoding:

| | Duration | Note range |
|---|---|---|
| **Driller (1987)** | `$fd nn` — a two-byte control code | `$01-$f9` |
| **Last Ninja 2 (1988)** | `$70 + n` **in the note stream**, sticky | `$01-$6f` |

```
$419d: cmp #$70
$419f: bcc $41a9      ; < $70 -> a real note
$41a1: sbc #$70       ; >= $70 -> duration = byte - $70
$41a3: sta $4460,x    ;            (sticky, exactly like Driller's)
$41a6: jmp $4157      ; consume and fetch the next byte
```

The parser was reading those duration bytes as notes. `_duration_base()` now
detects the split from the unmistakable `cmp #N / bcc / sbc #N` idiom in real
code, and `song.duration_base` selects the decode (`None` = Driller style).

### Result (siddump, 1500-frame sweep, plain instruments)

**12 of 13 subtunes at 100% onset and 100% pitch.**

| sub | n | | sub | n | | sub | n |
|---|---|---|---|---|---|---|---|
| 0 | 131 | | 5 | **3** | | 10 | 167 |
| 1 | 45 | | 6 | **1** | | 11 | 157 |
| 2 | 35 | | 7 | *refuses* | | 12 | 190 |
| 3 | 210 | | 8 | 209 | | | |
| 4 | 376 | | 9 | 163 | | | |

Longer windows confirm it: subtune 1 at 3000 frames is 303/303 onset and
303/303 pitch; subtune 3 is 403/403 and 403/403.

**Caveats, stated plainly.** Subtunes 5 (n=3) and 6 (n=1) are *not* evidence —
a one-note sample proves nothing and those need a longer window before anyone
quotes them. Subtune 7 still refuses with a one-byte overrun at the blob
boundary and is unsolved. And as everywhere here, the headline covers the
sequencer on plain instruments only; the synth side remains Stage B.

### The signature locator (`locate()`)

Used when the Driller fast path's fixed offsets don't verify. It walks real
code by recursive descent from `play_voice` (a flat byte scan is not adequate —
the player interleaves code and data, so a linear sweep invents instructions out
of table bytes), collects every `LDA abs,y`, then matches:

- **track pointers** — 6 consecutive sites whose operands step by 2
- **tune_tempo** — the next distinct table after those 6
- **freq lo/hi** — operands exactly 96 apart, confirmed by an octave-doubling
  check on the hi bytes
- **instruments** — two operand *clusters* (the driver reads many fields of one
  record) whose bases differ by a multiple of 8
- **patterns** — located **last**, from operands no other table has claimed.
  Done earlier it reliably mis-fires: two adjacent instrument-field reads
  (LN2's `$461a`/`$4620`, six apart) look exactly like a lo/hi pointer pair for
  a six-pattern song.

## Gotchas

- **`load = 0`.** Driller's PSID header declares load `$0000`, so the real load
  address is the first two bytes of the data block. Getting this wrong makes
  every table operand decode to garbage while the file still *looks* parseable.
- **`music_init` ignores the accumulator.** It is literally
  `lda #$01 / sta $0d0f / rts`, so the PSID's 2 subtunes both play tune 1.
  HVSC nonetheless lists two different songlengths for them.
- **Tusker's `play=$e002`** sits under KERNAL ROM, unlike every other build
  examined ($0e46/$4002/$4da1/$4bb3, all RAM). Expect a banked or relocated
  player; do not assume it behaves like Driller.
- **Hunter's Moon is a co-credit.** Its PSID author field reads
  `Matt Gray & Martin Walker`. It is the only co-credit among the 55 files.

---

## Files

| Path | What |
|------|------|
| `sidm2/mattgray_parser.py` | parser + frame-accurate sequencer simulation |
| `bin/mattgray_validate.py` | onset/pitch validation vs siddump (plain/modulated split) |
| `bin/mattgray_to_sf2.py` | Stage A → Driver 11 SF2, with part windowing |
| `pyscript/test_mattgray_parser.py` | 14 tests (skip cleanly without HVSC) |

## Next

1. Play-test the Stage A parts in real SID Factory II (the only thing that
   catches SF2II-only hazards).
2. Generalise the locator past Driller — the other 54 files are per-game
   builds; `verify()` will refuse them loudly rather than mis-parse.
3. Stage B native driver: the slide engine ($fb/$fc + A1[0]/A1[4]), the
   arpeggio table, the A0[4] pulse sweep, and the A0[7] bit0 drum path.

## Sources

- Codebase64 Driller disassembly — https://codebase64.net/doku.php?id=base:matt_gray_-_driller
- SIDin #2 ("Matt Gray's Driller music routine") and SIDin #3 (fingerprinting
  his engine via its portamento-flag check) — both in the TDZ C64 knowledge base
- TDZ knowledge card `matt-gray` (also records a verified reassembly of the
  separate *Dominator* build, from dmx87's `c64_6581_sid_players`)
