# SF2 Viewer & Tools Guide

Complete guide to SF2 viewing, analysis, and export tools.

**Version**: 2.4.0
**Last Updated**: 2025-12-21

---

## Table of Contents

1. [SF2 Viewer GUI](#sf2-viewer-gui)
2. [SF2 Text Exporter](#sf2-text-exporter)
3. [SF2 Editor Enhancements](#sf2-editor-enhancements)

---

## SF2 Viewer GUI

Professional PyQt6 GUI tool for viewing and analyzing SF2 files.

### Quick Start

```bash
# Windows (simplest - batch launcher with auto-dependency installation)
cd SIDM2
launch_sf2_viewer.bat

# Or cross-platform with Python launcher
cd SIDM2
python launch_sf2_viewer.py

# Or direct launch (requires PyQt6 installed)
cd SIDM2
python pyscript/sf2_viewer_gui.py
```

### Core Features

**File Loading**:
- Drag-and-drop SF2 file loading
- Recent Files menu for quick access to last 10 files
- File validation on load

**Multi-Tab Interface** (8 tabs):
1. **Overview**: File info and validation summary
2. **Header Blocks**: SF2 block structure and metadata
3. **Tables**: Music data tables in spreadsheet view
4. **Memory Map**: Visual memory layout diagram
5. **OrderList**: XXYY unpacked format (transpose + sequence)
6. **Sequences**: Step-by-step sequence data with auto-format detection
7. **Visualization**: Waveform, filter, and envelope graphs
8. **Playback**: Audio preview with play/pause/volume controls

**Smart Features**:
- Auto-detects single-track vs 3-track interleaved sequences
- Hex notation display: "Sequence 10 ($0A)" matching SID Factory II
- OrderList unpacking: Shows A00E as "transpose A0, sequence 0E"
- Professional GUI matching SID Factory II editor layout

### Version History

**v2.4 (2025-12-21)**:
- **Track View Tab**: Combines OrderList + Sequences with transpose applied
- **OrderList Transpose Decoding**: Shows A00E (+0), A20A (+2), AC0F (-4)
- **Track Selector**: Switch between Track 1/2/3 views
- **100% Feature Parity**: Matches C++ editor and Python exporter exactly

**v2.3 (2025-12-21)**:
- **OrderList XXYY Format**: Unpacked display (A00E, A20A, etc.)
- **Transpose Change Tracking**: Notes when transpose changes
- **SF2 Editor Parity**: OrderList matches C++ editor display

**v2.2 (2025-12-18)**:
- **Single-track sequence support**: Auto-detects format correctly
- **Hex notation**: Sequence numbering matches SID Factory II
- **96.9% Track 3 accuracy**: Correct Track 3 extraction

**v2.1**:
- **Recent Files Menu**: Persistent storage of last 10 files
- **Visualization Tab**: Graph waveforms, filters, ADSR envelopes
- **Playback Tab**: SF2→SID→WAV conversion with audio playback
- Real-time position tracking and status display

### Tab Details

#### 1. Overview Tab
- File path and size
- Load address
- Driver type detection
- Block count summary
- Validation status

#### 2. Header Blocks Tab
- Complete SF2 block structure
- Block types and sizes
- Memory addresses
- Metadata extraction

#### 3. Tables Tab
Spreadsheet view of music data:
- OrderLists (3 voices)
- Sequences (up to 128)
- Instruments (32 entries)
- Wave tables
- Pulse tables
- Filter tables

#### 4. Memory Map Tab
Visual ASCII diagram showing:
- Driver code region
- Header blocks region
- Music data region
- Memory usage statistics

#### 5. OrderList Tab
XXYY unpacked format display:
- XX = transpose value (A0 = +0, A2 = +2, AC = -4)
- YY = sequence index (00-7F)
- Transpose change tracking
- Matches SF2 editor display exactly

#### 6. Sequences Tab
Step-by-step sequence data:
- Auto-format detection (single-track vs 3-track)
- Hex notation: "Sequence 10 ($0A)"
- Note values, instruments, commands
- Duration and gate control
- End markers and loops

#### 7. Visualization Tab
Interactive graphs:
- **Waveform graphs**: Visual wave table data
- **Filter curves**: Filter frequency/resonance plots
- **ADSR envelopes**: Attack/Decay/Sustain/Release visualization
- Matplotlib-based interactive plots

#### 8. Playback Tab
Audio preview system:
- **Convert**: SF2→SID→WAV conversion
- **Play/Pause**: Audio playback controls
- **Volume**: 0-100% volume slider
- **Position**: Real-time playback position
- **Status**: Conversion and playback status

### Technical Details

**Implementation**:
- Core: `pyscript/sf2_viewer_gui.py` (main GUI)
- Parser: `pyscript/sf2_viewer_core.py` (SF2 format parser, 500 lines)
- Visualization: `pyscript/sf2_visualization_widgets.py` (300 lines)
- Playback: `pyscript/sf2_playback.py` (200 lines)

**Dependencies**:
- PyQt6 (GUI framework)
- Matplotlib (visualization)
- Python standard library (wave, struct, pathlib)

**File Format Support**:
- SF2 files (SID Factory II format)
- All driver types (11, 12, 13, 14, 15, 16, NP20)
- Single-track and 3-track interleaved sequences

---

## SF2 Text Exporter

Export all SF2 data to human-readable text files for validation and debugging.

### Quick Start

```bash
# Export single file
python pyscript/sf2_to_text_exporter.py "file.sf2" output/export_dir

# Auto-generate output directory
python pyscript/sf2_to_text_exporter.py "learnings/Laxity - Stinsen.sf2"
# Output: output/Laxity - Stinsen_export/
```

### Exported Files

**Core Files**:
- **orderlist.txt** - Sequence playback order in XXYY format
- **track_1.txt** - Track 1 with musical notation
- **track_2.txt** - Track 2 with musical notation
- **track_3.txt** - Track 3 with musical notation
- **sequence_XX.txt** - Individual sequences (128 files)
- **instruments.txt** - Instrument definitions (AD, SR, waveform, tables, HR)

**Table Files**:
- **wave.txt** - Wave table data
- **pulse.txt** - Pulse table data
- **filter.txt** - Filter table data

**Reference Files**:
- **commands.txt** - Command reference guide
- **summary.txt** - Export statistics and file list

### Features (v2.3)

**OrderList XXYY Format**:
- Shows unpacked format: A00E = transpose A0, sequence 0E
- Transpose values: A0 (+0), A2 (+2), AC (-4), etc.
- Matches SF2 editor display exactly

**Track Export**:
- 3 files combining OrderList + Sequences
- Musical notation: C-4, F#-2, +++ (sustain), --- (silence)
- Transpose applied to note values
- Shows +0, +2, -4 semitones in headers

**Format Detection**:
- Auto-detects single-track vs 3-track interleaved format
- Correct parsing of all sequence types
- 100% feature parity with SF2 C++ editor track export (F8 key)

### Use Cases

1. **Validation**: Create reference files from known-good SF2 files
2. **Debugging**: Compare text exports to find conversion issues
3. **Learning**: Study SF2 format through human-readable output
4. **Comparison**: Validate against SF2 editor track display
5. **Documentation**: Generate human-readable music data for analysis

### Example Output

**orderlist.txt**:
```
# OrderList (XXYY format: XX=transpose, YY=sequence)
# Voice 1
A00E  # +0 semitones, Sequence 14
A00F  # +0 semitones, Sequence 15
A010  # +0 semitones, Sequence 16

# Voice 2
A20A  # +2 semitones, Sequence 10
A20B  # +2 semitones, Sequence 11
```

**track_1.txt**:
```
=== Track 1 (Voice 1) ===
Transpose: +0 semitones

OrderList Position 0: A00E (Transpose: A0, Sequence: 0E)
  Step 0: C-4 Instr:00 Cmd:00 Dur:4
  Step 1: E-4 Instr:00 Cmd:00 Dur:4
  Step 2: G-4 Instr:00 Cmd:00 Dur:4
  Step 3: +++ Instr:00 Cmd:00 Dur:8
```

**instruments.txt**:
```
# Instruments (32 entries)
Instrument 00: AD=09 SR=00 Wave=11 Pulse=00 Filter=00 HR=00
Instrument 01: AD=0F SR=08 Wave=21 Pulse=01 Filter=01 HR=80
```

### Technical Details

**Implementation**:
- Script: `pyscript/sf2_to_text_exporter.py` (v2.3.0)
- Parser: `pyscript/sf2_viewer_core.py` (shared with GUI)
- Pure Python (no external dependencies)

**Format Compatibility**:
- All SF2 driver types supported
- Single-track and 3-track interleaved sequences
- XXYY orderlist format
- Musical notation matching SF2 editor

---

## SF2 Editor Enhancements

Custom modifications to SID Factory II editor for enhanced export and usability.

**Build Location**: `C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master\`
**Executable**: `x64\Release\SIDFactoryII.exe` (987 KB)

### New Features

#### 1. Track Export with Musical Notation

**Keyboard Shortcut**: Press **F8** to export

**Creates 3 New Files**:
- `track_1.txt` - Track 1 musical notation
- `track_2.txt` - Track 2 musical notation
- `track_3.txt` - Track 3 musical notation

**Features**:
- Unpacked sequences organized by OrderList positions
- Musical notation: C-4, F#-2, +++ (sustain), --- (silence)
- OrderList references: "OrderList: A00E"
- Duration expanded into visible sustain steps
- Transpose applied to note values

#### 2. Enhanced OrderList Export

**File**: `orderlist.txt` (created with F8 export)

**Format**: Unpacked XXYY display
- XX = transpose value (A0, A2, AC, etc.)
- YY = sequence index (00-7F)
- Matches SF2 editor OrderList display exactly

#### 3. Build Timestamp

**Feature**: Window title shows build date/time

**Example**: `SID Factory II (Build: Dec 21 2025 07:58:12)`

**Purpose**: Version tracking and debugging

#### 4. Zoom Functionality

**Keyboard Shortcuts**:
- **Ctrl + +** (or Ctrl + =) - Zoom In (0.25x increments)
- **Ctrl + -** - Zoom Out (0.25x decrements)
- **Ctrl + 0** - Reset to original zoom

**Range**: 0.5x to 4.0x zoom levels

**Use Case**: Perfect for high-resolution screenshots

### Export Files Created

After **F8** export in SF2 editor (total 148 files):

```
exports/music_data_export/
├── orderlist.txt              # NEW: Unpacked XXYY format
├── track_1.txt                # NEW: Track 1 musical notation
├── track_2.txt                # NEW: Track 2 musical notation
├── track_3.txt                # NEW: Track 3 musical notation
├── sequence_00.txt            # Original: 128 packed sequence files
├── sequence_01.txt
├── ...
├── sequence_7F.txt
├── instruments.txt            # Original: Instrument definitions
├── wave.txt                   # Original: Wave table
├── pulse.txt                  # Original: Pulse table
├── filter.txt                 # Original: Filter table
└── [other files]              # Original: Commands, init, arp, etc.
```

### Technical Implementation

**Files Modified**:
1. `table_text_exporter.h/cpp` - Track and OrderList export
2. `viewport.h/cpp` - Zoom functionality and build timestamp
3. `editor_facility.cpp` - Keyboard shortcut handling

**Code Statistics**:
- Lines added: ~370
- New methods: 7 total
  - `ExportTracks()`
  - `FormatNote()`
  - `ZoomIn()`
  - `ZoomOut()`
  - `ResetZoom()`
  - `SetScaling()`
  - `GetScaling()`

**Build Requirements**:
- Visual Studio 2019/2022
- SDL2 library
- Windows platform

### Complete Documentation

**See**: `docs/SF2_EDITOR_ENHANCEMENTS.md` for:
- Complete implementation details
- Source code changes
- Build instructions
- Testing procedures

---

## Related Documentation

- **SF2 Format Specification**: `docs/SF2_FORMAT_SPEC.md`
- **SF2 Tracks & Sequences**: `docs/SF2_TRACKS_AND_SEQUENCES.md`
- **SF2 Instruments**: `docs/SF2_INSTRUMENTS_REFERENCE.md`
- **Text Exporter README**: `SF2_TEXT_EXPORTER_README.md`
- **Editor Enhancements**: `docs/SF2_EDITOR_ENHANCEMENTS.md`

---

## Troubleshooting

### Viewer Won't Launch

**Issue**: PyQt6 not installed

**Solution**:
```bash
# Use batch launcher (auto-installs dependencies)
launch_sf2_viewer.bat

# Or install manually
pip install PyQt6 matplotlib
```

### Export Fails

**Issue**: Invalid SF2 file format

**Solution**:
1. Check file size (must be ≥2 bytes for load address)
2. Verify file is valid SF2/PRG format
3. Check for file corruption
4. Try opening in SF2 editor first

### Playback Not Working

**Issue**: Missing tools (sf2_to_sid.py, SID2WAV.EXE)

**Solution**:
1. Ensure `scripts/sf2_to_sid.py` exists
2. Ensure `tools/SID2WAV.EXE` exists
3. Check Python path configuration
4. Verify SF2→SID conversion works separately

---

**Last Updated**: 2025-12-21
**Version**: 2.4.0
