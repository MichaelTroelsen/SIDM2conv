# SID Factory II Source Code Analysis

*Implementation details from the SF2 editor C++ source code*

## Overview

This document captures implementation details discovered from analyzing the SID Factory II editor source code. These insights are crucial for correctly implementing SF2 file reading/writing.

**Source Location**: `SIDFactoryII/source/`

---

## Directory Structure

```
SIDFactoryII/source/
├── foundation/          # Cross-platform utilities (graphics, sound, input)
├── libraries/           # Third-party (residfp, miniz, picopng)
├── runtime/
│   ├── editor/          # Main editor implementation
│   │   ├── auxilarydata/        # Songs, preferences, play markers
│   │   ├── components/          # UI components (tables, buttons)
│   │   ├── converters/          # Format converters (MOD, SNG, CT)
│   │   ├── datacopy/            # Copy/paste for orderlist/sequences
│   │   ├── datasources/         # Data abstraction for memory access
│   │   ├── driver/              # Driver info and architecture
│   │   ├── instrument/          # Instrument data structures
│   │   ├── packer/              # Data packing/compression
│   │   └── screens/             # Screen layouts
│   ├── emulation/       # C64 emulation (SID chip, CPU memory)
│   └── execution/       # Execution engine
└── utils/               # File I/O, config, C64 file format
```

---

## Key Classes

### SF2::Interface

**Location**: `converters/utils/sf2_interface.h/cpp`

Central interface for all SF2 file operations.

```cpp
class Interface {
    // Table access
    GetTable(TableType type) -> DataSourceTable*

    // Order list access (3 tracks)
    GetOrderList(int track) -> DataSourceOrderList*

    // Sequence access
    GetSequence(int index) -> DataSourceSequence*

    // Driver memory (64KB)
    GetDriverMemory() -> C64File*

    // Generate output file
    GetResult() -> C64File*
}
```

**Table Types Enum**:
```cpp
enum TableType {
    Instruments,
    Commands,
    Wave,
    Pulse,
    Filter,
    HR,
    Arpeggio,
    Tempo,
    Init
}
```

**Command Enum** (Driver 11):
```cpp
Cmd_Slide = 0x00
Cmd_Vibrato = 0x01
Cmd_Portamento = 0x02
Cmd_Arpeggio = 0x03
Cmd_Fret = 0x04
Cmd_ADSR_Note = 0x08
Cmd_ADSR_Persist = 0x09
Cmd_Index_Filter = 0x0a
Cmd_Index_Wave = 0x0b
Cmd_Index_Pulse = 0x0c      // Driver 11.02+
Cmd_Tempo = 0x0d            // Driver 11.02+
Cmd_Volume = 0x0e           // Driver 11.02+
Cmd_Demo_Flag = 0x0f
```

---

### DriverInfo

**Location**: `driver/driver_info.h/cpp`

Parses and validates SF2 driver structure.

```cpp
class DriverInfo {
    // Driver identification
    m_DriverType: int           // 11, 12, 13, etc.
    m_MajorVersion: int
    m_MinorVersion: int

    // Parse header blocks
    ParseDescriptorBlock()
    ParseDriverCommonBlock()
    ParseDriverTablesBlock()
    ParseMusicDataBlock()

    // Validation
    IsValid() -> bool
}
```

#### DriverCommon Structure

Essential driver addresses:

```cpp
struct DriverCommon {
    m_InitAddress: unsigned short          // Driver init entry point
    m_UpdateAddress: unsigned short        // Main update routine
    m_DriverStateAddress: unsigned short   // State tracking location
    m_OrderListIndexAddress: unsigned short
    m_SequenceIndexAddress: unsigned short
    m_CurrentSequenceAddress: unsigned short
    m_CurrentTransposeAddress: unsigned short
}
```

#### TableDefinition Structure

Defines table memory layout:

```cpp
struct TableDefinition {
    m_Type: unsigned char       // 0x00=Generic, 0x80=Instruments, 0x81=Commands
    m_ID: unsigned char         // Table identifier for rules
    m_Name: string             // Human-readable name
    m_DataLayout: unsigned char // 0=RowMajor, 1=ColumnMajor
    m_Address: unsigned short   // Start address in memory
    m_ColumnCount: unsigned char
    m_RowCount: unsigned char
    m_Properties: unsigned char // EnableInsertDelete, LayoutVertically, etc.
}
```

