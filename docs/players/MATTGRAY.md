# Matt Gray — player RE + Stage A

**Status:** RE complete and Stage A shipped for **Driller, Last Ninja 2 (13 subtunes) and Tusker (4 subtunes)** — 18 tunes, all at 100% onset / 100% pitch on plain instruments.
**Native Stage B: SHIPPED** (`bin/build_mattgray_native_song.py`) — **37 tunes
across 8 games**: Last Ninja 2, Driller, Tusker, and (after the stride and
`psid_song` fixes) Maze_Mania, Motocross, KGB_Superspy, Hyperion_2 and
Hunters_Moon_Remastered. **6 of the 37 are 1-3 second jingles** whose
percentages carry almost no information, and **`Motocross` sub 4 fails
outright** — see *The corpus after the fix*. For Last Ninja 2 —
12 of 13 subtunes build, **98.16% audible per-frame frequency** (n=172,745),
**16 of 36 voice-scores at exactly 100.0%**; subtune 7 is refused, not mis-built.
See *Stage B* below. Not wired into `DriverSelector`. Current headline figures:
`docs/reference/ACCURACY_MATRIX.md` (canonical; verified to match this doc 2026-08-09).

Matt Gray wrote his own driver from scratch — it is **not** derived from
Hubbard or Galway — and refined it per game. Treat the map below as *one
confirmed build*, not a canonical layout for all 55 of his HVSC files.

### Three denominators, don't conflate (the SDI 343-348-324 trap, re-measured 2026-08-21)

Three different questions over the same 55 top-level `SID/Gray_Matt/*.sid`
files (the 2 `Worktunes/` files are not HVSC-catalogued and are excluded from
the 55):

| Question | Count | How |
|---|---|---|
| Does `native_dispatch.probe("mattgray", path)` **accept** it? | **13/55** | `locate()` finds every table by signature; raises otherwise |
| Does `parse_sid()` **decode** it (tables + sequencer walk)? | **11/55** | the 2 accept-but-not-decode files (`Pogo_Stick_Olympics`, `Warriors`) fail on a pattern-with-no-`$ff`-terminator bug — open separately, see `mattgray-pattern-no-ff-terminator` |
| How many Stage B **artifacts** are on disk? | **8 songs / 37 song×subtune / 78 built `.sf2` parts** | `out/mattgray_native/*.sf2`, one game per song, part-split for length |

These are not disagreeing answers — accept ⊇ decode ⊇ built, each a stricter
gate than the last. Of the 11 that decode, 36 of the resulting 37 built parts
use `layout='signature'` and 1 (`Driller` sub 1) uses `layout='driller'`, the
fast path — see *The `signature` decode is no longer unverified* below for
what "1 of 55 HVSC files located by the fast path" means precisely.

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
(the figure once quoted here, ~27,650 play-calls, was never derivable -- see R20 below), so the converter **splits into parts** rather than
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
| **1part × 3** (R20b) | 700 s | **105%** of 665.6 s — song **+ loop** | **3/3 SURVIVED**, clock **11:41** |
| part01 × 3 (R20b control) | 700 s | interleaved control arm | 2 SURVIVED + 1 CLOSED, 0 crashes |

The scripted 492 s part01 trial returned `CRASHED`, and that verdict is **void**:
`probe_once()` decides by checking whether the process is still alive after the
window, so a human closing the editor is indistinguishable from a crash — and
that is what happened. No proof-of-play screenshot was written, which is the
same signature either way. The user instead confirmed part01 directly, watching
it play through **twice** in the editor without incident.

**Probe limitation worth fixing** — ✅ **all fixed** (R23, then a second pass on
2026-07-30; affected the Blackbird play-tests too, same oracle):
- "process absent" was treated as "crashed" unconditionally → now classified by
  **exit code**, so a clean close reads `CLOSED`, not `CRASHED`.
- The verdict never checked that the trial *started* → now gated on SF2II's own
  "Playing time" clock **advancing**, with a new `NOPLAY` verdict for a lost `F1`.
- The proof-of-play screenshot was a screen-**region** grab, so it captured
  whatever window was on top of the editor → now `PrintWindow`, which is immune
  to occlusion and focus.
- Deaths are timestamped (1 s polling), so a crash reports *when*.

⚠️ **Never run `pytest` while a play-test is in flight.** Until 2026-07-30
`pyscript/conftest.py` killed **every** `SIDFactoryII` process on the machine at
the end of any pytest session — a TerminateProcess whose exit code reads as
CRASHED. It faked a *100% crash rate on both arms* of a Driller A/B, two-part
build included. Both cleanup paths are now scoped to editors the session itself
started, but the ordering rule is still worth keeping.

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

### The fourth control code ($f9)

One more branch sat between the instrument code and the duration split:

```
$418d: cmp #$f9
$418f: bcc $419d      ; < $f9 -> the $70 duration / note split
$4191: iny            ; >= $f9 -> consume a PARAMETER byte
$4195: lda ($fe),y
$4197: sta $44ba,x    ; store it; NO note is played
$419a: jmp $4157      ; continue fetching
```

`$f9` is a two-byte code that plays nothing. Because `$f9 >= $70`, missing it
was doubly wrong: the parser read `$f9` as a *duration* and then played its
parameter byte as a *note*. The signature was one invented note per occurrence
followed by immediate realignment — which is why pitch stayed at 100% while
onset drifted, and why only the sparsest voice showed it.

Full dispatch order for the 1988 build: `>= $fb` slide · `>= $fa` instrument ·
`>= $f9` parameter · `>= $70` duration · else note.

### Result — 13/13 subtunes, 6000-frame sweep, plain instruments

**Every subtune: 100% onset and 100% pitch.**

| sub | n | sub | n | sub | n |
|---|---|---|---|---|---|
| 0 | 922 | 5 | **19** | 10 | 1000 |
| 1 | 692 | 6 | **1** | 11 | 699 |
| 2 | 334 | 7 | 230 | 12 | 836 |
| 3 | 1003 | 8 | 654 | | |
| 4 | 1070 | 9 | 774 | | |

**Caveats.** Subtune 6 reaches n=1 even at 6000 frames (753 of its notes are on
pitch-modulated instruments) and subtune 5 only n=19 — those two are *not*
evidence at that sample size, whatever the percentage says. Subtune 7's final
pattern is genuinely truncated by the relocating copy; `_read_pattern` returns
it short and reports `song.truncated_patterns`. As everywhere, the headline
covers the sequencer on plain instruments; the synth side is Stage B.

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

## Stage B — native, trace-driven (v3.26.0)

