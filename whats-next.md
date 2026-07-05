<original_task>
User request (a single directive, then repeated "go on"): "please fix the optional issues"
listed in the PRIOR whats-next.md, then — when part-count turned out to need deep work —
"go on" (repeatedly) to pursue the lossless part-count re-architecture.

The three "optional issues" from the prior handoff (Supremacy + Myth MoN native builds were
already COMPLETE and committed):
  1. Myth sub0 FILTER ~53% (the one weak register; ear-confirmed fine but low fidelity).
  2. PART-COUNT: Supremacy sub2 = 70 files, Myth sub0 = 7 files (correct/byte-exact, just many).
  3. GUI/ear-confirm the not-yet-listened parts (needs the user's ears — cannot be done by me).

Project: SIDM2, C64 music tools. This thread is the Jeroen Tel / "Maniacs of Noise" (MoN)
SID->SF2 native-driver line of work (SID/Tel_Jeroen/). Standing goal: notes/order correct,
then SOUND FIDELITY (~100% freq/waveform/pulse/filter), BYTE-EXACT where possible. The
byte-exactness is the project's crown jewel — do NOT ship lossy output silently.
</original_task>

<work_completed>

=== ISSUE 1: MYTH sub0 FILTER — FIXED + COMMITTED (a10bdd0) ===
Raised the MoN native-driver filter fidelity on multi-shape tunes, no regressions.
- Myth sub0: ~53% -> ~90% weighted (part1 77%, parts 2-7 = 90-98%).
- Hawkeye sub3: 56% -> 99% (bonus; freq/wf/pulse already 100%).
- NO regression: Hawkeye sub2 96.5%, Myth sub2 95.7% (full-song, 1 part), Supremacy 100% (no
  filter drives).
Root cause (in `bin/build_mon_native_song.py`, `build_native_song`): (a) drives were
mis-attributed to unrouted voices (Myth sub0 routes filter to voice 1 via $D417 low nibble, but
7 drives were credited to the unrouted voice 0); (b) the per-instrument canonical filter program
conflated Myth sub0's co-existing envelope SHAPES (up-ramp-from-64 / down-ramp-from-128 /
closed-at-0 across song sections); (c) a 1-frame phase error (note-on leads the cutoff reset).
Three fixes:
  1. `routed_voice(ftr)` — dominant single-bit $D417 low-nibble routing bit -> 0/1/2 (or None).
     `detect_filter_drives(ftr, onsets, routed)` now restricts restart mapping to that voice.
  2. Canonical filter program keyed by COMPOSITE (MoN instrument, envelope shape) instead of
     per-instrument. Hawkeye's shape is fixed per instrument -> collapses to per-instrument
     (unchanged, 96.5%); Myth sub0's instrument spans sections -> splits into its shapes.
     `_shape_sig(o)` reads one frame PAST the onset (skip the note-on transitional cutoff);
     signature = (settled base hi & 0xF8, initial delta hi clamped -8..+8). Canonical = the
     FULLEST-span drive of each (instr, shape) key, captured from the onset (phase-correct).
  3. Removed the earlier `global_filter_program` / `_filter_reset_frames` dead ends (see below).
Guarded by NEW `pyscript/test_mon_filter.py` (7 tests: routed-voice detection, drive restriction,
fast-sweep NOT over-detected, a filter-program round-trip through a faithful model of the driver's
`filt_prog_step`, up/down ramps distinct). All 1459 pyscript tests pass.
Verify: `py -3 bin/build_myth_native_song.py 0 auto` then
`py -3 bin/mon_part_fidelity.py out/mon/Myth_sub0_part01.sf2 0 46 0` -> filter 77%.

=== ISSUE 2: PART-COUNT — root cause proven; structural rebuild STARTED, arp parser committed ===