#### MusicData Structure

Track and sequence organization:

```cpp
struct MusicData {
    m_TrackCount: int           // Typically 3
    m_SequenceCount: int        // Max sequences available
    m_TrackOrderListPointers: vector<unsigned short>
    m_SequencePointers: vector<unsigned short>
    m_OrderListSize: int
    m_SequenceSize: int
}
```

---

### DataSource Hierarchy

**Location**: `datasources/`

Abstract access to different data types:

```
DataSource (base)
├── DataSourceTable
│   ├── DataSourceTableRowMajor
│   └── DataSourceTableColumnMajor
├── DataSourceOrderList
├── DataSourceSequence
└── DataSourceMemory
```

#### DataSourceOrderList

```cpp
struct Entry {
    unsigned char m_Transposition;
    unsigned char m_SequenceIndex;
}
```

- Max 256 entries per track
- Supports packed format with loop index marker

#### DataSourceSequence

```cpp
struct Event {
    unsigned char m_Instrument;    // 0x80+ = no instrument
    unsigned char m_Command;       // 0x80+ = no command
    unsigned char m_Note;          // Note value
}
```

- 3 bytes per event
- Variable-length packed format

---

### C64File

**Location**: `utils/c64file.h/cpp`

Represents 64KB C64 memory image:

```cpp
class C64File {
    // Create/load
    CreateContainer(int size)
    LoadPRG(filename)  // Handles 2-byte load address prefix

    // Memory access
    GetByte(address) -> unsigned char
    SetByte(address, value)
    GetWord(address) -> unsigned short
    SetWord(address, value)

    // Block operations
    GetData(address, length) -> vector<unsigned char>
    SetData(address, data)
}

class C64FileReader {
    ReadByte() -> unsigned char
    ReadWord() -> unsigned short
    ReadString(length) -> string
}

class C64FileWriter {
    WriteByte(value)
    WriteWord(value)
    WriteString(str)
}
```

---

## Header Block System

SF2 files use a block-based header after the driver code. Each block has an ID byte followed by block-specific data.

### Block IDs

| ID | Name | Description |
|----|------|-------------|
| 1 | Descriptor | Driver type, version, name, size |
| 2 | DriverCommon | Addresses, state info |
| 3 | DriverTables | Table definitions |
| 4 | InstrumentDescriptor | Instrument cell descriptions |
| 5 | MusicData | Track/sequence counts and addresses |
| 6 | ColorRules | Table coloring rules |
| 7 | InsertDeleteRules | Row insert/delete rules |
| 8 | ActionRules | Action handling rules |
| 9 | InstrumentDataDescriptor | Extended instrument info |
| 255 | End | End of header blocks |

### Block Parsing Example

```cpp
while (true) {
    unsigned char blockID = reader.ReadByte();
    if (blockID == 255) break;

    switch (blockID) {
        case 1: ParseDescriptorBlock(reader); break;
        case 2: ParseDriverCommonBlock(reader); break;
        case 3: ParseDriverTablesBlock(reader); break;
        // ...
    }
}
```

---

## Critical Constants

### File Identification

```cpp
// Driver ID marker at top address
const unsigned short DRIVER_ID_MARKER = 0x1337;

// Auxiliary data vector offset (5 bytes before init)
const int AUX_DATA_OFFSET = -5;

// IRQ vector offset (2 bytes before init)
const int IRQ_VECTOR_OFFSET = -2;
```

### Standard Addresses

```cpp
// Typical auxiliary data pointer
const unsigned short AUX_DATA_POINTER_ADDRESS = 0x0ffb;
```

### Table Layout Types

```cpp
enum DataLayout {
    RowMajor = 0,      // Traditional row-by-row
    ColumnMajor = 1    // Column-by-column (Driver 11)
}
```

---

## Packing/Unpacking Algorithms

### Order List Packing

Order lists use variable-length encoding:

```cpp
// Packed format:
// - Entry bytes until end
// - End marker (typically 0x00 or special value)
// - Loop index marker

void PackOrderList(const vector<Entry>& entries) {
    for (auto& entry : entries) {
        // Write transposition + sequence index
        WriteByte(entry.m_Transposition);
        WriteByte(entry.m_SequenceIndex);
    }
    // Write end/loop markers
}
```

### Sequence Packing

Sequences use persistence encoding for efficiency:

```cpp
// If instrument/command same as previous, use 0x80 marker
// Otherwise write full value

void PackSequence(const vector<Event>& events) {
    unsigned char lastInstr = 0x80;
    unsigned char lastCmd = 0x80;

    for (auto& event : events) {
        if (event.m_Instrument == lastInstr)
            WriteByte(0x80);
        else {
            WriteByte(event.m_Instrument);
            lastInstr = event.m_Instrument;
        }
        // Similar for command
        WriteByte(event.m_Note);
    }
}
```

---

## Converter Implementations

### ConverterBase Interface

```cpp
class ConverterBase {
    virtual void Convert(
        const vector<unsigned char>& sourceData,
        SF2::Interface* sf2Interface
    ) = 0;
}
```

### MOD Converter

**Location**: `converters/mod/converter_mod.h/cpp`

Key features:
- 4-channel MOD to 3-channel SF2
- Channel selection for reduction
- Tempo extraction (first tempo command sets SF2 tempo)
- Triangle waveform defaults for instruments

### GoatTracker Converter

**Location**: `converters/gt/converter_gt.cpp`

Handles .sng files with:
- Arpeggio conversion
- Slide/portamento mapping
- Instrument translation

### CheeseCutter Converter

**Location**: `converters/jch/converter_jch.cpp`

Handles .ct files with similar mapping strategies.

---

## Table Format Details

### WrapFormat Structure

Defines table end/loop markers:

```cpp
struct WrapFormat {
    m_ByteIDPosition: int      // Position of end marker byte
    m_ByteIDMask: unsigned char // Mask for end marker value
    m_ByteWrapPosition: int    // Position of loop marker
    m_ByteWrapMask: unsigned char // Mask for wrap value
}
```

### Table Type Constants

```cpp
const unsigned char TABLE_TYPE_GENERIC = 0x00;
const unsigned char TABLE_TYPE_INSTRUMENTS = 0x80;
const unsigned char TABLE_TYPE_COMMANDS = 0x81;
```

---

## Important Source Files

### Core Format Handling
- `runtime/editor/converters/utils/sf2_interface.h/cpp`
- `runtime/editor/driver/driver_info.h/cpp`
- `runtime/editor/driver/driver_state.h`
- `runtime/editor/driver/driver_utils.h/cpp`

### Data Structures
- `runtime/editor/datasources/datasource_orderlist.h`
- `runtime/editor/datasources/datasource_sequence.h`
- `runtime/editor/datasources/datasource_table.h`
- `runtime/editor/datasources/datasource_table_row_major.h`
- `runtime/editor/datasources/datasource_table_column_major.h`

### Instruments
- `runtime/editor/instrument/instrumentdata.h`
- `runtime/editor/instrument/instrumentdata_table.h`
- `runtime/editor/instrument/instrumentdata_tablemapping.h`

### File I/O
- `utils/c64file.h/cpp`
- `utils/utilities.h/cpp`

### Converters
- `runtime/editor/converters/converterbase.h/cpp`
- `runtime/editor/converters/mod/converter_mod.h/cpp`
- `runtime/editor/converters/gt/converter_gt.cpp`
- `runtime/editor/converters/jch/converter_jch.cpp`

---

## Implementation Notes

### Driver 11 Column-Major Layout

Driver 11 uses column-major storage for instruments:

```
Memory layout for 32 instruments × 6 bytes:
Offset 0x00-0x1F: All AD values (column 0)
Offset 0x20-0x3F: All SR values (column 1)
Offset 0x40-0x5F: All Flags values (column 2)
Offset 0x60-0x7F: All Filter indices (column 3)
Offset 0x80-0x9F: All Pulse indices (column 4)
Offset 0xA0-0xBF: All Wave indices (column 5)
```

### Sequence Event Encoding

```
0x00-0x5D: Notes (C-0 to B-7)
0x7E: Gate on (+++)
0x7F: End of sequence
0x80: Gate off (---)
```

### Instrument/Command References

In sequences:
- Instrument: `0x80` = no change, `0xA0-0xBF` = instrument 0-31
- Command: `0x80` = no change, `0xC0-0xFF` = command 0-63

---

## References

- [SF2 Format Specification](SF2_FORMAT_SPEC.md)
- [Driver Reference](DRIVER_REFERENCE.md)
- [Conversion Strategy](CONVERSION_STRATEGY.md)
- [SID Factory II GitHub](https://github.com/Chordian/sidfactory2)