`bin/build_mattgray_native_song.py`. **No new driver**: a MON-compatible shim
feeds `build_mon_native_song.build_native_song`, the same engine behind
Hawkeye / Hubbard / DMC / Sound Monitor / SDI / FC / HardTrack.

### The four engines this did NOT have to reverse-engineer

The old *Next* list called Stage B "the slide engine (`$fb`/`$fc` +
A1[0]/A1[4]), the arpeggio table, the A0[4] pulse sweep, and the A0[7] bit0
drum path" — four more engines to RE. **None was needed.** Stage B CAPTURES the
synth side per frame from the original's own siddump, so whatever those engines
did is what the driver replays. Only the SEQUENCER crosses the shim boundary —
notes, durations, instrument indices — which is exactly the part Stage A had
already validated to 100%. Pinned by
`test_the_shim_does_not_model_the_synth_engine`.

### Result — Last Ninja 2, 12 of 13 subtunes, full song length

Per-frame frequency vs the original, **audible** column (frames where the
ORIGINAL's gate is on); `raw` includes gate-off frames nothing can hear.

| sub | v0 | v1 | v2 | | sub | v0 | v1 | v2 |
|---|---|---|---|---|---|---|---|---|
| 0 | **100.0** | 99.5 | 99.8 | | 6 | 98.7 | 98.5 | 97.4 |
| 1 | 96.7 | 99.9 | 95.0 | | 8 | **100.0** | **100.0** | 99.9 |
| 2 | **100.0** | **100.0** | **100.0** | | 9 | **100.0** | **100.0** | **100.0** |
| 3 | 94.6 | 98.8 | **100.0** | | 10 | **100.0** | **100.0** | **100.0** |
| 4 | 98.4 | **100.0** | 98.7 | | 11 | 98.7 | 94.9 | **100.0** |
| 5 | 99.2 | **100.0** | 92.4 | | 12 | 97.4 | 85.8 | 98.0 |

**n-weighted mean 98.16%** over 172,745 audible frames; **16 of 36 voice-scores
at exactly 100.0%**. Quote raw AND audible, never one alone.

### Driller and Tusker build too (v3.26.0)

The shim is not Last-Ninja-specific -- the other two games needed nothing but a
run. Every one of these fits its **full ~120 s in a single part**.

| tune | v0 | v1 | v2 |
|---|---|---|---|
| Driller sub 1 | **100.0** | 96.0 | 89.4 |
| Tusker sub 0 | 99.2 | 97.7 | 89.6 |
| Tusker sub 1 | 99.8 | 99.3 | 88.7 |
| Tusker sub 2 | **100.0** | 99.9 | 95.5 |
| Tusker sub 3 | 99.2 | 98.0 | 99.0 |

Driller subtune 0 is refused by the parser (`address $0000 outside image`),
which is consistent with the documented gotcha that its PSID declares 2
subtunes while `init` forces tune 1 for both. **16 tunes build across the three
games.**

⚠️ Voice 2 is the weak voice on Driller and Tusker (88.7-95.5) where it is not
on Last Ninja 2. Unexplained, and recorded as such rather than averaged away.

### Rung 3 — the instrumented SF2II capture: **PASSES**

`pyscript/sf2ii_vs_wrapper.py`, comparing the editor against **our own wrapper
render** (both carry the same driver and data, so this isolates editor-vs-us
from conversion-vs-original):

| build | freq | waveform | pulse | n |
|---|---|---|---|---|
| `Last_Ninja_2_sub09_part01` | **100.0%** | **100.0%** | **100.0%** | 900 / 788 / 255 |
| `Last_Ninja_2_sub12_part01` | **100.0%** | **100.0%** | **100.0%** | 516 / 708 / 900 |

At offset 0, both. The second is deliberately the **weakest** subtune (voice 1
scores 85.8% against the original): rung 3 tests whether the editor executes
our build faithfully, so it should pass regardless of fidelity — and it does,
which places subtune 12's residual on the conversion side, not the editor's.
The first Matt Gray build ever to clear rung 3.

### Rung 4 — the first listening pass, and the defect it found

No Matt Gray build had ever had one. `Last_Ninja_2` subtune 0, 25 s, original
vs the Stage B render.

**Whole-file features are very close** — level identical (−17.8 dBFS both,
+0.2 dBA), centroid **+10.3 Hz**, rolloff +33.7 Hz, flatness −0.009, pitch
classes essentially unchanged (largest shift 0.020). For scale, HardTrack's
first pass was −99 Hz on centroid.

**But the onset match is 62.1%** (157 of 253) — and here that number is
interpretable, because the floor was measured properly rather than assumed:

| comparison | matched |
|---|---|
| original vs **itself** | 100.0% (trivially — same file) |
| original vs **itself delayed exactly one frame** | **100.0%**, 0 missing, 0 extra |
| original vs **Stage B** | **62.1%**, 96 missing, 69 extra |

The middle row is the one that matters. The render sits one frame late, and the
tool's offset removal handles that perfectly, so **the 38-point gap is not
alignment** — it is real.

#### The defect: the voice-off waveform is not reproduced

Every per-voice register is byte-exact over **gate-on** frames — waveform,
pulse, frequency **100.0% on all three voices** (n=2,636), and AD/SR 100.0% on
all 1,248 frames. Which is exactly why this was invisible: the builder's
fidelity report scores **frequency on gate-on frames and nothing else**.

Scored over **all** frames instead:

| voice | waveform | pulse | freq |
|---|---|---|---|
| 0 | **84.6%** | 100.0% | 84.6% |
| 1 | **84.6%** | 100.0% | 83.6% |
| 2 | 100.0% | 100.0% | 66.7% |

The whole waveform residual is one substitution: the original writes **`$00`**
— no waveform bits at all, so the oscillator is silent — on **192 frames per
voice**, and the render writes **`$40`** (pulse, gate off) instead. The
original goes quiet; ours keeps releasing a tone.

Corroborated independently by the feature summary, which measures the same
thing from the audio without knowing about registers: **silence fraction 0.2%
(original) → 0.0% (ours)**. Our render never falls fully silent.

This is the same *class* as HardTrack's `$D418` passband defect — a real
audible difference that no headless number in this builder's own report could
move, found only by listening. The likely fix is the shared driver's existing
`RELEASE_WF` path (a per-instrument release waveform written verbatim on
gate-off frames, instead of `program & $fe`), which Sound Monitor already uses;
it is **not** attempted here.

#### The waveform half is FIXED (`release_wf`)

The driver already had the mechanism — `RELEASE_WF`, a per-instrument release
waveform written verbatim on gate-off frames instead of `program & $fe`, which
Sound Monitor uses. It is a **shim flag, not a driver change**.

The release byte is **derived from the trace, not from a flag bit**
(`release_waveforms()`): for every decoded note, walk from its gate fall to the
next note on that voice and take the modal gate-off waveform. An instrument
whose releases are never observed keeps the driver's default rather than being
assigned a guess, and a near-tie (< 60%) is rejected for the same reason. It is
genuinely per-instrument — sub 0 derives `$40`/`$80`, sub 12 derives `$00`.

**Waveform over ALL frames: 84.6% → 100.0% byte-exact on all three voices.**
No headline regression on the three subtunes re-checked (0, 9, 12).

#### ⚠️ The audio gap is NOT closed, and the cause is not established

Onset match moved only **62.1% → 63.6%**, and silence fraction is still
0.2% → 0.0%. A direct waveform correlation of the two renders — with the
correlator validated first (1.0000 against itself, 0.9759 against a one-frame
delayed copy, recovering the offset exactly) — gives **0.579** at a stable
−2.18 frame offset, with no drift across 11 windows. So the audio really does
differ, and it is not a timing artifact.

That sits against gate-on frames being byte-exact on **every** register:
waveform, pulse, frequency, AD, SR, and the global filter/volume. The
difference is confined to **gate-off frames**, where our render writes freq
`$010C` and pulse `180` against the original's `0000`/`000` — a voice in
RELEASE is still sounding, so that is the leading candidate and the next thing
to test.

One metric to distrust on the way: raw siddump rows agree only 37.7%, but that
compares *write patterns* rather than state — siddump prints `...` for a
register not written that frame, and our driver writes a different set each
frame. Fill-forward state is the fidelity measure; raw-row equality is not.

### Rung 4, part 2 — the gate-off freq/pulse test

#### The named candidate was WRONG, and the real cause is the REST row

The candidate above ("a voice in RELEASE is still sounding — our render writes
freq `$010C` and pulse `180` against the original's `0000`/`000`") is
**falsified**. Those frames carry waveform **`$00` on BOTH sides** once
`release_wf` lands: no waveform bits, so the oscillator is silent and a
frequency written to it cannot be heard. Counting the frames where our
oscillator sounds while the original's is silent gives **0 on all three
voices** — the thing the last commit went looking for is not there.

What *is* there appears as soon as every sounding gate-off run is attributed to
the event that owns it. Both builds are scored over **one common 2,780-frame
window** below, because the merge moves the part split — "part 1" is a
different span on each side and the two cannot be compared as such:

| the run lives inside | before | after |
|---|---|---|
| a NOTE's own span | 138 exact, 0 wrong | 138 exact, 0 wrong |
| a REST | **0 exact, 236 wrong** | **236 exact, 0 wrong** |

Before, every wrong run was ours **frozen on one constant**, and the wrong
frames are not scatter: **76% are an exact octave relation** to the original
(`x2` 347 frames, `/2` 290, `x4` 172, `/4` 116). The original is
**arpeggiating through the release**; ours held a single value.

One line of the shared builder explains it. `build_mon_native_song` emits a
rest as bare GATE-OFF rows carrying **no wave, pulse or FM program**, so the
pitch freezes at whatever the previous note left in the register — correct for
an engine whose release is quiet, wrong for one whose arpeggio keeps stepping.

#### The fix: merge a sounding rest into the note before it

`merge_sounding_rests()` — a **shim-layer** change: no driver change, no new
engine, and nothing added to the four synth engines Stage B deliberately does
not model. A rest the original still sounds through is absorbed into the
preceding note, which puts its frames back inside the per-note capture that is
already reproducing every note-internal run exactly.

Two guards, both of which cost nothing and prevent a wrong merge:

- only rests the original **actually sounds through** — waveform bits set AND a
  non-zero frequency. A rest the player silences with `$00` is left alone;
  nothing is heard through it, so a capture would only cost program space.
- only while the note stays inside **`FM_CAP`**. Past that `fm_program_for`
  freezes anyway, so the merge would buy nothing and still cost the space.

`MG_NO_REST_MERGE=1` restores the old behaviour for anyone re-checking.

**Every register, all frames** (sub 0, the same common window, 2,790 frames,
best whole-render offset -1 on both sides):

| | v0 freq | v1 freq | v2 freq | v0 pulse | v1 pulse | v2 pulse |
|---|---|---|---|---|---|---|
| before | 89.24 | 82.57 | 70.17 | 82.57 | 75.26 | 85.59 |
| after | **92.69** | **92.90** | **100.00** | **84.08** | **88.60** | **100.00** |

Waveform, AD/SR, `$D416`/`$D417` and `$D418` are **100.00% on both sides**, and
the whole remaining freq residual is the inaudible class above — 192 frames
each on voices 0 and 1 where both sides carry waveform `$00`. Voice 2 has none
of them, which is why it lands on an exact 100.00%. Scored the way that matters,
**audible** gate-off frames carrying the wrong frequency go
**93 / 288 / 832 → 0 / 0 / 0** over the common window. Not "almost none": none.

#### The whole corpus, built both ways

Judged on every tune that builds, not on the one it was developed against --
17 files (sub 7 still refused), 51 voices, **719 rests merged**:

| column | up | down | unchanged | frame-weighted mean |
|---|---|---|---|---|
| `raw` (includes gate-off frames) | **13** | 2 | 36 | **+1.50 pp** |
| `audible` (gate-on frames only) | 1 | 5 | 45 | -0.011 pp |

Largest `raw` gains: sub 2 v0 **+28.4**, sub 4 v1 +13.9, sub 0 v2 +13.7, sub 2
v2 +9.4, sub 9 v1 +5.8. The two `raw` losses are -0.3 and -0.1. The five
`audible` losses are -0.1 or -0.2 each, second-order: a longer note changes
which canonical program the instrument-cap optimizer picks and where the part
boundary falls, not what the driver plays on a gated-on frame.

**The merge is a strict no-op on Driller and Tusker sub 0** -- neither has a
rest the original sounds through, so their weak voice 2 (89.4 / 89.6) is a
*different, still-unexplained* defect and this fix does not touch it.

⚠️ **Cost, stated rather than buried: `Last_Ninja_2` sub 2 and `Tusker` sub 1
now need 2 parts where they needed 1.** That is the price of carrying the
release contours, and it is not waste: a tighter guard (merge only where
freezing would actually be *wrong* -- the original's freq/pulse during the rest
differs from the value we would freeze at) was tried and keeps **100%** of the
merges on all three files, 277/277, 325/325 and 31/31. There is no cheaper
version of this fix.

#### ⚠️ The 0.579 correlation was never evidence — measure the floor first

The previous commit read a 0.579 waveform correlation as proof that "the audio
really does differ". **It is not.** Rendering the ORIGINAL against ITSELF at a
different sidplayfp power-on delay — byte-identical registers, only a different
oscillator/CPU phase — scores:

| orig vs itself, `--delay` | raw samples | RMS envelope | magnitude spectrogram |
|---|---|---|---|
| 1000 cy | 0.5811 | 0.9712 | 0.9742 |
| 4000 cy | 0.7439 | 0.9934 | 0.9819 |
| 12000 cy | 0.6291 | 0.9735 | 0.9745 |

**0.579 is indistinguishable from what identical material scores** — it sits at
the bottom edge of that 0.58-0.74 spread, and the spread itself is set by
nothing but the start cycle. (The exact 0.579 cannot be re-derived: the script
that produced it was never committed. That is the second reason to distrust
it.) A raw-sample correlation is dominated by SID oscillator phase, which no
register-exact build controls and which a different write cycle re-rolls, so it
has almost no dynamic range left to spend on fidelity. The phase-invariant
measures do have some — they sit at 0.97-0.99 for identical material — so those
are the ones to quote. Read against them (25 s, sub 0, every measure validated at 1.0000 against the identity and
recovering a planted one-frame delay exactly):

| | raw samples | RMS envelope | magnitude spectrogram | chroma L1 |
|---|---|---|---|---|
| floor (orig vs itself) | 0.58-0.74 | 0.971-0.993 | 0.974-0.982 | 0.0026 |
| before | 0.4982 | 0.8141 | 0.8740 | 0.0690 |
| after | 0.4942 | **0.8172** | **0.9152** | **0.0586** |

The spectrogram — the phase-invariant measure with real range — closes about a
third of its gap to the floor. Onset match moves 63.6% → 66.0%. The envelope
barely moves, which is consistent rather than disappointing: this was a **pitch**
defect, and amplitude-domain measures are nearly blind to one. That is the
calibration doc's own finding (`docs/AUDIO_LISTENING_CALIBRATION.md`: which
feature is informative is defect-dependent) holding on a fourth case.

#### What is still open — and a retraction of the candidate above

**Correction to the numbers first published here.** The per-window figure was
quoted as "0.78 against a 0.98 floor". The 0.78 was an artifact: the alignment
search stepped in 441-sample (10 ms) hops, which is coarser than a 1024-sample
FFT window is sensitive to, and the *same* comparison scored 0.98 in one run
and 0.87 in another. With a coarse pass plus a 32-sample refine the measurement
is stable and both floors agree:

| per-window magnitude spectrogram, mean over 4 s+ | |
|---|---|
| floor, orig vs itself @ delay 1000 / 4000 cy | **0.9810 / 0.9828** |
| before | 0.8457 |
| after | **0.8545** |

So the gap is ~0.13, not ~0.20. It is still **uniform** — 0.83-0.85 in every
window from 4 s on, at a stable -63 ms offset with no drift — and the first two
windows are where the rest fix shows most (0-2 s: 0.552 → 0.735; 2-4 s: 0.768 →
0.953). Per band, the residual is **broadband**, worst in 3-8 kHz:

| band | floor | before | after |
|---|---|---|---|
| 0-400 Hz | 0.960 | 0.691 | 0.694 |
| 400-1200 | 0.808 | 0.529 | **0.572** |
| 1200-3000 | 0.836 | 0.528 | **0.591** |
| 3000-8000 | 0.932 | 0.481 | 0.506 |
| 8000+ | 0.966 | 0.558 | 0.574 |

**The "register written twice within one frame" candidate is FALSIFIED.** A
cycle-accurate VICE trace of both sides (1,250 frames each; the original's
reconstructed state validates at **100.00%** against siddump over 3,570
comparisons) says our driver already reproduces it:

| within one play call | original | ours |
|---|---|---|
| control-register gate blips (v2 / v0 / v1) | 104 / 20 / 16 | **105 / 21 / 16** |
| note-ons writing freq BEFORE gate-on | 107 | **108** |
| mid-call value changes, total | 157 | 142 |

Our driver issues 16.5 writes per call against the original's 7.2, but the
excess is **536 same-value re-writes**, which change nothing. The writes must be
grouped by **play call, not by the tracer's frame window** — the tracer's
boundary does not coincide with the player's IRQ, so a frame holds the tail of
one call and the head of the next, and counting those together invents
mid-frame changes that never happened. That confound produced a 764-vs-161
reading that was wrong.

One real difference survives and is far too small to be the cause: the original
makes **16 mid-call frequency changes** (v0 freq_lo 9, v1 freq_lo 6, v2 freq_hi
1 over 1,249 calls) that we never make.

**So the cause of the remaining gap is unidentified.** Per-frame register state
is essentially exact, within-call write pattern and order are reproduced, and
the audio still sits 0.13 below a floor measured on the same tune. Naming a
fourth candidate without testing one would be guessing.

⚠️ **Tooling note for whoever picks this up**: `tools/sidm2-sid-trace.exe`
**cannot trace this file** — 0 writes at 400 frames on subtunes 0, 1 and 2,
while exiting 0. Use the VICE wrapper
(`sid-reference-project/scripts/dev/vsid-trace.js --frames N --song 1 --json`),
which validated at 100.00% here, and validate it against siddump again before
reading anything into it.

#### Rung 4, part 3 — the gap is sub-millisecond write PHASE, and the metric cannot see past it

Following the instruction above (find one window and voice where the audio
differs and the registers do not), the instance is **voice 0, 14-16 s**.

Per voice, each read against **its own floor** — which is not optional, because
the three floors are nowhere near each other:

| voice | floor (orig vs itself) | ours | deficit |
|---|---|---|---|
| 0 | **0.9993** | 0.9322 | 0.0671 |
| 1 | 0.9366 | 0.9178 | 0.0188 |
| 2 | 0.9537 | 0.9549 | **-0.0012** |

Voice 0 is the instance: an almost perfectly reproducible voice (0.9993) that
our render misses by 0.067. In its worst window the registers are **not** the
explanation — of 100 frames, **one** differs, by 6 frequency units (0.02 of a
semitone).

**Every physical measure of that window says the two are the same audio:**

| | orig | floor | ours |
|---|---|---|---|
| RMS level | -18.54 dBFS | -18.54 | **-18.54** |
| top 8 harmonic peaks | — | within 0.0 dB | **within 0.1 dB** |
| per-octave energy, 6 bands 50 Hz-22 kHz | — | within 0.00 dB | **within 0.03 dB** |
| RMS envelope corr @ 20 ms | — | 0.9848 | **0.9794** |

So the loss is not level, not timbre, not the harmonic structure and not the
envelope. It is confined to time-frequency fine structure — and that is where
the metric turns out to have no usable resolution.

**The metric's own sensitivity, measured** (per-frame integer-sample jitter
imposed on the ORIGINAL, so no interpolation is involved; controls: identity
and a constant integer shift both score exactly 1.0000):

