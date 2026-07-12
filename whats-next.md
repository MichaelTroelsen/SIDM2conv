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
1. C walk phase — RESOLVED 2026-07-12 (later same session): strict
   median 66.7 -> 84.6 -> **86.0** with the TWO-MODEL refinement
   (55/80 files >= 80 strict, was 26/80; <50 strict: 8 -> 5 files).
   TWO WALK-RESTART MODELS, selected per file by strict agreement
   (the E/V calibration precedent; sweep validate() A/Bs them,
   bin/sdi_to_sf2.py --c-steady passes the winner):
   'onset' (default) = walk restarts at note-on, first plausible arg
   from the start row; 'steady' = walk FREE-RUNS across retriggers
   (tie-style drums) -> majority arg of the $9x loop body (Survival
   33 -> 100/100 STRICT, Denver 80 -> 82.4; Everytime's $FF-arg drums
   were the motivating find but its residual is elsewhere). THE MECHANISM (py65-verified, bin/_sdi_c_walk_trace.py
   on Micro_Mix + Bahbar): instrument records are 11 BYTES (sound-set
   tail computes snd*11 via ASL x3 + ADC x3 at the STA $174D,X site —
   stride now extracted by locate() as c_rec_stride); walk start row =
   record byte +2 ($17B9 column); the walk steps ONE ROW PER FRAME from
   the note-on frame; wf >= $90 = jump BACK (wf-$90) rows and execute
   that row THIS frame ($91 = 1-row park reading arg[Y-1], $93 = a
   looping 3-row chord arp e.g. {+12,+7,+4}). arg bit7 = ABSOLUTE.
   instr_pitch now returns the first-valid-row arg (skips >= $60
   spike rows, follows jump-backs). 3 lock tests added
   (pyscript/test_sdi_parser.py TestSDIVariantCWalk).
   DEAD HYPOTHESES (do not re-tread): (a) "walk steps every other
   frame / $1594 AND #$01 gate" — FALSE for Micro_Mix AND Bahbar (both
   step 1/frame; the no-walk frame is fr+1 only, an HR/transient
   frame); (b) "walk phase differs per sub-class caused the Bahbar
   regression" — FALSE: the old regression was the STRIDE BUG
   (instr % max(1, stride=0) == 0 -> every instrument read the same
   record; Bahbar's args are all zero so correct decode is a no-op
   there — it now scores 97.1/97.1); (c) the 2.1 SOURCE's "$90+ = AND
   #$7F literal waveform" grammar does NOT match this rip generation
   (the rip's $9x = jump-back — trace beats source, PATTERNS.md).
   C RESIDUALS (new item 1b): (i) glide-class voices — sequence glide
   rows slide pitch every frame, no walk reads at all (Magic_Moment v1:
   ctrl $09/$81 then $10 with semi 42,38,35,30,...; Survival 100/33 =
   same shape) — needs glide-aware strict sampling, same as E's open
   item; (ii) the low-WINDOWED subclass — Tanks_3000 DIAGNOSED (py65,
   2026-07-12): the image embeds a DORMANT SECOND PLAYER COPY at
   $25xx-$2B8F whose C patterns match and whose tables reference the
   same song data (hence 64% windowed by luck), while the LIVE player
   runs at $1000 (play vector $1F43 = JMP $1003; init $1F40 = JMP
   $1F46 shim) and matches NO variant signature — an unrecognized
   sub-generation (per-voice dur counters $1083+7v reloaded at $11BA,
   row clock ~12 f/tick vs the dormant record's tempo=1). New
   PATTERNS.md D2 addendum: "the dormant-copy variant". NEXT: flow-dis
   the live $1000 player (fresh variant or a shifted known grammar?);
   the reachability check (follow the play JMP chain, demand matched
   pattern PCs execute) in locate would kill this class generically.
   (iii) WALK-REGATE ROLLS — Everytime/Neverending_Story/Ninja_IV
   DIAGNOSED (2026-07-12, flow-dis $10C8-$11F8 + B1 read trace on
   Neverending): the C track/seq DECODE IS CORRECT (track grammar
   verified instruction-level: $80-$FD all transpose bias $A0 incl.
   the ^$1F+1 borrow path, $FF restart, $FE stop, NO repeats; seq $8x
   dur = AND #$3F, matches ours). Neverending v2 really is ONE
   24-tick note — the 6-frame "onsets" are the INSTRUMENT WALK
   RE-GATING the voice (drum-roll wfprg loops toggling the gate bit
   every cycle; note-on writes $D404=$08 TEST first, $11D9-$11DB).
   Our sequencer-level note matches only the first re-gate; the
   validator counts every gate rise. FIX SHIPPED (commit 7d102e0):
   _c_regate() + _c_emit_note() expand rolls into synthetic re-gate
   notes (re-gate = gate 0->1 rise OR a $09 TEST+GATE hard-restart
   row; per-row pitch args) — Neverending windowed 43.6 -> 100.0.
   ROUND 2 (commit 0bf03c4): flow-dis of the $FE/$FD handlers
   ($1174/$1183) corrected the grammar — $FE = HOLD (gate + walk keep
   running; our old 'off' was WRONG), $FD = GATE TOGGLE (EOR #$01).
   _play_seq_c now models NOTE RUNS (note + $FE holds = one gated
   span) and _c_regates() returns the full (aperiodic) re-gate
   schedule over the run. Selector weighs 2*strict+windowed.
   FINAL C CORPUS: windowed median 98.3, strict median 86.0
   (6 improved / 0 regressed vs pre-rework). STILL OPEN, niche:
   Everytime 28/21 (twin noise voices, mechanism unidentified);
   Ninja_IV 33/33 = GATELESS TEST-CLICK percussion (emu shows ZERO
   gate rises on v1/v2 — the siddump onset heuristic counts
   something else; n=12, low value — consider excluding or aligning
   the onset definition).
   OLD FINDINGS (superseded, kept for context): FINDINGS SO FAR
   (2026-07-12, post-v3.20.0): (a) the naive RESTING-walk model is DEAD:
   C walks step every OTHER frame ($1594 AND #$01 gate; wf >= $90 =
   RELATIVE loop-back by wf-$90), so Bahbar's melodic instruments park
   at +5 only ~fr+10 — OUTSIDE the strict sampler's fr+{0,2,3,5} window,
   while row 0 (arg 0) hits at fr+0. Applying resting pitch would
   regress Bahbar again. The sampler sees EARLY walk rows (0..2), not
   the park. (b) The REAL C gap shape: 54/80 files < 80 strict; the
   interesting class = HIGH windowed + collapsed strict (Micro_Mix
   100/22.7, Little_Bee 100/36.4, Denver 98.9/26.4, Magic_Moment
   98.1/37.0) = timing exact, pitch off by a consistent IN-WINDOW
   amount — suspect per-file/per-voice TRANSPOSE error or an early-row
   offset, NOT the resting-pitch class.
   ROUND 2 (same day, bin/_sdi_c_delta_hist.py — gitignored, D1 delta
   histogram over the 4 files above, broken out by (instrument,
   fr+dk) not just aggregated): the delta is 100% DETERMINISTIC per
   (instrument, frame-offset-since-onset) — ZERO scatter across every
   sampled onset (e.g. Denver instr21 n=49 at EACH of fr+{0,2,3,5}:
   {3,7,7,10} exactly, every time). This proves it's a real stepping
   program, not noise — but also KILLS the single-static-row model:
   several instruments show a multi-step staircase across fr+0..+5
   (Denver instr21, Magic_Moment instr21: 65,8,5,-7), so a frame-paced
   simulator is required, not a lookup.
   BUG FOUND (confirmed, currently dormant/harmless): `instr_pitch`'s
   shared A-style formula indexes `wfprg_start_col + (instr %
   max(1, lay.stride))`; `lay.stride` is ONLY computed in the 'A'
   branch (sdi_parser.py:362-366) — `locate()` returns early for
   B/C/D at line 348, before that runs. So for C, stride stays the
   dataclass default 0 -> `instr % 1 == 0` ALWAYS -> every instrument
   in a file reads the SAME table row. Verified: dumping
   wfprg_start_col+instr%1 gave IDENTICAL wf/arg for every instrument
   in Micro_Mix/Little_Bee/Denver/Magic_Moment; indexing directly by
   `+instr` (no modulo) immediately produced per-instrument-distinct
   rows. Harmless today only because C's instr_pitch short-circuits to
   None before reaching this code (sdi_parser.py:1079-1086) — MUST be
   fixed (proper stride, not just `+instr`, since some instrument
   counts may exceed the column and alias into the next column) before
   any row model is re-tried.
   SOURCE CONTRADICTION (unresolved): the C-locate comment
   (sdi_parser.py:131-134) says "wf,Y CMP #$90 / BCC = $90+ is a
   RELATIVE loop-back" — but re-reading the actual 2.1 source engine
   (bin/SIDDuzz/extracted/sdi21-n49.asm:1580-1635, `wf{CBM-@}kik` /
   `wf{CBM-@}stand`) shows $90-$E1 wf bytes are just AND-$7F-masked as
   a literal SID waveform register value (no loop), and the pitch ARG
   byte is read via `LDA f-1,Y` — one position BEHIND the current wf
   read position (an off-by-one between the wf and arg columns). The
   generic source may not match this rip's compiled variant (editor
   assembles per-song, feature-flagged per CLAUDE.md history) — do NOT
   trust the source grammar blindly; the $90+ semantics need a fresh
   py65 disassembly trace of an actual C rip (Bahbar or Micro_Mix),
   same method used to nail D's walk and A's wfprg.
   NEXT ACTION: py65-trace Micro_Mix (or Bahbar) through its WFPRG
   interpreter at a real note-on to get the ACTUAL row-advance cadence
   + arg/wf column alignment byte-exact, then build a frame-paced
   walk simulator (D's `_d_walk_pitch` style but stepping, not
   resolving to one resting value) gated behind the fixed stride.
2. E (strict median 57.8 -> 61.9, commit d9b1a53; sweep scratch
   bin/_sdi_e_resweep.py -> out/_sdi_e_resweep1.log):
   - Evil_Within FIXED (was all-3-voices-same-track): the tl/th array
     GAP = channels x SUBTUNES (gap 6 = 2 subtunes x 3ch); now factors
     to the compiled channel count. 0-ish -> 51.9/32.7; its residual =
     the general E timing/conduct items below.
   - Arabia (69.1/16.2) SCOPED + PARTIALLY DIS'D (2026-07-12): real
     structure = sparse onsets among dense rows. B1 trace (all-B1 py65
     probe): track reads $EE69 (head) + $EE95/$EEA0 (per-opcode arg
     PCs differ: $C7's arg via $EE95, $A0's via $EEA0); seq reads
     $EEE1 (row head) + $EF37/$EF56 (operands) + $EF65 (LOOKAHEAD —
     the next row's head is PEEKED and Y stored as the new position,
     $EF6A-$EF6B; peek==0 = seq loop marker). Row dispatcher at
     $EEE1-$EF7F hand-read: head $5F = rest/hold; $F0+ = RELEASE
     nibble PREFIX (continues row); $C0-$EF = arp-record redirect
     (idx*2 into $F5B8, known); $A0 exact = self-modifies $EF7E to 5
     (default gate-time?); $A1-$BF = GATE-TIME row ((b&$1F)*4 ->
     $E948,X); $80-$9F = DURATION (&$3F -> $E94A/$E92D/$E947,X) then
     an operand chain ($E0 glide cases at $EF39-$EF44); $60-$7F =
     SOUND set then note; <$60 = NOTE (path at $EF61, pushes #$5F,
     stores via $E943 GLOBAL — tail $EF6E-$EF7F = PHA/PLA lookahead
     dispatch, NOT yet fully understood). KEY MUSIC FACT: Arabia v0
     plays repeated [61 xx] rows with DESCENDING xx every 5 frames
     that do NOT re-gate (a manual glide) — real onsets only every
     ~75 frames. Our E walker emits each as a note -> dense garbage.
     NEXT: finish the $EF61-$EF7F tail dis (when does a note row
     re-gate vs glide?), then port; Zap/Xard/Sweeper likely same.
   - Same low-both-metrics class: Zap 23/10, Xard 45/23, Sweeper 44/23
     — likely the same sub-grammar; diagnose WITH Arabia.
   - Still open: the conduct program (dual row condition), glide-heavy
     strict sampling (shared with C's Magic_Moment class).
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
