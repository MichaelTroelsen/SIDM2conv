# Cleanup 2026-05-09

## broken_imports/

Two `pyscript/` files that imported `disassembler_6502` — a module
that was itself archived to
`archive/cleanup_2026-01-02/obsolete_utils/disassembler_6502.py`
months ago. The dependent files weren't archived alongside it, so
they accumulated as `ModuleNotFoundError`-on-import dead code:

- `test_disassembler.py` (16.4 KB) — pytest test suite for the
  archived disassembler. Was already excluded from CI runs via
  `--ignore=pyscript/test_disassembler.py` in CLAUDE.md and several
  doc references; the exclude was a workaround, not the actual fix.
  Archived now so the exclude can be removed.

- `quick_disasm.py` (3 KB) — CLI wrapper around the archived
  disassembler. Still listed in CLAUDE.md's "Quick Commands" as
  `python pyscript/quick_disasm.py file.sid # Disassemble`, but
  raises `ModuleNotFoundError` on every invocation. Removed from the
  CLAUDE.md command list as part of this cleanup.

If the disassembler is wanted back, restore from
`archive/cleanup_2026-01-02/obsolete_utils/` plus these two files.

## Phantom reference cleanup

`pyscript/test_detection_fix.py` was referenced in
`CLAUDE.md`, `docs/FILE_INVENTORY.md`, and `docs/criterion3_plan.md`
but didn't actually exist on disk. References scrubbed in the same
commit.
