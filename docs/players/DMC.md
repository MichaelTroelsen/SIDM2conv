# DMC (Demo Music Creator) player — SID → SF2 support

**Format:** **DMC (Demo Music Creator)** — one of the most-used C64 music editors ever.
The corpus is DMC-family: the **DMC4 Player written by Brian/Graffity in '91** (per the
DMC4 editor ReadMe). A DMC parser is therefore high-leverage — it generalises across
hundreds of HVSC tunes, not just this corpus.
**Composer / corpus:** `SID/JohannesBjerregaard/` — **88 `.sid` files**, ~all by
**Johannes Bjerregaard** (he authored DMC). Many are covers/remakes (Blue_Monday_88,
Billie_Jean, Domino_Dancing, Crazy_Comets_remix) plus the DMC_Demo_IV tunes.
**Ground truth:** the **DMC4 editor** (`~/Downloads/dmc4editor11_win64.zip`; disk images
in `bin/DMC/`). Balloon.sid was the RE exemplar (load `$1000`, init `$1440`, play `$1003`).
**Parser:** `sidm2/dmc_parser.py`; tests `pyscript/test_dmc_parser.py` (6, green).
**Native Stage B:** `bin/build_dmc_native_song.py` (DMCShim → the shared MoN native
pipeline).
**Status:** format fully RE'd; parser + decoder done. Native Stage B **works end-to-end** —
the headline result is **Balloon: 77 parts merged into ONE 400s SF2, wf/pulse 100×3 over
the FULL 400s** (n=19996/voice, 0 skips — the best-evidenced number in the project; its
freq is 80.6/100/97.7). **Rockbuster ≈97%** (freq 65→97, waveform 87→100, pulse 100/100/100)
*on part 1 of 16, the first ~20s only*; most eligible files 2/3 voices at 90–100%. Corpus
survey (`bin/dmc_build_all.py --dry`, all 88 files, re-run 2026-07-16): **56 ELIGIBLE**
(onset-aligned build; split/ADC-vibrato/staged freq + five sound-generation fallbacks + the
interleaved-track generation), **18 FALLBACK** (tables located but onsets disagree —
multispeed/self-IRQ/legato), **14 NO-TABLES** (signature miss — the corpus spans multiple
DMC code generations; see below), 0 ERROR. `bin/` only, not registry-wired. Current headline
figures: `docs/reference/ACCURACY_MATRIX.md` (canonical; corrected here 2026-08-09,
`DOC-AUDIT.md`, to lead with Balloon rather than Rockbuster).

> **ELIGIBLE IS NOT AN ACCURACY FIGURE** (2026-07-16 audit). It means *the decoder's
> emulated onsets agree ≥85% with siddump*, which selects a **build mode** — the built SF2
> is never involved. An eligible file can still score badly: **Twilight_Beyond** is ELIGIBLE
> at 99% onset-agree yet its part01 reads freq **39.2/39.2/54.1**. Likewise "all build" is a
> build count, not a fidelity claim. Quote a per-register measurement, not this survey.

> **EVERY DMC PERCENTAGE IS WINDOW-DEPENDENT, AND THE WINDOW IS A FREE PARAMETER.**
> `bin/_dmc_fidelity.py` takes `secs` from argv and never bounds it to the part's span, so
> past a part's end an exhausted probe is scored against the still-playing original. Same
> file, same artifact: **Thunder_Force part01 = 100/89.2/94.9 at 6s, 82.5/74.2/77.6 at 10s,
> 43.5/37.8/38.8 at 20s.** A DMC number without its window is meaningless. (This is the
> post-end-silence trap — `docs/players/PLAYBOOK.md` §4.)

---

## How it was reverse-engineered

RE'd from **Balloon.sid** (PSID `load=$0000` embedded — the real load word is the first
two data bytes → `$1000`) via py65 disassembly of the play body + emulation-tracing:
1. **Disassembly** of `play $1003 = JMP $1050` (the play body) — the sequencer model.
2. **Emulation trace** (the siddump `CPU6502Emulator` + a `$D012` raster fake) — the
   per-frame SID writes and the wavetable-arp behaviour, which no static read reveals.
3. **The DMC4 editor's three views** (Track / Sector / Sound) named the model.

The player is **relocated to many load addresses** (absolute addresses in code differ per
file — the same trap as Hubbard V2), so every table is **signature-located**, never
hardcoded. The player fingerprint is the `(init−load, play−load)` offset; the dominant
DMC player is **`init+$440, play+$3`** (load `$1000` → init `$1440`, play `$1003`).

## Format model — Track → Sector → Sound

Matches the editor's three views. All addresses below are for load `$1000` (relocatable).
Player state lives in the code page `$1006–$104F`, per-voice indexed by `X ∈ {0,1,2}`.

- **Track** = the orderlist (per-voice sequence of sectors).
- **Sector** = a pattern.
- **Sound** = an instrument.

**Tempo:** a countdown at `$1039` reloads to `#imm` (Balloon `$04` = 4 frames/tick); a
note-tick fires only when it reaches 0. Detected from the code as `DEC tempo / BPL / LDA
#imm / STA` → `frames_per_tick = imm + 1`, per tune. (Gotcha: DMC has both a **global**
tempo counter and **per-voice** counters read indexed `,x`/`,y` — the tempo detector must
pick the global one, else the whole schedule is wrong.)

**Track (orderlist), per voice:** data pointer `$104A,x` (lo) / `$104D,x` (hi); bytes =
**sector numbers**. `$FF` = loop (reset all 3 voice positions → restart), `$FE` = end.

**Sector-pointer table:** `$1900` (lo) / `$1980` (hi), indexed by sector number.

**Sector (pattern) event:** first byte = the **command**:

| bits | meaning |
|---|---|
| low 5 (`& $1F`) | duration (note-tick countdown) |
| bit 5 (`$20`) | flag → `$1044,x` |
| bit 6 (`$40`) | two more **effect** bytes follow → `$1023,x`, `$1026,x` |
| bit 7 (`$80`) | a **sound** (instrument) byte follows → `sound × 8` offset |
| `(cmd & $E0) == $C0` | **REST** (duration, no note; consumes one byte) |

Then a **pitch** byte (a freq-table row selector — see wavetable below). A `$FF` here
ends the sector → advance the track position.

