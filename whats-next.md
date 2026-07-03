<original_task>
Reverse-engineer the Hawkeye/Maniacs-of-Noise (Jeroen Tel / "MoN") music player family,
build SID->SF2 converters + native SF2 drivers that load in stock SID Factory II (SF2II).
Standing goal: notes/order correct, then SOUND FIDELITY. This multi-session effort has done
Hawkeye + Cybernoid + Cybernoid_II. Corpus: SID/Tel_Jeroen/.

THIS SESSION's two directives, in order:
1. "read whats-next.md" then "yes" -> execute the (previously-approved) MULTISPEED fix for the
   Cybernoid LEAD ("track 1") that the user reported "sounds wrong when vibrating" (track 2 is
   fine). [This premise turned out to be WRONG — see below.]
2. "commit and then continue" -> commit the actual fix, then continue with the NEXT tunes:
   Myth + Supremacy (both SID/Tel_Jeroen/, same MoN engine family, structured differently).
3. "merge to master and continue with Myth + Supremacy".
</original_task>

<work_completed>

=== PART A: The Cybernoid "lead wrong when vibrating" — REAL ROOT CAUSE FOUND + FIXED + MERGED ===
The previously-approved fix (MULTISPEED=3) was based on a WRONG premise. After a full
re-diagnosis the real cause was a **SBC carry bug in the CPU emulator** (`sidm2/cpu6502_emulator.py`,
the CPU behind `siddump_complete.py`). MERGED TO MASTER.

- THE BUG: SBC set its carry-out from `if temp < 0x100` where `temp = A - value - borrow` is
  in [-256, 255] -> the condition is ALWAYS true -> carry was permanently stuck SET after
  every SBC. A real 6502 sets carry after SBC iff no borrow (`temp >= 0`). Present in BOTH the
  binary branch (~line 312) and the decimal branch (~line 300) of `sbc()`.
