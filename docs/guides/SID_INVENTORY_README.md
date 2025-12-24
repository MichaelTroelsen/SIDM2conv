# SID Inventory System - Quick Reference

**Created**: 2025-12-24
**Status**: ✅ Complete and working

---

## What Was Created

### 1. SID Inventory File: `SID_INVENTORY.md`

A comprehensive catalog of **all 658 SID files** in the project with:
- **Title**, **Author**, **Copyright** (from SID header)
- **Player Type** (identified by player-id.exe)
- **Format** (PSID/RSID version)
- **Addresses** (Load, Init, Play)
- **Songs** (number of subtunes)
- **File Size**

**Location**: `SID_INVENTORY.md` (root directory)
**Size**: 91 KB
**Format**: Markdown table (grid view)

### 2. Inventory Generator Script: `create_sid_inventory.py`

Python script that scans all SID files and generates the inventory.

**Location**: `pyscript/create_sid_inventory.py`
**Size**: 330 lines
**Dependencies**: Python 3.6+, player-id.exe (optional)

### 3. Batch Launcher: `create-sid-inventory.bat`

Windows batch file for easy execution.

**Location**: `create-sid-inventory.bat` (root directory)
**Usage**: Double-click or run from command line

### 4. Documentation: `SID_INVENTORY_GUIDE.md`

Complete guide with troubleshooting and advanced usage.

**Location**: `docs/guides/SID_INVENTORY_GUIDE.md`

---

## Quick Usage

### Regenerate Inventory (Windows)

```batch
create-sid-inventory.bat
```

### Regenerate Inventory (Mac/Linux)

```bash
python pyscript/create_sid_inventory.py
```

**Time**: ~2-3 minutes for 658 files

---

## Inventory Statistics

**Total Files**: 658 SID files
**Total Size**: 4.24 MB
**Total Songs**: 2,054 subtunes
**Directories**: 10

**File Formats**:
- PSID v2: 611 files (92.9%)
- RSID v2: 47 files (7.1%)

**Top Player Types**:
1. Rob_Hubbard: 131 files (19.9%)
2. Vibrants/Laxity: 127 files (19.3%)
3. SidFactory_II/Laxity: 83 files (12.6%)
4. Soundmonitor: 72 files (10.9%)
5. MoN/Deenen: 72 files (10.9%)
6. MoN/FutureComposer: 49 files (7.4%)
7. Martin_Galway: 40 files (6.1%)
8. SidFactory/Laxity: 27 files (4.1%)
9. Laxity_NewPlayer_V21: 22 files (3.3%)
10. JCH_NewPlayer: 12 files (1.8%)

---

## Tools Used

The inventory system uses three tools to gather information:

### 1. SID Header Parser (Python - Built-in)

**Extracts from PSID/RSID header**:
- Title, Author, Copyright
- Load/Init/Play addresses
- Number of songs (subtunes)
- File format and version

**Method**: Parses first 124 bytes of SID file
**Accuracy**: 100% for valid PSID/RSID files

### 2. player-id.exe (External Tool)

**Identifies**:
- SID player type (e.g., Rob Hubbard, Laxity, Martin Galway)
- Player variants and versions

**Method**: Pattern matching against known player signatures
**Location**: `tools/player-id.exe`
**Source**: JC64 SIDId project

**Accuracy**:
- Known players: 80-99%
- Unknown players: Shows as "UNIDENTIFIED"

### 3. File System (Python - Built-in)

**Provides**:
- File size (bytes)
- File path and directory
- Modification date (for regeneration detection)

**Method**: Standard Python `pathlib` module

---

## Directory Structure

The inventory organizes files by directory:

| Directory | Files | Description |
|-----------|-------|-------------|
| **Laxity** | 286 | Laxity NewPlayer files (various versions) |
| **Tel_Jeroen** | 179 | Jeroen Tel compositions |
| **Hubbard_Rob** | 95 | Rob Hubbard player files |
| **Galway_Martin** | 40 | Martin Galway player files |
| **Fun_Fun** | 20 | Fun Fun player files |
| **SIDSF2player** | 18 | SID Factory II exported files |
| **SID** | 17 | Miscellaneous SID files |
| **tools** | 1 | Test files in tools directory |
| **learnings** | 1 | Learning/test files |
| **roundtrip_output** | 1 | Roundtrip test output |

**Total**: 10 directories, 658 files

**Note**: The `output/` directory is automatically excluded from inventory.

---

## Example Inventory Entry

From the Laxity directory:

```markdown
| File | Title | Author | Player Type | Format | Songs | Load | Init | Play | Size |
|------|-------|--------|-------------|--------|-------|------|------|------|------|
| Stinsens_Last_Night_of_89.sid | Stinsen's Last Night of '89 | Thomas E. Petersen (Laxity) | SidFactory_II/Laxity | PSID v2 | 1 | $1000 | $1000 | $1006 | 6,201 |
```

