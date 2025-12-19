# SF2 Text Exporter - README

**Version**: 1.0
**Date**: 2025-12-18

## Purpose

The SF2 Text Exporter extracts all data from SF2 files and exports it to human-readable text files. This creates "ground truth" reference files for:
- Validating SID→SF2 conversions
- Understanding SF2 file structure
- Debugging conversion issues
- Creating test cases
- Learning the SF2 format

## Why This Tool?

Instead of building a full SID Factory II editor clone, this tool provides the essential functionality needed for conversion validation:
- **Reads SF2 files** using our existing parser
- **Exports all tables and sequences** to text format
- **Matches SID Factory II display format** for easy comparison
- **Auto-detects sequence formats** (single-track vs 3-track interleaved)
- **Comprehensive export** of all SF2 data structures

## Usage

### Basic Usage

```bash
python sf2_to_text_exporter.py <sf2_file> [output_directory]
```

### Examples

```bash
# Export to auto-generated directory
python sf2_to_text_exporter.py "learnings/Laxity - Stinsen.sf2"
# Output: output/Laxity - Stinsen_export/

# Export to specific directory
python sf2_to_text_exporter.py "learnings/Laxity - Stinsen.sf2" "output/stinsen_export"

# Export multiple files
for file in learnings/*.sf2; do
    python sf2_to_text_exporter.py "$file"
done
```

## Exported Files

### Core Data Files

1. **orderlist.txt** - OrderList (sequence playback order)
   - Shows which sequences play for Track 1, 2, 3 at each step
   - Format: Step | Track 1 | Track 2 | Track 3
   - Each entry: TT SS (TT=transpose, SS=sequence)

2. **sequence_XX.txt** - Individual sequences (one file per sequence)
   - Auto-detects format: single-track or 3-track interleaved
   - Single-track: Step | Inst | Cmd | Note
   - Interleaved: Step | Track 1 | Track 2 | Track 3
   - Shows hex step numbers matching SID Factory II

3. **instruments.txt** - Instrument definitions
   - 6 bytes per instrument
   - Attack/Decay, Sustain/Release, Waveform
   - Pulse table, Wave table, HR settings
   - Decoded waveform names

### Table Data Files

4. **wave.txt** - Wave table sequences
   - Waveform modulation sequences
   - End markers (0x7F) and loop markers (0x7E)

5. **pulse.txt** - Pulse width sequences
   - 16-bit pulse width values
   - Used for pulse width modulation

6. **filter.txt** - Filter cutoff sequences
   - Filter frequency modulation
   - Used for filter sweeps

7. **arp.txt** - Arpeggio table (placeholder)
   - Note: Most SF2 files don't use arpeggio tables

8. **tempo.txt** - Tempo information
   - Note: Usually embedded in player code

9. **hr.txt** - Hard Restart table reference
   - Note: HR values stored in instrument table

10. **init.txt** - Init table reference
    - Note: Usually embedded in player code

### Reference Files

11. **commands.txt** - Command reference
    - Complete list of SF2 sequence commands
    - Command descriptions and special values

12. **summary.txt** - Export summary
    - File statistics
    - Detected format (Laxity vs Standard SF2)
    - Complete file list with descriptions

## Output Format

All files use human-readable text format:
- **Hex values**: Uppercase (0A, FF)
- **Step numbers**: 4-digit hex (0000, 001F)
- **Special markers**: END (0x7F), +++ (note continue), --- (rest)
- **Table columns**: Aligned for easy reading
- **Headers**: Clear section markers (=== and ---)

## Example Output

### sequence_08.txt (Single-track format)
```
SEQUENCE $08 (8)
================================================================================
Format: single
Length: 32 entries

Step  | Inst | Cmd  | Note
------|------|------|------
0000  | 0B   | --   | F-3
0001  | --   | --   | +++
0002  | --   | 02   | +++
0003  | --   | --   | +++
0004  | --   | --   | F-3
...
```

### sequence_06.txt (3-track interleaved format)
```
SEQUENCE $06 (6)
================================================================================
Format: interleaved
Length: 128 entries

Step  | Track 1           | Track 2           | Track 3
      | In  Cmd  Note     | In  Cmd  Note     | In  Cmd  Note
------|-------------------|-------------------|-------------------
0000  | 01  --  C-3       | 02  --  E-3       | 03  --  G-3
0001  | --  --  +++       | --  --  +++       | --  --  +++
...
```

