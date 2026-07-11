<original_task>
Standing mission: any SID -> SF2 at 99% fidelity + 100% editable. Session
2026-07-11 (two releases in one day): user chose the INSTRUMENT-CAP OPTIMIZER
(v3.18.0), then "rebuild the dmc corpus with the new default", then
"please do 3. then 2." (= SM residual pockets, then part-bloat levers), then
"can we work on glen now" -> the Gallefoss/SDI arc opened. v3.19.0 released.
STANDING RULES: accuracy over speed; never ship lossy silently; NEVER run
pyscript/sf2_open_in_editor.py; ONE MoN-engine build at a time; git checkout
drivers_src includes after every native build; DON'T edit builder modules
while a corpus runner is active (subprocess imports race — nearly burned
Fun_Mix).
</original_task>

<work_completed>
ALL PUSHED (master @ dc93464 = v3.19.0). Full suite 1524 green. See
CHANGELOG v3.18.0 + v3.19.0 for the complete list. Highlights beyond the
changelogs:
- Measuring traps found this session (in memory): per-voice-delay metrics
  can't see inter-voice desync; rounded-second window labels wreck sweeps of
  grid parts (parse the f-form frame bounds); grid probes lead by the grid
  RESIDUE (Balloon -4) — search delays wide; vacuous guards (tolerance >
  compared frames) accept garbage.
- SM corpus: out/soundmonitor = 11 songs / 27 parts, sweep out/_opt_sweep.log
  = 99.23% strict freq+wf. Dance parts 2-6 + Fuck_Off part01 (242s) = 100.0
  every register. Honest residuals: Dance drum-roll (part07 v1 76), Thats_All
  v2 pulse 71-85 + part03 v1 88.7, Dreamix_Two v1 pulse 61-71 + filt 53-88
  (release-tail class), 1s stub parts at song ends (cosmetic).
- DMC corpus: out/dmc = 56 songs / ~944 files (grid pass). Grid collapses
  SEQUENCE-bound files (Balloon 77->1); BUNDLE-bound files keep counts (Alf
  40 parts at bundles 50-62/63 — the proven DMC diversity boundary). Files
  with off-grid onset minorities (Cant_Stop 273/26 split residues,
  French_Frites) honestly stay fpt=1.
- Gallefoss/SDI: source EXTRACTED + first-pass format map (see
  memory/gallefoss-sdi-player.md — extraction recipe, track/seq bytes,
  zN instrument tables, section map of sdi21-n49.asm).
</work_completed>

<work_remaining>
1. **Gallefoss/SDI parser — SHIPPED to 172/229 play+3 decode-capable**
   (commits 5e01520..0e79154; sidm2/sdi_parser.py + test_sdi_parser.py +
   bin/_sdi_validate.py): variant A (50 files; 4x100%, rest 98-99.5),
   B (42; Airwalk/Airwalk_II 100%), C (80; Banana_Man 98.9, Basselusk
   94.9, Bahbar 91.4). REMAINING: variant D (Another_Day class) recon'd +
   gated (2-byte track header w/ per-voice speed; freq layout differs;
   needs a flow-following disasm); the Commando/Delta-cover locate-NONE
   sub-group; the play+4 generation (213 files); then instrument tables
   -> Stage A -> Stage B (step-grid native; C's note-on writes $D404=$08
   TEST bit = hard-restart-style). Full trail in
   memory/gallefoss-sdi-player.md.
2. DMC bundle-bound files (Alf/Cant_Stop class): needs a DMC bundle lever —
   v3.16 proved clustering is a dud; candidates: DMC pulse canonicals
   (pulse_canon pattern — DMC PWM restarts per note like SM?) or wavetable-
   arp structural programs (the $1A00 table IS known to the parser; the SM
   arp_struct pattern now exists to copy — but the freq table isn't PAL,
   mind the dead-end note in docs/players/DMC.md).