**Interpretation**:
- **Title**: "Stinsen's Last Night of '89"
- **Author**: Thomas E. Petersen (Laxity)
- **Player**: SidFactory_II/Laxity (Laxity player exported from SID Factory II)
- **Format**: PSID version 2
- **Songs**: 1 subtune
- **Load**: Loads at address $1000
- **Init**: Initialization routine at $1000
- **Play**: Play routine at $1006
- **Size**: 6,201 bytes

---

## Common Use Cases

### 1. Find All Files by a Specific Author

Open `SID_INVENTORY.md` and search for the author name:
- Press Ctrl+F (Windows) or Cmd+F (Mac)
- Type author name (e.g., "Thomas E. Petersen")
- Browse all matches

### 2. Find Files Using Specific Player Type

Search for player type:
- Search for "Rob_Hubbard" → 131 files
- Search for "Laxity_NewPlayer_V21" → 22 files
- Search for "Martin_Galway" → 40 files

### 3. Identify Unknown Player Types

Search for "UNIDENTIFIED" to find files with unknown players.
These files may need manual analysis or pattern database expansion.

### 4. Batch Conversion by Player Type

Use inventory to create batch conversion lists:
1. Search for specific player type
2. Copy filenames
3. Create batch conversion script

### 5. Quality Assurance

Compare inventory before/after conversion:
1. Generate inventory of original SIDs
2. Convert SIDs to SF2 and export back
3. Generate inventory of exported SIDs
4. Compare player types, addresses, songs

---

## Maintenance

### When to Regenerate

Regenerate the inventory when:
- ✅ New SID files added to collection
- ✅ Files moved between directories
- ✅ Player identification patterns updated
- ✅ File metadata changes

### How to Regenerate

```batch
# Windows
create-sid-inventory.bat

# Mac/Linux
python pyscript/create_sid_inventory.py
```

**Time**: ~2-3 minutes
**Note**: Overwrites existing `SID_INVENTORY.md`

---

## Files Created

| File | Purpose | Location |
|------|---------|----------|
| **SID_INVENTORY.md** | Main inventory file | Root directory |
| **create_sid_inventory.py** | Generator script | `pyscript/` |
| **create-sid-inventory.bat** | Batch launcher | Root directory |
| **SID_INVENTORY_GUIDE.md** | Full documentation | `docs/guides/` |
| **SID_INVENTORY_README.md** | This file | Root directory |

---

## Troubleshooting

### Player Type Shows as "N/A"

**Cause**: player-id.exe not found

**Solution**: Ensure `tools/player-id.exe` exists

### Player Type Shows as "UNIDENTIFIED"

**Cause**: Player type not in player-id.exe pattern database

**Solution**:
- File may use unknown/custom player
- Consider adding to pattern database
- Check disassembly for distinctive patterns

### Slow Performance

**Cause**: player-id.exe takes time per file

**Solution**:
- Normal for 650+ files (~2-3 minutes)
- Increase timeout if needed (edit script)

---

## Integration with Other Tools

### With Batch Conversion

```bash
# Get all Laxity files from inventory
grep "Laxity_NewPlayer_V21" SID_INVENTORY.md

# Convert with Laxity driver
batch-convert-laxity.bat
```

### With Pattern Database

```bash
# Find unidentified files
grep "UNIDENTIFIED" SID_INVENTORY.md > unidentified.txt

# Analyze and add patterns
python pyscript/test_pattern_database.py
```

### With Validation System

```bash
# Generate inventory before conversion
python pyscript/create_sid_inventory.py

# Convert SIDs
# ... conversion process ...

# Generate inventory after conversion
python pyscript/create_sid_inventory.py

# Compare (manual diff or script)
```

---

## Next Steps

1. **Browse the Inventory**: Open `SID_INVENTORY.md` in your favorite markdown viewer
2. **Search for Specific Files**: Use Ctrl+F to find titles, authors, or player types
3. **Plan Batch Conversions**: Identify files for conversion using player type filter
4. **Expand Pattern Database**: Analyze UNIDENTIFIED files to add new patterns
5. **Quality Assurance**: Use inventory for before/after conversion validation

---

## Support

For issues or questions:
- Check `docs/guides/SID_INVENTORY_GUIDE.md` for detailed documentation
- Check troubleshooting section above
- Verify player-id.exe is available at `tools/player-id.exe`

---

**Quick Command**: `create-sid-inventory.bat` (Windows) or `python pyscript/create_sid_inventory.py` (Mac/Linux)

**Output**: `SID_INVENTORY.md` with 658 SID files cataloged
