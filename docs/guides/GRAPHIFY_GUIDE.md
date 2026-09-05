# Graphify Code Graph — Usage and Two Silent Failure Modes

**Status**: current as of 2026-09-05. Covers `graphify-out/` in this repo, the
`.graphify_root` repair, and — more importantly — why a *negative* answer from
the `graphify` CLI is not evidence of anything.

`graphify` builds a code graph of the repo into `graphify-out/`. It is a
supplement to this project's own code-research tooling (tokensave), not a
replacement: use whichever actually answers the question in front of you.

---

## The short version

```bash
py -3 pyscript/graphify_root_fixup.py --check   # is the graph queryable here?
py -3 pyscript/graphify_root_fixup.py           # repair it if not
```

Then, for any structural question, **read `graphify-out/graph.json` directly**.
Do not take `graphify path` or `graphify query` at their word when they say
*no* — see "Failure mode 2".

---

## Failure mode 1: a root path that Windows cannot resolve

`graphify` records the directory it extracted as a bare path in
`graphify-out/.graphify_root`. Run `graphify extract` from **Git Bash** and the
recorded value is POSIX-style:

```
/c/Users/mit/claude/c64server/sidm2
```

Windows `pathlib.Path()` parses that as a **drive-relative** path whose root
directory is named `c`, which does not exist. Nothing raises. graphify carries
on and answers queries against a root it cannot resolve, so the result is an
empty graph reported as a normal, successful, empty answer.

**That silence is the whole problem.** A stale root does not look like a
misconfiguration; it looks like a clean result. Two `/runqueue` cycles here
stopped on a `touches` list naming the wrong file because a cross-check came
back empty and was believed.

### Why the repair does not stay repaired

`.gitignore` ignores `graphify-out/` wholesale — it is ~37 MB of rebuildable
cache plus a bundled HTML report. So the repaired `.graphify_root` is
**untracked by construction**:

* it does not survive a fresh clone, and
* anyone who re-extracts from Git Bash re-breaks it.

A repair stored inside the directory it repairs is not durable. Hence
`pyscript/graphify_root_fixup.py`, which is tracked, derives the correct root
from **its own location** (`Path(__file__).parent.parent`), and is therefore
correct in any clone on any machine without being edited.

It is conservative on purpose:

* a value that already **resolves to this repo** is left alone, even if it is
  spelled with different case — graphify itself wrote `SIDM2` for a directory
  named `sidm2`, and rewriting that is churn;
* it writes the path with **no trailing newline**, matching graphify's own
  output (35 bytes for a 35-character path);
* a clone with no `graphify-out/` at all reports `absent`, not `broken` — an
  un-built cache is not a defect.

Tests: `pyscript/test_graphify_root_fixup.py`.

---

## Failure mode 2: the CLI's negatives are not evidence

**This is the one that costs real time, and repairing the root does not fix
it.**

Measured in this repo: the import edge

```
bin_build_sdi_native_song  ->  bin_build_mon_native_song
```

**is present** in `graph.json`'s `links` array. Yet with a correctly resolved
root and the correct underscore node ids, `graphify path` reported *"no
directed path"* in **both** directions. And:

```
graphify query "what depends on bin/build_mon_native_song.py"
```

returned `ROMUZAK_SF2_DRIVER_PLAN.md` and `build_galway_digi_songs.py` —
neither of which is a dependent.

So:

> **A negative from `graphify path` or `graphify query` means NOTHING.**

The matcher is fuzzy label/substring, not exact-path lookup. A query for a file
the structural extraction does not cover can silently return unrelated
same-word nodes instead of failing loudly. Always confirm a returned node's
`source_file` is actually the path you asked about.

### The method that does work

1. Read `graphify-out/graph.json` and use its `links` array directly.
2. Map node ids to files via each node's `source_file` field.
3. Treat a cross-file edge as a **prompt to look**, never as a conclusion.
4. **Confirm with grep** before acting on it — in particular before widening a
   task's `touches` on the strength of an edge.

Steps 3 and 4 are not ceremony. The graph is a lead generator; the source is
the authority.

---

## Rebuilding

`graphify update` re-extracts changed **code** files with no LLM call, so it
does not need an API key and is cheap enough to run routinely. A full
`/graphify` build is the expensive path and is only needed when the graph is
absent or the extraction itself changed.

If you rebuild from Git Bash, run the fixup afterwards — that is exactly the
sequence that re-introduces failure mode 1.

---

## See also

* `pyscript/graphify_root_fixup.py` — the repair, with the reasoning inline
* `pyscript/test_graphify_root_fixup.py` — the tests, including the vacuous one
  that a mutation caught
* `CLAUDE.md` → "Context economy" — prefer targeted lookups over broad searches
