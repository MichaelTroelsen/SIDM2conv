<original_task>
Add a NEW player to SIDM2: convert Future Composer (C64) SID files to SF2 format,
starting with `SID/Fun_Fun/Triangle_Intro.sid` (composer Michael Troelsen / Fun Fun,
1988). The user explicitly wants the output to play in **stock SID Factory II**
using a **standard SF2 driver** (Driver 11), and wants to "convert some old FC songs
to SF2" broadly. Reference manual: `bin/FC10/Futurecomposer Instructions.txt`.

Over the session the scope grew (with the user's explicit go-aheads) to:
1. Faithful timbre (arps, drums, pulse) — done for arp/bass/drums.
2. Fix the one remaining defect: a voice with a LONG SILENT INTRO (Triangle_Intro's
   lead) plays wrong/silent in SF2II's Driver 11.
3. The user chose "option 1": port the emitter to a driver that handles long silent
   intros (Driver 15). THIS PORT IS IN PROGRESS — 2 of 3 voices work, bass (osc3)
   silent. That is the live task to resume.
</original_task>

<work_completed>
## New files created
- `sidm2/fc_parser.py` — Future Composer V1.0 ($1800 player) extractor. Decodes
  orderlists, blocks/patterns, 8-byte instruments, 96-entry PAL freq table, and the
  drum tables. Locates all tables via FIXED CODE-OPERAND offsets off the player base
  (= load addr) so it's relocation-safe. Key API: `parse_fc(data, load) -> FCSong`,
  `detect_player(data, load)`, `FCSong.drum_sequence(drumtype)`, and
  `FCSong.voice_blocks` (per-voice list of per-block FCNote lists, added for the
  structure-preserving emission).
- `bin/fc_to_sf2.py` — transpiles to a Driver 11 (default) or Driver 15 (`--d15`)
  SF2, reusing the Galway IR (`GalwayDriver11Song`) + emitter. Accepts both `.sid`
  rips and raw `.prg` native FC modules. Functions: `load_sid`, `calibrate_base`,
  `build_instruments(fc, base)` (arps + drums + PWM), `_block_rows`,
  `build_structured(fc, base)` (one sequence per FC block + per-voice orderlists),
  `build_track`, `fc_to_song`, `main` (has `--d15`).
- `pyscript/test_fc_parser.py` — 6 tests (detect+load, structure, V2 melody vs
  trace, arp offsets, drum freq sequence vs trace, timing). ALL PASS.
- `docs/players/FUTURECOMPOSER.md` — full write-up (matches GALWAY.md style): player
  RE, byte formats, timing, arp/drum reproduction, validation lessons, the long-
  intro problem, the D11/D14/D15 investigation, and the D15 port status.

## Files modified
- `sidm2/galway_to_driver11.py` — added `pulse_width: int = 0` field to
  `D11Instrument` (D15 static-pulse byte).
- `sidm2/galway_driver11_emitter.py` — `emit_driver11_sf2` gained 3 params (all
  backward-compatible, default to old behavior):
  - `sequences: Optional[List[bytes]]`, `orderlists: Optional[List[List[int]]]` —
    when given, written verbatim instead of segmenting `song.tracks` (preserves FC's
    block/orderlist structure). Injection point ~line 226.
  - `instr_layout: str = 'd11'` — `'d15'` writes columns `[AD,SR,pulse_width,0,
    wave_idx]` instead of D11's `[AD,SR,flags,filter_idx,pulse_idx,wave_idx]`. ~line 184.

## Memory + docs
- `memory/future-composer-player.md` (the durable memory note) — extensively
  updated with all RE findings (see Critical Context). `memory/MEMORY.md` has the
  index pointer.

## The Future Composer V1.0 format (fully RE'd, validated)
Player at $1800 (PSID load=0 -> real load = first 2 data bytes = $1800; init $1800,
play $1806). Table locator offsets from base:
- voice orderlist ptr lo[3] @ base+0x05a; hi[3] @ base+0x05f (NOTE off-by-2 trap: a
  `STA $fb` sits between the two LDAs)
- block ptr table @ base+0x0c4; freq lo/hi @ base+0x168/0x16c; instr base = operand
  @ base+0x191 minus 2; master speed $211d @ base+0x91d
- drum table ptrs @ base+0x48c/0x492/0x498/0x49e
Orderlist byte: $fe=stop, $ff=loop, b&$80->transpose=b&$1f, b&$40->repeat=b&$3f
(next block plays 1+n times), else $00-$3f=block#.
Block byte: b&$f0==$f0->tie(next byte=note); b&$f0==$e0->glide(2 param bytes);
b&$e0==$c0->set instr=b&$1f; b&$c0==$80->set dur=b&$3f; $ff=end; else $00-$7f=note
(index >=96 reads near-zero freq = a rest).
Instrument 8-byte record: [0]pulse [1]waveform [2]AD->$d405 [3]SR->$d406 [4]unused
[5]vibrato/arp/drumtype [6]pulse-sweep [7]MCTRL ($04 arp enable, $10 drum, gate
bits). V1.0 ≠ the V4.1 manual (manual says [6]=arp; V1.0 uses [5] when mctrl&$04).
Arp: enabled when [7]&$04 and [5]!=0; offsets = [0, [5]>>4, [5]&$0f], cycled one
step/frame (phase counter $2161 at $1d25). Order root,+lo,+hi.
Drums: mctrl&$10; drumtype=[5]&$0f selects waveform seq ($1e56/$1e76) + pitch seq
($1e46/$1e66); 14-frame burst, freq=(pitch[i]+$0d)<<8; FC plays the note's OWN pitch
on the trigger frame then the drum table from frame 1.
Timing: frames/note = (dur+1)*(speed+1). Driver11 rows-per-note = dur+1; SF2 tempo =
fc.speed (SF2II Driver 11 holds each row tempo+1 frames -> tempo=1 gives 2 frames/
row = exact match). pitch_base = calibrate_base(...) - 1 (PAL calibration lands a
semitone high vs Driver 11's freq table).

## Validation results (D11 flat build, rendered to SID then siddump, vs original SID)
ALL THREE voices matched note-for-note over 30s on Triangle_Intro AFTER the drum-
root fix: arp 129/129, lead 35/35, bass 156/156 — BUT this used the false-positive
proxy `sf2_to_wav`/`sf2_to_sid` which does NOT reproduce SF2II's actual playback.
The RELIABLE tool is `bin/sf2ii_vs_real.capture_sf2ii` (instrumented SF2II_dbg) which
captures SF2II's real per-frame SID registers from row 0. Against THAT, the D11 flat
build: arp+bass+drums correct, but the LEAD voice (288-tick silent intro) plays
WRONG (high droning notes from start). 2 of 3 native D64 tunes (GAME OVER, HEART)
play all 3 voices fully on D11; ITS_A_SIN has 1 silent voice (long intro).

## Driver investigation (the core blocker)
- SF2II Driver 11 + Driver 14 both HANG (0 frames) on an ALL-REST sequence, and play
  a long REST-PREFIX sequence WRONG. Confirmed it's the driver engine, not the
  emitter (flat build plays on both D11 and D14).
- Stock SF2 silent-intro idiom: D11/D14 examples use only SHORT rest prefixes;
  Driver 15 (Mood) uses a repeated ALL-REST sequence (`A0 00 00`) — so D15 handles
  long silence.
- Disassembled D15 (`bin/drivers/sf2driver15_00.prg`, load $0DFE, cached at
  scratchpad d15_disasm.txt). Its orderlist/sequence/wave-table formats are
  IDENTICAL to D11 (pointer tables at different addrs but `parse_sf2_blocks` finds
  them right: ol ptrs $17f4/$17f7, seq ptrs $17fa/$187a, wave table $14f4/$15f4).
  Instrument cols differ: col0=AD, col1=SR, col2=pulse(static byte->$d403),
  col4=wave-ptr. Voice map $13d1=[0,7,14].
- IMPLEMENTED the D15 emitter port (instr_layout='d15' + --d15 flag). Result: song
  PLAYS, the all-rest silent intro WORKS, osc1+osc2 gate (312/415 gate-on).
</work_completed>

<work_remaining>
## D15 osc3/bass — PARTIAL (lead fixed; bass = X=2 driver quirk, needs 6502 trace)
PROGRESS (committed 48d812a): the LEAD is fixed. `--d15` now uses
`build_structured(merge_rests=False)` -> rest blocks stay SHORT separate sequences
replayed by the orderlist (the Mood idiom), NOT a merged long rest prefix (a long
prefix breaks the voice). Result: osc1 (arp) @196, osc2 (lead) @580 — correct.
REMAINING: osc3 (bass, track2 = voice index X=2) is DEAD (no gate) despite a valid
instr1 pulse wave program (wave rows 2-3) and a correct orderlist/seq. ISOLATION
done this session: (a) reorder so the bass is OFF X=2 -> osc3 gates (but the rest-
intro voices' timing breaks); (b) a rest lead-in on the bass does NOT help; (c)
arp/lead (with rest intros) on X=2 are fine. => an **X=2-first-voice + immediate-
content** state-machine timing quirk. $5b,x cycles 2->1[orderlist fetch @ $104d]->
0[gate-on @ $10ee/$1104], init=2, DEC @ $12d8. Static analysis says X=2 should
fetch+gate; dynamics disagree. BLACK-BOX CAPTURE TESTING IS EXHAUSTED. Next step =
cycle-level 6502 single-step (e.g. VICE with breakpoints on $104d/$1104/$12d8 while
playing out/Tri_d15.sf2 in SF2II_dbg, or model the X=2 first 3 frames in py65).
Reproduce: `py -3 bin/fc_to_sf2.py SID/Fun_Fun/Triangle_Intro.sid out/Tri_d15.sf2
--d15` then `bin/sf2ii_vs_real.capture_sf2ii('out/Tri_d15.sf2',18)` (ctrl r4/r11/r18
bit0; freq r0/1,r7/8,r14/15). d15 disasm: scratchpad/d15_disasm.txt (regen from
bin/drivers/sf2driver15_00.prg). Default emit = D11 flat; --d15 experimental.

Steps to debug:
1. Trace D15's per-voice note-on/gate state machine. Voices loop X=2,1,0 (osc3 is
   X=2, processed FIRST). Key code in scratchpad/d15_disasm.txt:
   - init: ~$101f-$1029 (sets ZP $5b/$5c/$5d=0, $03=$80)
   - orderlist fetch: $1051-$1083 (needs $5b,x==1 and $0d,x==0)
   - sequence advance: $1085-$10e6 ($07,x duration counter; $7f at $10e0 -> DEC $0d)
   - gate-on path: $10ee CPY #$01 / $10f2 CPY #$00 -> $1104 (sets $55,x=$ff gate on),
     vs $10f6 (sets $55,x=$fe gate off). Y = $5b,x.
   - SID writes: $1291-$12b3 ($d404 = $4c,x AND $55,x).
2. Check whether the voices are SCRAMBLED rather than osc3 independently broken:
   osc2's captured freqs ($057B, $0296) look BASS-range, not lead-range — so the
   LEAD may have landed on osc2 and the bass on... nothing. Decode the 3 emitted
   orderlists in out/Tri_d15.sf2 and confirm each track's sequences contain the
   expected voice (track0=arp instr13-16, track1=lead instr10/notes 60+, track2=
   bass instr1/notes ~23). Then compare to which osc actually plays them.
3. Likely suspects: (a) the D15 init only fully sets up some voices; (b) a per-voice
   ZP state ($5b,x for X=2) not initialized; (c) the bass's drum (instr2, absolute-
   semitone wave program $80-$df) — verify D15's wave step handles col1 $80-$df the
   same as D11 (read $125c-$1290 fully; only partially read so far).

## AFTER osc3 is fixed
4. Verify all 3 voices play CORRECT notes on D15 (capture + compare to original SID
   per-voice, the reliable way).
5. Map the remaining D15 instrument columns (3,5,6,7,8 + the $13bd table) if needed
   for timbre fidelity (filter, gate flags). Currently only AD/SR/pulse/wave used.
6. Tune the D15 static pulse (currently fixed $08 = 50% for pulse voices) — FC's PWM
   is lost on D15 (no pulse table), accept static or fold into wave.
7. Decide default: keep D11 flat as default (works for most songs) and `--d15` for
   long-intro songs, OR auto-detect long intros and pick the driver.
8. Run the converter on the whole corpus; validate each tune per-voice.

## Task #2 — DONE (full FC<->SF2 round-trip complete, 2026-06-27)
Editor decrunched, native format decoded, and the round-trip BUILT + validated:
- `sidm2/fc_writer.py` — write_fc(FCSong) -> native FC PRG @ $1800 (FC->FC round-
  trip byte-identical in siddump).
- `sidm2/sf2_to_fc.py` + `bin/sf2_to_fc.py` — sf2_to_fcsong(sf2, template) reads a
  Driver-11 SF2 back to an FCSong. End-to-end FC->SF2->FC plays byte-identical
  (200/200 siddump frames). 16 FC tests green. CLI: `py -3 bin/sf2_to_fc.py
  edited.sf2 template.sid out.prg`.
Lossy edges (documented): FC notes 0/1 (SF2 floor clamp, silent), exact rest values,
glides; instruments come from the template so timbre is preserved.
Possible follow-ups: reconstruct FC instruments from Driver-11 columns (template-
free SF2->FC); preserve orderlist repeats/transpose in fc_writer for compactness.

## (historical) Task #2 — SF2->FC writer (was: unblocked + well-specified)
The FC editor was DECRUNCHED (out/fc_editor_v1_decrunched.prg) and its SAVE routine
RE'd: a native FC V1.0 module = a PRG @ $1800 = player + song data, saved $1800..
($03ff:$03fe). IDENTICAL to the layout fc_parser already reads. So the writer is the
INVERSE of fc_parser:
1. Player template: copy the fixed player code + freq table ($1d64) + pointer-table
   SLOTS from an existing module ($1800 up through the instrument base $2188). These
   addresses are HARDCODED in the player code so data must honor them: voice
   orderlist ptrs $1ea1(lo[3])/$1ea4(hi[3]); block-ptr table $1ea7 (lo/hi per
   block*2); instrument base $2188 (8 bytes/instr); freq table $1d64/$1dc4.
2. Lay out orderlists + blocks AFTER the instruments ($2288+); fill the pointer
   tables to point at them; write instruments at $2188.
3. Emit PRG @ $1800; end address = top of data.
FIRST MILESTONE: FC->FC round-trip — parse a native tune (out/fc_native/GAME_OVER.prg
or bin/FC10/"- game over.prg"), re-serialize via the new sidm2/fc_writer.py, and
verify it re-parses to the same notes (and ideally byte-diffs small / plays same via
siddump). THEN wire an SF2 source (parse the Driver-11 SF2 back to notes/instruments
-> FC tables). New file: sidm2/fc_writer.py. Reference: docs/players/FUTURECOMPOSER.md
"Native FC V1.0 on-disk module format".

## Longer-horizon (documented, not started)
- Task #1 (memory): the OTHER ~15 Fun_Fun rips use a SECOND player (init $C000, play
  $C475) or Sound Monitor — page-aligned orderlist pointer tables RE'd partially.
