# Galway per-frame FM / PM synth — RE'd from wizball.asm (2026-05-30)

The remaining Wizball fidelity gap is Galway's **per-frame frequency modulation**
(FM) and **pulse modulation** (PM) — the part that lives in his per-frame synth,
not in static tables. This is the "faithful FM/PM" work deferred since Stage A.
Ground truth: Martin Galway's own `wizball.asm` (`/c/Users/mit/Downloads/galway_src/`).

## What the real Wizball does (measured)

Traced song 4 (subtune idx 3) osc1 over 500 frames with the zig64 tracer:
- **ONE sustained note** the entire 500 frames (control `$D404`=`$41` written once
  at frame 0, never retriggered; zero freq jumps > 300).
- Frequency: **linear slide UP +10/frame** for ~100 frames (7967→8967), then a
  **vibrato** (±~225, ~40-frame period). The classic Galway "slide-into-vibrato".

The native driver currently plays this note at *static* pitch (plus a wrong
auto-vibrato) — so the signature Galway pitch motion is missing.

## The mechanism: an FM "offset list" (a pitch program)

Galway's voice working block (the 29-byte "Dn" struct) carries FM + PM state.
Field offsets (from `wizball.asm` EQUs, lines ~125-149):

| Off | Name   | Meaning |
|-----|--------|---------|
| 0-7 | FMG0-3 | 4 FM generators (2 bytes each) |
| 8-11| FMD0-3 | FM generator durations |
| 12  | FMDLY  | FM delay (frames before FM starts) |
| 13  | FMC    | FM control — **bit 3 set (e.g. $08) = FM enabled** |
| 14-15| PMD0-1| pulse-mod generator deltas |
| 16  | PMDLY  | pulse-mod delay |
| 17  | PMC    | pulse-mod control |
| 18,20| PMG0-1| pulse-mod generators (2 bytes each) |
| 22  | PINIT  | pulse init (12-bit start width) |
| 24  | VWF    | waveform control byte |
| 25  | VADV   | attack/decay |
| 26  | VSRV   | sustain/release |
| 27,28| VADSD/VRD | ADSR durations |

### "OFFSET LIST" FM data structure (wizball.asm:175-184)
```
 0&1  RESERVED = 0
 2&3  RESERVED = 0
 4&5  INITIAL single-offset duration counter (usually 1)
 6&7  MAXIMUM-EVER single-offset duration (1-255)
 8&9  ADDRESS OF OFFSET LIST  (read END-FIRST, BACKWARDS)
 10   RESERVED = 0
 11   MAXIMUM offset-list index (0-255)
 12   RESERVED = 0
 13   FM CONTROL — any value with bit 3 set (e.g. 8)
```
So FM = a list of **frequency offsets**, each held for a duration, walked
**backwards**, accumulated into the note frequency each frame once FMC bit3 is
set (after FMDLY). The slide (+10/frame ×100) then vibrato (±225) is this offset
list playing out. `MBendOn`/`MBendOff` commands (COM+38/36) toggle FMC (7/5) from
the sequence. Per-frame application: `TUNE`/`get.tune.data` (wizball.asm:~1110)
resets `D0+FMC`/`D0+PMC` on note start; the SOUNDn walker accumulates offsets.

PM is the same shape (PMG generators + PMD durations + PMC) driving pulse width —
this is the *generative* source of the `+8/frame` pulse ramp we currently emit as
a fixed Driver-11 pulse program.

## Implementation plan (next subsystem — sizable)

This is a per-voice **pitch program**, directly analogous to the wave/pulse/filter
program runners already in `galway_driver.asm`:
1. **Extract** per-instrument FM offset lists (+ PM generators) from the Wizball
   binary — decode the Dn block FMG/FMD/FMDLY/offset-list per instrument. The
   current extractor (`galway_1stgen_extractor.GalwayInstrument`) only pulls
   ADSR+waveform; this adds the FM/PM fields.
2. **Driver**: add an `fm_step` per-voice runner — a frequency accumulator that
   walks the offset list (backwards, duration per offset), gated by an FMC-style
   flag after a delay, adding to the base note freq before vibrato. Mirror for PM
   (replace the fixed pulse ramp with the real generator).
3. **Represent it editably** — either a new SF2 "pitch/FM" table, or map onto the
   wave-program semitone column / a Driver-11 vibrato (T1) + slide (T0) command
   where it fits. (FM offsets are finer than semitones, so a dedicated table is
   the faithful choice.)
4. **Verify** against the trace: reproduce the +10/frame slide then vibrato on the
   opening note byte-for-byte.

Estimated effort comparable to the whole wave+pulse+filter port — best started in
a fresh context. The RE (this doc) is the hard part; the runner mirrors existing
program-runner code.
