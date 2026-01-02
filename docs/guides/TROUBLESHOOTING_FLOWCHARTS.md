# Troubleshooting Flowcharts

**Version 3.1.0** | **Last Updated**: 2026-01-02

Visual decision trees for diagnosing and resolving common SIDM2 issues.

---

## Table of Contents

1. [Conversion Failed](#conversion-failed)
2. [Low Accuracy Results](#low-accuracy-results)
3. [Driver Selection Issues](#driver-selection-issues)
4. [File Not Found](#file-not-found)
5. [External Tools Not Working](#external-tools-not-working)
6. [SF2 File Won't Open](#sf2-file-wont-open)
7. [Tests Failing](#tests-failing)

---

## Conversion Failed

```
┌──────────────────────────────────────┐
│  Conversion Failed - Start Here     │
└──────────────┬───────────────────────┘
               │
               ▼
        ┌─────────────┐
        │ Check Error │
        │  Message    │
        └──────┬──────┘
               │
   ┌───────────┼───────────┬───────────────┐
   │           │           │               │
   ▼           ▼           ▼               ▼
┌──────┐  ┌───────┐  ┌────────────┐ ┌────────────┐
│ File │  │Player │  │ Missing    │ │ Extraction │
│Error │  │ Type  │  │ Dependency │ │  Failed    │
└──┬───┘  └───┬───┘  └──────┬─────┘ └──────┬─────┘
   │          │             │              │
   ▼          ▼             ▼              ▼
┌──────────────────────────────────────────────────┐
│ FILE ERROR:                                      │
│ • Check file exists: ls input.sid               │
│ • Check permissions: ls -la input.sid           │
│ • Try absolute path: /full/path/to/input.sid   │
│ • Verify SID format: file input.sid            │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ PLAYER TYPE:                                     │
│ • Check player type:                            │
│   tools/player-id.exe input.sid                 │
│ • If "UNIDENTIFIED":                            │
│   → Not supported, use Driver 11 fallback      │
│ • If "Laxity_NewPlayer_V21":                    │
│   → Use --driver laxity                         │
│ • If "SidFactory_II/*":                         │
│   → Use --driver driver11 (auto-selected)      │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ MISSING DEPENDENCY:                              │
│ • Check tools exist:                            │
│   ls tools/player-id.exe                        │
│ • Install missing tools (see README.md)         │
│ • Alternative: Use --no-validation flag         │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ EXTRACTION FAILED:                               │
│ • Check init/play addresses valid:              │
│   python pyscript/siddump_complete.py -t10      │
│ • Check load address:                           │
│   python pyscript/quick_disasm.py input.sid    │
│ • Try different driver:                         │
│   --driver driver11  (safe fallback)            │
└──────────────────────────────────────────────────┘
```

---

## Low Accuracy Results

```
┌──────────────────────────────────────┐
│  Low Accuracy (< 50%) - Diagnose     │
└──────────────┬───────────────────────┘
               │
               ▼
        ┌─────────────┐
        │ Check Player│
        │    Type     │
        └──────┬──────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
┌──────────────┐ ┌──────────────┐
│ SF2-exported │ │ Native Laxity│
│ detected as  │ │ using wrong  │
│ "Laxity"?    │ │  driver?     │
└──────┬───────┘ └──────┬───────┘
       │                │
       ▼                ▼
┌────────────────────────────────────────────────┐
│ SF2-EXPORTED MISDETECTION:                    │
│                                                │
│ Problem: File shows "SidFactory_II/Laxity"    │
│          but converter used Laxity driver     │
│                                                │
│ Fix:                                           │
│ • Use Driver 11 explicitly:                   │
│   python scripts/sid_to_sf2.py input.sid \    │
│     output.sf2 --driver driver11              │
│                                                │
│ • Expected result: 100% accuracy              │
│                                                │
│ Why: "SidFactory_II/Laxity" = Author name     │
│      NOT player format!                       │
└────────────────────────────────────────────────┘

┌────────────────────────────────────────────────┐
│ NATIVE LAXITY WRONG DRIVER:                   │
│                                                │
│ Problem: File is Laxity NP21 but used         │
│          Driver 11 or NP20                    │
│                                                │
│ Verify:                                        │
│ • tools/player-id.exe input.sid               │
│   Should show: "Laxity_NewPlayer_V21"         │
│                                                │
│ Fix:                                           │
│ • Use Laxity driver:                          │
│   python scripts/sid_to_sf2.py input.sid \    │
│     output.sf2 --driver laxity                │
│                                                │
│ • Expected result: 99.93-100% accuracy        │
└────────────────────────────────────────────────┘

               ┌──────────────┐
               │ Still Low?   │
               │ Check Tables │
               └──────┬───────┘
                      │
                      ▼
┌────────────────────────────────────────────────┐
│ TABLE EXTRACTION CHECK:                       │
│                                                │
│ 1. Disassemble SID:                           │
│    python pyscript/quick_disasm.py input.sid  │
│                                                │
│ 2. Check table addresses:                     │
│    • Instruments: Look for ADSR values        │
│    • Wave Table: Look for waveform bytes      │
│      (0x11, 0x21, 0x41, 0x81)                │
│                                                │
│ 3. Compare dumps:                             │
│    python pyscript/siddump_complete.py \      │
│      original.sid -t300 > orig.txt            │
│    python pyscript/siddump_complete.py \      │
│      converted.sid -t300 > conv.txt           │
│    diff orig.txt conv.txt                     │
│                                                │
│ 4. Find divergence point:                     │
│    • Early divergence (< frame 10):           │
│      → Init address wrong                     │
│    • Mid divergence (frames 50-100):          │
│      → Sequence extraction issue              │
│    • Late divergence (> frame 100):           │
│      → Loop handling issue                    │
└────────────────────────────────────────────────┘

                      │
                      ▼
               ┌──────────────┐
               │ Still stuck? │
               │ Report Issue │
               └──────┬───────┘
                      │
                      ▼
┌────────────────────────────────────────────────┐
│ REPORT ISSUE:                                  │
│                                                │
│ Include:                                       │
│ • Player-ID output                            │
│ • Driver used (auto vs manual)                │
│ • Accuracy percentage                         │
│ • First 20 lines of diff (if available)       │
│ • SID file (if shareable)                     │
│                                                │
│ Post to:                                       │
│ https://github.com/MichaelTroelsen/SIDM2conv  │
│                              /issues           │
└────────────────────────────────────────────────┘
```

---

## Driver Selection Issues

```
┌──────────────────────────────────────┐
│  Wrong Driver Selected - Fix It      │
└──────────────┬───────────────────────┘
               │
               ▼
        ┌─────────────┐
        │ Identify    │
        │ Player Type │
        └──────┬──────┘
               │
               ▼
    tools/player-id.exe input.sid
               │
               ▼
┌──────────────────────────────────────────────────┐
│ PLAYER TYPE SIGNATURES:                         │
├──────────────────────────────────────────────────┤
│ Signature              → Correct Driver          │
├──────────────────────────────────────────────────┤
│ "SidFactory_II/Laxity" → Driver 11 (100%)       │
│ "SidFactory_II/*"      → Driver 11 (100%)       │
│ "SidFactory/*"         → Driver 11 (100%)       │
│ "Driver_11"            → Driver 11 (100%)       │
├──────────────────────────────────────────────────┤
│ "Laxity_NewPlayer_V21" → Laxity (99.93%)        │
│ "Vibrants/Laxity"      → Laxity (99.93%)        │
│ "256bytes/Laxity"      → Laxity (99.93%)        │
├──────────────────────────────────────────────────┤
│ "NewPlayer_20.G4"      → NP20 (70-90%)          │
│ "NewPlayer_20"         → NP20 (70-90%)          │
├──────────────────────────────────────────────────┤
│ "UNIDENTIFIED"         → Driver 11 (fallback)   │
│ "Unknown"              → Driver 11 (fallback)   │
└──────────────────────────────────────────────────┘

               ┌──────────────┐
               │ Force Driver │
               │  if needed   │
               └──────┬───────┘
                      │
                      ▼
┌────────────────────────────────────────────────┐
│ MANUAL DRIVER OVERRIDE:                       │
│                                                │
│ Syntax:                                        │
│   python scripts/sid_to_sf2.py input.sid \    │
│     output.sf2 --driver DRIVER_NAME           │
│                                                │
│ Available Drivers:                             │
│ • laxity    - Laxity NewPlayer v21            │
│ • driver11  - Standard SF2 driver (fallback)  │
│ • np20      - NewPlayer 20.G4                 │
│                                                │
│ Examples:                                      │
│ # Force Laxity driver                         │
│ --driver laxity                                │
│                                                │
│ # Force Driver 11 (safe default)              │
│ --driver driver11                              │
└────────────────────────────────────────────────┘

               ┌──────────────┐
               │ Verify Result│
               └──────┬───────┘
                      │
                      ▼
┌────────────────────────────────────────────────┐
│ VERIFY DRIVER SELECTION:                      │
│                                                │
│ • Check output.txt file:                      │
│   cat output.txt | grep "Selected Driver"     │
│                                                │
│ • Should show:                                 │
│   Selected Driver: LAXITY (sf2driver_laxity)  │
│   Expected Acc:    99.93%                     │
│                                                │
│ • Run validation:                             │
│   python scripts/validate_sid_accuracy.py \   │
│     original.sid converted.sid                │
└────────────────────────────────────────────────┘
```

---

## File Not Found

```
┌──────────────────────────────────────┐
│  File Not Found Error - Solve It     │
└──────────────┬───────────────────────┘
               │
               ▼
        ┌─────────────┐
        │ Check Which │
        │    File?    │
        └──────┬──────┘
               │
   ┌───────────┼───────────┬───────────┐
   │           │           │           │
   ▼           ▼           ▼           ▼
┌──────┐  ┌───────┐  ┌───────┐  ┌────────┐
│ Input│  │Output │  │Template│  │ Tools  │
│ SID  │  │  SF2  │  │ Driver │  │(.exe)  │
└──┬───┘  └───┬───┘  └───┬───┘  └───┬────┘
   │          │          │          │
   ▼          ▼          ▼          ▼

┌──────────────────────────────────────────────────┐
│ INPUT SID FILE NOT FOUND:                       │
│                                                  │
│ 1. Check file exists:                           │
│    ls input.sid                                 │
│    ls "path with spaces/input.sid"              │
│                                                  │
│ 2. Check current directory:                     │
│    pwd   (Linux/Mac)                            │
│    cd    (Windows)                              │
│                                                  │
│ 3. Use absolute path:                           │
│    python scripts/sid_to_sf2.py \               │
│      C:/full/path/input.sid output.sf2          │
│                                                  │
│ 4. Quote paths with spaces:                     │
│    python scripts/sid_to_sf2.py \               │
│      "G5/examples/Driver 11 Test.sid" out.sf2   │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ OUTPUT SF2 DIRECTORY NOT FOUND:                 │
│                                                  │
│ 1. Check output directory exists:               │
│    ls output_dir/                               │
│                                                  │
│ 2. Create directory:                            │
│    mkdir -p output_dir                          │
│                                                  │
│ 3. Check write permissions:                     │
│    ls -la output_dir/                           │
│    touch output_dir/test.txt                    │
│                                                  │
│ 4. Use absolute path:                           │
│    python scripts/sid_to_sf2.py input.sid \     │
│      C:/full/path/output_dir/output.sf2         │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ DRIVER TEMPLATE NOT FOUND:                      │
│                                                  │
│ 1. Check driver files exist:                    │
│    ls G5/drivers/laxity/sf2driver_laxity_00.prg│
│    ls G5/drivers/driver11/sf2driver_11.prg      │
│                                                  │
│ 2. Verify repository structure:                 │
│    ls G5/drivers/                               │
│                                                  │
│ 3. Re-clone repository if missing:              │
│    git clone <repository-url>                   │
│                                                  │
│ 4. Check you're in project root:                │
│    ls CLAUDE.md README.md                       │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ TOOLS (.exe) NOT FOUND:                         │
│                                                  │
│ 1. Check tools directory:                       │
│    ls tools/player-id.exe                       │
│    ls tools/SIDwinder.exe                       │
│                                                  │
│ 2. Download missing tools:                      │
│    • player-id.exe:                             │
│      See README.md for download links           │
│                                                  │
│ 3. Alternative (Python fallback):               │
│    • siddump: pyscript/siddump_complete.py      │
│    • SIDwinder: pyscript/sidwinder_trace.py     │
│                                                  │
│ 4. Platform compatibility:                      │
│    • Windows: Use .exe directly                 │
│    • Linux/Mac: Use Wine or Python versions     │
└──────────────────────────────────────────────────┘
```

---

## External Tools Not Working

```
┌──────────────────────────────────────┐
│  External Tools Failing - Debug      │
└──────────────┬───────────────────────┘
               │
               ▼
        ┌─────────────┐
        │ Which Tool? │
        └──────┬──────┘
               │
   ┌───────────┼───────────┬───────────┐
   │           │           │           │
   ▼           ▼           ▼           ▼
┌──────┐  ┌────────┐  ┌────────┐  ┌────────┐
│player│  │siddump │  │SIDwind │  │SIDFac  │
│-id   │  │  .exe  │  │ er.exe │  │tory II │
└──┬───┘  └───┬────┘  └───┬────┘  └───┬────┘
   │          │           │           │
   ▼          ▼           ▼           ▼

┌──────────────────────────────────────────────────┐
│ PLAYER-ID.EXE ISSUES:                           │
│                                                  │
│ Symptom: "Player type: Unknown"                 │
│                                                  │
│ Solutions:                                       │
│ 1. Run manually:                                │
│    tools/player-id.exe input.sid                │
│                                                  │
│ 2. Check output:                                │
│    • If "UNIDENTIFIED": Use Driver 11           │
│    • If works: Check Python subprocess call     │
│                                                  │
│ 3. Fallback:                                     │
│    • Use manual driver selection:               │
│      --driver laxity  (if you know it's Laxity) │
│      --driver driver11  (safe default)          │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ SIDDUMP.EXE ISSUES:                             │
│                                                  │
│ Symptom: "siddump.exe not found" or crashes    │
│                                                  │
│ Solutions:                                       │
│ 1. Use Python version (no .exe needed):         │
│    python pyscript/siddump_complete.py \        │
│      input.sid -t300                            │
│                                                  │
│ 2. Check .exe exists:                           │
│    ls tools/siddump.exe                         │
│                                                  │
│ 3. Platform-specific:                           │
│    • Windows: Should work directly              │
│    • Linux/Mac: Use Python version              │
│                                                  │
│ 4. Skip validation (not recommended):           │
│    python scripts/sid_to_sf2.py input.sid \     │
│      output.sf2 --no-validation                 │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ SIDWINDER.EXE ISSUES:                           │
│                                                  │
│ Symptom: "SIDwinder.exe failed" or timeout      │
│                                                  │
│ Solutions:                                       │
│ 1. Use Python version:                          │
│    python pyscript/sidwinder_trace.py \         │
│      --trace output.txt input.sid               │
│                                                  │
│ 2. Increase timeout:                            │
│    • Default: 60 seconds                        │
│    • Large files may need more time             │
│                                                  │
│ 3. Check manually:                              │
│    tools/SIDwinder.exe disassemble \            │
│      input.sid output.asm                       │
│                                                  │
│ 4. Alternative disassembler:                    │
│    python pyscript/quick_disasm.py input.sid    │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ SID FACTORY II ISSUES:                          │
│                                                  │
│ Symptom: Won't open SF2 file                    │
│                                                  │
│ Solutions:                                       │
│ 1. Check file size:                             │
│    ls -lh output.sf2                            │
│    • Should be 8-40 KB                          │
│    • If 0 bytes: Conversion failed              │
│                                                  │
│ 2. Check SF2 magic marker:                      │
│    xxd output.sf2 | head -20                    │
│    • Look for: 37 13 at offset 0x0900           │
│                                                  │
│ 3. Try SF2 Viewer GUI:                          │
│    python pyscript/sf2_viewer_gui.py output.sf2 │
│                                                  │
│ 4. Validate with batch test:                    │
│    test-batch-pyautogui.bat --file output.sf2   │
└──────────────────────────────────────────────────┘
```

---

## SF2 File Won't Open

```
┌──────────────────────────────────────┐
│  SF2 File Won't Open - Diagnose      │
└──────────────┬───────────────────────┘
               │
               ▼
        ┌─────────────┐
        │ Check File  │
        │    Size     │
        └──────┬──────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
   ┌───────┐      ┌────────┐
   │ 0 KB  │      │ 8-40KB │
   │ Empty │      │ Normal │
   └───┬───┘      └───┬────┘
       │              │
       ▼              ▼
┌──────────────┐  ┌──────────────┐
│ EMPTY FILE:  │  │ VALID SIZE:  │
│              │  │              │
│ Conversion   │  │ Check format │
│ failed!      │  │              │
└──────┬───────┘  └──────┬───────┘
       │                 │
       ▼                 ▼
┌────────────────────────────────────────────────┐
│ EMPTY FILE (0 bytes):                         │
│                                                │
│ Cause: Conversion failed                       │
│                                                │
│ 1. Check error logs:                          │
│    python scripts/sid_to_sf2.py -vv \          │
│      input.sid output.sf2                     │
│                                                │
│ 2. Check player type:                         │
│    tools/player-id.exe input.sid              │
│                                                │
│ 3. Try safe driver:                           │
│    python scripts/sid_to_sf2.py input.sid \   │
│      output.sf2 --driver driver11             │
└────────────────────────────────────────────────┘

┌────────────────────────────────────────────────┐
│ VALID SIZE - CHECK MAGIC MARKER:              │
│                                                │
│ 1. Dump first 2KB of file:                    │
│    xxd output.sf2 | head -100                  │
│                                                │
│ 2. Look for SF2 magic at offset 0x0900:       │
│    00000900: 37 13 ...                        │
│    ^^^^^^^^  ^^^^^                            │
│    Offset    Magic (should be 0x37 0x13)      │
│                                                │
│ 3. If missing magic:                           │
│    • File corrupted during conversion         │
│    • Try conversion again                     │
│    • Check disk space                         │
│                                                │
│ 4. If magic present:                          │
│    • File is valid                            │
│    • Problem with SID Factory II              │
│    • Try SF2 Viewer GUI:                      │
│      python pyscript/sf2_viewer_gui.py file   │
└────────────────────────────────────────────────┘

               ┌──────────────┐
               │ Try SF2      │
               │ Viewer GUI   │
               └──────┬───────┘
                      │
                      ▼
┌────────────────────────────────────────────────┐
│ SF2 VIEWER GUI:                                │
│                                                │
│ Launch:                                        │
│   python pyscript/sf2_viewer_gui.py output.sf2│
│   # or                                         │
│   sf2-viewer.bat output.sf2                    │
│                                                │
│ Features:                                      │
│ • View sequences for all 3 voices             │
│ • View instruments, wave table, pulse table   │
│ • Export to HTML                               │
│ • Validate SF2 format                         │
│                                                │
│ If GUI shows data:                             │
│ • SF2 file is valid                           │
│ • Problem with SID Factory II installation    │
│                                                │
│ If GUI shows errors:                           │
│ • SF2 file corrupted                          │
│ • Re-run conversion                            │
└────────────────────────────────────────────────┘
```

---

## Tests Failing

```
┌──────────────────────────────────────┐
│  Tests Failing - Quick Fix           │
└──────────────┬───────────────────────┘
               │
               ▼
        ┌─────────────┐
        │ Run Tests   │
        │  Verbose    │
        └──────┬──────┘
               │
               ▼
    test-all.bat -v
               │
               ▼
        ┌─────────────┐
        │ Check Which │
        │ Tests Failed│
        └──────┬──────┘
               │
   ┌───────────┼───────────┬────────────┐
   │           │           │            │
   ▼           ▼           ▼            ▼
┌──────┐  ┌────────┐  ┌────────┐  ┌─────────┐
│Import│  │Converter│  │Parser │  │External │
│Errors│  │  Tests │  │ Tests  │  │  Tools  │
└──┬───┘  └───┬────┘  └───┬────┘  └────┬────┘
   │          │           │            │
   ▼          ▼           ▼            ▼

┌──────────────────────────────────────────────────┐
│ IMPORT ERRORS:                                   │
│                                                  │
│ Symptom: "ModuleNotFoundError" or               │
│          "ImportError: cannot import..."        │
│                                                  │
│ 1. Check Python path:                           │
│    python -c "import sys; print(sys.path)"      │
│                                                  │
│ 2. Verify module structure:                     │
│    ls sidm2/__init__.py                         │
│                                                  │
│ 3. Re-run from project root:                    │
│    cd /path/to/SIDM2                            │
│    test-all.bat                                  │
│                                                  │
│ 4. Check for circular imports:                  │
│    python -m pytest pyscript/test_*.py -vv      │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ CONVERTER TESTS FAILING:                        │
│                                                  │
│ 1. Check test data exists:                      │
│    ls batch_test/originals/Angular.sid          │
│    ls G5/examples/*.sid                         │
│                                                  │
│ 2. Run specific test:                           │
│    python -m pytest \                           │
│      pyscript/test_laxity_converter.py::TestX   │
│                                                  │
│ 3. Check for recent code changes:               │
│    git diff HEAD~1 sidm2/laxity_converter.py    │
│                                                  │
│ 4. Restore known-good version:                  │
│    git checkout HEAD~1 -- sidm2/*.py            │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ PARSER TESTS FAILING:                           │
│                                                  │
│ 1. Check test assertions:                       │
│    • Wrong expected values?                     │
│    • Test data changed?                         │
│                                                  │
│ 2. Run parser manually:                         │
│    python -c "from sidm2.laxity_parser import *"│
│                                                  │
│ 3. Update tests if format changed:              │
│    • Review recent commits                      │
│    • Update expected values                     │
│                                                  │
│ 4. Check memory layout:                         │
│    • Verify addresses in test match code        │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ EXTERNAL TOOLS TESTS FAILING:                   │
│                                                  │
│ Symptom: Tests timeout or "tool not found"      │
│                                                  │
│ 1. Check tools exist:                           │
│    ls tools/*.exe                               │
│                                                  │
│ 2. Skip external tool tests:                    │
│    python -m pytest -k "not external"           │
│                                                  │
│ 3. Use Python fallbacks:                        │
│    • Tests should auto-fallback to Python       │
│    • Check fallback logic                       │
│                                                  │
│ 4. Platform compatibility:                      │
│    • Windows: All tests should pass             │
│    • Linux/Mac: External tool tests may skip    │
└──────────────────────────────────────────────────┘

               ┌──────────────┐
               │ Still Failing│
               │ Clean + Retry│
               └──────┬───────┘
                      │
                      ▼
┌────────────────────────────────────────────────┐
│ CLEAN SLATE APPROACH:                         │
│                                                │
│ 1. Clean all generated files:                 │
│    cleanup.bat                                 │
│                                                │
│ 2. Remove cached files:                       │
│    rm -rf __pycache__                          │
│    rm -rf .pytest_cache                        │
│                                                │
│ 3. Re-run tests:                               │
│    test-all.bat                                 │
│                                                │
│ 4. If still failing:                           │
│    • Check git status: git status              │
│    • Restore clean state: git reset --hard     │
│    • Re-run: test-all.bat                      │
└────────────────────────────────────────────────┘
```

---

## Quick Reference Card

**Most Common Issues**:

```
┌─────────────────────────────────────────────────────────────┐
│ ISSUE                    → QUICK FIX                        │
├─────────────────────────────────────────────────────────────┤
│ Conversion failed        → Check player-id.exe output       │
│ Low accuracy (< 50%)     → Check driver selection           │
│ File not found           → Use absolute path with quotes    │
│ Wrong driver selected    → Use --driver laxity/driver11     │
│ SF2 won't open           → Check file size (0 = failed)     │
│ Tests failing            → Run from project root            │
│ Tool not found           → Use Python fallback version      │
└─────────────────────────────────────────────────────────────┘
```

**Emergency Commands**:

```bash
# Quick diagnosis
tools/player-id.exe input.sid                     # Check player type
python pyscript/siddump_complete.py input.sid -t10  # Test playback
python scripts/sid_to_sf2.py input.sid out.sf2 -vv  # Verbose conversion

# Force specific driver
--driver laxity      # For Laxity NP21
--driver driver11    # Safe fallback

# Compare files
python scripts/validate_sid_accuracy.py original.sid converted.sid

# Batch analysis
batch-analysis.bat originals/ converted/ -o results/

# View SF2 without SID Factory II
python pyscript/sf2_viewer_gui.py output.sf2
```

---

**End of Troubleshooting Flowcharts**

**Version**: 3.1.0 | **Last Updated**: 2026-01-02

For detailed troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