--- 2a. ANALYSIS (answered the user's own question; hypothesis confirmed) ---
The user asked "what is the issue with the size? instruments, wave, pulse, notes? ... some of
the problem is you replicate wave/pulse/instruments/filters very close to each other; the
original SID fits in 32K." CONFIRMED with data. For Supremacy sub2, PRE-cluster resource usage
of a 30s window vs the SF2II driver HARD caps (per SF2 file): bundles 178/63, instruments 87/32,
wave-rows 570/256 — THREE caps blow at once, and the song is 588s -> ~8s/part -> ~70 files.
NEAR-DUP PROOF: the 87 instruments collapse to only 5 distinct (AD,SR,waveform) cores — all 87
exist from WAVE-PROGRAM variety. Bundles: 178 -> 95 distinct pulse-progs, 171 distinct FM contours.
ROOT CAUSE: the trace-driven build captures per-NOTE, unrolling the player's CONTINUOUS/COMPACT
looping tables (why the original fits in 32K). Proven with `bin/_freerun_proof.py` (deleted):
free-running per-voice streams from the trace do NOT compress (817 wave RLE rows/30s, up to 741
FM rows/voice) and are only 62-97% semitone-exact — because the trace is UNROLLED OUTPUT; the
player's compactness lives in table JUMPS/LOOPS the trace can't recover. => NO trace-based method
(per-note bundles OR free-running streams) can reduce the part count losslessly. The ONLY path =
structural RE of the player's synth engine (extract its looping wave/pulse/arp tables + selectors).

--- 2b. STRUCTURAL RE — BOTH SYNTH ENGINES CRACKED (documented in memory) ---
Disassembled Supremacy sub2's synth engine (`bin/_mon_disasm.py START END SID` + emulation write-PC
probes, since raw disasm misaligns on illegal opcodes):
  * ARP/PITCH engine ($15CB-$1643): the $60-$7F pattern byte -> `AND #$1F -> $1064,X` (arp index);
    ptr = $1746[$1064] + $17C0 -> program bytes; per-voice position $1067, dur counter $106A
    (-$10/frame). Byte $FF=LOOP (nibble-offset target), $FE=END, else=ARP VALUE -> $106D. Applied:
    `$106D + $F0 -> freq lookup` => $106D is a SIGNED SEMITONE OFFSET (pitch-INDEPENDENT). Resets
    per note ($1067=0 at note-on). Table dump ($1746 index=[00 05 0a 0f...], $17C0 programs):
    `10 00 03 07 ff`=[dur$10; arp 0,+3,+7 minor; loop], `10 00 04 07 ff`=major, etc. ~16 chord arps.
  * WAVEFORM/GATE engine (`bin/_supr_wf_probe.py`, deleted): per-frame $D404 = $104F,X AND $1013,X.
    NOT a complex table — a plain attack+steady+release gate envelope, SAME for every note, only
    the steady LENGTH varies. v1: 3-frame onset transient ($D404 $10,$41,$11), steady $41, gate-off
    release. v0 (wprog27 octave arp): onset $40,$41,$81, steady $41, note RE-TRIGGERS ~every 40
    frames (re-attack). So the 87-from-5 instrument explosion = capturing the VARIABLE-length steady
    + internal re-triggers per note. FIX (future) = wave program [attack][steady + $7f LOOP],
    duration held by the sequence -> collapses 87 -> ~5.
  * Instrument table = $1868 stride 7: [0]=$1020 effect [1]=$1869 ctrl/wf [2]=AD [3]=SR [4]=pulse.

--- 2c. ARP PARSER — COMMITTED (400d2e0), byte-exact, tested ---
`sidm2/mon_parser.py`: added `MON.arp_program(wprog)` + arp-table location in `_locate_supremacy`
(relocation-safe signature `BD 64 10 A8 B9 <idx> 18 69 <off> 85 E0 A9 <hi>` -> tbl_arp_idx=$1746,
tbl_arp_base=$17C0). Returns `{'dur','steps','loop'}` (steps = signed semitone offsets). Verified
byte-exact from ROM (wprog 0 [0,3,7] minor, 1 [0,4,7] major, 4 [0,3,8], 27 octave) AND against a
py65 $106D trace (v1 wprog4 [0,3,8] cycles exact; v0 octave; v2 none). NOTE: uses `self._u8(a)`
(the memory accessor is `_u8`, NOT `_mem`). Guarded by `test_supremacy_arp_table` in
`pyscript/test_supremacy_parser.py`. All 18 supremacy/filter/mon-parser tests pass.

