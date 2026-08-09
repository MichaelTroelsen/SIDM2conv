# Documentation Audit — SIDM2

**Audited:** 2026-08-09 · **Commit:** `e6cceba` · **Branch:** master
**Working tree:** clean (0 uncommitted) — findings are reproducible from this commit
**Scope:** SCOPED AUDIT, not a full doc sweep. Commissioned to answer one question: what can
safely be compressed out of `CLAUDE.md`'s two largest sections.
**Findings:** 0 P0 · 1 P1 · 2 P2 · 0 P3
**Confidence:** 3 HIGH · 0 MEDIUM · 0 LOW (LOW is never reported)

---

## What this audit did and did not check

Stated first, because a scoped audit that reads as comprehensive is itself a false claim.

**Checked in full:** `CLAUDE.md` (225 lines / 31.8 KB, read completely), and every path it
references (78 candidates, existence-tested).

**Checked in targeted regions:** `docs/players/MON.md`, `docs/players/DMC.md`,
`docs/reference/ACCURACY_MATRIX.md` — searched and the matched regions read. Not read end to end.

**Tier 3, indexed but NOT read:** the remaining 18 files in `docs/players/` (722 KB total,
`BLACKBIRD.md` alone is 420 KB). Their existence was verified; their contents were not audited.

**NOT checked at all — accuracy percentages.** `CLAUDE.md`'s Known Limitations table is mostly
fidelity figures. This project ships its own verification agent
(`.claude/agents/sidm2-fidelity-falsify.md`), and the audit workflow requires deferring
measurement-shaped claims to it rather than adjudicating them with weaker tools. Verifying them
would also mean running builds and renders with real side effects and long runtimes. **No
percentage in `CLAUDE.md` was confirmed or disconfirmed here.** They are listed under
Unverifiable. This does not affect the compression decision, which turns on duplication and
caveat survival, not on whether a given number is currently right.

---

## Ground truth

Established by execution before any prose was read.

| Fact | Actual value | Source | Confidence |
|---|---|---|---|
| Version | `3.23.0`, build `2026-08-09` | `sidm2/__init__.py` via import | HIGH |
| Tests collected | **2075** (2065 passed, 8 skipped, 2 xfailed) | `pytest --collect-only` | HIGH |
| Commit / tree state | `e6cceba`, clean | `git rev-parse`, `git status --porcelain` | HIGH |
| Project verification agent | `sidm2-fidelity-falsify.md` present | `ls .claude/agents/` | HIGH |
| `CLAUDE.md` size | 225 lines, 31,842 bytes (~7,750 tokens/session) | `wc`, section tally | HIGH |

Section sizes, measured:

| Section | Bytes | % of file | Bytes/line |
|---|---:|---:|---:|
| Known Limitations | 12,925 | 41.7% | ~479 |
| Python Tools | 7,266 | 23.4% | ~269 |
| all others (10 sections) | 10,812 | 34.9% | — |

---

## Findings

### P1-1 · The Known Limitations table duplicates the file CLAUDE.md itself calls the source of truth

**Locations:** `CLAUDE.md` Known Limitations (12,925 bytes, 41.7% of the file) ·
`docs/reference/ACCURACY_MATRIX.md` (14,970 bytes) · 21 files in `docs/players/` (722 KB)

**Claim:** `CLAUDE.md` names `docs/reference/ACCURACY_MATRIX.md` as
*"accuracy source of truth, v3.22.0"* — then carries its own 27-row copy of the same material.

**Verified by:** membership test for 15 player names across both files; `wc -c` on all
`docs/players/*.md`; version stamps read from both `sidm2/__init__.py` and `ACCURACY_MATRIX.md`.

**Actual:** **15 of 15 players appear in both documents.** The duplication is total, not partial.

**Evidence:** Laxity, Galway, Maniacs of Noise, Hubbard, Kimmel, Deenen, Future Composer, Matt
Gray, DMC, Sound Monitor, Blackbird, SID Duzz, ROMUZAK, NP20, Driver 11 — all `YES`/`YES`. Every
one also has a dedicated player doc.

**The copies have already drifted, which is the proof this is a live problem, not a theoretical
one:** `ACCURACY_MATRIX.md` is stamped `v3.22.0` while the shipped version is `3.23.0`. Two of the
three copies are one release stale.

**Confidence:** HIGH — both files read, the version compared against the manifest that ships.