**Sound (instrument) table:** `$1500`, **8 bytes/sound** (offset = sound# × 8):

| +0 | +1 | +2 | +3 | +4 | +5 | +6 | +7 |
|----|----|----|----|----|----|----|----|
| AD (`$D405`) | SR (`$D406`) | PW init | PW rails (nibbles min/max) | PW speed | vibrato | filter | flags |

- **PWM engine** (`$1171`): a per-voice 12-bit accumulator (`$100B,x`/`$100E,x`) bounces
  up (dir flag `$1030,x`) until ≥ +3-hi, then down until ≤ +3-lo — the classic DMC
  pulse-width sweep, at +4-hi step.
- **Vibrato** (Sound +5): per-voice 16-bit accumulator `$1011,x`/`$1014,x`, phase `$103A,x`.
- **Filter** (Sound +7 bit0 → `$D417` via per-voice masks; Sound +6 → `$100A`).

**Freq table:** two layouts across DMC generations — **interleaved lo/hi** (Balloon `$135F`,
indexed by note × 2) or **split** (separate lo/hi arrays like MoN — the `$3f00` "Fat"
generation). The parser detects both (`freq_hi == 0` ⇒ interleaved) and `note_freq` reads
each accordingly.

**Wavetables — the DMC signature:** `$1A00` (arp) / `$1B00` (waveform), **advanced one
step per frame** → a fast per-frame arpeggio. The freq-table **row = the wavetable arp
value**, not the raw note byte — so DMC plays notes far above its own table via octave
shift.

- **`$1A00` arp byte:** bit7 set + low 7 bits = **absolute note index** (`$DF`→95,
  `$AE`→46, `$A3`→35, `$BD`→61 — all `$80|note`, verified). `$00` = hold/base.
  `$7E`/`$7F` = loop-back control.
- **`$1B00`:** the waveform (gate bit + waveform) per step.
- Per-sound wavetable **start** comes from the sound record's wave pointer field.

**SID emit** (`$1314+`, per voice): `$1011/$1014 → $D400/1` (freq), `$1036 → $D404`
(waveform), `$100B/$100E → $D402/3` (pulse), `$D416`/`$D418` (filter). DMC drives
freq + waveform + pulse + filter — a full-featured player.

## ⚠️ The `$D418` passband: 26 of 57 shipped builds were wrong

**Re-measured 2026-08-15 after the corpus rebuild — 0 failures.** The figures
below (26 of 57 wrong, rebuilt to 55/57) describe artifacts that **no longer
exist**: every DMC build was regenerated with the F10/F11 timing fixes, so the
passband had to be re-checked or this section would be quoting a corpus that is
gone — the same F7 shape it was written to document. `passband_check.py
--player dmc` over the 74 built files now reports **53 pass / 0 fail / 21 never
exercise the filter in their window**.

Read the 53 with the routed fraction, not as a mode-match score: **10 of them
pass only because the original routes NO voice through the filter**, so its mode
selection is inaudible and ours differing from it costs nothing (`Roadblaster`,
`Rosanna`, `Eagles`, `Happy_Jingle`, `In_the_Mood`, `Blobby`, `Tiny_Symphony`,
`Twilight_Beyond` and 2 more). That leaves **43 files where a voice is actually
routed and the passband is reproduced**. The single sub-100 agreement in the
whole corpus is `Soap_Theme` at **98.5%** (19 frames, routed 73%; re-measured
post-`00893cd` — the offset-fit rewrite moved this from the previously
published 99.1%/8 frames). Cause: a **startup transient** — the original never
writes a `$D418` default at INIT, so the first 19 frames run on whatever the
register powers up holding. `passband_check.py`'s own `audible` field (gated
on `$D417` routing a voice into the filter, computed only over the
disagreeing frames) reads **0 of 19** over the file's own part-1 span (26s):
none of the 19 mismatched frames are on a voice the original has routed into
the filter in that window, so the transient is inaudible *in the sense of
"not on a routed frame"* — not a measured loudness/onset figure for the gap
itself.

The 21 uncounted are not a pass either — `passband_check` refuses to score a
window in which the original never routes a voice and never selects a mode.
Widen `--seconds` before reading the total as a corpus verdict.

⚠️ **A HARDTRACK-shaped claim, measured here for the first time (2026-08-19):
"the driver zeroes `F_MODE` at INIT, so every build opens on `off`."** Nothing
in this document had actually swept it for DMC — HARDTRACK.md's twin passage
found its own version of this claim refuted (2 of 33 open clear, not all), and
the Soap_Theme note two paragraphs up (a startup transient where the *original*
never writes a `$D418` default at INIT) is the kind of single-file evidence
that would tempt the same blanket claim here. Swept across the same **70
on-disk builds** (`out/dmc/*_part01.sf2`, 73 files minus 3 `_`-prefixed
scratch/backup copies — the same denominator `passband_check.py --player dmc`
counts), each over its own `.span`-derived window:

- **20 of 70 never touch `$D418` at all in that window** — mode sits at a
  constant `off` on BOTH sides for the whole trace, not just at the open.
  Counting these as "opens clear" would be the same 0==0 vacuous pass
  `fidelity_common.exercised` exists to catch, so they are set aside rather
  than scored either way.
- Of the remaining **50 builds where the register is actually exercised, 14
  (28%)** open with `$D418`'s mode bits clear at the first frame the tool can
  trust — siddump force-displays frame 0 regardless of what was written, so
  this reads the first frame after that, the same convention
  `passband_check.mode_sequence` already uses to drop the forced row. The
  other **36 of 50** already carry a mode — matching the original's or not —
  by that same frame.
