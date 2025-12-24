# SID Inventory System Guide

**Version**: 1.0.0
**Date**: 2025-12-24

---

## Overview

The SID Inventory System provides a comprehensive catalog of all SID files in the SIDM2 project. It automatically scans, analyzes, and documents every SID file with detailed metadata.

**Output**: `SID_INVENTORY.md` - A markdown file with sortable grid view of all SID files

---

## Quick Start

### Windows

Run the batch file:
```batch
create-sid-inventory.bat
```

### Mac/Linux

Run the Python script directly:
```bash
python pyscript/create_sid_inventory.py
```

**Time**: ~2-5 minutes for 650+ files

**Output**: `SID_INVENTORY.md` in the root directory

---

## Tools Used

The inventory system uses multiple tools to gather comprehensive information:

### 1. SID Header Parser (Python)

**Source**: `pyscript/create_sid_inventory.py` (built-in function)

**Extracts**:
- File format (PSID/RSID)
- Format version
- Load/Init/Play addresses
- Number of songs (subtunes)
- Start song
- Title
- Author
- Copyright/Release info

**Method**: Parses PSID/RSID file header (first 124 bytes)

**Accuracy**: 100% for valid PSID/RSID files

### 2. Player-ID.exe (Player Identification)

**Source**: `tools/player-id.exe` (JC64 SIDId tool)

**Identifies**:
- SID player type (e.g., Laxity NewPlayer v21, Rob Hubbard, Martin Galway)
- Player variants

**Method**: Pattern matching against known player signatures

**Accuracy**: 80-99% depending on player type (see Pattern Database)

**Fallback**: If player-id.exe not found, player type shows as "N/A"

### 3. File System (Size & Path)

**Source**: Python `pathlib` module

**Extracts**:
- File size (bytes)
- File path (relative to project root)
- Directory structure

**Method**: Direct file system access

---

## Inventory Format

### Markdown Table Structure

Each directory gets its own table with the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| **File** | Filename | `Stinsens_Last_Night_of_89.sid` |
| **Title** | Song title from header | `Stinsen's Last Night of '89` |
| **Author** | Composer/author | `Thomas E. Petersen (Laxity)` |
| **Player Type** | Identified player | `Laxity_NewPlayer_V21` |
| **Format** | File format & version | `PSID v2` |
| **Songs** | Number of subtunes | `1` |
| **Load** | Load address | `$1000` |
| **Init** | Init routine address | `$1000` |
| **Play** | Play routine address | `$1006` |
| **Size** | File size in bytes | `6,201` |

### Summary Statistics

The inventory includes aggregate statistics:

**File Formats**:
- Count by PSID version
- Count by RSID version
- Percentage distribution

**Player Types** (Top 10):
- Count by player type
- Percentage distribution
- Sorted by frequency

**Total Statistics**:
- Total files
- Total size (bytes & MB)
- Total songs/subtunes
- Average file size
- Average songs per file

---

## Directory Structure

The inventory organizes files by directory:

```
SIDM2/
├── Laxity/           # 286 Laxity NewPlayer v21 files
├── Fun_Fun/          # Fun Fun player files
├── Galway_Martin/    # Martin Galway player files
├── Tel_Jeroen/       # Jeroen Tel player files
├── Hubbard_Rob/      # Rob Hubbard player files
└── Other directories...
```

Each directory gets:
- File count
- Dedicated table section
- Link from table of contents

**Note**: The `output/` directory is automatically excluded from inventory.

---

## Usage Examples

### Finding Files by Player Type

Search the inventory for specific player types:

1. Open `SID_INVENTORY.md`
2. Use Ctrl+F (or Cmd+F) to search
3. Search for player name (e.g., "Laxity_NewPlayer_V21")

### Finding Files by Author

Search by author name:

1. Open `SID_INVENTORY.md`
2. Search for author (e.g., "Thomas E. Petersen")
3. See all files by that author

### Finding Files by Title

Search by song title:

1. Open `SID_INVENTORY.md`
2. Search for title keywords
3. Find exact matches

### Identifying Unknown Files

Files with unknown player types show as "UNIDENTIFIED":

1. Search for "UNIDENTIFIED" in inventory
2. These files may need manual analysis
3. Consider adding patterns to pattern database

---

## Inventory Statistics (Example)

Based on typical SIDM2 collection:

**Total Files**: ~658 SID files
**Total Size**: ~5-8 MB
**File Formats**:
- PSID v2: ~90%
- PSID v3: ~8%
- RSID: ~2%

**Top Player Types**:
1. Laxity_NewPlayer_V21: ~43% (286 files)
2. Generic_SID_Init: ~20%
3. Rob_Hubbard: ~10%
4. Martin_Galway: ~5%
5. Others: ~22%

**Average File Size**: ~9-10 KB
**Average Songs per File**: ~1.2

---

## Updating the Inventory