**Consequence:** Three copies of every fidelity figure, updated by hand. The audit-docs premise
applies exactly: the individual mismatches are symptoms; the duplication is the disease. Every
future accuracy change requires three edits, and the evidence says the third gets missed.

**Fix:** Reduce each `CLAUDE.md` row to a one-line verdict plus a link to
`docs/players/<PLAYER>.md`. Keep `ACCURACY_MATRIX.md` canonical for numbers, as `CLAUDE.md`
already declares. Estimated saving ~9–10 KB (~2,400 tokens per session).

---

### P2-1 · `ACCURACY_MATRIX.md` is one version behind the shipped release

**Locations:** `docs/reference/ACCURACY_MATRIX.md` (header) · `CLAUDE.md` (its pointer to it)

**Claim:** both stamp the accuracy matrix `v3.22.0`.

**Verified by:** `import sidm2; sidm2.__version__` → `3.23.0`; regex over the matrix header → the
first version token found is `3.22.0`.

**Actual:** shipped version is **3.23.0** (2026-08-09).

**Confidence:** HIGH — read from the manifest that ships and from the doc itself.

**Consequence:** A reader treating the matrix as current gets v3.22.0-era figures. Mild on its
own; it is listed separately because it is the *observable symptom* of P1-1 and the reason that
finding is P1 rather than P3.

**Fix:** Re-stamp on version bump, or drop the stamp and let git date it. Note that `CLAUDE.md`'s
own "On Version Bump" rule does not currently list `ACCURACY_MATRIX.md` among the files to update
— which is why it was missed.

---

### P2-2 · CLAUDE.md's footer misstates its own size

**Location:** `CLAUDE.md:225`

**Claim (verbatim):** ``**Lines**: ~215 (version history moved to CHANGELOG.md) | **For full docs**: See README.md and docs/``

**Verified by:** `wc -l` → 225; `wc -c` → 31,842.

**Actual:** 225 lines — the line count is nearly right. But at **31.8 KB** the average line is
~141 bytes, and in Known Limitations ~479 bytes. The file stayed within its line budget while its
*content* grew several-fold inside table cells.

**Confidence:** HIGH — both numbers measured.

**Consequence:** The footer reassures a maintainer the file is still compact. Line count is the
wrong metric for a document whose cost is tokens; this is why the growth went unnoticed.

**Fix:** State size in KB or approximate tokens, not lines.

---

## The caveat-survival question (the one that gates the compression)

The commissioning concern was that trimming would lose hard-won corrective caveats. **Tested
directly, with the absence protocol: three independent patterns each, plus a positive control.**

Positive control: `Hawkeye` → 31 hits in `MON.md`; `Balloon` → 6 hits in `DMC.md`. The search
machinery matches, so a zero is meaningful.

| Caveat (as written in CLAUDE.md) | Survives elsewhere? | Evidence |
|---|---|---|
| "read older *filter 100%* figures as **cutoff only**" | **YES — stronger** | `MON.md:136` is a dedicated section heading: ``### `$D418` — two defects that hid under "filter 100%" until 2026-08-07``, followed at `:138` by ``**Read the "filter" percentages above as *cutoff* (`$D415/$D416`) only.**`` |
| "56/88 build-eligible = a **mode count, NOT accuracy**" | **YES — stronger** | `DMC.md:24`: ``> **ELIGIBLE IS NOT AN ACCURACY FIGURE** (2026-07-16 audit).`` |
| "**Every % is window-dependent** — quote the window" | **YES — stronger** | `DMC.md:30`: ``> **EVERY DMC PERCENTAGE IS WINDOW-DEPENDENT, AND THE WINDOW IS A FREE PARAMETER.**`` and `:34` gives the worked numbers |

**All three survive, each in a fuller form than the CLAUDE.md compression.** In every case the
player doc carries the caveat as a bolded standalone statement with its date and supporting
measurement, where CLAUDE.md carries a parenthetical.

**Confidence:** HIGH — patterns run, matches printed and read in context, positive control passed.

**Caveat on this caveat check:** three caveats were tested because three were named. The Known
Limitations table contains further inline warnings that were **not** individually tested. Before
trimming any given row, run the same protocol on that row's warnings. Do not generalise from 3/3
to "all caveats are safe" — that is precisely the inference this skill exists to prevent.

---

## Duplicated facts

