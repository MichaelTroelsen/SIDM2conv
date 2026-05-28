# Martin Galway "1st-Generation" Player — Engine Map

**Status:** Reverse-engineered from the author's own commented source
(github.com/MartinGalway/C64_music), 2026-05-28. Checkpoint deliverable —
**not yet wired into conversion**. Source-of-truth for the Galway 1st-gen
detector (`sidm2/galway_1stgen_detector.py`) and any future extractor.

Line citations below refer to `wizball.asm` (the canonical 1st-gen
reference). Cross-validated against `arkanoid.asm`, `gameover.asm`,
`greenberet.asm` (full engine) and `rambload.asm` (same VM, minor label
differences). `arkadrum.asm` is an Arkanoid drum-overlay fragment, not a
standalone player.

> **Generations.** Galway used a "1st-gen" player (design 1984–mid-1987:
> Wizball, Arkanoid, Green Beret, Game Over, Rambo) and a "2nd-gen" player
> (first on Athena; later Times of Lore, Insects in Space). This document
> covers ONLY the 1st-gen. The 2nd-gen source is not in the repo.

---

## 1. Architecture in one paragraph

The 1st-gen player is **not table-driven** (unlike SF2 Driver 11 / Laxity
NP21). Each of the 3 SID voices runs an independent **bytecode interpreter**
over a per-channel command stream addressed by a zero-page program counter
(`PC0/PC1/PC2`). The stream mixes *note records* (2 bytes: note + duration)
and *commands* (≥ `$C0`, variable length) including subroutine call/return,
for/next loops, transpose, volume/instrument loads, pulse/filter/frequency
modulation setup, and inline native code. A separate per-voice **synth
stage** (`SOUNDn`) runs every frame to apply ADSR gating and frequency/pulse
modulation, writing the SID voice registers. A **filter engine** runs a
small filter "program". Because the music is an executed program (with
loops, calls, inline code, and self-modifying pokes), it **cannot be losslessly represented as flat instrument/wave/pulse/filter arrays** — which
is why a Driver-11 table remap is fundamentally lossy, and why audio-correct
conversion must embed the real player.

---

## 2. Per-frame flow

`REFRESH` (wizball.asm:576) is the play routine body, run once per refresh
(the player is multi-speed; `RF` / `ClkAdd` gate how many times per raster):

```
REFRESH:
  JSR FILTER                 ; filter cutoff sweep engine -> $D415-$D418
  (if CH0VALUE) JSR MUSIC0 ; sequencer voice 0
                JSR SOUND0 ; synth     voice 0  -> $D400-$D406
  (if CH1VALUE) JSR MUSIC1 / JSR SOUND1            -> $D407-$D40D
  (if CH2VALUE) JSR MUSIC2 / JSR SOUND2            -> $D40E-$D414
```

- **MUSICn** = the bytecode sequencer (advances `PCn`, triggers notes,
  executes commands, sets the duration counter `CLOCKn`).
- **SOUNDn** = the per-frame synth (envelope gate/release timing + FM/PM
  modulation), writes the voice registers.
- **FILTER** (wizball.asm:1725) = runs the 16-byte filter program loaded
  into `CUTST` by the `Filter` command.

---

## 3. Zero-page / workspace layout (wizball.asm:46-95)

Three ZP regions (`ZERO0=$04`, `ZERO1=$29`, `ZERO2=$87`) — exact addresses
vary per file; structure is constant.

| Symbol | Size | Meaning |
|--------|------|---------|
| `PC0/PC1/PC2` | 2 each | per-voice command-stream program counter (read via `(PCn),Y`) |
| `CLOCK0/1/2` | 1 each | per-voice duration countdown (note plays until it hits 0) |
| `SP0/1/2` | 1 each | per-voice stack pointer into `STnL/STnH/STnC` (call/for stacks) |
| `TR0/1/2` | 1 each | per-voice transpose offset (added to note before freq lookup) |
| `MFL0/1/2` | 1 each | per-voice music-active flag (0 = channel silent/done) |
| `CUTST` | 16 | active filter program (working copy) |
| `CUT` | 22 | filter modulation control block |
| `IN`/`OUT` | 2 each | scratch indirect pointers |

