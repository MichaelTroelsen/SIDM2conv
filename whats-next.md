<original_task>
Standing mission (project): static RE + AI tools converting any SID into an SF2 at
99% fidelity + 100% editable. This session's explicit user tasks, chronological:
1. "read whats-next" -> resume at the Sound Monitor arc (work_remaining #1 of the
   previous handoff).
2. "yes, start on Sound Monitor" -> the full arc: format RE -> parser -> Stage A ->
   ("continue with stage B") -> Stage B native.
3. "yes commit. the push next phase" (commit cadence maintained throughout).
4. GUI listening loop: "can we hear any soundmonitor tunes in SF2 editor" / "load
   fuck_off into sf2" / "load poppy road into sf2" (multiple).
5. "final_luv and fuck_off are not 100% fidelity but close. please continue
   improving soundmonitor" -> the pulse-fix round.
6. "i have looked at songs. i think the speed in the editor is the reason why there
   is a need to split songs into more files. There is to much space between notes."
   + "if it were more compressed it would use less space?" -> the step-grid round.
7. "if this method works it could be used in other players." (grid generalization)
8. "the notes could be tigther. the bass sound is almost not audiable" -> coarse
   grid + THE HALF-LOUDNESS BUG hunt.
9. "It should 6581." / "the volume is just very low" / "The bass worked before.
   try again." -> root-caused to within-frame gate retriggers; "It sounds right
   now." = user confirmation.
10. "what is cause the number of files to larger than 1?" / "can you show the exact
    numbers for dance?" -> the per-cap analysis.
11. "try the wave-program canonicalization on Dance. This finding is very good. I
    think it sould be possible to build some kind of optimizer for this. In the old
    days (the original SID) did not have more thant 32 instruments, so the players
    back then must inclusde some fancy code the wave, filter and pulse. the
    instruments ADSR should be similar." + "THis applies for all players." -> the
    INSTRUMENT-CAP OPTIMIZER (designed, not yet built = the next arc).
12. Earlier user directive (2026-07-10): "after soundmonitor it is time for
    Gallefoss_Glenn look in SID folder" -> arc OPENED (recon done).
STANDING RULES: accuracy over speed; never ship lossy silently; archive-not-delete;
NEVER run pyscript/sf2_open_in_editor.py (launch SF2II via
`bin/SIDFactoryII.exe --skip-intro <abs path>`, workdir bin); ONE MoN-engine build
at a time; `git checkout -- drivers_src/mon/layout.inc drivers_src/mon/freqtable.inc
drivers_src/romuzak/layout.inc` after every native build.
</original_task>

<work_completed>
ALL COMMITTED + PUSHED (master == origin/master @ 75860b0). The commit chain tells
the story; every claim below is measured, not assumed.

