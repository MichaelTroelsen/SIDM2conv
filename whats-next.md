<original_task>
Standing mission (project): static RE + AI tools converting any SID into an SF2 at
99% fidelity + 100% editable. This session (2026-07-11), chronological:
1. "read whats-next" -> resumed the previous handoff; user chose (AskUserQuestion)
   to START ON THE INSTRUMENT-CAP OPTIMIZER (over Gallefoss/SDI or the sweep).
2. "cont" mid-session (continue) — the only other user input; the whole arc ran
   autonomously per the handoff's design (memory/soundmonitor-player.md "THE
   INSTRUMENT-CAP OPTIMIZER" section).
STANDING RULES: accuracy over speed; never ship lossy silently; archive-not-delete;
NEVER run pyscript/sf2_open_in_editor.py (launch SF2II via
`bin/SIDFactoryII.exe --skip-intro <abs path>`, workdir bin); ONE MoN-engine build
at a time; `git checkout -- drivers_src/mon/layout.inc drivers_src/mon/freqtable.inc
drivers_src/romuzak/layout.inc` after every native build.
</original_task>

<work_completed>
ALL COMMITTED + PUSHED (master == origin/master @ 53240b7). v3.18.0 RELEASED
(CLAUDE.md/CHANGELOG/STORY/__init__ bumped; docs/SF2.md regenerated; artifact
ef593833-e303-4745-88e5-23190f4eef5b republished). Full suite 1524 green.

THE INSTRUMENT-CAP OPTIMIZER (commits 171b0de + a210d83) — all measured:
- WAVE PRONG: (a) RELEASE_WF driver feature (drivers_src/mon/romuzak_driver.asm):
  gated-off frames write per-voice VRELWF ($193D) = the instrument's release wf
  VERBATIM (poked IRELWF $1960, 32 bytes, = SM rec[8]; mutually exclusive with
  HP_ENGINE/TEMPO_SCHED region reuse) instead of program&$fe. `_rel_split` moves
  each note's trailing rec[8] run into gate-off sequence rows -> wave programs
  collapse to the duration-independent body. Guards: register-exact (_wave_rel_ok)
  + tail within 1 frame of a row tick. RELEASE_WF=0 compiles BYTE-IDENTICALLY —
  Hawkeye sub2 SF2 proven identical TWICE (after each commit).
  (b) `_first_row_norm`: gate-clear frame 0 + gate-set frame 1 -> frame 1's value
  (boundary bleed; 1-frame class). Shim flags wave_canon/release_wf; kills
  SM_WCANON=0/SM_RELWF=0. exi tuple is now 8 wide (relwf at [7]); build_native_song
  returns 8-tuple; instr key + idist include relwf.
