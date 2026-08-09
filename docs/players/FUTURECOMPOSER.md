# Future Composer player — SID → SF2 support

**Format:** Future Composer (C64), player by "The Beat-Machine" — FC **V1.0** (the
on-disk editors span V1.0 / V2.0 / V3.1 / V4.1).
**Corpus:** `SID/Fun_Fun/` (Michael Troelsen / Fun Fun) + native modules on the FC
disk (`bin/FC10/futurecomposer + acid demo/...D64`).
**Reference:** `bin/FC10/Futurecomposer Instructions.txt` (V4.1 manual — note the
sound-parameter byte order differs from V1.0, see below).
**Converter:** Stage A `bin/fc_to_sf2.py`, **Stage B `bin/build_fc_native_song.py`**
(+ `sidm2/fc_parser.py`); tests `pyscript/test_fc_parser.py`,
`pyscript/test_fc_native_song.py`.
**Status:** Stage A — **notes / orderlist / patterns / arps / drums / tempo are
byte-exact** vs the original on the **arp + bass** voices in real SID Factory II;
its one open defect is that a voice with a **long silent intro** (Triangle_Intro's
lead, muted 288 ticks) does not gate under SF2II's Driver 11 (see *Open issues*).
**Stage B (native, shipped 2026-07-30) removes that constraint** — it writes its
own sequencer, so all-rest sequences and long rest prefixes are simply not a
problem — and reaches **14 of 15 corpus voices at exactly 100.0% audible
per-frame pitch over full song length** (below). Current headline figures:
`docs/reference/ACCURACY_MATRIX.md` (canonical; verified to match this doc 2026-08-09).

---

## How Future Composer is converted

