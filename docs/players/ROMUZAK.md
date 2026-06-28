# ROMUZAK player — SID → SF2 support

**Format:** ROMUZAK V6.3 (C64), by **Oliver Blasnik** / Radwar, published by Digital
Marketing, Aug 1989. An **expanded Future Composer** driver (it even ships built-in
converters *from* Future Composer and SoundMonitor), so it maps ~1:1 onto the FC
pipeline.
**Corpus:** `SID/Fun_Fun/` — **Delirious_9_tune_1** (`$2BFE`) and **Road_of_Excess_end**
(`$2C00`), both Michael Troelsen / Fun Fun. Editor + ~25 native tunes on the disk
`bin/RoMusak/romuzak v6.3 100p.d64`.
**Reference:** the official manual `bin/RoMusak/romuzak.txt` (German, V6.x + V7.9x);
the decrunched editor `out/romuzak_editor_decrunched.prg` (entry `$1000`).
**Converter:** `bin/romuzak_to_sf2.py`; tests `pyscript/test_romuzak_to_sf2.py`.
**Status:** **notes + song-order (orderlist) are byte-exact** vs the original siddump
on Delirious (osc2 92/93, osc3 113/113); plays in real SID Factory II. Sounds are
decoded structurally (arps / drums / SEEK pulse / →pulse) — **Stage A**, transpile to
the stock **Driver 11** SF2, like FC and Galway.

---

## How it was reverse-engineered

Three independent, agreeing sources (this is *not* a black box):
1. **Player disassembly** (py65 `Disassembler`) of the `$2BFE` Delirious rip.
2. **Decrunched editor** — `bin/RoMusak/romuzak    -nato.prg` (a `$0801` BASIC cruncher)
   decompressed *without VICE* by emulating the depacker in py65 (load at `$0801`, run
   from `$080B`, step until PC leaves the decruncher → editor entry `$1000`, dump
   `$0800-$FFFF`). No copy-protection issue: we never *run* the editor, just capture
   the decompressed RAM (the fake-Guru self-check only fires at runtime).
3. **The official manual** (`romuzak.txt`).

The editor's `EXTRAS/CONVERTER` contains **FUTURE COMPOSER_CNV** and **SOUNDMONITOR_CNV**
routines — literal reference mappings for both players (also useful for the separate
SoundMonitor RE of the 12 `$C000` Fun_Fun tunes).

## Memory layout (Delirious/Road rips; relocation-safe lookups)

The player is at fixed *absolute* addresses in both rips (Memory-Moved); the converter
locates the data tables by player-code **signature** (`B9 lo hi 85 F8` = `LDA tbl,Y;
STA $F8`), in code order:

| Table | Delirious addr | Find |
|---|---|---|
| TRACK (orderlist) ptrs, voice×2 | `$3640` | 1st `B9 ..,Y;STA $F8` |
| SECTOR (pattern) ptrs, sector×2 | `$3676` | 2nd `B9 ..,Y;STA $F8` |
| DRUM/ARP ptr table, B4×2 | `$2D60` | 3rd `B9 ..,Y;STA $F8` |
| SOUND table, sound×8 | `$36F6` | `sector_ptrs + 0x80` (after 64 sector ptrs) |

Player entry: **init `$8000` / play `$8003`** in the canonical build (`LDA #tune; JSR
$8000`, `$FF`=stop). The rips relocate via the Memory Mover; their wrappers differ —
Delirious `$2BFE = LDA #1; JMP $2E88` then play `$2C03 = JMP $2EB7`; Road `$2C00 = JMP
$2E88; JMP $2EB7` (no `LDA` prefix), so Road's **real play is `$2C03`, not init+5**.

## Format

**TRACK (orderlist) bytes** — per voice, terminated by `$FF`:

| byte | meaning |
|---|---|
| `$00-$3F` | play sector N (once) |
| `$40-$7F` | repeat the NEXT byte's sector `(b-$40)+1` times |
| `$80-$BF` | NOTE transpose: following notes `+ (b-$80)` semitones |
| `$C0-$FB` | SOUND transpose: following sound numbers `+ (b-$C0)` |
| `$FC xx` | goto track-byte xx | `$FD` restart-all | `$FE` stop | `$FF` restart-track |