`DEPTHOFSTACKS = 5` → call/loop nesting depth 5. Per-voice stacks:
`STnL` (return-addr lo), `STnH` (return-addr hi), `STnC` (for/next counter),
5 entries each.

Per-voice **data blocks**:
- `D0/D1/D2` (29 bytes each) — the *instrument/modulation definition* block
  the stream pokes into (the "patch").
- `S0/S1/S2` (35 bytes each) — the *working* synth block `SOUNDn` runs from
  (copied/derived from `Dn` when a note triggers).
- `DTAB` (wizball.asm:1066) = `DFL D0-D0, D1-D0, D2-D0` — per-voice byte
  offset of each `Dn` block (used to index by channel).

---

## 4. Instrument / modulation block field offsets (wizball.asm:125-173)

Offsets into a `Dn`/`Sn` block. FM = frequency modulation (vibrato/slide),
PM = pulse-width modulation, V = voice waveform/ADSR.

| Offset | Sym | Field |
|--------|-----|-------|
| 0,2,4,6 | `FMG0..FMG3` | FM generator words (4) |
| 8-11 | `FMD0..FMD3` | FM data |
| 12 | `FMDLY` | FM delay |
| 13 | `FMC` | FM control/counter |
| 14-17 | `PMD0/PMD1/PMDLY/PMC` | PM data/delay/control |
| 18,20 | `PMG0/PMG1` | PM generator words |
| 22 | `PINIT` | initial pulse width (-> $D402/$D403) |
| 24 | `VWF` | waveform byte (-> $D404 control) |
| 25 | `VADV` | attack/decay (-> $D405) |
| 26 | `VSRV` | sustain/release (-> $D406) |
| 27 | `VADSD` | AD sustain-duration counter seed |
| 28 | `VRD` | release-duration counter seed |

`Sn` adds working/counter fields (`VWFG`,`VADSC`,`VRC`,`FMxC`,`PMxC`,
`FOLB`...) beyond offset 28 — that's why `Sn` is 35 bytes vs `Dn` 29.

---

## 5. Command stream encoding

`read.byte0` (wizball.asm:1820) fetches `(PC0),Y=0` and branches on `$C0`:

### 5a. Notes & rests (byte < `$C0`)
Two-byte record: **`[note-byte][duration-byte]`**.
- `R = $60`, `Rest = $5F`. Bytes `$60..$BF` are the "no-restart" note range
  (`SBC #R` → same pitch class, different articulation flag tested later for
  the FOLB/legato path). Bytes `$00..$5F` are normal notes; `$5F` = Rest.
- Pitch = `note + TRn` (transpose) → index into `LoFrq,X`/`HiFrq,X`.
- `RF AND #1` gates whether a fresh note actually retriggers this tick
  (multi-speed handling).
- **Duration byte**: if the note byte < `$60`, the duration byte is an
  *index* into `IDRT` (`LDA IDRT-1,X`); otherwise it's used raw. Result →
  `CLOCKn`. PC advances by 2.

### 5b. Commands (byte ≥ `$C0 = COM`)
Dispatch is **direct-indexed** into a per-voice jump table `vtn`
(wizball.asm:989/1011/1033). The command byte equals `COM + 2*k`, and each
`vtn` entry is a 2-byte `DFW`, so `vtn + (cmdbyte - COM)` is the handler
pointer. The fetch reads the **next** stream byte into `A` as the handler's
first operand, then `JMP (vtn-computed)`.

Opcode table (offset from `COM=$C0`; vt index = offset):