- WHY IT MANIFESTED: breaks multi-byte subtraction chains `SEC; SBC lo; SBC hi` (the low
  byte's borrow must propagate to the high byte via carry). MoN's VIBRATO uses a 16-bit SBC
  chain, so siddump computed a too-WIDE vibrato. The native SF2 driver is built FROM siddump,
  so it replayed the wrong vibrato -> "lead sounds wrong when vibrating." Single `SEC; SBC`
  (carry-in set explicitly) is unaffected, which is why most prior project validations were fine.
- THE FIX: `if temp >= 0:` set carry (both branches). Committed with 5-line comment.
- FILES CHANGED (committed 699c878 "Fix SBC carry bug in cpu6502_emulator (fixes MoN vibrato)"):
  * `sidm2/cpu6502_emulator.py` — the 2 carry conditions.
  * `pyscript/test_cpu6502_sbc.py` — NEW, 5 regression tests (single SBC no-borrow/borrow/zero
    + two 16-bit borrow-propagation chains; the 16-bit tests FAIL on the old code).
  * `whats-next.md` — (this file, previous version).
  * Branch `fix-siddump-sbc-carry` created off master, committed, then FAST-FORWARD MERGED to
    master and deleted. `git log --oneline -1` = 699c878.

- VALIDATION (all done):
  * py65 (correct 6502) and siddump now AGREE on the vibrato (lockstep CPU diff = no divergence).
  * VICE (cycle-accurate, the ground truth = what SF2II's reSID does) A/B: native-vs-original
    Cybernoid lead spectral distance 0.331 -> 0.189.
  * Hawkeye sub3 stays 100/100/100 byte-exact (compare ONLY the ~2s song length; the song halts
    at ~frame 129, so a longer window measures post-song silence and falsely reads ~47%).
  * ALL 1443 pyscript tests pass (100.31s) + the 5 new SBC tests.
  * Rebuilt from corrected siddump: Cybernoid sub0 = 11 parts, Cybernoid_II = 13 parts (no
    inflation). out/mon/*.sf2 (gitignored).

- RESIDUAL characterized + DISMISSED as trace-replay floor (NOT worth a procedural port):
  after the fix, native VICE spectral-dist = 0.189; a byte-exact bunched register replay floor
  = 0.168. Tested reproducing the original's intra-frame WRITE SCHEDULE (V2 -> delay -> V1+
  filter -> delay -> V0, gaps from `bin/_mon_write_schedule.py`): result 0.168, IDENTICAL to
  bunched -> the write schedule is IRRELEVANT (a procedural/cycle-scheduled driver would NOT
  help). Frame alignment also ruled out (shift 0 best; +1/+2 worse). The 0.168 is the
  fundamental floor of trace-replay vs the cycle-accurate original for a high-Q resonant filter.
  The native (0.189) already sits ~at that floor.

=== PART B: SUPREMACY — FULLY REVERSE-ENGINEERED + DATA-VALIDATED (parser NOT yet written) ===
SID/Tel_Jeroen/Supremacy.sid: load=$1000, init=$1000->$1079, play=$1003->$10D5, 3 subtunes,
4256 bytes ($1000-$209F). A compact FLAT MoN variant — NO relocation/wrapper (unlike Myth) —
a 5th orderlist model. Structure mapped via `bin/_mon_disasm.py` and CONFIRMED against the
actual data bytes (freq table is a clean semitone ramp, orderlist ptrs sane in-range,
orderlist data decodes exactly per the dispatch). ALL tables located:
  - INIT $1079: A=subtune; ASL A x3 -> subtune*8 -> $1048 (self-mod idx). LDA $16E3,Y ->
    $12BD = per-subtune BASE added to pattern pointers. $D417=$08. Per-voice $1013,Y=$FE
    (gate mask); voice SID-offset table $1010 (0,7,14).
  - PLAY $10D5 (gated by $1035): $D418=$06. OUTPUT (X=2..0, Y=$1010,X): $D400/1<-ZP $F9/$FC,X
    (freq); $D402/3<-$1049/$104C,X (pulse); $D405/6<-$1052/$1055,X (AD/SR); $D404<-$104F,X AND
    $1013,X (ctrl gate-masked). TEMPO $1006/$1019/$10DB; song-end -> $117B. SEQUENCER: DEC $EF;
    reload speed table $16E2+subtune*8 ($80 sign-toggle); per-voice if $F0,X!=$FF -> JSR $134A.
  - ORDERLIST PTR TABLE: $16DC + subtune*8 + voice*2 (lo/hi). Verified: sub0 -> $194C/$1960/
    $1985; sub1 -> $1D67/6B/6F; sub2 -> $1DFE/E07/E10.
  - ORDERLIST BYTE DISPATCH $11DF (read via ($E0),Y): >=$80 -> AND$7F -> $1007,X (TRANSPOSE),
    next byte; >=$70 -> AND$0F -> $100D,X, next; >=$40 -> AND$1F -> $1016,X (REPEAT), next;
    <$40 -> $E3,X (PATTERN INDEX), INC $1016; cmds $FD (4 bytes, pattern ptrs = val+transpose+
    $12BD), $E0+ (AND$1F -> $F6,X), $FE (song-end -> $117B).
  - PATTERN PTR TABLE: $16F3(lo)/$171C(hi), indexed by pattern index. Verified pat 1..12 ->
    $19C0..$1B04 in-range (pat 0 -> $B1FD OOR = unused; indices effectively 1-based).
  - PATTERN BYTES = STANDARD MoN FORMAT (same as Hawkeye/Cybernoid): $C0-$FF = command
    (instrument/effect), $80-$9F = duration, $00-$7F = note. E.g. pat5 @$1A3B `C7 84 6A 1F 24
    26...`. => the existing mon_parser pattern-decode logic largely APPLIES.
  - FREQ TABLES: $1650 (lo) / $1696 (hi), note-indexed (code does LDA $1644,Y / $168A,Y; the
    12-semitone data starts at +$0C, so note byte offset ~+$0C). Verified 12-semitone ramp:
    LO $1650 = 2E 38 5A 7D A3 CC F6 23 53 86 BB F4.
  - INSTRUMENT TABLE $186D (2-byte records, indexed by $1026,X). CTRL/WAVEFORM TABLE $1947.
  - NOTE HANDLER $134A: portamento/slide ($102F/$1029/$102C,X) + instrument setup + note->freq
    via JSR $1644.
  - Speed table $16E2 (sub0=$02,sub1=$04,sub2=$82); per-subtune base $16E3 (FD/08/FD).

=== MEMORY UPDATES (persistent, C:\Users\mit\.claude\...\memory\) ===
- NEW `siddump-sbc-carry-bug.md` — the CPU bug (project-wide relevance) + MEMORY.md index line.
- `cybernoid-mon-orderlist-re.md` — corrected: multispeed DISPROVEN, SBC ROOT CAUSE + fix,
  residual = trace-replay floor / schedule irrelevant. (Prior wrong "MULTISPEED" section rewritten.)
- `myth-supremacy-mon-re.md` — Supremacy section rewritten with the full RE + data validation.
- MEMORY.md — added the SBC-bug index line at top.

=== SCRATCH TOOLS created this session (bin/, all "_"-prefixed) ===
- `_mon_multispeed_probe.py SID sub nframes` — per-voice distinct-freq-per-frame (disproved multispeed).
- `_mon_cpu_diff.py SID sub warmup` — lockstep py65 vs CPU6502Emulator; pins the divergent opcode.
- `_mon_write_schedule.py SID sub frame` — cycle position of every $D4xx write in one play call.
- `_mon_regreplay.py SID sub secs [bunched|sched] [out.sid] [shift]` — replay captured regs as a PSID.
- `_mk_probe.py PART.sf2 out.sid` — wrap a native part SF2 as a PSID probe (native play=$1003).
- `_mon_filter_diff.py`, `_mon_filt_hist.py`, `_mon_v0_exact.py`, `_mon_voice_cmp.py`,
  `_mon_filter_restart_probe.py` — filter/vibrato diagnostics.
</work_completed>

<work_remaining>

=== SUPREMACY — PARSER INTEGRATED (6/9 voices byte-exact); remaining = arp/command voices + build ===
DONE this session: `sidm2/mon_parser.py` now has ol_mode='supremacy' (`_locate_supremacy`
signature-detects + locates tables; `_orderlist_ptr`/`_voice_blocks`/`_pattern` branches +
`_pattern_supremacy` + note_base in `_emit`). Note formula SOLVED: note = (pattern_byte +
orderlist_transpose($80+ &$7F) + subtune_base($16E3[sub*8] signed)) & $7F. Validated vs py65
freq-lookup ground truth: 6/9 (subtune,voice) BYTE-EXACT (sub0 all 3, sub1 v0/v1, sub2 v2);
the 3 misses are arp/command voices (base notes mostly right). All 9 old MoN tests pass +
new `pyscript/test_supremacy_parser.py` (3 tests). Tables: orderlist $16DC+sub*8+voice*2,
pattern $16F3/$171C, freq $1644/$168A, base $16E3, speed $16E2(stride8,&$7F), instr $186D.
REMAINING for Supremacy:
1. Complete the arp/command voices. My `_pattern_supremacy` is a WORKING APPROXIMATION; the
   PRECISE dispatch (disasm $1246+, see memory) differs: NOTE range is <$60 (not <$70);
   $60-$7F = wave-program (b&$1F -> $1064); $80-$BF = duration (AND$7F, ADDITIVE to $F3);
   $C0-$DF = instrument (idx=(b+$100D)&$1F, stride 7); $E0-$FF = rest/note-off (AND$1F->$F6)
   EXCEPT $FA (loop $1212) + $FD (3-byte command). ORDERLIST also has $Fx commands (sub1 v2
   `...00 FA 08 D2...` — $FA currently mis-read as transpose $7A -> desync). Pattern
   termination is NOT a clean $FF (it's a rest) — orderlist-driven; needs care. Re-validate
   all 9 voice/subtunes vs py65 after each change (bin/_supremacy_validate.py pattern).
2. Capture $6x/$7x WAVE/ARP programs (arp data ~$1855) for native fidelity (like Cybernoid wprog).
3. Stage-A + native build (reuse bin/mon_to_sf2.py + bin/build_mon_native_song.py); validate
   vs siddump + VICE; GUI-confirm in SF2II.
[ORIGINAL detailed RE notes below retained:]
- (historical) Add a Supremacy path to `sidm2/mon_parser.py`. It has orderlist variants (ol_mode
   selfmod/stride); add a NEW variant. Key differences from Hawkeye/Cybernoid:
   - Per-voice-per-subtune orderlist start = word at $16DC + subtune*8 + voice*2.
   - Orderlist dispatch is PREFIX-based (NOT the $F0/$E0/$C0/$80 nibble prefixes of Cybernoid):
     >=$80 -> transpose (AND$7F); >=$70 -> AND$0F ($100D role TBD); >=$40 -> repeat (AND$1F);
     <$40 -> pattern index; $FD/$E0/$FE = commands.
   - Pattern lookup: pattern index -> word at $16F3[idx]/$171C[idx].
   - Pattern bytes: REUSE the existing MoN pattern decode ($C0-$FF cmd / $80-$9F dur / $00-$7F note).
   - Freq: note -> ($1650[note] | $1696[note]<<8) (mind the ~+$0C index offset; verify against
     siddump note pitches). Instruments $186D (stride/fields TBD — inspect like Cybernoid).
   - Locate tables relocation-safe via player-code signatures (like the rest of mon_parser),
     OR hardcode for Supremacy first then generalize.
2. VALIDATE note decode vs siddump (per-voice onset match), the Cybernoid way — use/adapt
   `bin/mon_sf2_validate.py` (Stage-A Driver-11) and `bin/mon_part_fidelity.py`.
3. Native build: reuse `bin/build_mon_native_song.py` (register the Supremacy load/tables).
   Then VICE ear-equivalent check (`bin/listen_compare.py`). GUI-confirm in SF2II.
4. Remaining unknowns to nail during impl: exact instrument record stride/fields at $186D; the
   role of $100D ($70+ orderlist byte) and $16F3/$171C secondary setup at $1191 vs the $16DC
   setup at $11B9 (both set $E0/$E1 — confirm which is orderlist-advance vs pattern-fetch);
   the $FD command's 4-byte payload semantics ($102F,X + two pattern ptrs).

=== MYTH (do SECOND — bigger: relocating compilation + play=$0000 self-IRQ) ===
Structure already mapped in memory (myth-supremacy-mon-re.md). Remaining:
- (a) map the NOTE handler $93CA (relocated; source $23CA) — note->pitch/dur/instrument/wave;
- (b) add a Myth-class mon_parser path: relative-ptr + $900A:B relocation base + orderlist @
  $9B8B + pattern ptr table @ $91B2/$91B3; pattern byte dispatch at $22DE+ (<$60 NOTE, $FF end,
  $FE 2-byte cmd, $FD 1-byte cmd) — DIFFERENT from both Cybernoid and Supremacy;
- (c) a RELOCATION step: build a 64K image = binary at $1D00 + emulate the copy $2000->$9000
  (sub0) / $3E00->$A400 (sub2) via the wrapper routine $1DC0, then parse MON(image, la=0, sub).
  (Confirmed: with the relocated image, freq=$90F4/$9153, instr=$9073, speed=$991D resolve.)
- (d) play=$0000 IRQ tracing for the native build + fidelity (wrapper installs its own IRQ at
  $1D59: SEI; $01=$35; JSR $1F55). Use siddump play=0 path / the zig64 IRQ path.

=== OPTIONAL / LOWER PRIORITY ===
- Ear-confirm the committed Cybernoid SBC fix in SF2II (user's real validation; I can't do it
  headlessly): `py -3 pyscript/sf2_open_in_editor.py out/mon/Cybernoid_sub0_part01.sf2 40`.
- The tiny native-driver 0.189->0.168 gap (RLE/cluster/$00-silent-note/filter-seam) — low value.
- Pulse still not visible/editable in SF2II across the MoN builds (driver-internal bundle).
</work_remaining>

<attempted_approaches>
CYBERNOID LEAD — all RULED OUT (do NOT repeat):
- MULTISPEED=3 (the previously-approved fix): DISPROVEN. `bin/_mon_multispeed_probe.py` shows
  exactly 1 distinct V0 pitch per play call across 3000 frames (Cybernoid sub0/sub3, Hawkeye
  sub3). MoN is single-speed. The old "3 pitches/frame ($0300,$13EF,$0130)" was the THREE
  VOICES' freq writes ($D400/$D407/$D40E) misattributed to V0 (cross-check: $13EF=V0,
  $0130/$0300=V2, same frame). The prior "110%->72% replayer proof" was an artifact of
  bunching writes. Building MULTISPEED=3 would do nothing but triple table pressure.
- SID model 6581/8580: user ruled out (track 2 is also pulse+filter and is fine).
- Intra-frame write ORDER (voice-major): prior session got EXACTLY identical WAV. No effect.
- Intra-frame whole-burst write TIMING: injected ~1785-cycle delay before do_play synthesis
  (DELAY_TEST flag, then reverted) to shift writes to the original's ~8%-into-frame offset ->
  VICE 2.88 vs 3.03 semitones, 0.331 vs 0.330 spec = ZERO change.
- Intra-frame write SCHEDULE (spread, voice-major, filter-between): the `sched` regreplay =
  0.168 = identical to bunched. Schedule is IRRELEVANT.
- EMBED the original player: SF2II crashes (0xC0000005) for both Hawkeye/Cybernoid; high-load
  path ignores voice_streams -> empty placeholder -> segfault. Not a quick fix.
- PROCEDURAL DRIVER (path B, briefly chosen by the user before the SBC discovery): NOT NEEDED.
  Proven: MoN has ZERO SID-register reads (pure computation, no live-SID feedback), and the
  write schedule is irrelevant, so a procedural port would produce the same per-frame values
  bunched and NOT beat the trace-replay floor. The SBC fix was the complete audio fix.

GOTCHAS hit this session:
- py65 vs siddump DISAGREED on the vibrato values — this was the clue. py65 (battle-tested
  6502) is correct; siddump's CPU6502Emulator had the SBC bug.
- py65 has NO SID emulation, so a py65-captured register replay is only valid because MoN reads
  zero SID registers (verified). For players that DO read SID state, py65 capture is invalid.
- `_mon_regreplay.py` scheduled-stub bug: `STA $D400+r,Y` with Y=r writes to $D400+2r — use
  ABSOLUTE STA ($8D), not STA abs,Y ($99), when Y already holds the register index.
- `git stash` blocked on build-scratch .inc (`drivers_src/{mon,romuzak}/layout.inc`,
  `mon/freqtable.inc` are BUILD-GENERATED) — `git checkout` them before stash/merge ops.
- Bash tool is Git Bash, NOT PowerShell: `@'...'@` here-strings FAIL; use `git commit -F file`.
- The disassembler `bin/_mon_disasm.py` misaligns on data regions (linear decode) — cross-check
  suspicious opcodes; a whole-image opcode scan for "$D4xx reads" produces false positives.
</attempted_approaches>

<critical_context>
- KEY META-LESSON: when a trace-replay driver SOUNDS wrong but every per-frame register looks
  byte-exact via siddump, suspect the CAPTURE tool's CPU, not the driver. Cross-check siddump
  vs py65 (register values) and VICE (cycle-accurate audio = ground truth for what SF2II does).
  siddump (1 sample/frame, its own CPU) can be byte-exact yet audio-wrong two ways: a CPU bug
  (the SBC bug) OR intra-frame effects.
- THE FIX FILE: `sidm2/cpu6502_emulator.py` `sbc()` — carry now `temp >= 0` (was `temp < 0x100`),
  both binary + decimal branches. Guarded by `pyscript/test_cpu6502_sbc.py`. This CPU is used
  PROJECT-WIDE (Galway/ROMUZAK/Laxity/etc. all siddump-based); the fix is strictly more correct
  and all 1443 tests still pass, but only chained SBC (no re-SEC) manifests the difference.
- MON PARSER: `sidm2/mon_parser.py` — decodes the two-level MoN format; has orderlist variants
  (`ol_mode` selfmod/stride for Hawkeye/Cybernoid/Cybernoid_II). Supremacy needs a NEW variant
  (prefix-dispatch orderlist). Tables are located relocation-safe via player-code signatures.
- NATIVE BUILD: `bin/build_mon_native_song.py` — trace-replay driver (`drivers_src/mon/
  romuzak_driver.asm`, a ROMUZAK-engine copy) fed per-frame FM/pulse/wave/filter programs from
  siddump. RLE wave rows, adaptive part-packing (caps: 64 command bundles $c0-$ff, 32
  instruments $a0-$bf, 256 WAVE/FILTER rows, 120 seq-ptrs, $D000 memory wall). Build-scratch
  `drivers_src/{mon,romuzak}/layout.inc` + `mon/freqtable.inc` are REGENERATED each build ->
  `git checkout` before committing.
- BUILD/TEST COMMANDS:
  * `py -3 bin/build_mon_native_song.py SID/Tel_Jeroen/Cybernoid.sid 0 auto` (adaptive parts)
    or `... 0 38` (fixed 38s parts for quick tests).
  * `py -3 -m pytest pyscript/test_mon_parser.py pyscript/test_mon_to_sf2.py
    pyscript/test_cpu6502_sbc.py -q` (fast MoN+SBC set).
  * `py -3 -m pytest pyscript/ -q` (full suite, ~100s, 1443 pass).
  * Native fidelity (siddump, part-aligned): `bin/mon_part_fidelity.py PART SUB SECS T0` —
    compare ONLY the song length for short/halting subtunes.
  * VICE ear-equivalent (autocorr pitch + log-mel spec-dist): `bin/listen_compare.py orig.sid
    mine.sid SECS TUNE` (TUNE 1-based; controls orig-vs-orig = 0.000). Build `mine.sid` via
    `bin/_mk_probe.py PART.sf2 out/x.sid`.
  * Cycle-accurate WAV: `tools/SID2WAV.EXE` (ABSOLUTE paths + cwd=ROOT, or CreateProcess fails).
- SF2II CMP-CARRY caveat for native drivers: SF2II's 6510 computes CMP carry from bit7 of
  (A-op), only right for |A-op|<=$7f. Native driver dispatch on values >$7f apart must use
  bit-tests (bmi), not CMP.
- Supremacy addresses (all confirmed): orderlist ptr $16DC+sub*8+voice*2; pattern ptr $16F3/
  $171C; freq $1650/$1696; instr $186D; ctrl $1947; speed $16E2; base $16E3->$12BD; init $1079;
  play $10D5; note handler $134A; freq lookup $1644; song-end $117B.
- Myth addresses (memory): wrapper init $1D00, copy routine $1DC0 ($2000->$9000 sub0, $3E00->
  $A400 sub2), relocation base $900A/$900B, orderlist $9B8B, pattern ptr $91B2/$91B3, note
  handler $93CA, pattern dispatch $22DE+, play=$0000 self-IRQ at $1D59.
</critical_context>

<current_state>
- COMMITTED + ON MASTER (699c878): the SBC carry fix + `pyscript/test_cpu6502_sbc.py`. Branch
  `fix-siddump-sbc-carry` merged (fast-forward) and deleted. Working tree clean except the
  pre-existing (NOT this work) `bin/SIDFactoryII_dbg.exe` modification and untracked scratch
  (bin/_mon_*.py, out/, etc.). Build-scratch .inc reverted.
- The Cybernoid lead vibrato defect is FIXED (VICE spectral-dist 0.331->0.189; vibrato values
  now byte-correct). NOT yet user-ear-confirmed in SF2II. Residual (0.168) is trace-replay
  floor, schedule-independent, not worth chasing.
- SUPREMACY: fully reverse-engineered AND parser INTEGRATED into sidm2/mon_parser.py
  (ol_mode='supremacy'), 6/9 (subtune,voice) byte-exact vs py65 ground truth; new
  pyscript/test_supremacy_parser.py (3 tests) + all 9 old MoN tests pass. UNCOMMITTED (user
  said "go ahead with supremacy" = do the work, not commit). Remaining: complete the 3
  arp/command voices (precise $1246 pattern dispatch + orderlist $Fx cmds, in memory), then
  wave/arp capture + Stage-A/native build + siddump/VICE validation.
- MYTH: structure mapped in memory (relocating compilation + play=$0000 IRQ); needs the NOTE
  handler decode + Myth-class parser + relocation step + IRQ tracing. Do AFTER Supremacy.
- All findings checkpointed to persistent memory (siddump-sbc-carry-bug.md,
  cybernoid-mon-orderlist-re.md, myth-supremacy-mon-re.md, MEMORY.md index).
- Last user instruction: "merge to master and continue with Myth + Supremacy." Merge is DONE.
  The plan is to implement the Supremacy parser next (RE complete), then Myth. Open question
  offered to the user: proceed straight to the Supremacy parser vs ear-check Cybernoid first
  (recommended: proceed to the Supremacy parser).
</current_state>