## Use Cases

### 1. Validate SID→SF2 Conversion

```bash
# Export reference SF2
python sf2_to_text_exporter.py reference.sf2 output/reference_export

# Export converted SF2
python sf2_to_text_exporter.py converted.sf2 output/converted_export

# Compare files
diff output/reference_export/sequence_08.txt output/converted_export/sequence_08.txt
```

### 2. Create Reference Files

```bash
# Export known-good SF2 files
python sf2_to_text_exporter.py learnings/*.sf2

# Use as reference for SID→SF2 conversion
# Compare extracted SID data against SF2 reference
```

### 3. Debug Conversion Issues

```bash
# Export SF2 to see actual data structure
python sf2_to_text_exporter.py problematic.sf2 debug_export

# Check sequence format detection
cat debug_export/summary.txt

# Examine specific sequences
cat debug_export/sequence_0A.txt
```

### 4. Learn SF2 Format

```bash
# Export various SF2 files
python sf2_to_text_exporter.py examples/*.sf2

# Study structure differences
# Compare single-track vs interleaved sequences
# Analyze table data formats
```

## Features

### Automatic Format Detection
- **Single-track sequences**: Detected and displayed as continuous track
- **3-track interleaved**: Detected and displayed in parallel columns
- **Detection results**: Shown in summary.txt

### Hex Notation
- **Sequence numbers**: Shows "Sequence $0A" format
- **Step numbers**: 4-digit hex (0000, 001F)
- **All values**: Uppercase hex for consistency

### Comprehensive Export
- **All sequences**: Every detected sequence exported
- **All tables**: Wave, pulse, filter, instruments
- **OrderList**: Complete playback order
- **Summary**: Statistics and file list

### Human-Readable Format
- **Aligned columns**: Easy to read
- **Clear headers**: Section markers
- **Decoded values**: Waveform names, special markers
- **Comments**: Format descriptions

## Requirements

- Python 3.x (no external packages)
- sf2_viewer_core.py (SF2 parser)
- Valid SF2 file as input

## Integration with Validation

This tool complements the existing validation system:
- **SF2 Viewer**: Visual inspection of SF2 files
- **Text Exporter**: Text-based reference files
- **Comparison Tool**: Side-by-side comparison (compare_track3_flexible.py)
- **Complete Pipeline**: Full SID→SF2→validation workflow

## Next Steps

After exporting SF2 data:
1. Use text files as reference for SID→SF2 conversion
2. Compare against SID extraction output
3. Identify conversion accuracy issues
4. Debug table extraction problems
5. Validate sequence format detection

## Technical Details

### Parser Integration
- Uses `sf2_viewer_core.SF2Parser` for file parsing
- Accesses all parsed data structures
- Handles both Laxity and standard SF2 formats

### OrderList Format
- Stored as 3 separate columns at different addresses
- Column 1: Track 1 sequences
- Column 2: Track 2 sequences (offset +0x100)
- Column 3: Track 3 sequences (offset +0x200)

### Sequence Format Detection
- Uses heuristics from sf2_viewer_core
- Checks sequence length, instrument patterns
- Distribution analysis (modulo 3)

## Troubleshooting

### "No instrument data found"
- Some SF2 files may not have instruments extracted yet
- Check parser implementation
- Instrument data may be in different format

### "No orderlist data found"
- Parser may not have detected OrderList address
- Check music_data_info
- File may use different format

### Empty sequences
- File may have invalid sequence data
- Check parser log output
- Sequence detection may need adjustment

## Version History

- **v1.0** (2025-12-18) - Initial release
  - Export all SF2 data to text files
  - Auto-detect sequence formats
  - Comprehensive table export
  - Summary statistics

## See Also

- **sf2_viewer_gui.py** - Visual SF2 viewer
- **compare_track3_flexible.py** - Track comparison tool
- **SINGLE_TRACK_IMPLEMENTATION_SUMMARY.md** - Format detection details
- **CLAUDE.md** - Project documentation