| Fact | Locations | Currently agree? | Canonical source should be |
|---|---|---|---|
| Per-player accuracy figures | `CLAUDE.md` · `ACCURACY_MATRIX.md` · `docs/players/*.md` | **NO** — matrix is v3.22.0, ship is v3.23.0 | `ACCURACY_MATRIX.md` (CLAUDE.md already says so) |
| Per-player technical detail | `CLAUDE.md` rows · `docs/players/<PLAYER>.md` | Substantially, where checked | `docs/players/<PLAYER>.md` |
| Corrective caveats | `CLAUDE.md` · player docs | **YES**, player docs are fuller | `docs/players/<PLAYER>.md` |
| Tool descriptions | `CLAUDE.md` Python Tools · each tool's own `Docs:` target | Not individually verified | the linked doc |

---

## Verified clean

Reported so the user knows what was checked, not only what broke.

- **Dead references: ZERO.** All 78 backticked paths in `CLAUDE.md` resolve. An initial pass
  flagged 18 "missing"; all 15 real files were then located repo-wide (`PATTERNS.md` →
  `docs/players/PATTERNS.md`, `audio_tightness.py` → `sidm2/audio_tightness.py`, etc). **The first
  result was a false positive from assuming root-relative paths** — the naive-absence trap, caught
  by the protocol rather than published.
- The remaining 3 are correct by design: `memory/*.md` is documented in CLAUDE.md itself as living
  outside the repo, and `zig-out/bin/...` is an external build path in rebuild instructions.
- **Test count is accurate.** `CLAUDE.md` says `~2,065 tests`; 2065 passed, 2075 collected.
- **Version is consistent** across `sidm2/__init__.py`, `CHANGELOG.md`, `STORY.md` and the
  `CLAUDE.md` header — all `3.23.0` / `2026-08-09`. Only `ACCURACY_MATRIX.md` lags (P2-1).

---

## Unverifiable

| Claim class | Why not verified |
|---|---|
| Every accuracy/fidelity percentage in Known Limitations | Routed to `.claude/agents/sidm2-fidelity-falsify.md` per workflow step 3b. Verifying requires running builds and renders — real side effects, long runtimes — and the project's own agent encodes which denominators and windows are legitimate. **Not confirmed, not disconfirmed.** |
| Behavioural claims in Python Tools (e.g. "100% musical match", "27 tests, cross-platform") | Path existence verified; behaviour not exercised. Test counts per tool not individually run. |
| Contents of 18 `docs/players/*.md` files | Tier 3 — existence verified, contents not read. |

---

## Recommendation

**Compressing is safe, and P1-1 is the reason to do it** — not the token count. The table is a
third copy of a fact the project has already designated a canonical home for, and that copy set
has demonstrably drifted.

Suggested order:

1. **Known Limitations → one line per player + link.** ~9–10 KB saved. Before trimming each row,
   run the caveat protocol on *that row's* warnings, as done here for three.
2. **Add `ACCURACY_MATRIX.md` to CLAUDE.md's "On Version Bump" checklist.** It was missed because
   the rule does not name it — fixing the rule prevents the recurrence, where re-stamping only
   fixes today.
3. **Python Tools → one line each + existing `Docs:` pointer.** ~4–5 KB. Lower priority: its
   claims were not audited, so trim it on a separate pass with its own verification.
4. **Replace the footer's line count with a KB/token figure.**

Do not treat step 1 as mechanical. The evidence says the caveats survive *in the three places
checked*; it does not say that about rows nobody looked at.

---

## Learnings

| Observation | Rule it suggests |
|---|---|
| A path-existence check over `CLAUDE.md` produced 18 false "missing" because it assumed repo-root-relative paths; docs cite bare basenames in prose. | When existence-checking documentation references, resolve basenames repo-wide before reporting absence. Documentation cites names, not paths. |
| `rg` was not directly invocable in this environment (`FileNotFoundError` via `subprocess`), though the Grep tool works. | Prefer the harness's Grep tool, or in-process text search, over shelling to `rg` in a skill that must run cross-platform. |
| A file can stay inside its documented *line* budget while tripling in bytes, because prose migrated into table cells. | Size guidance for context-loaded files should be stated in bytes or tokens. A line count cannot see this failure mode. |
| The project's "On Version Bump" checklist omits the very file it elsewhere calls the accuracy source of truth. | When a doc names a canonical source, check that the project's own update ritual includes it. A canonical source outside the update path will drift by construction. |