- FILTER PRONG: Dance part-8 window was 9 src -> 32 slots ALL from filter splits
  (15 programs/247 rows). TWO root causes: (1) SM SWITCHES FILTER ROUTING PER
  SECTION — detect_filter_drives gained `dynamic` mode (flag filter_tie): credit
  the voice the $D417 routing bits point at ON the attack frame (the fixed
  dominant-voice restriction dropped every re-attack in re-routed sections; the
  re-attacks aligned with v0's notes at ctl=$f1 while v1 dominates globally).
  (2) SM restarts the envelope on EVERY note-set incl. same-pitch legato sets (no
  row): tie events are now drive-eligible (drive_onsets) + SMShim inserts
  same-pitch ties at observed re-attacks (±2 frames, routing-credited dict
  filt_resplit; kill SM_FTIE=0). Driver restarts filter on tie rows already
  (VIFLAGS $40 check runs for every note). Window result: 32->14 slots,
  filter 247->60 rows / 5 programs.
- THE GRID-PART INTER-VOICE DESYNC BUG (pre-existing, SHIPPED IN v3.17.0):
  SMShim.frame_to_tick was IDENTITY; on grid builds the engine's per-part lead
  (first_tick - frame_to_tick(t0)) went negative -> clamped 0 -> ALL 3 VOICES
  started their first in-window note at ROW 0 for every grid part >= 2. Masked by
  part01-only strict sweeps + per-voice-delay tooling. Fix: round(frame/fpt).
  Dance part05: 28-65% freq at any single delay -> 100.0 EVERY register EVERY
  voice + filter 98.3.
- SM CORPUS REBUILT (bin/_sm_build_all.py, SM_GRID=0 for Final_Luv/Thats_All):
  11 songs / 28 parts (was 32): Dance 11->8, Fun_Mix 3->2, Dreamix_Two 3->2.
  CORPUS-WIDE STRICT SWEEP (bin/_opt_sweep_corpus.py — GLOBAL delay, EVERY part,
  first-audible-frame skip; parses out/_sm_build_all.log for windows):
  99.08% freq+wf corpus-wide; most parts 100.0 flat, filter 99.9-100.
  WAV RMS: Poppy_Road 0.92, Dance 1.05 (no loudness regression).
  Dance's binder is now BUNDLES 62-63/63 on every window.

DMC WITHIN-FRAME AUDIT + DEFAULT FLIP (commit e0cf467, work_remaining #3 done):
- bin/_dmc_wf_audit.py: 24/88 DMC files retrigger OFF+ON in one play call
  (Jazz_1 3 state onsets vs 316 write-stream; list in memory
  johannes-bjerregaard-player.md). WORSE than loudness: missed onsets FAILED the
  onset-agreement gate -> whole files on the tick-grid fallback.
- Balloon A/B (part01, own 4s span, best delay): state = wf 0/70/36 pulse 1/0/95;
  within-frame = wf 100/100/92 pulse 100/100/100 (agreement 71/175 -> 174/175 =
  ONSET-ALIGNED unlocked; Domino_Dancing flips too; Jazz_1 fails BOTH ways =
  multispeed, byte-identical tick-grid output either way — the gate protects it).
- within_frame=True is now the DMC DEFAULT (DMC_WF=0 reverts). DMC corpus NOT
  yet rebuilt with it (out/dmc is stale vs the new default).

Diagnostics added: INSTR_DECOMPOSE=1 env (pre-cluster per-source-instrument slot
decomposition in build_native_song), FILT_DEBUG unchanged. Scratch (untracked):
bin/_opt_diag.py (one-window probe), bin/_opt_measure.py, bin/_opt_measure_parts.py,
bin/_opt_sweep_corpus.py (corpus sweep), bin/_opt_filtdump.py, bin/_dmc_wf_audit.py,
bin/_sm_build_all.py (updated: SM_GRID=0 set, romuzak layout checkout).
Memories updated: soundmonitor-player.md (optimizer results + desync bug + final
corpus + residual pockets), johannes-bjerregaard-player.md (audit + flagged list).
</work_completed>

<work_remaining>
1. **DMC corpus rebuild with the within-frame default** (out/dmc is stale).
   Balloon alone went wf 0->100; the other 23 flagged files should improve
   similarly. Sequential runner needed (mirror bin/_sm_build_all.py; DMC corpus
   ~43 onset-eligible files, hours). Then update docs/players/DMC.md numbers +
   gen_sf2_index. NOTE: many DMC files are 77-parts-class (fpt=1 bloat) — the
   SM step-grid generalization (whats-next of v3.17.0, still open) would cut
   those 3-5x; consider doing grid + rebuild together to avoid two full passes.
2. **SM residual pockets** (bounded, documented in memory): Dance part03 v0
   pulse 4.0 (!) + part04 v1 pulse 43.7 + part08 v1 52/45/47 (song end) +
   part02 filter 32.3; Dreamix_Two v1 release-tail slides (known class — the
   RELEASE_WF feature may now make the tail-slide expressible!); Thats_All
   part03 v1 89. Also grid × tie-chain interaction (Final_Luv/Thats_All still
   SM_GRID=0, root cause undiagnosed).
3. **The bundle channel = the next part-reduction lever**: after the optimizer,
   EVERY Dance window binds on bundles 62-63/63 (the (FM,pulse) command
   channel). docs/analysis/PART_REDUCTION_PLAN.md Phase 1 (BUNDLE_TOL) +
   arp-struct are the mapped tools; SM's chord arps are STRUCTURAL (8-byte
   semitone tables in the row headers — the parser knows them!) so a
   MON_ARP_STRUCT-style semitone-arp emission for SM could collapse the FM side
   losslessly.
4. **Cross-player instrument-cap audit** (user: "this applies for all players"):
   run INSTR_DECOMPOSE=1 on a MoN/Hubbard window; Hubbard uses hp_engine keys
   (different mechanics) but MoN may have tail classes; RELEASE_WF is generic —
   any shim can provide 'release_wf' per instrument.
5. **Gallefoss/SDI arc** (user priority; memory/gallefoss-sdi-player.md):
   extract the SDI 2.1 ASSEMBLER SOURCE from bin/SIDDuzz/SDI-21-BMTass.d64
   (need a d64 reader — check bin/DMC tooling), map the play+3 cluster (222
   files) from the source, then parser -> Stage A -> Stage B. Apply the
   step-grid from day one; grid × tie caveat applies.
6. Smaller: SM sound-record bytes 7/14/15 + the 16-23 extension block (the
   editor binary bin/'sound monitor'/soundmonitor 1.1.prg = ground-truth
   shortcut); Demo_of_the_Year_87_menu $C020 variant.
</work_remaining>

<attempted_approaches>
DO NOT RE-TREAD (this session's additions):
- Filter ties on the DOMINANT routed voice only: barely landed (drives 570->585)
  — SM re-routes per section; the attack-frame routing credit was the real fix.
- Filter-tie insertion for pitch-change ties only: the re-attacks are mostly on
  SAME-PITCH note-sets and v0 GATE rows — the drive-eligibility + dynamic
  routing did the work; the same-pitch tie insertion adds little on Dance but
  is kept (harmless, catches non-gate note-sets).
- Jazz_1 as a DMC within-frame testbed: it fails the agreement gate in BOTH
  modes (multispeed class) -> byte-identical tick-grid output; use Balloon/
  Domino_Dancing to demonstrate the effect.
- Measuring later parts at delay 0 or with per-voice delays: the desync bug was
  invisible to both for a whole release. GLOBAL best-delay per part, strict,
  from each voice's first audible frame (bin/_opt_sweep_corpus.py) is the
  honest metric.
- Naive 25s measurement of a 5s part (Balloon): scores garbage past the part's
  span — always clamp to the part window.
- vsid export_to_wav needs pathlib.Path args (str -> AttributeError).
</attempted_approaches>

<critical_context>
- ENV: Windows, `py -3`; /tmp in Bash = C:\Users\mit\AppData\Local\Temp. Long
  jobs: PowerShell Start-Process detached + log redirect (Bash tool cap = 10
  min); ONE MoN-ENGINE BUILD AT A TIME; checkout drivers_src includes after
  builds (bin/_sm_build_all.py does it per file).
- MEASURING LADDER (v3.18 edition): (1) corpus sweep bin/_opt_sweep_corpus.py
  (global delay, every part — catches desync), (2) INSTR_DECOMPOSE=1 +
  FILT_DEBUG (cap decomposition), (3) WAV RMS via vsid (Path args!), (4) CPU
  write-stream dumps, (5) crown jewel = Hawkeye sub2 BYTE-COMPARE (stash the
  old SF2, rebuild, cmp — stronger than re-measuring).
- SM shim flags now: freerun_pulse=1, pulse_loop=1, pulse_tie=1, sid_model=6581,
  wave_canon=1, release_wf=1, filter_tie=1 (env kills SM_WCANON/SM_RELWF/
  SM_FTIE=0), snap_gate=True, grid auto (SM_GRID=0 kill).
- Driver conditionals: RELEASE_WF joins HARD_RESTART/PULSE_LOOP/PULSE_TIE/
  NOTE_PREAMBLE etc. in layout.inc (written by build_romuzak_native_song's
  gen; B.RELEASE_WF set in emit_one from m.release_wf). IRELWF poked in
  emit_one after assemble.
- build_native_song returns 8-tuple (…, instr_src, instr_relwf); emit_one
  unpacks it; count_only unchanged 5-tuple.
- detect_filter_drives(ftr, onsets_by_voice, routed, dynamic=False) — dynamic
  only when the shim sets filter_tie; MoN path byte-identical (proven).
- DMC builder: within_frame default ON (DMC_WF=0 reverts); the 0.85
  onset-agreement gate still routes multispeed files to tick-grid.
- The Balloon state-build parts are stashed in the session scratchpad
  (balloon_state/) — gone after session end; rebuild with DMC_WF=0 if needed.
- v3.18.0 released this session: 4 commits (171b0de wave prong, a210d83 filter
  prong + desync fix, e0cf467 DMC default, 53240b7 release docs), all pushed.
</critical_context>

<current_state>
- Repo: master == origin/master @ 53240b7, tree CLEAN except intentional
  untracked (SID/Gallefoss_Glenn, SID/Jeff, SID/Red_kommel_jeroen, bin/LFT,
  bin/SIDDuzz, archive/cleanup_2026-07-09, bin/_*.py scratch, out/).
  Version constant 3.18.0. Full suite 1524 passed (this session, post-changes).
- SM corpus: out/soundmonitor/ = 11 songs / 28 parts, all fixes, sweep-verified
  99.08% strict freq+wf corpus-wide (log: out/_opt_sweep.log; build log:
  out/_sm_build_all.log — _opt_sweep_corpus.py parses it for windows).
- DMC corpus: out/dmc STALE vs the new within-frame default (only Balloon +
  Jazz_1 rebuilt this session, Balloon with the new default).
- Crown jewel: out/mon/Hawkeye_sub2_native.sf2 byte-identical to pre-session.
- NEXT SESSION: user's standing priority = Gallefoss/SDI (work_remaining 5);
  the DMC corpus rebuild (1) is mechanical and could run detached alongside;
  the bundle lever (3) is the next SM part-reduction step. Ask which.
</current_state>