- D15 osc3/bass fix (the in-progress --d15 long-intro path, see top of this doc).
- Stage-B: PWM sweep, vibrato, mctrl&$80 noise-attack.
</work_remaining>

<attempted_approaches>
## Long-silent-intro: every D11 representation FAILED
- FLATTEN voice into one row-stream -> lead lands in a 960-row sequence with 288-row
  rest prefix -> SF2II skips the prefix, DRONES a wrong note. (current D11 default)
- ONE SEQUENCE PER BLOCK (preserve orderlist, replay short rest block 6x) -> an
  all-note-off sequence STALLS/HANGS the D11 orderlist -> 0 frames, whole song silent.
- MERGE rest-only blocks into the next content block -> plays, but the long rest
  PREFIX still mutes the lead AND it broke the bass (merge logic bug).
- Lowering `_SEQ_EVENT_LIMIT` (960->480->256->192->240) on the flat build -> ERRATIC
  SF2II results (silent / bass / arp content on the lead voice). NOT a clean length
  or rest-count threshold. Dead end.
- D14 template + structured build -> 0 frames (D14 also hangs on all-rest; flat
  build plays on D14, so the emitter is fine).
- All-rest PACKING is NOT the issue: Mood's `8F 00 00 00 00` (one duration, 4 note-
  offs) vs my `8F 00 8F 00...` unpack identically (duration persists across notes).

