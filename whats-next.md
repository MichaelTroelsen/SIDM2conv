<original_task>
Standing mission: any SID -> SF2 at 99% fidelity + 100% editable.
Session 2026-07-12/13 (continuous). Entry point: "continue" from the
v3.20.0 handoff (SDI campaign complete). Work then flowed through a
sequence of user directives:
1. "continue" -> resume SDI variant-C walk-phase investigation.
2. TDZ knowledge base: "start adding information to the Knowledge LLM
   ... build all the knowledge from SIDM2" (shared cross-project KB).
3. "keep pushing" -> SDI coverage/fidelity.
4. "convert the remaining subtunes too" (multi-subtune support).
5. Q&A: songs/subtunes per file, how conversion works.
6. "please move version history from claude.md into changelog.md ...
   keep claude.md compact" + "add the usage for TDZ knowledge MCP into
   claude.md".
7. This /whats-next handoff.

STANDING RULES (do not violate): accuracy over speed; never ship lossy
silently; NEVER run pyscript/sf2_open_in_editor.py; ONE MoN-engine
build at a time (shared drivers_src .inc scratch); git checkout
drivers_src includes after every native build; DON'T edit builder
modules while a corpus runner is active (subprocess import race);
corpus-gate every decoder change (broad blast radius); verify
disassembly branch targets by EMULATION before rewriting a parser.
</original_task>

<work_completed>
Repo: master, pushed to origin (github.com/MichaelTroelsen/SIDM2conv).
Latest commit 25a5d01. Version constant still 3.20.0 (no bump this
session — all work is post-v3.20.0, unreleased). 1537 tests green.

