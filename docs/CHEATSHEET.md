# SIDM2 Command Cheatsheet

**One-page quick reference** 📋

---

## Quick Commands

### Basic Conversion
```bash
# Convert SID to SF2
sid-to-sf2.bat input.sid output.sf2

# Quick single-file converter (auto-detects Laxity)
convert-file.bat input.sid

# High accuracy (Laxity files)
sid-to-sf2.bat input.sid output.sf2 --driver laxity

# Convert SF2 to SID
sf2-to-sid.bat input.sf2 output.sid
```

### Batch Operations
```bash
batch-convert.bat                    # Convert all SID files
batch-convert-laxity.bat             # Convert all Laxity files
pipeline.bat                         # Complete validation pipeline
```

### Viewing & Analysis
```bash
sf2-viewer.bat file.sf2              # Open SF2 Viewer GUI
view-file.bat file.sf2               # Quick viewer launcher
sf2-export.bat file.sf2              # Export to text files
analyze-file.bat input.sid           # Complete SID analysis
```

### Testing & Validation
```bash
quick-test.bat                       # Fast core tests (30 sec)
test-all.bat                         # All test suites (2 min)
validate-file.bat input.sid          # Complete validation workflow
validate-accuracy.bat orig.sid conv.sid  # Check accuracy
test-roundtrip.bat input.sid         # Test SID→SF2→SID
```

### Maintenance
```bash
cleanup.bat                          # Clean temporary files
update-inventory.bat                 # Update file inventory
TOOLS.bat                            # Interactive menu
```

---

## File Locations

```
SIDM2/
├── SID/               Input SID files
├── output/            Converted SF2 files
├── tools/             External tools
├── scripts/           Python scripts
└── docs/              Documentation
```

---

## Common Workflows

### Quick Convert & View (Simplest)
```bash
convert-file.bat song.sid
view-file.bat output/song.sf2
```

### Convert & Validate Laxity File
```bash
convert-file.bat "Laxity.sid" --driver laxity
# Or manually:
sid-to-sf2.bat "Laxity.sid" output.sf2 --driver laxity
validate-accuracy.bat "Laxity.sid" output/exported.sid
view-file.bat output.sf2
```

### Complete Validation Workflow
```bash
validate-file.bat song.sid --driver laxity
# Creates: song_validation/ with accuracy report
```

### Complete Analysis
```bash
analyze-file.bat SID/song.sid
# Creates: output/song_analysis/
#   - player_id.txt
#   - registers.dump
#   - disassembly.asm
#   - audio.wav
```

### Batch Convert Collection
```bash
# 1. Put SID files in SID/ directory
# 2. Run batch converter
batch-convert.bat
# 3. Results in output/ directory
```

---

## Python Commands

### Direct Python Usage
```bash
# Conversion
python scripts/sid_to_sf2.py input.sid output.sf2
python scripts/sf2_to_sid.py input.sf2 output.sid

# Validation
python scripts/validate_sid_accuracy.py orig.sid conv.sid
python scripts/test_roundtrip.py input.sid

# Testing
python scripts/test_converter.py
python scripts/test_sf2_format.py
python scripts/test_laxity_driver.py

# Tools
python pyscript/sf2_viewer_gui.py
python pyscript/sf2_to_text_exporter.py file.sf2
python pyscript/cleanup.py --scan
```

---

## Driver Options

```bash
--driver laxity        # 99.93% accuracy (Laxity NewPlayer v21)
--driver driver11      # Standard Driver 11 (default)
--driver np20          # NewPlayer v20 driver
```

---

## Tool Shortcuts

### siddump (Register Dumps)
```bash
tools\siddump.exe input.sid -t30 > output.dump
```

### SIDwinder (Disassembly & Trace)
```bash
tools\SIDwinder.exe disassemble input.sid > output.asm
tools\SIDwinder.exe trace input.sid > output.trace
```

### SID2WAV (Audio Rendering)
```bash
tools\SID2WAV.EXE -t30 -16 input.sid output.wav
```

### player-id (Player Detection)
```bash
tools\player-id.exe input.sid
```

---

## Error Messages

| Error | Solution |
|-------|----------|
| "Python not found" | Install Python 3.x from python.org |
| "File not found" | Use quotes: `"My Song.sid"` |
| "Low accuracy (< 10%)" | Use `--driver laxity` for Laxity files |
| "Test failures" | Run `git pull` for latest updates |

---

## Quick Tips

✅ **Always use `--driver laxity` for Laxity files** (99.93% vs 1-8%)

✅ **Check `info.txt`** in output folders for conversion details

✅ **Use batch launchers** (.bat files) - easier than Python commands

✅ **Run `quick-test.bat` first** to verify everything works

❌ **Don't put experiments in root** - use `experiments/` directory

❌ **Don't commit output files** - they're auto-generated

---

## Documentation Links

| Document | Purpose |
|----------|---------|
| [QUICK_START.md](QUICK_START.md) | 5-minute getting started guide |
| [README.md](../README.md) | Complete user documentation |
| [CLAUDE.md](../CLAUDE.md) | AI assistant quick reference |
| [INDEX.md](INDEX.md) | Complete documentation index |

### Specific Topics

- **Laxity Files**: [LAXITY_DRIVER_USER_GUIDE.md](guides/LAXITY_DRIVER_USER_GUIDE.md)
- **SF2 Viewer**: [SF2_VIEWER_GUIDE.md](guides/SF2_VIEWER_GUIDE.md)
- **Validation**: [VALIDATION_GUIDE.md](guides/VALIDATION_GUIDE.md)
- **Troubleshooting**: [ROOT_FOLDER_RULES.md](guides/ROOT_FOLDER_RULES.md)

---

## Version Info

**Current Version**: v2.5.2
**Test Coverage**: 130+ tests (100% pass rate)
**Last Updated**: 2025-12-21

---

**Print this page for quick reference** 🖨️

🤖 Generated with [Claude Code](https://claude.com/claude-code)
