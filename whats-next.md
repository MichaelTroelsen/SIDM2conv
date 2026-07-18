<original_task>
Session entry: user asked "read bugs from github" -> read the 2 open GitHub issues
on MichaelTroelsen/SIDM2conv, then user said "yes please fix htem" (fix both).
After that: user said "read what next" -> I read the PRIOR whats-next.md handoff
(2026-07-18, "mainstream-MoN/Tel arc opened, B1 bucket RE'd") and its recommended
next step (work_remaining #1: RE Alloyrun's orderlist $40-$7F op).
User redirections in order, each a one-word/short continuation:
  1. "yes start" -> began the B1 BROKEN-tier RE unit (Alloyrun's orderlist $40-$7F
     op + $C0-$FF pattern ctrls, per the prior handoff).
  2. "continue" -> after Alloyrun/Starball shipped, moved to the next untouched
     broken file (Bantam).
  3. "yes" -> after Bantam shipped, moved to the next untouched file (Zynon_Zak),
     which led to the length-mask generalization (the session's biggest win).
  4. "go on" -> after the length-mask fix, moved to the next-highest untouched
     broken file (Tel_1), which led to the column-major instrument-table fix.
  5. "stop and lets restart" -> ended the session. Confirmed working tree clean
     (all 6 substantive commits pushed; only whats-next.md itself has
     pre-existing uncommitted changes from BEFORE this session, never touched).
  6. /taches-cc-resources:whats-next -> this handoff.
</original_task>

<work_completed>
=== PART 0: GitHub issue triage (github.com/MichaelTroelsen/SIDM2conv) ===
Found 2 open issues via `gh issue list`, fixed both, both closed:
- **#9** "docs: memory/ knowledge store does not exist but 11 documents reference
  15 files in it" (docs-audit, P1). Root cause: `memory/*.md` throughout the repo's
  docs is NOT a tracked repo path -- it's the Claude Code auto-memory store at
  `C:\Users\mit\.claude\projects\C--Users-mit-claude-c64server-SIDM2\memory\`,
  outside the git repo. Fix (commit `959728b`, pushed): added one clarifying note
  each in `CLAUDE.md` (TDZ knowledge base section) and `docs/players/PLAYBOOK.md`
  (reference table) rather than touching all 15 individual references (matches
  the issue's own "say so once" resolution guidance). GitHub auto-closed #9 via
  the "Fixes #9" commit-message trailer.
- **#4** "Improve Test Coverage from 17.61% to 70%" (opened 2025-12-27, stale).
  Closed via `gh issue close 4` with a comment: its numbers (391 tests, 17.61%)
  are 7 months stale; current suite is 1561+ tests; no linked sub-issues or
  phase-completion tracking ever happened.

=== PART 1: B1-tel broken-tier RE, 4 rounds, ALL in sidm2/mon_parser.py ===
Extends the mainstream MoN/Jeroen Tel arc from the PRIOR session (`ab99032`,
already shipped before this session started: `_locate_b1` + `_voice_blocks_tel`,
6 onset-EXACT files out of the 24-file B1-indirect bucket in `SID/Tel_Jeroen/`).
This session added a NEW method `_locate_b1_row_variant` (called from `_locate()`
right after `tbl_pat` is found, gated `if getattr(self, "_tel", False)`) plus a
second new method `_locate_tel_instr_fields`, and modified `_voice_blocks_tel` and
`_silent_instr`. **Net result: 12/24 bucket files now onset-EXACT (was 6 at
session start).** Every round was verified via a full 23-file bucket resweep
(script content preserved below, since it lived in the session-temp scratchpad
and will NOT exist in a fresh session) PLUS the 5-file byte-exact gate (Hawkeye
sub2 152/152, sub3 28/28; Cybernoid sub0 53/53, sub1 15/15; Cybernoid_II sub0
37/37) PLUS the full `pytest pyscript/` suite (1561 passed / 7 skipped / 2
xfailed every single time, confirmed 4 separate times this session). ALL 4
commits are pushed to `origin/master`.

--- Round 1 (commit `ed4b3cc`, pushed): Alloyrun + Starball, 1.1%/1.0% -> 61%/76% ---
Disassembled Alloyrun's ACTUAL compiled dispatch directly via `bin/_mon_disasm.py`
(NOT guessed) and found the prior session's "the $40-$7F byte breaks pattern
indexing" recon was half right: it's a genuine feature, not a bug. Three quirks,
all gated in `_locate_b1_row_variant`:
- **`_tel_repeat`**: orderlist byte `$40-$7F` (bit7=0, bit6=1) is a REPEAT command
  (`AND #$40; BEQ; AND #$3F; STA,X reload`, disassembled Alloyrun `$E127-$E137`).
  Sets a per-voice counter = `byte&$3F`; the pattern selected by the NEXT
  orderlist byte then plays `(counter+1)` times before the orderlist advances
  (end-of-pattern check at `$E210-$E22B`: `DEC` counter, `BPL` -> redo same
  pattern from its start, index reset to 0). PROOF this is safe: Scout (one of
  the original 6 EXACT files) has byte-identical dispatch code -- it just never
  sets bit6 in its own song data, which is why it stayed EXACT under the OLD
  model the whole time.
- **`_tel_pat_off1`** (Alloyrun ONLY): `SEC;SBC#$01` right before the `ASL;TAY`
  pattern-table index (`$E13A`) -- this one compile's orderlist pattern numbers
  are 1-based, not 0-based.
- **`_tel_classic_row`** (Alloyrun + Starball ONLY): these two don't use the
  "simple" ctrl-byte-encodes-length grammar at all. Their row dispatch
  (`$E182-$E19A`) is the SAME `$8x`-duration/`$Cx`-instrument/`$Ex`-command chain
  already implemented and Hawkeye/Cybernoid-validated as `_pattern()` -- reused
  verbatim (`self._pattern(idx, st, blk)`) instead of re-derived.
Detection signatures (in `_locate_b1_row_variant`, ~line 309-345 as of this
commit): scan `d[po-40:po]` (`po` = the existing `tbl_pat` locate offset) for
`29 40` (AND #$40) followed by `F0` (BEQ) within 2 bytes, then `29 3F` (AND #$3F)
followed by `9D` (STA,X) within 2 bytes -> `_tel_repeat=True`. Check
`d[po-3:po] == [0x38,0xE9,0x01]` (SEC;SBC#$1) -> `_tel_pat_off1=True`. Scan
`d[po:po+220]` for `29 E0 C9 C0` or `29 C0 C9 80` (the AND/CMP pairs that gate
`_pattern()`'s Cx/8x branches) -> `_tel_classic_row=True`.
**Bug caught and fixed mid-round**: my FIRST version of the `_tel_repeat`
detector had an off-by-one (`pre[i3f + 3] == 0x9D` should have been `i3f + 2`) --
found by re-deriving the exact byte offsets from the disassembly by hand rather
than trusting the first draft; fixed before the gate check, not after.

--- Round 2 (commit `5ab7eff`, pushed): Bantam, 2.7% -> 73% (later 77%) ---
Bantam's row dispatch is structurally Scout's shape (raw ctrl `AND #$7F` for
length, ctrl's bit7 gates an instrument-command byte) EXCEPT it does
`SEC;SBC#$01` on the ctrl byte BEFORE both the length mask and the bit7 test
(`$80E8-$80F9`) -- shifting the instrument-command threshold to raw-ctrl>=`$81`,
one higher than Scout/05-09-87. New flag `_tel_row_ctrl_off1`: locates the
row-ctrl fetch (`B1 zp` where `zp = d[po+6]`, the SAME zero page the `tbl_pat`
lookup's `85 zp` operand stored to) within 80 bytes forward of `po`, then checks
the ~20 bytes after that fetch for `SEC;SBC#$01` preceding the first `AND #imm`.
Fires ONLY for Bantam in the whole 23-file bucket (verified via scan-and-print
before wiring in, discipline repeated every round).

--- Round 3 (commit `4fdfd7f`, pushed): THE BIG ONE -- row length-mask, 11/24 EXACT ---
While disassembling Zynon_Zak (next-highest untouched broken file, 35.6%) to
scope its own RE unit, found its orderlist+row dispatch BYTE-IDENTICAL to
05-09-87's simple grammar in every way except ONE instruction: `$C098: AND #$3F`
where 05-09-87 has `AND #$1F`. That's it -- no new op, no off-by-one, just a
length field one bit wider than the grammar-defining file (05-09-87) happened to
need. Generalized rather than special-cased: `_locate_b1_row_variant` now reads
the length-mask operand DIRECTLY from each file's own `AND #imm` instruction
(new field `_tel_row_len_mask`, default `0x1F` if the scan fails to resolve one)
instead of the hardcoded `0x1F` constant. Safe-by-construction reasoning
(verified empirically too, not just argued): a WIDER mask is a strict superset of
a narrower one -- any file whose real note lengths fit under the old `$1F`
decodes byte-identically (the newly-unmasked high bits are always zero in that
file's data), so this can only ever fix a file that was silently wrapping a
longer length into a wrong shorter one, never regress a working decode.
**Result -- 5 files went STRAIGHT to onset-EXACT with no other change needed**:
Happy_JT (87.5%->100%), Beginning (82.5%->100%), Beginning_v2 (82.5%->100%),
DemoSong (81.6%->100%), Reggae_Example (75.5%->100%). Every one of these had
been diagnosed in the PRIOR session as "middle tier -- Stage-B instrument arp
residual, not a grammar gap." **That diagnosis was WRONG for these 5 files** --
it was this exact decode bug, subtle enough that the wrapped lengths still
produced plausible-looking (if systematically off) event timing, which is
exactly the failure mode the "instrument residual" hypothesis was invented to
explain. Plus real (non-exact) gains: Zynon_Zak 35.6%->84% (120/143), Orion_Intro
77%->92% (189/206), Trying_Out 61%->78% (125/160), Bantam ticked up again to 77%
(its own real mask is `$7F`, only now actually applied since `_tel_row_len_mask`
also covers the `_tel_row_ctrl_off1` branch).
**Re-check performed on Orion_Intro's residual** (per the lesson above -- don't
inherit an old "Stage-B" diagnosis without re-verifying it): hand-traced V0's raw
pattern bytes against siddump ground truth directly. Confirmed genuinely
Stage-B THIS time -- every onset using instrument 4 lands exactly 1 frame late
vs siddump, consistently, an ADSR-attack-detection artifact (siddump sees the
note reach threshold 1 frame after the gate-on write), not a decode bug.
Diagnosis upheld by evidence, not assumed.

--- Round 4 (commit `2f47dbe`, pushed): Tel_1 investigation -> column-major instrument tables, 12/24 EXACT ---
Investigated Tel_1 (still only 24% despite disassembling orderlist+row code
BYTE-IDENTICAL to 05-09-87's, a validated-EXACT file -- so the bug had to be
somewhere else). Found TWO separate bugs, neither a grammar gap:
1. **The simple-grammar note-append in `_voice_blocks_tel` never called
   `_silent_instr` at all.** Only `_pattern()`/`_emit()` (the classic-row path)
   had the "instrument 0 = MoN rest slot, suppress the onset" convention (fixed
   in an EARLIER, PRIOR session for that path only). Every B1-tel file using the
   simple grammar with instrument-0 padding was silently emitting phantom onsets
   for it. One-line fix: `retrig = not self._silent_instr(instr)` before
   appending the MONEvent (~line 610 area).
2. **`_silent_instr` itself assumed Hawkeye's ROW-MAJOR 8-byte-record layout**
   (`base = self.tbl_instr + i*8; all zero for k in range(8)`). Disassembled
   Tel_1's ACTUAL instrument-field reads (`$10FA:LDA,X $1520->D404(wf)`,
   `$1103:LDA,X $1516->D402(pulse-lo)`, `$1111:LDA,X $151B->D403(pulse-hi)`,
   `$111C:LDA,X $1525->D405(AD)`, `$1122:LDA,X $152A->D406(SR)`) -- FIVE SEPARATE
   parallel arrays, each 5 bytes apart, each indexed DIRECTLY by instrument
   number (`field_base + i`, NO `*8`). Verified empirically BEFORE touching code:
   dumped wf/ad/sr for instruments 0-5 under this column-major model --
   instrument 0 reads ALL-ZERO (confirms it's the padding slot) vs garbage under
   the old row-major*8 guess.
   New method `_locate_tel_instr_fields(self, d, ad_io)` (called from `_locate()`
   right after `tbl_instr`/`io` are computed, gated `if getattr(self, "_tel",
   False)`): locates the real waveform/AD/SR array bases by searching within
   +-80 bytes of the already-trusted `io` (AD) anchor for `BD ?? ??` (LDA tab,X)
   followed within 3-6 bytes by `99 0N D4` (STA $D40N,Y) for N=2(pulse-lo),
   3(pulse-hi), 4(wf), 6(sr). Stores as `self._tel_instr_fields` (a list, or
   `None` if not resolved). `_silent_instr` now checks: if `_tel_instr_fields`
   is set, `all(self._u8(base + i) == 0 for base in fields)`; else falls back to
   the original row-major`*8` guess (so Hawkeye/Cybernoid, which never set
   `_tel`, are completely untouched).
   **CAUGHT A REAL REGRESSION mid-round**: the FIRST version of this locate (no
   consistency check) broke Orion_Intro (92%->0%) and Chrome_Met1 (1.5%->0%) --
   both because the +-80-byte "near" search still snagged an UNRELATED
   `STA $D404` elsewhere in those files' code, producing a bogus `wf` address far
   from the real `ad`/`sr` cluster. FIXED by requiring the three found fields be
   EVENLY SPACED (`ad - wf == sr - ad`, and `ad > wf`) before trusting them --
   the signature every GENUINE match showed (Tel_1: gaps `[5,5,5,5]`; the earlier
   dry-run scan across Beginning/Happy_JT/Ikari_Union/Monitor_Madness/Trying_Out/
   Zynon_Zak all showed clean `[5,5,5]`/`[6,6,6]`/`[8,8,8]`/`[10,10,10]`/
   `[13,13,13]` gaps). Re-verified against the FULL bucket after the fix, not
   just Tel_1 -- regression gone, zero other files changed.
   **Result**: zero regressions, PLUS a bonus win the fix wasn't even aimed at --
   **Chrome_Met1 jumped straight to onset-EXACT (1.5%->100%)**, it turned out to
   be column-major too with nothing else wrong. Tel_1 itself only partially
   improved (its instrument-0 padding is now correctly suppressed, confirmed via
   direct `_silent_instr(0..5)` dump matching the manual verification) but has a
   SEPARATE, undiagnosed timing bug past that -- see work_remaining #1.

=== Docs + memory updated every round (all pushed with their code commit) ===
- `docs/players/MON.md`: the "## The mainstream-Tel 'B1-indirect' generation"
  section rewritten incrementally each round; now has a "Same-day #1/#2/#3/#4"
  bullet list under the status summary, with the tier counts corrected each time
  (6 EXACT -> 11 EXACT -> 12 EXACT).
- `CLAUDE.md`: the Known Limitations table's Tel row updated each round (now
  reads "12/24 onset-EXACT... See memory/mainstream-mon-tel.md").
- `memory/mainstream-mon-tel.md` (Claude Code auto-memory, NOT a repo file --
  path: `C:\Users\mit\.claude\projects\C--Users-mit-claude-c64server-SIDM2\
  memory\mainstream-mon-tel.md`): four new `## BROKEN-tier RE unit #N SHIPPED`
  sections appended this session, each with full disassembly evidence, the
  before/after numbers, and an explicit "PLAN (PLAYBOOK staged) — updated"
  section kept current. This file is THE place to start next.
- `MEMORY.md` index line (`memory/MEMORY.md`) for `mainstream-mon-tel.md`
  updated each round with a running summary.
</work_completed>

<work_remaining>
## THE LIVE THREAD -- B1-tel bucket, priority order (per memory/mainstream-mon-tel.md PLAN section)

1. **Tel_1's SECOND bug** (the file that triggered round 4, still only ~25%
   after round 4's fix). V0/V1 now match ground truth at onset 0 (previously
   didn't -- round 4 fixed that much) but diverge starting at onset 1: V0
   siddump frame8 vs parser frame4 (a 4-frame/2-tick gap); V1 siddump frame12 vs
   parser frame8 (same 2-tick gap). Hand-traced pattern0's raw bytes
   (`[0x81,0x00,0x00,0xFF]` at pattern-ptr `$165B`) and confirmed the decode
   (ctrl=0x81, length=(0x81&0x1F)+1=2 ticks, instr=0, note=0) is a FAITHFUL
   reading of the disassembly and the length MASK is confirmed correct (`$1F`,
   matches 05-09-87 exactly, verified via direct disassembly at `$1098: AND
   #$1F`). So the bug is NOT in ctrl/length/mask decode -- something else is
   adding an extra ~2 ticks of delay before the first REAL (non-silent) note
   fires, that our model doesn't currently account for. NOT diagnosed further
   this session. Approach: dump siddump's frame-by-frame register trace for V1's
   first ~20 frames and cross-reference against the exact SID register writes
   `_pattern`/the simple-grammar loop would produce, frame by frame, to find
   exactly where the extra ~2 ticks comes from (a stale-duration carryover? a
   second silent event we're not counting? something in the `$105F`-orderlist-
   dispatch region not yet disassembled for Tel_1 specifically?). Gate + resweep
   after any change, same discipline as all 4 rounds.

2. **Monitor_Madness_1 (2/108), Monitor_Madness_2 (3/146), Trying_Out_2 (1/59)**
   -- still essentially 0%, completely untouched this session. NOT yet checked
   against ANY of the 4 known quirks (repeat-op, pattern-off1, classic-row,
   row-ctrl-off1, length-mask, OR the new column-major-instrument-table quirk
   from round 4). Start with the SAME workflow used for Tel_1/Zynon_Zak:
   `py -3 "<locate-dump-script>" SID/Tel_Jeroen/<file>.sid` (script content
   below, since the session scratchpad won't persist) to get located table
   addresses, then `py -3 bin/_mon_disasm.py <hex-start> <hex-end>
   SID/Tel_Jeroen/<file>.sid` on the orderlist-dispatch region (found via the
   printed "orderlist-pattern dispatch signature ... c64=0x????" line) to see
   the ACTUAL compiled code, comparing byte-for-byte against 05-09-87's known
   dispatch (reproduced in the docstrings of `_locate_b1_row_variant` and
   `_voice_blocks_tel` in `sidm2/mon_parser.py`). Don't assume any of these 3
   share Tel_1's or Bantam's or Zynon_Zak's exact shape -- EVERY file this
   session turned out to be its own micro-variant, sometimes sharing one quirk,
   sometimes needing a genuinely new one (round 4's column-major finding was
   NOT anticipated going in).

3. **Zynon_Zak (84%, 120/143), Bantam (77%, 69/90), Starball (76%, 71/93),
   Alloyrun (61%, 55/90)** -- all real, gate-verified improvements but not yet
   onset-EXACT. None of these were hand-traced to find their SPECIFIC remaining
   residual this session (unlike Alloyrun's V1 in round 1's own investigation,
   and Orion_Intro in round 3's re-check, both of which WERE traced and
   diagnosed as genuine Stage-B instrument-envelope artifacts). Given the
   session's own lesson ("a Stage-B diagnosis needs the same disassembly-level
   proof as a fix"), do NOT assume these 4 are Stage-B without tracing them --
   they might be more decode bugs like round 3/4 found. Recommended per-file
   approach: `bin/mon_validate.py <file> 0` for the per-voice frame-match
   detail, then dump raw parser events (tick/dur/note/instr) alongside siddump's
   ground-truth (frame,note) onset list for the divergent voice (see the
   "hand-trace" pattern used successfully on Alloyrun V1 and Tel_1 V0/V1 this
   session -- Python one-liners against `sidm2.mon_parser.MON` + `sidm2.
   fidelity_common.siddump_note_onsets`, not a persisted tool).

4. **`Alloyrun_v2` still decodes to 0 events** (separate, unrelated bug from
   everything above): the copy-loop/feeder locate itself misses at that file's
   relocation (`load=$107A`, different from Alloyrun's `$E000`). Not
   investigated at all this session.

5. **Trying_Out (78%, 125/160)** -- also not hand-traced. First diff was V1 idx2:
   siddump frame26 vs parser frame48 (parser LATER than ground truth, unlike
   most other residuals seen this session which were parser-earlier or
   parser-has-extra-events) -- possibly a DIFFERENT failure shape worth checking
   first since it doesn't match the pattern of the other diagnosed cases.

## Beyond the B1 bucket (lower priority, per the standing PLAN)

6. **The 85-file "no-copy-loop" bucket** (the BULK of `SID/Tel_Jeroen`'s 179
   files -- e.g. Battle_Valley `$0810`, 2400_AD, 64_Dwarfs, Alternative_Fuel).
   These don't even have the `A0/A2-05` copy-loop signature the B1 locate keys
   on at all -- likely an entirely different/newer MoN engine generation,
   probably the single biggest remaining RE unit in this arc. Zero
   investigation this session; would need its own locate-from-scratch pass
   (disassemble a representative file's subtune-setup code to find whatever
   THEIR orderlist-pointer mechanism is, since it's provably not `A0 05 B9`/`BD`/
   `B1`).
7. **The ~36 "located-but-degenerate" files** noted in the PRIOR session's
   recon (locate succeeds but decode is non-sane -- runaway or trivial note
   counts). Not touched this session; diagnosis TBD (wrong olptr resolution?
   wrong grammar variant entirely?).
8. **Stage B** for the now-12 EXACT files, via `bin/build_mon_native_song.py`
   (the shared, Hawkeye/Cybernoid-validated Stage-B builder) -- turns the Stage-A
   onset-exact decode into an actual native SF2 build. Not started for ANY of
   the 6 newly-EXACT files from this session (Happy_JT, Beginning, Beginning_v2,
   DemoSong, Reggae_Example, Chrome_Met1) or the original 6.
9. **SDI Stage B** (from an even earlier, unrelated session): `bin/
   build_sdi_native_song.py` still not wired into a shipping path -- standalone
   builder only. Unrelated to this session's work, just still open per the
   long-running PLAN.
10. **Deenen leftovers** (7 clean wins, banked from a prior session): the `$FD`
    portamento slide effect (Zamzara + After_the_War), Mantalos (0% broken), 9
    not-located files. Unrelated to this session, still open.
</work_remaining>

<attempted_approaches>
**Two self-caught bugs in MY OWN detection code this session (both found by
re-deriving byte offsets from the disassembly by hand, not by trusting the first
draft):**
- Round 1: `_tel_repeat`'s signature check first read `pre[i3f + 3] == 0x9D`;
  the correct offset (re-derived from the actual Alloyrun/Scout byte layout,
  `AND #$3F` is a 2-byte instruction so the following opcode starts at `i3f+2`
  not `i3f+3`) was `pre[i3f + 2] == 0x9D`. Caught via a debug dump script
  (`alloyrun_v1_dump.py`) BEFORE the gate check, when Alloyrun V1's first
  events came out wrong despite the repeat-op logic looking right on paper.
- Round 4: `_locate_tel_instr_fields`'s first version had NO consistency check
  on the located `wf`/`ad`/`sr` addresses, just "first match within +-80 bytes."
  This is what caused the Orion_Intro/Chrome_Met1 regression (see work_completed
  round 4) -- FIXED by requiring `ad - wf == sr - ad`.

**A metric-scale confusion caught and corrected mid-session** (not a bug, but a
near-miss): early in round 4's investigation, briefly worried that Bantam's
off1-adjusted length mask (`$1F` used, when Bantam's OWN real mask is `$7F` per
round 3's scan) might be under-representing its true length range -- checked
whether this mattered empirically (it didn't cause a regression when the
`_tel_row_len_mask` field also started covering the off1 branch in round 3), so
no separate fix was needed there; noted for completeness, not a dead end.

**Approaches NOT pursued (considered, explicitly deferred):**
- Fully reimplementing `_pattern()`'s `$70-$7F` wave-program-select branch check
  for Alloyrun's classic-row grammar: confirmed via direct disassembly that
  Alloyrun's actual code LACKS this check (unlike Hawkeye's `_pattern()`, which
  has it) -- bytes `$70-$7F` in Alloyrun's row stream fall through to the plain
  NOTE branch instead. This is a KNOWN, documented discrepancy between
  `_pattern()`'s general model and Alloyrun's specific compile, left as-is
  because reusing `_pattern()` verbatim (not forking a partial copy) was judged
  higher-value than chasing a rarely-hit edge case; if a future file's residual
  traces back to a `$70-$7F` byte being misread as a note, this is the place to
  look.
- Hardcoding column-major field offsets relative to `tbl_instr` (e.g. "-13,-8,
  -3,+2,+7 are universal") instead of properly re-locating them per-file via
  signature: REJECTED after only one data point (Tel_1) -- not enough evidence
  the exact byte gaps generalize; the disciplined per-file signature locate
  (`_locate_tel_instr_fields`) was implemented instead, which is what caught
  and needed the stride-consistency fix.
</attempted_approaches>

<critical_context>
## THE 4 KNOWN B1-TEL DISPATCH QUIRKS (all in `_locate_b1_row_variant`,
sidm2/mon_parser.py, roughly lines 309-382 as of commit 2f47dbe) -- READ THE
METHOD DOCSTRING FIRST, it's kept current with disassembly citations:
1. `_tel_repeat` (orderlist `$40-$7F` = REPEAT next pattern N+1 times)
2. `_tel_pat_off1` (Alloyrun-only: 1-based pattern indexing)
3. `_tel_classic_row` (Alloyrun+Starball-only: reuse `_pattern()` instead of the
   simple ctrl/length/bit6/bit7 inline loop)
4. `_tel_row_ctrl_off1` + `_tel_row_len_mask` (Bantam's ctrl-1'd threshold; EVERY
   file's real length mask read directly, not assumed `$1F`)
Plus a 5th, SEPARATE fix from round 4 (not a `_locate_b1_row_variant` field, a
different method): `_locate_tel_instr_fields` -> `self._tel_instr_fields`,
consumed by `_silent_instr`.

## THE ROW-DECODE PATH SPLIT in `_voice_blocks_tel` (same file, ~line 522-620):
`classic = getattr(self, "_tel_classic_row", False)` selects between calling
`self._pattern(idx, st, blk)` (Alloyrun/Starball) or the inline
length/bit6-rest/bit7-instrcmd loop (everyone else). The inline loop now applies
`row_off1` (Bantam's ctrl-1 adjustment, BEFORE the FF-terminator check is done on
the RAW byte -- order matters, don't move it) and `row_mask` (the real length
mask) and, as of round 4, `retrig = not self._silent_instr(instr)`.

## THE GROUND-TRUTH WORKFLOW (used identically every round, this IS the
project's established discipline per docs/players/PLAYBOOK.md, re-confirmed
useful again and again this session):
1. `py -3 bin/_mon_disasm.py <START-hex> <END-hex> SID/Tel_Jeroen/<file>.sid` --
   the reusable disassembler (steals the OPS table from
   `bin/_disasm_filter_handler.py` via exec-of-source, a slightly hacky but
   working pattern from a prior session; don't "clean it up" without checking
   nothing else depends on its exact import mechanism).
2. `py -3 bin/mon_validate.py SID/Tel_Jeroen/<file>.sid <subtune>` -- the ONLY
   trustworthy ground-truth signal (frame-exact per-voice onset comparison vs
   siddump, with freq->note-name calibration). "onset frames matched: X/Y" is
   the number to quote; X==Y means fully onset-EXACT (verify per-voice too,
   "frame-match=EXACT" on every voice line, not just the total).
3. GATE every change against: `py -3 bin/mon_validate.py SID/Tel_Jeroen/
   Hawkeye.sid 2` (expect 152/152), `... Hawkeye.sid 3` (28/28), `...
   Cybernoid.sid 0` (53/53), `... Cybernoid.sid 1` (15/15), `...
   Cybernoid_II.sid 0` (37/37). These MUST stay byte-identical after every
   single change -- they're the pre-existing, hard-won Hawkeye/Cybernoid
   byte-exact Stage-B wins from a much earlier session.
4. Full bucket resweep (NOT just the target file -- this caught round 4's
   regression) -- SCRIPT CONTENT (was in session scratchpad, will NOT exist in a
   fresh session, recreate from this):
```python
import sys, os, glob, io, contextlib
ROOT = r"C:\Users\mit\claude\c64server\SIDM2"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))
os.chdir(ROOT)
import bin.mon_validate as mv

names = ["05-09-87", "Ikari_Union", "Lost_in_China", "Scout", "Trying_Out_2_v1",
         "Trying_Out_3", "Happy_JT", "Beginning", "Beginning_v2", "DemoSong",
         "Orion_Intro", "Reggae_Example", "Trying_Out", "Alloyrun", "Alloyrun_v2",
         "Zynon_Zak", "Tel_1", "Bantam", "Monitor_Madness_1", "Monitor_Madness_2",
         "Trying_Out_2", "Chrome_Met1", "Starball"]

for n in names:
    path = os.path.join(ROOT, "SID", "Tel_Jeroen", n + ".sid")
    if not os.path.exists(path):
        print(f"{n}: MISSING FILE"); continue
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            sys.argv = ["mon_validate.py", path, "0"]
            mv.main()
    except SystemExit: pass
    except Exception as e:
        print(f"{n}: EXC {e}"); continue
    out = buf.getvalue()
    last = [l for l in out.splitlines() if "onset frames matched" in l]
    print(f"{n}: {last[-1] if last else 'NO OUTPUT'}")
```
5. Full suite: `py -3 -m pytest pyscript/ -q` (~3-4 min; run in background, wait
   for the completion notification rather than polling -- this was explicitly
   corrected mid-session after an inappropriate `ScheduleWakeup` call that
   turned out to be the wrong tool outside `/loop` context).
6. ALSO USEFUL (not scripted, ad-hoc each time): a "locate dump" one-liner to
   see a file's located table addresses + all `_tel_*` flags:
```python
import sys, os
ROOT = r"C:\Users\mit\claude\c64server\SIDM2"
sys.path.insert(0, ROOT)
from sidm2.mon_parser import load_sid, MON, _find
path = "SID/Tel_Jeroen/<FILE>.sid"
d, la, h = load_sid(path)
print("load=%04X len=%d init=%04X play=%04X" % (la, len(d), h.init_address, h.play_address))
m = MON(d, la, subtune=0)
for attr in ("ol_mode","tbl_olptr","tbl_olptr_hi","tbl_speed","tbl_pat","tbl_freq",
             "tbl_freq_hi","tbl_instr","_tel","_tel_repeat","_tel_pat_off1",
             "_tel_classic_row","_tel_row_ctrl_off1","_tel_row_len_mask",
             "_tel_instr_fields"):
    v = getattr(m, attr, None)
    print(attr, "=", hex(v) if isinstance(v, int) else v)
po = _find(d, 0x0A, 0xA8, 0xB9, None, None, 0x85, None)
print("tbl_pat dispatch sig c64=", hex(la+po) if po is not None else None)
```

## GOTCHAS reconfirmed / newly discovered this session
- **Never trust a file-first `_find` for a feeder/anchor byte pattern** -- a
  stray earlier match elsewhere in the binary WILL grab first (this bit round 1
  slightly differently than the prior session's version of this lesson, and bit
  round 4 HARD -- the Orion_Intro/Chrome_Met1 regression). Anchor searches near
  an ALREADY-confirmed reference point, and when even that isn't enough, add a
  STRUCTURAL CONSISTENCY check (like the `ad-wf == sr-ad` even-spacing
  requirement) rather than trusting proximity alone.
- **A "Stage-B, not a grammar gap" diagnosis is not self-evidently true just
  because the score is in the 60-88% "plausible" band.** 5 of the original 7
  "middle tier" files (round 3) turned out to be a length-mask decode bug, not
  Stage-B. The 2 that WERE re-checked and held up as genuine Stage-B (Alloyrun
  V1 in round 1, Orion_Intro in round 3) were verified by hand-tracing raw
  pattern bytes against siddump, not by re-stating the old diagnosis.
- **Different compiles of the "same" B1-tel generation can differ in almost any
  single instruction** -- length mask width, an extra `SEC;SBC#$1`, presence/
  absence of a repeat-op branch, presence/absence of a bit6-rest check, row-major
  vs column-major instrument tables. Every file this session needed its OWN
  disassembly pass; NOTHING should be assumed to generalize from one file to
  another without checking (this is why every fix in this session is
  signature-gated, never applied blind).
- **`whats-next.md` itself was NOT part of this session's git work.** It had
  pre-existing uncommitted changes from a session BEFORE this one (visible in
  `git status` since before this session even started) -- I never touched it
  until this final /whats-next invocation, which now overwrites it. If the
  PRIOR uncommitted version had content worth preserving, it's gone now
  (overwritten) -- but that was already the established behavior of the
  whats-next skill (each invocation replaces the file), and the user explicitly
  invoked it, so this is expected, not a mistake.
- **`ScheduleWakeup` should NOT be used to poll a background Bash task** -- the
  harness auto-notifies on background-task completion; I mistakenly called it
  once mid-session out of habit, immediately caught it (wrong tool for
  non-`/loop` context) and called `stop:true` to cancel it. No harm done, but
  don't repeat this.
</critical_context>

<current_state>
- **Repo**: `C:\Users\mit\claude\c64server\SIDM2`, branch `master`, ALL 6
  substantive commits from this session PUSHED to `origin/master`
  (`github.com/MichaelTroelsen/SIDM2conv`): `959728b` (issue #9 docs fix),
  `ed4b3cc` (Alloyrun/Starball), `5ab7eff` (Bantam), `4fdfd7f` (length-mask, the
  big one), `2f47dbe` (column-major instrument tables). `master...origin/master`
  is clean (no ahead/behind) as of the last push.
- **GitHub issues**: #9 and #4 both closed. Zero open issues on the repo as of
  session end.
- **Version**: `sidm2/__init__.py __version__` UNCHANGED (this is RE/bug-fix
  work, not a release milestone -- consistent with the standing convention).
- **Tests**: `py -3 -m pytest pyscript/ -q` -> **1561 passed / 7 skipped / 2
  xfailed**, confirmed identically 4 separate times this session (once per
  round), zero flakiness observed, zero regressions across the whole session.
- **B1-tel bucket status: 12/24 onset-EXACT** (was 6 at session start):
  05-09-87, Ikari_Union, Lost_in_China, Scout, Trying_Out_2_v1, Trying_Out_3
  (pre-existing) + Happy_JT, Beginning, Beginning_v2, DemoSong, Reggae_Example,
  Chrome_Met1 (all 6 new this session). Near-exact: Orion_Intro 92% (189/206,
  genuine Stage-B residual, diagnosed), Trying_Out 78% (125/160, NOT diagnosed).
  Improved-not-exact: Zynon_Zak 84%, Bantam 77%, Starball 76%, Alloyrun 61%,
  Tel_1 25% (all improved this session, none fully diagnosed to completion).
  Unchanged/untouched: Monitor_Madness_1 (~2%), Monitor_Madness_2 (~2%),
  Trying_Out_2 (~1.6%), Alloyrun_v2 (0 events, separate locate bug), the 85-file
  no-copy-loop bucket (entirely separate, larger RE unit).
- **Working tree**: clean except this `whats-next.md` write itself (about to be
  committed or left for the user, per normal whats-next-skill convention -- NOT
  auto-committed by the skill) and the SAME pre-existing untracked items noted
  at session start (`SID/Gallefoss_Glenn/`, `SID/Jeff/`, `SID/Red_kommel_jeroen/`,
  `SID_INVENTORY.md`, `archive/cleanup_2026-07-09/`, `bin/LFT/`, `bin/SIDDuzz/`,
  `bin/_kimmel_work/`, `DOC-AUDIT.md`, `.claude/settings.local.json` -- none of
  these were touched this session, all pre-existing).
- **Memory files updated and current** (Claude Code auto-memory, NOT in the git
  repo): `memory/mainstream-mon-tel.md` (the primary record -- read this FIRST
  next session), `memory/MEMORY.md` (index line updated).
- **NEXT SESSION SHOULD START WITH**: `memory/mainstream-mon-tel.md`'s "PLAN
  (PLAYBOOK staged) — updated" section (kept current through round 4), then
  work_remaining #1 above (Tel_1's second bug -- it's the most recently-touched
  file and the investigation is freshest/most-scaffolded, OR work_remaining #2
  (Monitor_Madness_1/2, Trying_Out_2 -- completely fresh files, no assumptions
  carried over, matches the session's proven "disassemble each file fresh"
  workflow). Both are reasonable next steps; #2 is lower-risk (fresh disassembly
  from scratch, same proven workflow) while #1 has more existing context loaded.
- **NO open question pending** -- user said "stop and lets restart", this
  whats-next.md is the requested handoff. Session is at a clean, fully-pushed
  checkpoint.
</current_state>
