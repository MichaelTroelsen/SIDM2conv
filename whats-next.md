<original_task>
The session began with: "I want you to reconsolidate your knowledge... update ALL docs and
combine all knowledge and make suggestions to improvements to optimize size and fidelity and
tools. We need this before we take on more players. The dream and mission statement is to
create tools that combine static code combined with AI to convert any SID into a SF2 99%
fidelity play and 100% editable."

That consolidation was completed and shipped as v3.13.1; the user then said "start on the
roadmap - fidelity lib first" and afterwards repeatedly "go on" / "continue" through the
roadmap's MoN structural-rebuild items. The bulk of the session became the Jeroen Tel /
Maniacs-of-Noise (MoN) Supremacy structural work (SID/Tel_Jeroen/Supremacy.sid), executing
and far exceeding the old whats-next plan (note-timing -> FM arps -> wave -> pulse ->
slides -> song-length discovery).
</original_task>

<work_completed>
ALL COMMITTED AND PUSHED to master (MichaelTroelsen/SIDM2conv). Commit chain this session:

1. 68e569d (v3.13.1 docs consolidation): NEW docs/players/PLAYBOOK.md (the cross-player
   porting method: staged RE->StageA->StageB->StageC pipeline, technique catalog, SF2II
   caps, fidelity ladder, gotchas, new-player checklist), NEW docs/players/MON.md +
   CLUSTERS.md, rewritten docs/reference/ACCURACY_MATRIX.md (v3.1.1->v3.13), rewritten
   docs/ROADMAP.md (prioritized optimization plan), README.md/docs/INDEX.md/CLAUDE.md
   refreshed, version bumped (sidm2/__init__.py 3.13.1), CHANGELOG/STORY updated.

2. 647fddf (roadmap A3): NEW sidm2/fidelity_common.py — shared validator plumbing:
   freq_to_semi (canonical SEMI_REF=0x1167), psid_wrap, siddump_per_frame/
   siddump_note_onsets/siddump_filter_trace/iter_siddump_rows, fill_forward/zig64_voices/
   zig64_trace_voices, best_gated_offset. Refactored 8 consumers (mon_fidelity,
   mon_sf2_validate, mon_validate, romuzak_validate, romuzak_native_validate, fc_validate,
   build_mon_native_song.filter_trace, sf2ii_vs_real.rser). VERIFIED: all validator outputs
   byte-identical to pre-refactor baselines (out/_a3_baseline/ vs out/_a3_after/).
   NEW pyscript/test_fidelity_common.py (13 tests).

