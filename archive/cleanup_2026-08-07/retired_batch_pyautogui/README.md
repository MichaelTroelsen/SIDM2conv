# Cleanup 2026-08-07 — retired batch-pyautogui launcher

## test-batch-pyautogui.bat

Launcher for `pyscript/test_batch_pyautogui.py`, which was itself archived
on 2026-04-29 (`archive/cleanup_2026-04-29/skip_tests/test_batch_pyautogui.py`)
because it required `output/` fixtures that were archived in the same cleanup.
The launcher `.bat` wasn't archived alongside it, so it (and the CI workflow,
and seven doc files) kept pointing at a script that no longer existed:

- `.github/workflows/batch-testing.yml`'s `Batch Testing Unit Tests` job
  `open()`'d the archived path directly, hard-failing every run once an
  unrelated fix (bumping the deprecated `actions/upload-artifact@v3`) let
  the workflow actually reach that step instead of failing earlier.
- `CLAUDE.md`, `README.md`, `docs/CI_CD_SYSTEM.md`, `docs/FILE_INVENTORY.md`,
  `docs/guides/BEST_PRACTICES.md`, `docs/guides/FAQ.md`,
  `docs/guides/GETTING_STARTED.md`, `docs/guides/TROUBLESHOOTING_FLOWCHARTS.md`,
  and `docs/guides/TUTORIALS.md` all still documented `test-batch-pyautogui.bat`
  as a working command (TUTORIALS.md had an entire dedicated tutorial for it,
  renumbered out when removed).

`batch-testing.yml` still validates the underlying automation modules
(`pyscript/sf2_pyautogui_automation.py`, `sidm2/sf2_editor_automation.py`) —
those are unarchived and still functional. Only the standalone batch-runner
CLI and its launcher are retired.

If the batch-runner is wanted back, restore this file plus
`archive/cleanup_2026-04-29/skip_tests/test_batch_pyautogui.py`, and its
`output/` fixture directory would need reconstructing too.