- Of the 14 that open clear, 5 are the already-documented no-voice-routed
  static files (`Eagles`, `Happy_Jingle`, `In_the_Mood`, `Roadblaster`,
  `Rosanna` — mode never leaves `off` in-window on either side, inaudible by
  construction). The other 9 (`Cant_Stop`, `DMC_Demo_IV_tune_1`, `Deel_2`,
  `Domino_Dancing`, `Dreaming`, `Fruitbank`, `Scandalous`, `Soap_Theme`,
  `Special_Agent`) route real audio (34-100%) while ours opens clear; only
  `Domino_Dancing`'s original *also* opens clear, so it's the sole agreement
  in this group (both at frame 5). The other 8 disagree — the original already
  shows a mode 1 to 19 frames before ours catches up (`Soap_Theme`'s 19-frame
  gap is the corpus's one sub-100% passband agreement, described above).
- First-non-zero-frame agreement across all 50 exercised builds: **33 of 50**
  identical on both sides.

**REFUTED, the same shape as HARDTRACK.md's answer.** Raw over all 70 on-disk
builds, `$D418` reads clear at the trace's first trustworthy frame on **34 of
70** (14 meaningfully + 20 vacuously, because those 20 never write the
register at all); the informative figure, once the vacuous ones are set aside,
is **14 of 50**. Either way it is not "every build" — INIT zeroing is a
necessary condition, not a sufficient one: most builds simply emit a filter
row before the trace's first countable frame and already match the original
there.

`cffc51e` (2026-08-10) fixed the passband in **both** `build_dmc_native_song.py`
and the HardTrack builder, and it was recorded only in `HARDTRACK.md`. DMC's
artifacts were never rebuilt: 968 of 984 `out/dmc/*.sf2` still predated the fix
on 2026-08-12, and `pyscript/passband_check.py --player dmc` scored **31 of 57**
songs selecting the original's passband. `Balloon` — this document's headline —
was among the failures, at **0.0%**.

After rebuilding the 26 failures: **55 of 57**.

**The DMC fidelity script could never have caught this.** `bin/_dmc_fidelity.py`
scores freq / waveform / pulse, and `$D418` is in none of them. Re-measured
after the rebuild, `Balloon` is **byte-identical to its published figures** —
`v1 f 80.6/w100.0/p100.0, v2 f100.0/w100.0/p100.0, v3 f 97.7/w100.0/p100.0` —
which is the point: a scorer blind to a register cannot report it wrong, and
HardTrack's builder had the same blind spot ("scores frequency and nothing
else"). That is why the passband check is a separate tool over the ARTIFACT
rather than another column in either scorer.

**One confirmed failure.** ⚠️ `Domino_Dancing`'s 99.0% is **withdrawn**: its
part 1 spans 596 frames and the check compared 1,400, so past its end our part
**looped** and showed 5 mode changes against the original's 1. At the 12 s its
part actually spans it is **100.0%, 1 change against 1**. `French_Frites` is
real and **audible**, but only *past its own part 1* — at its own part-1 span
(8 s, the window the 53/74 corpus figure above actually used) it is
**100.0%**, which is why it is not one of the 21 uncounted or a corpus
failure. Asserting `--seconds 39` (deliberately over-running part 1, the way
the old fixed-window check always did) still finds the same real defect the
per-file investigation below describes; re-measured post-`00893cd` it reads
**49.4%** (was 49.6%) with the filter routed on 100% of frames and **986
mismatched frames that the original actually routes** (was 978), holding
LP+BP+HP while the original moves HP → BP+HP → LP+BP+HP. ⚠️ **But it is not a
passband-specific defect, and calling it "the largest one left in the
project" was misleading.** The corpus sweep scores this file **freq
24.1/34.4/26.3, pulse 48.3/35.5/40.4** over the same part — the whole build is
wrong, and the passband is one symptom rather than the fault. Fixing the
passband would not make this file right. The capture is sound: `passband_trace`
returns exactly the original's programme (7 → 4 → 6, changing at frames 964
and 1934), and the shared program builder emits a SET row on a passband
switch, so the loss is downstream of both. **What IS true**: every other
player's passband residual is 100%, unexercised, or confined to frames the
original does not route. ⚠️ **`DMC_Demo_IV_tune_5` is SETTLED, and it was never a
passband defect.** The published 98.0% / 10 audible frames / 3 mode changes
reproduces at **no window at all**, and its three components are mutually
exclusive under the current tool — a full sweep reads 100.0%/0a/0chg at ≤8 s,
96.4%/18a/1chg at 10 s, 80.3%/118a/1chg at 12 s, 63.4%/366a/2chg at 20 s,
**64.1%/538a/3chg at 30 s** and 58.1%/732a/4chg at 35 s. Three mode changes
occur only near 30 s, where the audible count is **538**, fifty-four times the
published 10; no window yields 98.0%/10a. THE REASON: the build is
**truncated**. It emits four parts spanning **0–9 s** (`.span` 0-1, 1-3, 3-7,
7-9) of a song that runs past 60 s, and the original's first passband
transition is at **frame 482 = 9.6 s** — after the last frame we produce.
Measured over part 1's own span the file reads **100.0%, LP+HP both sides, 0
changes**, so it PASSES by the tool's default; every mismatch above is
manufactured by over-running a 1-second part against a 60-second original,
exactly as with `Domino_Dancing`. The causal claim below (a mode change
coinciding with no cutoff change has nowhere to go) is therefore **not
applicable here** — there is no mode change inside this build to explain. The
file's real defect is the `WAVE overflow: 288 rows > 256` recorded further
down, which is what truncates it.

That suggested a mechanism — a passband is only expressible where the builder
emits a filter row, so a mode change coinciding with no cutoff change has
nowhere to go — and `Zoom`, which passes at 100%, changes mode only where the
cutoff also moves. ⚠️ **`French_Frites` REFUTES it.** Both of its mode changes
coincide with cutoff changes (frame 963, cutoff 896→768; frame 1933,
768→1024), so a filter row exists at each, and our build still holds
LP+BP+HP across both. The mechanism explains `DMC_Demo_IV_tune_5` and `Zoom` and
does not explain the one confirmed failure — so either there are two causes or
it is the wrong one. **No live hypothesis for `French_Frites`.**

**Three more were failures for three consecutive runs and should never have
been.** `Eagles`, `In_the_Mood` and `Roadblaster` emit mode `off` — no passband
at all — before *and* after a rebuild, so staleness was never their cause. The
cause is that their filter is **completely static**: cutoff, `$D417` and `$D418`
each hold one value for every frame, and the builder emits filter rows on
*change*, so a filter set once at init produces **zero bundles** (`filter=0` in
the build log against `filter=7` for a passing file) and the passband is never
established.

But the severity is nil, and that took a fourth run to see: **`$D417` = `$00`
on all three — no voice is routed into the filter at all**, and the cutoff is 0.
`$D418`'s mode bits choose which filter OUTPUT is summed; `$D417`'s low nibble
chooses which voices are fed IN. With nothing fed in, the passband selects among
three silent outputs. The register difference is real and **inaudible by
construction**. `passband_check.py` now reports the routed fraction per file and
declines to count a mismatch where the original routes nothing.

> ⚠️ **This check reads part 1 only**, against the original's first 28 s. Most
> DMC songs split into many parts (`Alf_TV_Theme` 40, `Balloon` 77 before the
> merge), so a clean result means "part 1's passband is right", never "the
> song's is". A dirty result is conclusive; a clean one is not.

### The tracked sweep (`pyscript/dmc_native_sweep.py`)

Every DMC number above came from `bin/_dmc_fidelity.py`, which is **untracked**
(`bin/_*.py` is gitignored) and scores one part named on argv — so "the
best-evidenced number in the project" was not reproducible from a checkout, and
nothing swept the corpus at all. Third instance of the defect
`pyscript/soundmonitor_sweep.py` and `pyscript/sdi_native_sweep.py` were
promoted to fix. The tracked sweep derives its corpus from
`SID/JohannesBjerregaard/` and **reproduces `Balloon` exactly** —
`dly=+4  v1 f 80.6/w100.0/p100.0  v2 f100.0/w100.0/p100.0  v3 f 97.7/w100.0/p100.0`,
n=19996.

> ⚠️ **THE WINDOW MUST BE ASSERTED, and by default nothing is scored.** DMC's
> adaptive splitter emits parts of 2–20 s and the part→original-window mapping
> is printed at build time, **not stored in the SF2**. Part-1 spans across this
> corpus run **6.9 s to 399.9 s**, so a fixed 20 s window is wrong in *both*
> directions — and the direction that matters most is the flattering one:
>
> | file | true span | fixed 20 s said | true window |
> |---|---:|---|---|
> | `Alf_TV_Theme` | 6.9 s | 73.9/69.4/58.4 | **99.7/99.7/99.7** |
> | `Camel_Riders_Inc` | 9.9 s | 49.3/20.4/43.2 | 85.1/40.9/81.9 |
> | `Cant_Stop` | 17.9 s | 34.8/86.0/91.5 | 37.2/95.2/98.1 |
> | `Blobby` | 67.9 s | v3 **97.9** | v3 **59.5** |
> | `Blue_Monday_88` | 37.9 s | v1 **87.8** | v1 **65.8** |
>
> An over-running window understates; a SHORT one **hides a defect** —
> `Blobby`'s 20 s stopped before the divergence. ⚠️ An earlier version of this
> section said the fixed window cost `Cant_Stop` "~15 s of music it never
> contained" and that a guessed window only deflates. Both were wrong: its part 1
> is 17.9 s (a 2 s over-run), and part counts do not imply equal durations — the
> later parts are the short ones. Restricting the rule to multi-part songs was
> not enough either: a single part's span is the *whole song*, so Balloon's
> 400 s forced onto `Zoom` scored it 24.4/27.7/23.9 at a confident n=19996.
> `--build` reads the real bounds off the builder's stdout; `--seconds N`
> asserts one for a spot check; with neither, every row says NEEDS BOUNDS.
> `Deel_2` is the cautionary case — its part 1 happens to be exactly 20 s, so
> the broken default gave it the right answer.