### When to Regenerate

Regenerate the inventory when:
- New SID files are added to the collection
- Files are moved between directories
- Player identification improves (updated patterns)
- File metadata changes

### How to Regenerate

Simply run the script again:

```bash
create-sid-inventory.bat
```

**Note**: The inventory file is overwritten each time. Previous versions are not kept.

---

## Advanced Usage

### Custom Exclude Directories

Edit `create_sid_inventory.py` to exclude additional directories:

```python
sid_files = scan_sid_files(root_dir, exclude_dirs=['output', 'backup', 'test'])
```

### Custom Output Location

Change the output file path in the script:

```python
output_file = root_dir / 'docs' / 'SID_INVENTORY.md'  # Custom location
```

### Adding Custom Columns

To add custom columns to the inventory table:

1. Edit `create_inventory_markdown()` function
2. Add column to table header
3. Add data extraction logic
4. Add column to table row output

**Example**: Add "Year" column from copyright string.

---

## Integration with Other Tools

### Batch Conversion

Use inventory to identify files for batch conversion:

1. Open `SID_INVENTORY.md`
2. Find all Laxity files
3. Pass to batch conversion script

### Quality Validation

Compare inventory before/after conversion:

1. Generate inventory of original SIDs
2. Generate inventory of converted SIDs
3. Compare player types, addresses, songs

### Pattern Database Expansion

Use inventory to find candidates for new patterns:

1. Search for "UNIDENTIFIED" files
2. Group by directory/author
3. Disassemble to find common patterns
4. Add to pattern database

---

## Troubleshooting

### player-id.exe Not Found

**Error**: `Player type shows as "N/A (player-id.exe not found)"`

**Solution**:
- Ensure `tools/player-id.exe` exists
- Download from JC64 project if missing
- Or use Python pattern matcher instead

### Timeout Errors

**Error**: `Player type shows as "TIMEOUT"`

**Cause**: player-id.exe took >5 seconds to identify

**Solution**:
- Increase timeout in script (default: 5 seconds)
- File may have complex/unusual player

### Parse Errors

**Error**: `Title/Author shows as "ERROR"`

**Cause**: Invalid or corrupted SID file header

**Solution**:
- Check file integrity
- Verify file is valid PSID/RSID format
- File may be different format (e.g., MUS, PRG)

### Missing Files

**Error**: Expected files not in inventory

**Solution**:
- Check if files are in `output/` directory (excluded)
- Verify file extension is `.sid` (case-sensitive on Unix)
- Check file permissions

---

## Performance

### Processing Speed

**Typical Performance**:
- ~100-200 files per minute
- Total time for 650+ files: 2-5 minutes

**Factors Affecting Speed**:
- player-id.exe execution time (0.1-1 second per file)
- Disk I/O speed
- CPU performance

### Memory Usage

**Typical Usage**: < 100 MB RAM

**Factors**:
- Number of files
- File sizes
- Python overhead

---

## File Locations

**Script**: `pyscript/create_sid_inventory.py` (330 lines)
**Batch Launcher**: `create-sid-inventory.bat`
**Output**: `SID_INVENTORY.md` (root directory)
**Documentation**: `docs/guides/SID_INVENTORY_GUIDE.md` (this file)

---

## Version History

### v1.0.0 (2025-12-24)
- Initial release
- SID header parsing
- Player identification with player-id.exe
- Markdown grid/table output
- Directory grouping
- Summary statistics
- Excludes output/ directory

---

## Future Enhancements

### Potential Features

1. **HTML Output**: Generate interactive HTML table with sorting/filtering
2. **CSV Export**: Export to CSV for spreadsheet analysis
3. **Comparison Mode**: Compare two inventories (before/after conversion)
4. **Duplicate Detection**: Find duplicate files by hash or metadata
5. **Quality Metrics**: Add accuracy/quality scores from validation
6. **Web Interface**: Browse inventory in web browser
7. **Incremental Updates**: Only scan changed files
8. **Database Backend**: SQLite database for advanced queries

### Contributing

To add features or fix bugs:

1. Edit `pyscript/create_sid_inventory.py`
2. Test with `python pyscript/create_sid_inventory.py`
3. Update this documentation
4. Submit changes

---

## Related Documentation

- **Pattern Database**: `docs/analysis/PATTERN_DATABASE_FINAL_RESULTS.md`
- **Player Identification**: `docs/analysis/DISASSEMBLER_LAXITY_TEST_RESULTS.md`
- **PSID Format Spec**: `docs/SF2_FORMAT_SPEC.md` (includes SID header details)

---

## Support

For issues or questions:

1. Check troubleshooting section above
2. Review error messages in console output
3. Check that all required files exist
4. Verify Python version (3.6+)

---

**End of Guide**

**Quick Command**: `create-sid-inventory.bat` (Windows) or `python pyscript/create_sid_inventory.py` (Mac/Linux)