| jitter imposed on the original | score |
|---|---|
| 0-1 sample (0-**0.023 ms**) | 0.9651 |
| 0-2 samples (0.045 ms) | 0.9517 |
| 0-5 samples (0.113 ms) | 0.9394 |
| 0-22 samples (0.499 ms) | **0.9269** |
| 0-58 samples (1.315 ms) | 0.9243 |
| *(our render, for comparison)* | *0.9283* |

**23 microseconds of jitter costs 0.035.** Half a millisecond reproduces our
render's score exactly. The measure is a proxy for sub-millisecond timing, not
for musical accuracy.

And that timing difference is real and measured. Per-voice spread of the write
offsets within one play call (frames 200-1200):

| voice | original | ours | extra |
|---|---|---|---|
| 0 | 0.032 ms | 0.890 ms | **+0.858 ms** |
| 1 | 0.045 ms | 0.856 ms | +0.812 ms |
| 2 | 0.027 ms | 0.864 ms | +0.837 ms |

The original writes a voice's registers within ~0.03 ms; our driver spreads the
same writes over ~0.87 ms. **Uniform across all three voices** — and our three
voices score 0.918 / 0.932 / 0.955, exactly the band the jitter table predicts
for that spread. The per-voice *deficits* differ only because the *floors* do.

