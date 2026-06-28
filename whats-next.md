<original_task>
Add a NEW player to SIDM2: convert Future Composer (C64) SID files to SF2, starting
with SID/Fun_Fun/Triangle_Intro.sid (Michael Troelsen / Fun Fun, 1988). Output must
play in stock SID Factory II using a standard SF2 driver (Driver 11). Goal grew (all
with the user's explicit go-aheads) to: faithful timbre (arps/drums/pulse); fix a
voice with a LONG SILENT INTRO (Triangle's lead) that broke under Driver 11; and a
full FC<->SF2 ROUND-TRIP (convert FC->SF2, edit in SF2II, then SF2->FC to load back
into the real C64 Future Composer editor). User's standing instruction: "we need
this to work" — keep pushing on the open items.
</original_task>

<work_completed>
## DONE + committed/pushed to master (github MichaelTroelsen/SIDM2conv)
Latest commit: 6d4cb9f (handoff refresh). Earlier FC commits: c9dd5ff (converter),
0f9f5d0 (editor decrunch + native format), d71ff40 (fc_writer), 469e451 (sf2_to_fc),
48d812a (D15 lead fix), de8292b/052f8fb (handoff + D15 trace).

### FC V1.0 parser — sidm2/fc_parser.py (COMPLETE, validated, tested)
Decodes the $1800 FC V1.0 player (orderlists, blocks, 8-byte instruments, 96-entry
PAL freq table, drum tables). Table addresses read from FIXED CODE-OPERAND offsets
off the player base (relocation-safe). detect_player() gates the $1800 variant.
Exposes FCSong (voices: 3 flat FCNote lists; voice_blocks: per-block lists;
instruments; freq_lo/hi; drum_sequence(drumtype); _mem; _drum_tbls).

### FC->SF2 converter — bin/fc_to_sf2.py (default Driver 11; --d15 experimental)
Transpiles to editable Driver 11 SF2 reusing the Galway IR + emitter. Arpeggios
(mctrl&$04, byte[5] nibbles -> wave-table semitone rows), drums (mctrl&$10, 14-frame
waveform+abs-pitch wave program; note's own pitch first then the drum table), PWM
sweep, correct pitch (calibrate_base-1) and tempo (=fc.speed). Accepts .sid or .prg.
`--d15` path uses build_structured(merge_rests=False) + Driver 15 template +
instr_layout='d15'.

### fc_writer.py — sidm2/fc_writer.py (COMPLETE, validated, tested)
write_fc(FCSong) -> native FC PRG @ $1800 (player+data), the exact format the C64
editor's SAVE writes. Copies player template up to instr_base, writes instruments at
$2188, chunks each voice into <256-byte blocks (in-block index $2124,x is 8-bit),
chains via per-voice orderlists, fills voice-ptr ($1ea1/$1ea4) + block-ptr ($1ea7)
tables. FC->FC round-trip byte-identical in siddump.

### sf2_to_fc — sidm2/sf2_to_fc.py + bin/sf2_to_fc.py (COMPLETE, validated, tested)
sf2_to_fcsong(sf2, template) walks a Driver-11 SF2's orderlists/sequences back to
per-voice events -> FCSong. base inverted exactly (calibrate_base(template freq)-1);
instrument threads across sequences; player/tables/instrument-records from template.
CLI: py -3 bin/sf2_to_fc.py edited.sf2 template.sid out.prg.
FULL ROUND-TRIP VALIDATED: FC->fc_to_sf2->SF2->sf2_to_fcsong->write_fc->FC plays
BYTE-IDENTICAL in siddump (200/200 frames). Audible notes round-trip exactly.

### Editor decrunched + native format (task #2 DONE)
Decrunched future comp.v1.0.prg in VICE -> out/fc_editor_v1_decrunched.prg. SAVE
routine RE'd: native FC V1.0 module = PRG @ $1800 = player+data, saved $1800..
($03ff:$03fe). Editor entry $C000; FC player at $1800 byte-matches the SID-rip RE.

### Tests: 16 FC tests green
pyscript/test_fc_parser.py (6), test_fc_writer.py (6), test_sf2_to_fc.py — wait,
counts: parser 6 + writer 6 + sf2_to_fc tests. Run: `py -3 -m pytest
pyscript/test_fc_parser.py pyscript/test_fc_writer.py pyscript/test_sf2_to_fc.py -q`
(16 passed). pyflakes gate green.

### Corpus note-for-note validation + instrument-0 HOLD fix (2026-06-28, NEW)
Validated all 5 supported $1800 tunes note-for-note (scratchpad
`fc_validate_corpus.py`: build D15 SF2 -> wrap as PSID probe (load=la, init=$1000,
play=$1006, via `parse_sf2_blocks`+`PSIDHeader`) -> siddump probe AND original ->
compare per-voice unbracketed note-onset sequences). **Found + fixed a real general
bug**: FC **instrument 0 is a HOLD sentinel** (a note on instr 0 makes no sound — it
sustains the ringing note; at song start, nothing ringing = silence). The converter
emitted them as audible notes (`_norm_waveform(0)`=$41) -> spurious B-3/B-1 onsets at
phrase boundaries. Fix in `bin/fc_to_sf2.py`: instr-0 notes now emit `SF2_GATE_ON`
sustain rows (pitch ignored), never a note-on; new `_instr_change` helper never sets
or becomes instr 0. **Result: 4/5 tunes note-EXACT** (Triangle_Intro, Triangle_2_years,
Demo_of_the_Year_88, Is_There osc1/osc2 — all were broken on 1-2 voices). Residual:
Carillo osc1 (123 vs 135) + Is_There osc3 (62/87) = FC per-frame ARP/effect on the
instr-0 grace notes = Stage-A timbre limitation, not a clean note bug. Round-trip:
instr-0 holds fold into the prior note's duration (identical audio by construction),
so `test_sf2_to_fc._audible` excludes instr-0; +3 new `pyscript/test_fc_to_sf2.py`.
**19 FC tests green**, pyflakes clean. NOTE: Triangle was already EXACT pre-fix, so
the SF2II-loaded `out/Tri_d15.sf2` is unchanged. Committed (not pushed) — see Git.

### D15 long-intro path — MAJOR PROGRESS THIS SESSION
- LEAD FIXED: --d15 with build_structured(merge_rests=False) keeps rest blocks as
  SHORT separate sequences replayed by the orderlist (the Mood/Driver-15 idiom), NOT
  a merged long rest prefix. Result: osc1(arp)@196, osc2(lead)@580 — both correct.
- BASS (osc3, voice X=2) appeared "dead" in SF2II_dbg captures. **6502-TRACED in
  py65**: the D15 driver is CORRECT — frame2 X=2 fetches orderlist, frame4 gate-on,
  frame5 osc3 ctrl=$41. siddump AND reSID/WAV CONFIRM: osc3 plays 8 bass notes
  (B-1,C-2,D-2,E-2,F#2,…). So 3 independent cycle-accurate emulators all play osc3.
- CMP-carry-bug scan of the whole play path: only 2 discrepant compares ($1076,
  $104f), BOTH followed by BNE (Z-based, carry unused) -> the SF2II CMP bug does NOT
  break osc3. => SF2II_dbg capture is the outlier (likely a capture artifact).
- Currently LOADED out/Tri_d15.sf2 in the REAL SF2II GUI awaiting the user's by-ear
  verdict on whether the bass plays.
</work_completed>

<work_remaining>
## IMMEDIATE: resolve the D15 bass question (awaiting user's ear)
out/Tri_d15.sf2 is loaded in the real SF2II GUI (bin/SIDFactoryII.exe). The user must
press F1 and report whether the BASS plays (it should enter immediately under the
arp/lead). Also out/_d15_probe.wav is a reSID render of the same build (all 3 voices).
- IF the bass plays in real SF2II: the --d15 long-intro path WORKS; Triangle is fully
  correct via --d15; mark task #3 effectively done for the lead/bass. Then consider
  making --d15 auto-selected when a tune has a long staggered intro.
- IF the bass is still dead in real SF2II (but py65/siddump/reSID all play it): then
  SF2II's BUNDLED 6510 emulator diverges in a way not yet pinned. Use the py65 harness
  to REPLICATE SF2II's exact emulator quirks (start from the documented CMP-carry bug;
  check other instruction behaviors — ADC/SBC decimal, indexed-page-cross timing,
  illegal opcodes) and re-trace until the divergence reproduces, then adjust emission
  to avoid it. The dbg is SIDFactoryII_dbg.exe (from C:\Users\mit\Downloads\
  sidfactory2-master); the bundled SIDFactoryII.exe (Build Dec 26 2025) may differ.

## Other open items
- Task #1 (memory note): the OTHER ~15 Fun_Fun rips use a SECOND player (init $C000,
  play $C475) or Sound Monitor. Page-aligned orderlist pointer tables partly RE'd
  ($a000/$a100 voice0, $a400/$a500 v1, $a800/$a900 v2, $ac00/$ad00 patterns).
- Stage-B polish: PWM sweep is static-ish; vibrato + mctrl&$80 noise-attack not
  emitted; D11 lead (long intro) plays wrong on default (use --d15 once it's confirmed).
- SF2->FC follow-ups: reconstruct FC instruments from Driver-11 columns (template-
  free SF2->FC); preserve orderlist repeats/transpose in fc_writer for compactness.
- Lossy round-trip edges (documented): FC notes 0/1 (SF2 floor clamp, silent), exact
  rest-note values, glides, Driver-11-table timbre (instruments from template).
</work_remaining>

<attempted_approaches>
## Long-silent-intro — what failed
- D11 flatten: lead in a 960-row sequence w/ 288-row rest prefix -> SF2II DRONES a
  wrong note (skips prefix). Current D11 default behaviour for the lead.
- D11/D14 all-rest sequence (one seq per block): HANGS the driver (0 frames).
- D11 merge rest-into-next-block: plays but long rest PREFIX mutes the lead + broke
  bass.
- D11 _SEQ_EVENT_LIMIT changes (960/480/256/192): erratic, not a clean threshold.
- D14 template + structured: 0 frames (D14 also hangs on all-rest; flat plays on D14).
- D15 structured WITH merge: lead voice STUCK on the long rest prefix.
- D15 structured NO-merge: LEAD FIXED (this is the current --d15). Only osc3 looked
  dead in dbg — later proven a false alarm (py65/siddump/reSID play it).
- D15 reorder bass off X=2: osc3 gates but rest-intro voices' timing breaks.
- D15 rest lead-in on bass: did NOT help.

## Validation tooling — a costly false-positive lesson
- bin/sf2_to_wav.py / scripts/sf2_to_sid.py do NOT reproduce SF2II's playback — gave
  a false "all match". Use bin/sf2ii_vs_real.capture_sf2ii (instrumented SF2II_dbg)
  for SF2II behaviour, BUT it too has misled (auto-play artifacts, and now the D15
  osc3 false-dead). MOST RELIABLE for driver LOGIC: py65 single-step + siddump.
- Spent a very long time treating the D15 osc3 dbg reading as ground truth before
  py65+siddump+reSID proved the build correct. Lesson: cross-check the dbg capture
  with py65/siddump before deep-diving a "dead voice".
</attempted_approaches>

<critical_context>
## Run / tooling
- Convert FC->SF2: `py -3 bin/fc_to_sf2.py in.sid|in.prg out.sf2 [--d15]`
- SF2->FC: `py -3 bin/sf2_to_fc.py edited.sf2 template.sid out.prg`
- Real SF2II GUI: launch bin\SIDFactoryII.exe with the sf2 + --skip-intro, cwd=bin
  (needs SDL2.dll + config). Kill prior SIDFactoryII/SIDFactoryII_dbg first.
- SF2II actual-output capture: `from sf2ii_vs_real import capture_sf2ii` (in bin/),
  returns {frame:[r0..r24]}. osc ctrl regs r4/r11/r18 (bit0=gate); freq r0/1,r7/8,
  r14/15; pulse r2/3,r9/10,r16/17; adsr r5/6,r12/13,r19/20.
- py65 6502 trace pattern (see sidm2/sid_init_runner.py): MPU(); set memory; push
  sentinel return ($01ff=$FF,$01fe=$FE -> RTS to $FFFF), sp=$FD, set pc, step until
  pc==$FFFF. Build the D15 traceable image: parse_sf2_blocks(sf2)->la; mem[la:]=
  sf2[2:]. D15 driver entries: $1000 (sets mode=init), $1006 (per-frame: mode0=init
  ->sets $03=$80, mode$80=play, mode$40=stop). So call $1000 then $1006 each frame;
  first $1006 inits.
- siddump cross-check: wrap the D15 image as PSID (load=la, init=$1000, play=$1006)
  -> out/_d15_probe.sid; `py -3 pyscript/siddump_complete.py out/_d15_probe.sid -tN`.
  reSID WAV: `py -3 bin/sf2_to_wav.py out/_d15_probe.sid 20` -> out/_d15_probe.wav.
- VICE: C:\winvice\bin\x64sc.exe. Decrunch recipe (-warp -autostart -moncommands;
  GOTCHA: `g <addr>` SETS pc, use a breakpoint+attached command). Cached disasms in
  the session SCRATCHPAD: fc_disasm.txt, d11_disasm.txt, d15_disasm.txt, c000_*.txt,
  fced_disasm.txt (regenerate from the prgs via pyscript/disasm6502.py if a fresh
  session lacks them — they're temp-dir, not in git).

## FC V1.0 format (RE'd, validated)
Player $1800 (PSID load=0 -> real load=first 2 bytes=$1800; init $1800, play $1806).
Locator offsets from base: voice ol ptr lo[3]@+0x05a, hi[3]@+0x05f (off-by-2 trap: a
STA $fb between the two LDAs); block ptr tbl@+0x0c4; freq lo/hi@+0x168/0x16c; instr
base=operand@+0x191 -2 ($2188); speed $211d@+0x91d; drum tbl ptrs@+0x48c/492/498/49e.
Orderlist byte: $fe stop, $ff loop, b&$80 transpose=b&$1f, b&$40 repeat=b&$3f, else
block#. Block byte: b&$f0==$f0 tie(next=note); ==$e0 glide(2 params); b&$e0==$c0 set
instr=b&$1f; b&$c0==$80 set dur=b&$3f; $ff end; else note ($00-$7f; >=96=rest).
Instr 8 bytes: [0]pulse [1]waveform [2]AD [3]SR [4]- [5]vib/arp/drumtype [6]pulse-
sweep [7]MCTRL ($04 arp,$10 drum,gate). Arp: mctrl&$04 & [5]!=0 -> offsets [0,[5]>>4,
[5]&$0f], 1 step/frame ($2161 phase). Drum: mctrl&$10, drumtype=[5]&$0f -> wf seq
$1e56/$1e76 + pitch seq $1e46/$1e66, 14 frames, freq=(pitch+$0d)<<8, note's own pitch
on the trigger frame first. Timing: frames/note=(dur+1)*(speed+1); D11 rows=dur+1,
SF2 tempo=fc.speed (SF2II holds each row tempo+1 frames). pitch_base=calibrate-1.

## Driver 11 vs 15 (SF2II)
Both: orderlist [$a0+transpose][seq#]...$ff[loop]; packed seq $00 off,$01-$6f note,
$7e sustain,$7f end,$80-$8f dur(&$0f),$90-$9f dur+tie,$a0-$bf set-instr,$c0-$ff cmd;
wave table 2-col (col0 wf/$7f-jump, col1 $00-$7f relative semitone / $80-$df absolute
[drums]). D11 (sf2driver11_00.prg $0d7e): instr 6 cols [AD,SR,Flags,Filter,Pulse(idx),
Wave]; ol ptrs $2324/$2327, seq ptrs $232a/$23aa. D11/D14 HANG on all-rest sequences.
D15 (sf2driver15_00.prg $0dfe, "Tiny Mark I"): instr 9 cols, used = col0 AD/col1 SR/
col2 pulse(static byte->$d403)/col4 wave-ptr; ol ptrs $17f4/$17f7, seq ptrs $17fa/
$187a, wave $14f4/$15f4, voice map $13d1=[0,7,14]; per-voice state $5b/$5c/$5d (init
2; cycles 2->1[fetch @$104d]->0[gate-on @$10ee/$1104]; DEC @$12d8). emit_driver11_sf2
gained params: sequences=, orderlists= (verbatim), instr_layout='d11'|'d15'.
D11Instrument gained pulse_width (D15 static pulse). parse_sf2_blocks finds all D15
addresses correctly.

## Gotchas
- SF2II CMP carry = bit7 of (A-op), wrong when |A-op|>$7f (only matters if a BCC/BCS
  uses it; the 2 in the D15 play path are BNE = harmless).
- The 3 emulators (py65, siddump, reSID) agree the D15 build is correct; SF2II_dbg
  alone disagrees on osc3.
- D11 default works for FC songs whose voices start together (GAME OVER, HEART play
  fully); only long staggered intros need --d15.
</critical_context>

<current_state>
## Deliverables
- FC V1.0 parser: COMPLETE + tested.
- FC->SF2 (D11 default): COMPLETE for songs without long staggered intros.
- fc_writer + sf2_to_fc (full FC<->SF2 round-trip): COMPLETE + validated (200/200
  byte-identical) + tested. Task #2 done.
- Editor decrunch + native format: COMPLETE.
- --d15 long-intro path: lead FIXED; bass CONFIRMED correct in py65+siddump+reSID;
  awaiting user's by-ear verdict in the real SF2II GUI (loaded now). NOT yet the
  default; experimental flag.
- 16 FC tests green; pyflakes clean.

## Git
All FC work committed + pushed to master (latest 052f8fb). Working tree: only
out/*.sf2 / out/*.sid / out/*.wav scratch + SID/Fun_Fun/Triangle_Intro.wav are
untracked (gitignored / artifacts). out/fc_editor_v1_decrunched.prg is regenerable
via the VICE recipe (not committed).

## Current position / open question
Waiting on the user to press F1 in the real SF2II (out/Tri_d15.sf2 is loaded) and
report whether the BASS plays. That single answer decides whether the D15 path is
done or whether an SF2II-emulator quirk needs py65-replication. The next session
should start from that answer (see Work Remaining IMMEDIATE).
</current_state>