**FIRST CORPUS FIGURE (2026-08-13, `--build`, all 88 files).** Every other DMC
number in this document is a single file.

| | |
|---|---:|
| **scored** | **72 of 88** |
| refused | 14 (`DMC tables not located` — the documented NO-TABLES class) |
| errored | 2 (one `WAVE overflow` builder cap, one assemble failure) |

| metric | median over 216 voices | at 100 | below 90 |
|---|---:|---:|---:|
| **frequency** | **94.7** | 59 | **87** |
| waveform | **100.0** | 113 | 66 |
| pulse | **100.0** | 119 | 77 |

Read with three conditions:

- **`--build` scored 72 songs where only 57 had shipped artifacts** — 15 had
  never been built at all. A build count and a corpus are different numbers.
- **`n` spans 46 to 19,996 frames** (median 1,046), and **9 of the 72 scored
  under the 250-frame floor**, carrying the `!` marker. Unlike SDI, where that
  guard is inert, it fires here: a median pools a 1-second sting with a
  400-second song.
- **Part 1 only, freq/wf/pulse only.** 87 of 216 frequency voices sit below 90,
  so the tail is large and unexplained, and `$D418` is not in this figure at all.

### ⚠️ The tail was a WINDOW, and the tail is now split by cause (2026-08-15)

**A quarter of it was the sweep measuring past the part it was scoring.**
`part1_span()` read the span back out of the builder's stdout with `re.search`,
which takes the FIRST `part 1/N` line — and the DMC builder prints a discarded
single-part trial before its adaptive split settles:

```
part 1/1 (0-90s, 0-4500f)     <- trial, thrown away
part 1/2 (0-7s, 0-395f)       <- the part actually emitted
```

So `Happy_Jingle`'s **7-second** part 1 was scored over **90 seconds**, and past
7 s our part LOOPS against the original's continuing music. It read
**23.4/16.1/8.1**; measured over its own part it is **98.3/100.0/98.8 with zero
presence mismatch**. `Depeche_Mode_Songs` read 37.9/31.6/29.0 and is
**100.0/100.0/94.5**. Both figures are RETRACTED.

Fixed two ways, and the second is the durable one: `part1_span` takes the last
match, and the `.span` sidecar the emitter writes now takes **precedence over
re-parsing the log** — a record written by the code that emitted the artifact
cannot pick up a decision that was thrown away. (`PATTERNS.md` F8.)

**Corrected corpus** (`pyscript/dmc_native_sweep.py`, 74 scored, 222 voices):

| metric | before | after |
|---|---:|---:|
| freq median | 94.7 | **97.3** |
| freq at 100 | 60 | **76** |
| **freq below 90** | **89** | **64** |
| wf at 100 | 116 | **141** |
| pulse at 100 | 122 | **145** |

### What the 64 actually are

A single number could not say whether this was one defect or several. It is
several, and only one of them is about pitch:

| class | voices | songs |
|---|---:|---|
| **underpowered** (`n` below the 250-frame floor) | 22 | not a score at all |
| **pitch-only** (wf & pulse ≥ 99.5) | **6** | 5 |
| **whole-build** (wf & pulse also < 90) | **22** | 17 |
| mixed | 14 | |

- **Pitch-only — the real frequency residual**: `Balloon` v0 **80.6** (n=19,996,
  the flagship build), `Namnam_Special` v1 81.0 / v2 88.8, `Again_Its_JB` v0
  81.8, `Blobby` v0 88.9, `DMC_Demo_IV_tune_2` v1 88.7. Six voices, five songs.
- **Whole-build** is a different queue. `Roadblaster` v0/v2 58.6/62.0 over
  15,996 frames. These are build failures; pitch is a symptom, exactly as
  `French_Frites` already showed on one file and this now generalises.

### `Flimbos_Quest_main` was never a fidelity defect (2026-08-15)

It read **0.2/0.2/0.2** — 589 frames where the original sounds and the build
never writes a frequency, on every voice, at every offset from −40 to +400. The
cause is upstream of everything the score can see: **the parser decodes no
notes**. All three voices come back as 4,100 events of `note=0, dur=1`, a rest
per tick for the whole song, so `freq` is 0 by construction. The waveform still
moves (20.0/77.1/56.3) only because the captured wave programs run regardless —
which is exactly what made it look like a bad build rather than a failed decode.

It then shipped **34 parts of silence** and was scored.

`build_native_song` now **refuses** a decode with no note on any voice. All three
voices deliberately: a silent VOICE is ordinary, a silent SONG is not. Raised, so
it lands in the sweep's refusal class — which exists precisely so a build gap
cannot masquerade as a fidelity gap.

**Three** files are affected: `Flimbos_Quest_main`, `Kamikaze` (n=90) and
`Nightdawn`.

⚠️ **Two counts of this were wrong before the corpus run settled it**, and both
are instructive. A first probe claimed **20 of 88**; it bypassed the builder's
phase selection (`Namnam_Special` was in that list while really scoring
81.0/88.8). Counting from the shipped artifacts instead — freq ~0 on every voice
— gave **two**, and missed `Nightdawn`, whose silent build read freq **100.0/97.8**
rather than ~0: a constant frequency held on BOTH sides across its 46 frames
scores a vacuous 100. That is the `exercised()` trap, and it is the same file
whose wf/pulse move was earlier written off as an unstable refit — an incomplete
explanation, because it was scoring a build that never plays a note.

Only building the corpus with the guard produced the right number.

**Corpus effect** (88 files): scored **74 → 70**, freq median **98.4 → 98.7**,
voices below 90 **56 → 47**. Removing three builds that were scored without ever
sounding a note is what moved the medians. 88 = 70 scored + 14 tables-not-located
+ 3 decoded-no-notes + 1 WAVE overflow.

**It is a FALSE LOCATE, not a variant (2026-08-15, corrected).** The wording
above — "4,100 events of `note=0, dur=1`, a rest per tick" — described the
symptom from the guard's message rather than from the decode, and it is wrong in
both particulars: the decode emits **zero rests**, and what it emits is not a
note either. All three files produce `pitch=0, ticks=1` on every voice for
exactly `tick_budget` events (2,000 in → 2,000 out; 8,000 in → 8,000 out), with
**no instrument ever selected**. `ticks=1` on every single event is the tell: the
track walker never advances a real duration, so it is not decoding a song at all.

Each of the three has a visibly wrong layout:

| file | layout |
|---|---|
| `Flimbos_Quest_main` | every table **outside the loaded image** — `trk_lo=$15F4` against load `$47B4..$71FA`; also `sector_lo == trk_lo` |
| `Nightdawn` | every table outside the image (`$8539..$9D87` against load `$0801..$46D0`); additionally an **RSID with `play=$0000`**, so it has no traceable onsets either |
| `Kamikaze` | tables inside the image, but `sector_lo == trk_lo == $1ADE` — one address matched twice |

This is `PATTERNS.md` **D2**, the false-locate zero: the locator returned an
answer instead of returning nothing.