⚠️ **A corroboration that FAILED, recorded rather than dropped**: the rank order
of extra spread (0, 2, 1) does **not** match the rank order of deficit
(0, 1, 2). Read as a rank test this falsifies the mechanism. It is reported
above on the absolute scores instead — where all three voices agree — and the
reader should weigh that this is **consistency, not proof**. The decisive test
is to make the driver issue its writes at the original's cycle offsets and
re-measure; **not attempted**.

Two false leads killed on the way, both cheap and both worth checking first:
**the PSID headers are identical** where it matters (both PAL, both 6581, both
vblank speed — a mismatched chip model would have produced exactly this
signature), and **alignment is not the artifact** (the correlation peak is flat
within ±1 sample and an ideal FFT fractional shift gains 0.0000). One trap did
fire: a first version of the jitter test used **linear interpolation**, whose
half-sample low-pass alone costs 0.07 — indistinguishable from the effect being
measured. Integer-sample jitter avoids it; the controls are what caught it.

**Practical conclusion.** The per-window spectrogram number should not be quoted
as an audio-fidelity figure for this build. It is dominated by where inside the
frame the driver happens to poke the SID, which is inaudible and which no
register-level fix would change. The audible measures — level, harmonics,
per-octave energy, envelope — are already at the floor.

### Two decisions made by measuring

