# HTML Annotation Tool Learnings - Application to SIDM2 Tools

**Created**: 2026-01-01
**Purpose**: Identify reusable patterns from HTML annotation tool for enhancing SIDM2 tools

---

## 🎨 Key Patterns from HTML Annotation Tool

### 1. **Interactive HTML Generation Architecture**

**Pattern**: Self-contained HTML with embedded CSS/JS
```python
def generate_html_export(...) -> str:
    """Generate interactive HTML with all assets embedded"""
    html_parts = []
    html_parts.append(_get_html_header(title))      # CSS embedded
    html_parts.append(_get_html_body(...))          # Content
    html_parts.append(_get_html_footer())           # JS embedded
    return "".join(html_parts)
```

**Benefits**:
- ✅ Single-file export (no dependencies)
- ✅ Works offline
- ✅ Easy to share/archive
- ✅ No server required

---

### 2. **Visual Design System**

**Dark Theme VS Code-like Styling**:
```css
body {
    background: #1e1e1e;
    color: #d4d4d4;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}
.sidebar { background: #252526; }
.stat-value { color: #4ec9b0; }  /* Teal accent */
```

**Stat Cards**:
```css
.stat-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
}
.stat-item {
    background: #1e1e1e;
    padding: 12px;
    border-radius: 4px;
}
```

**Benefits**:
- ✅ Professional appearance
- ✅ Easy to read (high contrast)
- ✅ Consistent with developer tools
- ✅ Reusable component library

---

### 3. **Interactive Features**

**Collapsible Sections**:
```javascript
function toggleSection(id) {
    const section = document.getElementById(id);
    section.classList.toggle('collapsed');
}
```

**Search/Filter**:
```javascript
function searchCode(query) {
    // Filter visible elements based on query
    // Highlight matches
}
```

**Jump-to-Section Navigation**:
```html
<nav class="sidebar">
    <a href="#subroutines">Subroutines (15)</a>
    <a href="#loops">Loops (8)</a>
    <a href="#patterns">Patterns (23)</a>
</nav>
```

**Benefits**:
- ✅ Progressive disclosure (hide complexity)
- ✅ Quick navigation to relevant sections
- ✅ Better UX for large datasets

---

### 4. **Data Visualization Patterns**

**Cross-References (XRefs)**:
```python
# Link related code sections
xrefs = {
    0x1000: [
        {'type': 'call', 'from': 0x10A1, 'label': 'init_sid'},
        {'type': 'jump', 'from': 0x10F3, 'label': 'main_loop'}
    ]
}
```

**Pattern Detection**:
```python
patterns = [
    {'type': 'SID_WRITE', 'addr': 0x1234, 'register': 'FREQ_LO'},
    {'type': 'LOOP', 'addr': 0x1250, 'iterations': 8}
]
```

**Color Coding**:
- 🟢 Green: Success/Normal
- 🟡 Yellow: Warning/Attention
- 🔴 Red: Error/Critical
- 🔵 Blue: Info/Note

**Benefits**:
- ✅ Quick pattern recognition
- ✅ Visual hierarchy
- ✅ Cognitive load reduction

---

## 🎯 Application to SIDM2 Tools

### **1. SF2 Viewer - HTML Export Feature** ⭐ HIGH VALUE

**Current State**: PyQt6 GUI only, no export
**Opportunity**: Add HTML export matching annotation tool quality

#### Implementation Plan

**New File**: `pyscript/sf2_html_exporter.py`

```python
class SF2HTMLExporter:
    """Export SF2 data to interactive HTML"""

    def export(self, sf2_file: str, output_html: str):
        """Generate interactive HTML report"""
        parser = SF2Parser(sf2_file)

        html = self._build_html(
            stats=self._get_stats(parser),
            orderlists=parser.orderlists,
            sequences=parser.sequences,
            instruments=parser.instruments,
            tables=self._get_tables(parser)
        )

        Path(output_html).write_text(html)
```

#### Features to Include

**Sidebar Navigation**:
- 📊 Statistics (file size, driver, tables)
- 📋 Orderlists (3 voices)
- 🎵 Sequences (expandable)
- 🎹 Instruments (8 entries)
- 📈 Tables (Wave, Pulse, Filter, Arpeggio)

