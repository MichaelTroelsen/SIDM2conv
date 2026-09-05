# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for a standalone `sid-to-sf2` binary.

    pip install pyinstaller
    pyinstaller sidm2.spec          # -> dist/sid-to-sf2/sid-to-sf2.exe

✅ BUILT AND RUN, 2026-09-05, PyInstaller 6.22.2. `pyinstaller sidm2.spec`
exits 0 and produces a 3.36 MB `sid-to-sf2.exe` in a 41 MB bundle, which
converts SID/Angular.sid end to end. Everything below was reasoned from the
tree before that build and is now confirmed by it -- no bundling change was
needed to make the build succeed.

⚠️ AND THE FROZEN-MODE DEFECT PREDICTED BELOW IS REAL AND MEASURED. Same binary,
same arguments, same input, different working directory:

    from a checkout root : driver LAXITY   -> 9,029 bytes, valid
    from anywhere else   : driver DRIVER11 -> 7,408 bytes, and the log says
                           'Instruments table (0x80) MISSING - file will be
                           rejected!' followed by 'SF2 FILE VALIDATION FAILED'

BOTH EXIT 0. The bad run reports success, so an exit-code check passes and the
user gets a file SID Factory II refuses -- and native Laxity through Driver 11
is the documented 1-8% path, so this is the bad conversion, not a variant of it.
WORKAROUND, measured: `--driver laxity` from outside the checkout produces a
BYTE-IDENTICAL file to the in-checkout run (md5 a46642f7...). Naming the driver
skips auto-selection, so player-id.exe is never consulted; only auto-selection
depends on the working directory.

The mechanism is exactly the one described next, and it is NOT a packaging
fault -- do not try to fix it by bundling differently:

  * NOTHING in the codebase consults `sys._MEIPASS` or `sys.frozen` -- zero
    matches across the whole tree. PyInstaller unpacks bundled data into
    `sys._MEIPASS`, so a bundled `tools/` directory is invisible to code that
    does not look there.
  * `sidm2/conversion_pipeline.py:339` resolves the player identifier as
    `os.path.join(os.getcwd(), 'tools', 'player-id.exe')` -- relative to the
    USER'S WORKING DIRECTORY. Run the binary from anywhere but a checkout root
    and that lookup misses, which is precisely the silent runtime failure this
    spec's accompanying documentation exists to prevent.

  So bundling the executables below is necessary but NOT sufficient: a
  `_tool_path()` helper that prefers `sys._MEIPASS` when frozen and falls back
  to the repo layout otherwise has to land first. Tracked as
  sidm2-has-no-frozen-mode-tool-resolution.

WHAT IS BUNDLED AND WHY. Only executables that are TRACKED IN GIT are listed --
an untracked binary is not reproducible from a clone, so bundling it would make
the build machine-specific. Verified tracked on 2026-09-05.

WHAT IS NOT BUNDLED. VICE (`vsid.exe`) and SID Factory II (`SIDFactoryII.exe`)
are third-party installs living outside the repo; they stay on PATH or in their
configured locations. See docs/guides/GETTING_STARTED.md, "Standalone binary".
"""

import os

block_cipher = None

# Tracked helper executables. Each is confirmed present AND `git ls-files`
# tracked; a path that stops being tracked should be removed here rather than
# quietly shipping a file only this machine has.
TOOL_BINARIES = [
    ('tools/player-id.exe',        'tools'),   # driver auto-selection -- REQUIRED
    ('tools/siddump.exe',          'tools'),   # register tracing
    ('tools/SIDwinder.exe',        'tools'),   # frame trace
    ('tools/SIDdecompiler.exe',    'tools'),   # disassembly
    ('tools/sidm2-sid-trace.exe',  'tools'),   # cycle-accurate zig64 tracer
]

# sidplayfp ships as a directory (9 tracked files: exe plus its ROM/data
# sidecars), so it is added wholesale rather than file by file.
TOOL_TREES = [
    ('tools/sidplayfp', 'tools/sidplayfp'),
]

datas = [(src, dst) for src, dst in TOOL_BINARIES if os.path.exists(src)]
datas += [(src, dst) for src, dst in TOOL_TREES if os.path.isdir(src)]

# The SF2 drivers the converter injects into its output. Without these the
# binary builds and then fails on the first conversion.
if os.path.isdir('G5/drivers'):
    datas.append(('G5/drivers', 'G5/drivers'))

# Imported dynamically by driver dispatch, so PyInstaller's static analysis
# does not see them. This list is the reason a naive `pyinstaller scripts/
# sid_to_sf2.py` produces a binary that dies on an unusual player.
hiddenimports = [
    'sidm2.laxity_analyzer',
    'sidm2.martin_galway_analyzer',
    'sidm2.galway_memory_analyzer',
    'sidm2.mon_parser',
    'sidm2.dmc_parser',
    'sidm2.sdi_parser',
    'sidm2.hardtrack_parser',
    'sidm2.hubbard_parser',
    'sidm2.mattgray_parser',
    'sidm2.fc_parser',
    'sidm2.blackbird_parser',
    'sidm2.soundmonitor_parser',
    'sidm2.kimmel_parser',
    'sidm2.deenen_parser',
]

# The GUIs are deliberately OUT: PyQt6 roughly triples the bundle and the
# console converter is what this binary is for. `conversion-cockpit.bat` and
# `sf2-viewer.bat` remain source-only entry points.
excludes = ['PyQt6', 'matplotlib', 'pytest', 'tkinter']

a = Analysis(
    ['scripts/sid_to_sf2.py'],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='sid-to-sf2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# ONEDIR, not --onefile, deliberately: a one-file build unpacks the whole
# bundle to a temp directory on every run, which for ~20 MB of helper .exe
# files is a per-invocation cost the batch workflows in this repo would pay
# on every conversion.
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='sid-to-sf2',
)
