<original_task>
Standing mission: any SID -> SF2 at 99% fidelity + 100% editable.
Session 2026-07-16. Entry point: **"read what next"** — no pre-set task; the user
asked what to work on. Scope was set turn by turn:

1. "read what next" -> I read memory + surveyed the tree and recommended:
   (a) land the uncommitted tracer fix, (b) pay down the docs debt from two
   UNDOCUMENTED player ports (Kimmel, Deenen), (c) cut v3.21.0.
2. "continue" -> executed that. It expanded because landing (a) uncovered a live bug.
3. "merge" -> merged the fix branch to master.
4. "fix the stale owning docs too" / "remove v1 from the KB" / "just write the prompt
   and i will built it" (a spec for TDZ KB in-place edit).
5. "go ahead. please remeber to read and update TDZ knowledge LLM" -> start the next
   RE arc (Deenen "Variant-B"), reading + writing the TDZ KB around it.
6. "port the Tel pattern-row grammar" -> turned out to need NO porting.
7. "cont" x3 -> continued each thread to a stopping point.

STANDING RULES (do not violate — carried from the v3.20.0 handoff, all still live):
accuracy over speed; never ship lossy silently; NEVER run
pyscript/sf2_open_in_editor.py (unless the user directly asks to load an SF2);
ONE MoN-engine build at a time (shared drivers_src .inc scratch); git checkout
drivers_src includes after every native build; DON'T edit builder modules while a
corpus runner is active (subprocess import race); corpus-gate every decoder change
(broad blast radius); verify disassembly branch targets by EMULATION before
rewriting a parser.

NEW STANDING RULE earned this session: **verify a falsifier/agent finding exactly as
you would verify the claim it attacks** (it produced one confident wrong finding that
would have destroyed 19 good files), and **read your own tool's output before trusting
it** (I shipped the vacuous-100 bug into a brand-new tool hours after fixing it in 11
files).
</original_task>

<work_completed>
Repo: master. 15 commits, 0a362a4 -> 5444b5e. Version bumped 3.20.0 -> **3.21.0 /
2026-07-16**. Tests **1561 passed / 7 skipped / 2 xfailed**. Working tree has NO
tracked changes.

=== A. THE ZIG64 AUDIO GATE WAS CERTIFYING OUTPUT IT NEVER CHECKED (669772e) ===
The headline bug. `sidm2/zig64_audio_gate.py::verify_sf2_audio` compared two traces
for equality; when the tracer could not drive a file BOTH came back empty ->
len(0)==len(0) -> the compare loop never ran -> **returned True**.
**PROVEN: 64 bytes of zeros certified as byte-identical audio to
SID/Laxity/Broken_Ass.sid** — a file in the PRIMARY supported corpus (also
Sanxion_Loader_Remix).
`_trace` compounded it: ignored the exit code, and the tracer's `FAILED:` line
CONTAINS COMMAS so the `len(p) >= 5` row filter dropped it -> looked like a clean
empty trace. **The user's uncommitted tracer fix could never have closed this** — the
gate had to reject empty evidence itself.
Fixes: `_trace` -> Optional, returns None on non-zero exit or `FAILED:` (None = "no
evidence", distinct from empty); verify_sf2_audio fails closed on None/empty.
Missing-tracer still returns True — that fail-open is DELIBERATE and pre-existing
(systems without zig64); left alone, now documented.
Tracer (tools/sidm2_sid_trace.zig): reject IRQ handlers < $0200 (zero page is always
a stale-vector mis-read — LFT/A_Mind_Is_Born resolved $0031); count SID writes on
BOTH the IRQ and normal PLAY paths, 0 across the window = FAILED; exit(1) on every
FAILED path (mcp-siddump/server.py already checks it). Rebuilt via zig 0.15.2.
3 regression tests, **each verified to FAIL against the pre-fix gate first**.
MEASURED: RSID sweep @200 frames — silently-empty fake successes **20 -> 0**; honest
failures 3 -> 22; traced ok 66 -> 73.

=== B. VICE FALLBACK: RSID FILES NOW GET VERIFIED, NOT REFUSED (4765524) ===
zig64 has no autonomous VIC/CIA delivery -> RSIDs with play=$0000 are untraceable.
The user's OTHER project has a working wrapper:
C:\Users\mit\claude\sid-reference-project\scripts\dev\vsid-trace.js
- Tested vs SIDM2's 22 untraceable RSIDs: **21 of 22 trace** (Broken_Ass 1068 writes,
  Platform_Hopping 23705, Myth 259, A_Mind_Is_Born 100). Only Final_Countdown_BASIC
  = 0 (a BASIC tune — plausibly genuine).
