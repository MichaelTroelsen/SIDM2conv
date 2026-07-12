<original_task>
Standing mission: any SID -> SF2 at 99% fidelity + 100% editable. Session
2026-07-12: user directives "complete the SDI first", then the knowledge
tiers ("Do 1 and 2"). v3.20.0 released (commit 157afc5).
STANDING RULES: accuracy over speed; never ship lossy silently; NEVER run
pyscript/sf2_open_in_editor.py; ONE MoN-engine build at a time; git checkout
drivers_src includes after every native build; DON'T edit builder modules
while a corpus runner is active (subprocess imports race — nearly burned
Fun_Mix).
</original_task>

<work_completed>
v3.20.0 = THE SDI PITCH-CARRIER CAMPAIGN + THE KNOWLEDGE BASE (all on
master; full suite 1534 green). See CHANGELOG v3.20.0 + docs/players/SDI.md.
- SDI six variants decoded (A-E + V). D wfprg resting-pitch port -> 12
  files 100.0 STRICT (Another_Day 81->100, Banana 69->100); D $ff = track
  LOOP not stop (Sveitser 69.5->99.2, Space_Suit 49.6->69.9); E row-0
  pitch (byte-verified 2_Young $EE1F: set-instr tail applies f[z0[sound]]
  ON the note-on frame) + $c0-$ef arp records REDIRECT the sound + timing
  calibrated per file by STRICT agreement (Kirby 16.5->71.0 from
  calibration alone); V = the "VE-2x/4x multispeed" files were FALSE D
  LOCATES (play=$0000 wrapper drives a 3-JMP module 2x/4x; V's seq-row
  read is byte-identical to D's track read -> V dispatches BEFORE D) —
  full tracker engine decoded from 0.0 (state blocks $0400+v*$40, per-seq
  length-in-ticks, per-note instrument in the fx byte, octave-nibble
  pitch); C wfprg LOCATED but GATED (onset apply regressed Bahbar
  94.3->81.4 — the walk phase differs per sub-class).
- Final corpus map (dual-metric sweep out/_sdi_sweep2.log, 249 validated,
  windowed/strict medians): A 98.3/98.3, D 100/100, C 98/66.7, B 89/74.8,
  E 72/57.8, V 70/21.8; 122 locate-NONE (play+4 tail + covers).
- STAGE A: 254 SF2s, 0 failures (bin/sdi_to_sf2.py -> out/sdi_sf2/,
  indexed in docs/SF2.md with Composer/Released columns).
- KNOWLEDGE BASE: docs/players/PATTERNS.md (technique catalog — named
  mechanisms P1-P9 / diagnostics D1-D8 / failure classes F1-F4, each with
  sightings; the pitch-carrying instrument = P1, 5 independent finds) +
  sidm2/player_idioms.py (find_pattern/find_all/scan_freq_tables/
  follow_immediate_poke/bounded_init; tests lock idioms against corpus
  files; sdi_parser consumes it). Linked from PLAYBOOK/README/INDEX.
</work_completed>

<work_remaining>
SDI residuals (docs/players/SDI.md "Open items" + memory
gallefoss-sdi-player.md):
1. C walk phase (Bahbar vs Banana_Man sub-classes) — emulate the first
   walk step's timing vs note-on, then un-gate C's instr_pitch.
2. E: Evil_Within (all 3 voices decode the SAME track — tp mapping; note
   its tick gaps x3 == real gaps exactly, tempo model is right), Arabia
   (row grammar misparse — structure wrong, not just tempo), the conduct
   program (dual row condition), glide-heavy strict sampling.
3. V: its own wfprg walk (drum absolutes +32-class, -1 detunes), tempo
   commands done right (the naive tick->call map LOST the A/B to a flat
   calibrated clock — Oh_Boy 47 vs 70 windowed).
4. D pocket: Holy_Josh 65.7 / Max_Mix_1 75.0 (long tracks, cause unknown).
5. Acid_Jazz sixth layout (play=$1B36, absolute state arrays $22ED+).
6. SDI STAGE B native via the shared MoN engine (step-grid; the C-class
   note-on writes $D404=$08 TEST bit — mind the gate model).
Backlog: SM bundle channel (binds 62-63/63); DMC bundle-bound files;
cross-player INSTR_DECOMPOSE audit; new players per
memory/new-player-priority.md (MoN/Deenen after Gallefoss).
</work_remaining>

<attempted_approaches>
DO NOT RE-TREAD (see docs/players/PATTERNS.md for the named catalog):
- C onset pitch from arg[start] blindly: regresses Bahbar (walk phase).
- V tempo emulation via naive tick->call map: lost the A/B to flat fpt.
- Selecting E/V timing models by windowed onsets: picks wrong mappers —
  select by STRICT agreement.
- Treating 0.0-on-both-metrics as a decode bug: it is a FALSE LOCATE
  until the operands are verified (paid twice: PATTERNS.md D2).
- Flow-dis alone for state semantics: it misses paths behind unfollowed
  dispatch — complement with raw-binary greps for state-cell writes
  (V's per-note instrument at $1669).
- Plus all v3.18/19 entries (vacuous tolerances, freerun pulse streams on
  pulse_tie, rounded-second sweep windows, editing builders mid-run).
</attempted_approaches>

<critical_context>
- sdi_parser: SDILayout has per-variant fields (d_*, e_*, v_*); locate
  dispatch order A -> C -> V -> D -> E -> B (V BEFORE D is load-bearing).
  E/V validators calibrate timing per file (bin/_sdi_sweep.py, gitignored
  scratch). V frames are PLAY CALLS -> divide by lay.v_mult.
- instr_pitch(): A row-1, D _d_walk_pitch (resting row), E row-0 f[z0],
  C returns None (gated), V handled inline in _decode_voice_v.
- player_idioms.bounded_init: stop on JMP-self spin, NOT first vector
  write (vectors install before module init — SDI V left voices unset).
- SDI 2.1 source: bin/SIDDuzz/extracted/sdi21-n49.asm (c1541+petcat at
  /c/winvice/bin/). WAVEFORM PROGRAM section line 1451, SET INSTRUMENTS
  670, SEQUENCER 857.
- Crown jewel stash-compare method: cp the SF2, rebuild, cmp.
- SM/DMC state unchanged from v3.19.0 (out/soundmonitor 27 parts,
  out/dmc ~944 files).
</critical_context>

<current_state>
- Repo: master @ 157afc5 (v3.20.0), tree clean except intentional
  untracked (SID/ corpora, bin/SIDDuzz, out/, scratch). 1534 tests green.
- out/sdi_sf2 = 254 Stage A SF2s; docs/SF2.md regenerated.
- NEXT: SDI residuals above, or Stage B, or the next player — user's call.
</current_state>