**Main Content**:
- **Header**: File info, load address, driver type
- **Statistics Cards**: Like annotation tool stat grid
- **Orderlists**: Table with voice 1/2/3 sequence order
- **Sequences**: Collapsible sections per sequence
  - Notes in musical notation (C-4, F#-2)
  - Instrument references (clickable → jump to instrument)
  - Special commands highlighted (END, GATE ON/OFF, TRANSPOSE)
- **Instruments**: 8-byte hexdump + parameter breakdown
- **Tables**: Visual representation (waveforms, pulse widths, filter values)

**Interactive Features**:
- 🔍 Search sequences for specific notes/patterns
- 📎 Cross-reference: Click instrument → see all sequences using it
- 🎨 Syntax highlighting for commands
- 📋 Copy sequence data to clipboard

**Styling**: Reuse annotation tool CSS with SF2-specific colors

#### Value Proposition
- **Users**: Share SF2 analysis without installing GUI
- **Documentation**: Archive SF2 structure for reference
- **Debugging**: Compare before/after conversions visually
- **Learning**: Understand SF2 format interactively

**Effort**: 4-6 hours
**Priority**: P1 (High) - Complements SF2 Viewer GUI

---

### **2. Conversion Cockpit - Batch Report Generation** ⭐ HIGH VALUE

**Current State**: Results only in GUI
**Opportunity**: Export batch conversion results as professional HTML report (CC-4)

#### Implementation Plan

**New File**: `pyscript/cockpit_report_generator.py`

```python
class CockpitReportGenerator:
    """Generate HTML reports for batch conversions"""

    def generate_report(self, batch_results: List[Dict], output_html: str):
        """Create interactive HTML report from batch results"""

        html = self._build_html(
            summary=self._get_summary_stats(batch_results),
            files=batch_results,
            charts=self._generate_charts_data(batch_results),
            config=self._get_batch_config(batch_results)
        )

        Path(output_html).write_text(html)
```

#### Features to Include

**Report Sections**:
1. **Executive Summary** (Top Card)
   - Total files processed
   - Success rate (green/yellow/red)
   - Average accuracy
   - Total time / Avg per file
   - Driver breakdown

2. **Charts** (Chart.js like validation dashboard)
   - Success vs Failed pie chart
   - Accuracy distribution histogram
   - Processing time per file bar chart
   - Driver usage pie chart

3. **File-by-File Details** (Collapsible)
   - ✅/❌ Status icon
   - Input file name
   - Output file size
   - Driver used
   - Accuracy % (if validation enabled)
   - Duration
   - Error message (if failed)
   - **NEW**: Mini hex dump preview (first 128 bytes)
   - **NEW**: Link to detailed SF2 HTML export

4. **Configuration Used**
   - Driver selection
   - Pipeline mode
   - Steps enabled
   - Concurrent workers
   - Output directory

**Interactive Features**:
- 🔍 Filter by status (success/failed/warning)
- 📊 Sort by accuracy, size, duration
- 📋 Export summary as CSV
- 🔗 Generate individual SF2 HTML reports (link to feature #1)

**Styling**: Reuse annotation tool dark theme + validation dashboard gradients

#### Value Proposition
- **Professional**: Shareable reports for clients/teams
- **Archival**: Record of batch conversions
- **Analysis**: Identify patterns in failures
- **Documentation**: Proof of conversion quality

**Effort**: 4-5 hours
**Priority**: P2 (Medium) - Fulfills CC-4 requirement

---

### **3. SIDwinder/siddump - Interactive Frame Trace** ⭐ MEDIUM VALUE

**Current State**: Text-only frame dumps
**Opportunity**: HTML visualization of SID register changes over time

#### Implementation Plan

**Enhancement to**: `pyscript/siddump_complete.py`

```python
def export_html_trace(frames: List[Frame], output_html: str):
    """Export frame trace as interactive HTML"""

    html = _build_trace_html(
        frames=frames,
        stats=_analyze_frames(frames),
        patterns=_detect_patterns(frames)
    )

    Path(output_html).write_text(html)
```

#### Features to Include

**Sidebar**:
- 📊 Frame count
- 🎵 Active voices
- 📈 Register write count
- ⏱️ Frame rate
- 🔍 Quick jump to frame N

**Main Timeline**:
- **Frame-by-frame view** (collapsible)
  - Frame number
  - Timestamp
  - Register writes (color-coded by voice)
    - Voice 1: 🔵 Blue (D400-D406)
    - Voice 2: 🟢 Green (D407-D40D)
    - Voice 3: 🟡 Yellow (D40E-D414)
    - Filter: 🟣 Purple (D415-D417)
  - Changed values highlighted
  - **NEW**: Waveform visualization (ASCII art: /\\/\\/\\)
  - **NEW**: Note name (e.g., "C-4" from freq value)

**Interactive Features**:
- 🎬 Play/Pause animation (auto-step through frames)
- 🔍 Filter by voice/register
- 📊 Graph frequency over time
- 🎨 Diff mode (show only changes)

**Styling**: Dark theme with register-specific colors

#### Value Proposition
- **Debugging**: Visual analysis of player behavior
- **Learning**: Understand SID programming patterns
- **Comparison**: Side-by-side before/after traces

**Effort**: 6-8 hours
**Priority**: P3 (Low) - Nice to have, not essential

---

### **4. Validation Dashboard - Enhanced Features** ⭐ LOW VALUE

**Current State**: Basic HTML dashboard with Chart.js
**Opportunity**: Add annotation-style interactive features

#### Quick Wins

**Add to**: `scripts/generate_dashboard.py`

1. **Collapsible File Details**
   ```javascript
   // Expand each file to show:
   // - Input/output sizes
   // - Driver used
   // - Accuracy breakdown (register writes, frame count)
   // - Link to SF2 HTML export
   ```

2. **Search/Filter Files**
   ```javascript
   function filterFiles(query) {
       // Filter visible files by name
       // Filter by driver type
       // Filter by accuracy range
   }
   ```

3. **Export Individual File Reports**
   ```python
   def generate_file_report(file_result: Dict) -> str:
       """Generate single-file HTML report"""
       # Reuse batch report template
       # Focus on one file with full details
   ```

**Effort**: 2-3 hours
**Priority**: P3 (Low) - Dashboard already functional

---

## 📊 Effort vs Value Matrix

| Feature | Effort | Value | Priority | Status |
|---------|--------|-------|----------|--------|
| **SF2 Viewer HTML Export** | 4-6h | HIGH | P1 | Not Started |
| **Cockpit Batch Reports** | 4-5h | HIGH | P2 | Fulfills CC-4 |
| **Dashboard Enhancements** | 2-3h | LOW | P3 | Quick wins |
| **SIDwinder HTML Trace** | 6-8h | MEDIUM | P3 | Future |

---

## 🎯 Recommended Implementation Order

### Phase 1: High-Value Quick Wins (6-9 hours)
1. **SF2 Viewer HTML Export** (4-6h)
   - Reuse annotation tool HTML structure
   - SF2-specific content (orderlists, sequences, instruments, tables)
   - Add to SF2 Viewer menu: File → Export to HTML

2. **Cockpit Batch Reports** (4-5h)
   - Reuse annotation tool stats cards
   - Add Chart.js from validation dashboard
   - Integrate with Conversion Cockpit Results tab
   - Completes CC-4 from IMPROVEMENTS_TODO.md

### Phase 2: Dashboard Polish (2-3 hours)
3. **Validation Dashboard Enhancements** (2-3h)
   - Add collapsible file details
   - Add search/filter
   - Link to SF2 HTML exports

### Phase 3: Future Enhancement (6-8 hours)
4. **SIDwinder HTML Trace** (6-8h)
   - Interactive frame-by-frame visualization
   - Optional enhancement for advanced debugging

---

## 🔧 Reusable Components Library

Create shared HTML components to maximize code reuse:

**New File**: `pyscript/html_components.py`

```python
"""Shared HTML components for SIDM2 tools"""

class HTMLComponents:
    """Reusable HTML/CSS/JS components"""

    @staticmethod
    def get_dark_theme_css() -> str:
        """VS Code-like dark theme (from annotation tool)"""
        return """
        body { background: #1e1e1e; color: #d4d4d4; }
        .sidebar { background: #252526; }
        /* ... full CSS ... */
        """

    @staticmethod
    def get_stat_card(label: str, value: str, color: str = 'primary') -> str:
        """Metric card component"""
        return f"""
        <div class="metric-card {color}">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """

    @staticmethod
    def get_collapsible_section(title: str, content: str, id: str) -> str:
        """Collapsible section component"""
        return f"""
        <div class="collapsible-section">
            <h3 onclick="toggleSection('{id}')">{title}</h3>
            <div id="{id}" class="content">{content}</div>
        </div>
        """

    @staticmethod
    def get_interactive_js() -> str:
        """Common JavaScript functions"""
        return """
        function toggleSection(id) { ... }
        function searchContent(query) { ... }
        function copyToClipboard(text) { ... }
        """
```

**Benefits**:
- ✅ Consistent styling across all tools
- ✅ Reduce code duplication
- ✅ Easy to maintain and update
- ✅ Professional appearance

---

## 🎨 Visual Consistency Guide

### Color Palette (from annotation tool)

```css
/* Primary Colors */
--bg-primary: #1e1e1e;
--bg-secondary: #252526;
--text-primary: #d4d4d4;
--text-secondary: #858585;
--accent-teal: #4ec9b0;
--accent-blue: #569cd6;

/* Status Colors */
--success: #56ab2f;  /* Green */
--warning: #f09819;  /* Orange */
--error: #eb3349;    /* Red */
--info: #667eea;     /* Purple */

/* Syntax Highlighting */
--keyword: #569cd6;  /* Blue */
--string: #ce9178;   /* Orange */
--number: #b5cea8;   /* Light green */
--comment: #6a9955;  /* Green */
```

### Typography

```css
--font-mono: 'Consolas', 'Monaco', 'Courier New', monospace;
--font-sans: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
```

---

## 📝 Implementation Checklist

### For Each New HTML Export Feature:

- [ ] Create exporter class in `pyscript/`
- [ ] Reuse `HTMLComponents` library
- [ ] Include dark theme CSS
- [ ] Add stat cards for key metrics
- [ ] Implement collapsible sections
- [ ] Add search/filter functionality
- [ ] Include copy-to-clipboard
- [ ] Test with sample files
- [ ] Add to tool's menu/UI
- [ ] Document in user guide
- [ ] Add unit tests

---

## 🚀 Quick Start: SF2 HTML Export

To demonstrate the pattern, here's a minimal SF2 HTML export:

```python
#!/usr/bin/env python3
"""SF2 HTML Exporter - Minimal Example"""

from pathlib import Path
from pyscript.html_components import HTMLComponents
from pyscript.sf2_viewer_core import SF2Parser

def export_sf2_to_html(sf2_file: str, output_html: str):
    """Export SF2 to interactive HTML"""

    parser = SF2Parser(sf2_file)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{Path(sf2_file).name} - SF2 Analysis</title>
        <style>{HTMLComponents.get_dark_theme_css()}</style>
    </head>
    <body>
        <div class="container">
            <h1>{Path(sf2_file).name}</h1>

            <div class="stat-grid">
                {HTMLComponents.get_stat_card("File Size", f"{parser.file_size:,} bytes")}
                {HTMLComponents.get_stat_card("Sequences", str(len(parser.sequences)))}
                {HTMLComponents.get_stat_card("Instruments", "8")}
            </div>

            {HTMLComponents.get_collapsible_section(
                "Orderlists",
                _format_orderlists(parser.orderlists),
                "orderlists"
            )}

            {HTMLComponents.get_collapsible_section(
                "Sequences",
                _format_sequences(parser.sequences),
                "sequences"
            )}
        </div>

        <script>{HTMLComponents.get_interactive_js()}</script>
    </body>
    </html>
    """

    Path(output_html).write_text(html)
    print(f"✅ Exported to: {output_html}")

# Usage:
# export_sf2_to_html("test.sf2", "test_analysis.html")
```

---

## 📚 References

- **Annotation Tool**: `pyscript/annotate_asm.py`, `pyscript/html_export.py`
- **Validation Dashboard**: `validation/dashboard.html`, `scripts/generate_dashboard.py`
- **SF2 Viewer**: `pyscript/sf2_viewer_gui.py`, `pyscript/sf2_viewer_core.py`
- **SF2 Exporter**: `pyscript/sf2_to_text_exporter.py`

---

**End of Analysis** - Ready to implement! 🚀
