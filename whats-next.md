<original_task>
Standing mission: tools combining static RE + AI to convert any SID into an SF2 at 99%
fidelity + 100% editable. User priorities: fidelity, honest fidelity MEASURING, and fewer
SF2 files per song (a subtune may be its own file; parts within a subtune should shrink).
NEXT PLAYER (user, 2026-07-10): **SOUND MONITOR** (memory/soundmonitor-player.md — arc
opened, recon done). Priority list: Hubbard DONE, DMC 41/88 (active), Soundmonitor next,
then MoN/Deenen; more players incoming.
</original_task>

<current_state>
v3.16.0 (2026-07-10). Repo in sync; 1512 tests green; CI fully green (the security scan
was red for 199 runs — fixed for real, see CHANGELOG 3.16.0). Campaign results:
- PART REDUCTION: root cause measured (~95% of splits = the 64-slot (FM,pulse) bundle
  channel). pulse_canon (V1 hp_engine only): Commando 45->4, Monty 22->4 byte-exact.
  Track bit7 TRANSPOSE generation decoded -> Shockway 638->21 parts (first correct
  decode). Builders auto-prune stale parts. Hubbard corpus ~529 files (a full rebuild
  with ALL fixes was launched 2026-07-10 ~11:30 — check out/_hub_rebuild2.log, then
  `py -3 pyscript/gen_sf2_index.py` to refresh docs/SF2.md + republish the artifact).
- FIDELITY: wave REST-TAIL fix (shared engine) -> Supremacy sub1 94.3->99.9 every
  register, Cybernoid II part01 100x3, Cybernoid I wf/pulse 100; crown jewel intact.
  DMC 41/88 eligible; legato full-song A/B shipped.
- ANALYSER (bin/mon_part_fidelity.py): per-voice delay, skew-vs-content classification,
  mismatch-cluster report, part-loop auto-cap. TRUST ITS CLASSIFICATIONS: 47.7 strict /
  100 skew-tolerant = audibly exact write-jitter, not a defect.
</current_state>

<work_remaining>
1. **SOUND MONITOR (the next arc — start here).** memory/soundmonitor-player.md has the
   recon: 11 Fun_Fun files init=$C000/play=$C475 (Hülsbeck Soundmonitor; player at
   $C000-$CBFA, song data below at varying loads). GROUND TRUTH: ROMUZAK's editor has a
   SOUNDMONITOR_CNV converter (out/romuzak_editor_decrunched.prg, entry $1000) — read its
   SM-parsing code FIRST; plus bin/'sound monitor/' disks + the public 64'er format docs.
   Method: docs/players/PLAYBOOK.md (exemplar disasm -> parser -> onset validate ->
   Stage A/B via the shared MoN engine).
2. Transposed-track Hubbard class (Shockway/Star_Paws/Saboteur/Auf_W): pulse engine
   DECODED (self-modifying per-instrument rails — memory/hubbard-player-re.md); remaining
   = (a) fetch-frame pulsework step, (b) fx-arp steps RE-FETCH (PW resets per arp flip;
   decode holds one longer note). osc2/osc3 pulse already 100; osc1 27.
3. DMC: ~21 NO-TABLES left (next cluster: 2nd/Skateboard/Tuba share la=$c367); Special_
   Agent osc2 pulse; Scandalous osc1 pulse.
4. Hawkeye sub0 filter window-seams; Deep_Strike WAVE-overflow count-vs-emit crash;
   Devils_Galop/I_Ball/Wiz spin timeouts.
5. Registry-wire the native players into the auto sid-to-sf2 pipeline (ROADMAP).
</work_remaining>

<critical_context>
- ENV: Windows, `py -3`. NEVER run pyscript/sf2_open_in_editor.py (PyAutoGUI hijacks the
  user's window). ONE MoN-engine build at a time (shared drivers_src scratch); after any
  driver build: `git checkout -- drivers_src/mon/layout.inc drivers_src/mon/freqtable.inc
  drivers_src/romuzak/layout.inc`. Long jobs: PowerShell Start-Process detached + log
  (Bash bg dies at 10 min); PS `*>>` logs are UTF-16 (read via PowerShell Get-Content).
- MEASURING: bin/mon_part_fidelity.py <part> <sub> <secs> [t0_s] — pass the part's REAL
  window (from the build log); the loop auto-cap catches overruns now. DMC files:
  bin/_dmc_fidelity.py (untracked scratch) or the mon tool pattern.
- Builders prune stale parts automatically now, but older-era leftovers may still lurk
  in out/ subdirs the rebuild didn't touch.
- Bandit gate: bandit -r . -ll -ii -x ./test_converter.py,./archive — bin/_*.py scratch
  is untracked/ignored so local findings there don't hit CI; don't commit os.system/
  shell=True/hardcoded /tmp in tracked code.
- pulse_canon: hp_engine builds ONLY (lossy for captured-pulse). MON_PULSE_CANON opt-in.
- On version bump: CLAUDE.md + CHANGELOG.md + STORY.md + sidm2/__init__.py (done for
  v3.16.0); after native builds: py -3 pyscript/gen_sf2_index.py (docs/SF2.md).
</critical_context>
