# Sound Monitor (Musicmaster) player — SID → SF2 support

**Format:** **Sound Monitor** by **Chris Hülsbeck** (1986, published as the 64'er
magazine "Listing of the Month" — an 11 KB hex dump readers typed in by hand). The
driver self-identifies as **"MUSICMASTER CREATED BY CHRIS HUELSBECK"** (ASCII at
`$CBD4`; truncated away in some rips). One of the most influential C64 editors —
RockMonitor and many others descend from it.
**Composer / corpus:** `SID/Fun_Fun/` — **11 files** by Michael Trolle/Fun Fun
(Dance_at_Night_remix, Dreamix, Dreamix_Two, Final_Luv, Fuck_Off, Fun_Mix,
Just_Cant_Get_Enough, No_Title, Poppy_Road, Thats_All, Times_Up), all
`init=$C000 / play=$C475`. `Demo_of_the_Year_87_menu` is a `$C020` variant (open).
**Ground truth:** the player disassembly itself (`bin/_sm_disasm.py`, untracked) +
the real editor binary `bin/sound monitor/soundmonitor 1.1.prg` (untracked).
**Parser:** `sidm2/soundmonitor_parser.py`; tests `pyscript/test_soundmonitor_parser.py`.
**Stage A:** `bin/soundmonitor_to_sf2.py` → editable Driver-11 SF2 (+ validator
`bin/soundmonitor_sf2_validate.py`, smoke tests `pyscript/test_soundmonitor_to_sf2.py`).
**Stage B:** `bin/build_soundmonitor_native_song.py` (SMShim → the shared MoN native
pipeline). Output `out/soundmonitor/`. `bin/` only, not registry-wired.

**Status (2026-07-10, all in one day):** format fully RE'd; parser onset-validated
**99.9% corpus-wide** (10/11 files 100%); Stage A **32/33 voices note-accurate**;
Stage B first cut: **Final_Luv = the whole 161s song in ONE part at 98.1-99.9
skew-tolerant on every register (filter 99.9)**; Dance ~100% audible (the whole
residual = the 91-frame silent intro); Dreamix osc3 (legato+glide) and Fuck_Off osc2
(mixed legato) are the open voices.

---

## How it was reverse-engineered

Direct disassembly of the rip (the ROMUZAK editor's `SOUNDMONITOR_CNV` reference was
a dead end — its menu table is walked positionally with no chaseable code pointer).
The whole 11-file cluster shares **byte-identical player code at a fixed load**
(`$C000-$CBFA`) — only two per-song constants (`$C010/$C011`) and the trailing song
data differ — so every table lives at a **hardcoded absolute address**: no
signature/relocation machinery needed (the opposite of Hubbard/DMC).

## Format model — ROW → BAR → (ctrl, data) steps

**ROW (song step)** — the top-level structure, advanced LINEARLY with natural 8-bit
wraparound (`$02C1` is a plain `INX`; `row_start > row_count` is normal — Fun_Mix
runs rows 247→255→0→164). Per row, indexed directly by row number:

| Table | v0 | v1 | v2 | Meaning |
|---|---|---|---|---|
| BAR ptr lo/hi | `$A000/$A100` | `$A400/$A500` | `$A800/$A900` | pattern data for this row |
| NOTE transpose | `$A200` | `$A600` | `$AA00` | added to notes (semitones) |
| SOUND transpose | `$A300` | `$A700` | `$AB00` | added to instrument numbers |

Shared: `ROW_HDR` ptr (`$AC00/$AD00`) → header record: byte2=SPEED (s+1
frames/step), byte3=LENGTH (steps/row), byte4=volume-fade speed, byte5&$0F=volume.
**Past the 6 fixed bytes the header record is a BANK of 8-byte CHORD TABLES**
(`0C 07 04`=major, `0C 07 03`=minor, `0C 00 0C 00…`=octave) — the arpeggios.
Song constants: `ROW_COUNT=$C010`, `ROW_START=$C011`. Sound table `$AE00`
(24-byte records). Freq tables `FREQ_LO=$C416 / FREQ_HI=$C3B7` (note index → SID
freq; SM note index = SF2 chromatic semitone, no calibration).

**BAR** = LENGTH × (ctrl, data) byte pairs, one pair per step (all 3 voices step
synchronously on the row's speed clock):
- `ctrl $00` = REST — writes the current instrument's **byte-8 release waveform**
  to the WF register. For most instruments that is gate-off (`$40/$80/$00`), but a
  GATED release wf (`$11/$81`) keeps the voice ringing through "rests".
- `ctrl $80` = TIE (hold, no event).
- else NOTE: `note = (ctrl & $7F) + row-note-transpose`; ctrl bit7 = trigger flag
  (bit7 clear = legato pitch-set). The envelope only restarts if the gate was
  actually off (SM never writes gate-off except via REST).
- **data flags:** `$0F` instrument (masked BEFORE the sound-transpose add — effective
  indices exceed 15), `$10` GLIDE (portamento from the previous pitch), `$20`
  suppress note-transpose, `$40` ARPEGGIO on, `$80` suppress sound-transpose.

**ARPEGGIO engine** (`$CB65/$CB8A` — initially mistaken for a digi player): per
frame, cycle = `(cycle+1) & 7`, semitone offset = `header[base + cycle]` where
**base = the LAST data byte of the voice's bar**; played freq = freq-table[note +
offset]. The chord bank lives inside the row-header record (above).