- **`snap_gate` is OFF**, against HardTrack's ON. Chosen on the corpus, not on
  one file: `False` scores **98.16%** vs `True`'s 97.87%, is better on **5**
  voices and worse on **none**, and moves exactly-100.0% voices from 15/36 to
  16/36. Strictly dominant. `MG_SNAP=1` restores the other setting.
- **Subtune 7 is REFUSED, not built.** It is the only one of the 13 whose final
  pattern the relocating copy truncates (`song.truncated_patterns == 1`), and
  the only one that renders catastrophically — voice 0 at **1.9%** audible
  against 92-100% everywhere else. A 1:1 correlation with a named cause is not
  a residual for a table; it is a file we cannot build, and the builder says so
  rather than emitting a plausible-looking SF2. `MG_ALLOW_TRUNCATED=1`
  overrides for investigation.

### Verified, not assumed

`filter=0` on every part is **correct**, not a missing capture: the filter and
passband traces are one constant value across the whole tune, so Last Ninja 2
genuinely never filters. (Checked because a silently-absent `passband_trace`
had already rebuilt HardTrack and DMC low-pass — see `HARDTRACK.md` rung 4.)

### The `signature` decode is no longer unverified

The locator reports `layout='signature'`, not the validated `driller` fast
path, for every Last Ninja 2 and Tusker subtune — so every Stage B number rests
on a decode this doc called unverified. Two checks now stand behind it.

**1. Where both paths run, they agree exactly.** `parse()` tries the fast path
first and only falls back, so the two never meet; forcing `verify()` to raise
sends a driller-layout file down the signature path. On **`Driller` sub 1** the
two decodes are **identical in every field** — table addresses, all 3 tracks,
all 42 patterns, `pattern_addrs`, all 22 instruments including raw record
bytes, both freq tables, tempo, arp address, `duration_base`. n=1 file, which
is all the corpus offers: it is the only file where both paths produce a
decode.

⚠️ **The signature locator is NOT a superset of the fast path.**
`Make_My_Day.sid` parses via `driller` but the signature locator **refuses** it
("could not locate the track-pointer tables") on both its subtunes. It fails
closed rather than mis-parsing, which is the right behaviour — but do not
assume `locate()` can replace the fast path.

**"1 of 55 HVSC files located by the fast path", defined.** `layout=='driller'`
fires on **2 of the 55** top-level Gray_Matt files (the `Worktunes/` subfolder's
2 files are excluded from the 55 — they are not HVSC-catalogued): `Driller.sid`
itself, whose init/play the fast path was written FROM (Codebase64-corroborated,
see *Why Driller first*), and `Make_My_Day.sid`. Excluding `Driller.sid` as the
reference the fast path was derived from — not a file it *found* — the fast
path locates **1 of the other 54**: `Make_My_Day`. Both readings are correct;
CLAUDE.md's headline uses the 1-of-54 (novel-find) sense. Measured 2026-08-21.

**2. The located tables are confirmed against the ORIGINAL's register trace**,
ground truth that owes nothing to our build. In this player family
`$D405`/`$D406` at a note-on is a verbatim copy of the instrument record, so
every sounded AD/SR pair should appear in the located instrument table. Against
a null — the same table read 16 bytes off the located base:

| file | sub | onsets | AD/SR in located table | AD/SR in NULL table |
|---|---|---|---|---|
| Last Ninja 2 | 0 | 749 | **100.0%** | 0.0% |
| Last Ninja 2 | 9 | 487 | **100.0%** | 0.0% |
| Last Ninja 2 | 12 | 140 | **100.0%** | 0.7% |
| Tusker | 1 | 596 | **100.0%** | 0.0% |
| Tusker | 3 | 409 | **100.0%** | 0.0% |

100.0% on **all 8** signature-located subtunes tested, null 0.0-0.7%. The
instrument table location is carrying that result; it is not something any
address would score.