## Validation tooling: a costly false positive
- `bin/sf2_to_wav.py` -> `scripts/sf2_to_sid.py` (SF2->SID->WAV) gave a FALSE "all
  voices match note-for-note" while SF2II actually played the lead wrong. It does NOT
  reproduce SF2II's Driver 11 playback. The user caught this. ONLY trust
  `bin/sf2ii_vs_real.capture_sf2ii` (instrumented SF2II_dbg) for SF2II fidelity.
- Earlier I ALSO wrongly believed the dbg capture "doesn't start at row 0" (because
  osc3 showed a drum before note24). That was wrong — it DOES start at row 0; I was
  mis-offsetting frames in my analysis. The capture is reliable.

## D15 driver
- D15 has NO pulse/filter TABLES, but it DOES write pulse ($d402/3) from instrument
  col2 — so pulse is NOT lost (earlier worry was wrong).
- First D15 attempt (D11 instrument columns) -> scrambled voices. Fixed by adding
  instr_layout='d15'. Now osc1+osc2 play; osc3 still silent (the open bug).
</attempted_approaches>

<critical_context>
## Tooling / environment
- Project: SIDM2 (C:\Users\mit\claude\c64server\SIDM2). Windows, PowerShell + Bash.
- Run converter: `py -3 bin/fc_to_sf2.py <in.sid|in.prg> <out.sf2> [--d15]`
- SF2II GUI launch (to let user listen): launch `bin/SIDFactoryII.exe` with the sf2
  as arg + `--skip-intro`, WorkingDirectory = `bin/` (needs SDL2.dll + config there).
  Always kill prior SIDFactoryII/SIDFactoryII_dbg processes first.
