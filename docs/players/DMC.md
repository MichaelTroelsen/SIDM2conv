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
real and **audible** — at its true 39 s span it reads **49.6%** with the filter routed on 100% of frames and **978 mismatched frames that the original actually routes**, holding LP+BP+HP while the original moves HP → BP+HP → LP+BP+HP. It is the **largest genuine passband defect left in the project** — every other player's residual is either 100%, unexercised, or confined to frames the original does not route. `DMC_Demo_IV_tune_5` reads 98.0% at
10 s with **10 audible mismatched frames**, and its 3 mode changes all occur with the **cutoff unchanged**.

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

It scores **freq/waveform/pulse only**, like the script it replaces. `$D418` is
in none of them, which is exactly how the passband defect survived — use
`pyscript/passband_check.py --player dmc` for that.

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
