# SF2 Editor Class Reference

*Quick reference for key C++ classes in the SID Factory II editor*

## Core Classes

### SF2::Interface

**File**: `converters/utils/sf2_interface.h/cpp`

Central interface for all SF2 file operations.

```cpp
class Interface {
public:
    // Table access
    DataSourceTable* GetTable(TableType type);

    // Order lists (3 tracks)
    DataSourceOrderList* GetOrderList(int track);

    // Sequences
    DataSourceSequence* GetSequence(int index);

    // Driver memory (64KB)
    C64File* GetDriverMemory();

    // Generate output
    C64File* GetResult();
};

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
};
```

**Usage**: Primary entry point for reading/writing SF2 data.

---

### DriverInfo

**File**: `driver/driver_info.h/cpp`

Parses SF2 driver structure and metadata.

```cpp
class DriverInfo {
public:
    // Driver identification
    int m_DriverType;        // 11, 12, 13, etc.
    int m_MajorVersion;
    int m_MinorVersion;

    // Validation
    bool IsValid();

    // Header block parsing
    void ParseDescriptorBlock(C64FileReader& reader);
    void ParseDriverCommonBlock(C64FileReader& reader);
    void ParseDriverTablesBlock(C64FileReader& reader);
    void ParseMusicDataBlock(C64FileReader& reader);

    // Access structures
    DriverCommon m_DriverCommon;
    MusicData m_MusicData;
    vector<TableDefinition> m_TableDefinitions;
};
```

---

### DriverInfo::DriverCommon

Essential driver addresses.

```cpp
struct DriverCommon {
    unsigned short m_InitAddress;          // Init entry point
    unsigned short m_UpdateAddress;        // Main update routine
    unsigned short m_DriverStateAddress;   // State tracking
    unsigned short m_OrderListIndexAddress;
    unsigned short m_SequenceIndexAddress;
    unsigned short m_CurrentSequenceAddress;
    unsigned short m_CurrentTransposeAddress;
};
```

---

### DriverInfo::TableDefinition

Defines table memory layout.

```cpp
struct TableDefinition {
    unsigned char m_Type;        // 0x00=Generic, 0x80=Instruments, 0x81=Commands
    unsigned char m_ID;          // Table identifier
    string m_Name;               // Human-readable name
    unsigned char m_DataLayout;  // 0=RowMajor, 1=ColumnMajor
    unsigned short m_Address;    // Start address in memory
    unsigned char m_ColumnCount;
    unsigned char m_RowCount;
    unsigned char m_Properties;  // EnableInsertDelete, etc.
};
```

---

### DriverInfo::MusicData

Track and sequence organization.

```cpp
struct MusicData {
    int m_TrackCount;                          // Typically 3
    int m_SequenceCount;                       // Max sequences
    vector<unsigned short> m_TrackOrderListPointers;
    vector<unsigned short> m_SequencePointers;
    int m_OrderListSize;
    int m_SequenceSize;
};
```

---

## DataSource Classes

### DataSourceTable (Base)

**File**: `datasources/datasource_table.h`

Abstract table access.

```cpp
class DataSourceTable {
public:
    // Cell access
    unsigned char GetCell(int row, int col);
    void SetCell(int row, int col, unsigned char value);

    // Dimensions
    int GetRowCount();
    int GetColumnCount();

    // Memory
    unsigned short GetAddress();
};
```

### DataSourceTableRowMajor

Row-by-row storage (traditional).

```cpp
// Memory layout: row0col0, row0col1, ..., row1col0, row1col1, ...
```

### DataSourceTableColumnMajor

Column-by-column storage (Driver 11 instruments).

```cpp
// Memory layout: row0col0, row1col0, ..., row0col1, row1col1, ...
```

---

### DataSourceOrderList

**File**: `datasources/datasource_orderlist.h`

Order list with packing/unpacking.

```cpp
struct Entry {
    unsigned char m_Transposition;
    unsigned char m_SequenceIndex;
};

class DataSourceOrderList {
public:
    Entry GetEntry(int index);
    void SetEntry(int index, const Entry& entry);
    int GetLength();

    // Packing
    void Pack();
    void Unpack();
};
```

---

### DataSourceSequence

**File**: `datasources/datasource_sequence.h`

Sequence with event compression.

```cpp
struct Event {
    unsigned char m_Instrument;    // 0x80+ = no change
    unsigned char m_Command;       // 0x80+ = no change
    unsigned char m_Note;
};

class DataSourceSequence {
public:
    Event GetEvent(int row);
    void SetEvent(int row, const Event& event);
    int GetLength();

    // Packing (persistence encoding)
    void Pack();
    void Unpack();
};
```

---