- RELIABLE per-voice validation: `from sf2ii_vs_real import capture_sf2ii` (in bin/),
  returns {frame: [r0..r24]}. Voice ctrl regs: osc1=r4, osc2=r11, osc3=r18 (bit0=
  gate). Freq: osc1=r0/r1, osc2=r7/r8, osc3=r14/r15. Compare to the original via
  `pyscript/siddump_complete.py <sid> -tN` (unbracketed note = a new gated note;
  bracketed `(X)` = effect-driven change like arp/vibrato).
- Disassembler: `pyscript/disasm6502.py` (Disassembler6502(code, load, len);
  disassemble_range; format_output). Cached disasms in the session SCRATCHPAD:
  fc_disasm.txt (FC player), d11_disasm.txt, d15_disasm.txt. Regenerate from
  bin/drivers/sf2driver11_00.prg ($0d7e) and sf2driver15_00.prg ($0dfe).
- Tests: `py -3 -m pytest pyscript/test_fc_parser.py -q` (6 tests).
- Templates: `G5/examples/Driver 11 Test - Arpeggio.sf2` (D11, the Galway emitter
  default) and `G5/examples/Driver 15 Test - Mood.sf2` (D15, the --d15 template,
  has a working all-rest silent intro to model on).

## Driver 11.00 format (RE'd, sf2driver11_00.prg $0d7e)
Orderlist = [$a0+transpose][seq#]...$ff[looppos]. Sequence packed format (per SF2II
source datasource_sequence.cpp): $00=note-off, $01-$6f=notes, $7e=note-on/sustain,
$7f=end, $80-$8f=duration(&$0f, max 15), $90-$9f=duration+tie, $a0-$bf=set instr,
$c0-$ff=set command. Wave table 2-col (col0=waveform/$7f-jump, col1: $00-$7f=
semitones ADDED to note [arp], $80-$df=ABSOLUTE semitone [drums]).

