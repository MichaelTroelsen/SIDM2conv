# ROMUZAK native SF2 driver — plan (byte-100% fidelity, editable)

**Goal:** A purpose-built SID Factory II driver (descriptor type 0x00) that runs
ROMUZAK's real per-frame engine, driven by EDITABLE SF2 tables, reaching byte-100%
fidelity vs the original SID on both corpus tunes (Delirious, Road_of_Excess).

**Why native (not Stage-A Driver-11):** the editable Driver-11 wave table quantises
frequency to the 96-note PAL grid. ROMUZAK's drums set an arbitrary frequency (the
drum table value is the freq HIGH byte; the LOW byte is the note's) → off-grid → a
static table can't emit them. A native driver writes `$D400/1` directly, so it can.

## Strategy: adapt the proven Galway native driver

The Galway driver (`drivers_src/galway/galway_driver.asm`, build
`bin/build_galway_driver_full.py`) already implements, and is validated for, the entire
SF2II contract we need: the descriptor/Block-1..5 headers, the `$16cc-$1702`
playback-state region, the 3-voice orderlist→sequence sequencer, and STANDARD SF2II
table interpreters — `wave_step` (col-major 256×2: waveform + semitone-offset/abs,
`$7f`=jump), `pulse_step` (row-major 3-byte: set/add/freeze), `filt_prog_step` (global
filter), `fm_step` (per-frame freq offset). The build pipeline regenerates `layout.inc`
+ `freqtable.inc`, assembles with 64tass, wraps the SF2, and headless-validates.

**ROMUZAK reuses all of that.** The only genuinely new pieces:

1. **Exact freq table.** Use ROMUZAK's own note→freq table (`$2CA2` in the rip,
   2 bytes/note) as the driver `freqtable.inc` → melody + arp frequencies match the
   original byte-for-byte (they're on-grid).
2. **Drum "set-freq-high-byte" wave mode.** Add a `wave_step` convention: a wave-table
   row whose col0 carries a DRUM flag means "write col1 directly to the freq HIGH byte
   ($D401), keep the running LOW byte" instead of resolving a semitone. Reproduces the
   ROMUZAK drum exactly (the value IS the high byte). This is the one thing Stage-A
   could not do.
3. **Map ROMUZAK effects onto the existing runners** — arp → `wave_step` semitone
   rows; SEEK / pulse-width → `pulse_step`; `WF→pulse` → `wave_step` waveform change;
   freq/pulse vibrato (B5/B6) → `fm_step` / `pulse_step`; filter (B7 bit5) →
   `filt_prog_step`. No new engines needed.

The native driver reads the SAME SF2-standard editable tables that the current Stage-A
`bin/romuzak_to_sf2.py` already emits (wave/pulse/filter/instruments/orderlist/
sequences), so the song-builder is largely the existing decode + table emission.

## Stages

- **B0 — scaffold + load.** Copy the Galway driver/build to `drivers_src/romuzak/` +
  `bin/build_romuzak_driver_full.py`; strip the digi engine (ROMUZAK has no $D418
  samples); swap in ROMUZAK's `$2CA2` freq table. Build a test pattern; confirm it
  assembles, wraps a valid SF2, and headless-plays. *(this turn)*
- **B1 — real song.** `bin/build_romuzak_native_song.py`: feed the existing
  `romuzak_to_sf2` decode (orderlist + sectors + instruments + wave/pulse) into the
  native tables. Melody + arps play; verify osc2/osc-melody byte-match vs the rip.
- **B2 — drums.** Add the drum-high-byte wave mode; emit drum programs as high-byte
  rows. Verify osc3 drum frames now byte-match (the ±1/-8 residual → 0).
- **B3 — remaining timbre.** SEEK/pulse-width, freq/pulse vibrato (B5/B6), CONT/GLD
  glide, B7-bit5 filter (none in Delirious, but Road/D64 tunes use them).
- **B4 — validate byte-100%.** `sf2ii_vs_real.py` on both tunes → 100% on every
  register; confirm in the SF2II GUI (loads, plays, tables editable & affect playback).

## Verify each stage
`py -3 bin/sf2ii_vs_real.py SID/Fun_Fun/<tune>.sid out/romuzak/<tune>.sf2 14`
(per-voice freq/waveform/pulse/AD-SR % vs the real SID, via the instrumented
`bin/SIDFactoryII_dbg.exe`). Headless audio check is built into the full builder.

## Gotchas (from the Galway build, carry over)
- Keep code/tables OUT of `$16cc-$1702` (SF2II playback-state; silent corruption).
- Cap each packed sequence < ~960 unpacked events (SF2II's 1024 Unpack buffer; no
  bounds check → heap corruption/hang).
- Split note/command on the HIGH BIT first; never `cmp` values >$7f apart (SF2II's
  6510 CMP-carry bug).
- 6502 branch range ±128: use `jmp` to re-enter long loops.
- SF2II reads sequences from FIXED editor slots, not the pointer table — write each
  packed sequence into its own `sequence_start + idx*stride` slot.
- `STY abs,x` is invalid; long routines overflow `bpl`/`bne` (near-branch + `jmp`).

## Source of truth for the ROMUZAK format
`docs/players/ROMUZAK.md` + the `romuzak-player-re` memory + `bin/romuzak_to_sf2.py`
(orderlist/sector/sound decode, all RE'd & validated this session). Freq table `$2CA2`
(2 B/note); note-setup engine `$30EB` (reads the 8-byte sound from `$36F6`).