## File I/O Classes

### C64File

**File**: `utils/c64file.h/cpp`

64KB C64 memory image.

```cpp
class C64File {
public:
    // Create/load
    static C64File CreateContainer(int size);
    static C64File LoadPRG(const string& filename);

    // Byte access
    unsigned char GetByte(unsigned short address);
    void SetByte(unsigned short address, unsigned char value);

    // Word access (little-endian)
    unsigned short GetWord(unsigned short address);
    void SetWord(unsigned short address, unsigned short value);

    // Block operations
    vector<unsigned char> GetData(unsigned short address, int length);
    void SetData(unsigned short address, const vector<unsigned char>& data);

    // Save
    void SavePRG(const string& filename);
};
```

### C64FileReader

Sequential read operations.

```cpp
class C64FileReader {
public:
    C64FileReader(const C64File& file, unsigned short startAddress);

    unsigned char ReadByte();
    unsigned short ReadWord();
    string ReadString(int length);
    void Skip(int bytes);
};
```

### C64FileWriter

Sequential write operations.

```cpp
class C64FileWriter {
public:
    C64FileWriter(C64File& file, unsigned short startAddress);

    void WriteByte(unsigned char value);
    void WriteWord(unsigned short value);
    void WriteString(const string& str);
};
```

---

## Converter Classes

### ConverterBase

**File**: `converters/converterbase.h/cpp`

Base interface for format converters.

```cpp
class ConverterBase {
public:
    virtual void Convert(
        const vector<unsigned char>& sourceData,
        SF2::Interface* sf2Interface
    ) = 0;
};
```

### ConverterMod

**File**: `converters/mod/converter_mod.h/cpp`

MOD file conversion.

```cpp
class ConverterMod : public ConverterBase {
public:
    // Channel selection (4 MOD → 3 SID)
    void SetChannelMapping(int modChannel1, int modChannel2, int modChannel3);

    void Convert(
        const vector<unsigned char>& sourceData,
        SF2::Interface* sf2Interface
    ) override;
};
```

### ConverterGT

GoatTracker .sng file conversion.

### ConverterJCH

CheeseCutter .ct file conversion.

---

## Instrument Classes

### InstrumentData

**File**: `instrument/instrumentdata.h`

Single instrument data.

```cpp
class InstrumentData {
public:
    unsigned char GetByte(int index);
    void SetByte(int index, unsigned char value);

    // Driver 11 accessors
    unsigned char GetAD();
    unsigned char GetSR();
    unsigned char GetFlags();
    unsigned char GetFilterIndex();
    unsigned char GetPulseIndex();
    unsigned char GetWaveIndex();
};
```

### InstrumentDataTable

Collection of all instruments.

```cpp
class InstrumentDataTable {
public:
    InstrumentData& GetInstrument(int index);
    int GetInstrumentCount();  // Usually 32
};
```

---

## Enums and Constants

### Command Enum

```cpp
enum Command {
    Cmd_Slide = 0x00,
    Cmd_Vibrato = 0x01,
    Cmd_Portamento = 0x02,
    Cmd_Arpeggio = 0x03,
    Cmd_Fret = 0x04,
    Cmd_ADSR_Note = 0x08,
    Cmd_ADSR_Persist = 0x09,
    Cmd_Index_Filter = 0x0a,
    Cmd_Index_Wave = 0x0b,
    Cmd_Index_Pulse = 0x0c,      // Driver 11.02+
    Cmd_Tempo = 0x0d,            // Driver 11.02+
    Cmd_Volume = 0x0e,           // Driver 11.02+
    Cmd_Demo_Flag = 0x0f
};
```

### Header Block IDs

```cpp
enum HeaderBlockID {
    Block_Descriptor = 1,
    Block_DriverCommon = 2,
    Block_DriverTables = 3,
    Block_InstrumentDescriptor = 4,
    Block_MusicData = 5,
    Block_ColorRules = 6,
    Block_InsertDeleteRules = 7,
    Block_ActionRules = 8,
    Block_InstrumentDataDescriptor = 9,
    Block_End = 255
};
```

### Constants

```cpp
const unsigned short DRIVER_ID_MARKER = 0x1337;
const unsigned char TABLE_TYPE_GENERIC = 0x00;
const unsigned char TABLE_TYPE_INSTRUMENTS = 0x80;
const unsigned char TABLE_TYPE_COMMANDS = 0x81;
```

---

## References

- [SF2 Source Analysis](SF2_SOURCE_ANALYSIS.md) - Complete source code analysis
- [SF2 Format Specification](SF2_FORMAT_SPEC.md) - File format details
- [SID Factory II GitHub](https://github.com/Chordian/sidfactory2)