**PULSE engine** (`$C31B` — initially mislabeled a freq bend): the dispatcher passes
**Y=2/9/16**, so its `STA $D400,Y` writes land on the PULSE registers. Triangle PWM:
add `$CDAE,X` per frame for `$CDA8,X` frames, then subtract for `$CDAB,X`
(reloads = rec[5]/rec[6]); enabled by rec[9] & $10; runs continuously, including on
idle voices (the init `$810→$848` sweep).

**24-byte SOUND record** (base = `$AE00 + instr*24`): byte0=waveform, byte1=AD,
byte2=SR, byte3→`$CD85`, **byte4 = pulse width nibble-swapped** (`lo=(b4<<4)&$FF,
hi=b4>>4`; `$80`→`$800`), byte5/6=PWM up/down counts, byte8=release waveform,
byte9=effect flags (`$10`=PWM on), byte10=glide gate, byte11→`$CD8A`,
byte12=vibrato depth (`$CD98`), byte13=vibrato ctrl (`$CD95`), bytes16-23 =
FF-terminated extension block (copied only if byte16≠$FF; role partly open).
Bytes 7/14/15 not yet pinned.

Other engine facts: `$CA17` = ZP save/swap (`$A5-$AC` ↔ `$07E9`, BASIC safety);
`$CA2B` = master volume fade; `$C1BE/$C1E3` = freq vibrato (Y=0/7/14);
`$C034/$C098` = glide toward target; `$C25F` = filter cutoff sweep (`$D415/16`).

## Stage A — Driver-11 transpile (editable)

SM maps nearly 1:1 onto Driver 11: **1 step = 1 row**, note index = SF2 semitone
(base 0), row speed = tempo (uniformly 2 on this corpus). Per-note arps → one
Driver-11 instrument per (sound record, arp table) combo with an 8-row wave
program; combos over the 32-slot cap drop their arp to the plain timbre with a loud
warning (only Dance's 51 combos exceed it). Gated-release rests → sustain rows.

**GOTCHA (locked by a regression test): the runtime Driver 11 does NOT parse
`$90-$9F` tie durations.** They are an editor-only feature
(`datasource_sequence.cpp`); emitting them desyncs the driver's sequence reader
into garbage pitches/noise. Stage A therefore re-gates legato notes.

Validation (`bin/soundmonitor_sf2_validate.py`, order-preserving coverage):
**32/33 voices note-accurate** (13 EXACT; the rest = every original attack present
in order at the right pitch). Residual: Times_Up osc2 attack +1 semi (instr 3's
bend fields).

## Stage B — native driver (the shared MoN pipeline)

`SMShim` (the DMCShim pattern): notes ONSET-ALIGNED at exact emulated `$D404`
gate-rise frames (`sidm2.dmc_parser.measure_onsets` — player-agnostic; agrees
74-138/138 with siddump on every file), pitch trace-resolved (`_sem` with the FM
`$40-$43` collision guard), per-voice **legato A/B** (gate vs decode schedule —
Dreamix osc3 38.3→87.3, Fuck_Off osc3 11.5→89.3, both auto-picked), **TIE splits**
at decode note boundaries that lack a gate-rise (mixed-legato voices; the
Supremacy `$FB` mechanism re-seats pitch without re-gating), adaptive
part-splitting (63-bundle/32-instrument caps).

First-cut fidelity (`bin/mon_part_fidelity.py`): Final_Luv ONE part / 161s at
98.1-99.9 skew-tolerant everything; Dance ~100% audible after its silent intro;
captured pulse reproduces the triangle PWM at a 1-frame skew (strict % misleading,
skew-tolerant = audibly exact — the accepted Supremacy class).

## Open items

- Fuck_Off osc2 (mixed legato — tie-splits shipped, verify), Dreamix osc3
  (legato+glide residual class, same as DMC Dreaming).
- The idle/intro divergence (orig idles wf=00 with its init pulse sweep; the driver
  idles differently — inaudible, costs a few strict % on late-entering voices).
- Sound-record bytes 7/14/15 + the 16-23 extension block; the editor binary
  (`bin/sound monitor/soundmonitor 1.1.prg`) is the ground-truth shortcut.
- The `Demo_of_the_Year_87_menu` `$C020` variant.
- Registry-wiring into auto `sid-to-sf2` (with the other native players).

## Dead ends (do not retry)

- Chasing `SOUNDMONITOR_CNV` inside the ROMUZAK editor dump — the menu text is
  walked positionally; no code pointer to find. Disassembling the SM player
  directly was faster.
- The credit string as the detection signature — Final_Luv's rip is truncated at
  exactly `$CBD4` where it starts. Use the play-routine byte signature.
- Emitting `$90-$9F` tie bytes to Driver 11 (see the Stage A gotcha).
- Treating header byte4 as a next-row chain pointer — row order is linear
  (with 8-bit wraparound); byte4 is the volume-fade speed.
