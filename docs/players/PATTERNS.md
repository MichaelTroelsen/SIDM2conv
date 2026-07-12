# The Technique Catalog — named patterns from eight player arcs

Companion to [PLAYBOOK.md](PLAYBOOK.md) (the *method*). This is the *pattern
library*: recurring player mechanisms, diagnostic techniques, and failure
classes, each named so the next arc can look them up instead of rediscovering
them. Every entry lists where it has already appeared — if your symptom
matches, read that arc's doc/memory before writing new code.

Sources: Laxity NP21, Galway, ROMUZAK, MoN (Jeroen Tel), Hubbard V1/V2, DMC
(Bjerregaard), Sound Monitor (Hülsbeck), SDI (Gallefoss/Tjelta) + the NP21
clusters. *Created 2026-07-12 (v3.19.0 era).*

---

## Part I — Player mechanisms (what the 6502 is actually doing)

### P1. The pitch-carrying instrument
**The single most-rediscovered pattern (5 independent finds).** The sequence's
note byte is NOT the heard pitch: the instrument's wave/synth program carries
a semitone offset (melodic) or an absolute semitone (drums), applied per frame.
Sequences can play a *constant* note while the music moves.

- **Symptom:** windowed pitch score ≫ strict score; onset deltas **constant
  per instrument** (see D1).
- **Where the pitch lives — differs per player, get this right:**
  - SDI A: wfprg **row 1** arg (row 0 = the `($01,0)` init/test row).
  - SDI D: the walk's **resting row** (3-byte rows; `$FE` parks on the last
    row — the onset frame itself carries the raw note, attack rows spike past).
  - SDI E: wfprg **row 0**, applied to the SID **on the note-on frame** by the
    set-instrument tail (`lda f-1,y / bmi / adc note,x`).
  - SDI V: instrument **octave nibble** (freq word doubled `oct-1` times =
    `+12*(oct-1)` semis) + per-note instrument in the row's fx byte.
  - DMC: the wavetable byte `$80|note` = absolute semitone (the freq-table row
    IS the wavetable value).
  - Galway: chord arps inside the driver-internal FM (ported to editable wave
    programs, `GALWAY_ARP_WAVE`).
- **Trap:** applying the offset at the wrong walk phase **regresses** files
  whose onset frame is clean (SDI C: Bahbar 94.3→81.4). When sub-classes
  disagree, gate the application until the walk phase is settled by emulation.

### P2. Tie vs retrigger (gate semantics)
Every player distinguishes "new note" from "pitch change under a held gate",
and every wrong guess costs a debugging day.
- Hubbard V1: no-release (bit5) chains are **ties**, not retriggers (the
  2-frame bass chop bug). MoN: `$FB` = tie flag (was decoded as 27-tick rest —
  a whole-subtune desync). SDI E: note bit7 **SET = tie** (the draft had it
  inverted; every calibration scored 0 until flipped). Galway Wizball: fully
  legato voices — gate-based note detection collapses to ~2 notes/voice.
- **Runtime Driver 11 cannot parse `$90-$9F` tie bytes** (editor-only feature;
  emitting them desyncs playback — Sound Monitor lesson, locked by test).
- **Validation note:** ties produce no gate rise, so onset validators skip
  them; but Stage A/B must model them (re-gate in cut 1, exact legato in B).

### P3. The wrapper / self-installed-IRQ class (`play=$0000`)
The rip's INIT installs its own raster/CIA handler (vector at `$0314` or
`$FFFE`), never RTSes (CLI + `JMP *` spin), and PSID `play=0`.
- Seen: 6 Galway tunes (Arkanoid, Game Over…), SDI variant V (the `VE-2x/4x`
  files — the wrapper drives a 3-JMP module 2x/4x per frame).
- **Handling:** bounded init emulation — run until the vector installs or the
  PC hits a JMP-to-self; derive the handler; the multiplier is usually a
  literal compare in the wrapper (`LDA counter / CMP #$02`). zig64 has the
  full path (simulated IRQ per frame); py65 suffices for locate-only.
- Often the module + data are **in-file** and only scratch state is
  runtime-built — check before building an emulation pipeline (SDI V needed
  none).

### P4. Multispeed (Nx play calls per video frame)
Filename hints (`_VE-4x`, `2x`), CIA-timer speed bits, or wrapper counters.
The decoder's tick domain is *play calls*; the trace's frame domain is *video
frames* — divide, don't guess. DMC multispeed variants gate the within-frame
onset default (P5). A 1x decoder against a 4x file scores ~0 on both metrics.

### P5. Within-frame retriggers (gate OFF+ON in one play call)
A state scan that samples the gate once per frame is **blind** to a retrigger
completing inside a single call (DMC: 24/88 files; Balloon wf 0→100 after the
fix). Capture gate *events* (every `$D404` write), not end-of-frame state.

### P6. Feature-flag assembly (one source, many binaries)
The editor assembles the player per song with features compiled in/out (SDI's
`rem@` flags; the 2.1 source explains the rip clusters). Consequences: byte
signatures must **wildcard across the optional blocks**, addresses shift per
song, and "the same variant" can have structurally different code paths.
Locate by *idiom* (short, distinctive instruction runs), never by offset.

### P7. Column-major zN instrument tables
Instruments as parallel byte *columns* indexed by sound#, not row-major
records (SDI z0-z9, Stinsen `$1808/$181C`, SDI V stride-31 columns). The read
site tells you the layout: `LDA table,Y` with Y = sound# = column-major;
`LDA table,Y` with Y = instr*stride = row-major records. Confirm the stride
before claiming a format (the DRAX v3.5.67→68 mislabel).

