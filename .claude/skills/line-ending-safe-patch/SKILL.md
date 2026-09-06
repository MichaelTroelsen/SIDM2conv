---
name: line-ending-safe-patch
description: Patch a source file without corrupting its line endings. Use when editing any file in this repo via a script, heredoc or generated patch — endings are per-file here (CRLF and LF both appear), and a mismatched write produces a whole-file diff that hides the real change.
disable-model-invocation: true
---

# Line-ending-safe patching

This repo has **no `.gitattributes`** and `core.autocrlf` is true, so line
endings are a **per-file** property. Both conventions are in active use:

| Convention | Examples |
|---|---|
| CRLF | `sidm2/conversion_pipeline.py`, `sidm2/sequence_translator.py`, `sidm2/dmc_parser.py`, `bin/build_mon_native_song.py`, `CLAUDE.md`, `.mcp.json` |
| pure LF | `bin/build_sdi_native_song.py`, `bin/build_hardtrack_native_song.py`, `pyscript/test_mon_filter.py`, most `pyscript/test_*.py`, `.claude/settings.json` |

Write `\n` into a CRLF file and git reports the **whole file** as changed. The
diff becomes unreviewable and the actual change is invisible inside it.

## Procedure

**1. Detect before you write.**

```bash
py -3 .claude/skills/line-ending-safe-patch/endings.py <file>
```

**2. Write in the file's own convention.** Build the replacement text with `\n`,
then convert once at the end if the file is CRLF:

```python
s = open(p, 'r', encoding='utf-8', newline='').read()   # newline='' preserves them
new_block = new_block.replace('\n', '\r\n')             # only if the file is CRLF
open(p, 'w', encoding='utf-8', newline='').write(s)     # newline='' again
```

`newline=''` on **both** the read and the write is what stops Python translating
endings behind you.

**3. Verify by counting bytes.**

```bash
py -3 .claude/skills/line-ending-safe-patch/endings.py <file> --expect crlf
```

## The two traps, both of which have cost real time here

**`grep -c '\r'` is not a line-ending test.** It counts *lines containing* a
carriage return. On a 549-line pure-LF file it answered **549**, which reads as
"uniformly CRLF". Only byte counts are reliable:
`data.count(b"\r\n")` vs `data.count(b"\n") - data.count(b"\r\n")`.

**A partial replacement mixes the file.** Converting only the block you inserted
leaves the rest untouched — correct. Converting the *whole file* when you only
meant to fix your block rewrites every line. If you do need a full normalise,
round-trip it: `b.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")` for CRLF, or
just the first `replace` for LF. Never chain them the other way.

## If the file ends up mixed anyway

The `check_line_endings` PostToolUse hook warns with the counts. Normalise with
the round-trip above and re-verify with `endings.py`. Do not commit a mixed file:
`core.autocrlf` will renormalise it on the next checkout and the diff will move
again.

## Related

- A **NUL byte** anywhere makes git treat the file as binary and report a
  whole-file diff regardless of endings. If a diff looks like a full rewrite and
  the endings are uniform, check for `\x00` — it has happened here, from a
  heredoc that ate an escape.