| Byte | Name | Handler | Effect |
|------|------|---------|--------|
| `$C0` | `Ret` | `retsubrutn` | pop call stack → PC; if stack empty, `DEC MFLn` (voice ends) |
| `$C2` | `Call` | `calln` | push PC+3, load 2-byte target → PC |
| `$C4` | `Jmp` | `goton` | load 2-byte target → PC (no push) |
| `$C6` | `CT` | `calltn` | set `TRn`=operand, then `Call` |
| `$C8` | `JT` | `gototn` | set `TRn`=operand, then `Jmp` |
| `$CA` | `Moke` | `mpoken` | poke 1 byte → `Dn`+operand (3-byte cmd) |
| `$CC` | `For` | `forn` | push PC+2 + loop count (`STnC`) |
| `$CE` | `Next` | `nextn` | dec loop count; loop back or pop |
| `$D0` | `FLoad`| `floadn` | copy a byte run from a table → `Dn` |
| `$D2` | `Vlm` | `volumen`| copy 5 bytes (`VWF..VRD`) from operand ptr → `Dn` (set instrument) |
| `$D4` | `Soke` | `spoken` | poke 1 byte → `Sn`+operand |
| `$D6` | `Code` | `coden` | `JMP (operand)` — inline native code, returns to add3cn |
| `$D8` | `Transp`| `transpn`| set `TRn` = operand |
| `$DA` | `DMoke`| `dmpoken`| poke 2 bytes → `Dn`+operand |
| `$DC` | `DSoke`| `dspoken`| poke 2 bytes → `Sn`+operand |
| `$DE` | `Master`| `mastern`| master volume / filter routing → `$D417`,`$D418` |
| `$E0` | `Filter`| `filtern`| copy 16-byte filter program → `CUTST` |
| `$E2` | `Disown`| `disownn`| release filter ownership |
| `$E4` | `MBendOff`| `mbendoffn` | master bend (vibrato) off |
| `$E6` | `MBendOn` | `mbendonn`  | master bend on |
| `$E8` | `Freq` | `freqn` | copy 14 bytes → `Dn` (FM/freq-mod setup) |
| `$EA` | `Time` | `timen` | (vt2 only) tempo/timing |

Not all voices implement all commands: `vt1`/`vt2` route some entries to
`HANG1`/`HANG2` (e.g. no `Master`/`Filter` on voice 1). Control-flow (`Call`/
`Ret`/`For`/`Next`/`Jmp`) + the `Code` inline-native-code escape are why this
is a true interpreter, not a table.

---

## 6. Note trigger path → SID anchors (wizball.asm:1841 `NOTE0`)

```
LDY HiFrq,X / LDA LoFrq,X      ; freq from note index X
STA $D400 / STY $D401          ; <-- voice-0 frequency (FIXED ANCHOR)
LDX D0+PINIT / LDY D0+PINIT+1
STX $D402 / STY $D403          ; pulse width
LDA D0+VADV  -> $D405          ; attack/decay
LDA D0+VSRV  -> $D406          ; sustain/release
... waveform -> $D404
JSR transferpm0a               ; seed PM working state
... copy D0[0..12] -> S0       ; seed FM working state for SOUNDn
```

Voice register bases: V0 `$D400`, V1 `$D407`, V2 `$D40E`. Filter/vol
`$D415-$D418`. `SOUNDn` (wizball.asm:2242) then runs the envelope state
machine (`$D404` gate) and FM/PM each frame.

---

## 7. Tune table (song entry points) — wizball.asm:2772 `TUNETABLE`

**7-byte records**, one per tune: `DFW ch0PC, ch1PC, ch2PC` (3×2 bytes) +
`DFL durbase` (1 byte). `TUNE` (wizball.asm:1110) is entered with
`Y = tune*7 - 2`; it loads the three channel PCs into `PC0/1/2`, seeds
`SPn=DEPTHOFSTACKS-1`, `CLOCKn=1`, `MFLn=1`, zeroes `TRn`, and runs
`CalcDurations` to fill the 32-entry `IDRT` duration table from `durbase`
(a running `ADC durbase`). Unused channels point to `Texit` (silent stub).