=== A. TDZ KNOWLEDGE BASE SEEDING (mcp__tdz-c64-knowledge) ===
Discovered a connected shared MCP KB (220 general C64 docs + 5
pre-existing "sid-player-kb" cards seeded by ANOTHER session). Seeded
21 SIDM2 documents via parallel background agents (each read
docs/players/*.md + parser + CLAUDE.md changelog + memory, wrote a
card to ~/.tdz-c64-knowledge/temp/, called add_document):
- 10 player/catalog cards: galway (396ee1e69c26), maniacs-of-noise
  (30c8ed7c6b94), rob-hubbard (f877412c3c95), dmc (ef145e10e0cf),
  sound-monitor (86ac9f41a017), romuzak (7c1fe86d1634),
  future-composer (c74d612c42c6), sid-duzz-it (23936cd49d04),
  sid-factory-ii-driver-11 (9ffc2f48aa44), technique-catalog
  (ab3651abf026).
- 3 methodology refs: SF2 file format (f742a4d03d0c), native-driver
  authoring how-to (57738c395f16), fidelity toolchain (fefa764d5852).
- 8 more (2nd/3rd wave): STORY (cd7c08f28599), tooling landscape
  (70e7de8d9e99), SF2 driver family (7f75330d7a4d), PSID/RSID format
  (a9c1e1348165), Laxity NP21 disassembly (1c4ad8d0c81f), 3 primers
  (df14227e7987/ded5e2475eb2/62657b762e23).
Another session concurrently added 7 NP21-cluster cards (JCH NP20,
DRAX, Stinsen, Beast/Angular, Wizax-A, Zetrex/YP, 2000AD) — those are
COVERED, don't re-add. Card schema + add_document allowed-dir gotcha
documented in memory/tdz-c64-knowledge-base.md.

=== B. DOC-TRUTH FIXES (surfaced by the KB audit) — commit 3044876 ===
- docs/reference/format-specification.md: PSID v3/v4 corrected to
  HVSC-canonical ($7A/$7B = 2nd/3rd SID ADDRESS bytes; flags bits 6-9
  = 2nd/3rd SID MODELS not addresses).
- docs/analysis/DRIVER_LIMITATIONS.md: stale accuracy (Laxity 70% ->
  99.93-100%, NP20 95% -> 70-90%).
- STINSENS_PLAYER_DISASSEMBLY.md + LAXITY_DRIVER_TECHNICAL_REFERENCE.md:
  instrument-table layout contradiction annotated (row-major prose vs
  column-reading hex dump; 32 = editor capacity vs 8 populated) —
  UNRESOLVED, needs byte verification.
- sidm2/low_load_layout.py docstring: $0500 -> $0100 floor (code
  already enforced $0100 since v3.5.56).

=== C. SDI VARIANT C — DECODED (strict median 66.7 -> 86.0) ===
Commits 1ab12be, cf7f8d9, d4f42ea, 7d102e0, 0bf03c4 (+ checkpoints).
The C wfprg walk is a py65-verified frame-paced program (tool:
bin/_sdi_c_walk_trace.py — MPU + PC breakpoints at the located wf/arg
read instructions):
- Instrument records are 11 BYTES. The sound-set tail computes
  instr*11 via ASL x3 + ADC x3 at the STA $174D,X site; locate() now
  extracts lay.c_rec_stride from that pattern (locate handler:
  [0xBD,-1,-1,0x0A,0x0A,0x0A,0x7D,-1,-1] then count ADCs, stride =
  8 + #ADCs). Walk start row = record byte +2 (the $17B9 column).
- Walk steps ONE ROW PER FRAME from the note-on frame. wf >= $90 =
  jump BACK (wf-$90) rows and execute that target row the SAME frame
  ($91 = 1-row park, $93 = looping 3-row chord arp {+12,+7,+4}).
- arg bit7 = ABSOLUTE semitone, else relative to note+transpose.
- TWO per-file restart models (self.c_pitch_model, default 'onset'):
  'onset' = walk restarts at note-on, first plausible arg from the
  start row; 'steady' = walk free-runs across retriggers (tie drums)
  -> majority arg of the $9x loop body. Selected per file by strict
  agreement in the sweep (weighted 2*strict + windowed so a tiny
  strict gain can't trade a big windowed loss). Builder flag:
  bin/sdi_to_sf2.py --c-steady.
- WALK-REGATE ROLL EXPANSION: a $09 TEST+GATE walk row re-executed
  each loop = a drum roll; each re-gate is a real gate rise the
  validator/Stage A must see. _c_regates() returns the walk's full
  (aperiodic) re-gate schedule; _c_emit_note() expands note rows into
  synthetic re-gate notes with per-row pitch args.
- SEQ GRAMMAR corrected via flow-dis ($1174/$1183): $FE = HOLD row
  (gate + walk keep running, NOT gate-off); $FD = GATE TOGGLE
  (EOR #$01). _play_seq_c models NOTE RUNS (a note row + following
  $FE holds = one gated span).
- The old "regressed Bahbar" gate was a DORMANT STRIDE BUG
  (instr % max(1, stride=0) == 0 -> every C instrument read the same
  record; lay.stride is only set in the A branch). NOT walk phase.
- The authors' 2.1 source ($90+ = AND #$7F literal waveform) does NOT
  match this rip generation — trace beats source.
- 3 lock tests: pyscript/test_sdi_parser.py TestSDIVariantCWalk.
- C corpus (80 files): strict median 86.0, windowed 98.3, 55/80 >= 80
  strict (was 26). Sweep scratch: bin/_sdi_c_resweep.py.

Two NEW named patterns added to docs/players/PATTERNS.md D2:
- "the dormant-copy variant": an image can embed a SECOND never-run
  player whose patterns match + reference the same song data (moderate
  windowed / collapsed strict). Detector: follow init/play JMP chain,
  demand the matched pattern PC is reachable (py65 PC-breakpoint that
  never fires = dormant). Found on Tanks_3000.

=== D. SDI MULTI-SUBTUNE SUPPORT — commit 168cbc0 ===
SDIModule(d, la, subtune=N). Byte-verified mechanisms:
- E: tp = init_block[subtune] (Evil_Within/Phneumatic init_block =
  02 05.. = sub0/sub1 track-set indices, stepping by channel count).
- C/A: 8-byte record at init_block + subtune*8 (the A*8 init index).
- B/D/V: NOT supported (B indexes subtunes differently — sub1 tracks
  == sub0; guard skips duplicates).
bin/sdi_to_sf2.py --subtune N, with a duplicate guard. Converted the
5 VERIFIED E extras (Aldebaran sub1-3, Evil_Within sub1, Phneumatic
sub1). Tanks_3000's 12 subtunes were generated but REMOVED (dormant-
copy locate, unverified — never ship lossy silently).

=== E. SDI "SIXTH LAYOUT" WRAPPER CRACKED (+62 files) — commit 63b240b ===
The 69-file $0FFF play+4 cluster (Acid_Jazz/Afterburner/Ambient/...)
is variant E behind a WRAPPER: init $0FFF = TAX/JMP realinit,
play $1003 = JMP realplay. The real player is E with the SAME row
grammar + tables (all found by the existing E signatures at relocated
addresses). Only the init shape differs: LDY $tp,X / LDX #(nch-1)
[imm $02 = 3ch, $03 = 4ch conduct gen] instead of the classic
LDX #$15. New _sdi_e_wrapper_init(d) anchors on that tail (guarded by
a preceding record-copy BD/8D within 20 bytes) and returns the tp
array; the rest of the E locate is shared unchanged.
RESULT: located 254 -> 312, E corpus 52 -> 114 files, out/sdi_sf2
254 -> 336 SF2s. Examples: Acid_Jazz 100/80, Beginning 98/90,
Arnhild 100/52. E strict median 61.9 -> 47.5 (COMPOSITION effect:
the 62 new conduct-gen files are harder; 2_Young/Kirby unchanged, no
regression). Sweep: bin/_sdi_e_resweep.py -> out/_sdi_e_resweep2.log.

=== F. SDI VARIANT E — foundation (grammar/pitch/timing all proven) ===
Commits d9b1a53 (multi-subtune track fix), ed5fdb5 (conductor).
- Evil_Within FIXED: the tl/th array GAP = channels x SUBTUNES (gap 6
  = 2 subtunes x 3ch). Now factors to the compiled channel count
  (3, or 4 for the ghost-fx gen). __init__ gap logic: gap in (3,4) ->
  nch=gap; gap%4==0 and gap%3!=0 -> 4; else 3.
- CONDUCT PROGRAM decoded: the ghost 4th channel (nch=4) writes its
  note bytes to a GLOBAL pitch base $E943 (Arabia note-handler dis,
  CPX #$15 tail). Real voices play note + $E943(conductor) + transpose
  (dis-verified $EFAF bytes 18 69 00 18 6D 43 E9 18 7D 29 E9 — note
  NO -$18 bias; that byte is CLC). Shipped as ZERO-DELTA-SAFE infra:
  self.e_ghost_track (nch=4 only), _e_conduct timeline built by
  decoding the ghost track in _e_ghost_mode, applied as a RELATIVE
  delta (zero when static -> 3-channel files unchanged). But
  emulation showed Arabia's conductor is STATIC (1 write, value 0), so
  the conduct infra doesn't lift Arabia. Ghost timeline for the
  WRAPPER nch=4 gen is NOT wired (e_ghost_track stays None there).
- ROW GRAMMAR confirmed CORRECT by emulation (bin/_sdi_e_semantics.py,
  abs,Y column-read watch): $8x = sound (column reads use Y=sound,
  persisting across prefix-less rows), $6x = dur (b&$1F+1 ticks x
  tempo — predictions 9/6/21 frames EXACT). tempo_seq=[2,3] averages
  2.5 frames/tick; frame_of_tick maps our exact tick advances to the
  real gaps for every dur byte ($61->5, $65->15, $63->10, $67->20,
  $6B->30 frames).

=== G. DOC/HOUSEKEEPING — commits 31d548e, 25a5d01, 0ffc204 ===
- docs/players/SDI.md brought current to 2026-07-13 (C resolved, E
  wrapper, subtunes, open items rewritten, --subtune).
- CLAUDE.md limitations row updated; then version history (93 lines)
  MOVED OUT to CHANGELOG.md (CLAUDE.md 286 -> 210 lines). Preserved
  v3.6.1/6.2/6.3 (only in CLAUDE.md) by adding to CHANGELOG in
  descending order. Added a "TDZ C64 Knowledge Base (shared MCP)"
  section to CLAUDE.md. "On Version Bump" instruction updated (write
  releases to CHANGELOG not CLAUDE.md).
- docs/SF2.md regenerated (py -3 pyscript/gen_sf2_index.py): SDI now
  336 songs / 336 files.
</work_completed>

<work_remaining>
SDI residuals (priority order):

1. VARIANT E TIMING/RESIDUALS (biggest fidelity lift; median 47.5, 59
   files <50 strict of 114). Grammar, pitch, AND base timing are all
   PROVEN CORRECT — the residual is elsewhere:
   a. ARABIA (69/16): isolated to a SINGLE early over-count. $D404
      gate-rise emulation shows onset COUNT matches (11/11) but our
      notes are a CONSTANT +6 FRAMES LATE after the first (real
      1,6,21,41,46 vs our 0,12,27,47,52). +6 > the +-4 strict window
      -> strict collapses. Our first seq row spans ~12 frames (5
      ticks) where real spans 5 (2 ticks) — ~3 ticks over. NOTE: this
      is NOT the multi-command theory (that FAILED — see attempted).
      NEXT: emulate the real per-tick advance THROUGH the seq-end ->
      track-delay ($C0-$F6) -> next-seq boundary (watch the tick
      counter cell, not just $EEE1 reads); the ~3-tick over-count is
      a rest-row and/or $C3 track-delay being double-applied.
      Zap/Xard/Sweeper likely share it.
   b. WRAPPER nch=4 CONDUCT: Afterburner 80/40, Ambient 78/18 — the
      ghost/conduct-channel timeline isn't wired for the wrapper gen
      (e_ghost_track stays None; the gap logic / conduct-track locate
      needs the wrapper's tl/th layout). Wire it -> lifts the 4ch
      wrapper files.
   c. glide-heavy files (strict parks in slides) — needs glide-aware
      strict sampling (shared with C's Magic_Moment class).

2. THE 85 REMAINING locate-NONE FILES (biggest COVERAGE lift):
   - 50 play+3 files, ALSO wrapped (init $1000 = JMP realinit), TWO
     load groups ($1000 x18, $2D80 x18, tail). CAUTION: MIXED — names
     include DMC_Demo, Delta, Commando (possible DMC/Hubbard rips in
     the Gallefoss composer-folder, NOT SDI). TRIAGE per-file FIRST:
     follow the init JMP, run the DMC/Hubbard parsers' locate on them,
     only wrap-crack the genuinely-SDI ones. Not a single clean crack.
   - ~35 more with weird play-init offsets (covers, self-IRQ digi).

3. VARIANT C NICHE (median already 86; low value):
   - Everytime (28/21): twin NOISE voices, mechanism unidentified
     (instr14 walk has no $09 row, args $FF). Trace
     bin/_sdi_c_walk_trace.py Everytime.
   - Ninja_IV (33/33): GATELESS test-click percussion — emu shows
     ZERO gate rises on v1/v2; the siddump onset heuristic counts
     something else. An onset-DEFINITION disagreement, not a decode
     bug (n=12, low value — consider excluding or aligning).
   - Tanks_3000 (dormant-copy image; live $1000 player unrecognized —
     see #2).

4. MULTI-SUBTUNE TAIL: B multi-subtune indexing (Coming_Soon,
   Commercial_Countdown — find the B song table); Tanks_3000's 12
   subtunes (need its live player first, #2/#3); the 11 locate-NONE
   multi-subtune files. ~417 of 671 Gallefoss songs still undecoded.

5. VARIANT V (strict median 22, lowest): its own wfprg walk (drum
   absolutes +32-class, -1 detunes), tempo commands ($Cx global-tempo
   fx recorded not emulated).

6. VARIANT D POCKET: Holy_Josh 65.7 / Max_Mix_1 75.0 (long tracks).

7. SDI STAGE B NATIVE (byte-exact, like MoN/Galway) — NOT STARTED.
   Via the shared MoN engine (step-grid). Gotcha: the C-class note-on
   writes $D404 = $08 TEST bit — mind the gate model.

Backlog (non-SDI): the deenen corpus (40 files, 202 songs — next
player per memory/new-player-priority.md, after Gallefoss); Gray_Matt
(57) + LFT (61) untouched corpora; SM bundle channel; DMC bundle-bound
files. The instrument-table row/column contradiction (item B above)
needs byte verification.
</work_remaining>

<attempted_approaches>
DO NOT RE-TREAD (all corpus-tested this session):

- E "MULTIPLE LEADING COMMANDS PER ROW" (loop $5F + $80-$BF prefix
  consumption in _play_seq_e): REGRESSED the whole E class (Arabia
  69->16, Zap/Xard/Sweeper/Evil_Within down). Reverted clean. LESSON:
  seq $00 DOES end correctly at the $00 byte — the trailing bytes are
  the NEXT seq's contiguous data, NOT skipped rows.

- E "-$18 pitch bias" / "2x dur bug" / "timing drift": WRONG, both
  arithmetic/dis slips. The $EFB6 byte is CLC not SBC #$18; the
  "2x dur" was dividing frame-gaps by 5 when [2,3] averages 2.5. E
  timing is CORRECT (verified byte-exact). Do not re-open E timing as
  the cause of Arabia — it's the early track-delay over-count.

- E "spurious tempo locate": half-wrong. The tempo_seq extraction
  reads addresses in the track-ptr region for some gens, BUT the
  [2,3] it produced for Arabia is actually CORRECT (2.5 avg matches).

- C "onset pitch from arg[start] blindly" (pre-session): regressed
  Bahbar — but that was the STRIDE BUG, not walk phase (now fixed).

- V tempo emulation via naive tick->call map: lost the A/B to flat
  fpt (pre-session, still true).

- Treating 0.0-on-both-metrics as a decode bug: FALSE LOCATE until
  operands verified (PATTERNS.md D2). Plus the new dormant-copy
  variant (Tanks_3000): matched + non-zero but WRONG player.

- Selecting E/V timing by windowed onsets: picks wrong mappers —
  select by STRICT agreement.

- Flow-dis alone for state semantics: misses paths behind unfollowed
  dispatch; complement with raw-binary greps + EMULATION (the
  bin/_sdi_e_semantics.py write-watch harness caught a swapped-branch
  grammar hypothesis BEFORE it shipped).

- Plus all v3.18/19 entries (vacuous tolerances, freerun pulse streams
  on pulse_tie, rounded-second sweep windows, editing builders
  mid-run).
</attempted_approaches>

<critical_context>
FILES:
- sidm2/sdi_parser.py: the parser. SDIModule(d, la, subtune=0).
  locate() dispatch order A -> C -> V -> D -> E -> B (V BEFORE D is
  load-bearing). E branch now accepts classic ($15) OR wrapper
  (_sdi_e_wrapper_init) init. instr_pitch(): A row-1, C the walk model
  (c_pitch_model), D _d_walk_pitch, E row-0 f[z0]. _play_seq_c does
  note-runs + roll expansion. events() resets _c_gate/_c_regate_cache/
  _e_conduct per call (the validator calls events() multiple times for
  A/B model selection — state MUST reset).
- bin/sdi_to_sf2.py: Stage A converter. --subtune N, --c-steady.
  Duplicate-subtune guard.
- bin/_sdi_sweep.py: the dual-metric validator (windowed 0..+37 /
  strict delta==0, samples fr+{0,2,3,5}). E/V/C calibrate timing/model
  per file by STRICT agreement. _score() is the shared scorer.
- SCRATCH TOOLS (gitignored bin/_*.py, ON DISK): _sdi_c_walk_trace.py
  (py65 PC-breakpoint walk tracer — the workhorse; adapts to E),
  _sdi_e_semantics.py (E write-watch + row-byte harness),
  _sdi_c_resweep.py / _sdi_e_resweep.py (variant-filtered corpus
  sweeps -> out/_sdi_*_resweep*.log), _sdi_c_delta_hist.py (D1).

METHOD LESSONS (this session's throughline):
- VERIFY DISASSEMBLY BRANCH TARGETS BY EMULATION before editing a
  parser — the E grammar is subtle; wrong structural guesses regress
  all 114 files. Three wrong hypotheses were caught by emulation/
  corpus-diff before shipping; one arithmetic slip was caught and a
  correction committed (integrity).
- Corpus-gate EVERY decoder change; report windowed AND strict; a
  median drop can be a composition effect (harder files added), not a
  regression — check the overlap files (2_Young/Kirby) are unchanged.

GROUND TRUTH: the authors' SDI 2.1 source is
bin/SIDDuzz/extracted/sdi21-n49.asm (c1541+petcat at /c/winvice/bin/).
But it does NOT match every rip generation (feature-flag assembly) —
trace beats source.

TDZ KB: mcp__tdz-c64-knowledge (shared, cross-project). Cards are
add_document-only (no in-place edit); write to
~/.tdz-c64-knowledge/temp/ then ingest. Schema + gotchas in
memory/tdz-c64-knowledge-base.md. CLAUDE.md now has a usage section.

CORPUS NUMBERS: Gallefoss = 473 files / 671 songs. Located 312
(A 50, C 80, E 115, B 43, D 18, V 6), NONE 85 + off-other 76.
out/sdi_sf2 = 336 SF2s (subtune 0 + 5 E extras). Strict medians:
A 98.3, D 100, C 86.0, B 74.8, E 47.5, V 21.8.

MEMORY: memory/gallefoss-sdi-player.md (the full SDI trail, updated),
memory/tdz-c64-knowledge-base.md (KB), MEMORY.md index.
</critical_context>

<current_state>
- Repo: master @ 25a5d01, PUSHED to origin. Tree clean except
  intentional untracked (SID/ corpora, bin/SIDDuzz, bin/LFT, out/,
  archive/, scratch bin/_*.py). Version constant 3.20.0 (NO bump this
  session — all work unreleased; a v3.21.0 bump could capture the C
  decode + wrapper crack + subtunes when desired).
- 1537 tests green (full suite run before the last push).
- SDI Stage A: 336 SF2s in out/sdi_sf2/ (untracked build output),
  indexed in docs/SF2.md. 0 conversion failures on located files.
- All docs current to 2026-07-13 (SDI.md, CLAUDE.md, CHANGELOG.md,
  PATTERNS.md, SF2.md). CLAUDE.md compacted (version history ->
  CHANGELOG.md; TDZ KB usage section added).
- 21 SIDM2 documents live in the shared TDZ KB.
- NEXT (user's call): the E timing residual (Arabia +6 early-delay,
  the highest-confidence fidelity fix), OR the 85 locate-NONE files
  (biggest coverage, but the play+3 cluster needs mixed-player
  triage first), OR SDI Stage B native, OR the next player (deenen).
- No open blockers. No temporary workarounds in place. The failed
  E multi-command experiment was reverted clean.
</current_state>