--- 2d. FM WIRING — PROTOTYPED, DEMONSTRATED (bundles 178->127, arp byte-exact 1 note), then REVERTED
(blocked on note-timing; not byte-exact over the window) ---
Reverted from `drivers_src/mon/romuzak_driver.asm` + `bin/build_mon_native_song.py`. The exact
changes (to RE-APPLY next session) are documented in memory/myth-supremacy-mon-re.md:
  * Driver fm_step: SEMITONE entry (byte2 bit7 set -> dur=byte2&$7f, byte0=signed S,
    FM_ACC = freqtable[(vbasenote+S)&$7f] - vfreq; the accumulate branch unchanged for Hz-delta).
    LOOP entry (byte2=$7f -> FMP = VIFM + byte0*3, where byte0 = loop-back entry index; matches
    the ROM's $ff+nibble-offset). Runaway guard via ws_grd (set at fm_run, dec in fm_loop, freeze
    at 0). ENCODING: byte2 $00=freeze, $01-$7e=Hz-delta (durs must be capped <127 in the emitter!),
    $7f=loop, $80-$ff=semitone. `cmp #$7f` used only when A is $01-$7f (SF2II CMP-carry-safe).
  * Build: `arp_fm_program(prog, fpt)` = [base-hold (0,0,$81)] + per-step semitone entries
    (fps=(dur>>4)+1 frames each) + loop-to-entry-1 (1,0,$7f). `_fm_for_note(...)` (flag
    MON_ARP_STRUCT) uses arp_fm_program when the note's wprog gives a non-trivial arp (steps!=[0]);
    else fm_program_for. Also capped fm_program_for Hz runs at 126 (so byte2 stays <$80).
  * RESULT: count_only bundles 178 -> 127 (real collapse). Flag-OFF = zero regression (Hawkeye
    sub3 100/100/100). Frame-diff vs original (voice 1, first note): frames 2-79 BYTE-EXACT — the
    semitone entry, loop entry, and 1-frame base-hold lead-in ALL work.