SOUND MONITOR — COMPLETE ARC (v3.17.0 released mid-session):
- `sidm2/soundmonitor_parser.py`: full format decode of the 11-file Fun_Fun
  $C000/$C475 cluster (Hülsbeck "MUSICMASTER" driver; byte-identical player at a
  fixed load -> hardcoded table addresses, no relocation). ROW model with 8-bit
  wraparound (`row_start > row_count` is normal); per-row per-voice BAR ptr +
  NOTE-transpose + SOUND-transpose tables; (ctrl,data) step pairs; complete
  data-flag map ($0F instr / $10 GLIDE / $20 no-note-transpose / $40 ARP / $80
  no-sound-transpose); the CHORD-ARP BANK lives INSIDE the row-header record
  (8-byte semitone tables selected by the bar's LAST data byte); 24-byte sound
  records (byte0=WF, 1=AD, 2=SR, 4=PW nibble-swapped, 5/6=PWM up/down, 8=RELEASE
  WAVEFORM — gated release ($11/$81) keeps voices ringing through "rests", 9=fx
  flags, 12/13=vibrato). Onset-validated 99.9% corpus-wide.
- Stage A `bin/soundmonitor_to_sf2.py` -> editable Driver-11 SF2s (out/sm_sf2/),
  32/33 voices note-accurate (`bin/soundmonitor_sf2_validate.py`).
- Stage B `bin/build_soundmonitor_native_song.py` (SMShim -> shared MoN engine):
  onset-aligned, per-voice legato A/B, FM_CAP-40-gated TIE-SPLITS (native tie =
  the Supremacy-$FB freq re-seat), STEP-GRID mode with coarse auto-grid (largest
  multiple of speed+1 where all gates share one residue AND ties land within ±1;
  SM_GRID=0 kill-switch), sid_model=6581 declared. Output out/soundmonitor/.
- Tests: pyscript/test_soundmonitor_parser.py (9) + test_soundmonitor_to_sf2.py (3).
- docs/players/SOUNDMONITOR.md + players README/INDEX rows; docs/SF2.md refreshed
  (gen_sf2_index.py gained the soundmonitor folder).

THE FIDELITY-FIX ROUNDS (all driver changes crown-jewel-verified — Hawkeye sub2
rebuilt + measured 100.0x4 after EACH):
- PULSE_TIE driver flag: SM re-inits PW on EVERY note incl. legato; the MoN tie
  path skipped the pulse restart -> 17-second pulse freezes. Fuck_Off osc2 pulse
  57.6->96.3.
- PULSE_LOOP driver flag: the $7f+byte1 pulse LOOP path was compile-gated behind
  HARD_RESTART; non-HR builds read loop rows as FREEZE. Gate widened to
  `HARD_RESTART + PULSE_LOOP` (+ pl_loop re-blocked; layout.inc writer + B-flags).
- SEAMLESS LOOPS (PULSE_LOOP builds only): the loop row's 1-frame hold seam
  drifted SM's exact-period PWM +1 frame/lap; the loop now re-enters the row
  loader same-frame (ws_grd budget guard). Fuck_Off osc3 pulse 53->99.7.
- allow_loop gated to pdur>FM_CAP (unconditional loops REGRESSED fully-captured
  short notes: v0 pulse 100->58.9); offset-periodic detection with 3-frame
  boundary-bleed trim in pulse_program_for.
- Tie-split margin FM_CAP-40 (events stayed under the 256-frame capture).

THE HALF-LOUDNESS BUG (the session's biggest find, commit b503c77):
- User: "the bass sound is almost not audiable" -> "the volume is just very low"
  -> "The bass worked before" -> after fix: "It sounds right now."
- ROOT CAUSE: SM's note-set retriggers by writing gate OFF then ON inside ONE
  play call. End-of-frame register state stays 1 -> measure_onsets, siddump, and
  EVERY fidelity metric built on them were blind. We built those notes LEGATO:
  envelope attacked once, decayed to sustain, stayed quiet. VICE WAV RMS 1846 vs
  the original's 3683 (bass band -63%) while every register metric read 100%.
- HUNT TRAIL (reusable method): WAV RMS A/B (vsid_wrapper.export_to_wav) ->
  per-second RMS profile (uniform halving) -> band-split (bass -63%) -> bass-note
  amplitude envelope (ours dies in 30ms, orig rings 500ms) -> CPU WRITE-STREAM
  dump at an onset frame (orig writes wf $40 then $41 + AD/SR in one frame).
- FIX: `measure_onsets(within_frame=True)` in sidm2/dmc_parser.py — gate-rise
  detection in the WRITE STREAM (per-voice, first rise per frame); SM builder
  passes True; the state-based default is unchanged (DMC unaffected).
- BONUS: the fix REDUCED parts (properly retriggered notes make short, repeating,
  dedupable capture programs): Dreamix 9->5, Dance 13->11, Poppy_Road ->1.
- Also fixed en route: scripts/sf2_to_sid.py PSIDHeader flags now follow the PSID
  v2 spec (model in bits 4-5; the old bits-0-1 layout left every wrapped probe's
  SID model UNKNOWN -> VICE rendered probes on its default chip).

FINAL SM CORPUS (uniform rebuild, all fixes): **11 songs / 32 parts** (52 at the
round's start): Final_Luv/Poppy_Road/No_Title/Just_Cant_Get_Enough=1, Times_Up/
Fun_Mix/Fuck_Off=2, Thats_All/Dreamix_Two=3, Dreamix=5, Dance=11. Loudness
verified on Poppy_Road (RMS 3323 vs orig 3683) + Final_Luv (2704 vs 2998).
Fidelity (delay-aware strict from first audible frame): Poppy 100/100/100 x2 +
100/100/96; earlier sweep had Fun_Mix/Times_Up/JCGE/Fuck_Off byte-perfect —
NOTE: that sweep predates the retrigger rebuild; a final corpus-wide sweep after
b503c77 was NOT run (only Poppy + spot RMS checks).

THE DANCE CAP ANALYSIS (user asked "exact numbers"):
- Per-part cap usage measured via count_only: Dance's binder = the 32-INSTRUMENT
  cap (6/11 parts at 30-32/32) + the FILTER table (253/256 rows on parts 8-11).
  Bundles peak 56/63 and never bind. (Corrects the earlier "bundles dominate"
  assumption for this file.)
- Diagnostic (part-1 window): 9 real SM instruments -> 37 captured wave programs;
  decomposes into exactly 3 capture-artifact classes: (1) first-byte boundary
  bleed ([65,..] vs [64,65,..] vs [128,65,..]), (2) duration-positioned release
  tails (rec[8] wf at note-length-dependent offsets), (3) hold-length variants.
- TRIED: MON_ARP_STRUCT=1 on Dance — still 11 parts (guards reject SM shapes:
  _gate_split needs dur<=WAVE_CAP=96, SM notes run longer; release wf $11 on a
  $41 note inexpressible via the &$fe gate mask; first-byte bleed unhandled).

GALLEFOSS/SDI ARC OPENED (user priority after SM):
- memory/gallefoss-sdi-player.md: 442-file corpus recon (largest yet); clusters
  init+0/play+3 (222 files) + init+0/play+4 (114) + ~15 small (digi/self-IRQ/
  GRG_tiny); sidid identifies only 6/441. FULL ground truth staged in
  bin/SIDDuzz/: **SDI-21-BMTass.d64 = the SDI 2.1 ASSEMBLER SOURCE** (GRG
  co-wrote SDI: "Written by Geir Tjelta and Glenn Rune Gallefoss"), the editor
  d64, 65KB docs, note tables, manual PDF.

Memories updated: soundmonitor-player.md (phases 1-9 + the optimizer design +
final corpus), MEMORY.md index, new-player-priority.md, gallefoss-sdi-player.md
(new). Scratch (untracked): bin/_sm_disasm.py, bin/_sm_build_all.py,
bin/_sm_measure_direct.py, bin/_grg_classify.py.
</work_completed>

<work_remaining>
1. **THE INSTRUMENT-CAP OPTIMIZER (user directive; cross-player; START HERE).**
   Design in memory/soundmonitor-player.md ("THE INSTRUMENT-CAP OPTIMIZER"
   section). Steps:
   a. Shim-gated + guarded (like pulse_canon) transforms in
      bin/build_mon_native_song.py:
      - first-row normalization of wave programs (guard: unroll-equal from
        frame 1) — merges the [65..]/[64,65..]/[128,65..] boundary-bleed class;
      - tail-aware canonical acceptance (programs equal after removing each's
        duration-positioned release-tail run);
      - a per-instrument RELEASE-WF driver feature (1-byte instrument field =
        SM rec[8]; gate-off rows write it instead of program&$fe) — makes the
        tails expressible and kills class 2 entirely;
      - the same treatment for FILTER programs (Dance parts 8-11 at 253/256).
   b. Measure ladder per change: Dance parts + per-part caps (count_only), the
      delay-aware strict sweep, WAV RMS A/B, crown jewel (Hawkeye sub2 100.0x4),
      and a Hubbard/DMC spot part (engine is shared!).
   c. Cross-player audit with the same diagnostic (9-instruments-vs-37-programs
      script pattern is in the session log; reconstruct from the memory notes):
      MoN, Hubbard, DMC instrument counts vs real instrument counts.
2. **Final corpus-wide fidelity sweep post-b503c77** (only Poppy was fully
   re-measured after the retrigger rebuild): run the delay-aware strict sweep
   (pattern in bin/_sm_measure_direct.py + best-delay search) + WAV RMS for all
   11; update memory numbers. Expect improvements (retriggers also fixed
   envelope-adjacent captures).
3. **Within-frame retrigger audit for DMC** (the same blindness likely affects
   some of its 88 files): compare measure_onsets(False) vs (True) onset counts
   per file; where they differ materially, rebuild + A/B (state-based default
   was ear-validated, so change only with measurements).
4. **Gallefoss/SDI arc** (memory/gallefoss-sdi-player.md has the full plan):
   extract the BMTass source from bin/SIDDuzz/SDI-21-BMTass.d64 (need a d64
   reader — check bin/DMC tooling for one), map the play+3 cluster's tables from
   the player's own source, then parser -> Stage A -> Stage B. Mind version
   drift (2013 source vs 1992 rips). Apply the step-grid from day one; grid ×
   tie interaction caveat applies.
5. Smaller SM residuals (documented in memory): Dance's noise-drum section
   (~280 frames, octave-off drum-capture phase class); Dreamix_Two v1
   release-tail slides (orig slides pitch DURING gate-off decay; a new residual
   class — the release-wf/optimizer work may enable fixing it); grid × tie-chain
   interaction (Final_Luv/Thats_All forced SM_GRID=0 — root cause undiagnosed);
   Demo_of_the_Year_87_menu $C020 variant; sound-record bytes 7/14/15 + the
   16-23 extension block (the editor binary bin/'sound monitor'/soundmonitor
   1.1.prg is the ground-truth shortcut).
6. Version bump when the optimizer lands (v3.18.0): CLAUDE.md + CHANGELOG +
   STORY.md + sidm2/__init__.py; gen_sf2_index refresh; artifact republish
   (same URL ef593833-e303-4745-88e5-23190f4eef5b).
</work_remaining>

<attempted_approaches>
DO NOT RE-TREAD:
- Chasing SOUNDMONITOR_CNV inside the ROMUZAK editor dump: the menu text is
  walked positionally, no code pointer findable — disassembling the SM player
  directly was faster.
- The credit string as SM detection: Final_Luv's rip is truncated at exactly
  $CBD4 where "MUSICMASTER CREATED BY CHRIS HUELSBECK" starts. Use the
  play-routine byte signature.
- Emitting $90-$9F tie duration bytes to RUNTIME Driver 11: editor-only feature
  (datasource_sequence.cpp) — desyncs the driver into garbage (locked by a
  regression test in test_soundmonitor_to_sf2.py).
- Header byte4 as a next-row chain: row order is LINEAR with 8-bit wraparound;
  byte4 = volume-fade speed.
- Unconditional pulse loops (allow_loop for short notes): the loop seam
  regressed fully-captured notes (v0 100->58.9). Loops only when pdur>FM_CAP.
- MoN pulse_canon semantics for SM ties pre-PULSE_TIE: ties froze the previous
  program (the 17s freeze).
- 8580 SF2 flag "to fix the bass": user rejected (correct chip = 6581) AND it
  wasn't the cause anyway.
- $D418/$D417/ADSR-value theories for the low volume: registers were all equal;
  the $1F-vs-$0F LP bit gave only 1846->2070. The real cause was the envelope
  history (within-frame retriggers).
- naive delay-0 strict sweeps on grid builds: a constant 1-frame lead reads as
  a 33-62% collapse. Check gate-rise DELTAS first; use best-delay search.
- mon_part_fidelity pulse numbers: its per-voice delay is freq-tuned and
  misreports per-frame-changing pulse (a byte-identical region scored 24%).
  Always cross-check with a direct fixed-delay compare.
- MON_ARP_STRUCT=1 as the Dance instrument-collapse: no effect (guards reject
  SM shapes; see work_remaining 1a for what's actually needed).
- The step grid on tie-chain-heavy files (Final_Luv pulse 100->8, Thats_All
  95-100->79-95): SM_GRID=0 for those two; root cause of the grid × tie-restart
  interaction NOT yet found.
- 12-frame coarse grid for Poppy: vetoed by the tie-±1 rule automatically —
  the auto-grid picked 6; the veto logic is correct, don't loosen it blindly.
</attempted_approaches>

<critical_context>
- ENV: Windows, `py -3`; PowerShell + Git Bash tools. /tmp in Bash =
  C:\Users\mit\AppData\Local\Temp (Windows Python can't open '/tmp/...' paths!).
  Long jobs: run_in_background Bash; ONE MoN-ENGINE BUILD AT A TIME (shared
  drivers_src scratch); after ANY native build: `git checkout --
  drivers_src/mon/layout.inc drivers_src/mon/freqtable.inc
  drivers_src/romuzak/layout.inc` (and bin/SIDFactoryII_dbg.exe gets touched by
  sf2ii_vs_real — checkout too).
- SID REGISTER MAP (was misread twice this session — voice bases are 7 apart):
  voice1 $D400-06 (flo,fhi,pwlo,pwhi,wf,AD,SR), voice2 $D407-0D, voice3
  $D40E-14; $D415/16 cutoff, $D417 res/route, $D418 mode/vol.
- MEASURING LADDER (the session's methodology yield): per-frame register
  metrics CANNOT see within-frame gate retriggers OR envelope state. The full
  ladder: (1) register sweeps (best-delay, from first audible frame), (2)
  sf2ii_vs_real (bin/, instrumented SF2II = what SF2II REALLY plays; opens a
  brief GUI window), (3) WAV RMS A/B via sidm2.vsid_wrapper.export_to_wav
  (VICE; needs correct PSID model flags — now fixed), (4) CPU WRITE-STREAM
  dumps (sidm2.cpu6502_emulator, cpu.sid_writes per frame) for within-frame
  truth, (5) the user's ear (beat 3 layers of instrumentation TWICE).
- SM driver flags on SMShim: freerun_pulse=1 (allow_loop + tie-chain capture
  spans), pulse_loop=1 (compiles the $7f loop path), pulse_tie=1 (ties re-init
  PW), sid_model=6581, hp_engine=0, hard_restart=0, snap_gate=True. Grid: auto
  (mults 4/2/1 of speed+1; gates one-residue + ties ±1; SM_GRID=0 disables).
- Driver asm (drivers_src/mon/romuzak_driver.asm) new conditionals:
  `.if HARD_RESTART + PULSE_LOOP` (loop path + pl_loop), `.if PULSE_LOOP`
  (seamless re-enter, ws_grd budget=4), `.if PULSE_TIE` (tie pulse restart in
  pn_tied). PULSE_LOOP=0 + PULSE_TIE=0 compiles byte-identically to before —
  Hubbard/MoN unaffected (verified via Hawkeye rebuilds).
- The engine's per-frame pulse write order: pulse_step runs AFTER do_row (same
  frame note resets); the loop seam applies only in non-seamless (HR) builds.
- fits()/caps: CAP_B=63 bundles, CAP_I=32 instruments (instr_of key = (MoN
  instr, wave program, flags, filter)), wave/filter tables 256 rows, CAP_SEG
  =120, seq event limit 960 (SF2II's 1024 Unpack buffer). The adaptive splitter
  grows windows until a cap would burst.
- Wave programs = per-frame wf-byte tuples, settle-trimmed (_wave_prog_for);
  canonical acceptance via _wave_masked_ok/_wave_unroll_eq; _gate_split is
  ARP_STRUCT-gated and requires dur<=WAVE_CAP=96.
- The user's editor-density preference: notes should sit close (the step grid
  = 1 musical step/row; Poppy auto-picked fpt=6 = 2 steps/row).
- SM corpus fidelity classification: strict-vs-skew (±1 frame = audibly exact,
  the accepted Supremacy class); intros/idle registers differ inaudibly (both
  silent); the honest strict numbers live in memory phase 8-9 notes.
- Artifact: docs/SF2.md mirrors to claude.ai artifact
  ef593833-e303-4745-88e5-23190f4eef5b (republish by re-publishing the same
  file path).
- v3.17.0 was released THIS session (CLAUDE.md/CHANGELOG/STORY.md updated);
  the post-release fixes (loudness, grid, 32-part corpus) are committed but NOT
  yet version-bumped — fold into v3.18.0 with the optimizer.
</critical_context>

<current_state>
- Repo: master == origin/master @ 75860b0, working tree CLEAN (only intentional
  untracked: SID/Gallefoss_Glenn, bin/LFT, bin/SIDDuzz, bin/'sound monitor',
  archive/cleanup_2026-07-09, out/ artifacts, bin/_*.py scratch). Version
  constant 3.17.0.
- Tests: full suite was 1524 green at v3.17.0; player-subset tests green after
  every later change; a FULL suite run after b503c77/75860b0 has NOT been done
  (only subsets) — run `py -3 -m pytest pyscript/ -q` before the next release.
- SM corpus: out/soundmonitor/ = 11 songs / 32 parts, ALL built with every fix
  (retriggers, pulse fixes, grids; Final_Luv+Thats_All via SM_GRID=0). Loudness
  verified on Poppy_Road + Final_Luv; corpus-wide post-retrigger fidelity sweep
  pending (work_remaining 2).
- Stage A corpus: out/sm_sf2/ (11 editable Driver-11 SF2s) — predates the
  session's Stage-B fixes but Stage A is unaffected by them.
- The user last confirmed by ear: Poppy_Road "sounds right now" (post-retrigger).
  SF2II windows may still be open on their desktop.
- NEXT SESSION STARTS ON: the instrument-cap optimizer (work_remaining 1) —
  design complete in memory/soundmonitor-player.md; Dance is the testbed
  (9 instruments -> 37 wave programs measured); OR the Gallefoss/SDI arc
  (work_remaining 4) if the user prefers the new player first. Ask.
- No temporary changes or workarounds in place; drivers_src scratch clean.
</current_state>