- Cross-validated independently: on Stinsen (a PSID both drive) **both report exactly
  90** changed-value writes over 16 frames.
- **LOAD-BEARING CONSTRAINT, measured:** the (register,value) SEQUENCE is identical
  across all 90 writes (the wrapper even emits zig64's own register names) **BUT FRAME
  ATTRIBUTION IS OFFSET BY EXACTLY 1** (zig64 frame 1 == vsid frame 0). The gate
  compares (frame,register,value) -> **a mixed comparison diverges on EVERY row**.
  Therefore: if zig64 fails on either side, BOTH sides are re-traced with vsid.
- `_verify_via_vsid()` wraps the SF2 PRG as a minimal PSID via the existing
  fidelity_common.psid_wrap; the original .sid goes to vsid as-is.
- **RESULT: Broken_Ass's real SF2 now VERIFIES — 499 matching rows per side.** Arc:
  certified-without-checking -> unverifiable -> genuinely verified.
- 4 tests; the e2e one asserts the pass rests on >100 REAL rows so it fails if the
  pass ever goes hollow. The 2 mock tests that stub _trace now also stub
  _verify_via_vsid so they keep testing the no-fallback path.
- $VSID_TRACE_JS overrides the path; absence disables the fallback (stays fail-closed).
  No common-path cost (fires only after zig64 already failed).

=== C. v3.21.0 + THE DOCUMENTATION DEBT (faa9032, b5b70af, 8e0c0ce) ===
Kimmel + Deenen had shipped 2026-07-13 with ZERO docs; version still read 3.20.0 six
commits later.
- NEW docs/players/KIMMEL.md + docs/players/DEENEN.md; rows in players/README.md,
  CLAUDE.md, ACCURACY_MATRIX.md; CHANGELOG + STORY; version bump.
- **Numbers re-verified against the code before writing** (not copied from notes):
  Kimmel 11/12 voice-medians exact (Rhaa v2 92.9%, n=14); Deenen 10/19 located,
  4 clean wins. Both matched.
- gen_sf2_index.py registry never knew about either player -> 21 SF2s missing from
  docs/SF2.md. Added + regenerated. Verified subtunes-as-separate-songs is CORRECT
  (matches the MoN convention) — a non-bug I checked rather than "fixed".
- ACCURACY_MATRIX was stale since v3.13.0: added Hubbard V1+V2, DMC, SM, SDI, with
  provenance stated honestly. **Verified all 17 bin/ paths resolve — TWO I had written
  were WRONG** (dmc_to_sf2.py doesn't exist; SM's native builder is
  build_soundmonitor_native_song.py).
- Documented the VICE escape hatch in CLAUDE.md + PLAYBOOK.md (+2 trust rules).

=== D. THE FALSIFIER AGENT AND WHAT IT FOUND (f7b8680, 406152a, 3125d41, ba312d6, 2f7fdc4) ===
docs/AI_TOOLING.md = DESIGN ONLY (review). Prior art: sid-reference-project/.claude/
(a working research->falsify pair, 200 cards). Borrows its STRUCTURE, not its content:
that project's unit is a document (falsifier fetches URLs); SIDM2's is a measured claim
about a binary (ours RE-RUNS TRACES). Includes **§8 what NOT to build**.
.claude/agents/sidm2-fidelity-falsify.md — SIDM2's FIRST agent. Read-only, opus,
**default REFUTED**. Value = <what_to_attack>: 14 named traps, each a real shipped
failure. Adds a **VACUOUS** verdict the sibling lacks (*the number is real but measures
nothing*). Key line: *a doc, a memory file, a CHANGELOG entry and a commit message are
the same claim wearing different hats — RE-RUN IT.*

THE RUN: 4 agents (one per matrix row I'd committed 3h earlier), ~40min, ~430k tokens.
**6 REFUTED, 8 VACUOUS, 1 NOT-REPRODUCED, 3 STALE.**
> **HEADLINE: not one headline percentage was wrong.** SM 99.23% reproduces to the
> digit (n~841k); SDI's 7 medians within 0.2 on a full 324-file sweep; Balloon 100x3
> exact over 19996 frames; Hubbard V1 pulse 100 (a MODELLED engine).
> **The measurements are sound; the PACKAGING was the problem.** -> relabel, don't
> re-measure.
ROOT CAUSE NAMED: **CLAIM DRIFT**. v3.19.0's CHANGELOG (origin of 99.23%) never says
"every part" — that belongs to v3.18.0's DIFFERENT 99.08%/28-part sweep. CLAUDE.md
merged the old parenthetical onto the new number; the matrix copied CLAUDE.md; I copied
it into the "single source of truth". Four hops from true to false, no lie anywhere.

**!! THE FALSIFIER PRODUCED ONE CONFIDENT WRONG FINDING !!** It reported "348 SF2s is
really 329 + 19 stale orphans", with a plausible story (pre-guard timestamps, DELTA
false-positives). **WRONG.** Raw locate() over the 441 SDI .sid gives **343**, and
343 + 5 subtune extras = **348 exactly**; every SF2 maps to a still-locating source ->
**0 orphans**. It conflated the SWEEP's validated count (324) with the builder's locate
gate (343 — convert() checks `lay is None` and nothing else), then explained the gap
with a cause that merely FIT the number. **Deleting on its say-so would have destroyed
19 legitimate SF2s.**

**3125d41 — THE VACUOUS-100 BUG CLASS (the systemic find).** 4 independent agents, 4
players, same defect; a follow-up sweep found it in **11 files**, not the 3-4 reported.
Every scorer had a private `100.0*ok/tot if tot else 100.0` -> **NO DATA reported
PERFECT AGREEMENT**. NOT cosmetic: in build_dmc_native_song.py and
build_soundmonitor_native_song.py it fed a REAL BUILD DECISION —
`legato_set = frozenset(v for v in cands if fl[v] > fg[v] + 1.0)` — a voice with no
data scored 100.0 from BOTH sides -> 100.0 > 101.0 is False -> **the voice silently
voted "keep gate"**. Now both are None, the A/B is explicitly inconclusive, and the
build prints "(no data, kept gate: [v])".
Canonical fix: **sidm2/fidelity_common.score_pct()** returns None when tot==0; fmt_pct
renders "n/a"; None cannot be silently compared (None > x raises). **Use it for any new
scorer.** Fixed 5 tracked + 6 untracked-but-shipping-numbers files. The _opt_* family
had the INVERTED form (`max(1,tot)` = phantom FAILURES). 7 tests, verified failing first.

**ba312d6 / 2f7fdc4 — corrections.** filter-100 -> "not exercised" (Hubbard never
writes cutoff: 0 filter writes/1000 frames, $D417 never touched -> the metric compared
0==0 a thousand times, so **any driver ignoring the filter scores 100%**); V1 freq
100 -> 99.3-100; Delta pulse 100 marked **CAPTURED not modelled** (hp_engine=0); Delta
wf 85-96 -> 85-97 and flagged as the PESSIMISTIC figure (residual is pure +/-1-frame
skew); **DELTA "89.8/55.5" -> "win 89.8 / strict 55.5" (MY transcription error)**; SDI
-> "343 locate -> 348 SF2s, 324 sweep-validated"; SM "every part" -> 26/27 (restoring
the missing one gives **99.25%** — the omission UNDERSTATED); SM "Dance parts 2-6 at
100.0" -> **parts 03/04 only**; build/mode counts moved OUT of the accuracy claim;
removed the anti-matrix's "Rob Hubbard -> no pipeline exists" (my own refresh had left
it contradicting my new rows).
Stale owning docs fixed after RE-MEASURING: dmc_build_all.py --dry -> **56/18/14/0**
(DMC.md:17 said 41 while its OWN line 140 said 56; README said 21/43); locate() -> 343
(SDI.md said 312/336). Fixed SDI/DMC/SOUNDMONITOR (2 releases behind, held NONE of its
own numbers)/HUBBARD/README/INDEX **and CLAUDE.md, the upstream source the drift came
FROM**. All five cross-check as agreeing.