**SECTOR (pattern) bytes** — terminated by `$FF`:

| byte | meaning |
|---|---|
| `$00-$5F` | NOTE (chromatic, `$00`=c-0 … `$5F`=b-7 → maps straight to SF2) |
| `$60-$7F` | DUR — reload value `b & $1F` (note plays **`reload + 1`** ticks/rows) |
| `$80-$9F` | PSE — pause = **`b & $1F`** ticks (fallback current DUR if 0), then **+1** |
| `$A0-$BF` | SND (sound/instrument = `b & $1F`) |
| `$C0-$DF` | SND base | `$E0 xx` GLD/APM (2-byte, 0 rows) | `$F0` CONT (+`reload+1`) |

**Durations** (RE'd from the `$2FE9/$302B/$3079` handler): a shared per-voice counter
(`$2C3E`) is reloaded on every NOTE/CONT and loaded directly by PSE; it decrements one
per tick and the event ends only when it goes **negative**, so every event lasts
`value + 1` ticks. A tick = `reload + 1` video frames (the `$2C6F` divider). The
**silent-intro** sector 00 = `8F FF` is therefore a 15(+1)-row rest, not a single row.
This makes **all three voices exactly equal-length** (synced tracks) — the prior decode
(PSE = current DUR, no `+1`, `$E0` mis-skip) left them up to ~124/463 rows apart and the
song drifted. Driver-11 plays `tempo + 1` frames/row, so the faithful **tempo = reload**
(Delirious 3, Road 2); onset timing then matches the original to a constant 2-frame
phase offset with zero drift.

**8-byte SOUND record** (≈ FC's instrument), sound table ends with 8× `$FF`:

`[B0 pulse/SEEK][B1 waveform=$D404][B2 AD][B3 SR][B4 drum/echo idx][B5 freq-vib]
[B6 pw-vib / CH80][B7 EFFECT]`

**B7 effect byte** (≈ FC mctrl):

| bit | effect |
|---|---|
| `$01` | DRUM (B4 = drumtype → `$2D60[B4]` = `(waveform,value)` seq until `$FF`) |
| `$02` | ARPEGGIO (4 semitones in the NEXT sound row, e.g. snd06 → `+12/+7/+3/+0`) |
| `$04` | ECHO | `$08` B5 mode (0=FC/1=normal) |
| `$10` | SEEK (pulse-width ramps from 0 by B0/tick) |
| `$20` | FILTER on this voice (base+add via SOUNDS/EDIT FILTER) |
| `$40` | waveform → `$41` pulse after 2 DUR | `$80` noise 1st DUR | `$C0` alternate B1/noise |

## Converter (`bin/romuzak_to_sf2.py`)

`RMZ` decodes tracks/sectors/sounds; `build_structured` emits one Driver-11 sequence
per SECTOR + a per-voice orderlist (real song patterns), reusing the FC fixed-slot
emitter + silent-intro anchors. `build_instruments` decodes the B7 effects into
wave/pulse programs (arp, drum, SEEK, →pulse). `base` is a **fixed 0** (ROMUZAK note
values ARE SF2 chromatic semitones — verified note-for-note on both tunes). `find_tempo`
derives the SF2II tempo **per tune** from the player's tick-divider reload constant
(`DEC divider; BPL; LDA #reload; STA divider`): the driver plays `tempo + 1` frames/row,
so tempo = `reload` matches the `reload + 1`-frame tick. Delirious reload `$03` → tempo 3;
Road reload `$02` → tempo 2.

Run: `py -3 bin/romuzak_to_sf2.py SID/Fun_Fun/Delirious_9_tune_1.sid out/romuzak/x.sf2`

Validate note-for-note vs the original siddump with `py -3 bin/romuzak_validate.py`
(per voice, ordered unbracketed note-onsets). Both tunes' **bass voice aligns at a
modal semitone offset of exactly 0**, the probe note-count equals the original's (faithful
timing), and **all three voices decode to exactly equal length** (synced tracks); the
all three voices decode to exactly equal length (synced tracks). osc1 over-counts only
because the silent-intro rests emit gate-off silent anchors (inaudible; an FC-style
artifact, not a pitch error — its real melody matches).

**Drum pitch**: a `$2D60` drum entry's value is the frequency HIGH byte (the player keeps
the note's freq LOW byte and rewrites the high byte per frame), mapped to the nearest PAL
semitone — NOT a semitone directly (the old decode was ~7-30 semitones off). **Arp**: the
4 offsets live in the NEXT sound record `[d0,d1,d2,d3]` (d3 = root 0) and play ROTATED
RIGHT (root-first) `[0,d0,d1,d2]`. Both verified vs the osc3 trace -> osc3 freq **26% ->
85%**, waveform **37% -> 99%**, note-onsets EXACT on both tunes.

## Native driver (Stage B — byte-100% fidelity, `drivers_src/romuzak/`)

For TRUE byte-100% the editable Driver-11 tables aren't enough: they quantise
frequency to the 96-note grid, but ROMUZAK's drums set an OFF-grid frequency
(`drum_freq = note_freq` with the HIGH byte overwritten by `table_value + B6`). So
`drivers_src/romuzak/romuzak_driver.asm` (a native SF2II driver, adapted from the
Galway one) + `bin/build_romuzak_native_song.py` write `$D400/1` directly. RE'd +
implemented this session:
- **Exact freq table** — the driver uses ROMUZAK's own `$2CA2` table (not generic
  PAL), so on-grid voices match byte-for-byte.