⚠️ **The obvious locate-time guard was tested against the corpus and REFUTED —
do not add it.** "Tables outside the loaded image" and "`sector_lo == trk_lo`"
both look like clean tells, and both fire on files that build and score today:
out-of-range on `Depeche_Mode_Songs`, `M_A_C_H`, `Predictable_main`, `Some_Soul`
and `Stormlord`; the degenerate pair on `Myth_Demo`, `STII8` and `Stormlord_V2`.
Eight working files rejected to catch three broken ones. Of 74 located files, 63
pass both checks and **11 fail at least one, only 3 of which are actually
broken** — so neither predicate discriminates.

What DOES discriminate is the decode outcome itself: `pitch=0, ticks=1` for
exactly `tick_budget` events with no instrument ever selected. That is what
`build_native_song`'s guard already tests, and on this evidence the guard is in
the right place. Locating these variants properly remains open and needs the
actual layout, not a sanity check.

**Read the old "87 of 216, large and unexplained" as superseded.** The work it
implied — hunt one pitch mechanism — was the wrong shape for the tail as a
whole, though the pitch-only class it exposed did have exactly one mechanism
behind it (below).

### The pitch residual was the SCALED-vibrato marker (2026-08-15)

The six pitch-only voices existed to isolate one mechanism, and they did.
`Balloon` v0 read **80.6 over n=19,996** — the largest sample in the corpus —
with waveform and pulse both at 100.

Every layer above the driver looked healthy. The emitted FM program is
**correct**: `+0 x3, +16833 x1, -16833 x1, +0 x2, ...`, exactly the two-octave
arpeggio the original plays through its release tails. Bundles were 55, under
the 63 cap, so nothing was force-merged. `fm_loop` is unset for DMC, so the
`$7f` LOOP path never ran.

The driver marks **SCALED** (pitch-proportional vibrato) FM entries by a
`$40-$43` offset HI byte — and `+16833 = $41C1`. The octave jump is read as a
vibrato leg, so the pitch ramps away and wraps mod 65536: ours cycles
`[-16833, -252]` where the original cycles `[-16833, 0, 0, +16833]`, netting
−34170 every four frames.

**Third player to hit this.** Hubbard's drum dives first (which is why
`hard_restart` implies the opt-out), then HardTrack's percussion, now DMC. The
shim sets `no_fm_scale = 1`; `DMC_FM_SCALE=1` re-enables the marker for an A/B.

**It is audible.** All 3,888 mismatching frames are gate-off, but the release
nibble is **11 on every one of them** — ~750 ms, ~37 frames — and 3,190 sit
within 40 frames of the gate falling. A wrong pitch rings out through the tail.
"Gate-off" is not "silent"; that inference was made and withdrawn here.

| | before | after |
|---|---:|---:|
| `Balloon` v0 (n=19,996) | **80.6** | **100.0** |
| corpus freq median | 97.3 | **98.4** |
| freq voices at 100 | 76 | **81** |
| freq voices below 90 | 64 | **56** |

Per voice across the whole corpus: **freq 12 improved, 207 unchanged, 0
regressed.** Two apparent losses were checked and are not the fix:

- `Nightdawn` wf/pulse move only because its fitted offset went 0 → 6 on an
  **n=46** sample — below the 250-frame floor and already marked `!`. An
  unstable refit, which is what that guard is for.
- `DMC_Demo_IV_tune_5` errors `WAVE overflow: 288 rows > 256` **identically with
  and without the change**, and the first `--build` sweep already recorded it.
  The intermediate sweep only scored it because that run had no `--build` and
  picked up a **stale artifact**. Rebuilding stopped a stale number, it did not
  lose a file.

Taken with the window fix earlier the same day, DMC frequency has moved
**94.7 → 98.4** median and **89 → 56** voices below 90.



It scores **freq/waveform/pulse only**, like the script it replaces. `$D418` is
in none of them, which is exactly how the passband defect survived — use
`pyscript/passband_check.py --player dmc` for that.

### The "whole-build" class was mostly TIMING, and two causes are fixed (2026-08-15)

The `whole-build / pitch-only / mixed` split above was derived from strict
per-frame scores alone, and strict scoring **cannot tell a phase defect from a
wrong-content one** — a voice playing the right notes two frames out of step
scores exactly like one playing different notes. Re-scoring every sub-90 voice
with a ±k frame tolerance (`PATTERNS.md` **D10**) separates them:

⚠️ **SUPERSEDED 2026-08-17 — the 31/18 split below is PRE-F10/F11 and does
not reproduce.** It was measured on the 49 sub-90 voices of a corpus that no
longer exists, so it was never reproducible in principle; what follows replaces
it. Re-run over the CURRENT artifacts (74 of 88 songs scored, **210 voices, 51
sub-90** — both figures matching the independent post-rebuild derivation
exactly), with `k=0` first validated to reproduce `dmc_native_sweep`'s strict
column on **208 of 210** voices:

| | voices | reading |
|---|---:|---|
| recovers at **±2**, flat to ±10 | **8** | bounded per-note skew — content exact |
| recovers only by **±10** | **4** | wider or drifting offset |
| gains **≥5 points** but stays sub-90 | **7** | partly timing; NOT content |
| moves **<5 points** | **22** | genuinely different content |

over the **41** sub-90 voices with `n ≥ 250`; the other **10 are underpowered**
and set aside rather than bucketed. So **TIMING 12 / PARTIAL 7 / CONTENT 22**,
against the published 31/18 — the proportions inverted, which is what fixing
the timing defects should do.

**Two lessons about the OLD table, not just its numbers.** Its three buckets
are under-specified: read strictly (`recovered` = reaches 90) they force large
recoveries into "different content" — `Sweet` v2 goes **17.9 → 75.6 → 84.3**
and `Chase` v1 **34.1 → 84.6 → 85.5**, neither of which "barely moves". That
alone accounts for much of 18 → 35 under a strict reading, and is why the
third bucket above exists. And the scorer must compare `freq` by **semitone**,
as `score_pair` does; a raw-equality re-implementation scored `Roadblaster` v2
at 58.2 where the sweep says 96.9, which would have manufactured a content
bucket full of pitch-correct voices.

The old table, for the record:

| | voices | reading |
|---|---:|---|
| recovered at **±2**, no further gain at ±10 | **24** | bounded per-note skew |
| recovered only by **±10** | **7** | wider or drifting offset |
| barely moves | **18** | genuinely different content |

The 18 was called an **upper bound**, because tolerance can only see offsets
inside its own range. `Roadblaster` proved both halves of that on one file: v0
read `58.6/84.4/62.5` strict and `96.9/100.0/100.0` at ±2 with a flat plateau,
which is the clean phase signature; v2 moved only 62.0 → 65.0 across ±10 and was
classified **content on that evidence and classified wrong** — it was a
491-frame whole-timeline shift, invisible to any ±k score. See the second cause
below.

Two causes found, both in code shared beyond DMC:

**1. `_snap_onset` returned the FIRST rise in its window, not the nearest**
(`PATTERNS.md` **F10**). It snaps each note's capture onset to the real gate
rise within `fr-2 .. fr+3`. Whenever the previous note was ≤2 frames long *its*
rise sat at `fr-2` and won, so the capture began two frames early, replayed two
frames of the previous instrument, and the driver hard-restarted on top —
emitting a gate rise the original does not have. Purely **additive**:
`Roadblaster` v0 matched **352 of 352** real rises at delta 0 with none missing
and **93 spurious**, against exactly 93 two-frame notes. Ordering the window by
distance from `fr` (ties backward, for Hubbard) fixes it.
`Roadblaster` v0 **58.6/84.4/62.5 → 96.9/100.0/100.0** (n=15,996), 93 extra
rises → 0. This is in `bin/build_mon_native_song.py`, so it reaches every shim
that sets `snap_gate`: DMC, Future Composer, HardTrack, Hubbard, SDI and Sound
Monitor. `SNAP_FIRST=1` restores the old order.

**2. Only *legato* voices got the leading rest that records where they start**
(`PATTERNS.md` **F11**). Note durations are onset-to-onset **gaps**, so a
voice's tick timeline is relative to its own first onset and
`build_native_song` places event k at tick `sum(dur[:k])`. `Billie_Jean`'s first
onsets are `[2, 0, 962]` and all three voices began at tick 0. Voice 1 (onset 0)
scored 100.0 and set the global boot-offset fit, so the other two read as broken
content. **Voice 2's 962-frame shift measured as the same −2 as voice 0**,
because that phrase is periodic at 96 frames and 962 = 10×96 + 2 — invisible to
every per-frame column, visible only against the absolute onset list.
`Billie_Jean` v0 **63.3/50.1/81.2 → 99.9/99.9/99.9**, `Blue_Monday_88` v0
**65.8/60.0/8.1 → 98.8/99.8/99.4**, and `Roadblaster` v2 (first onset 491)
**62.0/85.5/53.1 → 96.9/96.9/52.2 raw, 100.0/100.0/100.0 audible over n=6,265** —
the voice this file's own tolerance sweep had called wrong content. HardTrack met
this contract first and pinned it in its own test file; the pin did not travel,
and now `pyscript/test_dmc_native_song.py` carries it here.

**The raw column FALLS on some of the voices this fixes, and that is correct.**
A late-entering voice now spends its pre-entry frames on rest rows while the
original holds whatever init left in `$D404`/`$D400`. Both are gated off and
inaudible. `Billie_Jean` v2's raw wf went 94.2 → 49.3 while all 67 of its onsets
became exact and **all 190 frames it actually sounds are 100.0%**. The sweep
therefore grew an `[aud …]` column — gate-on frames only, printed **only where
it differs from raw**, with its own `n`. Quote both: raw alone hides a
regression behind a rest, and audible alone is blind to a release-tail defect
(the exact trap `MATTGRAY.md` records).

**Corpus effect (2026-08-15).** 70 scored / 14 tables-not-located / 4 errored,
210 voices. Per-voice worst-of-three-metrics below. **Correction (2026-08-19,
`shipped-corpora-stale-vs-head`): this was NOT "all 88 rebuilt."** Bisecting
the on-disk `out/dmc/*.sf2` against the shipped corpus found 3 of the 88 —
`Test`, `Fourth_Dimension`, `First_Try_PSX` — still building at an older
commit (`Test` gave 10 parts at `1498c3b`, 7 at `afd2f63` — the actual
2026-08-15 16:19 F10/F11 fix — and 7 at HEAD, versus 14 parts in what had
shipped). They are deterministic and current as of that correction; the
`Test`/`First_Try_PSX` before/after rows quoted below were measured directly
and are unaffected, but the corpus-wide "all 88" framing was false for those
3 files until the bisection rebuilt them.

| | before | after |
|---|---:|---:|
| freq median, raw | 98.7 | **99.5** |
| voices below 90, raw | 47 | **34** |
| freq median, **audible** | — | **100.0** |
| voices below 90, **audible** | — | **14** (of 204 with audible frames) |
| voices at exactly 100 | 59 | **128** (audible) |

**39 voices improved, 26 regressed, 145 unchanged** — and **not one of the 26 is
an audible regression**. 22 of them read audible ≥ 99.5 and 25 read ≥ 90; the
single exception, `Scandalous` v0, has audible `None` at **n=0** — it never
sounds inside part 1, so `score_pct` refuses to score it rather than inventing a
number. The raw drops are the leading rest's pre-entry idle frames, and the
largest of them are the clearest cases: `Test` v1 87.8 → 20.2 raw with **audible
100.0** (n=250), `First_Try_PSX` v2 91.5 → 28.0 with **audible 100.0**,
`Domino_Dancing` v2 95.1 → 47.8 with **audible 100.0**. Quote raw alone and this
fix reads as 26 regressions; quote audible alone and `Dreaming_2` v3 below stays
hidden. Print both.

Biggest gains, all previously in the whole-build bucket: `Chase_v2` v0
**0.0 → 100.0** (audible 100.0, n=4,524), `Wanna_Get_Sick` v1 0.0 → 99.9,
`DMC_Demo_IV_tune_3` v1 0.0 → 99.8, `Hit_the_Baze` v0 0.0 → 99.2,
`Mixerplot` v1 1.1 → 96.5, `Blue_Monday_88` v0 8.1 → 98.8, `STII8` v2 11.1 → 99.7,
`Special_Agent` v0 14.3 → 99.6.

**The audible column found one defect of its own**, which is the whole point of
carrying it: `Dreaming_2` v3 reads raw 61.4/67.9/58.7 — *unchanged by either fix*
— and **audible 13.3/0.0/5.3 over n=75**. On every one of the 75 frames the
original sounds, it writes `$51` (pulse+TEST+gate) and we write `$50`: our gate
never opens, the oscillator sits in TEST reset, and freq and pulse are frozen
while the original arpeggiates. A silent voice that the raw column had been
reporting as 61.4% for as long as the file has been built. It is the **only**
voice in the corpus where audible is more than 10 points below raw. Open.

**`FILT_LEAD`/`FILT_EXACT_PB` — ZERO of 70 DMC songs respond (2026-08-19).**
`filt-flags-adopt-as-default` first reported DMC as the one player these
shared `detect_filter_drives` flags cost something: `Predictable_main`
"1 part → 4 parts" and audible v1 freq "100.0 → 99.35" with the flags on.
`dmc-predictable-main-part-split` retracted that same day: built serially at
HEAD, flags-ON and flags-OFF `Predictable_main` are **byte-identical**
(4 parts, combined md5 `154757d5924b` either way; 3 consecutive OFF builds
also byte-identical to each other, confirming the serial build is
deterministic). The apparent 1-part / regressed-freq result came from the
OFF arm having been built via `pyscript/dmc_native_sweep.py --build -j8`,
which is non-reproducible for this song — a build-concurrency flake
(`dmc-corpus-rebuild-serial-vs-j8`, open), not a filter-flag effect. **DMC
pays no cost from either flag**; both remain scoped to SDI only
(`bin/build_sdi_native_song.py`, `169ef09`), whose own commit message still
quotes the retracted "+3 parts, `Predictable_main` audible v1 freq 100.0 →
99.35" figure as DMC's cost — read that clause as superseded by this
correction, not as current.