## Galway emitter reuse
The FC converter rides on the Galway Driver-11 path: IR = `GalwayDriver11Song`
(instruments: List[D11Instrument]; wave_table: List[(wf,sem)]; pulse_table;
tracks: 3 flat List[D11Row]; tempo; pitch_base). Emitter writes by table NAME from
`parse_sf2_blocks(template, di).table_addresses` (keys 'Instruments','Wave','Pulse',
'Filter','Tempo','I'/'Init') so it adapts to whatever driver the template embeds —
EXCEPT the instrument COLUMN layout, which is what `instr_layout` now switches.
`segment_track(rows)` packs a D11Row list into sequences; `_SEQ_EVENT_LIMIT=960`,
`_MAX_SEQUENCES=128`. Orderlist body built as `[A0+trans][seq&0x7f]...FF 00`.

## D15 format (sf2driver15_00.prg $0DFE-$1BFD, "Tiny Mark I")
- Orderlist ptrs $17f4/$17f7; seq ptrs $17fa/$187a; wave table $14f4(wf)/$15f4(arg).
  ALL found correctly by parse_sf2_blocks (verified). Same packed format as D11.
- Instruments: 9 column-major cols at $13d4 (col stride 0x20=32 rows). SID writes
  ($1291-$12b3): col0->AD($d405), col1->SR($d406), col2->pulse($d403, &$f0->$d402),
  col4->wave-ptr($58). Wave programs are ALSO command-overridable (seq cmd $c0-$ff
  at $22,x indexes $1474/$14b4) but the INSTRUMENT's col4 is the default — my
  emission uses no commands so the instrument wave program is used.
