# SIDM2 Quick Start Guide

**Get started in 5 minutes** ⚡

---

## 1. What is SIDM2?

Converts Commodore 64 SID music files to SID Factory II (.sf2) format for editing.

**Best for**: Laxity NewPlayer v21 files (99.93% accuracy)

---

## 2. Installation

**Requirements**: Python 3.x (Windows, Mac, Linux)

```bash
# Clone repository
git clone https://github.com/MichaelTroelsen/SIDM2conv.git
cd SIDM2conv

# Done! No pip install needed (uses standard library)
```

---

## 3. Basic Usage (30 seconds)

### Convert a SID file

```bash
# Quickest way (auto-detects Laxity, suggests driver)
convert-file.bat input.sid

# Basic conversion
sid-to-sf2.bat input.sid output.sf2

# High accuracy (Laxity files)
sid-to-sf2.bat input.sid output.sf2 --driver laxity
```

**Output**: `output.sf2` ready to open in SID Factory II editor

### View SF2 file

```bash
# Quickest way
view-file.bat output.sf2

# Or use full viewer launcher
sf2-viewer.bat output.sf2
```

**Opens**: Professional GUI with 8 tabs (Overview, Tables, Sequences, Visualization, Playback, etc.)

---

## 4. Common Tasks

### Batch Convert Multiple Files

```bash
batch-convert.bat
```

Converts all SID files in `SID/` directory.

### Test Conversion Quality

```bash
# Complete validation workflow (recommended)
validate-file.bat original.sid

# Or manual accuracy check
validate-accuracy.bat original.sid converted.sid
```

Shows frame-by-frame accuracy percentage and creates detailed report.

### Analyze a File

```bash
analyze-file.bat input.sid
```

Creates complete analysis: player ID, register dump, disassembly, audio.

### Run Tests

```bash
# Quick test (30 seconds)
quick-test.bat

# All tests (2 minutes)
test-all.bat
```

---

## 5. Example Workflow

**Goal**: Convert Laxity SID file with high accuracy

```bash
# Step 1: Convert with Laxity driver
sid-to-sf2.bat "Laxity - Stinsen.sid" output.sf2 --driver laxity

# Step 2: Validate quality
validate-accuracy.bat "Laxity - Stinsen.sid" output/exported.sid

# Step 3: View in GUI
sf2-viewer.bat output.sf2

# Done! 99.93% accuracy achieved
```

---

## 6. File Locations

```
SIDM2/
├── SID/              # Put your input SID files here
├── output/           # Converted SF2 files appear here
├── tools/            # External tools (included)
└── *.bat             # Batch launchers (easy to use)
```

---

## 7. Getting Help

### Quick Reference
```bash
TOOLS.bat              # Interactive menu of all tools
```

### Documentation
- **This guide**: Quick start in 5 minutes
- **README.md**: Complete user guide
- **CHEATSHEET.md**: One-page command reference
- **CLAUDE.md**: AI assistant quick reference

### Troubleshooting
- Check `docs/guides/TROUBLESHOOTING.md`
- Review `info.txt` in output folders
- Run `test-all.bat` to verify installation

---

## 8. Next Steps

**After your first conversion**:

1. **Learn more**: Read `README.md` for advanced features
2. **Explore tools**: Try `sf2-export.bat` for text export
3. **Batch processing**: Use `batch-convert.bat` for multiple files
4. **Validation**: Run complete pipeline with `pipeline.bat`

**For specific workflows**:
- **Laxity files**: See `docs/guides/LAXITY_DRIVER_USER_GUIDE.md`
- **Validation**: See `docs/guides/VALIDATION_GUIDE.md`
- **SF2 Viewer**: See `docs/guides/SF2_VIEWER_GUIDE.md`

---

## 9. Quick Tips

✅ **Always use `--driver laxity` for Laxity files** (99.93% vs 1-8% accuracy)

✅ **Check `info.txt` in output folders** for conversion details

✅ **Use batch launchers** (.bat files) - easier than typing Python commands

✅ **Run `quick-test.bat` first** to verify everything works

❌ **Don't put experiments in root** - use `experiments/` directory

❌ **Don't commit output files** - they're auto-generated

---

## 10. Common Issues

**Issue**: "Python not found"
- **Fix**: Install Python 3.x from python.org

**Issue**: "File not found"
- **Fix**: Check file path, use quotes for spaces: `"My Song.sid"`

**Issue**: "Low accuracy (< 10%)"
- **Fix**: Use `--driver laxity` for Laxity files

**Issue**: "Test failures"
- **Fix**: Run `git pull` to get latest updates

---

## That's It! 🎉

You're ready to convert SID files to SF2 format.

**Next**: Try converting your first file with `sid-to-sf2.bat`

**Questions?** Check `README.md` or `docs/guides/TROUBLESHOOTING.md`

---

**Last Updated**: 2025-12-21
**Version**: 2.5.2
