"""Archived tests -- NOT collected by this repo's pytest.ini (--ignore=archive).

This file exists so pytest names these modules by their PACKAGE PATH rather than
by BASENAME. Two files here collide with live tests by basename:
  archive/cleanup_2026-04-29/skip_tests/test_audio_export_wrapper.py
  archive/python_cleanup_2025-12-21/scripts_tests_old/test_sf2_player_parser.py
Without __init__.py, rootdir-relative basenames are the module names, so pytest
raises "import file mismatch ... use a unique basename" the moment archive/ is
collected alongside pyscript/ -- which happens to anyone whose own pytest.ini
displaces this one, since --ignore=archive lives in addopts and does not travel.

Fixing the CAUSE here rather than hiding archive/ from collection: a root
conftest.py would work but is forbidden by CLAUDE.md Critical Rule #1 (no .py in
the repo root), and a conftest under pyscript/ cannot reach a sibling directory.
"""