### P8. The state-block engine
Per-voice state as fixed-size blocks (`$0400+v*$40`, X = 0/$40/$80) instead of
parallel arrays (X = voice). Signature: `LDA/STA $04xx,X` with block-stride X
setup at init. Track position, row counters, transpose all live at fixed
block offsets — decode needs the offsets, not the addresses.

### P9. Track-conductor with independent row stream (tracker class)
SDI V: the track entry runs for `length_tbl[seq#]` **ticks** and advances on
expiry — *independent* of the row stream inside the seq (rows just keep a
countdown). Sequence overrun/underrun is normal, not a decode bug. Contrast
with the A-D class where the seq's END byte drives the track.

---

## Part II — Diagnostic techniques (how to find the above)

### D1. The delta histogram (the pitch-class detector)
For every real onset (gate rise in siddump), find our nearest decoded note
(±4 frames) and record `freq_to_semi(real) − freq_to_semi(ours)` at samples
`fr+{0,2,3,5}`. Read the histogram:
- **Constant per instrument** → pitch carrier (P1). Port it.
- **Huge at fr+0, settling to a constant** → attack rows spiking past; the
  sustained pitch = a later walk row (SDI D's resting row).
- **Scatter ±2..7** → glides/vibrato/arps mid-flight (extend the sample
  window to confirm: if strict rises with `fr+{8,12,16,20}`, it's slides).
- **Wrong stream entirely** (deltas look like a different melody) → false
  locate (D2) or voice-mapping error before anything else.

### D2. The false-locate zero
**A variant scoring 0.0 on BOTH metrics is a mis-locate until proven
otherwise.** Dump the extracted operands and check they point at sane file
offsets *before* touching the decoder. Paid for twice in one day (SDI V: the
"D" pattern matched a wrapper; identical operands across different songs =
matching invariant player code, not per-song data).

### D3. Content-verified table location
Don't trust a lone byte pattern for data tables — verify the *content*: freq
tables = two abs,Y read targets exactly `$60` apart whose combined words
double per octave (`_freq_scan`); pulse tables = plausible PW ranges; track
pointer arrays = addresses inside the file. A pattern match with garbage
content is a false locate (D2).

### D4. Strict + windowed dual metrics, and vacuous acceptance
Always report BOTH: windowed (0..+37 semis, arp-tolerant) and strict
(delta==0). The gap *is* the pitch-carrier signal. And test every tolerance
against a known-bad case: the 0..37 window happily passed +2-semitone errors
for months; a `secs=0` fidelity window measured a silent SF2 as perfect
(Hubbard's vacuous-100 bug); an arp tolerance of `max(4, dur//8)` against 3
compared frames accepted garbage (SM drums).

### D5. Timing-model calibration by strict agreement
When the tempo conductor is unresolved (E's dual-row condition, V's global
tempo commands), select the tick→frame mapper **per file by strict
pitch+onset score** over a small candidate set (flat fpt 1-8 + extracted
tempo programs). Selecting by windowed onsets picks wrong mappers (Kirby
16.5→71.0 from calibration alone). This is calibration, not cheating: the
pitch comparison stays exact.

### D6. Flow-following disasm + raw-binary greps (use BOTH)
Linear disassembly derails on embedded data (state cells between routines).
Flow-following (worklist over branch/JMP/JSR targets) fixes that — but it
**misses paths behind unfollowed dispatch** (SDI V's per-note instrument at
`$1669`). Complement: grep the raw binary for *state-cell writes* (`9D 04 04`
= `STA $0404,X`) to enumerate every writer of a cell you care about.

### D7. Bounded init emulation
For wrapper/relocating players: py65-step INIT with (a) vector-change
detection, (b) JMP-to-self spin detection, (c) a step cap. Vectors often
install *before* the module init runs — stop on the spin, not the first
vector write (SDI V: stopping early left voices 1/2 unset). Myth: full
emulation extraction (intercept the freq lookup) when the player relocates.

### D8. Per-file confirmation before generalizing
Never generalize a table layout from one file (DRAX $1B8A: "wave table" →
actually 8-byte instrument records; two releases to unwind). Confirm the
record stride + one decoded field against a second file, then generalize.

---

## Part III — Infrastructure failure classes

### F1. The capture CPU poisons everything downstream
A byte-exact metric with audibly wrong sound = suspect the *capture* CPU, not
the driver (siddump SBC-carry bug broke 16-bit chains project-wide — the
Cybernoid vibrato defect). Fix in one place; every player inherits it.

### F2. Don't edit builder modules while a corpus runner is live
Corpus runners spawn subprocesses that re-import the module mid-run — a
half-edited file corrupts random builds (nearly lost Fun_Mix). Edit after the
run, or run the corpus after the edit.

### F3. Silent-caps and swallowed exceptions
A bare `except Exception` swallowed a `NameError` for nine releases while a
safety gate stayed bypassed (v3.5.63). Narrow excepts in extract+rewrite
blocks; if a build bounds coverage (top-N, truncation), log what was dropped.

### F4. Boundary/label artifacts masquerading as fidelity loss
Rounded-seconds part labels strict-collapsed grid-aligned parts (SM: a 58.66%
"regression" that was a *parsing* artifact); per-voice-delay metrics masked an
inter-voice desync that global-delay metrics caught immediately (Dance
part05). Label parts in exact frames; measure later parts with global delay.

---

## Adding an entry
One screenful max: symptom → detection → exploit/fix → players seen in.
If a technique is rediscovered in a new arc, add the sighting here *in the
same commit* as the fix.
