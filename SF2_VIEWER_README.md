# SF2 Viewer - Professional SID Factory II File Viewer

A comprehensive Python-based viewer for SID Factory II (.sf2) files with a modern PyQt6 interface matching the SID Factory II editor layout.

## Features

✨ **Display SF2 File Structure**
- View PRG load address and magic ID
- Parse all SF2 header blocks (Descriptor, Driver Common, Tables, etc.)
- Display block structure and raw data

🎹 **View Music Data**
- Display all tables (Instruments, Wave, Pulse, Filter, Commands, etc.)
- Show table properties (rows, columns, data layout)
- View table memory locations and sizes

🔍 **Analysis Tools**
- File validation summary
- Memory map visualization
- Driver information display
- Critical addresses (init, play, stop routines)

🎯 **Easy File Loading**
- Drag and drop SF2 files directly onto the viewer
- File browser dialog
- File path display

## Installation

### Prerequisites

- Python 3.8 or higher
- PyQt6 (installed via pip)

### Quick Setup

#### Windows (Easiest - Batch Launcher)

```batch
cd SIDM2
launch_sf2_viewer.bat
```

The batch launcher will:
- Check if Python is installed
- Check if PyQt6 is installed
- Offer to install PyQt6 if missing (via pip)
- Launch the SF2 Viewer automatically

#### macOS/Linux

```bash
# Install PyQt6
pip install PyQt6

# Navigate to SIDM2 directory
cd ./SIDM2

# Run the viewer
python sf2_viewer_gui.py
```

OR use the Python launcher:

```bash
cd SIDM2
python launch_sf2_viewer.py
```

### Detailed Installation Steps

#### For Windows Users

1. **Install Python 3.8+**
   - Download from https://www.python.org/downloads/
   - Important: Check "Add Python to PATH" during installation
   - Verify: Open Command Prompt and run `python --version`

2. **Navigate to SIDM2 Directory**
   ```batch
   cd SIDM2
   ```

3. **Run the Batch Launcher**
   ```batch
   launch_sf2_viewer.bat
   ```
   The launcher will automatically:
   - Check for Python installation
   - Check for PyQt6
   - Install PyQt6 if needed (with your confirmation)
   - Launch the SF2 Viewer

#### For macOS/Linux Users

1. **Install Python 3.8+**
   - Using Homebrew (macOS): `brew install python3`
   - Using apt (Linux): `sudo apt-get install python3`

2. **Create Virtual Environment (Optional but Recommended)**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   ```

3. **Install Dependencies**
   ```bash
   pip install PyQt6
   ```

4. **Navigate to SIDM2 Directory**
   ```bash
   cd SIDM2
   ```

5. **Run the Viewer**
   ```bash
   python sf2_viewer_gui.py
   ```

   OR use the Python launcher:
   ```bash
   python launch_sf2_viewer.py
   ```

## Usage

### Loading Files

**Method 1: Drag and Drop**
1. Open the SF2 Viewer
2. Drag an SF2 file onto the window
3. File is loaded automatically

**Method 2: Browse Button**
1. Click the "Browse..." button in the top right
2. Select an SF2 file from the file dialog
3. Click "Open"

**Method 3: File Menu**
1. Click "File" in the menu bar
2. Select "Open SF2 File..."
3. Choose your SF2 file

### Viewing Tabs

#### Overview Tab
- **File Validation Summary**: Quick validation checklist
  - Magic ID verification
  - Load address
  - File size
  - Driver information
  - Critical addresses

- **File Information**: Detailed file information
  - File name and path
  - File size
  - Driver name and version
  - Init/Play/Stop addresses

#### Header Blocks Tab
- **Block Tree**: All SF2 header blocks with their types and sizes
- **Block Details**:
  - Hex dump of block data
  - Parsed information for supported blocks
  - Memory offset location

**Supported Blocks:**
- 0x01: Descriptor (driver name and size)
- 0x02: Driver Common (critical addresses)
- 0x03: Driver Tables (table descriptors)
- 0x04: Instrument Descriptor
- 0x05: Music Data
- 0x06-0x09: Optional blocks (rules, action handlers)

#### Tables Tab
- **Table Selector**: Dropdown to choose which table to view
- **Table Grid**: Display table data in spreadsheet format
  - Each cell shows byte value in hex format
  - Row and column headers for easy navigation
- **Table Info**:
  - Table name and memory address
  - Dimensions (rows × columns)
  - Data layout type (Row-Major or Column-Major)
  - Total data size

**Common Tables:**
- Instruments: Music note instrument definitions
- Wave: Waveform selection and note offset
- Pulse: Pulse width progression
- Filter: Filter cutoff and resonance
- Commands: Special effect commands

#### Memory Map Tab
- **Visual Memory Layout**: ASCII text representation of memory organization
- **Table Locations**: Where each table is stored in memory
- **Critical Addresses**: Init, Play, Stop routine locations

## File Format Details

### SF2 File Structure

```
Offset  Size   Description
------  ----   -----------
$0000   2      PRG Load Address (little-endian)
$0002   2      SF2 Magic: 0x1337 (little-endian)
$0004   var    Header Blocks
                [Block ID: 1 byte]
                [Block Size: 1 byte]
                [Block Data: N bytes]
                ...
                [0xFF: End marker]
