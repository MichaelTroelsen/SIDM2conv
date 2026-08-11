# Matt Gray — player RE + Stage A

**Status:** RE complete and Stage A shipped for **Driller, Last Ninja 2 (13 subtunes) and Tusker (4 subtunes)** — 18 tunes, all at 100% onset / 100% pitch on plain instruments.
**Native Stage B: SHIPPED** (`bin/build_mattgray_native_song.py`) — **16 tunes across
Last Ninja 2, Driller and Tusker**; for Last Ninja 2 —
12 of 13 subtunes build, **98.16% audible per-frame frequency** (n=172,745),
**16 of 36 voice-scores at exactly 100.0%**; subtune 7 is refused, not mis-built.
See *Stage B* below. Not wired into `DriverSelector`. Current headline figures:
`docs/reference/ACCURACY_MATRIX.md` (canonical; verified to match this doc 2026-08-09).

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

⚠️ The locator reports `layout='signature'`, not the validated `driller` fast
path, for every Last Ninja 2 subtune. The decode is therefore unverified in the
sense `MATTGRAY.md` uses everywhere else; the builder prints that on every run.

## Next

1. Play-test the Stage B parts in real SID Factory II (PLAYBOOK §4 rung 3) —
   use `pyscript/sf2ii_vs_wrapper.py`, which compares the editor against our
   own wrapper render rather than against the original.
2. A listening pass (rung 4) — no Matt Gray build has ever had one.
3. Extend Stage B past Last Ninja 2: Driller (2 subtunes) and Tusker (4) parse
   today and should need nothing but a run.
4. Generalise the locator past Driller — the other 54 files are per-game
   builds; `verify()` will refuse them loudly rather than mis-parse.
5. Subtune 7's truncated pattern: recover the missing bytes from the
   relocating copy, or confirm the rip itself is short.

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