**The frequency table cannot be tested the same way, and its low scores are a
property of the MUSIC, not the decode.** A note-on frequency is only a table
entry when the note is not pitch-modulated at onset. Tusker scores 99.5-100%,
Last Ninja 2 sub 0 scores 100% on voices 0 and 2 — but **6 of 134** on voice 1,
the pitch-modulated one, and sub 12 scores 1.4%. That is not a mis-location:
sub 0's voice 1 renders at **99.3% audible** with the same table, and its
misses sit within 1% of a table entry (a detuned slide entry), not at random.
Read the freq column as confirmation when it fires and as uninformative when it
does not; the null is 0.0% either way.

⚠️ Two limits of the check itself. The onset detector keys on a **gate rise**,
so it under-counts legato voices — `Driller` sub 1 yields only 4 onsets in
120 s, and its freq null scores a meaningless 100% at that n. And this
validates the **tables**, not the sequencer walk: a correct table read by a
wrong orderlist would still pass.

## Next

Rungs 3 and 4 are done and Stage B covers all three games; what is left:

1. **The audio deficit is explained and is inaudible** (rung 4 part 3): it
   tracks the ~0.85 ms of extra within-call write spread, not what is written,
   and the metric loses 0.035 for 23 microseconds of jitter. Nothing to fix at
   the register level. If anyone wants certainty, the one decisive test left is
   to issue the writes at the original's cycle offsets and re-measure. **Do not
   quote the per-window spectrogram as an audio-fidelity figure** — measure
   level / harmonics / per-octave energy / envelope, which are already at the
   floor, and always measure the floor **per voice** (they range 0.937-0.999
   on this tune).
2. Generalise the locator further — **6 → 11 of 55 files now parse**, 3 of the
   5 new ones with confirmed instrument tables. `Make_My_Day` still shows
   `locate()` is not a superset of the fast path.
3. Subtune 7's truncated pattern: recover the missing bytes from the
   relocating copy, or confirm the rip itself is short.

### The track-table stride was hard-coded, and it is per-build

`locate()` identifies the six per-voice track-pointer tables as six consecutive
`LDA abs,y` sites whose operands step by a constant — but the constant was
written as **2**, which is Last Ninja 2's and Tusker's. It is not universal.
The same six-table shape appears at stride **3** (`Pogo_Stick_Olympics`),
**4** (`Hyperion_2`), **5** (`KGB_Superspy`, `Motocross`) and **6**
(`Maze_Mania`), and hard-coding 2 refused every one of them — with the message
"could not locate the track-pointer tables" on **14 files that had already
passed the `music_play` shim check**, i.e. files the parser had itself just
recognised as Matt Gray builds. Requiring the step to be *constant* is what
identifies the tables; its value is a per-build layout detail, exactly like the
site offsets the surrounding comment already says move between builds.

**6 → 11 of 55 files parse, and nothing that parsed before was lost** (verified
by running the census against an unmodified copy of the parser in the same
process). Newly parsing: `Hunters_Moon_Remastered`, `Hyperion_2`,
`KGB_Superspy`, `Maze_Mania`, `Motocross` — all at subtune 1.

#### 3 of the 5 are confirmed — and the first version of this section was wrong

**Retraction.** This section first reported "1 of 5 confirmed, `Motocross`
probably broken", on the strength of `Motocross` building to 120/108/108
gate-on frames against what was described as "the original's 601/652/555
note-ons". Both halves were wrong. 601 is **our driver's** note-on count, not
the original's; and 120/108/108 is the number of frames the **original** sounds
at that subtune. The original is not playing six times more than us — it is
playing almost nothing, because **the subtune index was wrong**.

`parse_sid(subtune=N)` indexes the **track-pointer table**. On these five
builds entry 0 is null (`address $0000 outside image`) and the first real tune
is entry **1** — the documented Driller gotcha, now seen to be the norm rather
than a quirk. But siddump's `-a` counts songs from 0, so the busy first tune is
`-a0`. The builder passes its parser subtune straight through as `-a{SUB}`, so
for these files it scored the decode of tune 1 against the **trace of tune 2**.

Re-run against the correct trace, the AD/SR cross-validation is decisive:

| file | table vs `-a0` | table vs `-a1` | verdict |
|---|---|---|---|
| `Motocross` | **411 / 411** | 7/7 | **CONFIRMED** |
| `KGB_Superspy` | **140 / 140** | 9/9 | **CONFIRMED** |
| `Maze_Mania` | — | **354 / 354** | **CONFIRMED** |
| `Hyperion_2` | 3/3 | 3/3 | insufficient data |
| `Hunters_Moon_Remastered` | 3/3 | 3/3 | insufficient data |

So **3 of the 5 newly-parsing files have independently confirmed instrument
tables**, not 1, and none is known to be wrong. `Motocross`'s 30.6% / 62.0%
audible figures measured a comparison against the wrong tune and should be
discarded, not quoted.

#### The subtune offset — FIXED (`psid_song`)

`subtune` indexes the track-pointer **table**; siddump's `-a` counts the songs
that **exist**. The parser now derives the second from the first
(`MattGraySong.psid_song`) and the builder traces that.

The rule is **"the k-th valid entry is song k"**, which is right under both
conventions and is not an offset: `Driller` declares 2 songs for 1 valid entry,
so a blind `-1` is wrong reasoning that happens to give the right answer there.
Two code paths, because they differ:

- **relocating compilation** (Last Ninja 2): `subtune` selects the blob, so it
  already *is* the song index — the inner parse only ever sees its own index 1
  and would otherwise report song 0 for all 13.
- **plain layout**: count the non-null entries below `subtune`.

Verified on both: LN2 0/9/12 → `-a0/-a9/-a12`, Tusker 2 → `-a2`, Motocross 1/3
→ `-a0/-a2`, KGB_Superspy and Maze_Mania 1 → `-a0`.

**What it changes.** `Motocross` sub 1, rebuilt against the tune it is actually
playing:

| | raw | audible | n |
|---|---|---|---|
| before (wrong tune) | 90.0 / 89.1 / 90.7 | 99.2 / **30.6** / **62.0** | 120 / 108 / 108 |
| after | 93.7 / 98.6 / 84.3 | **92.5 / 100.0 / 82.2** | 5057 / 2747 / 4797 |

The `n` column is the point: the old comparison scored ~110 frames of a tune
the build was not playing. Nothing about the build changed.

**What it does not change.** The 16 shipped tunes are untouched — Last Ninja 2
and Tusker have a real entry 0, so `psid_song == subtune` for every one of
them. `Driller` *does* change index (`-a1` → `-a0`) and rebuilds
**byte-identically** (100.0 / 96.7 / 74.5 raw, 100.0 / 96.0 / 89.4 audible),
because its PSID declares two songs for one tune and `init` forces the same one
either way — the documented gotcha, now confirmed from the other direction.

