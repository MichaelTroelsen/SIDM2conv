---
name: bump-version
description: Bump the SIDM2 package version and re-stamp every documented copy of it — README, CLAUDE.md, ACCURACY_MATRIX, STORY, the build dates and the CHANGELOG heading — then run the test that pins them together. Use for any release; the manual version has shipped half-done twice.
disable-model-invocation: true
---

# Bump the version, all five copies at once

The version number lives in **five** places plus two build dates plus a
CHANGELOG heading. `sidm2/__init__.py` is canonical; the rest are banners a
human has to remember. Twice they were not remembered:

* `docs/reference/ACCURACY_MATRIX.md` sat at v3.22.0 **through** the v3.23.0
  release.
* `README.md`'s banner sat at v3.22.0 for **four** releases — 3.23.0, 3.24.0,
  3.25.0, 3.26.0.
* v3.25.0 bumped the version but left the entries under `## [Unreleased]`, so
  the CHANGELOG had no heading for the release it had just cut.

`pyscript/test_version_stamps_agree.py` now makes those failures red instead of
shipped. This skill is the other half: it performs the bump so the test has
nothing to catch.

## Procedure

**1. Dry-run first.** It prints every substitution and writes nothing.

```bash
py -3 .claude/skills/bump-version/bump.py 3.29.0 --dry-run
```

**2. Apply.** Add `--release-unreleased` to promote the CHANGELOG's
`## [Unreleased]` heading to this version and open a fresh one above it; leave
it off if you want to write the release entry by hand.

```bash
py -3 .claude/skills/bump-version/bump.py 3.29.0
```

It runs `test_version_stamps_agree.py` itself and **exits non-zero if the bump
is half-done** — including when the stamps agree but the CHANGELOG heading is
still missing.

**3. Write the release entry.** The script moves headings; it does not write
prose. `CHANGELOG.md` is the canonical history and `STORY.md` is the narrative —
per CLAUDE.md, append to STORY's per-version index, and touch its Eras or
deep-tech sections only if a new architectural finding warrants it.

**4. Update what actually changed.** The Known Limitations table in CLAUDE.md
and the relevant `docs/players/*.md` — only if behaviour moved. A version bump
is not a licence to refresh figures that were not re-measured; a doc-carried
number stays doc-carried and says so.

**5. Run the suite.** `test-all.bat`, or at minimum
`py -3 -m pytest pyscript/ -q`.

## Why the script does not list the stamped files

It imports `STAMPS` and `DATE_STAMPS` from the test. A hard-coded list here
would be a **sixth** copy of the same fact, going stale exactly the way
ACCURACY_MATRIX.md and README.md each did — which is the failure the test was
written to end. To add a stamped location, add a row to `STAMPS` in
`pyscript/test_version_stamps_agree.py`; this skill picks it up unchanged.

## Line endings

Files are read and written with `newline=""`, so only the version characters
change. This matters: the repo has no `.gitattributes`, `core.autocrlf` is true,
and CLAUDE.md is CRLF while other docs are not — rewriting one with the wrong
endings turns a three-character change into a whole-file diff.

## What this never does

It does not commit, tag, push, or open a PR. The bump is left in the working
tree and the release is yours to make.