3. SM residuals (small): Dreamix_Two release-tail pulse/filter; drum-roll
   phase class; 1s stub parts (absorb-or-drop cosmetic); grid x tie root
   cause (Final_Luv/Thats_All still SM_GRID=0).
4. Version-history docs for the DMC per-tune fidelity table in docs/SF2.md
   are stale vs the grid corpus (re-measure the strongest files with wide
   delay + own-span windows someday).
5. Cross-player: INSTR_DECOMPOSE audit on MoN/Hubbard; RELEASE_WF is generic
   (any shim can provide 'release_wf').
</work_remaining>

<attempted_approaches>
DO NOT RE-TREAD (adds to the v3.18.0 handoff list):
- Arp acceptance with flat tolerance: VACUOUS for short notes (accepted
  garbage drum steps). Tolerance must scale with compared frames.
- Freerun pulse STREAMS on pulse_tie engines: categorically wrong (the
  engine resets PW per note); banned in build_native_song.
- Sweeping grid parts with rounded-second windows or narrow delay searches:
  both produce catastrophic-looking numbers on byte-faithful builds.
- DMC grid residue test including legato decode frames: their phase differs;
  test gates only.
- Editing bin/build_soundmonitor_native_song.py (or any builder) while
  _sm_build_all/dmc_build_all runs: per-file subprocesses import the edited
  module mid-run.
</attempted_approaches>

<critical_context>
- SMShim flags now: freerun_pulse=1 pulse_loop=1 pulse_tie=1 wave_canon=1
  release_wf=1 fm_loop=1 filter_tie=1 arp_struct=1 pulse_canon=1 (env kills:
  SM_WCANON/SM_RELWF/SM_FMLOOP/SM_FTIE/SM_ARP/SM_PCANON=0, SM_GRID=0,
  sid_model=6581). tbl_arp_idx=1 + arp_program(w) expose the deduped
  row-header chord tables; MONEvent.wprog = arp id (0=none).
- DMCShim: within_frame default (DMC_WF=0), grid (DMC_GRID=0), _onset_mode
  keys note_freq (PAL when onset-aligned!), _grid keys frame_to_tick round.
- Engine (build_mon_native_song): _rel_split/RELEASE_WF, _first_row_norm,
  _wave_rel_ok, _rel/gate split ARP gates, fm_program_for(allow_loop),
  detect_filter_drives(dynamic + reversal), drive_onsets incl. ties (ftie),
  streams banned for pulse_tie, arp tolerance scaled. exi = 8-tuple,
  build_native_song returns 8-tuple, IRELWF poked $1960.
- Crown jewel verified BYTE-IDENTICAL 4x this session (stash-compare method:
  cp the SF2, rebuild, cmp — stronger than re-measuring).
- SDI extraction recipe + format map: memory/gallefoss-sdi-player.md.
  c1541 at /c/winvice/bin/ (petcat too). PETSCII disk = the readable source.
- Sweep tooling: bin/_opt_sweep_corpus.py (frame-exact, global best-delay,
  first-audible skip); bin/_opt_measure_parts.py; bin/_dmc_wf_audit.py;
  INSTR_DECOMPOSE=1/FILT_DEBUG=1/BUNDLE_DECOMPOSE=1 envs.
</critical_context>

<current_state>
- Repo: master == origin/master @ dc93464 (v3.19.0), tree CLEAN except
  intentional untracked (+ bin/SIDDuzz/extracted = the SDI sources,
  bin/_rebuild_both.py + _opt_* scratch). 1524 tests green post-changes.
- out/soundmonitor 27 parts (swept); out/dmc ~944 files (grid corpus,
  Alf rebuilt post-legato-fix). Artifact republished (same URL).
- NEXT: the Gallefoss/SDI parser (work_remaining 1) — the arc is open with
  the format substantially mapped; start at the SEQUENCER section + the
  data-table definitions, then 30seconds.sid.
</current_state>
