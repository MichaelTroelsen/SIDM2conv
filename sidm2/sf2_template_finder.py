"""Locate SF2 driver / template files on disk.

Extracted from sf2_writer.py at the v3.5.43 refactor.

# What this module does

SIDM2 ships several SF2 driver templates and bundled examples. When
the converter needs a base SF2 to splice music data into (the legacy
"driver11 template" path), it has to find a usable template on the
host filesystem. Search behavior varies by driver type:

  - `driver11`  — prefers the bundled `G5/examples/Driver 11 Test -
    Arpeggio.sf2` (correct table addresses); falls back to project-
    local + a Downloads-folder check + legacy .prg drivers (whose
    table addresses are WRONG for SF2II but still parse).
  - `np20`      — bundled `G5/drivers/sf2driver_np20_00.prg` etc.
  - `laxity`    — `drivers/laxity/sf2driver_laxity_00.prg`

`d11` and `11` are accepted as aliases for `driver11`.

# Public API

  find_template(driver_type='driver11') -> Optional[str]
    Return the first existing path from the per-driver-type search
    list. None if no template found.

  find_driver() -> Optional[str]
    Locate the v1.6 driver (sf2driver16_01.prg). Search-path-only
    utility separate from `find_template` because it has a single
    target file rather than a driver-type-dispatched list.

Both functions are read-only filesystem lookups (os.path.exists +
os.path.isabs). No mutation, no side effects beyond returning
strings.
"""
from __future__ import annotations
import os
from typing import Optional


def _base_dir() -> str:
    """Project root — the directory two levels up from this file."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_template(driver_type: str = 'driver11') -> Optional[str]:
    """Find an SF2 template file to use as a base.

    Args:
        driver_type: Which driver template to look for. Accepts
            'driver11' (preferred), 'np20', 'laxity'. Aliases 'd11'
            and '11' also map to 'driver11'.

    Returns:
        Absolute path to the first existing template file, or None
        if no candidate was found on disk.
    """
    base_dir = _base_dir()

    # Per-driver-type search lists. Order matters — first existing
    # path wins. SF2 example files come before .prg drivers because
    # they have correct table addresses; .prg drivers have wrong
    # addresses but still parse, kept as last-resort fallback.
    driver_templates = {
        'driver11': [
            os.path.join(base_dir, 'G5', 'examples',
                         'Driver 11 Test - Arpeggio.sf2'),
            r'C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master'
            r'\SIDFactoryII\music\Driver 11 Test - Arpeggio.sf2',
            'template.sf2',
            os.path.join(base_dir, 'G5', 'drivers', 'sf2driver11_03.prg'),
            os.path.join(base_dir, 'G5', 'drivers', 'sf2driver11_05.prg'),
            os.path.join(base_dir, 'G5', 'drivers', 'sf2driver11_00.prg'),
        ],
        'np20': [
            os.path.join(base_dir, 'G5', 'drivers', 'sf2driver_np20_00.prg'),
            'template_np20.sf2',
            r'C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master'
            r'\SIDFactoryII\drivers\sf2driver_np20_00.prg',
            r'C:\Users\mit\Downloads\SIDFactoryII_Win32_20231002\drivers'
            r'\sf2driver_np20_00.prg',
        ],
        'laxity': [
            os.path.join(base_dir, 'drivers', 'laxity', 'sf2driver_laxity_00.prg'),
        ],
    }

    # Aliases for driver11 short forms.
    if driver_type in ('d11', '11'):
        driver_type = 'driver11'

    search_paths = driver_templates.get(driver_type,
                                          driver_templates['driver11'])

    for path in search_paths:
        if os.path.isabs(path):
            if os.path.exists(path):
                return path
        else:
            full_path = os.path.join(base_dir, path)
            if os.path.exists(full_path):
                return full_path

    return None


def find_driver() -> Optional[str]:
    """Find the v1.6 SF2 driver file.

    Looks in three conventional locations relative to the project
    root: at root, in `drivers/`, and one level up. Returns the
    first match or None.
    """
    base_dir = _base_dir()
    search_paths = [
        'sf2driver16_01.prg',
        'drivers/sf2driver16_01.prg',
        '../drivers/sf2driver16_01.prg',
    ]
    for path in search_paths:
        full_path = os.path.join(base_dir, path)
        if os.path.exists(full_path):
            return full_path
    return None
