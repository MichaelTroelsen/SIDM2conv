#!/bin/bash
# SessionStart hook for Claude Code on the web.
# Installs the Python test/lint dependencies so tests and linters run.
set -euo pipefail

# Only run in the remote (Claude Code on the web) environment.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"

echo "[session-start] Installing Python dev/test dependencies..."

# Best-effort pip upgrade; the system pip may be distro-managed (not uninstallable).
python -m pip install --upgrade pip || echo "[session-start] pip upgrade skipped (distro-managed pip)"

# Dev/test tooling: pytest (test suite), pytest-cov (CI coverage flags),
# pyflakes (the project's undefined-name gate), flake8 (CI lint).
python -m pip install pytest pytest-cov pyflakes flake8

# Project dev requirements (pytest + pyflakes pins), if present.
if [ -f requirements-dev.txt ]; then
  python -m pip install -r requirements-dev.txt
fi

# Note: requirements.txt holds only optional PyQt6 GUI deps (heavy, not needed
# for the stdlib-only converter, tests, or linters) so it is intentionally
# skipped here. Install it manually if working on the GUI tools.

echo "[session-start] Done."