**The lesson, since it cost a published claim twice in one file:** a fidelity
number is only as good as the trace it is compared against, and "the original
is nearly silent here" is a statement about the *trace selection*, not about
the music. Check what the original actually sounds before concluding anything
from a small `n`.

### The corpus after the fix: 8 games, and one bad build named

With `psid_song` tracing the right tune, every valid subtune of the five
newly-parsing files was built. **20 build**, taking Stage B from 3 games to
**8** and from 17 tunes to **37**.

(The 17 is worth stating because this doc had long said "16 tunes across the
three games" — Last Ninja 2's 12 building subtunes plus Driller 1 plus Tusker 4
is 17, and the enumeration on disk agrees. A count nobody re-derived, off by
one, for as long as the section existed.) Audible (gate-on) fidelity, with `n` beside every number because four of
these are short jingles where a percentage carries almost no information:

| game | subtunes | audible v0/v1/v2 | note |
|---|---|---|---|
| `Maze_Mania` | 1-3 | 100/100/98.6, 100/93.5/100, 99.3/99.9/100 | n 1580-6045 |
| `Maze_Mania` | 4, 5 | 100/100/100 | **n=105, 128** — jingles |
| `Motocross` | 1 | 92.5/100/82.2 | n 2747-5057 |
| `Motocross` | 2, 3 | 100/100/100 | **n=72-136** — jingles |
| `Motocross` | 4 | **0.0/10.9/0.0** | **n=46-58 — BROKEN, see below** |
| `KGB_Superspy` | 1, 3, 4 | 99.9/100/99.4, 100/99.4/99.5, 100/100/100 | n 4032-6045 |
| `KGB_Superspy` | 2 | 99.0/100/100 | n=114-420 |
| `Hyperion_2` | 1-3 | 99.9/99.0/96.7, 97.8/100/88.6, 100/100/98.7 | n 5461-6133 |
| `Hunters_Moon_Remastered` | 1-4 | 99.1/100/82.9 … 100/99.7/80.6 | n 3420-6333 |

**`Motocross` sub 4 is a real failure and is not averaged away**: 0.0% on two
voices, the only failure of the 20, and this one *is* measured against the
correct tune. Diagnosed rather than left as a shrug:

- Voice 0 decodes **zero notes**. Its track is `[34, 2, 2, 254]`, and pattern
  34 is `[$FA 03, $F9, $FF]` — an instrument select, a `$F9`, and the
  terminator. **No note bytes at all.** Voices 1 and 2 reference patterns 35/36,
  which do carry notes (3 each), and score 10.9% / 0.0%.
- The original nonetheless sounds **64 gate-on frames on voice 0** (52 on each
  of the others). So either the track→pattern mapping is wrong for this subtune,
  or a control code we treat as inert produces sound.
- `$F9` (`PC_PARAM`) consumes the following byte, so here it swallows the `$FF`
  terminator. Checking `$FF` first would not rescue it — the pattern still holds
  no notes either way — but it is the kind of adjacency worth knowing about.
  **Corpus-wide it occurs exactly once**: this one pattern, in this one game
  (the four hits below are the same shared pattern seen from four subtunes).

So it is not a general decode bug, and it is not the `$F9` handling. It is one
voice of one 1.3-second sting whose pattern contains no notes while the hardware
plays something. Left open, scoped, and now also flagged `!` as underpowered
(n=46-58) so it cannot be quoted as a fidelity figure in either direction.

⚠️ **A percentage on n≈50-130 frames is not a fidelity claim.** Six of the 20
are jingles of one to three seconds. They are listed because omitting them would
inflate the corpus count without saying so, not because 100.0% on 46 frames
means anything.

#### What this says about the AD/SR check

`Maze_Mania` sub 1 scored **80.2/92.0/88.0** before the fix and
**100.0/100.0/98.6** after — yet the AD/SR cross-validation had "confirmed" it
at the **wrong** subtune index (354/354 against `-a1`, where the truth is
`-a0`). No contradiction: the instrument table is shared across a file's
subtunes, so it explains onsets in *any* of them. This is a live demonstration
of the limit that check already states — **it validates the tables, not the
sequencer walk, and it cannot discriminate a subtune at all.** Anyone using it
as a decode gate should read it that narrowly.

## Sources

- Codebase64 Driller disassembly — https://codebase64.net/doku.php?id=base:matt_gray_-_driller
- SIDin #2 ("Matt Gray's Driller music routine") and SIDin #3 (fingerprinting
  his engine via its portamento-flag check) — both in the TDZ C64 knowledge base
