"""
Tests that LaxityConverter.DRIVER_PATH resolves regardless of the process's
current working directory.

DRIVER_PATH used to be a class attribute set to Path('./drivers/laxity/...'),
which resolves relative to cwd. Any consumer constructed from a working
directory other than the repo root got FileNotFoundError. It is now anchored
on __file__.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sidm2.laxity_converter import LaxityConverter

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_driver_path_is_absolute_and_anchored_on_file():
    assert LaxityConverter.DRIVER_PATH.is_absolute()
    expected = REPO_ROOT / 'drivers' / 'laxity' / 'sf2driver_laxity_00.prg'
    assert LaxityConverter.DRIVER_PATH == expected
    assert LaxityConverter.DRIVER_PATH.exists()


def test_construct_from_different_cwd(monkeypatch, tmp_path):
    """The real regression case: construct LaxityConverter from a cwd that is
    NOT the repo root, and confirm the driver still resolves instead of
    raising FileNotFoundError."""
    monkeypatch.chdir(tmp_path)

    converter = LaxityConverter()

    assert converter.driver is not None
    assert len(converter.driver) > 0