FC is a **flat table-driven** player (unlike Galway's bytecode interpreter), so the
score can be read statically from the player embedded in the SID rip. Pipeline:

1. **`sidm2/fc_parser.py`** decodes the FC tables (orderlists, blocks/patterns,
   8-byte instruments, 96-entry PAL freq table, drum tables) into an IR.
2. **`bin/fc_to_sf2.py`** transpiles to a Driver 11 SF2, reusing the Galway IR
   (`GalwayDriver11Song`) and emitter (`sidm2/galway_driver11_emitter.py`).

Run: `py -3 bin/fc_to_sf2.py SID/Fun_Fun/Triangle_Intro.sid out/Triangle_Intro.sf2`
(also accepts a raw `.prg` native FC module).

---

## Stage B — the native driver path (`bin/build_fc_native_song.py`, R13, 2026-07-30)

FC was the **last ported player without a native driver**, and was picked as the
test that the R1–R3 consolidated pipeline generalises to a new player. It does:
Stage B added **no new driver and no new engine code**. A MON-compatible shim
(`FCShim`) feeds `bin/build_mon_native_song.build_native_song` — the same
trace-driven engine behind Hawkeye / Hubbard / DMC / Sound Monitor / SDI — and
`emit_one` assembles MoN's driver. Arps, drums and PWM therefore arrive from the
**per-frame capture** instead of being modelled, which is the PLAYBOOK §2
"parse statically, trace the synth side" split. That is the right mode for FC
precisely because its parser is already validated byte-exact (`fc_validate`:
25/27 voices note-accurate; the FC→FC round-trip is byte-identical in siddump),
so — unlike the SDI/DMC shims — notes are **decode-driven**, not re-derived from
trace gate-rises. Re-deriving them would also have thrown away the rests, which
is the whole reason to build FC natively.

    py -3 bin/build_fc_native_song.py SID/Fun_Fun/Triangle_Intro.sid auto
    # -> out/fc/<name>_part<NN>.sf2   (FC_MAX_PARTS=n caps the split)

### Corpus result — full song length, not a window

| tune | parts | v0 audible | v1 audible | v2 audible |
|------|------:|-----------:|-----------:|-----------:|
| Triangle_2_years | 4 | **100.0** (1061) | **100.0** (346) | **100.0** (742) |
| Carillo_part_2 | 4 | **100.0** (778) | **100.0** (474) | **100.0** (366) |
| Demo_of_the_Year_88_Elite_1997 | 3 | **100.0** (1212) | **100.0** (592) | **100.0** (2253) |
| Is_There_a_Difference | 5 | **100.0** (466) | **100.0** (1079) | **100.0** (554) |
| Triangle_Intro | 3 | **100.0** (870) | **83.6** (633) | **100.0** (1011) |

**14 of 15 voices at exactly 100.0%**; `(n)` = audible frames compared. Note
placement is independently **frame-exact**: the decode's predicted onset frames
equal the trace's own gate-rise frames exactly (v1: `576, 684, 696, 708, 720,
732, 768, 864…` in both), at alignment delay **+0**.

### Read the two columns, not one — both mislead alone

The builder prints **raw** and **audible (gate-on)** per voice, because:

- **Raw understates, badly.** An FC rest is note index ≥ 96, which the player
  resolves by reading **past** its 96-entry freq table — so during a rest the
  original parks a near-zero **`$0002`** in `$D400` with the **gate off**. This
  build emits a real rest, so every such frame scores as a freq "mismatch" on a
  register nothing can hear. On Triangle_Intro v1 that is 636 of 1496 frames:
  raw **57.8%** vs audible **100.0%** in the same window. `Triangle_2_years` is
  the control — it has **zero** rests, and its raw ≈ audible (99.9/100/100).
- **Audible overstates if you ignore its n.** FC gates briefly (percussive
  envelopes), so a voice can be audible for only ~5–20% of frames. "100% of 70
  frames" is real but small — hence `(n)` in every cell above.

The `$0002`-during-rest divergence is a genuine (if inaudible) departure from
byte-exactness. Closing it would need the driver to write a freq **while gated
off**, which the shared engine has no way to express today — a driver feature for
an inaudible register, weighed against touching the just-merged shared driver.
Left open deliberately, recorded here rather than hidden.

### Open Stage-B residual

**Triangle_Intro voice 1 (the lead): 83.6% audible over 633 frames.** It is
**100.0% over the first 30 s** and only diverges later — the same
"widen-the-window" trap that has bitten this project repeatedly (Matt Gray's
subtune 1 read 303/303 at 3000 frames and 683/692 at 6000). It is the voice with
48 rests and the long silent intro. Not yet localised: a first attempt to bucket
the misses per part used a brute-force `t0` search over the original instead of
the parts' **known** bounds and produced nonsense (it "found" a 15-frame window),
so its numbers were discarded rather than reported. Redo that using the `t0`
values `build_song` already computes.

### Follow-ups (not blockers)

- **Block structure.** `FCShim._voice_blocks` returns one flat block per voice
  (the SDI/DMC/Sound-Monitor first-cut shape). `fc_parser` *does* expose
  `voice_blocks` (51/41/51 on Triangle_Intro); feeding those through would let
  repeated blocks share sequences and cut part counts. A part-count optimisation,
  not a correctness one.
- **Native `.prg` modules.** The 4 FC-disk modules in `out/fc_native/` are not
  yet buildable here (siddump needs a PSID; they would need wrapping first).
  Stage A's `fc_validate` already covers them.

### A live naming trap in `FCInstrument`

The dataclass names byte `[5]` **`vibrato`** and byte `[6]` **`arp`**, following
the **V4.1 manual** — which this document already flags as **wrong for V1.0**.
V1.0 reads the arp offsets from `[5]`; the field *named* `arp` is the pulse-sweep
control and is unused by both converters. Confirmed against Stage A, which uses
`ins.vibrato` for both the arp offsets and the drum type. Harmless for Stage B
(the capture supplies arps/drums) but it will bite anyone extending either path.

---

## Player layout (RE'd from the $1800 V1.0 player)

The rip is PSID `load=0` → the real load word ($1800) is the first 2 data bytes;
init `$1800`, play `$1806`. All table addresses are read from **fixed code-operand
offsets** off the player base (= load), so they survive relocation:

| Table | Code site | Operand |
|-------|-----------|---------|
| voice orderlist ptr lo[3] | `$1859 LDA $1ea1,x` | base+0x05a |
| voice orderlist ptr hi[3] | `$185e LDA $1ea4,x` | base+0x05f (a `STA $fb` sits between the two LDAs — off-by-2 trap) |
| block ptr table (lo/hi, block#×2) | `$18c3 LDA $1ea7,y` | base+0x0c4 |
| freq table lo / hi (96 entries) | `$1967` / `$196b` | base+0x168 / 0x16c |
| instrument base (−2) | `$1990 LDA $218a,x` | base+0x191 |
| master speed `$211d` | — | base+0x91d |
| drum wf/pitch table ptrs | `$1c8b/$1c91/$1c97/$1c9d` | base+0x48c/0x492/0x498/0x49e |

### Orderlist byte (`($voiceptr),y`)
`$fe`=stop, `$ff`=loop/restart, `b&$80`→set transpose=`b&$1f`, `b&$40`→set
repeat=`b&$3f` (next block plays 1+n times), else `$00-$3f`=block number.

### Block / pattern byte (`($blockptr),y`)
`b&$f0==$f0`→tie (next byte=note, no retrigger); `b&$f0==$e0`→glide (2 param bytes);
`b&$e0==$c0`→set instrument=`b&$1f`; `b&$c0==$80`→set duration=`b&$3f`; `$ff`=end of
block; else `$00-$7f`=note (freq-table index; ≥96 reads near-zero freq = a rest,
used for drum/bass percussion rows).

### Instrument (8-byte record at `instr_base + n*8`)
`[0]`pulse `[1]`waveform `[2]`AD→$d405 `[3]`SR→$d406 `[4]`unused `[5]`vibrato /
**arp** / drumtype `[6]`pulse-sweep ctrl `[7]`**MCTRL** (`$01` filter, `$04` arp
enable, `$10` drum, `$40/$80` gate). **V1.0 ≠ the V4.1 manual**: the manual calls
`[6]` "Arpeggio CTRL", but V1.0 reads the arp offsets from `[5]` when `mctrl & $04`.

---

## Timing (validated against siddump + SF2II capture)

Frames per note = `(dur+1) * (speed+1)`. The master-speed counter `$2173` reloads
from `$211d`=1 → the player processes a row every **2** frames; the duration counter
runs `dur..0..-1` = `dur+1` ticks. So **Driver 11 rows-per-note = `dur+1`**, and the
SF2 **tempo = `fc.speed`** (SF2II's Driver 11 holds each row `tempo+1` frames —
measured: tempo 2 → 3 frames/row → 1.5× too slow; tempo 1 → 2 frames/row = exact).
The `+1` matters for *relative* timing (dur5:dur2 is really 6:3 = 2:1, not 5:2).

**Pitch base:** the PAL-table calibration lands a **semitone high** vs Driver 11's
own freq table, so `fc_to_song` uses `calibrate_base(...) − 1` (FC note 24 must emit
SF2 note **B-1 / $0430**, not C-2).

---

## Timbre reproduction (Stage-B features already in)

Driver 11's **wave table** does the heavy lifting (col1 `$00-$7f` = relative
semitone added to the note; `$80-$df` = absolute semitone, for drums):

- **Arpeggio** (`mctrl & $04`, `[5] != 0`): FC cycles a 3-step offset table
  `[0, [5]>>4, [5]&$0f]`, one step/frame (phase counter `$2161` at `$1d25`).
  Emitted as a 4-row wave program `[(wf,0),(wf,lo),(wf,hi),$7f]`. Order is
  **root,+lo,+hi** (phase 2→1→0; e.g. `[5]=$58` → root,+8,+5 — verified vs trace).
- **Drums** (`mctrl & $10`): drumtype = `[5]&$0f` selects a per-frame waveform
  sequence (`$1e56`/`$1e76`) + pitch sequence (`$1e46`/`$1e66`); the engine
  (`$1c7b`) plays 14 frames with `freq = (pitch[i]+$0d)<<8`. Emitted as a wave
  program: **one root frame** (the note's own pitch — FC plays it before the drum,
  `$1cad` indexes by frame-1) then the absolute drum-pitch rows, then a gate-off
  settle. Byte-exact vs trace: drum0 = `$81/$2000, $41/$0E00, $40/$0C00, …`.
- **Pulse-width**: pulse-waveform instruments get a triangle PWM sweep
  (`_pwm_program`) so thin-pulse leads aren't silent. (Sweep is approximate — FC's
  real `[6]` sweep envelope is not yet ported.)

---

## Validation — what worked, what lied

**Use `bin/sf2ii_vs_real.capture_sf2ii` (the instrumented SF2II_dbg) as ground
truth.** It captures SF2II's *actual* per-frame SID registers and **does start at
song row 0** (frame 0 = INIT; osc1 correctly silent, osc3 plays the bass). Compare
note onsets per voice vs the original SID's siddump.

**Do NOT trust `bin/sf2_to_wav.py` / `scripts/sf2_to_sid.py` for SF2II fidelity** —
its SF2→SID path interprets the module **differently** from SF2II's Driver 11 and
produced a **false "all voices match"** while SF2II actually played the lead wrong.
(This cost hours; the user caught it — *"do a wav file compare and you'd see the
difference"*.)

Result (arp + bass, real SF2II, note-for-note over 30 s after the drum-root fix):
arp **129/129**, bass **156/156**. The lead is the open item below.

---

## SF2II Driver 11.00 sequence/orderlist format (RE'd from `sf2driver11_00.prg`, load $0d7e)

The per-voice interpreter (state in `$16xx`/`$17xx` arrays, X = voice):
- **Orderlist** (`$2324/$2327` = ptr lo/hi per voice): a stream of entries
  `[$a0+transpose]? [seq#] … $ff [loop_pos]`. A byte ≥ $80 is a transpose marker
  (`transpose = byte − $a0`, persists); the next byte is the sequence number; the
  loop is `$ff <pos>`. Read at `$1088-$10ac`. (My emitter writes this correctly.)
- **Sequence** (`$232a/$23aa` = ptr lo/hi per seq#): the packed bytes from the
  format above. A note's duration counter `$16d8` counts down; when it expires the
  next packed event is decoded (`$10b9-$111e`): `$c0-$ff`→command, `$a0-$bf`→
  instrument, `$80-$9f`→duration (`& $0f`, the `$90` bit = tie), then the note.
  `$7f` (peeked at `$1118`) decrements `$16de` to flag end-of-sequence.
- **Orderlist advance** is gated by a state machine: `$1741,x` counts down each
  frame (`$1541 DEC`), and at `$150d-$1512` the decrement is **suppressed while
  `$16ea,x` (the tie/note-off hold flag) is non-zero**. Note-off rows (`$00`)
  INC `$16ea` (`$10fd`). This is the suspected mechanism behind the long-rest /
  all-rest stall, but the exact trigger isn't fully pinned yet.

**Empirically:** a content sequence with a ≤~96-row rest *prefix* plays fine (the
arp voice's 96-rest intro works); a 288-row rest prefix, or a *separate* all-rest
sequence, does **not** on **Driver 11 or 14** (both hang → 0 frames).

### Driver-swap investigation (option 1)
Stock SF2 silent-intro idiom: **D11/D14** examples use only short rest *prefixes*;
**D15** (Mood) uses a repeated **all-rest sequence** (`A0 00 00`, seq0 = `8F 00 00
00 00 7F` = one duration byte then 4 note-offs = 64 rests — duration persists across
notes; my `8F 00 8F 00…` packing is functionally identical, verified). 
- **D11/D14 hang on all-rest sequences** (confirmed: flat build plays on both;
  the all-block structured build = 0 frames on both).
- **D15 plays the all-rest structured build (773 frames) AND the LEAD GATES (98
  gate-on)** — the silent-intro fix works. BUT D15 is the minimal "Tiny Mark I"
  driver: **no Pulse/Filter tables**, and a **different instrument column layout**,
  so the emitter (which writes D11's `[AD,SR,Flags,Filter,Pulse,Wave]` columns)
  produces **scrambled voices** (osc2 played bass notes, osc3 went silent).
- **D15 driver RE'd so far (`sf2driver15_00.prg`, $0DFE-$1BFD, 3.5 KB "Tiny
  Mark I"):**
  - **Orderlist/sequence format = identical to D11** (`[$a0+t][seq#]…$ff[loop]`).
    Pointer tables differ but `parse_sf2_blocks` already finds them correctly:
    orderlist ptrs `$17f4`/`$17f7`, sequence ptrs `$17fa`/`$187a` (read at
    `$1059`/`$108f`). **So orderlists + sequences emit correctly as-is** — the
    scramble was NOT the orderlist.
  - **Instrument table = 9 column-major columns at `$13d4`** (vs D11's 6). Mapped
    SID writes (`$1291-$12b3`): **col0 `$13d4`→AD ($d405)**, **col1 `$13f4`→SR
    ($d406)**, **col2 `$1414`→pulse ($d403, and `&$f0`→$d402)** — so D15 DOES do
    pulse, from the instrument, no separate table. Other cols (`$1454`=col4 wave-
    prog ptr, `$1474`=col5, `$14b4`=col7, plus a small `$13bd` table) feed the
    waveform/wave-program path — not yet fully mapped.
  - **Wave programs are COMMAND-driven**, not instrument-driven: the sequence
    command byte (`$c0-$ff`, stored at `$22,x` at `$10a3`) indexes the wave table
    `$1474`/`$14b4` (`$1138`). This is a different architecture from D11 (where the
    instrument points at the wave program) — the arp/drum wave programs would need
    re-targeting onto D15's command channel.
  - **Wave table = same 2-col format as D11** at `$14f4` (waveform/`$7f`-jump) /
    `$15f4` (semitone/jump), stepped by a per-voice pointer (`$58`) that starts
    from instrument **col4** (`$1454`) — so the arp/drum wave programs emit
    unchanged, just at D15's wave address (which `parse_sf2_blocks` already gives).
  - **EMITTER PORT IMPLEMENTED** (`emit_driver11_sf2(..., instr_layout='d15')` +
    `--d15` flag in `bin/fc_to_sf2.py`): D15 instrument columns `[AD(0), SR(1),
    pulse(2), -, wave_idx(4)]`, static pulse byte (`D11Instrument.pulse_width`).
    Result on Triangle_Intro: **the song plays AND the long-silent-intro voices
    gate** — osc1 (arp) + osc2 play (312 / 415 gate-on). The all-rest intro works.
  - **LEAD NOW FIXED** with `build_structured(merge_rests=False)` (the `--d15`
    default): keep rest blocks as SHORT separate sequences replayed by the orderlist
    (the Mood idiom), NOT merged into a long rest *prefix* (a long prefix breaks the
    voice; a 96-row prefix is fine but 288 is not). Result: osc1 (arp) enters @196,
    osc2 (lead) enters @580 — both timings correct.
  - **REMAINING BUG: osc3 (bass / track2 = voice index X=2) is dead** — no gate,
    despite a valid instr1 pulse wave program (wave rows 2-3) and correct orderlist/
    seq (seq 0x1D = `A1 85 17` = set-instr1, B-1), voice map `$13d1`=[0,7,14], all
    matching Mood. Isolation done: reordering so the bass is OFF X=2 makes osc3 gate
    (but breaks the rest-intro voices' timing); a rest lead-in on the bass does NOT
    help; arp/lead (with rest intros) on X=2 are fine. So it's an **X=2-first-voice
    + immediate-content** state-machine timing quirk ($5b,x cycles 2->1[fetch]->0
    [gate-on], init=2). Static analysis says it should work; dynamics disagree.
    **6502-traced (py65) and the build is CORRECT.** Single-stepping the D15
    driver on out/Tri_d15.sf2: frame2 X=2 fetches its orderlist, frame4 gate-on,
    frame5 osc3 ctrl=$41 (pulse+gate). siddump (its own emulator) AND reSID/WAV
    confirm: osc3 plays 8 bass notes (B-1,C-2,D-2,E-2,F#2,…). So all three voices
    play in THREE independent cycle-accurate emulators. The SF2II_dbg "osc3 dead"
    disagrees with all of them. A CMP-carry-bug scan of the whole play path found
    only 2 carry-discrepant compares ($1076, $104f) and BOTH are followed by BNE
    (Z-based, carry unused) — so the SF2II CMP bug does NOT break osc3. Conclusion:
    the SF2II_dbg auto-play capture is the outlier (it has misled before), the build
    is logically correct, and it should play in the real SF2II GUI — TO BE CONFIRMED
    BY EAR (load out/Tri_d15.sf2, F1). Render to listen: out/_d15_probe.wav (the
    D15 driver via reSID, init=$1000/play=$1006). py65 tracer is the harness if a
    real SF2II-emulator quirk turns up. Default stays D11 flat; `--d15` experimental.
The default emit stays **Driver 11 flat** (works for most FC songs; only long silent
intros break) until the D15 emitter adaptation is done.

## Open issues

- **Long silent intro / lead voice.** Triangle_Intro's lead (V1) is silent for 6×
  the short rest-block (288 ticks) then enters. Representing that in Driver 11 is
  the crux and SF2II's driver is fussy:
  - **Flatten** the voice into one stream → the lead lands in a **960-row sequence**
    with a 288-row rest prefix → SF2II plays the lead **wrong** (high sustained
    notes from the start; the rest prefix is skipped).
  - **One sequence per FC block** (preserve the orderlist, replay a short rest
    sequence 6×) → an **all-note-off sequence stalls the orderlist** → the whole
    song goes silent (0 frames).
  - **Merge** rest-only blocks into the next block (no all-rest sequence) → song
    plays again, but the long rest-*prefix* still mutes the lead, and it perturbed
    the bass.
  Net: SF2II Driver 11 mishandles **both** all-rest sequences **and** long rest
  prefixes. The default emit is the **flat** path (arp/bass/drums correct; lead
  intro wrong) until the constraint is pinned down. **Next step: disassemble
  `bin/drivers/sf2driver11_*.prg`** to learn exactly how it advances orderlists /
  counts sequence rows, then emit within that constraint (likely: short content
  sequences + orderlist replay, with the rest intro handled the way SF2II itself
  does).
- **PWM sweep** is static-ish ($800), not the real FC `[6]` envelope.
- **Vibrato** and the `mctrl & $80` noise-attack are not emitted yet.
- **Other Fun_Fun rips** (15/20) load at `$A000`/`$7000`/`$9000` and use a
  **second player** (init `$C000`, play `$C475`) or Sound Monitor — not the `$1800`
  V1.0 player. `detect_player` gates them out cleanly. Architecture partly RE'd
  (page-aligned orderlist pointer tables `$a000/$a100/$a400/$a500/$a800/$a900/
  $ac00/$ad00`, ZP-indirect sequencing). See the memory note.

---

## Decrunching the editor (for task #2 = native module format / SF2->FC export)

`future comp.v1.0.prg` is crunched (BASIC `1988 SYS2072` -> depacker copied to
`$00f8`/`$0100` -> final `JMP $C000`). Decrunched headlessly in VICE
(`C:\winvice\bin\x64sc.exe`) -> `out/fc_editor_v1_decrunched.prg` ($0800-$FFFF RAM):

    x64sc -warp -autostart "future comp.v1.0.prg" -moncommands cmds.txt
    # cmds.txt (run at startup; GOTCHA: VICE `g <addr>` SETS pc, not run-until,
    #   so use a breakpoint with an attached command):
    bank ram
    break c000
    command 1 "save \"dump.prg\" 0 0800 ffff"
    g
    # (launch with WorkingDirectory=out/, wait ~10s in -warp, then kill x64sc)

Verified: editor entry **$C000**; the **FC player is at $1800** (byte-identical to
the SID-rip player — validates the RE), a second copy at $dd2b. Editor = "COMPOSER
NO: 00.18 V1.0, FINLAND TRACKING, 13.06.1988". The decrunched dump is the place to
RE the editor's SAVE/LOAD routines (menu "SAVE SONG"/"SAVE NAME:" near $CD78) to
learn the native on-disk module format for the SF2->FC writer (task #2).

### Native FC V1.0 on-disk module format (RE'd from the editor SAVE routine)
SAVE routine at $cd82 (KERNAL SAVE $ffd8 @ $cdaa): start = $1800 (`LDA #$00/STA $fb;
LDA #$18/STA $fc`), end = ($03ff:$03fe), `LDA #$fb` (ZP ptr), `JSR $ffd8`. LOAD at
$cdbb (KERNAL LOAD $ffd5 @ $cdd7). So **a native FC V1.0 module is a PRG loaded at
$1800 = the player + all song data, from $1800 up to the editor's end-pointer
$03fe/$03ff.** This is IDENTICAL to the SID-rip / native-`.prg` layout the parser
already reads. So an **SF2->FC writer (task #2)** = the inverse of `fc_parser`:
start from the $1800 player template (fixed code + freq table + the pointer-table
slots at $1ea1/$1ea4 voice ptrs, $1ea7 block-ptr table, $2188 instruments), lay out
the orderlists/blocks/instruments after it, fill those pointer tables, set the end
address, write a PRG @ $1800. A good first milestone is an FC->FC round-trip
(parse a native tune, re-serialize, diff) before wiring the SF2 source.

### Writer IMPLEMENTED + validated (`sidm2/fc_writer.py`)
`write_fc(FCSong) -> PRG @ $1800` is the inverse of `fc_parser`: copies the player
template ($1800..instr_base) from `song._mem`, writes instruments at $2188 (32
slots), chunks each voice into blocks (<256 B because the in-block index $2124,x is
8-bit; instr/dur state threads across blocks), chains them via per-voice orderlists
([block#...]$ff), and fills the voice ptrs ($1ea1/$1ea4) + block-ptr table ($1ea7).
Pointer-table addresses read from the template via fc_parser's code-operand offsets
(relocation-safe). VALIDATED: FC->FC round-trip reproduces identical per-voice
note/dur/instr/tie streams for all 7 corpus tunes (incl. 1314-note VOICES_IN_SPC),
AND a written module is BYTE-IDENTICAL in siddump to the original (150/150 frames,
cycle-accurate). Tests: `pyscript/test_fc_writer.py` (6). Limits/next: one block-
chain per voice (no orderlist repeat compression / per-block transpose), glides not
re-emitted, <=64 blocks total. NEXT for the full round-trip: parse a Driver-11 SF2
back to notes+instruments and feed `write_fc` -> loadable in the real C64 editor.

### SF2->FC reader + FULL ROUND-TRIP DONE (`sidm2/sf2_to_fc.py`, `bin/sf2_to_fc.py`)
`sf2_to_fcsong(sf2_bytes, template) -> FCSong` walks the SF2 orderlists/sequences
back to per-voice (note, instr, rows, tie) events and maps them to FCNotes: dur =
rows-1; fc_note = sf2_note - base - 1 (base = calibrate_base(template freq) - 1,
the exact inverse of fc_to_song); $00/out-of-range -> rest; instrument THREADS
across sequences (the player carries it; the SF2 only re-emits on change — getting
this wrong reset instruments to 0). Player code, freq/arp/drum tables and the 8-byte
instrument records come from the TEMPLATE FC module (the Driver-11 SF2 doesn't carry
FC's arp/drum bytes), so use the original FC tune as template.

CLI: `py -3 bin/sf2_to_fc.py edited.sf2 template.sid out.prg`.

**VALIDATED end-to-end**: FC -> fc_to_sf2 -> SF2 -> sf2_to_fcsong -> write_fc -> FC
module plays BYTE-IDENTICAL to the original in siddump (200/200 frames). Audible
notes round-trip exactly for the corpus (Triangle/HEART exact; GAME_OVER/VOICES_IN_
SPC differ only on FC note 0 + instr 0 silent placeholders, which fc_to_sf2 clamps
to the SF2 note floor — inaudible). Tests: `pyscript/test_sf2_to_fc.py`; 16 FC tests
green. Lossy edges: FC notes 0/1 (SF2 floor clamp), exact rest-note values, glides,
and Driver-11-table timbre (arps/drums) — instruments are taken from the template,
so timbre is preserved as long as the SF2's instrument set isn't re-defined.

## The FC disk (`bin/FC10/...D64`)

Holds four editor versions (V1.0–V4.1), the **relocator**, the manual, and native
FC tune modules (VOICES IN SPC / HEART / IT'S A SIN / GAME OVER — all `$1800` V1.0,
so the converter reads them as `.prg` directly). The editor/relocator PRGs are
**crunched** (load `$0801` BASIC stub) — to read them, extract from the D64
(uncrunched data) or run in VICE and snapshot. The native V1.0 module format **is**
the `$1800` player+data layout the converter already parses.

---

## Files

- `sidm2/fc_parser.py` — FC table extractor (orderlists, blocks, instruments,
  freq table, drum sequences). `detect_player` gates the `$1800` V1.0 variant.
- `bin/fc_to_sf2.py` — **Stage A**: transpile to Driver 11 SF2 (arps, drums, PWM,
  pitch/tempo). `build_structured` preserves the FC orderlist (currently disabled
  — see open issues).
- `bin/build_fc_native_song.py` — **Stage B**: `FCShim` (MON-compatible, decode-
  driven) → the shared trace-driven native engine. Refuses non-`$1800` rips
  loudly via `detect_player`. Reports raw **and** audible fidelity per voice.
- `pyscript/test_fc_native_song.py` — 17 tests: FC's two `+1`s (fpt = speed+1,
  ticks = dur+1), instrument-0 threading, rest mapping, own-freq-table use.
- `sidm2/galway_driver11_emitter.py` — shared emitter; gained optional
  `sequences=`/`orderlists=` params so a caller can supply its own block structure.
- `pyscript/test_fc_parser.py` — 6 tests (detect, structure, V2 melody vs trace,
  arp offsets, drum freq sequence vs trace, timing).
