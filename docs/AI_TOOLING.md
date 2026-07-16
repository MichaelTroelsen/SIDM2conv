# AI tooling design — skills, subagents, workflows

**Status:** DESIGN — for review. Nothing here is built yet.
**Date:** 2026-07-16 · **Version:** v3.21.0

This proposes what SIDM2 should put in `.claude/`. It is deliberately a design
doc first: the shape matters more than the code, and the wrong shape here
produces confident wrong answers at scale.

---

## 1. The invariant everything serves

> **A fidelity claim must never outrun its evidence. Never ship lossy output silently.**

SIDM2's unit of truth is **a measured claim about a binary** — not a document,
not a plausible engine model. Everything below exists to keep claims and
evidence attached to each other.

Prior art: `sid-reference-project/.claude/` already runs a
`research` → `falsify` pair (`sid-card-research`, `sid-card-falsify`,
`/sid-card`) and it works — 200 KB cards. **This design borrows its structure
and its discipline, not its content.** That project's unit is a *document*, so
its falsifier fetches URLs. Ours is a *binary*, so ours re-runs traces. Copying
its evidence rules over would produce an auditor that checks the wrong things.

## 2. Why this repo, specifically

This is not speculative. Every item is a real, named failure from this project's
history — see `STORY.md`'s museum of metrics that lied, and §4's trust rules in
`docs/players/PLAYBOOK.md`:

| Real failure | Cost |
|---|---|
| The zig64 gate compared two empty traces and returned True | Certified 64 zero bytes as byte-identical to `Broken_Ass.sid` (v3.21.0) |
| siddump's SBC carry bug | A wrong 16-bit vibrato **project-wide**; byte-exact metric, wrong sound |
| Headless metrics overstating | Galway "37 faithful" → **30/40** under the objective real-SF2II metric |
| Gate-onset metric on a legato engine | Kimmel reads ~**0%** on a *perfect* decode |
| SDI "multispeed" false locates | Six files at 0.0 — a wrapper matched variant D's bytes exactly, different engine |
| MoN default subtune 3 | A mis-located speed table producing **confident garbage** (speed=155) |

Each looked like a result. None was. That is exactly what an independent
adversary is for — and what a lone main-loop session, optimising for a finished
answer, is worst at.

## 3. The three layers

Pick by **what the thing needs**, not by what it's about.

| Layer | Use when | SIDM2 examples |
|---|---|---|
| **Skill** | The *main loop* needs a method it doesn't have in context | `porting-playbook`, `fidelity-metrics` |
| **Subagent** | You need **independence** (an auditor that cannot fix its own findings) or **context isolation** (a corpus dump that must not enter the main thread) | `sidm2-fidelity-falsify`, `sidm2-corpus-sweep` |
| **Workflow** | Deterministic **fan-out** over a known work-list | corpus sweep over 348 SDI / 88 DMC / 95 RSID |

The distinction that matters: a skill *informs* the session; a subagent *replaces*
part of it. `/sid-card`'s constraint says it best — *"do not defeat the subagent
by reading the card back into the main thread."*

---

## 4. `sidm2-fidelity-falsify` — the centrepiece

**Read-only. Opus. It attacks one claim and cannot repair what it finds.**

```
tools: Read, Grep, Glob, Bash        # Bash to RE-RUN measurements, not to edit
model: opus
```

Input: one claim, in the form the project actually states them —
*"Kimmel Radax v0 = 100% frame-pitch"*, *"Deenen B_A_T 100/100"*,
*"SM corpus strict 99.23%"*.

Its burden of proof is inverted, exactly as the sibling project's is: **default
to REFUTED**. "I could not reproduce this" is a finding, not a dead end.

### `<what_to_attack>` — the named traps (ranked by damage if wrong)

This list is the agent's real value. Every entry is a trap this project has
already fallen into at least once.

**Severity 1 — the metric is vacuous (the claim measures nothing):**
1. **Empty-vs-empty.** Did anything actually get compared? `len(0)==len(0)` is
   not a match, it is "no test ran". *(the v3.21.0 gate bug)*
2. **Post-end silence.** `$FE`-halting subtunes score garbage against silence —
   compare only over the real song length. *(PLAYBOOK §4)*
3. **Window too short.** 0 writes at 5 frames vs 460 at 200 is the same file.
   *(Arkanoid)* Re-run at ≥200 frames before believing any zero.
4. **Dead/silent voice** counted as agreement.

**Severity 2 — the metric is wrong for this engine:**
5. **Gate-onset on a legato engine** → ~0% on a perfect decode. *(Kimmel)*
   Conversely, frame-pitch on a percussive engine hides onset drift.
6. **Skew vs content.** ±1-frame write jitter reads 47.7 strict / 100.0
   skew-tolerant and is *audibly exact*. Which is being claimed?
7. **Small n.** Rhaa v2's "92.9%" is **n=14**. One note moves it 7 points.
   Demand n alongside every percentage.
8. **Best-global-offset fitting.** How many free parameters bought this number?

