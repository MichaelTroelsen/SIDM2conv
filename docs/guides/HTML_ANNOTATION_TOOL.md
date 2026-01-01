# HTML Annotation Tool - Interactive SID Analysis Generator

**Version**: 1.0.0
**Updated**: 2026-01-01
**For**: SIDM2 v3.0.1+

Generate beautiful, interactive HTML documentation for SID files with comprehensive annotations, clickable navigation, and professional VS Code dark theme styling.

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Quick Start](#quick-start)
4. [Usage Examples](#usage-examples)
5. [Output Structure](#output-structure)
6. [Annotation Types](#annotation-types)
7. [Navigation Features](#navigation-features)
8. [Technical Details](#technical-details)
9. [Customization](#customization)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The HTML Annotation Tool (`generate_stinsen_html.py`) creates comprehensive, interactive HTML documentation from SID music files. It disassembles the player code, extracts all data tables, annotates every byte with semantic meaning, and presents everything in a professional, navigable format.

**Perfect for**:
- Understanding complex SID player internals
- Documenting music file structure
- Educational purposes
- Reverse engineering
- Creating shareable analysis reports

---

## Features

### 🎨 **Visual Design**
- **VS Code Dark Theme** - Professional monospace display
- **Syntax highlighting** - Color-coded assembly and data
- **Responsive layout** - Sidebar + main content
- **Collapsible sections** - Organize information efficiently

### 📊 **Data Analysis**
- **11 section types** identified and annotated:
  1. Voice/Channel Control (406 bytes)
  2. Pulse Table (64 bytes)
  3. Arpeggio Pointers (99 bytes)
  4. Wave Table (32 bytes)
  5. Wave Control (18 bytes)
  6. Wave Note Offsets (32 bytes)
  7. Filter Control (242 bytes)
  8. Filter Table (64 bytes)
  9. Reserved/Padding (13 bytes)
  10. Instrument Table (96 bytes)
  11. Sequence/Arpeggio Data (variable, up to 3,312+ bytes)

- **Smart annotations** for each section type
- **Hex dumps** with ASCII preview
- **Byte-by-byte** semantic decoding

### 🔗 **Navigation**
- **Clickable Memory Layout** - Jump to any section
- **Clickable table names** - VoiceControl, PulseTable, etc.
- **Clickable addresses** - Jump to raw data viewers
- **SID register annotations** - Named registers (Filter: Cutoff Lo, etc.)
- **Cross-references** - Between assembly and data

### 📈 **Analysis Pipeline**
- **Automatic player detection** - Laxity NP21, SF2, etc.
- **6502 disassembly** - Using SIDwinder
- **Code pattern detection** - 16-bit math, loops, etc.
- **Label generation** - Meaningful names (Loop_ClearMemory)
- **Symbol table** - Complete cross-reference

---

## Quick Start

### Basic Usage

```bash
# Analyze a SID file
python pyscript/generate_stinsen_html.py "path/to/file.sid"

# Output will be in analysis/filename_ANNOTATED.html
```

### Example

```bash
# Analyze Stinsen's Last Night of '89
python pyscript/generate_stinsen_html.py "Laxity/Stinsens_Last_Night_of_89.sid"

# Output: analysis/Stinsens_Last_Night_of_89_ANNOTATED.html
```

The HTML file will automatically open in your default browser.

---

## Usage Examples

### Example 1: Laxity NewPlayer V21 File

```bash
python pyscript/generate_stinsen_html.py "Laxity/Stinsens_Last_Night_of_89.sid"
```

**Output**:
- **11 sections** (full Laxity format)
- **3,718 annotations** total
- **Sequence Data**: 3,312 bytes with note/command annotations
- **Voice Control**: 406 bytes with state flags and waveforms

### Example 2: Shorter SID File

```bash
python pyscript/generate_stinsen_html.py "SID/Unboxed_Ending_8580.sid"
```

**Output**:
- **10 sections** (no sequence data)
- **692 annotations** total
- Shorter, simpler structure

### Example 3: Batch Processing

```bash
# Process multiple files
for file in Laxity/*.sid; do
    python pyscript/generate_stinsen_html.py "$file"
done
```

---

## Output Structure

### HTML File Organization

```
📄 [Filename]_ANNOTATED.html
├─ 📊 Statistics Panel (sidebar)
│  ├─ File Info
│  ├─ Player Detection
│  └─ Memory Stats
│
├─ 🏗️ Architectural Insights
│  └─ Player type description
│
├─ 📐 Code Organization
│  ├─ Memory Layout - Complete Map
│  │  └─ All 11 sections with clickable links
│  └─ Structure Summary
│
├─ 🔍 Code Patterns Detected
│  └─ 16-bit math, loops, etc.
│
├─ 💾 Raw Data (11 sections)
│  ├─ Voice/Channel Control
│  ├─ Pulse Table
│  ├─ Arpeggio Pointers
│  ├─ Wave Table
│  ├─ Wave Control
│  ├─ Wave Note Offsets
│  ├─ Filter Control
│  ├─ Filter Table
│  ├─ Reserved
│  ├─ Instrument Table
│  └─ Sequence/Arpeggio Data
│
└─ 📝 Full Assembly Code
   └─ Complete disassembly with inline annotations
```

---

## Annotation Types

### Voice/Channel Control Annotations

```
$16A1: 01 01 01 01 01 01 01 01 01 01 01 02 02 02 02 02
       Flag:1, Flag:1, Flag:1, Flag:1, Flag:1, Flag:1, Flag:1, Flag:1,
       Flag:1, Flag:1, Flag:1, Flag:2, Flag:2, Flag:2, Flag:2, Flag:2

$16C1: 06 07 07 08 08 09 09 0A 0A 0B 0C 0D 0D 0E 0F 10
       Wave:S+P, Wave:All, Wave:All, Wave:Noi, Wave:Noi, Wave:T+N,
       Wave:T+N, Wave:S+N, Wave:S+N, Wave:TSN, Wave:P+N, Wave:TPN,
       Wave:TPN, Wave:SPN, Wave:Full, Val:$10
```

**Categories**:
- `Empty` - Zero value
- `Flag:1-3` - State flags
- `Wave:X` - Waveform values (Tri, Saw, Pulse, Noise, combinations)
- `Idx:X` - Small indices (0x04-0x0F)
- `Val:$XX` - Medium values (0x10-0x3F)
- `Data:$XX` - Higher data (0x40-0x7F)
- `Trans:+X` - Transpose values (0xA0-0xBF)
- `Cmd:$XX` - Command bytes (0xB0-0xCF)
- `Byte:$XX` - Other control bytes
- `Max:$FF` - Maximum value marker

### Sequence/Arpeggio Data Annotations

```
$1ACB: 26 A0 1E 22 FF 00 8F 00 00 7F C4 A0 81 39 39 39
       Note:C#3, Trans:+0, Note:F-2, Note:A-2, Mark:$FF, Rest,
       Ctrl:$8F, Rest, Rest, END, Cmd:$C4, Trans:+0, Dur:$81,
       Note:G#4, Note:G#4, Note:G#4
```

**Categories**:
- `Rest` - Empty/rest beat (0x00)
- `Note:X-Y` - Note names with octaves (0x01-0x5F)
- `Gate:ON/OFF` - Gate control (0x7E/0x80)
- `END` - End of sequence (0x7F)
- `Dur:$XX` - Duration values (0x81-0x8E)
- `Trans:+X` - Transpose semitones (0xA0-0xBF)
- `Cmd:$XX` - Command bytes (0xC0-0xCF)
- `Mark:$FF` - Sequence marker (0xFF)

### Wave Table Annotations

```
$18DA: 21 21 41 7F 81 41 41 41 7F 81 41 80 80 7F 81 01
       Wave:Triangle, Wave:Triangle, Wave:Triangle, Wave:All,
       Wave:Triangle, Wave:Triangle, Wave:Triangle, Wave:Triangle,
       Wave:All, Wave:Triangle, Wave:Triangle, Wave:None, Wave:None,
       Wave:All, Wave:Triangle, Wave:Triangle
```

**Waveforms**:
- `Tri/Triangle` - Triangle wave (0x11, 0x21, 0x41, 0x81)
- `Saw/Sawtooth` - Sawtooth wave
- `Pls/Pulse` - Pulse wave
- `Noi/Noise` - Noise
- `All` - All waveforms (0x7F)
- Combinations: `T+S`, `T+P`, `S+P`, `T+N`, `S+N`, `P+N`, `TSN`, `TPN`, `SPN`

### Pulse Table Annotations

```
$1837: 00 00 00 00 00 08 00 00 00 10 00 00 18 00 00 00
       PW.Lo=$00, PW.Hi=$00, Byte2=$00, Byte3=$00,
       PW.Lo=$00, PW.Hi=$08, Byte2=$00, Byte3=$00,
       PW.Lo=$00, PW.Hi=$10, Byte2=$00, Byte3=$00,
       PW.Lo=$18, PW.Hi=$00, Byte2=$00, Byte3=$00
```

4-byte pulse width entries with decoded values.

### Filter Table Annotations

```
$1A1E: 00 00 00 00 04 04 04 04 08 08 08 08 0C 0C 0C 0C
       Cutoff=$00, Reson=$00, Ctrl=$00, Mode=$00,
       Cutoff=$04, Reson=$04, Ctrl=$04, Mode=$04,
       Cutoff=$08, Reson=$08, Ctrl=$08, Mode=$08,
       Cutoff=$0C, Reson=$0C, Ctrl=$0C, Mode=$0C
```

4-byte filter entries with cutoff, resonance, control, and mode.

### Instrument Table Annotations

```
$1A6B: 25 25 26 26 27 A0 0E 0F 0F 0F 0F 11 01 05 01 04
       Val:$25, Val:$25, Val:$26, Val:$26, Val:$27, Cmd:Loop,
       Wave:SPN, Wave:Full, Wave:Full, Wave:Full, Wave:Full,
       Val:$11, Wave:Tri, Wave:T+P, Wave:Tri, Wave:Pls
```

Commands and waveform sequences for each instrument.

### SID Register Annotations (in Assembly)

```assembly
sta SID0+21  ;  [Filter: Cutoff Lo]    ; Store Accumulator; $167F
sty SID0+22  ;  [Filter: Cutoff Hi]    ; Store Y Register; $1679
sta SID0+23  ;  [Filter: Resonance/Routing] ; Store Accumulator; $1676
```

All 25 SID registers annotated with descriptive names.

---

## Navigation Features

### 1. Memory Layout Navigation

Click any address in the Memory Layout to jump to the raw data hex dump:

```
├─ $16A1-$1836 - Voice/Channel Control (406 bytes)  [CLICK]
       └──> Jumps to hex dump at #data-16a1
```

### 2. Table Name Hyperlinks

Click table names in assembly code to jump to section headers:

```assembly
lda VoiceControl + $E4  [CLICK VoiceControl]
      └──> Jumps to Voice/Channel Control section header
```

### 3. Address Links in Assembly

Click addresses in comments to view raw data:

```assembly
;   ; $16A1 - 16B0  [CLICK $16A1]
      └──> Jumps to hex dump viewer
```

### 4. Section Anchors

Each section has a unique anchor ID for direct linking:

```html
<a id="VoiceControl">...</a>
<a id="PulseTable">...</a>
<a id="SequenceData">...</a>
```

---

## Technical Details

### File Processing Pipeline

```
Input SID File
    ↓
[1] Parse SID Header
    ↓
[2] Extract Music Data
    ↓
[3] Detect Player Type (Laxity NP21, SF2, etc.)
    ↓
[4] Extract Data Sections (Wave, Pulse, Filter, Instrument, etc.)
    ↓
[5] Generate Annotations (Voice Control, Sequence Data)
    ↓
[6] Disassemble with SIDwinder
    ↓
[7] Analyze Assembly (patterns, symbols, labels)
    ↓
[8] Generate HTML (structure, styling, navigation)
    ↓
Output HTML File
```

### Memory Address Calculation

```python
# Known Laxity NewPlayer v21 addresses (relative to load address)
load_addr = 0x1000  # Typical load address

wave_table_addr = 0x18DA
pulse_table_addr = 0x1837
filter_table_addr = 0x1A1E
instrument_table_addr = 0x1A6B
voice_control_addr = 0x16A1
sequence_data_addr = 0x1ACB  # If present
```

### Annotation Functions

```python
annotate_wave_table(data)          # Waveform values
annotate_wave_note_offsets(data)   # Note transpose offsets
annotate_pulse_table(data)         # 4-byte pulse entries
annotate_filter_table(data)        # 4-byte filter entries
annotate_instrument_table(data)    # Commands & waveforms
annotate_voice_control(data)       # Voice state & control
annotate_sequence_data(data)       # Notes, commands, transpose
```

### Color Scheme (VS Code Dark)

| Element | Color | Usage |
|---------|-------|-------|
| Background | `#1e1e1e` | Main background |
| Text | `#d4d4d4` | Normal text |
| Hex bytes | `#ce9178` | Orange - hex data |
| Addresses | `#858585` | Gray - memory addresses |
| ASCII | `#6a9955` | Green - ASCII preview |
| Annotations | `#4fc1ff` | Bright blue - semantic info |
| Section headers | `#dcdcaa` | Yellow - section names |
| Links | `#4ec9b0` | Cyan - clickable links |

---

## Customization

### Modify Output Location

Edit `generate_stinsen_html.py`:

```python
# Change output directory
output_file = Path(f"custom_output/{base_name}_ANNOTATED.html")
```

### Add Custom Annotations

Add new annotation logic:

```python
def annotate_custom_section(data: bytes) -> List[str]:
    """Your custom annotation logic"""
    annotations = []
    for byte in data:
        if byte == 0xFF:
            annotations.append("Special:Marker")
        else:
            annotations.append(f"Value:${byte:02X}")
    return annotations
```

Then apply in extraction:

```python
if name == "Custom Section":
    annotations = annotate_custom_section(data)
```

### Customize Styling

Edit the CSS in `html_export.py`:

```python
# Change colors
body_bg = "#1e1e1e"  # Background
text_color = "#d4d4d4"  # Text
accent_color = "#4ec9b0"  # Links

# Change fonts
font_family = "'Consolas', 'Monaco', 'Courier New', monospace"
```

---

## Troubleshooting

### Issue: "SID file not found"

**Solution**:
```bash
# Use absolute path
python pyscript/generate_stinsen_html.py "C:/full/path/to/file.sid"

# Or relative from project root
python pyscript/generate_stinsen_html.py "Laxity/file.sid"
```

### Issue: "No sections extracted"

**Cause**: File is not Laxity NewPlayer V21 format

**Solution**:
- Check player detection output
- Tool currently optimized for Laxity NP21 files
- Other formats may have different table addresses

### Issue: "SIDwinder.exe not found"

**Solution**:
```bash
# Ensure tools/SIDwinder.exe exists
# Download from project resources if missing
```

### Issue: "Missing annotations in output"

**Cause**: Section wasn't detected or annotated

**Solution**:
1. Check console output for "Added DataBlock_6 section" messages
2. Verify section addresses match your file's format
3. Add custom annotation function if needed

### Issue: "HTML won't open in browser"

**Solution**:
```bash
# Manually open the file
start analysis/filename_ANNOTATED.html  # Windows
open analysis/filename_ANNOTATED.html   # Mac
xdg-open analysis/filename_ANNOTATED.html  # Linux
```

---

## Examples Gallery

### Example 1: Stinsen's Last Night of '89

**File**: `Laxity/Stinsens_Last_Night_of_89.sid`
**Author**: Thomas E. Petersen (Laxity)
**Player**: Laxity NewPlayer V21

**Output**:
- 11 sections
- 3,718 total annotations
- 1,019 assembly lines
- 3,312-byte sequence data
- 19 code patterns detected

**Highlights**:
- Complete sequence data with note names
- All 12 instruments annotated
- Full voice control state tracking

### Example 2: Unboxed Ending (8580)

**File**: `SID/Unboxed_Ending_8580.sid`
**Author**: Thomas Mogensen (DRAX)
**Player**: Laxity NewPlayer V21

**Output**:
- 10 sections
- 692 total annotations
- 968 assembly lines
- No sequence data (shorter tune)
- 19 code patterns detected

**Highlights**:
- Compact structure
- Instrument-focused annotations
- Voice control with embedded code

---

## Command Reference

```bash
# Basic usage
python pyscript/generate_stinsen_html.py <sid_file>

# Examples
python pyscript/generate_stinsen_html.py "Laxity/file.sid"
python pyscript/generate_stinsen_html.py "C:/absolute/path/file.sid"

# Output location
# analysis/<filename>_ANNOTATED.html

# Temp files (can be deleted)
# analysis/<filename>_temp.asm
```

---

## See Also

- **[SIDwinder Documentation](../analysis/SIDWINDER_PYTHON_DESIGN.md)** - Disassembly tool
- **[Player Detection Guide](../implementation/PLAYER_DETECTION.md)** - Format identification
- **[Laxity Format Spec](../reference/LAXITY_FORMAT.md)** - Table structures
- **[SF2 Format Spec](../reference/SF2_FORMAT_SPEC.md)** - Alternative format

---

## Version History

**1.0.0** (2026-01-01)
- Initial release
- Full Laxity NP21 support
- 11 section types
- 7 annotation functions
- Interactive HTML with navigation
- VS Code dark theme styling
- Clickable table names and addresses
- SID register annotations

---

**Tool Created**: 2026-01-01
**Documentation**: Complete
**Status**: Production Ready ✅
