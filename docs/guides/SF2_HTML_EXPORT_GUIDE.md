# SF2 HTML Export - User Guide

**Version**: 1.0.0
**Created**: 2026-01-01

Export SF2 files to professional interactive HTML reports for analysis and documentation.

---

## 🚀 Quick Start

### Command Line

```bash
# Basic usage
python pyscript/sf2_html_exporter.py input.sf2

# Specify output file
python pyscript/sf2_html_exporter.py input.sf2 -o report.html

# Windows batch launcher
sf2-to-html.bat input.sf2
sf2-to-html.bat input.sf2 -o report.html
```

### From Python

```python
from pyscript.sf2_html_exporter import SF2HTMLExporter

exporter = SF2HTMLExporter("input.sf2")
success = exporter.export("output.html")
```

---

## 📊 What's Included

The HTML report includes:

### 1. **Overview Section**
- File information (name, size, load address)
- Statistics dashboard with metric cards
- Quick navigation sidebar

### 2. **File Information**
- File name and size
- Load, init, and play addresses
- Driver type detection

### 3. **Orderlists** (3 voices)
- Sequence playback order for each voice
- Hexadecimal sequence indices
- Visual table format

### 4. **Sequences**
- Summary table (top 20 sequences)
- Note preview (first 3 notes per sequence)
- Detailed expandable view for each sequence
  - Musical notation (C-4, F#-2, etc.)
  - Instrument references (clickable links)
  - Hexadecimal values
  - Color-coded special notes (END, GATE ON/OFF)

### 5. **Instruments** (8 entries)
- 8-byte instrument definitions
- Parameter breakdown (AD, SR, Wave, Pulse)
- Hexadecimal display
- Cross-referenced from sequences

### 6. **Tables**
- Wave table (waveform types)
- Pulse table (pulse width modulation)
- Filter table (cutoff and resonance)
- Arpeggio table (chord effects)

---

## 🎨 Features

### Interactive Elements

- **Search Box**: Filter sequences, instruments, and tables
- **Collapsible Sections**: Click headers to expand/collapse
- **Cross-References**: Click instrument numbers in sequences to jump to instrument definition
- **Smooth Scrolling**: Sidebar navigation with smooth scroll to sections
- **Color Coding**:
  - 🟢 Green: Gate on / sustain notes
  - 🔴 Red: END markers
  - 🟦 Blue: Normal notes
  - ⚪ Gray: Silence / gate off

### Professional Styling

- Dark VS Code-like theme
- Clean, modern interface
- Syntax highlighting for musical notation
- Responsive layout with sidebar
- Mobile-friendly design

### Data Export

- Self-contained HTML (no external dependencies)
- Works offline
- Easy to share (single file)
- Archive-ready
- Print-friendly layout

---

## 📖 Usage Examples

### Export a Test SF2 File

```bash
python pyscript/sf2_html_exporter.py "G5/examples/Driver 11 Test - Arpeggio.sf2"
# Creates: G5/examples/Driver 11 Test - Arpeggio.html
```

### Export with Custom Output Name

```bash
python pyscript/sf2_html_exporter.py "my_music.sf2" -o "analysis_report.html"
```

### Batch Export Multiple Files

```bash
# Windows PowerShell
Get-ChildItem *.sf2 | ForEach-Object {
    python pyscript/sf2_html_exporter.py $_.FullName -o "$($_.BaseName)_report.html"
}

# Bash
for file in *.sf2; do
    python pyscript/sf2_html_exporter.py "$file" -o "${file%.sf2}_report.html"
done
```

---

## 🔍 Understanding the Report

### Orderlist Entries

Orderlists define the playback order of sequences for each of the 3 voices.

```
Voice 1: 00 01 02 03 04 05
Voice 2: 06 07 08 09 0A 0B
Voice 3: 0C 0D 0E 0F 10 11
```

- Each number is a sequence index (hex)
- Voices play in parallel (3 simultaneous tracks)
- 0xFF marks the end of the orderlist

### Sequence Notation

Musical notes are displayed in SID Factory II format:

```
C-4  = Middle C (note 48)
F#-2 = F-sharp in octave 2
---  = Silence (gate off)
+++  = Gate on (sustain)
END  = End of sequence
```

### Instrument References

Instruments are referenced by index (00-07):

```
Seq 00:
  Step  Note  Inst
  000   C-4   02    <- Uses instrument #2
  001   D-4   02
  002   E-4   03    <- Switches to instrument #3
```

Click instrument numbers to jump to instrument definition.

### Color Coding

- **Blue (Teal)**: Normal musical notes
- **Green**: Gate on / sustain (+++, 0x7E)
- **Red**: END marker (0x7F)
- **Gray**: Silence / gate off (---, 0x00)
- **Orange**: Control bytes (0x80+)

---

## ⚙️ Technical Details

### File Format Support

- **SF2 Driver 11**: Full support
- **Laxity Driver**: Partial support (orderlists may be limited)
- **Other formats**: Basic support

### Data Sources

The exporter uses `SF2Parser` from `sf2_viewer_core.py`:

- Orderlists: `parser.orderlist_unpacked` (3 tracks)
- Sequences: `parser.sequences` (dict of SequenceEntry objects)
- Instruments: `parser.instruments` (raw bytes)
- Tables: `parser.wave_table`, `parser.pulse_table`, `parser.filter_table`, `parser.arp_table`

### HTML Components

Built with `html_components.py` library:

- Dark theme CSS (VS Code-like)
- Interactive JavaScript
- Responsive layout
- Self-contained (all assets embedded)

---

## 🐛 Troubleshooting

### "No sequences found"

**Cause**: SF2 file format not fully supported or sequences use non-standard format

**Solution**:
- Check if file is valid SF2 format
- Try with SF2 Driver 11 files (best support)
- File info and orderlists should still display

### "Driver Common block too small"

**Cause**: Warning from parser, not critical

**Solution**: Ignore warning, export should still succeed

### "Music Data block too small"

**Cause**: Warning from parser, not critical

**Solution**: Ignore warning, export should still succeed

### HTML file won't open

**Cause**: File path contains special characters

**Solution**: Use simple ASCII filenames for output

---

## 📚 See Also

- **SF2 Viewer GUI**: `pyscript/sf2_viewer_gui.py` - Interactive GUI viewer
- **SF2 Format Spec**: `docs/reference/SF2_FORMAT_SPEC.md` - Format documentation
- **HTML Components Library**: `docs/reference/HTML_COMPONENTS_LIBRARY.md` - Styling reference
- **SF2 Parser Core**: `pyscript/sf2_viewer_core.py` - Parser implementation

---

## 🎯 Next Steps

After exporting to HTML:

1. **Open in Browser**: Double-click the HTML file
2. **Navigate**: Use sidebar to jump to sections
3. **Search**: Use search box to filter content
4. **Explore**: Click collapsible headers to expand/collapse
5. **Cross-Reference**: Click instrument numbers to jump to definitions
6. **Share**: Send single HTML file (works offline)

---

## 💡 Tips

- **Compare Before/After**: Export original SID and converted SF2 side-by-side
- **Document Conversions**: Include HTML export with conversion results
- **Archive**: HTML reports are perfect for long-term storage
- **Learn**: Study sequence patterns to understand music structure
- **Share**: Send HTML reports to collaborators (no software required)

---

**End of Guide** - Happy analyzing! 🎵