- Note-on/gate: $55,x = gate mask ($ff on / $fe off); $d404 = $4c,x (waveform from
  wave step) AND $55,x. Gate-on path $1104 requires Y(=$5b,x)==0.

## Key gotchas
- SF2II's 6510 emulator: never `cmp` values >$7f apart (carry bug) — relevant if
  ever writing a native driver, not for table emission.
- The dbg auto-play CAN be confused into looking mid-song; verify frame 0 = INIT by
  checking osc1 silent + osc3 = the bass's actual first note.
- pitch_base off-by-one is real: must be calibrate-1 (else everything +1 semitone).
- Drum root frame: prepend the note's own pitch (relative 0) before the absolute
  drum-pitch rows, else the recurring drum note in the bass shows A#4 not B-3.
</critical_context>

<current_state>
## Deliverables status
- FC V1.0 parser (`sidm2/fc_parser.py`): COMPLETE + validated + tested.
- D11 converter (default, `bin/fc_to_sf2.py`): COMPLETE and WORKING for FC songs
  whose voices start together (arp/bass/drums/pitch/tempo correct; 2/3 native D64
  tunes fully play). KNOWN GAP: a voice with a long silent intro plays wrong.
- D15 converter (`--d15`): IN PROGRESS. Plays; the all-rest silent intro WORKS (the
  core breakthrough); osc1+osc2 gate; **osc3 (bass) silent — THE open bug to fix
  next.**
- Tests: 6/6 green. D11 default path UNBROKEN (verified all 3 voices play after the
  emitter changes).
- Docs: `docs/players/FUTURECOMPOSER.md` complete and current.
- Memory: `memory/future-composer-player.md` complete and current.

## NOT committed
Nothing has been git-committed this session (started from a clean `master`). New +
modified files are saved on disk but uncommitted: sidm2/fc_parser.py,
bin/fc_to_sf2.py, pyscript/test_fc_parser.py, docs/players/FUTURECOMPOSER.md,
sidm2/galway_driver11_emitter.py, sidm2/galway_to_driver11.py. The user said "save
work" — consider committing (branch first if required) before/after resuming.

## Output artifacts in out/ (temporary, regenerable)
- out/Triangle_Intro.sf2 = current D11 flat build (plays; lead intro wrong).
- out/Tri_d15.sf2 = D15 build (plays; osc3 bass silent — the debug target).
- Various out/Tri_*.sf2 = experiment artifacts (l192, l480, d14*, merge, etc.) —
  scratch, can be deleted.

## Current workflow position
Mid-way through the Driver 15 emitter port (the user's chosen "option 1" to fix long
silent intros). The hard part (all-rest intro on a capable driver) is SOLVED and the
emitter port is written. One concrete bug remains: osc3/bass silent in the D15 build
— resume by tracing D15's per-voice gate-on state machine (X=2 path) and confirming
the 3 tracks map to the right oscillators.
</current_state>