**`out/dmc` part count: 991, not 988.** 988 was the flaky `-j8`-built total
(`Predictable_main` at its non-reproducible 1 part). A serial rebuild at HEAD
gives `Predictable_main` 4 parts and the corpus totals **70 songs / 991
parts**; any older note quoting 988 predates this fix.

**What is still open**: a third sub-cause, OBSERVED but not explained.

The observation is solid and reproducible. A **held** voice — one that changes
instrument without re-gating, so its restarts never enter the onset list — has
its pulse-program restarts placed a constant 1-3 frames early:
`Ace_II_remake` v1 **48 of 49 exactly 1 frame early**, `Jazz_3` v1 **521
restarts, all at −2/−3**. Those voices are ±2-recoverable, have byte-perfect gate
onsets, and are unmoved by both fixes above.

**The obvious explanation was tested and does NOT hold.** The STEP-GRID picks one
residue mod `fpt*mult` from the gate onsets, so an event on a different residue
should pay up to `fpt-1` frames — but measured against the ORIGINAL alone
(`scratchpad` tool, no build in the loop), `Ace_II_remake`'s restarts are **0 of
124 off-grid** and `Jazz_3`'s **0 of 138**. They sit exactly on the residue the
shim chose. Grid quantisation is not the mechanism, and the 1-frame error has no
confirmed cause yet. Do not repeat the guess.

What the same measurement DID find is a real but much rarer grid-residue case:
`Some_Soul` runs grid 6 at residue 2 and **every one of its 117 restarts is off
that residue by 1**, on all three voices. It sits in the content bucket
(v2 63.5/64.1/100.0). One file of eight sampled — worth fixing on its own terms,
not worth generalising from. `DMC_GRID=0` is the A/B lever, but the grid exists
to stop sequences bloating 4-5× (`Balloon` 77 parts), so turning it off
corpus-wide is not the answer.

## Parser + decoder (`sidm2/dmc_parser.py`)

Signature-locates the sector-ptr / sound / freq / track tables (relocation-safe, resolves
on 44/88 files); `DMCNote` dataclass; `decode_track` / `decode_sector` / `decode_song`
(`$C0` = rest, `$FF` = loop/end); tempo from the **global** counter (excludes the per-voice
counters accessed `,x`/`,y`). `measure_onsets` uses the siddump CPU + a `$D012` raster
fake + banking to record every per-voice `$D404` gate-rise = the exact onset frames.

**Onset validation vs siddump (per-voice phase — the correct metric; a single global
phase undercounts because voices trigger a few frames apart within a tick): 29/43
main-player files ≥90%**, 20 of them ≥95% (Dummy_II / Blobby / Jazz_1 ≈99–100).

## Native Stage B (`bin/build_dmc_native_song.py`)

`DMCShim` feeds the shared trace-driven pipeline (`build_mon_native_song.build_native_song`
+ `emit_one`, also used by MoN / Hubbard / ROMUZAK). Two modes:

- **(a) Onset-aligned** (default when emulated onsets agree ≥85% with siddump): `fpt = 1`,
  one native note per emulated gate-rise, pitch = the trace-resolved **absolute semitone**
  (via the full-range PAL table), `note_freq` = `_pal[semi]`. Triggering on the **true**
  frame lets the FM capture reproduce DMC's per-frame arp **in phase** — this is what took
  Rockbuster from ~65% to ~97%.
- **(b) Tick-grid fallback** for legato / multispeed / self-IRQ variants where the onset
  check fails.

The native ceiling was **onset alignment**, not the arp: `tick × fpt` placement started the
wavetable arp at the wrong phase; onset-aligning fixed it. The build self-checks
emulated-vs-siddump onsets (≥85%) and falls back otherwise.

**Within-frame onsets are the default since 2026-07-11** (`DMC_WF=0` reverts): the
2026-07-11 audit (`bin/_dmc_wf_audit.py`) found **24/88 files whose note-set retriggers
gate OFF+ON inside one play call** — invisible to end-of-frame register state (the Sound
Monitor half-loudness class). Worse than loudness: the missed onsets **failed the ≥85%
agreement gate**, dumping whole files onto the tick-grid fallback. Measured on Balloon
part01 (its own span, best delay): state-based = wf 0/70/36, pulse 1/0/95 → within-frame =
**wf 100/100/92, pulse 100/100/100** (agreement 71/175 → 174/175). The corpus survey went
**41 → 56 ELIGIBLE** (18 FALLBACK, 14 NO-TABLES); all 56 build clean (2026-07-11 rebuild,
1135 part files). The gate still protects multispeed variants (Jazz_1 fails both modes and
produces byte-identical tick-grid output either way).

Run: `py -3 bin/build_dmc_native_song.py SID/JohannesBjerregaard/<name>.sid [secs|auto]`
→ `out/dmc/<name>_partNN.sf2`. (`DMC_MAX_PARTS` caps parts.) Corpus runner:
`py -3 bin/dmc_build_all.py --dry` categorises all 88 (ELIGIBLE / FALLBACK / NO-TABLES);
without `--dry` it builds every ELIGIBLE file (sequential — the shared MoN scratch forbids
concurrency — with a per-file timeout).

**Fidelity measurement** — DMC files aren't under `Tel_Jeroen/`/`Hubbard_Rob/`, so
`mon_part_fidelity.py` returns 0; measure directly: wrap the SF2 via
`mon_sf2_validate._psid(bytes(sf2[2:]), sla, 0x1000, 0x1003)`, trace both with
`mon_fidelity.per_frame`, diff `freq_to_semi`/wf/pulse over a **non-zero** window
(`secs=0` yields a vacuous 100.0 — a silent SF2 measures "perfect").

## Base-note resolution (`_sem`, RESOLVED 2026-07-09)

The driver holds `base` (= `note_freq(note)`) on each note's **trigger frame**, and the FM
capture reproduces every *later* frame exactly — so the metric-optimal base is the
original's freq at the note's **gate-rise frame** (frame 0). `_sem` (mode `adapt`, default)
snaps to the `wf&1` gate-rise and takes that semitone. One exception makes it non-trivial:

- **The FM `$40-$43` high-byte collision.** The driver's FM dispatch reads a raw Hz delta
  whose *high byte* is `$40-$43` as a **scaled-vibrato** entry, not a delta — an
  unencodable-delta format collision that corrupts the whole note. Only `delta1 =
  trace[o+1] − base` depends on the base (all later deltas are base-independent). A
  drum/arp voice whose gate-rise sits an octave-plus **below** its loud excursion (e.g.
  Tiny_Symphony osc3: gate-rise semi 24, then a noise spike at semi 72 → `delta1 = 16710 =
  $4146`, hi `$41`) collides. `adapt` detects this and seats the base at the **high** value
  instead (`delta1 → ~0`; the downward return delta has hi `≥ $bc`, safe) — one frame of
  base pitch is wrong, but the note plays.

Result (15 s windows, freq %): **Wanna_Get_Sick osc1 66→100, Blobby osc1/2 75/87→87/100,
Tiny_Symphony osc1 98→100 while osc3 holds 98** (a fixed frame-0 base crashed osc3 to 1.6).
Rockbuster unchanged (~97). Env `DMC_SEM_MODE=spike|trig|adapt` selects the legacy
fixed-order resolvers for comparison. *(Latent, unfixed: a base-independent mid-note
`+$40xx` single-frame jump — a fast arp that repeats the octave-plus leap — hits the same
collision and no base choice avoids it; it would need a driver FM-encoding change.)*

