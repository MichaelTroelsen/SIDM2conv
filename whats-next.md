<original_task>
This session: (1) executed the MoN handoff (adaptive corpus rebuild, filter/boundary/
tie/preamble fixes — Supremacy wf+pulse now 100% EXACT), (2) completed the Tel-corpus
survey (15 new tunes converted; 4 new player arcs identified and prioritized by the
user: 1. Rob Hubbard, 2. Soundmonitor, 3. MoN/Deenen), (3) BUILT THE ROB HUBBARD ARC
end-to-end in one day: format RE (C=Hacking #5 ground truth), parser (100% onsets),
Stage A (11 editable SF2s, 99.85% onsets, ear-approved), Stage B native driver
(Zoids 100% registers; Commando ear-approved "mix is good"; 10 tunes built natively).
</original_task>

<work_completed>
ALL COMMITTED AND PUSHED through dda7d88. Key commits this session:
02bd52d/68e4fa0/a7a7ceb/5a17c5b/6c32aa1 (MoN arc: races found+fixed, $FB tie decode,
filter guard+residual, boundary continuation, fcmp floor, hard-restart PREAMBLE —
Supremacy sub2 = 93.3 freq / 100 wf / 100 pulse / 100 filter over the full 150s),
37640fd (Tel corpus: 15 new tunes + pseudo-parse gate), 6c9c885/14fc73b/c6e6619
(Hubbard parser + validator + Stage A), 762a4d6/87e478a/c76c607/dda7d88 (Hubbard
Stage B: $7D hard-restart rows + HRC delayed re-arm, gate-rise snap, FMSCALE_ON,
$D418 synthetic-filter suppression, _hr_rows GATE_ON extension).

HUBBARD STAGE B STATE (out/hubbard/, all *_song0_partNN.sf2):
- Zoids: 15 parts, part1 100/100/100/100 (VICE registers ~100% incl ADSR 89-99).
- Commando: 45 parts, parts1-3 96-97/100/100, ADSR 90-92%, EAR-CONFIRMED mix.
- One_Man_and_his_Droid: 100/100/100 on parts 1-3. Gremlins/Crazy_Comets 97-100.
- Monty: 21 parts; parts2-3 ~100; part1 = THE TWO REMAINING DEFECTS (below).
- Master_of_Magic part1 90/90 (same class); batch output has the rest.
</work_completed>

<work_remaining>
1. **Hubbard lead-voice defects** (Monty part1 82.5 freq / 80.1 pulse, all on V1=lead;
   user ear: "close but not 100%"):
   (a) ornament FM: repeated 6-frame rises (~$540/frame) played flat — short/appended
       note capture misses; diagnose with the per-note capture dump method.
   (b) free-running pulse: ~90-frame phase-drift runs — implement per-instrument
       PERIODIC pulse programs + driver PFREE ($08) cross-note phase (dormant).
2. **Part-count compression** (Commando 45, Monty 21): the Supremacy structural path
   (per-instrument pulse/drum-FM programs instead of per-note captures).
3. **Hubbard variants** (20 files): Warhawk/Spellbound (speed semantics), Knucklebusters
   (per-voice speed: V2 already 100%), Star_Paws/Bangkok (runaway decodes), + later
   Hubbard routines (more fx bits) for the remaining ~50 Hubbard-tagged files.
4. **Next player arcs** (user priority): Soundmonitor (39 files; bin/sound monitor/ =
   user's reference material), MoN/Deenen (72 files, Robocop3/Turrican engine).
5. MoN leftovers: Supremacy V0 drum-attack frame ($FF00 rides 1 late); Hubbard-style
   VICE-dump ADSR audit for MoN tunes (the metric blind spot applies there too).
</work_remaining>

<attempted_approaches>
- Gate-EDGE ADSR kill: WRONG — the ROM kills at NOTE-LENGTH END; a drum's body is its
  release ring (Zoids drums died). The $7D-row model is correct.
- FM_CNT=0 preamble variant: shifted vibratos 1 frame early; keep FM_CNT=1 (pure
  insertion). Trust empirics over phase algebra — iterate with the VICE dump.
- Fixed-second windows for measurement/testing: BYPASS the cap probe -> ungated
  bundle force-merges -> garbage programs ("$900 pulse mystery"). AUTO windows only.
- Register-STATE % metrics as the only truth: BLIND to ADSR values, $D418, 1-frame
  gate windows, and content-static tempo errors. The VICE register-stream dump diff
  (vsid -sounddev dump) is the truth-teller; audio attack-rate/RMS A/B catches what
  registers can't.
</attempted_approaches>

<critical_context>
- METHOD: docs/players/PLAYBOOK.md + memory/hubbard-player-re.md (the complete arc
  log incl. every gotcha: 64tass case-collisions ×2, VICE $FF-fill RAM, siddump vs
  note-onset frame origins, drum runtime-state pitches, ±8 drum gate-on windows).
- Hubbard format: memory/hubbard-player-re.md; C=Hacking #5 source at
  docs/analysis/hubbard/chacking5_monty_disassembly.txt (effects: vibrato osc
  01233210, pulse $08xx-$0Exx bounce stored INTO the instrument, portamento/frame,
  drums=noise 1st frame + freqhi--, skydive, octarp note/note+12).
- Driver flags (layout.inc, from shim attrs): HARD_RESTART (+$7D rows, VAD/VSR/HRC
  state $1880-$1888, out-of-line handlers at $1890), FMSCALE_ON (0 for Hubbard:
  real deltas hit the $40-$43 scaled marker), NOTE_PREAMBLE (Supremacy only).
- MoN builds: ALL flags default -> byte-identical (Hawkeye sub3 regression-checked
  after every driver change: 100/100/100/100). NEVER run two MoN/Hubbard builds
  concurrently (shared drivers_src scratch). git checkout -- the .inc files.
- Fidelity rig: bin/mon_part_fidelity.py PART SONG SECS OFF0 (folders: Tel_Jeroen +
  Hubbard_Rob); VICE dump diff snippets in the session log / memory; WAV A/B via
  sidm2.vsid_wrapper.export_to_wav + numpy attack-rate/RMS.
- User: ear-driven acceptance; the ear caught THREE defects all metrics missed.
  Standing rule: accuracy first, never ship lossy silently.
</critical_context>

<current_state>
Working tree clean at dda7d88 (pushed). The 9-tune native batch may still be
completing — artifacts land in out/hubbard/; check the batch output for
Last_V8/Geoff_Capes/5_Title_Tunes/Chimera numbers. Tests: 1490 green at last full
run; mon+hubbard+romuzak subsets green after every driver change.
Next natural actions: the two Monty lead defects (ornament FM + free-run pulse),
then part-count compression, then variants/Soundmonitor.
</current_state>
