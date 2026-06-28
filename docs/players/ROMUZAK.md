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
| `$60-$7F` | DUR (note length = `b & $1F`, 01-20) |
| `$80-$9F` | PSE / pause |
| `$A0-$BF` | SND (sound/instrument = `b & $1F`) |
| `$C0-$DF` | SND base | `$E0 xx` GLD/APM (1 param) | `$F0` CONT (extend last note) |

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
(`DEC divider; BPL; LDA #reload; STA divider`): tick = `reload + 1` frames, tempo =
`reload + 2`. Delirious reload `$03` → tempo 5; Road reload `$02` → tempo 4.

Run: `py -3 bin/romuzak_to_sf2.py SID/Fun_Fun/Delirious_9_tune_1.sid out/romuzak/x.sf2`

Validate note-for-note vs the original siddump with `py -3 bin/romuzak_validate.py`
(per voice, ordered unbracketed note-onsets). Both tunes' **bass voice aligns at a
modal semitone offset of exactly 0**; the lead voices over-count because arps/drums
emit extra onsets (see Sound fidelity below).

## Open issues / TODO

- ~~**Per-tune base + tempo**~~ — **FIXED**: base is a fixed 0 and tempo is derived
  per-tune from the tick-divider reload (Road now tempo 4, base 0; bass validates).
- **Sound fidelity**: arp *phase* + drum *pitch* are Stage-A-approximate (per-frame
  effects, same limit as FC); add the **trace-driven pulse/filter** (`fc_to_sf2.
  _trace_pulse_programs` / `_trace_filter_program`) and tune the arp order.
- **The other Fun_Fun players**: 12 are SoundMonitor (`$C000`), 1 unknown (Byte_Bite).
  ROMUZAK's `SOUNDMONITOR_CNV` is a reference for that RE.

See the `romuzak-player-re` memory for the full RE trail.