- TDZ knowledge card `matt-gray` (also records a verified reassembly of the
  separate *Dominator* build, from dmx87's `c64_6581_sid_players`)

---

## Tusker (1989) — third build, second wrapper shape

Tusker's `play=$e002` is not a quirk to work around: it is **correct**, because
its wrapper copies the selected blob to **`$e000`**, under KERNAL ROM. A second
wrapper shape, distinct from Last Ninja 2's:

| | Last Ninja 2 (1988) | Tusker (1989) |
|---|---|---|
| copy loop | straight `($fa),y -> ($fc),y` | **self-modifying** operands |
| source table | lo **and** hi (`$3f80`/`$3f8d`) | **hi only** (`$4138`) — blobs are page-aligned |
| length | pages + tail byte | **whole pages** (`$413c`) |
| destination | `$4000` | **`$e000`** (under KERNAL ROM) |
| subtunes | 13 | 4 |

`relocating_subtunes_v2()` handles it. The player itself is the **same 1988
generation as Last Ninja 2** — `duration_base` comes out as `$70` on all four
subtunes, so the `$70` duration split and the `$f9` parameter code both apply.
That is the first evidence these findings generalise rather than being
per-file.

**Result (6000-frame sweep, plain instruments): 4/4 subtunes at 100% onset and
100% pitch** — n = 86, 439, 708, 685.

---

## Deliverance and Quedex — NOT supported (two further generations)

Both refuse, and the *way* they refuse is the finding.

**Deliverance (1990)** — flat file, no relocating wrapper. Its PSID play
address is a **trampoline** (`$4da1: jsr $4daa …`), so the shim had to be found
by scanning for the unmistakable 15-byte body
(`ldx #$00 / jsr pv / ldx #$07 / jsr pv / ldx #$0e / jsr pv`) rather than
assumed to sit at `play`. That now works — but the file then fails at
`could not locate the track-pointer tables`. The 1990 build reorganised the
tables, so the signature locator's "6 sites stepping by 2" no longer holds.
**A third generation.**

**Quedex (1987)** — the shim scan finds *nothing at all*. Its play routine is
`$4bb3: lda $4b7f / bne …`, and there is no `ldx #$00/$07/$0e / jsr` triple
anywhere in the image. So Quedex does not use one shared `play_voice` called
three times: its voice dispatch is structurally different. **A fourth
generation**, and the earliest of the four — plausibly pre-dating the shared
`play_voice` refactor entirely.

Neither is a heuristic gap. Both need the same treatment Last Ninja 2 got:
disassemble the play routine, re-derive the dispatch, then confirm against
siddump. Until then the parser refuses them loudly rather than guessing.

### Generations so far

| Build | Year | Wrapper | Voice dispatch | Duration | Status |
|---|---|---|---|---|---|
| Driller | 1987 | none | shared `play_voice` ×3 | `$fd nn` | **100%/100%** |
| Quedex | 1987 | none | **not the shared shim** | ? | unsupported |
| Last Ninja 2 | 1988 | copy → `$4000` | shared `play_voice` ×3 | `$70+n`, `$f9` code | **100%/100%** ×13 |
| Tusker | 1989 | self-mod copy → `$e000` | shared `play_voice` ×3 | `$70+n`, `$f9` code | **100%/100%** ×4 |
| Deliverance | 1990 | none (trampoline at `play`) | shared `play_voice` ×3 | ? | tables not located |

---

## R20 (2026-07-30): part capacity is now MEASURED -- Driller emits ONE file

Driller used to split into **2 parts**. It does not need to: the whole
8320-row / 665.6 s song emits as **one valid module** using **57 of 128**
sequence slots and reaching only **$61CF** against the `$D000` wall -- about
28 KB of headroom left unused.

The split came from `MAX_PART_FRAMES = 24_000`, a hardcoded constant justified
in-code as "the SF2II memory wall ... roughly 27,650 play-calls (~9.2 min)".
**That derivation is not in the git history and does not follow from the
format**: nothing in a Driver 11 file grows with *time* -- instruments, wave,
pulse, filter, tempo and init tables are all fixed-size, and the sequence
region is a fixed 128 x 256-byte slots. Capacity is a function of event
**density**, not duration.

`convert()` now **probes** it: emit the candidate row range for real, then check
the only two limits that actually bind --

1. `<= 128` sequences across all three voices, and
2. file top `< $D000`

-- growing the window (doubling) while it fits and binary-searching the edge.
The per-sequence caps (250 packed bytes / 960 unpacked events) need no probe;
`segment_track` already splits rather than overflowing them.

Verified: the one-part Driller walks its orderlists to **[8320, 8320, 8320]**
rows/voice (the complete song, all three voices), **zero** cap violations, and
its row total equals the old two parts summed exactly. Songs that already fitted
one part are **byte-identical** (checked on Last_Ninja_2 sub2 and Tusker sub2),
so this only affects songs that were being over-split.

### R20a (2026-07-30): the slot check above was TAUTOLOGICAL, and overflow was silent

Limit 1 was not being enforced. `_part_fits` counted non-zero pointer entries
across all 128 slots and compared that count to 128 -- a value bounded by the cap
tested against the cap, so **it could never be false**. Only the `$D000` wall
actually bound the probe.

The quantity was also unmeasurable that way *in principle*: the emitter
**truncates** at the cap, so an emitted blob never reports more sequences than
the cap however much music was dropped. And `galway_driver11_emitter` dropped
them **silently** -- its `break` left the *voice* loop, so every voice after the
cap fell through to the emergency empty sequence and went **completely silent**,
in a file that parses and loads perfectly.

Demonstrated by forcing the cap to 30 on Driller (which needs 57): the emitter
returned a 14,931-byte module with **voice 2 reduced to a single empty sequence**
and voice 1 truncated to 7 of its 16 -- and the old check called it a fit. Driller
itself was never affected (57 <= 128), but a denser song would have shipped that
way, silently, which the project's lossless-only rule forbids.

Fixed:
- `_part_fits` counts what the range **needs** (`segment_track`) *before*
  emitting, so an oversized candidate is never emitted at all (which also keeps
  the new warning from firing on throwaway probe candidates).
- the emitter announces any dropped sequence on stderr, per voice.
- `SEQ_SLOTS` is read through the emitter **module** rather than a
  `from ... import` copy, which is bound once and would silently go stale --
  that copy is also why the first version of the regression test appeared to
  pass while patching the cap had no effect.

Verified: the normal Driller build is **byte-identical**; with the cap forced to
30 it now **splits into 2 parts covering all 8320 rows** (4142 + 4178) with zero
drops; 3 new regression tests, one pinning the *shape* of the check so the
tautology cannot come back (the pre-existing test only asserted the string
`SEQ_SLOTS` appeared in the source, which the vacuous version satisfied).

### R20b (2026-07-30): the one-part play-test -- ✅ **PASSED, 3/3 full duration**

The one-part 665.6 s Driller **loads and plays to completion in real SID Factory
II**, interleaved against the already-play-tested two-part build as a control:

| Arm | Window | Result | Final "Playing time" |
|-----|--------|--------|----------------------|
| **`Driller_1part.sf2`** (R20, whole song) | 700 s | **3/3 SURVIVED**, crash rate **0%** | **11:41** |
| `Driller_stageA_part01.sf2` (control) | 700 s | 2 SURVIVED + 1 CLOSED, crash rate **0%** (n=2) | -- |

700 s > the song's 665.6 s loop point, and the editor's own clock reads **11:41**
in the final frame, so the module played the **entire song and looped** inside one
file. The screenshot also shows a healthy editor at that point: `Driver 11.00`,
`Song 1/1: Main`, all three tracks populated, 22 instruments. Trials were
**interleaved**, not blocked, because an unrelated job on the same desktop was
cycling VICE instances -- a block design would have confounded "which build" with
"what else was running". The control arm's single `CLOSED` (exit code 0 at ~391 s)
is R23's classifier working: a clean window close is excluded from the crash-rate
denominator instead of being counted as a crash.

**One-file Driller is now shipped, not just measured.**

Getting here produced a **phantom failure** worth recording. A first 700 s trial
reported CRASHED, and a full-duration A/B then reported **100% CRASHED on both
arms** -- including the two-part build that had already passed -- at scattered
times (3 s to 309 s), every one with **exit code 15**. A uniform exit code across
unrelated builds is the tell that the cause is external: `pyscript/conftest.py`
was killing every `SIDFactoryII` on the machine at the end of any pytest session,
and a TerminateProcess exit code is exactly what the oracle reads as CRASHED.
Fixed (both cleanup paths now scope to the session's own editors); the table above
is the clean re-run, same protocol, no pytest in flight.