`INITSOUND` (wizball.asm:1092) clears `$D400-$D417` with a distinctive
double-store loop (`LDA #8; STA $D400,X; LDA #0; STA $D400,X; DEX; BPL`) and
zeroes the per-voice flags. In a shipped SID this is the `init` entry body.

---

## 8. Frequency tables (wizball.asm:190-272, 1067-1088)

`N00..N89` (+ `NSil`) are 16-bit PAL frequency values. Stored split:
`LoFrq = DFL N00..` (low bytes), `HiFrq = DFH N00..` (high bytes), indexed by
note number. NTSC table also present (commented region ~285). ~90 chromatic
notes + silence.

---

## 9. Deterministic detector signatures

Robust because the VM code is shared across all 1st-gen files (only operands
— ZP addrs and table addresses — vary). Recommended signatures (operands
wildcarded as `??`):

1. **Dispatch idiom** (`read.byteN`, strongest). Universal prefix
   `C9 C0  90 ??` (`CMP #$C0 / BCC`) + one of three variant tails (the VM
   code is shared; only operands vary across files):
   - `indirect` — computed `JMP (vt0)` (self-modifies the operand low byte):
     `ADC #imm`+`STA abs`+`JMP (ind)` in a short window; `INY` precedes the
     ADC (`C8 69 ?? 8D ?? ?? [B1 ??] 6C ?? ??`, Wizball/Arkanoid) or follows
     the STA (`69 ?? 8D ?? ?? C8 6C ?? ??`, Parallax). `vt0` = `6C` operand.
   - `indexed` — `AA BD ?? ?? 8D …` (`TAX / LDA vt0-192,X`). `vt0` = that
     `LDA abs,X` operand **+ `$C0`**. (Green Beret)
   - `masked` — `29 3F AA BD ?? ?? 8D …` (`AND #$3F / TAX / LDA vt0,X`).
     `vt0` = that `LDA abs,X` operand **directly**. (Rambo)
2. **Note freq write** (`NOTE0`):
   `BC ?? ??  BD ?? ??  …  8D 00 D4  8C 01 D4`
   = `LDY HiFrq,X / LDA LoFrq,X / … / STA $D400 / STY $D401`. The two indexed
   loads give **`HiFrq`/`LoFrq`** addresses.
3. **INITSOUND reset loop**: `A9 08 9D 00 D4 A9 00 9D 00 D4 CA 10 ??`.

Detection = (dispatch idiom) AND (note-freq idiom); the init loop raises
confidence to "high". **Do NOT validate addresses against `[load, load+len]`**
— several files self-relocate (Game Over loads $0F00 / runs $E000; Rambo
loads $6F00 / runs $2A00), so `vt0`/`LoFrq`/`HiFrq` are RUNTIME addresses
that may sit outside the load range; their mutual consistency is the signal.

From these the detector reports the (runtime) `vt0`, `LoFrq`/`HiFrq`, and
`INITSOUND`/init. Walking the `TUNE` routine to recover `TUNETABLE` is a
future step. The PSID header already provides init/play.

Implemented in `sidm2/galway_1stgen_detector.py` (`detect_galway_1stgen`);
validated over `SID/Galway_Martin/` — 21/40 detected (all three variants),
the 3 known 2nd-gen files correctly rejected.

---

## 10. Implications for SIDM2

- **Audio:** correct playback needs the real player embedded (the proven
  minimal-embed / Laxity-raw approach). No table remap can reproduce loops,
  calls, inline `Code`, or the FM/PM/filter modulation faithfully.
- **Editor (SF2 C3):** mapping the bytecode to SF2 patterns/instruments is
  the hard, source-driven part. The note-record stream (note+duration) and
  the `Vlm`/`Freq`/`Filter` instrument loads are the most SF2-mappable;
  `Call/For/Code`/self-modifying pokes have no SF2 equivalent.
- The current `sidm2/galway_*` table-extract pipeline models a flat-table
  player this engine is not — it should be treated as a stub, not a base to
  extend.
