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
**Rockbuster ≈97%** (freq 65→97, waveform 87→100, pulse 100/100/100), most eligible files
2/3 voices at 90–100%. Corpus survey (`bin/dmc_build_all.py --dry`, all 88 files): **27
ELIGIBLE** (onset-aligned build; +9 this cycle from split-freq + three sound-generation
fallbacks), **~26 FALLBACK** (tables located but onsets disagree — multispeed/self-IRQ/
legato), **~35 NO-TABLES** (signature miss — the corpus spans multiple DMC code
generations; see below). `bin/` only, not registry-wired.

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

- **Per-voice legato onset undercount** (the residual on eligible files). Some voices are
  legato — they change pitch WITHOUT re-gating, so the gate-rise onsets collapse the whole
  voice into one note (Cant_Stop osc3 = **1 gate-rise for 1338 decode notes**; that note's
  FM freezes after `FM_CAP=256` frames → wrong tail). The **decode** note boundaries
  (`tick*fpt+phase`) DO align with the trace frame-for-frame (verified: decoded pitch ==
  trace semitone at that frame), so a decode-driven schedule fixes the truly-legato voices.
  **Investigated + reverted (2026-07-09):** switching legato voices to the decode schedule
  helps the extreme case (Cant_Stop osc3 44→66) but **regresses others** — a merely-sparse
  gate voice whose long notes are *static* was already byte-perfect (Fourth_Dimension osc2:
  9 gates, 100%), and the legato schedule has its own failure mode (decode phase
  misalignment) that hurt Cant_Stop osc2 (98→68). Six trigger heuristics (gate-count ratio,
  gate≤2, gap>FM_CAP, and a direct trace-truncation measure) each trade one voice for
  another — **no trace-derived heuristic reliably predicts gate-vs-legato per voice.** The
  clean path is a **per-voice A/B**: build both schedules for each voice and keep whichever
  reconstructs the trace better (expensive; a real design, not a heuristic). Plus **pulse
  extraction** on a few voices (Scandalous osc1 p25, Shape osc1 p0.3).
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