## Open issues / TODO

- **Per-voice legato onset undercount — SOLVED by the full-song A/B (`DMC_LEGATO_AB`,
  default on).** Some voices are legato: they change pitch WITHOUT re-gating, so gate-rise
  onsets collapse the voice into one note whose FM freezes after `FM_CAP=256` frames. The
  **decode** note boundaries (`tick*fpt+phase`) align with the trace frame-for-frame
  (verified: decoded pitch == trace semitone at that frame), so a decode-driven schedule
  fixes truly-legato voices — but *only some*: a sparse-but-static gate voice was already
  byte-perfect (Fourth_Dimension osc2), and the decode schedule has its own failure mode
  (phase misalignment, and more notes ⇒ shorter parts ⇒ more clustering). **No trace
  heuristic reliably predicts gate-vs-legato per voice** (six were tried, each traded one
  voice for another). The fix is a **per-voice A/B**: build the whole song BOTH ways (gate
  vs candidate-legato) with the real adaptive part-splitting, measure per-voice across all
  parts, and keep the decode schedule for a voice only where it *measurably* wins. It is
  guaranteed non-regressing (gate is the default) and — measured like-for-like, unlike a
  single window — it works: **Dreaming osc3 39→90** (kept legato), while Fourth_Dimension
  osc2 correctly stays gate (100 vs 95.9), and M_A_C_H/Rockbuster have no candidates at all.
  (Key insight: the adaptive part-splitting re-triggers each note at every part boundary, so
  it already mitigates most of the truncation — which is why an earlier single-part window
  *over*-stated the legato benefit. The A/B decides on the first ~90s to bound cost; extra
  builds happen only for candidate files.) Remaining: **pulse extraction** on a few voices
  (Scandalous osc1 p25, Shape osc1 p0.3).
- **Multispeed / self-IRQ variants** (Chase, Dummy_II): 1× replay reads them wrong (Chase
  4× too slow — PSID speed flag 0 but they self-install faster timing). Falls back to the
  tick grid. Lower priority.
- **NO-TABLES = multiple DMC generations (44/88, the big coverage front).** The signature
  parser (built on Balloon = the `init+$440/play+$3` DMC4 generation) misses tables on 44
  files that span *many* load addresses and fingerprints (`init+$0/play+$6`, `init+$c40`,
  `init+$7764`, …). Miss counts: `snd` 32, `frq` 32, `trk` 16, `sec` 9. The variants write
  the SID envelope registers with **`STA $D405,Y` (`99`) in a batched store block** rather
  than the `LDA abs,Y / STA $D405,X` (`9D`) idiom the parser anchors on — i.e. a different
  code generation, not a relocation. 12 files miss exactly one signature (nearest wins).
  **The `$3f00` "Fat" freq-only cluster is now handled** (split-freq support, above):
  Fat_6/First_Try_PSX → ELIGIBLE (build ~60–84%), Fat_Complete_2 → FALLBACK. The `snd`
  generation is **multi-idiom**; three sub-variants now handled via gated fallbacks (each
  runs only when the primary sig misses → no regression): **(1) state** (In_the_Mood — `LDA
  base,Y / STA st,X / LDA base+1,Y / AND #$0F`) → **100/100/100**; **(2) absolute-store
  unrolled** (Thunder_Force/M_A_C_H/Predictable_main — voice-1 AD via `LDA base,Y / STA
  $D405` absolute `8D`, AD/SR consecutive) → M_A_C_H **100/100/100**, Thunder_Force v1 100 /
  v2·v3 ~96, Predictable freq·pulse 100 (wf 50); **(3) stack/indexed-store** (Special_Agent
  /Spy_vs_Spy_III/Twilight_Beyond — the store index is reloaded between field read and SID
  write: `LDA field,Y / LDY var,X / STA $D405,Y` for AD, `/STA $D406,Y` for SR with AD=SR−1)
  → Spy v1 & Special_Agent v1·v3 **100/100/100**, Twilight v1 100. That's **7 of the 9
  `snd`-only files** unlocked. Still NO-TABLES: **Depeche_Mode_Songs** (multi-song, yet
  another idiom) + the multi-signature-miss files. Remaining full coverage is per-version
  dataflow RE (like the DRAX cluster), high-leverage (unlocks Domino_Dancing, Stormlord,
  Flimbos_Quest, Crazy_Comets_remix, …).
- **Interleaved-track generation handled** (Deel_2 / Fruitbank / Slimbo4 — the `trk`-only
  cluster). These read the track ptr via `TXA / ASL / TAY / LDA trk,Y` (interleaved lo/hi,
  indexed **voice×2**) — a read that *also* matched the sector signature first, so the parser
  had mislabelled the track table as the sector table and missed both. Now detected: take the
  track from that idiom (`trk_interleaved`, voice×2 stride in `_voice_track_ptr`) and
  re-locate the real **split** sector table (`TAY / LDA sec_lo,Y / … / LDA sec_hi,Y`). →
  Deel_2 (osc2·osc3 ~100), Fruitbank (~95), Slimbo4 (osc1·osc2 ~99). The track note-format
  (bit7 = control) isn't fully decoded, so the instrument timeline is approximate — but
  freq/wf/pulse come from the trace, so fidelity holds.
- **Decode variants:** the "0% variant" cluster (Billie_Jean track sig mis-locates to the
  `$1440` code region) + the 70–90% `$C0` sector desync. Onset-align already covers many
  (it's decode-independent for pitch/timing). Low priority.
- **Editor-view / F-key population** for editability (Stage A / F1–F5), once fidelity lands.

## Dead ends (do not re-tread)

- **`note_freq` bound to DMC's own freq table** — wrong; DMC plays notes above its table
  via octave shift. Use the full PAL table + trace-resolved semitone.
- **Global tick→frame schedule** calibrated from the best voice — regressed the good
  voices, didn't fix the bad ones.
- **Pitch-step onset detection** (gate-rise OR freq jump) — 100% coverage but over-emits
  on the per-frame arp (Dummy_II 423 vs 106 real), breaking 1:1 placement.
- **Debounced settle onset detection** (semitone held ≥3 frames) — improved legato coverage
  but regressed the build (Blobby 74/87/99 → 1/1/98). Coverage ≠ native fidelity.
- **Wavetable-arp SEMITONE model** (Galway/MoN structural-arp path) — **regresses**
  (Rockbuster osc3 93→75, Omega 40→16). WHY: semitone-hold entries play `freqtable[base+S]`
  quantised to whole semitones in PAL tuning, but DMC's freq table isn't PAL and arp steps
  aren't on-semitone → strictly **less** exact than the Hz-delta onset-aligned capture,
  which already reproduces DMC's per-frame freq bit-for-bit. The Hz-delta capture is the
  right representation.
- **Minimal-embed SF2** for Rockbuster — plays byte-identical under siddump but **crashes
  SF2II** on load (`$A000` high-load player). Abandoned in favour of the native build.

See the `johannes-bjerregaard-player` memory for the full RE trail, and
[PLAYBOOK.md](PLAYBOOK.md) for the shared porting method.