=== E. DEENEN "VARIANT-B" — FOUR REFRAMINGS (62f4243, c1c28ca, 69156e0, d83e7f0, 5444b5e) ===
**1. The reloc/groove were already CORRECT** (emulation-verified: ord table $195C,
absolute ptrs $1AD1/$1AEA/$1B07, reloc 0).
**2. It is not A-vs-B — THE GRAMMAR IS PER-FILE.** Every rip carries its orderlist class
boundaries as IMMEDIATES in its own fetch routine; decode_voice hardcoded Ding's.
  Ding_van_Charles $12A6  pattern <$5F  $FF=seg-advance(cap26/step27)  note=A-$82
  After_the_War    $0E94  pattern <$6F  $FF=seg-advance                note=A-$84
  Soldier_of_Light $0CDC  pattern <$50  $FF=restart          uses AND #$1F not SBC
  Constant_Runner  $13F3  pattern <$40  $FF=RESTART TO INDEX 0         note=A-$80
CR from the 6502: $40-$5F = **PATTERN LOOP COUNT** (A-$40), proven by DEC $e0,X @$145B;
$60-$7F = A-transpose; >=$80 = note. So `8C 43 0B` = transpose/loop-3/pattern $0B.
**$43 was NEVER a pattern** — under Ding's <$5F it became pattern 67, whose table entry
($136D+$86 = **$13F3, THE CODE ITSELF**) gave the out-of-file ptr $D1B9 ($4E -> $40C9).
That + $FF unmodelled = the whole **500-notes-vs-44** runaway.
GENERAL LESSON: **a pointer table ends where CODE begins**; an out-of-range index
silently reads instruction bytes as a pointer.
**3. THE <$40 FILES ARE THE JEROEN TEL ENGINE WE ALREADY SUPPORT.**
sidm2/mon_parser.py:397-404 — shipping, tested, used for Hawkeye/Cybernoid — already
implements it byte-for-byte (>=$80 transpose b&$1F / >=$60 instr base / >=$40 REPEAT
(b&$3F)+1 / <$40 pattern). The 12: Airwolf, Constant_Runner, Day_After_the_Beat,
Double_Dragon, F1_Simulator, Mantalos, **Melig**, Mr_Heli, **Say_Hello**, Zamzara,
Zamzara_v1, Zynon. **Melig + Say_Hello are ALREADY proven Tel** (2 of the 3 MoN TTWII
freebies decoding EXACT at sub0 via mon_parser). The other 10 fail only on **LOCATE**
(mon_validate returns 0/0 = vacuous no-evidence, not a decode failure).
**HOW IT WAS MISSED FOR 3 SESSIONS:** I DID search the KB first. I searched "Charles
Deenen variant orderlist groove" / "Zamzara Smooth Criminal Mantalos" -> nothing ->
concluded native RE -> disassembled. **The knowledge was in the `maniacs-of-noise`
card** — different composer, exact same byte ranges.
**=> SEARCH THE TDZ KB BY MECHANISM (byte ranges, opcode shape), NOT BY COMPOSER/NAME.**
**4. Routed the Tel class (69156e0). CR's structure is now EXACT:
`parse [113,101,44]` == `real [113,101,44]`, onsets 100.0x3.** Runaways gone (CR v2
500->44; Zamzara v1 600->gone). The 4 clean wins are byte-identical (not $40-class).
Zamzara 75->25 and CR pitch 15.9->35.6 are **NOT regressions** — the old numbers were
scored against CAPPED RUNAWAY streams (600/500 = the cap) = vacuous; both refused then
and now.
**GUARD ADDED**: routing made CR structurally sound -> plausible() (purely structural,
cannot see pitch) flipped True -> the builder would have **EMITTED an SF2 at 35.6%
pitch**. plausible() now REFUSES the whole $40 class.
**d83e7f0 — the ROWS need NO porting (negative result, committed so it isn't redone).**
Ding == Constant_Runner == Mantalos row-classes: CMP $60 $FF $FE $FD $FC $FB $E0 $C0,
SBC $E1 $C0 $81. Note formation identical too (CR $1519 = LDA $d0/CLC/ADC $da,X ->
FREQ_LO $12AF / FREQ_HI $130E, diff $5F). **Only the ORDERLIST ever differed.**
**Zamzara IS different**: CMP $60 $FD $FE $FC $E0 $C0 $80..., SBC $C8 $F6 $C8 $C8 $E1,
no $FF row-end -> the one real row-port left.
**5444b5e — PROVEN: CR's DECODE IS EXACT; THE METRIC IS WRONG.** New tool
`bin/deenen_engine_check.py` compares the decoder to **the player's OWN computed note**
(watches the note handler's STA $f2,X @$152A under py65 — no metric in between):
**Constant_Runner v0 100.0% n=92, v1 100.0% n=80, v2 100.0% n=34.** Every note, all 3
voices — while deenen_validate says pitch 35.6%.

=== F. SIDE WORK ===
- Deleted tools/sidm2-sid-trace.exe.orig-pre-rsid-honest-fail-fix (user request) after
  verifying it was the pre-fix binary and the identical original is recoverable at 0a362a4.
- TDZ KB: wrote `jeroen-kimmel` (**ae6ed3679b03**) — the FIRST RE of that variant
  anywhere; sets edges.derives_from: ["rob-hubbard"], filling a gap that card leaves
  TODO. Wrote `mon-deenen` (0ba7668ee01e), then CORRECTED it with `mon-deenen-v2`
  (**a33394d73906**) once the per-file grammar was found. **Removed v1 at user request.**
  Wrote the KB in-place-edit spec prompt (delivered in chat, not to a file).
- Memory: zig64-gate-false-pass.md, vice-rsid-wrapper.md, fidelity-falsifier.md,
  deenen-player.md, kimmel-player.md, tdz-c64-knowledge-base.md, MEMORY.md index.
</work_completed>

<work_remaining>
## IMMEDIATE (the live thread)
1. **EXPLAIN why deenen_validate reports 35.6% pitch for a decode PROVEN exact.**
   The blocker for Constant_Runner and possibly more. Do NOT just observe it.
   - Re-confirm: `py -3 bin/deenen_engine_check.py Constant_Runner` -> 100% x3.
   - deenen_validate compares decoded note indices to freq_to_semi() of the real SID
     freq at each gate-on frame, picking a best global semitone offset (`so` = -12 for CR).
   - **REFUTED, DO NOT RETRY**: (a) init seeding $da,X — it's $00 on all voices;
     (b) note index != semitone — both Ding $10F3 and CR $12AF give
     index == freq_to_semi(freq); (c) slide density — B_A_T has MORE $FD (27 vs 23) and
     scores 100/100.
   - UNTRIED: is the `so` search picking an offset that helps ONSET alignment but wrecks
     pitch? Is the freq at a gate-on frame a slide/vibrato START rather than the target?
     (a crude diff showed real v0 semitone **94** interleaved — a wild value consistent
     with a ramp). Try comparing at frame N-after-onset.
   - **If the metric undercounts here it may undercount elsewhere** — the 4 "clean wins"
     AND every refusal were scored with it.
2. **Then decide the $40-class guard** (sidm2/deenen_parser.py::plausible()). If the
   metric is wrong, CR is a 5th clean win. NOTE: engine_check validates **NOTES ONLY**
   — not timing/timbre/effects — so "notes right" != "SF2 right".
3. **Zamzara's row grammar** ($C8/$F6 bases, no $FF row-end) — the one real row-port left.
4. **Extend mon_parser's LOCATE to the 12 $40 rips** (bigger prize than the Deenen
   decoder). It keys on Hawkeye's `LDY #5 / LDA setSrc,Y / STA setDst,Y`; CR instead
   **self-modifies the LDA $1ad1,Y operand at $13E6** — same grammar, different pointer
   setup (like Kimmel<->Hubbard). This route also unlocks MoN **native Stage B**
   (100% byte-exact on Hawkeye) instead of a Stage A transpile.
5. **Flow-walk the class chain** and wire DeenenGrammar fully (only fetch/pat_thr/ff_mode
   are read now). MUST handle **BCC vs BCS** polarity. Validate file-by-file.
   **DO NOT ship a byte-scan** — see attempted_approaches.
6. Still open: the ZP $88,X nested-loop orderlist variant (Astro/Mr_Heli); the 9
   not-located; the **72-file MoN/Deenen group in SID/Tel_Jeroen/** (MON.md ~line 119);
   the 15 MoN/FutureComposer dialect files.

## DEFERRED / FLAGGED (not done, deliberately)
7. **The DEGENERATE-value bug** — different from the empty one score_pct fixes. Hubbard's
   "filter 100%" is tot=1000 with **ONE distinct value** -> 0==0 matches 1000x.
   score_pct CANNOT see it. **Needs a distinct-value check.**
8. **pyscript/trace_comparator.py:291,341** — identical `else 100.0`; **:341 is
   reachable** (a voice with no pulse writes scores 100%). Not fixed: user-facing viz
   feeding the Accuracy Heatmap's JSON, JS consumers, no tests.
9. **bin/hubbard_validate.py is V1-only and FAILS SILENTLY on V2** — reads Delta sub11 at
   23-25% by computing onsets as tk*fpt, ignoring swallow_period=5 (Monty 0, Delta 5).
   Returns a meaningless number instead of refusing.
10. **SM's 99.23% is NOT reproducible from a fresh clone** — bin/_opt_sweep_corpus.py,
    bin/_sm_build_all.py, out/_opt_sweep.log all untracked+gitignored, and **no tracked
    test asserts any SM number**. Also: re-running the (now-fixed) _opt_sweep_corpus.py
    will shift 99.23% slightly UP (the fix removed phantom failures). Not re-run.
11. **`/verify-claims <player>` command** — re-run a player's documented numbers vs code,
    report drift; would gate version bumps so the matrix can't rot 8 versions again.
12. **docs/AI_TOOLING.md §9 open questions** await review (esp. whether the falsifier
    keeps Bash). Per §8 the deliberate decision was **STOP AT ONE AGENT** — no skill, no
    workflow — until the falsifier proves itself repeatedly.
13. **LEAD, unchased:** Sound Monitor's ASCII signature lives at **$CBD4** — the exact
    "stale handler" address the 6 Matt Gray + 2 Laxity RSIDs resolved to in the tracer
    sweep. They may be SM-family rips drivable through the existing SM pipeline, as the
    3 Deenen SM freebies were. Unverified.
14. Never audited by the falsifier: **Galway, MoN, ROMUZAK, FC** matrix rows. Only
    Hubbard/DMC/SM/SDI were.

## USER-SIDE
15. The user is building **in-place edit for the TDZ KB** (spec delivered in chat).
    **ADD TO IT: `remove_document` LEAVES ORPHANED CHUNKS — CONFIRMED LIVE.** After
    removing 0ba7668ee01e, get_document says "not found" but **search_docs STILL RETURNS
    ITS FULL TEXT**. The retracted v1 grammar is currently searchable and un-checkable by
    id — WORSE than before the delete. **Until fixed, deleting a card does not retract it.**
</work_remaining>

<attempted_approaches>
**DeenenGrammar class-chain byte-scan — BUILT, TESTED, DROPPED.** Scanned for
`CMP #imm / BCC` + `SBC #imm` to extract the A-transpose/loop boundaries. Produced
GARBAGE on Ding, the file it should reproduce exactly (loop=$70-$5E, inverted), because
**Ding branches with BCS where Constant_Runner uses BCC** and the scan caught unrelated
instructions. Verified it would have altered **ALL FOUR currently-100% files**. Dropped
rather than shipped; only the 3 disassembly-verified fields survive; unreadable files
report read_ok=False rather than guessing. **A real flow-walk is required.**

**"Port the Tel pattern-row grammar" — the task rested on a wrong premise.** Disassembled
first: rows already identical. Nothing to port (d83e7f0).

**3 refuted hypotheses for CR's 35.6% pitch**: init seeds $da,X; note index != semitone;
slide density. All disproven — details in work_remaining #1.

**"Eye_to_Eye's ground truth is vacuous" — REFUTED.** I suspected siddump couldn't drive
an RSID (play=$0000), making its "real onsets [8,47,8]" garbage. It CAN: *"Warning: SID
has play address 0, reading from interrupt vector instead. New play address is $7984"*,
401 rows. Checked before building on it.

**Reusing mon_parser wholesale on the $40 files — not a one-liner.** mon_validate returns
0/0 on 5 of 6 tried; its locate keys on a subtune setup these rips don't have.

**The falsifier's "19 stale orphans" — a confident WRONG finding I nearly acted on.**
See work_completed D. **Verify falsifier findings.**

**My own deenen_engine_check shipped with the vacuous-100 bug** (`all([])` is True -> a
no-evidence file claimed a perfect match) AND an unanchored locate (scanned for the first
`18 75 xx 95 xx` anywhere -> not the note handler -> every file read 0%). Both caught by
reading its own output; now anchored on the row dispatch's JMP operand + requires evidence.

**The tracer's own default addresses fooled ME mid-session**: ran sidm2-sid-trace.exe with
the default $1000/$1003 on a PRG whose real addrs are $1573/$13D7, got an empty trace,
briefly read it as a regression I'd caused. The bug demonstrating itself on the person
fixing it.

**Bash tool != PowerShell**: `git commit -m @'...'@` is a PS here-string and leaked `@`
into a commit subject (amend changed the hash fe1a3d7 -> 669772e; a memory file briefly
cited the dead hash). Use heredoc -> file -> `git commit -F`.

**mcp__tdz-c64-knowledge__search_docs threw** `cannot access local variable 'load_time'`
once, then worked. Transient; retry.
</attempted_approaches>

<critical_context>
## THE RULE THAT GOVERNS EVERYTHING
**A fidelity claim must never outrun its evidence. Never ship lossy output silently.**
The whole session follows from it: the gate fails closed; the builder refuses implausible
decodes; the $40 class stays guarded DESPITE a proof; negative results get committed.

## THE BUG CLASS THIS PROJECT KEEPS RE-LEARNING
**An equality/diff check over evidence must FIRST assert the evidence EXISTS.**
`compare(a,b)` where both are empty is not a match — it's "no test ran". Sightings THIS
SESSION: the zig64 gate (certified 64 zero bytes); 11 fidelity scorers; two BUILDERS
where it cast a real A/B vote; mon_validate's 0/0; **and my own new tool**. Its sibling
is the **DEGENERATE** case (Hubbard's filter: tot=1000, one distinct value) which
score_pct does **NOT** catch.

## VERIFIED ENVIRONMENT
- **zig 0.15.2.** Tracer source-of-truth = the repo's tools/sidm2_sid_trace.zig; rebuild:
  copy to C:\Users\mit\Downloads\zig64\src\examples\, `zig build`, copy
  zig-out/bin/sidm2-sid-trace.exe back. **The zig64 copy goes STALE (was Jun 23).**
- **vsid**: C:\winvice\bin\vsid.exe (present, NOT on PATH). Wrapper:
  C:\Users\mit\claude\sid-reference-project\scripts\dev\vsid-trace.js; override with
  $VSID_TRACE_JS. JSON: `trace.writeCount`, `frames[].writes[]` (NOT a top-level
  write_count — that guess cost a round-trip).
- **vsid gotchas (all real)**: **exits 1 on NORMAL termination** — check for the dump
  file, not the exit code; `--changed-only` REQUIRED to match zig64 semantics; **cycle
  timings NOT comparable between tools (~1 frame apart)** — only the write SEQUENCE agrees.
- Tests: `py -3 -m pytest pyscript/ -q` -> 1561 passed / 7 skipped / 2 xfailed (~4 min).
- **New .claude/agents/ files are NOT selectable until a session restart.** Workaround:
  dispatch `general-purpose` and tell it to read+adopt the agent file (read-only then
  prompt-enforced, not tool-enforced).

## NON-OBVIOUS DISCOVERIES
- **A pointer table ends where CODE begins.** An out-of-range index silently reads
  instruction bytes as a pointer (CR's pattern $43 -> $136D+$86 = $13F3 = the fetch
  routine itself -> $D1B9).
- **A too-short window is indistinguishable from a broken trace.** Arkanoid: 0 writes at
  5 frames, 460 at 200. Re-check any zero at >=200 frames.
- **The SDI denominator trap**: 343 locate (the BUILDER's gate) / 324 sweep-validated
  (needs usable ground-truth onsets) / 671 songs. Conflating the first two invented 19
  orphans that don't exist.
- **Kimmel validation trap**: gate-onset metrics read ~0% on that legato engine even on a
  PERFECT decode — validate on frame-pitch.
- **Deenen groove rate varies per file**; ratio-of-medians gives the wrong answer (~5.25).
- **SEARCH THE TDZ KB BY MECHANISM, NOT BY NAME.** Engines cross composer boundaries —
  that IS the KB's premise (rob-hubbard documents a 51-composer routine family). A name
  search only finds the card someone happened to file it under.

## KEY FILES
- Gate: sidm2/zig64_audio_gate.py (_trace, _verify_via_vsid, verify_sf2_audio).
- **Canonical scorer: sidm2/fidelity_common.py::score_pct / fmt_pct — USE FOR ANY NEW
  SCORER.** Also psid_wrap, freq_to_semi, siddump parsers.
- Deenen: sidm2/deenen_parser.py (DeenenGrammar, DeenenLocate, DeenenModule,
  decode_voice, _parse_row, plausible); bin/deenen_validate.py,
  bin/deenen_engine_check.py, bin/_deenen_vb.py + bin/_deenen_emu.py (gitignored).
- Falsifier: .claude/agents/sidm2-fidelity-falsify.md; design + what-NOT-to-build:
  docs/AI_TOOLING.md.
- Docs owning numbers: docs/reference/ACCURACY_MATRIX.md, CLAUDE.md Known Limitations,
  docs/players/*.md. **These copy from each other — that is CLAIM DRIFT; fix UPSTREAM
  (CLAUDE.md) too or it drifts back.**
- TDZ KB card sources: C:\Users\mit\.tdz-c64-knowledge\temp\.
</critical_context>

<current_state>
- **Version 3.21.0 / 2026-07-16** live in sidm2/__init__.py.
- **15 commits on master** (0a362a4 -> 5444b5e). **No tracked changes** in the working
  tree; only pre-existing untracked corpora/scratch (SID/Gallefoss_Glenn/, SID/Jeff/,
  SID/Red_kommel_jeroen/, SID_INVENTORY.md, archive/cleanup_2026-07-09/, bin/LFT/,
  bin/SIDDuzz/, bin/_kimmel_work/). NOT pushed to origin this session.
- **Tests: 1561 passed / 7 skipped / 2 xfailed.** No known failures.
- **Deenen corpus: 10/19 located, 4 clean wins — UNCHANGED BY DESIGN.**
  Constant_Runner decodes **exactly** (structure [113,101,44]; notes 100% x3 vs the
  player's own state) but is **deliberately REFUSED** by plausible() because the
  deenen_validate pitch metric disagrees (35.6%) and the disagreement is not yet
  EXPLAINED. **It is one explanation away from a 5th clean win — not one metric away.**
- **DeenenGrammar**: fetch/pat_thr/ff_mode are read and route decode_voice; the class
  chain is deliberately NOT parsed.
- **TDZ KB**: jeroen-kimmel = ae6ed3679b03; mon-deenen-v2 = a33394d73906 (live, correct).
  v1 0ba7668ee01e **removed — but its chunks are STILL in the search index** (server bug),
  so its wrong grammar remains findable.
- **docs/AI_TOOLING.md is DESIGN ONLY / not built** beyond the one falsifier agent.
- **NEXT SESSION SHOULD START WITH**: `py -3 bin/deenen_engine_check.py Constant_Runner`
  to re-confirm the exact decode, then attack **why deenen_validate disagrees**. That
  single question gates Constant_Runner, possibly other files, and the trustworthiness of
  every Deenen number already published.
</current_state>
