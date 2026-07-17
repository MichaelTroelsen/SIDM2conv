<original_task>
Standing mission: any SID -> SF2 at 99% fidelity + 100% editable.
Session 2026-07-17. Entry: "read what next and continue" -> picked up the
prior handoff's recommended next step (Zamzara's unexplained pitch 25%).
Later, at a genuine fork, the user was asked and chose:
**"Implement the arp/slide engine"** (over relaxing a stale guard, or moving
to mon_parser LOCATE) -- i.e. accuracy over speed, make Constant_Runner a
genuine win rather than a metric-passing one. That is the live task.

STANDING RULES (all still live): accuracy over speed; never ship lossy
silently; verify by EMULATION before rewriting a parser; a fidelity claim
must never outrun its evidence; NEVER run pyscript/sf2_open_in_editor.py
unless asked; corpus-gate every decoder change; read your own tool's output
before trusting it.
</original_task>

<work_completed>
Repo: master. **6 new commits**, version UNCHANGED at 3.21.0 (bug-fix/RE
work, not a release). Tests **1561 passed / 7 skipped / 2 xfailed** verified
after every single commit -- zero regressions throughout.

  0e1c823  Zamzara decode byte-exact (engine-check 100/100/100)
  32a5afd  Zamzara freq tables were byte-swapped -> 100/100, 6th clean win
  623f4e3  verify EVERY located file's freq table order (not just Zamzara)
  7e6a594  the "voice1 arpeggio" is PERCUSSION - RE'd, located, decoded
  a441055  emit the percussion/wave streams as real Driver 11 wave rows

**Deenen corpus: 10/19 located, 5 -> 6 CLEAN WINS.** Zamzara is the new one
(onset 100.0 / pitch 100.0). The 6: Ding, B_A_T, LotR, After_the_War,
Zamzara (all exactly 100/100) + Astro (77.4/91.5).

=== ZAMZARA: 6 bugs, 18.8% -> byte-exact -> 6th clean win ===
1. Orderlist high-byte grammar was the WRONG DIALECT. It shares
   Constant_Runner's shallow pat_thr==$40/ff_mode=='restart' signature, so it
   was routed through tel's 3-tier grammar. Disassembly ($BE3C-$BE56) shows
   only TWO tiers, no $60 branch: $80+ (fall-through) = AND #$1F ->
   note-transpose; $40-$7F (BCC target) = AND #$3F -> repeat count. A first
   attempt got the branch DIRECTION backwards -- caught by a live register
   trace ($e2,x=12 from byte $8C, $fb,x=3 from byte $43) before shipping.
   Routed via a new `zclass` local (if zclass / elif tel / else).
2/3. _parse_row_zamzara's duration path: a $FD interrupting duration
   accumulation needs the SAME full 3-byte consumption as a top-level $FD;
   and accumulation is NOT an unbounded loop (hardware allows exactly ONE
   inline step; a third $80+ byte re-enters $BE91 -- not modelled).
4. An unmodelled post-note "peek tail" ($BF9B-$BFA9): every note-forming path
   does an unconditional INC $e9,X then peeks for $FF. Not $FF -> cursor
   stays; IS $FF -> hardware resets to 0 THAT SAME FRAME. Slide-terminated
   notes leave $e9,x one byte AHEAD of the note's read position (the
   DEY-refetch dance); other paths stay in lockstep -> different offsets.
   Two hand-traced guesses (universal +1, then +2) each BROKE the
   previously-100% voice1/voice2 before a live per-voice row-entry trace
   (watching $e9,x at every $BE7D) revealed the real shape.
