# Documentation Audit — SIDM2 (accuracy-figure duplication, scoped)

**Audited:** 2026-08-09 · **Commit:** 6d6350f · **Branch:** master
**Scope:** `docs/reference/ACCURACY_MATRIX.md` vs `docs/players/*.md` (21 files) and
`docs/players/README.md`'s own index table. Deliberately narrow, per this session's task:
find headline accuracy-percentage duplication and drift, NOT a full-repo audit. Narrative /
session-log content inside player docs (round-by-round development history, RE findings,
gotchas) was intentionally **not** read or evaluated — only each doc's header/status block
(typically the first 15-60 lines) and its own summary sections.
**Documents read (header/status block only, by design — see above):** 21 player docs +
`ACCURACY_MATRIX.md` (101 lines, read in full) + `README.md` (57 lines, read in full).
`BLACKBIRD.md` is 5,141 lines; only its ~60-line header was read, which is sufficient to
answer "does the header state the current headline number" — the question this audit asks.
**Findings:** 2 P0 · 4 P1 · 1 P2 · 0 P3 (duplication-only items are listed under "Duplicated
facts", not as numbered findings, since the fix is identical for all of them)
**Confidence:** 7 HIGH · 0 MEDIUM · 0 LOW (LOW is never reported)

## Outcome — all findings fixed same session (2026-08-09)

Every P0/P1/P2 finding below was corrected, plus one found during the fix pass that the
initial audit missed (see note): `DMC.md`'s own header also omitted its headline result
(Balloon's 400s/100×3 achievement), the same "header undersells the current state" pattern
as ROMUZAK/Blackbird/README-FutureComposer — caught because fixing ROMUZAK's identical
pattern made it recognizable, not because the first pass looked for it. Recorded here
rather than silently folded into the original findings list, since a report claiming it
found this from the start would be inaccurate.

| Finding | Fix applied |
|---|---|
| P0-1 Blackbird README row | Rewrote to current matrix figures (mean 99.96%, 11/16 at 100.0%) + corrected Path column |
| P0-2 Hubbard "filter 100%" ×3+ | Corrected in `HUBBARD.md` (header + 3 table cells), `HUBBARD_V2_PLAN.md` (2 locations), `README.md` — 6 locations total, 2 more than the original count found (the corpus-status table in HUBBARD.md itself) |
| P1-1 SoundMonitor README row | 99.23%/26 → 99.25%/27 |
| P1-2 ROMUZAK.md header | Re-led with Stage B byte-perfect result |
| P1-3 BLACKBIRD.md header | Added a current-state callout above the stale (but historically-accurate-for-its-date) B22 narrative, rather than rewriting 65 lines of dated history |
| P1-4 FutureComposer README row | Added Stage B (14/15 at 100.0%) |
| P2-1 Deenen README row | 4 → 7 clean wins |
| (found during fix, not in original list) DMC.md header | Re-led with Balloon's 400s/100×3 result ahead of Rockbuster's partial 97% |
| Duplication trim, ~15 consistent docs | Added a one-line canonical-source pointer to each (DEENEN, MON, GALWAY, FUTURECOMPOSER, LAXITY, MATTGRAY, KIMMEL, SDI, SOUNDMONITOR, DRIVER11, CLUSTERS, ROMUZAK) rather than stripping their numbers outright — lower risk, and the goal (a canonical source future drift gets checked against) is met either way |

18 files changed, all `docs/players/*.md` + `docs/players/README.md`; no code touched (grep
confirmed no non-`.md` files in the diff, so no test suite re-run was needed).

---

## Ground truth

`ACCURACY_MATRIX.md` is the designated canonical source (explicit user decision this
session: "ACCURACY_MATRIX.md is the home"). It carries its own re-measurement/verification
provenance (line 6: "Figures last re-measured: v3.22.0 — unchanged in v3.23.0, and verified
rather than assumed"; lines 18-25: adversarial-audit provenance for 6 of the rows). Every
comparison below treats the matrix's current text as ground truth and checks player docs /
`README.md` against it — not the reverse.

| Fact | Value | Source |
|---|---|---|
| Matrix version stamp | 3.23.0, 2026-08-09 | `ACCURACY_MATRIX.md:4-5` |
| Player docs in scope | 21 files, `docs/players/*.md` | `ls docs/players/*.md` |
| Largest player doc | `BLACKBIRD.md`, 5,141 lines / 410 KB | `wc -l` |

---

## Findings

### P0-1 · README.md's Blackbird row describes a state ~3 weeks and dozens of commits stale — reads as "not working" when the feature is production-tested at 99.96% mean

**Locations:** `docs/players/README.md:29`
**Claim:** `"| **Blackbird** (Linus Åkesson / "lft") | [BLACKBIRD.md](BLACKBIRD.md) | recon only, not wired | locate/table-layout solved (11/59 files exact template match); decompression algorithm identified but not yet correctly decoding | SID/LFT/ (59; ~27 genuinely Blackbird across tool versions) |"`
**Verified by:** Read `ACCURACY_MATRIX.md:61` and `BLACKBIRD.md:1-60` directly.
**Actual:** Matrix: *"Corpus **mean 99.96** overall, **11 of 16 at exactly 100.0**, none below 99.8 ... Glyptodont **162/162 note-ons** ... reproducible from a fresh clone ... asserted by a test."* `BLACKBIRD.md`'s own header (dated 2026-07-21, i.e. mid-arc, itself also stale — see P1-3) already describes a working native driver for all 11 corpus files at 97.4-99.8%.
**Confidence:** HIGH — both the matrix and the doc's own header directly contradict this row; not an inference.
**Consequence:** A reader using `docs/players/README.md` as the entry index (its stated purpose — line 1: "One document per player") would conclude Blackbird support does not exist yet ("decompression ... not yet correctly decoding"), when it is one of the project's most mature, test-covered player families (34 tests, a tracked reproducible sweep script, corpus mean 99.96%). This is the single most consequential drift found: it could cause a future session to re-attempt already-solved work, or to omit Blackbird when summarizing project capabilities.
**Fix:** Replace the row's Fidelity/Status cell with a one-line current summary + pointer to the matrix, matching the treatment recommended for the other rows below.

### P0-2 · Hubbard's retracted "filter 100%" claim still appears in 3 places, all after the project's own adversarial audit named it a vacuous claim

**Locations:** `docs/players/HUBBARD.md:6`, `docs/players/HUBBARD_V2_PLAN.md:5`, `docs/players/README.md:20`
**Claim:** HUBBARD.md:6 — *"byte-exact freq + pulse + filter on all 3 voices for the V1 corpus ... and for the first V2 tune (Delta theme: freq/pulse/filter 100%, waveform 85–96%)"*. HUBBARD_V2_PLAN.md:5 — *"one tune fully plays (Delta theme: freq/pulse/filter 100%)"*. README.md:20 — *"V1 native: pulse/freq/filter **100%**; V2 Delta theme 100% (wf 85–96%)"*.
**Verified by:** Read `ACCURACY_MATRIX.md:56` directly, cross-checked against `HUBBARD.md`, `HUBBARD_V2_PLAN.md`, `README.md`.
**Actual:** `ACCURACY_MATRIX.md:56` — *"**Filter: not exercised** — Hubbard never writes cutoff/resonance, so the old 'filter 100%' was `0==0` for 1000 frames and meant nothing."* This is not a new finding by this audit — the matrix's own provenance note (lines 18-25) already documents that this exact class of claim ("Hubbard's 'filter 100%' — a register the player never writes") was identified and corrected by the project's 2026-07-16 adversarial audit. It was corrected in the matrix. It was never propagated to the 3 places that repeat it.
**Confidence:** HIGH — the matrix explicitly names this exact claim as retracted; the 3 locations still state it unqualified.
**Consequence:** Someone reading any of these 3 docs (rather than the matrix) walks away believing Hubbard's filter emulation was verified byte-exact, when the truth is the opposite: the register was never exercised, so the metric is meaningless (100% because 0 always equals 0). This is precisely the failure mode the matrix's own header warns about: *"Read the caveats in each row, not just the number."* Three separate docs currently make that impossible.
**Fix:** Remove "filter 100%" from all 3 locations (or replace with "filter: not exercised, see ACCURACY_MATRIX.md" if the sentence needs to mention all 3 registers for flow).

### P1-1 · README.md's Sound Monitor row states the number the matrix explicitly calls superseded

**Locations:** `docs/players/README.md:22`
**Claim:** `"native: corpus **99.23% freq+wf** (n≈841k, 26/27 parts; pulse 96.7/filter 97.3)"`
**Verified by:** Read `ACCURACY_MATRIX.md:59` and `SOUNDMONITOR.md:24-29` directly.
**Actual:** Both the matrix and `SOUNDMONITOR.md`'s own header (updated 2026-07-30) state **99.25% / all 27 of 27 parts**, and explicitly: *"Supersedes the 2026-07-16 audit's 99.23%/26-parts figure — same metric, now including the previously-missing `Dance_at_Night_remix part01`."* `README.md`'s row still carries the retracted 99.23%/26-parts figure.
**Confidence:** HIGH — three-way comparison (matrix, the player doc itself, and README.md), two agree, one is verbatim the number the other two call stale.
**Consequence:** Understates coverage (26/27 vs 27/27) and quotes a number the project's own newer measurement superseded. Lower severity than P0-1/P0-2 because the magnitude of the discrepancy is small (0.02 percentage points, one part) and doesn't change any conclusion about the player's status.
**Fix:** Update to 99.25% / 27 of 27 parts, or trim to a pointer.

### P1-2 · ROMUZAK.md's own header omits its native Stage B result — undersells a byte-perfect achievement

**Locations:** `docs/players/ROMUZAK.md:1-16` (header) vs `docs/players/ROMUZAK.md:131-164` (same file, later)
**Claim:** Header (lines 13-16): *"**Status:** notes + song-order (orderlist) are byte-exact vs the original siddump ... Sounds are decoded structurally ... **Stage A**, transpile to the stock **Driver 11** SF2, like FC and Galway."*
**Verified by:** Read the full header, then grepped the rest of the file and read lines 131-164.
**Actual:** Line 154, same file: *"**Result — both tunes, full song loop: BYTE-PERFECT. freq + waveform + pulse + AD-SR ="* — a working, byte-perfect **native Stage B driver** (`drivers_src/romuzak/romuzak_driver.asm`), matching `ACCURACY_MATRIX.md:55`'s *"byte-exact wf/pulse/AD-SR (~98-100%)"*. The header describes only the Stage-A (Driver 11 transpile) state and never mentions Stage B exists.
**Confidence:** HIGH — within a single file, the header contradicts the file's own later, more current content.
**Consequence:** A reader stopping at the header (the doc's stated purpose) would classify ROMUZAK as a Stage-A-only player like Galway/FutureComposer, missing that it is one of the few players with a byte-perfect **native** driver — understating the project's own work.
**Fix:** Update the header to lead with the Stage B / native-driver result, matching the matrix.

### P1-3 · BLACKBIRD.md's own header (post-B22) predates dozens of commits' worth of later fixes (E3-E6) that the matrix already reflects

**Locations:** `docs/players/BLACKBIRD.md:3-13`
**Claim:** *"now ranging 97.4%-99.8% overall post-B22 (mean ~98%, up from B17's 93.9%-98.9%/~97% ...)"* — dated in-line "updated 2026-07-21, post-B22".
**Verified by:** Read the header directly; compared against `ACCURACY_MATRIX.md:61`.
**Actual:** Matrix (reflecting E3-E6, later than B22): *"mean 99.96, 11 of 16 at exactly 100.0, none below 99.8."* Not a small drift — 11 files moved from "somewhere in 97.4-99.8%" to "exactly 100.0%" after the header was written, and the header still leads with the older range as if current.
**Confidence:** HIGH — the header names its own "as of" commit (post-B22); the matrix and the rest of this same file (further down, per its own section headers like "E5 SHIPPED", "E6 SHIPPED") describe later work the header never absorbed.
**Consequence:** Same failure mode as ROMUZAK (P1-2) but on the project's largest, most actively developed player doc — anyone trusting the header specifically undersells the corpus's actual state by ~2 percentage points and misses that 11 files are now byte-exact-equivalent (100.0%).
**Fix:** Re-stamp the header to the matrix's current figures (mean 99.96, 11/16 at 100.0) rather than leaving it pinned to B22. Given the file's length (5,141 lines), this is a header-only edit — the narrative body is explicitly out of scope for this audit.

### P1-4 · README.md's Future Composer row omits Stage B entirely, describing only the older Stage A

**Locations:** `docs/players/README.md:26`
**Claim:** `"Stage A: notes/order trace-validated | SID/Fun_Fun/ ($1800 variant, 5/20)"`
**Verified by:** Read `ACCURACY_MATRIX.md:62` and `FUTURECOMPOSER.md:12-19` directly.
**Actual:** Both the matrix and `FUTURECOMPOSER.md`'s own header (shipped 2026-07-30) lead with: *"Stage B (native, shipped 2026-07-30) ... reaches 14 of 15 corpus voices at exactly 100.0% audible per-frame pitch over full song length."* README.md's row describes only the pre-Stage-B state.
**Confidence:** HIGH — matrix and the player doc's own header agree with each other and both contradict README.md's row.
**Consequence:** Same pattern as P0-1 (Blackbird) and P1-2/P1-3 — README.md's index table is the most stale of the three copies for this player too, describing capability that no longer reflects the shipped state.
**Fix:** Update the row to reflect Stage B, or trim to a pointer.

### P2-1 · README.md's Deenen row undercounts "clean wins" (4 vs 7)

**Locations:** `docs/players/README.md:25`
**Claim:** `"4 clean wins ~100% (10/19 located) + 8 freebies at 100%"`
**Verified by:** Read `ACCURACY_MATRIX.md:64` and `DEENEN.md:11-14` directly.
**Actual:** Both the matrix and DEENEN.md's own header agree: **7** clean wins ("5 at exactly 100/100 onset+pitch, Constant_Runner 100/97.7, Astro 77.4/91.5"). README.md's "4" is the outlier.
**Confidence:** HIGH — two independent sources (matrix, player doc) agree with each other and disagree with README.md.
**Consequence:** Understates the player's progress by 3 files. Lower severity than the P1 items because the "located"/"freebies" numbers (the more load-bearing figures) are correct in all three places — only the "clean wins" sub-count is off.
**Fix:** Correct to 7, or trim to a pointer.

---

## Duplicated facts

The root cause behind every finding above: **every player's headline accuracy figure is
stored in THREE places**, not two — `ACCURACY_MATRIX.md`, the player's own doc header, and
`docs/players/README.md`'s index table row. The matrix was updated for this session's own
work (v3.23.0 re-stamp, commit `fe9846b`); the other two copies were not checked and several
had already drifted independently of anything done this session.

| Fact | Locations | Currently agree? | Canonical source (per this session's decision) |
|---|---|---|---|
| Hubbard filter status | `ACCURACY_MATRIX.md`, `HUBBARD.md`, `HUBBARD_V2_PLAN.md`, `README.md` | **NO** — 3 of 4 still say "100%" | `ACCURACY_MATRIX.md` |
| Sound Monitor corpus % | `ACCURACY_MATRIX.md`, `SOUNDMONITOR.md`, `README.md` | **NO** — README.md stale | `ACCURACY_MATRIX.md` |
| Blackbird corpus status | `ACCURACY_MATRIX.md`, `BLACKBIRD.md` header, `README.md` | **NO** — all 3 disagree with each other at 3 different staleness levels | `ACCURACY_MATRIX.md` |
| ROMUZAK driver status | `ACCURACY_MATRIX.md`, `ROMUZAK.md` header, `README.md` | Matrix/README.md agree; `ROMUZAK.md`'s OWN header is the outlier | `ACCURACY_MATRIX.md` |
| Future Composer stage | `ACCURACY_MATRIX.md`, `FUTURECOMPOSER.md` header, `README.md` | Matrix/doc header agree; README.md stale | `ACCURACY_MATRIX.md` |
| Deenen clean-win count | `ACCURACY_MATRIX.md`, `DEENEN.md`, `README.md` | Matrix/doc agree; README.md is the outlier | `ACCURACY_MATRIX.md` |
| Every other player's headline % (Laxity, Driver11, NP20, Galway, MoN, SDI, Kimmel, Matt Gray) | `ACCURACY_MATRIX.md` + player doc header + `README.md` row, all 3 | **YES**, currently consistent | `ACCURACY_MATRIX.md` (still worth trimming the other 2 copies, since agreement today doesn't prevent drift tomorrow — that's what happened to every finding above) |

**Structural note:** `docs/players/README.md`'s table is the most-drifted single location, in 4 of
6 divergent rows (Blackbird, Sound Monitor, Future Composer, Deenen). It is also the
project's own player-family INDEX (its stated job, line 1), so it gets read by exactly the
audience most likely to trust a summary table over a detail page — the worst place for
drift to concentrate.

---

## Verified clean

- `FUTURECOMPOSER.md`'s own header (as opposed to `README.md`'s stale row) — matches the
  matrix exactly ("14 of 15 corpus voices at exactly 100.0%"). Verified by direct read of
  both.
- `MON.md`'s header — matches the matrix ("100% byte-exact ... Hawkeye sub 2/3 ...
  98-100% on all four registers except Supremacy's ~86-92%"). Verified by direct read.
- `GALWAY.md`'s calibrated blockquote (line 45-47, "30/40 objectively clean in real SF2II")
  — matches the matrix exactly. Note: the doc's OWN status line just above it (line 6, "37
  trace-faithful ... 0 blocked") uses a different, superseded headless metric alongside the
  corrected one, without the matrix's own explicit caveat ("The earlier headless '37
  faithful' overstated — the objective per-voice metric is the truth" — this exact sentence
  lives in `CLAUDE.md`, not in `GALWAY.md` itself). Flagged here rather than as a numbered
  finding because it is not factually wrong, just under-caveated relative to the matrix.
- `LAXITY.md`, `MATTGRAY.md`, `KIMMEL.md`, `SDI.md`, `DEENEN.md` (its own header, as
  opposed to `README.md`'s row), `SOUNDMONITOR.md` (its own header) — all verified
  consistent with the matrix by direct read.
- `DRIVER11.md`, `NP20.md` — small files, both consistent with the matrix.

---

## Unverifiable

None — every claim in scope (headline accuracy percentages) was checkable directly against
`ACCURACY_MATRIX.md`'s text. No claim required running a build or measurement tool, so the
"defer to the project's verification agent" step did not apply here; the matrix already
carries that provenance (adversarial-audit-verified rows are marked as such).

---

## Learnings

### Near-misses

| Expected | What actually happened | Why the check failed | Belongs in |
|---|---|---|---|
| Trimming player docs' headline numbers to a pointer would only remove *duplication* | Several headers were also independently *stale/wrong* relative to the matrix, in both directions (overselling Hubbard's filter, underselling Blackbird/ROMUZAK/FutureComposer) | The task was framed as "find duplication to trim," which primed a search for matching pairs — the drift was found only because each pair was actually compared value-by-value rather than assumed equal | `references/drift-catalog.md` — "duplication audits should diff, not just locate" |

### Environment notes

None — no shell/OS surprises this run; all reads were plain `Read`/`Grep`.

### Rule gaps

| Situation | What the rules say | What was actually right | Belongs in |
|---|---|---|---|
| A very large file (BLACKBIRD.md, 5,141 lines) inside an otherwise-small doc set (21 files, ~9.7K lines total) | "Under ~20 files / ~150 KB: read every file completely. No tiering." — this set is 21 files and the total *is* under 150KB of the SHORT files, but one file alone is 410KB | Read only the header/status block of the large file, matching the user's own explicit scope ("do NOT touch narrative/session-log content") rather than either reading all 5,141 lines or skipping the file entirely | `references/verification.md` — scoped audits (a user-named subset of claims, not "everything") may legitimately read less than a full file when the claim type (headline status) is knowably confined to the header |

### Cross-project signal

This project already had ONE instance of exactly this pattern self-diagnosed and fixed
mid-session (`SOUNDMONITOR.md`'s own text: *"the 'parts 2–6 at 100.0' claim in CHANGELOG
v3.19.0 → CLAUDE.md → the accuracy matrix was wrong; corrected 2026-07-16"*) — a 3-hop
propagation chain, the same shape as this audit's findings. A project that has caught this
pattern once and still has 6 more live instances of it suggests the fix needs to be
structural (single source + trimmed pointers, which is exactly this session's plan) rather
than another one-off correction — the same conclusion the earlier `CLAUDE.md` compression
session reached for a different pair of documents.

---

## Structural observations

- The project's own established pattern for this exact problem (CLAUDE.md's Known
  Limitations table, compressed in commit `c09fd9c` this repo's history) is directly
  reusable here: verify each caveat survives elsewhere before trimming, then replace the
  duplicate headline with a compact pointer.
- `docs/players/README.md`'s table is structurally the same kind of "convenience summary
  that duplicates a canonical source" as CLAUDE.md's former Known Limitations table was —
  and it has drifted the same way, for the same reason (nobody re-derives it, everyone
  hand-edits it when something changes and sometimes misses a copy).

---

## Recommended order

1. **P0 fixes first** (Blackbird README row, Hubbard "filter 100%" in 3 places) — these are
   actively misleading in opposite directions (one hides a shipped feature, one claims an
   unearned one).
2. **P1 fixes** (Sound Monitor/ROMUZAK/Blackbird-header/FutureComposer staleness) — real but
   lower-consequence drift.
3. **P2 fix** (Deenen count) — smallest discrepancy.
4. **Duplication trim** for the remaining, currently-consistent player docs — apply the same
   one-line-pointer treatment even though they agree today, since every P0-P2 finding above
   started as an agreeing pair that drifted later.
