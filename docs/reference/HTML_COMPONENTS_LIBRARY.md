# HTML Components Library - Quick Reference

**Module**: `pyscript/html_components.py`
**Version**: 1.0.0
**Created**: 2026-01-01

Professional HTML export components with dark VS Code-like theme for SIDM2 tools.

---

## 📚 Components Overview

### Core Components
- **Document Structure**: Header, Footer with metadata
- **Layout**: Sidebar navigation, Main content area
- **Stat Cards**: Metric display with color coding
- **Collapsible Sections**: Expandable/collapsible content
- **Tables**: Professional data tables
- **Code Blocks**: Syntax-highlighted code with line numbers
- **Search**: Filter/search functionality
- **Badges**: Status indicators

### Color Scheme
- **Dark Theme**: VS Code-inspired (#1e1e1e background)
- **Status Colors**: Green (success), Yellow (warning), Red (error), Blue (info)
- **Syntax Highlighting**: Keyword, String, Number, Comment colors
- **Accent Colors**: Teal (#4ec9b0), Blue (#569cd6), Purple (#c586c0)

---

## 🚀 Quick Start

### Basic Usage

```python
from pyscript.html_components import HTMLComponents, StatCard, NavItem, StatCardType

# Create HTML document
html = HTMLComponents.get_document_header("My Report", include_chartjs=True)

# Add stat cards
cards = [
    StatCard("Total Files", "42", StatCardType.SUCCESS),
    StatCard("Accuracy", "99.2%", StatCardType.INFO)
]
html += HTMLComponents.create_stat_grid(cards)

# Add collapsible section
content = HTMLComponents.create_table(
    headers=["File", "Status"],
    rows=[["test.sid", "Success"], ["demo.sid", "Failed"]]
)
html += HTMLComponents.create_collapsible("section1", "Results", content)

# Close document
html += HTMLComponents.get_document_footer()

# Save
from pathlib import Path
Path("report.html").write_text(html, encoding='utf-8')
```

---

## 📦 Component Reference

### 1. Document Structure

#### `get_document_header(title, include_chartjs=False)`
Create HTML document header with CSS.

```python
html = HTMLComponents.get_document_header(
    title="SIDM2 Report",
    include_chartjs=True  # Include Chart.js for graphs
)
```

#### `get_document_footer()`
Create HTML document footer with JavaScript.

```python
html += HTMLComponents.get_document_footer()
```

---

### 2. Layout Components

#### `create_sidebar(title, nav_items, stats=None)`
Create sidebar with navigation and optional stats.

```python
nav_items = [
    NavItem("Overview", "overview"),
    NavItem("Files", "files", count=42),
    NavItem("Results", "results", count=40)
]

stats = [
    StatCard("Success", "95%", StatCardType.SUCCESS),
    StatCard("Failed", "2", StatCardType.ERROR)
]

html += HTMLComponents.create_sidebar("Navigation", nav_items, stats)
```

---

### 3. Stat Cards

#### `create_stat_card(card)`
Create a single stat card.

```python
card = StatCard(
    label="Total Files",
    value="42",
    card_type=StatCardType.PRIMARY,  # PRIMARY, SUCCESS, WARNING, ERROR, INFO
    icon="📊"  # Optional emoji icon
)

html += HTMLComponents.create_stat_card(card)
```

#### `create_stat_grid(cards)`
Create a grid of stat cards.

```python
cards = [
    StatCard("Files", "42", StatCardType.PRIMARY),
    StatCard("Success", "40", StatCardType.SUCCESS),
    StatCard("Failed", "2", StatCardType.ERROR)
]

html += HTMLComponents.create_stat_grid(cards)
```

**Stat Card Types**:
- `StatCardType.PRIMARY` - Blue accent
- `StatCardType.SUCCESS` - Green
- `StatCardType.WARNING` - Orange
- `StatCardType.ERROR` - Red
- `StatCardType.INFO` - Purple

---

### 4. Collapsible Sections

#### `create_collapsible(section_id, title, content, collapsed=False)`
Create expandable/collapsible section.

```python
content = "<p>This is collapsible content</p>"

html += HTMLComponents.create_collapsible(
    section_id="my-section",
    title="Click to Expand",
    content=content,
    collapsed=True  # Start collapsed
)
```

**Interactive Features**:
- Click header to toggle
- Smooth animation
- Icon rotates on toggle
- Keyboard accessible

---

### 5. Tables

#### `create_table(headers, rows, table_class="")`
Create professional data table.

```python
headers = ["File", "Status", "Accuracy"]
rows = [
    ["file1.sid", "Success", "99.5%"],
    ["file2.sid", "Success", "98.8%"],
    ["file3.sid", "Failed", "N/A"]
]

html += HTMLComponents.create_table(headers, rows)
```

**Features**:
- Hover highlighting
- Striped rows (via CSS)
- Responsive width
- Sortable (via JavaScript)

---

### 6. Search Box

#### `create_search_box(placeholder, target_class)`
Create search/filter input.

```python
html += HTMLComponents.create_search_box(
    placeholder="Search files...",
    target_class=".searchable"  # CSS class to filter
)

# Mark elements as searchable
html += '<div class="searchable">Content to search</div>'
```

**Features**:
- Real-time filtering
- Case-insensitive
- Keyboard navigation

---

### 7. Badges

#### `create_badge(text, badge_type)`
Create status badge/tag.

```python
html += HTMLComponents.create_badge("Success", StatCardType.SUCCESS)
html += HTMLComponents.create_badge("Warning", StatCardType.WARNING)
html += HTMLComponents.create_badge("Error", StatCardType.ERROR)
```

**Use Cases**:
- Status indicators in tables
- File type labels
- Driver names
- Accuracy ratings

---

### 8. Code Blocks

#### `create_code_block(code, language="", show_line_numbers=True)`
Create syntax-highlighted code block.

```python
code = """def convert_sid(input_file):
    parser = SIDParser(input_file)
    return parser.convert()"""

html += HTMLComponents.create_code_block(
    code=code,
    language="python",
    show_line_numbers=True
)
```

**Features**:
- Line numbers
- Syntax highlighting classes
- Horizontal scroll for long lines
- Copy-to-clipboard button

---

### 9. Footer

#### `create_footer(version, timestamp)`
Create page footer with generation info.

```python
from datetime import datetime

html += HTMLComponents.create_footer(
    version="3.0.1",
    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)
```

---

## 🎨 Color Scheme Reference

### Background Colors
```python
ColorScheme.BG_PRIMARY      # #1e1e1e (Main background)
ColorScheme.BG_SECONDARY    # #252526 (Sidebar, cards)
ColorScheme.BG_TERTIARY     # #2d2d30 (Code blocks)
ColorScheme.BG_HOVER        # #2a2d2e (Hover states)
```

### Text Colors
```python
ColorScheme.TEXT_PRIMARY    # #d4d4d4 (Main text)
ColorScheme.TEXT_SECONDARY  # #858585 (Muted text)
ColorScheme.TEXT_DISABLED   # #656565 (Disabled text)
```

### Status Colors
```python
ColorScheme.SUCCESS         # #56ab2f (Green)
ColorScheme.WARNING         # #f09819 (Orange)
ColorScheme.ERROR           # #eb3349 (Red)
ColorScheme.INFO            # #667eea (Purple)
```

### Accent Colors
```python
ColorScheme.ACCENT_TEAL     # #4ec9b0 (Primary accent)
ColorScheme.ACCENT_BLUE     # #569cd6 (Secondary accent)
ColorScheme.ACCENT_PURPLE   # #c586c0 (Tertiary accent)
```

---

## 📝 Complete Example

```python
#!/usr/bin/env python3
"""Example: SF2 Analysis Report"""

from pathlib import Path
from datetime import datetime
from pyscript.html_components import (
    HTMLComponents, StatCard, NavItem, StatCardType
)

def generate_sf2_report(sf2_file: str, output_html: str):
    """Generate interactive SF2 analysis report"""

    # Document header
    html = HTMLComponents.get_document_header(
        title=f"{Path(sf2_file).name} - SF2 Analysis",
        include_chartjs=False
    )

    html += '<div class="container">'

    # Sidebar
    nav_items = [
        NavItem("Overview", "overview"),
        NavItem("Orderlists", "orderlists", count=3),
        NavItem("Sequences", "sequences", count=47),
        NavItem("Instruments", "instruments", count=8)
    ]

    sidebar_stats = [
        StatCard("File Size", "12.3 KB", StatCardType.INFO),
        StatCard("Sequences", "47", StatCardType.PRIMARY)
    ]

    html += HTMLComponents.create_sidebar(
        "SF2 Analysis",
        nav_items,
        sidebar_stats
    )

    # Main content
    html += '<div class="main-content">'

    # Header
    html += f'''
    <div class="header">
        <h1>{Path(sf2_file).name}</h1>
        <div class="subtitle">SF2 Format Analysis</div>
    </div>
    '''

    # Stats grid
    stats = [
        StatCard("Orderlists", "3", StatCardType.PRIMARY),
        StatCard("Sequences", "47", StatCardType.INFO),
        StatCard("Instruments", "8", StatCardType.SUCCESS),
        StatCard("Tables", "4", StatCardType.WARNING)
    ]
    html += HTMLComponents.create_stat_grid(stats)

    # Search box
    html += HTMLComponents.create_search_box(
        "Search sequences...",
        ".searchable"
    )

    # Orderlists section
    orderlist_table = HTMLComponents.create_table(
        headers=["Voice", "Sequence Order"],
        rows=[
            ["Voice 1", "00 01 02 03 04 05"],
            ["Voice 2", "06 07 08 09 0A 0B"],
            ["Voice 3", "0C 0D 0E 0F 10 11"]
        ]
    )

    html += HTMLComponents.create_collapsible(
        "orderlists",
        "Orderlists (3 voices)",
        orderlist_table,
        collapsed=False
    )

    # Sequences section
    sequences_content = "<p>47 sequences analyzed...</p>"
    html += HTMLComponents.create_collapsible(
        "sequences",
        "Sequences (47)",
        sequences_content,
        collapsed=True
    )

    # Footer
    html += HTMLComponents.create_footer(
        "3.0.1",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    html += '</div>'  # main-content
    html += '</div>'  # container

    # Document footer
    html += HTMLComponents.get_document_footer()

    # Save
    Path(output_html).write_text(html, encoding='utf-8')
    print(f"[OK] Report generated: {output_html}")


if __name__ == '__main__':
    generate_sf2_report("test.sf2", "sf2_report.html")
```

---

## 🔧 JavaScript API

### Interactive Functions

```javascript
// Toggle collapsible section
toggleCollapsible('section-id');

// Search/filter content
searchContent('query', '.target-class');

// Copy to clipboard
copyToClipboard('text to copy');

// Show notification
showNotification('Message', 3000);  // duration in ms

// Smooth scroll to anchor
scrollToAnchor('section-id');
```

### Auto-initialized Features

- Collapsible headers (click to toggle)
- Smooth scroll navigation
- Keyboard accessibility

---

## 📁 File Structure

```
pyscript/
  html_components.py          # Main library (28 KB, 1002 lines)

output/
  html_components_demo.html   # Demo page (18 KB)

docs/reference/
  HTML_COMPONENTS_LIBRARY.md  # This guide
```

---

## 🎯 Usage in SIDM2 Tools

### SF2 Viewer HTML Export
```python
from pyscript.html_components import HTMLComponents
from pyscript.sf2_viewer_core import SF2Parser

# Use components to generate SF2 HTML report
```

### Conversion Cockpit Batch Reports
```python
from pyscript.html_components import HTMLComponents

# Use components to generate batch conversion report
```

### SIDwinder Frame Trace
```python
from pyscript.html_components import HTMLComponents

# Use components to generate interactive frame trace
```

---

## ✅ Testing

Run the demo to see all components:
```bash
python pyscript/html_components.py
# Opens output/html_components_demo.html
```

---

## 📚 References

- **Source**: `pyscript/html_components.py`
- **Demo**: `output/html_components_demo.html`
- **Patterns**: Based on `pyscript/html_export.py` (annotation tool)
- **Styling**: VS Code dark theme

---

**End of Reference** - Ready to use in SIDM2 tools! 🚀