$????   var    Driver code
$????   var    Music data
```

### Header Blocks

**Block 1: Descriptor (0x01)**
- Driver type, size, and name
- Identifies the driver implementation

**Block 2: Driver Common (0x02)**
- Critical routine addresses:
  - Init: Player initialization
  - Play/Update: Main player routine
  - Stop: Cleanup routine
  - State tracking locations

**Block 3: Driver Tables (0x03)**
- Descriptors for all music tables
- Memory locations and dimensions
- Data layout (Row-Major or Column-Major)

**Block 4: Instrument Descriptor (0x04)**
- Instrument parameter definitions

**Block 5: Music Data (0x05)**
- Pointers to sequences and orderlists
- Track organization

### Table Data Layouts

**Row-Major (0x00)**
```
Memory: [Row0Col0][Row0Col1][Row1Col0][Row1Col1]...
Access: address = base + row * cols + col
```

**Column-Major (0x01)**
```
Memory: [Row0Col0][Row1Col0][Row0Col1][Row1Col1]...
Access: address = base + col * rows + row
Used by: Driver 11 instruments (optimized for column-wise access)
```

## Examples

### Viewing Broware.sf2

```bash
python sf2_viewer_gui.py
# Then drag Broware.sf2 onto the window
```

The viewer will display:
- **Overview**: Magic ID 0x1337, load address $0D7E, Laxity driver info
- **Header Blocks**: 9 blocks including Descriptor, Driver Common, Driver Tables
- **Tables**: Instruments (32×6), Wave, Pulse, Filter tables
- **Memory Map**: Visual layout of all music data structures

### Checking Table Data

1. Go to "Tables" tab
2. Select "Instruments" from dropdown
3. View 32 rows × 6 columns of instrument data
4. Click on a cell to see value in hex format

Each cell shows:
- Attack/Decay values
- Sustain/Release
- Hard Restart flags
- Wave, Pulse, Filter table indices

## Technical Architecture

### Core Parser (`sf2_viewer_core.py`)

**SF2Parser class:**
- Reads and parses SF2 file structure
- Extracts header blocks
- Parses block data into Python objects
- Provides memory map generation
- Validates file format

**Block Type Enum:**
- Defines all SF2 block type IDs
- Used for block identification and parsing

**TableDescriptor class:**
- Stores table metadata
- Memory location and dimensions
- Data layout type
- Properties and flags

**DriverCommonAddresses class:**
- Stores all critical driver addresses
- Init, Play, Stop routines
- State tracking locations
- Event handling addresses

### GUI (`sf2_viewer_gui.py`)

**SF2ViewerWindow class:**
- Main application window
- Tab-based interface
- File loading (browse + drag-drop)
- Tab update methods

**Tabs:**
- Overview: Summary and file info
- Header Blocks: Tree view of all blocks
- Tables: Dropdown + grid display
- Memory Map: Text visualization

**Features:**
- Syntax highlighting
- Hex dump formatting
- Auto-updating displays
- Responsive layout

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Open file |
| Ctrl+Q | Quit |
| Ctrl+Tab | Switch tabs |

## Troubleshooting

### "PyQt6 is required"
Install with: `pip install PyQt6`

### "Failed to parse SF2 file"
- Verify file is valid SF2 format (magic ID 0x1337)
- Check file is not corrupted
- Try with known good SF2 file first

### Table data shows all zeros
- Table might be empty
- Memory address might be incorrect
- Data layout type might be wrong

### Memory map looks empty
- File might not have Driver Common block
- Critical addresses might not be set

## Development

### Adding New Blocks

To support additional SF2 block types:

1. Add block type to `BlockType` enum in `sf2_viewer_core.py`
2. Add parsing method (e.g., `_parse_custom_block()`)
3. Add display method in GUI
4. Update block_details text in `on_block_selected()`

### Extending Table Support

To add support for additional tables:

1. Ensure `TableDescriptor` is parsed (Block 3)
2. `get_table_data()` automatically formats tables
3. GUI automatically populates table selector
4. Display handles any row/column count

## References

### Documentation
- `SF2_FORMAT_SPEC.md` - Complete SF2 format specification
- `SF2_HEADER_BLOCK_ANALYSIS.md` - Detailed block formats
- `DRIVER_REFERENCE.md` - All SF2 driver specifications
- `SF2_CLASSES.md` - C++ editor class reference

### Source Code
- `sf2_reader.py` - Original SF2Reader implementation
- `constants.py` - Format constants and definitions
- SID Factory II source code (sidfactory2-master)

## License

This viewer is part of the SIDM2 project for analyzing and converting SID music files.

## Version History

**v1.0** (2025-12-14)
- Initial release
- Support for all basic SF2 blocks
- Table display with hex formatting
- Drag-and-drop file loading
- Memory map visualization
- File validation summary

## Future Enhancements

- [ ] Sequence and orderlist viewer
- [ ] Binary editing capabilities
- [ ] SF2 file export/creation
- [ ] Validation report export
- [ ] Comparison tool for multiple SF2 files
- [ ] Player emulation preview
- [ ] Disassembly display
- [ ] Search and filter functions
- [ ] Keyboard shortcuts customization
- [ ] Dark mode theme