3. bcfd165 + 9fa4260 (MoN note-timing step 1): Supremacy speed byte bit7 = SWING tempo
   (tick periods alternate speed,speed+1 — RE'd from the $1128-$114D gate toggle of $E2);
   MON.tick_to_frame/frame_to_tick/tempo_toggle/onset_delay(=2 supremacy); native driver
   swing reload (SWTOG=$185f toggle in do_row, TEMPO2 in layout.inc via
   build_romuzak_native_song's writer + emit_one); build_mon_native_song frame accumulation
   made tick-exact; PREFIX-CHAIN RETRIGGER decode (a $Cx/dur/wave byte followed by another
   prefix finalizes = retriggers the previous note); _fm_curve cluster distance extended to
   full freeze-extended programs (a 24-frame-prefix compare had let a forced merge freeze a
   voice at freq 0 for 20 frames). mon_part_fidelity gained a small constant-offset search.

4. e67f491 (structural arps, MON_ARP_STRUCT=1): driver fm_step entry dispatch on byte2
   ($00 freeze | $01-$7e Hz run, emitter splits RLE at 126 | $7f LOOP: FMP=VIFM+byte0*3,
   ws_grd guard | $80-$ff SEMITONE: dur=byte2&$7f, FM_ACC=freqtable[(vbasenote+S)&$7f]-vfreq).
   arp_fm_program PHASE-ALIGNED (step0 gets fps-1 frames because pr_note's base hold covers
   frame 0; rotation step1..stepN,step0; loop to rotation start). _is_struct_fm cluster
   exemption. NEW pyscript/test_mon_arp_struct.py.

5. 00ac20a (wave/pulse/FM canonicalization): the unifying insight — all per-note captures
   carry DURATION-RELATIVE boundary tails. _gate_split (terminal gate-off -> sequence
   note-$00 rows; VGMASK=$fe masks the looping steady into the $40 tail; tolerates the
   1-frame wf-leads-freq register skew + 1-2 bleed frames); canonical longest-note
   wave/pulse/FM per (instr,wprog) with exact unrolled guards (_wave_masked_ok,
   _pulse_unroll, _fm_unroll). NEW pyscript/test_mon_wave_struct.py.

6. 6fc06f6 (free-running pulse + scaled vibrato): driver VIFLAGS $08 + PFREE latch
   (pr_note keeps PPTR/VPC after the first flagged note) + per-voice stream emission;
   EMITTER BUG FIXED: gen_includes_song's instrument-flags if/elif DROPPED all bits except
   its own — now ORs instr_flags & $48. SCALED VIBRATO entries: hi=$40/$41 Hz entries ->
   offset = +-(VSTEP*byte0)>>8 via 24-bit shift-add mul (out-of-line past fm_done);
   VSTEP = freqtable[n+1]-freqtable[n] set at pr_note; _vibrato_program + exact guards.

7. 3cf1cf9 (THE EVENT TRACER + complete pattern decode): NEW bin/mon_event_trace.py —
   py65 logs sequencer state at $1203 (orderlist select), $12C1 (event finalize), $1343
   (epilogue): frame/voice/Y/$E3/$E6/$E9/$F0/$F3/$F6/$1026/$1064/$102F/$1032/$1007/$100D/
   $1016/$10DB. It answered EVERY decode question: pattern reader enters at $1212
   (top-level $FA = 2-byte cmd -> $10DB; $FD = 4-byte SLIDE); $FD after instr/dur prefixes
   = the same slide (speed->$102F, note->$F0, target->$1032, gated trigger); remaining
   top-level $E0+ = REST (b&$1F ticks, $F0=$FF, updates sticky dur); retrigger peeks
   INCLUDE $FF/$FE (`A4 FF` = a 36-tick gated hold; only TOP-LEVEL $FF ends a pattern);
   durations are ADDITIVE into $F3 until finalize (`A0 A0` = 64 ticks). MONEvent gained
   rest/slide fields; build emits rests as note-$00 rows. Supremacy sub2 = 962/962 onsets
   EXACT over 120s. The old sub0 test constant had a phantom pitch (freq-lookup fires on
   non-trigger lookups) — recaptured from the event tracer.

8. 312e2b9: free-running-pulse hypothesis REVERSED — with correct note boundaries the
   pulse RESETS per note (the "phase drift" had sampled at wrong onsets); detection now
   correctly never fires (PFREE feature dormant); stream bundles merge-protected anyway.

9. 2e973ee (driver SLIDE entry + first sub1 native build): rate = 7 << (speed-1) Hz/frame
   (trace-calibrated: sp5=112, sp6=224), ramps from frame 1, driver clamps at
   FM_TGT ($1870+ state) on sign-flip/arrival — pitch-independent (the clamp frame varies
   per pitch). SEMITONE entries dispatch on byte1 (0=instant arp, 1-31=slide speed).
   _slide_fm_program (+ spliced tail vibrato), _fm_unroll_full (universal all-entry-type
   guard model), _slide candidates exact-guarded. ARP GUARD added at the SEMITONE level
   (freq_to_semi): unguarded arps broke sub1 osc1 to 32% (wprog $14 = a WAVE shape, not a
   pitch arp); Hz-exact guarding rejected all DETUNED canon notes (bimodal bad=0/bad=all).
   Driver code relocated: out-of-line FM handlers at `* = $1880` (main bank overflowed the
   pinned state region $16CC-$1702); 64tass is CASE-INSENSITIVE (fm_slide label collided
   with the FM_SLIDE symbol).

10. 1e3303b: per-program mul rounding (scaled marker bit1 = TRUNCATE, $40-$43; the ROM's
    depth rule is neither pure trunc nor round — guards arbitrate per note); loop-aware
    mon_validate scaffolding (vpass).

11. 924b498 (THE BIG ONE): **orderlist byte $00 = GLOBAL SONG LOOP** (py65 write-watch on
    $E9-$EB: all three voices reset together at $11CF-$11D6 STY $E9/$EA/$EB when an
    orderlist step STARTS with $00, checked at $11CD). Pattern 0 never existed. Parser:
    _ol_loop_ticks marks -> song_loop_ticks = min across voices -> _clip_to_song_loop
    re-decode. REAL LENGTHS: sub1 = 38s (was 374s overrun), sub2 = 150s (was 490s).

12. b8df39a: the sub2 single-part "defect" was a MEASUREMENT ARTIFACT — mon_part_fidelity's
    OFF0 shifts only the ORIGINAL; whole-song parts need OFF0=0 + full SECS. Measured
    correctly over 150s: osc1 86.5/86.5/93.6, osc2 97.6/95.5/97.9, osc3 92.8/97.8/93.4,
    filter 100. The fr79 "phantom onset" = the wave program's trailing bleed row regating
    1 frame (byte-correct to keep).

13. d604e5b: **$FE = GLOBAL song HALT** ($11DD -> $117B zeroes freqs + gates play off) —
    song ends at the FIRST voice's $FE; sub0's real length = 234s (V2's $FE; V0's own is at
    698s = the old overrun). Also measured-and-rejected: trimming the wave bleed (osc3 wf
    97.8 -> 91.6 — reproducing the bleed is byte-correct).

SUPREMACY END STATE (2026-07-05): sub0 = 10 adaptive parts (234s, part1 92-95 freq /
88-90 wf / 95-99 pulse / filter 100), sub1 = 1 part (38s, 95.1-97.7 freq), sub2 = 1 part
(150s, 86.5-97.6 freq, filter 100, 13 instruments / 18 bundles). From 34 / never-built /
70 parts at session start. Onset decode EXACT: sub2 962/962 @120s (1230/1230 @150s), sub1
136/136 @60s (loop-aware), sub0 V0 137/137 (V1/V2 = constant 1-frame engine jitter from
idx 74). Hawkeye sub3+sub2 stayed 100/100/100 byte-exact throughout (verified repeatedly);
Cybernoid sub0 regression clean (99.9/99/96 + 100/100). Full suite: 1490 passed.

Memory files updated throughout: memory/myth-supremacy-mon-re.md (the primary MoN log,
extensively appended per commit), memory/docs-consolidation-2026-07.md (new), MEMORY.md
(compacted to grouped one-liners).
</work_completed>

<work_remaining>
All small/optional; the structural rebuild is essentially complete for Supremacy.

1. **GUI/ear-confirm the new single-file builds** (NEEDS THE USER): load
   out/mon/Supremacy_sub2_part01.sf2 (whole 150s song), Supremacy_sub1_part01.sf2 (38s),
   and a couple of sub0 parts in real SF2II via
   `py -3 pyscript/sf2_open_in_editor.py out/mon/<file>.sf2 40` (argv Heisenbug retries;
   native play=$1003). Rebuild first if out/ is stale:
   `MON_ARP_STRUCT=1 py -3 bin/build_mon_native_song.py SID/Tel_Jeroen/Supremacy.sid {0,1,2} auto`.

2. **3007-vs-3008 rows clip off-by-one** (cosmetic, ~2.5 frames at song end): sub2's
   per-voice emitted rows total 3007 while song_loop_ticks=3008 — check
   _clip_to_song_loop / the window clip in build_native_song's pass loop.

3. **sub0 V1/V2 constant 1-frame onset jitter from onset idx 74** (cosmetic — engine
   output jitter after the long dur-64 hold; native builds self-align via the trace).

4. **Apply today's decode rules to the OTHER MoN tunes**: Hawkeye sub0 (13x30s windowed —
   re-run with the current build; the caps may now fit far fewer parts), Myth sub0 filter
   part1 (77%), Cybernoid part counts. The $00/$FE global markers are supremacy-branch
   only — check whether the Hawkeye-family orderlists ($FE=song-end already handled there)
   need the same global-cut treatment for multi-voice overruns.

5. **Cross-tune regression command set** (run after any MoN change):
   - `py -3 bin/mon_validate.py SID/Tel_Jeroen/Supremacy.sid {0,1,2} {60,60,120}`
   - `py -3 bin/build_mon_native_song.py SID/Tel_Jeroen/Hawkeye.sid 3 auto` +
     `py -3 bin/mon_part_fidelity.py out/mon/Hawkeye_sub3_part01.sf2 3 2 0` (expect 100/100/100)
   - full: `py -3 -m pytest pyscript/ -q` (1490)

6. **Roadmap (docs/ROADMAP.md) continuation beyond MoN**: A1 native-driver unification
   (one asm + 64tass -D flags; drivers_src/mon has diverged FURTHER this session — swing,
   SWTOG/PFREE/VSTEP/FM_TGT state, scaled/slide entries, $1880 out-of-line bank — fold
   these in as MoN feature flags when unifying), A2 shared native-build lib, A4 registry
   wiring, D1 universal trace-first fallback, FC Stage B, Hubbard.
</work_remaining>

<attempted_approaches>
DEAD ENDS / MEASURED-AND-REJECTED (do not retry):
- ORDERLIST FALL-THROUGH CHAIN implemented verbatim from the $11DF disasm: BROKE sub0's
  validated note order while fixing nothing (reverted). The committed independent-dispatch
  model is what all validation rests on. The chain is real in the ROM but its re-entry
  semantics differ from a naive per-step chain; only revisit with tracer olsel evidence.
- TOP-LEVEL $FA/$FD as rest/2-byte-skip variants (multiple wrong combinations tried before
  the tracer): the reader enters at $1212 — $FA/$FD are top-level commands AND prefix
  suffixes; everything else $E0+ is a rest. Only the tracer settled it.
- Hz-EXACT arp guard: rejected every detuned canon note (bimodal bad=0 or bad=all — a
  constant few-Hz detune differs at every frame but is semitone-invisible). Use the
  SEMITONE-level guard (freq_to_semi), threshold max(4, dur_f//8) bad frames.
- UNGUARDED arps: sub1 osc1 32% freq (wprog $14 is a wave shape, not a pitch arp).
- WAVE-BLEED TRIM (dropping the trailing next-note attack rows from unsplit wave
  programs): osc3 wf 97.8 -> 91.6. Reproducing the bleed is byte-correct; the phantom
  onsets it causes are an onset-metric artifact only.
- FREE-RUNNING PULSE hypothesis: an artifact of wrong note boundaries; with the correct
  decode every (instr,wprog) key has ONE set-row start. The driver PFREE/$08 feature and
  stream machinery remain but are dormant.
- Chasing the sub2 "40s+ collapse": it was mon_part_fidelity's OFF0 semantics (shifts only
  the original). ALWAYS measure whole-song parts with OFF0=0.
- A single mul rounding rule: ROM depths need round for some (47@step362), trunc for
  others — hence the per-program bit1 flag; sub2's auto count stayed 31 pre-$00-discovery
  because the old 26 had included lossy unguarded arps (moot now — sub2 = 1 part).
- FM prototype with byte2 run counts up to 255: the new $7f/$80+ entry space requires the
  emitter to split Hz RLE runs at 126 (done) — old programs with 127+ runs would misparse.
</attempted_approaches>

<critical_context>
- FLAG: the structural path = MON_ARP_STRUCT=1 (env). Flag-off = the plain trace path
  (byte-identical to pre-session behavior; Hawkeye's 100/100/100 lives there). Every
  structural substitution (arp/slide/vibrato/canonical wave+pulse) is exact- or
  semitone-guarded per note with trace fallback.
- SUPREMACY ENGINE FACTS (all py65-tracer-proven): swing tempo (speed byte bit7; periods
  alternate speed,speed+1, SHORT first after tick 0); onset_delay = 2 frames (output phase
  runs before the sequencer); $D404 writes lead freq writes by ~1 frame (per-register skew
  -> gate-split tolerates 1, capture tails hold 1-2 bleed frames); durations ADD into $F3
  until event finalize; sticky duration = $F6; REST = top-level $E0+ (dur = b&$1F, also
  sets sticky); $FD = 4-byte slide (speed/$102F, note/$F0, target/$1032, %12C1 gated
  trigger; slide rate = 7<<(speed-1) Hz/frame from frame 1, clamps at target; speed-26
  down-jumps land ~frame 4 and are NOT modeled — guard keeps them trace-Hz); vibrato =
  pitch-proportional (depth = (step*scale ±rounding)>>8, scale ~30-34, centered half first
  leg); $00 orderlist step = GLOBAL loop; $FE = GLOBAL halt; orderlists overlap/share
  tails across voices (sub1 V1 = V0+4).
- DRIVER (drivers_src/mon/romuzak_driver.asm) state added this session: SWTOG $185f,
  PFREE $1860(3), VSTEP $1863/1866(3+3), mul scratch $1869-$186f, FM_TGT $1870/1873(3+3),
  FM_SLIDE $1876(3). Out-of-line FM handlers (scaled mul + slide setup) live at
  `* = $1880` (free window $1880-$19FF between driver scratch and EDIT_BASE $1A00) because
  the main bank overflowed SF2II's pinned state region ($16CC-$1702). FM entry encoding:
  byte2 = $00 freeze / $01-$7e Hz run / $7f loop (byte0 = entry index) / $80|dur semitone
  family, where byte1 = 0 instant, 1-31 slide speed; Hz entries with byte1(hi) = $40-$43
  = scaled vibrato (bit0 sign, bit1 truncate). 64tass gotchas: CASE-INSENSITIVE labels
  (fm_slide vs FM_SLIDE!), branch ranges (near-branch + jmp), `* =` org sections fine.
- BUILD (bin/build_mon_native_song.py): _fm_unroll_full = the universal driver model
  (use it for any new entry type); _gate_split/_wave_masked_ok/_pulse_unroll/_settle_trim;
  canonical per (instr,wprog) from canon_pick (longest note, whole clipped song);
  bundles/instr protected from bad merges (_is_struct_fm, stream_set, full-length curves).
  blk tuples = (note_c|None, ticks, bi, ii, tk, gate_ticks); note None = rest rows.
- MEASUREMENT TOOLS + TRAPS: bin/mon_event_trace.py = THE decode ground truth (extend it
  for any new question — log more state at more PCs); event-tracer 'note' kind = real
  gated triggers (the freq-lookup trace fires on non-trigger lookups — one phantom pitch
  was in the old sub0 test constant); mon_part_fidelity: windowed parts use OFF0 = window
  start seconds; WHOLE-SONG parts MUST use OFF0=0 + full SECS; adaptive part filenames do
  NOT encode their window offsets — read them from the build stdout ("part 2/26 (38-72s)").
- BUILD-SCRATCH: drivers_src/mon/{layout,freqtable}.inc + drivers_src/romuzak/layout.inc
  regenerated every build — `git checkout --` them before committing. Never commit
  bin/SIDFactoryII_dbg.exe. Bash tool = Git Bash (heredocs OK).
- SF2II CMP-carry rule for any driver asm: never `cmp` values >$7f apart (bit-test first);
  my dispatchs use bmi/eor/and patterns.
- USER STANDING RULE: accuracy/byte-exactness over speed/cost/file count; never ship lossy
  silently (every lossy trade this session is flag-gated + documented + measured).
- Older shipped context this session: v3.13.1 docs (docs/players/PLAYBOOK.md is the
  cross-player method reference), sidm2/fidelity_common.py (use freq_to_semi etc. for any
  new validator), docs/ROADMAP.md = the plan beyond MoN.
</critical_context>

<current_state>
- Working tree CLEAN except whats-next.md (this file). Everything committed AND pushed
  through d604e5b on master. Tests: 1490 passed, 7 skipped, 2 xfailed.
- out/mon/ artifacts may be stale relative to HEAD for some tunes — rebuild before
  measuring or GUI-testing (commands in work_remaining #1/#5).
- Supremacy: DONE to the structural-rebuild standard (sub0 10 parts / sub1 1 part /
  sub2 1 part, all validated headless; NOT yet ear/GUI-confirmed by the user).
- Hawkeye/Cybernoid/Myth: untouched by regressions (verified), not yet rebuilt to exploit
  the new machinery (work_remaining #4).
- No blockers. The natural next actions are: user ear-check of the single-file builds,
  then either propagating the machinery to Hawkeye sub0/Myth, or returning to
  docs/ROADMAP.md items A1/A2 (driver unification — now with this session's driver
  features to fold in) and D1 (universal trace-first fallback).
</current_state>