=== ISSUE 3: GUI/ear-confirm — cannot be done by me (needs user's ears). Not attempted. ===

=== GIT / TESTS ===
Two commits this session on master (both pushed? NOT verified — check `git status` for ahead count):
  a10bdd0 MoN filter: composite (instr, shape) canonical + routed-voice drives  (2 files)
  400d2e0 Supremacy: parse the arp/wave-program table (structural FM-cap foundation)  (2 files)
All pyscript tests green (1459). Memory updated: myth-supremacy-mon-re.md (extensive; the arp +
waveform engine RE, the FM-wiring prototype, and the note-timing blocker).
</work_completed>

<work_remaining>
Everything below is the LOSSLESS PART-COUNT structural rebuild (issue 2). Ordered:

1. **Note-timing reconciliation — ✅ DONE 2026-07-05 (TWO root causes, both fixed + committed).**
   (a) **SWING TEMPO**: the Supremacy speed byte's $80 bit (sub2 = $82) makes the tempo-gate
   reload ($1128-$114D) toggle $E2 and alternate periods speed/speed+1 (2,3 = avg 2.5 f/tick,
   NOT the constant speed+1=3). Fixed: `MON.tick_to_frame/frame_to_tick/tempo_toggle/onset_delay`
   (mon_parser), driver swing reload (SWTOG in drivers_src/mon do_row + TEMPO2 in layout),
   build_mon_native_song fr accumulation now tick-exact. (b) **PREFIX-CHAIN RETRIGGER**: a $Cx
   instrument (or dur/wave) byte followed by another prefix >= $C0 finalizes the event WITHOUT
   a note byte = retriggers the previous note with sticky dur ($1246-$12C1 disasm) — the missing
   3rd onset per phrase on sub2 V2. Also fixed `_fm_curve` cluster blindness (24-frame prefix ->
   full freeze-extended program; a forced merge had frozen a voice at freq 0 for 20 frames).
   RESULTS: mon_validate Supremacy sub2 = 220/220 EXACT (all 3 voices); part1 fidelity (adaptive)
   = osc1 96/100/100 (residual = the unreproducible 2-frame onset spikes), osc2 100/100/100,
   osc3 100/100/100, filter 100; **auto part count 70 -> 43**. NO regressions: Hawkeye sub3 + sub2
   100/100/100 (delay 0), Cybernoid sub0 99.9/99/96 + 100/100. Remaining sub-issues (separate):
   sub1 V1/V2 arp-voice decode, sub0 staggered canon entries (parser misses per-voice lead rests).

2. **FM wiring — ✅ DONE 2026-07-05 (structural arps live behind MON_ARP_STRUCT=1).**
   Driver fm_step gained SEMITONE entries (byte2 bit7: dur=byte2&$7f, FM_ACC =
   freqtable[(vbasenote+S)&$7f]-vfreq, pitch-independent) + LOOP entries (byte2=$7f,
   FMP=VIFM+byte0*3, ws_grd runaway guard); Hz-run byte2 capped at 126 in the emitter.
   `arp_fm_program` is PHASE-ALIGNED to the ROM (step0 gets fps-1 frames — pr_note's
   base hold covers frame 0 — then the rotation step1..stepN,step0 at full fps, loop
   to the rotation start; validated by a fm_step-model round-trip test). Structural
   programs are cluster-exempt (_is_struct_fm: never similarity-merged). RESULTS
   (Supremacy sub2): bundles 79->52 on a 30s window; **auto parts 43 -> 36**; part1
   fidelity osc1 92.2/100/100, osc2 98/100/100, osc3 100/100/100, filter 100 — the
   trace path (96/100/100) minus the unreproducible per-note tail/onset spikes and
   the steps[0]!=0 trigger frame. Flag stays OPT-IN until steps 3-4 land (trace path
   is still the fidelity default). Flag-off + Hawkeye/Cybernoid: unchanged (verified).
   Tests: pyscript/test_mon_arp_struct.py (4). NEXT LEVER: instruments (32) + WAVE
   rows (256) now bind alone -> step 3.

2-old. (historical) **Re-apply the FM wiring** (driver semitone+loop entries + arp_fm_program + _fm_for_note; all
   documented in memory to re-apply verbatim). After step 1, the arp path should hit the trace
   path's ~98% (byte-exact minus the ~2-frame onset freq=0 spike/note, which the driver's
   frame-0=base model can't reproduce — same residual as the trace path). Validate:
   `MON_ARP_STRUCT=1 py -3 bin/build_mon_native_song.py SID/Tel_Jeroen/Supremacy.sid 2 8` then
   `py -3 bin/mon_part_fidelity.py out/mon/Supremacy_sub2_part01.sf2 2 8 0` (freq should be ~98%,
   bundles collapsed). No regression on Hawkeye/Cybernoid/Myth (flag off = untouched).

3+4 (partial). **Wave gate-split + canonical wave/pulse/FM — ✅ LANDED 2026-07-05 (flag-gated).**
   All three per-note program captures suffer the same disease: the tail holds DURATION-
   RELATIVE boundary content (wave: terminal gate-off + next-note attack bleed; pulse: the
   next note's base reset 1 frame early; FM: the end-of-note freq drop), so same-shape notes
   of different durations get distinct programs. Landed (all under MON_ARP_STRUCT=1, each with
   an exact unrolled-output guard + <=1-3 accepted boundary frames/note):
   (a) WAVE GATE-SPLIT: terminal gate-off -> sequence note-$00 rows (VGMASK=$fe masks the
       looping steady = the captured $40 tail); program = attack+steady only. NOTE the engine
       writes $D404 ~1 frame BEFORE the freq (per-register delay skew) -> gate-off sits 1 off
       the tick grid (tolerated) and captures have 1-2 bleed frames.
   (b) CANONICAL WAVE/PULSE/FM per (instr, wprog): longest note's program substituted when
       it reproduces the note's capture (masked for wave; minus 1/3 boundary frames for
       pulse/FM). Canonical-under-mask even fixes short "echo" notes better than their own
       capture ($41&$fe = the real $40 tail).
   RESULTS Supremacy sub2: 30s window bundles 79->32, instr 18->11, wave rows 73->24; part1
   fidelity freq 92/98/100, wf 92/97/97, pulse 98/100/100, filter 100 (boundary-frame cost
   ~3-8% wf — the documented flag trade); **auto parts 36 -> 34**. Flag-off + Hawkeye byte-
   identical (verified). Tests: test_mon_wave_struct.py (4). REMAINING part-count levers:
   (i) FREE-RUNNING PULSE PHASE (v2 instr 14/30/31: sweeps continue ACROSS notes -> 10-15
       distinct set-row phases/key; needs a driver "no pulse reset on note-on" instrument
       flag + per-voice stream emission) — the binding constraint at 45s+ windows;
   (ii) full-song canonicals are weaker than per-window ones (the standalone 30s build got
       50 bundles vs the 32 probe with window-local canonicals) — consider window-local
       canonical selection in the adaptive packer.

4b. **FREE-RUNNING PULSE + SCALED VIBRATO — ✅ LANDED 2026-07-05 (flag-gated).**
   (a) PULSE FREE-RUN: driver VIFLAGS $08 + PFREE latch (pr_note keeps PPTR/VPC after the
       first flagged note) + per-voice STREAM program (whole-window pulse RLE; detection =
       a key with >=3 distinct set-row starts, voice-instrument-disjoint guard). Part2 v2
       pulse 47% -> **100%**. GOTCHA FIXED: RN.gen_includes_song's flags emission DROPPED
       all bits except its own ($20/$10/$40 if/elif) — now ORs instr_flags & $48; the $08
       silently missing = the stream restarting per note.
   (b) SCALED VIBRATO FM entries: MoN vibrato depth = (semitone_step * scale) >> 8 (pitch-
       PROPORTIONAL; e.g. scale 30 = the v2 lead). Driver: hi=$40/$41 Hz entries -> offset =
       +-(VSTEP*byte0)>>8 via a 24-bit shift-add mul (out-of-line past fm_done — inline it
       blew branch ranges, 3 asm errors); VSTEP = freqtable[n+1]-freqtable[n] set at pr_note.
       Build: _vibrato_program (delay + centered half-leg + looping legs, EXACT-guarded via
       _fm_unroll(step=)). One program serves every pitch AND duration.
   RESULTS: 30s window bundles 32->24; 45s 82->70; part2 (30-60s) flag-on = osc1 87/87/94,
   osc2 96/96/98, osc3 63.5/98/100 vs flag-off 82/85/53 (freq BETTER, pulse 100%).
   Hawkeye/ROMUZAK regressions clean (100%). Also NOTE: fixed-30s flag-off builds still
   WAVE-overflow at part 6 (canonicalization is flag-gated); parts >=2 were NEVER measured
   before today — add part2+ to the standard validation.

5. **PORTAMENTO / 30-60s SECTION — DIAGNOSED 2026-07-05, implementation reverted (a first
   attempt made sub0 worse; accuracy-first). This is a DECODE problem before a driver one.**
   The osc3-freq-63% section (sub2 V2 from onset idx 88, fr 1512+; 60s-window bundle
   residual) findings, all from the $11B9-$1246 disasm + pattern-$0C hand-decode + trace:
   (a) V2's real note at fr1512 lasts 36 ticks; the parser emits 24t + two $Cx-retriggers
       at 1572/1582 that siddump does NOT show as onsets -> the prefix-chain RETRIGGER
       (step-1 fix, correct in 0-30s) is INSTRUMENT-CONDITIONAL — likely a flag bit in
       instrument record byte [0] (-> $1020; bit6 = arp enable, other bits TBD).
   (b) ORDERLIST is a FALL-THROUGH prefix chain ($11DF: >=$80 transpose&$7F -> read next;
       >=$70 -> $100D instr-base -> read; >=$40 repeat&$1F -> read; then STA pattern) —
       BUT implementing it verbatim broke sub0's validated note order while leaving V2
       unchanged. The reader's re-entry semantics must be settled with a py65 GROUND-TRUTH
       POSITION TRACE before trusting either model (the current independent-dispatch model
       is what all existing validation rests on).
   (c) PATTERN commands: $FA/$FD are NOT top-level bytes — only recognized as the byte
       AFTER a duration ($1295: $FA -> $1212 = 2-byte -> $10DB; $FD -> $121F) or after an
       instrument ($127D: $FD -> $121F). **$FD = the 4-byte SLIDE: speed -> $102F, note ->
       $F0 (+transpose +$12BD), target -> $1032, then FINALIZES at $12C1 (it IS a note
       trigger).** Top-level $E0-$FF = the REST handler $124A ($F6 = b&$1F, $F0 = $FF,
       ctrl/AD/SR zeroed, exits via $1343 — whether it consumes a duration slot is TBD).
   (d) THE TOOL TO BUILD FIRST: a py65 EVENT-BOUNDARY tracer (intercept the finalize at
       $12C1/$1343 logging Y, $E6, $E9, $F3/$F6, $1016 per event) — the same method as the
       freq-lookup tracer that cracked the note formula. With per-event ground truth the
       retrigger condition, rest timing, additive-duration and orderlist-chain questions
       all become mechanical. THEN the driver SLIDE entry (target+speed, like the scaled
       vibrato) is straightforward.
   Reference data: sub2 V2 orderlist `... 26 00 C0 88 79 0C C0 C0 18 0C ...`; pattern $0C
   @ $1AD1 = `C9 8C 61 2E 88 63 29 A0 27 90 67 26 88 63 26 CB FD 03 43 08 FF ...` (note the
   `CB FD 03 43 08` instrument+slide chain and the trailing $FF).

3-old. (historical) **Wave [attack][steady-loop] structural rebuild** (the INSTRUMENT cap, 87->~5). The waveform is
   attack + steady + release (RE'd); emit it as [attack transient][steady + $7f loop] so the note
   duration is held by the sequence gate-on rows (not the wave program). Byte-exact (attack is
   instrument-fixed; steady constant). Handle the ~40-frame internal re-trigger (confirm whether
   it's a sequence note-on -> dur naturally short, or an internal retrigger needing a wave-program
   retrigger row).

4. **Pulse structural** (pulse-progs were 95 -> RE similarly if it also explodes; may be arp/gate
   driven and collapse with the above).

5. **Only when ALL THREE caps (bundles/instruments/wave-rows) drop under does the part count fall.**
   A single prong yields NO part reduction (measured: caps bind simultaneously). Then measure the
   Supremacy sub2 auto part count (was 70) and Myth sub0 (was 7).

6. **SF2II load-test + byte-exact validation** across Hawkeye/Cybernoid/Myth/Supremacy (all
   subtunes) before committing. SF2II load: `py -3 pyscript/sf2_open_in_editor.py out/mon/PART.sf2
   40` (argv Heisenbug -> up to 40 retries; native play=$1003).

OPTIONAL/LOW: Myth sub0 filter part1 77% (the rapid multi-section opening; other parts 90-98%;
ear-confirmed fine). GUI-confirm the unlistened parts (needs the user).
</work_remaining>

<attempted_approaches>
FILTER (issue 1) — dead ends before the composite-key fix:
- `global_filter_program` (one global canonical for all driven notes): CATASTROPHIC (filter 2.7%)
  — Myth sub0 mixes UP-ramp and DOWN-ramp envelopes; one global shape is fundamentally wrong.
- `_filter_reset_frames(ftr)` (detect resets from the cutoff trace alone, threshold FILT_FAST=$40):
  over-detected 909 "resets" on Hawkeye sub2 (its normal ±8 hi/frame sweep == FILT_FAST) -> shattered
  spans -> Hawkeye 96.5%->31%. LESSON: do NOT derive resets from a trace-only threshold; use the
  note-on-aligned drives from detect_filter_drives. Both functions removed.
- Snapping the canonical capture to the reset frame + a `lead_hold` param: introduced/needed a phase
  fix but was superseded by capturing from the onset (phase-correct by construction).
The WINNING insight: shape is per-(instrument) for Hawkeye but per-(section) for Myth sub0 ->
the COMPOSITE (instrument, shape) key unifies both.

PART-COUNT (issue 2) — proven-dead trace-based approaches (do NOT retry):
- Semitone-arp from the TRACE (detect arps by matching per-frame freq to freqtable[note+S]):
  bundles 178->177 only. The variety is FREE-RUNNING PHASE not pitch; also the trace arps aren't
  100% clean (freq=0 onset spikes). Reverted.
- Lossy wave-program suffix-merge (ignore the leading-run count): cut instr 29->22 but dropped
  waveform fidelity 99.8%->90-95%. REJECTED (conflicts with accuracy-over-speed).
- Free-running per-voice streams FROM THE TRACE: 817 wave RLE rows/30s (cap 256), 741 FM rows/voice,
  62-97% semitone. Does NOT compress + not byte-exact. The trace is unrolled output.
CONCLUSION reached via these: only the STRUCTURAL (player-table) RE works. That is now in progress
(arp parser committed; FM wiring prototyped + reverted on the note-timing blocker).

FM WIRING (2d) — the note-timing blocker (NOT a dead end, just unfinished):
- First attempt used a per-note verify (compare arp expansion to frames[fr]) to fall back safely —
  but that comparison is against the raw trace at the PARSER's fr, which has the alignment offset,
  so it rejected correct arp programs. Dropped the per-note verify; validate the WHOLE build via
  mon_part_fidelity instead.
- fps=(dur>>4)+1 and the base-hold-lead + loop-to-entry-1 are CORRECT (frames 2-79 byte-exact).
  The residual is purely the parser note-duration vs original note-length mismatch (step 1 above).
</attempted_approaches>

<critical_context>
- KEY FILES:
  * `bin/build_mon_native_song.py` — the shared trace-driven native build. `build_native_song`
    (the pass-1 bundle/instrument extraction + count_only + clustering + pass-2 emission). The
    filter fix lives here (routed_voice, detect_filter_drives, _shape_sig, canon_filt composite
    key). Caps: 63 bundles ($c0-$ff), 32 instruments ($a0-$bf), 256 WAVE rows, 256 FILTER rows,
    120 sequences (128 real, 120 margin), $D000 mem wall. `emit_one` sets B.TEMPO=m.speed+1.
  * `bin/build_myth_native_song.py` — Myth's emulation-based build (py65 relocate+init+play/frame;
    MythShim feeds build_native_song via traces=). fpt=1 for Myth sub0 (row-count bound).
  * `sidm2/mon_parser.py` — the MoN parser. ol_mode variants: selfmod / stride / supremacy. NEW:
    `arp_program(wprog)` + tbl_arp_idx/tbl_arp_base in `_locate_supremacy`. Memory accessor is
    `_u8(addr)` (absolute SID addr -> byte). MONEvent has `.wprog` (the $60-$7F selector).
  * `drivers_src/mon/romuzak_driver.asm` — the native driver (a copy of the ROMUZAK/Galway engine).
    fm_step (accumulator: FM_ACC += offset/frame, freq = vfreq + FM_ACC), wave_step (col1 = RLE
    FRAME COUNT here, NOT the base engine's semitone col — ws_play hardcodes vfreq=freqtable
    [vbasenote]), pulse_step, filt_prog_step. pr_note (note trigger: sets vbasenote/vfreq, gate
    retrigger, restarts pulse/wave/FM/filter). VIFM/FMP (per-voice FM start / read ptr). vbasenote
    = $1841. freqtable = the song's own table (write_mon_freqtable).
  * `pyscript/test_mon_filter.py` (NEW, 7 tests), `pyscript/test_supremacy_parser.py` (added
    test_supremacy_arp_table).
- BUILD-SCRATCH REGENERATED every build (git checkout before committing!): `drivers_src/mon/
  {layout,freqtable}.inc`, `drivers_src/romuzak/layout.inc`. `bin/SIDFactoryII_dbg.exe` is a
  PRE-EXISTING modified binary — NEVER commit it. `whats-next.md` is tracked (this doc).
- COMMANDS:
  * Supremacy: `py -3 bin/build_mon_native_song.py SID/Tel_Jeroen/Supremacy.sid {0,1,2} auto|30|8`
  * Myth: `py -3 bin/build_myth_native_song.py {0,2} auto|30`
  * Fidelity vs siddump (part 1 aligns to song frame 0): `py -3 bin/mon_part_fidelity.py PART SUB
    SECS OFF0_SECS` — freq(semitone)/wf/pulse per voice + filter cutoff %.
  * count_only resource probe (fast, no assemble): call build_native_song(..., count_only=True)
    -> (bundles, instruments, wave-rows, filter-rows, sequences). See the inline scripts I ran.
  * Disasm: `py -3 bin/_mon_disasm.py START END SID/Tel_Jeroen/Supremacy.sid` (misaligns on illegal
    opcodes -> cross-check with an emulation write-PC probe).
  * Tests: `py -3 -m pytest pyscript/ -q` (~112s, 1459) or the mon subset (test_mon_parser,
    test_mon_to_sf2, test_supremacy_parser, test_mon_filter -> 18-ish, ~4s).
- SF2II CMP-CARRY caveat (any native-driver ASM): SF2II's 6510 computes CMP carry from bit7 of
  (A-op), only right for |A-op|<=$7f. Dispatch on values >$7f apart must use bit-tests (bmi/and),
  NOT cmp. (My fm_step `cmp #$7f` is safe only because A is already narrowed to $01-$7f there.)
- 6502 gotchas (from CLAUDE.md): `STY abs,x` invalid (use TYA/STA); long routines overflow
  bpl/bne range (use near-branch + jmp). Bash tool = Git Bash (heredocs OK; `@'...'@` FAILS —
  use `git commit -F -` with a heredoc).
- MEMORY (persistent): `myth-supremacy-mon-re.md` is the primary reference — it now contains the
  full filter fix, the size analysis, the proven-infeasible trace approaches, the arp + waveform
  engine RE, the FM-wiring prototype (exact driver+build changes to re-apply), and the note-timing
  blocker. Also: siddump-sbc-carry-bug.md, cybernoid-mon-orderlist-re.md, hawkeye-mon-*.md.
- USER PREFERENCE (memory feedback-accuracy-over-speed): accuracy/byte-exactness over speed/cost.
  Do NOT ship lossy output to reduce file count. This drove rejecting the lossy suffix-merge.
</critical_context>

<current_state>
- WORKING TREE CLEAN except `whats-next.md` (this doc). All exploratory part-count code (driver +
  build FM wiring, free-running experiments, scratch probes) REVERTED. Committed state = the arp
  parser + filter fix only, both byte-exact + tested.
- COMMITS (this session, on master; verify pushed via `git status`):
  * a10bdd0 — filter fix (Myth sub0 ~53%->~90%, Hawkeye sub3 56%->99%, no regressions, 7 tests)
  * 400d2e0 — Supremacy arp-table parser (byte-exact, tested)
- ISSUE 1 (Myth filter): DONE + committed.
- ISSUE 2 (part-count): NOT reduced yet — proven that ONLY a structural synth-engine RE can do it
  losslessly. Both engines RE'd; arp parser committed; FM wiring PROVEN VIABLE (bundles 178->127,
  arp byte-exact for a full note) but reverted, blocked on ONE bounded task: reconcile the parser's
  note durations with the original's note lengths (~9-frame drift). This is the immediate next step.
- ISSUE 3 (GUI/ear-confirm): open (needs the user).
- SCRATCH RE TOOLS kept (untracked, referenced in memory): `bin/_mon_disasm.py`. Deleted after use:
  _supr_synth_probe, _supr_wf_probe, _freerun_proof, _myth_filt_diag*, _supr_wave_*, _size_analysis,
  _semi_probe (all recreatable from memory notes).
- NO pending decision blocks progress; the next action is unambiguous (note-timing reconciliation,
  step 1 of work_remaining). The structural approach is de-risked — the hard conceptual work
  (proving trace can't compress + cracking both synth engines + demonstrating byte-exact arp) is
  DONE. Remaining is bounded implementation + validation, realistically a focused follow-up session.
</current_state>