5. groove_rate() tie-broke toward a harmonic alias: R=2.0 and R=3.0 both
   scored 10 hits but 2.0 emitted 21 candidates to 3.0's 10. `if tot >
   best[0]` kept the first on a tie. Now breaks ties toward FEWER candidates.
   Generic subsystem -- verified zero change to all clean wins.
6. **THE REAL PITCH KILLER: the freq tables were BYTE-SWAPPED.**
   DeenenLocate pairs them by ADDRESS ORDER (lower = FREQ_LO, since
   hi-lo==$5F on the Ding class). Zamzara reverses it: $C3EE is HI, $C44D is
   LO. Every computed frequency was byte-swapped (note 60 -> $8623=34339 vs
   the real $2386=9094). Proven 3 independent ways: the SID write itself
   ($C3CE LDA $c6,x/STA $d400,y vs $C3D3 LDA $ef,x/STA $d401,y, while note-
   formation loads $c44d,y->$c6,x and $c3ee,y->$ef,x); the slide engine's
   16-bit arithmetic at $C1F0; and real siddump output.
   Fix: `_fix_freq_table_order()` decides from the SID write, acts only on
   positive evidence, abstains otherwise.

   ⚠️ **I FIRST MISDIAGNOSED THIS AS "an unmodelled portamento" -- WRONG, and
   retracted in 32a5afd's message.** The glide is real but happens AFTER the
   onset; the metric samples at onset+0..2 where the freq is exactly the
   note's table value. Reasoning from a real observation to a wrong cause.

   ⚠️⚠️ **WHY IT HID: deenen_engine_check.py read 100/100/100 on a file whose
   EVERY EMITTED FREQUENCY WAS WRONG.** It watches the note-INDEX store; the
   corruption is downstream in index->frequency. **A ground-truth tool
   certifies only the quantity it actually watches.** Its own docstring says
   "validates NOTES, not timing/timbre/effects". LESSON: note-exact decode +
   a pitch metric that still disagrees => suspect index->frequency BEFORE
   inventing an unmodelled effect.

Then 623f4e3 generalized the detector to the second shadow shape (`LDA
abs,X`, the Ding class -- e.g. LDA $1086,x/CLC/STA $d400,y) so **ALL 10
located files now come back positively VERIFIED, zero abstentions**, Zamzara
the only one rewritten. Freq order is now confirmed from code everywhere,
not assumed.

=== THE "ARPEGGIO" IS PERCUSSION (the task the user chose) ===
**RETRACTS this project's 2-session-old "Constant_Runner voice1 has an
unmodelled ARPEGGIO" diagnosis.** The $1723 wave engine has 2 stream modes
selected by the stream HEADER's bit7. The old note read the bit7-CLEAR
branch (relative semitone + base note) and assumed that was the path taken.
It isn't: instr 1/2/6 all have header bit7 SET -> `$1765 BIT $d0 / BMI ->
STA $75,x / STA $fb,x` = the byte goes to BOTH freq hi and lo, raw freq =
`b<<8|b`, INDEPENDENT of the played note. A fixed descending click. A DRUM.
  Proof: instr 1's stream `3C 09 05 04 03 02 38` -> semitones
  **[69,37,26,23,18,11,68]** = byte-for-byte the very sweep the old notes
  recorded as the mystery. The old note quotes the right numbers while
  drawing the wrong conclusion. Confirmed LIVE (watching $fb,x/$75,x on
  voice1): 15420(69) 2313(37) 1285(26) 1028(23) 771(18) 514(11) 14392(68),
  then hold. **LESSON: read the SELECTOR, not the first branch you find.**

SHIPPED (7e6a594): `_locate_wave_engine()` -- relocation-safe, everything
from operands (both zp shadows mapped back to instrument-record offsets via
their `LDA instr+k,Y / STA zp` sites; CR: instr[4]=enable bit3, instr[7] high
nibble = arp-table index; `bias` VARIES per file: $0a CR / $19 After_the_War
/ $11 Astro / $1e Mantalos / $14 Mr_Heli).
  Signature gotcha: bare `4A 4A 4A 4A A8 88 B9` = 3 hits/file. Anchor the
  WHOLE dispatcher incl. the `18 69 imm A8` tail -> exactly 1 hit on rips
  that have it (After_the_War, Astro, Constant_Runner, Eye_to_Eye, Mantalos,
  Mr_Heli), 0 on those that don't (B_A_T, Ding, LotR). **Zamzara has a
  wave/arp engine too but a DIFFERENT one** (its row grammar's $C4F0/$C502).
And `wave_program(i)` -- full byte grammar: header (bit7 raw, (>>4)&7
frames/step-1, &$0F loop target), $FF loop -> (header&$0F)+1, $FE
hold-forever (sustain/terminator), raw vs absolute($7F+) vs relative steps.
CR: 1/2/6 percussion; **instr 0 is the ONLY note-mode one** (absolute $81
then relative +5..+0 = a descending slide into pitch) -- so the relative path
IS real, just not what 1/2/6 use.

SHIPPED (a441055): `bin/deenen_to_sf2.py::_wave_program()` emits them as real
Driver 11 wave rows, replacing the 2-row held-waveform stub. Follows
**fc_to_sf2.py's drum path** (closest precedent -- same problem, solved for
Future Composer) + kimmel_to_sf2. Encoding confirmed from TWO shipping
builders, not just the spec: col1 $80-$DF = absolute semitone, $01-$7D =
relative, col0 $7F = jump.
  Nice corroboration: fc_to_sf2's drum comment says FC "plays the note's OWN
  pitch on the trigger frame, then the drum table from frame 1" -> leads with
  one root row. EXACTLY what the live CR trace shows (frame 1 = base note
  568, drum from frame 2). Two unrelated engines, same shape.
  Verified emission: instr 1 -> root, ABS 69/37/26/23/18/11/68, self-jump
  (hold). instr 6 -> 23 steps, jump back to row 39 = its step 5 (loop=5).
</work_completed>

<work_remaining>
## THE LIVE THREAD (the user's chosen task, partially done)
1. ⚠️ **AUDIO-VALIDATE THE WAVE EMISSION -- THE #1 NEXT STEP.** All files
   BUILD and tests pass, but **"builds" is not "sounds right"**.
   `bin/deenen_validate.py` scores the DECODER (onset+pitch), NOT the emitted
   SF2 -- it is structurally BLIND to a441055 in both directions. The wave
   rows are UNVALIDATED against real audio. Do not claim the percussion is
   reproduced until this runs.
   HOW: build the SF2, wrap as PSID (`fidelity_common.psid_wrap`), trace with
   the zig64 tracer, diff per-frame freq vs the original. Or reuse the
   instrumented-SF2II approach in `bin/sf2ii_vs_real.py` from the Galway arc
   (see [[galway-sf2ii-listen-tool]]).
   **TRACE After_the_War FIRST**: it is an existing 100/100 clean win that
   HAS this engine, so its SF2 just changed and NO current metric would catch
   a regression there. That is the live risk from a441055.
2. **Zamzara's $FD portamento** -- the other half of the chosen task, not
   started. The engine is at `$C166-$C220`: `$c3`=speed, `$c4c3`=target
   (`ADC $e2,x`-transposed), `$d5,x`=enable flag, a self-modified SEC/SBC vs
   CLC/ADC direction patch at `$C1B2-$C1BB`, and a 16-bit divide at
   `$C1C8-$C1EF`. Real freq observed gliding 9094->7624 over 24 frames.
   NOT metric-visible (onset-only), so it needs the same audio validation.
   Driver 11 has a T0 slide command (XXYY = 16-bit speed) -- Kimmel already
   ports freq-slide via T0 (see [[kimmel-player]]), so there is a template.
3. **Constant_Runner's plausible() guard** -- still refusing, deliberately.
   Its premise is ALREADY provably stale (rows proven identical in d83e7f0;
   the 35.6% it cites was the metric bug fixed in 2dccee7 -> now 97.7).
   Once (1) is validated, relax it BECAUSE the effect is genuinely modelled
   -- never because relaxing it scores a win. Would make CR the 7th win
   (onset 100.0 / pitch 97.7).

## OPEN, NOT TOUCHED
4. **Mantalos** -- 0%/0%/0% vs the player's own notes. Confirmed to take the
   Ding path (`_is_zamzara_row_class()` False, `gram.ff_mode=='seg'`), so
   none of this session's fixes touch it. Its 924322d orderlist fix stands;
   the remaining brokenness is separate and undiagnosed.
5. **mon_parser LOCATE extension** -- the prior handoff calls this a BIGGER
   prize than the Deenen decoder work: 12 $40-class Tel rips already decode
   but fail file detection (`mon_validate` 0/0 = vacuous). Also unlocks MoN
   native Stage B (100% byte-exact on Hawkeye) vs a Stage A transpile.
6. Astro/Mr_Heli's ZP `$88,X` nested-loop orderlist variant. The 9
   not-located files. `Zamzara_v1` (`no dispatch` -- more basic).
   Smooth_Criminal (matches `_is_zamzara_row_class`, not fully located; will
   auto-route once located -- check it for the self-modify orderlist too).
7. Older, still open: the DEGENERATE-value bug (`score_pct` can't catch
   tot=1000/ONE distinct value); `pyscript/trace_comparator.py:291,341`
   reachable vacuous-100; `bin/hubbard_validate.py` V1-only silently wrong on
   V2; SM's 99.23% not reproducible from a fresh clone; Galway/MoN/ROMUZAK/FC
   matrix rows never audited by the falsifier.
</work_remaining>

<attempted_approaches>
**A frame-pitch fidelity probe -- INVALID, discarded, do NOT redo it.** To
settle whether Zamzara-vs-CR were being judged consistently, I wrote a
per-frame (sustain-inclusive) pitch metric. It read **Ding voice0 at 5.3%**
-- while Ding is a verified 100/100 clean win. That is not Ding being broken;
these engines have per-frame vibrato/porta that Stage A never models, so the
probe measured "does the engine modulate pitch" (yes) rather than "is the
decode right". The project's onset-only metric is chosen deliberately for
exactly this reason. I discarded the numbers rather than report them.

**Hand-tracing 6502 control flow instead of probing it -- cost 3 wrong
attempts.** On Zamzara's peek-tail I guessed a universal `+1`, then a
universal `+2`; each BROKE voices that were already at 100%. Only a live
per-voice register trace ($e9,x at every $BE7D dispatch, across ALL three
voices -- not just voice0) revealed the real asymmetry. The standing
"verify by emulation before rewriting a parser" rule earned its keep again.

**Reading a disassembled branch without checking its selector.** The whole
"voice1 arpeggio" error: the relative-semitone branch IS real code and I
found it, but instr 1/2/6 never take it -- the header bit7 selects the raw
path instead. Read the SELECTOR, not the first branch you find.

**/tmp on this Windows setup** -- still unreliable (resolves unpredictably,
and a stray dis.py there shadows the stdlib `dis`). Use the session
scratchpad.
</attempted_approaches>

<critical_context>
## THE LESSON OF THIS SESSION
**A ground-truth tool certifies ONLY the quantity it actually watches.**
`deenen_engine_check.py` reported "the decoder reproduces the player
EXACTLY" (100/100/100) on Zamzara while every frequency it emitted was
byte-swapped -- because it watches note INDICES and the corruption was
downstream. I over-read its verdict as "the decode is right". Its docstring
even says "validates NOTES, not timing/timbre/effects".
**Corollary: note-exact decode + a pitch metric that still disagrees =>
suspect index->frequency BEFORE inventing an unmodelled effect.** I invented
one (portamento) and was wrong.

## THE SAME BUG CLASS, A NEW SHAPE EVERY TIME
A locate/metric silently substitutes a PLAUSIBLE-LOOKING WRONG VALUE.
This session added three more shapes: freq tables paired by ADDRESS ORDER
(right for Ding, backwards for Zamzara); groove_rate tie-breaking to a
harmonic ALIAS that scores equal on hits but emits 2x the candidates; and a
`plausible()` guard whose justification quietly went stale under it (both its
cited facts became false without the guard changing).

## PER-FILE, ALWAYS -- NOW SIX INDEPENDENT LAYERS
Deenen varies per file at: orderlist grammar, row grammar, orderlist-pointer
resolution (direct vs self-modifying code), freq-table byte order,
wave/percussion engine (present/absent AND which shape -- Zamzara's is a
different one entirely), and groove rate. **Assume nothing carries across
files without re-verifying.**

## KEY FILES
- `sidm2/deenen_parser.py` -- `_fix_selfmod_ord_ptr`, `_fix_freq_table_order`
  (NEW), `_locate_wave_engine` + `wave_program` (NEW), `_parse_row_zamzara`,
  `decode_voice` (zclass/tel/Ding routing), `groove_rate`, `plausible`.
- `bin/deenen_to_sf2.py` -- `_wave_program()` (NEW) emits the wave rows.
- `bin/deenen_engine_check.py` -- ground truth for NOTES ONLY (see lesson).
- `bin/deenen_validate.py` -- scores the DECODER, not the SF2. Cannot see
  a441055 at all.
- `bin/fc_to_sf2.py` -- the drum->absolute-note-wave-row TEMPLATE.
- `bin/kimmel_to_sf2.py` -- `_wave_program` (arp) + T0 freq-slide template.
- Memory: `memory/deenen-player.md` -- READ FIRST. Now carries the retraction
  boxes, the corrected PERCUSSION ENGINE map (exact addresses/flags), and the
  emission's validation gap.

## ENVIRONMENT
- Tests: `py -3 -m pytest pyscript/ -q` -> **1561/7/2** (~3 min). Confirmed
  after every commit this session.
- Corpus: `py -3 bin/deenen_validate.py` (~2-3 min) -> 10/19, 6 clean wins.
- Ground truth: `py -3 bin/deenen_engine_check.py [names]` (notes only).
- py65 MPU + a minimal Mem wrapper is the standard probe pattern.
- Nothing pushed to origin (local only, as prior sessions).
</critical_context>

<current_state>
- **v3.21.0 unchanged** (correctly -- bug-fix/RE work, no release milestone).
- **6 commits on master, none pushed.** Working tree clean except the same
  pre-existing untracked corpora/scratch (SID/Gallefoss_Glenn/, SID/Jeff/,
  SID/Red_kommel_jeroen/, SID_INVENTORY.md, archive/cleanup_2026-07-09/,
  bin/LFT/, bin/SIDDuzz/, bin/_kimmel_work/) plus a local-only
  `.claude/settings.local.json` diff deliberately left uncommitted.
- **Tests 1561/7/2.** No known failures.
- **Deenen: 10/19 located, 6 clean wins** (was 5 at session start, 4 in the
  stale docs). Zamzara is new at 100.0/100.0.
- **Docs refreshed**: DEENEN.md's fidelity table (was stale at 4 wins, never
  updated when Astro became the 5th), + the freq-table-order trap documented
  at the engine-map source; ACCURACY_MATRIX.md + CLAUDE.md rows now say 6.
- **The one un-validated thing**: a441055's wave rows. They build; they are
  not audio-checked. After_the_War is the regression risk.
- **NEXT SESSION SHOULD START WITH**: `memory/deenen-player.md` (the
  retraction boxes + PERCUSSION ENGINE map), then item (1) above -- trace a
  built SF2 vs the original, After_the_War first. That closes the loop on the
  user's chosen task and is the only thing standing between "emitted" and
  "reproduced".
</current_state>