- **Drum high-byte wave mode** (instrument flag `$20`): `col1` is the freq high byte;
  the played high byte = `drum_table_value + B6` (the sound's byte 6), keeping the
  note's low byte.
- **Per-instrument pulse**: `INSTR_PULSE` (col4) indexes a pulse program; the width
  ramps by `B6 & $F0` per frame from a B0-derived base (SEEK = from 0 by B0), reset
  per note.

Build: `py -3 bin/build_romuzak_native_song.py [SID]` → `out/romuzak/<tune>_native.sf2`.
Verify: `py -3 bin/romuzak_native_validate.py <orig>.sid <seconds>` — a DETERMINISTIC
full-length py65 trace diff (reliable, unlike the real-time `sf2ii_vs_real`, which
drifts past ~16s). Measure within ONE song loop (Delirious loops ~110s, Road longer):
a single per-voice alignment offset can't span the loop boundary.

**Result — both tunes, full loop: freq + waveform + AD-SR = 100% on EVERY voice
(byte-perfect).** Pulse 90-97% on the melodic voices (osc1/osc2); the drum voice's
pulse is don't-care (noise). The arp is note-relative `note+[0,12,7,3]`; the drum is
`(table+B6)<<8 | note_lo`; the pulse holds a B0 base then ramps by `B6 & $F0`. Remaining
polish: the last few % of pulse, full GUI confirm in SF2II. Plan:
`docs/analysis/ROMUZAK_SF2_DRIVER_PLAN.md`.

## Open issues / TODO

- ~~**Per-tune base + tempo**~~ — **FIXED** (base 0; tempo = reload; bass validates).
- ~~**Orderlist desync**~~ — **FIXED**: sector durations (PSE = embedded `b&$1F`, all
  events `value+1` ticks, `$E0` glide = 0 rows) -> all 3 voices exactly equal length.
- ~~**Arp phase + drum pitch**~~ — **FIXED** (drum value = freq high byte; arp rotated
  root-first). osc2/osc3 now ~99%/EXACT.
- **Remaining sound fidelity**: ±1-semitone drum jitter (the low-byte is approximated),
  pulse-width MODULATION (B5/B6 vibrato), CONT/GLD/APM glides, and B7 bit5 FILTER (none
  in Delirious). Optional: trace-driven pulse/filter (`fc_to_sf2._trace_*`).
- **The other Fun_Fun players**: 12 are SoundMonitor (`$C000`), 1 unknown (Byte_Bite).
  ROMUZAK's `SOUNDMONITOR_CNV` is a reference for that RE.

See the `romuzak-player-re` memory for the full RE trail.