**Severity 3 — the decode is confidently wrong:**
9. **Pseudo-parse.** Output that parses and is garbage. *(MoN subtune 3)*
10. **False locate.** Right byte pattern, wrong engine. *(SDI multispeed)*
    Content-verify the location, don't trust the signature.
11. **One-file generalization.** *(the DRAX lesson — never generalize from one file.)*

**Severity 4 — the tooling lied:**
12. **The capture CPU.** Byte-exact registers + wrong sound → suspect the
    tracer, not the model. *(the SBC carry bug)* Cross-check py65 + VICE.
13. **Cross-tool mixing.** zig64 and vsid agree on the (register, value)
    *sequence* but their **frame attribution is offset by 1** — a mixed
    comparison diverges on every row. *(found 2026-07-16)*
14. **Headless vs the real driver.** Only the objective real-SF2II metric is
    the truth. *(Galway 37→30)*

### Output

The sibling's format is right and should be kept: a table, most severe first,
one row per claim examined; verdicts `REFUTED` / `UNSUPPORTED` / `NOT-REPRODUCED`
/ `CONFIRMED` (= "I actively tried to break it and could not — here is what I
checked"). Plus: *"Finding nothing is a valid and useful result; do not
manufacture concerns to appear thorough."*

### Must never
- Edit anything. An auditor that repairs its own findings is not independent.
- Accept a number because a doc, a memory file, or a commit message says it.
  **Re-run it.** (This session: two `bin/` paths in the "single source of truth"
  accuracy matrix did not exist. Only re-running caught them.)
- Flag an honest `TODO` / documented residual as a defect. A refused decode is
  the system working — `plausible()` rejecting garbage is a feature.

---

## 5. `porting-playbook` skill

`docs/players/PLAYBOOK.md` (the staged method) + `docs/players/PATTERNS.md` (the
named technique catalog) + `sidm2/player_idioms.py` (the tested locate library)
are **already written as a method** and 11 players prove it repeats. Today they
are only used if someone remembers to read them.

As a skill they load on demand for any new-player work — Stage A/B staging, the
size caps, the locate idioms, the gotcha table. Cheapest thing here to build and
immediately useful on the next player (Deenen Variant-B).

**Must never:** duplicate the docs. The skill should *point at* PLAYBOOK/PATTERNS
and carry only the decision procedure. Two copies of the method is how a method
rots.

## 6. `sidm2-corpus-sweep` subagent + workflow

Two different things, both needed:

- **Subagent** (read-only): sweep a corpus, return **a report, not the dump**.
  The context-isolation case — 348 per-file results must never enter the main
  thread. My RSID sweep this session was ~5 min serial across 95 files and its
  raw output was pure noise; the *finding* was two numbers.
- **Workflow**: the deterministic fan-out — `pipeline(files, validate, verify)`.
  The corpora are embarrassingly parallel and slow. This is the textbook case.

**Must never:** silently cap coverage. If a sweep drops files (top-N, sampling,
no-retry), it must **say what it dropped**. Silent truncation reads as "covered
everything" — which is the same lie class as the empty trace.

## 7. Commands (the thin orchestration layer)

| Command | Does |
|---|---|
| `/falsify <claim>` | one falsifier run; relay the verdict; never auto-fix |
| `/verify-claims <player>` | re-run a player's documented numbers vs the code, report drift *(what I did by hand for Kimmel/Deenen this session — it should be one command)* |
| `/port-player <name>` | the PLAYBOOK staged pipeline, with a falsify gate before Stage B |

Follow `/sid-card`'s constraints: run research→falsify **sequentially**; **relay,
don't re-read**; **never auto-fix** a falsifier finding — what the truth actually
is can be a judgement call.

## 8. What NOT to build

- **A "fix-the-findings" agent.** The falsifier's value is that a human decides.
- **A player-porting *subagent*.** Porting is exploratory, multi-day, and
  needs the user's ear (*"notes fine, fidelity not there"* is unreproducible
  headless). Skill, not agent.
- **Anything that writes docs unsupervised.** This session produced two wrong
  paths in one doc; an unsupervised writer produces them at scale.
- **A KB-card agent here.** `sid-reference-project` already owns that surface.
  Don't fork it.

## 9. Open questions for review

1. **Does the falsifier get `Bash`?** It needs it to *re-run* measurements —
   that's the whole point — but Bash is a write vector (it could edit via
   `sed`). Options: trust the prompt constraint (what the sibling does), or
   restrict to a validated allowlist. **Recommendation: trust the constraint,
   as the sibling already does; revisit if it ever misbehaves.**
2. **Model tiers.** Falsifier on opus (it must be smarter than the thing it
   audits); sweep on sonnet/haiku (mechanical).
3. **Does `/verify-claims` gate the release?** It could run at every version
   bump so the accuracy matrix can never rot 8 versions again.
4. **Scope of `fidelity-metrics`** — separate skill, or folded into
   `porting-playbook`?

## See also

`docs/players/PLAYBOOK.md` §4 (the measurement ladder + trust rules) ·
`docs/players/PATTERNS.md` (diagnostics, failure classes) · `STORY.md` (why
each trap has a name) · `sid-reference-project/.claude/` (the working prior art)
